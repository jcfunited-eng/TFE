from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from tools.probe_auditory_full_field_hierarchical_census import (
    SPECS,
    _component_field_order,
    _component_field_relation,
    _component_ray_gate,
    _component_ray_relation,
    _neighborhood_field_order,
    _neighborhood_relation,
)
from tools.probe_auditory_full_field_separability_census import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    CorpusItem,
    ExactFrame,
    FullFieldExperience,
    _digest,
    _root,
)


def _sha(name: str) -> str:
    return _digest({"name": name})


def _experience(
    *,
    command: str,
    scale: int,
    item_name: str,
) -> FullFieldExperience:
    components = []
    tuple_authorities = []
    tuple_supports = []
    for component_index in range(AUDITORY_KERNEL_COMPONENT_COUNT):
        frames = []
        for frame_index in range(4):
            values = tuple(
                Fraction(
                    scale
                    * (
                        (component_index + 1)
                        * (field_index + 2)
                        + frame_index * (field_index + 1)
                    )
                )
                for field_index in range(len(DSF_FIELD_ORDER))
            )
            support = _sha(
                f"{item_name}-support-{component_index}-{frame_index}"
            )
            authority = _sha(
                f"{item_name}-authority-{component_index}-{frame_index}"
            )
            tuple_supports.append(support)
            tuple_authorities.append(authority)
            frames.append(ExactFrame(
                fields=values,
                tuple_integrity_sha256=support,
                l4_tuple_authority_sha256=authority,
            ))
        components.append(tuple(frames))
    result = FullFieldExperience(
        item=CorpusItem(
            item_id=_sha(item_name),
            oracle_command=command,
            speaker_id=f"speaker-{item_name}",
            archive_member=f"{command}/{item_name}.wav",
            pcm_sha256=_sha(f"pcm-{item_name}"),
            split="held_out",
            ordinal=0,
        ),
        l4_support_integrity_sha256=_sha(
            f"{item_name}-full-support"
        ),
        component_integrity_sha256s=tuple(
            _sha(f"{item_name}-component-{index}")
            for index in range(AUDITORY_KERNEL_COMPONENT_COUNT)
        ),
        tuple_authority_root_sha256=_root(
            "guala.audit.l4_tuple_authority_root.v1",
            tuple_authorities,
        ),
        tuple_support_root_sha256=_root(
            "guala.audit.l4_tuple_support_root.v1",
            tuple_supports,
        ),
        frames_by_component=tuple(components),
    )
    result.verify()
    return result


def test_hierarchies_lock_exact_positive_scale_equivalents_without_labels():
    left = _experience(command="left", scale=1, item_name="left-a")
    right = _experience(command="stop", scale=9, item_name="stop-b")
    cases = (
        (
            _component_field_order,
            _component_field_relation,
        ),
        (
            _component_ray_gate,
            _component_ray_relation,
        ),
        (
            _neighborhood_field_order,
            _neighborhood_relation,
        ),
    )

    for tokenizer, relation_function in cases:
        left_signature = tokenizer(left)
        right_signature = tokenizer(right)
        relation = relation_function(
            left.item.item_id,
            right.item.item_id,
            left_signature,
            right_signature,
        )

        assert relation["relation_locked"] is True
        assert "left" not in relation
        assert "stop" not in relation
        assert all(
            left_partition.token_root_sha256
            == right_partition.token_root_sha256
            for left_partition, right_partition in zip(
                left_signature.partitions,
                right_signature.partitions,
                strict=True,
            )
        )


def test_hierarchies_retain_every_physical_partition_and_disclose_losses():
    experience = _experience(
        command="yes",
        scale=1,
        item_name="yes-a",
    )
    expected_partition_counts = {
        "component_field_order_b_c_hierarchy_v1": 224,
        "component_full_ray_b_c_partition_hierarchy_v1": 32,
        "neighborhood_field_order_b_c_hierarchy_v1": 196,
    }

    for spec in SPECS:
        signature = spec.tokenizer(experience)

        assert (
            len(signature.partitions)
            == expected_partition_counts[spec.candidate_id]
        )
        assert all(
            partition.token_sha256s
            and len(partition.token_root_sha256) == 64
            and len(partition.witness_root_sha256) == 64
            for partition in signature.partitions
        )
        assert spec.quotient_loses
        assert spec.record()["full_fields_used"] == list(DSF_FIELD_ORDER)
