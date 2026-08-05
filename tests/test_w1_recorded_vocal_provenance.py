from __future__ import annotations

import json
from pathlib import Path

import pytest

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.w1_recorded_vocal_provenance import (
    load_checked_w1_recorded_vocals,
)
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _emission,
    _vocal_execution,
    _world,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "dsf_ai_service"
    / "curriculum"
    / "w1_recorded_vocal_manifest.json"
)


def _canonical_file(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def test_checked_real_vocal_manifest_binds_repo_blob_and_decoded_pcm():
    recordings = load_checked_w1_recorded_vocals(
        repository_root=ROOT,
        manifest_path=MANIFEST,
    )

    assert len(recordings) == 5
    assert len({
        value.provenance.git_blob_sha1 for value in recordings
    }) == 5
    assert len({
        value.provenance.decoded_pcm_s16le_sha256
        for value in recordings
    }) == 5
    assert all(
        value.provenance.repository_commit
        == "f7a61fbd82cec6a69837d382d2f4f8bd16a06b2d"
        for value in recordings
    )
    assert all(
        not hasattr(value.provenance, "transcript")
        and not hasattr(value.provenance, "meaning")
        and not hasattr(value.provenance, "label")
        for value in recordings
    )


def test_recording_or_authority_manifest_tamper_is_rejected(tmp_path):
    manifest = json.loads(MANIFEST.read_bytes())
    manifest["assets"][0]["decoded_pcm_s16le_sha256"] = "0" * 64
    altered_pcm = tmp_path / "altered-pcm-manifest.json"
    altered_pcm.write_bytes(_canonical_file(manifest))
    with pytest.raises(
        ValueError,
        match="provenance authority changed",
    ):
        load_checked_w1_recorded_vocals(
            repository_root=ROOT,
            manifest_path=altered_pcm,
        )

    manifest = json.loads(MANIFEST.read_bytes())
    manifest["repository_authorities"][0]["sha256"] = "0" * 64
    altered_authority = tmp_path / "altered-authority-manifest.json"
    altered_authority.write_bytes(_canonical_file(manifest))
    with pytest.raises(
        ValueError,
        match="repository authority changed",
    ):
        load_checked_w1_recorded_vocals(
            repository_root=ROOT,
            manifest_path=altered_authority,
        )

    manifest = json.loads(MANIFEST.read_bytes())
    manifest["repository_authorities"][0]["git_blob_sha1"] = "0" * 40
    altered_blob = tmp_path / "altered-authority-blob.json"
    altered_blob.write_bytes(_canonical_file(manifest))
    with pytest.raises(
        ValueError,
        match="repository authority changed",
    ):
        load_checked_w1_recorded_vocals(
            repository_root=ROOT,
            manifest_path=altered_blob,
        )


def test_real_recorded_pressure_grows_two_ear_q_without_meaning():
    recording = next(
        value
        for value in load_checked_w1_recorded_vocals(
            repository_root=ROOT,
            manifest_path=MANIFEST,
        )
        if value.provenance.repository_path
        == "docs/Daddy says Hello.mp3"
    )
    assert recording.zero_tail_sample_count == 140
    q_owner = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-real-recorded-pressure-q",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=4,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )
    world = _world()
    physical = _authority(world)
    mounts = []
    epoch = physical.open_epoch()
    source_sample_start = 0
    for occurrence in range(3):
        execution = _vocal_execution(
            world,
            epoch,
            sequence=occurrence,
            source_sample_start=source_sample_start,
            pcm=recording.framed_pcm_s16le,
        )
        mount = physical.mount(
            epoch_token=epoch,
            sequence=occurrence,
            execution_receipt=execution,
            acoustic_emission=_emission(
                physical,
                epoch,
                execution,
                sequence=occurrence,
                source_sample_start=source_sample_start,
                pcm=recording.framed_pcm_s16le,
            ),
        )
        mounts.append(mount)
        if len(mounts) < 3:
            q_owner.observe_binaural(
                mount.binaural_receptor_settlement
            )
        source_sample_start += (
            len(recording.framed_pcm_s16le) // 2
        )
    firing = q_owner.fire_binaural(
        mounts[-1].binaural_receptor_settlement
    )
    assert firing.activations
    assert {
        value.ear_id for value in firing.activations
    } == {"left", "right"}
    assert recording.framing_receipt_sha256
    assert not hasattr(firing, "transcript")
    assert not hasattr(firing, "meaning")
    assert not hasattr(firing, "label")
