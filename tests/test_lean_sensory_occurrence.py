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
RETINA = tuple(index % 256 for index in range(RETINAL_SITE_COUNT))
PRESSURE = bytes(index % 256 for index in range(8_000))
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
            "retina_u8": RETINA,
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
