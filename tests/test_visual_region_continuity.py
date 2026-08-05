from fractions import Fraction
from io import BytesIO
import json
import threading

import numpy as np
import pytest
from PIL import Image

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.visual_region_continuity import (
    CanonicalVisualFrame,
    DeterministicVisualRegionContinuityAuthority,
    RETINA_RECEPTOR_COUNT,
    decode_visual_image_bytes,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.visual_exposure_epoch import (
    VisualExposureEpochAuthority,
)
import dsf_ai_service.substrate.visual_region_continuity as visual_module
from tests.native_joint_occurrence_support import joint_occurrences_for


KEY = b"visual-region-test-authority-key-32-bytes-minimum"


def _frames(*, shifted=False, source_base_seconds=0):
    result = []
    for index in range(4):
        pixels = np.zeros((64, 64), dtype=np.uint8)
        left = 8 if shifted else 0
        pixels[16:32, left : left + 16] = 40 + index * 20
        pixels[40:56, 40:56] = 180 - index * 10
        result.append(
            CanonicalVisualFrame.from_uint8(
                (source_base_seconds + index + 1) * 1_000_000_000,
                pixels,
            )
        )
    return tuple(result)


def _object_frames(*, x, source_base_seconds, split=False, descending=False):
    result = []
    for index in range(4):
        pixels = np.zeros((64, 64), dtype=np.uint8)
        value = (40, 80, 40, 80)[index] if descending else 40 + index * 20
        pixels[16:32, x : x + 16] = value
        if split:
            pixels[16:32, x + 8 : x + 16] = 180 - index * 10
        result.append(
            CanonicalVisualFrame.from_uint8(
                (source_base_seconds + index + 1) * 1_000_000_000,
                pixels,
            )
        )
    return tuple(result)


def _built(prepared, assembly_id, *, source_start=0):
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(source_start),
        source_time_end=Fraction(source_start + 5),
        observed_substreams={PhysicalSense.SIGHT: prepared.substreams}, occurrences=joint_occurrences_for({PhysicalSense.SIGHT: prepared.substreams}),
        states=states,
    )


def test_preparation_covers_every_receptor_and_retains_no_raw_frame():
    prepared = DeterministicVisualRegionContinuityAuthority.prepare_retinotopic_inputs(
        _frames()
    )
    assert len(prepared.substreams) == RETINA_RECEPTOR_COUNT
    assert len(prepared.native_records()) == RETINA_RECEPTOR_COUNT
    assert tuple(value.topology_index for value in prepared.substreams) == tuple(
        range(RETINA_RECEPTOR_COUNT)
    )
    assert all(len(value.normalized_signal) == 5 for value in prepared.substreams)
    assert not hasattr(prepared, "frames")
    assert not hasattr(prepared, "pixels")


def test_preparation_rejects_wrong_shape_dtype_order_and_cardinality():
    with pytest.raises(ValueError, match="64 by 64"):
        CanonicalVisualFrame.from_uint8(1, np.zeros((32, 32), dtype=np.uint8))
    with pytest.raises(ValueError, match="uint8"):
        CanonicalVisualFrame.from_uint8(1, np.zeros((64, 64), dtype=np.float64))
    frames = list(_frames())
    frames[2] = CanonicalVisualFrame.from_uint8(
        frames[1].source_time_ns, np.zeros((64, 64), dtype=np.uint8)
    )
    with pytest.raises(ValueError, match="strictly increase"):
        DeterministicVisualRegionContinuityAuthority.prepare_retinotopic_inputs(
            frames
        )
    with pytest.raises(ValueError, match="four through eight"):
        DeterministicVisualRegionContinuityAuthority.prepare_retinotopic_inputs(
            _frames()[:3]
        )


def test_decoder_rejects_compressed_images_above_physical_capture_dimensions():
    encoded = BytesIO()
    Image.new("L", (129, 128), color=1).save(encoded, format="PNG")
    with pytest.raises(ValueError, match="128 by 128 capture boundary"):
        decode_visual_image_bytes(encoded.getvalue())


def test_l5_reads_full_field_and_static_scene_is_only_a_recurrence_candidate():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    first_built = _built(prepared, "visual-first")
    first = authority.settle_l5(
        first_built.boundary, first_built.receipt_registry
    )
    authority.verify_settlement(first)
    assert sum(len(value.receptor_indices) for value in first.regions) == 64
    assert {value.continuity for value in first.regions} == {"unknown"}

    second_prepared = authority.prepare_retinotopic_inputs(
        _frames(source_base_seconds=5)
    )
    second_built = _built(
        second_prepared, "visual-second", source_start=5
    )
    second = authority.settle_l5(
        second_built.boundary, second_built.receipt_registry
    )
    authority.verify_settlement(second)
    assert {value.continuity for value in second.regions} == {"ambiguous"}
    assert tuple(
        value.lineage_receipt_sha256 for value in second.regions
    ) != tuple(value.lineage_receipt_sha256 for value in first.regions)
    assert all(
        value.continuity_basis
        == "touching_exact_structural_recurrence_candidate"
        for value in second.regions
    )
    assert second.window_relation == "touching_window_bounds"


def test_authenticated_acquisition_predecessor_is_candidate_not_identity():
    exposure = VisualExposureEpochAuthority(authority_key=KEY)
    authority = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY,
        exposure_epoch_authority=exposure,
    )
    auditory = AuditoryPCMStreamRegistry()
    stream_id = auditory.open()["stream_id"]

    prepared = authority.prepare_retinotopic_inputs(_frames())
    first_audio = auditory.accept(
        stream_id=stream_id,
        sequence=0,
        first_sample_index=0,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=b"\0\0" * 8,
    ).receipt
    first_evidence = exposure.prepare(
        auditory=first_audio,
        frame_receipt_sha256s=prepared.frame_receipt_sha256s,
        preparation_receipt_sha256=prepared.preparation_receipt_sha256,
    )
    exposure.commit(first_evidence)
    first_built = _built(prepared, "authenticated-first")
    first = authority.settle_l5(
        first_built.boundary,
        first_built.receipt_registry,
        exposure_evidence=first_evidence,
        preparation_receipt_sha256=prepared.preparation_receipt_sha256,
    )
    assert first.window_relation == "first"

    second_prepared = authority.prepare_retinotopic_inputs(
        _frames(source_base_seconds=5)
    )
    second_audio = auditory.accept(
        stream_id=stream_id,
        sequence=1,
        first_sample_index=8,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=b"\0\0" * 8,
    ).receipt
    second_evidence = exposure.prepare(
        auditory=second_audio,
        frame_receipt_sha256s=second_prepared.frame_receipt_sha256s,
        preparation_receipt_sha256=(
            second_prepared.preparation_receipt_sha256
        ),
    )
    before = authority.snapshot_encoded()
    forged_built = _built(
        second_prepared,
        "authenticated-second-forged",
        source_start=5,
    )
    with pytest.raises(ValueError, match="crossed preparation authority"):
        authority.settle_l5(
            forged_built.boundary,
            forged_built.receipt_registry,
            exposure_evidence=second_evidence,
            preparation_receipt_sha256="f" * 64,
        )
    assert authority.snapshot_encoded() == before

    exposure.commit(second_evidence)
    second_built = _built(
        second_prepared,
        "authenticated-second",
        source_start=5,
    )
    second = authority.settle_l5(
        second_built.boundary,
        second_built.receipt_registry,
        exposure_evidence=second_evidence,
        preparation_receipt_sha256=(
            second_prepared.preparation_receipt_sha256
        ),
    )
    assert second.window_relation == "authenticated_predecessor_evidence"
    assert {region.continuity for region in second.regions} == {"ambiguous"}
    assert all(
        region.continuity_basis.startswith("authenticated_")
        for region in second.regions
    )


def test_static_distinct_light_levels_remain_distinct_at_l4():
    frames = []
    for index in range(4):
        pixels = np.zeros((64, 64), dtype=np.uint8)
        pixels[:, 32:] = 180
        frames.append(
            CanonicalVisualFrame.from_uint8(
                (index + 1) * 1_000_000_000, pixels
            )
        )
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(frames)
    built = _built(prepared, "static-distinct-light")
    settlement = authority.settle_l5(
        built.boundary, built.receipt_registry
    )
    assert len(settlement.regions) == 2
    assert settlement.regions[0].receptor_indices == tuple(
        row * 8 + column for row in range(8) for column in range(4)
    )
    assert settlement.regions[1].receptor_indices == tuple(
        row * 8 + column for row in range(8) for column in range(4, 8)
    )


def test_l5_rejects_forged_registry_without_mutating_state():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    built = _built(prepared, "visual-forgery")
    before = authority.snapshot_encoded()
    with pytest.raises(Exception):
        authority.settle_l5(built.boundary, ReceiptRegistryForForgery())
    assert authority.snapshot_encoded() == before


class ReceiptRegistryForForgery:
    pass


def test_snapshot_round_trip_and_tamper_rejection():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    built = _built(prepared, "visual-persist")
    authority.settle_l5(built.boundary, built.receipt_registry)
    encoded = authority.snapshot_encoded()

    restored = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    restored.restore_encoded(encoded)
    restored_record = json.loads(restored.snapshot_encoded())
    original_record = json.loads(encoded)
    assert restored_record["payload"]["history"] == (
        original_record["payload"]["history"]
    )
    assert restored_record["payload"]["live"] is False
    assert restored_record["payload"]["prior_regions"] == []
    assert restored_record["payload"]["prior_source_time_end"] is None
    inactive_encoded = restored.snapshot_encoded()

    changed = bytearray(encoded)
    changed[len(changed) // 2] ^= 1
    with pytest.raises(ValueError):
        restored.restore_encoded(bytes(changed))
    assert restored.snapshot_encoded() == inactive_encoded


def test_concurrent_settlements_are_serialized_as_one_visual_state_owner(
    monkeypatch,
):
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(_frames())
    first_built = _built(first_prepared, "serialized-first")
    second_prepared = authority.prepare_retinotopic_inputs(
        _frames(source_base_seconds=5)
    )
    second_built = _built(
        second_prepared,
        "serialized-second",
        source_start=5,
    )
    first_entered = threading.Event()
    second_entered = threading.Event()
    release_first = threading.Event()
    entry_lock = threading.Lock()
    entry_count = 0
    original = authority._explicit_receptor_fields

    def blocking_receptor_fields(sight):
        nonlocal entry_count
        with entry_lock:
            entry_count += 1
            current = entry_count
        if current == 1:
            first_entered.set()
            assert release_first.wait(timeout=5)
        else:
            second_entered.set()
        return original(sight)

    monkeypatch.setattr(
        authority,
        "_explicit_receptor_fields",
        blocking_receptor_fields,
    )
    results = []
    errors = []

    def settle(built):
        try:
            results.append(
                authority.settle_l5(
                    built.boundary,
                    built.receipt_registry,
                )
            )
        except Exception as error:
            errors.append(error)

    first_thread = threading.Thread(target=settle, args=(first_built,))
    second_thread = threading.Thread(target=settle, args=(second_built,))
    first_thread.start()
    assert first_entered.wait(timeout=5)
    second_thread.start()
    assert not second_entered.wait(timeout=0.2)
    release_first.set()
    first_thread.join(timeout=5)
    second_thread.join(timeout=5)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert errors == []
    assert second_entered.is_set()
    assert [value.window_relation for value in results] == [
        "first",
        "touching_window_bounds",
    ]


def test_shifted_scene_never_inherits_without_unique_exact_overlap():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(_frames())
    first_built = _built(first_prepared, "visual-origin")
    authority.settle_l5(first_built.boundary, first_built.receipt_registry)

    shifted_prepared = authority.prepare_retinotopic_inputs(
        _frames(shifted=True, source_base_seconds=5)
    )
    shifted_built = _built(
        shifted_prepared, "visual-shifted", source_start=5
    )
    shifted = authority.settle_l5(
        shifted_built.boundary, shifted_built.receipt_registry
    )
    assert all(
        value.continuity in {"unknown", "ambiguous"}
        for value in shifted.regions
    )
    authority.verify_settlement(shifted)


def test_touching_exact_structure_is_candidate_across_translation():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=0)
    )
    first_built = _built(first_prepared, "translated-first")
    first = authority.settle_l5(
        first_built.boundary, first_built.receipt_registry
    )
    second_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=16, source_base_seconds=5)
    )
    second_built = _built(
        second_prepared, "translated-second", source_start=5
    )
    second = authority.settle_l5(
        second_built.boundary, second_built.receipt_registry
    )
    first_object = next(
        value for value in first.regions if len(value.receptor_indices) == 4
    )
    second_object = next(
        value for value in second.regions if len(value.receptor_indices) == 4
    )
    assert not set(first_object.receptor_indices).intersection(
        second_object.receptor_indices
    )
    assert second_object.continuity == "ambiguous"
    assert second_object.continuity_basis == (
        "touching_exact_structural_recurrence_candidate"
    )
    assert second_object.lineage_receipt_sha256 != (
        first_object.lineage_receipt_sha256
    )
    assert second_object.candidate_lineage_receipt_sha256s == (
        first_object.lineage_receipt_sha256,
    )


def test_touching_reciprocal_overlap_is_only_a_candidate():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=0)
    )
    first_built = _built(first_prepared, "changed-first")
    first = authority.settle_l5(
        first_built.boundary, first_built.receipt_registry
    )
    second_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=5, descending=True)
    )
    second_built = _built(second_prepared, "changed-second", source_start=5)
    second = authority.settle_l5(
        second_built.boundary, second_built.receipt_registry
    )
    first_object = next(
        value for value in first.regions if len(value.receptor_indices) == 4
    )
    second_object = next(
        value for value in second.regions if len(value.receptor_indices) == 4
    )
    assert second_object.structural_receipt_sha256 != (
        first_object.structural_receipt_sha256
    )
    assert second_object.continuity == "ambiguous"
    assert second_object.continuity_basis == (
        "touching_reciprocal_retinotopic_overlap_candidate"
    )
    assert second_object.lineage_receipt_sha256 != (
        first_object.lineage_receipt_sha256
    )
    assert second_object.candidate_lineage_receipt_sha256s == (
        first_object.lineage_receipt_sha256,
    )


def test_split_region_is_ambiguous_instead_of_becoming_two_objects():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=0)
    )
    first_built = _built(first_prepared, "split-first")
    authority.settle_l5(first_built.boundary, first_built.receipt_registry)
    second_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=5, split=True)
    )
    second_built = _built(second_prepared, "split-second", source_start=5)
    second = authority.settle_l5(
        second_built.boundary, second_built.receipt_registry
    )
    object_regions = tuple(
        value for value in second.regions if len(value.receptor_indices) == 2
    )
    assert len(object_regions) == 2
    assert {value.continuity for value in object_regions} == {"ambiguous"}
    assert all(
        value.continuity_basis == "touching_competing_candidates"
        for value in object_regions
    )


def test_gap_recurrence_is_candidate_only_and_restart_is_inactive():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=0)
    )
    first_built = _built(first_prepared, "gap-first")
    first = authority.settle_l5(
        first_built.boundary, first_built.receipt_registry
    )
    gap_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=10)
    )
    gap_built = _built(gap_prepared, "gap-second", source_start=10)
    gap = authority.settle_l5(gap_built.boundary, gap_built.receipt_registry)
    assert gap.window_relation == "gap"
    assert {value.continuity for value in gap.regions} == {"ambiguous"}
    assert all(
        value.continuity_basis == "source_gap_structural_recurrence"
        for value in gap.regions
    )
    assert tuple(value.lineage_receipt_sha256 for value in gap.regions) != tuple(
        value.lineage_receipt_sha256 for value in first.regions
    )

    restored = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    restored.restore_encoded(authority.snapshot_encoded())
    assert restored.status()["active"] is False
    next_prepared = restored.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=15)
    )
    next_built = _built(next_prepared, "restart-first", source_start=15)
    next_settlement = restored.settle_l5(
        next_built.boundary, next_built.receipt_registry
    )
    assert next_settlement.window_relation == "first"
    assert {value.continuity for value in next_settlement.regions} == {"unknown"}


def test_digest_collision_cannot_replace_explicit_field_comparison(monkeypatch):
    monkeypatch.setattr(
        visual_module,
        "_region_structure_receipt",
        lambda _value: "a" * 64,
    )
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(x=0, source_base_seconds=0)
    )
    first_built = _built(first_prepared, "collision-first")
    authority.settle_l5(first_built.boundary, first_built.receipt_registry)
    second_prepared = authority.prepare_retinotopic_inputs(
        _object_frames(
            x=16,
            source_base_seconds=5,
            descending=True,
        )
    )
    second_built = _built(second_prepared, "collision-second", source_start=5)
    second = authority.settle_l5(
        second_built.boundary, second_built.receipt_registry
    )
    translated = next(
        value for value in second.regions if len(value.receptor_indices) == 4
    )
    assert translated.continuity != "unique"
    assert translated.continuity_basis != (
        "touching_exact_structural_recurrence_candidate"
    )


def test_settlement_retains_explicit_complete_dsf_field_order():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    built = _built(prepared, "explicit-field")
    settlement = authority.settle_l5(
        built.boundary, built.receipt_registry
    )
    record = settlement.as_record()
    for region in record["regions"]:
        for receptor in region["explicit_structural_field"]:
            histories = receptor["exact_D_M_R_U_C_P_B"]
            assert histories
            assert all(len(field_tuple) == 7 for field_tuple in histories)


def test_lifetime_history_is_bounded_and_contains_no_raw_media():
    authority = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY, history_capacity=8
    )
    prepared = authority.prepare_retinotopic_inputs(_frames())
    for index in range(20):
        current = authority.prepare_retinotopic_inputs(
            _frames(source_base_seconds=index * 5)
        )
        built = _built(
            current, f"visual-bounded-{index}", source_start=index * 5
        )
        authority.settle_l5(built.boundary, built.receipt_registry)
    encoded = authority.snapshot_encoded()
    assert authority.status()["history_count"] == 8
    assert len(encoded) < 2 * 1024 * 1024
    assert b"frame_b64" not in encoded
    assert b"pixels" not in encoded


def test_production_authority_retains_only_current_visual_settlement():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    for index in range(4):
        current = authority.prepare_retinotopic_inputs(
            _frames(source_base_seconds=index * 5)
        )
        built = _built(
            current, f"visual-current-only-{index}", source_start=index * 5
        )
        authority.settle_l5(built.boundary, built.receipt_registry)
    assert authority.status()["history_count"] == 1
