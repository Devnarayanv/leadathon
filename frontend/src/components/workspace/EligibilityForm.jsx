import { useState } from "react";
import { Loader2 } from "lucide-react";
import { checkEligibility } from "../../services/api.js";

const BUCKETS = [
  { key: "meets", label: "Meets requirement", tone: "good" },
  { key: "does_not_meet", label: "Does not appear to meet", tone: "crit" },
  { key: "missing", label: "Missing information", tone: "warn" },
  { key: "needs_verification", label: "Needs verification", tone: "note" },
];

const FIELDS = [
  { key: "business_type", label: "Business type", hint: "e.g. private limited" },
  { key: "turnover", label: "Annual turnover", hint: "e.g. Rs. 75 lakh" },
  { key: "experience_years", label: "Years of experience", hint: "e.g. 6" },
  { key: "certifications", label: "Certifications", hint: "comma separated" },
  { key: "registrations", label: "Registrations", hint: "comma separated" },
  { key: "documents", label: "Documents you hold", hint: "comma separated" },
];

const splitList = (text) =>
  text.split(",").map((item) => item.trim()).filter(Boolean);

// Tender eligibility assistant. The user types their own facts; the backend
// compares them with the tender's requirements. Never a guarantee.
export default function EligibilityForm({ requirements }) {
  const [form, setForm] = useState({
    business_type: "",
    turnover: "",
    experience_years: "",
    certifications: "",
    registrations: "",
    documents: "",
  });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const update = (key) => (event) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const years = form.experience_years.trim();
      const response = await checkEligibility({
        business: {
          business_type: form.business_type.trim(),
          turnover: form.turnover.trim() || null,
          experience_years: years === "" ? null : Number(years),
          certifications: splitList(form.certifications),
          registrations: splitList(form.registrations),
          documents: splitList(form.documents),
        },
        requirements,
      });
      setResult(response);
    } catch (exception) {
      setError(exception.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-5 sm:p-6">
      <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
        Eligibility assistant
      </h2>
      <p className="panel-note mt-2">
        Enter your own business facts. Doc Decode compares them with the requirements
        above. It never says you are eligible.
      </p>

      <form onSubmit={submit} className="mt-4 grid gap-3 sm:grid-cols-2">
        {FIELDS.map(({ key, label, hint }) => (
          <label key={key} className="block">
            <span className="label">{label}</span>
            <input
              className="field mt-1.5"
              value={form[key]}
              placeholder={hint}
              inputMode={key === "experience_years" ? "decimal" : undefined}
              onChange={update(key)}
            />
          </label>
        ))}
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={busy || !requirements?.length}
            className="btn-primary text-xs"
          >
            {busy && <Loader2 size={14} className="animate-spin" />}
            Check against requirements
          </button>
        </div>
      </form>

      {error && (
        <p className="mt-3 rounded-lg bg-crit-soft px-3 py-2.5 text-sm text-crit">{error}</p>
      )}

      {result && (
        <div className="mt-5 space-y-4 border-t border-line pt-4">
          {result.headline && <p className="text-[0.85rem] font-medium">{result.headline}</p>}
          {BUCKETS.map(({ key, label, tone }) => {
            const rows = result[key] ?? [];
            if (!rows.length) return null;
            return (
              <div key={key}>
                <p className="eyebrow">
                  {label} <span className="tabular-nums">({rows.length})</span>
                </p>
                <ul className="mt-2 space-y-1.5">
                  {rows.map((row, index) => (
                    <li
                      key={index}
                      className="border-l-2 pl-2.5 text-[0.8rem] leading-relaxed text-ink-soft"
                      style={{ borderColor: `var(--color-${tone})` }}
                    >
                      <span className="text-ink">{row.requirement}</span>
                      {row.detail && <span> · {row.detail}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
          {result.disclaimer && (
            <p className="text-[0.72rem] leading-relaxed text-ink-faint">{result.disclaimer}</p>
          )}
        </div>
      )}
    </section>
  );
}
