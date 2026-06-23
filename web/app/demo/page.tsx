"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DemoWorkspace = {
  id: number;
};

export default function DemoPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    void fetch(`${apiUrl}/workspaces/demo/public`)
      .then(async (response) => {
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "The demo workspace is unavailable.");
        }

        return data as DemoWorkspace;
      })
      .then((workspace) => {
        if (!cancelled) {
          router.replace(`/workspaces/${workspace.id}?demo=1`);
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "The demo workspace is unavailable.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <main className={styles.shell}>
      <section className={styles.card}>
        <span className={styles.logo} aria-hidden="true">S</span>
        <p>Opening the live demo workspace…</p>
        {error && (
          <>
            <strong>{error}</strong>
            <Link href="/">Return home</Link>
          </>
        )}
      </section>
    </main>
  );
}
