import { useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import DocumentOverview from "../components/DocumentOverview.jsx";
import KeyFacts from "../components/KeyFacts.jsx";
import RiskSummary from "../components/RiskSummary.jsx";
import AskDocument from "../components/AskDocument.jsx";
import ExtractedTextViewer from "../components/ExtractedTextViewer.jsx";
import LanguageSelector from "../components/LanguageSelector.jsx";
import { VoicePicker } from "../components/AudioControls.jsx";
import VerifyPanel from "../components/workspace/VerifyPanel.jsx";
import TimelinePanel from "../components/workspace/TimelinePanel.jsx";
import FindingsPanel from "../components/workspace/FindingsPanel.jsx";
import TenderPanel from "../components/workspace/TenderPanel.jsx";
import { ws } from "../components/workspace/common.jsx";
import { t } from "../i18n.js";

// Workspace tabs. One document, several lenses. Tab state is local: a refresh
// returns to Overview, which is the honest default.
function tabsFor(result) {
  return [
    { id: "overview", label: ws("en", "overview"), ml: ws("ml", "overview") },
    { id: "data", label: ws("en", "data"), ml: ws("ml", "data") },
    { id: "verify", label: ws("en", "verify"), ml: ws("ml", "verify") },
    {
      id: "timeline",
      label: ws("en", "timeline"),
      ml: ws("ml", "timeline"),
      count: result.deadlines?.length,
    },
    {
      id: "findings",
      label: ws("en", "findings"),
      ml: ws("ml", "findings"),
      count: result.findings?.length,
    },
    {
      id: "tender",
      label: ws("en", "tender"),
      ml: ws("ml", "tender"),
      count: result.requirements?.length,
    },
    { id: "ask", label: ws("en", "ask"), ml: ws("ml", "ask") },
  ];
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
  onReclassify,
  reclassifyBusy,
  onCompareFile,
  compareBusy,
  compareResult,
  compareError,
}) {
  const [tab, setTab] = useState("overview");
  const tabs = tabsFor(result);
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

      <header className="card flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <div className="min-w-0">
          <p className="label">{t(language, "docType")}</p>
          <p className="mt-0.5 truncate text-base font-semibold">{result.classification.label}</p>
        </div>
        <p className="min-w-0 truncate text-xs text-ink-soft">
          {result.filename} · {result.page_count} {t(language, "pages")}
        </p>
      </header>

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

      <nav
        role="tablist"
        aria-label="Workspace"
        className="sticky top-14 z-10 -mx-4 mt-5 overflow-x-auto border-b border-line bg-canvas/90 px-4 backdrop-blur sm:-mx-6 sm:px-6"
      >
        <ul className="flex gap-1">
          {tabs.map((item) => {
            const active = tab === item.id;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setTab(item.id)}
                  className={`flex items-center gap-1.5 border-b-2 px-2.5 py-2.5 text-xs whitespace-nowrap transition-colors ${
                    active
                      ? "border-ink text-ink"
                      : "border-transparent text-ink-faint hover:text-ink-soft"
                  }`}
                >
                  {language === "ml" ? item.ml : item.label}
                  {item.count > 0 && (
                    <span className="tabular-nums text-[0.65rem] text-ink-faint">{item.count}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div role="tabpanel" className="mt-5">
        {tab === "overview" && (
          <div className="space-y-4">
            <DocumentOverview result={result} language={language} speech={speech} />
            <RiskSummary
              clauses={result.clauses}
              counts={result.attention_counts}
              language={language}
              onJump={() => setTab("findings")}
            />
          </div>
        )}

        {tab === "data" && (
          <div className="space-y-4">
            <KeyFacts facts={result.facts} language={language} />
            <ExtractedTextViewer pages={result.pages} language={language} />
          </div>
        )}

        {tab === "verify" && (
          <VerifyPanel
            result={result}
            language={language}
            onReclassify={onReclassify}
            reclassifyBusy={reclassifyBusy}
            onCompareFile={onCompareFile}
            compareBusy={compareBusy}
            compareResult={compareResult}
            compareError={compareError}
          />
        )}

        {tab === "timeline" && (
          <TimelinePanel
            deadlines={result.deadlines}
            filename={result.filename}
            language={language}
          />
        )}

        {tab === "findings" && (
          <FindingsPanel result={result} language={language} speech={speech} />
        )}

        {tab === "tender" && (
          <TenderPanel requirements={result.requirements} language={language} />
        )}

        {tab === "ask" && <AskDocument result={result} language={language} speech={speech} />}
      </div>

      <p className="mt-8 border-t border-line pt-5 text-xs leading-relaxed text-ink-faint">
        Doc Decode flags wording that deserves attention and explains it in simpler
        words. It does not decide whether anything is legal, valid or fair, and it
        can miss clauses. Check the original document and take professional advice
        before you sign, pay or reply.
      </p>
    </div>
  );
}
