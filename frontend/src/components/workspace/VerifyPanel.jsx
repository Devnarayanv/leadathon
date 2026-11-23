import { useRef, useState } from "react";
import { GitCompareArrows, Loader2, Upload } from "lucide-react";
import { Empty, Panel, SourceText, StatusChip, ws } from "./common.jsx";
import { COMPARE_RESULT, VERIFY, EVIDENCE } from "../../labels.js";
import { docTypeLabel } from "../../i18n.js";

function CheckRow({ check, language }) {
  const values = [
    ["documentValue", check.document_value],
    ["calculated", check.calculated_value],
    ["difference", check.difference],
  ].filter(([, value]) => value != null);

  return (
    <li className="py-4 first:pt-3 last:pb-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="text-[0.88rem] font-medium">{check.label}</p>
        <StatusChip map={VERIFY} status={check.status} language={language} />
      </div>
      {check.formula && (
        <p className="mt-1 font-mono text-[0.72rem] text-ink-faint">{check.formula}</p>
      )}
      {values.length > 0 && (
        <dl className="mt-2.5 flex flex-wrap gap-x-8 gap-y-2">
          {values.map(([key, value]) => (
            <div key={key}>
              <dt className="text-[0.68rem] tracking-[0.04em] uppercase text-ink-faint">
                {ws(language, key)}
              </dt>
              <dd className="mt-0.5 text-[0.85rem] font-semibold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {check.explanation && (
        <p className="mt-2 text-[0.8rem] leading-relaxed text-ink-soft">{check.explanation}</p>
      )}
      <SourceText
        className="mt-2"
        text={check.source_text}
        page={check.page}
        language={language}
      />
    </li>
  );
}

function ComparisonTable({ rows, language }) {
  if (!rows?.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] border-collapse text-left text-[0.8rem]">
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={`${row.label}-${index}`} className="align-top">
              <td className="py-2.5 pr-3 font-medium">{row.label}</td>
              <td className="py-2.5 pr-3 tabular-nums text-ink-soft">
                {row.left_value ?? "—"}
              </td>
              <td className="py-2.5 pr-3 tabular-nums text-ink-soft">
                {row.right_value ?? "—"}
              </td>
              <td className="py-2.5">
                <StatusChip map={COMPARE_RESULT} status={row.result} language={language} />
                {row.note && <p className="mt-1 text-[0.72rem] text-ink-faint">{row.note}</p>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function VerifyPanel({
  result,
  language,
  onReclassify,
  reclassifyBusy,
  onCompareFile,
  compareBusy,
  compareResult,
  compareError,
}) {
  const fileRef = useRef(null);
  const [pickedType, setPickedType] = useState(result.classification.doc_type);
  const report = result.verification;
  const options = result.doc_type_options ?? [];

  const onFile = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) onCompareFile(file);
  };

  return (
    <div className="space-y-4">
      <Panel
        title={
          report.applicable
            ? report.kind_label || ws(language, "verify")
            : ws(language, "verify")
        }
        action={
          report.applicable && <StatusChip map={VERIFY} status={report.status} language={language} />
        }
      >
        {!report.applicable ? (
          <Empty>{ws(language, "verifyNotApplicable")}</Empty>
        ) : (
          <>
            {report.headline && <p className="panel-note">{report.headline}</p>}
            {report.checks.length > 0 && (
              <ul className="mt-3 divide-y divide-line border-t border-line">
                {report.checks.map((check) => (
                  <CheckRow key={check.key} check={check} language={language} />
                ))}
              </ul>
            )}
            {report.missing_fields.length > 0 && (
              <div className="mt-4">
                <p className="label">{ws(language, "missingFields")}</p>
                <ul className="mt-1.5 list-inside list-disc text-[0.8rem] text-ink-soft">
                  {report.missing_fields.map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.assumptions.length > 0 && (
              <div className="mt-4">
                <p className="label">{ws(language, "assumptions")}</p>
                <ul className="mt-1.5 list-inside list-disc text-[0.8rem] text-ink-soft">
                  {report.assumptions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </Panel>

      <Panel title={ws(language, "lineItems")}>
        {result.line_items.length === 0 ? (
          <Empty>{ws(language, "noLineItems")}</Empty>
        ) : (
          <div className="-mx-1 overflow-x-auto">
            <table className="w-full min-w-[30rem] border-collapse text-left text-[0.8rem]">
              <thead className="border-b border-line">
                <tr className="text-[0.68rem] tracking-[0.05em] uppercase text-ink-faint">
                  <th className="pb-2 pr-3 font-medium">{ws(language, "description")}</th>
                  <th className="pb-2 pr-3 text-right font-medium">{ws(language, "qty")}</th>
                  <th className="pb-2 pr-3 text-right font-medium">{ws(language, "unitPrice")}</th>
                  <th className="pb-2 pr-3 text-right font-medium">{ws(language, "amount")}</th>
                  <th className="pb-2 text-right font-medium">{ws(language, "page")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {result.line_items.map((item, index) => (
                  <tr key={index}>
                    <td className="py-2.5 pr-3">{item.description}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{item.quantity ?? "—"}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{item.unit_price ?? "—"}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">
                      {item.amount ?? "—"}
                      {item.amount_was_computed && (
                        <StatusChip
                          className="ml-1.5"
                          map={EVIDENCE}
                          status="calculated"
                          language={language}
                        />
                      )}
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-ink-soft">{item.page ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title={ws(language, "changeType")}>
        <p className="panel-note">{ws(language, "changeTypeHint")}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            value={pickedType}
            onChange={(event) => setPickedType(event.target.value)}
            disabled={reclassifyBusy}
            className="field !w-auto !py-1.5 text-[0.8rem]"
          >
            {options.map((option) => (
              <option key={option.key} value={option.key}>
                {docTypeLabel(option.key, option.label, language)}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn-secondary text-xs"
            disabled={reclassifyBusy || pickedType === result.classification.doc_type}
            onClick={() => onReclassify(pickedType)}
          >
            {reclassifyBusy && <Loader2 size={13} className="animate-spin" />}
            {reclassifyBusy ? ws(language, "reclassifyBusy") : ws(language, "changeType")}
          </button>
        </div>
      </Panel>

      <Panel
        title={ws(language, "compareTitle")}
        action={
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.txt"
            onChange={onFile}
            className="hidden"
          />
        }
      >
        <p className="panel-note">{ws(language, "compareHint")}</p>
        <button
          type="button"
          className="btn-secondary mt-3 text-xs"
          disabled={compareBusy}
          onClick={() => fileRef.current?.click()}
        >
          {compareBusy ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
          {compareBusy ? ws(language, "compareBusy") : ws(language, "compareTitle")}
        </button>

        {compareError && (
          <p className="mt-3 rounded-lg bg-crit-soft px-3 py-2.5 text-sm text-crit">
            {compareError}
          </p>
        )}

        {compareResult && (
          <div className="mt-4 border-t border-line pt-4">
            <p className="flex items-center gap-1.5 text-[0.85rem] font-medium">
              <GitCompareArrows size={14} className="text-ink-faint" />
              {compareResult.left_label} / {compareResult.right_label}
            </p>
            {compareResult.headline && (
              <p className="mt-1 text-[0.8rem] leading-relaxed text-ink-soft">
                {compareResult.headline}
              </p>
            )}
            {!compareResult.comparable ? (
              <div className="mt-2">
                <Empty>{ws(language, "noCompare")}</Empty>
              </div>
            ) : (
              <div className="mt-3 space-y-4">
                <ComparisonTable rows={compareResult.field_rows} language={language} />
                <ComparisonTable rows={compareResult.item_rows} language={language} />
                {compareResult.notes?.length > 0 && (
                  <ul className="list-inside list-disc text-[0.78rem] text-ink-soft">
                    {compareResult.notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
