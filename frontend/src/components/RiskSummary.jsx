import { AlertTriangle, CalendarClock, CircleDollarSign, Flag, ShieldAlert } from "lucide-react";
import { ATTENTION_LABELS, t } from "../i18n.js";

export const LEVEL_STYLES = {
  attention: {
    chip: "bg-warn-soft text-warn",
    ring: "ring-warn/25",
    icon: AlertTriangle,
  },
  financial: {
    chip: "bg-crit-soft text-crit",
    ring: "ring-crit/25",
    icon: CircleDollarSign,
  },
  deadline: {
    chip: "bg-note-soft text-note",
    ring: "ring-note/25",
    icon: CalendarClock,
  },
  unusual: {
    chip: "bg-crit-soft text-crit",
    ring: "ring-crit/25",
    icon: ShieldAlert,
  },
  info: { chip: "bg-canvas text-ink-soft", ring: "ring-line", icon: Flag },
};

const ORDER = ["unusual", "financial", "attention", "deadline", "info"];

export default function RiskSummary({ clauses, counts, language, onJump }) {
  const total = clauses?.length ?? 0;
  const levels = ORDER.filter((level) => (counts?.[level] ?? 0) > 0);

  return (
    <section className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">{t(language, "attention")}</h2>
        <p className="text-xs text-ink-soft">
          Attention indicators from the rule engine. Not legal advice, and not a
          judgment that anything is illegal.
        </p>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold tabular-nums">{total}</span>
          <span className="text-sm text-ink-soft">{t(language, "clausesFlagged")}</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {levels.map((level) => {
            const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.info;
            const Icon = style.icon;
            return (
              <button
                key={level}
                type="button"
                onClick={() => onJump?.(level)}
                className={`chip ${style.chip} hover:brightness-95`}
                title="Jump to the first clause in this category"
              >
                <Icon size={13} />
                {ATTENTION_LABELS[language]?.[level] ?? level}
                <span className="font-semibold tabular-nums">{counts[level]}</span>
              </button>
            );
          })}
          {!levels.length && (
            <span className="chip bg-good-soft text-good">Nothing flagged</span>
          )}
        </div>
      </div>
    </section>
  );
}
