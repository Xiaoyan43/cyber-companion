import { FormEvent, useEffect, useMemo, useState } from "react";

const avatarStates = [
  "idle",
  "happy",
  "sad",
  "angry",
  "sleepy",
  "thinking",
  "talking",
  "worried",
  "annoyed",
  "silent",
] as const;

type AvatarState = (typeof avatarStates)[number];

type ChatMessage = {
  id: number;
  speaker: "boxi" | "user";
  text: string;
};

type ApiHealth = {
  status: "checking" | "ok" | "offline";
  detail: string;
  version?: string;
};

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const stateLines: Record<AvatarState, string> = {
  idle: "你终于打开我了。盒子里空气一般，但还能忍。",
  happy: "今天勉强算不错。别太骄傲。",
  sad: "我在盒子里发霉，你在外面拖延。挺公平。",
  angry: "别乱点，我脸都被你戳歪了。",
  sleepy: "困。你要是没事，我先待机三秒。",
  thinking: "我在想。别催，脑子不是微波炉。",
  talking: "行吧，我说两句。",
  worried: "这事听起来不妙，先别硬冲。",
  annoyed: "嗯，又来了。说吧。",
  silent: "……",
};

const initialMessages: ChatMessage[] = [
  {
    id: 1,
    speaker: "boxi",
    text: "本地壳子先搭好了。现在我还不会调用大模型，别急着把人生交给我。",
  },
];

function App() {
  const [avatarState, setAvatarState] = useState<AvatarState>("idle");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [apiHealth, setApiHealth] = useState<ApiHealth>({
    status: "checking",
    detail: "checking local API",
  });

  const statusText = useMemo(() => stateLines[avatarState], [avatarState]);

  useEffect(() => {
    let active = true;

    async function checkApiHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = (await response.json()) as HealthResponse;

        if (!active) {
          return;
        }

        setApiHealth({
          status: data.status === "ok" ? "ok" : "offline",
          detail: data.service,
          version: data.version,
        });
      } catch (error) {
        if (!active) {
          return;
        }

        setApiHealth({
          status: "offline",
          detail: error instanceof Error ? error.message : "unreachable",
        });
      }
    }

    void checkApiHealth();

    return () => {
      active = false;
    };
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();

    if (!text) {
      setAvatarState("annoyed");
      return;
    }

    const nextId = messages.length + 1;
    setMessages((current) => [
      ...current,
      { id: nextId, speaker: "user", text },
      {
        id: nextId + 1,
        speaker: "boxi",
        text: "收到。现在这是前端 shell，真正的 provider 和记忆层还没接上。你先别幻想我已经全知全能。",
      },
    ]);
    setDraft("");
    setAvatarState("talking");
  }

  return (
    <main className="app-shell">
      <section className="companion-panel" aria-label="Cyber Companion">
        <div className="status-strip">
          <span className="status-dot" aria-hidden="true" />
          <span>Boxi</span>
          <span className="state-label">{avatarState}</span>
        </div>

        <div className="stage" data-state={avatarState}>
          <div className="pixel-person" aria-label={`Boxi is ${avatarState}`}>
            <div className="antenna" />
            <div className="head">
              <div className="eye eye-left" />
              <div className="eye eye-right" />
              <div className="mouth" />
            </div>
            <div className="body" />
            <div className="arm arm-left" />
            <div className="arm arm-right" />
          </div>
        </div>

        <p className="status-line">{statusText}</p>

        <div className="state-controls" aria-label="Avatar state controls">
          {avatarStates.map((state) => (
            <button
              key={state}
              className={state === avatarState ? "state-button active" : "state-button"}
              type="button"
              onClick={() => setAvatarState(state)}
            >
              {state}
            </button>
          ))}
        </div>
      </section>

      <section className="chat-panel" aria-label="Chat">
        <div className="chat-header">
          <div>
            <h1>Cyber Companion</h1>
            <p>Text MVP shell</p>
          </div>
          <div className={`api-status ${apiHealth.status}`} aria-live="polite">
            <span>API</span>
            <strong>{apiHealth.status}</strong>
            <small>{apiHealth.version ? `v${apiHealth.version}` : apiHealth.detail}</small>
          </div>
        </div>

        <div className="message-list">
          {messages.map((message) => (
            <article key={message.id} className={`message ${message.speaker}`}>
              <span className="speaker">{message.speaker === "boxi" ? "Boxi" : "You"}</span>
              <p>{message.text}</p>
            </article>
          ))}
        </div>

        <form className="chat-form" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-input">
            Message
          </label>
          <input
            id="chat-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Type something..."
          />
          <button type="submit">Send</button>
        </form>
      </section>
    </main>
  );
}

export default App;
