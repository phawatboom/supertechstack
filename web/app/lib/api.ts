const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const betaAccessToken = process.env.NEXT_PUBLIC_BETA_ACCESS_TOKEN;

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);

  if (betaAccessToken) {
    headers.set("Authorization", `Bearer ${betaAccessToken}`);
  }

  return fetch(`${apiUrl}${path}`, {
    ...init,
    headers,
  });
}
