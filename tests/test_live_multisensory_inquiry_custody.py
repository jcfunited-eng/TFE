from __future__ import annotations

import io
import json
import math
import struct
import wave
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.visual_region_continuity import (
    CanonicalVisualFrame,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


def _physical_tone_wav() -> bytes:
    sample_rate = 16_000
    samples = tuple(
        int(
            8_000
            * (
                math.sin(2.0 * math.pi * 317.0 * index / sample_rate)
                + 0.37
                * math.sin(2.0 * math.pi * 911.0 * index / sample_rate)
            )
            / 1.37
        )
        for index in range(sample_rate)
    )
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return payload.getvalue()


def _physical_frames(source_start_ns: int) -> tuple[
    CanonicalVisualFrame, ...
]:
    rows, columns = np.indices((64, 64))
    frames = []
    for index, offset_ns in enumerate(
        (100_000_000, 500_000_000, 900_000_000, 1_300_000_000)
    ):
        values = (
            rows * 17
            + columns * 31
            + index * 13
            + (rows // 8) * index * 7
        ) % 256
        frames.append(
            CanonicalVisualFrame.from_uint8(
                source_start_ns + offset_ns,
                values.astype(np.uint8),
            )
        )
    return tuple(frames)


def _all_mapping_keys(value: object) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        result.update(str(key) for key in value)
        for child in value.values():
            result.update(_all_mapping_keys(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_all_mapping_keys(child))
    return result


def test_real_av_window_retries_then_creates_one_unresolved_inquiry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "live-multisensory-inquiry-custody-test-key",
    )

    engine = Guala()
    engine.load_full_state(str(tmp_path))
    context_id = "test:live-multisensory-inquiry"
    source_start_ns = 1_000_000_000_000
    source_end_ns = source_start_ns + 5_000_000_000
    pcm_wav = _physical_tone_wav()
    try:
        engine.window_manager.begin_context(
            context_id,
            "audiovisual_capture",
            context_detail={
                "source_time_start_ns": source_start_ns,
                "source_time_end_ns": source_end_ns,
                "sensor_unavailable": [
                    "touch",
                    "smell",
                    "taste",
                    "body",
                ],
            },
        )
        engine.process_live_visual_region_sequence(
            _physical_frames(source_start_ns),
            source_time_start_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
        )
        engine.process_sound_frame(
            pcm_wav,
            source="browser_microphone",
            source_anchor_ns=source_start_ns,
            source_time_end_ns=source_start_ns + 1_000_000_000,
            auditory_event_boundary="ambient",
        )
        capture = engine._latest_auditory_full_field_capture
        authentic_source_sample_count = len(
            capture.channels[0].causal_offsets_ns
        )

        visual_before = (
            engine._visual_region_continuity.snapshot_encoded()
        )
        exposure_before = engine._visual_exposure_epoch.snapshot_encoded()
        prediction_before = engine._full_field_prediction.encoded_snapshot()
        anonymous_before = (
            engine._anonymous_passive_window.snapshot_encoded()
        )
        inquiry_before = engine._causal_inquiry_owner.snapshot_encoded()
        thing_before = (
            engine._causal_thing_mosaic_owner.snapshot_encoded()
        )
        lived_before = (
            engine._causal_thing_lived_context.snapshot_encoded()
        )
        consequence_before = (
            engine._articulatory_consequence_closure.snapshot_encoded()
        )
        play_before = engine._autonomous_causal_play.encoded_snapshot()
        action_cycle_before = engine._causal_action_cycle.encoded_snapshot()
        dispatcher_before = (
            engine._causal_action_dispatcher.encoded_snapshot()
        )
        causal_status_before = engine._causal_experience_owner.status()
        accepted_before = engine._causal_settlement_accepted
        original_inquiry_admission = (
            engine.admit_anonymous_causal_inquiry_window
        )

        def reject_after_inquiry_commit(*args, **kwargs):
            original_inquiry_admission(*args, **kwargs)
            raise RuntimeError("injected late inquiry rejection")

        monkeypatch.setattr(
            engine,
            "admit_anonymous_causal_inquiry_window",
            reject_after_inquiry_commit,
        )
        with pytest.raises(
            RuntimeError,
            match="injected late inquiry rejection",
        ):
            engine.window_manager.end_context(
                context_id,
                "audiovisual_capture_complete",
                return_settlement=True,
            )

        assert engine.window_manager.open_context_ids() == (context_id,)
        assert (
            engine._visual_region_continuity.snapshot_encoded()
            == visual_before
        )
        assert (
            engine._visual_exposure_epoch.snapshot_encoded()
            == exposure_before
        )
        assert (
            engine._full_field_prediction.encoded_snapshot()
            == prediction_before
        )
        assert (
            engine._anonymous_passive_window.snapshot_encoded()
            == anonymous_before
        )
        assert engine._causal_inquiry_owner.snapshot_encoded() == inquiry_before
        assert (
            engine._causal_thing_mosaic_owner.snapshot_encoded()
            == thing_before
        )
        assert (
            engine._causal_thing_lived_context.snapshot_encoded()
            == lived_before
        )
        assert (
            engine._articulatory_consequence_closure.snapshot_encoded()
            == consequence_before
        )
        assert (
            engine._autonomous_causal_play.encoded_snapshot()
            == play_before
        )
        assert (
            engine._causal_action_cycle.encoded_snapshot()
            == action_cycle_before
        )
        assert (
            engine._causal_action_dispatcher.encoded_snapshot()
            == dispatcher_before
        )
        assert engine._causal_experience_owner.status() == causal_status_before
        assert engine._causal_settlement_accepted == accepted_before

        monkeypatch.setattr(
            engine,
            "admit_anonymous_causal_inquiry_window",
            original_inquiry_admission,
        )
        window_id, settlement = engine.window_manager.end_context(
            context_id,
            "audiovisual_capture_complete",
            return_settlement=True,
        )
        settlement.verify()

        assert settlement.assembly_id == f"causal-{window_id}"
        assert settlement.source_time_start == Fraction(
            source_start_ns, 1_000_000_000
        )
        assert settlement.source_time_end == Fraction(
            source_end_ns, 1_000_000_000
        )
        assert settlement.language_events == ()
        assert settlement.routing_chis == ()
        assert settlement.source_tags == ()
        interpretations = {
            value.sense: value for value in settlement.interpretations
        }
        assert tuple(interpretations) == (
            "sight",
            "sound",
            "touch",
            "smell",
            "taste",
            "body",
        )
        assert (
            interpretations["sight"].state,
            len(interpretations["sight"].substreams),
        ) == ("observed", 64)
        assert (
            interpretations["sound"].state,
            len(interpretations["sound"].substreams),
        ) == ("observed", 32)
        assert all(
            interpretations[sense].state == "sensor_unavailable"
            and not interpretations[sense].substreams
            for sense in ("touch", "smell", "taste", "body")
        )

        inquiry = engine._causal_inquiry_owner
        assert inquiry.status()["witness_count"] == 1
        assert inquiry.status()["active_need"] is True
        assert inquiry.status()["retained_media_bytes"] == 0
        assert len(inquiry.witnesses) == 1
        witness = inquiry.witnesses[0]
        assert witness.route_state in {"unresolved", "ambiguous"}
        assert witness.thing_ids == ()
        assert witness.observed_senses == ("sight", "sound")
        assert witness.source_time_start == settlement.source_time_start
        assert witness.source_time_end == settlement.source_time_end
        assert (
            witness.settlement_receipt_sha256
            == settlement.authority_receipt_sha256
        )
        assert (
            engine._latest_causal_inquiry_observation["inquiry_state"]
            == "witness_admitted"
        )
        assert (
            engine._latest_causal_inquiry_observation["meaning_authority"]
            is False
        )
        assert (
            engine._latest_causal_inquiry_observation["word_authority"]
            is False
        )

        sound_roots = tuple(
            root for root in witness.full_field_roots
            if root.sense == "sound"
        )
        assert len(sound_roots) == 32
        assert tuple(root.topology_index for root in sound_roots) == tuple(
            range(32)
        )
        for root in sound_roots:
            root.verify()
            evidence = json.loads(root.full_evidence_json)
            assert (
                evidence["source_sample_count"]
                == authentic_source_sample_count
            )
            assert evidence["topology_index"] == root.topology_index
            assert evidence["field_tuples"]
            assert evidence["field_tuples"][0]["source_index_start"] == 0
            assert (
                evidence["field_tuples"][-1]["source_index_end"]
                == authentic_source_sample_count - 1
            )
            prior_end = -1
            for tuple_index, field_tuple in enumerate(
                evidence["field_tuples"]
            ):
                assert field_tuple["tuple_index"] == tuple_index
                assert field_tuple["source_index_start"] == prior_end + 1
                assert (
                    field_tuple["source_index_end"]
                    >= field_tuple["source_index_start"]
                )
                prior_end = field_tuple["source_index_end"]
                assert tuple(
                    name for name, _value in field_tuple["fields"]
                ) == DSF_FIELD_ORDER
                for _name, value in field_tuple["fields"]:
                    exact = Fraction(value)
                    assert value == (
                        f"{exact.numerator}/{exact.denominator}"
                    )
                assert len(
                    field_tuple[
                        "source_l0_l4_trace_receipt_sha256"
                    ]
                ) == 64

        persisted = json.loads(inquiry.snapshot_encoded())
        forbidden_physical_payload_keys = {
            "frame",
            "frame_bytes",
            "pcm",
            "pcm_s16le",
            "pixels",
            "raw_pcm",
            "recognized_language_record",
            "routing_chis",
            "source_tags",
            "text",
            "transcript",
            "tutor_label",
            "unicode_scalars",
        }
        assert not (
            _all_mapping_keys(persisted)
            & forbidden_physical_payload_keys
        )
        assert engine.window_manager.open_context_ids() == ()
        assert engine._causal_settlement_accepted == accepted_before + 1
        assert engine._causal_settlement_failed == 1
    finally:
        engine.shutdown()
