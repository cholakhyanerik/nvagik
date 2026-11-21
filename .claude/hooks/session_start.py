"""SessionStart hook: Python and dependency drift, GitHub security, git state, next tasks.

Implements CLAUDE.md rules 4 (security: private vulnerability reports and
Dependabot alerts, see SECURITY.md), 5 (Python follows the system), 6
(dependencies stay current) and 9 (TASKS.md drives the work). Standard library only: it runs with
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
from pathlib import Path

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


def git_status() -> str:
    out = run("git", "status", "--porcelain=v1", "--branch")
    if out is None:
        return "Git: not available"
    lines = out.splitlines()
    head = lines[0] if lines else ""
    changes = len(lines) - 1
    parts = [head.removeprefix("## ").split("...")[0] or "?"]
    parts.append(f"{changes} uncommitted change(s)" if changes else "working tree clean")
    if ahead := re.search(r"ahead (\d+)", head):
        parts.append(f"{ahead.group(1)} commit(s) not pushed")
    if behind := re.search(r"behind (\d+)", head):
        parts.append(f"{behind.group(1)} commit(s) behind origin -> pull first")
    return "Git: " + ", ".join(parts)


def next_tasks(limit: int = 5) -> str:
    try:
        text = (ROOT / "TASKS.md").read_text(encoding="utf-8")
    except OSError:
        return "TASKS.md: missing -> create it (rule 9)"
    section = text.partition("## Next up")[2].split("\n## ", 1)[0]
    items = [line.strip() for line in section.splitlines() if re.match(r"\s*\d+\.\s", line)]
    if not items:
        return "TASKS.md: 'Next up' is empty -> refill it from the backlog"
    return "Next up (TASKS.md):\n" + "\n".join(f"  {item}" for item in items[:limit])


def main() -> None:
    with ThreadPoolExecutor(max_workers=1) as pool:
        # Network checks run side by side so the hook stays within its 60 s timeout.
        security = pool.submit(github_security_status)
        lines = ["Nvagik session check (.claude/hooks/session_start.py):", python_status()]
        if uv := uv_status():
            lines.append(uv)
        lines += [dependency_status(), security.result(), git_status(), next_tasks()]
    context = "\n".join(lines)
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
        )
    )


if __name__ == "__main__":
    main()
