const QUOTED_SPAN_PATTERN = /"[^"]*"|「[^」]*」|'[^']*'/g;

/** Remove stage-direction brackets before TTS; quoted dialogue is preserved. */
export function stripStageDirections(text: string): string {
  const placeholders: string[] = [];
  const protectedText = text.replace(QUOTED_SPAN_PATTERN, (match) => {
    placeholders.push(match);
    return `\u0000Q${placeholders.length - 1}\u0000`;
  });

  const stripped = protectedText
    .replace(/（[^）]*）/g, "")
    .replace(/【[^】]*】/g, "")
    .replace(/\([^)]*\)/g, "");

  return stripped.replace(
    /\u0000Q(\d+)\u0000/g,
    (_, index) => placeholders[Number(index)] ?? "",
  );
}

export function normalizeSpeechText(text: string): string {
  return text
    .replace(/\s+/g, " ")
    .replace(/\s+([，。！？…；、])/g, "$1")
    .replace(/([，。！？…；、]){2,}/g, "$1")
    .trim();
}

function prepareTextForSpeech(text: string): string {
  return normalizeSpeechText(stripStageDirections(text.trim()));
}

/** Split reply text into TTS-sized chunks (prefer sentence boundaries). */
export function textChunksForSpeech(text: string, maxChars: number): string[] {
  const prepared = prepareTextForSpeech(text);
  if (!prepared || maxChars <= 0) {
    return [];
  }

  if (prepared.length <= maxChars) {
    return [prepared];
  }

  const chunks: string[] = [];
  let remaining = prepared;

  while (remaining.length > 0) {
    if (remaining.length <= maxChars) {
      chunks.push(remaining);
      break;
    }

    const window = remaining.slice(0, maxChars);
    const splitAt = findChunkSplit(window, maxChars);

    const chunk = remaining.slice(0, splitAt).trim();
    if (chunk) {
      chunks.push(chunk);
    }

    remaining = remaining.slice(splitAt).trim();
    if (!chunk && remaining.length > 0) {
      chunks.push(remaining.slice(0, maxChars));
      remaining = remaining.slice(maxChars).trim();
    }
  }

  return chunks;
}

const STREAMING_SENTENCE_BOUNDARY = /[。！？…\n!?]/;

export function drainStreamingSpeechChunks(
  rawBuffer: string,
  maxChars: number,
): { chunks: string[]; remainder: string } {
  if (!rawBuffer || maxChars <= 0) {
    return { chunks: [], remainder: rawBuffer };
  }

  const chunks: string[] = [];
  let remaining = rawBuffer;

  while (remaining.length > 0) {
    const splitAt = findStreamingChunkEnd(remaining, maxChars);
    if (splitAt === null) {
      break;
    }

    const rawChunk = remaining.slice(0, splitAt);
    remaining = remaining.slice(splitAt);
    const prepared = prepareTextForSpeech(rawChunk);
    if (prepared) {
      chunks.push(prepared);
    }
  }

  return { chunks, remainder: remaining };
}

export function flushStreamingSpeechRemainder(
  rawBuffer: string,
  maxChars: number,
): string[] {
  const prepared = prepareTextForSpeech(rawBuffer);
  if (!prepared) {
    return [];
  }

  if (prepared.length <= maxChars) {
    return [prepared];
  }

  return textChunksForSpeech(prepared, maxChars);
}

function findStreamingChunkEnd(text: string, maxChars: number): number | null {
  let earliest: number | null = null;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === ".") {
      const next = text[index + 1];
      if (next && next !== " " && next !== "\n") {
        continue;
      }
      const end = index + 1 + (next === " " ? 1 : 0);
      earliest = earliest === null ? end : Math.min(earliest, end);
      continue;
    }

    if (!STREAMING_SENTENCE_BOUNDARY.test(char)) {
      continue;
    }

    const end = index + 1;
    earliest = earliest === null ? end : Math.min(earliest, end);
  }

  if (earliest !== null) {
    return earliest;
  }

  if (text.length >= maxChars) {
    return findChunkSplit(text, maxChars);
  }

  return null;
}

function findChunkSplit(window: string, maxChars: number): number {
  let splitAt = lastIndexOfAny(window, ["\n", "。", "！", "？", "…", "；"]);
  if (splitAt > 0) {
    return splitAt + 1;
  }

  const westernMatch = window.match(/[.!?](?:\s|$)/g);
  if (westernMatch) {
    let lastEnd = -1;
    for (const match of westernMatch) {
      const index = window.lastIndexOf(match);
      if (index >= 0) {
        lastEnd = Math.max(lastEnd, index + match.length);
      }
    }
    if (lastEnd > 0) {
      return lastEnd;
    }
  }

  splitAt = window.lastIndexOf(" ");
  if (splitAt > maxChars * 0.4) {
    return splitAt + 1;
  }

  return maxChars;
}

function lastIndexOfAny(text: string, needles: string[]): number {
  let best = -1;
  for (const needle of needles) {
    const index = text.lastIndexOf(needle);
    if (index > best) {
      best = index;
    }
  }
  return best;
}

export function textForSpeech(text: string, maxChars: number): string {
  const prepared = prepareTextForSpeech(text);
  if (!prepared || maxChars <= 0) {
    return "";
  }

  if (prepared.length <= maxChars) {
    return prepared;
  }

  return textChunksForSpeech(prepared, maxChars)[0] ?? "";
}
