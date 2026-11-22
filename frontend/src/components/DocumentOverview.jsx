import { AlertTriangle, CheckCircle2, FileText, Info, ScanLine } from "lucide-react";
import { t } from "../i18n.js";
import AudioControls from "./AudioControls.jsx";

function Stat({ label, value, title }) {
  return (
    <div className="min-w-0">
      <p className="label">{label}</p>
      <p className="mt-0.5 truncate text-sm font-medium" title={title ?? value}>
        {value}
      </p>
    </div>
  );
}

export default function DocumentOverview({ result, language, speech }) {
  const { classification } = result;
  const uncertain = !classification.certain;

  return (
    <section className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand-ink">
          <FileText size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold sm:text-lg" title={result.filename}>
            {result.filename}
          </h1>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-soft">
            <span className={uncertain ? "text-warn" : ""}>{classification.label}</span>
            <span>&middot;</span>
            <span>
              {result.page_count} {t(language, "pages")}
            </span>
            <span>&middot;</span>
            <span>{(result.file_size_bytes / 1024).toFixed(0)} KB</span>
            <span>&middot;</span>
            <span>{(result.duration_ms / 1000).toFixed(1)}s</span>
          </p>
        </div>
        <span className="chip bg-good-soft text-good">
          <CheckCircle2 size={13} />
          {t(language, "analysed")}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 sm:grid-cols-4">
        <Stat label={t(language, "docType")} value={classification.label} />
        <Stat label={t(language, "pages")} value={String(result.page_count)} />
        <Stat
          label="Text read by"
          value={result.ocr_used ? "PDF text + OCR" : "PDF text layer"}
        />
        <Stat
          label={t(language, "source")}
          value={
            result.summary_source === "llm"
              ? t(language, "bySource").llm
              : t(language, "bySource").rules
          }
        />
      </div>

      {result.summary && (
        <div className="mt-5 rounded-lg bg-canvas p-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h2 className="label">{t(language, "summary")}</h2>
            <AudioControls
              id="summary"
              text={result.summary}
              language={language}
              speech={speech}
              label={t(language, "play")}
              stopLabel={t(language, "stop")}
              compact
            />
          </div>
          <p className={`prose-plain ${language === "ml" ? "lang-ml" : ""}`}>
            {result.summary}
          </p>
          {result.summary_source === "rules" && (
            <p className="mt-2 flex items-start gap-1.5 text-xs text-ink-soft">
              <Info size={13} className="mt-0.5 shrink-0" />
              Written from rule output, not from the AI model.
            </p>
          )}
        </div>
      )}

      {uncertain && (
        <p className="mt-4 flex items-start gap-2 rounded-lg bg-warn-soft px-3.5 py-3 text-sm text-warn">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>
            Document type uncertain. The facts below are still read directly from the
            text, but the field names were chosen for the closest matching type.
          </span>
        </p>
      )}

      {result.ocr_used && (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-note-soft px-3.5 py-3 text-xs text-note">
          <ScanLine size={14} className="mt-0.5 shrink-0" />
          <span>
            Some pages had no selectable text, so OCR was used. OCR can misread
            characters. Check any amount or date against the original.
          </span>
        </p>
      )}
    </section>
  );
}
