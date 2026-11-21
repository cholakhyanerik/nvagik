"""End-to-end tests: run the guard hook as Claude Code does, against throwaway repositories.

Each case is a bypass found in review (non-ASCII names, other folders, UTF-16,
messages, history, tags, authors, uploads) and must stay blocked.
Sensitive-looking strings are assembled at run time.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import GUARD_PATH

NOREPLY = "1+tester" + "@" + "users.noreply.github.com"
TOKEN = "ghp_" + "A" * 36
PERSONAL = "someone" + "@" + "gmail.com"
WORK_EMAIL = "dev" + "@" + "example.com"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def commit_all(repo: Path, message: str = "change") -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def run_guard(command: str, cwd: Path) -> str | None:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)})
    proc = subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    git(work, "config", "user.name", "Tester")
    git(work, "config", "user.email", NOREPLY)
    git(work, "config", "commit.gpgsign", "false")
    git(work, "config", "tag.gpgsign", "false")
    (work / ".gitignore").write_text("PRIVATE.md\n", encoding="utf-8")
    (work / "README.md").write_text("hello\n", encoding="utf-8")
    commit_all(work, "init")
    git(work, "remote", "add", "origin", str(remote))
    git(work, "push", "-q", "-u", "origin", "main")
    return work


def test_clean_commit_and_push_are_allowed(repo):
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    assert run_guard("git add -A && git commit -m 'feat: app'", repo) is None
    commit_all(repo)
    assert run_guard("git push origin main --follow-tags", repo) is None


def test_secret_in_non_ascii_file_name_is_blocked(repo):
    (repo / "заметки.md").write_text(f"token {TOKEN}\n", encoding="utf-8")
    assert "a GitHub token in заметки.md" in run_guard("git add -A && git commit -m x", repo)
    git(repo, "add", "-A")
    assert "a GitHub token in заметки.md" in run_guard("git commit -m x", repo)


def test_untracked_secret_outside_the_cwd_is_blocked(repo):
    (repo / "docs").mkdir()
    (repo / "src").mkdir()
    (repo / "docs" / "t.md").write_text(TOKEN, encoding="utf-8")
    assert "docs/t.md" in run_guard("git add -A && git commit -m x", repo / "src")


def test_utf16_file_is_scanned(repo):
    (repo / "out.txt").write_text(f"token {TOKEN}", encoding="utf-16")
    assert "a GitHub token in out.txt" in run_guard("git add -A && git commit -m x", repo)


def test_value_from_private_md_is_blocked(repo):
    (repo / "PRIVATE.md").write_text("Account: 98765432109876\n", encoding="utf-8")
    (repo / "notes.md").write_text("acct 98765432109876\n", encoding="utf-8")
    reason = run_guard("git add -A && git commit -m x", repo)
    assert "a value from PRIVATE.md in notes.md" in reason
    assert "private file PRIVATE.md" not in reason  # ignored, so never committed


def test_personal_email_in_commit_message_is_blocked(repo):
    reason = run_guard(f'git commit --allow-empty -m "contact {PERSONAL}"', repo)
    assert "commit command or message" in reason


def test_non_noreply_author_config_blocks_commit(repo):
    git(repo, "config", "user.email", WORK_EMAIL)
    assert "not a GitHub noreply address" in run_guard("git commit -m x", repo)


def test_push_scans_history_not_just_the_final_tree(repo):
    (repo / "secret.txt").write_text(TOKEN, encoding="utf-8")
    commit_all(repo, "add")
    (repo / "secret.txt").unlink()
    commit_all(repo, "remove")
    assert "a GitHub token in secret.txt" in run_guard("git push", repo)


def test_push_blocks_personal_email_in_commit_message(repo):
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    commit_all(repo, f"contact {PERSONAL}")
    assert "in a commit or tag message" in run_guard("git push", repo)


def test_push_blocks_personal_email_in_tag_message(repo):
    git(repo, "tag", "-a", "v1", "-m", f"by {PERSONAL}")
    assert "in a commit or tag message" in run_guard("git push --follow-tags", repo)


def test_push_blocks_non_noreply_author(repo):
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "-c", f"user.email={WORK_EMAIL}", "commit", "-q", "-m", "b")
    assert "not noreply" in run_guard("git push", repo)


def test_gh_upload_of_private_file_is_blocked(repo):
    (repo / "doc.pdf").write_bytes(b"%PDF-1.7")
    assert "private file doc.pdf" in run_guard("gh release upload v1 doc.pdf", repo)
