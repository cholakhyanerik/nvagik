"""Stop hook: if work is left uncommitted or unpushed, ask Claude to finish the task.

Enforces the Definition of done in CLAUDE.md (commit and push after every task,
then clean up). Blocks the stop at most once in a row (`stop_hook_active`), so it
can never loop.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git(*args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return proc.stdout if proc.returncode == 0 else None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    if data.get("stop_hook_active"):
        return
    status = git("status", "--porcelain=v1")
    if status is None:
        return
    dirty = [line[3:] for line in status.splitlines() if line.strip()]
    ahead_raw = (git("rev-list", "--count", "@{u}..HEAD") or "").strip()
    ahead = int(ahead_raw) if ahead_raw.isdigit() else 0
    if not dirty and not ahead:
        return
    parts = []
    if dirty:
        shown = ", ".join(dirty[:8]) + (f" and {len(dirty) - 8} more" if len(dirty) > 8 else "")
        parts.append(f"{len(dirty)} uncommitted change(s): {shown}")
    if ahead:
        parts.append(f"{ahead} commit(s) not pushed to origin")
    reason = (
        "Before stopping: "
        + "; ".join(parts)
        + ". If a task is finished, run the finish-task skill (verify, TASKS.md, "
        "CHANGELOG.md, version, README.md, CLAUDE.md, .claude/rules/, commit, push, "
        "clean up). If the "
        "work is intentionally unfinished or the owner only asked a question, say so "
        "briefly and stop."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
