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

type PublicFeedPost = {
  id: number;
  workspace_id: number;
  source_id: number | null;
  author_id: string;
  title: string;
  slug: string;
  markdown_content: string;
  excerpt: string | null;
  cover_image_url: string | null;
  visibility: "private" | "workspace" | "unlisted" | "public";
  status: "draft" | "published" | "archived";
  published_at: string | null;
  created_at: string;
  updated_at: string;
  workspace_name: string;
};

type DashboardPost = PublicFeedPost;

function getDashboardPostKey(post: DashboardPost) {
  if (post.source_id !== null) {
    return `${post.workspace_id}:source:${post.source_id}`;
  }

  return `${post.workspace_id}:title:${post.title.trim().toLowerCase()}`;
}

function dedupeDashboardPosts(posts: DashboardPost[]) {
  const postsByKey = new Map<string, DashboardPost>();

  for (const post of posts) {
    const key = getDashboardPostKey(post);
    const current = postsByKey.get(key);

    if (
      !current ||
      new Date(post.updated_at).getTime() > new Date(current.updated_at).getTime()
    ) {
      postsByKey.set(key, post);
    }
  }

  return Array.from(postsByKey.values());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

function formatDisplayLabel(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/\b[\p{L}\p{N}]/gu, (character) => character.toUpperCase());
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
  const [feedPosts, setFeedPosts] = useState<PublicFeedPost[]>([]);
  const [isFeedLoading, setIsFeedLoading] = useState(true);
  const [feedError, setFeedError] = useState("");
  const [privatePosts, setPrivatePosts] = useState<DashboardPost[]>([]);
  const [isPrivatePostsLoading, setIsPrivatePostsLoading] = useState(false);
  const [privatePostsError, setPrivatePostsError] = useState("");
  const [isCreateWorkspaceOpen, setIsCreateWorkspaceOpen] = useState(false);

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
    let cancelled = false;

    void apiFetch("/feed/public?limit=6")
      .then((response) => readResponse<PublicFeedPost[]>(response))
      .then((data) => {
        if (!cancelled) {
          setFeedPosts(data);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setFeedError(
            error instanceof Error ? error.message : "Failed to load feed.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsFeedLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
      setIsCreateWorkspaceOpen(false);
      router.push(`/workspaces/${workspace.id}`);
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

  useEffect(() => {
    if (!session || workspaces.length === 0) {
      setPrivatePosts([]);
      setIsPrivatePostsLoading(false);
      return;
    }

    let cancelled = false;
    setIsPrivatePostsLoading(true);
    setPrivatePostsError("");

    void Promise.all(
      workspaces.map(async (workspace) => {
        const response = await apiFetch(`/workspaces/${workspace.id}/posts`);
        const posts = await readResponse<Omit<DashboardPost, "workspace_name">[]>(
          response,
        );

        return posts.map((post) => ({
          ...post,
          workspace_name: workspace.name,
        }));
      }),
    )
      .then((groups) => {
        if (cancelled) {
          return;
        }

        setPrivatePosts(
          dedupeDashboardPosts(
            groups.flat().filter((post) => post.visibility !== "public"),
          )
            .sort(
              (left, right) =>
                new Date(right.updated_at).getTime() -
                new Date(left.updated_at).getTime(),
            )
            .slice(0, 8),
        );
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPrivatePostsError(
            error instanceof Error
              ? error.message
              : "Failed to load private posts.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsPrivatePostsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [session, workspaces]);

  const createWorkspaceForm = (
    <form onSubmit={createWorkspace} className={styles.form}>
      <label>
        Workspace name
        <input
          value={workspaceName}
          onChange={(event) => setWorkspaceName(event.target.value)}
          placeholder="e.g. AI industry research"
          disabled={isCreating}
          maxLength={120}
          autoComplete="off"
        />
      </label>

      <label>
        Description <span>Optional</span>
        <textarea
          value={workspaceDescription}
          onChange={(event) => setWorkspaceDescription(event.target.value)}
          placeholder="What are you researching?"
          rows={3}
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
        {isCreating ? "Creating workspace..." : "Create workspace"}
      </button>
    </form>
  );

  return (
    <main className={styles.shell}>
      <header
        className={`${styles.header} ${session ? styles.dashboardHeader : ""}`}
      >
        <Link href="/" className={styles.brand} aria-label="InsightOS home">
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

      {!session && (
        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>Your research, organized</p>

            <div className={styles.heroVisual} aria-hidden="true">
              <img
                src="https://images.phawats.com/homepage_workflow_interface_design_3.png"
                alt=""
              />
            </div>
          </div>

          <div className={styles.createCard}>
            <div className={styles.cardHeader}>
              <div>
                <p className={styles.step}>Get started</p>
                <h2>Create a workspace</h2>
              </div>
            </div>

            <p className={styles.cardDescription}>
              Give your research a clear scope. You can add and index sources
              after creating it.
            </p>

            {createWorkspaceForm}
          </div>
        </section>
      )}

      {session && (
        <section className={styles.workspaceSection}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Library</p>
            </div>
          </div>

          {isLoading ? (
            <div className={styles.loadingGrid} aria-label="Loading workspaces">
              {[1, 2, 3].map((item) => (
                <div key={item} className={styles.skeleton} />
              ))}
            </div>
          ) : workspaces.length === 0 ? (
            <div className={styles.emptyState}>
              <span aria-hidden="true">&#9671;</span>
              <h3>No workspaces yet</h3>
              <p>Create your first workspace to begin organizing research.</p>
              <button
                type="button"
                className={styles.emptyStateAction}
                onClick={() => setIsCreateWorkspaceOpen(true)}
              >
                New workspace
              </button>
            </div>
          ) : (
            <div className={styles.workspaceGrid}>
              {workspaces.map((workspace) => (
                <Link
                  key={workspace.id}
                  href={`/workspaces/${workspace.id}`}
                  className={styles.workspaceCard}
                >
                  <div>
                    <h3>{workspace.name}</h3>
                  </div>

                  <div className={styles.workspaceMeta}>
                    <span>{formatDate(workspace.created_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      {session && (
        <section className={styles.feedSection}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.eyebrow}>Private</p>
            </div>
          </div>

          {isPrivatePostsLoading ? (
            <div
              className={styles.loadingGrid}
              aria-label="Loading private posts"
            >
              {[1, 2, 3].map((item) => (
                <div key={item} className={styles.skeleton} />
              ))}
            </div>
          ) : privatePostsError ? (
            <p className={styles.error} role="alert">
              {privatePostsError}
            </p>
          ) : privatePosts.length === 0 ? (
            <div className={styles.emptyState}>
              <span aria-hidden="true">&#9671;</span>
              <h3>No private posts yet</h3>
              <p>Drafts and private workspace posts will appear here.</p>
            </div>
          ) : (
            <div className={styles.feedGrid}>
              {privatePosts.map((post) => (
                <Link
                  key={post.id}
                  href={`/posts/${post.id}`}
                  className={styles.feedCard}
                >
                  <div>
                    <div className={styles.feedMeta}>
                      <span>{formatDisplayLabel(post.workspace_name)}</span>
                      <time dateTime={post.updated_at}>
                        {formatDate(post.updated_at)}
                      </time>
                    </div>
                    <h3>{post.title}</h3>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      <section className={styles.feedSection}>
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.eyebrow}>Public</p>
          </div>
        </div>

        {isFeedLoading ? (
          <div className={styles.loadingGrid} aria-label="Loading public feed">
            {[1, 2, 3].map((item) => (
              <div key={item} className={styles.skeleton} />
            ))}
          </div>
        ) : feedError ? (
          <p className={styles.error} role="alert">
            {feedError}
          </p>
        ) : feedPosts.length === 0 ? (
          <div className={styles.emptyState}>
            <span aria-hidden="true">&#9671;</span>
            <h3>No public posts yet</h3>
            <p>Published posts marked public will appear here.</p>
          </div>
        ) : (
          <div className={styles.feedGrid}>
            {feedPosts.map((post) => (
              <Link
                key={post.id}
                href={`/posts/${post.id}`}
                className={styles.feedCard}
              >
                <div>
                  <div className={styles.feedMeta}>
                    <span>{formatDisplayLabel(post.workspace_name)}</span>
                    <time dateTime={post.published_at ?? post.created_at}>
                      {formatDate(post.published_at ?? post.created_at)}
                    </time>
                  </div>
                  <h3>{post.title}</h3>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {isCreateWorkspaceOpen && (
        <div
          className={styles.modalBackdrop}
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isCreating) {
              setIsCreateWorkspaceOpen(false);
            }
          }}
        >
          <section
            className={styles.modalPanel}
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-workspace-title"
          >
            <div className={styles.modalHeader}>
              <div>
                <p className={styles.step}>New workspace</p>
                <h2 id="create-workspace-title">Create a workspace</h2>
              </div>
              <button
                type="button"
                className={styles.closeModalButton}
                onClick={() => setIsCreateWorkspaceOpen(false)}
                disabled={isCreating}
                aria-label="Close create workspace dialog"
              >
                &times;
              </button>
            </div>
            <p className={styles.cardDescription}>
              Give your research a clear scope. You can add sources after
              creating it.
            </p>
            {createWorkspaceForm}
          </section>
        </div>
      )}
    </main>
  );
}
