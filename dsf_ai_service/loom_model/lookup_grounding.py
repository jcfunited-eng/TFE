"""Explicit boundary for external-model language grounding.

Language meaning is admitted through completed Fact-Strand experience windows.
An external model cannot supply or substitute that experience.  This module is
kept only as a loud compatibility boundary for callers from older releases.
It performs no network access and reads no credentials.
"""

from __future__ import annotations


UNAVAILABLE_REASON = (
    "external-model lookup is not a Fact-Strand experience source; "
    "grounding requires an observed or emulated completed experience window"
)


class GroundingLookupUnavailable(RuntimeError):
    """Raised when retired external-model grounding is requested."""


def status() -> dict[str, object]:
    """Return the permanent, explicit availability boundary."""
    return {
        "available": False,
        "state": "unavailable",
        "reason": UNAVAILABLE_REASON,
        "authority": "language_fact_strand",
    }


def describe(term: object, timeout: object = None) -> str:
    """Reject retired lookup use instead of returning a silent fallback."""
    del term, timeout
    raise GroundingLookupUnavailable(UNAVAILABLE_REASON)
