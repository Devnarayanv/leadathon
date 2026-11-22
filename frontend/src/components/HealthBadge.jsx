import { useState } from "react";
import { Cpu, RefreshCw, X } from "lucide-react";

// Shows the real state of the local model. It never claims the model is ready
// when the backend says otherwise.
export default function HealthBadge({ health, onRefresh }) {
  const [open, setOpen] = useState(false);

  const ollama = health?.ollama;
  const ready = Boolean(ollama?.reachable && ollama?.model_available);
  const unknown = !health;

  const dot = unknown
    ? "bg-ink-soft"
    : ready
      ? "bg-good"
      : ollama?.reachable
        ? "bg-warn"
        : "bg-crit";

  const label = unknown
    ? "Checking"
    : ready
      ? ollama.model
      : ollama?.reachable
        ? "Model missing"
        : "Ollama offline";

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="btn-secondary !px-2.5 !py-2 text-xs"
        title="Local AI status"
      >
        <span className={`h-2 w-2 rounded-full ${dot}`} />
        <Cpu size={14} className="hidden sm:block" />
        <span className="max-w-[9rem] truncate">{label}</span>
      </button>

      {open && (
        <div className="card absolute right-0 mt-2 w-[min(22rem,calc(100vw-2rem))] p-4 shadow-lg">
          <div className="mb-2 flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold">Local AI status</h3>
            <button type="button" onClick={() => setOpen(false)} className="btn-ghost !p-1">
              <X size={14} />
            </button>
          </div>

          <dl className="space-y-1.5 text-xs">
            <Row name="Backend" value={health ? "running" : "not reachable"} />
            <Row name="Ollama URL" value={ollama?.base_url ?? "-"} />
            <Row name="Configured model" value={ollama?.model ?? "-"} />
            <Row
              name="Model installed"
              value={unknown ? "-" : ollama?.model_available ? "yes" : "no"}
            />
            <Row
              name="OCR (scans)"
              value={
                health?.ocr?.available
                  ? `available (${health.ocr.active_languages || "eng"})`
                  : "not installed"
              }
            />
            <Row
              name="Malayalam OCR"
              value={health?.ocr?.malayalam ? "installed" : "not installed"}
            />
          </dl>

          {!ready && (
            <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-canvas p-3 text-[0.7rem] leading-relaxed whitespace-pre-wrap text-ink-soft">
              {ollama?.message ||
                "The backend is not reachable. Start it with: uvicorn main:app --reload"}
            </pre>
          )}
          {!health?.ocr?.available && health && (
            <pre className="mt-2 max-h-32 overflow-auto rounded-lg bg-canvas p-3 text-[0.7rem] leading-relaxed whitespace-pre-wrap text-ink-soft">
              {health.ocr?.message}
            </pre>
          )}

          <button
            type="button"
            onClick={onRefresh}
            className="btn-secondary mt-3 w-full text-xs"
          >
            <RefreshCw size={14} />
            Check again
          </button>
        </div>
      )}
    </div>
  );
}

function Row({ name, value }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-ink-soft">{name}</dt>
      <dd className="max-w-[60%] truncate text-right font-medium">{value}</dd>
    </div>
  );
}
