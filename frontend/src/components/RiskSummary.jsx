import { AlertTriangle, CalendarClock, CircleDollarSign, Flag, ShieldAlert } from "lucide-react";
import { ATTENTION_LABELS, t } from "../i18n.js";

// Colour carries meaning here, so each level keeps a distinct hue, but the
// chips are quiet: tinted text on a hairline border rather than filled blocks.
export const LEVEL_STYLES = {
  attention: { chip: "text-warn bg-warn-soft", accent: "border-warn/40", icon: AlertTriangle },
  financial: { chip: "text-crit bg-crit-soft", accent: "border-crit/40", icon: CircleDollarSign },
  deadline: { chip: "text-note bg-note-soft", accent: "border-note/40", icon: CalendarClock },
  unusual: { chip: "text-crit bg-crit-soft", accent: "border-crit/40", icon: ShieldAlert },
  info: { chip: "text-ink-soft bg-canvas", accent: "border-line-strong", icon: Flag },
};

const ORDER = ["unusual", "financial", "attention", "deadline", "info"];

export default function RiskSummary({ clauses, counts, language, onJump }) {
  const total = clauses?.length ?? 0;
  const levels = ORDER.filter((level) => (counts?.[level] ?? 0) > 0);

  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold tabular-nums">{total}</span>
          <span className="text-sm text-ink-soft">{t(language, "clausesFlagged")}</span>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {levels.map((level) => {
            const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.info;
            const Icon = style.icon;
            return (
              <button
                key={level}
                type="button"
                onClick={() => onJump?.(level)}
                className={`chip ${style.chip} hover:brightness-97`}
                title="Jump to the first clause in this category"
              >
                <Icon size={12} />
                {ATTENTION_LABELS[language]?.[level] ?? level}
                <span className="tabular-nums opacity-70">{counts[level]}</span>
              </button>
            );
          })}
          {!levels.length && (
            <span className="chip bg-good-soft text-good">Nothing flagged</span>
          )}
        </div>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-ink-faint">
        Attention indicators from the rule engine &mdash; not legal advice, and not
        a judgment that anything is illegal.
      </p>
    </section>
  );
}
