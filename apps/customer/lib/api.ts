// Thin fetch wrapper for api-public. Cookies (access_token/refresh_token) are
// httpOnly and scoped to this app's subdomain — see architecture doc §5.
//
// IMPORTANT: this file is used both by Server Components (which run inside
// the customer-web *container*) and by Client Components (which run in the
// user's browser on the host machine). Those two contexts can't share one
// "localhost" URL:
//   - Browser  -> http://localhost:8001 (the published port on the host)
//   - Server   -> http://api-public:8000 (the Docker Compose service name;
//                 "localhost" inside the container means the container itself)
const API_URL =
  typeof window === "undefined"
    ? process.env.API_URL_INTERNAL || "http://api-public:8000/api/v1"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
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
};