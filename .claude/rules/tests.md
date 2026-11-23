---
paths:
  - "tests/**"
---

# Tests

- Widget tests use pytest-qt on the `offscreen` platform (`tests/conftest.py`):
  - take `qtbot` and register every top-level widget with `qtbot.addWidget(w)`;
  - wait with `qtbot.waitSignal` / `qtbot.waitUntil`, never `time.sleep`.
- Any Qt warning fails the test (`qt_log_level_fail`). Fix the cause, or add a known harmless message to `qt_log_ignore` in pyproject.toml (the offscreen "This plugin does not support ..." messages already are).
- `pytest -s` turns that check off (pytest-qt only captures Qt messages while output is captured), so never use `-s` in CI.
- Offscreen needs `QT_QPA_FONTDIR` (set to the Windows fonts folder), otherwise Qt has no fonts and text metrics are wrong. Its default font is Arial, not Segoe UI.
- Strings that look like secrets must be assembled at run time (`"ghp_" + "A" * 36`), otherwise the guard blocks the commit.
- Every bug fix gets a regression test; never weaken or delete a test to make it pass (rule 3).
- The tooling tests (hooks, CI, repository files, CLAUDE.md, TASKS.md) are listed in `/next-task`: contributors' pull requests may not change them.
