from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 600
ALLOWLIST = ROOT / ".loc-allowlist"
CHECK_ROOTS = [ROOT / "stringdb_link", ROOT / "server.py", ROOT / "mcp_server.py"]


def load_allowlist() -> dict[str, int]:
    entries: dict[str, int] = {}
    if not ALLOWLIST.exists():
        return entries

    for line_number, raw_line in enumerate(ALLOWLIST.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        path, separator, ceiling = line.partition(":")
        if not separator:
            raise ValueError(
                f"{ALLOWLIST}:{line_number}: expected repo-relative path and LOC ceiling"
            )
        entries[path] = int(ceiling)
    return entries


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in CHECK_ROOTS:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(path for path in root.rglob("*.py") if "tests" not in path.parts)
    return sorted(files)


def line_count(path: Path) -> int:
    return len(path.read_text().splitlines())


def main() -> int:
    allowlist = load_allowlist()
    failures: list[str] = []

    for path in iter_python_files():
        relative = path.relative_to(ROOT).as_posix()
        count = line_count(path)
        ceiling = allowlist.get(relative, MAX_LINES)
        if count > ceiling:
            failures.append(f"{relative}: {count} lines exceeds ceiling {ceiling}")

    if failures:
        print("File size budget failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
