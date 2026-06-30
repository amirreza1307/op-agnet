# CLAUDE.md

Guidance for Claude Code when working in `src/tools`.

## Scope

This directory contains the agent tool-service foundation:

- `base_tool.py` defines shared schemas, lifecycle contract, session helpers, auth-header forwarding, action logging, and error payload helpers.
- `registry.py` defines explicit slug-based tool registration and lookup.

## Tool service contract

Every concrete tool service must inherit from `BaseToolService` and implement:

- nested `Input(ToolInputSchema)` class
- nested `Output(ToolOutputSchema)` class
- async `run(self) -> dict[str, Any]`

Use `_abstract = True` only for intermediate abstract base classes that should not declare `Input`/`Output`.

`BaseToolService.__init__` validates forwarded kwargs through `self.Input`; access parsed values via `self.input`.

`BaseToolService` also wraps every concrete `run()` method with DB-managed
knowledge output. The `@register_tool` slug is used to load active rows from
`platform.tool_knowledge_nodes`; ordered knowledge nodes are returned under
`knowledge_nodes`, followed by the original result under `tool_output`.
Concrete tools do not need to opt in or change their `run()` implementation.

## Registration rules

Register concrete tools with:

```python
@register_tool(slug="stable-slug", name_fa="نام فارسی")
class SomeToolService(BaseToolService):
    ...
```

Rules:

- `slug` is stable platform/DB identifier. Do not rename casually.
- duplicate slugs fail at import time.
- empty slugs fail at import time.
- `name_fa` is admin-facing Persian display name.
- registry maps `slug -> ToolRegistration -> service_class`.

## Discovery behavior

`load_registry()` imports every Python module under package `tools`, skipping:

- `_*.py`
- `base_tool.py`
- `registry.py`

It is idempotent. Lookup helpers lazily load registry on miss.

## Session helpers

Use built-in helpers instead of duplicating session parsing:

- `_vendor_id()` for current vendor id
- `_user_id()` for current principal/user id
- `_principal_id()` for string principal id when optional
- `_session_id()` for current session id when optional
- `_forwarded_auth_headers()` for forwarded lowercase auth headers

Missing required vendor/user context raises `ValueError("Vendor context is missing")` or `ValueError("User context is missing")`.

## Action logging

For tools that return an envelope with an `action` block, call:

```python
await self._record_action_view(payload)
```

Call right before returning output. Logging is best-effort and must not break propose paths.

Required action fields for logging:

- `payload["action"]["domain"]`
- `payload["action"]["operation"]`

## Error payloads

Use `_error_payload(message, status=...)` for consistent tool errors.

Default status is `ToolErrorStatusEnum.ERROR`.

## Style

- Keep registry explicit and slug-based.
- Keep `BaseToolService` generic; avoid tool-specific logic there.
- Prefer Pydantic schema validation over manual kwarg parsing.
- Preserve async `run()` contract.
- Keep imports lightweight in registry paths; broad imports happen during `load_registry()`.
- Do not swallow import failures silently in registry; current behavior logs exceptions.

## Testing checklist

When changing this directory, verify:

- concrete services without `Input`/`Output` fail at class creation.
- duplicate slugs fail during module import.
- `load_registry()` remains idempotent.
- lazy lookup still loads registry on miss.
- session helper behavior stays compatible with camelCase and snake_case keys.
