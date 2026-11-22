import { AlertTriangle, FileText, Info, ScanLine } from "lucide-react";
import { t } from "../i18n.js";
import AudioControls from "./AudioControls.jsx";

function Stat({ label, value, title }) {
  return (
    <div className="min-w-0">
      <p className="label">{label}</p>
      <p className="mt-1 truncate text-sm" title={title ?? value}>
        {value}
      </p>
    </div>
  );
}

export default function DocumentOverview({ result, language, speech }) {
  const { classification } = result;
  const uncertain = !classification.certain;

  return (
    <section className="card p-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-ink-faint">
          <FileText size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold" title={result.filename}>
            {result.filename}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-ink-faint">
            <span className={uncertain ? "text-warn" : "text-ink-soft"}>
              {classification.label}
            </span>
            <span>·</span>
            <span>
              {result.page_count} {t(language, "pages")}
            </span>
            <span>·</span>
            <span>{(result.file_size_bytes / 1024).toFixed(0)} KB</span>
            <span>·</span>
            <span>{(result.duration_ms / 1000).toFixed(1)}s</span>
          </p>
        </div>
      </div>

      {result.summary && (
        <div className="mt-4">
          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
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
          <p
            className={`prose-plain rule-left border-line-strong ${
              language === "ml" ? "lang-ml" : ""
            }`}
          >
            {result.summary}
          </p>
          {result.summary_source === "rules" && (
            <p className="mt-1.5 text-[0.7rem] text-ink-faint">
              Written from rule output, not from the AI model.
            </p>
          )}
        </div>
      )}

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

      {uncertain && (
        <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-warn">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>
            Document type uncertain. The facts below are still read directly from
            the text, but the field names come from the closest matching type.
          </span>
        </p>
      )}

      {result.ocr_used && (
        <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-ink-soft">
          <ScanLine size={14} className="mt-0.5 shrink-0" />
          <span>
            Some pages had no selectable text, so OCR was used. OCR can misread
            characters &mdash; check any amount or date against the original.
          </span>
        </p>
      )}
    </section>
  );
}
