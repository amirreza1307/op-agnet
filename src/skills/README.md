# Skills

Local Agno skill packages live under this directory.

Each skill should be a folder containing at least a `SKILL.md` file.

Example:

```text
src/skills/
  vendor-policy/
    SKILL.md
    references/
      faq.md
    scripts/
      helper.py
```

In the platform API, `skill_packages.source_path` can be either:

- a relative path like `vendor-policy`
- or a nested relative path like `ops/vendor-policy`

Paths are resolved relative to `src/skills`.
