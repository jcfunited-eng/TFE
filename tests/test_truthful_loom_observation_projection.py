from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    BINAURAL_CHANNEL_ORDER,
    BrowserBinauralLineageMode,
    BrowserBinauralPCMStreamRegistry,
    future_browser_binaural_integration_contract,
)
from dsf_ai_service.substrate.auditory_live_motif import (
    AUDITORY_LIVE_MOTIF_RESULT_SCHEMA,
    compact_live_motif_q_receipt,
)
from dsf_ai_service.substrate.truthful_loom_observation_projection import (
    LoomRuntimeComponentEvidence,
    TruthfulLoomObservationProjector,
)


PROJECTION_KEY = b"truthful-loom-projection-authority"


def _browser_chunk():
    registry = BrowserBinauralPCMStreamRegistry()
    opened = registry.open()
    lineage = registry.register_lineage(
        stream_id=opened["stream_id"],
        capture_session_sha256="1" * 64,
        worklet_source_sha256="2" * 64,
        media_track_settings_sha256="3" * 64,
        mode=BrowserBinauralLineageMode.DISCRETE_SOURCE_CHANNELS,
        media_track_channel_count=2,
        worklet_input_channel_count=2,
        channel_order=BINAURAL_CHANNEL_ORDER,
    )
    return registry.accept(
        stream_id=opened["stream_id"],
        lineage_receipt_sha256=lineage.receipt_sha256,
        sequence=0,
        first_sample_index=0,
        render_frame_start=48_000,
        sample_rate_hz=16_000,
        source_epoch_start_ns=8_000_000_000,
        left_pcm_s16le=b"\0\0" * 320,
        right_pcm_s16le=b"\0\0" * 320,
    )


def _projector() -> TruthfulLoomObservationProjector:
    return TruthfulLoomObservationProjector(
        authority_key=PROJECTION_KEY,
    )


def _pending_q_receipt():
    payload = {
        "activation_spans": [],
        "firing_motif_neuron_ids": [],
        "firing_reason": "exact four-unit physical window is incomplete",
        "firing_state": "awaiting_exact_window_composition",
        "firing_work_cells": 0,
        "learning_firing_motif_neuron_ids": [],
        "learning_reason": "continued receptor interval is retained",
        "learning_state": "awaiting_exact_window_composition",
        "learning_work_cells": 0,
        "newly_grown_motif_neuron_ids": [],
        "reinforced_motif_neuron_ids": [],
        "schema": AUDITORY_LIVE_MOTIF_RESULT_SCHEMA,
        "source_experience_receipt_sha256": "b" * 64,
        "source_receptor_event_receipt_sha256": "a" * 64,
        "unresolved_source_indices": [],
    }
    authority = hashlib.sha256(json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()
    return compact_live_motif_q_receipt(
        payload | {"authority_receipt_sha256": authority},
        source_receptor_event_receipt_sha256="a" * 64,
        source_experience_receipt_sha256="b" * 64,
    )


def test_projection_has_no_model_or_transcript_observation_input():
    projection = _projector().project()
    record = projection.as_record(PROJECTION_KEY)

    assert record["boundary_observations"] == []
    assert record["cognition"]["status"] == "not_observed"
    assert record["cognition"]["firing_motif_neuron_ids"] == []
    assert record["cognition"]["activation_spans"] == []
    assert record["meaning"] == {
        "authority": False,
        "status": "not_established_by_observation_projection",
        "text": None,
    }


def test_tutor_label_is_designation_only_and_never_meaning():
    projection = _projector().project(
        tutor_designations=("hello", "guala"),
    )
    record = projection.as_record(PROJECTION_KEY)

    assert [value["display_text"] for value in record["designations"]] == [
        "hello",
        "guala",
    ]
    assert all(
        value["designation_only"] is True
        and value["cognition_authority"] is False
        and value["meaning_authority"] is False
        for value in record["designations"]
    )
    assert record["cognition"]["meaning_authority"] is False
    assert record["meaning"]["text"] is None


def test_discrete_browser_channels_remain_unproven_and_unadmitted():
    chunk = _browser_chunk()
    projection = _projector().project(
        browser_binaural_chunk=chunk,
    )
    record = projection.as_record(PROJECTION_KEY)

    assert record["binaural_transport"] == {
        "cognition_admitted": False,
        "hardware_authority_proven": False,
        "status": "discrete_transport_hardware_unproven",
        "transport_receipt_sha256": chunk.receipt.receipt_sha256,
    }
    assert record["cognition"]["status"] == "not_observed"


def test_recurrent_q_pending_state_is_presemantic_and_receipted():
    receipt = _pending_q_receipt()
    record = _projector().project(
        recurrent_q_result=receipt,
    ).as_record(PROJECTION_KEY)

    assert record["cognition"] == {
        "activation_spans": [],
        "firing_motif_neuron_ids": [],
        "learning_state": "awaiting_exact_window_composition",
        "meaning_authority": False,
        "presemantic_authority": True,
        "q_result_authority_receipt_sha256": (
            receipt.authority_receipt_sha256
        ),
        "source_experience_receipt_sha256": "b" * 64,
        "source_receptor_event_receipt_sha256": "a" * 64,
        "status": "recurrent_q_pending_window",
        "transcript_authority": False,
    }


def test_unwired_contract_cannot_appear_as_active_architecture():
    contract = future_browser_binaural_integration_contract()
    component = LoomRuntimeComponentEvidence(
        component_id="browser-binaural-cutover",
        contract_schema=contract["schema"],
        wired=contract["wired"],
        runtime_authority_receipt_sha256=None,
    )

    record = _projector().project(
        runtime_components=(component,),
    ).as_record(PROJECTION_KEY)

    assert record["runtime_components"] == [{
        "cognition_authority": False,
        "component_id": "browser-binaural-cutover",
        "contract_schema": contract["schema"],
        "runtime_authority_receipt_sha256": None,
        "status": "inactive_contract",
        "wired": False,
    }]


def test_contract_cannot_claim_live_receipt_while_unwired():
    component = LoomRuntimeComponentEvidence(
        component_id="inactive-only",
        contract_schema="guala.future.contract.v1",
        wired=False,
        runtime_authority_receipt_sha256="c" * 64,
    )

    with pytest.raises(
        ValueError,
        match="inactive Loom contract cannot carry live authority",
    ):
        _projector().project(runtime_components=(component,))


def test_arbitrary_status_or_label_dictionary_cannot_enter_cognition():
    with pytest.raises(
        TypeError,
        match="typed recurrent-q result",
    ):
        _projector().project(
            recurrent_q_result={  # type: ignore[arg-type]
                "status": "recognized",
                "transcript": "I understand",
                "meaning": True,
            },
        )


def test_projection_authority_rejects_observation_promoted_to_cognition():
    projection = _projector().project()
    changed_cognition = dict(projection.cognition)
    changed_cognition.update({
        "meaning_authority": True,
        "status": "recurrent_q_observed",
    })
    changed = replace(
        projection,
        cognition=changed_cognition,
    )

    with pytest.raises(
        ValueError,
        match="fabricated cognition meaning",
    ):
        changed.verify(PROJECTION_KEY)
