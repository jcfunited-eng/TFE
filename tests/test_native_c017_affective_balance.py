"""C-017 bounded physical affective-balance evidence transport."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production


def _transfer(source: str, target: str, carriers: int):
    return (source, target, 0, carriers)


def _gradient(ordinal: int):
    return (ordinal, -5, -3, -4, 2, 2, 0, (11, 2), (13, 2), (1, 1))


def test_same_interval_recovery_is_not_a_later_consequence() -> None:
    lineage = "10" * 16
    observed = (
        lineage,
        10,
        4,
        (7, _transfer("07" * 16, lineage, 3)),
        (7, _transfer("08" * 16, lineage, 2)),
        _gradient(7),
    )

    retained = production._advance_bounded_affective_balance_evidence(
        (), {"affective_balance_trajectories": (observed,)}
    )

    assert retained[0][3:5] == observed[3:5]
    assert retained[0][5] is None


def test_later_local_recovery_completes_one_bounded_cell_trajectory() -> None:
    lineage = "10" * 16
    influence = (
        lineage,
        10,
        4,
        (7, _transfer("07" * 16, lineage, 3)),
        (8, _transfer("08" * 16, lineage, 2)),
        None,
    )
    recovery = (lineage, 10, 4, None, None, _gradient(9))

    retained = production._advance_bounded_affective_balance_evidence(
        (), {"affective_balance_trajectories": (influence,)}
    )
    retained = production._advance_bounded_affective_balance_evidence(
        retained, {"affective_balance_trajectories": (recovery,)}
    )

    assert retained == ((
        lineage,
        10,
        4,
        influence[3],
        influence[4],
        recovery[5],
    ),)
