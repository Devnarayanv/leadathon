import { useState } from "react";
import { t } from "../i18n.js";

function FactRow({ fact, language }) {
  const [showSource, setShowSource] = useState(false);
  return (
    <div className="py-3 first:pt-0 last:pb-0">
      <div className="flex items-baseline justify-between gap-3">
        <p className="label">{fact.label}</p>
        <div className="flex items-center gap-2 text-[0.7rem] text-ink-faint">
          {fact.page != null && (
            <span>
              {t(language, "page")} {fact.page}
            </span>
          )}
          {fact.source_text && (
            <button
              type="button"
              onClick={() => setShowSource((value) => !value)}
              className="hover:text-ink"
            >
              {showSource ? "hide" : "source"}
            </button>
          )}
        </div>
      </div>
      <p className="mt-1 text-sm leading-snug font-medium break-words">
        {fact.value}
        {fact.uncertain && (
          <span className="ml-2 align-middle text-[0.7rem] font-normal text-warn">
            uncertain
          </span>
        )}
      </p>
      {showSource && fact.source_text && (
        <p className="evidence mt-2">{fact.source_text}</p>
      )}
    </div>
  );
}

export default function KeyFacts({ facts, language }) {
  if (!facts?.length) {
    return (
      <section className="card p-5">
        <h2 className="text-sm font-semibold">{t(language, "keyInfo")}</h2>
        <p className="mt-1.5 text-sm text-ink-soft">{t(language, "noFacts")}</p>
      </section>
    );
  }

  return (
    <section className="card p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">{t(language, "keyInfo")}</h2>
        <p className="text-xs text-ink-faint">Read from the text by rules</p>
      </div>
      <div className="grid gap-x-8 sm:grid-cols-2 lg:grid-cols-3">
        {facts.map((fact) => (
          <div key={fact.key} className="border-b border-line last:border-b-0">
            <FactRow fact={fact} language={language} />
          </div>
        ))}
      </div>
    </section>
  );
}
