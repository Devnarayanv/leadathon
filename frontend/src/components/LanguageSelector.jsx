import { Languages, Loader2 } from "lucide-react";
import { t } from "../i18n.js";

const OPTIONS = [
  { value: "en", label: "English" },
  { value: "ml", label: "മലയാളം" },
];

// Switching language re-asks the model for explanations in that language. The
// original clause text is never translated: it stays exactly as the document
// wrote it.
export default function LanguageSelector({ language, onChange, busy }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1.5 text-xs text-ink-soft">
        <Languages size={14} />
        {t(language, "language")}
      </span>
      <div className="inline-flex rounded-lg border border-line bg-surface p-0.5">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            disabled={busy}
            onClick={() => option.value !== language && onChange(option.value)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-60 ${
              option.value === language
                ? "bg-brand text-white"
                : "text-ink-soft hover:text-ink"
            }`}
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
    </div>
  );
}
