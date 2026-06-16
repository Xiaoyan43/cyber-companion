import { useMemo } from "react";

import "./LetterView.css";
import { LetterMood } from "./scripts";
import { useTypewriter } from "./useTypewriter";

const MOOD_LABELS: Record<LetterMood, string> = {
  calm: "平静",
  hesitant: "犹豫",
  excited: "激动",
  fragile: "虚弱",
};

const MOODS: LetterMood[] = ["calm", "hesitant", "excited", "fragile"];

function formatDate(): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date());
}

type Props = {
  mood?: LetterMood;
};

export function LetterView({ mood: externalMood }: Props) {
  const { mood, text, tone, note, caretVisible, paused, run, pauseOrResume } = useTypewriter("calm");
  const activeMood = externalMood ?? mood;
  const today = useMemo(() => formatDate(), []);

  const writingClassName = `writing ${activeMood === "calm" ? "" : activeMood}`.trim();
  const writingStyle = {
    "--letter-weight": tone.weight,
    "--letter-opacity": tone.alpha,
    "--letter-size": tone.size,
    color: `rgba(30, 29, 26, ${tone.alpha})`,
  } as React.CSSProperties;

  return (
    <div className="letter-spike">
      <header className="bar">
        <div className="brand">
          <strong>情绪信笺</strong>
          <span>private letter interface</span>
        </div>

        {externalMood === undefined && (
          <nav className="modes" aria-label="情绪">
            {MOODS.map((m) => (
              <button
                key={m}
                type="button"
                className={m === mood ? "active" : ""}
                onClick={() => run(m)}
              >
                {MOOD_LABELS[m]}
              </button>
            ))}
          </nav>
        )}

        <div className="status" aria-label="文字状态">
          <span>{tone.pace}ms</span>
          <span>{tone.weight}</span>
          <span>{Math.round(tone.alpha * 100)}%</span>
        </div>
      </header>

      <section className="letter-wrap" aria-label="信笺">
        <article className="letter">
          <div className="letter-head">
            <span className="recipient">Dear you,</span>
            <span className="meta">{today}</span>
          </div>

          <div className={`emotion-sketch ${activeMood}`} aria-hidden="true">
            <svg viewBox="0 0 120 120">
              <path className="paper-mark" d="M26 66c14-32 46-42 68-24" />
              <path className="paper-mark" d="M32 83c18 12 45 10 59-8" />

              <g className="mood mood-calm">
                <path className="soft-line" d="M37 54c7-5 15-5 21 0" />
                <path className="soft-line" d="M70 54c7-5 15-5 21 0" />
                <path className="face-line" d="M42 75c12 10 28 11 43 0" />
              </g>

              <g className="mood mood-hesitant">
                <path className="soft-line" d="M38 58c7-2 14-1 20 3" />
                <path className="soft-line" d="M72 58c7-3 14-2 20 2" />
                <path className="face-line" d="M49 78c10 4 21 4 31-1" />
                <path className="soft-line" d="M60 68c3 3 6 3 9 0" />
              </g>

              <g className="mood mood-excited">
                <path className="face-line" d="M36 52c8-8 17-8 25 0" />
                <path className="face-line" d="M70 52c8-8 17-8 25 0" />
                <path className="face-line" d="M40 76c13 14 33 15 48-1" />
                <path className="soft-line" d="M25 42c3-6 8-10 14-12" />
                <path className="soft-line" d="M95 31c6 3 10 7 13 13" />
              </g>

              <g className="mood mood-fragile">
                <path className="soft-line" d="M39 60c7 4 14 4 21 0" />
                <path className="soft-line" d="M70 60c7 4 14 4 21 0" />
                <path className="face-line" d="M48 81c11-5 22-5 33 0" />
                <path className="soft-line" d="M36 70c5 3 10 5 16 5" />
              </g>
            </svg>
          </div>

          <div className={writingClassName} style={writingStyle} aria-live="polite">
            <span>{text}</span>
            <span className="caret" style={{ visibility: caretVisible ? "visible" : "hidden" }} aria-hidden="true" />
          </div>

          <div className="letter-foot">
            <span className="signature">Always here,</span>
            <span className="meta">{activeMood}</span>
          </div>
        </article>
      </section>

      <footer className="toolbar">
        <button className="icon-button" type="button" title="重写" onClick={() => run(mood)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 11a8 8 0 0 0-15.5-2M4 5v4h4" />
            <path d="M4 13a8 8 0 0 0 15.5 2M20 19v-4h-4" />
          </svg>
        </button>
        <button className="icon-button" type="button" title={paused ? "继续" : "暂停"} onClick={pauseOrResume}>
          {paused ? (
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m8 5 11 7-11 7V5Z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8 5v14M16 5v14" />
            </svg>
          )}
        </button>
        <span className="note">{note}</span>
      </footer>
    </div>
  );
}
