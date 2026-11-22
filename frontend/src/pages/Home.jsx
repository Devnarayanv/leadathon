import { CalendarClock, FileSearch, Languages, Lock } from "lucide-react";
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
    body: "Every amount, date and flagged clause carries the original sentence and its page number.",
  },
  {
    icon: Languages,
    title: "English or Malayalam",
    body: "Clauses are rewritten in plain words by a model running on this machine. The original wording is never altered.",
  },
  {
    icon: CalendarClock,
    title: "Deadlines you confirm",
    body: "Tick the dates you have checked, then send them to Google Calendar or download a reminder file.",
  },
];

const STEPS = [
  "Read the text, using OCR only for pages that need it",
  "Pull out amounts, dates and clauses worth a second look",
  "Rewrite those clauses in plain language, locally",
  "Show each one beside the original text",
];

export default function Home({ onAnalyse, busy, maxUploadMb, error, onClearError, aiEnabled }) {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16">
      <div className="mx-auto max-w-xl text-center">
        <span className="chip bg-canvas text-ink-soft">
          <Lock size={12} />
          Runs on your machine
        </span>
        <h1 className="mt-4 text-3xl leading-[1.15] font-semibold tracking-tight sm:text-4xl">
          Understand before you sign.
        </h1>
        <p className="mx-auto mt-3 max-w-lg text-[0.95rem] leading-relaxed text-ink-soft">
          Upload a rental agreement, loan agreement, hospital bill or government
          notice. PlainSpeak shows the amounts and dates it contains, the sentences
          worth a second look, and what each one means in plain words.
        </p>
      </div>

      <div className="mx-auto mt-8 max-w-xl">
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

        <div className="mt-3 flex flex-wrap justify-center gap-1.5">
          {DOC_TYPES.map((type) => (
            <span key={type} className="chip bg-canvas text-ink-faint">
              {type}
            </span>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-14 grid max-w-3xl gap-8 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <div key={title}>
            <Icon size={17} className="text-ink-faint" />
            <h3 className="mt-2.5 text-sm font-semibold">{title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-ink-soft">{body}</p>
          </div>
        ))}
      </div>

      <div className="mx-auto mt-14 max-w-3xl border-t border-line pt-8">
        <h2 className="label">How it works</h2>
        <ol className="mt-3 grid gap-x-8 gap-y-2 sm:grid-cols-2">
          {STEPS.map((step, index) => (
            <li
              key={step}
              className="flex gap-2.5 text-xs leading-relaxed text-ink-soft"
            >
              <span className="tabular-nums text-ink-faint">{index + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      <div className="mx-auto mt-10 max-w-3xl space-y-2 border-t border-line pt-8 text-xs leading-relaxed text-ink-faint">
        <p>
          <strong className="font-medium text-ink-soft">Privacy.</strong> The file
          is held in memory for one request and never written to disk. Its text
          goes only to the Ollama model on your own machine. No cloud AI service is
          used. Sending a deadline to Google Calendar is the one action that leaves
          your machine, and it is always your click.
        </p>
        <p>
          <strong className="font-medium text-ink-soft">Not legal advice.</strong>{" "}
          PlainSpeak points out wording that deserves attention and explains it in
          simpler words. It does not decide whether a clause is valid, legal or
          fair, and it can miss things. For a decision that matters, read the
          original and talk to a qualified professional.
        </p>
      </div>
    </div>
  );
}
