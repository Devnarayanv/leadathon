import { Info, Languages, Loader2 } from "lucide-react";
import { t } from "../i18n.js";

const OPTIONS = [
  { value: "en", label: "English" },
  { value: "ml", label: "മലയാളം" },
];

// Switching language re-asks the model for explanations in that language. The
// original clause text is never translated: it stays exactly as the document
// wrote it.
export default function LanguageSelector({
  language,
  onChange,
  busy,
  modelName,
  malayalamModel,
  speech,
}) {
  const canSpeak = speech ? speech.canSpeak(language) : true;
  const browserVoice = speech ? speech.hasVoiceFor(language) : true;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1.5 text-xs text-ink-soft">
        <Languages size={14} />
        {t(language, "language")}
      </span>
      <div className="seg" role="group" aria-label={t(language, "language")}>
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            disabled={busy}
            data-active={option.value === language}
            aria-pressed={option.value === language}
            onClick={() => option.value !== language && onChange(option.value)}
            className="seg-item"
          >
            {option.label}
          </button>
        ))}
      </div>
      {busy && (
        <span className="flex items-center gap-1.5 text-xs text-ink-soft">
          <Loader2 size={13} className="animate-spin" />
          {t(language, "switching")}
        </span>
      )}
      {language === "ml" && !busy && (
        <span className="flex items-start gap-1.5 text-[0.7rem] text-ink-soft">
          <Info size={12} className="mt-0.5 shrink-0" />
          <span>
            Malayalam uses a larger model
            {malayalamModel ? ` (${malayalamModel})` : ""}, so the first switch is
            slower while it loads. Doc Decode checks that the reply really is
            Malayalam script and falls back to rule-based notes rather than show
            you something it cannot vouch for. The original clause text is never
            translated.
          </span>
        </span>
      )}
      {language === "ml" && !busy && !canSpeak && (
        <span className="text-[0.7rem] text-warn">
          No Malayalam voice on this machine, so audio is off for Malayalam.
          Install the offline engine (see Privacy &rarr; Audio) to enable it.
        </span>
      )}
      {language === "ml" && !busy && canSpeak && !browserVoice && (
        <span className="text-[0.7rem] text-ink-faint">
          Malayalam audio uses the offline engine on this machine.
        </span>
      )}
      {language === "en" && !busy && malayalamModel && modelName &&
        malayalamModel !== modelName && (
          <span className="text-[0.7rem] text-ink-soft">
            English uses {modelName}; Malayalam switches to {malayalamModel}.
          </span>
        )}
    </div>
  );
}
