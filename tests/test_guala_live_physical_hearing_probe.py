"""Contracts for the live physical-hearing proof.

These tests exercise the receipt and authority validators without contacting
production.  The browser/live execution remains a deployment-time gate.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_CHUNK_SAMPLES,
    PCM_CONTINUITY_SCHEMA,
    PCM_SAMPLE_RATE_HZ,
)
from tools.probe_guala_live_physical_hearing import (
    FULL_FIELD_NAMES,
    OBSERVATION_SCHEMA,
    SCHEMA,
    validate_binaural_transport,
    validate_full_field_observation,
    validate_mono_settlements,
)


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = (ROOT / "tools" / "deploy_dsf_ai.sh").read_text()
PROBE = (
    ROOT / "tools" / "probe_guala_live_physical_hearing.py"
).read_text()


def _digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _sha(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _mono_records(count: int = 5) -> list[dict[str, object]]:
    stream_id = "physical-stream"
    source_epoch_ns = 8_000_000_000
    prior = None
    records = []
    for sequence in range(count):
        pcm = (
            (sequence + 1).to_bytes(2, "little", signed=True)
            * PCM_CHUNK_SAMPLES
        )
        request = {
            "audio_encoding": "pcm_s16le",
            "audio_first_sample_index": sequence * PCM_CHUNK_SAMPLES,
            "audio_sample_count": PCM_CHUNK_SAMPLES,
            "audio_sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "audio_sequence": sequence,
            "audio_source_epoch_ms": source_epoch_ns // 1_000_000,
            "audio_stream_id": stream_id,
            "text": base64.b64encode(pcm).decode("ascii"),
        }
        continuity_receipt = _digest({
            "first_sample_index": sequence * PCM_CHUNK_SAMPLES,
            "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "prior_receipt_sha256": prior,
            "sample_count": PCM_CHUNK_SAMPLES,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": PCM_CONTINUITY_SCHEMA,
            "sequence": sequence,
            "stream_id": stream_id,
            "source_epoch_start_ns": source_epoch_ns,
        })
        motif_receipt = _sha(f"motif-{sequence}")
        response = {
            "ok": True,
            "causal_boundary": "sound",
            "observed_senses": ["sound"],
            "spoken_word_recognition": {
                "candidate_labels": [],
                "kind_id": None,
                "meaning_authority": False,
                "recognized_form": None,
                "transcript_authority": False,
            },
            "auditory_motif": {
                "authority_receipt_sha256": motif_receipt,
                "firing_motif_neuron_ids": [],
                "firing_state": "awaiting_exact_window_composition",
                "newly_grown_motif_neuron_ids": [],
                "source_receptor_event_receipt_sha256": _sha(
                    f"receptor-{sequence}"
                ),
            },
            "auditory_l5": {
                "recognition_attempted": False,
                "continuous_streams": {
                    "active_streams": 1,
                    "stream_capacity": 8,
                },
                "recurrent_motif": {
                    "active_terminal_streams": 1,
                    "max_pending_transport_units_per_stream": 4,
                    "pending_independent_experience_capacity": 64,
                    "pending_independent_experience_count": sequence,
                    "pending_transport_units": sequence % 4,
                    "semantic_authority": False,
                    "transcript_authority": False,
                },
            },
            "pcm_continuity": {
                "auditory_motif_result_receipt_sha256": motif_receipt,
                "binaural_hardware_authority_proven": False,
                "causal_settlement_receipt_sha256": _sha(
                    f"settlement-{sequence}"
                ),
                "cochlear_state_receipt_sha256": _sha(
                    f"cochlear-{sequence}"
                ),
                "first_sample_index": sequence * PCM_CHUNK_SAMPLES,
                "meaning_authority": False,
                "receipt_sha256": continuity_receipt,
                "room_hearing_authority": False,
                "sample_count": PCM_CHUNK_SAMPLES,
                "sequence": sequence,
                "status": "contiguous",
                "transcript_authority": False,
            },
        }
        records.append({
            "fetchError": None,
            "request": request,
            "response": response,
            "responseStatus": 200,
        })
        prior = continuity_receipt
    return records


def _observation() -> dict[str, object]:
    value = {
        "schema": OBSERVATION_SCHEMA,
        "full_field_authority": {
            "available": True,
            "settlement_receipt_sha256": _sha("observed-settlement"),
            "status": "observed",
            "senses": [{
                "sense": "sound",
                "state": "observed",
                "substreams": [{
                    "fields": [
                        [name, f"{index}/1"]
                        for index, name in enumerate(
                            FULL_FIELD_NAMES,
                            start=1,
                        )
                    ],
                    "substream_id": "auditory-receptor-0",
                    "total_temporal_tuples": 3,
                }],
            }],
            "view_contract": {
                "decision_authority": False,
                "required_fields": list(FULL_FIELD_NAMES),
            },
        },
    }
    return {
        **value,
        "snapshot_receipt_sha256": _digest(value),
    }


def test_mono_proof_is_receipt_custody_not_motif_firing_or_word_matching():
    result = validate_mono_settlements(_mono_records())

    assert result["settled_chunks"] == 5
    assert result["settled_samples"] == 5 * PCM_CHUNK_SAMPLES
    assert len(result["continuity_receipt_sha256s"]) == 5
    assert len(result["cochlear_state_receipt_sha256s"]) == 5
    assert len(result["receptor_event_receipt_sha256s"]) == 5
    assert result["word_result"] is None


def test_mono_proof_rejects_semantic_or_resource_authority_crossing():
    semantic = _mono_records()
    semantic[0]["response"]["spoken_word_recognition"][
        "meaning_authority"
    ] = True
    with pytest.raises(RuntimeError, match="word or meaning authority"):
        validate_mono_settlements(semantic)

    unbounded = _mono_records()
    unbounded[0]["response"]["auditory_l5"]["recurrent_motif"][
        "pending_transport_units"
    ] = 5
    with pytest.raises(RuntimeError, match="exceeded exact capacity"):
        validate_mono_settlements(unbounded)


def test_observation_proves_explicit_full_field_and_signed_snapshot():
    result = validate_full_field_observation(_observation())

    assert result["receptor_substream_count"] == 1
    assert len(result["settlement_receipt_sha256"]) == 64
    assert len(result["snapshot_receipt_sha256"]) == 64

    flattened = _observation()
    flattened["full_field_authority"]["senses"][0]["substreams"][0][
        "fields"
    ].pop()
    payload = dict(flattened)
    payload.pop("snapshot_receipt_sha256")
    flattened["snapshot_receipt_sha256"] = _digest(payload)
    with pytest.raises(RuntimeError, match="explicit full field"):
        validate_full_field_observation(flattened)


def test_unavailable_pair_is_reported_without_false_binaural_authority():
    result = validate_binaural_transport(
        [],
        [],
        active=False,
        input_channel_count=1,
        mono_settlement_count=5,
    )

    assert result == {
        "available": False,
        "binaural_hardware_authority_proven": False,
        "distinct_channel_bytes_observed": False,
        "input_channel_count": 1,
        "reason": "runtime_exposed_one_captured_channel",
        "room_hearing_authority": False,
    }


def test_deploy_does_not_turn_hearing_into_release_authority():
    assert SCHEMA not in DEPLOY
    assert "tools/probe_guala_live_physical_hearing.py" not in DEPLOY
    assert "probe_guala_candidate_browser.py --live" not in DEPLOY
    assert "_validate_recurrent_motif_cognitive_proof" not in PROBE
    assert "HELLO_LEARNING_SETTLEMENT_SEQUENCE" not in PROBE
    assert "recurrent_motif_cognitive_proof" not in PROBE
    assert '"cognition": False' in PROBE
    assert '"word": False' in PROBE
