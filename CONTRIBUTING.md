# Contributing to Nvagik

Thank you for helping! Nvagik is a free, open-source DAW for Windows, written in Python with PySide6 and uv. It is in early development, so the code changes quickly; this short guide keeps contributions easy to review and merge.

## Before you start

- **Find or propose a task.** The backlog to 1.0 is in [TASKS.md](TASKS.md). Cards listed in its "Next up" section are about to be worked on by the maintainer, so pick another card or a bug you found. Before you start anything bigger than a small fix, open an [issue](https://github.com/cholakhyanerik/nvagik/issues) that names the card (for example `NVG-205`) and what you plan to do, and wait for an answer, so work is not done twice. While that issue or your pull request is open and active, the maintainer leaves the card to you. Name one card per issue, or at most three closely related ones: an issue naming more is not read as a claim, and one person can hold at most three cards at a time. A claim with no activity (comments or commits) for 30 days lapses, and the card is free again.
- **Security problems are never reported in public.** Follow [SECURITY.md](SECURITY.md) instead.

## Set up

You need Windows, Python 3.15 and [uv](https://docs.astral.sh/uv/). The commands below are for PowerShell.

```powershell
git clone https://github.com/cholakhyanerik/nvagik.git
cd nvagik
uv sync          # create .venv and install everything, including dev tools
uv run nvagik    # run the app
```

Use uv for everything and never call `pip`. A change that needs a new dependency starts with an issue: the maintainer checks the package and adds it with `uv add`, because pull requests that change `pyproject.toml` or `uv.lock` are not merged as they are (see below).

## Check your change

Run these before every commit, and make sure all of them pass:

```powershell
uv run ruff format .   # format
uv run ruff check .    # lint
uv run pytest          # all tests; widget tests run headless, no windows open
```

CI runs the same checks on pull requests that change code; for a first-time contributor, the run starts after the maintainer approves it. Changes to Markdown files alone (such as your `CHANGELOG.md` line) skip CI, so run `uv run pytest` yourself: some tests check the Markdown files.

## Project rules

The full list is in [CLAUDE.md](CLAUDE.md); these matter most.

- **Speed first.** Fast start, instant response, low memory. Measure instead of guessing: a change that slows the app down is optimized or not accepted. Heavy modules (NumPy, sounddevice, soundfile, MIDI, plugins) are imported when first needed, never at startup. Inside the audio callback there is no file I/O, no memory allocation, no locks, no logging and no Qt call.
- **Windows only.** No code paths or conditional branches for other operating systems, so pull requests that add macOS or Linux support are not accepted.
- **Three languages.** The interface is in Armenian (`hy`), Russian (`ru`) and English (`en`, the source language). No user-facing text is hard-coded: use `self.tr()` or `QCoreApplication.translate()`, named placeholders with `.format()` and plurals with `tr(text, "", n)`. If you cannot write the Armenian or Russian translation, say so in the pull request and it will be added.
- **Don't break what works.** The full test suite passes before every commit. Every bug fix comes with a regression test. Never weaken or delete a test to make it pass. Old project files must keep loading: every format change bumps the schema version and adds a migration with a test file.
- **Security.** Project files, audio, MIDI and plugin data are untrusted: validate sizes and types, keep paths inside the project folder, and never use `pickle`, `eval` or `exec` on them. The app makes no network requests. Never commit secrets, keys or personal data.
- **Design.** Colors, fonts and spacing come from the theme, never inline.
- **Dependencies** must be well known, maintained, GPL-compatible and have Windows wheels for the current Python. Qt comes from `pyside6-essentials`, so modules from `pyside6-addons` (QtMultimedia, QtCharts, QtWebSockets and others) are not installed: open an issue before using one.
- **English** for code, comments, docs and commit messages.

## Commits and pull requests

Commit messages follow this format:

```text
<type>(<scope>): <summary> (NVG-<id>)
```

- `type` is one of `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`.
- `(<scope>)` is optional and names the area you changed, for example `audio`, `ui` or `i18n`.
- `(NVG-<id>)` names the [TASKS.md](TASKS.md) card; leave it out if the change has no card.
- Example: `fix(audio): reopen the stream after the device changes (NVG-211)`.

For pull requests:

- Branch from `main` and keep each pull request small, about one task or fix.
- Describe what changed and why, and how you tested it.
- Add a line under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md). The maintainer moves it into the next version.
- Change only the app code in `src/nvagik/`, tests in `tests/test_*.py`, text test files in `tests/fixtures/` and your line in `CHANGELOG.md`, with no binary files or symlinks. Pull requests that touch the tooling or the project documents (`.claude/`, `.github/`, `scripts/`, `pyproject.toml`, `uv.lock`, `tests/conftest.py`, the tests of the tooling such as `tests/test_guard*.py`, `CLAUDE.md`, `TASKS.md`, `README.md`, `docs/` and the like) are not merged as they are, for security reasons. Suggest such a change in an issue instead; the maintainer makes it.
- The maintainer's assistant reviews your pull request and the maintainer merges it. Push new commits to answer a review; a force push is fine.
- To keep your e-mail address private, commit with your [GitHub noreply address](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).

The maintainer develops with Claude Code, so the repository contains a `.claude/` folder with hooks and agents. You don't need it: the hooks only run inside Claude Code.

## License of contributions

Nvagik is licensed under the [GNU General Public License v3.0 or later](LICENSE) (GPL-3.0-or-later). Contributions are accepted under the same license ("inbound = outbound"), as GitHub's [Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#6-contributions-under-repository-license) also provide. There is no separate contributor agreement (CLA), and you keep the copyright in your work.

By opening a pull request, you confirm that:

- you wrote the contribution yourself, or have the right to submit it under GPL-3.0-or-later;
- code taken from elsewhere is under a license that allows its use under GPL-3.0-or-later (for example MIT, BSD, Apache-2.0, or GPL or LGPL version 3 or later), keeps its original copyright and license notice, and the pull request names its source and license.

Ready-made builds in the Microsoft Store may become paid later. The GPL allows this: your contribution stays under the GPL, and everyone who gets a build is entitled to its source code.
