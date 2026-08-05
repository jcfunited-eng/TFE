from __future__ import annotations

import io
import struct
import wave

from tools.probe_auditory_full_field_causal_recurrence import (
    MAX_EXPERIENCES_PER_GROUNDING,
    MAX_GROUNDINGS,
    RAW_SPEC,
    _grow_memories,
    _mix_wavs,
    _read_pcm_wav,
    _recurrent,
    _write_pcm_wav,
)
from tools.probe_auditory_full_field_hierarchical_census import (
    ExactPartition,
    HierarchicalSignature,
)
from tools.probe_auditory_full_field_separability_census import (
    CorpusItem,
    FullFieldExperience,
    _digest,
)


def _sha(name: str) -> str:
    return _digest({"name": name})


def _experience(
    *,
    grounding_index: int,
    experience_index: int,
) -> FullFieldExperience:
    name = f"g{grounding_index}-e{experience_index}"
    return FullFieldExperience(
        item=CorpusItem(
            item_id=_sha(name),
            oracle_command=f"oracle-{grounding_index}",
            speaker_id=f"speaker-{name}",
            archive_member=f"{name}.wav",
            pcm_sha256=_sha(f"pcm-{name}"),
            split="reference",
            ordinal=grounding_index * MAX_EXPERIENCES_PER_GROUNDING
            + experience_index,
        ),
        l4_support_integrity_sha256=_sha(f"support-{name}"),
        component_integrity_sha256s=(),
        tuple_authority_root_sha256=_sha(f"authority-{name}"),
        tuple_support_root_sha256=_sha(f"tuples-{name}"),
        frames_by_component=(),
    )


def _signature(
    *,
    experience: FullFieldExperience,
    grounding_index: int,
    experience_index: int,
) -> HierarchicalSignature:
    tokens = {
        _sha("shared"),
        _sha(f"noise-{grounding_index}-{experience_index}"),
    }
    if experience_index < 4:
        tokens.add(_sha(f"unique-{grounding_index}"))
    return HierarchicalSignature(
        candidate_id=RAW_SPEC.candidate_id,
        partitions=(
            ExactPartition(
                partition_id="component:0",
                token_sha256s=frozenset(tokens),
                token_root_sha256=_sha(f"token-root-{experience.item.item_id}"),
                witness_root_sha256=_sha(
                    f"witness-root-{experience.item.item_id}"
                ),
            ),
        ),
        quotient_receipt_sha256=_sha(
            f"quotient-{experience.item.item_id}"
        ),
    )


def test_recurrence_boundary_is_canonical_l6_not_a_tuned_threshold():
    token_a = _sha("a")
    token_b = _sha("b")
    token_sets = (
        frozenset((token_a, token_b)),
        frozenset((token_a, token_b)),
        frozenset((token_a, token_b)),
        frozenset((token_a,)),
        frozenset(),
    )

    assert _recurrent(token_sets) == {token_a}


def test_causal_fission_retains_shared_structure_without_identity_authority():
    groups = []
    signatures = {}
    for grounding_index in range(MAX_GROUNDINGS):
        group = []
        for experience_index in range(
            MAX_EXPERIENCES_PER_GROUNDING
        ):
            experience = _experience(
                grounding_index=grounding_index,
                experience_index=experience_index,
            )
            group.append(experience)
            signatures[experience.item.item_id] = _signature(
                experience=experience,
                grounding_index=grounding_index,
                experience_index=experience_index,
            )
        groups.append(tuple(group))

    memories = _grow_memories(
        spec=RAW_SPEC,
        reference_groups=tuple(groups),
        signatures=signatures,
    )

    assert len(memories) == MAX_GROUNDINGS
    for grounding_index, memory in enumerate(memories):
        record = memory.partition_records[0]
        assert record.recurrent_token_count == 2
        assert record.shared_token_count == 1
        assert record.identity_token_count == 1
        assert memory.signature.partitions[0].token_sha256s == {
            _sha(f"unique-{grounding_index}")
        }


def test_overlapping_sound_mix_is_exact_bounded_and_keeps_longer_tail():
    left = _write_pcm_wav((1000,) * 160)
    right = _write_pcm_wav((-200,) * 320)

    mixed = _mix_wavs(left, right)
    samples = _read_pcm_wav(mixed)

    assert len(samples) == 320
    assert samples[:160] == (400,) * 160
    assert samples[160:] == (-100,) * 160


def test_pcm_writer_emits_canonical_mono_sixteen_kilohertz_wav():
    data = _write_pcm_wav((0,) * 160)

    with wave.open(io.BytesIO(data), "rb") as source:
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert source.getframerate() == 16_000
        assert source.getnframes() == 160
        assert source.readframes(160) == struct.pack("<160h", *((0,) * 160))
