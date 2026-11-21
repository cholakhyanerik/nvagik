"""Remove build, test and temporary junk from the working tree.

Run after every finished task (CLAUDE.md, Definition of done):

    py -3 scripts/clean.py

Never touches .git, .venv, PRIVATE.md or anything tracked by git.
"""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv"}
JUNK_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".hypothesis", "htmlcov"}
ROOT_JUNK_DIRS = ("build", "dist")
JUNK_SUFFIXES = (".pyc", ".pyo", ".tmp", ".bak", ".orig", ".rej")
JUNK_FILES = {".coverage"}
PROTECTED = {"PRIVATE.md"}


def tracked_files() -> set[Path]:
    """Files tracked by git. Exits instead of guessing: an empty set would delete tracked files."""
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=False)
    names = [name for name in proc.stdout.decode("utf-8", "replace").split("\0") if name]
    if proc.returncode != 0 or not names:
        error = proc.stderr.decode("utf-8", "replace").strip() or "no tracked files"
        raise SystemExit(f"clean.py: cannot list tracked files ({error}); nothing was removed.")
    return {(ROOT / name).resolve() for name in names}


def main() -> None:
    tracked = tracked_files()
    tracked_dirs = {parent for file in tracked for parent in file.parents}
    removed: list[Path] = []

    def remove_dir(path: Path) -> None:
        if path.resolve() not in tracked_dirs:
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path)

    for name in ROOT_JUNK_DIRS:
        if (path := ROOT / name).is_dir():
            remove_dir(path)
    for path in ROOT.glob("*.egg-info"):
        remove_dir(path)

    for dirpath, dirnames, filenames in os.walk(ROOT):
        current = Path(dirpath)
        for dirname in list(dirnames):
            if dirname in SKIP_DIRS:
                dirnames.remove(dirname)
            elif dirname in JUNK_DIRS:
                dirnames.remove(dirname)
                remove_dir(current / dirname)
        for filename in filenames:
            path = current / filename
            if filename in PROTECTED or path.resolve() in tracked:
                continue
            if filename in JUNK_FILES or filename.endswith(JUNK_SUFFIXES):
                path.unlink(missing_ok=True)
                removed.append(path)

    if removed:
        print(f"Removed {len(removed)} item(s):")
        for path in removed:
            print(f"  {path.relative_to(ROOT)}")
    else:
        print("Nothing to clean.")


if __name__ == "__main__":
    main()
