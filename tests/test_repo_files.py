"""Repository files that GitHub reads: security policy (NVG-4), funding (NVG-6), contributing
(NVG-9), README style (NVG-19)."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/cholakhyanerik/nvagik"
SPONSORS_URL = "https://github.com/sponsors/cholakhyanerik"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w")
# Inline links `](target "title")` and reference definitions `[name]: target`.
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?[^)]*\)|^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.M)
# README is written in short lists, without big paragraphs (rule 15, NVG-19).
MAX_BLOCK = 300  # characters per paragraph or list item, links counted as their text
LIST_ITEM = re.compile(r"(?:[-*+]|\d{1,9}[.)])\s")
HEADING = re.compile(r"#{1,6}(?:\s|$)")
FENCE = re.compile(r"(?ms)^ *(`{3,}|~{3,})[^\n]*\n.*?^ *\1[^\n]*$")
INLINE_LINK = re.compile(r"!?\[([^\[\]]*)\]\([^()]*\)")


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def commit_types(text: str, marker: str) -> list[str]:
    """Backticked words in the first line after `marker`, e.g. "with types `feat`, `fix`"."""
    assert marker in text, f"{marker!r} not found"
    line = text.partition(marker)[2].splitlines()[0]
    return re.findall(r"`(\w+)`", line)


def repo_paths() -> set[str]:
    """Tracked and new (not ignored) files and their folders, with git's exact spelling."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    files = {name for name in out.split(chr(0)) if name}
    folders = {"/".join(f.split("/")[:i]) for f in files for i in range(1, f.count("/") + 1)}
    return files | folders


def prose_blocks(text: str) -> list[str]:
    """Paragraphs and list items as readers see them: links shown as their text.

    Code blocks, tables, headings and reference definitions are left out. A list item
    includes its continuation lines; a nested item is a block of its own.
    """
    text = FENCE.sub("", text)
    while INLINE_LINK.search(text):  # a badge is a link around an image
        text = INLINE_LINK.sub(r"\1", text)
    blocks: list[str] = []
    current: list[str] = []
    for line in [*text.split("\n"), ""]:
        stripped = re.sub(r"^(?:\s*>)+", "", line).strip()
        skip = (
            HEADING.match(stripped)
            or stripped.startswith("|")
            or re.match(r"\[[^\]]+\]:\s", stripped)
        )
        if not stripped or skip or LIST_ITEM.match(stripped):
            if current:
                blocks.append(" ".join(current))
            current = []
        if stripped and not skip:
            current.append(stripped)
    return blocks


@pytest.mark.parametrize(
    ("text", "blocks"),
    [
        ("One\ntwo.\n\nThree.", ["One two.", "Three."]),
        ("- a\n  more a\n  - nested\n1. b", ["- a more a", "- nested", "1. b"]),
        ("See [the guide](CONTRIBUTING.md).", ["See the guide."]),
        ("# Title\n| a | b |\n```text\nlong code\n```\n> Quote", ["Quote"]),
        ("[name]: https://example.org", []),
        ("> a\n>\n> b\n> > c", ["a", "b c"]),
        ("1. a\n   more\n2) b\n3) c", ["1. a more", "2) b", "3) c"]),
        ("## H\ntext\n#1 more", ["text #1 more"]),
        ("~~~\ncode\n~~~\n````md\n```\nstill code\n````\nafter", ["after"]),
        ("[![CI](https://x/badge.svg)](https://x/ci) ok", ["CI ok"]),
    ],
)
def test_prose_blocks(text, blocks):
    assert prose_blocks(text) == blocks


def test_readme_has_no_big_paragraphs():
    long = [block[:60] for block in prose_blocks(read("README.md")) if len(block) > MAX_BLOCK]
    assert long == [], f"README.md: split these into list items of at most {MAX_BLOCK} characters"


def test_security_policy_points_to_private_reporting():
    policy = read("SECURITY.md")
    assert f"{REPO_URL}/security/advisories/new" in policy
    assert "## Supported versions" in policy
    assert "@" not in policy, "no e-mail addresses: reports go through GitHub only"


def test_sponsor_button_points_to_github_sponsors():
    # GitHub reads .github/FUNDING.yml on the default branch for the "Sponsor" button.
    assert read(".github/FUNDING.yml").splitlines() == ["github: cholakhyanerik"]
    assert SPONSORS_URL in read("README.md")


def test_contributing_states_the_inbound_license():
    guide = read("CONTRIBUTING.md")
    assert "GPL-3.0-or-later" in guide
    assert "inbound = outbound" in guide
    assert "](LICENSE)" in guide
    assert "](SECURITY.md)" in guide, "security problems go to the private form, not issues"
    assert not EMAIL.search(guide), "no e-mail addresses in a public guide"


def test_contributing_commit_types_match_claude_md():
    claude = commit_types(read("CLAUDE.md"), "with types ")
    guide = commit_types(read("CONTRIBUTING.md"), "`type` is one of ")
    assert len(claude) >= 5
    assert guide == claude


def test_contributing_checks_match_ci():
    guide = read("CONTRIBUTING.md")
    section = guide.partition("## Check your change")[2].split("\n## ", 1)[0]
    block = re.search(r"```powershell\n(.*?)```", section, re.S)
    assert block, "the checks block in CONTRIBUTING.md is missing"
    listed = {line.split("#")[0].strip() for line in block.group(1).splitlines() if line.strip()}
    runs = re.findall(r"(?m)^\s*- run: (.+?)\s*$", read(".github/workflows/ci.yml"))
    assert "uv sync" in runs
    assert "uv sync" in guide
    # CI checks formatting (`--check`); contributors format.
    assert listed == {cmd.replace(" --check", "") for cmd in runs} - {"uv sync"}


def test_docs_name_the_project_python():
    python = read(".python-version").strip()
    for name in ("README.md", "CONTRIBUTING.md"):
        assert f"Python {python}" in read(name), f"{name} does not say Python {python}"


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_contributing_relative_links_exist():
    # Exact names from git: NTFS would accept `tasks.md` or an ignored file, GitHub would 404.
    paths = repo_paths()
    targets = [a or b for a, b in LINK.findall(read("CONTRIBUTING.md"))]
    local = [t for t in targets if not re.match(r"[a-z]+:|#", t)]
    assert local, "no relative links found"
    for target in local:
        path = unquote(target.split("#")[0]).strip("/")
        assert path in paths, f"CONTRIBUTING.md links to {target}, which is not in the repository"
