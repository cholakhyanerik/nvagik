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
        "- Date: 2026-01-01\n- Word: PRIVATEMD\n- Mail: " + "owner" + "@" + "example.am\n",
        encoding="utf-8",
    )
    assert guard.private_values(tmp_path) == {
        "98765432109876",
        "123.4567890",
        "ABCDEF12",
        "ABCDEF12XXX",
        "owner" + "@" + "example.am",
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


@pytest.mark.parametrize(
    ("command", "files"),
    [
        ("gh issue comment 5 --body-file a.md", ["a.md"]),
        ("gh pr review 7 -F a.md && gh pr comment 7 -Fb.md", ["a.md", "b.md"]),
        ("gh issue create --body-file=a.md --title t", ["a.md"]),
        ("gh issue comment 5 --body-file -", []),
        ("gh api x -F body=@a.md -f title=t --input b.json", ["a.md", "b.json"]),
        ("gh api x -F foo=bar", []),  # -F is a field for api, not a file
        ("gh api x -f body=@alice", []),  # a raw field never reads a file
        ("gh workflow run ci.yml -F x=1", []),  # -F is an input here
        (r"C:\tools\gh.exe pr comment 7 -F C:\tmp\a.md", ["C:/tmp/a.md"]),
        ("gh -R o/r issue comment 5 -F a.md", ["a.md"]),
        ("gh release create v1 --notes-file n.md", ["n.md"]),
        ("gh pr merge 5 --squash --subject 'fix(x): y (NVG-5)' --body-file m.md", ["m.md"]),
        ("gh pr comment 5 --body-file", [""]),
    ],
)
def test_gh_text_files(guard, command, files):
    assert guard.gh_text_files(command) == files


@pytest.mark.parametrize(
    ("command", "write"),
    [
        ("gh issue comment 5 -b hi", True),
        ("gh issue new -b hi", True),
        ("gh issue reopen 5 --comment hi", True),
        ("gh pr merge 7 --squash", True),
        ("gh pr review 7 --approve", True),
        ("gh issue close 5 --comment bye", True),
        ("gh -R o/r issue comment 5 -b hi", True),
        ("GH issue comment 5 -b hi", True),
        ('"C:/Program Files/GitHub CLI/gh.exe" issue comment 5 -b hi', True),
        ("gh release create v1 --notes hi", True),
        ("gh gist edit 1 -a f.md", True),
        ("gh repo edit --description hi", True),
        ("gh label create x --description hi", True),
        ("gh workflow run ci.yml -f x=1", True),
        ("gh api -X POST repos/o/r/actions/runs/1/approve", True),
        ("gh api repos/o/r/issues/5/comments -f body=hi", True),
        ("gh api graphql -F query=@q.graphql", True),
        ("gh api repos/o/r --input body.json", True),
        ("gh api repos/o/r", False),
        ("gh api -X GET repos/o/r", False),
        ("gh api --paginate repos/o/r/issues --jq '.[].number'", False),
        ("gh pr view 7", False),
        ("gh pr diff 7", False),
        ("gh issue list", False),
        ("gh run watch 1", False),
    ],
)
def test_gh_write_detection(guard, command, write):
    found = guard.GH_WRITE.search(command) or guard.GH_API_WRITE.search(command)
    assert bool(found) is write


@pytest.mark.parametrize(
    ("command", "problem"),
    [
        ('gh issue comment 5 --body "$(cat notes.md)"', "command substitution"),
        ("gh issue comment 5 --body `cat notes.md`", "command substitution"),
        ("gh issue comment 5 --body $env:NOTES", "command substitution or a variable"),
        ('gh issue comment 5 --body "$NOTES"', "command substitution or a variable"),
        ("gh issue comment 5 --body %NOTES%", "command substitution or a variable"),
        ("gh issue comment 5 --body (Get-Content notes.md -Raw)", "parentheses"),
        ("gh issue comment 5 -F - < notes.md", "a redirect"),
        ("cat notes.md | gh issue comment 5 -F -", "standard input"),
        ("gh api repos/o/r/issues/5/comments -F body=@-", "standard input"),
        ("echo hi >> reply.md && gh issue comment 5 -F reply.md", "a redirect"),
        ("cd sub && gh issue comment 5 -F reply.md", "a change of directory"),
        ("Set-Location sub; gh issue comment 5 -F reply.md", "a change of directory"),
        ("gh issue comment 5 -b hi --attach notes.md#x", "--attach"),
    ],
)
def test_post_problems(guard, command, problem):
    assert any(problem in found for found in guard.post_problems(command))


@pytest.mark.parametrize(
    "command",
    [
        "gh issue comment 5 --body 'Thanks! $5 (or more) > nothing'",
        'gh issue comment 5 --body "Thanks (really)"',
        "gh pr merge 5 --squash --match-head-commit 0123abc --subject 'fix(x): y (NVG-5)' -F m.md",
        "gh api -X POST repos/o/r/actions/runs/1/approve 2>&1",
        "gh api repos/o/r/issues/5/comments -f body='@alice thanks'",
    ],
)
def test_clean_posts_have_no_problems(guard, command):
    assert guard.post_problems(command) == []


def test_stdin_from_a_heredoc_is_fine(guard):
    command = "gh issue comment 5 --body-file - <<'EOF'\nThanks!\nEOF"
    text = guard.strip_heredocs(command)
    assert guard.post_problems(text, heredoc=True) == []
    assert guard.post_problems(text) != []


@pytest.mark.parametrize(
    ("command", "kept"),
    [
        ("git commit -F - <<'EOF'\nmsg\nEOF", "git commit -F - \n"),
        # The rest of the `<<EOF` line is still a command.
        ("cat <<'EOF' | git commit -F -\nmsg\nEOF", "cat  | git commit -F -\n"),
        ("cat <<'EOF' > PRIVATE.md\nx\nEOF", "cat  > PRIVATE.md\n"),
        # `<<EOF` in quotes or a comment starts no heredoc: the next lines are commands.
        ("echo '<<EOF'\ngit push\nEOF", "echo '<<EOF'\ngit push\nEOF"),
        ("echo x # <<EOF\ngit push\nEOF", "echo x # <<EOF\ngit push\nEOF"),
        ("git commit -F - @'\nmsg\n'@", "git commit -F - \n"),
    ],
)
def test_strip_heredocs(guard, command, kept):
    assert guard.strip_heredocs(command) == kept


@pytest.mark.parametrize(
    "command",
    [
        "gh auth token",
        "gh auth status --show-token",
        "gh auth status -t",
        "git credential fill",
        "gh pr checkout 13",
        "gh co 13",
        "git checkout refs/pr/13",
        "git switch --detach refs/pr/13",
        "git worktree add ../pr13 refs/pr/13",
        "git merge refs/pr/13",
        "git pull origin pull/13/head",
        "gh pr diff 13 | git apply",
        "gh alias set c 'issue comment'",
        "gh extension install someone/gh-x",
        "cat <<'EOF' && rm PRIVATE.md\nx\nEOF",
        "cat <<'EOF' > PRIVATE.md\nx\nEOF",
    ],
)
def test_secret_and_pull_request_commands_are_blocked(guard, command):
    assert guard.check_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "gh auth status",
        "git fetch origin +pull/13/head:refs/pr/13",
        "git diff --text --no-textconv --no-ext-diff origin/main...refs/pr/13",
        "git diff --raw --no-renames origin/main...refs/pr/13",
        "git update-ref -d refs/pr/13",
        "gh pr diff 13 --name-only",
        "git pull --rebase",
        "gh config get git_protocol",
    ],
)
def test_pull_request_review_commands_are_allowed(guard, command):
    assert guard.check_command(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "git diff --text --no-textconv --no-ext-diff origin/main...refs/pr/12 | git apply",
        "git show refs/pr/12 | git apply",
        "git format-patch --stdout origin/main..refs/pr/12 | git am",
    ],
)
def test_applying_a_fetched_pull_request_is_blocked(guard, command):
    assert guard.check_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "git merge-base origin/main refs/pr/12",
        "git apply fix.patch",
        "git diff origin/main...refs/pr/12 | head -50",
    ],
)
def test_reading_a_fetched_pull_request_is_allowed(guard, command):
    assert guard.check_command(command) is None


def test_a_heredoc_inside_command_substitution_is_stripped(guard):
    command = "git commit -m \"$(cat <<'EOF'\ndocs: never run gh auth token\nEOF\n)\""
    assert "auth token" not in guard.strip_heredocs(command)
    assert guard.check_command(command) is None


def test_network_paths_are_never_opened(guard):
    assert guard.is_network_path("//host/share/x.md")
    assert guard.is_network_path(r"\\host\share\x.md")
    assert not guard.is_network_path("C:/tmp/x.md")
    assert not guard.is_network_path("docs/x.md")


def test_e_mail_scan_is_fast_on_long_runs(guard):
    import time

    start = time.perf_counter()
    assert guard.scan_text("a." * 50_000 + " %a" * 10_000, set()) == []
    assert time.perf_counter() - start < 1
