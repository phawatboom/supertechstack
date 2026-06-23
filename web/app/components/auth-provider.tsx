"use client";

import type { Session } from "@supabase/supabase-js";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";
import { getSupabaseClient, isSupabaseConfigured } from "../lib/supabase";
import styles from "./auth-provider.module.css";

type AuthContextValue = {
  session: Session | null;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  session: null,
  signOut: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(isSupabaseConfigured);
  const isPublicPath =
    pathname === "/" ||
    pathname === "/auth" ||
    pathname === "/demo" ||
    pathname.startsWith("/workspaces/");

  useEffect(() => {
    if (!isSupabaseConfigured) {
      return;
    }

    const supabase = getSupabaseClient();

    void supabase.auth.getSession().then(({ data, error }) => {
      if (error) {
        void supabase.auth.signOut({ scope: "local" });
      }
      setSession(data.session);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession);
      setIsLoading(false);

      if (event === "SIGNED_OUT") {
        router.replace("/");
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!isSupabaseConfigured || isLoading) {
      return;
    }

    if (!session && !isPublicPath) {
      router.replace("/auth");
    } else if (session && pathname === "/auth") {
      router.replace("/");
    }
  }, [isLoading, isPublicPath, pathname, router, session]);

  if (isLoading) {
    return <div className={styles.loading}>Checking your session…</div>;
  }

  if (isSupabaseConfigured && !session && !isPublicPath) {
    return null;
  }

  async function signOut() {
    setSession(null);
    router.replace("/");
    await getSupabaseClient().auth.signOut();
  }

  return (
    <AuthContext.Provider value={{ session, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
