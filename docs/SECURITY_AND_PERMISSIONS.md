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

