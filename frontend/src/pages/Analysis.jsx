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
import { docTypeLabel, t } from "../i18n.js";

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
  if (compact) {
    return (
      <button
        type="button"
        role="tab"
        aria-selected={active}
        onClick={() => onSelect(item.id)}
        className={`inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 px-0.5 pt-1 pb-2.5 text-[0.78rem] font-medium transition-colors ${
          active
            ? "border-ink text-ink"
            : "border-transparent text-ink-soft hover:text-ink"
        }`}
      >
        <Icon size={14} />
        {ws(language, item.id)}
        {item.count > 0 && (
          <span className="text-[0.7rem] tabular-nums text-ink-faint">{item.count}</span>
        )}
      </button>
    );
  }

  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={() => onSelect(item.id)}
      className={`flex w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left text-[0.85rem] transition-colors ${
        active
          ? "border-line bg-surface font-medium text-ink shadow-[0_1px_2px_rgb(16_18_21/0.04)]"
          : "border-transparent text-ink-soft hover:bg-surface/60 hover:text-ink"
      }`}
    >
      <Icon size={15} className={active ? "text-brand" : "text-ink-faint"} />
      <span className="flex-1">{ws(language, item.id)}</span>
      {item.count > 0 && (
        <span
          className={`text-[0.7rem] tabular-nums ${
            active ? "text-ink-soft" : "text-ink-faint"
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
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-8 sm:py-8">
      <div className="grid gap-8 lg:grid-cols-[16rem_minmax(0,1fr)] lg:gap-9">
        {/* Sidebar: section navigation and explanation settings. */}
        <aside className="hidden lg:block">
          <div className="sticky top-22 space-y-4">
            <p className="eyebrow px-3">{ws(language, "sections")}</p>
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
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`chip ${uncertain ? "bg-warn-soft text-warn" : "bg-brand-soft text-brand-ink"}`}
              >
                {docTypeLabel(
                  result.classification.doc_type,
                  result.classification.label,
                  language,
                )}
              </span>
              {result.ocr_used && (
                <span className="chip bg-note-soft text-note">
                  <ScanLine size={11} />
                  OCR
                </span>
              )}
            </div>
            <h1
              className="mt-3 text-[1.55rem] leading-tight font-semibold break-words tracking-[-0.03em] sm:text-[1.95rem]"
              title={result.filename}
            >
              {result.filename}
            </h1>
            <p className="mt-2 flex flex-wrap items-center gap-x-2 text-[0.78rem] tabular-nums text-ink-faint">
              <span>
                {result.page_count} {t(language, "pages")}
              </span>
              <span aria-hidden="true">·</span>
              <span>{(result.file_size_bytes / 1024).toFixed(0)} KB</span>
              <span aria-hidden="true">·</span>
              <span>
                {t(language, "analysedIn")} {(result.duration_ms / 1000).toFixed(1)}s
              </span>
            </p>
          </header>

          {/* Mobile and tablet: settings and horizontal section tabs. */}
          <div className="mt-5 lg:hidden">
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
            className="sticky top-14 z-10 -mx-4 mt-4 overflow-x-auto border-b border-line bg-canvas px-4 sm:-mx-8 sm:px-8 lg:hidden"
          >
            <div className="flex gap-5">
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
            <section className="mt-5 rounded-[var(--radius-card)] border border-warn/25 bg-warn-soft px-4 py-3">
              <p className="flex items-center gap-2 text-[0.82rem] font-medium text-warn">
                <AlertTriangle size={14} />
                {t(language, "warnings")}
              </p>
              <ul className="mt-1.5 space-y-1">
                {result.warnings.map((warning) => (
                  <li
                    key={warning}
                    className="text-[0.8rem] leading-relaxed whitespace-pre-wrap text-ink-soft"
                  >
                    {warning}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div role="tabpanel" key={tab} className="rise mt-5">
            {tab === "overview" && (
              <div className="space-y-4">
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

            {tab === "ask" && (
              <AskDocument result={result} language={language} speech={speech} />
            )}
          </div>

          <p className="mt-8 border-t border-line pt-4 text-[0.72rem] leading-relaxed text-ink-faint">
            {t(language, "footerNote")}
          </p>
        </main>
      </div>
    </div>
  );
}
