export function formatRtcApiError(raw: string, fallback: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map((item) => String(item)).join("; ");
    }
  } catch {
    // not JSON — show raw text
  }

  return trimmed;
}
