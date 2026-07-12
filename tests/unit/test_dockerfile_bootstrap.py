"""F-19: the Docker builder must not bootstrap a floating pip/uv.

The builder stage previously ran ``pip install --upgrade pip uv`` — an
unpinned, network-resolved installer bootstrap that makes the image
non-reproducible and widens the supply-chain surface. Replace it with a
digest-pinned ``uv`` binary copied from the official image.
"""

from __future__ import annotations

from pathlib import Path

_DOCKERFILE = Path(__file__).resolve().parents[2] / "docker" / "Dockerfile"
_UV_PIN = (
    "ghcr.io/astral-sh/uv:0.8.7@sha256:"
    "1e26f9a868360eeb32500a35e05787ffff3402f01a8dc8168ef6aee44aef0aab"
)


def test_dockerfile_pins_uv_and_has_no_floating_pip_upgrade() -> None:
    text = _DOCKERFILE.read_text()
    assert "pip install --upgrade" not in text, "floating pip/uv upgrade must be removed"
    assert _UV_PIN in text, "uv must be copied from a digest-pinned image"
