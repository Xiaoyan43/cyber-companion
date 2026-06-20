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

/** Clean reply text for TTS — Fish Audio's HTTP streaming endpoint handles the full
 * text in one request and chunks the audio internally, so callers should not pre-split. */
export function prepareTextForSpeech(text: string): string {
  return normalizeSpeechText(stripStageDirections(text.trim()));
}
