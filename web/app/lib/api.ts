import { getSupabaseClient, isSupabaseConfigured } from "./supabase";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const betaAccessToken = process.env.NEXT_PUBLIC_BETA_ACCESS_TOKEN;

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  async function request(accessToken?: string) {
    const headers = new Headers(init.headers);

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    return fetch(`${apiUrl}${path}`, {
      ...init,
      headers,
    });
  }

  if (!isSupabaseConfigured) {
    return request(betaAccessToken);
  }

  const supabase = getSupabaseClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  let response = await request(session?.access_token);

  if (response.status !== 401) {
    return response;
  }

  const { data, error } = await supabase.auth.refreshSession();

  if (error || !data.session) {
    await supabase.auth.signOut({ scope: "local" });
    return response;
  }

  response = await request(data.session.access_token);

  if (response.status === 401) {
    await supabase.auth.signOut({ scope: "local" });
  }

  return response;
}
