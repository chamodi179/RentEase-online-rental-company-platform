// Points at api-admin — a separate running instance from api-public, with
// its own connection pool and its own session cookie scope (architecture doc §5, §8).
//
// Same server/browser split as the customer app's lib/api.ts: Server
// Components run inside the admin-web container, where "localhost" doesn't
// reach api-admin (a separate container) — that needs the Compose service name.
const API_URL =
  typeof window === "undefined"
    ? process.env.ADMIN_API_URL_INTERNAL || "http://api-admin:8000/api/v1"
    : process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8002/api/v1";

// Same fix as the customer app's lib/api.ts: login sets a refresh_token
// cookie but nothing consumed it before, so staff got logged out every
// time the access token expired. Refresh once, transparently, on a 401.
async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  if (res.status === 401 && !isRetry && path !== "/auth/refresh" && path !== "/auth/login") {
    const refreshRes = await fetch(`${API_URL}/auth/refresh`, { method: "POST", credentials: "include" });
    if (refreshRes.ok) {
      return request<T>(path, options, true);
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};