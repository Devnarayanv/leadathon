import { Plus, ShieldCheck } from "lucide-react";
import HealthBadge from "./HealthBadge.jsx";
import Logo from "./Logo.jsx";

export default function Navbar({ onNew, onPrivacy, health, onRefreshHealth, showNew }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas/90 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-8">
        <button
          type="button"
          onClick={onNew}
          className="flex items-center gap-2.5 rounded-md text-left"
        >
          <Logo size={22} className="text-ink" />
          <span className="text-[0.98rem] font-semibold whitespace-nowrap tracking-[-0.02em]">
            Doc Decode
          </span>
        </button>

        <div className="ml-auto flex items-center gap-1.5">
          <HealthBadge health={health} onRefresh={onRefreshHealth} />
          <button
            type="button"
            onClick={onPrivacy}
            className="btn-ghost hidden !px-2.5 text-xs sm:inline-flex"
          >
            <ShieldCheck size={14} />
            Privacy
          </button>
          {showNew && (
            <button type="button" onClick={onNew} className="btn-primary !px-3 text-xs">
              <Plus size={14} />
              New<span className="hidden sm:inline"> document</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
