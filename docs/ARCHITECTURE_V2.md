# Architecture V2 — Real-time Companion in a Box

Status: target architecture (the rebuild). Supersedes the voice/UI parts of
`docs/ARCHITECTURE.md`; the memory/behavior/provider/file-gateway parts of V1
are KEPT. This is the source of truth for the rebuild.

## North Star — two cores

1. **Full-duplex real-time voice conversation** — talk naturally, interrupt and
   be interrupted, like a person. On top of **long-term memory** and a real
   **personality**. This is what separates it from a toy tool: emotional-value
   companionship.
2. **The person in a box** — a 2.5D pixel room where *the screen is the glass*.
   A character with 8–10 states, expressions, and behaviors; 4–6 fixed activity
   spots; the room shifts with day/night, mood, and the user's progress. Not 3D
   — a convincing 2D stage (glass layer + room layer + character layer + behavior
   binding).

## End goal — the box

The companion eventually lives as a desktop object. Two device paths; the
brain/surface split makes the software identical for both:

**Path A — old iPhone as the box (recommended, available now).** An old iPhone
(e.g. iPhone SE 2) in a 3D-printed shell IS the box: its screen is the glass, its
mic + speaker are the ears + mouth, and its built-in echo cancellation (the
speakerphone audio path) is far better than a laptop's external speaker — so real
**full-duplex barge-in is likely achievable here, well before any dedicated
hardware**. The iPhone runs only the **surface**: the web app shipped via **Capacitor** as a
native iOS app (native mic + AEC + background audio — better than a raw Safari
PWA, which stays a simpler fallback), showing the PixiJS room + mic/speaker + a
WebSocket link to the brain, locked via iOS Guided Access on a charging dock. It
does NOT run the brain. (Capacitor approach borrowed from AIRI's Stage Pocket.)

**Path B — dedicated SBC (optional, later).** A Pi-class board + small screen +
mic array (hardware AEC) + speaker + 3D enclosure. Same surface, swapped to local
audio + kiosk Chromium. Only needed if you want it to run without the Mac/phone.

**The brain needs a host either way** (Pipecat + memory + behavior + persona are
Python — they do not run on iOS). Host = your **Mac** while at the desk (now), or
a cheap **headless mini-box** later (no screen/mic/speaker needed → cheaper than a
full SBC kit). Keep the brain local for privacy + latency; cloud only for
DeepSeek/Doubao.

Built **hardware-ready from day one**:

- **Same software runs on laptop (dev), iPhone (box), and Pi (later)** — only the
  *surface* changes.
- **Heavy compute stays in the cloud** (DeepSeek + Doubao). The device is thin.
- **Brain/surface separation** is exactly what makes the iPhone-as-box path free
  and rewrite-free.

## Design principles

1. **Brain/surface separation.**
   - *Brain*: Pipecat pipeline + memory engine + behavior engine + persona +
     cloud calls. Identical on laptop and Pi.
   - *Surface*: PixiJS room rendering + audio I/O. Laptop = browser; Pi = local
     ALSA audio + full-screen kiosk Chromium.
2. **Cloud brains, thin box.** DeepSeek/Doubao are cloud; the device stays cheap.
3. **Audio I/O is abstracted** (browser getUserMedia/WebAudio ↔ Pi local ALSA).
   Pipecat supports both transports.
4. **Web renderer for portability.** PixiJS runs in a browser now and in kiosk
   Chromium on the Pi — one renderer, two surfaces.
5. **Reuse-first; keep the soul.** Adopt mature open source for the hard plumbing
   (real-time voice, rendering, VAD); keep our memory/behavior/persona.
6. **Turn-taking is configurable (half ↔ full duplex)** so the same software
   upgrades when a mic array with hardware AEC arrives (see Echo).

## The stack

| Layer | Choice | Notes |
|---|---|---|
| Real-time voice pipeline | **Pipecat** (open source) | 1:1 voice agent framework, frame-processor pipeline, built-in interruption, DeepSeek supported, transport-agnostic, runs on Pi. Level-4 base adoption. |
| Voice activity detection | **Silero VAD** (Pipecat built-in) | Endpointing + barge-in trigger. |
| STT / TTS | **Doubao streaming** as **custom Pipecat services** | Not in Pipecat's official list; we port our existing Doubao adapter logic into Pipecat services. Streaming STT also removes the post-release latency. |
| LLM | **DeepSeek** (kept) | Pipecat supports it natively (OpenAI-compatible). |
| 2.5D room renderer | **PixiJS** (WebGL 2D) | Layered scene: glass / room / character; lighting tints for day/night/mood; AnimatedSprite for character states. Level-3 adoption. |
| Character art | Aseprite sprite sheets | State + action frames. |
| Device (later) | Pi-class SBC + small screen + **mic array w/ hardware AEC** (e.g. ReSpeaker) + speaker | Box only orchestrates + renders + audio I/O. |

> LiveKit was considered and not chosen: it is WebRTC/multi-participant-oriented
> and wants a media server — heavier than a 1:1 desktop box needs. Pipecat is
> lighter and more controllable. (LiveKit's one edge — WebRTC AEC — we cover with
> a hardware mic array on the box.)

## System shape

```
 mic ─► VAD (Silero) ─► STT (Doubao stream) ─► ┌─ Companion Brain ─┐ ─► TTS (Doubao stream) ─► speaker
        (barge-in)                              │ behavior engine    │
                                                │ + memory context   │
                                                │ + DeepSeek          │
                                                │ + persona           │
                                                │ + M2 memory write   │
                                                └─ emits avatar_state │
                                                     + action tags ───┼──► 2.5D Room (PixiJS)
                                                                      │     glass / room / character
 Pipecat orchestrates the whole pipeline + interruption.             ┘
```

The **Companion Brain** is the one custom step inside Pipecat's LLM slot. It is
where the project's distinctiveness lives: it runs the behavior engine first
(reply / silent / mutter / refuse / interrupt / proactive — Boxi does NOT always
answer), injects retrieved memory + mood + persona, calls DeepSeek, writes
memories (M2), and emits the avatar state + action tags that drive the room.

## Keep / Rebuild / Retire

- **Keep (the soul):** memory engine (SQLite, retrieval, summaries, M2
  auto-write), behavior engine (decisions, mood, persona), provider abstraction
  (DeepSeek), file permission gateway (for the later personal-files feature),
  config/persona/budget JSON system.
- **Rebuild:** voice layer → Pipecat pipeline; UI layer → PixiJS room.
- **Retire / demote to reference:** push-to-talk UI, the STT/TTS HTTP routers,
  `/chat/stream`, the CSS pixel character. The **Doubao adapter logic is ported,
  not thrown away.** Prior work proved the path; the soul carries over.

## Echo & turn-taking (external speaker is permanent)

The companion uses an external speaker on both the laptop (dev) and the box
(target), so echo is a permanent design constraint, not a dev annoyance.

- **Laptop / external speaker (now):** **half-duplex** — Boxi pauses listening
  while it speaks, resumes after (driven by VAD). Browser AEC is best-effort.
  **Reliable barge-in is NOT expected here** — external-speaker echo is too hard
  to cancel in software.
- **iPhone-as-box (likely soon):** the iPhone's built-in AEC (speakerphone audio
  path) is far better than a laptop's external speaker — **full-duplex barge-in is
  likely achievable here**. Validate early; if it holds, "interrupt any time"
  arrives well before any dedicated hardware.
- **Dedicated box (later):** a **mic array with hardware AEC** (smart-speaker
  style) → real full-duplex, interrupt-any-time.
- The turn-taking layer is **configurable (half ↔ full)** so the same software
  upgrades as soon as a surface with good AEC (iPhone, or a mic array) is present.

## Honest limits (none are blockers)

- **Voice ceiling:** STT→text-LLM→TTS is not native speech-to-speech (e.g.
  GPT-4o voice). With DeepSeek + Doubao streaming + Pipecat interruption it is
  genuinely real-time and interruptible, but a touch less seamless / less vocal
  nuance than a frontier speech-to-speech model. The right cost/control tradeoff.
- **Doubao in Pipecat** needs a custom service (we have the logic).
- **Full laptop barge-in** on external speakers is unreliable; true barge-in is a
  hardware-phase win (mic array AEC).
- **Described-action → animation** (parenthetical stage directions → real
  character motion) is an ongoing iteration, not a one-shot.

## Open-source evaluation outcome (base decision)

Evaluated the companion/VTuber field (Open-LLM-VTuber, Project AIRI, Soul of
Waifu, etc.). Decision:

- **Base = Pipecat (voice) + our existing Python soul (kept) + PixiJS pixel room
  (built).** NOT a fork of AIRI.
- **Why not base on AIRI** (despite MIT + web/mobile + voice + memory): AIRI is a
  Vue/TS/pnpm/xsAI world; basing on it means switching stacks and **rewriting our
  hardened Python soul (memory + behavior engine + persona) in TS** — AIRI has no
  "behavior engine" (silent/refuse/interrupt/proactive) concept. Its visual core
  is Live2D/VRM anime (we want pixel), and the renderer is not plug-and-play. Net:
  basing on AIRI = adopt a foreign world + discard the soul we tuned + still build
  the pixel stage ourselves. Bad trade.
- **AIRI / Open-LLM-VTuber = references to steal from, not bases.**

### Steal list (borrow the hard-won parts)

- **Capacitor for the iPhone surface** (from AIRI's "Stage Pocket"): wrap the web
  app as a native iOS app → native mic + AEC + background, better than raw Safari
  PWA. This is the preferred iPhone-box path.
- **`@ricky0123/vad-web`** (browser Silero VAD) — used by AIRI; adopt directly.
- **Open-LLM-VTuber's echo-cancellation / barge-in-without-headphones** approach —
  study and replicate; it's our hardest problem.
- **Emotion mapping** (LLM emits emotion → character expression) — the pattern for
  binding stage directions to our pixel character.
- **Brain/surface WebSocket split** — AIRI confirms the pattern (clients ↔ WS ↔
  server-runtime).

### Pixel-art references (we build the room; these inform art/scene)

- CATAI (pixel sprite + Retina nearest-neighbor polish), deskrpg (2D pixel room +
  AI NPCs), CodeWalkers / OpenPets (sprite desktop pet interaction), Pixel-Pets
  (pixel pet on embedded hardware — future hardware angle).

## Reuse ledger (record in OPEN_SOURCE_REUSE.md when pulled in)

- Pipecat — Level 4 (base, voice). BSD-2. Approved by user.
- PixiJS — Level 3/2 (renderer, pixel room). MIT. Approved by user.
- Silero VAD via `@ricky0123/vad-web` — Level 2. MIT.
- Capacitor — Level 2 (iPhone surface wrapper). MIT.
- Project AIRI (MIT) / Open-LLM-VTuber (custom license) / Soul of Waifu (GPL-3) —
  Level 1, reference only (study patterns; do not copy code, esp. the non-MIT ones).
