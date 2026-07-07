"""Security guard: no caller identifiers/URLs leak into emitted log values.

STRING identifiers are caller-supplied gene/protein lists that may be
patient-derived (GDPR Art. 9). The fleet ``security-review`` contract forbids
logging them, the generated STRING URLs (which embed the identifiers in their
query string), raw exception strings, or tracebacks -- any of which can carry
the same free-text. Two central mechanisms close this class at the sink:

* ``redact_sensitive_processor`` (structlog) digests denylisted event-dict keys
  and drops structlog-rendered exception frames; and
* ``RedactingFilter`` (stdlib) nulls ``exc_info``/``stack_info`` on every
  record, because ``Logger.exception()`` re-attaches the traceback *after* the
  structlog processors run.

Research use only; not clinical decision support."""

from __future__ import annotations

import io
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from stringdb_link import logging_config
from stringdb_link.exceptions import StringDBServiceError
from stringdb_link.logging_config import RedactingFilter, redact_sensitive_processor
from stringdb_link.models.requests import LinkRequest
from stringdb_link.services.stringdb_service import StringDBService

# Distinctive token; its sha256 digest cannot contain this substring.
SENTINEL = "SENTINEL-PII-7f3a9-DO-NOT-LEAK"


def test_processor_redacts_sensitive_keys_and_strips_exc_info() -> None:
    """Denylisted keys are digested; exc_info/exception are dropped."""
    event = {
        "event": "Error getting network link",  # static message: preserved
        "error_type": "RuntimeError",  # triage field: preserved
        "identifiers": [SENTINEL],
        "url": f"https://string-db.org/api/json/network?identifiers={SENTINEL}",
        "error": f"upstream failed for {SENTINEL}",
        "error_message": f"upstream failed for {SENTINEL}",
        "detail": f"boom {SENTINEL}",
        "query": SENTINEL,
        "species": 9606,  # non-sensitive taxon id: preserved
        "exc_info": True,
        "exception": f"Traceback ... {SENTINEL}",
    }

    out = redact_sensitive_processor(None, "error", event)

    assert SENTINEL not in repr(out)
    assert "exc_info" not in out
    assert "exception" not in out
    assert out["error_type"] == "RuntimeError"
    assert out["species"] == 9606
    assert out["event"] == "Error getting network link"
    # Redacted values are non-reversible digests, not the raw text.
    assert out["identifiers"].startswith("sha256:")


def test_redacting_filter_nulls_traceback_channel() -> None:
    """The stdlib filter drops exc_info/stack_info that carry raw exception text."""
    try:
        raise RuntimeError(f"upstream failed for {SENTINEL}")
    except RuntimeError:
        record = logging.LogRecord(
            name="t",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="boom",
            args=(),
            exc_info=logging.sys.exc_info(),  # type: ignore[attr-defined]
        )
    record.stack_info = f"stack ... {SENTINEL}"

    assert RedactingFilter().filter(record) is True
    assert record.exc_info is None
    assert record.stack_info is None
    # The formatted record (what a handler would emit) is sentinel-free.
    rendered = logging.Formatter("%(message)s").format(record)
    assert SENTINEL not in rendered


def test_configure_logging_wires_redacting_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """The production logging setup attaches RedactingFilter to its handler."""
    monkeypatch.setattr(logging_config.settings, "debug", False)
    monkeypatch.setattr(logging_config.settings, "development_mode", False)
    monkeypatch.setattr(logging_config.settings, "reload", False)
    logging_config.configure_logging()
    root = logging.getLogger()
    assert any(isinstance(f, RedactingFilter) for h in root.handlers for f in h.filters), (
        "configure_logging must attach RedactingFilter to its handler(s)"
    )


async def test_failing_service_call_leaks_no_sentinel_to_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive a failing get_network_link through the real configured pipeline and
    assert the sentinel identifier is absent from every rendered log line."""
    # Force the production (non-dev) StreamHandler + JSON rendering path.
    monkeypatch.setattr(logging_config.settings, "debug", False)
    monkeypatch.setattr(logging_config.settings, "development_mode", False)
    monkeypatch.setattr(logging_config.settings, "reload", False)
    monkeypatch.setattr(logging_config.settings.logging, "format", "json")
    logging_config.configure_logging()

    # Redirect the app's real configured handler (with its RedactingFilter and
    # formatter) into a buffer so we assert on exactly what would be emitted.
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    buf = io.StringIO()
    stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
    assert stream_handlers, "expected a StreamHandler from configure_logging"
    for handler in stream_handlers:
        handler.setStream(buf)
        handler.setLevel(logging.DEBUG)

    client = MagicMock()
    client.get_link = AsyncMock(side_effect=RuntimeError(f"upstream failed for {SENTINEL}"))
    service = StringDBService(client=client)  # real structlog logger, not a mock

    request = LinkRequest(identifiers=[SENTINEL], species=9606)

    with pytest.raises(StringDBServiceError):
        await service.get_network_link(request)

    emitted = buf.getvalue()
    assert emitted, "expected the failing call to emit at least one log record"
    assert SENTINEL not in emitted
    # Prove logging still happened and stayed useful for triage.
    assert "error" in emitted.lower()
