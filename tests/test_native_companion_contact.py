from fractions import Fraction

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    BodySurfaceContactCommand,
    command_record,
)


def test_named_care_profiles_end_at_physical_surface_commands_only() -> None:
    expected_width = {
        "forehead_kiss": 1,
        "head_pat": 1,
        "hold_hand": 1,
        "hug": 3,
        "shoulder_touch": 1,
    }
    for operation, width in expected_width.items():
        actuations, duration = production._companion_contact_profile(
            operation,
            "guala-body-1",
        )
        record = command_record(
            BodySurfaceContactCommand(actuations, duration)
        )
        assert record["operation"] == "body_surface_contact"
        assert len(record["actuations"]) == width
        encoded = repr(record).lower()
        assert operation not in encoded
        assert "reward" not in encoded
        assert "dopamine" not in encoded
        assert "meaning" not in encoded


def test_one_surface_contact_reaches_only_its_exact_cutaneous_site(
    monkeypatch,
) -> None:
    monkeypatch.setattr(production, "TOUCH_RECEPTORS_AUTHORIZED", True)
    times = (Fraction(0), Fraction(1, 2))
    topology_index = 4
    trajectories = tuple(
        (
            (Fraction(1, 2), Fraction(1, 2))
            if index == topology_index
            else (Fraction(0), Fraction(0))
        )
        for index in range(production.CONTACT_SHEET_SITE_COUNT)
    )
    ports = production._touch_ports(
        times,
        None,
        body_surface_contact_trajectories=trajectories,
    )

    sheet = ports[: production.CONTACT_SHEET_SITE_COUNT]
    assert tuple(
        index
        for index, port in enumerate(sheet)
        if any(port.normalized_signal)
    ) == (topology_index,)
    assert sheet[topology_index].normalized_signal == (
        Fraction(1, 2),
        Fraction(1, 2),
    )
