import { useMemo, useState } from "react";
import { CalendarDays, CalendarPlus, Info, Loader2 } from "lucide-react";
import { CONFIDENCE_LABELS, t } from "../i18n.js";
import { downloadCalendar } from "../services/api.js";

function formatDate(iso) {
  if (!iso) return null;
  const parsed = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function DeadlineList({ deadlines, filename, language }) {
  const [verified, setVerified] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const exportable = useMemo(
    () => (deadlines ?? []).filter((item) => item.date_iso && verified[item.id]),
    [deadlines, verified],
  );

  const onExport = async () => {
    setError("");
    setBusy(true);
    try {
      await downloadCalendar({
        filename,
        deadlines: exportable.map((item) => ({
          date_iso: item.date_iso,
          description: item.description,
          source_text: item.source_text,
          page: item.page,
        })),
      });
    } catch (exception) {
      setError(exception.message);
    } finally {
      setBusy(false);
    }
  };

  if (!deadlines?.length) {
    return (
      <section className="card p-5 sm:p-6">
        <h2 className="text-sm font-semibold">{t(language, "deadlines")}</h2>
        <p className="mt-2 text-sm text-ink-soft">{t(language, "noDeadlines")}</p>
      </section>
    );
  }

  return (
    <section id="deadlines" className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">{t(language, "deadlines")}</h2>
        <span className="text-xs text-ink-soft">{deadlines.length} found</span>
      </div>

      <p className="mt-2 flex items-start gap-2 rounded-lg bg-note-soft px-3.5 py-2.5 text-xs text-note">
        <Info size={14} className="mt-0.5 shrink-0" />
        <span>{t(language, "deadlineHint")}</span>
      </p>

      <ul className="mt-4 space-y-3">
        {deadlines.map((item) => (
          <li key={item.id} className="rounded-lg border border-line p-3.5">
            <div className="flex flex-wrap items-start gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-canvas text-ink-soft">
                <CalendarDays size={16} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">
                  {formatDate(item.date_iso) ?? item.date_text}
                </p>
                <p className="mt-0.5 text-xs text-ink-soft">{item.description}</p>
                <p className="mt-1 flex flex-wrap items-center gap-x-2 text-[0.7rem] text-ink-soft">
                  {item.page != null && (
                    <span>
                      {t(language, "page")} {item.page}
                    </span>
                  )}
                  <span>&middot;</span>
                  <span>
                    {CONFIDENCE_LABELS[language]?.[item.confidence] ?? item.confidence}
                  </span>
                  <span>&middot;</span>
                  <span>document wording: &ldquo;{item.date_text}&rdquo;</span>
                </p>
              </div>
              {item.date_iso ? (
                <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={Boolean(verified[item.id])}
                    onChange={(event) =>
                      setVerified((current) => ({
                        ...current,
                        [item.id]: event.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-line accent-[var(--color-brand)]"
                  />
                  {t(language, "verified")}
                </label>
              ) : (
                <span className="chip shrink-0 bg-warn-soft text-warn">
                  no exact date
                </span>
              )}
            </div>
            <p className="evidence mt-2.5">{item.source_text}</p>
          </li>
        ))}
      </ul>

      {error && (
        <p className="mt-3 rounded-lg bg-crit-soft px-3.5 py-2.5 text-sm text-crit">{error}</p>
      )}

      <button
        type="button"
        onClick={onExport}
        disabled={!exportable.length || busy}
        className="btn-primary mt-4 w-full sm:w-auto"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : <CalendarPlus size={16} />}
        {t(language, "exportCalendar")}
        {exportable.length > 0 && ` (${exportable.length})`}
      </button>
    </section>
  );
}
