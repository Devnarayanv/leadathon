import { useState } from "react";
import { CornerDownLeft, Cpu, Loader2, Ruler, SearchX } from "lucide-react";
import { t } from "../i18n.js";
import { askDocument } from "../services/api.js";
import AudioControls from "./AudioControls.jsx";

const SUGGESTIONS = {
  rental_agreement: [
    "What happens if I terminate this agreement early?",
    "What is the notice period?",
    "How much deposit is mentioned?",
    "What are the extra charges?",
  ],
  loan_agreement: [
    "What is the interest rate?",
    "What happens if I miss an instalment?",
    "What does it cost to repay early?",
    "How many instalments are there?",
  ],
  hospital_bill: [
    "How much do I have to pay?",
    "When is the payment due?",
    "What are the biggest charges?",
    "What happens if I pay late?",
  ],
  government_notice: [
    "What am I being asked to do?",
    "What is the last date to reply?",
    "What happens if I do not reply?",
    "How much is demanded?",
  ],
  other: [
    "What are the main amounts in this document?",
    "What are the important dates?",
    "What do I have to do?",
  ],
};

export default function AskDocument({ result, language, speech }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const suggestions = SUGGESTIONS[result.classification.doc_type] ?? SUGGESTIONS.other;

  const submit = async (text) => {
    const asked = (text ?? question).trim();
    if (asked.length < 2 || busy) return;
    setQuestion(asked);
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      const response = await askDocument({
        question: asked,
        segments: result.segments,
        docType: result.classification.doc_type,
        language,
      });
      setAnswer(response);
    } catch (exception) {
      setError(exception.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section id="ask" className="card scroll-mt-24 p-5 sm:p-6">
      <h2 className="text-[1.02rem] leading-tight font-semibold tracking-[-0.02em]">
        {t(language, "askTitle")}
      </h2>
      <p className="panel-note mt-2">
        Answers come only from your document&rsquo;s text. If it is not in there, the
        answer says so.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="mt-4 flex flex-col gap-2 sm:flex-row"
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={t(language, "askPlaceholder")}
          maxLength={500}
          className="field flex-1"
        />
        <button type="submit" disabled={busy || question.trim().length < 2} className="btn-primary">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <CornerDownLeft size={15} />}
          {t(language, "ask")}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {suggestions.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => submit(item)}
            disabled={busy}
            className="chip border border-line bg-surface text-ink-soft transition-colors hover:border-line-strong hover:text-ink"
          >
            {item}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-crit">{error}</p>}

      {answer && (
        <div className="mt-4 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-2">
            {answer.grounded ? (
              <span className="chip bg-good-soft text-good">
                {answer.source === "llm" ? <Cpu size={11} /> : <Ruler size={11} />}
                {answer.source === "llm"
                  ? t(language, "bySource").llm
                  : t(language, "bySource").rules}
              </span>
            ) : (
              <span className="chip bg-warn-soft text-warn">
                <SearchX size={11} />
                not found in document
              </span>
            )}
            <div className="ml-auto">
              <AudioControls
                id="answer"
                text={answer.answer}
                language={language}
                speech={speech}
                label={t(language, "play")}
                stopLabel={t(language, "stop")}
                compact
              />
            </div>
          </div>

          <p className={`prose-plain mt-3 ${language === "ml" ? "lang-ml" : ""}`}>
            {answer.answer}
          </p>

          {answer.evidence?.length > 0 && (
            <div className="mt-4">
              <p className="label">{t(language, "evidence")}</p>
              <ul className="mt-2 space-y-2">
                {answer.evidence.map((item, index) => (
                  <li key={`${item.page}-${index}`}>
                    <p className="evidence">{item.text}</p>
                    {item.page != null && (
                      <p className="mt-1 text-[0.7rem] text-ink-faint">
                        {t(language, "page")} {item.page}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
