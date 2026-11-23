import { useCallback, useRef, useState } from "react";
import { AlertCircle, ArrowRight, FileText, Loader2, Upload, X } from "lucide-react";

const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png"];
const ACCEPT_ATTR = "application/pdf,image/jpeg,image/png";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function extensionOf(name) {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot).toLowerCase();
}

export default function UploadArea({
  onAnalyse,
  busy,
  maxUploadMb = 15,
  error,
  onClearError,
}) {
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState("");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const validate = useCallback(
    (candidate) => {
      if (!ACCEPTED.includes(extensionOf(candidate.name))) {
        return `Only PDF, JPG and PNG files are accepted.`;
      }
      if (candidate.size === 0) return "That file is empty.";
      if (candidate.size > maxUploadMb * 1024 * 1024) {
        return `That file is ${formatSize(candidate.size)}. The limit is ${maxUploadMb} MB.`;
      }
      return "";
    },
    [maxUploadMb],
  );

  const accept = useCallback(
    (candidate) => {
      if (!candidate) return;
      const message = validate(candidate);
      setLocalError(message);
      onClearError?.();
      setFile(message ? null : candidate);
    },
    [validate, onClearError],
  );

  const clear = () => {
    setFile(null);
    setLocalError("");
    onClearError?.();
    if (inputRef.current) inputRef.current.value = "";
  };

  const shownError = localError || error;

  return (
    <div className="card p-3 sm:p-4">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!busy) accept(event.dataTransfer.files?.[0]);
        }}
        onClick={() => !file && inputRef.current?.click()}
        onKeyDown={(event) => {
          if (!file && (event.key === "Enter" || event.key === " ")) {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={file ? -1 : 0}
        aria-label="Choose a document to analyse"
        className={`group rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors sm:py-16 ${
          dragging
            ? "border-brand bg-brand-soft"
            : "border-line-strong bg-sunken hover:border-ink-faint"
        } ${file ? "" : "cursor-pointer"} ${busy ? "opacity-60" : ""}`}
      >
        <span
          className={`mx-auto grid h-14 w-14 place-items-center rounded-full transition-transform duration-200 group-hover:-translate-y-0.5 ${
            dragging ? "bg-brand text-on-ink" : "bg-ink text-on-ink"
          }`}
        >
          <Upload size={22} />
        </span>
        <p className="mt-5 text-base font-semibold">
          {dragging ? "Drop it here" : "Drop a document, or click to choose"}
        </p>
        <p className="mt-1.5 text-[0.82rem] text-ink-faint">
          PDF, JPG or PNG · up to {maxUploadMb} MB · processed on this machine
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          className="hidden"
          onChange={(event) => accept(event.target.files?.[0])}
        />
      </div>

      {file && (
        <div className="mt-3 flex items-center gap-3 rounded-xl bg-sunken px-4 py-3">
          <FileText size={18} className="shrink-0 text-ink-soft" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-ink-faint">{formatSize(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={clear}
            disabled={busy}
            className="btn-ghost !px-2 !py-2"
            title="Remove file"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {shownError && (
        <p className="mt-3 flex items-start gap-2 rounded-xl bg-crit-soft px-4 py-3 text-sm text-crit">
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          <span>{shownError}</span>
        </p>
      )}

      <button
        type="button"
        onClick={() => file && onAnalyse(file)}
        disabled={!file || busy}
        className="btn-accent mt-3 w-full !py-3 text-[0.95rem]"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : null}
        {busy ? "Analysing..." : "Analyse document"}
        {!busy && <ArrowRight size={16} />}
      </button>
    </div>
  );
}
