"""Line endings (NVG-5): LF everywhere, binary files never converted."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Every extension .gitattributes must mark as binary (audio, MIDI, instruments, plugins,
# presets, images, translations, fonts, NumPy data, archives, packages, native code).
BINARY = [
    "wav",
    "w64",
    "flac",
    "mp3",
    "ogg",
    "opus",
    "aif",
    "aiff",
    "aifc",
    "caf",
    "m4a",
    "aac",
    "wma",
    "wv",
    "mid",
    "midi",
    "sf2",
    "sf3",
    "vst3",
    "clap",
    "vstpreset",
    "fxp",
    "fxb",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "tif",
    "tiff",
    "ico",
    "qm",
    "ttf",
    "ttc",
    "otf",
    "woff",
    "woff2",
    "npy",
    "npz",
    "zip",
    "7z",
    "gz",
    "xz",
    "tar",
    "whl",
    "cab",
    "msi",
    "msix",
    "msixbundle",
    "msixupload",
    "appx",
    "appxupload",
    "exe",
    "dll",
    "pyd",
    "lib",
    "obj",
    "pdb",
]

pytestmark = pytest.mark.skipif(
    not (ROOT / ".git").exists(), reason="needs a git checkout (not a source archive)"
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8"
    ).stdout


def attributes(path: str, *names: str) -> dict[str, str]:
    """`git check-attr` values for a path (the file does not have to exist)."""
    lines = git("check-attr", *names, "--", path).splitlines()
    return {line.split(": ")[1]: line.split(": ")[2] for line in lines}


def test_text_files_use_lf():
    for path in ("src/nvagik/__init__.py", "README.md", "uv.lock", "x.ts", "x.svg", "x.nvagik"):
        assert attributes(path, "text", "eol") == {"text": "auto", "eol": "lf"}, path


def test_batch_files_use_crlf():
    assert attributes("build.bat", "eol") == {"eol": "crlf"}


@pytest.mark.parametrize("extension", BINARY)
def test_binary_files_are_not_converted(extension):
    path = f"assets/sample.{extension}"
    assert attributes(path, "binary", "text", "diff") == {
        "binary": "set",
        "text": "unset",
        "diff": "unset",
    }


def test_binary_list_matches_gitattributes():
    rules = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert sorted(re.findall(r"^\*\.(\S+) binary$", rules, re.MULTILINE)) == sorted(BINARY)


def test_no_crlf_in_the_index():
    lines = git("ls-files", "--eol").splitlines()
    crlf = [
        line
        for line in lines
        if line.startswith(("i/crlf", "i/mixed")) and "attr/-text" not in line  # explicit opt-out
    ]
    assert not crlf, f"files stored with CRLF line endings: {crlf}"
