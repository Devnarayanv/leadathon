import { useState } from "react";
import { Check } from "lucide-react";
import RiskCard from "../RiskCard.jsx";
import { Empty, Panel, SourceText, StatusChip, ws } from "./common.jsx";
import { EVIDENCE, FINDING_CATEGORY, SEVERITY, labelOf } from "../../labels.js";

function FindingRow({ finding, language }) {
  return (
    <li className="py-4 first:pt-3.5 last:pb-3.5">
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        <StatusChip map={SEVERITY} status={finding.severity} language={language} />
        <span className="eyebrow">
          {labelOf(FINDING_CATEGORY, finding.category, language)}
        </span>
        <span className="ml-auto text-[0.7rem] text-ink-faint">
          {labelOf(EVIDENCE, finding.evidence_status, language)}
        </span>
      </div>

      <p className="mt-1.5 text-[0.88rem] leading-relaxed font-medium">{finding.title}</p>
      {finding.explanation && (
        <p className="mt-1 text-[0.82rem] leading-relaxed text-ink-soft">
          {finding.explanation}
        </p>
      )}
      {finding.why_it_matters && (
        <p className="mt-1 text-[0.82rem] leading-relaxed text-ink-soft">
          {finding.why_it_matters}
        </p>
      )}
      {finding.suggested_action && (
        <p className="mt-2 border-l-2 border-line-strong pl-2.5 text-[0.82rem] leading-relaxed text-ink">
          {finding.suggested_action}
        </p>
      )}
      <SourceText
        className="mt-2.5"
        text={finding.original_text}
        page={finding.page}
        language={language}
      />
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
              className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border transition-colors ${
                checked ? "border-ink bg-ink text-on-ink" : "border-line-strong bg-surface hover:border-ink-soft"
              }`}
            >
              {checked && <Check size={11} strokeWidth={3} />}
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                <p className={`text-[0.85rem] font-medium ${checked ? "text-ink-faint line-through" : ""}`}>
                  {action.title}
                </p>
                <span className="text-[0.7rem] text-ink-faint">
                  {labelOf(SEVERITY, action.priority, language)}
                  {action.page != null && ` · ${ws(language, "page")} ${action.page}`}
                </span>
              </div>
              {action.detail && (
                <p className="mt-0.5 text-[0.8rem] leading-relaxed text-ink-soft">
                  {action.detail}
                </p>
              )}
              {action.due_date_text && (
                <p className="mt-0.5 text-[0.7rem] text-ink-faint">
                  {ws(language, "dueOn")}: {action.due_date_text}
                </p>
              )}
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
              <FindingRow key={finding.id} finding={finding} language={language} />
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
