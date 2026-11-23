import { useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  ClipboardCheck,
  Database,
  Flag,
  LayoutDashboard,
  MessageSquareText,
  RefreshCw,
  ScanLine,
  Sigma,
} from "lucide-react";
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

// Workspace sections. One document, several lenses. Tab state is local: a
// refresh returns to Overview, which is the honest default.
function tabsFor(result) {
  return [
    { id: "overview", icon: LayoutDashboard },
    { id: "data", icon: Database },
    { id: "verify", icon: Sigma },
    { id: "timeline", icon: CalendarClock, count: result.deadlines?.length },
    { id: "findings", icon: Flag, count: result.findings?.length },
    { id: "tender", icon: ClipboardCheck, count: result.requirements?.length },
    { id: "ask", icon: MessageSquareText },
  ];
}

function TabButton({ item, active, onSelect, language, compact }) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={() => onSelect(item.id)}
      className={`flex items-center gap-2.5 whitespace-nowrap transition-colors ${
        compact
          ? `rounded-full px-3.5 py-2 text-xs font-medium ${
              active ? "bg-ink text-on-ink" : "bg-surface text-ink-soft hover:text-ink"
            }`
          : `w-full rounded-xl px-3 py-2.5 text-left text-sm ${
              active
                ? "bg-surface font-semibold text-ink"
                : "text-ink-soft hover:bg-surface/60 hover:text-ink"
            }`
      }`}
    >
      <Icon size={compact ? 14 : 16} className={active && !compact ? "text-brand" : ""} />
      <span className={compact ? "" : "flex-1"}>{ws(language, item.id)}</span>
      {item.count > 0 && (
        <span
          className={`min-w-5 rounded-full px-1.5 text-center text-[0.7rem] tabular-nums ${
            active
              ? compact
                ? "bg-on-ink/20"
                : "bg-brand-soft text-brand-ink"
              : "bg-sunken text-ink-faint"
          }`}
        >
          {item.count}
        </span>
      )}
    </button>
  );
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
  const uncertain = !result.classification.certain;

  const select = (id) => {
    setTab(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-8 sm:py-10">
      <div className="grid gap-8 lg:grid-cols-[16.5rem_minmax(0,1fr)] lg:gap-10">
        {/* Sidebar: section navigation and explanation settings. */}
        <aside className="hidden lg:block">
          <div className="sticky top-24 space-y-5">
            <nav role="tablist" aria-label="Workspace" className="space-y-0.5">
              {tabs.map((item) => (
                <TabButton
                  key={item.id}
                  item={item}
                  active={tab === item.id}
                  onSelect={select}
                  language={language}
                />
              ))}
            </nav>

            <div className="card space-y-4 p-4">
              <LanguageSelector
                language={language}
                onChange={onLanguageChange}
                busy={languageBusy}
                modelName={result.ollama?.model}
                malayalamModel={malayalamModel}
                speech={speech}
              />
              <VoicePicker speech={speech} language={language} />
              {!aiReady && (
                <button
                  type="button"
                  onClick={onRetryAi}
                  disabled={retryBusy}
                  className="btn-secondary w-full text-xs"
                >
                  <RefreshCw size={13} className={retryBusy ? "animate-spin" : ""} />
                  {t(language, "retryAi")}
                </button>
              )}
            </div>
          </div>
        </aside>

        <main className="min-w-0">
          <header className="rise">
            <p className="flex flex-wrap items-center gap-2 text-sm text-ink-soft">
              <span
                className={`chip ${uncertain ? "bg-warn-soft text-warn" : "bg-brand-soft text-brand-ink"}`}
              >
                {result.classification.label}
              </span>
              {result.ocr_used && (
                <span className="chip bg-note-soft text-note">
                  <ScanLine size={12} />
                  OCR
                </span>
              )}
            </p>
            <h1
              className="mt-3 truncate text-2xl font-semibold tracking-[-0.03em] sm:text-[2.1rem] sm:leading-tight"
              title={result.filename}
            >
              {result.filename}
            </h1>
            <p className="mt-1.5 text-sm text-ink-faint tabular-nums">
              {result.page_count} {t(language, "pages")} ·{" "}
              {(result.file_size_bytes / 1024).toFixed(0)} KB · analysed in{" "}
              {(result.duration_ms / 1000).toFixed(1)}s
            </p>
          </header>

          {/* Mobile and tablet: settings and horizontal section tabs. */}
          <div className="mt-5 space-y-3 lg:hidden">
            <div className="flex flex-wrap items-center gap-2">
              <LanguageSelector
                language={language}
                onChange={onLanguageChange}
                busy={languageBusy}
                modelName={result.ollama?.model}
                malayalamModel={malayalamModel}
                speech={speech}
              />
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
          <nav
            role="tablist"
            aria-label="Workspace"
            className="sticky top-16 z-10 -mx-4 mt-4 overflow-x-auto bg-canvas px-4 py-2.5 sm:-mx-8 sm:px-8 lg:hidden"
          >
            <div className="flex gap-1.5">
              {tabs.map((item) => (
                <TabButton
                  key={item.id}
                  item={item}
                  active={tab === item.id}
                  onSelect={select}
                  language={language}
                  compact
                />
              ))}
            </div>
          </nav>

          {result.warnings?.length > 0 && (
            <section className="mt-6 rounded-[var(--radius-card)] bg-warn-soft px-5 py-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-warn">
                <AlertTriangle size={15} />
                {t(language, "warnings")}
              </p>
              <ul className="mt-2 space-y-1">
                {result.warnings.map((warning) => (
                  <li
                    key={warning}
                    className="text-[0.82rem] leading-relaxed whitespace-pre-wrap text-ink-soft"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div role="tabpanel" key={tab} className="rise mt-6">
            {tab === "overview" && (
              <div className="space-y-5">
                <RiskSummary
                  clauses={result.clauses}
                  counts={result.attention_counts}
                  language={language}
                  onJump={() => select("findings")}
                />
                <DocumentOverview result={result} language={language} speech={speech} />
              </div>
            )}

            {tab === "data" && (
              <div className="space-y-5">
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

            {tab === "ask" && (
              <AskDocument result={result} language={language} speech={speech} />
            )}
          </div>

          <p className="mt-10 text-xs leading-relaxed text-ink-faint">
            Doc Decode flags wording that deserves attention and explains it in simpler
            words. It does not decide whether anything is legal, valid or fair, and it
            can miss clauses. Check the original document and take professional advice
            before you sign, pay or reply.
          </p>
        </main>
      </div>
    </div>
  );
}
