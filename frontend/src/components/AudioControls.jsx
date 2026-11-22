import { useEffect, useMemo, useState } from "react";
import { Square, Volume2 } from "lucide-react";

// Browser SpeechSynthesis only. No server-side audio, no extra dependency.
// Malayalam voices exist on some systems and not on others, so the control
// says which voice it actually found instead of promising one.
const synth = typeof window !== "undefined" ? window.speechSynthesis : null;

function useVoices() {
  const [voices, setVoices] = useState(() => synth?.getVoices() ?? []);
  useEffect(() => {
    if (!synth) return undefined;
    const update = () => setVoices(synth.getVoices());
    update();
    synth.addEventListener?.("voiceschanged", update);
    return () => synth.removeEventListener?.("voiceschanged", update);
  }, []);
  return voices;
}

export function useSpeech() {
  const voices = useVoices();
  const [speakingId, setSpeakingId] = useState(null);

  useEffect(() => () => synth?.cancel(), []);

  const pickVoice = (language) => {
    if (!voices.length) return null;
    const wanted = language === "ml" ? ["ml-in", "ml_in", "ml"] : ["en-in", "en-gb", "en-us", "en"];
    for (const prefix of wanted) {
      const match = voices.find((voice) =>
        voice.lang?.toLowerCase().replace("_", "-").startsWith(prefix.replace("_", "-")),
      );
      if (match) return match;
    }
    return language === "ml" ? null : voices[0] ?? null;
  };

  const speak = (id, text, language) => {
    if (!synth || !text?.trim()) return;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice(language);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = language === "ml" ? "ml-IN" : "en-IN";
    }
    utterance.rate = 0.95;
    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);
    setSpeakingId(id);
    synth.speak(utterance);
  };

  const stop = () => {
    synth?.cancel();
    setSpeakingId(null);
  };

  const hasVoiceFor = (language) => Boolean(pickVoice(language));

  return {
    supported: Boolean(synth),
    voices,
    speakingId,
    speak,
    stop,
    hasVoiceFor,
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
  const missingVoice = useMemo(
    () => language === "ml" && !speech.hasVoiceFor("ml"),
    [language, speech],
  );

  if (!speech.supported) {
    return (
      <span className="text-xs text-ink-soft">
        This browser does not support speech synthesis.
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={() => (active ? speech.stop() : speech.speak(id, text, language))}
        className={`btn-secondary ${compact ? "!px-2.5 !py-1.5 text-xs" : "text-xs"}`}
        disabled={!text?.trim()}
      >
        {active ? <Square size={13} /> : <Volume2 size={14} />}
        {active ? stopLabel : label}
      </button>
      {missingVoice && (
        <span className="text-[0.7rem] text-warn">
          No Malayalam voice is installed in this browser, so the text will be read
          with another voice.
        </span>
      )}
    </div>
  );
}
