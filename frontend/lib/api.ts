export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("dataklin_token");
}

export function setSession(token: string, user: object) {
  localStorage.setItem("dataklin_token", token);
  localStorage.setItem("dataklin_user", JSON.stringify(user));
}

export function getUser(): { name?: string; email?: string; role?: string } {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem("dataklin_user") || "{}");
  } catch {
    return {};
  }
}

export function logout() {
  localStorage.removeItem("dataklin_token");
  localStorage.removeItem("dataklin_user");
  window.location.href = "/login";
}

export async function api(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (resp.status === 401 && typeof window !== "undefined") {
    logout();
    throw new Error("Sesi berakhir");
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return resp.json();
}

export async function downloadFile(path: string, filename: string) {
  const token = getToken();
  const resp = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error(`Gagal mengunduh (HTTP ${resp.status})`);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
