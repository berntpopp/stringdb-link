"""Upstream fetch times of the current tool call (Response-Envelope Standard v1.2).

The envelope reports ``_meta.retrieved_at`` as the oldest upstream fetch behind a
result. The service cache stores the fetch time with each entry and notes it on
every call, hit or miss; the MCP tool wrapper opens the log and the envelope
builder reads it.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import UTC, datetime

# A shared list, not a value: the in-process route call may run in a task that
# copies the context but still appends to the same list.
_FETCHES: ContextVar[list[datetime] | None] = ContextVar("stringdb_fetches", default=None)


def begin_fetch_log() -> None:
    """Start a fresh fetch log for the current tool call."""
    _FETCHES.set([])


def note_fetch(at: datetime) -> None:
    """Record an upstream fetch (the original time for a cached one)."""
    log = _FETCHES.get()
    if log is not None:
        log.append(at)


def retrieved_at() -> str:
    """Oldest fetch of the current call as RFC 3339 UTC; now when nothing was fetched."""
    oldest = min(_FETCHES.get() or [], default=datetime.now(UTC))
    return oldest.strftime("%Y-%m-%dT%H:%M:%SZ")
