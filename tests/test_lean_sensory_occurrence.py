from __future__ import annotations

import base64

import pytest

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_embodiment_observation import (
    lean_embodiment_observation,
)
from dsf_ai_service.lean_production_app import OccurrenceBody, _physical_occurrence
from dsf_ai_service.lean_sensory_occurrence import (
    LeanSensoryOccurrence,
    RETINAL_SITE_COUNT,
)


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
RETINA = tuple(index % 256 for index in range(RETINAL_SITE_COUNT * 3))
PRESSURE = bytes(index % 256 for index in range(8_000))
GUIDED = ((37, 0, 1_500), (38, 0, 1_500), (39, 0, 1_500), (44, 0, 1_500))
BODY_AXES = (
    (0, "neck_yaw", "millidegree", 0, -180_000, 0, 180_000),
    (1, "left_eyelid_aperture", "micrometre", 320, 0, 0, 320),
    (2, "right_eyelid_aperture", "micrometre", 320, 0, 0, 320),
)


def test_each_source_has_one_exact_mounted_modality_shape() -> None:
    valid = (
        ("camera", RETINA, None),
        ("media", RETINA, None),
        ("text-light", RETINA, None),
        ("microphone", None, PRESSURE),
        ("camera-microphone", RETINA, PRESSURE),
        ("card-microphone", RETINA, PRESSURE),
        ("text-microphone", RETINA, PRESSURE),
    )
    for source, retina, pressure in valid:
        occurrence = LeanSensoryOccurrence(source, retina, pressure)
        assert len(occurrence.source_receipt_sha256) == 64

    invalid = (
        ("camera", None, None),
        ("media", None, PRESSURE),
        ("text-light", RETINA, PRESSURE),
        ("microphone", RETINA, PRESSURE),
        ("camera-microphone", RETINA, None),
        ("card-microphone", None, PRESSURE),
        ("text-microphone", RETINA, None),
    )
    for source, retina, pressure in invalid:
        with pytest.raises(ValueError):
            LeanSensoryOccurrence(source, retina, pressure)


def test_retina_pressure_and_receipt_are_exact_and_bounded() -> None:
    first = LeanSensoryOccurrence("camera-microphone", RETINA, PRESSURE)
    second = LeanSensoryOccurrence("camera-microphone", RETINA, PRESSURE)
    assert first.source_receipt_sha256 == second.source_receipt_sha256
    assert first.source_receipt_sha256 != LeanSensoryOccurrence(
        "card-microphone", RETINA, PRESSURE
    ).source_receipt_sha256
    for retina in (RETINA[:-1], RETINA + (0,), (0,) * 134 + (256,)):
        with pytest.raises(ValueError):
            LeanSensoryOccurrence("camera", retina, None)
    for pressure in (b"", b"x", PRESSURE + b"xx"):
        with pytest.raises(ValueError):
            LeanSensoryOccurrence("microphone", None, pressure)


def test_transport_decodes_one_typed_sensory_occurrence() -> None:
    encoded = base64.b64encode(PRESSURE).decode("ascii")
    parsed = OccurrenceBody.model_validate({
        "kind": "sensory",
        "payload": {
            "source": "camera-microphone",
            "retina_rgb_u8": RETINA,
            "pcm_s16le_base64": encoded,
        },
    })
    physical = _physical_occurrence(parsed)
    assert physical.kind == "sensory"
    assert physical.payload == LeanSensoryOccurrence(
        "camera-microphone", RETINA, PRESSURE
    )
    malformed = OccurrenceBody.model_validate({
        "kind": "sensory",
        "payload": {
            "source": "microphone",
            "pcm_s16le_base64": "not base64",
        },
    })
    with pytest.raises(ValueError, match="canonical base64"):
        _physical_occurrence(malformed)


def test_guided_vocal_pressure_retains_one_bounded_physical_guide() -> None:
    encoded = base64.b64encode(PRESSURE).decode("ascii")
    parsed = OccurrenceBody.model_validate({
        "kind": "sensory",
        "payload": {
            "source": "guided-vocal-microphone",
            "pcm_s16le_base64": encoded,
            "guided_vocal_drives": [
                {
                    "axis_ordinal": axis,
                    "direction_ordinal": direction,
                    "outward_elementary_carriers": carriers,
                }
                for axis, direction, carriers in GUIDED
            ],
        },
    })
    physical = _physical_occurrence(parsed)
    assert physical.payload == LeanSensoryOccurrence(
        "guided-vocal-microphone", None, PRESSURE, GUIDED
    )
    assert physical.payload.source_receipt_sha256 != LeanSensoryOccurrence(
        "guided-vocal-microphone",
        None,
        PRESSURE,
        tuple((axis, 1, carriers) for axis, _direction, carriers in GUIDED),
    ).source_receipt_sha256

    for invalid in (
        (),
        ((37, 0, 1_500), (37, 1, 1_500)),
        ((23, 0, 1_500),),
        ((37, 2, 1_500),),
        ((37, 0, 0),),
    ):
        with pytest.raises(ValueError):
            LeanSensoryOccurrence(
                "guided-vocal-microphone", None, PRESSURE, invalid
            )


def test_home_projection_is_exact_compact_geometry_not_a_second_world() -> None:
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    record = lean_embodiment_observation(snapshot, BODY_AXES)
    assert record["schema"] == "guala.lean_embodiment_observation.v1"
    assert record["revision"] == snapshot.revision
    assert record["state_sha256"] == snapshot.state_sha256
    assert record["authority_receipt_sha256"] == (
        snapshot.authority_receipt_sha256
    )
    assert record["self_body_id"] == "guala-body-1"
    assert len(record["regions"]) == 9
    assert len(record["portals"]) == 9
    assert len(record["objects"]) == len(snapshot.objects)
    assert len(record["bodies"]) == 2
    assert len(record["native_body_axes"]) == len(BODY_AXES)
    assert all("material" not in item for item in record["objects"])
    assert all(
        set(item["optical_surface"] or ()) <= {"columns", "rows"}
        for item in record["objects"]
    )


def test_direct_acoustic_guide_retains_nine_existing_controls_only() -> None:
    axes = (18, 37, 38, 39, 40, 41, 42, 43, 44)
    for direction in (0, 1):
        drives = tuple((axis, direction, 1) for axis in axes)
        occurrence = LeanSensoryOccurrence(
            "guided-vocal-microphone", None, PRESSURE, drives
        )
        assert occurrence.guided_vocal_drives == drives
    for axis in range(45):
        if axis not in axes:
            with pytest.raises(ValueError, match="bounded unique anatomy"):
                LeanSensoryOccurrence(
                    "guided-vocal-microphone", None, PRESSURE, ((axis, 0, 1),)
                )
    with pytest.raises(ValueError, match="fixed vocal anatomy"):
        LeanSensoryOccurrence(
            "guided-vocal-microphone", None, PRESSURE,
            tuple((axis, 0, 1) for axis in axes) + ((18, 1, 1),),
        )


def test_guided_body_source_admits_caregiver_guidable_axes_only() -> None:
    from dsf_ai_service.lean_sensory_occurrence import (
        CAREGIVER_GUIDABLE_BODY_AXES,
        MAX_GUIDED_BODY_DRIVES,
    )

    assert CAREGIVER_GUIDABLE_BODY_AXES == frozenset({0, 1, 2, 3, 14, *range(19, 37)})
    hand_over_hand = ((14, 0, 1_500), (24, 1, 1_500), (26, 1, 1_500))
    with_card = LeanSensoryOccurrence("guided-body-microphone", RETINA, PRESSURE, hand_over_hand)
    without_light = LeanSensoryOccurrence("guided-body-microphone", None, PRESSURE, hand_over_hand)
    assert with_card.source_receipt_sha256 != without_light.source_receipt_sha256
    for invalid in (
        ((4, 1, 1_500),),  # an eye: nobody moves it by hand
        ((18, 0, 1_500),),  # the airway belongs to the guided-vocal source
        ((37, 0, 1_500),),
        ((14, 0, 0),),  # no work
        ((14, 2, 1_500),),  # no such direction
        ((14, 0, 1_500), (14, 1, 1_500)),  # one axis twice
        tuple((19 + index, 0, 1) for index in range(MAX_GUIDED_BODY_DRIVES + 1)),
    ):
        with pytest.raises(ValueError):
            LeanSensoryOccurrence("guided-body-microphone", None, PRESSURE, invalid)
    with pytest.raises(ValueError):
        LeanSensoryOccurrence("guided-body-microphone", RETINA, None, hand_over_hand)
    with pytest.raises(ValueError):
        LeanSensoryOccurrence("guided-body-microphone", RETINA, PRESSURE, None)
    with pytest.raises(ValueError):
        LeanSensoryOccurrence("guided-vocal-microphone", None, PRESSURE, ((14, 0, 1_500),))
    with pytest.raises(ValueError):
        LeanSensoryOccurrence("camera-microphone", RETINA, PRESSURE, hand_over_hand)


def test_metabolic_need_ports_mount_only_after_the_focal_field() -> None:
    from fractions import Fraction
    from dsf_ai_service.guala_physical_sensorium import (
        NEED_PORTS, PhysicalSensorium, compact_signal_body,
    )
    from dsf_ai_service.guala_receptor_anatomy import NEED_PORT_COUNT, receptor_anatomy

    F = Fraction
    base = dict(frame_count=2, retina=(F(0),) * 135, legacy_ears=(F(0),) * 2, cochleae=(F(0),) * 32,
                touch=(F(0),) * 28, smell=(F(0),) * 8, taste=(F(0),) * 5, displacement=(F(0),) * 4,
                articulation=(F(0),) * 4, thermal=(F(0),) * 2)
    fed = PhysicalSensorium.constant(**base, retina_focal=(F(0),) * 768, need=(F(1, 3), F(1, 5)))
    assert len(fed.ordered_ports()) == NEED_PORT_COUNT == 990
    assert fed.ordered_ports()[-2:] == ((F(1, 3), F(1, 3)), (F(1, 5), F(1, 5)))
    assert len(compact_signal_body(fed, frame_count=2)) == 990 * 2 * 8
    assert receptor_anatomy(include_focal=True, include_need=True).port_count == 990
    with pytest.raises(ValueError):
        compact_signal_body(PhysicalSensorium.constant(**base, need=(F(0), F(0))), frame_count=2)
    with pytest.raises(ValueError):
        compact_signal_body(PhysicalSensorium.constant(**base, retina_focal=(F(0),) * 768, need=(F(0),)), frame_count=2)
    with pytest.raises(ValueError):
        receptor_anatomy(include_focal=False, include_need=True)
    assert NEED_PORTS == 2
