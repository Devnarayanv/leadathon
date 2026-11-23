import { useState } from "react";
import { t } from "../i18n.js";

function FactRow({ fact, language }) {
  const [showSource, setShowSource] = useState(false);
  return (
    <div className="border-t border-line py-3">
      <div className="flex items-baseline justify-between gap-3">
        <p className="label">{fact.label}</p>
        <div className="flex items-center gap-2 text-[0.7rem] text-ink-faint">
          {fact.page != null && (
            <span className="tabular-nums">
              {t(language, "page")} {fact.page}
            </span>
          )}
          {fact.source_text && (
            <button
              type="button"
              onClick={() => setShowSource((value) => !value)}
              className="rounded px-1 transition-colors hover:bg-sunken hover:text-ink"
            >
              {showSource ? "hide" : "source"}
            </button>
          )}
        </div>
      </div>
      <p className="mt-1 text-[0.88rem] leading-snug font-medium break-words">
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
      <section className="card p-5 sm:p-6">
        <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
          {t(language, "keyInfo")}
        </h2>
        <p className="mt-2 text-[0.85rem] text-ink-soft">{t(language, "noFacts")}</p>
      </section>
    );
  }

  return (
    <section className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
          {t(language, "keyInfo")}
        </h2>
        <p className="text-[0.72rem] text-ink-faint">Read from the text by rules</p>
      </div>
      <div className="mt-3 grid gap-x-8 sm:grid-cols-2 xl:grid-cols-3">
        {facts.map((fact) => (
          <FactRow key={fact.key} fact={fact} language={language} />
        ))}
      </div>
    </section>
  );
}
