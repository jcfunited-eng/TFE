from __future__ import annotations

import importlib
import json
import math
import struct
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


KEY = b"auditory-bilateral-nonflattening-contract-key"
SAMPLE_COUNT = 960
LAYERS = (
    "L0_SEV",
    "L1_GateL1State",
    "L2_GateInterpretation",
    "L3_ResonanceResult",
    "L4_DSF",
)
_CONTRACT_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "auditory_bilateral_nonflattening_contract_v1.json"
)
_PENDING_REASON = (
    "fail-first: transaction-level bilateral L0-L4 inquiry authority is "
    "intentionally absent until loss localization proves the operator"
)


def _source(frequency: int) -> bytes:
    values = tuple(
        4 * int(
            1_500 * math.sin(
                2.0 * math.pi * frequency * index / 16_000
            )
        )
        for index in range(SAMPLE_COUNT)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _mount_pair(left_pcm: bytes, right_pcm: bytes):
    sample_count = len(left_pcm) // 2
    assert len(right_pcm) // 2 == sample_count
    inputs = (
        *binaural_sound_field_inputs(
            ear="left",
            topology_index=0,
            pcm=left_pcm,
            source_time_start=Fraction(0),
        ),
        *binaural_sound_field_inputs(
            ear="right",
            topology_index=32,
            pcm=right_pcm,
            source_time_start=Fraction(0),
        ),
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id="auditory-bilateral-nonflattening-contract",
        source_time_start=Fraction(0),
        source_time_end=Fraction(sample_count, 16_000),
        observed_substreams={PhysicalSense.SOUND: inputs}, occurrences=joint_occurrences_for({PhysicalSense.SOUND: inputs}),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    built.verify_construction()
    sound = next(
        value
        for value in built.boundary.boundaries
        if value.sense is PhysicalSense.SOUND
    )
    assert len(sound.substreams) == 64
    return built, sound


def _layer_records(built, sound) -> tuple[tuple[dict, dict], ...]:
    records = []
    for index in range(32):
        pair = []
        for substream in (
            sound.substreams[index],
            sound.substreams[32 + index],
        ):
            encoded = built.receipt_registry.resolve(
                substream.l0_l4_trace_receipt_sha256,
                "bilateral L0-L4 trace",
            )
            pair.append(json.loads(encoded.decode("utf-8")))
        records.append((pair[0], pair[1]))
    return tuple(records)


def _candidate_asymmetry():
    authority = PhysicalStereoAuditAuthority(authority_key=KEY)
    capture = authority.render(
        (_source(440),),
        source_ordinals=(0,),
    )
    built, sound = _mount_pair(
        capture.left_pcm_s16le,
        capture.right_pcm_s16le,
    )
    return authority, capture, built, sound


def _pending_auditor():
    return importlib.import_module(
        "dsf_ai_service.glew_runtime.auditory_bilateral_nonflattening"
    )


def test_identical_physical_inputs_do_not_invent_layer_differences() -> None:
    pcm = _source(440)
    built, sound = _mount_pair(pcm, pcm)
    for left, right in _layer_records(built, sound):
        assert all(left[layer] == right[layer] for layer in LAYERS)


def test_current_physical_asymmetry_layer_loss_baseline_is_exact() -> None:
    _authority, capture, built, sound = _candidate_asymmetry()
    assert capture.left_pcm_s16le != capture.right_pcm_s16le
    pairs = _layer_records(built, sound)
    actual = {
        layer: sum(left[layer] != right[layer] for left, right in pairs)
        for layer in LAYERS
    }
    contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert actual == contract[
        "current_asymmetric_layer_difference_counts"
    ]


@pytest.mark.xfail(strict=True, reason=_PENDING_REASON)
def test_symmetry_equality_opens_a_traced_investigation() -> None:
    pcm = _source(440)
    built, sound = _mount_pair(pcm, pcm)
    audit = _pending_auditor().audit_bilateral_l0_l4(
        left_right_input_equal=True,
        calibration_equal=True,
        quiescent=False,
        topology_receipt_sha256=sound.topology.authority_receipt_sha256,
        trace_pairs=_layer_records(built, sound),
        exact_collapse_receipts=(),
    )
    assert all(
        value.disposition == "symmetry_conserved"
        and value.explanation_receipt_sha256
        for value in audit.layers
    )


@pytest.mark.xfail(strict=True, reason=_PENDING_REASON)
def test_every_asymmetric_layer_collapse_requires_exact_accounting() -> None:
    _authority, _capture, built, sound = _candidate_asymmetry()
    audit = _pending_auditor().audit_bilateral_l0_l4(
        left_right_input_equal=False,
        calibration_equal=False,
        quiescent=False,
        topology_receipt_sha256=sound.topology.authority_receipt_sha256,
        trace_pairs=_layer_records(built, sound),
        exact_collapse_receipts=(),
    )
    audit.verify()
    assert all(
        value.disposition == "difference_preserved"
        or (
            value.disposition == "declared_exact_collapse"
            and value.explanation_receipt_sha256
        )
        for value in audit.layers
    )


@pytest.mark.xfail(strict=True, reason=_PENDING_REASON)
def test_unexplained_asymmetric_equality_fails_closed() -> None:
    _authority, _capture, built, sound = _candidate_asymmetry()
    with pytest.raises(
        ValueError,
        match="unexplained bilateral equality",
    ):
        _pending_auditor().audit_bilateral_l0_l4(
            left_right_input_equal=False,
            calibration_equal=False,
            quiescent=False,
            topology_receipt_sha256=(
                sound.topology.authority_receipt_sha256
            ),
            trace_pairs=_layer_records(built, sound),
            exact_collapse_receipts=(),
        )


@pytest.mark.xfail(strict=True, reason=_PENDING_REASON)
def test_bilateral_topology_is_bound_into_every_layer_audit() -> None:
    authority, capture, built, sound = _candidate_asymmetry()
    brainstem = authority.compare_brainstem(capture)
    left = tuple(
        value.kernel_basin.authority_receipt_sha256
        for value in sound.substreams[:32]
    )
    right = tuple(
        value.kernel_basin.authority_receipt_sha256
        for value in sound.substreams[32:]
    )
    assembly = authority.assemble_bilateral(
        left_ear_port_receipt_sha256s=left,
        right_ear_port_receipt_sha256s=right,
        brainstem=brainstem,
    )
    audit = _pending_auditor().audit_bilateral_l0_l4(
        left_right_input_equal=False,
        calibration_equal=False,
        quiescent=False,
        topology_receipt_sha256=sound.topology.authority_receipt_sha256,
        trace_pairs=_layer_records(built, sound),
        exact_collapse_receipts=(),
        bilateral_assembly=assembly,
    )
    assert all(
        value.topology_receipt_sha256
        == sound.topology.authority_receipt_sha256
        for value in audit.layers
    )


@pytest.mark.xfail(strict=True, reason=_PENDING_REASON)
def test_static_quiescent_equality_receives_legitimate_explanation() -> None:
    silence = bytes(SAMPLE_COUNT * 2)
    built, sound = _mount_pair(silence, silence)
    audit = _pending_auditor().audit_bilateral_l0_l4(
        left_right_input_equal=True,
        calibration_equal=True,
        quiescent=True,
        topology_receipt_sha256=sound.topology.authority_receipt_sha256,
        trace_pairs=_layer_records(built, sound),
        exact_collapse_receipts=(),
    )
    assert all(
        value.disposition == "static_quiescent_equal"
        and value.explanation_receipt_sha256
        for value in audit.layers
    )
