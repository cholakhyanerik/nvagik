# Changelog

All notable changes to Nvagik are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html): before 1.0, every finished task bumps the patch version and every finished roadmap phase bumps the minor version.

## [Unreleased]

## [0.1.17] - 2026-11-23

### Added

- Owner's rule 15, "CLAUDE.md stays short" (NVG-18): about 200 lines, at most 400, because the file loads whole into every session. Details live in path-scoped `.claude/rules/*.md` files (`hooks`, `github`, `python`, `tests`, `qt`, `docs`, `repo-files`), which Claude Code loads only when a matching file is read.
- `tests/test_claude_md.py`: CLAUDE.md has at most 400 lines and 30,000 characters and no `@` imports; the owner's rules are numbered 1, 2, 3, ...; every "rule N" cited in the repository exists; every rules file has `paths:` frontmatter whose patterns each match a file; CLAUDE.md lists every rules file, and no file names one that doesn't exist; the `#anchor` links in CLAUDE.md and README.md resolve; the Security section keeps its key rules.
- The SessionStart hook reports CLAUDE.md when it is over the 200-line target, asks for action above the test's limits (without reading a huge file whole), and asks to restore it when it is missing or not UTF-8.

### Changed

- CLAUDE.md is about a quarter shorter (19,602 to 14,984 characters): the hook descriptions, the CI budget details, the GitHub settings checks, the test and Qt gotchas moved to the rules files, and dated notes were dropped. Security rules stay in CLAUDE.md, which every session loads.
- `/finish-task` puts new conventions and gotchas into the matching rules file instead of CLAUDE.md, and now has the commands to watch the CI run.
- `code-reviewer`, `security-auditor` and `i18n-translator` read the rules files that apply to their work. The CI workflow, its test and the Stop hook point to the new places.

### Security

- `/next-task` binds a contributor's merged pull request to the reviewed commit: the session report names the reviewed commit, the owner merges only while it is still the latest one, and before pulling, the agent checks that the merged head is the commit it approved and that only allowed paths changed. GitHub merges the current head, and `main` has no rule that dismisses an approval after a new push, so a commit pushed after the review would otherwise run on this machine at the next pull.
- `/next-task` no longer accepts Python files under `tests/fixtures/` from contributors: pytest collects `conftest.py` and other `.py` files anywhere under `tests/`.

## [0.1.16] - 2026-11-22

### Security

- CI runs of fork pull requests now wait for approval for every external contributor, not only first-time ones (NVG-17, applied by the owner), so no stranger's code runs in CI before the agent has read the diff. CLAUDE.md lists the check command.

## [0.1.15] - 2026-11-22

### Security

- Repository Actions settings (NVG-12), applied by the owner: every action must be pinned to a full commit SHA, and only GitHub-owned actions plus `astral-sh/setup-uv` may run. A CI run under the new settings passed. `tests/test_ci_workflows.py` mirrors the allow list, so a workflow with any other action fails locally first; CLAUDE.md lists the check commands, and `/update-deps` says how a new action gets allowed.

### Changed

- TASKS.md: the remaining step, requiring CI approval for all external contributors, is its own card, NVG-17 (`Blocked (owner)`: the permission check refused the change).

## [0.1.14] - 2026-11-22

### Added

- The SessionStart hook reports pinned GitHub Actions that are behind their latest release (NVG-11): `Action pins: 1 outdated (actions/checkout v7.0.1 -> v7.1.0) -> ACTION (rule 6): run /update-deps before any other work`. It reads the `- uses: owner/repo@<sha> # vX.Y.Z` lines in `.github/workflows/` (whole lines only, so commented-out steps don't count; the oldest pin of an action counts), asks `gh` for each action's latest release in parallel with the other checks (8 s timeout, at most 16 actions, 8 at a time), and compares versions as numbers with up to four parts. A release counts only once it is 7 days old, because hijacked releases (tj-actions, 2025) are usually found and pulled within days. Release tags come from other people's repositories, so only plain version numbers are reported; anything else, and a `gh` failure for one action, shows as "could not check". When `gh` cannot tell for any action, there is no line.
- `tests/test_ci_workflows.py` accepts only the pin form the hook reads (ASCII names of GitHub's length, versions of up to four parts with up to six digits each), and a test checks that the hook sees every pin.

### Fixed

- One SessionStart check failing (for example a workflow, `TASKS.md` or `pyproject.toml` that is not valid UTF-8) used to crash the whole hook, so the session started without any report, including the security lines. Each check now costs only its own line ("could not check"), and files that are not UTF-8 are treated like missing ones.

## [0.1.13] - 2026-11-22

### Added

- The SessionStart hook reports open issues and pull requests, oldest first, and the cards they claim (NVG-14), in parallel with the other GitHub checks. Their titles and bodies are untrusted, so the hook prints only numbers, the `NVG-<id>`s it extracts itself (ASCII digits only) and fixed words. A claim counts only for a card still in TASKS.md and not in "Next up", from an item naming at most 3 cards, by someone who is not a maintainer or a bot, not labelled `not-a-claim`, with activity in the last 30 days, and for at most 3 cards per person; the first claim on a card wins. Each skipped card names its issue (`NVG-205 (#12)`), draft pull requests are not offered for review, and the item list stops after 20. When `gh` fails or returns something unexpected, it says so in one line.
- `/next-task` reviews up to 2 contributors' pull requests per session before task work, without ever checking them out, applying or running them: it reads the fetched diff (`refs/pr/<n>`) in full, checks paths and file modes, lets CI run the code, approves only the first-time CI run for the reviewed commit, and passes the same rules to its reviewer agents. It approves a good pull request and reports it to the owner, who merges it; it never merges one itself. It skips pull requests still waiting for the contributor, skips claimed cards (also when refilling "Next up"), confirms a real claim once or labels a mere mention `not-a-claim`, releases pull requests the owner merged, and runs the check of `Blocked (owner)` cards every session.
- TASKS.md: NVG-16 (a script that pre-checks contributors' pull requests, so hostile diffs are not read every session). NVG-12 also asks the owner to require approval of CI runs for all external contributors.

### Changed

- CONTRIBUTING.md: claim limits (one to three cards per issue, three per person, 30 days without activity lapses), pull requests may change only the app code, tests (not the tooling tests), text test files and the CHANGELOG, the maintainer's assistant reviews and the maintainer merges, and new dependencies start with an issue.
- CLAUDE.md Security: contributors' issues and pull requests are untrusted; read pull requests only as a fetched diff, never check them out or run them; the owner merges.
- NVG-12 is `Blocked (owner)`: Claude Code's permission check refused the repository settings change again, so the card now holds the steps for the owner.
- Agents keep their temporary files in their own subfolder of the scratchpad and delete only that: a reviewer cleaning up had removed the caller's drafts.

### Security

- The guard scans the text of every `gh` call, recognised in any case, quoted, as a full path and with `-R owner/repo`. Calls that publish text (issue and pull request comments, reviews, edits, merges and reopens, releases, gists, repository settings, labels, workflow inputs, `gh api` writes) also scan every file they read (`--body-file`, `-F`, `--notes-file`, `--input`, `field=@file`) and may not hide text: command substitution, variables, subexpressions, redirects, directory changes, `--attach`, standard input other than a heredoc, and missing, binary or unclear text files are blocked. The agent writes such replies right after reading strangers' text, the classic path from prompt injection to a leak.
- The guard blocks `gh auth token`, `gh auth status --show-token`, `git credential fill`, `gh pr checkout` (and the `gh co` alias), gh aliases and extensions, piping a pull request's diff (`gh pr diff`, or `git diff`, `git show`, `git format-patch` of `refs/pr/` or `pull/`) into `git apply` or `git am`, and git commands that put `refs/pr/` or `pull/` commits into a work tree, where a pull request's hooks would run at once.
- The guard never opens network paths (`\\host\share`, `//host/share`) named in a command: on Windows that would send the login to the host before any prompt.
- The guard also treats e-mail addresses from PRIVATE.md as private values, and `ya`, `inbox`, `list`, `bk` and `rambler` addresses as personal.

### Fixed

- The guard dropped the rest of a `<<EOF` line together with the heredoc body, so `cat <<'EOF' | git commit -F -` skipped the commit scan and `cat <<'EOF' > PRIVATE.md` or `cat <<'EOF' && rm PRIVATE.md` were allowed. That text now stays, and a `<<EOF` inside quotes or a comment no longer hides the lines after it (inside `"$(...)"` it is still a heredoc, as in bash).
- The guard's personal e-mail pattern took quadratic time on long runs like `a.a.a...` (100 KB: 49 s, over the hook's timeout); it now finds the same addresses in linear time.
- The SessionStart hook split `git status` output with `str.splitlines()`, which also cuts at U+2028, U+2029 and U+0085, characters git allows in branch names: such a branch name could carry free text into the report. It now splits at `\n` only and does not print unusual branch names. The new claims check splits gh output the same way.

## [0.1.12] - 2026-11-22

### Added

- `tests/test_dependencies.py` allows only `pyside6-essentials` among the PySide packages in `uv.lock` and checks that Qt's Russian strings (`qtbase_ru`) still load.

### Changed

- Qt now comes from `pyside6-essentials` instead of the full `pyside6` (NVG-13), which also pulled `pyside6-addons`, `pyside6-webengine` and `pyside6-pdf` that the app does not use. Qt wheels to download for Windows: 259.2 MB → 83.4 MB (175.8 MB less in every CI run); `.venv` on disk: about 700 MB → about 260 MB. The modules the app plans to use and the `pyside6-lupdate`, `pyside6-lrelease` and `pyside6-deploy` tools are in Essentials. One catch: Qt's `qt_ru.qm` also needs a file from the Addons, so NVG-112 loads `qtbase_<lang>` instead (written into the card, the i18n skill and CLAUDE.md).
- `/update-deps` raises the `pyside6-essentials` bound instead of `pyside6`; CONTRIBUTING.md tells contributors that the Addons modules are not installed.
- TASKS.md: NVG-117 (Armenian translation of Qt's own strings, because Qt ships none).

## [0.1.11] - 2026-11-21

### Changed

- Repository topics on GitHub (NVG-10): `daw`, `digital-audio-workstation`, `music`, `music-production`, `audio`, `pyside6`, `qt`, `python`, `windows`, `armenian`, so the project shows up in GitHub's topic pages and search.
- TASKS.md: the social preview image moved to its own card, NVG-15, which waits for the app icon (NVG-122). GitHub has no API for uploading it, so the card already holds the exact steps in case it needs the owner's browser.

## [0.1.10] - 2026-11-21

### Added

- `CONTRIBUTING.md` (NVG-9): a short guide for outside contributors covering setup with uv, the checks to run (and that pull requests changing only Markdown or `docs/` skip CI), the main project rules (speed first, Windows only, three languages, don't break what works, security, design tokens, dependencies), the commit format and pull request steps. Contributions are accepted under GPL-3.0-or-later (inbound = outbound, as in GitHub's Terms of Service), with no CLA; code from elsewhere must be usable under GPL-3.0-or-later and name its source. The guide says openly that Store builds may become paid. GitHub now shows it on new issues and pull requests, and the README links to it.
- `tests/test_repo_files.py` keeps the guide from drifting: its commit types must match CLAUDE.md, its checks must match the `run:` steps of `ci.yml` in both directions, README and the guide must name the Python version in `.python-version`, and its relative links must match git's file list exactly (NTFS would accept a wrongly cased name that GitHub cannot open).
- TASKS.md: NVG-14 (session start reports open issues and pull requests, and `/next-task` skips cards a contributor has claimed); NVG-808 now also covers e-mail addresses in third-party license notices, which the guard would block.

### Changed

- `/finish-task` moves lines left under `[Unreleased]` by merged pull requests into the new version; `/update-deps` also updates the Python version in CONTRIBUTING.md.
- CLAUDE.md links the guide and notes that outside pull requests are merged on GitHub, because the guard blocks pushing commits with a non-noreply e-mail.

### Fixed

- The README setup commands were in an `sh` block with `#` comments, which cmd.exe passes to the program as arguments. They are now marked as PowerShell, where `#` starts a comment.

## [0.1.9] - 2026-11-21

### Added

- Continuous integration (NVG-8): `.github/workflows/ci.yml` runs `uv sync`, `ruff check`, `ruff format --check` and `pytest` on `windows-latest` for pushes to `main` and pull requests, skipping docs-only changes. It follows the Actions budget: one job, `timeout-minutes: 10`, older runs cancelled, read-only token, no schedules or matrix. `UV_LOCKED` makes the run fail if `uv.lock` is out of date, and ruff errors appear inline on pull requests. The README shows the CI badge.
- `tests/test_ci_workflows.py` checks every workflow file against the budget and security rules, failing closed on anything it cannot read: triggers, read-only permissions (no job-level permissions), concurrency, timeouts, GitHub-hosted runners only, actions pinned to full commit SHAs with a `# vX.Y.Z` comment, `${{ }}` expressions from an allowlist only (no event data such as pull request titles, so no script injection), no secrets, no `continue-on-error` or `if:` that could switch checks off, checkout without a stored token, and the uv settings below.
- `/update-deps` now also refreshes the pinned actions, checks that a new SHA is in the action's own history (or an immutable release) before accepting it, and keeps CI's uv version in step with the local one.
- TASKS.md: NVG-11 (report outdated action pins at session start), NVG-12 (enforce pinning and allowed actions in the repository settings) and NVG-13 (depend on `pyside6-essentials` to download about 175 MB less per CI run).

### Security

- CI installs uv only in versions whose checksums the pinned `astral-sh/setup-uv` release bundles (`version: latest-known`, `require-checksums: true`). Only pushes to `main` save the uv cache, so pull requests from forks cannot fill or replace it, and caching is off for tag and release events (`enable-cache: auto`). The cache is pruned to locally built wheels, because its key changes with every version bump and a full cache (about 650 MB) would be uploaded on every push and never restored.

## [0.1.8] - 2026-11-21

### Added

- Headless widget tests (NVG-7): `pytest-qt` 4.5.0 is a dev dependency and `tests/conftest.py` forces the Qt `offscreen` platform, so tests never open windows on screen and behave the same locally and in CI. pytest-qt is pinned to PySide6 (`qt_api = "pyside6"`), and a Qt warning during a test fails it (`qt_log_level_fail = "WARNING"`), because Qt warnings usually mean real bugs. The offscreen platform's own "This plugin does not support ..." messages (resizing a shown window, popups, keyboard grab) are ignored.
- `tests/test_qt_offscreen.py`: example widget tests (button click, typing into a line edit, a main window with a combo box and a menu popup) that run in about 0.2 s together, a check that offscreen text uses real fonts, and a check that a real Qt warning fails a test while offscreen limits do not. `tests/conftest.py` enables pytest's `pytester` plugin for such in-process test runs.

### Fixed

- On Windows the offscreen platform looks for fonts inside PySide6, which ships none: widgets had no fonts, Qt printed a `QFontDatabase` warning and text measured about twice its real width. `tests/conftest.py` points `QT_QPA_FONTDIR` to the Windows fonts folder, so Latin, Cyrillic and Armenian text in a named font gets native metrics. NVG-121 now also sets the application font, because the offscreen default font is Arial, not Segoe UI.

## [0.1.7] - 2026-11-21

### Added

- GitHub Sponsors button on the repository page (NVG-6): `.github/FUNDING.yml` with `github: cholakhyanerik`, and the repository's Sponsorships feature turned on. The README "Support the project" section mentions the button. `tests/test_repo_files.py` checks the file.

## [0.1.6] - 2026-11-21

### Added

- `.gitattributes` (NVG-5): every text file is stored and checked out with LF line endings, also on Windows (`* text=auto eol=lf`); `*.bat` and `*.cmd` keep CRLF; audio, MIDI, SoundFonts, plugins and presets, images, icons, compiled translations, fonts, NumPy test data, archives, Store packages and native code are marked binary. Git no longer warns "LF will be replaced by CRLF". `git add --renormalize .` found nothing to change, because the index was already LF.
- `tests/test_gitattributes.py` checks the attributes with `git check-attr`, that the binary list matches `.gitattributes`, and that no tracked file is stored with CRLF (unless it opts out with `-text`). It is skipped outside a git checkout.

### Security

- The guard hook no longer misses secrets in files that diffs show as binary. With the new `binary` attributes, `git log -p` printed "Binary files ... differ" for a text file named, for example, `notes.png`, so a token in it could be pushed. UTF-16 files had the same gap on push (an older gap), and a staged file deleted from the working copy was not scanned on commit. Such files are now read whole from the object database (`--full-index` patches and `git cat-file`), and textconv is disabled.
- A security review of that fix closed further gaps in the guard: UTF-32 files, UTF-16 without a BOM (also mostly Russian or Armenian text) and text with stray NUL bytes are decoded, while binary tables such as fonts are not taken for text; text files up to 8 MB are scanned whole (before: skipped above 1 MB) and larger ones are blocked as unscannable; Git LFS pointers are blocked (their content would be uploaded unscanned); git output is read as bytes and split on `\n` only, so a `\r` in a file or a U+2028 in a file name can no longer fake or hide diff lines; pushes also scan merge commits (against the first parent), a detached HEAD, root commits when `log.showRoot` is off, and explicit refspec sources such as `stash@{0}:refs/heads/x` or a commit on no branch; pushing a blob or tree (as a source or through a tag) is blocked, and the tag check only runs when tags are pushed.
- Every gap has a regression test in `tests/test_guard_repo.py` or `tests/test_guard.py`.

## [0.1.5] - 2026-11-21

### Added

- `SECURITY.md` (NVG-4): vulnerabilities are reported privately through GitHub's "Report a vulnerability" form; only the latest release gets fixes before 1.0; first answer within 7 days, fix within 90 days, credit in the advisory; scope covers file parsing, plugin scanning and loading (plugins themselves are not sandboxed), release builds including bundled dependencies, and the development hooks, scripts and CI workflows.
- README "Project documents" lists `SECURITY.md`.
- `tests/test_repo_files.py` checks that the security policy points to private reporting and contains no e-mail address.

### Changed

- The SessionStart hook also reports private vulnerability reports waiting for triage and open Dependabot alerts (via `gh`, in parallel with the dependency check), so the 7-day answer promised in `SECURITY.md` is not missed. `/next-task` handles them first, treats report text and attachments as untrusted, and avoids early disclosure. Tested in `tests/test_session_start.py`.

## [0.1.4] - 2026-11-21

### Security

- GitHub security features enabled on the repository (NVG-3): Dependabot alerts (the dependency graph reads `uv.lock`), secret scanning with push protection, and private vulnerability reporting. Dependabot security-update pull requests stay off, because dependencies are upgraded every session and extra pull requests would only add CI runs.

## [0.1.3] - 2026-11-21

### Added

- `LICENSE` with the verbatim GNU GPL v3 text (NVG-2).
- `license = "GPL-3.0-or-later"` and `license-files` in pyproject.toml, so built packages carry the license in their metadata and include `LICENSE`.
- `tests/test_license.py` checks the license text against the official SHA-256 and the declared license in pyproject.toml and in the installed metadata.

## [0.1.2] - 2026-11-21

### Changed

- License decided: GPL-3.0-or-later (NVG-1). It keeps `pedalboard` (GPL-3.0) available for VST3 hosting, allows paid Microsoft Store builds of the open code (as Krita does) and keeps forks open. The comparison with MIT/Apache-2.0 is in `docs/DECISIONS.md`.
- README: "License" section, the repository rule and open question 1 updated; open question 7 notes that the license allows a paid Store build.
- TASKS.md: the About dialog (NVG-133), VST3 spike (NVG-610), CONTRIBUTING (NVG-9), Store decision (NVG-23) and Store submission (NVG-812) cards now follow from the license; new card NVG-808 ships license notices with release builds.

## [0.1.1] - 2026-11-21

### Added

- `CLAUDE.md` with the owner's development rules: autonomy, speed first, no regressions, security, Python and dependencies kept current, three interface languages (AM/RU/EN), design and UI/UX, always-current task list, bugs fixed immediately, definition of done, GitHub Actions budget, Cloudflare for the web, and subagents inheriting the session's model and effort.
- `TASKS.md`: Jira-style backlog of small tasks for everything needed to ship 1.0 (project setup, decisions, roadmap phases 0–6 and the Microsoft Store release).
- `CHANGELOG.md` and `docs/DECISIONS.md` (decision log).
- Claude Code hooks: a session-start check (system vs project Python, outdated dependencies, git state, next tasks), a git guard, automatic ruff formatting of edited Python files, and a reminder to finish uncommitted work.
- Claude Code subagents: `code-reviewer`, `security-auditor`, `performance-auditor`, `ui-ux-reviewer`, `i18n-translator`, `deps-updater`.
- Claude Code skills: `/next-task`, `/finish-task`, `/update-deps`, `/add-task`, `/i18n`.
- Development tools: pytest and ruff (with performance and security rule sets), tests for the app entry point, version/CHANGELOG consistency and the TASKS.md format, plus unit and end-to-end tests of the guard hook against throwaway git repositories.
- `scripts/clean.py` to remove build, test and temporary junk after each task.

### Changed

- README: development commands, project documents, landing page on Cloudflare.
- `.gitignore`: tool caches, secrets and private documents, personal Claude Code settings.

### Security

- The guard hook blocks deleting, moving, copying or overwriting `PRIVATE.md`, `git clean -x`, `git stash --all`, `git add --force` and force pushes, and scans commits, pushes and `gh` uploads (file contents, the whole unpushed history, commit and tag messages, author and tagger e-mails) for private files, secrets, personal e-mail addresses and values from `PRIVATE.md`. A security review found and fixed bypasses for non-ASCII file names, UTF-16 files, files outside the current folder, history-only secrets and alternative git syntax.
- `scripts/clean.py` refuses to run when git cannot list tracked files, so it can never delete tracked files.

## [0.1.0] - 2026-11-21

### Added

- Initial uv project for Python 3.15 with PySide6 (`uv run nvagik` prints a greeting).
- README with the project description, principles, technical rules, roadmap, distribution and revenue model, risks, open questions and the name availability check.

[Unreleased]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.17...HEAD
[0.1.17]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.16...v0.1.17
[0.1.16]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.15...v0.1.16
[0.1.15]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.14...v0.1.15
[0.1.14]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.13...v0.1.14
[0.1.13]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.12...v0.1.13
[0.1.12]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cholakhyanerik/nvagik/releases/tag/v0.1.0
