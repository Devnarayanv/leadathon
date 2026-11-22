import { Plus } from "lucide-react";
import HealthBadge from "./HealthBadge.jsx";
import Logo from "./Logo.jsx";

export default function Navbar({ onNew, onPrivacy, health, onRefreshHealth, showNew }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-surface/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-3 px-4 sm:px-6">
        <button
          type="button"
          onClick={onNew}
          className="flex items-center gap-2 text-left"
        >
          <Logo size={20} className="text-ink" />
          <span className="text-[0.95rem] font-semibold tracking-tight">
            Doc Decode
          </span>
          <span className="hidden text-xs text-ink-faint sm:block">
            Understand every document. Know what matters.
          </span>
        </button>

        <div className="ml-auto flex items-center gap-1">
          <HealthBadge health={health} onRefresh={onRefreshHealth} />
          <button
            type="button"
            onClick={onPrivacy}
            className="btn-ghost hidden text-xs sm:inline-flex"
          >
            Privacy
          </button>
          {showNew && (
            <button type="button" onClick={onNew} className="btn-primary text-xs">
              <Plus size={14} />
              New
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
