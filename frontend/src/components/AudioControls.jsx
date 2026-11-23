import { useEffect, useMemo, useRef, useState } from "react";
import { Square, Volume2 } from "lucide-react";
import { speakUrl } from "../services/api.js";
import { t } from "../i18n.js";

// Speech comes from the browser's own voices first. Windows ships no Malayalam
// voice, so when none is found the backend's offline eSpeak NG engine is used
// instead of quietly reading Malayalam text in an English voice.
const synth = typeof window !== "undefined" ? window.speechSynthesis : null;

function normaliseLang(lang) {
  return (lang || "").toLowerCase().replace("_", "-");
}

function useVoices() {
  const [voices, setVoices] = useState(() => synth?.getVoices() ?? []);
  useEffect(() => {
    if (!synth) return undefined;
    const update = () => setVoices(synth.getVoices());
    update();
    synth.addEventListener?.("voiceschanged", update);
    // Some browsers populate the list late and never fire the event.
    const retry = setTimeout(update, 400);
    return () => {
      clearTimeout(retry);
      synth.removeEventListener?.("voiceschanged", update);
    };
  }, []);
  return voices;
}

export function useSpeech(serverTts = { available: false, malayalam: false }) {
  const voices = useVoices();
  const [speakingId, setSpeakingId] = useState(null);
  const [chosenVoice, setChosenVoice] = useState("");
  const [error, setError] = useState("");
  const audioRef = useRef(null);
  // The server's WAV arrives as a blob, so its object URL has to be released
  // explicitly or every spoken clause leaks one for the life of the page.
  const audioUrlRef = useRef(null);

  const releaseAudioUrl = () => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  const stop = () => {
    synth?.cancel();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    releaseAudioUrl();
    setSpeakingId(null);
  };

  useEffect(() => () => stop(), []);

  const voicesFor = (language) => {
    const prefix = language === "ml" ? "ml" : "en";
    return voices.filter((voice) => normaliseLang(voice.lang).startsWith(prefix));
  };

  const pickVoice = (language) => {
    if (chosenVoice) {
      const exact = voices.find((voice) => voice.voiceURI === chosenVoice);
      if (exact) return exact;
    }
    const matching = voicesFor(language);
    if (matching.length) {
      const preferred = language === "ml" ? ["ml-in"] : ["en-in", "en-gb", "en-us"];
      for (const tag of preferred) {
        const hit = matching.find((voice) => normaliseLang(voice.lang).startsWith(tag));
        if (hit) return hit;
      }
      return matching[0];
    }
    return null;
  };

  const hasVoiceFor = (language) => Boolean(pickVoice(language));

  // True when this language can be spoken at all, by browser or by server.
  const canSpeak = (language) =>
    hasVoiceFor(language) ||
    (serverTts.available && (language !== "ml" || serverTts.malayalam));

  const speakViaServer = async (id, text, language) => {
    try {
      const response = await fetch(speakUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.slice(0, 1200), language }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Local speech engine unavailable.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        setSpeakingId(null);
        releaseAudioUrl();
      };
      audio.onerror = () => {
        setError("The audio could not be played.");
        setSpeakingId(null);
        releaseAudioUrl();
      };
      setSpeakingId(id);
      await audio.play();
    } catch (exception) {
      setError(exception.message);
      setSpeakingId(null);
    }
  };

  const speak = (id, text, language) => {
    if (!text?.trim()) return;
    stop();
    setError("");

    const voice = pickVoice(language);
    if (!voice) {
      // No browser voice for this language: use the local engine rather than
      // reading it aloud in the wrong language.
      speakViaServer(id, text, language);
      return;
    }
    if (!synth) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = 0.95;
    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = (event) => {
      if (event.error !== "interrupted" && event.error !== "canceled") {
        setError("The browser could not speak this text.");
      }
      setSpeakingId(null);
    };
    setSpeakingId(id);
    synth.speak(utterance);
  };

  return {
    supported: Boolean(synth) || serverTts.available,
    voices,
    voicesFor,
    chosenVoice,
    setChosenVoice,
    speakingId,
    speak,
    stop,
    hasVoiceFor,
    canSpeak,
    serverTts,
    error,
  };
}

export default function AudioControls({
  id,
  text,
  language,
  speech,
  label = "Read aloud",
  stopLabel = "Stop",
  compact = false,
}) {
  const active = speech.speakingId === id;
  const browserVoice = useMemo(
    () => speech.hasVoiceFor(language),
    [language, speech],
  );
  const usable = speech.canSpeak(language);

  if (!speech.supported) {
    return (
      <span className="text-[0.7rem] text-ink-faint">
        {t(language, "browserNoSpeech")}
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={() => (active ? speech.stop() : speech.speak(id, text, language))}
        className={`btn-secondary ${compact ? "!px-2.5 !py-1.5" : ""} text-xs`}
        disabled={!text?.trim() || !usable}
        title={usable ? undefined : t(language, "noVoice")}
      >
        {active ? <Square size={12} /> : <Volume2 size={13} />}
        {active ? stopLabel : label}
      </button>

      {!browserVoice && usable && (
        <span className="text-[0.7rem] text-ink-faint">{t(language, "offlineVoice")}</span>
      )}

      {!usable && (
        <span className="text-[0.7rem] text-warn">
          {t(language, "noVoiceShort").replace(
            "%s",
            language === "ml" ? "മലയാളം" : "English",
          )}
        </span>
      )}

      {speech.error && (
        <span className="text-[0.7rem] text-crit">{speech.error}</span>
      )}
    </div>
  );
}

export function VoicePicker({ speech, language }) {
  const options = speech.voicesFor(language);
  if (options.length < 2) return null;
  return (
    <select
      value={speech.chosenVoice}
      onChange={(event) => speech.setChosenVoice(event.target.value)}
      className="max-w-full rounded-lg border border-line-strong bg-surface px-2 py-1 text-[0.7rem] text-ink-soft outline-none focus:border-brand"
      title={t(language, "voice")}
    >
      <option value="">{t(language, "defaultVoice")}</option>
      {options.map((voice) => (
        <option key={voice.voiceURI} value={voice.voiceURI}>
          {voice.name}
        </option>
      ))}
    </select>
  );
}
