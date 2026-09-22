"""Bounded durable custody for complete whole-organism consequences."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field

from dsf_ai_service.substrate.whole_organism_episode import (
    DownstreamAuthority,
    MechanismKind,
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodeCapability,
    WholeOrganismEpisodePhase,
)

SCHEMA = "guala.durable_sensed_consequence.record.v1"
STATE_SCHEMA = "guala.durable_sensed_consequence.state.v1"
ENVELOPE_SCHEMA = "guala.durable_sensed_consequence.state_hmac.v1"
_RECORD_DOMAIN = b"guala-durable-sensed-consequence-v1\0"
_STATE_DOMAIN = b"guala-durable-sensed-consequence-state-v1\0"


def _canonical(value: object) -> bytes:
    return json.dumps(value, allow_nan=False, ensure_ascii=False,
                      separators=(",", ":"), sort_keys=True).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    raw = value.encode() if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4096:
        raise ValueError("sensed-consequence key changed")
    return hashlib.sha256(_RECORD_DOMAIN + raw).digest()


@dataclass(frozen=True, slots=True)
class DurableSensedConsequence:
    sequence: int
    episode_receipt_sha256: str
    episode_record_json: str
    body_contribution_json: str
    recovery_contribution_json: str
    prior_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "body_contribution_json": self.body_contribution_json,
            "episode_receipt_sha256": self.episode_receipt_sha256,
            "episode_record_json": self.episode_record_json,
            "prior_receipt_sha256": self.prior_receipt_sha256,
            "recovery_contribution_json": self.recovery_contribution_json,
            "schema": SCHEMA,
            "sequence": self.sequence,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedDurableSensedConsequence:
    prior: tuple[DurableSensedConsequence, ...]
    staged: tuple[DurableSensedConsequence, ...]


@dataclass(frozen=True, slots=True)
class DurableSensedConsequenceUndo:
    prepared: PreparedDurableSensedConsequence = field(repr=False)


class DurableSensedConsequenceOwner:
    def __init__(
        self, *, authority_key: bytes | str,
        episode_authority: WholeOrganismEpisodeAuthority,
        body_mechanism_id: str = "state:internal-physical-chemical",
        recovery_mechanism_id: str = "state:recovery",
        max_records: int = 32, max_state_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        if not isinstance(episode_authority, WholeOrganismEpisodeAuthority):
            raise TypeError("sensed consequence requires episode authority")
        if not 1 <= max_records <= 4096 or not 1 <= max_state_bytes:
            raise ValueError("sensed consequence capacity changed")
        specs = {
            v.mechanism_id: v for v in episode_authority.manifest.mechanisms
        }
        if (
            body_mechanism_id not in specs
            or recovery_mechanism_id not in specs
            or specs[body_mechanism_id].kind
            is MechanismKind.RECEPTOR_FAMILY
            or specs[recovery_mechanism_id].kind
            is MechanismKind.RECEPTOR_FAMILY
        ):
            raise ValueError("sensed consequence body/recovery anatomy absent")
        self._key = _key(authority_key)
        self._state_key = hashlib.sha256(_STATE_DOMAIN + self._key).digest()
        self._episodes = episode_authority
        self._body_id = body_mechanism_id
        self._recovery_id = recovery_mechanism_id
        self._max_records = max_records
        self._max_bytes = max_state_bytes
        self._records: tuple[DurableSensedConsequence, ...] = ()
        self._prepared: PreparedDurableSensedConsequence | None = None
        self._lock = threading.RLock()

    @property
    def records(self) -> tuple[DurableSensedConsequence, ...]:
        return self._records

    def _verify(self, value: DurableSensedConsequence) -> None:
        episode = self._episodes.require(
            self._episodes.capability_for(value.episode_receipt_sha256),
            DownstreamAuthority.LEARNING,
        )
        contributions = {v.mechanism_id: v for v in episode.contributions}
        specs = self._episodes.manifest.mechanisms
        receptors = [v for v in specs if v.kind is MechanismKind.RECEPTOR_FAMILY]
        if (
            episode.phase is not WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED
            or episode.action_authority_receipt_sha256 is None
            or episode.action_execution_receipt_sha256 is None
            or episode.prior_episode_receipt_sha256 is None
            or not episode.full_field_roots
            or any(v.mechanism_id not in contributions for v in receptors)
            or self._body_id not in contributions
            or self._recovery_id not in contributions
            or value.episode_record_json
            != _canonical(episode.record()).decode()
            or value.body_contribution_json
            != _canonical(contributions[self._body_id].record()).decode()
            or value.recovery_contribution_json
            != _canonical(contributions[self._recovery_id].record()).decode()
        ):
            raise ValueError("sensed consequence left complete causal custody")
        expected = hmac.new(
            self._key, _RECORD_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({"authority_hmac_sha256": expected,
                        "payload": value.payload()})
        ):
            raise ValueError("sensed consequence authority changed")

    def prepare(
        self, capability: WholeOrganismEpisodeCapability,
    ) -> PreparedDurableSensedConsequence:
        episode = self._episodes.require(capability, DownstreamAuthority.LEARNING)
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("sensed consequence already prepared")
            if any(v.episode_receipt_sha256 == episode.authority_receipt_sha256
                   for v in self._records):
                raise ValueError("sensed consequence episode already retained")
            contributions = {v.mechanism_id: v for v in episode.contributions}
            provisional = DurableSensedConsequence(
                sequence=len(self._records) + 1,
                episode_receipt_sha256=episode.authority_receipt_sha256,
                episode_record_json=_canonical(episode.record()).decode(),
                body_contribution_json=_canonical(
                    contributions.get(self._body_id, {}).record()
                    if self._body_id in contributions else {}
                ).decode(),
                recovery_contribution_json=_canonical(
                    contributions.get(self._recovery_id, {}).record()
                    if self._recovery_id in contributions else {}
                ).decode(),
                prior_receipt_sha256=(
                    None if not self._records
                    else self._records[-1].authority_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._key, _RECORD_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            record = DurableSensedConsequence(
                **{n: getattr(provisional, n)
                   for n in provisional.__dataclass_fields__
                   if n not in {"authority_hmac_sha256",
                                "authority_receipt_sha256"}},
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._verify(record)
            if len(self._records) >= self._max_records:
                raise RuntimeError("sensed consequence capacity exhausted")
            prepared = PreparedDurableSensedConsequence(
                self._records, self._records + (record,)
            )
            self._encoded(prepared.staged)
            self._prepared = prepared
            return prepared

    def commit(self, prepared: PreparedDurableSensedConsequence
               ) -> DurableSensedConsequenceUndo:
        with self._lock:
            if self._prepared != prepared or self._records != prepared.prior:
                raise ValueError("prepared sensed consequence is not current")
            for value in prepared.staged:
                self._verify(value)
            self._records = prepared.staged
            self._prepared = None
            return DurableSensedConsequenceUndo(prepared)

    def discard(self, prepared: PreparedDurableSensedConsequence) -> None:
        with self._lock:
            if self._prepared != prepared:
                raise ValueError("prepared sensed consequence is not current")
            self._prepared = None

    def rollback(self, undo: DurableSensedConsequenceUndo) -> None:
        with self._lock:
            if self._prepared is not None or self._records != undo.prepared.staged:
                raise ValueError("sensed consequence rollback is stale")
            self._records = undo.prepared.prior

    def _encoded(self, records: tuple[DurableSensedConsequence, ...]) -> bytes:
        body = {"records": [v.record() for v in records],
                "schema": STATE_SCHEMA}
        encoded = _canonical({
            "body": body, "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key, _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._max_bytes:
            raise RuntimeError("sensed consequence state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("sensed consequence mutation in flight")
            return self._encoded(self._records)

    def status(self) -> dict[str, object]:
        encoded = self.snapshot_encoded()
        return {
            "mechanism_state": (
                "quiescent" if not self._records else "perturbed"
            ),
            "records": len(self._records),
            "state_bytes": len(encoded),
            "state_capacity_bytes": self._max_bytes,
            "meaning_authority": False,
            "recognition_authority": False,
            "schema": "guala.durable_sensed_consequence.status.v1",
        }

    @classmethod
    def restore_encoded(cls, *, authority_key, episode_authority,
                        encoded, **kwargs):
        raw = json.loads(encoded)
        owner = cls(authority_key=authority_key,
                    episode_authority=episode_authority, **kwargs)
        body = raw.get("body")
        expected = hmac.new(owner._state_key,
                            _STATE_DOMAIN + _canonical(body),
                            hashlib.sha256).hexdigest()
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != ENVELOPE_SCHEMA
            or _canonical(raw) != encoded
            or not isinstance(body, dict)
            or body.get("schema") != STATE_SCHEMA
            or not hmac.compare_digest(raw.get("state_hmac_sha256", ""),
                                       expected)
        ):
            raise ValueError("sensed consequence cold authority changed")
        values = []
        for item in body.get("records", []):
            values.append(DurableSensedConsequence(
                sequence=item["sequence"],
                episode_receipt_sha256=item["episode_receipt_sha256"],
                episode_record_json=item["episode_record_json"],
                body_contribution_json=item["body_contribution_json"],
                recovery_contribution_json=item["recovery_contribution_json"],
                prior_receipt_sha256=item["prior_receipt_sha256"],
                authority_hmac_sha256=item["authority_hmac_sha256"],
                authority_receipt_sha256=item["authority_receipt_sha256"],
            ))
        owner._records = tuple(values)
        for value in owner._records:
            owner._verify(value)
        if owner.snapshot_encoded() != encoded:
            raise ValueError("sensed consequence cold round-trip changed")
        return owner


__all__ = (
    "DurableSensedConsequence",
    "DurableSensedConsequenceOwner",
    "DurableSensedConsequenceUndo",
    "PreparedDurableSensedConsequence",
)
