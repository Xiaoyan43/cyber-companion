const SILENT_WAV_DATA_URL =
  "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==";

let unlocked = false;

export function primeAudioPlayback(): void {
  if (unlocked) {
    return;
  }

  const silent = new Audio(SILENT_WAV_DATA_URL);
  silent.volume = 0.01;
  void silent.play().then(() => {
    unlocked = true;
    silent.pause();
    silent.currentTime = 0;
  }).catch(() => {
    // Browser may still allow playback after a later explicit gesture.
  });
}

export function isAudioPlaybackPrimed(): boolean {
  return unlocked;
}
