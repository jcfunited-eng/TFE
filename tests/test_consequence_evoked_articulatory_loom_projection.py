from __future__ import annotations

import hashlib
import hmac
import inspect
import json
from dataclasses import replace

import pytest

import dsf_ai_service.substrate.consequence_evoked_articulatory_loom_projection as projection_module
from dsf_ai_service.substrate.consequence_evoked_articulatory_loom_projection import (
    CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA,
    project_consequence_evoked_articulatory_loom_observation,
    verify_consequence_evoked_articulatory_loom_observation,
)
from dsf_ai_service.substrate.consequence_evoked_articulatory_response import (
    CommittedConsequenceEvokedArticulatoryAct,
    ConsequenceEvokedArticulatoryResponse,
    verify_consequence_evoked_articulatory_response,
)


PROJECTION_KEY = b"consequence-articulatory-loom-projection-key"
RESPONSE_KEY = b"consequence-articulatory-source-response-key"
RESPONSE_DOMAIN = b"guala-consequence-evoked-articulatory-response-v1\0"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _identity(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _seal(
    *,
    state: str,
    thing_ids: tuple[str, ...],
    executed: bool,
    pcm_sha256: str | None,
) -> ConsequenceEvokedArticulatoryResponse:
    world_before = _identity(f"{state}-world-before")
    world_after = (
        _identity(f"{state}-world-after")
        if executed
        else world_before
    )
    provisional = ConsequenceEvokedArticulatoryResponse(
        state=state,
        cue_settlement_receipt_sha256=_identity(f"{state}-cue"),
        evocation_receipt_sha256=_identity(f"{state}-evocation"),
        thing_ids=thing_ids,
        binding_receipt_sha256=(
            _identity(f"{state}-binding") if executed else None
        ),
        program_id=(
            _identity(f"{state}-program") if executed else None
        ),
        synthesis_receipt_sha256=(
            _identity(f"{state}-synthesis") if executed else None
        ),
        synthesis_pcm_sha256=pcm_sha256 if executed else None,
        emission_receipt_sha256=(
            _identity(f"{state}-emission") if executed else None
        ),
        self_acoustic_receipt_sha256=(
            _identity(f"{state}-self-acoustic")
            if executed
            else None
        ),
        prepared_self_acoustic_commitment_receipt_sha256=(
            _identity(f"{state}-prepared-commitment")
            if executed
            else None
        ),
        world_before_receipt_sha256=world_before,
        world_after_receipt_sha256=world_after,
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    response_authority_key = hashlib.sha256(
        RESPONSE_DOMAIN + RESPONSE_KEY
    ).digest()
    signature = hmac.new(
        response_authority_key,
        RESPONSE_DOMAIN + _canonical(provisional.payload()),
        hashlib.sha256,
    ).hexdigest()
    result = replace(
        provisional,
        authority_hmac_sha256=signature,
        authority_receipt_sha256=hashlib.sha256(
            _canonical({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            })
        ).hexdigest(),
    )
    verify_consequence_evoked_articulatory_response(
        result,
        authority_key=RESPONSE_KEY,
    )
    return result


def test_not_observed_projection_is_exactly_silent_and_media_free() -> None:
    value = project_consequence_evoked_articulatory_loom_observation(
        authority_key=PROJECTION_KEY,
        source_authority_key=RESPONSE_KEY,
        occurrence=None,
    )

    verify_consequence_evoked_articulatory_loom_observation(
        value,
        authority_key=PROJECTION_KEY,
    )
    assert value["schema"] == CONSEQUENCE_ARTICULATORY_LOOM_SCHEMA
    assert value["status"] == "not_observed"
    assert value["response_state"] is None
    assert value["program_id"] is None
    assert value["retained_pcm_bytes"] == 0
    assert value["emission_observed"] is False
    assert value["fresh_articulatory_synthesis_observed"] is False
    assert value["thing_ids"] == []
    assert all(item is None for item in value["receipts"].values())
    assert value["transient_act"] == {
        "committed": False,
        "pcm_byte_count": 0,
        "pcm_sha256": None,
    }
    assert all(
        authority is False
        for authority in value["authorities"].values()
    )


def test_signed_silent_and_committed_occurrences_project_only_truth() -> None:
    silent_response = _seal(
        state="unbound",
        thing_ids=(_identity("unbound-thing"),),
        executed=False,
        pcm_sha256=None,
    )
    silent = project_consequence_evoked_articulatory_loom_observation(
        authority_key=PROJECTION_KEY,
        source_authority_key=RESPONSE_KEY,
        occurrence=silent_response,
    )
    verify_consequence_evoked_articulatory_loom_observation(
        silent,
        authority_key=PROJECTION_KEY,
    )
    assert silent["status"] == "observed"
    assert silent["response_state"] == "unbound"
    assert silent["thing_ids"] == list(silent_response.thing_ids)
    assert silent["program_id"] is None
    assert silent["emission_observed"] is False
    assert silent["retained_pcm_bytes"] == 0
    assert silent["transient_act"]["committed"] is False

    pcm = tuple(
        value
        for sample in range(256)
        for value in int(sample - 128).to_bytes(
            2,
            "little",
            signed=True,
        )
    )
    pcm_s16le = bytes(pcm)
    response = _seal(
        state="executed",
        thing_ids=(_identity("executed-thing"),),
        executed=True,
        pcm_sha256=hashlib.sha256(pcm_s16le).hexdigest(),
    )
    act = CommittedConsequenceEvokedArticulatoryAct(
        response=response,
        pcm_s16le=pcm_s16le,
    )
    observed = project_consequence_evoked_articulatory_loom_observation(
        authority_key=PROJECTION_KEY,
        source_authority_key=RESPONSE_KEY,
        occurrence=act,
    )
    verify_consequence_evoked_articulatory_loom_observation(
        observed,
        authority_key=PROJECTION_KEY,
    )
    assert observed["status"] == "observed"
    assert observed["response_state"] == "executed"
    assert observed["program_id"] == response.program_id
    assert observed["thing_ids"] == list(response.thing_ids)
    assert observed["emission_observed"] is True
    assert observed["fresh_articulatory_synthesis_observed"] is True
    assert observed["retained_pcm_bytes"] == 0
    assert observed["transient_act"] == {
        "committed": True,
        "pcm_byte_count": len(pcm_s16le),
        "pcm_sha256": response.synthesis_pcm_sha256,
    }
    assert observed["receipts"] == {
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
    }
    encoded = json.dumps(observed, sort_keys=True)
    assert "pcm_s16le" not in encoded
    assert "causal_thing_vocal_route" not in encoded
    assert all(
        authority is False
        for authority in observed["authorities"].values()
    )

    with pytest.raises(
        ValueError,
        match="requires its transient committed act",
    ):
        project_consequence_evoked_articulatory_loom_observation(
            authority_key=PROJECTION_KEY,
            source_authority_key=RESPONSE_KEY,
            occurrence=response,
        )
    with pytest.raises(ValueError, match="changed pressure custody"):
        project_consequence_evoked_articulatory_loom_observation(
            authority_key=PROJECTION_KEY,
            source_authority_key=RESPONSE_KEY,
            occurrence=replace(
                act,
                pcm_s16le=act.pcm_s16le[:-2] + b"\x00\x00",
            ),
        )
    changed = {
        **observed,
        "retained_pcm_bytes": 1,
    }
    with pytest.raises(ValueError):
        verify_consequence_evoked_articulatory_loom_observation(
            changed,
            authority_key=PROJECTION_KEY,
        )

    source_text = inspect.getsource(projection_module)
    assert "sight_evoked_articulatory_response" not in source_text
    assert "causal_thing_vocal_route" not in source_text
    assert "SelfVocalPCM" not in source_text
