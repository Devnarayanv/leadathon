// Shared status vocabulary. Every status shown in the workspace maps through
// here, so one word means the same thing on every tab.

export const TONE = {
  good: "bg-good-soft text-good",
  note: "bg-note-soft text-note",
  brand: "bg-brand-soft text-brand-ink",
  warn: "bg-warn-soft text-warn",
  crit: "bg-crit-soft text-crit",
  neutral: "bg-canvas text-ink-soft",
};

// How a value was obtained. Mirrors EvidenceStatus in backend/schemas.py.
export const EVIDENCE = {
  extracted: {
    en: "Directly extracted",
    ml: "നേരിട്ട് എടുത്തത്",
    tone: "good",
  },
  calculated: {
    en: "Calculated",
    ml: "കണക്കാക്കിയത്",
    tone: "note",
  },
  interpreted: {
    en: "AI interpretation",
    ml: "AI വ്യാഖ്യാനം",
    tone: "brand",
  },
  needs_verification: {
    en: "Needs verification",
    ml: "പരിശോധന വേണം",
    tone: "warn",
  },
};

// Arithmetic check outcome. Mirrors VerificationStatus.
export const VERIFY = {
  verified: { en: "Verified", ml: "ശരിയാണ്", tone: "good" },
  needs_attention: { en: "Needs attention", ml: "ശ്രദ്ധ വേണം", tone: "warn" },
  mismatch: { en: "Mismatch", ml: "പൊരുത്തക്കേട്", tone: "crit" },
  missing_information: { en: "Missing information", ml: "വിവരം ഇല്ല", tone: "warn" },
  unable_to_verify: { en: "Unable to verify", ml: "പരിശോധിക്കാനായില്ല", tone: "neutral" },
};

export const SEVERITY = {
  high: { en: "High", ml: "ഉയർന്നത്", tone: "crit" },
  medium: { en: "Medium", ml: "ഇടത്തരം", tone: "warn" },
  low: { en: "Low", ml: "കുറഞ്ഞത്", tone: "neutral" },
};

export const FINDING_CATEGORY = {
  deadline: { en: "Deadline", ml: "അവസാന തീയതി" },
  financial_obligation: { en: "Financial obligation", ml: "പണ ബാധ്യത" },
  important_condition: { en: "Important condition", ml: "പ്രധാന വ്യവസ്ഥ" },
  verification_required: { en: "Verification required", ml: "പരിശോധന ആവശ്യം" },
  missing_information: { en: "Missing information", ml: "വിവരം ഇല്ല" },
};

// Position of a deadline on the timeline. Computed in the browser from today's
// date; never shown for ambiguous or unverified dates (no countdown).
export const TIMELINE = {
  overdue: { en: "Overdue", ml: "കാലാവധി കഴിഞ്ഞു", tone: "crit" },
  due_soon: { en: "Due soon", ml: "ഉടൻ", tone: "warn" },
  upcoming: { en: "Upcoming", ml: "വരാനിരിക്കുന്നത്", tone: "good" },
  needs_verification: { en: "Needs verification", ml: "പരിശോധന വേണം", tone: "neutral" },
};

// Eligibility outcome per requirement. Never a guarantee.
export const TENDER_STATUS = {
  meets: { en: "Meets requirement", ml: "ആവശ്യം പാലിക്കുന്നു", tone: "good" },
  does_not_meet: { en: "Does not appear to meet", ml: "പാലിക്കുന്നതായി തോന്നുന്നില്ല", tone: "crit" },
  missing: { en: "Missing information", ml: "വിവരം ഇല്ല", tone: "warn" },
  needs_verification: { en: "Needs verification", ml: "പരിശോധന വേണം", tone: "note" },
  not_assessed: { en: "Not assessed yet", ml: "ഇതുവരെ പരിശോധിച്ചിട്ടില്ല", tone: "neutral" },
};

// Row outcome from /api/compare.
export const COMPARE_RESULT = {
  match: { en: "Match", ml: "ഒത്തുപോകുന്നു", tone: "good" },
  mismatch: { en: "Mismatch", ml: "പൊരുത്തക്കേട്", tone: "crit" },
  missing_left: { en: "Missing in this document", ml: "ഈ രേഖയിൽ ഇല്ല", tone: "warn" },
  missing_right: { en: "Missing in other document", ml: "മറ്റ് രേഖയിൽ ഇല്ല", tone: "warn" },
  extra: { en: "Extra charge", ml: "അധിക ചാർജ്", tone: "note" },
};

export function labelOf(map, key, language) {
  const entry = map[key];
  if (!entry) return key ?? "";
  return entry[language] ?? entry.en;
}

export function toneOf(map, key) {
  return TONE[map[key]?.tone] ?? TONE.neutral;
}

const DAY_MS = 86400000;

// Days from today to an ISO date (negative = past). Null when not a real date.
export function daysUntil(iso, today = new Date()) {
  if (!iso) return null;
  const start = new Date(today);
  start.setHours(0, 0, 0, 0);
  const target = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(target.getTime())) return null;
  return Math.round((target - start) / DAY_MS);
}

// Timeline bucket. An unverified or undated item is never bucketed as
// upcoming or overdue: that would be a countdown on a guess.
export function timelineStatus(item, today = new Date()) {
  if (!item.date_iso || item.needs_verification) return "needs_verification";
  const days = daysUntil(item.date_iso, today);
  if (days == null) return "needs_verification";
  if (days < 0) return "overdue";
  if (days <= 14) return "due_soon";
  return "upcoming";
}
