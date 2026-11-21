import importlib.util
import os
from pathlib import Path

import pytest

# Widget tests run headless: no windows on screen, no focus stealing, and the
# same behavior locally and in CI. Forced (not setdefault) so a value left in
# the shell cannot open real windows. Both variables must be set before the
# QApplication exists; pytest-qt creates it lazily in the `qapp` fixture.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# On Windows the offscreen platform looks for fonts in PySide6/lib/fonts, which
# is empty: widgets then have no fonts and wrong text metrics (about twice the
# real width). With the system fonts, a font asked for by name (Segoe UI, and
# later the theme font) gets native metrics for Latin, Cyrillic and Armenian
# text; loading them costs about 20 ms per test run. The default app font is
# still Arial here, not Segoe UI as on the real Windows platform.
os.environ["QT_QPA_FONTDIR"] = str(Path(os.environ["SYSTEMROOT"]) / "Fonts")

pytest_plugins = ["pytester"]  # run small test files in-process (tests/test_qt_offscreen.py)

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / ".claude" / "hooks" / "guard.py"


@pytest.fixture(scope="session")
def guard():
    """The guard hook module (it lives outside the package, so load it by path)."""
    spec = importlib.util.spec_from_file_location("nvagik_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
