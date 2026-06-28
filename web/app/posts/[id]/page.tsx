"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";
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
  const blocks: Array<{ kind: "h2" | "h3" | "li" | "p"; text: string }> = [];
  let paragraph: string[] = [];

  function flushParagraph() {
    const text = paragraph.join(" ").trim();

    if (text) {
      blocks.push({ kind: "p", text });
    }

    paragraph = [];
  }

  for (const rawLine of markdown.split(/\r?\n/)) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      continue;
    }

    if (line.startsWith("## ")) {
      flushParagraph();
      blocks.push({ kind: "h2", text: line.slice(3).trim() });
      continue;
    }

    if (line.startsWith("# ")) {
      flushParagraph();
      blocks.push({ kind: "h2", text: line.slice(2).trim() });
      continue;
    }

    if (line.startsWith("### ")) {
      flushParagraph();
      blocks.push({ kind: "h3", text: line.slice(4).trim() });
      continue;
    }

    if (line.startsWith("- ")) {
      flushParagraph();
      blocks.push({ kind: "li", text: line.slice(2).trim() });
      continue;
    }

    paragraph.push(line);
  }

  flushParagraph();

  return (
    <div className={styles.postBody}>
      {blocks.map((block, index) => {
        if (block.kind === "h2") {
          return <h2 key={index}>{block.text}</h2>;
        }

        if (block.kind === "h3") {
          return <h3 key={index}>{block.text}</h3>;
        }

        if (block.kind === "li") {
          return <p key={index} className={styles.listItem}>{block.text}</p>;
        }

        return <p key={index}>{block.text}</p>;
      })}
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
          <p>{errorMessage || "This post is not public."}</p>
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
          {post.excerpt && <p className={styles.excerpt}>{post.excerpt}</p>}
          <div className={styles.provenance}>
            <span>Read-only published post</span>
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
