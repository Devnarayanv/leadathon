import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import DocumentOverview from "../components/DocumentOverview.jsx";
import KeyFacts from "../components/KeyFacts.jsx";
import RiskSummary from "../components/RiskSummary.jsx";
import RiskCard from "../components/RiskCard.jsx";
import DeadlineList from "../components/DeadlineList.jsx";
import AskDocument from "../components/AskDocument.jsx";
import ExtractedTextViewer from "../components/ExtractedTextViewer.jsx";
import LanguageSelector from "../components/LanguageSelector.jsx";
import { VoicePicker } from "../components/AudioControls.jsx";
import { t } from "../i18n.js";

const SECTIONS = [
  { id: "facts", label: "Information" },
  { id: "clauses", label: "Clauses" },
  { id: "deadlines", label: "Deadlines" },
  { id: "ask", label: "Ask" },
  { id: "text", label: "Text" },
];

// Highlights whichever section is currently in view, so a long page still
// tells you where you are without a heavy sidebar.
function useActiveSection() {
  const [active, setActive] = useState(SECTIONS[0].id);
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-64px 0px -60% 0px", threshold: 0 },
    );
    SECTIONS.forEach(({ id }) => {
      const node = document.getElementById(id);
      if (node) observer.observe(node);
    });
    return () => observer.disconnect();
  }, []);
  return active;
}

export default function Analysis({
  result,
  language,
  onLanguageChange,
  languageBusy,
  speech,
  onRetryAi,
  retryBusy,
  malayalamModel,
}) {
  const active = useActiveSection();

  const jump = (level) => {
    const target = result.clauses.find((clause) => clause.attention_level === level);
    if (!target) return;
    document
      .getElementById(`clause-${target.id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const aiReady = result.ollama?.reachable && result.ollama?.model_available;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <LanguageSelector
          language={language}
          onChange={onLanguageChange}
          busy={languageBusy}
          modelName={result.ollama?.model}
          malayalamModel={malayalamModel}
          speech={speech}
        />
        <div className="flex items-center gap-2">
          <VoicePicker speech={speech} language={language} />
          {!aiReady && (
            <button
              type="button"
              onClick={onRetryAi}
              disabled={retryBusy}
              className="btn-secondary text-xs"
            >
              <RefreshCw size={13} className={retryBusy ? "animate-spin" : ""} />
              {t(language, "retryAi")}
            </button>
          )}
        </div>
      </div>

      <DocumentOverview result={result} language={language} speech={speech} />

      {result.warnings?.length > 0 && (
        <section className="mt-4 rule-left border-warn/50">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-warn">
            <AlertTriangle size={13} />
            {t(language, "warnings")}
          </p>
          <ul className="mt-1.5 space-y-1">
            {result.warnings.map((warning) => (
              <li
                key={warning}
                className="text-xs leading-relaxed whitespace-pre-wrap text-ink-soft"
              >
                {warning}
              </li>
            ))}
          </ul>
        </section>
      )}

      <nav className="sticky top-14 z-10 -mx-4 mt-5 overflow-x-auto border-b border-line bg-canvas/90 px-4 backdrop-blur sm:-mx-6 sm:px-6">
        <ul className="flex gap-1">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                className={`inline-block border-b-2 px-2.5 py-2.5 text-xs transition-colors ${
                  active === section.id
                    ? "border-ink text-ink"
                    : "border-transparent text-ink-faint hover:text-ink-soft"
                }`}
              >
                {section.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-5 space-y-4">
        <div id="facts" className="scroll-mt-28">
          <KeyFacts facts={result.facts} language={language} />
        </div>

        <div id="clauses" className="scroll-mt-28 space-y-4">
          <RiskSummary
            clauses={result.clauses}
            counts={result.attention_counts}
            language={language}
            onJump={jump}
          />

          {result.clauses.length === 0 ? (
            <p className="card p-5 text-sm text-ink-soft">
              {t(language, "noClauses")}
            </p>
          ) : (
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

        <div className="scroll-mt-28">
          <DeadlineList
            deadlines={result.deadlines}
            filename={result.filename}
            language={language}
          />
        </div>

        <AskDocument result={result} language={language} speech={speech} />

        <div id="text" className="scroll-mt-28">
          <ExtractedTextViewer pages={result.pages} language={language} />
        </div>
      </div>

      <p className="mt-6 border-t border-line pt-5 text-xs leading-relaxed text-ink-faint">
        PlainSpeak flags wording that deserves attention and explains it in simpler
        words. It does not decide whether anything is legal, valid or fair, and it
        can miss clauses. Check the original document and take professional advice
        before you sign, pay or reply.
      </p>
    </div>
  );
}
