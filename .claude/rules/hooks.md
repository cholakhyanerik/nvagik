---
paths:
  - ".claude/hooks/**"
  - ".claude/settings.json"
  - "tests/test_guard*.py"
  - "tests/test_session_start.py"
---

# Claude Code hooks

- Scripts live in `.claude/hooks/` and are wired in `.claude/settings.json`.
- They run with the system Python (`py -3`), not the venv, so they use only the standard library.
- Changes take effect in a new session (or after opening `/hooks`).

## session_start.py (SessionStart)

- Reports, one line each:
  - system vs project Python, outdated dependencies, uv vs `uv_build`;
  - action pins in `.github/workflows/` behind a latest release that is at least 7 days old (no line when `gh` cannot tell);
  - private vulnerability reports waiting for triage and open Dependabot alerts;
  - the cards claimed in open issues and pull requests (claim limits: docs/DECISIONS.md);
  - git state (plain branch names only), CLAUDE.md over its size target (rule 15), the next tasks.
- The `gh` checks run in parallel with the dependency check, so the hook stays within its 60 s timeout.
- Issue and pull request text is untrusted: only numbers, `NVG-<id>`s and fixed words are reported.
- A check that fails costs only its own line ("could not check"), never the whole report.
- Tested in `tests/test_session_start.py` with `gh` faked.

## guard.py (PreToolUse: Bash, PowerShell)

- Blocks deleting, moving, copying or overwriting PRIVATE.md (globs like `*.md` too), `git clean -x`, `git stash --all`, `git add -f` and force pushes (`-f`, `+refspec`). `git rm --cached PRIVATE.md` stays allowed.
- Blocks commits, pushes and `gh` uploads whose files, history, commit or tag messages, or author or tagger e-mails contain private files, secrets, personal e-mails or PRIVATE.md values.
- Scanning:
  - files that diffs show as binary (`binary` in `.gitattributes`, UTF-16) are read whole from the object database;
  - text up to 8 MB is scanned whole; larger text, Git LFS pointers and pushed blobs or trees (tags, refspec sources) are blocked as unscannable;
  - pushes also cover merges, a detached HEAD, root commits and explicit refspec sources.
- Every `gh` call's text is scanned. Calls that publish text (comments, reviews, merges, releases, gists, settings, `gh api` writes) also scan the files they read and may not hide text: no substitution, variables, redirects, `cd`, `--attach`, or standard input other than a heredoc.
- Also blocks `gh auth token`, `git credential fill`, `gh pr checkout` and putting `refs/pr/` commits into a work tree.
- A `<<EOF` only starts a heredoc outside quotes and comments, and the rest of its line is still checked.
- Tested in `tests/test_guard.py` and `tests/test_guard_repo.py`.

## format_py.py (PostToolUse: Edit, Write)

- Formats the edited Python file with ruff (format plus import order).

## stop_check.py (Stop)

- If changes are uncommitted or unpushed, reminds you once to run `/finish-task`.

## Gotchas

- The guard reads the literal command text: a command that merely mentions deleting PRIVATE.md (even inside `echo`) is blocked. Put test payloads in files and pipe them in (`py -3 .claude/hooks/guard.py < payload.json`).
- The guard treats every argument of `sed -i` (the script too) as a path, and it splits commands at `(` and `)` even inside quotes. A script containing `/Nvagik` (the repository folder name) is then blocked as "touching the project root". Use the Edit tool for such edits.
- Strings that look like secrets in tests must be assembled at run time (`"ghp_" + "A" * 36`), otherwise the guard blocks the commit.
- Text from outside (gh output, git branch names) is split at `"\n"` only, see `.claude/rules/python.md`.
