"""Honest semantic-recognition capability boundary.

Raw sight and sound still enter their Krimelack transducers.  This module
describes the separate semantic capabilities that are *not* available until a
deterministic Language Fact-Strand reciprocity operator has been ratified and
implemented.  It deliberately contains no pretrained model adapter, label
table, vocabulary lookup, confidence threshold, or fallback classifier.
"""

from __future__ import annotations


OBJECT_NAME_RECOGNITION = "object_name_recognition"
SPOKEN_WORD_RECOGNITION = "spoken_word_recognition"

_CAPABILITIES = {
    OBJECT_NAME_RECOGNITION: {
        "raw_sensing": "sight_krimelack",
        "reason": (
            "object naming is unavailable because no deterministic visual "
            "Fact-Strand reciprocity operator is deployed"
        ),
    },
    SPOKEN_WORD_RECOGNITION: {
        "raw_sensing": "sound_krimelack",
        "reason": (
            "spoken-word recognition is unavailable because no deterministic "
            "audio-language Fact-Strand reciprocity operator is deployed"
        ),
    },
}


def recognition_unavailable(capability: str) -> dict:
    """Return the canonical public status for an unavailable capability.

    Unknown capability names are programming errors.  They must not be folded
    into a generic empty result because that would recreate the fail-silent
    behavior this boundary removes.
    """

    try:
        definition = _CAPABILITIES[capability]
    except KeyError as exc:
        raise ValueError(f"unknown recognition capability: {capability}") from exc

    return {
        "capability": capability,
        "available": False,
        "status": "unavailable",
        "reason": definition["reason"],
        "raw_sensing": {
            "available": True,
            "mechanism": definition["raw_sensing"],
            "semantic_recognition": False,
        },
    }
