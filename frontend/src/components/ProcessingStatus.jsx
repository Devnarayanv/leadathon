import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

// The backend does the whole pipeline in one request, so this shows which
// stage is plausibly running rather than inventing a progress percentage.
const STAGES = [
  { label: "Checking the file", seconds: 0 },
  { label: "Reading the text", seconds: 1 },
  { label: "Finding facts and clauses", seconds: 3 },
  { label: "Asking the local AI model", seconds: 5 },
];

export default function ProcessingStatus({ aiEnabled }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => setElapsed((Date.now() - started) / 1000), 400);
    return () => clearInterval(timer);
  }, []);

  const stages = aiEnabled ? STAGES : STAGES.slice(0, 3);
  const activeIndex = stages.reduce(
    (current, stage, index) => (elapsed >= stage.seconds ? index : current),
    0,
  );

  return (
    <div className="card p-6 sm:p-8">
      <div className="flex items-center gap-2.5">
        <Loader2 size={16} className="animate-spin text-ink-soft" />
        <h2 className="text-base font-semibold">Working on your document</h2>
        <span className="ml-auto rounded-full bg-sunken px-2.5 py-0.5 text-xs text-ink-soft tabular-nums">{elapsed.toFixed(0)}s</span>
      </div>

      <ol className="mt-6 space-y-1">
        {stages.map((stage, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          return (
            <li
              key={stage.label}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${active ? "bg-sunken" : ""}`}
            >
              <span
                className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-[0.65rem] ${
                  done
                    ? "bg-good-soft text-good"
                    : active
                      ? "bg-ink text-on-ink"
                      : "bg-canvas text-ink-faint"
                }`}
              >
                {done ? <Check size={12} /> : index + 1}
              </span>
              <span className={done || active ? "text-ink" : "text-ink-soft"}>
                {stage.label}
              </span>
              {active && <Loader2 size={13} className="ml-auto animate-spin text-ink-soft" />}
            </li>
          );
        })}
      </ol>

      <p className="mt-5 text-xs leading-relaxed text-ink-soft">
        {aiEnabled
          ? "The local model runs on your own machine, so the first run after starting Ollama is the slowest."
          : "Rule-based analysis only. No AI explanations were requested."}
      </p>
    </div>
  );
}
