---
name: update-deps
description: Upgrade Nvagik to the newest system Python and the latest dependency versions, adapt the code and verify nothing broke (CLAUDE.md rules 5 and 6). Use when the SessionStart report shows Python or dependency drift, or at least once per session before task work.
---

# Update Python and dependencies

## 1. Python follows the system (rule 5)

```sh
py --list            # installed Pythons
py -3 --version      # newest system Python
cat .python-version  # project Python
```

If the system has a newer minor version (for example 3.16 while the project pins 3.15):

1. `uv python pin 3.16` (rewrites `.python-version`).
2. Set `requires-python = ">=3.16"` in `pyproject.toml`.
3. `uv sync`. If a dependency has no wheels for the new Python yet, roll back to the old pin, record the reason in `docs/DECISIONS.md`, add a TASKS.md card to retry, and stop here.
4. Update the Python version in README.md and CLAUDE.md.
5. Check for removed or deprecated stdlib APIs used in `src/`, `tests/`, `scripts/` and `.claude/hooks/` (read the "What's New" page) and fix them.

## 2. Dependencies (rule 6)

```sh
uv tree --outdated --depth 1     # what is behind
uv lock --upgrade                # upgrade everything within the constraints
uv sync
```

Then:

1. Raise the lower bounds in `pyproject.toml` to the new versions so they are explicit (`uv add "pyside6>=X.Y"`, `uv add --dev "pytest>=X.Y"`).
2. For every major or minor upgrade, read the release notes and adapt the code to breaking changes and deprecations.
3. If `uv --version` is outside the `uv_build>=…,<…` range in `[build-system]`, update the range to the current uv minor version.
4. When online, run `uvx pip-audit` and fix reported vulnerabilities.

## 3. Verify

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run nvagik    # must still start (close it after checking)
```

## 4. Record

CHANGELOG `Changed` (and `Security` for vulnerability fixes) with old and new versions, then `/finish-task`.

If PyPI is unreachable, add `--offline` where possible, note it in the session report, and retry later in the session; don't block other work on it.
