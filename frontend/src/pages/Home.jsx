import { useEffect, useState } from "react";
import {
  CalendarClock,
  FileSearch,
  Languages,
  Lock,
  ScrollText,
  Scale,
  ShieldCheck,
} from "lucide-react";
import UploadArea from "../components/UploadArea.jsx";
import ProcessingStatus from "../components/ProcessingStatus.jsx";
import { demoFileUrl, listDemoDocuments } from "../services/api.js";

// Document families Doc Decode reads. Wording matches the classifier's labels.
const FAMILIES = [
  { icon: ScrollText, label: "Rental & loan agreements" },
  { icon: ShieldCheck, label: "Insurance & contracts" },
  { icon: Scale, label: "Tenders & GST notices" },
  { icon: FileSearch, label: "Invoices & purchase orders" },
];

const PRINCIPLES = [
  {
    icon: FileSearch,
    title: "Evidence, not guesses",
    body: "Every amount, date and flagged clause carries the original sentence and its page number.",
  },
  {
    icon: CalendarClock,
    title: "Deadlines you confirm",
    body: "Dates are placed on a timeline only when the document states them. Tick what you have checked, then export.",
  },
  {
    icon: Languages,
    title: "English or Malayalam",
    body: "Plain-language explanations come from a model on this machine. The original wording is never altered.",
  },
];

function DemoCard({ doc, onOpen, busy }) {
  return (
    <li className="card flex flex-col p-4">
      <p className="text-[0.65rem] tracking-wide text-ink-faint uppercase">{doc.doc_type}</p>
      <p className="mt-1 text-sm font-semibold">{doc.label}</p>
      <p className="mt-1 flex-1 text-xs leading-relaxed text-ink-soft">{doc.description}</p>
      {doc.highlight && (
        <p className="mt-2 text-[0.7rem] text-ink-faint">Shows: {doc.highlight}</p>
      )}
      <button
        type="button"
        disabled={busy}
        onClick={() => onOpen(doc)}
        className="btn-secondary mt-3 self-start text-xs"
      >
        Explore Demo
      </button>
    </li>
  );
}

export default function Home({
  onAnalyse,
  busy,
  maxUploadMb,
  error,
  onClearError,
  aiEnabled,
  recent,
}) {
  const [demos, setDemos] = useState([]);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState("");

  // Sample documents are optional. If the endpoint is absent or fails, the
  // section simply does not appear; nothing is faked in its place.
  useEffect(() => {
    const controller = new AbortController();
    listDemoDocuments(controller.signal)
      .then((body) => setDemos(Array.isArray(body) ? body : (body?.documents ?? [])))
      .catch(() => setDemos([]));
    return () => controller.abort();
  }, []);

  const openDemo = async (doc) => {
    setDemoBusy(true);
    setDemoError("");
    try {
      const response = await fetch(demoFileUrl(doc.id));
      if (!response.ok) throw new Error(`Sample could not be loaded (HTTP ${response.status}).`);
      const blob = await response.blob();
      const file = new File([blob], doc.filename, { type: blob.type || undefined });
      await onAnalyse(file);
    } catch (exception) {
      setDemoError(exception.message);
    } finally {
      setDemoBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16">
      <section className="mx-auto max-w-2xl text-center">
        <span className="chip bg-canvas text-ink-soft">
          <Lock size={12} />
          Runs on your machine
        </span>
        <h1 className="mt-4 text-3xl leading-[1.12] font-semibold tracking-tight sm:text-5xl">
          Your documents. <span className="text-brand">Decoded.</span>
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-[0.95rem] leading-relaxed text-ink-soft">
          Understand every document. Know what matters. Doc Decode pulls out the
          amounts, dates and clauses worth a second look, and shows the original
          sentence beside each one.
        </p>
      </section>

      <section className="mx-auto mt-8 max-w-xl">
        {busy ? (
          <ProcessingStatus aiEnabled={aiEnabled} />
        ) : (
          <UploadArea
            onAnalyse={onAnalyse}
            busy={busy}
            maxUploadMb={maxUploadMb}
            error={error}
            onClearError={onClearError}
          />
        )}

        <ul className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {FAMILIES.map(({ icon: Icon, label }) => (
            <li
              key={label}
              className="flex items-center gap-2 rounded-lg border border-line bg-surface px-2.5 py-2 text-[0.7rem] text-ink-soft"
            >
              <Icon size={13} className="shrink-0 text-ink-faint" />
              {label}
            </li>
          ))}
        </ul>
      </section>

      {recent?.length > 0 && !busy && (
        <section className="mx-auto mt-10 max-w-3xl">
          <h2 className="label">Recent in this browser</h2>
          <ul className="mt-3 divide-y divide-line rounded-[var(--radius-card)] border border-line bg-surface">
            {recent.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-xs">
                <span className="min-w-0 flex-1 truncate font-medium">{item.filename}</span>
                <span className="text-ink-soft">{item.label}</span>
                <span className="text-ink-faint tabular-nums">
                  {new Date(item.savedAt).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[0.7rem] text-ink-faint">
            Only names and categories are kept here. Upload the file again to reopen it.
          </p>
        </section>
      )}

      {demos.length > 0 && !busy && (
        <section className="mx-auto mt-12 max-w-4xl">
          <h2 className="label">Sample document (fictional)</h2>
          <p className="mt-1 text-xs text-ink-soft">
            Made-up documents for trying the workspace. They are not real parties or real amounts.
          </p>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {demos.map((doc) => (
              <DemoCard key={doc.id} doc={doc} onOpen={openDemo} busy={demoBusy} />
            ))}
          </ul>
          {demoError && (
            <p className="mt-3 rounded-lg bg-crit-soft px-3 py-2.5 text-sm text-crit">{demoError}</p>
          )}
        </section>
      )}

      <section className="mx-auto mt-14 grid max-w-4xl gap-8 sm:grid-cols-3">
        {PRINCIPLES.map(({ icon: Icon, title, body }) => (
          <div key={title}>
            <Icon size={17} className="text-ink-faint" />
            <h3 className="mt-2.5 text-sm font-semibold">{title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-ink-soft">{body}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto mt-12 max-w-4xl space-y-2 border-t border-line pt-8 text-xs leading-relaxed text-ink-faint">
        <p>
          <strong className="font-medium text-ink-soft">Privacy.</strong> The file
          is held in memory for one request and never written to disk. Its text
          goes only to the Ollama model on your own machine. No cloud AI service is
          used. Sending a deadline to Google Calendar is the one action that leaves
          your machine, and it is always your click.
        </p>
        <p>
          <strong className="font-medium text-ink-soft">Not legal advice.</strong>{" "}
          Doc Decode points out wording that deserves attention and explains it in
          simpler words. It does not decide whether a clause is valid, legal or
          fair, and it can miss things. For a decision that matters, read the
          original and talk to a qualified professional.
        </p>
      </section>
    </div>
  );
}
