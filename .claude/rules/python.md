---
paths:
  - "**/*.py"
  - ".claude/hooks/*.py"
---

# Python code

- ruff targets the project Python (`.python-version`) and writes `except A, B:` without parentheses (PEP 758, valid since Python 3.14). Don't "fix" it.
- The PostToolUse hook formats every edited Python file with ruff (format plus import order).
- `str.splitlines()` also splits at U+2028, U+2029, U+0085 and a few control characters. Split text from outside (gh output, git branch names) at `"\n"` only.
- Hooks (`.claude/hooks/`) run with the system Python: standard library only.
