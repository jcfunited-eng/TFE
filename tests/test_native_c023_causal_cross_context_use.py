"""C-023 exact internally reassembled formation-to-later-action evidence."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production


class _FrontierObserver:
    def __init__(self) -> None:
        self.transfers: tuple[tuple[str, str, int, int, str], ...] = ()
        self.filters: list[tuple[str, ...]] = []

    def observe_active_electrical_frontier_advances_from(
        self, lineages: tuple[str, ...]
    ) -> tuple[tuple[str, str, int, int, str], ...]:
        self.filters.append(lineages)
        return tuple(
            transfer
            for transfer in self.transfers
            if (transfer[1] if transfer[4] == transfer[0] else transfer[0]) in lineages
        )


def _hop(
    predecessor_tick: int,
    *,
    cues: tuple[tuple[str, tuple[str, ...]], ...] = (),
    motors: tuple[
        tuple[str, int, int, tuple[object, ...], tuple[object, ...]], ...
    ] = (),
) -> dict[str, object]:
    return {
        "predecessor_organism_tick": predecessor_tick,
        "organism_tick": predecessor_tick + 1,
        "internally_reassembled_formation_cues": cues,
        "motor_unit_recruitments": motors,
    }


def test_exact_changed_endpoint_path_reaches_a_motor_only_on_a_later_interval() -> None:
    cue = "01" * 16
    integration = "02" * 16
    association = "03" * 16
    motor = "04" * 16
    receipt = "11" * 32
    first = (integration, cue, 0, 745)
    second = (association, integration, 0, 660)
    third = (association, motor, 0, 67)
    observer = _FrontierObserver()
    active = {}
    proof = None

    observer.transfers = ((*first, integration),)
    active, proof = production._advance_internal_formation_motor_trace(
        observer,
        active,
        proof,
        _hop(10, cues=((receipt, (cue,)),)),
    )
    assert proof is None

    observer.transfers = ((*second, association),)
    active, proof = production._advance_internal_formation_motor_trace(
        observer,
        active,
        proof,
        _hop(11),
    )
    assert proof is None

    observer.transfers = ()
    active, proof = production._advance_internal_formation_motor_trace(
        observer,
        active,
        proof,
        _hop(
            12,
            motors=(
                (
                    motor,
                    7,
                    21,
                    ((association, 11, motor, 12, 0, 67),),
                    (),
                ),
            ),
        ),
    )

    assert proof is not None
    assert proof["formation_receipt_sha256"] == receipt
    assert proof["internal_cue_lineages"] == (cue,)
    assert proof["recurrence_organism_tick"] == 11
    assert proof["motor_organism_tick"] == 13
    assert proof["directed_physical_transfers"] == (first, second, third)
    assert proof["motor_unit_recruitment"]["motor_lineage"] == motor
    assert len(observer.filters) == 3


def test_multi_interval_hop_refuses_to_invent_unobserved_causal_boundaries() -> None:
    observer = _FrontierObserver()
    active, proof = production._advance_internal_formation_motor_trace(
        observer,
        {},
        None,
        {
            "predecessor_organism_tick": 20,
            "organism_tick": 22,
            "internally_reassembled_formation_cues": (
                ("11" * 32, ("01" * 16,)),
            ),
            "motor_unit_recruitments": (("02" * 16, 1, 1, (), ()),),
        },
    )

    assert active == {}
    assert proof is None
    assert observer.filters == []
