"""Coercions that normalize STRING REST payloads onto strict response models.

STRING's JSON endpoints are not internally consistent across API versions and
stable mirrors: a logical field can arrive as a JSON array on one deployment and
as a single comma-separated string on another. These before-validators normalize
the known-variant shapes so the gateway never returns a bare HTTP 500 on a
documented, valid query.

Research use only; not clinical decision support. Mirror STRING's disclaimers.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BeforeValidator


def split_comma_separated(value: Any) -> Any:
    """Normalize a STRING gene-name field to ``list[str]``.

    STRING ``/api/json/enrichment`` returns ``inputGenes`` / ``preferredNames``
    as a JSON array on the current public v12 API but as a single
    comma-separated string on other versions/mirrors. Split the string form and
    pass any non-string value (already a list) through untouched so the
    downstream ``list[str]`` validation succeeds in both cases.
    """
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


GeneNameList = Annotated[list[str], BeforeValidator(split_comma_separated)]
"""``list[str]`` that also accepts STRING's comma-separated string variant."""
