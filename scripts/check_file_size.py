from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 600
ALLOWLIST = ROOT / ".loc-allowlist"
CHECK_ROOTS = [ROOT / "stringdb_link", ROOT / "server.py", ROOT / "mcp_server.py"]


class AllowlistError(ValueError):
    """Raised when the LOC allowlist cannot be applied safely."""


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
            raise AllowlistError(
                f"{ALLOWLIST}:{line_number}: expected repo-relative path and LOC ceiling"
            )
        path = path.strip()
        ceiling = ceiling.strip()
        if not path:
            raise AllowlistError(f"{ALLOWLIST}:{line_number}: path must not be blank")
        if not ceiling:
            raise AllowlistError(f"{ALLOWLIST}:{line_number}: ceiling must not be blank")
        try:
            parsed_ceiling = int(ceiling)
        except ValueError as error:
            raise AllowlistError(
                f"{ALLOWLIST}:{line_number}: ceiling must be a positive integer"
            ) from error
        if parsed_ceiling <= 0:
            raise AllowlistError(
                f"{ALLOWLIST}:{line_number}: ceiling must be a positive integer"
            )
        entries[path] = parsed_ceiling
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
    try:
        allowlist = load_allowlist()
    except AllowlistError as error:
        sys.stderr.write(f"File size allowlist error: {error}\n")
        return 1

    failures: list[str] = []
    files = iter_python_files()
    checked_paths = {path.relative_to(ROOT).as_posix() for path in files}

    stale_entries = sorted(set(allowlist) - checked_paths)
    for entry in stale_entries:
        failures.append(f"{entry}: allowlist entry does not match a checked Python file")

    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        count = line_count(path)
        ceiling = allowlist.get(relative, MAX_LINES)
        if count > ceiling:
            failures.append(f"{relative}: {count} lines exceeds ceiling {ceiling}")

    if failures:
        sys.stdout.write("File size budget failed:\n")
        for failure in failures:
            sys.stdout.write(f"  - {failure}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
