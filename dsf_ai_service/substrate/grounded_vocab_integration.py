"""Observability helpers for unavailable semantic recognition.

Sensory ingestion must call the raw Krimelack path directly.  These helpers do
not inspect the input, create words, mutate memory, or choose labels.  They
only provide one shared, explicit status and an optional substrate event so an
unavailable semantic capability can never be mistaken for an empty detection.
"""

from __future__ import annotations

from dsf_ai_service.substrate.grounded_vocab import (
    OBJECT_NAME_RECOGNITION,
    SPOKEN_WORD_RECOGNITION,
    recognition_unavailable,
)


def object_name_recognition_unavailable(guala=None, *, source: str) -> dict:
    """Report that raw sight was accepted without object naming."""

    return _report_unavailable(guala, OBJECT_NAME_RECOGNITION, source)


def spoken_word_recognition_unavailable(guala=None, *, source: str) -> dict:
    """Report that raw sound was accepted without word transcription."""

    return _report_unavailable(guala, SPOKEN_WORD_RECOGNITION, source)


def _report_unavailable(guala, capability: str, source: str) -> dict:
    status = recognition_unavailable(capability)
    if guala is not None:
        guala._log_substrate_event(
            f"{capability}_unavailable",
            capability=capability,
            status="unavailable",
            source=source,
            raw_sensing=status["raw_sensing"]["mechanism"],
        )
    return status
