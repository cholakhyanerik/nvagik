# Decisions

Decisions made while building Nvagik, newest first. CLAUDE.md rule 1: when something is unclear, choose the most reasonable option, record it here with the reason, and continue. Open product questions live in the [README](../README.md#open-questions) until a decision task in [TASKS.md](../TASKS.md) closes them.

| Date | Decision | Why |
| --- | --- | --- |
| 2026-11-22 | Qt comes from `pyside6-essentials` (NVG-13), not the full `pyside6`. A feature that needs an Addons module (Charts, Multimedia, WebSockets and so on) adds `pyside6-addons` then, with its own entry here. | `pyside6` is a meta package that also pulls `pyside6-addons`, `pyside6-webengine` and `pyside6-pdf`, none of which the app uses. Essentials has every module Nvagik plans to use (QtCore, QtGui, QtWidgets, QtSvg, QtOpenGL, QtTest) and the `pyside6-lupdate`, `pyside6-lrelease` and `pyside6-deploy` tools. Audio goes through sounddevice, so QtMultimedia is not needed. Qt wheels to download for Windows: 259.2 MB → 83.4 MB; `.venv` on disk: about 700 MB → about 260 MB. Qt's own translations must then be loaded as `qtbase_<lang>`, because the `qt_<lang>` meta file also needs `qtmultimedia_<lang>` from the Addons. `tests/test_dependencies.py` allows only `pyside6-essentials` among the PySide packages and checks that `qtbase_ru` loads. |
| 2026-11-21 | Repository topics (NVG-10): `daw`, `digital-audio-workstation`, `music`, `music-production`, `audio`, `pyside6`, `qt`, `python`, `windows`, `armenian`. The social preview image waits for the app icon (NVG-15). | The card's seven topics plus three that people search for DAW and Qt projects with (`digital-audio-workstation`, `music-production`, `qt`). `armenian` stays as the card asked because an Armenian interface is what sets Nvagik apart; more language topics would only dilute the list. GitHub has no API for uploading a social preview, so a placeholder image now would need the owner's browser twice; one upload with the real icon is enough. Check with `gh repo view cholakhyanerik/nvagik --json repositoryTopics`. |
| 2026-11-21 | Contributions (NVG-9) are accepted under GPL-3.0-or-later (inbound = outbound), with no CLA and no DCO sign-off; by opening a pull request the contributor confirms they may submit the code, and code from elsewhere must be usable under GPL-3.0-or-later (MIT, BSD, Apache-2.0, GPL or LGPL 3 or later; not GPL-3.0-only or AGPL), keep its notice and name its source. CONTRIBUTING.md is a short summary of CLAUDE.md, not a second rulebook. Pull requests that change only Markdown or `docs/` skip CI (the Actions budget requires `paths-ignore`), so the guide asks contributors to run the tests themselves and the maintainer runs them before merging. | Inbound = outbound is already the default in GitHub's Terms of Service (section D.6), so a CLA would only add friction for a small project; a DCO `Signed-off-by` line adds a step that people forget and that CI would have to check. The accepted cost: relicensing later needs every contributor's consent, which the license decision (NVG-1) already accepts. The guide says openly that Store builds may become paid, so contributors know before they contribute. Pointing to CLAUDE.md for the full rules, plus tests for the parts that drift (commit types, CI checks, links), keeps the two files from contradicting each other. |
| 2026-11-21 | CI (NVG-8) is one `windows-latest` job; actions are pinned to full commit SHAs; uv comes from the pinned setup-uv release with bundled checksums; the uv cache is pruned and saved only by pushes to `main`; Python is the runner's preinstalled 3.15. | One job keeps the shared Actions minutes low (rule 12). SHA pins and checksums keep the build from changing under us; a moved tag cannot inject code. setup-uv restores only exact cache keys, and the key hashes `uv.lock`, which every task's version bump changes, so a full cache would be uploaded on every push and never used: pruning keeps only wheels built in CI and downloads PyPI wheels each run, as setup-uv recommends for hosted runners. Saving only on `main` stops fork pull requests from evicting or replacing the cache. The runner image already has Python 3.15, so uv uses it and no Python cache is needed. Repository settings that enforce pinning (NVG-12) were refused by Claude Code's permission check in an unattended session and wait for the owner's approval. |
| 2026-11-21 | Widget tests (NVG-7) run on the Qt `offscreen` platform with the Windows fonts folder as `QT_QPA_FONTDIR`, and any Qt warning fails a test. | Offscreen keeps tests headless and identical in CI. Without the fonts folder Qt finds no fonts on Windows and text measures about twice its real width, which would make the later Russian and Armenian text-fit checks meaningless; loading the fonts costs about 20 ms per test run. Qt warnings (broken connections, painter errors) are usually real bugs; the offscreen platform's own "This plugin does not support ..." messages are ignored (`qt_log_ignore`). |
| 2026-11-21 | GitHub security (NVG-3): Dependabot alerts, secret scanning, push protection and private vulnerability reporting are on; Dependabot security-update pull requests stay off. | Alerts cost nothing and the dependency graph reads `uv.lock`. Dependencies are already upgraded every session (rule 6), and automatic pull requests would only add CI runs (rule 12). Generic-pattern secret scanning and validity checks need a paid GitHub Secret Protection license and could not be enabled; the guard hook covers generic secrets locally. |
| 2026-11-21 | License: GPL-3.0-or-later (NVG-1). | Keeps `pedalboard` (GPL-3.0) for VST3 hosting, still allows paid Store builds of the open code, and blocks closed forks. Full comparison: [License](#license-nvg-1). |
| 2026-11-21 | Each finished task bumps PATCH, each finished phase bumps MINOR, the Store release is 1.0.0. | The owner wants a version and CHANGELOG entry after every task; phases map naturally to minor versions. |
| 2026-11-21 | Steps that spend money, sign agreements or need the owner's identity are `Blocked (owner)` tasks, the only exception to full autonomy. | The agent cannot legally or financially act for the owner; everything else is prepared so the owner only clicks. |
| 2026-11-21 | Subagents use `model: inherit` with no `effort` key, plus `CLAUDE_CODE_SUBAGENT_EFFORT=inherit` in project settings. | The owner wants subagents on the session's model and effort. Agent frontmatter accepts `inherit` for the model but only fixed levels for effort; leaving effort unset makes agents follow the session (verified in Claude Code 2.1.329). |
| 2026-11-21 | Dev tooling: pytest for tests, ruff for lint and format (rules include `PERF` and `S`). | Standard, fast, uv-friendly; the performance and security rule sets match the project's top priorities. |
| 2026-11-21 | Claude hooks are stdlib-only Python scripts run with `py -3`. | Same language as the project; works before `uv sync` and keeps reporting the system Python version (rule 5). |
| 2026-11-21 | Business and bank details live in the git-ignored `PRIVATE.md`; a hook blocks committing its values. | The repository is public, and leaked history is practically impossible to remove. |
| 2026-11-21 | Commits use the GitHub noreply e-mail (global git config); history was rewritten once to remove the personal e-mail. | Privacy of the owner in a public repository. |
| 2026-11-21 | Repository is public at `cholakhyanerik/nvagik`, default branch `main`. | Open repository is a core principle of the project. |
| 2026-11-21 | Product name: Nvagik (backups: Yergik, Dzaynik). | See the name availability check in the README. |

## Details

### License (NVG-1)

**Decided on 2026-11-21: GPL-3.0-or-later.**

| Question | GPL-3.0-or-later | MIT or Apache-2.0 |
| --- | --- | --- |
| VST3 hosting (Phase 5) | [`pedalboard`](https://github.com/spotify/pedalboard) (GPL-3.0, built on JUCE under JUCE's GPL option) can be shipped. DawDreamer, the other maintained Python host, is GPL-3.0 as well. | Neither GPL host can be shipped. The VST3 SDK itself is [MIT since version 3.8](https://www.soundonsound.com/news/steinberg-adopt-mit-license-vst3) (October 2025), but using it directly means writing and maintaining our own C++ host extension: outside the fixed Python + PySide + uv stack, and a large job. |
| Other planned dependencies | All compatible: PySide6 (LGPL-3.0), NumPy (BSD-3-Clause), sounddevice and PortAudio (MIT), soundfile (BSD-3-Clause) with libsndfile (LGPL-2.1-or-later), mido and python-rtmidi (MIT). | All compatible. |
| Selling Store builds of open code (revenue stage B) | Allowed. The GPL lets anyone charge for copies as long as buyers get the source under the GPL, and the repository is public. Precedents: [Krita](https://krita.org/en/about/license/) sells its GPL-3.0 build in the Microsoft Store and on Steam while the same build is free on krita.org; Ardour, a GPL DAW, sells ready-made binaries. Partner Center's [license terms field](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/add-additional-information) takes the publisher's own terms (a link to `LICENSE`) instead of Microsoft's Standard Application License Terms. | Allowed; the Store build could even become closed later. |
| Copies and forks | Anyone may redistribute the build (even for free) and fork the code, but every distributed fork must stay open under the GPL. | Anyone may turn the code into a closed, paid product. |
| Relicensing later | Needs the consent of every contributor. Irrelevant while `pedalboard` is used, because it is GPL anyway. | Easy. |

**Why GPL-3.0-or-later:**

1. VST3 hosting is a 1.0 feature, and in Python it is practical today only through `pedalboard` (or DawDreamer), both GPL-3.0.
2. It does not block the paid stage: open code with a paid Store build is a proven model under the GPL (Krita).
3. It protects the owner's work from closed commercial forks, which matters for a solo project that will later be paid.
4. "Or later" (the FSF's recommendation) lets the project move to a future GPL version without asking every contributor. The program combined with `pedalboard` is distributed under GPL-3.0.

**Accepted downsides:**

- Buyers may legally share the Store build. People pay for convenience, automatic updates and supporting development (the Krita model).
- The license does not protect the name "Nvagik"; the Partner Center reservation (NVG-810) does that for the Store.

**Not affected:** users can load any VST3 plugin, including closed-source ones. The GPL governs what we distribute, not what users combine on their own computer.

**Follow-ups:**

- NVG-2: `LICENSE` with the verbatim GPL-3.0 text and `license = "GPL-3.0-or-later"` in pyproject.toml.
- NVG-133: the About dialog shows the license with the no-warranty notice (GPL section 5(d), "Appropriate Legal Notices") and links to the source of the running version.
- NVG-808: release builds include `LICENSE` and the licenses of bundled third-party packages.
- NVG-9 (done in 0.1.10): CONTRIBUTING.md accepts contributions under GPL-3.0-or-later (inbound = outbound).
- NVG-23 and NVG-812: Store terms checked (Krita once had a dispute with Microsoft over Store policy 10.8.5 about mentioning the free download); the Partner Center license field points to `LICENSE`.
