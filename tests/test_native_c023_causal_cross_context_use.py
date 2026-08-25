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

    def __iter__(self):
        return iter(self.transfers)


def test_post_publication_observer_failure_cannot_reject_or_change_prior_witness() -> None:
    recurrent = "05" * 16
    prior_key = ("retained_formation", "11" * 32, ("01" * 16,), 9)
    prior = {prior_key: {recurrent: ()}}
    malformed = _hop(
        10,
        cues=(("22" * 32, ("02" * 16,), recurrent),),
    )

    active, completed, error = (
        production._derive_causal_motor_observation_after_publication(
            prior,
            ((malformed, ()),),
        )
    )

    assert active == prior
    assert completed == {}
    assert error is not None
    assert error.startswith("RuntimeError:")


def _hop(
    predecessor_tick: int,
    *,
    cues: tuple[tuple[str, tuple[str, ...], str | None], ...] = (),
    external_reassemblies: tuple[
        tuple[str, tuple[str, ...], str], ...
    ] = (),
    motors: tuple[
        tuple[str, int, int, tuple[object, ...], tuple[object, ...]], ...
    ] = (),
    articulations: tuple[
        tuple[str, int, int, tuple[object, ...]], ...
    ] = (),
) -> dict[str, object]:
    return {
        "predecessor_organism_tick": predecessor_tick,
        "organism_tick": predecessor_tick + 1,
        "internally_reassembled_formation_cues": cues,
        "externally_reassembled_formation_frontiers": external_reassemblies,
        "motor_unit_recruitments": motors,
        "articulatory_unit_recruitments": articulations,
    }


def test_exact_changed_endpoint_path_reaches_a_motor_only_on_a_later_interval() -> None:
    cue = "01" * 16
    recurrent = "05" * 16
    integration = "02" * 16
    association = "03" * 16
    motor = "04" * 16
    receipt = "11" * 32
    first = (integration, recurrent, 0, 745)
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
        _hop(10, cues=((receipt, (cue,), recurrent),)),
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
                ("11" * 32, ("01" * 16,), "01" * 16),
            ),
            "motor_unit_recruitments": (("02" * 16, 1, 1, (), ()),),
        },
    )

    assert active == {}
    assert proof is None


def test_causal_trace_preserves_a_lawful_return_to_its_origin() -> None:
    origin = "01" * 16
    frontier = "02" * 16
    observer = _FrontierObserver()

    observer.transfers = ((origin, frontier, 0, 7, frontier),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(30, cues=(("11" * 32, (origin,), origin),)),
    )
    assert completed == {}

    observer.transfers = ((frontier, origin, 0, 9, origin),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(31),
    )

    assert active == {
        ("retained_formation", "11" * 32, (origin,), 31): {
            origin: (
                (origin, frontier, 0, 7),
                (frontier, origin, 0, 9),
            )
        }
    }
    assert completed == {}


def test_exact_recurrent_return_begins_the_next_causal_motor_path() -> None:
    cue = "01" * 16
    recurrent = "02" * 16
    ordering = "03" * 16
    motor = "04" * 16
    receipt = "11" * 32
    recurrent_return = (cue, recurrent, 0, 9)
    recurrent_to_ordering = (recurrent, ordering, 0, 7)
    ordering_to_motor = (ordering, motor, 0, 5)
    observer = _FrontierObserver()

    observer.transfers = ((*recurrent_return, recurrent),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(40, cues=((receipt, (cue,), recurrent),)),
    )
    assert completed == {}
    assert active == {
        ("retained_formation", receipt, (cue,), 41): {
            recurrent: (recurrent_return,)
        }
    }

    observer.transfers = ((*recurrent_to_ordering, ordering),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(41),
    )
    assert completed == {}

    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            42,
            motors=(
                (
                    motor,
                    7,
                    5,
                    ((ordering, 11, motor, 12, 0, 5),),
                    (),
                ),
            ),
        ),
    )

    assert active == {}
    proof = completed["retained_formation"]
    assert proof["formation_receipt_sha256"] == receipt
    assert proof["recurrence_organism_tick"] == 41
    assert proof["motor_organism_tick"] == 43
    assert proof["directed_physical_transfers"] == (
        recurrent_return,
        recurrent_to_ordering,
        ordering_to_motor,
    )


def test_retained_path_reaches_layer_13_without_false_body_motor_proof() -> None:
    cue = "01" * 16
    association = "02" * 16
    motor = "03" * 16
    articulation = "04" * 16
    receipt = "11" * 32
    first = (association, cue, 0, 29)
    motor_transfer = (association, motor, 0, 7)
    articulation_transfer = (motor, articulation, 0, 5)
    observer = _FrontierObserver()

    observer.transfers = ((*first, association),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(40, cues=((receipt, (cue,), cue),)),
    )
    assert completed == {}

    observer.transfers = ((*motor_transfer, motor),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(41),
    )
    assert completed == {}

    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            42,
            articulations=(
                (
                    articulation,
                    6,
                    5,
                    ((motor, 12, articulation, 13, 0, 5),),
                ),
            ),
        ),
    )

    assert "retained_formation" not in completed
    proof = completed["retained_formation_articulation"]
    assert proof["formation_receipt_sha256"] == receipt
    assert proof["recurrence_organism_tick"] == 41
    assert proof["articulation_organism_tick"] == 43
    assert proof["directed_physical_transfers"] == (
        first,
        motor_transfer,
        articulation_transfer,
    )
    assert proof["articulatory_unit_recruitment"] == {
        "articulatory_lineage": articulation,
        "articulatory_layer": 13,
        "articulatory_topology_index": 6,
        "outward_elementary_carriers": 5,
        "matched_preparation_transfer": (
            motor,
            12,
            articulation,
            13,
            0,
            5,
        ),
    }
    assert active == {}


def test_articulation_without_exact_layer_12_path_is_not_causal_proof() -> None:
    cue = "01" * 16
    unrelated_motor = "03" * 16
    articulation = "04" * 16
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(50, cues=(("11" * 32, (cue,), cue),)),
    )
    observer.transfers = ()
    _active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            51,
            articulations=(
                (
                    articulation,
                    6,
                    5,
                    ((unrelated_motor, 12, articulation, 13, 0, 5),),
                ),
            ),
        ),
    )

    assert "retained_formation_articulation" not in completed


def test_external_partial_cue_reassembly_reaches_later_articulation_from_its_recurrent_frontier() -> None:
    cue = "01" * 16
    recurrent = "02" * 16
    motor = "03" * 16
    articulation = "04" * 16
    receipt = "11" * 32
    recurrent_to_motor = (recurrent, motor, 0, 7)
    motor_to_articulation = (motor, articulation, 0, 5)
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(
            60,
            external_reassemblies=((receipt, (cue,), recurrent),),
        ),
    )
    assert completed == {}
    active = production._retain_cross_intake_causal_motor_traces(active)

    observer.transfers = ((*recurrent_to_motor, motor),)
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(61),
    )
    assert completed == {}
    active = production._retain_cross_intake_causal_motor_traces(active)

    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            62,
            articulations=(
                (
                    articulation,
                    6,
                    5,
                    ((motor, 12, articulation, 13, 0, 5),),
                ),
            ),
        ),
    )

    proof = completed[
        "externally_reassembled_retained_formation_articulation"
    ]
    assert proof["formation_receipt_sha256"] == receipt
    assert proof["external_cue_lineages"] == (cue,)
    assert proof["recurrent_lineage"] == recurrent
    assert proof["reassembly_organism_tick"] == 61
    assert proof["articulation_organism_tick"] == 63
    assert proof["directed_physical_transfers"] == (
        recurrent_to_motor,
        motor_to_articulation,
    )
    assert active == {}


def test_one_completed_formation_does_not_hide_a_second_later_motor_path() -> None:
    cue_a = "01" * 16
    cue_b = "02" * 16
    recurrent_a = "03" * 16
    recurrent_b = "04" * 16
    association_a = "05" * 16
    association_b = "06" * 16
    later_b = "07" * 16
    motor_a = "08" * 16
    motor_b = "09" * 16
    receipt_a = "11" * 32
    receipt_b = "22" * 32
    receipt_b_alternate = "33" * 32
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(
            80,
            external_reassemblies=(
                (receipt_a, (cue_a,), recurrent_a),
                (receipt_b, (cue_b,), recurrent_b),
                (receipt_b_alternate, (cue_b,), recurrent_b),
            ),
        ),
    )
    observer.transfers = (
        (recurrent_a, association_a, 0, 7, association_a),
        (recurrent_b, association_b, 0, 9, association_b),
    )
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(81),
    )

    observer.transfers = (
        (association_b, later_b, 0, 11, later_b),
    )
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            82,
            motors=(
                (
                    motor_a,
                    1,
                    5,
                    ((association_a, 11, motor_a, 12, 0, 5),),
                    (),
                ),
            ),
        ),
    )
    assert completed[
        "externally_reassembled_retained_formation"
    ]["recurrent_lineage"] == recurrent_a
    assert {key[2][0] for key in active} == {recurrent_b}

    observer.transfers = ()
    active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            83,
            motors=(
                (
                    motor_b,
                    2,
                    3,
                    ((later_b, 11, motor_b, 12, 0, 3),),
                    (),
                ),
            ),
        ),
    )

    all_paths = production._compact_completed_external_retained_motor_paths(
        completed,
    )
    assert tuple(path["recurrent_lineage"] for path in all_paths) == (
        recurrent_a,
        recurrent_b,
    )
    assert tuple(path["motor_organism_tick"] for path in all_paths) == (83, 84)
    assert active == {}


def test_external_reassembly_does_not_bind_an_unrelated_articulatory_path() -> None:
    cue = "01" * 16
    recurrent = "02" * 16
    unrelated_motor = "03" * 16
    articulation = "04" * 16
    observer = _FrontierObserver()

    active, completed = production._advance_causal_motor_traces(
        observer,
        {},
        {},
        _hop(
            70,
            external_reassemblies=(("11" * 32, (cue,), recurrent),),
        ),
    )
    _active, completed = production._advance_causal_motor_traces(
        observer,
        active,
        completed,
        _hop(
            71,
            articulations=(
                (
                    articulation,
                    6,
                    5,
                    ((unrelated_motor, 12, articulation, 13, 0, 5),),
                ),
            ),
        ),
    )

    assert (
        "externally_reassembled_retained_formation_articulation"
        not in completed
    )


def test_only_exact_cross_context_causes_cross_an_intake_boundary() -> None:
    paths = {"02" * 16: (("01" * 16, "02" * 16, 0, 7),)}
    active = {
        ("external_participant_sensory", "11" * 32, ("01" * 16,), 10): paths,
        (
            "externally_reassembled_retained_formation",
            "22" * 32,
            ("02" * 16, "03" * 16),
            11,
        ): paths,
        ("retained_formation", "33" * 32, ("04" * 16,), 12): paths,
        ("retained_formation", "34" * 32, ("07" * 16,), 15): paths,
        ("new_neuronal_fractal", "", ("05" * 16,), 13): paths,
        ("affective_gradient", "44" * 32, ("06" * 16,), 14): paths,
    }

    retained = production._retain_cross_intake_causal_motor_traces(active)

    assert tuple(key[0] for key in retained) == (
        "external_participant_sensory",
        "externally_reassembled_retained_formation",
        "new_neuronal_fractal",
        "retained_formation",
        "retained_formation",
    )
    assert tuple(key[1] for key in retained if key[0] == "retained_formation") == (
        "33" * 32,
        "34" * 32,
    )
