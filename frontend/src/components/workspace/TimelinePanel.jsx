import { useMemo } from "react";
import { Repeat } from "lucide-react";
import DeadlineList from "../DeadlineList.jsx";
import { Empty, Panel, SourceText, StatusChip, ws } from "./common.jsx";
import { EVIDENCE, TIMELINE, daysUntil, timelineStatus } from "../../labels.js";

const ORDER = ["overdue", "due_soon", "upcoming", "needs_verification"];

function formatDate(iso, language) {
  const parsed = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(language === "ml" ? "ml-IN" : undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function countdown(item, language) {
  const days = daysUntil(item.date_iso);
  if (days == null) return null;
  if (days < 0) return `${-days} ${language === "ml" ? "ദിവസം മുൻപ്" : "days ago"}`;
  if (days === 0) return language === "ml" ? "ഇന്ന്" : "today";
  return `${language === "ml" ? "" : "in "}${days}${language === "ml" ? " ദിവസത്തിൽ" : " days"}`;
}

function Item({ item, language }) {
  return (
    <li className="grid gap-1 py-3.5 first:pt-3 last:pb-3 sm:grid-cols-[8.5rem_minmax(0,1fr)] sm:gap-5">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <p className="text-[0.82rem] font-semibold tabular-nums">
          {item.date_iso ? formatDate(item.date_iso, language) : item.date_text}
        </p>
        <p className="text-[0.7rem] text-ink-faint">
          {timelineStatus(item) !== "needs_verification" && countdown(item, language)}
        </p>
      </div>

      <div className="min-w-0">
        <p className="text-[0.85rem] leading-relaxed text-ink">{item.description}</p>
        <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.7rem] text-ink-faint">
          {item.evidence_status === "calculated" && (
            <StatusChip map={EVIDENCE} status="calculated" language={language} />
          )}
          {item.recurrence && (
            <span className="inline-flex items-center gap-1 text-warn">
              <Repeat size={11} /> {ws(language, "recurring")}: {item.recurrence}
            </span>
          )}
          {item.page != null && (
            <span className="tabular-nums">
              {ws(language, "page")} {item.page}
            </span>
          )}
        </p>
        {item.evidence_status === "calculated" && (
          <p className="mt-1 text-[0.7rem] leading-relaxed text-ink-faint">
            {ws(language, "calculatedNote")}
          </p>
        )}
        <SourceText className="mt-2" text={item.source_text} language={language} />
      </div>
    </li>
  );
}

export default function TimelinePanel({ deadlines, filename, language }) {
  const groups = useMemo(() => {
    const buckets = Object.fromEntries(ORDER.map((key) => [key, []]));
    (deadlines ?? []).forEach((item) => {
      buckets[timelineStatus(item)].push(item);
    });
    ORDER.forEach((key) =>
      buckets[key].sort((a, b) => (a.date_iso ?? "").localeCompare(b.date_iso ?? "")),
    );
    return buckets;
  }, [deadlines]);

  if (!deadlines?.length) {
    return (
      <Panel title={ws(language, "timeline")}>
        <Empty>{ws(language, "noDates")}</Empty>
      </Panel>
    );
  }

  return (
    <div className="space-y-4">
      <Panel title={ws(language, "timeline")}>
        <p className="panel-note">{ws(language, "timelineNote")}</p>
        <div className="mt-5 space-y-6">
          {ORDER.filter((key) => groups[key].length > 0).map((key) => (
            <div key={key}>
              <div className="flex items-center gap-2.5 border-b border-line pb-2">
                <StatusChip map={TIMELINE} status={key} language={language} />
                <span className="text-[0.72rem] tabular-nums text-ink-faint">
                  {groups[key].length}
                </span>
              </div>
              <ul className="divide-y divide-line">
                {groups[key].map((item) => (
                  <Item key={item.id} item={item} language={language} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Panel>
      <DeadlineList deadlines={deadlines} filename={filename} language={language} />
    </div>
  );
}
