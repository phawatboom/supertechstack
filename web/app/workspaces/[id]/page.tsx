"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
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
  original_filename: string | null;
  mime_type: string | null;
  file_size: number | null;
  extraction_status: string;
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

type DetailView =
  | { kind: "source"; item: Source }
  | { kind: "chunk"; item: Chunk };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const maxUploadSize = 20 * 1024 * 1024;

function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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
  const [uploadTitle, setUploadTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [answerQuery, setAnswerQuery] = useState("");
  const [answerResult, setAnswerResult] = useState<AnswerResult | null>(null);
  const [isAnswering, setIsAnswering] = useState(false);
  const [answerError, setAnswerError] = useState("");
  const [detailView, setDetailView] = useState<DetailView | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const closeDetailButtonRef = useRef<HTMLButtonElement>(null);

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

  useEffect(() => {
    if (!detailView) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeDetailButtonRef.current?.focus();

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDetailView(null);
      }
    }

    window.addEventListener("keydown", closeOnEscape);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [detailView]);

  function sourceTitleForChunk(chunk: Chunk) {
    return (
      sources.find((source) => source.id === chunk.source_id)?.title ??
      `Source ${chunk.source_id}`
    );
  }

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

  async function uploadSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setUploadError("Select a file before uploading.");
      return;
    }

    if (selectedFile.size > maxUploadSize) {
      setUploadError("The selected file exceeds the 20 MB limit.");
      return;
    }

    setIsUploading(true);
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      if (uploadTitle.trim()) {
        formData.append("title", uploadTitle.trim());
      }

      const response = await fetch(
        `${apiUrl}/workspaces/${workspaceId}/uploads`,
        {
          method: "POST",
          body: formData,
        },
      );

      await readResponse<Source>(response);
      const data = await fetchWorkspaceData();

      setUploadTitle("");
      setSelectedFile(null);
      setSources(data.sourcesData);
      setChunks(data.chunksData);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "Unable to upload the file.",
      );
    } finally {
      setIsUploading(false);
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
                <h2>Upload a document</h2>
              </div>
              <span className={styles.badge}>PDF · DOCX · Text</span>
            </div>

            <p className={styles.sectionCopy}>
              Upload a PDF, DOCX, TXT, Markdown, or LaTeX file up to 20 MB.
              Scanned PDFs require OCR and may not contain extractable text.
            </p>

            <form
              onSubmit={uploadSource}
              encType="multipart/form-data"
              className={styles.form}
            >
              <label>
                Source title <span className={styles.optional}>Optional</span>
                <input
                  value={uploadTitle}
                  onChange={(event) => setUploadTitle(event.target.value)}
                  placeholder="Defaults to the filename"
                  disabled={isUploading}
                  maxLength={255}
                />
              </label>

              <label className={styles.filePicker}>
                <span className={styles.filePickerIcon} aria-hidden="true">
                  ↑
                </span>
                <strong>
                  {selectedFile ? "Choose a different file" : "Choose a document"}
                </strong>
                <small>PDF, DOCX, TXT, MD, or TEX · maximum 20 MB</small>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md,.tex"
                  disabled={isUploading}
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setSelectedFile(file);
                    setUploadError("");
                  }}
                />
              </label>

              {selectedFile && (
                <div className={styles.selectedFile}>
                  <div>
                    <strong>{selectedFile.name}</strong>
                    <span>{formatFileSize(selectedFile.size)}</span>
                  </div>
                  <button
                    type="button"
                    className={styles.removeFile}
                    disabled={isUploading}
                    onClick={() => {
                      setSelectedFile(null);
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                  >
                    Remove
                  </button>
                </div>
              )}

              {uploadError && (
                <p className={styles.error} role="alert">
                  {uploadError}
                </p>
              )}

              <div className={styles.formFooter}>
                <span>Text is extracted, chunked, and indexed automatically</span>
                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                >
                  {isUploading ? "Uploading document…" : "Upload document"}
                </button>
              </div>
            </form>
          </section>

          <section className={styles.card}>
            <div className={styles.sectionHeading}>
              <div>
                <p className={styles.step}>Step 2</p>
                <h2>Paste source text</h2>
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
                <p className={styles.step}>Step 3</p>
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
                    {source.original_filename && (
                      <div className={styles.sourceDetails}>
                        <span>{source.original_filename}</span>
                        {source.file_size !== null && (
                          <span>{formatFileSize(source.file_size)}</span>
                        )}
                      </div>
                    )}
                    <p>
                      {source.raw_text.slice(0, 150)}
                      {source.raw_text.length > 150 ? "…" : ""}
                    </p>
                    <button
                      type="button"
                      className={styles.viewButton}
                      onClick={() =>
                        setDetailView({ kind: "source", item: source })
                      }
                    >
                      View full source
                      <span aria-hidden="true">→</span>
                    </button>
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
                    <button
                      type="button"
                      className={styles.viewButton}
                      onClick={() =>
                        setDetailView({ kind: "chunk", item: chunk })
                      }
                    >
                      View full chunk
                      <span aria-hidden="true">→</span>
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>
        </aside>
      </div>

      {detailView && (
        <div
          className={styles.modalBackdrop}
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setDetailView(null);
            }
          }}
        >
          <section
            className={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="detail-title"
          >
            <header className={styles.modalHeader}>
              <div>
                <p className={styles.step}>
                  {detailView.kind === "source"
                    ? "Complete source"
                    : "Complete chunk"}
                </p>
                <h2 id="detail-title">
                  {detailView.kind === "source"
                    ? detailView.item.title
                    : `${sourceTitleForChunk(detailView.item)} · Chunk ${
                        detailView.item.chunk_index + 1
                      }`}
                </h2>
              </div>
              <button
                ref={closeDetailButtonRef}
                type="button"
                className={styles.closeButton}
                aria-label="Close full content view"
                onClick={() => setDetailView(null)}
              >
                ×
              </button>
            </header>

            {detailView.kind === "source" ? (
              <>
                <div className={styles.modalMetadata}>
                  <span>{detailView.item.source_type}</span>
                  <span>{formatDate(detailView.item.created_at)}</span>
                  <span>
                    {detailView.item.raw_text.length.toLocaleString()} characters
                  </span>
                  {detailView.item.file_size !== null && (
                    <span>{formatFileSize(detailView.item.file_size)}</span>
                  )}
                  {detailView.item.original_filename && (
                    <span>{detailView.item.original_filename}</span>
                  )}
                </div>
                <div className={styles.fullContent}>
                  {detailView.item.raw_text}
                </div>
              </>
            ) : (
              <>
                <div className={styles.modalMetadata}>
                  <span>Chunk #{detailView.item.chunk_index + 1}</span>
                  <span>Source #{detailView.item.source_id}</span>
                  <span>
                    {detailView.item.content.length.toLocaleString()} characters
                  </span>
                  <span>{formatDate(detailView.item.created_at)}</span>
                </div>
                <div className={styles.fullContent}>
                  {detailView.item.content}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
