"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useAuth } from "./components/auth-provider";
import { apiFetch } from "./lib/api";
import {
  clearPendingWorkspace,
  readPendingWorkspace,
  savePendingWorkspace,
} from "./lib/pending-workspace";
import styles from "./page.module.css";

type Workspace = {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

const workspaceMarks = [
  styles.mark1,
  styles.mark2,
  styles.mark3,
  styles.mark4,
];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

async function readResponse<T>(response: Response): Promise<T> {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "The request failed.");
  }

  return data as T;
}

export default function HomePage() {
  const router = useRouter();
  const { session, signOut } = useAuth();
  const pendingCreationStarted = useRef(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceDescription, setWorkspaceDescription] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchWorkspaces = useCallback(async () => {
    const response = await apiFetch("/workspaces");
    return readResponse<Workspace[]>(response);
  }, []);

  const postWorkspace = useCallback(
    async (
      name: string,
      description: string | null,
      requestId: string,
    ) => {
      const response = await apiFetch("/workspaces", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": requestId,
        },
        body: JSON.stringify({ name, description }),
      });

      return readResponse<Workspace>(response);
    },
    [],
  );

  useEffect(() => {
    if (!session) {
      setWorkspaces([]);
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    void fetchWorkspaces()
      .then((data) => {
        if (!cancelled) {
          setWorkspaces(data);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Failed to load workspaces.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchWorkspaces, session]);

  useEffect(() => {
    if (!session || pendingCreationStarted.current) {
      return;
    }

    const pendingWorkspace = readPendingWorkspace();

    if (!pendingWorkspace) {
      return;
    }

    pendingCreationStarted.current = true;
    clearPendingWorkspace();
    setIsCreating(true);
    setErrorMessage("");

    void postWorkspace(
      pendingWorkspace.name,
      pendingWorkspace.description,
      pendingWorkspace.requestId,
    )
      .then((workspace) => {
        router.replace(`/workspaces/${workspace.id}`);
      })
      .catch((error: unknown) => {
        savePendingWorkspace(pendingWorkspace);
        setWorkspaceName(pendingWorkspace.name);
        setWorkspaceDescription(pendingWorkspace.description ?? "");
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Failed to create workspace.",
        );
        pendingCreationStarted.current = false;
      })
      .finally(() => {
        setIsCreating(false);
      });
  }, [postWorkspace, router, session]);

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const name = workspaceName.trim();
    const description = workspaceDescription.trim();

    if (!name) {
      setErrorMessage("Enter a workspace name.");
      return;
    }

    if (!session) {
      savePendingWorkspace({
        name,
        description: description || null,
        requestId: crypto.randomUUID(),
      });
      router.push("/auth?mode=sign-up&next=create-workspace");
      return;
    }

    setIsCreating(true);
    setErrorMessage("");

    try {
      const workspace = await postWorkspace(
        name,
        description || null,
        crypto.randomUUID(),
      );

      setWorkspaceName("");
      setWorkspaceDescription("");
      setWorkspaces((current) => [workspace, ...current]);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Failed to create workspace.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="InsightOS home">
          <span className={styles.logoMark} aria-hidden="true">
            I
          </span>
          <span>Supertechstack</span>
        </Link>

        <div className={styles.headerActions}>
          <Link href="/demo" className={styles.demoLink}>
            View demo
          </Link>
          {session ? (
            <button type="button" onClick={() => void signOut()}>
              Sign out
            </button>
          ) : (
            <Link href="/auth" className={styles.signInLink}>
              Sign in
            </Link>
          )}
        </div>
      </header>

      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}>Your research, organized</p>
          <h1>Turn scattered sources into clear, grounded insight.</h1>
          <p className={styles.heroDescription}>
            Build focused workspaces, index source material, and generate
            evidence-backed answers without losing track of where they came
            from.
          </p>

          <div className={styles.featureList}>
            <span>
              <i aria-hidden="true">✓</i> Semantic search
            </span>
            <span>
              <i aria-hidden="true">✓</i> Grounded answers
            </span>
            <span>
              <i aria-hidden="true">✓</i> Saved reports
            </span>
          </div>
          <div className={styles.heroActions}>
            <Link href="/demo" className={styles.primaryAction}>
              Explore demo workspace <span aria-hidden="true">→</span>
            </Link>
            {!session && (
              <Link href="/auth?mode=sign-up" className={styles.secondaryAction}>
                Create an account
              </Link>
            )}
          </div>
        </div>

        <div className={styles.createCard}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.step}>Get started</p>
              <h2>Create a workspace</h2>
            </div>
            <span className={styles.cardIcon} aria-hidden="true">
              +
            </span>
          </div>

          <p className={styles.cardDescription}>
            Give your research a clear scope. You can add and index sources
            after creating it.
          </p>

          <form onSubmit={createWorkspace} className={styles.form}>
            <label>
              Workspace name
              <input
                value={workspaceName}
                onChange={(event) => setWorkspaceName(event.target.value)}
                placeholder="e.g. AI full-stack job research"
                disabled={isCreating}
                maxLength={120}
                autoComplete="off"
              />
            </label>

            <label>
              Description <span>Optional</span>
              <textarea
                value={workspaceDescription}
                onChange={(event) =>
                  setWorkspaceDescription(event.target.value)
                }
                placeholder="What are you researching?"
                rows={4}
                disabled={isCreating}
                maxLength={500}
              />
            </label>

            {errorMessage && (
              <p className={styles.error} role="alert">
                {errorMessage}
              </p>
            )}

            <button type="submit" disabled={isCreating}>
              {isCreating ? "Creating workspace…" : "Create workspace"}
              {!isCreating && <span aria-hidden="true">→</span>}
            </button>
          </form>
        </div>
      </section>

      {session && <section className={styles.workspaceSection}>
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.eyebrow}>Library</p>
            <h2>Your workspaces</h2>
          </div>
          <span className={styles.workspaceCount}>
            {workspaces.length} {workspaces.length === 1 ? "workspace" : "workspaces"}
          </span>
        </div>

        {isLoading ? (
          <div className={styles.loadingGrid} aria-label="Loading workspaces">
            {[1, 2, 3].map((item) => (
              <div key={item} className={styles.skeleton} />
            ))}
          </div>
        ) : workspaces.length === 0 ? (
          <div className={styles.emptyState}>
            <span aria-hidden="true">◇</span>
            <h3>No workspaces yet</h3>
            <p>Create your first workspace above to begin organizing research.</p>
          </div>
        ) : (
          <div className={styles.workspaceGrid}>
            {workspaces.map((workspace, index) => (
              <Link
                key={workspace.id}
                href={`/workspaces/${workspace.id}`}
                className={styles.workspaceCard}
              >
                <div className={styles.workspaceCardTop}>
                  <span
                    className={`${styles.workspaceMark} ${
                      workspaceMarks[index % workspaceMarks.length]
                    }`}
                    aria-hidden="true"
                  >
                    {workspace.name.charAt(0).toUpperCase()}
                  </span>
                  <span className={styles.openIcon} aria-hidden="true">
                    ↗
                  </span>
                </div>

                <div>
                  <h3>{workspace.name}</h3>
                  <p>
                    {workspace.description ||
                      "Add sources and ask grounded questions in this workspace."}
                  </p>
                </div>

                <div className={styles.workspaceMeta}>
                  <span>Created {formatDate(workspace.created_at)}</span>
                  <strong>Open workspace</strong>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>}
    </main>
  );
}
