from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
from tools.isolated_coupled_binaural_cochlear_candidate import (
    COMPONENTS_PER_EAR,
    EAR_IDS,
    RECEPTOR_KINDS,
    CoupledBinauralCochlearAuthority,
)


KEY = b"isolated-coupled-binaural-candidate-test-key"


def _signal() -> np.ndarray:
    sample_count = OBSERVATION_HOP_SAMPLES * 8
    time = np.arange(sample_count) / REQUIRED_SAMPLE_RATE_HZ
    return (
        0.3
        * (
            0.55
            + 0.4 * np.sin(2.0 * np.pi * 5.0 * time)
        )
        * np.sin(2.0 * np.pi * 440.0 * time)
    )


def _build_ear(authority, capture, ear_id):
    inputs = authority.mount_ear_l0_l4_inputs(
        capture,
        ear_id=ear_id,
        source_anchor=Fraction(0),
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"isolated-coupled-binaural-{ear_id}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(
            len(_signal()), REQUIRED_SAMPLE_RATE_HZ
        ),
        observed_substreams={PhysicalSense.SOUND: inputs},
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
    return inputs, built, sound


def test_two_bounded_ears_retain_all_receptors_and_full_l0_l4_fields():
    authority = CoupledBinauralCochlearAuthority(authority_key=KEY)
    capture = authority.transduce(
        _signal(),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )

    authority.verify_topology(authority.topology)
    authority.verify_capture(capture)
    assert len(authority.topology.vertex_ids) == 32
    assert len(authority.topology.neighbor_edges) == 30
    assert len(authority.topology.interaural_edges) == 16
    assert len(capture.fields) == 32
    assert {
        value.ear_id for value in capture.fields
    } == set(EAR_IDS)
    assert all(value.envelope for value in capture.fields)

    support_receipts = []
    for ear_id in EAR_IDS:
        inputs, built, sound = _build_ear(
            authority, capture, ear_id
        )
        assert len(inputs) == COMPONENTS_PER_EAR == 64
        assert len(sound.substreams) == COMPONENTS_PER_EAR
        assert {
            coordinate.coordinate_id
            for value in inputs
            for coordinate in value.coordinates
            if coordinate.axis_id == "receptor-kind"
        } == set(RECEPTOR_KINDS)
        for substream in sound.substreams:
            substream.verify(built.receipt_registry)
            support_receipts.append(
                substream.kernel_basin.authority_receipt_sha256
            )
            assert substream.kernel_basin.exact_dsf_field_tuples
            assert all(
                tuple(
                    getattr(field, name)
                    for name in DSF_FIELD_ORDER
                )
                == field.as_tuple()
                and all(
                    isinstance(getattr(field, name), Fraction)
                    for name in DSF_FIELD_ORDER
                )
                for field in (
                    substream.kernel_basin.exact_dsf_field_tuples
                )
            )
    assert len(set(support_receipts)) == 128


def test_candidate_rejects_unbounded_input_and_altered_authority():
    authority = CoupledBinauralCochlearAuthority(authority_key=KEY)
    with pytest.raises(ValueError, match="16 kHz"):
        authority.transduce(_signal(), sample_rate_hz=8_000)
    changed = _signal().copy()
    changed[0] = 1.1
    with pytest.raises(ValueError, match="bounded custody"):
        authority.transduce(
            changed,
            sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        )

    capture = authority.transduce(
        _signal(),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    with pytest.raises(ValueError, match="authority changed"):
        authority.verify_capture(replace(
            capture,
            authority_hmac_sha256="0" * 64,
        ))
    with pytest.raises(ValueError, match="topology authority changed"):
        authority.verify_topology(replace(
            authority.topology,
            authority_hmac_sha256="0" * 64,
        ))
