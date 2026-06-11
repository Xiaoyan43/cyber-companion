/** RTC room binary messages — subtitle + agent brief (demo-compatible). */

import { tlv2String } from "./tlv";

export type RtcAgentPhase = "idle" | "listening" | "thinking" | "speaking";

export type RtcSubtitleLine = {
  id: string;
  speaker: "user" | "boxi";
  text: string;
  definite: boolean;
  paragraph: boolean;
  interrupted?: boolean;
};

type MessageType = "subv" | "conv" | "tool";

const AGENT_BRIEF = {
  LISTENING: 1,
  THINKING: 2,
  SPEAKING: 3,
  INTERRUPTED: 4,
  FINISHED: 5,
} as const;

export type RtcMessageState = {
  localUserId: string;
  botUserId: string;
  botName: string;
  agentPhase: RtcAgentPhase;
  lines: RtcSubtitleLine[];
  agentEnabled: boolean;
  lineSeq: number;
};

export function createRtcMessageState(botName = "Boxi"): RtcMessageState {
  return {
    localUserId: "",
    botUserId: "",
    botName,
    agentPhase: "idle",
    lines: [],
    agentEnabled: false,
    lineSeq: 0,
  };
}

function isBotUser(userId: string, state: RtcMessageState): boolean {
  return userId === state.botUserId || userId.includes("voiceChat_");
}

function speakerFor(userId: string, state: RtcMessageState): "user" | "boxi" {
  return isBotUser(userId, state) ? "boxi" : "user";
}

function applySubtitle(
  state: RtcMessageState,
  payload: {
    text: string;
    user: string;
    definite?: boolean;
    paragraph?: boolean;
  },
): RtcMessageState {
  if (!state.agentEnabled) {
    return state;
  }

  const { text, user } = payload;
  const definite = Boolean(payload.definite);
  const paragraph = Boolean(payload.paragraph);
  const fromBot = isBotUser(user, state);
  const speaker = speakerFor(user, state);
  const lines = [...state.lines];
  const last = lines[lines.length - 1];

  const lastCompleted = last
    ? fromBot
      ? last.definite
      : last.paragraph
    : true;

  if (!text) {
    return state;
  }

  let lineSeq = state.lineSeq;
  if (!last || lastCompleted || last.speaker !== speaker) {
    lineSeq += 1;
    lines.push({
      id: `rtc-line-${lineSeq}`,
      speaker,
      text,
      definite,
      paragraph,
    });
  } else {
    const updated = { ...last, text, definite, paragraph };
    lines[lines.length - 1] = updated;
  }

  return { ...state, lines, lineSeq };
}

function applyBrief(state: RtcMessageState, parsed: Record<string, unknown>): RtcMessageState {
  const stage = (parsed.Stage ?? {}) as { Code?: number };
  const code = stage.Code ?? 0;
  let agentPhase = state.agentPhase;

  switch (code) {
    case AGENT_BRIEF.LISTENING:
      agentPhase = "listening";
      break;
    case AGENT_BRIEF.THINKING:
      agentPhase = "thinking";
      break;
    case AGENT_BRIEF.SPEAKING:
      agentPhase = "speaking";
      break;
    case AGENT_BRIEF.FINISHED:
      agentPhase = "listening";
      break;
    case AGENT_BRIEF.INTERRUPTED: {
      const lines = [...state.lines];
      const last = lines[lines.length - 1];
      if (last?.speaker === "boxi") {
        lines[lines.length - 1] = { ...last, interrupted: true };
      }
      agentPhase = "listening";
      return { ...state, lines, agentPhase };
    }
    default:
      break;
  }

  return { ...state, agentPhase };
}

export type RtcCompletedTurn = {
  userText: string;
  botText: string;
  turnKey: string;
};

/** Last line is a finalized bot subtitle → one exchange: the preceding user line +
 *  ALL bot segments since it, concatenated. Keyed by the user line id so a reply that
 *  finalizes in several `definite` segments posts ONCE (not once per segment). */
export function detectCompletedTurn(lines: RtcSubtitleLine[]): RtcCompletedTurn | null {
  if (lines.length < 2) {
    return null;
  }
  const last = lines[lines.length - 1];
  if (last.speaker !== "boxi" || !last.definite || !last.text.trim()) {
    return null;
  }

  // Walk back from the tail, collecting this turn's bot segments until the user
  // line that opened the exchange. Bot lines before that user line belong to an
  // earlier turn and are excluded.
  const botParts: string[] = [];
  let userLine: RtcSubtitleLine | undefined;
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    const line = lines[index];
    if (line.speaker === "boxi") {
      if (line.text.trim()) {
        botParts.unshift(line.text.trim());
      }
      continue;
    }
    if (line.speaker === "user" && line.text.trim()) {
      userLine = line;
      break;
    }
  }
  if (!userLine || botParts.length === 0) {
    return null;
  }

  return {
    userText: userLine.text.trim(),
    botText: botParts.join(""),
    turnKey: userLine.id,
  };
}

export function parseRtcRoomMessage(
  buffer: ArrayBuffer,
  state: RtcMessageState,
): RtcMessageState {
  try {
    const { type, value } = tlv2String(buffer);
    const parsed = JSON.parse(value) as Record<string, unknown>;

    if (type === "subv") {
      const data = (parsed.data as Array<Record<string, unknown>> | undefined)?.[0] ?? {};
      return applySubtitle(state, {
        text: String(data.text ?? ""),
        user: String(data.userId ?? ""),
        definite: Boolean(data.definite),
        paragraph: Boolean(data.paragraph),
      });
    }

    if (type === "conv") {
      return applyBrief(state, parsed);
    }
  } catch {
    // ignore malformed agent frames
  }

  return state;
}
