"""Authenticated one-channel projection from a verified browser pair.

The projection preserves an actually received channel for the existing mono
Krimelack hearing path while the two-channel room-hearing route remains
hardware-unproven.  It never averages, duplicates, swaps, or separates
channels.  Its authority is limited to byte provenance from one accepted
runtime channel; it proves neither a physical microphone nor an ear.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    AcceptedBrowserBinauralPCMChunk,
)


BROWSER_DISCRETE_CHANNEL_PROJECTION_SCHEMA = (
    "guala.browser_discrete_channel_projection.v1"
)
BROWSER_DISCRETE_CHANNEL_PROJECTION_DOMAIN = (
    b"guala-browser-discrete-channel-projection-v1\0"
)


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
        raise ValueError(
            "browser channel projection key must be bytes or text"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "browser channel projection key is outside its exact boundary"
        )
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class BrowserDiscreteChannelProjectionReceipt:
    stream_id: str
    target_mono_stream_id: str
    sequence: int
    first_sample_index: int
    sample_count: int
    channel: str
    pcm_sha256: str
    parent_lineage_receipt_sha256: str
    parent_continuity_receipt_sha256: str
    binaural_hardware_authority_proven: bool
    room_hearing_authority: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binaural_hardware_authority_proven": (
                self.binaural_hardware_authority_proven
            ),
            "channel": self.channel,
            "first_sample_index": self.first_sample_index,
            "parent_continuity_receipt_sha256": (
                self.parent_continuity_receipt_sha256
            ),
            "parent_lineage_receipt_sha256": (
                self.parent_lineage_receipt_sha256
            ),
            "pcm_sha256": self.pcm_sha256,
            "room_hearing_authority": self.room_hearing_authority,
            "sample_count": self.sample_count,
            "schema": BROWSER_DISCRETE_CHANNEL_PROJECTION_SCHEMA,
            "sequence": self.sequence,
            "stream_id": self.stream_id,
            "target_mono_stream_id": self.target_mono_stream_id,
        }

    def verify(
        self,
        authority_key: bytes | str,
        *,
        pcm_s16le: bytes | None = None,
    ) -> None:
        key = _key(authority_key)
        if (
            not isinstance(self.stream_id, str)
            or not self.stream_id
            or not isinstance(self.target_mono_stream_id, str)
            or not self.target_mono_stream_id
            or isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or isinstance(self.first_sample_index, bool)
            or not isinstance(self.first_sample_index, int)
            or self.first_sample_index < 0
            or isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or self.sample_count <= 0
            or self.channel != "left"
            or self.binaural_hardware_authority_proven is not False
            or self.room_hearing_authority is not False
        ):
            raise ValueError(
                "browser discrete channel projection boundary changed"
            )
        for value, name in (
            (self.pcm_sha256, "projected PCM"),
            (
                self.parent_lineage_receipt_sha256,
                "parent lineage",
            ),
            (
                self.parent_continuity_receipt_sha256,
                "parent continuity",
            ),
        ):
            _sha256(value, f"browser channel {name}")
        if pcm_s16le is not None:
            if (
                not isinstance(pcm_s16le, bytes)
                or len(pcm_s16le) != self.sample_count * 2
                or hashlib.sha256(pcm_s16le).hexdigest()
                != self.pcm_sha256
            ):
                raise ValueError(
                    "mono hearing bytes left their discrete channel"
                )
        payload = self.payload()
        expected_hmac = hmac.new(
            key,
            BROWSER_DISCRETE_CHANNEL_PROJECTION_DOMAIN
            + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError(
                "browser channel projection authority changed"
            )

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    @classmethod
    def from_record(
        cls,
        value: Mapping[str, object],
    ) -> BrowserDiscreteChannelProjectionReceipt:
        if not isinstance(value, Mapping):
            raise TypeError(
                "browser channel projection must be a typed record"
            )
        if value.get("schema") != (
            BROWSER_DISCRETE_CHANNEL_PROJECTION_SCHEMA
        ):
            raise ValueError(
                "browser channel projection schema changed"
            )
        try:
            return cls(
                stream_id=value["stream_id"],
                target_mono_stream_id=value["target_mono_stream_id"],
                sequence=value["sequence"],
                first_sample_index=value["first_sample_index"],
                sample_count=value["sample_count"],
                channel=value["channel"],
                pcm_sha256=value["pcm_sha256"],
                parent_lineage_receipt_sha256=(
                    value["parent_lineage_receipt_sha256"]
                ),
                parent_continuity_receipt_sha256=(
                    value["parent_continuity_receipt_sha256"]
                ),
                binaural_hardware_authority_proven=(
                    value["binaural_hardware_authority_proven"]
                ),
                room_hearing_authority=(
                    value["room_hearing_authority"]
                ),
                authority_hmac_sha256=value["authority_hmac_sha256"],
                authority_receipt_sha256=(
                    value["authority_receipt_sha256"]
                ),
            )
        except KeyError as error:
            raise ValueError(
                "browser channel projection record is incomplete"
            ) from error


class BrowserDiscreteChannelProjectionOwner:
    def __init__(self, authority_key: bytes | str) -> None:
        self._key = _key(authority_key)

    def issue(
        self,
        accepted: AcceptedBrowserBinauralPCMChunk,
        *,
        target_mono_stream_id: str,
    ) -> BrowserDiscreteChannelProjectionReceipt:
        if not isinstance(accepted, AcceptedBrowserBinauralPCMChunk):
            raise TypeError(
                "browser channel projection requires typed accepted pressure"
            )
        accepted.verify()
        if (
            not isinstance(target_mono_stream_id, str)
            or not target_mono_stream_id
        ):
            raise ValueError(
                "browser channel projection target stream is required"
            )
        draft = BrowserDiscreteChannelProjectionReceipt(
            stream_id=accepted.receipt.stream_id,
            target_mono_stream_id=target_mono_stream_id,
            sequence=accepted.receipt.sequence,
            first_sample_index=accepted.receipt.first_sample_index,
            sample_count=accepted.receipt.sample_count,
            channel="left",
            pcm_sha256=accepted.receipt.left_pcm_sha256,
            parent_lineage_receipt_sha256=(
                accepted.lineage.receipt_sha256
            ),
            parent_continuity_receipt_sha256=(
                accepted.receipt.receipt_sha256
            ),
            binaural_hardware_authority_proven=False,
            room_hearing_authority=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = draft.payload()
        signature = hmac.new(
            self._key,
            BROWSER_DISCRETE_CHANNEL_PROJECTION_DOMAIN
            + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = BrowserDiscreteChannelProjectionReceipt(
            stream_id=draft.stream_id,
            target_mono_stream_id=draft.target_mono_stream_id,
            sequence=draft.sequence,
            first_sample_index=draft.first_sample_index,
            sample_count=draft.sample_count,
            channel=draft.channel,
            pcm_sha256=draft.pcm_sha256,
            parent_lineage_receipt_sha256=(
                draft.parent_lineage_receipt_sha256
            ),
            parent_continuity_receipt_sha256=(
                draft.parent_continuity_receipt_sha256
            ),
            binaural_hardware_authority_proven=False,
            room_hearing_authority=False,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._key, pcm_s16le=accepted.left_pcm_s16le)
        return result

    def verify(
        self,
        receipt: BrowserDiscreteChannelProjectionReceipt,
        *,
        pcm_s16le: bytes,
    ) -> None:
        if not isinstance(
            receipt,
            BrowserDiscreteChannelProjectionReceipt,
        ):
            raise TypeError(
                "mono hearing requires a typed channel projection"
            )
        receipt.verify(self._key, pcm_s16le=pcm_s16le)


__all__ = [
    "BROWSER_DISCRETE_CHANNEL_PROJECTION_SCHEMA",
    "BrowserDiscreteChannelProjectionOwner",
    "BrowserDiscreteChannelProjectionReceipt",
]
