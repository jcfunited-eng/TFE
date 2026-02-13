from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Protocol, runtime_checkable, Iterable, Optional


@dataclass(frozen=True)
class ChainOfCustodyEvent:
    """
    Chain-of-custody event structure aligned with SES-Core COC-ES.

    Fields:

    - event_id: globally unique identifier.
    - tenant_id: logical tenant associated with the event.
    - actor_id: canonical identity of the actor performing the action.
    - asset_id: identifier for the asset or object affected.
    - action: vocabulary-controlled action name (e.g. "key.rotate").
    - occurred_at: ISO-8601 timestamp in UTC.
    - payload: arbitrary structured data associated with the event.
    - payload_hash: SHA-256 hash of the canonical payload representation.
    - signature: optional signature over the event (for non-repudiation).
    """

    event_id: str
    tenant_id: str
    actor_id: str
    asset_id: str
    action: str
    occurred_at: str
    payload: Mapping[str, Any]
    payload_hash: str
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["payload"] = dict(self.payload)
        return result

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "ChainOfCustodyEvent":
        required_fields = [
            "event_id",
            "tenant_id",
            "actor_id",
            "asset_id",
            "action",
            "occurred_at",
            "payload",
            "payload_hash",
        ]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing field in COC event: {field_name}")

        payload = data.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")

        return ChainOfCustodyEvent(
            event_id=str(data["event_id"]),
            tenant_id=str(data["tenant_id"]),
            actor_id=str(data["actor_id"]),
            asset_id=str(data["asset_id"]),
            action=str(data["action"]),
            occurred_at=str(data["occurred_at"]),
            payload=dict(payload),
            payload_hash=str(data["payload_hash"]),
            signature=(None if data.get("signature") is None else str(data["signature"])),
        )

    def canonical_payload_bytes(self) -> bytes:
        return json.dumps(
            dict(self.payload),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


@runtime_checkable
class ChainOfCustodySink(Protocol):
    """
    Interface for durable recording of chain-of-custody events.

    Implementations may write to files, databases, or external logging
    systems.
    """

    def record_event(self, event: ChainOfCustodyEvent) -> None:
        ...

    def record_events(self, events: Iterable[ChainOfCustodyEvent]) -> None:
        ...


@dataclass
class FileChainOfCustodySink:
    """
    Simple file-based implementation of ChainOfCustodySink.

    Events are serialized as one JSON object per line, suitable for later
    ingestion into an analytics or archival system.
    """

    path: str

    def record_event(self, event: ChainOfCustodyEvent) -> None:
        line = json.dumps(
            event.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")

    def record_events(self, events: Iterable[ChainOfCustodyEvent]) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            for event in events:
                line = json.dumps(
                    event.to_dict(),
                    separators=(",", ":"),
                    sort_keys=True,
                )
                f.write(line)
                f.write("\n")


@runtime_checkable
class SignatureBackend(Protocol):
    """
    Interface for signing and verifying chain-of-custody events.

    Implementations can use asymmetric cryptography, HSMs, or other
    mechanisms. The protocol here is intentionally minimal and does not
    constrain the algorithm.
    """

    def sign(self, payload_hash: bytes) -> bytes:
        ...

    def verify(self, payload_hash: bytes, signature: bytes) -> bool:
        ...


class ChainOfCustodyService:
    """
    Service for constructing and submitting chain-of-custody events.

    The service handles:
    - Canonical payload hashing.
    - Optional signing and signature verification.
    - Emission of events to a durable sink.
    """

    def __init__(
        self,
        sink: ChainOfCustodySink,
        signature_backend: Optional[SignatureBackend] = None,
    ) -> None:
        if not isinstance(sink, ChainOfCustodySink):
            raise TypeError("sink must implement ChainOfCustodySink")
        self._sink = sink
        self._signature_backend = signature_backend

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _hash_payload(self, payload: Mapping[str, Any]) -> bytes:
        canonical = json.dumps(
            dict(payload),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).digest()

    def _random_event_id(self) -> str:
        return f"coc-{uuid.uuid4().hex}"

    def create_event(
        self,
        tenant_id: str,
        actor_id: str,
        asset_id: str,
        action: str,
        payload: Mapping[str, Any],
    ) -> ChainOfCustodyEvent:
        if not tenant_id:
            raise ValueError("tenant_id must be non-empty")
        if not actor_id:
            raise ValueError("actor_id must be non-empty")
        if not asset_id:
            raise ValueError("asset_id must be non-empty")
        if not action:
            raise ValueError("action must be non-empty")

        phash = self._hash_payload(payload)
        signature_str: Optional[str] = None

        if self._signature_backend is not None:
            sig_bytes = self._signature_backend.sign(phash)
            signature_str = sig_bytes.hex()

        event = ChainOfCustodyEvent(
            event_id=self._random_event_id(),
            tenant_id=tenant_id,
            actor_id=actor_id,
            asset_id=asset_id,
            action=action,
            occurred_at=self._now_iso(),
            payload=dict(payload),
            payload_hash=phash.hex(),
            signature=signature_str,
        )
        return event

    def record_event(
        self,
        tenant_id: str,
        actor_id: str,
        asset_id: str,
        action: str,
        payload: Mapping[str, Any],
        verify_signature: bool = False,
    ) -> ChainOfCustodyEvent:
        """
        Create and record a single chain-of-custody event.

        If verify_signature is True and a signature_backend is present, the
        service verifies the signature before recording the event.
        """
        event = self.create_event(
            tenant_id=tenant_id,
            actor_id=actor_id,
            asset_id=asset_id,
            action=action,
            payload=payload,
        )

        if verify_signature and self._signature_backend is not None:
            phash_bytes = bytes.fromhex(event.payload_hash)
            signature_bytes = bytes.fromhex(event.signature or "")
            if not self._signature_backend.verify(phash_bytes, signature_bytes):
                raise ValueError("Signature verification failed for COC event")

        self._sink.record_event(event)
        return event

    def record_events_batch(
        self,
        events: Iterable[ChainOfCustodyEvent],
    ) -> None:
        """
        Record a batch of already-constructed events.
        """
        self._sink.record_events(events)
