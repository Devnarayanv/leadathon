import { useState } from "react";
import { HelpCircle, Quote } from "lucide-react";
import { CONFIDENCE_LABELS, t } from "../i18n.js";

function FactCard({ fact, language }) {
  const [showSource, setShowSource] = useState(false);
  return (
    <div className="rounded-lg border border-line bg-surface p-3.5">
      <div className="flex items-start justify-between gap-2">
        <p className="label">{fact.label}</p>
        {fact.uncertain && (
          <span className="chip bg-warn-soft text-warn" title="Read but ambiguous">
            <HelpCircle size={12} />
            uncertain
          </span>
        )}
      </div>
      <p className="mt-1 text-sm leading-snug font-semibold break-words">{fact.value}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.7rem] text-ink-soft">
        {fact.page != null && (
          <span>
            {t(language, "page")} {fact.page}
          </span>
        )}
        <span>&middot;</span>
        <span>{CONFIDENCE_LABELS[language]?.[fact.confidence] ?? fact.confidence}</span>
        {fact.source_text && (
          <button
            type="button"
            onClick={() => setShowSource((value) => !value)}
            className="ml-auto inline-flex items-center gap-1 text-brand hover:underline"
          >
            <Quote size={11} />
            {showSource ? t(language, "collapse") : "source"}
          </button>
        )}
      </div>
      {showSource && fact.source_text && (
        <p className="evidence mt-2">{fact.source_text}</p>
      )}
    </div>
  );
}

export default function KeyFacts({ facts, language }) {
  if (!facts?.length) {
    return (
      <section className="card p-5 sm:p-6">
        <h2 className="text-sm font-semibold">{t(language, "keyInfo")}</h2>
        <p className="mt-2 text-sm text-ink-soft">{t(language, "noFacts")}</p>
      </section>
    );
  }

  return (
    <section className="card p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">{t(language, "keyInfo")}</h2>
        <p className="text-xs text-ink-soft">
          Read straight from the text by rules. Nothing here is generated.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {facts.map((fact) => (
          <FactCard key={fact.key} fact={fact} language={language} />
        ))}
      </div>
    </section>
  );
}
