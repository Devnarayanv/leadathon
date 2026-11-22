import { useRef, useState } from "react";
import { GitCompareArrows, Loader2, Upload } from "lucide-react";
import { Empty, Panel, StatusChip, ws } from "./common.jsx";
import { COMPARE_RESULT, VERIFY, EVIDENCE } from "../../labels.js";

function CheckRow({ check, language }) {
  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium">{check.label}</p>
        <StatusChip map={VERIFY} status={check.status} language={language} />
      </div>
      {check.formula && (
        <p className="mt-1 font-mono text-xs text-ink-soft">{check.formula}</p>
      )}
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
        {check.document_value != null && (
          <>
            <dt className="text-ink-faint">{ws(language, "documentValue")}</dt>
            <dd className="tabular-nums">{check.document_value}</dd>
          </>
        )}
        {check.calculated_value != null && (
          <>
            <dt className="text-ink-faint">{ws(language, "calculated")}</dt>
            <dd className="tabular-nums">{check.calculated_value}</dd>
          </>
        )}
        {check.difference != null && (
          <>
            <dt className="text-ink-faint">{ws(language, "difference")}</dt>
            <dd className="tabular-nums">{check.difference}</dd>
          </>
        )}
      </dl>
      {check.explanation && (
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">{check.explanation}</p>
      )}
      {check.source_text && (
        <p className="evidence mt-2">
          {check.page != null && `${ws(language, "page")} ${check.page} · `}
          {check.source_text}
        </p>
      )}
    </li>
  );
}

function ComparisonTable({ rows, language }) {
  if (!rows?.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] text-left text-xs">
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={`${row.label}-${index}`} className="align-top">
              <td className="py-2 pr-3 font-medium">{row.label}</td>
              <td className="py-2 pr-3 tabular-nums text-ink-soft">
                {row.left_value ?? "—"}
              </td>
              <td className="py-2 pr-3 tabular-nums text-ink-soft">
                {row.right_value ?? "—"}
              </td>
              <td className="py-2">
                <StatusChip map={COMPARE_RESULT} status={row.result} language={language} />
                {row.note && <p className="mt-1 text-ink-faint">{row.note}</p>}
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
            {report.headline && (
              <p className="text-sm leading-relaxed text-ink-soft">{report.headline}</p>
            )}
            {report.checks.length > 0 && (
              <ul className="mt-4 divide-y divide-line">
                {report.checks.map((check) => (
                  <CheckRow key={check.key} check={check} language={language} />
                ))}
              </ul>
            )}
            {report.missing_fields.length > 0 && (
              <div className="mt-4">
                <p className="label">{ws(language, "missingFields")}</p>
                <ul className="mt-1.5 list-inside list-disc text-xs text-ink-soft">
                  {report.missing_fields.map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.assumptions.length > 0 && (
              <div className="mt-4">
                <p className="label">{ws(language, "assumptions")}</p>
                <ul className="mt-1.5 list-inside list-disc text-xs text-ink-soft">
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
          <div className="overflow-x-auto">
            <table className="w-full min-w-[30rem] text-left text-xs">
              <thead className="text-ink-faint">
                <tr>
                  <th className="pb-2 font-medium">{ws(language, "description")}</th>
                  <th className="pb-2 font-medium">{ws(language, "qty")}</th>
                  <th className="pb-2 font-medium">{ws(language, "unitPrice")}</th>
                  <th className="pb-2 font-medium">{ws(language, "amount")}</th>
                  <th className="pb-2 font-medium">{ws(language, "page")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {result.line_items.map((item, index) => (
                  <tr key={index}>
                    <td className="py-2 pr-3">{item.description}</td>
                    <td className="py-2 pr-3 tabular-nums">{item.quantity ?? "—"}</td>
                    <td className="py-2 pr-3 tabular-nums">{item.unit_price ?? "—"}</td>
                    <td className="py-2 pr-3 tabular-nums">
                      {item.amount ?? "—"}
                      {item.amount_was_computed && (
                        <span className="ml-1">
                          <StatusChip map={EVIDENCE} status="calculated" language={language} />
                        </span>
                      )}
                    </td>
                    <td className="py-2 tabular-nums">{item.page ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title={ws(language, "changeType")}>
        <p className="text-xs leading-relaxed text-ink-soft">{ws(language, "changeTypeHint")}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            value={pickedType}
            onChange={(event) => setPickedType(event.target.value)}
            disabled={reclassifyBusy}
            className="rounded-lg border border-line-strong bg-surface px-2.5 py-1.5 text-xs text-ink outline-none focus:border-ink"
          >
            {options.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
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

      <Panel title={ws(language, "compareTitle")}>
        <p className="text-xs leading-relaxed text-ink-soft">{ws(language, "compareHint")}</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.txt"
          onChange={onFile}
          className="hidden"
        />
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
            <p className="flex items-center gap-1.5 text-sm font-medium">
              <GitCompareArrows size={14} />
              {compareResult.left_label} / {compareResult.right_label}
            </p>
            {compareResult.headline && (
              <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">
                {compareResult.headline}
              </p>
            )}
            {!compareResult.comparable ? (
              <Empty>{ws(language, "noCompare")}</Empty>
            ) : (
              <div className="mt-3 space-y-4">
                <ComparisonTable rows={compareResult.field_rows} language={language} />
                <ComparisonTable rows={compareResult.item_rows} language={language} />
                {compareResult.notes?.length > 0 && (
                  <ul className="list-inside list-disc text-xs text-ink-soft">
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
