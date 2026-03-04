const API_URLS: Record<string, string> = {
  local: "http://localhost:8000",
  staging: "https://staging-api.example.com", // TBD
  prod: "https://api.example.com", // TBD
};

function resolveApiBase(): string {
  const params = new URLSearchParams(window.location.search);
  const env = params.get("api") ?? "local";
  return API_URLS[env] ?? API_URLS.local;
}

export const apiBase = resolveApiBase();

export function getApiEnv(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("api") ?? "local";
}

const TOKEN_KEY = "alma_admin_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${apiBase}${path}`, { ...options, headers });

  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }

  return res.json();
}
