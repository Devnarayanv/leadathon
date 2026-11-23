import { useState } from "react";
import { Check, X } from "lucide-react";
import { Empty, Panel, SourceText, StatusChip, ws } from "./common.jsx";
import EligibilityForm from "./EligibilityForm.jsx";
import { TENDER_STATUS } from "../../labels.js";

const KIND_LABEL = {
  eligibility: { en: "Eligibility", ml: "യോഗ്യത" },
  document: { en: "Document", ml: "രേഖ" },
  financial: { en: "Financial", ml: "സാമ്പത്തികം" },
  technical: { en: "Technical", ml: "സാങ്കേതികം" },
};

// "Rs. 50,00,000 (mandatory)." and "the bidder must hold a valid ISO 9001
// (mandatory)" are the same sentence in the tender. Compare on words only so
// the row never repeats itself three times.
function fingerprint(text) {
  return (text ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9\u0d00-\u0d7f]+/g, " ")
    .trim();
}

function kindLabel(req, language) {
  return KIND_LABEL[req.kind]?.[language] ?? KIND_LABEL[req.kind]?.en ?? req.kind;
}

// Checklist only. Each row starts as "not assessed yet"; the user moves it to
// meets / does-not-meet after checking their own papers. Doc Decode never
// marks a bidder as eligible.
export default function TenderPanel({ requirements, language }) {
  const [marks, setMarks] = useState({});

  if (!requirements?.length) {
    return (
      <Panel title={ws(language, "tender")}>
        <Empty>{ws(language, "noRequirements")}</Empty>
      </Panel>
    );
  }

  const setMark = (index, status) =>
    setMarks((current) => ({
      ...current,
      [index]: current[index] === status ? "not_assessed" : status,
    }));

  const total = requirements.length;
  const assessed = Object.values(marks).filter((value) => value && value !== "not_assessed").length;

  return (
    <div className="space-y-4">
      <Panel
        title={ws(language, "tender")}
        action={
          <span className="text-[0.72rem] font-medium tabular-nums text-ink-faint">
            {assessed} / {total} {ws(language, "assessed")}
          </span>
        }
      >
        <p className="panel-note">{ws(language, "tenderIntro")}</p>

        <div className="mt-4 h-1 w-full overflow-hidden rounded-full bg-sunken">
          <div
            className="h-full rounded-full bg-ink transition-[width] duration-300"
            style={{ width: `${total ? (assessed / total) * 100 : 0}%` }}
          />
        </div>

        <ul className="mt-5 divide-y divide-line border-y border-line">
          {requirements.map((req, index) => {
            const status = marks[index] ?? "not_assessed";
            const labelKey = fingerprint(req.label);
            const showDescription =
              req.description && fingerprint(req.description) !== labelKey;
            const showSource =
              req.source_text && fingerprint(req.source_text) !== labelKey;

            return (
              <li key={`${req.label}-${index}`} className="py-4 first:pt-3.5 last:pb-3.5">
                <div className="flex items-start gap-3.5">
                  <span className="mt-[0.15rem] w-5 shrink-0 text-[0.72rem] font-medium tabular-nums text-ink-faint">
                    {String(index + 1).padStart(2, "0")}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                      <span className="eyebrow">{kindLabel(req, language)}</span>
                      <span aria-hidden="true" className="h-3 w-px bg-line-strong" />
                      <span className="text-[0.72rem] text-ink-faint">
                        {req.mandatory === true
                          ? ws(language, "mandatory")
                          : ws(language, "optional")}
                      </span>
                      <span className="ml-auto">
                        <StatusChip map={TENDER_STATUS} status={status} language={language} />
                      </span>
                    </div>

                    <p className="mt-1.5 text-[0.88rem] leading-relaxed font-medium">
                      {req.label}
                    </p>
                    {showDescription && (
                      <p className="mt-1 text-[0.82rem] leading-relaxed text-ink-soft">
                        {req.description}
                      </p>
                    )}
                    {showSource && (
                      <SourceText
                        className="mt-2"
                        text={req.source_text}
                        page={req.page}
                        language={language}
                      />
                    )}

                    <div className="mt-3 flex flex-wrap items-center gap-2.5">
                      <div className="seg" role="group" aria-label={req.label}>
                        <button
                          type="button"
                          className="seg-item"
                          data-tone="good"
                          data-active={status === "meets"}
                          aria-pressed={status === "meets"}
                          onClick={() => setMark(index, "meets")}
                        >
                          {status === "meets" && <Check size={12} />}
                          {ws(language, "meetsShort")}
                        </button>
                        <button
                          type="button"
                          className="seg-item"
                          data-tone="crit"
                          data-active={status === "does_not_meet"}
                          aria-pressed={status === "does_not_meet"}
                          onClick={() => setMark(index, "does_not_meet")}
                        >
                          {status === "does_not_meet" && <X size={12} />}
                          {ws(language, "doesNotMeetShort")}
                        </button>
                      </div>
                      {status !== "not_assessed" && (
                        <button
                          type="button"
                          onClick={() =>
                            setMarks((current) => ({ ...current, [index]: "not_assessed" }))
                          }
                          className="text-[0.72rem] text-ink-faint underline underline-offset-2 transition-colors hover:text-ink"
                        >
                          {ws(language, "clearMark")}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </Panel>

      <EligibilityForm requirements={requirements} />
    </div>
  );
}
