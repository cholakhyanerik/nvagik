"""CLAUDE.md stays short, and its details live in path-scoped rules files (rule 15, NVG-18)."""

import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / ".claude" / "rules"
MAX_LINES = 400
MAX_CHARS = 30_000  # 400 lines of 75 characters: long lines must not dodge the line limit
FRONTMATTER = re.compile(r"\A---\n(.*?\n)---\n", re.S)
PATTERN = re.compile(r'  - "([^"\n]+)"')
OWNER_RULE = re.compile(r"^(\d+)\. \*\*", re.M)
# "rule 4", "rules 3, 9, and 12", "rules 4 (security), 5 (...) and 15", "rule 7/8", "rules 5-6"
_NUMBER = r"\d+(?:\s*\([^()]*\))?"
CITED_RULES = re.compile(rf"\brules? ({_NUMBER}(?:(?:,? and |,? or |, |/|-){_NUMBER})*)", re.I)
RULES_FILE = re.compile(r"\.claude/rules/[\w./-]+?\.md")
HEADING = re.compile(r"^#{1,6} (.+?)\s*$", re.M)
ANCHOR_LINK = re.compile(r"\]\(#([^)\s]+)\)")
# Files whose "rule N" and rules file names must be current. CHANGELOG.md is history, and
# test fixtures are untrusted data on purpose.
CITING = (".md", ".py", ".json", ".yml")
SKIPPED = ("CHANGELOG.md", "tests/fixtures/")
# Security rules stay in CLAUDE.md, which every session loads (rule 15).
SECURITY_PHRASES = (
    "PRIVATE.md",
    "noreply",
    "Never bypass the hook",
    "refs/pr/",
    "never check it out",
    "the owner merges",
    "security-auditor",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def repo_files() -> list[str]:
    """Tracked and new (not ignored) files, with git's exact spelling."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [name for name in out.split(chr(0)) if name and (ROOT / name).is_file()]


def citing_files() -> list[str]:
    return [n for n in repo_files() if n.endswith(CITING) and not n.startswith(SKIPPED)]


def cited_numbers(text: str) -> list[int]:
    """Owner's rule numbers cited in `text`, without the notes in parentheses."""
    numbers = []
    for group in CITED_RULES.findall(text):
        numbers += [int(n) for n in re.findall(r"\d+", re.sub(r"\([^()]*\)", "", group))]
    return numbers


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def section(text: str, heading: str) -> str:
    return text.partition(f"\n## {heading}\n")[2].split("\n## ", 1)[0]


def imports(text: str) -> list[str]:
    """`@path` imports Claude Code would follow: code blocks and code spans don't count."""
    text = re.sub(r"(?ms)^ *```.*?^ *```", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    return re.findall(r"(?<![\w@`])@[^\s@]+", text)


def owner_rules() -> list[int]:
    rules = section(read(ROOT / "CLAUDE.md"), "Owner's rules")
    return [int(number) for number in OWNER_RULE.findall(rules)]


def rule_patterns(path: Path) -> list[str] | None:
    """The `paths:` list of a rules file, or None when it has no such frontmatter."""
    match = FRONTMATTER.match(read(path))
    if not match:
        return None
    lines = match.group(1).split("\n")
    if "paths:" not in lines:
        return None
    patterns = []
    for line in lines[lines.index("paths:") + 1 :]:
        if not line.startswith("  "):
            break
        item = PATTERN.fullmatch(line)
        assert item, f'{path.name}: write each pattern as `  - "glob"`, got {line!r}'
        patterns.append(item.group(1))
    return patterns


def rules_files() -> list[Path]:
    return sorted(RULES.rglob("*.md"))


def test_claude_md_is_short():
    text = read(ROOT / "CLAUDE.md")
    lines = len(text.rstrip("\n").split("\n"))
    assert lines <= MAX_LINES, (
        f"CLAUDE.md has {lines} lines (max {MAX_LINES}): move details to .claude/rules/"
    )
    assert len(text) <= MAX_CHARS, (
        f"CLAUDE.md has {len(text)} characters (max {MAX_CHARS}): move details to .claude/rules/"
    )


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("See @docs/GUIDE.md for more.", ["@docs/GUIDE.md"]),
        ("@~/.claude/my-notes.md", ["@~/.claude/my-notes.md"]),
        ("A code span `@docs/GUIDE.md` is not an import.", []),
        ("```text\n@docs/GUIDE.md\n```\n", []),
        ("Mail someone@example.org, or tag `@name`.", []),
    ],
)
def test_import_detection(text, found):
    assert imports(text) == found


def test_claude_md_has_no_imports():
    assert imports(read(ROOT / "CLAUDE.md")) == [], "no @imports: they load at startup anyway"


def test_owner_rules_are_numbered_in_order():
    numbers = owner_rules()
    assert len(numbers) >= 15
    assert numbers == list(range(1, len(numbers) + 1)), (
        "owner's rules keep their numbers 1, 2, 3, ..."
    )


@pytest.mark.parametrize(
    ("text", "numbers"),
    [
        ("CLAUDE.md rules 3, 9, 10, 11 and 12.", [3, 9, 10, 11, 12]),
        ("rules 3, 9, and 12", [3, 9, 12]),
        ("rules 4 (security: a, b), 5 (Python) and 15\n(CLAUDE.md stays short)", [4, 5, 15]),
        ("Rule 1: autonomy; rule 7/8; rules 5-6", [1, 7, 8, 5, 6]),
        ("(rule 12, .claude/rules/github.md)", [12]),
        ("ruff rules E501 and the rules file", []),
    ],
)
def test_rule_citation_detection(text, numbers):
    assert cited_numbers(text) == numbers


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_cited_rules_exist():
    existing = set(owner_rules())
    cited = []
    for name in citing_files():
        text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        cited += [(name, number) for number in cited_numbers(text)]
    assert cited, "no rule citations found; is the pattern still right?"
    missing = [(name, number) for name, number in cited if number not in existing]
    assert missing == [], "these files cite owner's rules that CLAUDE.md doesn't have"


@pytest.mark.parametrize(
    ("text", "patterns"),
    [
        (
            '---\npaths:\n  - "src/**"\n  - "tests/test_*.py"\n---\n# Rules\n',
            ["src/**", "tests/test_*.py"],
        ),
        ('---\ndescription: x\npaths:\n  - "a.md"\nother: 1\n---\n', ["a.md"]),
        ("# Rules without frontmatter\n", None),
        ("---\ndescription: no paths\n---\n", None),
        ("---\npaths:\n---\n", []),
        ('\n---\npaths:\n  - "a.md"\n---\n', None),  # frontmatter must start the file
    ],
)
def test_rule_patterns_parsing(tmp_path, text, patterns):
    path = tmp_path / "rule.md"
    path.write_bytes(text.encode("utf-8"))
    assert rule_patterns(path) == patterns


def test_rules_files_are_path_scoped():
    assert rules_files(), "the details of CLAUDE.md live in .claude/rules/"
    for path in rules_files():
        patterns = rule_patterns(path)
        assert patterns, f"{path.name} needs `paths:` frontmatter, or it loads into every session"
        for pattern in patterns:
            assert not re.search(r"[{}]", pattern), (
                f"{path.name}: write {pattern!r} as two patterns"
            )


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_every_rules_pattern_matches_a_file():
    files = [PurePosixPath(name) for name in repo_files()]
    for path in rules_files():
        for pattern in rule_patterns(path) or []:
            assert any(file.full_match(pattern) for file in files), (
                f"{path.name}: {pattern!r} matches no file, so the rules never load"
            )


def test_claude_md_lists_every_rules_file():
    table = section(read(ROOT / "CLAUDE.md"), "Where the details are")
    listed = set(RULES_FILE.findall(table))
    actual = {path.relative_to(ROOT).as_posix() for path in rules_files()}
    assert actual - listed == set(), "add these rules files to 'Where the details are' in CLAUDE.md"
    assert listed - actual == set(), "CLAUDE.md lists rules files that don't exist"


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_rules_files_named_anywhere_exist():
    for name in citing_files():
        text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        for target in RULES_FILE.findall(text):
            assert (ROOT / target).is_file(), f"{name} points to {target}, which doesn't exist"


@pytest.mark.parametrize(
    ("heading", "anchor"),
    [
        ("Owner's rules", "owners-rules"),
        ("Getting started (development)", "getting-started-development"),
        ("Versioning, CHANGELOG and git", "versioning-changelog-and-git"),
    ],
)
def test_slug(heading, anchor):
    assert slug(heading) == anchor


@pytest.mark.parametrize("name", ["CLAUDE.md", "README.md"])
def test_anchor_links_resolve(name):
    text = read(ROOT / name)
    anchors = {slug(heading) for heading in HEADING.findall(text)}
    broken = [link for link in ANCHOR_LINK.findall(text) if link not in anchors]
    assert broken == [], f"{name} links to headings that don't exist"


def test_security_rules_stay_in_claude_md():
    security = section(read(ROOT / "CLAUDE.md"), "Security")
    missing = [phrase for phrase in SECURITY_PHRASES if phrase not in security]
    assert missing == [], "the Security section of CLAUDE.md lost these rules"
