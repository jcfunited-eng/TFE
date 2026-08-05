"""Exact validation for one authenticated auditory full-field occurrence.

This is a modality contract, not a grounding, recognition, or semantic
authority.  It preserves the complete ordered D/M/R/U/C/P/B pressure and
phase tuples, receptor topology, causal interval, and receipt identity.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("grounding causal time must be an exact Fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not an exact fraction") from exc
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonically encoded")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _validate_field_pairs(value: object, name: str) -> None:
    if (
        not isinstance(value, list)
        or len(value) != len(DSF_FIELD_ORDER)
        or tuple(
            item[0]
            for item in value
            if isinstance(item, list) and len(item) == 2
        )
        != DSF_FIELD_ORDER
    ):
        raise ValueError(f"{name} lost explicit DSF field order")
    for expected_name, item in zip(DSF_FIELD_ORDER, value, strict=True):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or item[0] != expected_name
        ):
            raise ValueError(f"{name} lost explicit DSF field order")
        _fraction(item[1], f"{name} {expected_name}")


def validate_auditory_full_field_occurrence(value: object) -> None:
    """Reject any changed physical, DSF, causal, or receipt coordinate."""

    expected = {
        "authority_receipt_sha256",
        "causal_interval_end",
        "phase_field_receipt_sha256",
        "phase_fields",
        "pressure_basin",
        "pressure_field_receipt_sha256",
        "pressure_fields",
        "receptor",
        "schema",
        "source_index",
        "source_time",
        "winding_delta",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA
        or value.get("pressure_basin") != "authoritative_upper"
    ):
        raise ValueError("grounding activation occurrence changed")
    receptor = value.get("receptor")
    if (
        not isinstance(receptor, Mapping)
        or set(receptor)
        != {"channel_id", "cochlear_index", "winding_direction"}
        or not isinstance(receptor.get("channel_id"), str)
        or isinstance(receptor.get("cochlear_index"), bool)
        or not isinstance(receptor.get("cochlear_index"), int)
        or receptor.get("winding_direction") not in (-1, 1)
    ):
        raise ValueError("grounding activation receptor changed")
    if (
        isinstance(value.get("source_index"), bool)
        or not isinstance(value.get("source_index"), int)
        or value["source_index"] < 0
        or isinstance(value.get("winding_delta"), bool)
        or not isinstance(value.get("winding_delta"), int)
        or value["winding_delta"] == 0
        or (1 if value["winding_delta"] > 0 else -1)
        != receptor["winding_direction"]
    ):
        raise ValueError("grounding activation occurrence order changed")
    source_time = _fraction(
        value.get("source_time"), "grounding occurrence source time"
    )
    causal_end = _fraction(
        value.get("causal_interval_end"),
        "grounding occurrence causal interval end",
    )
    if causal_end <= source_time:
        raise ValueError("grounding occurrence causal support changed")
    _validate_field_pairs(
        value.get("pressure_fields"),
        "grounding occurrence pressure",
    )
    _validate_field_pairs(
        value.get("phase_fields"),
        "grounding occurrence phase",
    )
    for key, name in (
        ("pressure_field_receipt_sha256", "pressure field receipt"),
        ("phase_field_receipt_sha256", "phase field receipt"),
        ("authority_receipt_sha256", "occurrence authority"),
    ):
        _sha256(value.get(key), f"grounding {name}")
    payload = {
        key: value[key]
        for key in value
        if key != "authority_receipt_sha256"
    }
    if _digest(payload) != value["authority_receipt_sha256"]:
        raise ValueError("grounding occurrence authority changed")


__all__ = ("validate_auditory_full_field_occurrence",)
