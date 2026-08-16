"""Exact compact GLORUN/CURRENT checkpoint proof with no cognitive copy."""

from __future__ import annotations

import hashlib
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    NativeJointSourceOccurrenceInput,
    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.native_resident_organism import (
    create_native_resident_organism,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate import native_organism_binary_store as store


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
MAX_ENVELOPE_BYTES = 67_108_864
MAX_FABRIC_BYTES = 67_108_000
MAX_LOGICAL_PEAK_BYTES = 536_870_912


def _growth_dna_fixture():
    """Authored growth DNA: a four-receptor sight anatomy episode plus one
    seed group covering its ports as a chain with 500 pS contacts."""

    times = tuple(Fraction(index, 4) for index in range(4))

    def _substream(topology_index: int) -> NativeSensorySubstreamInput:
        return NativeSensorySubstreamInput(
            sense=PhysicalSense.SIGHT,
            sensor_id="sight-organ",
            substream_id=f"sight-{topology_index}",
            topology_index=topology_index,
            coordinates=(
                NativeAxisCoordinate("receptor", str(topology_index)),
            ),
            physical_quantity="normalized_physical_excitation",
            physical_unit="normalized_binary64",
            source_times=times,
            normalized_signal=(0.0, 0.5, -0.25, 1.0),
            phase_turns=(Fraction(0),) * 4,
        )

    observed = {
        PhysicalSense.SIGHT: tuple(_substream(index) for index in range(4)),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    episode = settle_native_joint_source_episode(
        assembly_id="growth-dna-anatomy",
        observed_substreams=observed,
        states=states,
        occurrences=(
            NativeJointSourceOccurrenceInput(
                port_indices=(0, 1, 2, 3),
                source_times=times,
                joint_intersample_profile_payload=(
                    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
                ),
                groups=((0, 1, 2, 3),),
                joint_relevance_profile_payload=(
                    b"guala.test.explicit_joint_relevance.v1"
                ),
                joint_relevance=(Fraction(1),) * 4,
            ),
        ),
    )
    port_count = episode.port_count
    seed_groups = [
        (
            list(range(port_count)),
            [(index - 1, index, 500) for index in range(1, port_count)],
        )
    ]
    return (episode, seed_groups)


class _ObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_if_absent(
        self,
        key: str,
        chunks,
        *,
        byte_count: int,
        sha256: str,
    ) -> bool:
        body = b"".join(chunks)
        assert len(body) == byte_count
        assert hashlib.sha256(body).hexdigest() == sha256
        prior = self.objects.setdefault(key, body)
        if prior != body:
            raise RuntimeError("immutable object collision")
        return prior is body

    def iter_bytes(self, key: str):
        yield self.objects[key]

    def delete_if_exact(
        self,
        key: str,
        *,
        byte_count: int,
        sha256: str,
    ) -> None:
        body = self.objects[key]
        assert len(body) == byte_count
        assert hashlib.sha256(body).hexdigest() == sha256
        del self.objects[key]


def _publish(root: Path):
    organism = create_native_resident_organism(
        organism_identity=IDENTITY,
        organism_tick=0,
        growth_dna=_growth_dna_fixture(),
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )
    staged = store.stage_active_native_organism(
        root,
        organism,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
    )
    remote = _ObjectStore()
    published = store.publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=None,
        object_store=remote,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )
    return organism, published, remote


def _restore(root: Path):
    return store.restore_current_native_organism(
        root,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
        max_fabric_bytes=MAX_FABRIC_BYTES,
        max_logical_peak_bytes=MAX_LOGICAL_PEAK_BYTES,
    )


def test_checkpoint_is_one_compact_exact_generation_and_fixed_current_pointer(
    tmp_path: Path,
) -> None:
    organism, published, remote = _publish(tmp_path)
    body = organism.save()
    digest = hashlib.sha256(body).hexdigest()
    generation = tmp_path / store.GENERATIONS_DIRECTORY / f"{digest}.glorun"
    current = tmp_path / store.CURRENT_NAME
    restored = _restore(tmp_path)

    assert body.startswith(store.STATE_MAGIC)
    stored = generation.read_bytes()
    assert stored.startswith(store.COMPACT_STATE_MAGIC)
    assert store._decode_stored_state(
        stored,
        expected_bytes=len(body),
        expected_sha256=digest,
        max_envelope_bytes=MAX_ENVELOPE_BYTES,
    ) == body
    assert current.read_bytes().startswith(store.CURRENT_MAGIC)
    assert current.stat().st_size == store.POINTER_BYTES
    assert published.pointer.state_sha256 == digest
    assert published.pointer.predecessor_state_sha256 is None
    assert restored.organism.save() == body
    assert restored.pointer == published.pointer
    assert remote.objects[published.remote_key] == stored
    assert not list(tmp_path.rglob("*.json"))
    assert not any("owner" in path.name.lower() for path in tmp_path.rglob("*"))
    assert not any("lock" in path.name.lower() for path in tmp_path.rglob("*"))


def test_tampered_current_body_halts_without_predecessor_fallback(
    tmp_path: Path,
) -> None:
    _organism, published, _remote = _publish(tmp_path)
    path = (
        tmp_path
        / store.GENERATIONS_DIRECTORY
        / f"{published.pointer.state_sha256}.glorun"
    )
    body = bytearray(path.read_bytes())
    body[-1] ^= 1
    path.write_bytes(body)

    with pytest.raises(
        store.NativeOrganismBinaryStoreError,
        match="compact state|not exact current GLORUN",
    ):
        _restore(tmp_path)
