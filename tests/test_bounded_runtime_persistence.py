import json
from pathlib import Path
import struct

import pytest

from dsf_ai_service.substrate.deployment_generation import (
    BoundedStageAdmission,
    StageValidationError,
    _discover_staged_files,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


def _pressure(amplitude: int) -> bytes:
    return struct.pack(
        "<960h",
        *(
            amplitude if index % 16 < 8 else -amplitude
            for index in range(960)
        ),
    )


def test_real_whole_organism_cold_stage_is_bounded_and_roundtrips(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "bounded-whole-organism-current-owner-key",
    )
    stage = tmp_path / "stage"
    stage.mkdir()
    guala = Guala()
    guala.experience_companion_vocal_pressure(_pressure(12_000))
    captured_binaural = json.loads(
        guala._w1_binaural_auditory_l5_owner
        .encoded_snapshot().decode("utf-8")
    )
    admission = BoundedStageAdmission(
        stage,
        max_total_bytes=160 * 1024 * 1024,
        max_required_files=8,
        max_path_bytes=4096,
    )
    prior_state_file_ticks = dict(guala._state_file_ticks)
    prior_last_save_tick = guala._last_save_tick
    prior_last_cold_save_tick = guala._last_cold_save_tick
    prior_last_save_timestamp = guala._last_save_timestamp

    with guala.bounded_persistence_admission(admission):
        guala.save_full_state(
            str(stage),
            publish_generation=False,
        )
        prepared = dict(
            guala._prepared_authoritative_full_checkpoint
        )

    assert guala._state_file_ticks == prior_state_file_ticks
    assert guala._last_save_tick == prior_last_save_tick
    assert guala._last_cold_save_tick == prior_last_cold_save_tick
    assert guala._last_save_timestamp == prior_last_save_timestamp

    staged_core = json.loads(
        (stage / "guala_core.json").read_text(encoding="utf-8")
    )
    staged_data = staged_core["data"]
    captured_tick = prepared["tick"]
    assert staged_data["tick"] == captured_tick
    assert staged_data["state_file_ticks"] == {
        "guala_core.json": captured_tick,
    }
    assert staged_data["organism_state"][
        "w1_binaural_auditory_l5"
    ] == captured_binaural

    guala.finalize_authoritative_full_checkpoint(
        expected_tick=captured_tick,
        state_file_ticks=staged_data["state_file_ticks"],
    )
    assert guala._last_save_tick == captured_tick
    assert guala._last_cold_save_tick == captured_tick
    assert guala._cold_checkpoint_established is True

    files = _discover_staged_files(
        stage,
        max_total_bytes=160 * 1024 * 1024,
        max_required_files=8,
        max_path_bytes=4096,
    )
    admission.verify_complete(files)
    assert set(files) == {"guala_core.json", "guala_identity.json"}

    restored = Guala()
    restored.load_full_state(str(stage), require_exact_binary=True)
    assert restored._load_successful is True
    assert restored._guala_identity == guala._guala_identity
    assert restored.tick == captured_tick
    assert json.loads(
        restored._w1_binaural_auditory_l5_owner
        .encoded_snapshot().decode("utf-8")
    ) == captured_binaural


def test_whole_organism_cold_stage_cannot_cross_byte_capacity(
    tmp_path: Path,
) -> None:
    guala = Guala()
    prior_owner_lineage = dict(guala._owner_freeze_lineage)
    admission = BoundedStageAdmission(
        tmp_path,
        max_total_bytes=1024,
        max_required_files=8,
        max_path_bytes=4096,
    )

    with pytest.raises(
        StageValidationError,
        match="aggregate byte capacity",
    ):
        with guala.bounded_persistence_admission(admission):
            guala.save_full_state(
                str(tmp_path),
                publish_generation=False,
            )

    assert guala._prepared_authoritative_full_checkpoint is None
    assert guala._owner_freeze_lineage == prior_owner_lineage
    assert sum(
        path.stat().st_size
        for path in tmp_path.rglob("*")
        if path.is_file()
    ) <= 1024


def test_discarded_cold_candidate_keeps_both_dirty_gates_open(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "discarded-whole-organism-candidate-key",
    )
    baseline = tmp_path / "baseline"
    stage = tmp_path / "stage"
    guala = Guala()
    try:
        guala.save_full_state(str(baseline))
        stage.mkdir()
        prior_owner_lineage = {
            owner_id: dict(receipt)
            for owner_id, receipt in guala._owner_freeze_lineage.items()
        }
        prior_state_file_ticks = dict(guala._state_file_ticks)
        prior_last_save_tick = guala._last_save_tick
        prior_last_cold_save_tick = guala._last_cold_save_tick
        prior_last_save_timestamp = guala._last_save_timestamp
        prior_cold_established = guala._cold_checkpoint_established

        guala.experience_companion_vocal_pressure(_pressure(8_000))
        admission = BoundedStageAdmission(
            stage,
            max_total_bytes=160 * 1024 * 1024,
            max_required_files=8,
            max_path_bytes=4096,
        )
        with guala.bounded_persistence_admission(admission):
            guala.save_full_state(
                str(stage),
                publish_generation=False,
            )

        guala.discard_prepared_authoritative_full_checkpoint()

        assert guala._owner_freeze_lineage == prior_owner_lineage
        assert guala._prepared_authoritative_full_checkpoint is None
        assert guala._state_file_ticks == prior_state_file_ticks
        assert guala._last_save_tick == prior_last_save_tick
        assert guala._last_cold_save_tick == prior_last_cold_save_tick
        assert guala._last_save_timestamp == prior_last_save_timestamp
        assert (
            guala._cold_checkpoint_established
            is prior_cold_established
        )
        with guala.settled_external_persistence_transaction():
            assert guala.settled_hot_persistence_checkpoint_required()
            assert guala.settled_cold_persistence_checkpoint_required()
    finally:
        guala.strict_shutdown(timeout=30.0)


def test_rejected_hot_generation_does_not_advance_live_bookkeeping(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "rejected-hot-whole-organism-generation-key",
    )
    guala = Guala()
    guala.save_full_state(str(tmp_path))
    prior_ticks = dict(guala._state_file_ticks)
    prior_last_save_tick = guala._last_save_tick
    prior_owner_lineage = {
        owner_id: dict(receipt)
        for owner_id, receipt in guala._owner_freeze_lineage.items()
    }
    guala.experience_companion_vocal_pressure(_pressure(8_000))

    def reject_hot_generation(**_kwargs):
        raise RuntimeError("injected hot lineage rejection")

    guala._authoritative_hot_generation_publisher = (
        reject_hot_generation
    )
    try:
        with pytest.raises(
            RuntimeError,
            match="hot lineage rejection",
        ):
            guala.save_hot_state(str(tmp_path))
    finally:
        guala.strict_shutdown(timeout=30.0)

    assert guala._state_file_ticks == prior_ticks
    assert guala._owner_freeze_lineage == prior_owner_lineage
    assert guala._last_save_tick == prior_last_save_tick
