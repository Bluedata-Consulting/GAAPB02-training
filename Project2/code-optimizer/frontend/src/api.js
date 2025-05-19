// src/api.js
const API = import.meta.env.VITE_API_URL || "/api";  // Use environment variable with fallback

function fetchOpts(method, body) {
  const opts = { method, credentials: "include" };
  if (body) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body    = JSON.stringify(body);
  }
  return opts;
}

// Simple retry mechanism for session issues
async function withRetry(fn, maxRetries = 2) {
  let retries = 0;
  while (true) {
    try {
      return await fn();
    } catch (error) {
      if (error.message.includes("session") && retries < maxRetries) {
        console.log("Session error, retrying...");
        await createSession();
        retries++;
      } else {
        throw error;
      }
    }
  }
}

export async function createSession() {
  const res = await fetch(`${API}/session`, fetchOpts("POST"));
  if (!res.ok) throw new Error("session failed");
  return res.json();
}

export async function cloneRepo(url) {
  return withRetry(async () => {
    const res = await fetch(`${API}/clone`, fetchOpts("POST", { repo_url: url }));
    if (!res.ok) throw new Error(`clone failed (${res.status})`);
    return res.json();
  });
}

export async function getFile(path) {
  return withRetry(async () => {
    const res = await fetch(
      `${API}/file?relative_path=${encodeURIComponent(path)}`,
      fetchOpts("GET")
    );
    if (!res.ok) throw new Error(`getFile failed (${res.status})`);
    return res.text();
  });
}

export async function optimise(code, feedback) {
  return withRetry(async () => {
    const res = await fetch(
      `${API}/optimise`,
      fetchOpts("POST", { code, feedback })
    );
    if (!res.ok) throw new Error(`optimise failed (${res.status})`);
    return res.json();
  });
}

// Simple health check function
export async function checkHealth() {
  try {
    const res = await fetch(`${API}/health`, fetchOpts("GET"));
    return res.ok;
  } catch (error) {
    console.error("Health check failed:", error);
    return false;
  }
}