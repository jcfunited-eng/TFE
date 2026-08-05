from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import numpy as np
import pytest

from dsf_ai_service.embodied_reading_http_contract import (
    REQUEST_SCHEMA,
    RESPONSE_SCHEMA,
    ROUTE_PATH,
    EmbodiedReadingLessonHTTPRequest,
    embodied_reading_http_response,
)
from dsf_ai_service.substrate.embodied_glyph_tutoring import (
    AuthenticatedTutorAcousticActuator,
    GlyphBearingW1MaterialAuthority,
)


ROOT = Path(__file__).resolve().parents[1]
WAV = (
    ROOT
    / "dsf_ai_service"
    / "curriculum"
    / "assets"
    / "speech_commands"
    / "go"
    / "022cd682_nohash_0.wav"
).read_bytes()
KEY = b"embodied-reading-http-contract-production-key"


def _payload() -> dict[str, object]:
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[8:56, 10:18] = 1
    mask[8:16, 10:42] = 1
    mask[28:36, 10:44] = 1
    mask[48:56, 10:42] = 1
    packed = np.packbits(mask.reshape(-1), bitorder="big").tobytes()
    start = 4_000_000_000_000
    return {
        "background_luminance": 17,
        "context_id": "authenticated-operator-reading-lesson",
        "foreground_luminance": 238,
        "material_id": "W1-object-1",
        "packed_foreground_bits_base64": base64.b64encode(
            packed
        ).decode("ascii"),
        "schema": REQUEST_SCHEMA,
        "source_media_receipt_sha256": hashlib.sha256(WAV).hexdigest(),
        "source_time_ns": [
            start + 100_000_000,
            start + 400_000_000,
            start + 700_000_000,
            start + 900_000_000,
        ],
        "source_time_start_ns": start,
        "tutor_designation": "display provenance only",
        "wav_base64": base64.b64encode(WAV).decode("ascii"),
    }


def test_exact_operator_request_builds_only_typed_physical_inputs() -> None:
    decoded = EmbodiedReadingLessonHTTPRequest.decode(_payload())
    material = GlyphBearingW1MaterialAuthority(authority_key=KEY)
    acoustic = AuthenticatedTutorAcousticActuator(authority_key=KEY)
    prepared = decoded.prepare(
        material_authority=material,
        acoustic_authority=acoustic,
    )
    arguments = prepared.controller_arguments()

    assert ROUTE_PATH == "/api/v1/embodiment/reading-lesson"
    assert set(arguments) == {
        "acoustic_actuation",
        "acoustic_authority",
        "context_id",
        "presentation",
        "presentation_authority",
        "tutor_designation",
        "wav_bytes",
    }
    assert prepared.presentation.geometry.foreground_pixel_count > 0
    assert prepared.acoustic_actuation.pcm_sha256 == hashlib.sha256(
        prepared.acoustic_actuation.pcm_s16le
    ).hexdigest()
    assert prepared.tutor_designation not in repr(
        prepared.presentation.payload()
    )
    assert prepared.tutor_designation not in repr(
        prepared.acoustic_actuation.payload()
    )


def test_crossed_media_or_noncanonical_geometry_fails_closed() -> None:
    crossed = _payload()
    crossed["source_media_receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs"):
        EmbodiedReadingLessonHTTPRequest.decode(crossed)

    short_geometry = _payload()
    short_geometry["packed_foreground_bits_base64"] = (
        base64.b64encode(b"\x01" * 511).decode("ascii")
    )
    with pytest.raises(ValueError, match="64x64"):
        EmbodiedReadingLessonHTTPRequest.decode(short_geometry)

    extra_meaning = _payload()
    extra_meaning["meaning"] = "letter B"
    with pytest.raises(ValueError, match="request changed"):
        EmbodiedReadingLessonHTTPRequest.decode(extra_meaning)


def test_response_is_receipt_projection_only_and_never_returns_pcm() -> None:
    request_sha256 = EmbodiedReadingLessonHTTPRequest.decode(
        _payload()
    ).request_sha256
    response = embodied_reading_http_response(
        request_sha256=request_sha256,
        boundary_projection={
            "record_count": 1,
            "retained_pcm_bytes": 0,
        },
        lesson_projection={
            "lesson_count": 1,
            "retained_pcm_bytes": 0,
        },
    )

    assert response["schema"] == RESPONSE_SCHEMA
    assert response["retained_pcm_bytes"] == 0
    assert not any(response["claims"].values())
    assert "pcm_s16le" not in repr(response)

    with pytest.raises(ValueError, match="retained PCM"):
        embodied_reading_http_response(
            request_sha256=request_sha256,
            boundary_projection={"retained_pcm_bytes": 1},
            lesson_projection={"retained_pcm_bytes": 0},
        )
