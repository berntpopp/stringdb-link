"""CI must run the test suite on the interpreter the container actually ships.

``docker/Dockerfile`` ships ``python:3.14-slim``, but the CI test job ran only on
Python 3.12. ``container-ci``/``conformance`` exercise the *image* on 3.14; the
unit and API suites never did, so a 3.14-only stdlib or typing regression could
ship uncaught.

Both ends of the matrix are required. 3.12 is the declared ``requires-python``
floor -- drop it and the floor is a false claim. 3.14 is what reaches
production. And ``UV_PYTHON`` is load-bearing: ``uv`` resolves its interpreter
from ``.python-version`` *before* it consults ``PATH``, so ``setup-python``
alone would leave both matrix legs on 3.12 -- green, and meaningless.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]  # tests/unit/ -> repo root
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
DOCKERFILE = ROOT / "docker" / "Dockerfile"


def _quality_job() -> dict[str, Any]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return dict(workflow["jobs"]["quality"])


def _matrix_versions() -> list[str]:
    return [str(v) for v in _quality_job()["strategy"]["matrix"]["python-version"]]


def _requires_python_floor() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["project"]["requires-python"]).removeprefix(">=")


def _dockerfile_python_version() -> str:
    match = re.search(
        r"^FROM python:(\d+\.\d+)-slim", DOCKERFILE.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert match is not None, "docker/Dockerfile must pin a python:<major>.<minor>-slim base"
    return match.group(1)


def test_ci_tests_the_requires_python_floor() -> None:
    assert _requires_python_floor() in _matrix_versions(), (
        "the declared requires-python floor must stay under test, or it is a false claim"
    )


def test_ci_tests_the_interpreter_the_container_ships() -> None:
    assert _dockerfile_python_version() in _matrix_versions(), (
        "docker/Dockerfile ships a CPython the test matrix never runs"
    )


def test_matrix_forces_uv_to_the_matrix_interpreter() -> None:
    assert (ROOT / ".python-version").exists()
    assert _quality_job()["env"]["UV_PYTHON"] == "${{ matrix.python-version }}", (
        "uv reads .python-version before PATH, so without UV_PYTHON both matrix "
        "legs build a 3.12 environment and the matrix silently tests the floor twice"
    )


def test_coverage_gate_runs_once_not_per_matrix_leg() -> None:
    steps = _quality_job()["steps"]
    coverage = [step for step in steps if step.get("run") == "make test-cov"]

    assert len(coverage) == 1
    assert "matrix.python-version == '3.14'" in coverage[0]["if"], (
        "the coverage gate must run on one interpreter, not once per matrix leg"
    )
