"""PreToolUse hook (Bash and PowerShell): stop dangerous commands and leaks.

Denies (CLAUDE.md, Security):
- deleting, moving, copying or overwriting PRIVATE.md (rm, mv, cp, tee, sed -i,
  Remove-Item, Set-Content, redirects, `git rm`/`git mv`, globs such as `*.md`);
- `git clean -x/-X` and `git stash --all` (touch ignored files such as PRIVATE.md
  and .venv), `git add --force`, force pushes (`-f`, `--force`, `+refspec`);
- commits, pushes and `gh` uploads that contain private files, secrets, personal
  e-mail addresses or values from PRIVATE.md - in file contents, file history,
  commit or tag messages - or whose author/tagger e-mail is not a noreply address.
  Files that diffs show only as binary (the `binary` attribute, UTF-16) are read
  whole from the object database, so .gitattributes cannot hide a leak.

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
MAX_FILE_BYTES = 1_000_000  # blobs up to this size are read together with `git cat-file --batch`
MAX_TEXT_BYTES = 8_000_000  # larger text cannot be scanned and is blocked
UNPUSHED = ("--branches", "--tags", "--not", "--remotes")
# Patches with full blob ids and without textconv, so "Binary files ... differ" entries
# (`binary` in .gitattributes, UTF-16 files) can be read from the object database.
PATCH = ("-U0", "--full-index", "--no-color", "--no-ext-diff", "--no-textconv")
INDEX_LINE = re.compile(r"index [0-9a-f]+\.\.([0-9a-f]+)")

# `git` / `git.exe` plus any global options (-C dir, -c k=v, --no-pager, -P, --git-dir=...).
_GIT = (
    r"\bgit(?:\.exe)?[\"']?"
    r"(?:\s+(?:-[cC]\s+(?:\"[^\"]*\"|'[^']*'|\S+)|-{1,2}[A-Za-z][\w-]*(?:=\S+)?))*\s+"
)
_ARGS = r"[^\n;&|]*?"
# `gh` / `gh.exe` in any case, maybe quoted or a full path, plus the global `-R owner/repo`.
_GH = r"(?i:\bgh(?:\.exe)?)[\"']?(?:\s+(?:-R|--repo)(?:\s+|=)\S+)?\s+"

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
    (
        re.compile(_GH + r"auth\s+(?:token\b|status\b[^\n;&|]*\s(?:-t|--show-token)(?=\s|$))"),
        "this prints the owner's GitHub token, which no task needs",
    ),
    (
        re.compile(_GIT + r"credential\s+fill\b"),
        "`git credential fill` prints stored credentials, which no task needs",
    ),
    (
        re.compile(_GH + r"(?i:pr\s+checkout|co)\b"),
        "checking out a pull request puts its `.claude/hooks` in the work tree, where they "
        "run on the next tool call; read the fetched diff instead (/next-task)",
    ),
    (
        re.compile(
            _GIT + r"(?:checkout|switch|worktree|merge|cherry-pick|rebase|reset|restore|pull|"
            r"read-tree|checkout-index|apply|am)(?![\w-])" + _ARGS + r"(?:refs/pr/|pull/\d)"
        ),
        "this puts a pull request's files into a work tree, where its hooks or code could "
        "run; only read `git diff` of the fetched ref (/next-task)",
    ),
    (
        re.compile(
            r"(?:"
            + _GH
            + r"(?i:pr\s+diff)\b|refs/pr/|pull/\d)[^\n]*\|\s*"
            + _GIT
            + r"(?:apply|am)\b"
        ),
        "applying a pull request's diff puts its files into the work tree; only read it",
    ),
    (
        re.compile(_GH + r"(?i:alias\s+(?:set|import)|extension\s+install)\b"),
        "gh aliases and extensions hide commands from this guard",
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

# A heredoc (bash) or here-string (PowerShell). Group 3 is the rest of the `<<EOF` line,
# which is still part of the command (`cat <<'EOF' | git commit -F -`).
HEREDOC = re.compile(
    r"<<-?\s*([\"']?)(\w+)\1([^\n]*+)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)|@([\"'])\n.*?\n\4@", re.DOTALL
)
SEGMENT_SPLIT = re.compile(r"[\n;|&(){}]+")
# Simple commands: split at `\n ; | &` outside quotes, so quoted parentheses and pipes stay
# inside their argument (`--subject 'fix(x): y'`, `--jq '.a|.b'`).
COMMAND_SPLIT = re.compile(r"""((?:'[^']*+'|"(?:[^"\\]|\\.)*+"|[^'"\n;|&])++)""")

COMMIT = re.compile(_GIT + r"commit\b")
PUSH = re.compile(
    _GIT + r"push\b"
    r"|" + _GH + r"(?i:repo\s+create\b[^\n]*--push|pr\s+(?:create|new)\b"
    r"|release\s+(?:create|new|upload)\b|gist\s+(?:create|new)\b)"
)
GH_UPLOAD = re.compile(
    _GH + r"(?i:release\s+(?:create|new|upload)|gist\s+(?:create|new))\b([^\n;&|]*)"
)
# Every gh call: its text is scanned (cheap, and only real secrets match).
GH_CALL = re.compile(r"(?i:\bgh(?:\.exe)?)[\"']?\s")
# gh calls that publish text: issues, pull requests, reviews, comments, merge messages,
# releases, gists, repository settings, workflow inputs (public logs). The agent writes them
# right after reading strangers' text, so they follow stricter rules (prompt injection -> leak).
GH_WRITE = re.compile(
    _GH + r"(?i:(?:issue|pr)\s+(?:comment|create|new|edit|review|merge|close|reopen)"
    r"|release\s+(?:create|new|edit|upload)|gist\s+(?:create|new|edit)|repo\s+(?:create|edit)"
    r"|label\s+(?:create|new|edit)|workflow\s+run)\b"
)
# `gh api` writes: another method than GET, fields or an input file.
GH_API_WRITE = re.compile(
    _GH + r"(?i:api)\b[^\n;&|]*\s(?:-X\s*(?!GET\b)\w|--method[\s=](?!GET\b)\w|-[fF]\S*|--field|"
    r"--raw-field|--input)",
    re.IGNORECASE,
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
            # No leading \b: on long runs like `a.a.a...` it made the match quadratic.
            r"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@(?:gmail|googlemail|yahoo|outlook|"
            r"hotmail|live|icloud|"
            r"mail|yandex|ya|inbox|list|bk|rambler|proton(?:mail)?)\.[a-z]{2,}\b"
        ),
    ),
    (  # the real content would go to LFS storage unscanned
        "a Git LFS pointer (LFS content cannot be scanned)",
        re.compile(r"(?m)^version https://git-lfs\.github\.com/spec/"),
    ),
)
BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32"),  # before UTF-16: its BOM starts with the UTF-16 LE one
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),  # e.g. PowerShell 5.1 `>` output
    (codecs.BOM_UTF16_BE, "utf-16"),
)
# Text without a BOM: (bytes per character, codec, position of the ASCII byte).
WIDE_TEXT = ((4, "utf-32-le", 0), (4, "utf-32-be", 3), (2, "utf-16-le", 0), (2, "utf-16-be", 1))
HEAD_BYTES = 8192


# --- Dangerous commands -------------------------------------------------------------


def _quoted_or_comment(before: str) -> bool:
    """True if the end of `before` (the start of a line) is inside quotes or a comment,
    so a `<<EOF` or `@'` there does not start a heredoc (`echo '<<EOF'`, `# <<EOF`).

    `$(` starts a new, unquoted level even inside double quotes, as in bash, so
    `git commit -m "$(cat <<'EOF' ...)"` is a real heredoc."""
    levels = [""]  # the open quote at each `$(` nesting level
    escaped = False
    for i, char in enumerate(before):
        quote = levels[-1]
        if escaped:
            escaped = False
        elif quote == "'":
            if char == "'":
                levels[-1] = ""
        elif char == "\\":
            escaped = True
        elif char == "$" and before[i + 1 : i + 2] == "(":
            levels.append("")
        elif quote == '"':
            if char == '"':
                levels[-1] = ""
        elif char in "'\"":
            levels[-1] = char
        elif char == ")" and len(levels) > 1:
            levels.pop()
        elif char == "#" and (i == 0 or before[i - 1].isspace()):
            return True
    return bool(levels[-1])


def strip_heredocs(command: str) -> str:
    """Drop heredoc / here-string bodies (commit messages etc.) so their text isn't run.

    The rest of the `<<EOF` line is a command and stays. A `<<EOF` inside quotes or a
    comment is not a heredoc, so the lines after it stay too.
    """

    def replace(match: re.Match[str]) -> str:
        line_start = command.rfind("\n", 0, match.start()) + 1
        if _quoted_or_comment(command[line_start : match.start()]):
            return match.group(0)
        return (match.group(3) or "") + "\n"

    return HEREDOC.sub(replace, command)


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
    """Identifiers from the git-ignored PRIVATE.md (account, tax and registration numbers,
    SWIFT, e-mail addresses)."""
    try:
        text = (root / "PRIVATE.md").read_text(encoding="utf-8")
    except OSError:
        return set()
    values = set(re.findall(r"\b\d{8,}\b", text))
    values |= set(re.findall(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", text))
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
    # Split on "\n" only: str.splitlines() also splits on "\r", U+2028 and the like, which
    # file contents and names may contain, and that could fake or hide a header line.
    for line in diff.split("\n"):
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


def binary_blobs(diff: str) -> dict[str, str]:
    """Blob id -> file name for files a `--full-index` diff shows only as binary."""
    blobs: dict[str, str] = {}
    blob: str | None = None
    for line in diff.split("\n"):  # see added_lines_by_file
        if line.startswith("diff --git "):
            blob = None
        elif match := INDEX_LINE.match(line):
            blob = match.group(1)
        elif line.startswith("Binary files ") and line.endswith(" differ"):
            name = line.removesuffix(" differ").rpartition(" and ")[2].strip('"')
            if blob and blob.strip("0") and name != "/dev/null":
                blobs[blob] = name.removeprefix("b/")
    return blobs


def git(cwd: Path, *args: str) -> str | None:
    proc = subprocess.run(
        # log.showRoot=false would hide the content of root commits (orphan branches).
        ["git", "-c", "core.quotePath=false", "-c", "log.showRoot=true", *args],
        cwd=cwd,
        capture_output=True,  # bytes: text mode would turn a lone "\r" into a line break
        timeout=20,
        check=False,
    )
    return proc.stdout.decode("utf-8", errors="replace") if proc.returncode == 0 else None


def lines_of(text: str | None) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def names_of(text: str | None) -> list[str]:
    """Split `-z` output (NUL-separated file names)."""
    return [name.strip() for name in (text or "").split("\0") if name.strip()]


def decode_small(data: bytes) -> str | None:
    """Text of a file's bytes (UTF-8, UTF-16 or UTF-32, with or without a BOM, a few stray
    NULs allowed), or None for real binaries."""
    for bom, codec in BOMS:
        if data.startswith(bom):
            return data.decode(codec, errors="replace")
    if b"\0" not in data:
        return data.decode("utf-8", errors="replace")
    # Text with a few stray NULs. This comes first: tiny inputs fool the lane test below.
    # Wide text with this few NULs still shows its ASCII once the NULs are dropped.
    if data.count(0) <= max(1, len(data) // 1000):
        return data.replace(b"\0", b"").decode("utf-8", errors="replace")
    head = data[:HEAD_BYTES]
    for width, codec, ascii_lane in WIDE_TEXT:
        lanes = [head[i::width] for i in range(width)]
        padding = [lane for i, lane in enumerate(lanes) if i != ascii_lane]
        # Wide text: NULs in every padding lane (all of them for English, fewer for Russian
        # or Armenian), almost none in the ASCII lane, and the result reads as text. The
        # last check keeps big-endian binary tables (fonts) out.
        if (
            all(lane.count(0) * 10 >= len(lane) for lane in padding)
            and lanes[ascii_lane].count(0) * 50 < len(lanes[ascii_lane])
            and _reads_as_text(head[: len(head) - len(head) % width].decode(codec, "replace"))
        ):
            return data.decode(codec, errors="replace")
    return None


def _reads_as_text(text: str) -> bool:
    printable = sum(ch in "\t\n\r\f" or (ch.isprintable() and ch != "�") for ch in text)
    return printable * 100 >= len(text) * 95


def read_small_text(path: Path) -> str | None:
    """Text of a work-tree file up to MAX_TEXT_BYTES, or None (binary, missing, too large)."""
    try:
        if not path.is_file() or (size := path.stat().st_size) > MAX_TEXT_BYTES:
            return None
        with path.open("rb") as file:
            if size > MAX_FILE_BYTES and decode_small(file.read(HEAD_BYTES)) is None:
                return None  # a large real binary: don't read all of it
            file.seek(0)
            return decode_small(file.read())
    except OSError:
        return None


def is_large_text_file(path: Path) -> bool:
    """A file too big to scan whose start looks like text (real media files start with NULs)."""
    try:
        if not path.is_file() or path.stat().st_size <= MAX_TEXT_BYTES:
            return False
        with path.open("rb") as file:
            return decode_small(file.read(HEAD_BYTES)) is not None
    except OSError:
        return False


def too_large(name: str) -> str:
    return (
        f"{name} is over 8 MB and looks like text, so it cannot be scanned (split it, "
        "or move it out of the repository or into .gitignore)"
    )


def git_bytes(cwd: Path, args: list[str], data: bytes) -> bytes:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, input=data, capture_output=True, timeout=20, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"`git {' '.join(args)}` failed")  # main() then fails closed
    return proc.stdout


def blob_head(top: Path, blob: str) -> bytes:
    """The first bytes of a blob, without reading all of a large one."""
    proc = subprocess.Popen(["git", "cat-file", "blob", blob], cwd=top, stdout=subprocess.PIPE)
    try:
        return proc.stdout.read(HEAD_BYTES)
    finally:
        proc.kill()
        proc.wait(timeout=5)


def blob_texts(top: Path, blobs: dict[str, str]) -> tuple[dict[str, list[str]], list[str]]:
    """Read the blobs from `binary_blobs`: file name -> text of the non-binary ones, and
    findings for the ones too large to scan that look like text."""
    if not blobs:
        return {}, []
    request = "".join(f"{blob}\n" for blob in blobs).encode("ascii")
    small, findings = [], []
    texts: dict[str, list[str]] = {}
    for line in git_bytes(top, ["cat-file", "--batch-check"], request).decode().splitlines():
        parts = line.split()  # "<id> blob <size>", or "<id> missing" for unhashed work-tree files
        if len(parts) != 3 or parts[1] != "blob":
            continue
        blob, size = parts[0], int(parts[2])
        if size <= MAX_FILE_BYTES:
            small.append(blob)  # read together below
        elif decode_small(blob_head(top, blob)) is None:
            continue  # a large real binary
        elif size <= MAX_TEXT_BYTES:
            data = git_bytes(top, ["cat-file", "blob", blob], b"")
            if (text := decode_small(data)) is not None:
                texts.setdefault(blobs[blob], []).append(text)
        else:
            findings.append(too_large(blobs[blob]))
    if not small:
        return texts, findings
    request = "".join(f"{blob}\n" for blob in small).encode("ascii")
    out = git_bytes(top, ["cat-file", "--batch"], request)
    pos = 0
    while pos < len(out):  # "<id> <type> <size>\n<content>\n" per object
        header_end = out.index(b"\n", pos)
        blob, _, size = out[pos:header_end].decode().split()
        start, end = header_end + 1, header_end + 1 + int(size)
        if (text := decode_small(out[start:end])) is not None:
            texts.setdefault(blobs[blob], []).append(text)
        pos = end + 1
    return texts, findings


def merge(per_file: dict[str, list[str]], extra: dict[str, list[str]]) -> None:
    for name, chunks in extra.items():
        per_file.setdefault(name, []).extend(chunks)


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
    diff = "\n".join(git(top, "diff", *staged, *PATCH) or "" for staged in (("--cached",), ()))
    per_file = added_lines_by_file(diff)
    # Untracked files, and files git shows as binary (`binary` attribute, UTF-16), are read
    # whole: the staged copy from the object database, the rest from the work tree.
    unread = names - per_file.keys()
    texts, large = blob_texts(top, binary_blobs(diff))
    merge(per_file, texts)
    for name in sorted(unread):
        if (content := read_small_text(top / name)) is not None:
            per_file.setdefault(name, []).append(content)
        elif is_large_text_file(top / name):
            large.append(too_large(name))
    return findings + large + scan_files(per_file, private)


def push_arguments(command: str) -> list[list[str]]:
    """The arguments after `push` of each `git push` in a command (`stash@{0}` kept whole)."""
    result = []
    for part in re.split(r"[\n;|&]+", command):
        try:
            words = shlex.split(part.replace("\\", "/"))
        except ValueError:
            words = part.split()
        for i, word in enumerate(words):
            is_git = (w.rsplit("/", 1)[-1].lower().removesuffix(".exe") == "git" for w in words[:i])
            if word == "push" and any(is_git):
                result.append(words[i + 1 :])
                break
    return result


def push_sources(top: Path, command: str) -> tuple[list[str], list[str], bool]:
    """Explicit refspec sources of the push: commits to scan as well (they may be on no
    branch), findings for blobs and trees, and whether tags are pushed."""
    commits, findings, tags = [], [], False
    for args in push_arguments(command):
        tags |= any(arg in {"--tags", "--mirror"} for arg in args)
        for spec in [arg for arg in args if not arg.startswith("-")][1:]:  # [0] is the remote
            tags |= "refs/tags/" in spec
            source = spec.removeprefix("+").split(":", 1)[0]
            if not source:
                continue  # `:dst` deletes a remote ref
            tags |= git(top, "rev-parse", "-q", "--verify", f"refs/tags/{source}") is not None
            object_id = (git(top, "rev-parse", "-q", "--verify", f"{source}^{{}}") or "").strip()
            kind = (git(top, "cat-file", "-t", object_id) or "").strip() if object_id else ""
            if kind == "commit":
                commits.append(object_id)
            elif kind in {"blob", "tree"}:
                findings.append(f"push source {source} is a {kind}, which cannot be scanned")
    return commits, findings, tags


def check_push(top: Path, private: set[str], command: str = "") -> list[str]:
    """Scan every commit and tag that is not on a remote yet (not just the final tree)."""
    commits, findings, pushes_tags = push_sources(top, command)
    # A detached HEAD (`git push origin HEAD:main`) is on no branch; an unborn one would make
    # `git log` fail, so add it only when it exists.
    head = ("HEAD",) if git(top, "rev-parse", "-q", "--verify", "HEAD") else ()
    unpushed = (*head, *commits, *UNPUSHED)
    emails = set(lines_of(git(top, "log", "--format=%ae%n%ce", *unpushed)))
    tagger = lines_of(git(top, "for-each-ref", "refs/tags", "--format=%(taggeremail)"))
    emails |= {email.strip("<>") for email in tagger}
    if bad := sorted(email for email in emails if email and "noreply" not in email.lower()):
        findings.append(f"{len(bad)} author/committer/tagger e-mail(s) that are not noreply")
    messages = (git(top, "log", "--format=%B", *unpushed) or "") + "\n"
    messages += git(top, "for-each-ref", "refs/tags", "--format=%(contents)") or ""
    findings += [f"{label} in a commit or tag message" for label in scan_text(messages, private)]
    if pushes_tags:  # `--follow-tags` only sends annotated tags of pushed commits
        tags = git(
            top,
            "for-each-ref",
            "refs/tags",
            "--format=%(refname:short) %(objecttype) %(*objecttype)",
        )
        for name, *types in (line.split() for line in lines_of(tags)):
            if kind := next((t for t in types if t in {"blob", "tree"}), None):
                findings.append(f"tag {name} points at a {kind}, which cannot be scanned")
    # Merges are diffed against their first parent, so content added in a merge is seen too.
    log = ("log", "--diff-merges=first-parent")
    names = set(names_of(git(top, *log, "--name-only", "-z", "--format=", *unpushed)))
    findings += [f"private file {name}" for name in sorted(names) if is_forbidden_path(name)]
    patches = git(top, *log, "-p", *PATCH, "--format=", *unpushed) or ""
    per_file = added_lines_by_file(patches)
    texts, large = blob_texts(top, binary_blobs(patches))  # binary-marked and UTF-16 files
    merge(per_file, texts)
    return findings + large + scan_files(per_file, private)


def is_network_path(name: str) -> bool:
    """`\\\\host\\share` or `//host/share`: touching it would open an SMB connection and send
    the Windows login (NTLM) before any prompt, so the guard never opens one."""
    return name.replace("\\", "/").startswith("//")


def check_uploads(top: Path, args: str, private: set[str]) -> list[str]:
    """Files passed to `gh release create/upload` or `gh gist create`."""
    findings = []
    for words in _segments(args):
        for word in words:
            if is_network_path(word):
                findings.append(f"network path {word} (not opened)")
                continue
            path = Path(word) if Path(word).is_absolute() else top / word
            if word.startswith("-") or not path.is_file():
                continue
            if is_forbidden_path(word):
                findings.append(f"private file {word}")
            elif (content := read_small_text(path)) is not None:
                findings += [f"{label} in {word}" for label in scan_text(content, private)]
            elif is_large_text_file(path):
                findings.append(too_large(word))
    return findings


def _gh_calls(command: str) -> Iterator[tuple[str, list[str]]]:
    """(subcommand, arguments) of every gh call, after global `-R owner/repo` flags.

    Splits only at `\\n ; | &` outside quotes (COMMAND_SPLIT)."""
    for part in COMMAND_SPLIT.findall(command):
        try:
            words = shlex.split(part.replace("\\", "/"))
        except ValueError:
            words = part.replace("\\", "/").split()
        for i, word in enumerate(words):
            if word.rsplit("/", 1)[-1].lower() not in {"gh", "gh.exe"}:
                continue
            args = words[i + 1 :]
            while len(args) >= 2 and args[0] in {"-R", "--repo"}:
                args = args[2:]
            if args and args[0].startswith("--repo="):
                args = args[1:]
            if args:
                yield args[0].lower(), args[1:]
            break


def gh_text_files(command: str) -> list[str]:
    """Files gh reads public text from: `--body-file`/`-F` (issue, pr), `--notes-file`/`-F`
    (release), `--input` and `field=@file` (api). `-` is standard input (see post_problems).
    A flag without a plain value gives "" or the raw text, which check_posts rejects."""
    names = []
    for sub, args in _gh_calls(command):
        if sub == "api":
            flags = ("--input",)
        elif sub in {"issue", "pr"}:
            flags = ("--body-file", "-F")
        elif sub == "release":
            flags = ("--notes-file", "-F")
        else:
            continue
        for i, arg in enumerate(args):
            value = None
            if arg in flags:
                value = args[i + 1] if i + 1 < len(args) else ""
            elif arg.startswith(tuple(f"{flag}=" for flag in flags)):
                value = arg.split("=", 1)[1]
            elif "-F" in flags and arg.startswith("-F") and not arg.startswith("--"):
                value = arg[2:]  # `-Fbody.md`
            elif sub == "api" and "=@" in arg and not (i and args[i - 1] in {"-f", "--raw-field"}):
                value = arg.split("=@", 1)[1]  # `-F body=@file`; raw fields never read files
            if value is not None and value not in {"-", "@-"}:
                names.append(value)
    return names


def post_problems(command: str, heredoc: bool = False) -> list[str]:
    """Ways a command that publishes text could post something the guard cannot read.

    `command` has its heredoc bodies stripped; `heredoc` says whether it had one (then
    standard input is that heredoc, whose text was scanned). These rules are a seat belt
    against leaks, not a wall: an agent that wants to leak has other ways (DECISIONS.md)."""
    text = re.sub(r"'[^']*+'", "''", command)  # single quotes are literal in bash and PowerShell
    bare = re.sub(r'"(?:[^"\\]|\\.)*+"', '""', text)  # and parentheses in double quotes too
    bare = re.sub(r"\d?>&\d|2>\s*/dev/null", "", bare)  # harmless stream redirects
    problems = []
    if re.search(r"\$\(|`|<\(|\$\{?[A-Za-z_]|%[A-Za-z_]\w*%", text):
        problems.append("command substitution or a variable (write the text into a file first)")
    if re.search(r"[()]", bare):
        problems.append("parentheses outside quotes (a subshell or PowerShell subexpression)")
    if re.search(r"[<>]|\btee\b|\b(?:out-file|set-content|add-content)\b", bare, re.IGNORECASE):
        problems.append(
            "a redirect or file write in the same command (write files in an earlier step)"
        )
    if re.search(
        r"(?:^|[\s;&|])(?:cd|pushd|popd|chdir|set-location|sl|push-location)\s", bare, re.I
    ):
        problems.append("a change of directory (text files are checked in the current one)")
    if re.search(r"(?:^|\s)--attach\b", bare):
        problems.append("`--attach` uploads files to a public URL without a scan")
    stdin = re.search(
        r"(?:^|\s)(?:-F|--body-file|--notes-file|--input)(?:\s+|=)-(?=\s|$)|=@-(?=\s|$)", bare
    )
    if stdin and not heredoc:
        problems.append("text from standard input other than a heredoc")
    return problems


def check_posts(cwd: Path, command: str, private: set[str]) -> list[str]:
    """Every gh call: its text is scanned. Calls that publish text (GH_WRITE, GH_API_WRITE)
    must also not hide it (post_problems), and the files they read are scanned."""
    findings = [f"{label} in the command" for label in scan_text(command, private)]
    text = strip_heredocs(command)
    # Quoted text is blanked for the write check: a `|` in `--jq '.a|.b'` must not end it.
    blanked = re.sub(r'"(?:[^"\\]|\\.)*+"', '""', re.sub(r"'[^']*+'", "''", text))
    if not (GH_WRITE.search(text) or GH_API_WRITE.search(blanked)):
        return findings  # a read: nothing is published
    findings += post_problems(text, heredoc=text != command)
    for name in gh_text_files(text):
        if is_network_path(name):
            findings.append(f"network path {name} (not opened)")
            continue
        path = Path(name) if Path(name).is_absolute() else cwd / name
        if not name or name[0] in "($`@":
            findings.append(f"text file {name!r} for gh is not a plain path")
        elif not path.is_file():  # it could be written later in the same command, unscanned
            findings.append(f"text file {name} for gh not found (write it in an earlier step)")
        elif is_forbidden_path(name):
            findings.append(f"private file {name}")
        elif (content := read_small_text(path)) is not None:
            findings += [f"{label} in {name}" for label in scan_text(content, private)]
        elif is_large_text_file(path):
            findings.append(too_large(name))
        else:
            findings.append(f"text file {name} for gh is not readable text")
    return findings + check_uploads(cwd, text, private)  # other files the command reads


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
    post = bool(GH_CALL.search(text))
    if reason is None and (is_commit or is_push or upload or post):
        try:
            cwd = Path(data.get("cwd") or ROOT)
            top = Path((git(cwd, "rev-parse", "--show-toplevel") or "").strip() or cwd)
            private = private_values(top) | private_values()
            findings = check_commit(top, command, private) if is_commit else []
            if is_push:
                findings += check_push(top, private, text)
            if upload:
                findings += check_uploads(top, upload.group(1), private)
            if post:
                findings += check_posts(cwd, command, private)
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
