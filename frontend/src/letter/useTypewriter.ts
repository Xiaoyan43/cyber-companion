import { useCallback, useEffect, useRef, useState } from "react";

import { LetterMood, LetterStep, MOOD_CONFIG, MOOD_SCRIPTS, ToneConfig } from "./scripts";

export interface TypewriterState {
  mood: LetterMood;
  text: string;
  tone: ToneConfig;
  note: string;
  caretVisible: boolean;
  paused: boolean;
  run: (mood: LetterMood) => void;
  pauseOrResume: () => void;
}

function wait(ms: number, onTimer: (id: number | null) => void): Promise<void> {
  return new Promise((resolve) => {
    const id = window.setTimeout(() => {
      onTimer(null);
      resolve();
    }, ms);
    onTimer(id);
  });
}

export function useTypewriter(initialMood: LetterMood = "calm"): TypewriterState {
  const [mood, setMood] = useState<LetterMood>(initialMood);
  const [text, setText] = useState("");
  const [tone, setToneState] = useState<ToneConfig>(MOOD_CONFIG[initialMood]);
  const [note, setNote] = useState(MOOD_CONFIG[initialMood].note);
  const [caretVisible, setCaretVisible] = useState(true);
  const [paused, setPaused] = useState(false);

  const tokenRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const moodRef = useRef<LetterMood>(initialMood);

  const setTimer = useCallback((id: number | null) => {
    timerRef.current = id;
  }, []);

  const applyTone = useCallback((targetMood: LetterMood, partial: Partial<ToneConfig> = {}) => {
    const merged = { ...MOOD_CONFIG[targetMood], ...partial };
    setToneState(merged);
    setNote(merged.note);
    return merged;
  }, []);

  const typeText = useCallback(
    async (value: string, delay: number, pulse: boolean | undefined, token: number) => {
      const chars = Array.from(value);
      for (let i = 0; i < chars.length; i += 1) {
        if (token !== tokenRef.current) return;
        setText((prev) => prev + chars[i]);
        if (pulse && i % 7 === 0) {
          const heavy = i % 14 === 0 ? 820 : 680;
          setToneState((prev) => ({ ...prev, weight: heavy }));
        }
        await wait(delay + Math.random() * Math.min(34, delay * 0.45), setTimer);
      }
    },
    [setTimer],
  );

  const eraseText = useCallback(
    async (count: number, delay: number, token: number) => {
      for (let i = 0; i < count; i += 1) {
        if (token !== tokenRef.current) return;
        setText((prev) => Array.from(prev).slice(0, -1).join(""));
        await wait(delay, setTimer);
      }
    },
    [setTimer],
  );

  const run = useCallback(
    async (targetMood: LetterMood) => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      tokenRef.current += 1;
      const token = tokenRef.current;

      setPaused(false);
      moodRef.current = targetMood;
      setMood(targetMood);
      applyTone(targetMood);
      setText("");
      setCaretVisible(true);

      for (const step of MOOD_SCRIPTS[targetMood]) {
        if (token !== tokenRef.current) return;
        await runStep(step, token);
      }

      if (token === tokenRef.current) {
        setCaretVisible(false);
        setNote("still");
      }

      async function runStep(step: LetterStep, currentToken: number) {
        if (step.type === "pause") {
          await wait(step.ms, setTimer);
        } else if (step.type === "tone") {
          applyTone(targetMood, step);
        } else if (step.type === "type") {
          await typeText(step.text, step.delay, step.pulse, currentToken);
        } else if (step.type === "erase") {
          await eraseText(step.count, step.delay, currentToken);
        }
      }
    },
    [applyTone, eraseText, typeText, setTimer],
  );

  const pauseOrResume = useCallback(() => {
    if (!paused) {
      setPaused(true);
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      tokenRef.current += 1;
      setCaretVisible(false);
      setNote("held");
      return;
    }
    void run(moodRef.current);
  }, [paused, run]);

  useEffect(() => {
    void run(initialMood);

    const onVisibility = () => {
      if (document.hidden && timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
        tokenRef.current += 1;
        setCaretVisible(false);
        setNote("hidden");
        setPaused(true);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
    };
    // run only on mount; mood changes are driven explicitly via `run`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { mood, text, tone, note, caretVisible, paused, run, pauseOrResume };
}
