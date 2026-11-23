import { AlertTriangle, ScanLine } from "lucide-react";
import { t } from "../i18n.js";
import AudioControls from "./AudioControls.jsx";

function Stat({ label, value, title }) {
  return (
    <div className="min-w-0 rounded-xl bg-sunken px-4 py-3">
      <p className="label">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold" title={title ?? value}>
        {value}
      </p>
    </div>
  );
}

export default function DocumentOverview({ result, language, speech }) {
  const { classification } = result;
  const uncertain = !classification.certain;

  return (
    <section className="card p-5 sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold tracking-[-0.02em]">{t(language, "summary")}</h2>
        {result.summary && (
          <AudioControls
            id="summary"
            text={result.summary}
            language={language}
            speech={speech}
            label={t(language, "play")}
            stopLabel={t(language, "stop")}
            compact
          />
        )}
      </div>

      {result.summary ? (
        <>
          <p
            className={`mt-3 max-w-3xl text-[1.06rem] leading-[1.7] text-ink ${
              language === "ml" ? "lang-ml" : ""
            }`}
          >
            {result.summary}
          </p>
          {result.summary_source === "rules" && (
            <p className="mt-2 text-xs text-ink-faint">
              Written from rule output, not from the AI model.
            </p>
          )}
        </>
      ) : (
        <p className="mt-3 text-sm text-ink-soft">No summary was produced for this document.</p>
      )}

      <div className="mt-6 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
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
        <p className="mt-4 flex items-start gap-2.5 rounded-xl bg-warn-soft px-4 py-3 text-[0.82rem] leading-relaxed text-warn">
          <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          <span>
            Document type uncertain. The facts are still read directly from the text,
            but the field names come from the closest matching type.
          </span>
        </p>
      )}

      {result.ocr_used && (
        <p className="mt-3 flex items-start gap-2.5 rounded-xl bg-note-soft px-4 py-3 text-[0.82rem] leading-relaxed text-note">
          <ScanLine size={15} className="mt-0.5 shrink-0" />
          <span>
            Some pages had no selectable text, so OCR was used. OCR can misread
            characters &mdash; check any amount or date against the original.
          </span>
        </p>
      )}
    </section>
  );
}
