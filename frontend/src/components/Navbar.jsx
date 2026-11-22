import { FileText, Plus, ShieldCheck } from "lucide-react";
import HealthBadge from "./HealthBadge.jsx";

export default function Navbar({ onNew, onPrivacy, health, onRefreshHealth }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:px-6">
        <button
          type="button"
          onClick={onNew}
          className="flex items-center gap-2.5 rounded-lg px-1 py-1 text-left"
        >
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand text-white">
            <FileText size={18} strokeWidth={2.2} />
          </span>
          <span className="leading-tight">
            <span className="block text-[0.95rem] font-semibold">PlainSpeak</span>
            <span className="hidden text-xs text-ink-soft sm:block">
              Understand before you sign.
            </span>
          </span>
        </button>

        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <HealthBadge health={health} onRefresh={onRefreshHealth} />
          <button type="button" onClick={onPrivacy} className="btn-ghost hidden sm:inline-flex">
            <ShieldCheck size={16} />
            Privacy
          </button>
          <button type="button" onClick={onNew} className="btn-primary">
            <Plus size={16} />
            <span className="hidden sm:inline">New analysis</span>
            <span className="sm:hidden">New</span>
          </button>
        </div>
      </div>
    </header>
  );
}
