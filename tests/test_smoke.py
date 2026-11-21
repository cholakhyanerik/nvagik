import importlib.metadata
import tomllib
from pathlib import Path

import nvagik

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]["version"]


def test_main_runs(capsys):
    nvagik.main()
    assert "nvagik" in capsys.readouterr().out.lower()


def test_installed_version_matches_pyproject():
    assert importlib.metadata.version("nvagik") == project_version()


def test_changelog_has_entry_for_current_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{project_version()}]" in changelog
