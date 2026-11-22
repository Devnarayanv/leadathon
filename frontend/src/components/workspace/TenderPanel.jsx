import { useState } from "react";
import { Check } from "lucide-react";
import { Empty, Panel, StatusChip, ws } from "./common.jsx";
import EligibilityForm from "./EligibilityForm.jsx";
import { TENDER_STATUS } from "../../labels.js";

const KIND_LABEL = {
  eligibility: { en: "Eligibility", ml: "യോഗ്യത" },
  document: { en: "Document", ml: "രേഖ" },
  financial: { en: "Financial", ml: "സാമ്പത്തികം" },
  technical: { en: "Technical", ml: "സാങ്കേതികം" },
};

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

  return (
    <Panel title={ws(language, "tender")}>
      <p className="text-xs leading-relaxed text-ink-soft">{ws(language, "tenderIntro")}</p>
      <ul className="mt-4 divide-y divide-line">
        {requirements.map((req, index) => {
          const status = marks[index] ?? "not_assessed";
          return (
            <li key={`${req.label}-${index}`} className="py-3.5 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="chip bg-canvas text-ink-soft">
                  {KIND_LABEL[req.kind]?.[language] ?? KIND_LABEL[req.kind]?.en ?? req.kind}
                </span>
                <span className="text-[0.7rem] text-ink-faint">
                  {req.mandatory === true
                    ? ws(language, "mandatory")
                    : ws(language, "optional")}
                </span>
                <StatusChip map={TENDER_STATUS} status={status} language={language} />
              </div>
              <p className="mt-2 text-sm font-medium">{req.label}</p>
              {req.description && (
                <p className="mt-1 text-xs leading-relaxed text-ink-soft">{req.description}</p>
              )}
              {req.source_text && (
                <p className="evidence mt-2">
                  {req.page != null && `${ws(language, "page")} ${req.page} · `}
                  {req.source_text}
                </p>
              )}
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setMark(index, "meets")}
                  aria-pressed={status === "meets"}
                  className="btn-secondary !px-2.5 !py-1 text-xs"
                >
                  {status === "meets" && <Check size={12} />}
                  {TENDER_STATUS.meets[language] ?? TENDER_STATUS.meets.en}
                </button>
                <button
                  type="button"
                  onClick={() => setMark(index, "does_not_meet")}
                  aria-pressed={status === "does_not_meet"}
                  className="btn-secondary !px-2.5 !py-1 text-xs"
                >
                  {TENDER_STATUS.does_not_meet[language] ?? TENDER_STATUS.does_not_meet.en}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <EligibilityForm requirements={requirements} />
    </Panel>
  );
}
