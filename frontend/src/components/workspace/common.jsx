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
  evidence: { en: "Evidence", ml: "തെളിവ്" },
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
    en: "Requirements found in the tender. Doc Decode does not decide eligibility: it lists what the document asks for and marks each item as not yet assessed until you check it against your own papers.",
    ml: "ടെൻഡറിലെ ആവശ്യങ്ങൾ. യോഗ്യത Doc Decode തീരുമാനിക്കില്ല; ഓരോന്നും നിങ്ങളുടെ രേഖകളുമായി പരിശോധിക്കുന്നതുവരെ ഇതുവരെ പരിശോധിച്ചിട്ടില്ല എന്ന് കാണിക്കും.",
  },
  noRequirements: {
    en: "No eligibility requirements were found in this document.",
    ml: "ഈ രേഖയിൽ യോഗ്യതാ ആവശ്യങ്ങൾ കണ്ടെത്തിയില്ല.",
  },
  mandatory: { en: "Mandatory", ml: "നിർബന്ധം" },
  optional: { en: "Optional or unclear", ml: "ഐച്ഛികം / വ്യക്തമല്ല" },
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

export function Panel({ title, action, children, id }) {
  return (
    <section id={id} className="card p-5 sm:p-7">
      {(title || action) && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-lg font-semibold tracking-[-0.02em]">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Empty({ children }) {
  return <p className="text-sm leading-relaxed text-ink-soft">{children}</p>;
}
