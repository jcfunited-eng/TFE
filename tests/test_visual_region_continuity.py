from fractions import Fraction
from io import BytesIO

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


KEY = b"visual-region-test-authority-key-32-bytes-minimum"


def _frames(*, shifted=False):
    result = []
    for index in range(4):
        pixels = np.zeros((64, 64), dtype=np.uint8)
        left = 8 if shifted else 0
        pixels[16:32, left : left + 16] = 40 + index * 20
        pixels[40:56, 40:56] = 180 - index * 10
        result.append(
            CanonicalVisualFrame.from_uint8(
                (index + 1) * 1_000_000_000, pixels
            )
        )
    return tuple(result)


def _built(prepared, assembly_id):
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
        source_time_start=Fraction(0),
        source_time_end=Fraction(5),
        observed_substreams={PhysicalSense.SIGHT: prepared.substreams},
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


def test_l5_reads_full_field_and_static_scene_has_unique_continuity():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    first_built = _built(prepared, "visual-first")
    first = authority.settle_l5(
        first_built.boundary, first_built.receipt_registry
    )
    authority.verify_settlement(first)
    assert sum(len(value.receptor_indices) for value in first.regions) == 64
    assert {value.continuity for value in first.regions} == {"unknown"}

    second_built = _built(prepared, "visual-second")
    second = authority.settle_l5(
        second_built.boundary, second_built.receipt_registry
    )
    authority.verify_settlement(second)
    assert {value.continuity for value in second.regions} == {"unique"}
    assert tuple(
        value.lineage_receipt_sha256 for value in second.regions
    ) == tuple(value.lineage_receipt_sha256 for value in first.regions)


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
    assert restored.snapshot_encoded() == encoded

    changed = bytearray(encoded)
    changed[len(changed) // 2] ^= 1
    with pytest.raises(ValueError):
        restored.restore_encoded(bytes(changed))
    assert restored.snapshot_encoded() == encoded


def test_shifted_scene_never_inherits_without_unique_exact_overlap():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    first_prepared = authority.prepare_retinotopic_inputs(_frames())
    first_built = _built(first_prepared, "visual-origin")
    authority.settle_l5(first_built.boundary, first_built.receipt_registry)

    shifted_prepared = authority.prepare_retinotopic_inputs(_frames(shifted=True))
    shifted_built = _built(shifted_prepared, "visual-shifted")
    shifted = authority.settle_l5(
        shifted_built.boundary, shifted_built.receipt_registry
    )
    assert all(value.continuity in {"unknown", "unique"} for value in shifted.regions)
    authority.verify_settlement(shifted)


def test_lifetime_history_is_bounded_and_contains_no_raw_media():
    authority = DeterministicVisualRegionContinuityAuthority(
        authority_key=KEY, history_capacity=8
    )
    prepared = authority.prepare_retinotopic_inputs(_frames())
    built = _built(prepared, "visual-bounded")
    for _ in range(20):
        authority.settle_l5(built.boundary, built.receipt_registry)
    encoded = authority.snapshot_encoded()
    assert authority.status()["history_count"] == 8
    assert len(encoded) < 2 * 1024 * 1024
    assert b"frame_b64" not in encoded
    assert b"pixels" not in encoded


def test_production_authority_retains_only_current_visual_settlement():
    authority = DeterministicVisualRegionContinuityAuthority(authority_key=KEY)
    prepared = authority.prepare_retinotopic_inputs(_frames())
    built = _built(prepared, "visual-current-only")
    for _ in range(4):
        authority.settle_l5(built.boundary, built.receipt_registry)
    assert authority.status()["history_count"] == 1
