import { useState } from "react";
import { ChevronDown, Quote } from "lucide-react";
import { labelOf, toneOf } from "../../labels.js";

// Workspace-only strings. Malayalam falls back to English where a translation
// has not been written yet, so no key ever renders blank.
const WS = {
  overview: { en: "Overview", ml: "അവലോകനം" },
  data: { en: "Extracted data", ml: "വിവരങ്ങൾ" },
  verify: { en: "Verify", ml: "പരിശോധന" },
  timeline: { en: "Deadlines", ml: "അവസാന തീയതികൾ" },
  findings: { en: "Findings & actions", ml: "കണ്ടെത്തലുകൾ" },
  tender: { en: "Tender checklist", ml: "ടെൻഡർ പരിശോധന" },
  ask: { en: "Ask Doc Decode", ml: "ചോദിക്കൂ" },
  sections: { en: "Sections", ml: "വിഭാഗങ്ങൾ" },
  evidence: { en: "Evidence", ml: "തെളിവ്" },
  documentText: { en: "Document text", ml: "രേഖയിലെ വാചകം" },
  original: { en: "Original text", ml: "മൂല വാചകം" },
  page: { en: "Page", ml: "പേജ്" },
  description: { en: "Description", ml: "വിവരണം" },
  qty: { en: "Qty", ml: "എണ്ണം" },
  unitPrice: { en: "Unit price", ml: "യൂണിറ്റ് വില" },
  amount: { en: "Amount", ml: "തുക" },
  noFindings: {
    en: "No findings were raised for this document.",
    ml: "ഈ രേഖയ്ക്ക് കണ്ടെത്തലുകൾ ഇല്ല.",
  },
  noActions: { en: "No actions suggested.", ml: "നിർദേശിച്ച നടപടികൾ ഇല്ല." },
  actionCenter: { en: "Action center", ml: "നടപടി കേന്ദ്രം" },
  changeType: { en: "Change category", ml: "വിഭാഗം മാറ്റുക" },
  changeTypeHint: {
    en: "If the category is wrong, pick the right one. Doc Decode re-runs its checks on the text it already read.",
    ml: "വിഭാഗം തെറ്റാണെങ്കിൽ ശരിയായത് തിരഞ്ഞെടുക്കുക. നേരത്തെ വായിച്ച വാചകത്തിൽ വീണ്ടും പരിശോധിക്കും.",
  },
  reclassifyBusy: { en: "Re-running checks…", ml: "വീണ്ടും പരിശോധിക്കുന്നു…" },
  compareTitle: { en: "Compare with another document", ml: "മറ്റൊരു രേഖയുമായി താരതമ്യം" },
  compareHint: {
    en: "Upload the second document. It is analysed the same way, then the two are compared line by line.",
    ml: "രണ്ടാമത്തെ രേഖ അപ്‌ലോഡ് ചെയ്യുക. ഇതും അതേ രീതിയിൽ വിശകലനം ചെയ്യും.",
  },
  compareBusy: { en: "Comparing…", ml: "താരതമ്യം ചെയ്യുന്നു…" },
  noCompare: { en: "Nothing to compare yet.", ml: "താരതമ്യം ചെയ്യാൻ ഒന്നും ഇല്ല." },
  verifyNotApplicable: {
    en: "No arithmetic checks apply to this document type.",
    ml: "ഈ രേഖാ വിഭാഗത്തിന് കണക്ക് പരിശോധന ബാധകമല്ല.",
  },
  calculated: { en: "Calculated value", ml: "കണക്കാക്കിയ മൂല്യം" },
  documentValue: { en: "Document value", ml: "രേഖയിലെ മൂല്യം" },
  difference: { en: "Difference", ml: "വ്യത്യാസം" },
  assumptions: { en: "Assumptions", ml: "അനുമാനങ്ങൾ" },
  missingFields: { en: "Missing fields", ml: "ഇല്ലാത്ത വിവരങ്ങൾ" },
  lineItems: { en: "Line items", ml: "ഇനങ്ങൾ" },
  noLineItems: { en: "No line items found in this document.", ml: "ഇനങ്ങൾ കണ്ടെത്തിയില്ല." },
  tenderIntro: {
    en: "Every requirement the tender asks for, listed in one place. Doc Decode does not decide eligibility — mark each row once you have checked it against your own papers.",
    ml: "ടെൻഡർ ആവശ്യപ്പെടുന്ന എല്ലാ കാര്യങ്ങളും ഒരിടത്ത്. യോഗ്യത Doc Decode തീരുമാനിക്കില്ല; നിങ്ങളുടെ രേഖകളുമായി പരിശോധിച്ച ശേഷം ഓരോ വരിയും അടയാളപ്പെടുത്തുക.",
  },
  noRequirements: {
    en: "No eligibility requirements were found in this document.",
    ml: "ഈ രേഖയിൽ യോഗ്യതാ ആവശ്യങ്ങൾ കണ്ടെത്തിയില്ല.",
  },
  mandatory: { en: "Mandatory", ml: "നിർബന്ധം" },
  optional: { en: "Optional or unclear", ml: "ഐച്ഛികം / വ്യക്തമല്ല" },
  assessed: { en: "assessed", ml: "പരിശോധിച്ചു" },
  meetsShort: { en: "Meets", ml: "പാലിക്കുന്നു" },
  doesNotMeetShort: { en: "Does not meet", ml: "പാലിക്കുന്നില്ല" },
  clearMark: { en: "Clear mark", ml: "അടയാളം മാറ്റുക" },
  dueOn: { en: "Due", ml: "അവസാന തീയതി" },
  markDone: { en: "Done", ml: "ചെയ്തു" },
  priority: { en: "Priority", ml: "മുൻഗണന" },
  noDates: {
    en: "No dated deadlines. Undated or unverified items are listed without a countdown.",
    ml: "തീയതിയുള്ള അവസാന തീയതികൾ ഇല്ല. തീയതി ഇല്ലാത്തതോ പരിശോധിക്കാത്തതോ ആയവ കൗണ്ട്ഡൗൺ ഇല്ലാതെ കാണിക്കും.",
  },
  timelineNote: {
    en: "Countdowns use today's date on this device. Items with no verified date are never placed on the timeline as upcoming or overdue.",
    ml: "കൗണ്ട്ഡൗൺ ഈ ഉപകരണത്തിലെ ഇന്നത്തെ തീയതി അടിസ്ഥാനമാക്കിയാണ്.",
  },
  recurring: { en: "Repeats", ml: "ആവർത്തിക്കുന്നു" },
  calculatedNote: {
    en: "Calculated from another date in the document. Check before you act.",
    ml: "രേഖയിലെ മറ്റൊരു തീയതിയിൽ നിന്ന് കണക്കാക്കിയത്. പ്രവർത്തിക്കും മുൻപ് പരിശോധിക്കുക.",
  },
};

export function ws(language, key) {
  const entry = WS[key];
  if (!entry) return key;
  return entry[language] ?? entry.en;
}

// One status word, one colour, everywhere. `map` is one of the tables in
// labels.js; the chip never invents its own wording.
export function StatusChip({ map, status, language, className = "" }) {
  if (!status) return null;
  return (
    <span
      className={`chip ${toneOf(map, status)} ${className}`}
      data-status={status}
    >
      {labelOf(map, status, language)}
    </span>
  );
}

// Panel: eyebrow (optional), heading, an optional right-side action, then the
// body. The hairline above the body keeps every tab on the same rhythm.
export function Panel({ title, eyebrow, action, children, id }) {
  return (
    <section id={id} className="card p-5 sm:p-6">
      {(title || action) && (
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div className="min-w-0">
            {eyebrow && <p className="eyebrow mb-1.5">{eyebrow}</p>}
            {title && (
              <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
                {title}
              </h2>
            )}
          </div>
          {action}
        </div>
      )}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function Empty({ children }) {
  return <p className="text-[0.82rem] leading-relaxed text-ink-soft">{children}</p>;
}

// The document's own wording, folded away by default. Panels show our summary;
// the quoted sentence is one click away and never mixed into the reading flow.
export function SourceText({ text, page, language, className = "" }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 text-[0.72rem] font-medium text-ink-faint transition-colors hover:text-ink"
      >
        <Quote size={12} className="shrink-0" />
        {ws(language, "documentText")}
        {page != null && (
          <span className="tabular-nums">· {ws(language, "page")} {page}</span>
        )}
        <ChevronDown
          size={12}
          className={`shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && <p className="evidence mt-2">{text}</p>}
    </div>
  );
}
