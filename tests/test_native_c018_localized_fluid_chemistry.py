"""C-018 exact localized recovery-fluid conservation evidence."""

from __future__ import annotations

from dsf_ai_service import native_production_app as production
from dsf_ai_service.glew_runtime import native_resident_organism as boundary


def _settlement(
    *,
    unchanged_unreached: int,
    unchanged_developmental_resting: int = 0,
) -> tuple[object, ...]:
    return (
        "10" * 16,
        10,
        4,
        9,
        (
            250_000,
            (1, 1),
            1,
            1,
            unchanged_unreached,
            unchanged_developmental_resting,
            0,
        ),
        (-1_000, -998, 0, 12_484, 2, 12_482, 0, -2),
        (((10, 1), (0, 1), (0, 1)), ((9, 1), (1, 1), (0, 1)), (1, 1)),
    )


def test_bounded_transport_prefers_a_reached_unreached_locality_witness() -> None:
    single = _settlement(unchanged_unreached=0)
    local = _settlement(unchanged_unreached=1)

    retained = production._advance_bounded_localized_fluid_chemistry_evidence(
        (), {"localized_fluid_chemistry": (single,)}
    )
    retained = production._advance_bounded_localized_fluid_chemistry_evidence(
        retained, {"localized_fluid_chemistry": (local,)}
    )

    assert retained == (local,)


def test_public_record_reconciles_local_material_energy_and_unreached_state(
    monkeypatch,
) -> None:
    settlement = _settlement(unchanged_unreached=1)
    monkeypatch.setattr(
        production,
        "_last_tested_localized_fluid_chemistry_evidence",
        {
            "intake": "unattended_time",
            "localized_fluid_chemistry": (settlement,),
            "organism_tick": 9,
            "state_sha256": "a" * 64,
        },
    )

    record = production._localized_fluid_chemistry_record()

    assert record["available"] is True
    assert record["status"] == "localized_contact_conserved"
    assert record["locality_conserved"] is True
    assert record["exact_conservation"] is True
    assert record["carrier_material"]["material_conserved"] is True
    assert record["reservoir_energy"]["energy_conserved"] is True
    assert record["named_chemical_authority"] is False
    assert record["python_decision_authority"] is False


def test_public_record_distinguishes_unmaterialized_developmental_population(
    monkeypatch,
) -> None:
    settlement = _settlement(
        unchanged_unreached=0,
        unchanged_developmental_resting=196_552,
    )
    monkeypatch.setattr(
        production,
        "_last_tested_localized_fluid_chemistry_evidence",
        {
            "intake": "unattended_time",
            "localized_fluid_chemistry": (settlement,),
            "organism_tick": 9,
            "state_sha256": "a" * 64,
        },
    )

    record = production._localized_fluid_chemistry_record()

    assert record["available"] is True
    assert record["contact"]["unchanged_unreached_active_neuron_count"] == 0
    assert (
        record["contact"][
            "unchanged_unreached_developmental_resting_neuron_count"
        ]
        == 196_552
    )
    assert "outside the mutable pump boundary" in record["reason"]


def test_python_boundary_preserves_the_exact_native_local_settlement() -> None:
    raw = _settlement(unchanged_unreached=1)
    native_projection = (
        raw[0],
        raw[1],
        raw[2],
        raw[3],
        (250_000, ("1", "1"), 1, 1, 1, 0, 0),
        (-1_000, -998, "0", "12484", "2", "12482", 0, -2),
        (
            (("10", "1"), ("0", "1"), ("0", "1")),
            (("9", "1"), ("1", "1"), ("0", "1")),
            ("1", "1"),
        ),
    )

    assert boundary._localized_fluid_chemistry_evidence(
        [native_projection]
    ) == (raw,)
