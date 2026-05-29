const API_BASE = import.meta.env.VITE_API_URL || "";

export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem("mp_token");
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("mp_token");
    localStorage.removeItem("mp_user");
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  return res;
}
