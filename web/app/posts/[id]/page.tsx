"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { apiFetch } from "../../lib/api";
import { cleanCopiedText } from "../../lib/text-cleanup";
import styles from "./page.module.css";

type PublicPost = {
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
  source_title: string | null;
};

async function readResponse<T>(response: Response): Promise<T> {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "The request failed.");
  }

  return data as T;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

function MarkdownContent({ markdown }: { markdown: string }) {
  const sanitizedMarkdown = cleanCopiedText(markdown);

  return (
    <div className={styles.postBody}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className={styles.tableWrapper}>
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {sanitizedMarkdown}
      </ReactMarkdown>
    </div>
  );
}

export default function PublicPostPage() {
  const params = useParams<{ id: string }>();
  const postId = params.id;
  const [post, setPost] = useState<PublicPost | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    void apiFetch(`/posts/${postId}`)
      .then((response) => readResponse<PublicPost>(response))
      .then((data) => {
        if (!cancelled) {
          setPost(data);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : "Failed to load post.",
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
  }, [postId]);

  if (isLoading) {
    return (
      <main className={styles.shell}>
        <div className={styles.loadingCard}>Loading post...</div>
      </main>
    );
  }

  if (errorMessage || !post) {
    return (
      <main className={styles.shell}>
        <section className={styles.errorCard}>
          <Link href="/">Back to feed</Link>
          <h1>Post unavailable</h1>
          <p>{errorMessage || "This post is not available to your account."}</p>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <nav className={styles.nav}>
        <Link href="/">Back to feed</Link>
        <span>{post.visibility}</span>
      </nav>

      <article className={styles.post}>
        <header className={styles.header}>
          <div className={styles.meta}>
            <span>{post.workspace_name}</span>
            <time dateTime={post.published_at ?? post.created_at}>
              {formatDate(post.published_at ?? post.created_at)}
            </time>
          </div>
          <h1>{post.title}</h1>
          {post.excerpt && (
            <p className={styles.excerpt}>{cleanCopiedText(post.excerpt)}</p>
          )}
          <div className={styles.provenance}>
            <span>Read-only post</span>
            {post.source_title && (
              <span>Based on source: {post.source_title}</span>
            )}
          </div>
        </header>

        <MarkdownContent markdown={post.markdown_content} />
      </article>
    </main>
  );
}
