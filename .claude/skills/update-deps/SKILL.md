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
4. Update the Python version in README.md, CONTRIBUTING.md and CLAUDE.md (`tests/test_repo_files.py` checks README and CONTRIBUTING against `.python-version`).
5. Check for removed or deprecated stdlib APIs used in `src/`, `tests/`, `scripts/` and `.claude/hooks/` (read the "What's New" page) and fix them.

## 2. Dependencies (rule 6)

```sh
uv tree --outdated --depth 1     # what is behind
uv lock --upgrade                # upgrade everything within the constraints
uv sync
```

Then:

1. Raise the lower bounds in `pyproject.toml` to the new versions so they are explicit (`uv add "pyside6-essentials>=X.Y"`, `uv add --dev "pytest>=X.Y"`). Qt comes from `pyside6-essentials`, not the full `pyside6` (NVG-13, `tests/test_dependencies.py`).
2. For every major or minor upgrade, read the release notes and adapt the code to breaking changes and deprecations.
3. If `uv --version` is outside the `uv_build>=…,<…` range in `[build-system]`, update the range to the current uv minor version. CI installs the newest uv that its pinned `astral-sh/setup-uv` release knows (`version: latest-known`); after a local uv upgrade, bump that pin to a release that knows the new uv (see GitHub Actions below), or a `uv.lock` written by the newer uv can fail CI's locked sync.
4. When online, run `uvx pip-audit` and fix reported vulnerabilities.

### GitHub Actions

Workflows pin every action to a full commit SHA with the version in a comment (`uses: owner/repo@<sha> # vX.Y.Z`), so nothing updates them automatically. The SessionStart hook compares them with each action's latest release and reports the outdated ones ("Action pins: ...", NVG-11); to check by hand, compare each pin with the latest release:

```sh
grep -ho "uses: [^ ]* # v[0-9.]*" .github/workflows/*.y*ml | sort -u
gh api repos/<owner>/<repo>/releases/latest --jq .tag_name
gh api repos/<owner>/<repo>/git/ref/tags/<tag> --jq '.object.type + " " + .object.sha'
```

If the ref's type is `tag` (an annotated tag), resolve it to the commit with `gh api repos/<owner>/<repo>/git/tags/<sha> --jq .object.sha`.

Before accepting a new SHA (a moved tag can point to a malicious commit, as in the 2025 tj-actions incident), wait until the release is at least 7 days old (`gh api repos/<owner>/<repo>/releases/tags/<tag> --jq .published_at`; the hook already waits that long before reporting it), then:

1. The commit must be in the action's own history: `gh api repos/<owner>/<repo>/compare/<default-branch>...<new-sha> --jq .ahead_by` prints `0`. An immutable release (`gh api repos/<owner>/<repo>/releases/tags/<tag> --jq .immutable` is `true`) is safe as well.
2. Skim what changed: `gh api repos/<owner>/<repo>/compare/<old-sha>...<new-sha> --jq '.files[].filename'` and the release notes (changed inputs, new network access).

Then update the SHA and the version comment, and let the next push run CI once to confirm. Once NVG-12 restricts the repository's allowed actions, a new action must also be added there.

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
