from __future__ import annotations

from fractions import Fraction

from tools.probe_auditory_full_field_separability_census import (
    CorpusItem,
)
from tools.probe_auditory_layer_information_loss import (
    QUOTIENTS,
    _digest,
    _evaluate,
    _relation,
    _signature,
)


def _item(name: str, command: str, ordinal: int) -> CorpusItem:
    return CorpusItem(
        item_id=_digest({"name": name}),
        oracle_command=command,
        speaker_id=f"speaker-{name}",
        archive_member=f"{command}/{name}.wav",
        pcm_sha256=_digest({"pcm": name}),
        split="reference",
        ordinal=ordinal,
    )


def test_exact_trajectory_and_local_alphabet_disclose_different_relations():
    first = {
        "pressure": (
            Fraction(1), Fraction(2), Fraction(4), Fraction(3)
        ),
        "regime": ("a", "b", "b", "a"),
    }
    scaled = {
        "pressure": (
            Fraction(9), Fraction(18), Fraction(36), Fraction(27)
        ),
        "regime": ("a", "b", "b", "a"),
    }
    changed = {
        "pressure": (
            Fraction(1), Fraction(2), Fraction(5), Fraction(3)
        ),
        "regime": ("a", "b", "b", "a"),
    }

    exact_first = _signature("L4_DSF", QUOTIENTS[0], first)
    exact_scaled = _signature("L4_DSF", QUOTIENTS[0], scaled)
    exact_changed = _signature("L4_DSF", QUOTIENTS[0], changed)
    local_first = _signature("L4_DSF", QUOTIENTS[1], first)
    local_changed = _signature("L4_DSF", QUOTIENTS[1], changed)

    assert _relation(
        exact_first, exact_scaled
    )["joint_relation_locked"] is True
    assert _relation(
        exact_first, exact_changed
    )["joint_relation_locked"] is False
    assert _relation(
        local_first, local_changed
    )["joint_relation_locked"] is True


def test_oracle_labels_enter_only_after_complete_relations():
    items = (
        _item("a", "yes", 0),
        _item("b", "yes", 1),
        _item("c", "no", 2),
    )
    partitions = {
        items[0].item_id: {"x": (Fraction(1), Fraction(2))},
        items[1].item_id: {"x": (Fraction(7), Fraction(14))},
        items[2].item_id: {"x": (Fraction(1), Fraction(-2))},
    }
    signatures = {
        item.item_id: _signature(
            "raw_pcm", QUOTIENTS[0], partitions[item.item_id]
        )
        for item in items
    }

    evaluation = _evaluate(items=items, signatures=signatures)

    assert evaluation["within_command_locked_pairs"] == 1
    assert evaluation["cross_command_locked_pairs"] == 0
    assert len(evaluation["matrix"]) == len(items)
    assert all(
        "yes" not in str(relation) and "no" not in str(relation)
        for row in evaluation["matrix"]
        for relation in row
    )


def test_singleton_partition_is_preserved_without_inventing_transition():
    first = _signature(
        "L3_ResonanceResult",
        QUOTIENTS[1],
        {"state": (Fraction(3, 7),)},
    )
    same = _signature(
        "L3_ResonanceResult",
        QUOTIENTS[1],
        {"state": (Fraction(3, 7),)},
    )
    changed = _signature(
        "L3_ResonanceResult",
        QUOTIENTS[1],
        {"state": (Fraction(4, 7),)},
    )

    assert _relation(first, same)["joint_relation_locked"] is True
    assert _relation(first, changed)["joint_relation_locked"] is False
