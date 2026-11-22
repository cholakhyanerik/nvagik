---
name: i18n
description: How Nvagik handles its three interface languages (Armenian hy, Russian ru, English en) with Qt's translation system. Use when adding or changing any user-facing text, adding a language, or working on the translation scripts.
---

# Interface languages

Nvagik supports **AM (Armenian, Qt locale `hy`), RU (`ru`) and EN (`en`)** by default (CLAUDE.md rule 7). English is the source language written in code; Armenian and Russian come from Qt translation files.

## In code

- Every user-facing string goes through Qt: `self.tr("Add track")` inside a `QObject` subclass, or `QCoreApplication.translate("Context", "Add track")` elsewhere.
- Placeholders with names: `self.tr("Track {name}").format(name=track.name)`. Never build sentences from pieces.
- Plurals: `self.tr("%n track(s)", "", count)`; translators supply the plural forms.
- Accelerators (`&File`) and shortcuts stay in the translated string.
- Not translated: log messages, exceptions meant for developers, file formats and identifiers.
- Widgets react to `QEvent.LanguageChange` by calling a `retranslate_ui()` method, so the language switches without a restart.

## Files and scripts

These are created by NVG-110 to NVG-114; until then, follow the layout when adding them.

| Item | Location |
| --- | --- |
| Translation sources | `src/nvagik/i18n/nvagik_hy.ts`, `src/nvagik/i18n/nvagik_ru.ts` |
| Compiled translations | `src/nvagik/i18n/*.qm` (built, packaged) |
| Extract strings | `uv run python scripts/i18n.py extract` (`pyside6-lupdate`) |
| Compile | `uv run python scripts/i18n.py build` (`pyside6-lrelease`) |
| Terminology | `docs/GLOSSARY.md` |
| Completeness test | `tests/test_translations.py` |

## Workflow for a text change

1. Write the English string with `tr()`.
2. Run `extract`, then let the `i18n-translator` agent (or yourself) translate the new entries into Armenian and Russian using the glossary.
3. Run `build` and `uv run pytest` (the completeness test fails on unfinished entries).
4. Check the UI in Russian and Armenian for clipped text (`ui-ux-reviewer`).

## Language selection at startup

Saved setting, else the Windows UI language when it is Armenian or Russian, else English. Qt's own strings (standard dialogs) are translated too: load `qtbase_<lang>` from `QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)`, never `qt_<lang>`. `qt_<lang>.qm` is a meta file that also needs `qtmultimedia_<lang>.qm` from `pyside6-addons`, which the project does not install (NVG-13), so it fails to load without an error. Qt has no Armenian file at all; our own `qtbase_hy.ts` fills that gap (NVG-117).
