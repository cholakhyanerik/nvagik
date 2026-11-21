# Changelog

All notable changes to Nvagik are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html): before 1.0, every finished task bumps the patch version and every finished roadmap phase bumps the minor version.

## [Unreleased]

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

[Unreleased]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/cholakhyanerik/nvagik/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cholakhyanerik/nvagik/releases/tag/v0.1.0
