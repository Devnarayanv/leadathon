import { useMemo } from "react";
import { Repeat } from "lucide-react";
import DeadlineList from "../DeadlineList.jsx";
import { Empty, Panel, StatusChip, ws } from "./common.jsx";
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

function Item({ item, status, language }) {
  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium tabular-nums">
          {item.date_iso ? formatDate(item.date_iso, language) : item.date_text}
        </p>
        <StatusChip map={TIMELINE} status={status} language={language} />
        {status !== "needs_verification" && countdown(item, language) && (
          <span className="text-xs text-ink-soft">{countdown(item, language)}</span>
        )}
        {item.evidence_status === "calculated" && (
          <StatusChip map={EVIDENCE} status="calculated" language={language} />
        )}
      </div>
      <p className="mt-1 text-xs leading-relaxed text-ink-soft">{item.description}</p>
      {item.recurrence && (
        <p className="mt-1 flex items-center gap-1 text-xs text-warn">
          <Repeat size={12} />
          {ws(language, "recurring")}: {item.recurrence}
        </p>
      )}
      {item.evidence_status === "calculated" && (
        <p className="mt-1 text-xs text-warn">{ws(language, "calculatedNote")}</p>
      )}
      <p className="evidence mt-2">
        {item.page != null && `${ws(language, "page")} ${item.page} · `}
        {item.source_text}
      </p>
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
        <p className="text-xs leading-relaxed text-ink-soft">{ws(language, "timelineNote")}</p>
        <div className="mt-4 space-y-5">
          {ORDER.filter((key) => groups[key].length > 0).map((key) => (
            <div key={key}>
              <p className="mb-2">
                <StatusChip map={TIMELINE} status={key} language={language} />
              </p>
              <ul className="divide-y divide-line border-l-2 border-line pl-4">
                {groups[key].map((item) => (
                  <Item key={item.id} item={item} status={key} language={language} />
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
