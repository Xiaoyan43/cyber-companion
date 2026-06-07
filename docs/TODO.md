# TODO

## Current Priority

- [x] Create foundational project files and cross-tool rules.
- [x] Add open-source reuse policy.
- [x] Create project scaffold.
- [x] Build local dev scripts.
- [x] Create basic frontend shell.
- [x] Create basic backend health check.

## Backlog

### UI

- [ ] Pixel character renderer.
- [ ] State animation definitions.
- [ ] Chat panel.
- [ ] Avatar state debug controls.
- [ ] Trapped-in-box idle behaviors.

### Provider Layer

- [ ] Define provider interface.
- [ ] Add DeepSeek adapter.
- [ ] Add OpenAI adapter placeholder.
- [ ] Add local model adapter placeholder.
- [ ] Add provider config file.
- [ ] Add cost estimate metadata.

### Memory

- [ ] Define SQLite schema.
- [ ] Add database initialization.
- [ ] Add message persistence.
- [ ] Add memory CRUD.
- [ ] Add mood state persistence.
- [ ] Add retrieval policy.
- [ ] Add summary policy.

### Behavior

- [ ] Define behavior decision contract.
- [ ] Implement local state variables.
- [ ] Implement reply/silent/refuse/interrupt/proactive decisions.
- [ ] Add persona prompt.
- [ ] Add structured LLM response parser.

### Security

- [ ] Add allowed folders config.
- [ ] Implement path permission gateway.
- [ ] Add file access log.
- [ ] Add symlink escape tests.
- [ ] Review Vite/esbuild dev-server audit advisory before exposing dev server beyond localhost.

### Voice

- [ ] Design push-to-talk STT interface.
- [ ] Add STT adapter placeholder.
- [ ] Add TTS adapter placeholder.
- [ ] Define selective speech policy.

### Documentation

- [ ] Update docs after each milestone.
- [x] Add developer setup once scaffold exists.
- [ ] Add manual verification checklist.
- [ ] Evaluate open-source candidates before building major modules from scratch.

### Maintenance

- [ ] Review FastAPI TestClient/httpx2 deprecation warning.
