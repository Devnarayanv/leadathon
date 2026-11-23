import { useMemo, useState } from "react";
import { AlertCircle, Bell, CalendarPlus, Check, Download, ExternalLink, Loader2 } from "lucide-react";
import { CONFIDENCE_LABELS, t } from "../i18n.js";
import { downloadCalendar } from "../services/api.js";
import { SourceText } from "./workspace/common.jsx";
import { REMINDER_OPTIONS, isExportable, openGoogleCalendar } from "../services/calendarLinks.js";

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

function daysAway(iso) {
  if (!iso) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(target.getTime())) return null;
  return Math.round((target - today) / 86400000);
}

function Relative({ iso }) {
  const days = daysAway(iso);
  if (days == null) return null;
  if (days < 0) return <span className="text-ink-faint">passed</span>;
  if (days === 0) return <span className="text-crit">today</span>;
  if (days === 1) return <span className="text-crit">tomorrow</span>;
  if (days <= 30) return <span className="text-warn">in {days} days</span>;
  return <span className="text-ink-faint">in {Math.round(days / 30)} months</span>;
}

export default function DeadlineList({ deadlines, filename, language }) {
  const [verified, setVerified] = useState({});
  const [reminderDays, setReminderDays] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const datedDeadlines = useMemo(
    () => (deadlines ?? []).filter(isExportable),
    [deadlines],
  );
  const exportable = useMemo(
    () => datedDeadlines.filter((item) => verified[item.id]),
    [datedDeadlines, verified],
  );

  const toggle = (id, checked) =>
    setVerified((current) => ({ ...current, [id]: checked }));

  const onDownload = async () => {
    setError("");
    setBusy(true);
    try {
      await downloadCalendar({
        filename,
        reminderDays,
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
      <section id="deadlines" className="card p-5 sm:p-6">
        <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
          {t(language, "deadlines")}
        </h2>
        <p className="mt-2 text-[0.85rem] text-ink-soft">{t(language, "noDeadlines")}</p>
      </section>
    );
  }

  return (
    <section id="deadlines" className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
          {t(language, "deadlines")}
        </h2>
        <span className="text-[0.72rem] tabular-nums text-ink-faint">
          {deadlines.length} found
        </span>
      </div>

      <p className="panel-note mt-2">{t(language, "deadlineHint")}</p>

      <ul className="mt-4 divide-y divide-line border-t border-line">
        {deadlines.map((item) => {
          const checked = Boolean(verified[item.id]);
          const dated = isExportable(item);
          return (
            <li key={item.id} className="py-3.5">
              <div className="flex items-start gap-3">
                {dated ? (
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={checked}
                    onClick={() => toggle(item.id, !checked)}
                    title={t(language, "verified")}
                    className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border transition-colors ${
                      checked
                        ? "border-ink bg-ink text-on-ink"
                        : "border-line-strong bg-surface hover:border-ink-soft"
                    }`}
                  >
                    {checked && <Check size={11} strokeWidth={3} />}
                  </button>
                ) : (
                  <span className="mt-0.5 h-4 w-4 shrink-0" />
                )}

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <p className="text-[0.85rem] font-medium tabular-nums">
                      {formatDate(item.date_iso) ?? item.date_text}
                    </p>
                    <p className="text-[0.72rem]">
                      <Relative iso={item.date_iso} />
                    </p>
                  </div>
                  <p className="mt-0.5 text-[0.82rem] leading-relaxed text-ink-soft">
                    {item.description}
                  </p>
                  <p className="mt-1 flex flex-wrap items-center gap-x-2 text-[0.7rem] text-ink-faint">
                    {item.page != null && (
                      <span className="tabular-nums">
                        {t(language, "page")} {item.page}
                      </span>
                    )}
                    <span>
                      {CONFIDENCE_LABELS[language]?.[item.confidence] ?? item.confidence}
                    </span>
                    {item.recurrence && (
                      <span className="text-warn">Repeats: {item.recurrence}</span>
                    )}
                    {item.evidence_status === "calculated" && (
                      <span className="text-warn">Calculated, check before export</span>
                    )}
                  </p>

                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <SourceText text={item.source_text} language={language} />
                    {dated && (
                      <button
                        type="button"
                        onClick={() => openGoogleCalendar(item, filename)}
                        className="inline-flex items-center gap-1 text-[0.72rem] font-medium text-ink-soft transition-colors hover:text-ink"
                      >
                        <CalendarPlus size={12} />
                        Google Calendar
                        <ExternalLink size={10} className="text-ink-faint" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      {datedDeadlines.length > 0 && (
        <div className="mt-4 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="flex items-center gap-1.5 text-[0.78rem] text-ink-soft">
              <Bell size={13} />
              Remind me
            </span>
            <select
              value={reminderDays}
              onChange={(event) => setReminderDays(Number(event.target.value))}
              className="field !w-auto !px-2.5 !py-1.5 text-xs"
            >
              {REMINDER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={onDownload}
              disabled={!exportable.length || busy}
              className="btn-primary ml-auto text-xs"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Download .ics
              {exportable.length > 0 && ` (${exportable.length})`}
            </button>
          </div>

          <p className="mt-2.5 text-[0.7rem] leading-relaxed text-ink-faint">
            The <strong className="font-medium">.ics</strong> file carries the reminder you
            chose and stays on your machine &mdash; open it in any calendar app.{" "}
            <strong className="font-medium">Google Calendar</strong> opens a prefilled event
            in a new tab: the date, the description and the file name are sent to Google,
            the document text is not, and Google uses your own calendar&rsquo;s default
            notification.
          </p>

          {!exportable.length && (
            <p className="mt-2 flex items-start gap-1.5 text-[0.7rem] text-ink-faint">
              <AlertCircle size={12} className="mt-0.5 shrink-0" />
              Tick the dates you have checked against the document to enable the download.
            </p>
          )}
        </div>
      )}

      {error && (
        <p className="mt-3 rounded-lg bg-crit-soft px-3 py-2.5 text-sm text-crit">{error}</p>
      )}
    </section>
  );
}
