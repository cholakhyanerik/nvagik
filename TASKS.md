# Nvagik tasks

Everything that has to be done to ship **Nvagik 1.0** (roadmap phases 0–6 from the [README](README.md#roadmap), plus the Microsoft Store release). Phase 7 ("parity") is out of scope for 1.0; its tasks will be planned after the 1.0 release.

**How this file works** (details: `.claude/skills/add-task/SKILL.md`):

- Update it in every session: delete finished tasks (they move to [CHANGELOG.md](CHANGELOG.md)), refine and split the rest, add new tasks and improvements as they come up.
- Bugs found while working on a task are fixed in the same session and are **not** added here.
- Tasks are as small as possible. Sizes: `XS` ≤ 1 hour, `S` ≤ half a day, `M` ≤ 1 day. Anything bigger must be split.
- Priority: `P0` blocks the current phase, `P1` needed for 1.0, `P2` needed for 1.0 but can wait, `P3` nice to have.
- Status: `To Do`, `In Progress` or `Blocked (owner)`. A dependency that no longer appears in this file is done.
- IDs (`NVG-<n>`) are never reused. Hundreds group the epics: 1–99 project setup and decisions, 100 = Phase 0, 200 = Phase 1, … 800 = Release.
- `Blocked (owner)` is only for steps that spend money, sign agreements or need the owner's identity (see CLAUDE.md, rule 1). Everything else is done by the agent.

## Next up

1. NVG-13: Depend on pyside6-essentials instead of the full pyside6
2. NVG-100: App bootstrap module
3. NVG-120: Design system v0
4. NVG-130: Add sounddevice
5. NVG-400: Spike: MIDI libraries on Python 3.15
6. NVG-610: Spike: VST3 hosting
7. NVG-20: Decide the minimum Windows version

## Project setup and repository

### NVG-11: Report outdated GitHub Actions pins at session start
**Type:** Task · **Priority:** P3 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] `session_start.py` reads the `uses: owner/repo@<sha> # vX.Y.Z` pins in `.github/workflows/`, compares them with each action's latest release via `gh` (in parallel with the other checks, short timeout, quiet when offline) and reports the outdated ones, so `/update-deps` handles them (rule 6).
- [ ] Tested in `tests/test_session_start.py` with `gh` faked.

### NVG-12: Enforce action pinning in the repository settings
**Type:** Chore · **Priority:** P2 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] Repository Actions settings require full-SHA pins and allow only GitHub-owned actions plus `astral-sh/setup-uv@*`: `gh api -X PUT repos/cholakhyanerik/nvagik/actions/permissions -F enabled=true -f allowed_actions=selected -F sha_pinning_required=true`, then `gh api -X PUT repos/cholakhyanerik/nvagik/actions/permissions/selected-actions -F github_owned_allowed=true -F verified_allowed=false -f 'patterns_allowed[]=astral-sh/setup-uv@*'`. `tests/test_ci_workflows.py` only catches drift, because a pull request can edit the test. On 2026-11-21 Claude Code's permission check refused this settings change in an unattended session, so it needs the owner's approval of the command.
- [ ] Checked with `gh api repos/cholakhyanerik/nvagik/actions/permissions`; the check is added to the CLAUDE.md security-features line and recorded in docs/DECISIONS.md; a CI run still passes.

### NVG-13: Depend on pyside6-essentials instead of the full pyside6
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] `pyproject.toml` depends on `pyside6-essentials` (QtCore, QtGui, QtWidgets, QtTest, QtSvg, QtOpenGL; not QtMultimedia, which audio does not need because it uses sounddevice) instead of `pyside6`, which also pulls `pyside6-webengine` (131.7 MB wheel), `pyside6-addons` (40.5 MB) and `pyside6-pdf` (3 MB) that the code does not use. About 175 MB less to download in every CI run and a smaller installer (rule 2). A later feature that needs an Addons module adds `pyside6-addons` then.
- [ ] uv.lock no longer contains webengine, addons or pdf; `uv run pytest` passes and `uv run nvagik` starts; download and `.venv` sizes before and after recorded in the CHANGELOG; decision in docs/DECISIONS.md.

### NVG-14: Respect cards that contributors have claimed
**Type:** Task · **Priority:** P2 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] `session_start.py` reports open issues and pull requests (via `gh`, in parallel with the other checks, short timeout, quiet when offline) with the `NVG-<id>` they name; titles and bodies are untrusted text, so only numbers and IDs are reported. `/next-task` reviews open pull requests before task work and skips a card named in an open issue or pull request (CONTRIBUTING.md asks contributors to claim cards that way).
- [ ] Tested in `tests/test_session_start.py` with `gh` faked.

### NVG-15: Repository social preview image
**Type:** Chore · **Priority:** P3 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-122
- [ ] `docs/assets/social-preview.png` (1280 × 640 px, under 1 MB) shows the app icon and the name; made from the NVG-122 icon with design tokens from docs/DESIGN.md.
- [ ] Uploaded under Settings → General → Social preview, and `gh repo view cholakhyanerik/nvagik --json usesCustomOpenGraphImage` returns `true`. On 2026-11-21 GitHub had no API for this upload (only the web page, signed in as the owner); if that is still true, set the card to `Blocked (owner)` with these steps: open `https://github.com/cholakhyanerik/nvagik/settings`, click **Edit** under "Social preview", **Upload an image**, choose the file.

## Decisions

### NVG-20: Decide the minimum Windows version
**Type:** Decision · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] Windows 10 vs Windows 11 only, based on Microsoft's current lifecycle (Windows 10 support ended on 2025-10-14; check whether consumer ESU still applies), PySide6 support and market share.
- [ ] Recorded in docs/DECISIONS.md and README; open question 4 closed.

### NVG-21: Decide the project file format
**Type:** Decision · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] Format chosen (recommended: a project folder with a versioned, human-readable `*.nvagik` JSON file plus an `audio/` folder), with how audio is referenced and how future versions migrate old files.
- [ ] Recorded in docs/DECISIONS.md; open question 5 closed.

### NVG-22: Decide when to support ASIO
**Type:** Decision · **Priority:** P2 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-203
- [ ] WASAPI latency results from the Phase 1 spikes compared with what ASIO would add; ASIO licensing and PortAudio build checked.
- [ ] Recorded in docs/DECISIONS.md; open question 3 closed.

### NVG-23: Decide the Store edition and the paid model
**Type:** Decision · **Priority:** P2 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] Free vs paid Store edition, one-time purchase vs subscription, price, trial, timing of the switch, and how it fits the GPL-3.0-or-later license (Store policies for paid open-source apps checked, including policy 10.8.5 from the Krita case).
- [ ] Recorded in docs/DECISIONS.md; open questions 2, 6 and 7 closed.

### NVG-24: Decide the Partner Center account type
**Type:** Decision · **Priority:** P2 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] Individual vs Company for the sole proprietorship, and whether payouts to an Armenian bank account are supported (Microsoft docs checked).
- [ ] Recorded in docs/DECISIONS.md; open question 8 closed; owner steps written into NVG-810.

## Phase 0: Skeleton

### NVG-100: App bootstrap module
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-7
- [ ] `src/nvagik/app.py` creates the `QApplication` (organization and app name, version from package metadata) and returns the exit code.
- [ ] `uv run nvagik` and `uv run python -m nvagik` both start the app.
- [ ] Offscreen test covers app creation.

### NVG-101: Main window shell
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-100
- [ ] `QMainWindow` titled "Nvagik" with menu bar (File, Edit, View, Help) and status bar; all texts go through `tr()`.
- [ ] Offscreen test opens and closes the window.

### NVG-102: Remember window geometry
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-101, NVG-104
- [ ] Size, position and maximized state are saved on close and restored on start.

### NVG-103: Logging
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-100
- [ ] Rotating log in `%LOCALAPPDATA%\Nvagik\logs` (size-limited); no personal data in logs.
- [ ] Logging is never called from the audio callback (documented in CLAUDE.md).

### NVG-104: Settings storage
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-100
- [ ] One small wrapper over `QSettings` (INI in `%APPDATA%\Nvagik`) with typed getters and defaults; tested.

### NVG-105: Global error handler
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-103
- [ ] Uncaught exceptions are logged and shown in a translated, friendly dialog with "copy details"; the app does not silently die.

### NVG-106: Startup benchmark and performance log
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-101
- [ ] `scripts/bench_startup.py` measures launch-to-window time and idle memory (median of 5 runs).
- [ ] `docs/PERFORMANCE.md` created with the baseline and the budgets from CLAUDE.md.

### NVG-107: Import-time budget test
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-106
- [ ] Test fails if heavy modules (numpy, sounddevice, soundfile, mido) are imported during startup instead of lazily.

### NVG-110: Translation extraction script
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-101
- [ ] `scripts/i18n.py extract` runs `pyside6-lupdate` over `src/` and updates `src/nvagik/i18n/nvagik_hy.ts` and `nvagik_ru.ts` (English is the source language).

### NVG-111: Compile translations into the package
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-110
- [ ] `scripts/i18n.py build` runs `pyside6-lrelease`; `.qm` files are packaged and loaded from package resources.

### NVG-112: Load the interface language at startup
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-111, NVG-104
- [ ] Language = saved setting, else the Windows UI language if it is hy/ru, else English; Qt's own strings translated too.
- [ ] Test switches each of hy/ru/en and checks one translated string.

### NVG-113: Language menu with live switching
**Type:** Story · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-112
- [ ] View → Language: Հայերեն, Русский, English; the UI retranslates without restart (`LanguageChange` handled).

### NVG-114: Translation completeness test
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-110
- [ ] Test fails if a `.ts` file has unfinished or missing translations, or placeholders/shortcuts that differ from the source.

### NVG-115: Armenian glyph and font check
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-113
- [ ] Armenian text renders without missing glyphs on Windows (font fallback chosen and set in the theme); screenshot checked.

### NVG-116: DAW terminology glossary
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] `docs/GLOSSARY.md`: EN/RU/HY table of core terms (track, clip, mixer, send, bus, piano roll, quantize, latency, …) used by all translations.

### NVG-120: Design system v0
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] `docs/DESIGN.md`: color tokens (dark theme first), typography, spacing, radii, icon style, states, contrast rules (WCAG AA).

### NVG-121: Theme implementation
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-120, NVG-101
- [ ] `src/nvagik/ui/theme.py` builds the QSS/palette from the tokens; applied at startup; no colors or fonts hard-coded elsewhere.
- [ ] The theme sets the application font explicitly (the offscreen test platform otherwise defaults to Arial, the real Windows platform to Segoe UI), and widget tests apply the theme, so text widths measured in tests match the app. `tests/test_qt_offscreen.py` uses the theme font instead of the hard-coded "Segoe UI".

### NVG-122: Placeholder app icon
**Type:** Task · **Priority:** P2 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-120
- [ ] Multi-size `.ico` in the package; used for the window and taskbar.

### NVG-123: HiDPI check
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-121
- [ ] UI checked at 100/150/200 % scaling (offscreen screenshots); nothing blurry or clipped.

### NVG-130: Add sounddevice
**Type:** Spike · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] `sounddevice` installs and works on Python 3.15 (bundled PortAudio); result recorded in docs/DECISIONS.md.

### NVG-131: Audio device service
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-130
- [ ] `src/nvagik/audio/devices.py` lists host APIs and devices (WASAPI first, default device marked), imported lazily.
- [ ] Unit tests with a fake backend, no audio hardware needed.

### NVG-132: Device list in the main window
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-131, NVG-121
- [ ] The main window shows output and input devices grouped by host API; loading does not block the UI.

### NVG-133: About dialog
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-101
- [ ] Shows version, the GPL-3.0-or-later license with its no-warranty notice (GPL section 5(d)), a link to the source of the running version (its git tag) and the GitHub Sponsors donation link (required by the README); translated.

### NVG-134: Phase 0 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-113, NVG-132, NVG-133, NVG-106
- [ ] `uv run nvagik` opens the window with the device list in all three languages, within the startup budget.
- [ ] Version bumped to 0.2.0 and tagged.

## Phase 1: Audio core

### NVG-200: Spike: audio callback timing harness
**Type:** Spike · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-130
- [ ] Script plays a sine via `sounddevice` and records callback duration, jitter and underruns at 128/256/512 frames; results in docs/PERFORMANCE.md.

### NVG-201: Spike: GC and GIL impact under UI load
**Type:** Spike · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-200
- [ ] Same harness with a busy Qt UI; compares `gc.freeze()`/`gc.disable()` during playback and documents the effect.

### NVG-202: Spike: audio engine in a separate process
**Type:** Spike · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-200
- [ ] Prototype with `multiprocessing.shared_memory` ring buffers; compares underruns and latency with the in-thread engine.

### NVG-203: Decide the audio engine architecture
**Type:** Decision · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-201, NVG-202
- [ ] Thread vs process chosen from the measurements; recorded in docs/DECISIONS.md and the architecture rules in CLAUDE.md.

### NVG-210: Lock-free ring buffer
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-203
- [ ] Single-producer/single-consumer ring over a preallocated NumPy array; no allocation on read/write; unit tests incl. wrap-around.

### NVG-211: Engine: open and close the output stream
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-210
- [ ] Engine opens the selected device with sample rate and buffer size, starts/stops cleanly, recovers from device loss.

### NVG-212: Engine to UI messaging
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-211
- [ ] Commands go to the engine through a lock-free queue; status (position, xruns, meters) comes back as plain counters the UI polls with a `QTimer`.

### NVG-213: Audio settings dialog
**Type:** Story · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-211, NVG-104
- [ ] Choose host API, output device, sample rate and buffer size; applied without restart; saved.

### NVG-220: Load audio files off the audio thread
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-211
- [ ] `soundfile` decodes WAV/FLAC in a worker thread into float32 arrays; corrupt files give a translated error, never a crash.

### NVG-221: Sample-rate conversion on import
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-220
- [ ] Files with a different rate are resampled once on import (fast compiled resampler chosen and recorded); quality checked with a sine test.

### NVG-222: Transport: Play and Stop
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-212, NVG-220
- [ ] Play/Stop buttons play a loaded file from the playhead; stop is instant and click-free (short fade).

### NVG-223: Transport: loop region
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-222
- [ ] Loop start/end; playback wraps sample-accurately (unit test on the render function).

### NVG-224: Playhead position display
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-222, NVG-230
- [ ] Shows time and bars:beats; updates smoothly without loading the UI thread.

### NVG-225: Transport keyboard shortcuts
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-223
- [ ] Space = play/stop, L = loop on/off, Home = go to start; listed in menus.

### NVG-230: Tempo
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-212
- [ ] BPM (20–300) and 4/4 time signature in the model; BPM editable in the transport bar.

### NVG-231: Metronome
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-230, NVG-222
- [ ] Pre-rendered click with accent on beat 1, mixed sample-accurately in the callback.

### NVG-232: Metronome controls
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-231
- [ ] On/off toggle and volume; saved in settings.

### NVG-240: Latency display
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-211
- [ ] Status bar shows output (and later input) latency in ms as reported by the stream.

### NVG-241: Underrun counter
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-212
- [ ] Status bar shows xruns since playback start; counter resets on demand.

### NVG-242: 10-minute stability test
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-231, NVG-241
- [ ] Script plays a test project for 10 minutes and records xruns, callback load and memory; results in docs/PERFORMANCE.md; zero audible dropouts.

### NVG-243: Phase 1 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-242, NVG-224, NVG-225
- [ ] All Phase 1 exit criteria from the README met; version bumped to 0.3.0 and tagged.

## Phase 2: Timeline (Arrangement)

### NVG-300: Project model
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-21
- [ ] `Project`, `Track`, `AudioClip` dataclasses (positions in samples), pure Python, fully unit-tested.

### NVG-301: Project serialization
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-300
- [ ] Save/load to the chosen format with a schema version; input validated as untrusted (size limits, types, paths stay inside the project folder).

### NVG-302: Project file migrations
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-301
- [ ] Migration chain from every older schema version; test fixtures of each version must keep loading.

### NVG-303: Save, Save As, Open
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-301, NVG-310
- [ ] File menu commands with dialogs; unsaved-changes flag (`*` in title) and prompt on close.

### NVG-304: Audio files inside the project folder
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-303
- [ ] Imported audio is copied into the project's `audio/` folder; missing files are reported and can be relinked.

### NVG-305: Autosave and crash recovery
**Type:** Story · **Priority:** P2 · **Size:** S · **Status:** To Do · **Depends on:** NVG-303
- [ ] Autosave every few minutes to a side file; after a crash the app offers to restore it.

### NVG-306: Recent projects
**Type:** Task · **Priority:** P2 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-303
- [ ] File → Open Recent with the last 10 projects; missing ones are removed.

### NVG-310: Undo and redo
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-300
- [ ] `QUndoStack` wired to Edit → Undo/Redo (Ctrl+Z / Ctrl+Y); every model edit is a command.

### NVG-320: Timeline canvas and ruler
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-121, NVG-230
- [ ] `QGraphicsView` timeline with a bars/beats ruler; click on the ruler moves the playhead.

### NVG-321: Track lanes and headers
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-320, NVG-300
- [ ] One lane per track with a header (name, mute, solo placeholders).

### NVG-322: Add, remove, rename, reorder tracks
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-321, NVG-310
- [ ] All four actions work from menus and context menus and are undoable.

### NVG-323: Waveform peak cache
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-220
- [ ] Multi-resolution min/max peaks computed with NumPy in a worker thread and cached per file.

### NVG-324: Clip rendering
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-323, NVG-321
- [ ] Clips draw their waveform from the cache; scrolling a 10-minute project stays smooth.

### NVG-325: Import audio into a track
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-324, NVG-304
- [ ] Import via menu and via drag and drop from Explorer onto a lane at the drop position.

### NVG-326: Move clips
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-324, NVG-310
- [ ] Drag clips in time and between tracks; undoable.

### NVG-327: Split clip at the playhead
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-326
- [ ] Ctrl+E splits selected clips at the playhead; undoable.

### NVG-328: Copy, paste, duplicate clips
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-326
- [ ] Ctrl+C/Ctrl+V at the playhead, Ctrl+D duplicates after the selection; undoable.

### NVG-329: Delete clips
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-326
- [ ] Delete key removes selected clips; undoable.

### NVG-330: Trim clip edges
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-326
- [ ] Dragging a clip edge trims it without touching the source file; undoable.

### NVG-331: Zoom
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-324
- [ ] Horizontal zoom (Ctrl+wheel, +/−) around the mouse; vertical track height zoom.

### NVG-332: Snap to grid
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-326
- [ ] Grid sizes (bar, 1/2 … 1/16) with snap on/off; moves and splits snap.

### NVG-333: Clip fades
**Type:** Task · **Priority:** P2 · **Size:** S · **Status:** To Do · **Depends on:** NVG-330
- [ ] Fade-in/out handles on clips; default micro-fades prevent clicks at clip edges.

### NVG-340: Playback schedule
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-300, NVG-212
- [ ] The UI side builds an immutable schedule of clip segments and swaps it into the engine atomically after edits.

### NVG-341: Multi-track mixing in the callback
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-340
- [ ] The callback mixes scheduled segments with per-track gain using vectorized NumPy and preallocated buffers.

### NVG-342: Multi-track benchmark
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-341
- [ ] 32 stereo tracks play within the callback budget; numbers in docs/PERFORMANCE.md.

### NVG-343: Phase 2 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-303, NVG-325, NVG-332, NVG-342
- [ ] A simple song can be assembled from audio clips and saved; version bumped to 0.4.0 and tagged.

## Phase 3: MIDI

### NVG-400: Spike: MIDI libraries on Python 3.15
**Type:** Spike · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] `mido` + `python-rtmidi` wheels for Python 3.15 on Windows checked; fallback recorded if missing.

### NVG-401: MIDI model
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-300
- [ ] Notes (pitch, start, length, velocity) and MIDI clips in the project model and file format; tested.

### NVG-402: MIDI clips on the timeline
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-401, NVG-324
- [ ] Instrument tracks show MIDI clips with a note preview; move/split/copy work like audio clips.

### NVG-410: Piano roll view
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-402
- [ ] Opens on double-click; keyboard, grid, scrolling and zoom.

### NVG-411: Piano roll: draw and erase notes
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-410
- [ ] Click draws a note at grid size, right-click erases; undoable.

### NVG-412: Piano roll: edit notes
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-411
- [ ] Move, resize and multi-select (rubber band) notes; undoable.

### NVG-413: Piano roll: velocity lane
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-412
- [ ] Velocity bars under the grid, editable by dragging.

### NVG-414: Quantize
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-412
- [ ] Quantize selected notes to the grid (start, optionally length); undoable.

### NVG-420: Step sequencer model
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-401
- [ ] Patterns of 16 steps × N rows (sample per row), converted to note events for playback; tested.

### NVG-421: Step sequencer UI
**Type:** Story · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-420, NVG-121
- [ ] Grid of toggle steps with row sample selector; current step highlighted during playback.

### NVG-422: Step sequencer playback
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-421, NVG-433
- [ ] Patterns play in sync with the transport and loop.

### NVG-430: Synth: oscillators
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-341
- [ ] Band-limited sine/saw/square oscillators rendered per block with NumPy; aliasing checked.

### NVG-431: Synth: envelope and voices
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-430
- [ ] ADSR envelope, 16-voice polyphony with voice stealing; no allocation in the callback.

### NVG-432: Synth: filter and controls
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-431
- [ ] Low-pass filter with cutoff/resonance; instrument panel with translated parameter names.

### NVG-433: Sampler: one-shot pads
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-341, NVG-220
- [ ] Pads with assigned samples triggered by notes.

### NVG-434: Sampler: pitched playback
**Type:** Task · **Priority:** P2 · **Size:** S · **Status:** To Do · **Depends on:** NVG-433
- [ ] A sample mapped across the keyboard plays pitched by note.

### NVG-440: MIDI input devices
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-400
- [ ] MIDI inputs listed in audio settings; selection saved.

### NVG-441: Live MIDI input
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-440, NVG-431
- [ ] Notes from a MIDI keyboard play the armed instrument track with low latency.

### NVG-442: Record MIDI into a clip
**Type:** Story · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-441
- [ ] Recording creates a MIDI clip with the played notes at the right positions.

### NVG-443: Phase 3 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-414, NVG-422, NVG-432, NVG-442
- [ ] A melody and a rhythm can be written without external plugins; version bumped to 0.5.0 and tagged.

## Phase 4: Mixer and effects

### NVG-500: Mixer view and channel strip
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-321
- [ ] Mixer panel with one strip per track and a master strip.

### NVG-501: Volume and pan
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-500, NVG-341
- [ ] Fader in dB and constant-power pan, smoothed to avoid zipper noise.

### NVG-502: Mute and solo
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-501
- [ ] Mute/solo logic (solo overrides) in mixer and track headers; tested.

### NVG-503: Level meters
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-501
- [ ] Peak and RMS computed in the callback into counters; UI draws at 30 fps with peak hold.

### NVG-504: Master bus
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-503
- [ ] Master gain, meter and clip indicator.

### NVG-510: Send and return buses
**Type:** Story · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-504
- [ ] Return tracks with per-track send levels (pre/post fader).

### NVG-520: Effect chain framework
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-504
- [ ] Insert slots per track and master; add, remove, reorder, bypass; processing without allocation.

### NVG-521: Built-in EQ
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-520
- [ ] 4-band parametric EQ using compiled filtering (no per-sample Python loops); frequency response tested.

### NVG-522: Built-in compressor
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-520
- [ ] Threshold, ratio, attack, release, makeup gain; gain-reduction meter.

### NVG-523: Built-in reverb
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-520
- [ ] Algorithmic reverb with size, damping, mix; fits the callback budget.

### NVG-524: Effect parameter panel
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-521
- [ ] Generic panel for any effect's parameters (knobs/sliders, units, translated names).

### NVG-530: Automation model
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-300
- [ ] Breakpoint envelopes per parameter in the model and file format; interpolation tested.

### NVG-531: Automation lanes
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-530, NVG-321
- [ ] Show/hide lanes under a track; add, move, delete points; undoable.

### NVG-532: Automation playback
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-531, NVG-524
- [ ] Volume, pan and effect parameters follow automation at block rate with smoothing.

### NVG-533: Phase 4 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-510, NVG-523, NVG-532
- [ ] A whole song can be mixed with built-in tools; version bumped to 0.6.0 and tagged.

## Phase 5: Recording and plugins

### NVG-600: Audio input and monitoring
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-211
- [ ] Input device opened alongside output (duplex); monitoring on/off per track.

### NVG-601: Record to disk
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-600, NVG-304
- [ ] Record-armed tracks write WAV through a writer thread fed by a ring buffer (no disk I/O in the callback).

### NVG-602: Recording latency compensation
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-601
- [ ] Recorded clips are shifted by the measured round-trip latency; loopback test documented.

### NVG-603: Input level meter
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-600, NVG-503
- [ ] Armed tracks show the input level.

### NVG-610: Spike: VST3 hosting
**Type:** Spike · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** —
- [ ] `pedalboard` (allowed by the GPL-3.0-or-later license, see docs/DECISIONS.md) checked on Python 3.15: wheels, VST3 loading, latency, crash isolation; an alternative chosen if it fails; recorded in docs/DECISIONS.md.

### NVG-611: Plugin scanner
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-610
- [ ] Scans standard VST3 folders in a separate process (a crashing plugin cannot take the app down); results cached.

### NVG-612: Plugin browser
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-611
- [ ] Searchable list of found plugins; rescan button.

### NVG-613: Insert a VST3 effect
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-611, NVG-520
- [ ] A VST3 effect can be inserted into a chain and processes audio in the engine.

### NVG-614: Plugin editor window
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-613
- [ ] The plugin's own editor opens in a window.

### NVG-615: Save plugin state
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-613, NVG-301
- [ ] Plugin state is stored in the project and restored on open.

### NVG-616: Phase 5 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-602, NVG-615
- [ ] Vocals are recorded and processed with a third-party VST3 effect; version bumped to 0.7.0 and tagged.

## Phase 6: Export

### NVG-700: Offline render engine
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-532
- [ ] Renders the project faster than real time using the same DSP code as playback, with progress and cancel.

### NVG-701: Export WAV
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-700
- [ ] 16/24-bit integer (with dither) and 32-bit float WAV.

### NVG-702: Export FLAC
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-701
- [ ] FLAC export at 16/24 bit.

### NVG-703: Export MP3
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-701
- [ ] MP3 export (check the MP3 encoder bundled with `soundfile`/libsndfile, else choose another); bitrate options.

### NVG-704: Export stems
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-701
- [ ] One file per track (with track effects), named after the tracks.

### NVG-705: Export dialog
**Type:** Story · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-701
- [ ] Format, range (whole song / loop), file name; remembers the last choice.

### NVG-706: Export null test
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-700
- [ ] Automated test: offline render equals the real-time render of the same project (bit-exact or within float tolerance).

### NVG-707: Phase 6 exit check
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-702, NVG-703, NVG-704, NVG-705, NVG-706
- [ ] A finished song exports and sounds the same as in the app; version bumped to 0.8.0 and tagged.

## Release 1.0

### NVG-800: Spike: packaging tool
**Type:** Spike · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-134
- [ ] `pyside6-deploy` (Nuitka) vs PyInstaller compared on startup time, size and antivirus false positives; recorded in docs/DECISIONS.md.

### NVG-801: Standalone Windows build
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-800
- [ ] `scripts/build.py` produces a standalone build that starts on a clean Windows machine.

### NVG-802: MSIX package
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-801, NVG-20
- [ ] MSIX with manifest (name, publisher placeholders, icons, minimum Windows version) passes the Windows App Certification Kit.

### NVG-803: Store listing texts and screenshots
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-707
- [ ] Description, features and keywords in EN/RU/HY; screenshots in all three languages.

### NVG-804: Privacy policy
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** —
- [ ] Short policy (the app collects no data and makes no network requests) published on the landing page and in the repo.

### NVG-805: Landing page content and design
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-120, NVG-803
- [ ] Static page in EN/RU/HY: description, screenshots, links to the Store, GitHub and donations/purchase; follows docs/DESIGN.md.

### NVG-806: Deploy the landing page to Cloudflare
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-805
- [ ] Deployed as Cloudflare Workers static assets on a `*.workers.dev` URL (free plan).

### NVG-807: Connect the domain
**Type:** Task · **Priority:** P2 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-806, NVG-811
- [ ] Custom domain with HTTPS points to the landing page.

### NVG-808: Ship license notices with release builds
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-801
- [ ] The standalone build and the MSIX contain `LICENSE` and a generated `THIRD-PARTY-NOTICES.txt` with the name, version and license text of every bundled package (Qt and PySide6 included).
- [ ] A test builds the wheel and sdist and checks that both contain `LICENSE`, and fails if a runtime dependency is missing from the notices.
- [ ] Third-party license notices keep their authors' e-mail addresses (MIT and BSD require the notice unchanged), but the guard blocks personal e-mails in committed files: allowlist the generated notices file and vendored license files in the guard, with tests in `tests/test_guard*.py`.

### NVG-810: Reserve the name "Nvagik" in Partner Center
**Type:** Task · **Priority:** P1 · **Size:** XS · **Status:** Blocked (owner) · **Depends on:** NVG-24
- [ ] Owner registers the Partner Center account chosen in NVG-24 and reserves the app name (the agent prepares exact steps).

### NVG-811: Buy the domain via Cloudflare Registrar
**Type:** Task · **Priority:** P2 · **Size:** XS · **Status:** Blocked (owner) · **Depends on:** —
- [ ] Owner buys `nvagik.com` (and `nvagik.app` if wanted) in Cloudflare Registrar; availability re-checked first (it was free on 2026-11-21).

### NVG-812: Submit to Microsoft Store certification
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** Blocked (owner) · **Depends on:** NVG-802, NVG-803, NVG-804, NVG-808, NVG-810, NVG-820, NVG-821
- [ ] Owner uploads the package prepared by the agent and submits it; certification passes.
- [ ] Partner Center's license terms field links to `LICENSE` (GPL-3.0-or-later) instead of the Standard Application License Terms.

### NVG-820: Pre-release security audit
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-707
- [ ] `security-auditor` review of the whole code base and dependencies; all findings fixed.

### NVG-821: Pre-release performance audit
**Type:** Task · **Priority:** P0 · **Size:** S · **Status:** To Do · **Depends on:** NVG-707
- [ ] `performance-auditor` checks every budget in CLAUDE.md on a release build; results in docs/PERFORMANCE.md.

### NVG-822: Translation review
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-707
- [ ] All HY and RU strings reviewed against docs/GLOSSARY.md; nothing clipped in the UI.

### NVG-823: UI/UX review
**Type:** Task · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-707
- [ ] `ui-ux-reviewer` pass over every screen; improvements done or added as tasks.

### NVG-824: Release 1.0.0
**Type:** Task · **Priority:** P0 · **Size:** XS · **Status:** To Do · **Depends on:** NVG-812, NVG-822, NVG-823
- [ ] Version 1.0.0, CHANGELOG, tag and GitHub Release notes; README status updated.
