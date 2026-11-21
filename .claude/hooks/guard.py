"""PreToolUse hook (Bash and PowerShell): stop dangerous commands and leaks.

Denies (CLAUDE.md, Security):
- deleting, moving, copying or overwriting PRIVATE.md (rm, mv, cp, tee, sed -i,
  Remove-Item, Set-Content, redirects, `git rm`/`git mv`, globs such as `*.md`);
- `git clean -x/-X` and `git stash --all` (touch ignored files such as PRIVATE.md
  and .venv), `git add --force`, force pushes (`-f`, `--force`, `+refspec`);
- commits, pushes and `gh` uploads that contain private files, secrets, personal
  e-mail addresses or values from PRIVATE.md - in file contents, file history,
  commit or tag messages - or whose author/tagger e-mail is not a noreply address.

Standard library only. Values from PRIVATE.md are read at run time, matched,
and never printed or written anywhere. `git rm --cached PRIVATE.md` (untracking
it) stays allowed.
"""

import codecs
import fnmatch
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_FILE_BYTES = 1_000_000
UNPUSHED = ("--branches", "--tags", "--not", "--remotes")

# `git` / `git.exe` plus any global options (-C dir, -c k=v, --no-pager, -P, --git-dir=...).
_GIT = (
    r"\bgit(?:\.exe)?[\"']?"
    r"(?:\s+(?:-[cC]\s+(?:\"[^\"]*\"|'[^']*'|\S+)|-{1,2}[A-Za-z][\w-]*(?:=\S+)?))*\s+"
)
_ARGS = r"[^\n;&|]*?"

DANGEROUS_COMMANDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(_GIT + r"clean\b" + _ARGS + r"\s-[A-Za-z]*[xX]"),
        "`git clean -x/-X` deletes ignored files such as PRIVATE.md and .venv; "
        "remove junk with `py -3 scripts/clean.py` instead",
    ),
    (
        re.compile(_GIT + r"stash\b" + _ARGS + r"\s(?:-[A-Za-z]*a[A-Za-z]*|--all)(?=\s|$)"),
        "`git stash --all` also stashes ignored files such as PRIVATE.md and .venv",
    ),
    (
        re.compile(_GIT + r"add\b" + _ARGS + r"\s(?:-[A-Za-z]*f[A-Za-z]*|--force)(?=\s|$)"),
        "`git add --force` can stage ignored private files; fix .gitignore instead",
    ),
    (
        re.compile(_GIT + r"push\b" + _ARGS + r"\s(?:-[A-Za-z]*f[A-Za-z]*|--force|\+\S+)(?=\s|$)"),
        "a force push rewrites public history; use `--force-with-lease`, and only to "
        "remove leaked data",
    ),
    (
        re.compile(r">\s*[\"']?[^\s\"']*PRIVATE\.md", re.IGNORECASE),
        "redirecting output into PRIVATE.md would overwrite it",
    ),
)
PRIVATE_REASON = (
    "PRIVATE.md holds the owner's business and bank details; it must not be deleted, "
    "moved, copied or overwritten (`git rm --cached PRIVATE.md` is allowed)"
)
DESTRUCTIVE_VERBS = frozenset(
    {
        "rm", "del", "erase", "rd", "rmdir", "mv", "move", "ren", "rename", "cp", "copy",
        "tee", "truncate", "shred", "remove-item", "ri", "move-item", "mi", "rename-item",
        "rni", "copy-item", "cpi", "clear-content", "clc", "set-content", "add-content",
        "ac", "out-file", "tee-object",
    }
)  # fmt: skip
PREFIX_WORDS = frozenset({"sudo", "command", "builtin", "exec", "nohup", "time"})

HEREDOC = re.compile(
    r"<<-?\s*([\"']?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)|@([\"'])\n.*?\n\3@", re.DOTALL
)
SEGMENT_SPLIT = re.compile(r"[\n;|&(){}]+")

COMMIT = re.compile(_GIT + r"commit\b")
PUSH = re.compile(
    _GIT + r"push\b"
    r"|\bgh(?:\.exe)?\s+(?:repo\s+create\b[^\n]*--push|pr\s+create\b"
    r"|release\s+(?:create|upload)\b|gist\s+create\b)"
)
GH_UPLOAD = re.compile(
    r"\bgh(?:\.exe)?\s+(?:release\s+(?:create|upload)|gist\s+create)\b([^\n;&|]*)"
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "a GitHub token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})"),
    ),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("an API key (sk-...)", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{32,}")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    (
        "a hard-coded secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"
        ),
    ),
    (
        "a personal e-mail address",
        re.compile(
            r"(?i)\b[A-Za-z0-9._%+-]+@(?:gmail|googlemail|yahoo|outlook|hotmail|live|icloud|"
            r"mail|yandex|proton(?:mail)?)\.[a-z]{2,}\b"
        ),
    ),
)


# --- Dangerous commands -------------------------------------------------------------


def strip_heredocs(command: str) -> str:
    """Drop heredoc / here-string bodies (commit messages etc.) so their text isn't run."""
    return HEREDOC.sub("\n", command)


def _segments(command: str) -> Iterator[list[str]]:
    for part in SEGMENT_SPLIT.split(command):
        text = part.replace("\\", "/")  # Windows paths; also keeps shlex from eating them
        try:
            words = shlex.split(text)
        except ValueError:
            words = text.split()
        if words:
            yield words


def _touches_private(arg: str) -> bool:
    """True if a path argument (maybe a glob) can hit PRIVATE.md or the project root."""
    path = arg.strip("'\"").rstrip("/")
    directory, _, name = path.rpartition("/")
    root_name = ROOT.name.lower()
    if name in {".", ".."} or name.lower() == root_name:
        return True
    at_root = directory in {"", "."} or directory.lower().endswith("/" + root_name)
    return at_root and fnmatch.fnmatchcase("private.md", name.lower())


def _destructive_args(words: list[str]) -> list[str]:
    """Arguments of a command that deletes, moves, copies or overwrites files."""
    i = 0
    while i < len(words) and (words[i] in PREFIX_WORDS or re.fullmatch(r"\w+=.*", words[i])):
        i += 1
    if i >= len(words):
        return []
    verb = words[i].rsplit("/", 1)[-1].lower().removesuffix(".exe")
    args = words[i + 1 :]
    if verb == "git":
        j = 0
        while j < len(args) and args[j].startswith("-"):
            j += 2 if args[j] in {"-C", "-c"} else 1
        sub, rest = (args[j], args[j + 1 :]) if j < len(args) else ("", [])
        if sub == "mv" or (sub == "rm" and "--cached" not in rest):
            return rest
        return []
    if verb == "sed":
        return args if any(a.startswith(("-i", "--in-place")) for a in args) else []
    return args if verb in DESTRUCTIVE_VERBS else []


def check_command(command: str) -> str | None:
    """Return the reason a command is dangerous, or None."""
    text = strip_heredocs(command)
    for pattern, reason in DANGEROUS_COMMANDS:
        if pattern.search(text):
            return reason
    for words in _segments(text):
        if any(_touches_private(a) for a in _destructive_args(words) if not a.startswith("-")):
            return PRIVATE_REASON
    return None


# --- Leak scanning ------------------------------------------------------------------


def is_forbidden_path(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name == "private.md" or name.startswith(("id_rsa", "id_ed25519", "id_ecdsa")):
        return True
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    return name.endswith((".pdf", ".pem", ".key", ".pfx", ".p12"))


def private_values(root: Path = ROOT) -> set[str]:
    """Identifiers from the git-ignored PRIVATE.md (account, tax and registration numbers, SWIFT)."""
    try:
        text = (root / "PRIVATE.md").read_text(encoding="utf-8")
    except OSError:
        return set()
    values = set(re.findall(r"\b\d{8,}\b", text))
    values |= set(re.findall(r"\b\d{3}\.\d{7}\b", text))
    values |= {
        code
        for code in re.findall(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", text)
        if any(char.isdigit() for char in code)
    }
    return values


def scan_text(text: str, private: set[str]) -> list[str]:
    """Return labels of everything sensitive found in text (never the values themselves)."""
    found = [label for label, pattern in SECRET_PATTERNS if pattern.search(text)]
    if private:
        alternatives = "|".join(map(re.escape, sorted(private, key=len, reverse=True)))
        if re.search(rf"\b(?:{alternatives})\b", text):
            found.append("a value from PRIVATE.md")
    return found


def added_lines_by_file(diff: str) -> dict[str, list[str]]:
    """Map file -> added lines for a unified diff (`git diff` / `git log -p`)."""
    files: dict[str, list[str]] = {}
    current: str | None = None
    in_header = False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            in_header, current = True, None
        elif in_header:
            if line.startswith("+++ "):
                path = line[4:].strip()
                if len(path) > 1 and path[0] == path[-1] == '"':
                    path = path[1:-1]
                current = None if path == "/dev/null" else path.removeprefix("b/")
            elif line.startswith("@@"):
                in_header = False
        elif line.startswith("+") and current is not None:
            files.setdefault(current, []).append(line[1:])
    return files


def git(cwd: Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else None


def lines_of(text: str | None) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def names_of(text: str | None) -> list[str]:
    """Split `-z` output (NUL-separated file names)."""
    return [name.strip() for name in (text or "").split("\0") if name.strip()]


def read_small_text(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16", errors="replace")  # e.g. PowerShell 5.1 `>` output
    return None if b"\0" in data else data.decode("utf-8", errors="replace")


def scan_files(per_file: dict[str, list[str]], private: set[str]) -> list[str]:
    return [
        f"{label} in {name}"
        for name, chunks in sorted(per_file.items())
        for label in scan_text("\n".join(chunks), private)
    ]


def check_commit(top: Path, command: str, private: set[str]) -> list[str]:
    findings = []
    email = (git(top, "config", "user.email") or "").strip()
    if "noreply" not in email.lower():
        findings.append(
            "git user.email is not a GitHub noreply address (set it with "
            "`git config --global user.email <id>+<login>@users.noreply.github.com`)"
        )
    # The command carries the message (-m, heredoc) and options like --author / -c user.email.
    findings += [
        f"{label} in the commit command or message" for label in scan_text(command, private)
    ]
    # Over-approximate what will be committed: staged, unstaged and untracked files of the
    # whole repository, so `git add -A && git commit` in one command is covered too.
    names = set(names_of(git(top, "diff", "--cached", "--name-only", "-z", "--diff-filter=d")))
    names |= set(names_of(git(top, "diff", "--name-only", "-z", "--diff-filter=d")))
    names |= set(names_of(git(top, "ls-files", "-z", "--others", "--exclude-standard")))
    findings += [f"private file {name}" for name in sorted(names) if is_forbidden_path(name)]
    diff = "\n".join(
        git(top, "diff", *staged, "-U0", "--no-color", "--no-ext-diff") or ""
        for staged in (("--cached",), ())
    )
    per_file = added_lines_by_file(diff)
    # Untracked files, and files git treats as binary (e.g. UTF-16), are read whole.
    for name in sorted(names - per_file.keys()):
        if (content := read_small_text(top / name)) is not None:
            per_file[name] = [content]
    return findings + scan_files(per_file, private)


def check_push(top: Path, private: set[str]) -> list[str]:
    """Scan every commit and tag that is not on a remote yet (not just the final tree)."""
    findings = []
    emails = set(lines_of(git(top, "log", "--format=%ae%n%ce", *UNPUSHED)))
    tagger = lines_of(git(top, "for-each-ref", "refs/tags", "--format=%(taggeremail)"))
    emails |= {email.strip("<>") for email in tagger}
    if bad := sorted(email for email in emails if email and "noreply" not in email.lower()):
        findings.append(f"{len(bad)} author/committer/tagger e-mail(s) that are not noreply")
    messages = (git(top, "log", "--format=%B", *UNPUSHED) or "") + "\n"
    messages += git(top, "for-each-ref", "refs/tags", "--format=%(contents)") or ""
    findings += [f"{label} in a commit or tag message" for label in scan_text(messages, private)]
    names = set(names_of(git(top, "log", "--name-only", "-z", "--format=", *UNPUSHED)))
    findings += [f"private file {name}" for name in sorted(names) if is_forbidden_path(name)]
    patches = git(top, "log", "-p", "-U0", "--no-color", "--no-ext-diff", "--format=", *UNPUSHED)
    return findings + scan_files(added_lines_by_file(patches or ""), private)


def check_uploads(top: Path, args: str, private: set[str]) -> list[str]:
    """Files passed to `gh release create/upload` or `gh gist create`."""
    findings = []
    for words in _segments(args):
        for word in words:
            path = Path(word) if Path(word).is_absolute() else top / word
            if word.startswith("-") or not path.is_file():
                continue
            if is_forbidden_path(word):
                findings.append(f"private file {word}")
            elif (content := read_small_text(path)) is not None:
                findings += [f"{label} in {word}" for label in scan_text(content, private)]
    return findings


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Blocked by .claude/hooks/guard.py: {reason}",
                }
            }
        )
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    command = (data.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not command:
        return
    reason = check_command(command)
    text = strip_heredocs(command)
    is_commit, is_push = bool(COMMIT.search(text)), bool(PUSH.search(text))
    upload = GH_UPLOAD.search(text)
    if reason is None and (is_commit or is_push or upload):
        try:
            cwd = Path(data.get("cwd") or ROOT)
            top = Path((git(cwd, "rev-parse", "--show-toplevel") or "").strip() or cwd)
            private = private_values(top) | private_values()
            findings = check_commit(top, command, private) if is_commit else []
            if is_push:
                findings += check_push(top, private)
            if upload:
                findings += check_uploads(top, upload.group(1), private)
        except Exception as exc:  # fail closed: never let a broken guard wave a leak through
            reason = f"the guard itself failed ({exc!r}); fix it before committing or pushing"
        else:
            if findings:
                reason = (
                    "possible leak: "
                    + "; ".join(dict.fromkeys(findings))
                    + ". Remove it, or fix a false positive in the hook, then retry."
                )
    if reason:
        deny(reason)


if __name__ == "__main__":
    main()
