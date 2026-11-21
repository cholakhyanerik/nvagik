# Nvagik

**Nvagik** is a free, open-source digital audio workstation (DAW) for Windows. Write, record, edit and mix music in a fast, lightweight app with an Armenian, Russian and English interface. Built with Python 3.15, PySide and uv. Development is supported by donations via [GitHub Sponsors](https://github.com/sponsors/cholakhyanerik).

> **Status:** early development, Phase 0 (skeleton). The app is not usable yet: `uv run nvagik` currently only prints a greeting. See the [Roadmap](#roadmap).

## Contents

- [About the name](#about-the-name)
- [What Nvagik is](#what-nvagik-is)
- [Who it is for](#who-it-is-for)
- [Core principles](#core-principles)
- [Getting started (development)](#getting-started-development)
- [Project documents](#project-documents)
- [Technical rules](#technical-rules)
- [Roadmap](#roadmap)
- [Distribution and revenue model](#distribution-and-revenue-model)
- [Risks](#risks)
- [Open questions](#open-questions)
- [Name availability check](#name-availability-check)
- [License](#license)
- [Support the project](#support-the-project)

## About the name

**Nvagik** (Armenian: Նվագիկ) comes from the Armenian word *nvag* (նվագ, "tune, played music") plus the diminutive suffix *-ik*, so it means "little tune". It follows the same naming pattern as the author's other apps, Ekranik and Kvartik.

The name was chosen on 2026-11-21 after an availability check. Backup names are **Yergik** and **Dzaynik**. See [Name availability check](#name-availability-check) for details and limitations.

## What Nvagik is

Nvagik is an open-source digital audio workstation (DAW) for Windows for writing, recording, editing and mixing music. It is written in Python 3.15 with PySide and uv (by Astral).

The long-term goal is to provide all the core functionality of apps like **Logic Pro**, **FL Studio** and **Ableton Live**, without the price barrier.

For now the app is free, and the only source of income is donations via [GitHub Sponsors](https://github.com/sponsors/cholakhyanerik). It will be distributed through the **Microsoft Store**, and a landing page will follow later. Donations are a temporary model: later Nvagik will become a paid app (see [Distribution and revenue model](#distribution-and-revenue-model)).

## Who it is for

- **Beginner and hobby musicians** who are put off by the price of paid DAWs (roughly **$60–$199** in our research).
- **Armenian- and Russian-speaking users.** Logic Pro offers 7 interface languages, but neither Armenian nor Russian. Nvagik's interface will be available in Armenian, Russian and English.
- **Open-source and Python contributors** who want to read, change or extend the code of a music studio.

## Core principles

1. **Speed and optimization come first.** This is the top rule: the app must start fast, respond instantly and stay lightweight.
2. **Open repository.** All code is public.
3. **Free for now, funded by donations.** There is no paid edition and no subscription. Later, donations will be replaced by a paid model (see [Distribution and revenue model](#distribution-and-revenue-model)).
4. **Three languages:** Armenian, Russian, English.
5. **Windows only.** We don't split our focus across other platforms.

## Getting started (development)

Requirements:

- Windows
- Python 3.15
- [uv](https://docs.astral.sh/uv/)

```sh
git clone https://github.com/cholakhyanerik/nvagik.git
cd nvagik
uv sync          # create the virtual environment and install dependencies
uv run nvagik    # run the app
```

Day-to-day commands:

| Purpose | Command |
| --- | --- |
| Run the tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Add a dependency | `uv add <package>` (dev tools: `uv add --dev <package>`) |
| Remove build and test junk | `py -3 scripts/clean.py` |

Use uv for everything; don't use `pip` directly.

## Project documents

| Document | What it contains |
| --- | --- |
| [TASKS.md](TASKS.md) | Backlog of small, Jira-style tasks for everything needed to ship 1.0 |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each version |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decisions made during development, with reasons |
| [CLAUDE.md](CLAUDE.md) | Development rules for AI-assisted work (Claude Code): workflow, architecture, security, performance budgets |

Versions follow [Semantic Versioning](https://semver.org/): before 1.0, every finished task bumps the patch version and every finished roadmap phase bumps the minor version.

## Technical rules

These rules are mandatory and do not change.

- **Language and tools.** Python 3.15. GUI: PySide (Qt for Python). Package and environment management: uv (Astral). Day-to-day commands are `uv init`, `uv add`, `uv sync` and `uv run`. Everything is done with this stack only.
- **Platform.** Windows only. We don't write code or conditional branches for other operating systems.
- **Repository.** Open (public), licensed under GPL-3.0-or-later (see [License](#license)).
- **Funding.** For now, donations only: [github.com/sponsors/cholakhyanerik](https://github.com/sponsors/cholakhyanerik). The donation link is shown in this README and in the app's **About** window. This is temporary: later it will be replaced by a paid model, with payments going to the developer's sole proprietorship.
- **Interface languages.** Armenian, Russian, English. No user-facing text is hard-coded. All strings go through translation files (Qt's translation system), so adding a new language never requires a code change.
- **Speed.** This is the most important rule. Every new feature is measured: how fast the app starts, how much memory it uses, and how long the audio callback takes. A feature that slows the app down gets optimized or is not accepted.
- **Audio callback rule.** Inside the audio callback, never read files, allocate new memory or touch the UI. Buffers are pre-allocated, and heavy computation runs inside NumPy and other compiled libraries.
- **Libraries (candidates).** The final choice will be made after the Phase 1 measurements.

  | Purpose | Candidate |
  | --- | --- |
  | DSP | NumPy |
  | Audio input/output | `sounddevice` (PortAudio) |
  | Audio files | `soundfile` |
  | MIDI | `mido` / `python-rtmidi` |
  | VST3 plugin hosting | `pedalboard` (GPL-3.0, fits the project license) |

- **Distribution.** Through the Microsoft Store, with a landing page later. For whether the name is free, see [Name availability check](#name-availability-check).

## Roadmap

The goal is full coverage of the core functionality of Logic Pro, FL Studio and Ableton Live. That is a very large scope, so the work is split into phases. **At the end of every phase the app must be usable, not half-finished.** The exit criteria are proposals and will be refined along the way.

| Phase | Scope | Exit criterion |
| --- | --- | --- |
| **0. Skeleton** | `uv init` project, PySide window, base for the three-language interface, README with the donation link. | `uv run` opens the window, and the app lists the system's audio devices. |
| **1. Audio core** *(highest risk)* | WAV playback, Play/Stop/Loop, metronome, BPM, latency measurement, underrun counter. | A test project plays for 10 minutes without audible dropouts, and the measurement results are recorded. |
| **2. Timeline (Arrangement)** | Tracks, clips, cut/move/copy, zoom, snap-to-grid, Undo/Redo, saving and opening projects. | You can build a simple song from audio clips and save it to a file. |
| **3. MIDI** | Piano roll, step sequencer, a simple built-in synth/sampler, MIDI keyboard input. | A melody and a rhythm can be written inside the app with no external plugin. |
| **4. Mixer and effects** | Volume/Pan/Mute/Solo, send/return, built-in EQ, compressor, reverb, automation. | A whole song can be mixed with the built-in tools. |
| **5. Recording and plugins** | Recording from a microphone, VST3 plugin hosting, plugin scanning. | Vocals are recorded and processed with a third-party VST3 effect. |
| **6. Export** | Export to WAV, MP3 and FLAC, plus per-track export (stems). | A finished song is exported and sounds the same as it does inside the app. |
| **7. Parity** | Session view, time-stretch/warp, stem separation, AI assistants, notation, loop/sample library and more, following the [feature comparison table](https://claude.ai/artifact/EmizQdKqox46zUSi2URc59). | This phase will be split into its own sub-phases once we get there. |

**Phases 0–6 make up a working DAW (the MVP).** After that, the app can have its first public release.

## Distribution and revenue model

### Distribution

- **Microsoft Store** is the main distribution channel.
- **Landing page** (later). It will have the app's description, screenshots, and links to the Store and to donation or purchase. It will be hosted on Cloudflare (Workers static assets), with the domain bought through Cloudflare Registrar. The domains `nvagik.com` and `nvagik.app` were unregistered on 2026-11-21 (see [Name availability check](#name-availability-check)).
- **GitHub** hosts the open repository (the code).

### Revenue model

The revenue model has two stages:

1. **Stage A (now).** The app is free. The only source of income is donations via [GitHub Sponsors](https://github.com/sponsors/cholakhyanerik).
2. **Stage B (later).** Donations are replaced, the app becomes paid, and payments go to the developer's sole proprietorship. The price, the format (one-time purchase or subscription) and the timing of the switch are not decided yet (see [Open questions](#open-questions)).

### Selling a paid app in the Microsoft Store: what to check

- **Partner Center account type.** Choose Individual or Company for the sole proprietorship. Switching an Individual account to a Company account is not supported, so the type must be chosen up front.
- **Payouts to Armenia.** It hasn't been checked whether Partner Center can pay paid-app revenue into an Armenian bank account, or in which currency. Confirm this in Partner Center or with Microsoft support.
- **Store fee.** According to Microsoft's documentation, the Store fee is 15% for apps (12% for games). The supported monetization models are in-app purchases, subscriptions and ads. Account for this when setting the price.
- **Taxes.** Confirm with the State Revenue Committee (SRC) or an accountant how income from paid sales is handled under the sole proprietorship's tax regime.

## Risks

- **Real-time audio in Python.** The GIL and the garbage collector can stall the audio callback, which causes audible dropouts (underruns). The language and stack are fixed, so the question is not "can it be done?" but "how do we do it within this stack?". Candidate approaches:
  - pre-allocated NumPy buffers;
  - running the audio engine in a separate thread or a separate process, independent of the UI;
  - doing heavy DSP inside compiled libraries.

  Feasibility is measured in Phase 1. Only the architecture may change, never the language or the stack.
- **The scope is huge.** "All the functionality" means the size of apps that large teams have built over decades. The realistic path is to bring each phase to a working app, rather than starting every direction at once.
- **Funding.** Donations alone may not cover the time spent, and there is no other income for now. Donations are temporary and the app will become paid, so the price, the format and the timing of the switch still have to be decided (see [Open questions](#open-questions)).
- **Name and trademark.** The [name check](#name-availability-check) is only an indicator. It is not a legal trademark search.

## Open questions

These decisions are for the project owner.

1. **License.** *Decided on 2026-11-21:* **GPL-3.0-or-later**. It keeps `pedalboard` (GPL-3.0) available for VST3 hosting and still allows paid Store builds of the open code. See [License](#license) and the [comparison](docs/DECISIONS.md#license-nvg-1).
2. **Microsoft Store edition.** Should the Store offer the same free version, or a separate version for a small fee?
3. **Audio drivers.** WASAPI support is required. ASIO support still needs to be checked, since it depends on the PortAudio build and on ASIO licensing. Do we need ASIO for the lowest latency as early as the first phase?
4. **Minimum Windows version.** Windows 10, or Windows 11 only?
5. **Project file format.** An open, readable format (for example JSON), or a closed binary format?
6. **Paid model.** One-time purchase or subscription? What price (paid DAWs cost roughly $60–$199 in our research)? Will there be a free trial? When does the switch happen?
7. **Open source in the paid stage.** An open repository is a baseline requirement. In the paid stage, does the code stay open while the ready-made Store build is paid? The GPL-3.0-or-later license (question 1) allows this model: Krita sells its GPL build in the Microsoft Store. The Store terms still have to be checked against it (NVG-23).
8. **Partner Center account.** Individual or Company for the sole proprietorship? Can paid-app revenue be received in an Armenian bank account? Not checked yet (see [Distribution and revenue model](#distribution-and-revenue-model)).

## Name availability check

The check was done on **2026-11-21**. All candidates come from Armenian words and end in *-ik*, like the author's other apps, Ekranik and Kvartik.

### Shortlist

| Name | GitHub username | .com | .app / .dev | .io / .am (DNS) | Microsoft Store | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **Nvagik** (Նվագիկ, "little tune") | free; repo search: 0 results | free | free / free | no trace | no match | **Chosen** |
| **Yergik** (Երգիկ, "little song") | free; repo search not checked | free | free / free | no trace | no match | Backup |
| **Dzaynik** (Ձայնիկ, "little voice") | free; repo search not checked | free | free / free | no trace | no match | Third choice: "dz" is hard for English speakers to pronounce |

### Other candidates checked

- **Free on GitHub and .com/.app/.dev** (Store and repo search not checked): Kamanchik (Քամանչիկ), Zangik (Զանգիկ), Hnchyun (Հնչյուն).
- **Rejected because .com and .app are taken:** Dzayn (Ձայն). Its .com has been registered since 2010.
- **Taken on GitHub:** Takt, Taktik, Ritm, Ritmik, Sazik, Notik, Wavik, Beatik, Dholik, Shvik.
- **.com taken:** Nvag, Nvagaran, Zurnik, Hnchik.

### Method

- **GitHub username:** opening `github.com/<name>` returned HTTP 404, which means free. **Repo search** covered all GitHub repositories. It was run for Nvagik (0 results) but not for Yergik and Dzaynik, because GitHub rate-limited the requests (HTTP 429).
- **.com:** Verisign RDAP, where 404 means not registered. **.app and .dev:** Google Registry RDAP, where 404 means not registered. The method was validated on the already-registered `dzayn.app`, which returned 200.
- **.io and .am:** DNS response only (via `dns.google`). NXDOMAIN suggests the domain is free, but a registered domain with no name servers can also return NXDOMAIN, so check with a registrar before buying.
- **Microsoft Store:** searching the name on apps.microsoft.com returns only unrelated popular apps (for example TikTok and Adobe Photoshop). No app has the same name.

### Known limitations

- Microsoft Store names are reserved only in Partner Center, and a name that is reserved but not yet published doesn't show up in search. So the name must actually be reserved before the app is published.
- This is not proof that the name is free from a trademark point of view. No legal trademark search was done.
- Buying the domain, creating the GitHub account or organization, and reserving the name in Partner Center are up to the owner. The sooner they're done, the less likely it is that someone else takes the name.

## License

Nvagik is free software, licensed under the **GNU General Public License v3.0 or later** (GPL-3.0-or-later).

- You may use, study, share and change it, for any purpose.
- If you distribute Nvagik or a modified version, you must make its source code available under the same license.
- Ready-made builds in the Microsoft Store may become paid later (see [Distribution and revenue model](#distribution-and-revenue-model)); the source code stays open.
- Nvagik can load any VST3 plugin, including closed-source ones.

Why this license was chosen: [docs/DECISIONS.md](docs/DECISIONS.md#license-nvg-1).

## Support the project

Nvagik is free and is developed in the open. If you'd like to support development, please consider sponsoring it on [GitHub Sponsors](https://github.com/sponsors/cholakhyanerik).
