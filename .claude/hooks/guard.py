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
            elif is_large_text_file(path):
                findings.append(too_large(word))
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
                findings += check_push(top, private, text)
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
