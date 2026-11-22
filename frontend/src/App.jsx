import { useCallback, useEffect, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import PrivacyPanel from "./components/PrivacyPanel.jsx";
import Home from "./pages/Home.jsx";
import Analysis from "./pages/Analysis.jsx";
import { useSpeech } from "./components/AudioControls.jsx";
import { analyzeDocument, explainClauses, getHealth } from "./services/api.js";

export default function App() {
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [language, setLanguage] = useState("en");
  const [busy, setBusy] = useState(false);
  const [languageBusy, setLanguageBusy] = useState(false);
  const [retryBusy, setRetryBusy] = useState(false);
  const [error, setError] = useState("");
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [lastFile, setLastFile] = useState(null);
  // Health reports whether the offline engine can cover languages the
  // browser has no voice for.
  const speech = useSpeech({
    available: Boolean(health?.tts?.available),
    malayalam: Boolean(health?.tts?.malayalam),
  });

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await getHealth());
    } catch {
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  const aiReady = Boolean(health?.ollama?.reachable && health?.ollama?.model_available);

  const onAnalyse = async (file) => {
    setBusy(true);
    setError("");
    speech.stop();
    try {
      const analysis = await analyzeDocument({ file, language });
      setResult(analysis);
      setLastFile(file);
      // The analysis response carries fresh Ollama state; keep the badge honest.
      setHealth((current) =>
        current ? { ...current, ollama: analysis.ollama } : current,
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (exception) {
      setError(
        exception.message === "Failed to fetch"
          ? "The backend is not reachable. Start it with: uvicorn main:app --reload (inside the backend folder)."
          : exception.message,
      );
    } finally {
      setBusy(false);
    }
  };

  // Language switch and AI retry both re-explain the clauses the backend
  // already detected. No re-upload, no re-extraction.
  const reExplain = async (nextLanguage) => {
    if (!result?.clauses?.length) {
      setLanguage(nextLanguage);
      return;
    }
    try {
      const response = await explainClauses({
        clauses: result.clauses,
        docType: result.classification.doc_type,
        language: nextLanguage,
      });
      setResult((current) => ({
        ...current,
        clauses: response.clauses,
        summary: response.summary || current.summary,
        summary_source: response.summary_source,
        language: nextLanguage,
        ollama: response.ollama,
        warnings: response.warnings,
      }));
      setHealth((current) =>
        current ? { ...current, ollama: response.ollama } : current,
      );
    } catch (exception) {
      setResult((current) =>
        current
          ? { ...current, warnings: [...(current.warnings ?? []), exception.message] }
          : current,
      );
    }
    setLanguage(nextLanguage);
  };

  const onLanguageChange = async (nextLanguage) => {
    if (nextLanguage === language || languageBusy) return;
    speech.stop();
    setLanguageBusy(true);
    await reExplain(nextLanguage);
    setLanguageBusy(false);
  };

  const onRetryAi = async () => {
    if (retryBusy) return;
    setRetryBusy(true);
    await refreshHealth();
    await reExplain(language);
    setRetryBusy(false);
  };

  const onNew = () => {
    speech.stop();
    setResult(null);
    setError("");
    setLastFile(null);
    refreshHealth();
    window.scrollTo({ top: 0 });
  };

  return (
    <div className="min-h-dvh">
      <Navbar
        onNew={onNew}
        onPrivacy={() => setPrivacyOpen(true)}
        health={health}
        onRefreshHealth={refreshHealth}
        showNew={Boolean(result)}
      />

      {result ? (
        <Analysis
          result={result}
          language={language}
          onLanguageChange={onLanguageChange}
          languageBusy={languageBusy}
          speech={speech}
          onRetryAi={onRetryAi}
          retryBusy={retryBusy}
          malayalamModel={health?.ollama_malayalam?.model}
        />
      ) : (
        <Home
          onAnalyse={onAnalyse}
          busy={busy}
          maxUploadMb={health?.limits?.max_upload_mb ?? 15}
          error={error}
          onClearError={() => setError("")}
          aiEnabled={aiReady}
        />
      )}

      <footer className="border-t border-line py-6 text-center text-xs text-ink-soft">
        PlainSpeak &middot; local document understanding &middot; attention indicators,
        not legal advice
        {lastFile && <span className="ml-1">&middot; analysed locally</span>}
      </footer>

      <PrivacyPanel open={privacyOpen} onClose={() => setPrivacyOpen(false)} />
    </div>
  );
}
