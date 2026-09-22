"""Truthful Loom view of consequence-evoked physical articulation.

This boundary projects only an authenticated consequence-evoked response and,
when execution occurred, its transient committed physical act.  Raw pressure
bytes never cross the boundary.  The view reports physical receipt identities,
the selected retained program identity, and whether a transient act was
observed.  It retains no PCM and grants no word, label, transcript, meaning,
speech-understanding, cognition, or legacy-route authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Mapping

from dsf_ai_service.substrate.consequence_evoked_articulatory_response import (
    CommittedConsequenceEvokedArticulatoryAct,
    ConsequenceEvokedArticulatoryResponse,
    verify_consequence_evoked_articulatory_response,
)


CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA = (
    "guala.truthful_loom."
    "consequence_evoked_articulatory_observation.v1"
)
CONSEQUENCE_ARTICULATORY_LOOM_DOMAIN = (
    b"guala-truthful-loom-consequence-articulatory-observation-v1\0"
)
_HEX = frozenset("0123456789abcdef")
_RESPONSE_STATES = frozenset({
    "executed",
    "unresolved",
    "ambiguous",
    "unbound",
})
_AUTHORITIES = {
    "cognition": False,
    "decision": False,
    "label": False,
    "legacy_route": False,
    "meaning": False,
    "speech_understanding": False,
    "transcript": False,
    "word": False,
}
_RECEIPT_FIELDS = (
    "binding_receipt_sha256",
    "cue_settlement_receipt_sha256",
    "emission_receipt_sha256",
    "evocation_receipt_sha256",
    "prepared_self_acoustic_commitment_receipt_sha256",
    "self_acoustic_receipt_sha256",
    "source_response_authority_receipt_sha256",
    "synthesis_receipt_sha256",
    "world_after_receipt_sha256",
    "world_before_receipt_sha256",
)
_PHYSICAL_RECEIPT_FIELDS = (
    "binding_receipt_sha256",
    "emission_receipt_sha256",
    "prepared_self_acoustic_commitment_receipt_sha256",
    "self_acoustic_receipt_sha256",
    "synthesis_receipt_sha256",
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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError(
            "consequence articulatory Loom key must be bytes or text"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "consequence articulatory Loom key boundary changed"
        )
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _source(
    occurrence: (
        ConsequenceEvokedArticulatoryResponse
        | CommittedConsequenceEvokedArticulatoryAct
        | None
    ),
    *,
    source_authority_key: bytes | str,
) -> tuple[
    ConsequenceEvokedArticulatoryResponse | None,
    CommittedConsequenceEvokedArticulatoryAct | None,
]:
    _key(source_authority_key)
    if occurrence is None:
        return None, None
    if isinstance(
        occurrence,
        CommittedConsequenceEvokedArticulatoryAct,
    ):
        response = occurrence.response
        verify_consequence_evoked_articulatory_response(
            response,
            authority_key=source_authority_key,
        )
        if (
            response.state != "executed"
            or not isinstance(occurrence.pcm_s16le, bytes)
            or not occurrence.pcm_s16le
            or hashlib.sha256(occurrence.pcm_s16le).hexdigest()
            != response.synthesis_pcm_sha256
        ):
            raise ValueError(
                "consequence articulatory Loom act changed pressure custody"
            )
        return response, occurrence
    if isinstance(
        occurrence,
        ConsequenceEvokedArticulatoryResponse,
    ):
        verify_consequence_evoked_articulatory_response(
            occurrence,
            authority_key=source_authority_key,
        )
        if occurrence.state == "executed":
            raise ValueError(
                "executed Loom projection requires its transient committed act"
            )
        return occurrence, None
    raise TypeError(
        "consequence articulatory Loom occurrence is not typed"
    )


def _payload(
    occurrence: (
        ConsequenceEvokedArticulatoryResponse
        | CommittedConsequenceEvokedArticulatoryAct
        | None
    ),
    *,
    source_authority_key: bytes | str,
) -> dict[str, object]:
    response, act = _source(
        occurrence,
        source_authority_key=source_authority_key,
    )
    if response is None:
        return {
            "authorities": dict(_AUTHORITIES),
            "emission_observed": False,
            "fresh_articulatory_synthesis_observed": False,
            "program_id": None,
            "receipts": {
                name: None for name in _RECEIPT_FIELDS
            },
            "response_state": None,
            "retained_pcm_bytes": 0,
            "schema": CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA,
            "status": "not_observed",
            "thing_ids": [],
            "transient_act": {
                "committed": False,
                "pcm_byte_count": 0,
                "pcm_sha256": None,
            },
        }
    executed = act is not None
    return {
        "authorities": dict(_AUTHORITIES),
        "emission_observed": executed,
        "fresh_articulatory_synthesis_observed": executed,
        "program_id": response.program_id,
        "receipts": {
            "binding_receipt_sha256": (
                response.binding_receipt_sha256
            ),
            "cue_settlement_receipt_sha256": (
                response.cue_settlement_receipt_sha256
            ),
            "emission_receipt_sha256": (
                response.emission_receipt_sha256
            ),
            "evocation_receipt_sha256": (
                response.evocation_receipt_sha256
            ),
            "prepared_self_acoustic_commitment_receipt_sha256": (
                response
                .prepared_self_acoustic_commitment_receipt_sha256
            ),
            "self_acoustic_receipt_sha256": (
                response.self_acoustic_receipt_sha256
            ),
            "source_response_authority_receipt_sha256": (
                response.authority_receipt_sha256
            ),
            "synthesis_receipt_sha256": (
                response.synthesis_receipt_sha256
            ),
            "world_after_receipt_sha256": (
                response.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                response.world_before_receipt_sha256
            ),
        },
        "response_state": response.state,
        "retained_pcm_bytes": 0,
        "schema": CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA,
        "status": "observed",
        "thing_ids": list(response.thing_ids),
        "transient_act": {
            "committed": executed,
            "pcm_byte_count": (
                0 if act is None else len(act.pcm_s16le)
            ),
            "pcm_sha256": (
                None
                if act is None
                else response.synthesis_pcm_sha256
            ),
        },
    }


def project_consequence_evoked_articulatory_loom_observation(
    *,
    authority_key: bytes | str,
    source_authority_key: bytes | str,
    occurrence: (
        ConsequenceEvokedArticulatoryResponse
        | CommittedConsequenceEvokedArticulatoryAct
        | None
    ),
) -> dict[str, object]:
    """Project one verified occurrence without retaining its pressure."""

    payload = _payload(
        occurrence,
        source_authority_key=source_authority_key,
    )
    signature = hmac.new(
        _key(authority_key),
        CONSEQUENCE_ARTICULATORY_LOOM_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    return {
        **payload,
        "authority_hmac_sha256": signature,
        "authority_receipt_sha256": _digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        }),
    }


def verify_consequence_evoked_articulatory_loom_observation(
    value: Mapping[str, object],
    *,
    authority_key: bytes | str,
) -> None:
    """Verify one bounded projection without source runtime objects."""

    if not isinstance(value, Mapping):
        raise TypeError(
            "consequence articulatory Loom projection must be a mapping"
        )
    expected = {
        "authorities",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "emission_observed",
        "fresh_articulatory_synthesis_observed",
        "program_id",
        "receipts",
        "response_state",
        "retained_pcm_bytes",
        "schema",
        "status",
        "thing_ids",
        "transient_act",
    }
    receipts = value.get("receipts")
    transient = value.get("transient_act")
    if (
        set(value) != expected
        or value.get("schema") != CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA
        or value.get("authorities") != _AUTHORITIES
        or value.get("status") not in {"observed", "not_observed"}
        or value.get("retained_pcm_bytes") != 0
        or not isinstance(value.get("thing_ids"), list)
        or not isinstance(receipts, Mapping)
        or set(receipts) != set(_RECEIPT_FIELDS)
        or not isinstance(transient, Mapping)
        or set(transient)
        != {"committed", "pcm_byte_count", "pcm_sha256"}
        or not isinstance(transient.get("committed"), bool)
        or isinstance(transient.get("pcm_byte_count"), bool)
        or not isinstance(transient.get("pcm_byte_count"), int)
        or transient["pcm_byte_count"] < 0
    ):
        raise ValueError(
            "consequence articulatory Loom projection contract changed"
        )
    observed = value["status"] == "observed"
    executed = value.get("response_state") == "executed"
    committed = transient["committed"]
    occurrence_receipts = (
        "cue_settlement_receipt_sha256",
        "evocation_receipt_sha256",
        "source_response_authority_receipt_sha256",
        "world_after_receipt_sha256",
        "world_before_receipt_sha256",
    )
    if (
        value.get("emission_observed") is not committed
        or value.get("fresh_articulatory_synthesis_observed")
        is not committed
        or (
            not observed
            and (
                value.get("response_state") is not None
                or value.get("program_id") is not None
                or value.get("thing_ids")
                or any(item is not None for item in receipts.values())
                or committed
                or transient["pcm_byte_count"] != 0
                or transient["pcm_sha256"] is not None
            )
        )
        or (
            observed
            and value.get("response_state") not in _RESPONSE_STATES
        )
        or (
            observed
            and any(
                receipts[name] is None
                for name in occurrence_receipts
            )
        )
        or (
            executed
            and (
                not committed
                or value.get("program_id") is None
                or len(value["thing_ids"]) != 1
                or any(
                    receipts[name] is None
                    for name in _PHYSICAL_RECEIPT_FIELDS
                )
                or transient["pcm_byte_count"] <= 0
                or transient["pcm_sha256"] is None
                or receipts["world_before_receipt_sha256"]
                == receipts["world_after_receipt_sha256"]
            )
        )
        or (
            observed
            and not executed
            and (
                committed
                or value.get("program_id") is not None
                or any(
                    receipts[name] is not None
                    for name in _PHYSICAL_RECEIPT_FIELDS
                )
                or transient["pcm_byte_count"] != 0
                or transient["pcm_sha256"] is not None
                or receipts["world_before_receipt_sha256"]
                != receipts["world_after_receipt_sha256"]
            )
        )
    ):
        raise ValueError(
            "consequence articulatory Loom physical claim changed"
        )
    for thing_id in value["thing_ids"]:
        _sha256(
            thing_id,
            "consequence articulatory Loom THING",
        )
    if value.get("program_id") is not None:
        _sha256(
            value["program_id"],
            "consequence articulatory Loom program",
        )
    for name, receipt in receipts.items():
        if receipt is not None:
            _sha256(
                receipt,
                f"consequence articulatory Loom {name}",
            )
    if transient["pcm_sha256"] is not None:
        _sha256(
            transient["pcm_sha256"],
            "consequence articulatory Loom pressure",
        )
    _sha256(
        value.get("authority_hmac_sha256"),
        "consequence articulatory Loom HMAC",
    )
    _sha256(
        value.get("authority_receipt_sha256"),
        "consequence articulatory Loom authority",
    )
    payload = {
        key: value[key]
        for key in expected
        if key not in {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
        }
    }
    signature = hmac.new(
        _key(authority_key),
        CONSEQUENCE_ARTICULATORY_LOOM_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    if (
        not hmac.compare_digest(
            signature,
            value["authority_hmac_sha256"],
        )
        or value["authority_receipt_sha256"] != _digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        })
    ):
        raise ValueError(
            "consequence articulatory Loom projection authority changed"
        )


__all__ = (
    "CONSEQUENCE_ARTICULATORY_LOOM_DOMAIN",
    "CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA",
    "project_consequence_evoked_articulatory_loom_observation",
    "verify_consequence_evoked_articulatory_loom_observation",
)
