import { ShieldCheck, X } from "lucide-react";

const POINTS = [
  [
    "Where your document goes",
    "The file is uploaded to the Doc Decode backend running on this machine, held in memory for the length of that one request, and dropped when the request ends. This app does not write your document to disk.",
  ],
  [
    "Where the AI runs",
    "Explanations come from an Ollama model on your own machine, reached over localhost. No OpenAI, Gemini, Groq or other cloud AI service is used, and no API key exists in this project.",
  ],
  [
    "What is stored",
    "Nothing is stored between requests. There is no database and no document history. Reloading the page loses the analysis, which is deliberate.",
  ],
  [
    "Logging",
    "The server logs the filename, page count, character count and timings. Document text is not logged.",
  ],
  [
    "OCR",
    "Scans and photos are processed by Tesseract on this machine. Nothing is sent to an online OCR service.",
  ],
  [
    "Google Calendar",
    "Sending a deadline to Google Calendar is the only feature that leaves your machine, and it only happens when you click that button. Google receives the date, the short description and the file name. The quoted clause text is never put in the link. Downloading the .ics file instead keeps everything local.",
  ],
  [
    "Audio",
    "Speech uses your browser's own voices first. Windows ships no Malayalam voice, so when none is found Doc Decode falls back to eSpeak NG running locally on this machine rather than reading Malayalam in an English voice. If eSpeak NG is not installed, the Read aloud button is disabled for that language instead of speaking the wrong one. Install it with: winget install eSpeak-NG.eSpeak-NG",
  ],
  [
    "A note on browser voices",
    "Some browsers (notably Edge) offer 'Online (Natural)' voices that send the text to the vendor's servers to be spoken. Doc Decode cannot tell these apart from local ones, so if that matters to you, pick a local voice in the voice selector or rely on the offline engine.",
  ],
  [
    "What this is not",
    "This is a hackathon MVP. It has no authentication, no encryption at rest and no hardening. Do not expose it to a network you do not trust, and do not treat it as a secure document store.",
  ],
];

export default function PrivacyPanel({ open, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-ink/30 p-0 sm:items-center sm:p-4">
      <div className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-t-2xl border border-line bg-surface p-5 sm:rounded-[var(--radius-card)] ">
        <div className="flex items-start justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <ShieldCheck size={18} className="text-good" />
            Privacy and processing
          </h2>
          <button type="button" onClick={onClose} className="btn-ghost !p-1.5">
            <X size={16} />
          </button>
        </div>

        <dl className="mt-4 space-y-3.5">
          {POINTS.map(([title, body]) => (
            <div key={title}>
              <dt className="text-sm font-medium">{title}</dt>
              <dd className="mt-0.5 text-xs leading-relaxed text-ink-soft">{body}</dd>
            </div>
          ))}
        </dl>

        <button type="button" onClick={onClose} className="btn-primary mt-5 w-full">
          Close
        </button>
      </div>
    </div>
  );
}
