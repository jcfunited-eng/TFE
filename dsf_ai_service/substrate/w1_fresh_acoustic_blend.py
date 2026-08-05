"""Authenticated exact blend of two source-disjoint real speech pressures."""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.w1_speech_commands_tutor_plan import (
    W1TutoredSpeechPressure,
)


W1_FRESH_ACOUSTIC_BLEND_SCHEMA = "guala.w1.fresh_acoustic_blend.v1"
_DOMAIN = b"guala-w1-fresh-acoustic-blend-v1\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 acoustic blend key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 acoustic blend key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _saturating_pcm16_sum(left: bytes, right: bytes) -> bytes:
    if (
        not isinstance(left, bytes)
        or not isinstance(right, bytes)
        or len(left) != len(right)
        or not left
        or len(left) % 2
    ):
        raise ValueError("W1 acoustic blend PCM boundary changed")
    left_samples = struct.iter_unpack("<h", left)
    right_samples = struct.iter_unpack("<h", right)
    samples = tuple(
        max(-32_768, min(32_767, left_value[0] + right_value[0]))
        for left_value, right_value in zip(
            left_samples, right_samples, strict=True
        )
    )
    return struct.pack(f"<{len(samples)}h", *samples)


@dataclass(frozen=True, slots=True)
class W1FreshAcousticBlend:
    pcm_s16le: bytes
    blend_pcm_sha256: str
    sample_count: int
    source_pressure_receipt_sha256s: tuple[str, str]
    source_pcm_sha256s: tuple[str, str]
    source_file_sha256s: tuple[str, str]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "blend_pcm_sha256": self.blend_pcm_sha256,
            "channels": 1,
            "mix_law": "exact_pcm16_saturating_superposition",
            "sample_count": self.sample_count,
            "sample_rate_hz": 16_000,
            "sample_width_bytes": 2,
            "schema": W1_FRESH_ACOUSTIC_BLEND_SCHEMA,
            "source_file_sha256s": list(self.source_file_sha256s),
            "source_pcm_sha256s": list(self.source_pcm_sha256s),
            "source_pressure_receipt_sha256s": list(
                self.source_pressure_receipt_sha256s
            ),
        }


class W1FreshAcousticBlendAuthority:
    """Bounded owner of exact real-pressure superpositions."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        tutor_pressure_key: bytes | str,
        max_blends: int,
    ) -> None:
        if (
            isinstance(max_blends, bool)
            or not isinstance(max_blends, int)
            or max_blends <= 0
        ):
            raise ValueError("W1 acoustic blend capacity changed")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._key = hashlib.sha256(_DOMAIN + root).digest()
        self._tutor_key = tutor_pressure_key
        self._max_blends = max_blends
        self._blends: dict[str, W1FreshAcousticBlend] = {}
        self._used_source_files: set[str] = set()
        self._lock = threading.RLock()

    def verify(self, blend: W1FreshAcousticBlend) -> None:
        if not isinstance(blend, W1FreshAcousticBlend):
            raise TypeError("W1 acoustic blend is not typed")
        for value, name in (
            (blend.blend_pcm_sha256, "W1 acoustic blend PCM"),
            (blend.authority_hmac_sha256, "W1 acoustic blend HMAC"),
            (blend.authority_receipt_sha256, "W1 acoustic blend authority"),
            *(
                (value, "W1 acoustic blend pressure source")
                for value in blend.source_pressure_receipt_sha256s
            ),
            *(
                (value, "W1 acoustic blend PCM source")
                for value in blend.source_pcm_sha256s
            ),
            *(
                (value, "W1 acoustic blend file source")
                for value in blend.source_file_sha256s
            ),
        ):
            _sha256(value, name)
        payload = blend.payload()
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            blend.sample_count != 16_000
            or len(blend.pcm_s16le) != blend.sample_count * 2
            or hashlib.sha256(blend.pcm_s16le).hexdigest()
            != blend.blend_pcm_sha256
            or any(
                values != tuple(sorted(set(values)))
                for values in (
                    blend.source_pressure_receipt_sha256s,
                    blend.source_pcm_sha256s,
                    blend.source_file_sha256s,
                )
            )
            or not hmac.compare_digest(
                signature, blend.authority_hmac_sha256
            )
            or blend.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 acoustic blend authority changed")

    def blend(
        self,
        *,
        left: W1TutoredSpeechPressure,
        right: W1TutoredSpeechPressure,
    ) -> W1FreshAcousticBlend:
        left.verify(self._tutor_key)
        right.verify(self._tutor_key)
        if (
            left.source_file_sha256 == right.source_file_sha256
            or left.authority_receipt_sha256
            == right.authority_receipt_sha256
            or left.sample_count != right.sample_count
            or left.sample_count != 16_000
        ):
            raise ValueError(
                "W1 acoustic blend sources are not independent"
            )
        pcm = _saturating_pcm16_sum(left.pcm_s16le, right.pcm_s16le)
        source_pressures = tuple(sorted((
            left.authority_receipt_sha256,
            right.authority_receipt_sha256,
        )))
        source_pcms = tuple(sorted((
            left.pcm_sha256,
            right.pcm_sha256,
        )))
        source_files = tuple(sorted((
            left.source_file_sha256,
            right.source_file_sha256,
        )))
        provisional = W1FreshAcousticBlend(
            pcm_s16le=pcm,
            blend_pcm_sha256=hashlib.sha256(pcm).hexdigest(),
            sample_count=left.sample_count,
            source_pressure_receipt_sha256s=source_pressures,
            source_pcm_sha256s=source_pcms,
            source_file_sha256s=source_files,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1FreshAcousticBlend(
            pcm_s16le=pcm,
            blend_pcm_sha256=provisional.blend_pcm_sha256,
            sample_count=provisional.sample_count,
            source_pressure_receipt_sha256s=source_pressures,
            source_pcm_sha256s=source_pcms,
            source_file_sha256s=source_files,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result)
        with self._lock:
            if self._used_source_files.intersection(source_files):
                raise ValueError("W1 acoustic blend reuses a source file")
            if len(self._blends) >= self._max_blends:
                raise RuntimeError("W1 acoustic blend capacity exhausted")
            self._blends[result.authority_receipt_sha256] = result
            self._used_source_files.update(source_files)
        return result


__all__ = [
    "W1FreshAcousticBlend",
    "W1FreshAcousticBlendAuthority",
]
