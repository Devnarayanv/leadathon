import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { ATTENTION_LABELS, CONFIDENCE_LABELS, t } from "../i18n.js";
import { LEVEL_STYLES } from "./RiskSummary.jsx";
import AudioControls from "./AudioControls.jsx";

function Block({ title, children, language }) {
  if (!children) return null;
  return (
    <div>
      <p className="label">{title}</p>
      <p className={`prose-plain mt-1 ${language === "ml" ? "lang-ml" : ""}`}>
        {children}
      </p>
    </div>
  );
}

export default function RiskCard({ clause, language, speech, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const style = LEVEL_STYLES[clause.attention_level] ?? LEVEL_STYLES.info;
  const Icon = style.icon;
  const explanation = clause.explanation;
  const fromModel = explanation?.source === "llm";

  const spoken = [
    explanation?.plain_meaning,
    explanation?.why_pay_attention,
    explanation?.next_step,
  ]
    .filter(Boolean)
    .join(". ");

  return (
    <article
      id={`clause-${clause.id}`}
      className={`card scroll-mt-20 border-l-2 p-5 sm:p-6 ${style.accent}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`chip ${style.chip}`}>
          <Icon size={12} />
          {ATTENTION_LABELS[language]?.[clause.attention_level] ?? clause.attention_level}
        </span>
        <span className="text-xs text-ink-soft">{clause.label}</span>
        {clause.page != null && (
          <span className="text-xs text-ink-faint">
            {t(language, "page")} {clause.page}
          </span>
        )}
        <span className="ml-auto text-[0.7rem] text-ink-faint">
          {fromModel ? t(language, "bySource").llm : t(language, "bySource").rules}
        </span>
      </div>

      {explanation?.plain_meaning && (
        <p className={`prose-plain mt-3 ${language === "ml" ? "lang-ml" : ""}`}>
          {explanation.plain_meaning}
        </p>
      )}

      <p className="label mt-4">{t(language, "originalText")}</p>
      <blockquote className="evidence mt-1.5">{clause.text}</blockquote>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="btn-ghost !px-2 !py-1 text-xs"
          aria-expanded={open}
        >
          <ChevronDown
            size={13}
            className={`transition-transform ${open ? "rotate-180" : ""}`}
          />
          {open ? t(language, "collapse") : t(language, "expand")}
        </button>
        <AudioControls
          id={`clause-${clause.id}`}
          text={spoken || clause.text}
          language={language}
          speech={speech}
          label={t(language, "play")}
          stopLabel={t(language, "stop")}
          compact
        />
        <span
          className="ml-auto text-[0.7rem] text-ink-faint"
          title="How strongly the wording matched the rule"
        >
          {CONFIDENCE_LABELS[language]?.[clause.confidence] ?? clause.confidence}
        </span>
      </div>

      {open && (
        <div className="mt-4 space-y-3.5 border-t border-line pt-4">
          <div>
            <p className="label">{t(language, "whyFlagged")}</p>
            <p className="prose-plain mt-1 text-ink-soft">{clause.reason}</p>
          </div>
          <Block title={t(language, "whatItSays")} language={language}>
            {explanation?.what_it_says}
          </Block>
          <Block title={t(language, "whyAttention")} language={language}>
            {explanation?.why_pay_attention}
          </Block>
          {explanation?.uncertain && (
            <div className="rule-left border-warn/40">
              <p className="label text-warn">{t(language, "uncertain")}</p>
              <p
                className={`prose-plain mt-1 text-ink-soft ${
                  language === "ml" ? "lang-ml" : ""
                }`}
              >
                {explanation.uncertain}
              </p>
            </div>
          )}
          <div className="rule-left border-ink">
            <p className="label text-ink">{t(language, "suggestedAction")}</p>
            <p
              className={`prose-plain mt-1 ${language === "ml" ? "lang-ml" : ""}`}
            >
              {explanation?.next_step || clause.suggested_action}
            </p>
          </div>
          {clause.matched_terms?.length > 0 && (
            <p className="flex flex-wrap items-center gap-1.5 text-[0.7rem] text-ink-faint">
              Matched wording:
              {clause.matched_terms.map((term) => (
                <code key={term} className="rounded bg-canvas px-1.5 py-0.5">
                  {term}
                </code>
              ))}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
