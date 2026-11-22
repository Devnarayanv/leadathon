import {
  AlertTriangle,
  CalendarClock,
  FileSearch,
  Languages,
  Lock,
  ScanLine,
  ShieldCheck,
  Volume2,
} from "lucide-react";
import UploadArea from "../components/UploadArea.jsx";
import ProcessingStatus from "../components/ProcessingStatus.jsx";

const DOC_TYPES = [
  "Rental agreements",
  "Loan agreements",
  "Hospital bills",
  "Government notices",
];

const FEATURES = [
  {
    icon: FileSearch,
    title: "Evidence, not guesses",
    body: "Every amount, date and flagged clause is shown with the original sentence and its page number, so you can check it yourself.",
  },
  {
    icon: Languages,
    title: "Plain English or Malayalam",
    body: "Explanations are rewritten in simple language by a model running on this machine. The original wording is never altered.",
  },
  {
    icon: CalendarClock,
    title: "Deadlines you confirm",
    body: "Possible deadlines are extracted with their source sentence. You tick the ones you have checked, and only those export to your calendar.",
  },
];

const STEPS = [
  "Upload a PDF or a photo of the document.",
  "The backend reads the text, using OCR only for pages that need it.",
  "Python rules pull out amounts, dates and clauses worth a second look.",
  "A local Ollama model rewrites those clauses in plain language.",
  "You read the explanation beside the original text, ask questions, and export the dates you confirmed.",
];

export default function Home({ onAnalyse, busy, maxUploadMb, error, onClearError, aiEnabled }) {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <div className="grid gap-8 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
        <div>
          <span className="chip bg-brand-soft text-brand-ink">
            <Lock size={13} />
            Runs on your machine
          </span>
          <h1 className="mt-4 text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">
            Understand before you sign.
          </h1>
          <p className="mt-3 max-w-xl text-[0.95rem] leading-relaxed text-ink-soft">
            PlainSpeak reads a rental agreement, loan agreement, hospital bill or
            government notice and turns it into something you can actually act on:
            the amounts and dates it contains, the sentences worth a second look, and
            an explanation of each one in plain English or Malayalam.
          </p>

          <div className="mt-5">
            <p className="label">Supported documents</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {DOC_TYPES.map((type) => (
                <span key={type} className="chip bg-surface text-ink-soft ring-1 ring-line">
                  {type}
                </span>
              ))}
              <span className="chip bg-surface text-ink-soft ring-1 ring-line">
                Other (generic rules)
              </span>
            </div>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="card p-4">
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-soft text-brand-ink">
                  <Icon size={17} />
                </span>
                <h3 className="mt-3 text-sm font-semibold">{title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-ink-soft">{body}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:sticky lg:top-24 lg:self-start">
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

          <div className="card mt-4 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck size={16} className="text-good" />
              What happens to your document
            </p>
            <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-ink-soft">
              <li>
                The file is held in memory for one request and is never written to disk
                by this app.
              </li>
              <li>
                Its text is sent to the Ollama model running at your own
                <code className="mx-1 rounded bg-canvas px-1">localhost</code>
                address. Nothing leaves your machine.
              </li>
              <li>No cloud AI service is used, and nothing is kept for training.</li>
              <li>Document text is not written to the server log.</li>
            </ul>
            <p className="mt-2 text-xs text-ink-soft">
              This is a hackathon MVP, not a hardened product. Treat your documents as
              sensitive and do not run it on a machine you do not control.
            </p>
          </div>
        </div>
      </div>

      <section className="mt-12 card p-5 sm:p-6">
        <h2 className="text-sm font-semibold">How it works</h2>
        <ol className="mt-3 grid gap-3 sm:grid-cols-5">
          {STEPS.map((step, index) => (
            <li key={step} className="flex gap-2.5 text-xs leading-relaxed text-ink-soft">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-soft text-[0.65rem] font-semibold text-brand-ink">
                {index + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
        <p className="mt-4 flex items-center gap-2 text-xs text-ink-soft">
          <ScanLine size={14} />
          Scans and photos need Tesseract OCR installed.
          <Volume2 size={14} className="ml-2" />
          Audio uses your browser&rsquo;s own speech voices.
        </p>
      </section>

      <section className="mt-6 rounded-[var(--radius-card)] border border-warn/30 bg-warn-soft p-5">
        <p className="flex items-start gap-2 text-sm text-warn">
          <AlertTriangle size={17} className="mt-0.5 shrink-0" />
          <span>
            <strong className="font-semibold">Not legal or financial advice.</strong>{" "}
            PlainSpeak points out wording that deserves attention and explains it in
            simpler words. It does not decide whether a clause is valid, legal or fair,
            and it can miss things or read a scan wrongly. For a decision that matters,
            check the original document and talk to a qualified lawyer or financial
            adviser.
          </span>
        </p>
      </section>
    </div>
  );
}
