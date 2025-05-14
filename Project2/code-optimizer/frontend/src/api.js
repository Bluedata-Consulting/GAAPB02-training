const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function createSession() {
  const res = await fetch(`${API}/session`, { method: "POST", credentials: "include" });
  if (!res.ok) throw new Error("session failed");
}

export async function cloneRepo(url) {
  const res = await fetch(`${API}/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ repo_url: url }),
  });
  if (!res.ok) throw new Error("clone failed");
  return res.json(); // {files: []}
}

export async function getFile(path) {
  return fetch(`${API}/file?relative_path=${encodeURIComponent(path)}`, {
    credentials: "include",
  }).then((r) => r.text());
}

export async function optimise(code, feedback) {
  const res = await fetch(`${API}/optimise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ code, feedback }),
  });
  if (!res.ok) throw new Error("optimise failed");
  return res.json(); // {optimised, feedback_history}
}
