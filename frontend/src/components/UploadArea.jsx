import { useCallback, useRef, useState } from "react";
import { AlertCircle, FileUp, Loader2, Sparkles, Trash2, Upload } from "lucide-react";

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
        return `Only PDF, JPG, JPEG and PNG files are accepted. You picked ${
          extensionOf(candidate.name) || "a file with no extension"
        }.`;
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

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    if (busy) return;
    accept(event.dataTransfer.files?.[0]);
  };

  const clear = () => {
    setFile(null);
    setLocalError("");
    onClearError?.();
    if (inputRef.current) inputRef.current.value = "";
  };

  const shownError = localError || error;

  return (
    <div className="card p-5 sm:p-6">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`rounded-xl border-2 border-dashed px-5 py-10 text-center transition-colors ${
          dragging ? "border-brand bg-brand-soft" : "border-line bg-canvas"
        } ${busy ? "opacity-60" : ""}`}
      >
        <span className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-surface text-brand ring-1 ring-line">
          <FileUp size={22} />
        </span>
        <p className="text-sm font-medium">Drag a document here</p>
        <p className="mt-1 text-xs text-ink-soft">
          PDF, JPG or PNG &middot; up to {maxUploadMb} MB &middot; processed on this machine
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="btn-secondary mt-4"
        >
          <Upload size={16} />
          Choose a file
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          className="hidden"
          onChange={(event) => accept(event.target.files?.[0])}
        />
      </div>

      {file && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-line bg-surface px-3.5 py-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand-ink">
            <FileUp size={16} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-ink-soft">
              {formatSize(file.size)} &middot; {extensionOf(file.name).replace(".", "").toUpperCase()}
            </p>
          </div>
          <button
            type="button"
            onClick={clear}
            disabled={busy}
            className="btn-ghost !px-2"
            title="Remove file"
          >
            <Trash2 size={16} />
          </button>
        </div>
      )}

      {shownError && (
        <p className="mt-3 flex items-start gap-2 rounded-lg bg-crit-soft px-3.5 py-3 text-sm text-crit">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{shownError}</span>
        </p>
      )}

      <button
        type="button"
        onClick={() => file && onAnalyse(file)}
        disabled={!file || busy}
        className="btn-primary mt-4 w-full"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
        {busy ? "Analysing..." : "Analyse this document"}
      </button>
    </div>
  );
}
