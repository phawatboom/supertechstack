import type { Session } from "@supabase/supabase-js";
import { getSupabaseClient, isSupabaseConfigured } from "./supabase";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const betaAccessToken = process.env.NEXT_PUBLIC_BETA_ACCESS_TOKEN;
let refreshSessionPromise: Promise<Session | null> | null = null;

type ApiFetchInit = RequestInit & {
  auth?: boolean;
};

function refreshSessionOnce(): Promise<Session | null> {
  if (refreshSessionPromise) {
    return refreshSessionPromise;
  }

  const supabase = getSupabaseClient();

  refreshSessionPromise = supabase.auth
    .refreshSession()
    .then(({ data, error }) => (error ? null : data.session))
    .finally(() => {
      refreshSessionPromise = null;
    });

  return refreshSessionPromise;
}

export async function apiFetch(
  path: string,
  init: ApiFetchInit = {},
): Promise<Response> {
  const { auth = true, ...requestInit } = init;

  async function request(accessToken?: string) {
    const headers = new Headers(requestInit.headers);

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    return fetch(`${apiUrl}${path}`, {
      ...requestInit,
      headers,
    });
  }

  if (!auth) {
    return request();
  }

  if (!isSupabaseConfigured) {
    return request(betaAccessToken);
  }

  const supabase = getSupabaseClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const response = await request(session?.access_token);

  if (response.status !== 401 || !session) {
    return response;
  }

  const refreshedSession = await refreshSessionOnce();

  if (!refreshedSession) {
    return response;
  }

  return request(refreshedSession.access_token);
}
