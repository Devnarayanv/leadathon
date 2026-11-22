// Google Calendar event links.
//
// This is the one place in Doc Decode where data deliberately leaves the
// machine: opening the link hands Google the date, the short description and
// the file name. The document's own wording is NEVER put in the URL, and the
// UI says so next to the button. Everything else stays local.

const GOOGLE_BASE = "https://calendar.google.com/calendar/render";

function toGoogleDate(iso) {
  return iso.replaceAll("-", "");
}

function nextDay(iso) {
  // All-day events end on the following day (the end is exclusive).
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10).replaceAll("-", "");
}

export function isExportable(deadline) {
  return Boolean(deadline?.date_iso);
}

/**
 * Build a Google Calendar "create event" URL for one verified deadline.
 * Deliberately excludes the quoted clause text.
 */
export function googleCalendarUrl(deadline, filename) {
  if (!isExportable(deadline)) return null;

  const details = [
    "Deadline found by Doc Decode.",
    filename ? `Source file: ${filename}` : null,
    deadline.page != null ? `Page ${deadline.page} of the document.` : null,
    "You confirmed this date yourself. Check it against the original document.",
    "",
    "Doc Decode does not send your document anywhere. Only this event's date,",
    "description and file name were shared when you opened this link.",
  ]
    .filter(Boolean)
    .join("\n");

  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: deadline.description || "Document deadline",
    dates: `${toGoogleDate(deadline.date_iso)}/${nextDay(deadline.date_iso)}`,
    details,
  });
  return `${GOOGLE_BASE}?${params.toString()}`;
}

export function openGoogleCalendar(deadline, filename) {
  const url = googleCalendarUrl(deadline, filename);
  if (!url) return false;
  // noopener/noreferrer: the new tab must not get a handle on this page.
  window.open(url, "_blank", "noopener,noreferrer");
  return true;
}

export const REMINDER_OPTIONS = [
  { value: 0, label: "On the day" },
  { value: 1, label: "1 day before" },
  { value: 3, label: "3 days before" },
  { value: 7, label: "1 week before" },
  { value: 14, label: "2 weeks before" },
];
