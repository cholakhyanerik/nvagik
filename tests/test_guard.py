"""Unit tests for the security guard hook (.claude/hooks/guard.py).

Sensitive-looking strings are assembled at run time so this file itself never
contains anything the guard would block on commit.
"""

import pytest


@pytest.mark.parametrize(
    "command",
    [
        "git clean -fdX",
        "git clean -xfd",
        "git --no-pager clean -fdx",
        "git stash --all",
        "git stash -a",
        "git add -f PRIVATE.md",
        "git add -fA",
        "git add --force secrets.txt",
        "git push --force origin main",
        "git push -f",
        "git push -fu origin main",
        "git push origin +main",
        "git --no-pager push --force",
        "git.exe push --force",
        "rm PRIVATE.md",
        "rm -f *.md",
        "rm -rf .",
        "mv C:/dev/nvagik/PRIVATE.md backup.md",
        "Remove-Item .\\PRIVATE.md",
        "Remove-Item *.md -Force",
        "Set-Content -Path PRIVATE.md -Value x",
        "cp notes.md PRIVATE.md",
        "Copy-Item a.md PRIVATE.md -Force",
        "echo x | tee PRIVATE.md",
        "sed -i s/a/b/ PRIVATE.md",
        "git rm PRIVATE.md",
        "git mv PRIVATE.md notes.md",
        "echo x > PRIVATE.md",
        "echo x >> PRIVATE.md",
    ],
)
def test_dangerous_commands_are_blocked(guard, command):
    assert guard.check_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git add -A",
        "git clean -n",
        "git clean -fd",
        "git stash",
        "git stash pop",
        "git push --force-with-lease origin main",
        "git push origin main --follow-tags",
        "git push -u origin main",
        "cat PRIVATE.md",
        "git check-ignore -v PRIVATE.md",
        "uv run pytest 2>&1 | grep PRIVATE.md",
        "git rm --cached PRIVATE.md",
        'git commit -m "docs: move PRIVATE.md notes"',
        "git commit -F - <<'EOF'\nchore: tidy\n\nrm PRIVATE.md is never allowed\nEOF",
        "rm -rf build/*",
        "rm -f tests/_format_probe.py",
        "printf 'rename PRIVATE.md'",
        "Remove-Item .\\leak_test.txt",
    ],
)
def test_safe_commands_are_allowed(guard, command):
    assert guard.check_command(command) is None


@pytest.mark.parametrize(
    ("command", "commit", "push"),
    [
        ("git commit -m x", True, False),
        ("git add -A && git commit -F - <<'EOF'\nmsg\nEOF", True, False),
        ("git --no-pager commit -m x", True, False),
        ("git.exe commit -m x", True, False),
        ('git -C "a b" commit -m x', True, False),
        ("git --git-dir=.git --work-tree=. commit -m x", True, False),
        ("git -C repo push origin main", False, True),
        ("git -P push", False, True),
        ("gh repo create nvagik --public --source . --push", False, True),
        ("gh pr create --fill", False, True),
        ("gh release upload v1 dist/app.msix", False, True),
        ("cat > notes.txt <<'EOF'\ngit push\nEOF", False, False),
        ("git status", False, False),
    ],
)
def test_commit_and_push_detection(guard, command, commit, push):
    text = guard.strip_heredocs(command)
    assert bool(guard.COMMIT.search(text)) is commit
    assert bool(guard.PUSH.search(text)) is push


@pytest.mark.parametrize(
    "path", ["PRIVATE.md", "docs/Nvagik.pdf", ".env", ".env.local", "keys/server.pem", "id_rsa"]
)
def test_private_paths_are_forbidden(guard, path):
    assert guard.is_forbidden_path(path)


@pytest.mark.parametrize("path", ["README.md", ".env.example", "src/nvagik/keyboard.py"])
def test_regular_paths_are_allowed(guard, path):
    assert not guard.is_forbidden_path(path)


def test_secrets_and_personal_data_are_detected(guard):
    assert guard.scan_text("token: " + "ghp_" + "A" * 36, set())
    assert guard.scan_text("contact " + "someone" + "@" + "gmail.com", set())
    assert guard.scan_text("api_key = '" + "x" * 20 + "'", set())
    assert guard.scan_text("account 12345678901 here", {"12345678901"}) == [
        "a value from PRIVATE.md"
    ]


def test_clean_text_passes(guard):
    noreply = "111+someone" + "@" + "users.noreply.github.com"
    assert guard.scan_text(f"Author: {noreply}", set()) == []
    assert guard.scan_text("hash 0a12345678901bc", {"12345678901"}) == []


def test_private_values_are_extracted(guard, tmp_path):
    (tmp_path / "PRIVATE.md").write_text(
        "- Account: 98765432109876\n- Reg: 123.4567890\n- SWIFT: ABCDEF12 (ABCDEF12XXX)\n"
        "- Date: 2026-01-01\n- Word: PRIVATEMD\n",
        encoding="utf-8",
    )
    assert guard.private_values(tmp_path) == {
        "98765432109876",
        "123.4567890",
        "ABCDEF12",
        "ABCDEF12XXX",
    }


def test_added_lines_are_grouped_by_file(guard):
    diff = "\n".join(
        [
            "diff --git a/a.py b/a.py",
            "--- a/a.py",
            "+++ b/a.py",
            "@@ -0,0 +1,2 @@",
            "+one",
            "+++ not a header",
            'diff --git "a/notes q.md" "b/notes q.md"',
            "new file mode 100644",
            "--- /dev/null",
            '+++ "b/notes q.md"',
            "@@ -0,0 +1 @@",
            "+two",
            "diff --git a/gone.txt b/gone.txt",
            "deleted file mode 100644",
            "--- a/gone.txt",
            "+++ /dev/null",
            "@@ -1 +0,0 @@",
            "-old",
        ]
    )
    assert guard.added_lines_by_file(diff) == {
        "a.py": ["one", "++ not a header"],
        "notes q.md": ["two"],
    }


def test_binary_entries_map_new_blob_ids_to_file_names(guard):
    new, old, zero = "1" * 40, "2" * 40, "0" * 40
    diff = "\n".join(
        [
            "diff --git a/notes.png b/notes.png",
            "new file mode 100644",
            f"index {zero}..{new}",
            "Binary files /dev/null and b/notes.png differ",
            "diff --git a/gone.wav b/gone.wav",
            "deleted file mode 100644",
            f"index {old}..{zero}",
            "Binary files a/gone.wav and /dev/null differ",
            "diff --git a/a.py b/a.py",
            f"index {old}..{new[:-1]}3 100644",
            "--- a/a.py",
            "+++ b/a.py",
            "@@ -0,0 +1 @@",
            "+Binary files x and y differ",
        ]
    )
    assert guard.binary_blobs(diff) == {new: "notes.png"}


def test_decode_small_reads_text_encodings_and_skips_real_binaries(guard):
    assert guard.decode_small("tok".encode("utf-16")) == "tok"
    assert guard.decode_small("tok".encode("utf-32")) == "tok"
    assert guard.decode_small("token".encode("utf-16-be")) == "token"
    assert guard.decode_small(b"plain\x00") == "plain"
    assert guard.decode_small(b"plain") == "plain"
    assert guard.decode_small(b"RIFF\x00\x00WAVE") is None
    assert guard.decode_small(b"RIFF\x24\x00\x00\x00WAVEfmt " + bytes(64)) is None
