// Recent documents, kept in this browser only. It is a convenience list: it
// holds the filename, type and date of past analyses, never document text.
// Storage can be blocked (private window, cleared site data), so every access
// is guarded and the app works without it.

const KEY = "docdecode.recent";
const CAP = 8;

export function loadRecent() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.slice(0, CAP) : [];
  } catch {
    return [];
  }
}

export function rememberRecent(entry) {
  try {
    const next = [
      {
        id: entry.id,
        filename: entry.filename,
        docType: entry.docType,
        label: entry.label,
        savedAt: new Date().toISOString(),
      },
      ...loadRecent().filter((item) => item.id !== entry.id),
    ].slice(0, CAP);
    localStorage.setItem(KEY, JSON.stringify(next));
    return next;
  } catch {
    return loadRecent();
  }
}
