Local MCP servers must follow one fixed convention inside `src/mcps`:

1. Create one directory per MCP.
2. Put the entrypoint in `server.py`.
3. Keep the final structure as `src/mcps/<mcp-name>/server.py`.

Example:

```text
src/mcps/
  my-local-mcp/
    server.py
```

Use the same shape when creating new local MCPs: keep tools small, typed, JSON-serializable, and easy to test from the admin panel.

The admin panel and backend can scan `src/mcps` to discover local MCP candidates. Any directory that contains `server.py` is treated as a local MCP source.

For local MCPs:

- The admin UI shows the detected MCPs in a dropdown.
- The platform creates the MCP record only when you add it manually from the UI or API.
- `command` and `working_directory` are generated internally.
- The runtime launches local MCPs with `python server.py` from that MCP directory.

For remote MCPs:

- Keep using the `url` field in the admin panel.
- Optional protocol-specific settings stay under "More settings".
