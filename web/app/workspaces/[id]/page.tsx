"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

type Workspace = {
  id: number;
  name: string;
  description: string | null;
};

type Source = {
  id: number;
  workspace_id: number;
  title: string;
  source_type: string;
  raw_text: string;
  created_at: string;
};

type Chunk = {
  id: number;
  source_id: number;
  workspace_id: number;
  chunk_index: number;
  content: string;
  created_at: string;
};

type Citation = {
  citation_number: number;
  chunk_id: number;
  source_id: number;
  source_title: string;
  chunk_index: number;
  content: string;
  similarity: number;
};

type AnswerResult = {
  report_id: number | null;
  answer: string;
  citations: Citation[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export default function WorkspaceDetailPage() {
  const params = useParams<{ id: string }>();
  const workspaceId = params.id;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [sourceTitle, setSourceTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [answerQuery, setAnswerQuery] = useState("");
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null);
  const [isAnswering, setIsAnswering] = useState(false);
  const [answerError, setAnswerError] = useState("");

  const fetchWorkspaceData = useCallback(async () => {
    const [workspaceResponse, sourcesResponse, chunksResponse] =
      await Promise.all([
        fetch(`${apiUrl}/workspaces/${workspaceId}`),
        fetch(`${apiUrl}/workspaces/${workspaceId}/sources`),
        fetch(`${apiUrl}/workspaces/${workspaceId}/chunks`),
      ]);

    const [workspaceData, sourcesData, chunksData] = await Promise.all([
      readResponse<Workspace>(workspaceResponse),
      readResponse<Source[]>(sourcesResponse),
      readResponse<Chunk[]>(chunksResponse),
    ]);

    return { workspaceData, sourcesData, chunksData };
  }, [workspaceId]);

  useEffect(() => {
    let cancelled = false;

    void fetchWorkspaceData()
      .then(({ workspaceData, sourcesData, chunksData }) => {
        if (!cancelled) {
          setWorkspace(workspaceData);
          setSources(sourcesData);
          setChunks(chunksData);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setSourceError(
            error instanceof Error ? error.message : "Failed to load workspace.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsPageLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchWorkspaceData]);

  async function createSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const title = sourceTitle.trim();
    const text = rawText.trim();

    if (!title || !text) {
      setSourceError("Add both a title and source text.");
      return;
    }

    setIsSaving(true);
    setSourceError("");

    try {
      const response = await fetch(
        `${apiUrl}/workspaces/${workspaceId}/sources`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, raw_text: text }),
        },
      );

      await readResponse<Source>(response);
      const data = await fetchWorkspaceData();

      setSourceTitle("");
      setRawText("");
      setSources(data.sourcesData);
      setChunks(data.chunksData);
    } catch (error) {
      setSourceError(
        error instanceof Error ? error.message : "Failed to save source.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function answerWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const query = answerQuery.trim();
    if (!query) {
      setAnswerError("Enter a question first.");
      return;
    }

    setIsAnswering(true);
    setAnswerError("");
    setAnswerResult(null);

    try {
      const response = await fetch(
        `${apiUrl}/workspaces/${workspaceId}/answer`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, limit: 5, save_report: true }),
        },
      );

      setAnswerResult(await readResponse<AnswerResult>(response));
    } catch (error) {
      setAnswerError(
        error instanceof Error
          ? error.message
          : "Failed to generate an answer.",
      );
    } finally {
      setIsAnswering(false);
    }
  }

  if (isPageLoading) {
    return (
      <main className={styles.shell}>
        <div className={styles.loadingCard}>Loading workspace…</div>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <nav className={styles.nav}>
        <Link href="/" className={styles.backLink}>
          <span aria-hidden="true">←</span> All workspaces
        </Link>
        <span className={styles.workspaceId}>Workspace #{workspaceId}</span>
      </nav>

      <header className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>Research workspace</p>
          <h1>{workspace?.name ?? `Workspace ${workspaceId}`}</h1>
          <p className={styles.description}>
            {workspace?.description ||
              "Add source material, inspect retrieved chunks, and ask grounded questions."}
          </p>
        </div>

        <div className={styles.stats}>
          <div>
            <strong>{sources.length}</strong>
            <span>Sources</span>
          </div>
          <div>
            <strong>{chunks.length}</strong>
            <span>Chunks</span>
          </div>
        </div>
      </header>

      <div className={styles.grid}>
        <div className={styles.primaryColumn}>
          <section className={styles.card}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.step}>Step 1</p>
                <h2>Add a source</h2>
              </div>
              <span className={styles.badge}>Text</span>
            </div>

            <p className={styles.sectionCopy}>
              Paste useful reference material. It will be split into searchable
              chunks and embedded automatically.
            </p>

            <form onSubmit={createSource} className={styles.form}>
              <label>
                Source title
                <input
                  value={sourceTitle}
                  onChange={(event) => setSourceTitle(event.target.value)}
                  placeholder="e.g. Product strategy notes"
                  disabled={isSaving}
                />
              </label>

              <label>
                Source text
                <textarea
                  value={rawText}
                  onChange={(event) => setRawText(event.target.value)}
                  placeholder="Paste source text here…"
                  rows={9}
                  disabled={isSaving}
                />
              </label>

              {sourceError && (
                <p className={styles.error} role="alert">
                  {sourceError}
                </p>
              )}

              <div className={styles.formFooter}>
                <span>{rawText.trim().length.toLocaleString()} characters</span>
                <button type="submit" disabled={isSaving}>
                  {isSaving ? "Processing source…" : "Save source"}
                </button>
              </div>
            </form>
          </section>

          <section className={styles.card}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.step}>Step 2</p>
                <h2>Ask this workspace</h2>
              </div>
              <span className={styles.badge}>Grounded AI</span>
            </div>

            <p className={styles.sectionCopy}>
              Answers are generated only from your saved sources and include the
              retrieved evidence.
            </p>

            <form onSubmit={answerWorkspace} className={styles.form}>
              <label>
                Your question
                <textarea
                  value={answerQuery}
                  onChange={(event) => setAnswerQuery(event.target.value)}
                  placeholder="What are the main findings across these sources?"
                  rows={4}
                  disabled={isAnswering || chunks.length === 0}
                />
              </label>

              {chunks.length === 0 && (
                <p className={styles.hint}>
                  Save at least one source before asking a question.
                </p>
              )}

              {answerError && (
                <p className={styles.error} role="alert">
                  {answerError}
                </p>
              )}

              <div className={styles.formFooter}>
                <span>Uses up to 5 relevant chunks</span>
                <button
                  type="submit"
                  disabled={isAnswering || chunks.length === 0}
                >
                  {isAnswering ? "Generating answer…" : "Generate answer"}
                </button>
              </div>
            </form>

            {answerResult && (
              <article className={styles.answer}>
                <div className={styles.answerHeader}>
                  <h3>Answer</h3>
                  {answerResult.report_id && (
                    <span>Report #{answerResult.report_id}</span>
                  )}
                </div>
                <p className={styles.answerText}>{answerResult.answer}</p>

                <h4>Retrieved evidence</h4>
                <div className={styles.citations}>
                  {answerResult.citations.map((citation) => (
                    <div key={citation.chunk_id} className={styles.citation}>
                      <div className={styles.citationHeader}>
                        <strong>
                          [{citation.citation_number}] {citation.source_title}
                        </strong>
                        <span>
                          {(citation.similarity * 100).toFixed(1)}% match
                        </span>
                      </div>
                      <p>{citation.content}</p>
                    </div>
                  ))}
                </div>
              </article>
            )}
          </section>
        </div>

        <aside className={styles.sidebar}>
          <section className={styles.card}>
            <div className={styles.sectionHeading}>
              <h2>Sources</h2>
              <span className={styles.count}>{sources.length}</span>
            </div>

            {sources.length === 0 ? (
              <div className={styles.emptyState}>
                <span aria-hidden="true">＋</span>
                <p>No sources yet</p>
                <small>Your saved references will appear here.</small>
              </div>
            ) : (
              <div className={styles.list}>
                {sources.map((source) => (
                  <article key={source.id} className={styles.sourceItem}>
                    <div className={styles.itemMeta}>
                      <span>{source.source_type}</span>
                      <time dateTime={source.created_at}>
                        {formatDate(source.created_at)}
                      </time>
                    </div>
                    <h3>{source.title}</h3>
                    <p>
                      {source.raw_text.slice(0, 150)}
                      {source.raw_text.length > 150 ? "…" : ""}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className={styles.card}>
            <div className={styles.sectionHeading}>
              <h2>Indexed chunks</h2>
              <span className={styles.count}>{chunks.length}</span>
            </div>

            {chunks.length === 0 ? (
              <div className={styles.emptyState}>
                <span aria-hidden="true">⌁</span>
                <p>Nothing indexed yet</p>
                <small>Chunks are created when you save a source.</small>
              </div>
            ) : (
              <div className={`${styles.list} ${styles.chunkList}`}>
                {chunks.map((chunk) => (
                  <article key={chunk.id} className={styles.chunkItem}>
                    <span>
                      Source {chunk.source_id} · Chunk {chunk.chunk_index + 1}
                    </span>
                    <p>{chunk.content}</p>
                  </article>
                ))}
              </div>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}
