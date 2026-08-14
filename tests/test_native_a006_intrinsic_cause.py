"""A-006 exact new-impression-to-later-action causal observation."""

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
            if (transfer[1] if transfer[4] == transfer[0] else transfer[0])
            in lineages
        )


def _hop(
    predecessor_tick: int,
    *,
    emitted: tuple[str, ...] = (),
    cues: tuple[tuple[str, tuple[str, ...]], ...] = (),
    motors: tuple[tuple[str, int, int, tuple[object, ...]], ...] = (),
) -> dict[str, object]:
    return {
        "predecessor_organism_tick": predecessor_tick,
        "organism_tick": predecessor_tick + 1,
        "emitted_neuron_fractals": tuple(
            {"neuron_lineage": lineage} for lineage in emitted
        ),
        "internally_reassembled_formation_cues": cues,
        "motor_unit_recruitments": motors,
    }


def test_new_impression_advances_only_after_formation_then_reaches_motor() -> None:
    impression = "01" * 16
    association = "02" * 16
    motor = "03" * 16
    observer = _FrontierObserver()
    active = {}
    completed = {}

    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(10, emitted=(impression,)),
    )
    assert completed == {}
    assert observer.filters == []

    first = (association, impression, 0, 29)
    observer.transfers = ((*first, association),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(11),
    )
    assert completed == {}

    second = (association, motor, 0, 7)
    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            12,
            motors=((motor, 4, 7, ((association, 11, motor, 12, 0, 7),)),),
        ),
    )

    proof = completed["new_neuronal_fractal"]
    assert proof["emitted_neuron_lineages"] == (impression,)
    assert proof["impression_organism_tick"] == 11
    assert proof["motor_organism_tick"] == 13
    assert proof["directed_physical_transfers"] == (first, second)
    assert proof["motor_unit_recruitment"]["motor_lineage"] == motor
    assert observer.filters == [(impression,), (association,)]


def test_new_and_recurrent_roots_share_one_frontier_query_per_hop() -> None:
    impression = "01" * 16
    cue = "02" * 16
    observer = _FrontierObserver()
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(20, emitted=(impression,)),
    )

    observer.transfers = ()
    production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(21, cues=(("11" * 32, (cue,)),)),
    )

    assert observer.filters == [(impression, cue)]
