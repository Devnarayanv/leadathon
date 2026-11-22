import { useState } from "react";
import { Loader2 } from "lucide-react";
import { checkEligibility } from "../../services/api.js";

const BUCKETS = [
  { key: "meets", label: "Meets requirement" },
  { key: "does_not_meet", label: "Does not appear to meet" },
  { key: "missing", label: "Missing information" },
  { key: "needs_verification", label: "Needs verification" },
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

  const inputClass =
    "w-full rounded-lg border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink outline-none focus:border-ink";

  return (
    <section className="mt-6 border-t border-line pt-5">
      <h3 className="text-sm font-semibold">Eligibility assistant</h3>
      <p className="mt-1 text-xs leading-relaxed text-ink-soft">
        Enter your own business facts. Doc Decode compares them with the
        requirements above. It never says you are eligible.
      </p>
      <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-ink-soft">
          Business type
          <input className={inputClass} value={form.business_type} onChange={update("business_type")} />
        </label>
        <label className="text-xs text-ink-soft">
          Annual turnover (e.g. Rs. 75 lakh)
          <input className={inputClass} value={form.turnover} onChange={update("turnover")} />
        </label>
        <label className="text-xs text-ink-soft">
          Years of experience
          <input
            className={inputClass}
            inputMode="decimal"
            value={form.experience_years}
            onChange={update("experience_years")}
          />
        </label>
        <label className="text-xs text-ink-soft">
          Certifications (comma separated)
          <input className={inputClass} value={form.certifications} onChange={update("certifications")} />
        </label>
        <label className="text-xs text-ink-soft">
          Registrations (comma separated)
          <input className={inputClass} value={form.registrations} onChange={update("registrations")} />
        </label>
        <label className="text-xs text-ink-soft">
          Documents you hold (comma separated)
          <input className={inputClass} value={form.documents} onChange={update("documents")} />
        </label>
        <div className="sm:col-span-2">
          <button type="submit" disabled={busy || !requirements?.length} className="btn-primary text-xs">
            {busy && <Loader2 size={14} className="animate-spin" />}
            Check against requirements
          </button>
        </div>
      </form>

      {error && <p className="mt-3 rounded-lg bg-crit-soft px-3 py-2.5 text-sm text-crit">{error}</p>}

      {result && (
        <div className="mt-4 space-y-3">
          {result.headline && <p className="text-sm font-medium">{result.headline}</p>}
          {BUCKETS.map(({ key, label }) => {
            const rows = result[key] ?? [];
            if (!rows.length) return null;
            return (
              <div key={key}>
                <p className="label">{label} ({rows.length})</p>
                <ul className="mt-1.5 space-y-1.5">
                  {rows.map((row, index) => (
                    <li key={index} className="text-xs leading-relaxed text-ink-soft">
                      <span className="text-ink">{row.requirement}</span>
                      {row.detail && <span> · {row.detail}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
          {result.disclaimer && (
            <p className="text-[0.7rem] leading-relaxed text-ink-faint">{result.disclaimer}</p>
          )}
        </div>
      )}
    </section>
  );
}
