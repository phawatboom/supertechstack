"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { getSupabaseClient } from "../lib/supabase";
import styles from "./page.module.css";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [confirmationError, setConfirmationError] = useState("");

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const requestedMode = query.get("mode");
    const description =
      query.get("error_description") ?? hash.get("error_description");

    if (requestedMode === "sign-up") {
      setMode("sign-up");
    }

    if (description) {
      setConfirmationError(description.replaceAll("+", " "));
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setMessage("");

    const supabase = getSupabaseClient();
    const next = new URLSearchParams(window.location.search).get("next");
    const confirmationUrl = new URL("/auth", window.location.origin);

    if (next) {
      confirmationUrl.searchParams.set("next", next);
    }

    const result =
      mode === "sign-in"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({
            email,
            password,
            options: {
              emailRedirectTo: confirmationUrl.toString(),
            },
          });

    if (result.error) {
      setMessage(result.error.message);
    } else if (mode === "sign-up" && !result.data.session) {
      setMessage("Check your email to confirm your account, then sign in.");
    }

    setIsSubmitting(false);
  }

  function changeMode(nextMode: "sign-in" | "sign-up") {
    setMode(nextMode);
    setMessage("");
  }

  return (
    <main className={styles.shell}>
      <section className={styles.productPanel}>
        <Link href="/" className={styles.brand}>
          <span aria-hidden="true">S</span>
          SuperTechStack
        </Link>

        <div className={styles.productCopy}>
          <p className={styles.eyebrow}>Research you can verify</p>
          <h1>A Source-Grounded Research Workspace</h1>
          <p>
            Build a research library, retrieve the evidence, and
            generate answers backed by clear citations.
          </p>
          <Link href="/demo" className={styles.demoButton}>
            <span>Explore the live demo</span>
            <ArrowRight
              aria-hidden="true"
              className={styles.arrowRight}
              size={14}
            />
          </Link>
        </div>

        <div className={styles.benefits}>
          <div>
            <span aria-hidden="true">01</span>
            <p><strong>Private workspaces</strong>Keep your research private and organised.</p>
          </div>
          <div>
            <span aria-hidden="true">02</span>
            <p><strong>Traceable answers</strong>Review evidence and citations.</p>
          </div>
          <div>
            <span aria-hidden="true">03</span>
            <p><strong>Semantic retrieval</strong>Find meaning, not just keywords.</p>
          </div>
        </div>
      </section>

      <section className={styles.authPanel}>
        <div className={styles.card}>
          <div className={styles.mobileBrand}>
            <span aria-hidden="true">S</span>
            SuperTechStack
          </div>

          <div className={styles.tabs} aria-label="Authentication mode">
            <button
              type="button"
              className={mode === "sign-in" ? styles.activeTab : ""}
              onClick={() => changeMode("sign-in")}
            >
              Sign in
            </button>
            <button
              type="button"
              className={mode === "sign-up" ? styles.activeTab : ""}
              onClick={() => changeMode("sign-up")}
            >
              Create account
            </button>
          </div>

          <header className={styles.cardHeader}>
            <p className={styles.eyebrow}>
              {mode === "sign-in" ? "Welcome back" : "Start researching"}
            </p>
            <h2>
              {mode === "sign-in"
                ? "Sign in to your workspace"
                : "Create your research account"}
            </h2>
            <p>
              {mode === "sign-in"
                ? "Continue to your private sources, searches, and reports."
                : "Create isolated workspaces backed by verified authentication."}
            </p>
          </header>

          <form onSubmit={submit} className={styles.form}>
            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </label>

            <label>
              <span className={styles.labelRow}>
                Password
                <small>Minimum 8 characters</small>
              </span>
              <span className={styles.passwordField}>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  required
                  minLength={8}
                  autoComplete={
                    mode === "sign-in" ? "current-password" : "new-password"
                  }
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </span>
            </label>

            {(message || confirmationError) && (
              <p
                className={`${styles.message} ${
                  confirmationError ? styles.errorMessage : ""
                }`}
                role="status"
              >
                {message || confirmationError}
              </p>
            )}

            <button
              type="submit"
              className={styles.submitButton}
              disabled={isSubmitting}
            >
              <span>
                {isSubmitting
                  ? "Please wait…"
                  : mode === "sign-in"
                    ? "Sign in"
                    : "Create account"}
              </span>
            </button>
          </form>

          <p className={styles.legal}>
            By continuing, you agree to use the service responsibly and keep
            your account credentials private.
          </p>
        </div>
      </section>
    </main>
  );
}
