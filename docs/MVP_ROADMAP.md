# MVP Roadmap

## Phase 0 - Foundation

Status: in progress

Goal: create project rules, architecture docs, session protocol, and model responsibilities.

Deliverables:

- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/rules/cyber-companion.mdc`
- project docs
- TODO and session log

## Phase 1 - Project Scaffold

Goal: create runnable local prototype structure.

Recommended stack:

- frontend: React + TypeScript
- backend: FastAPI
- database: SQLite
- config: JSON

Deliverables:

- frontend app shell
- local API shell
- config examples
- basic health check
- dev scripts

## Phase 2 - Pixel Character UI

Goal: first visible companion screen.

Deliverables:

- pixel character renderer
- states: idle, happy, sad, angry, sleepy, thinking, talking, worried, annoyed, silent
- state transition demo
- chat panel shell

## Phase 3 - Provider Abstraction

Goal: configurable LLM provider layer.

Deliverables:

- provider interface
- DeepSeek adapter
- OpenAI adapter placeholder
- local model placeholder
- provider config
- token/cost estimate hook

## Phase 4 - SQLite Memory

Goal: local long-term memory storage.

Deliverables:

- database schema
- migrations or init script
- message persistence
- memory CRUD
- mood state persistence
- job/project/reminder memory types

## Phase 5 - Memory Retrieval And Summaries

Goal: stop sending full chat history.

Deliverables:

- relevant memory retrieval
- recent conversation summary
- compact context builder
- memory write policy

## Phase 6 - Behavior Engine

Goal: make the companion feel less like a normal chatbot.

Deliverables:

- local behavior decision engine
- reply/silent/refuse/interrupt/proactive/observe decisions
- mood and energy changes
- personality contract
- structured LLM response format

## Phase 7 - File Permission Gateway

Goal: safe restricted local file access.

Deliverables:

- allowed folder config
- path resolution checks
- symlink escape prevention
- access log
- tests

## Phase 8 - Integration Pass

Goal: make the text MVP coherent.

Deliverables:

- end-to-end chat flow
- avatar state updates
- memory writes and retrieval
- provider switching
- basic cost tracking
- manual verification notes

## Phase 9 - Voice Stage 1

Goal: push-to-talk STT after text MVP is stable.

Deliverables:

- push-to-talk UI
- audio capture
- STT provider adapter
- no continuous cloud streaming

## Phase 10 - Voice Stage 2

Goal: TTS output.

Deliverables:

- TTS provider adapter
- selective speech policy
- avatar talking state sync

## Phase 11 - Hardware Preparation

Goal: prepare for physical box integration.

Deliverables:

- hardware interface plan
- screen resolution constraints
- microphone/speaker/button assumptions
- local deployment target decision

