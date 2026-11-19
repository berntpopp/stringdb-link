"""``resolved_from`` echo for symbol inputs STRING mapped to a STRING id.

Router #319 / Response-Envelope Standard §2b: STRING resolves gene symbols natively,
so the network/partner tools take symbols directly. A symbol is echoed only when the
response itself proves the mapping (exactly one STRING id whose preferred name equals
the input, case-insensitively) -- no extra upstream call, and never a guess.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field


class ResolvedFrom(BaseModel):
    """One input identifier STRING converted to a canonical STRING id."""

    input: str = Field(..., description="Identifier as submitted")
    form: Literal["symbol"] = Field(..., description="Form of the submitted identifier")
    resolved_to: str = Field(..., description="STRING id the input was mapped to")


def resolve_symbols(
    inputs: Iterable[str], proteins: Iterable[tuple[str, str]]
) -> list[ResolvedFrom] | None:
    """Map each input matching one ``(string_id, preferred_name)`` pair; None if none did."""
    ids_by_name: dict[str, set[str]] = {}
    for string_id, name in proteins:
        ids_by_name.setdefault(name.casefold(), set()).add(string_id)
    resolved = [
        ResolvedFrom(input=raw, form="symbol", resolved_to=next(iter(ids)))
        for raw in inputs
        if len(ids := ids_by_name.get(raw.casefold(), set())) == 1 and raw not in ids
    ]
    return resolved or None
