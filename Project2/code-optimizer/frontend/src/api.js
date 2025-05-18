// src/api.js
const API = "/api";  // always proxy /api → backend

function fetchOpts(method, body) {
  const opts = { method, credentials: "include" };
  if (body) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body    = JSON.stringify(body);
  }
  return opts;
}

export async function createSession() {
  const res = await fetch(`${API}/session`, fetchOpts("POST"));
  if (!res.ok) throw new Error("session failed");
}

export async function cloneRepo(url) {
  const res = await fetch(`${API}/clone`, fetchOpts("POST", { repo_url: url }));
  if (!res.ok) throw new Error(`clone failed (${res.status})`);
  return res.json();
}

export async function getFile(path) {
  const res = await fetch(
    `${API}/file?relative_path=${encodeURIComponent(path)}`,
    fetchOpts("GET")
  );
  if (!res.ok) throw new Error(`getFile failed (${res.status})`);
  return res.text();
}

export async function optimise(code, feedback) {
  const res = await fetch(
    `${API}/optimise`,
    fetchOpts("POST", { code, feedback })
  );
  if (!res.ok) throw new Error(`optimise failed (${res.status})`);
  return res.json();
  
}