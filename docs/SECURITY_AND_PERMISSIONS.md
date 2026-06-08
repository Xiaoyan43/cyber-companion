# Security And Permissions

## Rule

The companion must not have broad access to the user's computer.

All file access must be restricted to explicit allowed folders.

## Allowed Folder Config

Example:

```json
{
  "allowed_folders": [
    {
      "path": "./sandbox",
      "read": true,
      "write": true
    }
  ]
}
```

## File Access Gateway

Every file operation must pass through a gateway that:

1. Resolves the requested path to a real absolute path.
2. Checks it is inside an allowed folder.
3. Rejects `..` path traversal.
4. Rejects symlink escape.
5. Logs the operation.
6. Returns a clear denial reason.

## Disallowed By Default

- Full home directory access.
- Desktop/Documents/Downloads access without explicit folder allowlist.
- Shell execution from the companion.
- Reading browser profiles, credentials, keychains, SSH keys, or token stores.
- Sending local files to an LLM provider without explicit user approval.

## Secret Handling

Do not store API keys in committed files.

Use `.env` or local secret storage. Commit only examples such as `.env.example`.

## Audit Trail

The MVP should log:

- provider calls
- estimated token usage
- memory writes
- file access attempts
- denied file access attempts

## Dev Server Exposure

This project is local-first. Frontend and backend dev servers must stay on localhost unless the user explicitly changes exposure for a controlled test.

Defaults:

- Vite dev/preview: `127.0.0.1:5173` (`frontend/vite.config.ts`, `npm run dev --workspace frontend`)
- FastAPI/Uvicorn: `127.0.0.1:8000` (`scripts/dev_backend.sh`, overridable via `CYBER_COMPANION_API_HOST`)

Rules:

- Do not bind dev servers to `0.0.0.0` or a public interface without a dedicated security review.
- CORS allowlist stays explicit (`backend/app/cors.py`); no wildcard origins.
- Production builds (`npm run build:frontend`) serve static assets only; Vite/esbuild advisories apply to dev-server mode, not shipped `dist/`.
- Run `npm audit` after frontend dependency changes. As of Session 23, Vite was upgraded to 6.4.x and Playwright to 1.60.x so dev audit is clean; re-check before exposing dev beyond localhost.

