import { useState } from "react";
import { ChevronDown, Check } from "lucide-react";
import RiskCard from "../RiskCard.jsx";
import { Empty, Panel, StatusChip, ws } from "./common.jsx";
import { EVIDENCE, FINDING_CATEGORY, SEVERITY, labelOf } from "../../labels.js";

// Evidence drawer: the original sentence, its page, and how the claim was
// reached. Opened per finding; nothing is shown that the document did not say.
function Evidence({ finding, language }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex items-center gap-1 text-xs font-medium text-ink-soft hover:text-ink"
      >
        <ChevronDown size={13} className={`transition-transform ${open ? "rotate-180" : ""}`} />
        {ws(language, "evidence")}
      </button>
      {open && (
        <div className="mt-2 space-y-2 rounded-lg bg-canvas p-3">
          <p className="label">{ws(language, "original")}</p>
          <p className="evidence">
            {finding.page != null && `${ws(language, "page")} ${finding.page} · `}
            {finding.original_text || "—"}
          </p>
          <p className="text-xs text-ink-faint">
            {labelOf(EVIDENCE, finding.evidence_status, language)}
            {finding.ref && ` · ${finding.ref}`}
          </p>
        </div>
      )}
    </div>
  );
}

function FindingCard({ finding, language }) {
  return (
    <li className="py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <StatusChip map={SEVERITY} status={finding.severity} language={language} />
        <span className="chip bg-canvas text-ink-soft">
          {labelOf(FINDING_CATEGORY, finding.category, language)}
        </span>
        <StatusChip map={EVIDENCE} status={finding.evidence_status} language={language} />
      </div>
      <p className="mt-2 text-sm font-medium">{finding.title}</p>
      {finding.explanation && (
        <p className="mt-1 text-xs leading-relaxed text-ink-soft">{finding.explanation}</p>
      )}
      {finding.why_it_matters && (
        <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">{finding.why_it_matters}</p>
      )}
      {finding.suggested_action && (
        <p className="mt-1.5 text-xs leading-relaxed text-ink">{finding.suggested_action}</p>
      )}
      <Evidence finding={finding} language={language} />
    </li>
  );
}

function ActionList({ actions, language }) {
  // Done-ticks live only in this view. They are not saved or sent anywhere.
  const [done, setDone] = useState({});
  if (!actions.length) return <Empty>{ws(language, "noActions")}</Empty>;
  return (
    <ul className="divide-y divide-line">
      {actions.map((action) => {
        const checked = Boolean(done[action.id]);
        return (
          <li key={action.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
            <button
              type="button"
              role="checkbox"
              aria-checked={checked}
              aria-label={`${ws(language, "markDone")}: ${action.title}`}
              onClick={() => setDone((current) => ({ ...current, [action.id]: !checked }))}
              className={`mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded border transition-colors ${
                checked ? "border-ink bg-ink text-white" : "border-line-strong bg-surface"
              }`}
            >
              {checked && <Check size={12} strokeWidth={3} />}
            </button>
            <div className="min-w-0 flex-1">
              <p className={`text-sm font-medium ${checked ? "text-ink-faint line-through" : ""}`}>
                {action.title}
              </p>
              {action.detail && (
                <p className="mt-0.5 text-xs leading-relaxed text-ink-soft">{action.detail}</p>
              )}
              <p className="mt-1 flex flex-wrap gap-x-2 text-[0.7rem] text-ink-faint">
                <span>{ws(language, "priority")}: {labelOf(SEVERITY, action.priority, language)}</span>
                {action.due_date_text && (
                  <span>
                    · {ws(language, "dueOn")}: {action.due_date_text}
                  </span>
                )}
                {action.page != null && (
                  <span>
                    · {ws(language, "page")} {action.page}
                  </span>
                )}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default function FindingsPanel({ result, language, speech }) {
  const findings = result.findings ?? [];
  return (
    <div className="space-y-4">
      <Panel title={ws(language, "actionCenter")}>
        <ActionList actions={result.actions ?? []} language={language} />
      </Panel>

      <Panel title={ws(language, "findings")}>
        {findings.length === 0 ? (
          <Empty>{ws(language, "noFindings")}</Empty>
        ) : (
          <ul className="divide-y divide-line">
            {findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} language={language} />
            ))}
          </ul>
        )}
      </Panel>

      {result.clauses?.length > 0 && (
        <div className="space-y-3">
          {result.clauses.map((clause, index) => (
            <RiskCard
              key={clause.id}
              clause={clause}
              language={language}
              speech={speech}
              defaultOpen={index === 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}
