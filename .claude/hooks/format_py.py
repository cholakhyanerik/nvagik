"""PostToolUse hook (Edit/Write): format an edited Python file with ruff.

Runs `ruff check --select I --fix` (import order) and `ruff format` on the one
file that changed. Silent; skips files outside the project, inside .venv, or
when ruff is not installed yet (`uv sync` installs it).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUFF = ROOT / ".venv" / "Scripts" / "ruff.exe"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    path = (data.get("tool_input") or {}).get("file_path")
    if not path or not RUFF.is_file():
        return
    file = Path(path).resolve()
    if (
        file.suffix not in {".py", ".pyi"}
        or not file.is_file()
        or not file.is_relative_to(ROOT)
        or file.is_relative_to(ROOT / ".venv")
    ):
        return
    for args in (("check", "--select", "I", "--fix", "--quiet"), ("format", "--quiet")):
        subprocess.run(
            [str(RUFF), *args, str(file)], cwd=ROOT, capture_output=True, timeout=20, check=False
        )


if __name__ == "__main__":
    main()
