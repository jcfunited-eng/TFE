"""Authenticated, bounded reflection over seven organism state owners.

The monitor has no decision, learning, recognition, or promotion authority.
It retains cryptographic facts about exact cold snapshots already produced by
the real owners and reports only whether those authenticated owner states
changed.  It never durably copies those snapshots.  Recent records roll
deterministically; an authenticated terminal anchor and count commit to the
evicted prefix without retaining it indefinitely.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
    ENVELOPE_SCHEMA as TAPESTRY_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.causal_recognition_attention import (
    CausalRecognitionAttentionOwner,
    ENVELOPE_SCHEMA as ATTENTION_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.causal_thing_action_intent import (
    CausalThingActionIntentOwner,
    ENVELOPE_SCHEMA as ACTION_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.durable_sensed_consequence import (
    DurableSensedConsequenceOwner,
    ENVELOPE_SCHEMA as CONSEQUENCE_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.live_ae_neurochemical_flow import (
    LiveAENeurochemicalFlowOwner,
    STATUS_SCHEMA as BODY_CHEMICAL_STATUS_SCHEMA,
)
from dsf_ai_service.substrate.whole_organism_neurochemical_mount import (
    ENVELOPE_SCHEMA as BODY_CHEMICAL_ENVELOPE_SCHEMA,
)
from dsf_ai_service.substrate.whole_organism_recovery_state import (
    COLD_SCHEMA as RECOVERY_ENVELOPE_SCHEMA,
    ExactWholeOrganismRecoveryOwner,
)
from dsf_ai_service.substrate.whole_organism_structural_perturbation import (
    OWNER_STATE_ENVELOPE_SCHEMA as STRUCTURAL_ENVELOPE_SCHEMA,
    WholeOrganismStructuralPerturbationOwner,
)


REFLECTION_SCHEMA = "guala.whole_organism.reflection.v3"
STATE_SCHEMA = "guala.whole_organism.reflection.state.v4"
STATUS_SCHEMA = "guala.whole_organism.reflection.status.v4"
_DOMAIN = b"guala-whole-organism-reflection-v3\0"
_STATE_DOMAIN = b"guala-whole-organism-reflection-state-v4\0"
_CONTRACT_DOMAIN = b"guala-whole-organism-reflection-contract-v2\0"
_CONSTRUCTION_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")

_OWNER_CONTRACTS = (
    (
        "action",
        CausalThingActionIntentOwner,
        ACTION_ENVELOPE_SCHEMA,
        "guala.causal_thing.action_intent.status.v1",
    ),
    (
        "attention-recognition",
        CausalRecognitionAttentionOwner,
        ATTENTION_ENVELOPE_SCHEMA,
        "guala.causal_recognition_attention.status.v1",
    ),
    (
        "body-chemical",
        LiveAENeurochemicalFlowOwner,
        BODY_CHEMICAL_ENVELOPE_SCHEMA,
        BODY_CHEMICAL_STATUS_SCHEMA,
    ),
    (
        "recovery",
        ExactWholeOrganismRecoveryOwner,
        RECOVERY_ENVELOPE_SCHEMA,
        "guala.whole_organism.recovery.status.v1",
    ),
    (
        "sensed-consequence",
        DurableSensedConsequenceOwner,
        CONSEQUENCE_ENVELOPE_SCHEMA,
        "guala.durable_sensed_consequence.status.v1",
    ),
    (
        "structural",
        WholeOrganismStructuralPerturbationOwner,
        STRUCTURAL_ENVELOPE_SCHEMA,
        None,
    ),
    (
        "tapestry",
        CausalMosaicTapestryOwner,
        TAPESTRY_ENVELOPE_SCHEMA,
        "guala.causal_mosaic_tapestry.status.v1",
    ),
)
REQUIRED_OWNER_IDS = tuple(value[0] for value in _OWNER_CONTRACTS)
_OWNER_CONTRACT_BY_ID = {
    value[0]: value[1:] for value in _OWNER_CONTRACTS
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _valid_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _HEX for character in value)
    )


def _contract_payload() -> dict[str, object]:
    return {
        "owners": [
            {
                "owner_class": (
                    f"{owner_type.__module__}.{owner_type.__qualname__}"
                ),
                "owner_id": owner_id,
                "snapshot_schema": snapshot_schema,
                "status_schema": status_schema,
            }
            for (
                owner_id,
                owner_type,
                snapshot_schema,
                status_schema,
            ) in _OWNER_CONTRACTS
        ],
        "schema": "guala.whole_organism.reflection.contract.v2",
    }


OWNER_CONTRACT_RECEIPT_SHA256 = hashlib.sha256(
    _CONTRACT_DOMAIN + _canonical(_contract_payload())
).hexdigest()


@dataclass(frozen=True, slots=True)
class WholeOrganismReflection:
    sequence: int
    moment_state: str
    changed_owner_ids: tuple[str, ...]
    prior_snapshot_sha256s: tuple[tuple[str, str], ...]
    current_snapshot_sha256s: tuple[tuple[str, str], ...]
    current_snapshot_byte_counts: tuple[tuple[str, int], ...]
    meta_health: str
    reasons: tuple[str, ...]
    owner_contract_receipt_sha256: str
    prior_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "changed_owner_ids": list(self.changed_owner_ids),
            "current_snapshot_sha256s": [
                list(value) for value in self.current_snapshot_sha256s
            ],
            "current_snapshot_byte_counts": [
                list(value) for value in self.current_snapshot_byte_counts
            ],
            "meta_health": self.meta_health,
            "moment_state": self.moment_state,
            "owner_contract_receipt_sha256": (
                self.owner_contract_receipt_sha256
            ),
            "prior_receipt_sha256": self.prior_receipt_sha256,
            "prior_snapshot_sha256s": [
                list(value) for value in self.prior_snapshot_sha256s
            ],
            "reasons": list(self.reasons),
            "schema": REFLECTION_SCHEMA,
            "sequence": self.sequence,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _Phase:
    value: str


@dataclass(frozen=True, slots=True)
class PreparedReflection:
    prior: tuple[WholeOrganismReflection, ...]
    prior_evicted_count: int
    prior_evicted_receipt_sha256: str | None
    prior_evicted_snapshot_sha256s: tuple[tuple[str, str], ...]
    staged: tuple[WholeOrganismReflection, ...]
    staged_evicted_count: int
    staged_evicted_receipt_sha256: str | None
    staged_evicted_snapshot_sha256s: tuple[tuple[str, str], ...]
    _owner_authority: object
    _construction_authority: object
    _phase: _Phase


@dataclass(frozen=True, slots=True)
class ReflectionUndo:
    _prepared: PreparedReflection
    _owner_authority: object
    _construction_authority: object


class WholeOrganismReflectionMonitorOwner:
    """Retain exact owner-state facts and a bounded authenticated suffix."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        owners: Mapping[str, object],
        max_history: int = 16,
        max_state_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        raw_key = (
            authority_key.encode("utf-8")
            if isinstance(authority_key, str)
            else authority_key
        )
        if not isinstance(raw_key, bytes) or len(raw_key) < 32:
            raise ValueError("reflection authority key is invalid")
        if (
            isinstance(max_history, bool)
            or not isinstance(max_history, int)
            or not 1 <= max_history <= 4_096
        ):
            raise ValueError("reflection history capacity is invalid")
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 2_048 <= max_state_bytes <= 512 * 1024 * 1024
        ):
            raise ValueError("reflection byte capacity is invalid")
        if not isinstance(owners, Mapping) or set(owners) != set(
            REQUIRED_OWNER_IDS
        ):
            raise ValueError("reflection is missing an exact required owner")
        retained: dict[str, object] = {}
        for owner_id in REQUIRED_OWNER_IDS:
            owner = owners[owner_id]
            expected_type = _OWNER_CONTRACT_BY_ID[owner_id][0]
            if type(owner) is not expected_type:
                raise TypeError(
                    f"reflection owner type changed:{owner_id}"
                )
            retained[owner_id] = owner
        self._key = hashlib.sha256(_DOMAIN + raw_key).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + raw_key
        ).digest()
        self._owners = retained
        self._max_history = max_history
        self._max_state_bytes = max_state_bytes
        self._records: tuple[WholeOrganismReflection, ...] = ()
        self._evicted_count = 0
        self._evicted_receipt_sha256: str | None = None
        self._evicted_snapshot_sha256s: tuple[
            tuple[str, str], ...
        ] = ()
        self._prepared: PreparedReflection | None = None
        self._owner_authority = object()
        self._lock = threading.RLock()
        self._encoded_current()

    def _owner_snapshot(
        self,
        owner_id: str,
    ) -> tuple[bytes, tuple[str, ...]]:
        owner = self._owners[owner_id]
        _, snapshot_schema, status_schema = _OWNER_CONTRACT_BY_ID[
            owner_id
        ]
        snapshot = owner.snapshot_encoded()
        if not isinstance(snapshot, bytes) or not snapshot:
            raise ValueError(
                f"reflection owner snapshot absent:{owner_id}"
            )
        try:
            envelope = json.loads(snapshot)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                f"reflection owner snapshot unreadable:{owner_id}"
            ) from error
        if (
            not isinstance(envelope, dict)
            or envelope.get("schema") != snapshot_schema
            or _canonical(envelope) != snapshot
        ):
            raise ValueError(
                f"reflection owner snapshot authority changed:{owner_id}"
            )

        reasons: list[str] = []
        if owner_id == "structural":
            current_state = owner.current_state
            if owner.in_flight is not None:
                reasons.append("structural:mutation_in_flight")
            if not _valid_sha(
                current_state.authority_receipt_sha256
            ):
                reasons.append("structural:state_authority_missing")
            return snapshot, tuple(reasons)

        status = owner.status()
        if (
            not isinstance(status, Mapping)
            or status.get("schema") != status_schema
        ):
            reasons.append(f"{owner_id}:status_authority_changed")
            return snapshot, tuple(reasons)
        state_bytes = status.get("state_bytes")
        state_capacity = status.get("state_capacity_bytes")
        if state_bytes is not None and state_bytes != len(snapshot):
            reasons.append(f"{owner_id}:state_byte_count_changed")
        if (
            state_capacity is not None
            and (
                isinstance(state_capacity, bool)
                or not isinstance(state_capacity, int)
                or state_capacity < len(snapshot)
            )
        ):
            reasons.append(f"{owner_id}:state_capacity_exceeded")
        mechanism_state = status.get("mechanism_state")
        if mechanism_state is not None and mechanism_state not in {
            "perturbed",
            "quiescent",
            "unavailable",
        }:
            reasons.append(f"{owner_id}:moment_state_changed")
        if owner_id in {
            "action",
            "attention-recognition",
            "tapestry",
        } and (
            status.get("full_field") is not True
            or status.get("reduced_approximation") is not False
        ):
            reasons.append(f"{owner_id}:full_field_custody_missing")
        return snapshot, tuple(reasons)

    def _snapshot_all(
        self,
    ) -> tuple[tuple[tuple[str, bytes], ...], tuple[str, ...]]:
        snapshots: list[tuple[str, bytes]] = []
        reasons: list[str] = []
        for owner_id in REQUIRED_OWNER_IDS:
            snapshot, owner_reasons = self._owner_snapshot(owner_id)
            snapshots.append((owner_id, snapshot))
            reasons.extend(owner_reasons)
        return tuple(snapshots), tuple(reasons)

    def _seal(
        self,
        *,
        sequence: int,
        moment_state: str,
        changed_owner_ids: tuple[str, ...],
        prior_snapshot_sha256s: tuple[tuple[str, str], ...],
        current_snapshot_sha256s: tuple[tuple[str, str], ...],
        current_snapshot_byte_counts: tuple[tuple[str, int], ...],
        meta_health: str,
        reasons: tuple[str, ...],
        prior_receipt_sha256: str | None,
    ) -> WholeOrganismReflection:
        provisional = WholeOrganismReflection(
            sequence=sequence,
            moment_state=moment_state,
            changed_owner_ids=changed_owner_ids,
            prior_snapshot_sha256s=prior_snapshot_sha256s,
            current_snapshot_sha256s=current_snapshot_sha256s,
            current_snapshot_byte_counts=current_snapshot_byte_counts,
            meta_health=meta_health,
            reasons=reasons,
            owner_contract_receipt_sha256=(
                OWNER_CONTRACT_RECEIPT_SHA256
            ),
            prior_receipt_sha256=prior_receipt_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismReflection(
            sequence=provisional.sequence,
            moment_state=provisional.moment_state,
            changed_owner_ids=provisional.changed_owner_ids,
            prior_snapshot_sha256s=(
                provisional.prior_snapshot_sha256s
            ),
            current_snapshot_sha256s=(
                provisional.current_snapshot_sha256s
            ),
            current_snapshot_byte_counts=(
                provisional.current_snapshot_byte_counts
            ),
            meta_health=provisional.meta_health,
            reasons=provisional.reasons,
            owner_contract_receipt_sha256=(
                provisional.owner_contract_receipt_sha256
            ),
            prior_receipt_sha256=provisional.prior_receipt_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _body(
        self,
        records: tuple[WholeOrganismReflection, ...],
        evicted_count: int,
        evicted_receipt_sha256: str | None,
        evicted_snapshot_sha256s: tuple[tuple[str, str], ...],
    ) -> dict[str, object]:
        return {
            "evicted_prefix_count": evicted_count,
            "evicted_prefix_receipt_sha256": (
                evicted_receipt_sha256
            ),
            "evicted_prefix_snapshot_sha256s": [
                list(value) for value in evicted_snapshot_sha256s
            ],
            "max_history": self._max_history,
            "owner_contract": _contract_payload(),
            "owner_contract_receipt_sha256": (
                OWNER_CONTRACT_RECEIPT_SHA256
            ),
            "records": [value.record() for value in records],
            "schema": STATE_SCHEMA,
        }

    def _encode_unbounded(
        self,
        records: tuple[WholeOrganismReflection, ...],
        evicted_count: int,
        evicted_receipt_sha256: str | None,
        evicted_snapshot_sha256s: tuple[tuple[str, str], ...],
    ) -> bytes:
        body = self._body(
            records,
            evicted_count,
            evicted_receipt_sha256,
            evicted_snapshot_sha256s,
        )
        return _canonical({
            "body": body,
            "schema": STATE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })

    def _encoded(
        self,
        records: tuple[WholeOrganismReflection, ...],
        evicted_count: int,
        evicted_receipt_sha256: str | None,
        evicted_snapshot_sha256s: tuple[tuple[str, str], ...],
    ) -> bytes:
        encoded = self._encode_unbounded(
            records,
            evicted_count,
            evicted_receipt_sha256,
            evicted_snapshot_sha256s,
        )
        if len(records) > self._max_history:
            raise RuntimeError(
                "reflection retained history exceeds capacity"
            )
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError("reflection state capacity exhausted")
        return encoded

    def _encoded_current(self) -> bytes:
        return self._encoded(
            self._records,
            self._evicted_count,
            self._evicted_receipt_sha256,
            self._evicted_snapshot_sha256s,
        )

    @staticmethod
    def _evict_oldest(
        records: tuple[WholeOrganismReflection, ...],
        evicted_count: int,
    ) -> tuple[
        tuple[WholeOrganismReflection, ...],
        int,
        str,
        tuple[tuple[str, str], ...],
    ]:
        if len(records) <= 1:
            raise RuntimeError(
                "reflection current exact snapshot exceeds byte capacity"
            )
        evicted = records[0]
        if evicted.sequence != evicted_count + 1:
            raise ValueError("reflection eviction sequence changed")
        return (
            records[1:],
            evicted_count + 1,
            evicted.authority_receipt_sha256,
            evicted.current_snapshot_sha256s,
        )

    def prepare(self) -> PreparedReflection:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "reflection mutation is already in flight"
                )
            snapshots, reasons = self._snapshot_all()
            current_hashes = tuple(
                (owner_id, hashlib.sha256(snapshot).hexdigest())
                for owner_id, snapshot in snapshots
            )
            if self._records:
                prior_hashes = (
                    self._records[-1].current_snapshot_sha256s
                )
                prior_receipt = (
                    self._records[-1].authority_receipt_sha256
                )
            else:
                prior_hashes = self._evicted_snapshot_sha256s
                prior_receipt = self._evicted_receipt_sha256
            prior_by_id = dict(prior_hashes)
            changed_owner_ids = (
                ()
                if not prior_hashes
                else tuple(
                    owner_id
                    for owner_id, snapshot_hash in current_hashes
                    if prior_by_id.get(owner_id) != snapshot_hash
                )
            )
            reflection = self._seal(
                sequence=(
                    self._evicted_count + len(self._records) + 1
                ),
                moment_state=(
                    "perturbed" if changed_owner_ids else "quiescent"
                ),
                changed_owner_ids=changed_owner_ids,
                prior_snapshot_sha256s=prior_hashes,
                current_snapshot_sha256s=current_hashes,
                current_snapshot_byte_counts=tuple(
                    (owner_id, len(snapshot))
                    for owner_id, snapshot in snapshots
                ),
                meta_health=(
                    "fail_closed" if reasons else "healthy"
                ),
                reasons=reasons,
                prior_receipt_sha256=prior_receipt,
            )
            staged = self._records + (reflection,)
            staged_count = self._evicted_count
            staged_receipt = self._evicted_receipt_sha256
            staged_hashes = self._evicted_snapshot_sha256s
            while len(staged) > self._max_history:
                (
                    staged,
                    staged_count,
                    staged_receipt,
                    staged_hashes,
                ) = self._evict_oldest(staged, staged_count)
            while (
                len(self._encode_unbounded(
                    staged,
                    staged_count,
                    staged_receipt,
                    staged_hashes,
                ))
                > self._max_state_bytes
            ):
                (
                    staged,
                    staged_count,
                    staged_receipt,
                    staged_hashes,
                ) = self._evict_oldest(staged, staged_count)
            prepared = PreparedReflection(
                prior=self._records,
                prior_evicted_count=self._evicted_count,
                prior_evicted_receipt_sha256=(
                    self._evicted_receipt_sha256
                ),
                prior_evicted_snapshot_sha256s=(
                    self._evicted_snapshot_sha256s
                ),
                staged=staged,
                staged_evicted_count=staged_count,
                staged_evicted_receipt_sha256=staged_receipt,
                staged_evicted_snapshot_sha256s=staged_hashes,
                _owner_authority=self._owner_authority,
                _construction_authority=_CONSTRUCTION_AUTHORITY,
                _phase=_Phase("prepared"),
            )
            self._encoded(
                prepared.staged,
                prepared.staged_evicted_count,
                prepared.staged_evicted_receipt_sha256,
                prepared.staged_evicted_snapshot_sha256s,
            )
            self._prepared = prepared
            return prepared

    def _verify_prepared(
        self,
        prepared: PreparedReflection,
        *,
        phase: str,
    ) -> None:
        if (
            not isinstance(prepared, PreparedReflection)
            or prepared._construction_authority
            is not _CONSTRUCTION_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or prepared._phase.value != phase
        ):
            raise ValueError(
                "reflection preparation authority changed"
            )

    def _matches_prior(self, prepared: PreparedReflection) -> bool:
        return (
            self._records == prepared.prior
            and self._evicted_count == prepared.prior_evicted_count
            and self._evicted_receipt_sha256
            == prepared.prior_evicted_receipt_sha256
            and self._evicted_snapshot_sha256s
            == prepared.prior_evicted_snapshot_sha256s
        )

    def _matches_staged(self, prepared: PreparedReflection) -> bool:
        return (
            self._records == prepared.staged
            and self._evicted_count == prepared.staged_evicted_count
            and self._evicted_receipt_sha256
            == prepared.staged_evicted_receipt_sha256
            and self._evicted_snapshot_sha256s
            == prepared.staged_evicted_snapshot_sha256s
        )

    def commit(self, prepared: PreparedReflection) -> ReflectionUndo:
        with self._lock:
            self._verify_prepared(prepared, phase="prepared")
            if prepared is not self._prepared or not self._matches_prior(
                prepared
            ):
                raise ValueError("reflection preparation is stale")
            self._encoded(
                prepared.staged,
                prepared.staged_evicted_count,
                prepared.staged_evicted_receipt_sha256,
                prepared.staged_evicted_snapshot_sha256s,
            )
            self._records = prepared.staged
            self._evicted_count = prepared.staged_evicted_count
            self._evicted_receipt_sha256 = (
                prepared.staged_evicted_receipt_sha256
            )
            self._evicted_snapshot_sha256s = (
                prepared.staged_evicted_snapshot_sha256s
            )
            self._prepared = None
            prepared._phase.value = "committed"
            return ReflectionUndo(
                _prepared=prepared,
                _owner_authority=self._owner_authority,
                _construction_authority=_CONSTRUCTION_AUTHORITY,
            )

    def discard(self, prepared: PreparedReflection) -> None:
        with self._lock:
            self._verify_prepared(prepared, phase="prepared")
            if prepared is not self._prepared:
                raise ValueError("reflection preparation is stale")
            self._prepared = None
            prepared._phase.value = "discarded"

    def rollback(self, undo: ReflectionUndo) -> None:
        with self._lock:
            if (
                not isinstance(undo, ReflectionUndo)
                or undo._construction_authority
                is not _CONSTRUCTION_AUTHORITY
                or undo._owner_authority is not self._owner_authority
            ):
                raise ValueError("reflection rollback authority changed")
            prepared = undo._prepared
            self._verify_prepared(prepared, phase="committed")
            if self._prepared is not None or not self._matches_staged(
                prepared
            ):
                raise ValueError("reflection rollback is stale")
            self._encoded(
                prepared.prior,
                prepared.prior_evicted_count,
                prepared.prior_evicted_receipt_sha256,
                prepared.prior_evicted_snapshot_sha256s,
            )
            self._records = prepared.prior
            self._evicted_count = prepared.prior_evicted_count
            self._evicted_receipt_sha256 = (
                prepared.prior_evicted_receipt_sha256
            )
            self._evicted_snapshot_sha256s = (
                prepared.prior_evicted_snapshot_sha256s
            )
            prepared._phase.value = "rolled_back"

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("reflection mutation is in flight")
            return self._encoded_current()

    @property
    def current_reflection(self) -> WholeOrganismReflection | None:
        with self._lock:
            return None if not self._records else self._records[-1]

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded_current()
            current = None if not self._records else self._records[-1]
            return {
                "decision_authority": False,
                "earliest_retained_sequence": (
                    None
                    if not self._records
                    else self._records[0].sequence
                ),
                "evicted_prefix_count": self._evicted_count,
                "evicted_prefix_receipt_sha256": (
                    self._evicted_receipt_sha256
                ),
                "full_field_reduction": False,
                "latest_sequence": (
                    0 if current is None else current.sequence
                ),
                "mechanism_state": (
                    "quiescent"
                    if current is None
                    else current.moment_state
                ),
                "meta_health": (
                    "healthy"
                    if current is None
                    else current.meta_health
                ),
                "owner_contract_receipt_sha256": (
                    OWNER_CONTRACT_RECEIPT_SHA256
                ),
                "owner_count": len(REQUIRED_OWNER_IDS),
                "records": len(self._records),
                "history_capacity": self._max_history,
                "schema": STATUS_SCHEMA,
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._max_state_bytes,
                "estimated_maximum_state_bytes": (
                    self._max_state_bytes
                ),
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        owners: Mapping[str, object],
        encoded: bytes,
        max_state_bytes: int = 64 * 1024 * 1024,
    ) -> "WholeOrganismReflectionMonitorOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("reflection cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "reflection cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != STATE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("reflection cold envelope changed")
        body = envelope.get("body")
        expected_fields = {
            "evicted_prefix_count",
            "evicted_prefix_receipt_sha256",
            "evicted_prefix_snapshot_sha256s",
            "max_history",
            "owner_contract",
            "owner_contract_receipt_sha256",
            "records",
            "schema",
        }
        if (
            not isinstance(body, dict)
            or set(body) != expected_fields
            or body.get("schema") != STATE_SCHEMA
            or body.get("owner_contract") != _contract_payload()
            or body.get("owner_contract_receipt_sha256")
            != OWNER_CONTRACT_RECEIPT_SHA256
            or not isinstance(body.get("records"), list)
        ):
            raise ValueError("reflection cold payload changed")
        owner = cls(
            authority_key=authority_key,
            owners=owners,
            max_history=body.get("max_history"),
            max_state_bytes=max_state_bytes,
        )
        expected_state_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_state_hmac,
        ):
            raise ValueError("reflection cold authority changed")
        count = body["evicted_prefix_count"]
        receipt = body["evicted_prefix_receipt_sha256"]
        try:
            hashes = tuple(
                tuple(value)
                for value in body[
                    "evicted_prefix_snapshot_sha256s"
                ]
            )
        except TypeError as error:
            raise ValueError(
                "reflection cold prefix anchor changed"
            ) from error
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            or (
                count == 0
                and (receipt is not None or hashes)
            )
            or (
                count > 0
                and (
                    not _valid_sha(receipt)
                    or not owner._valid_hash_pairs(hashes)
                )
            )
        ):
            raise ValueError(
                "reflection cold prefix anchor changed"
            )
        records = tuple(
            owner._reflection_from_record(value)
            for value in body["records"]
        )
        if (
            len(records) > owner._max_history
            or (count > 0 and not records)
        ):
            raise ValueError(
                "reflection cold retained history changed"
            )
        owner._verify_history(records, count, receipt, hashes)
        owner._records = records
        owner._evicted_count = count
        owner._evicted_receipt_sha256 = receipt
        owner._evicted_snapshot_sha256s = hashes
        if records:
            live_snapshots, live_reasons = owner._snapshot_all()
            if live_reasons != records[-1].reasons:
                raise ValueError(
                    "reflection restored owner health changed"
                )
            if tuple(
                (owner_id, hashlib.sha256(snapshot).hexdigest())
                for owner_id, snapshot in live_snapshots
            ) != records[-1].current_snapshot_sha256s:
                raise ValueError(
                    "reflection restored owner state changed"
                )
            if tuple(
                (owner_id, len(snapshot))
                for owner_id, snapshot in live_snapshots
            ) != records[-1].current_snapshot_byte_counts:
                raise ValueError(
                    "reflection restored owner state changed"
                )
        if owner.snapshot_encoded() != encoded:
            raise ValueError("reflection cold round-trip changed")
        return owner

    def _reflection_from_record(
        self,
        value: object,
    ) -> WholeOrganismReflection:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "changed_owner_ids",
            "current_snapshot_byte_counts",
            "current_snapshot_sha256s",
            "meta_health",
            "moment_state",
            "owner_contract_receipt_sha256",
            "prior_receipt_sha256",
            "prior_snapshot_sha256s",
            "reasons",
            "schema",
            "sequence",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != REFLECTION_SCHEMA
        ):
            raise ValueError("reflection record shape changed")
        try:
            record = WholeOrganismReflection(
                sequence=value["sequence"],
                moment_state=value["moment_state"],
                changed_owner_ids=tuple(value["changed_owner_ids"]),
                prior_snapshot_sha256s=tuple(
                    tuple(item)
                    for item in value["prior_snapshot_sha256s"]
                ),
                current_snapshot_sha256s=tuple(
                    tuple(item)
                    for item in value["current_snapshot_sha256s"]
                ),
                current_snapshot_byte_counts=tuple(
                    tuple(item)
                    for item in value["current_snapshot_byte_counts"]
                ),
                meta_health=value["meta_health"],
                reasons=tuple(value["reasons"]),
                owner_contract_receipt_sha256=(
                    value["owner_contract_receipt_sha256"]
                ),
                prior_receipt_sha256=value[
                    "prior_receipt_sha256"
                ],
                authority_hmac_sha256=value[
                    "authority_hmac_sha256"
                ],
                authority_receipt_sha256=value[
                    "authority_receipt_sha256"
                ],
            )
        except (KeyError, TypeError) as error:
            raise ValueError(
                "reflection record fields changed"
            ) from error
        expected_hmac = hmac.new(
            self._key,
            _DOMAIN + _canonical(record.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                record.authority_hmac_sha256,
                expected_hmac,
            )
            or record.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": record.payload(),
            })
        ):
            raise ValueError("reflection record authority changed")
        return record

    @staticmethod
    def _valid_hash_pairs(
        values: tuple[tuple[str, str], ...],
    ) -> bool:
        return (
            len(values) == len(REQUIRED_OWNER_IDS)
            and tuple(owner_id for owner_id, _ in values)
            == REQUIRED_OWNER_IDS
            and all(_valid_sha(value) for _, value in values)
        )

    @staticmethod
    def _valid_byte_count_pairs(
        values: tuple[tuple[str, int], ...],
    ) -> bool:
        return (
            len(values) == len(REQUIRED_OWNER_IDS)
            and tuple(owner_id for owner_id, _ in values)
            == REQUIRED_OWNER_IDS
            and all(
                not isinstance(value, bool)
                and isinstance(value, int)
                and value > 0
                for _, value in values
            )
        )

    def _verify_history(
        self,
        records: tuple[WholeOrganismReflection, ...],
        evicted_count: int,
        evicted_receipt_sha256: str | None,
        evicted_snapshot_sha256s: tuple[tuple[str, str], ...],
    ) -> None:
        prior_receipt = evicted_receipt_sha256
        prior_hashes = evicted_snapshot_sha256s
        for index, record in enumerate(
            records,
            start=evicted_count + 1,
        ):
            if (
                record.sequence != index
                or record.owner_contract_receipt_sha256
                != OWNER_CONTRACT_RECEIPT_SHA256
                or record.moment_state
                not in {"quiescent", "perturbed"}
                or record.meta_health
                not in {"healthy", "fail_closed"}
                or (record.meta_health == "healthy")
                != (not record.reasons)
                or not self._valid_hash_pairs(
                    record.current_snapshot_sha256s
                )
                or not self._valid_byte_count_pairs(
                    record.current_snapshot_byte_counts
                )
            ):
                raise ValueError(
                    "reflection record semantics changed"
                )
            prior_by_id = dict(prior_hashes)
            expected_changed = (
                ()
                if not prior_hashes
                else tuple(
                    owner_id
                    for owner_id, snapshot_hash in (
                        record.current_snapshot_sha256s
                    )
                    if prior_by_id.get(owner_id) != snapshot_hash
                )
            )
            if (
                record.prior_snapshot_sha256s != prior_hashes
                or record.prior_receipt_sha256 != prior_receipt
                or record.changed_owner_ids != expected_changed
                or record.moment_state
                != (
                    "perturbed"
                    if expected_changed
                    else "quiescent"
                )
            ):
                raise ValueError("reflection continuity changed")
            prior_receipt = record.authority_receipt_sha256
            prior_hashes = record.current_snapshot_sha256s


__all__ = (
    "OWNER_CONTRACT_RECEIPT_SHA256",
    "PreparedReflection",
    "REFLECTION_SCHEMA",
    "REQUIRED_OWNER_IDS",
    "ReflectionUndo",
    "STATE_SCHEMA",
    "STATUS_SCHEMA",
    "WholeOrganismReflection",
    "WholeOrganismReflectionMonitorOwner",
)
