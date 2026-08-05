from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from tools.probe_auditory_full_field_separability_census import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    CANDIDATE_SPECS,
    CorpusItem,
    ExactFrame,
    FullFieldExperience,
    _component_delta_gate,
    _component_state_ray,
    _component_temporal_order_gate,
    _digest,
    _neighborhood_order_gate,
    _neighborhood_ray_gate,
    _positive_scale_ray,
    _relation,
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
        for frame_index in range(3):
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


def test_positive_scale_ray_is_exact_and_preserves_orientation():
    source = (
        Fraction(-2, 3),
        Fraction(4, 5),
        Fraction(0),
        Fraction(7, 11),
    )
    scaled = tuple(Fraction(13, 7) * value for value in source)
    reversed_orientation = tuple(-value for value in source)

    assert _positive_scale_ray(source) == _positive_scale_ray(scaled)
    assert (
        _positive_scale_ray(source)
        != _positive_scale_ray(reversed_orientation)
    )


def test_candidate_relations_do_not_receive_oracle_labels():
    left = _experience(command="left", scale=1, item_name="left-a")
    right = _experience(command="stop", scale=9, item_name="stop-b")

    left_tokens = _component_state_ray(left)
    right_tokens = _component_state_ray(right)
    relation = _relation(
        left_tokens.candidate_id,
        left.item.item_id,
        right.item.item_id,
        left_tokens,
        right_tokens,
    )

    assert relation["relation_locked"] is True
    assert "left" not in relation
    assert "stop" not in relation
    assert (
        left_tokens.token_set_root_sha256
        == right_tokens.token_set_root_sha256
    )


def test_every_candidate_retains_complete_full_field_witness_roots():
    experience = _experience(
        command="yes",
        scale=1,
        item_name="yes-a",
    )
    tokenizers = (
        _component_state_ray,
        _component_delta_gate,
        _component_temporal_order_gate,
        _neighborhood_ray_gate,
        _neighborhood_order_gate,
    )

    for tokenize in tokenizers:
        result = tokenize(experience)
        result.verify(experience)
        assert result.token_sha256s
        assert all(
            token in result.token_sha256s
            for token, _witness in result.token_witness_roots
        )
        assert all(
            len(witness) == 64
            for _token, witness in result.token_witness_roots
        )


def test_candidate_specs_disclose_every_exact_quotient_loss():
    assert len(CANDIDATE_SPECS) == 5
    assert all(
        spec.quotient_loses
        and spec.quotient_invariance
        and spec.relation
        for spec in CANDIDATE_SPECS
    )
    assert all(
        spec.record()["full_fields_used"] == list(DSF_FIELD_ORDER)
        for spec in CANDIDATE_SPECS
    )
