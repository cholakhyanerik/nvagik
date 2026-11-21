"""The project license (NVG-1, NVG-2): verbatim GPL-3.0 text, declared as GPL-3.0-or-later."""

import hashlib
import importlib.metadata
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE = ROOT / "LICENSE"
# SHA-256 of https://www.gnu.org/licenses/gpl-3.0.txt with LF line endings.
GPL_3_SHA256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
SPDX = "GPL-3.0-or-later"


def test_license_file_is_the_verbatim_gpl_3_text():
    text = LICENSE.read_text(encoding="utf-8")  # universal newlines: CRLF checkouts still match
    assert text.startswith(" " * 20 + "GNU GENERAL PUBLIC LICENSE\n")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == GPL_3_SHA256


def test_pyproject_declares_the_license():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == SPDX
    assert project["license-files"] == ["LICENSE"]


def test_installed_metadata_carries_the_license():
    metadata = importlib.metadata.metadata("nvagik")
    assert metadata["License-Expression"] == SPDX
    assert "LICENSE" in metadata.get_all("License-File", [])
