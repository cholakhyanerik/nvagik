"""Runtime dependencies stay lean (NVG-13, rule 2)."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The full `pyside6` meta package also pulls `pyside6-addons`, `pyside6-webengine` and
# `pyside6-pdf`, which the app does not use. A feature that needs an Addons module adds
# `pyside6-addons` here, with a docs/DECISIONS.md entry.
ALLOWED_QT = {"pyside6-essentials"}


def load(name: str) -> dict:
    return tomllib.loads((ROOT / name).read_text(encoding="utf-8"))


def name(requirement: str) -> str:
    """The PEP 503 normalized name: `PySide6_Essentials>=6.12` -> `pyside6-essentials`."""
    return re.sub(r"[-_.]+", "-", re.match(r"[A-Za-z0-9._-]*", requirement).group()).lower()


def test_project_depends_on_pyside6_essentials():
    deps = load("pyproject.toml")["project"]["dependencies"]
    assert "pyside6-essentials" in {name(d) for d in deps}, deps


def test_lockfile_has_only_the_allowed_qt_packages():
    # An allow list, so a package that PySide splits off in a later release is caught too.
    locked = {p["name"] for p in load("uv.lock")["package"]}
    assert {n for n in locked if n.startswith("pyside6")} == ALLOWED_QT


def test_qt_russian_strings_load_without_the_addons(qapp):
    # `qt_ru.qm` also needs `qtmultimedia_ru.qm` from pyside6-addons and fails to load
    # silently, so NVG-112 loads `qtbase_<lang>`: it must stay in Essentials.
    from PySide6.QtCore import QLibraryInfo, QTranslator

    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    translator = QTranslator()
    assert translator.load("qtbase_ru", translations)
    assert translator.translate("QPlatformTheme", "Cancel") == "Отмена"
