"""Authenticated operator transport for one physical reading lesson.

This module is transport-only.  It decodes bounded exact material geometry
and bounded real WAV bytes, then asks the existing server-owned physical
authorities to authenticate them.  It does not infer a glyph, word,
pronunciation, recognition, or meaning from the operator's display text.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.substrate.embodied_glyph_tutoring import (
    MAX_PCM_SAMPLES,
    MAX_PRESENTATION_FRAMES,
    AuthenticatedTutorAcousticActuator,
    ExactGlyphGeometry,
    GlyphBearingW1MaterialAuthority,
    GlyphMaterialPresentation,
    TutorAcousticActuation,
)


ROUTE_PATH = "/api/v1/embodiment/reading-lesson"
REQUEST_SCHEMA = "guala.embodied_reading.http_request.v1"
RESPONSE_SCHEMA = "guala.embodied_reading.http_response.v1"
MIN_PRESENTATION_FRAMES = 4
MAX_WAV_BYTES = MAX_PCM_SAMPLES * 2 + 4_096
MAX_REQUEST_BYTES = 512 * 1024

_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _text(value: object, name: str, maximum_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > maximum_bytes
    ):
        raise ValueError(f"{name} changed")
    return value


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _uint(value: object, name: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= maximum
    ):
        raise ValueError(f"{name} changed")
    return value


def _decode_base64(value: object, name: str, maximum: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} is absent")
    if len(value) > 4 * ((maximum + 2) // 3):
        raise ValueError(f"{name} exceeds its byte boundary")
    try:
        result = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"{name} is not canonical base64") from error
    if not result or len(result) > maximum:
        raise ValueError(f"{name} exceeds its byte boundary")
    if base64.b64encode(result).decode("ascii") != value:
        raise ValueError(f"{name} is not canonical base64")
    return result


@dataclass(frozen=True, slots=True)
class EmbodiedReadingLessonHTTPRequest:
    context_id: str
    tutor_designation: str
    material_id: str
    packed_foreground_bits: bytes = field(repr=False)
    foreground_luminance: int
    background_luminance: int
    source_time_ns: tuple[int, ...]
    source_time_start_ns: int
    source_media_receipt_sha256: str
    wav_bytes: bytes = field(repr=False)
    request_sha256: str

    @classmethod
    def decode(
        cls,
        value: Mapping[str, object],
    ) -> "EmbodiedReadingLessonHTTPRequest":
        expected = {
            "background_luminance",
            "context_id",
            "foreground_luminance",
            "material_id",
            "packed_foreground_bits_base64",
            "schema",
            "source_media_receipt_sha256",
            "source_time_ns",
            "source_time_start_ns",
            "tutor_designation",
            "wav_base64",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != REQUEST_SCHEMA
            or len(_canonical(value)) > MAX_REQUEST_BYTES
        ):
            raise ValueError("embodied reading HTTP request changed")
        packed = _decode_base64(
            value["packed_foreground_bits_base64"],
            "glyph geometry",
            512,
        )
        if len(packed) != 512:
            raise ValueError("glyph geometry must be one exact 64x64 bit plane")
        wav = _decode_base64(value["wav_base64"], "tutor WAV", MAX_WAV_BYTES)
        media_receipt = _sha(
            value["source_media_receipt_sha256"],
            "source media receipt",
        )
        if hashlib.sha256(wav).hexdigest() != media_receipt:
            raise ValueError("tutor WAV differs from its source media receipt")
        raw_times = value["source_time_ns"]
        if (
            not isinstance(raw_times, list)
            or not (
                MIN_PRESENTATION_FRAMES
                <= len(raw_times)
                <= MAX_PRESENTATION_FRAMES
            )
        ):
            raise ValueError("glyph frame extent changed")
        times = tuple(
            _uint(item, "glyph source time", 2**63 - 1)
            for item in raw_times
        )
        if tuple(sorted(set(times))) != times:
            raise ValueError("glyph source times are not strictly increasing")
        start = _uint(
            value["source_time_start_ns"],
            "lesson source start",
            2**63 - 1,
        )
        if times[0] < start:
            raise ValueError("glyph presentation precedes lesson source start")
        request_payload = dict(value)
        return cls(
            context_id=_text(value["context_id"], "lesson context", 256),
            tutor_designation=_text(
                value["tutor_designation"],
                "tutor designation",
                128,
            ),
            material_id=_text(value["material_id"], "material id", 256),
            packed_foreground_bits=packed,
            foreground_luminance=_uint(
                value["foreground_luminance"],
                "foreground luminance",
                255,
            ),
            background_luminance=_uint(
                value["background_luminance"],
                "background luminance",
                255,
            ),
            source_time_ns=times,
            source_time_start_ns=start,
            source_media_receipt_sha256=media_receipt,
            wav_bytes=wav,
            request_sha256=hashlib.sha256(
                _canonical(request_payload)
            ).hexdigest(),
        )

    def prepare(
        self,
        *,
        material_authority: GlyphBearingW1MaterialAuthority,
        acoustic_authority: AuthenticatedTutorAcousticActuator,
    ) -> "PreparedEmbodiedReadingHTTPRequest":
        geometry = ExactGlyphGeometry.create(
            packed_foreground_bits=self.packed_foreground_bits,
            foreground_luminance=self.foreground_luminance,
            background_luminance=self.background_luminance,
        )
        presentation = material_authority.present(
            material_id=self.material_id,
            geometry=geometry,
            source_time_ns=self.source_time_ns,
        )
        actuation = acoustic_authority.actuate_wav(
            wav_bytes=self.wav_bytes,
            source_media_receipt_sha256=(
                self.source_media_receipt_sha256
            ),
            source_time_start_ns=self.source_time_start_ns,
        )
        return PreparedEmbodiedReadingHTTPRequest(
            request_sha256=self.request_sha256,
            context_id=self.context_id,
            tutor_designation=self.tutor_designation,
            presentation_authority=material_authority,
            presentation=presentation,
            acoustic_authority=acoustic_authority,
            acoustic_actuation=actuation,
            wav_bytes=self.wav_bytes,
        )


@dataclass(frozen=True, slots=True)
class PreparedEmbodiedReadingHTTPRequest:
    request_sha256: str
    context_id: str
    tutor_designation: str
    presentation_authority: GlyphBearingW1MaterialAuthority = field(
        repr=False,
        compare=False,
    )
    presentation: GlyphMaterialPresentation = field(repr=False)
    acoustic_authority: AuthenticatedTutorAcousticActuator = field(
        repr=False,
        compare=False,
    )
    acoustic_actuation: TutorAcousticActuation = field(
        repr=False,
        compare=False,
    )
    wav_bytes: bytes = field(repr=False, compare=False)

    def controller_arguments(self) -> dict[str, object]:
        return {
            "acoustic_actuation": self.acoustic_actuation,
            "acoustic_authority": self.acoustic_authority,
            "context_id": self.context_id,
            "presentation": self.presentation,
            "presentation_authority": self.presentation_authority,
            "tutor_designation": self.tutor_designation,
            "wav_bytes": self.wav_bytes,
        }


def embodied_reading_http_response(
    *,
    request_sha256: str,
    boundary_projection: Mapping[str, object],
    lesson_projection: Mapping[str, object],
) -> dict[str, object]:
    _sha(request_sha256, "embodied reading request")
    if (
        not isinstance(boundary_projection, Mapping)
        or boundary_projection.get("retained_pcm_bytes") != 0
        or not isinstance(lesson_projection, Mapping)
        or lesson_projection.get("retained_pcm_bytes") != 0
    ):
        raise ValueError("embodied reading response retained PCM")
    return {
        "boundary": dict(boundary_projection),
        "claims": {
            "glyph_identity_authority": False,
            "meaning_authority": False,
            "pronunciation_authority": False,
            "reading_authority": False,
            "recognition_authority": False,
        },
        "lesson": dict(lesson_projection),
        "request_sha256": request_sha256,
        "retained_pcm_bytes": 0,
        "schema": RESPONSE_SCHEMA,
    }


__all__ = (
    "EmbodiedReadingLessonHTTPRequest",
    "MAX_REQUEST_BYTES",
    "MAX_WAV_BYTES",
    "PreparedEmbodiedReadingHTTPRequest",
    "REQUEST_SCHEMA",
    "RESPONSE_SCHEMA",
    "ROUTE_PATH",
    "embodied_reading_http_response",
)
