import { useEffect, useState } from "react";
import { ArrowUpRight, Check, Clock, Loader2 } from "lucide-react";
import UploadArea from "../components/UploadArea.jsx";
import ProcessingStatus from "../components/ProcessingStatus.jsx";
import { demoFileUrl, listDemoDocuments } from "../services/api.js";

// Document families Doc Decode reads. Wording matches the classifier's labels.
const FAMILIES = [
  "rental and loan agreements",
  "insurance policies and contracts",
  "tenders and GST notices",
  "invoices and purchase orders",
];

const SAMPLE_LIMIT = 6;

const PRINCIPLES = [
  {
    title: "Evidence, not guesses",
    body: "Every amount, date and flagged clause carries the original sentence and its page number.",
  },
  {
    title: "Deadlines you confirm",
    body: "Dates reach the timeline only when the document states them. Tick what you have checked, then export.",
  },
  {
    title: "English or Malayalam",
    body: "Plain-language explanations come from a model on this machine. The original wording is never altered.",
  },
];

function DemoRow({ doc, onOpen, busy, active }) {
  return (
    <li>
      <button
        type="button"
        disabled={busy}
        onClick={() => onOpen(doc)}
        className="group flex h-full w-full items-start gap-4 rounded-xl px-4 py-3.5 text-left transition-colors hover:bg-sunken disabled:cursor-wait disabled:opacity-60"
      >
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-sm font-semibold">{doc.label}</span>
            <span className="text-xs text-ink-faint">{doc.doc_type}</span>
          </p>
          <p className="mt-0.5 text-[0.82rem] leading-relaxed text-ink-soft">{doc.description}</p>
          {doc.highlight && (
            <p className="mt-1 text-xs text-ink-faint">Shows {doc.highlight}</p>
          )}
        </div>
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-sunken text-ink-soft transition-colors group-hover:bg-ink group-hover:text-on-ink">
          {active ? <Loader2 size={15} className="animate-spin" /> : <ArrowUpRight size={15} />}
        </span>
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
  const [demoBusy, setDemoBusy] = useState(null);
  const [demoError, setDemoError] = useState("");
  const [showAll, setShowAll] = useState(false);

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
    setDemoBusy(doc.id);
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
      setDemoBusy(null);
    }
  };


  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-8">
      <section className="grid items-center gap-10 py-12 sm:py-16 lg:grid-cols-[1.1fr_1fr] lg:gap-16 lg:py-24">
        <div className="rise">
          <h1 className="max-w-[12ch] text-[2.6rem] leading-[1.02] font-semibold tracking-[-0.04em] sm:text-6xl lg:text-[4.6rem]">
            Every document, decoded.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-soft">
            Drop in a contract, notice or bill. Doc Decode pulls out the amounts, dates
            and clauses worth a second look, shows the original sentence beside each
            one, and never sends the file off this machine.
          </p>

          <ul className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3 sm:gap-5">
            {PRINCIPLES.map(({ title, body }) => (
              <li key={title}>
                <p className="flex items-center gap-1.5 text-sm font-semibold">
                  <Check size={15} className="shrink-0 text-brand" strokeWidth={2.5} />
                  {title}
                </p>
                <p className="mt-1 text-[0.8rem] leading-relaxed text-ink-soft">{body}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="rise rise-2">
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
          <p className="mt-4 text-center text-xs leading-relaxed text-ink-faint">
            Reads {FAMILIES.slice(0, -1).join(", ")} and {FAMILIES.at(-1)}.
          </p>
        </div>
      </section>

      {demos.length > 0 && !busy && (
        <section className="card p-2 sm:p-3">
          <div className="flex flex-wrap items-end justify-between gap-2 px-4 pt-3 pb-2">
            <div>
              <h2 className="text-lg font-semibold tracking-[-0.02em]">Try a sample document</h2>
              <p className="mt-0.5 text-[0.82rem] text-ink-soft">
                Made-up documents for exploring the workspace. No real parties or amounts.
              </p>
            </div>
            {demos.length > SAMPLE_LIMIT && (
              <button
                type="button"
                onClick={() => setShowAll((value) => !value)}
                className="btn-ghost !px-3 !py-1.5 text-xs"
              >
                {showAll ? "Show fewer" : `Show all ${demos.length}`}
              </button>
            )}
          </div>
          <ul className="grid md:grid-cols-2">
            {(showAll ? demos : demos.slice(0, SAMPLE_LIMIT)).map((doc) => (
              <DemoRow
                key={doc.id}
                doc={doc}
                onOpen={openDemo}
                busy={Boolean(demoBusy)}
                active={demoBusy === doc.id}
              />
            ))}
          </ul>
          {demoError && (
            <p className="m-3 rounded-xl bg-crit-soft px-3.5 py-2.5 text-sm text-crit">{demoError}</p>
          )}
        </section>
      )}

      {!busy && (
        <section className={`mt-6 grid gap-6 ${recent?.length > 0 ? "lg:grid-cols-2" : ""}`}>
          {recent?.length > 0 && (
            <div className="card p-5 sm:p-6">
              <h2 className="flex items-center gap-2 text-lg font-semibold tracking-[-0.02em]">
                <Clock size={16} className="text-ink-faint" />
                Recent in this browser
              </h2>
              <ul className="mt-3 space-y-1">
                {recent.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-center gap-3 rounded-lg bg-sunken px-3 py-2.5 text-xs"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[0.82rem] font-medium">{item.filename}</span>
                      <span className="text-ink-faint">{item.label}</span>
                    </span>
                    <span className="text-ink-faint tabular-nums">
                      {new Date(item.savedAt).toLocaleDateString()}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-ink-faint">
                Only names and categories are kept. Upload the file again to reopen it.
              </p>
            </div>
          )}

          <div className="rounded-[var(--radius-card)] bg-ink p-6 text-on-ink sm:p-7">
            <h2 className="text-lg font-semibold tracking-[-0.02em]">Stays on your machine</h2>
            <p className="mt-2 max-w-2xl text-[0.86rem] leading-relaxed opacity-75">
              The file is held in memory for one request and never written to disk. Its
              text goes only to the Ollama model running locally. Sending a deadline to
              Google Calendar is the one action that leaves, and it is always your click.
            </p>
          </div>
        </section>
      )}

      <p className="mx-auto mt-12 max-w-3xl text-center text-xs leading-relaxed text-ink-faint">
        <strong className="font-medium text-ink-soft">Not legal advice.</strong> Doc Decode
        points out wording that deserves attention and explains it in simpler words. It
        does not decide whether a clause is valid, legal or fair, and it can miss things.
        For a decision that matters, read the original and talk to a qualified professional.
      </p>
    </div>
  );
}
