import { AlertTriangle, Info, RefreshCw } from "lucide-react";
import DocumentOverview from "../components/DocumentOverview.jsx";
import KeyFacts from "../components/KeyFacts.jsx";
import RiskSummary from "../components/RiskSummary.jsx";
import RiskCard from "../components/RiskCard.jsx";
import DeadlineList from "../components/DeadlineList.jsx";
import AskDocument from "../components/AskDocument.jsx";
import ExtractedTextViewer from "../components/ExtractedTextViewer.jsx";
import LanguageSelector from "../components/LanguageSelector.jsx";
import { t } from "../i18n.js";

export default function Analysis({
  result,
  language,
  onLanguageChange,
  languageBusy,
  speech,
  onRetryAi,
  retryBusy,
}) {
  const jump = (level) => {
    const target = result.clauses.find((clause) => clause.attention_level === level);
    if (!target) return;
    document
      .getElementById(`clause-${target.id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const aiReady = result.ollama?.reachable && result.ollama?.model_available;

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <LanguageSelector
          language={language}
          onChange={onLanguageChange}
          busy={languageBusy}
        />
        {!aiReady && (
          <button
            type="button"
            onClick={onRetryAi}
            disabled={retryBusy}
            className="btn-secondary text-xs"
          >
            <RefreshCw size={14} className={retryBusy ? "animate-spin" : ""} />
            {t(language, "retryAi")}
          </button>
        )}
      </div>

      <DocumentOverview result={result} language={language} speech={speech} />

      {result.warnings?.length > 0 && (
        <section className="rounded-[var(--radius-card)] border border-warn/30 bg-warn-soft p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-warn">
            <AlertTriangle size={16} />
            {t(language, "warnings")}
          </p>
          <ul className="mt-2 space-y-1.5">
            {result.warnings.map((warning) => (
              <li
                key={warning}
                className="text-xs leading-relaxed whitespace-pre-wrap text-warn"
              >
                {warning}
              </li>
            ))}
          </ul>
        </section>
      )}

      <KeyFacts facts={result.facts} language={language} />

      <RiskSummary
        clauses={result.clauses}
        counts={result.attention_counts}
        language={language}
        onJump={jump}
      />

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold">{t(language, "clauseAnalysis")}</h2>
          <p className="text-xs text-ink-soft">
            Original wording is shown with every explanation.
          </p>
        </div>

        {result.clauses.length === 0 ? (
          <p className="card p-5 text-sm text-ink-soft">{t(language, "noClauses")}</p>
        ) : (
          result.clauses.map((clause, index) => (
            <RiskCard
              key={clause.id}
              clause={clause}
              language={language}
              speech={speech}
              defaultOpen={index === 0}
            />
          ))
        )}
      </section>

      <DeadlineList
        deadlines={result.deadlines}
        filename={result.filename}
        language={language}
      />

      <AskDocument result={result} language={language} speech={speech} />

      <ExtractedTextViewer pages={result.pages} language={language} />

      <p className="flex items-start gap-2 rounded-[var(--radius-card)] border border-line bg-surface p-4 text-xs leading-relaxed text-ink-soft">
        <Info size={14} className="mt-0.5 shrink-0" />
        <span>
          PlainSpeak flags wording that deserves attention and explains it in simpler
          words. It does not decide whether anything is legal, valid or fair, and it
          can miss clauses. Check the original document and take professional advice
          before you sign, pay or reply.
        </span>
      </p>
    </div>
  );
}
