import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / ".claude" / "hooks" / "guard.py"


@pytest.fixture(scope="session")
def guard():
    """The guard hook module (it lives outside the package, so load it by path)."""
    spec = importlib.util.spec_from_file_location("nvagik_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
