# CLAUDE.md: Nvagik

Nvagik is a free, open-source (GPL-3.0-or-later) DAW for Windows built with Python, PySide6 and uv, with an Armenian, Russian and English interface.

- Product, roadmap, risks, open questions: [README.md](README.md)
- Backlog to 1.0 (source of truth for work): [TASKS.md](TASKS.md)
- History: [CHANGELOG.md](CHANGELOG.md) · Decisions: [docs/DECISIONS.md](docs/DECISIONS.md)
- Guide for outside contributors: [CONTRIBUTING.md](CONTRIBUTING.md), a short public summary of these rules. When a rule, a command, the commit format or the CI checks change, update it too; `tests/test_repo_files.py` checks its commit types against CLAUDE.md, its checks against the `run:` steps of `ci.yml`, its Python version against `.python-version` and its links against git's file list.
- `PRIVATE.md` (git-ignored) holds the owner's business and bank details. Never commit, copy, move or quote it.

**Talk to the owner in Russian**, in simple words, and explain jargon. Everything written into the repository (code, comments, docs, CHANGELOG, commit messages) is in **English**.

## Owner's rules

These always apply. Rule numbers are referenced from hooks and skills.

1. **Autonomy.** Rely on yourself. Don't ask anyone and don't wait for answers. Don't hand tasks to the owner (don't ask them to do anything by hand). Do everything that needs doing yourself. If something is unclear, pick the most reasonable option, record the decision and the reason in [docs/DECISIONS.md](docs/DECISIONS.md), and carry on.
   *Only exception:* steps that spend money, sign agreements or need the owner's identity (buying a domain, Partner Center registration, Store submission). Prepare everything, mark the task `Blocked (owner)` in TASKS.md with exact steps, mention it in the session report, and keep working on other tasks.
2. **Optimized code, speed first.** Speed is the top product rule: fast start, instant response, low memory. Measure, don't guess. A feature that slows the app down is optimized or not accepted. See [Performance budgets](#performance-budgets).
3. **Never break what works.** New code must not break old code. Run the full test suite before every commit, add a regression test for every bug fix, keep old project files loadable (migrations), and never weaken or delete a test to make it pass.
4. **Security is a top priority.** See [Security](#security).
5. **Python follows the system.** The project uses the newest Python installed on this machine (now 3.15). When the system Python is upgraded, upgrade the project in the same session with `/update-deps`.
6. **Dependencies stay current.** At the start of every session, check dependencies first (the SessionStart hook reports it). If updates exist, upgrade them and adapt the code with `/update-deps` before task work.
7. **Three languages by default:** Armenian (AM, Qt locale `hy`), Russian (RU, `ru`), English (EN, `en`, the source language). No user-facing text is hard-coded. See `/i18n`.
8. **Follow the project design and improve UI/UX where possible.** [docs/DESIGN.md](docs/DESIGN.md) (created by NVG-120) is the source of truth. Until it exists, keep UI minimal and consistent. Improvements that don't fit the current task go into TASKS.md.
9. **TASKS.md is always current.** Tasks are written like Jira/Trello cards and kept as small as possible. In every session, update, improve and split tasks, and delete finished ones. See `/add-task`.
10. **Bugs are fixed now, not filed.** A bug or defect found while working is fixed in the same session (with a regression test). New tasks and improvements go into TASKS.md.
11. **Definition of done** after every task, via `/finish-task`: CHANGELOG, version, README and CLAUDE.md updated (all in English), then commit and push **without asking**, then delete junk (temporary files etc.).
12. **GitHub Actions minutes are shared** across the owner's many repositories. See [GitHub Actions budget](#github-actions-budget).
13. **Web means Cloudflare.** Anything on the web (the landing page, domains) uses Cloudflare: Workers static assets for hosting and Cloudflare Registrar for domains.
14. **Subagents inherit the session's model and effort.** Agent files use `model: inherit` and have no `effort` key, and `.claude/settings.json` sets `CLAUDE_CODE_SUBAGENT_EFFORT=inherit`. Never pin a model or effort level in an agent.

## Session workflow

1. Read the SessionStart hook report (Python, dependencies, GitHub security, git state, next tasks). Private vulnerability reports come first: answer them within 7 days as SECURITY.md promises (rule 4). If it shows Python or dependency drift or open Dependabot alerts, run `/update-deps` first (rules 5 and 6).
2. Run `/next-task`: take the first task in TASKS.md "Next up" whose dependencies are done, split it if it is bigger than `S`, and set it to `In Progress`.
3. Implement in small steps with tests. Fix any bug you meet along the way (rule 10).
4. Run `/finish-task` (rule 11). Then continue with the next task.

## Commands

Use uv for everything; never call `pip`.

| Purpose | Command |
| --- | --- |
| Install / sync | `uv sync` |
| Run the app | `uv run nvagik` |
| Tests | `uv run pytest` |
| Lint / format | `uv run ruff check .` · `uv run ruff format .` |
| Add a dependency | `uv add <pkg>` · dev only: `uv add --dev <pkg>` |
| Outdated dependencies | `uv tree --outdated --depth 1` |
| Bump the version | `uv version --bump patch` (or `minor`) |
| Remove junk | `py -3 scripts/clean.py` |

If PyPI is unreachable, add `--offline` to uv commands (the uv cache has the dev tools) and retry the online checks later.

## Architecture rules

- Layout: application code in `src/nvagik/`, tests in `tests/`, helper scripts in `scripts/`, docs in `docs/`.
- **Windows only.** No code paths or conditional branches for other operating systems.
- **Audio callback rule.** Inside the audio callback: no file I/O, no memory allocation, no locks, no logging, no Qt calls. Buffers are preallocated; heavy math runs in NumPy or other compiled code. The engine talks to the UI only through lock-free queues and counters that the UI polls with a `QTimer`.
- **Qt is `pyside6-essentials`**, not the full `pyside6` (NVG-13). A feature that needs an Addons module (Charts, Multimedia, WebSockets, ...) adds `pyside6-addons` with a docs/DECISIONS.md entry and to `ALLOWED_QT` in `tests/test_dependencies.py`. Qt's own translations are loaded as `qtbase_<lang>`, never `qt_<lang>` (that one needs an Addons file and fails silently).
- **Lazy imports.** Heavy modules (NumPy, sounddevice, soundfile, MIDI, plugins) are imported when first needed, never at startup.
- **No hard-coded UI text.** Use `self.tr()` / `QCoreApplication.translate()`; placeholders via `.format()` with names; plurals via `tr(text, "", n)`.
- **Design tokens only.** Colors, fonts and spacing come from the theme module, never inline.
- **Untrusted input.** Project files, audio, MIDI and plugin data are untrusted. Validate sizes and types, keep paths inside the project folder, never use `pickle`, `eval` or `exec` on them.
- **Project files stay compatible.** Every format change bumps the schema version and adds a migration with a test fixture.
- **Version** lives only in `pyproject.toml`; the app reads it with `importlib.metadata`.

## Performance budgets

These are initial targets and will be refined with measurements in `docs/PERFORMANCE.md` (NVG-106, NVG-242).

| Metric | Budget |
| --- | --- |
| Launch to interactive window (release build) | ≤ 1.5 s |
| Idle memory, empty project | ≤ 150 MB |
| Audio callback time | ≤ 50 % of the buffer period on average, ≤ 80 % worst case |
| Underruns in the 10-minute playback test | 0 |
| Meters and playhead redraw | 30 fps without stutter |

## Security

- **Private data never enters git.** No PRIVATE.md, PDFs, `.env` files, keys, tokens, personal e-mail addresses, tax, bank or ID numbers. Commits use the GitHub noreply e-mail. The guard hook enforces this; if it blocks you, remove the leak. Never bypass the hook.
- **No secrets in code.** If a secret is ever needed, read it from the environment or Windows Credential Manager (`keyring`), never from the repo.
- **The app makes no network requests** and collects no data unless a task explicitly adds a feature that needs it.
- **Plugins are untrusted native code.** Scan them in a separate process; a crashing plugin must not take the app down.
- **New dependencies** must be well known, maintained, license-compatible and have Windows wheels for the current Python. Check them before `uv add`, and run `uvx pip-audit` when online.
- **GitHub security features** (NVG-3): Dependabot alerts, secret scanning, push protection and private vulnerability reporting are on; Dependabot security-update PRs are off on purpose (docs/DECISIONS.md). Check with `gh api repos/cholakhyanerik/nvagik --jq .security_and_analysis` and `gh api repos/cholakhyanerik/nvagik/private-vulnerability-reporting`.
- **History is not rewritten** except to remove leaked data, and then only with `--force-with-lease`.
- Use the `security-auditor` agent for anything touching file parsing, subprocesses, plugins, networking, CI or these hooks.

## Versioning, CHANGELOG and git

- [Semantic Versioning](https://semver.org/). Before 1.0: every finished task bumps **PATCH**, every finished phase bumps **MINOR** (Phase 0 → 0.2.0, … Phase 6 → 0.8.0), and the Store release is **1.0.0**.
- [CHANGELOG.md](CHANGELOG.md) follows [Keep a Changelog](https://keepachangelog.com/). Each version has a date and lists task IDs. A test checks that the current version has an entry.
- Commit directly to `main` and push after every task without asking (the owner's rule). Message format: `<type>(<scope>): <summary> (NVG-<id>)` with types `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`.
- Tag every version: `git tag -a vX.Y.Z -m "vX.Y.Z"` and `git push origin main --follow-tags`.
- GitHub is available through the `gh` CLI (account `cholakhyanerik`, repository `cholakhyanerik/nvagik`, public).

## GitHub Actions budget

The owner has many repositories that use GitHub Actions, so keep this one from adding load:

- Verify locally first (tests, ruff). CI is a safety net, not the place to experiment.
- Trigger only on pushes to `main` and on pull requests. Skip docs-only changes (`paths-ignore: ['**.md', 'docs/**']`). No `schedule`, no matrix builds unless a task needs them.
- Every workflow sets `concurrency` with `cancel-in-progress: true` and `timeout-minutes` (≤ 10), caches uv, and pins actions to commit SHAs with `permissions: contents: read`.
- Standard GitHub-hosted runners are free for public repositories, but keep the habits anyway: they also protect the owner's private repositories, which share the monthly quota.
- The only workflow is `.github/workflows/ci.yml` (NVG-8): one `windows-latest` job running `uv sync`, `ruff check`, `ruff format --check` and `pytest`, with a pruned uv cache that only pushes to `main` save. `tests/test_ci_workflows.py` enforces the rules above for every workflow file and also rejects `${{ }}` expressions outside an allowlist, self-hosted runners, `continue-on-error`, `if:` conditions, secrets and unusual YAML spellings. Pins look like `uses: owner/repo@<full sha> # vX.Y.Z`; `/update-deps` refreshes them.
- Watch the run after a push (it takes a few seconds to appear; `gh run watch` needs a run ID outside a terminal): `id=$(gh run list --workflow ci.yml --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId')`, then `gh run watch "$id" --exit-status --compact`.

## Claude Code setup in this repository

**Hooks** (`.claude/settings.json`; scripts in `.claude/hooks/`, stdlib-only, run with `py -3`):

| Hook | Script | What it does |
| --- | --- | --- |
| SessionStart | `session_start.py` | Reports system vs project Python, outdated dependencies, uv vs `uv_build`, private vulnerability reports waiting for triage and open Dependabot alerts (via `gh`, in parallel with the dependency check), git state and the next tasks. Tested in `tests/test_session_start.py` |
| PreToolUse (Bash, PowerShell) | `guard.py` | Blocks deleting, moving, copying or overwriting PRIVATE.md (incl. globs like `*.md`), `git clean -x`, `git stash --all`, `git add -f`, force pushes (`-f`, `+refspec`), and commits, pushes and `gh` uploads whose files, history, commit/tag messages or author/tagger e-mails contain private files, secrets, personal e-mails or PRIVATE.md values. Files that diffs show as binary (`binary` in `.gitattributes`, UTF-16) are read whole from the object database; text up to 8 MB is scanned whole, larger text, Git LFS pointers and pushed blobs or trees (tags, refspec sources) are blocked as unscannable; pushes also cover merges, a detached HEAD, root commits and explicit refspec sources. `git rm --cached PRIVATE.md` stays allowed. Tested in `tests/test_guard*.py` |
| PostToolUse (Edit, Write) | `format_py.py` | Formats the edited Python file with ruff (format plus import order) |
| Stop | `stop_check.py` | If changes are uncommitted or unpushed, reminds you once to run `/finish-task` |

Hook changes take effect in a new session (or after opening `/hooks`).

**Subagents** (`.claude/agents/`, all `model: inherit`, no `effort`, see rule 14):

| Agent | Use it for |
| --- | --- |
| `code-reviewer` | Every non-trivial change before commit: bugs, regressions, performance, project rules |
| `security-auditor` | Changes to parsing, subprocesses, plugins, networking, CI, hooks; pre-release audit |
| `performance-auditor` | Startup, memory, audio callback and UI rendering measurements against the budgets |
| `ui-ux-reviewer` | Any UI change: design-system compliance, accessibility, HiDPI, text length in RU/HY |
| `i18n-translator` | Extracting strings and writing Armenian and Russian translations |
| `deps-updater` | Rules 5 and 6: Python and dependency upgrades with code adaptation |

**Skills** (`.claude/skills/`): `/next-task`, `/finish-task`, `/update-deps`, `/add-task`, `/i18n`.

Keep this setup improving: when a task teaches you something reusable (a convention, a gotcha, a better command), add it here or to the matching skill as part of `/finish-task`.

## Gotchas

- On 2026-11-21 PyPI was temporarily unreachable from this machine while GitHub worked. Use `--offline` and retry later; don't block task work on it.
- `.gitattributes` keeps every text file in LF, on disk too (`* text=auto eol=lf`, overriding `core.autocrlf`). Only `*.bat` and `*.cmd` use CRLF. When a new binary file type enters the repo (audio, images, fonts, packages), add it there as `binary`; `tests/test_gitattributes.py` checks the rules and that no file is stored with CRLF.
- Hook scripts run with the system Python (`py -3`), not the venv, so they must use only the standard library.
- Strings that look like secrets in tests must be assembled at run time (`"ghp_" + "A" * 36`), otherwise the guard blocks the commit.
- The guard reads the literal command text: a command that merely mentions deleting PRIVATE.md (even inside `echo`) is blocked. Put test payloads in files and pipe them in (`py -3 .claude/hooks/guard.py < payload.json`).
- The guard also treats every argument of `sed -i` (the script too) as a path, and it splits commands at `(` and `)` even inside quotes. A script containing `/Nvagik` (the repository folder name) is then blocked as "touching the project root". Use the Edit tool for such edits.
- The Stop hook blocks the first stop while the tree is dirty. If the work is intentionally unfinished (the owner asked to pause), say so and stop again.
- Widget tests use pytest-qt on the `offscreen` platform (`tests/conftest.py`): take `qtbot`, register every top-level widget with `qtbot.addWidget(w)`, and wait with `qtbot.waitSignal` / `qtbot.waitUntil`, never `time.sleep`. Any Qt warning fails the test (`qt_log_level_fail`); fix the cause, or add a known harmless message to `qt_log_ignore` in pyproject.toml (the offscreen "This plugin does not support ..." messages already are). `pytest -s` turns that check off (pytest-qt only captures Qt messages while output is captured), so never use `-s` in CI. Offscreen needs `QT_QPA_FONTDIR` (set to the Windows fonts folder), otherwise Qt has no fonts and text metrics are wrong; its default font is Arial, not Segoe UI.
- ruff targets Python 3.15 and writes `except A, B:` without parentheses (PEP 758). That is valid; don't "fix" it.
- When the owner pauses mid-task, save the exact remaining steps to memory so the next session can continue.
- Merge outside pull requests on GitHub (`gh pr merge --squash`), then `git pull --rebase`. Don't merge them locally and push: the guard blocks a push whose new commits have an author or committer e-mail that is not noreply, and a contributor's commits may use their own address.
- Don't write Python source through a shell heredoc with escapes like `\0` or `\n`: the shell and Python unescape them twice and the file can end up with NUL bytes or broken strings. Use the Write tool (or write to the scratchpad and copy).
