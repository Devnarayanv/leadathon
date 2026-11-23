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

// The <audio> element fetches this directly, so the caller needs the URL.
export function speakUrl() {
  return `${BASE}/api/tts`;
}

export async function downloadCalendar({ filename, deadlines, reminderDays = 3 }) {
  const response = await fetch(`${BASE}/api/calendar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, deadlines, reminder_days: reminderDays }),
  });
  if (!response.ok) throw await parseError(response);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `docdecode-${filename.replace(/\.[^.]+$/, "")}.ics`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking synchronously can cancel the download in some browsers: give the
  // navigation time to start, then release the blob.
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

// Re-runs the type-specific pipeline under a corrected document type. Sends
// back the text already extracted, so no re-upload and no second OCR pass.
export function reclassifyDocument({ docType, language, filename, pages, signal }) {
  return postJson(
    "/api/reclassify",
    { doc_type: docType, language, filename, pages },
    signal,
  );
}

// Compares two analysed documents. Both sides are the ComparableDocument shape
// built from analysis results, never from free text.
export function compareDocuments({ left, right, signal }) {
  return postJson("/api/compare", { left, right }, signal);
}

// Sample documents. The backend route may not exist yet; callers must treat a
// failure as "no demo section", never as an error to the user.
export async function listDemoDocuments(signal) {
  const response = await fetch(`${BASE}/api/demo`, { signal });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

export function demoFileUrl(id) {
  return `${BASE}/api/demo/${encodeURIComponent(id)}/file`;
}

// Tender eligibility checklist. Sends what the user typed plus the tender's
// requirements; the backend returns buckets, never an eligibility verdict.
export function checkEligibility({ business, requirements, signal }) {
  return postJson("/api/eligibility", { ...business, requirements }, signal);
}
