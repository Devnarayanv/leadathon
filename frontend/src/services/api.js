// All backend calls live here. The dev server proxies /api to FastAPI, so the
// browser only ever talks to its own origin.
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function parseError(response) {
  let detail = `Request failed (HTTP ${response.status}).`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail) && body.detail[0]?.msg)
      detail = body.detail.map((d) => d.msg).join("; ");
  } catch {
    // Non-JSON error body: keep the generic message.
  }
  return new Error(detail);
}

async function postJson(path, payload, signal) {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

export async function getHealth(signal) {
  const response = await fetch(`${BASE}/api/health`, { signal });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

export async function analyzeDocument({ file, language = "en", useAi = true, signal }) {
  const form = new FormData();
  form.append("file", file);
  form.append("language", language);
  form.append("use_ai", String(useAi));
  const response = await fetch(`${BASE}/api/analyze`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

export function askDocument({ question, segments, docType, language, signal }) {
  return postJson(
    "/api/ask",
    { question, segments, doc_type: docType, language },
    signal,
  );
}

export function explainClauses({ clauses, docType, language, signal }) {
  return postJson(
    "/api/explain",
    { clauses, doc_type: docType, language },
    signal,
  );
}

export async function downloadCalendar({ filename, deadlines }) {
  const response = await fetch(`${BASE}/api/calendar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, deadlines }),
  });
  if (!response.ok) throw await parseError(response);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `plainspeak-${filename.replace(/\.[^.]+$/, "")}.ics`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
