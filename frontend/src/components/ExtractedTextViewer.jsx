import { useState } from "react";
import { ChevronDown, FileSearch, ScanLine } from "lucide-react";
import { t } from "../i18n.js";

export default function ExtractedTextViewer({ pages, language }) {
  const [open, setOpen] = useState(false);
  const withText = (pages ?? []).filter((page) => page.text.trim());

  return (
    <section className="card p-5 sm:p-7">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 text-left"
        aria-expanded={open}
      >
        <FileSearch size={17} className="text-ink-soft" />
        <h2 className="text-lg font-semibold tracking-[-0.02em]">{t(language, "extractedText")}</h2>
        <span className="text-xs text-ink-soft">
          {withText.length} / {pages?.length ?? 0} {t(language, "pages")}
        </span>
        <ChevronDown
          size={16}
          className={`ml-auto text-ink-soft transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          <p className="text-xs text-ink-soft">
            This is exactly what the backend read. Every fact and clause above comes
            from this text.
          </p>
          {withText.length === 0 && (
            <p className="rounded-lg bg-warn-soft px-3.5 py-3 text-sm text-warn">
              No text was extracted from this file.
            </p>
          )}
          {withText.map((page) => (
            <div key={page.page}>
              <p className="label mb-1.5 flex items-center gap-1.5">
                {t(language, "page")} {page.page}
                {page.source === "ocr" && (
                  <span className="chip bg-note-soft text-note">
                    <ScanLine size={11} />
                    OCR
                  </span>
                )}
              </p>
              <pre className="evidence max-h-72 overflow-auto">{page.text}</pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
