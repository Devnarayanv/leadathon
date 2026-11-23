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
    <section className="card overflow-hidden">
      <div className="grid sm:grid-cols-[10rem_minmax(0,1fr)]">
        <div className="flex items-baseline gap-2.5 border-b border-line px-5 py-4 sm:flex-col sm:justify-center sm:border-r sm:border-b-0 sm:py-5">
          <p className="text-3xl leading-none font-semibold tabular-nums tracking-[-0.04em]">
            {total}
          </p>
          <p className="text-[0.78rem] text-ink-soft">{t(language, "clausesFlagged")}</p>
        </div>

        <div className="flex flex-col justify-center gap-2.5 px-5 py-4">
          <div className="flex flex-wrap gap-1.5">
            {levels.map((level) => {
              const style = LEVEL_STYLES[level] ?? LEVEL_STYLES.info;
              const Icon = style.icon;
              return (
                <button
                  key={level}
                  type="button"
                  onClick={() => onJump?.(level)}
                  className={`chip ${style.chip} !px-2.5 !py-1 transition-colors hover:opacity-85`}
                  title="Open findings"
                >
                  <Icon size={12} />
                  {ATTENTION_LABELS[language]?.[level] ?? level}
                  <span className="font-semibold tabular-nums">{counts[level]}</span>
                </button>
              );
            })}
            {!levels.length && (
              <span className="chip bg-good-soft !px-2.5 !py-1 text-good">
                Nothing flagged
              </span>
            )}
          </div>
          <p className="text-[0.72rem] leading-relaxed text-ink-faint">
            Attention indicators from the rule engine &mdash; not legal advice, and not a
            judgment that anything is illegal.
          </p>
        </div>
      </div>
    </section>
  );
}
