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
    <div className="card p-3">
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
        className={`group rounded-lg border border-dashed px-6 py-10 text-center transition-colors sm:py-12 ${
          dragging
            ? "border-brand bg-brand-soft"
            : "border-line-strong bg-sunken hover:border-ink-faint"
        } ${file ? "" : "cursor-pointer"} ${busy ? "opacity-60" : ""}`}
      >
        <span
          className={`mx-auto grid h-11 w-11 place-items-center rounded-lg transition-colors ${
            dragging ? "bg-brand text-on-ink" : "border border-line bg-surface text-ink-soft group-hover:text-ink"
          }`}
        >
          <Upload size={18} />
        </span>
        <p className="mt-4 text-[0.9rem] font-medium">
          {dragging ? "Drop it here" : "Drop a document, or click to choose"}
        </p>
        <p className="mt-1 text-[0.78rem] text-ink-faint">
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
        <div className="mt-2.5 flex items-center gap-3 rounded-lg border border-line px-3.5 py-2.5">
          <FileText size={16} className="shrink-0 text-ink-soft" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[0.82rem] font-medium">{file.name}</p>
            <p className="text-[0.72rem] text-ink-faint">{formatSize(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={clear}
            disabled={busy}
            className="btn-ghost !px-1.5 !py-1.5"
            title="Remove file"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {shownError && (
        <p className="mt-2.5 flex items-start gap-2 rounded-lg bg-crit-soft px-3.5 py-2.5 text-[0.82rem] text-crit">
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>{shownError}</span>
        </p>
      )}

      <button
        type="button"
        onClick={() => file && onAnalyse(file)}
        disabled={!file || busy}
        className="btn-accent mt-2.5 w-full !py-2.5"
      >
        {busy ? <Loader2 size={15} className="animate-spin" /> : null}
        {busy ? "Analysing..." : "Analyse document"}
        {!busy && <ArrowRight size={15} />}
      </button>
    </div>
  );
}
