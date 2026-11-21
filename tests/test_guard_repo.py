"""End-to-end tests: run the guard hook as Claude Code does, against throwaway repositories.

Each case is a bypass found in review (non-ASCII names, other folders, UTF-16,
files marked binary in .gitattributes, messages, history, tags, authors, uploads)
and must stay blocked.
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


def test_push_scans_text_in_a_file_marked_binary(repo):
    # `binary` in .gitattributes makes `git log -p` print "Binary files ... differ" (NVG-5).
    (repo / ".gitattributes").write_text("*.png binary\n", encoding="utf-8")
    (repo / "notes.png").write_text(f"token {TOKEN}\n", encoding="utf-8")
    commit_all(repo)
    assert "a GitHub token in notes.png" in run_guard("git push", repo)


def test_push_scans_utf16_files(repo):
    (repo / "out.txt").write_text(f"token {TOKEN}", encoding="utf-16")
    commit_all(repo)
    assert "a GitHub token in out.txt" in run_guard("git push", repo)


def test_commit_scans_the_staged_blob_of_a_file_marked_binary(repo):
    (repo / ".gitattributes").write_text("*.png binary\n", encoding="utf-8")
    commit_all(repo)
    (repo / "notes.png").write_text(f"token {TOKEN}\n", encoding="utf-8")
    git(repo, "add", "notes.png")
    (repo / "notes.png").unlink()  # only the staged copy is left
    assert "a GitHub token in notes.png" in run_guard("git commit -m x", repo)


def test_real_binary_files_are_not_false_positives(repo):
    (repo / ".gitattributes").write_text("*.wav binary\n", encoding="utf-8")
    (repo / "click.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00" + bytes(64))
    assert run_guard("git add -A && git commit -m x", repo) is None
    commit_all(repo)
    assert run_guard("git push", repo) is None


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("utf32.txt", f"token {TOKEN}".encode("utf-32")),  # its BOM starts like UTF-16's
        ("nobom.txt", f"token {TOKEN}".encode("utf-16-le")),
        ("stray.txt", f"token {TOKEN}\0\n".encode()),
        ("ru.txt", ("Привет, мир. " * 40 + TOKEN).encode("utf-16-le")),
    ],
    ids=["utf-32", "utf-16-without-bom", "stray-nul", "cyrillic-utf-16-without-bom"],
)
def test_push_scans_other_text_encodings(repo, name, data):
    (repo / name).write_bytes(data)
    commit_all(repo)
    assert f"a GitHub token in {name}" in run_guard("git push", repo)


def test_text_files_up_to_8_mb_are_scanned_whole(repo):
    (repo / ".gitattributes").write_text("*.log binary\n", encoding="utf-8")
    (repo / "big.log").write_text("x" * 1_100_000 + " " + TOKEN, encoding="utf-16")
    commit_all(repo)
    assert "a GitHub token in big.log" in run_guard("git push", repo)
    (repo / "big.txt").write_text("x" * 1_100_000 + " " + TOKEN, encoding="utf-8")
    assert "a GitHub token in big.txt" in run_guard("git add -A && git commit -m x", repo)


def test_text_over_8_mb_is_blocked_as_unscannable(repo):
    (repo / "huge.txt").write_text("x" * 8_100_000, encoding="utf-8")
    assert "huge.txt is over 8 MB" in run_guard("git add -A && git commit -m x", repo)


def test_large_binary_tables_are_not_taken_for_utf16(repo):
    # Font tables are big-endian 16-bit numbers: NUL, then a byte, like UTF-16BE text.
    table = b"".join(bytes((0, i % 250 + 1)) for i in range(800_000))  # 1.6 MB
    (repo / ".gitattributes").write_text("*.ttf binary\n", encoding="utf-8")
    (repo / "font.ttf").write_bytes(table)
    assert run_guard("git add -A && git commit -m x", repo) is None
    commit_all(repo)
    assert run_guard("git push", repo) is None


def test_git_lfs_pointers_are_blocked(repo):
    pointer = "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 9\n"
    (repo / "notes.png").write_text(pointer, encoding="utf-8")
    commit_all(repo)
    assert "a Git LFS pointer" in run_guard("git push", repo)


def test_line_separator_in_a_file_name_does_not_hide_a_binary_entry(repo):
    (repo / ".gitattributes").write_text("*.png binary\n", encoding="utf-8")
    (repo / f"x{chr(0x2028)}y.png").write_text(f"token {TOKEN}\n", encoding="utf-8")
    commit_all(repo)
    assert "a GitHub token in" in run_guard("git push", repo)


def test_carriage_return_does_not_fake_a_diff_header(repo):
    (repo / "a.txt").write_bytes(f"x\rdiff --git a/q b/q\n{TOKEN}\n".encode())
    commit_all(repo)
    assert "a GitHub token in a.txt" in run_guard("git push", repo)


def test_push_scans_content_added_in_a_merge_commit(repo):
    git(repo, "checkout", "-q", "-b", "side")
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    commit_all(repo, "side")
    git(repo, "checkout", "-q", "main")
    (repo / "main.txt").write_text("main\n", encoding="utf-8")
    commit_all(repo, "main")
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "side")
    (repo / "merge.txt").write_text(TOKEN, encoding="utf-8")
    git(repo, "add", "merge.txt")
    git(repo, "commit", "-q", "-m", "merge")
    git(repo, "branch", "-D", "side")
    assert "a GitHub token in merge.txt" in run_guard("git push", repo)


def test_push_scans_commits_on_a_detached_head(repo):
    git(repo, "checkout", "-q", "--detach")
    (repo / "detached.txt").write_text(TOKEN, encoding="utf-8")
    commit_all(repo)
    assert "a GitHub token in detached.txt" in run_guard("git push origin HEAD:main", repo)


def test_push_scans_root_commits_despite_log_show_root(repo):
    git(repo, "config", "log.showRoot", "false")
    git(repo, "checkout", "-q", "--orphan", "other")
    (repo / "root.txt").write_text(TOKEN, encoding="utf-8")
    commit_all(repo, "root")
    assert "a GitHub token in root.txt" in run_guard("git push origin other", repo)


def test_tags_that_point_at_a_blob_are_blocked(repo):
    (repo / "loose.txt").write_text(TOKEN, encoding="utf-8")
    blob = subprocess.run(
        ["git", "hash-object", "-w", "loose.txt"], cwd=repo, check=True, capture_output=True
    ).stdout.decode()
    (repo / "loose.txt").unlink()
    git(repo, "tag", "leak", blob.strip())
    assert "tag leak points at a blob" in run_guard("git push --tags", repo)


def blob_id(repo: Path, content: str) -> str:
    proc = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo,
        input=content.encode(),
        check=True,
        capture_output=True,
    )
    return proc.stdout.decode().strip()


def test_push_of_a_blob_as_the_source_is_blocked(repo):
    blob = blob_id(repo, TOKEN)
    reason = run_guard(f"git push origin {blob}:refs/tags/x", repo)
    assert f"push source {blob} is a blob" in reason


def test_push_scans_a_stash_given_as_the_source(repo):
    (repo / "README.md").write_text(f"hello {TOKEN}\n", encoding="utf-8")
    git(repo, "stash", "-q")
    reason = run_guard("git push origin stash@{0}:refs/heads/x", repo)
    assert "a GitHub token in README.md" in reason


def test_push_scans_a_commit_that_is_on_no_branch(repo):
    (repo / "gone.txt").write_text(TOKEN, encoding="utf-8")
    commit_all(repo)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True
    ).stdout.decode()
    git(repo, "reset", "-q", "--hard", "HEAD~1")
    reason = run_guard(f"git push origin {commit.strip()}:refs/heads/x", repo)
    assert "a GitHub token in gone.txt" in reason


def test_an_already_pushed_blob_tag_only_matters_when_tags_are_pushed(repo):
    git(repo, "tag", "old", blob_id(repo, "harmless"))
    git(repo, "push", "-q", "origin", "refs/tags/old")
    (repo / "c.txt").write_text("c\n", encoding="utf-8")
    commit_all(repo)
    assert run_guard("git push origin main --follow-tags", repo) is None
    assert "tag old points at a blob" in run_guard("git push --tags", repo)


def test_gh_upload_of_private_file_is_blocked(repo):
    (repo / "doc.pdf").write_bytes(b"%PDF-1.7")
    assert "private file doc.pdf" in run_guard("gh release upload v1 doc.pdf", repo)
