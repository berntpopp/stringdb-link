"""Regression coverage for README validation in an isolated worktree."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_readme_linter_uses_origin_repository_identity() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/check_readme.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("README Standard v1: OK")
