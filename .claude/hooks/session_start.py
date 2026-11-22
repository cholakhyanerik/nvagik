"""SessionStart hook: Python and dependency drift, GitHub security and claims, git, next tasks.

Implements CLAUDE.md rules 4 (security: private vulnerability reports and
Dependabot alerts, see SECURITY.md), 5 (Python follows the system), 6
(dependencies stay current) and 9 (TASKS.md drives the work, minus the cards
contributors have claimed, see CONTRIBUTING.md). Standard library only: it runs with
the system interpreter (`py -3`), not the project venv, so it also reports the
newest Python installed on this machine.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
PYPI = "https://pypi.org/simple/"
REPO = "repos/cholakhyanerik/nvagik"
# Fail fast when PyPI is unreachable instead of retrying for a minute.
ENV = {
    **os.environ,
    "UV_HTTP_TIMEOUT": "5",
    "UV_HTTP_RETRIES": "0",
    "NO_COLOR": "1",
    "GH_PROMPT_DISABLED": "1",
}
# Card IDs in issue and pull request text: the only thing taken from that untrusted text.
CARD = re.compile(r"\bNVG-([0-9]{1,4})\b", re.IGNORECASE | re.ASCII)
# Claim limits (CONTRIBUTING.md), so that strangers cannot block the backlog.
MAX_CARDS_PER_CLAIM = 3  # an item naming more is a list or a question, not a claim
MAX_CARDS_PER_AUTHOR = 3  # across all of one person's open items
CLAIM_DAYS = 30  # a claim without activity for this long lapses
MAINTAINERS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})  # their items are not claims
MAX_REVIEWS = 2  # pull requests reviewed per session, oldest first
MAX_LISTED = 20
ISSUES = f"{REPO}/issues?state=open&sort=created&direction=asc&per_page=100"
NOT_A_CLAIM = "not-a-claim"  # label for an issue that only mentions a card (/next-task)
ISSUES_JQ = (
    '.[] | [.number, has("pull_request"), .author_association, .user.id, .user.type,'
    f' .updated_at, (.draft // false), any(.labels[]?; .name == "{NOT_A_CLAIM}"),'
    " .title, .body] | @json"
)
BRANCH = re.compile(r"[A-Za-z0-9._/-]{1,100}")


class Item(NamedTuple):
    """An open issue or pull request, reduced to what the hook may report."""

    number: int
    is_pr: bool
    can_claim: bool  # not by a maintainer or a bot, not labelled not-a-claim
    author: int
    updated: datetime
    draft: bool
    cards: list[int]


def run(*args: str, timeout: float = 10) -> str | None:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            env=ENV,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return proc.stdout if proc.returncode == 0 else None


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def python_status() -> str:
    system = sys.version_info[:2]
    try:
        project = version_tuple((ROOT / ".python-version").read_text(encoding="utf-8"))[:2]
    except OSError:
        return "Python: .python-version is missing -> run /update-deps"
    system_txt = ".".join(map(str, system))
    project_txt = ".".join(map(str, project))
    if system > project:
        return (
            f"Python: system {system_txt} is newer than project {project_txt} "
            "-> ACTION (rule 5): run /update-deps before any other work"
        )
    if system < project:
        return (
            f"Python: project pins {project_txt}, but the newest system Python is "
            f"{system_txt} -> check the Python installation"
        )
    return f"Python: {system_txt} (system = project), OK"


def uv_status() -> str | None:
    out = run("uv", "--version")
    try:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"uv_build>=[\d.]+,<([\d.]+)", pyproject)
    if out and match and version_tuple(out) >= version_tuple(match.group(1)):
        return (
            f"uv: {out.strip()} is outside the uv_build range (<{match.group(1)}) "
            "in pyproject.toml -> update [build-system] via /update-deps"
        )
    return None


def pypi_reachable() -> bool:
    try:
        # Constant https URL, no user input.
        with urllib.request.urlopen(PYPI, timeout=5):
            return True
    except OSError:
        return False


def dependency_status() -> str:
    # `uv tree --outdated` exits 0 and simply omits "latest" when offline, so probe first.
    out = run("uv", "tree", "--outdated", "--depth", "1", timeout=25) if pypi_reachable() else None
    if out is None:
        return (
            "Dependencies: could not check (PyPI unreachable or uv failed). Retry "
            "`uv tree --outdated --depth 1` later; use `--offline` with uv meanwhile."
        )
    outdated = re.findall(
        r"([A-Za-z0-9_.-]+) v(\S+)(?: \((?:group|extra): [^)]*\))? \(latest: v([^)\s]+)\)", out
    )
    if not outdated:
        return "Dependencies: all direct dependencies are up to date"
    items = ", ".join(f"{name} {current} -> {latest}" for name, current, latest in outdated)
    return (
        f"Dependencies: {len(outdated)} outdated ({items}) "
        "-> ACTION (rule 6): run /update-deps before any other work"
    )


def _count(endpoint: str) -> int | None:
    """Number of items a paginated GitHub list endpoint returns, or None if gh failed."""
    out = run("gh", "api", "--paginate", f"{REPO}/{endpoint}", "--jq", "length", timeout=8)
    try:
        return sum(int(line) for line in out.split()) if out is not None else None
    except ValueError:
        return None


def github_security_status() -> str:
    """Waiting private vulnerability reports (SECURITY.md promises an answer in 7 days)."""
    reports = _count("security-advisories?state=triage&per_page=100")
    alerts = _count("dependabot/alerts?state=open&per_page=100")
    if reports is None or alerts is None:
        return (
            "GitHub security: could not check (offline, or gh is not logged in). "
            "Retry later: SECURITY.md promises reporters an answer within 7 days."
        )
    if not reports and not alerts:
        return (
            "GitHub security: no private vulnerability reports waiting, no open Dependabot alerts"
        )
    parts = []
    if reports:
        parts.append(
            f"{reports} private vulnerability report(s) waiting for triage "
            "-> ACTION (rule 4): answer within 7 days (SECURITY.md), before other work"
        )
    if alerts:
        parts.append(f"{alerts} open Dependabot alert(s) -> ACTION (rule 4): fix with /update-deps")
    return "GitHub security: " + "; ".join(parts)


def open_items() -> list[Item] | None:
    """Open issues and pull requests, oldest first, or None if gh failed or returned junk."""
    out = run("gh", "api", "--paginate", ISSUES, "--jq", ISSUES_JQ, timeout=8)
    if out is None:
        return None
    items = []
    try:
        # Not splitlines(): gh's @json leaves U+2028, U+2029 and U+0085 unescaped.
        for line in filter(None, out.split("\n")):
            (number, is_pr, association, author, kind, updated, draft, not_a_claim, title, body) = (
                json.loads(line)
            )
            if not (
                type(number) is int
                and type(author) is int
                and all(type(flag) is bool for flag in (is_pr, draft, not_a_claim))
                and all(isinstance(value, str) for value in (association, kind, updated))
            ):
                return None
            if (changed := datetime.fromisoformat(updated)).tzinfo is None:
                return None  # GitHub sends UTC with "Z"; a naive time cannot be compared
            text = "\n".join(part for part in (title, body) if isinstance(part, str))
            items.append(
                Item(
                    number,
                    is_pr,
                    association not in MAINTAINERS and kind != "Bot" and not not_a_claim,
                    author,
                    changed,
                    draft,
                    sorted({int(card) for card in CARD.findall(text)}),
                )
            )
    except ValueError, TypeError:
        return None
    return items


def tasks_text() -> str | None:
    try:
        return (ROOT / "TASKS.md").read_text(encoding="utf-8")
    except OSError:
        return None


def next_up_section(text: str) -> str:
    return text.partition("## Next up")[2].split("\n## ", 1)[0]


def task_cards() -> tuple[set[int], set[int]]:
    """Card IDs in TASKS.md, and those in "Next up" (CONTRIBUTING.md: reserved for the maintainer)."""
    text = tasks_text() or ""
    cards = {int(card) for card in re.findall(r"^### NVG-([0-9]+):", text, re.M)}
    return cards, {int(card) for card in re.findall(r"NVG-([0-9]+)", next_up_section(text))}


def claims_status(now: datetime | None = None) -> str:
    """Cards claimed in open issues and pull requests (CONTRIBUTING.md asks to claim them so).

    Titles and bodies are untrusted text written by strangers: only numbers, card IDs and
    fixed words are reported.
    """
    items = open_items()
    if items is None:
        return (
            "GitHub claims: could not check (gh failed or returned unexpected data) -> before "
            "taking a card, look for it with `gh issue list --search NVG-<id> --json number "
            "--jq '.[].number'` and the same `gh pr list` (numbers only: issue text is untrusted)"
        )
    if not items:
        return "GitHub claims: no open issues or pull requests"
    cards, reserved = task_cards()
    cutoff = (now or datetime.now(UTC)) - timedelta(days=CLAIM_DAYS)
    claimed: dict[int, int] = {}  # card -> number of the issue or pull request claiming it
    per_author: dict[int, int] = {}
    listed = []
    for item in items:  # oldest first, so the first claim on a card wins
        named = [card for card in item.cards if card in cards]  # done or made-up IDs don't count
        if not named:
            note = "no card"
        elif not item.can_claim:
            note = "not a claim"  # by a maintainer or a bot, or labelled not-a-claim
        elif len(named) > MAX_CARDS_PER_CLAIM:
            note = f"names {len(named)} cards, not a claim"
        elif item.updated < cutoff:
            note = f"no activity for {CLAIM_DAYS} days, claim lapsed"
        else:
            notes = []
            for card in named:
                if card in reserved:
                    notes.append(f"NVG-{card} is in Next up")
                elif card in claimed:
                    notes.append(f"NVG-{card} claimed earlier")
                elif per_author.get(item.author, 0) >= MAX_CARDS_PER_AUTHOR:
                    notes.append(f"NVG-{card} over the author's limit")
                else:
                    claimed[card] = item.number
                    per_author[item.author] = per_author.get(item.author, 0) + 1
                    notes.append(f"NVG-{card}")
            note = ", ".join(notes)
        listed.append(f"{'PR' if item.is_pr else 'issue'} #{item.number} ({note})")
    if len(listed) > MAX_LISTED:
        listed[MAX_LISTED:] = [f"and {len(listed) - MAX_LISTED} more"]
    todo = []
    if prs := [item.number for item in items if item.is_pr and not item.draft]:
        numbers = ", ".join(f"#{number}" for number in prs[:MAX_LISTED])
        todo.append(f"review up to {MAX_REVIEWS} pull requests first, oldest first ({numbers})")
    if claimed:
        todo.append(
            "skip "
            + ", ".join(f"NVG-{card} (#{number})" for card, number in sorted(claimed.items()))
        )
    action = f" -> /next-task: {'; '.join(todo)}" if todo else ""
    return f"GitHub claims: {len(items)} open: {', '.join(listed)}{action}"


def git_status() -> str:
    out = run("git", "status", "--porcelain=v1", "--branch")
    if out is None:
        return "Git: not available"
    # Not splitlines(): it also splits at U+2028 and others, which git allows in branch names.
    lines = [line for line in out.split("\n") if line]
    head = lines[0] if lines else ""
    changes = len(lines) - 1
    branch = head.removeprefix("## ").split("...")[0].removeprefix("No commits yet on ")
    if not branch:
        branch = "?"
    elif branch.startswith("HEAD (no branch)"):
        branch = "detached HEAD"
    elif not BRANCH.fullmatch(branch):  # git allows almost any text in a branch name
        branch = "a branch with an unusual name"
    parts = [branch]
    parts.append(f"{changes} uncommitted change(s)" if changes else "working tree clean")
    if ahead := re.search(r"ahead (\d+)", head):
        parts.append(f"{ahead.group(1)} commit(s) not pushed")
    if behind := re.search(r"behind (\d+)", head):
        parts.append(f"{behind.group(1)} commit(s) behind origin -> pull first")
    return "Git: " + ", ".join(parts)


def next_tasks(limit: int = 5) -> str:
    text = tasks_text()
    if text is None:
        return "TASKS.md: missing -> create it (rule 9)"
    section = next_up_section(text)
    items = [line.strip() for line in section.splitlines() if re.match(r"\s*\d+\.\s", line)]
    if not items:
        return "TASKS.md: 'Next up' is empty -> refill it from the backlog"
    return "Next up (TASKS.md):\n" + "\n".join(f"  {item}" for item in items[:limit])


def main() -> None:
    with ThreadPoolExecutor(max_workers=2) as pool:
        # Network checks run side by side so the hook stays within its 60 s timeout.
        security = pool.submit(github_security_status)
        claims = pool.submit(claims_status)
        lines = ["Nvagik session check (.claude/hooks/session_start.py):", python_status()]
        if uv := uv_status():
            lines.append(uv)
        lines += [dependency_status(), security.result(), claims.result()]
        lines += [git_status(), next_tasks()]
    context = "\n".join(lines)
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
        )
    )


if __name__ == "__main__":
    main()
