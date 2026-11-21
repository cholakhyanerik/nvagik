# Changelog

All notable changes to Nvagik are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html): before 1.0, every finished task bumps the patch version and every finished roadmap phase bumps the minor version.

## [Unreleased]

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

[Unreleased]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.8...HEAD
[0.1.8]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cholakhyanerik/nvagik/releases/tag/v0.1.0
