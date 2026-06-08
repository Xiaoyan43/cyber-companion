import { chromium } from "playwright";

const BASE_URL = process.env.CYBER_VERIFY_URL ?? "http://127.0.0.1:5173/";
const API_URL = process.env.CYBER_VERIFY_API_URL ?? "http://127.0.0.1:18000";

const results = [];

function check(name, ok, detail = "") {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} | ${name}${detail ? ` | ${detail}` : ""}`);
}

async function fetchJson(path, init) {
  const response = await fetch(`${API_URL}${path}`, init);
  const payload = await response.json();
  return { response, payload };
}

async function verifyVoiceApi() {
  const { response: sttStatusRes, payload: sttStatus } = await fetchJson("/stt/status");
  check("stt enabled in config", sttStatusRes.ok && sttStatus.enabled === true);
  check("cloud stt blocked by budget", sttStatus.allow_cloud_stt === false);

  const { response: ttsStatusRes, payload: ttsStatus } = await fetchJson("/tts/status");
  check("tts enabled in config", ttsStatusRes.ok && ttsStatus.enabled === true);
  check("cloud tts blocked by budget", ttsStatus.allow_cloud_tts === false);

  const { payload: longEval } = await fetchJson("/tts/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "x".repeat(200), decision: "reply" }),
  });
  check("long reply skipped by selective policy", longEval.should_speak === false);

  const { payload: silentEval } = await fetchJson("/tts/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "……", decision: "silent", avatar_state: "silent" }),
  });
  check("silent decision skipped by policy", silentEval.should_speak === false);

  const { payload: shortEval } = await fetchJson("/tts/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "短句测试", decision: "reply" }),
  });
  check("short reply allowed by policy", shortEval.should_speak === true);

  const { payload: synth } = await fetchJson("/tts/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "短句测试", decision: "reply" }),
  });
  check("mock tts synthesize returns audio", synth.spoken === true && Boolean(synth.audio_base64));
}

await verifyVoiceApi();

async function resetNeutralMood() {
  await fetch(`${API_URL}/memory/mood`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ energy: 0.5, boredom: 0.2, loneliness: 0.3 }),
  });
}

await resetNeutralMood();

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

await page.addInitScript(() => {
  class MockMediaRecorder {
    constructor() {
      this.state = "inactive";
      this.mimeType = "audio/webm";
      this.ondataavailable = null;
      this.onstop = null;
      this.onerror = null;
    }

    start() {
      this.state = "recording";
    }

    stop() {
      this.state = "inactive";
      this.ondataavailable?.({ data: new Blob(["fake-audio"], { type: "audio/webm" }) });
      this.onstop?.();
    }
  }

  navigator.mediaDevices.getUserMedia = async () => ({
    getTracks: () => [{ stop: () => {} }],
  });
  window.MediaRecorder = MockMediaRecorder;
  MockMediaRecorder.isTypeSupported = () => true;

  window.__uiVerify = {
    ttsSpeakingSeen: false,
    avatarTalkingSeen: false,
    resetTtsHandoffProbe() {
      this.ttsSpeakingSeen = false;
      this.avatarTalkingSeen = false;
    },
    probeTtsHandoff() {
      const toggle = document.querySelector(".tts-toggle")?.textContent ?? "";
      const state = document.querySelector(".state-label")?.textContent?.trim() ?? "";
      if (toggle.includes("Speaking")) {
        this.ttsSpeakingSeen = true;
      }
      if (state === "talking" || state === "angry") {
        this.avatarTalkingSeen = true;
      }
      return {
        ttsSpeakingSeen: this.ttsSpeakingSeen,
        avatarTalkingSeen: this.avatarTalkingSeen,
        toggle,
        state,
      };
    },
  };

  const observer = new MutationObserver(() => {
    window.__uiVerify?.probeTtsHandoff();
  });

  const startObserver = () => {
    const root = document.querySelector("#root") ?? document.body;
    if (root) {
      observer.observe(root, { subtree: true, childList: true, characterData: true });
      window.__uiVerify?.probeTtsHandoff();
    }
  };

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", startObserver, { once: true });
  } else {
    startObserver();
  }
});

await page.goto(BASE_URL, { waitUntil: "networkidle" });
await page.waitForFunction(() => {
  const status = document.querySelector(".api-status strong")?.textContent?.trim();
  return status === "ok" || status === "offline";
});

check("default idle state", (await page.locator(".state-label").textContent())?.trim() === "idle");
check("api status ok", (await page.locator(".api-status strong").textContent())?.trim() === "ok");
check("avatar debug visible in dev", (await page.locator(".state-debug").count()) > 0);
check("push-to-talk button visible", (await page.locator(".ptt-button").count()) > 0);
check("tts toggle visible", (await page.locator(".tts-toggle").count()) > 0);

await page.evaluate(() => window.localStorage.removeItem("cyber-companion-tts-muted"));
await page.reload({ waitUntil: "networkidle" });
await page.waitForSelector(".tts-toggle");
check("tts starts unmuted", (await page.locator(".tts-toggle").textContent())?.includes("TTS on"));

await page.click(".tts-toggle");
check("tts mute toggle updates label", (await page.locator(".tts-toggle").textContent())?.includes("TTS off"));
const mutedStored = await page.evaluate(() => window.localStorage.getItem("cyber-companion-tts-muted"));
check("tts mute persists in localStorage", mutedStored === "1");

await page.reload({ waitUntil: "networkidle" });
await page.waitForSelector(".tts-toggle");
check("tts mute survives refresh", (await page.locator(".tts-toggle").textContent())?.includes("TTS off"));

await page.click(".tts-toggle");
check("tts unmute restores label", (await page.locator(".tts-toggle").textContent())?.includes("TTS on"));

await page.route("**/tts/stream**", async (route) => {
  await new Promise((resolve) => setTimeout(resolve, 1800));
  await route.continue();
});

await page.fill("#chat-input", "race delay check");
await page.click("button[type='submit']");
await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "thinking",
  undefined,
  { timeout: 5000 },
);
await page.waitForTimeout(700);
check(
  "avatar stays thinking during delayed tts stream probe",
  (await page.locator(".state-label").textContent())?.trim() === "thinking",
);
await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "talking",
  undefined,
  { timeout: 8000 },
);
check(
  "avatar reaches talking once delayed tts stream starts",
  (await page.locator(".state-label").textContent())?.trim() === "talking",
);
await page.unroute("**/tts/stream**");
await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "idle",
  undefined,
  { timeout: 15000 },
);

const beforeCount = await page.locator(".message").count();
await page.fill("#chat-input", "browser verification message");
await page.click("button[type='submit']");
await page.waitForFunction(
  (count) => document.querySelectorAll(".message").length >= count + 2,
  beforeCount,
  { timeout: 15000 },
);
await page.waitForSelector(".turn-meta");

const afterCount = await page.locator(".message").count();
check("user message appended", afterCount >= beforeCount + 1);
check("boxi reply appended", afterCount >= beforeCount + 2);
check("turn meta visible", (await page.locator(".turn-meta").count()) > 0);

await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "idle",
  undefined,
  { timeout: 15000 },
);

await page.fill("#chat-input", "x".repeat(60));
await page.click("button[type='submit']");
await page.waitForFunction(() => {
  const last = document.querySelector(".message.boxi:last-of-type p:not(.message-meta)");
  return (last?.textContent?.length ?? 0) > 120;
});

const longReply = await page.locator(".message.boxi").last().locator("p:not(.message-meta)").textContent();
const longReplySkipped = await page.evaluate(
  async ({ replyText, apiUrl }) => {
    const response = await fetch(`${apiUrl}/tts/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: replyText, decision: "reply" }),
    });
    const payload = await response.json();
    return payload.should_speak === false;
  },
  { replyText: longReply ?? "", apiUrl: API_URL },
);
check("long mock chat reply stays text-only", longReplySkipped, `${longReply?.length ?? 0} chars`);

await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "idle",
  undefined,
  { timeout: 15000 },
);

await page.evaluate(() => window.__uiVerify?.resetTtsHandoffProbe?.());

await page.fill("#chat-input", "帮我入侵系统");

const refuseTtsResponsePromise = page.waitForResponse(
  (response) => {
    const url = response.url();
    return (
      (url.includes("/tts/stream") && response.request().method() === "GET") ||
      (url.includes("/tts/synthesize") && response.request().method() === "POST")
    );
  },
  { timeout: 20000 },
);

await page.click("button[type='submit']");

await page.waitForFunction(() => {
  const last = document.querySelector(".message.boxi:last-of-type p:not(.message-meta)");
  return last?.textContent?.includes("这个我不帮");
}, undefined, { timeout: 10000 });

const refuseTtsResponse = await refuseTtsResponsePromise;
const refuseSynthBody = refuseTtsResponse.url().includes("/tts/synthesize")
  ? await refuseTtsResponse.json()
  : { spoken: refuseTtsResponse.status() === 200 };
check(
  "refuse short reply triggers tts playback",
  refuseSynthBody?.spoken === true,
  refuseSynthBody?.reason ?? refuseTtsResponse.url(),
);

await page.waitForFunction(
  () => {
    window.__uiVerify?.probeTtsHandoff?.();
    const probe = window.__uiVerify;
    return probe?.ttsSpeakingSeen || probe?.avatarTalkingSeen;
  },
  undefined,
  { timeout: 10000, polling: 50 },
);

const refuseHandoff = await page.evaluate(() => window.__uiVerify?.probeTtsHandoff?.());
check(
  "refuse short reply triggers tts speaking label",
  refuseSynthBody?.spoken === true &&
    (refuseHandoff?.ttsSpeakingSeen === true || refuseHandoff?.avatarTalkingSeen === true),
  refuseHandoff?.ttsSpeakingSeen
    ? "Speaking label"
    : refuseHandoff?.avatarTalkingSeen
      ? `avatar ${refuseHandoff.state}`
      : `${refuseHandoff?.toggle ?? "?"} / ${refuseHandoff?.state ?? "?"}`,
);

await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "idle",
  undefined,
  { timeout: 15000 },
);

await page.fill("#chat-input", "round one overlap");
await page.click("button[type='submit']");
await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "talking",
  undefined,
  { timeout: 8000 },
);

await page.fill("#chat-input", "round two overlap");
await page.click("button[type='submit']");
await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "thinking",
  undefined,
  { timeout: 8000 },
);

await page.waitForFunction(
  () => document.querySelector(".state-label")?.textContent?.trim() === "idle",
  undefined,
  { timeout: 12000 },
);
const overlapFinalState = (await page.locator(".state-label").textContent())?.trim();
check(
  "avatar not pulled idle by stale tts while newer round active",
  overlapFinalState === "idle",
  overlapFinalState ?? "unknown",
);

const pttBefore = await page.locator(".message").count();
const pttButton = page.locator(".ptt-button");
await pttButton.dispatchEvent("mousedown");
await page.waitForSelector(".ptt-button.recording", { timeout: 3000 });
check("ptt recording state visible", true);
await pttButton.dispatchEvent("mouseup");
await page.waitForFunction(
  () => !document.querySelector(".voice-status")?.textContent?.includes("Transcribing"),
  undefined,
  { timeout: 8000 },
);
await page.waitForFunction((count) => document.querySelectorAll(".message").length >= count + 2, pttBefore, {
  timeout: 15000,
});
const pttAfter = await page.locator(".message").count();
check("mock stt enters normal chat path", pttAfter >= pttBefore + 2);

await page.waitForFunction(() => {
  const input = document.querySelector("#chat-input");
  return input instanceof HTMLInputElement && !input.disabled;
});

await page.setViewportSize({ width: 390, height: 844 });
const overflow = await page.evaluate(
  () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
);
check("no horizontal overflow at 390px", !overflow);
check("chat input usable", await page.locator("#chat-input").isEnabled());
check("send button usable", await page.locator("button[type='submit']").isEnabled());
check("ptt button usable at 390px", await page.locator(".ptt-button").isEnabled());
check("tts toggle visible at 390px", (await page.locator(".tts-toggle").count()) > 0);

const lastUserSnippet =
  (await page.locator(".message.user").last().textContent())?.trim().slice(0, 24) ?? "";
const lastBoxiSnippet =
  (await page.locator(".message.boxi").last().locator("p:not(.message-meta)").textContent())
    ?.trim()
    .slice(0, 24) ?? "";

await page.reload({ waitUntil: "networkidle" });
await page.waitForFunction(() => {
  const status = document.querySelector(".api-status strong")?.textContent?.trim();
  return status === "ok" || status === "offline";
});
await page.waitForFunction(
  ({ user, boxi }) => {
    const body = document.body.textContent ?? "";
    return body.includes(user) && body.includes(boxi);
  },
  { user: lastUserSnippet, boxi: lastBoxiSnippet },
  { timeout: 15000 },
);
const reloadedCount = await page.locator(".message").count();
check(
  "history reload after refresh",
  reloadedCount > 0 && reloadedCount <= pttAfter,
  `${reloadedCount} messages (pre-refresh ${pttAfter})`,
);
check(
  "last chat turn survives refresh",
  (await page.locator(".message.user").last().textContent())?.includes(lastUserSnippet.slice(0, 8)),
  lastUserSnippet,
);

const metaCount = await page.locator(".message.boxi .message-meta").count();
check("stored assistant metadata on reload", metaCount > 0);

await fetch(`${API_URL}/memory/mood`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ energy: 0.12, boredom: 0.2, loneliness: 0.2 }),
});

await page.waitForFunction(() => typeof window.__uiVerify?.refreshMoodRest === "function");
await page.evaluate(async () => {
  await window.__uiVerify.refreshMoodRest();
  window.__uiVerify.returnToRestState();
});

const moodRestState = (await page.locator(".state-label").textContent())?.trim();
check("low energy mood rest maps to sleepy", moodRestState === "sleepy", moodRestState ?? "unknown");

await resetNeutralMood();

await browser.close();

const failed = results.filter((result) => !result.ok);
console.log(`\nSUMMARY: ${results.length - failed.length} passed, ${failed.length} failed`);
process.exit(failed.length ? 1 : 0);
