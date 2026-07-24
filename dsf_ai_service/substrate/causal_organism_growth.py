"""Durable causal authority for bounded organism plasticity.

This journal does not decide meaning and does not retain sensor samples.  It
binds one already-verified full-field causal settlement to the organism
mechanisms that physically participated in accepting it.  A claim remains
pending until the cold structural graph proves the same claim id was applied.

The journal is deliberately capacity bounded.  It is not a lifetime
experience index: checkpointed claims are removed, recurrence contributes no
division energy, and the full explicit DSF field remains authoritative through
the upstream settlement receipt rather than being copied or flattened here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Iterable

from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


CAUSAL_GROWTH_CLAIM_SCHEMA = "guala.causal_organism_growth.claim.v1"
CAUSAL_GROWTH_STATE_SCHEMA = "guala.causal_organism_growth.state.v1"
CAUSAL_GROWTH_ORGAN_ORDER = (
    "em",
    "pr",
    "ep",
    "sc",
    "gp",
    "sf",
    "sv",
    "aff",
)
MAX_PENDING_CAUSAL_GROWTH_CLAIMS = 64
MAX_CAUSAL_GROWTH_STATE_BYTES = 2 * 1024 * 1024
_NOVEL_RELATIONS = frozenset(("first_observation", "structural_change"))


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hmac_sha256(key: bytes, value: object) -> str:
    return hmac.new(key, _canonical_bytes(value), hashlib.sha256).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a SHA-256 digest")
    return value


def _require_nonnegative_int(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class CausalOrganismGrowthClaim:
    """Compact authority for one novel causal plasticity contribution."""

    claim_id: str
    settlement_event_id: str
    settlement_structural_fingerprint: str
    settlement_authority_receipt_sha256: str
    engine_tick: int
    active_organs: tuple[str, ...]
    sense_relations: tuple[tuple[str, str, str, str], ...]
    contributes_division_energy: bool
    authority_hmac_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "active_organs": list(self.active_organs),
            "contributes_division_energy": self.contributes_division_energy,
            "engine_tick": self.engine_tick,
            "schema": CAUSAL_GROWTH_CLAIM_SCHEMA,
            "sense_relations": [list(value) for value in self.sense_relations],
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "settlement_event_id": self.settlement_event_id,
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
        }

    def persistence_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "claim_id": self.claim_id,
        }

    def verify(
        self,
        *,
        authority_key: bytes,
        allowed_organs: tuple[str, ...] = CAUSAL_GROWTH_ORGAN_ORDER,
    ) -> None:
        _require_sha256(self.claim_id, "causal growth claim id")
        _require_sha256(
            self.settlement_event_id,
            "causal growth settlement event id",
        )
        _require_sha256(
            self.settlement_structural_fingerprint,
            "causal growth structural fingerprint",
        )
        _require_sha256(
            self.settlement_authority_receipt_sha256,
            "causal growth settlement receipt",
        )
        _require_sha256(
            self.authority_hmac_sha256,
            "causal growth claim authority",
        )
        _require_nonnegative_int(self.engine_tick, "causal growth engine tick")
        if (
            not isinstance(self.active_organs, tuple)
            or not self.active_organs
            or any(value not in allowed_organs for value in self.active_organs)
            or self.active_organs
            != tuple(
                value for value in allowed_organs
                if value in frozenset(self.active_organs)
            )
        ):
            raise ValueError("causal growth active organs are not canonical")
        if (
            not isinstance(self.sense_relations, tuple)
            or len(self.sense_relations) != 6
            or any(
                not isinstance(value, tuple)
                or len(value) != 4
                or any(not isinstance(part, str) for part in value)
                for value in self.sense_relations
            )
        ):
            raise ValueError("causal growth sense relations changed")
        if not isinstance(self.contributes_division_energy, bool):
            raise ValueError("causal growth energy fact is not boolean")
        expected_novelty = any(
            state == "observed" and relation in _NOVEL_RELATIONS
            for _sense, state, relation, _fingerprint in self.sense_relations
        )
        if self.contributes_division_energy is not expected_novelty:
            raise ValueError("causal growth novelty differs from exact relations")
        unsigned = self.unsigned_record()
        if self.claim_id != _sha256(unsigned):
            raise ValueError("causal growth claim identity changed")
        if self.authority_hmac_sha256 != _hmac_sha256(
            authority_key,
            {"claim_id": self.claim_id, "claim": unsigned},
        ):
            raise ValueError("causal growth claim authority changed")


@dataclass(frozen=True, slots=True)
class CausalOrganismGrowthAdmission:
    observations: tuple[CausalOrganismGrowthClaim, ...]
    newly_journaled: tuple[CausalOrganismGrowthClaim, ...]
    prior_pending: tuple[CausalOrganismGrowthClaim, ...]


def _claim_from_record(
    value: object,
    *,
    authority_key: bytes,
    allowed_organs: tuple[str, ...],
) -> CausalOrganismGrowthClaim:
    if not isinstance(value, dict) or set(value) != {
        "active_organs",
        "authority_hmac_sha256",
        "claim_id",
        "contributes_division_energy",
        "engine_tick",
        "schema",
        "sense_relations",
        "settlement_authority_receipt_sha256",
        "settlement_event_id",
        "settlement_structural_fingerprint",
    }:
        raise ValueError("causal growth claim record changed")
    if value.get("schema") != CAUSAL_GROWTH_CLAIM_SCHEMA:
        raise ValueError("causal growth claim schema changed")
    active = value.get("active_organs")
    relations = value.get("sense_relations")
    if not isinstance(active, list) or not isinstance(relations, list):
        raise ValueError("causal growth claim collections changed")
    claim = CausalOrganismGrowthClaim(
        claim_id=value.get("claim_id"),
        settlement_event_id=value.get("settlement_event_id"),
        settlement_structural_fingerprint=value.get(
            "settlement_structural_fingerprint"
        ),
        settlement_authority_receipt_sha256=value.get(
            "settlement_authority_receipt_sha256"
        ),
        engine_tick=value.get("engine_tick"),
        active_organs=tuple(active),
        sense_relations=tuple(
            tuple(item) if isinstance(item, list) else item
            for item in relations
        ),
        contributes_division_energy=value.get(
            "contributes_division_energy"
        ),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    claim.verify(
        authority_key=authority_key,
        allowed_organs=allowed_organs,
    )
    return claim


class CausalOrganismGrowthJournal:
    """Bounded journal coordinated by the engine persistence transaction."""

    def __init__(
        self,
        *,
        authority_key: bytes,
        allowed_organs: tuple[str, ...] = CAUSAL_GROWTH_ORGAN_ORDER,
        max_pending: int = MAX_PENDING_CAUSAL_GROWTH_CLAIMS,
    ) -> None:
        if (
            not isinstance(authority_key, bytes)
            or len(authority_key) < hashlib.sha256().digest_size
        ):
            raise ValueError("causal growth authority key is invalid")
        if (
            not isinstance(allowed_organs, tuple)
            or not allowed_organs
            or len(set(allowed_organs)) != len(allowed_organs)
            or any(not isinstance(value, str) or not value for value in allowed_organs)
        ):
            raise ValueError("causal growth organ order is invalid")
        if (
            isinstance(max_pending, bool)
            or not isinstance(max_pending, int)
            or max_pending <= 0
        ):
            raise ValueError("causal growth pending capacity is invalid")
        self._authority_key = authority_key
        self._allowed_organs = allowed_organs
        self._max_pending = max_pending
        self._pending: tuple[CausalOrganismGrowthClaim, ...] = ()

    def _build_claim(
        self,
        settlement: CausalExperienceSettlement,
        *,
        engine_tick: int,
        active_organs: tuple[str, ...],
    ) -> CausalOrganismGrowthClaim:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("causal growth requires an exact settlement")
        settlement.verify()
        _require_nonnegative_int(engine_tick, "causal growth engine tick")
        canonical_active = tuple(
            value for value in self._allowed_organs
            if value in frozenset(active_organs)
        )
        if (
            not canonical_active
            or canonical_active != active_organs
            or len(canonical_active) != len(set(active_organs))
        ):
            raise ValueError("causal growth active organs are not canonical")
        sense_relations = tuple(
            (
                value.sense,
                value.state,
                value.relation,
                value.structural_fingerprint,
            )
            for value in settlement.interpretations
        )
        contributes = any(
            state == "observed" and relation in _NOVEL_RELATIONS
            for _sense, state, relation, _fingerprint in sense_relations
        )
        unsigned = {
            "active_organs": list(canonical_active),
            "contributes_division_energy": contributes,
            "engine_tick": engine_tick,
            "schema": CAUSAL_GROWTH_CLAIM_SCHEMA,
            "sense_relations": [list(value) for value in sense_relations],
            "settlement_authority_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "settlement_event_id": settlement.event_id,
            "settlement_structural_fingerprint": (
                settlement.structural_fingerprint
            ),
        }
        claim_id = _sha256(unsigned)
        claim = CausalOrganismGrowthClaim(
            claim_id=claim_id,
            settlement_event_id=settlement.event_id,
            settlement_structural_fingerprint=(
                settlement.structural_fingerprint
            ),
            settlement_authority_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            engine_tick=engine_tick,
            active_organs=canonical_active,
            sense_relations=sense_relations,
            contributes_division_energy=contributes,
            authority_hmac_sha256=_hmac_sha256(
                self._authority_key,
                {"claim_id": claim_id, "claim": unsigned},
            ),
        )
        claim.verify(
            authority_key=self._authority_key,
            allowed_organs=self._allowed_organs,
        )
        return claim

    def admit_episode(
        self,
        settlements: Iterable[CausalExperienceSettlement],
        *,
        engine_tick: int,
        active_organs: tuple[str, ...],
    ) -> CausalOrganismGrowthAdmission:
        immutable_settlements = tuple(settlements)
        if not immutable_settlements:
            raise ValueError("causal growth episode has no settlements")
        observations = tuple(
            self._build_claim(
                settlement,
                engine_tick=engine_tick,
                active_organs=active_organs,
            )
            for settlement in immutable_settlements
        )
        prior = self._pending
        known = {value.claim_id for value in prior}
        newly_journaled = tuple(
            value for value in observations
            if value.contributes_division_energy and value.claim_id not in known
        )
        if len(prior) + len(newly_journaled) > self._max_pending:
            raise RuntimeError("causal growth journal capacity is full")
        self._pending = prior + newly_journaled
        self.encoded_snapshot()
        return CausalOrganismGrowthAdmission(
            observations=observations,
            newly_journaled=newly_journaled,
            prior_pending=prior,
        )

    def rollback_admission(
        self,
        admission: CausalOrganismGrowthAdmission,
    ) -> None:
        if (
            not isinstance(admission, CausalOrganismGrowthAdmission)
            or self._pending
            != admission.prior_pending + admission.newly_journaled
        ):
            raise ValueError("causal growth rollback authority changed")
        self._pending = admission.prior_pending

    def acknowledge_checkpoint(
        self,
        applied_claim_ids: Iterable[str],
    ) -> tuple[CausalOrganismGrowthClaim, ...]:
        applied = frozenset(
            _require_sha256(value, "checkpointed causal growth claim")
            for value in applied_claim_ids
        )
        removed = tuple(
            value for value in self._pending if value.claim_id in applied
        )
        self._pending = tuple(
            value for value in self._pending if value.claim_id not in applied
        )
        return removed

    def reconcile_checkpoint(
        self,
        applied_claim_ids: Iterable[str],
    ) -> tuple[CausalOrganismGrowthClaim, ...]:
        self.acknowledge_checkpoint(applied_claim_ids)
        return self._pending

    def pending_claims(self) -> tuple[CausalOrganismGrowthClaim, ...]:
        return self._pending

    def encoded_snapshot(self) -> bytes:
        payload = {
            "allowed_organs": list(self._allowed_organs),
            "max_pending": self._max_pending,
            "pending": [value.persistence_record() for value in self._pending],
            "schema": CAUSAL_GROWTH_STATE_SCHEMA,
        }
        envelope = {
            "payload": payload,
            "state_hmac_sha256": _hmac_sha256(
                self._authority_key,
                payload,
            ),
        }
        encoded = _canonical_bytes(envelope)
        if len(encoded) > MAX_CAUSAL_GROWTH_STATE_BYTES:
            raise RuntimeError("causal growth state exceeds its byte boundary")
        return encoded

    def restore_encoded(self, encoded: bytes) -> None:
        inspect_causal_growth_snapshot(encoded)
        record = json.loads(encoded.decode("utf-8"))
        payload = record["payload"]
        if (
            payload.get("allowed_organs") != list(self._allowed_organs)
            or payload.get("max_pending") != self._max_pending
            or record.get("state_hmac_sha256")
            != _hmac_sha256(self._authority_key, payload)
        ):
            raise ValueError("causal growth state authority changed")
        pending = tuple(
            _claim_from_record(
                value,
                authority_key=self._authority_key,
                allowed_organs=self._allowed_organs,
            )
            for value in payload["pending"]
        )
        if len({value.claim_id for value in pending}) != len(pending):
            raise ValueError("causal growth state repeats a claim")
        self._pending = pending

    def status(self) -> dict[str, object]:
        return {
            "capacity": self._max_pending,
            "pending": len(self._pending),
            "pending_claim_ids": [
                value.claim_id for value in self._pending
            ],
            "schema": CAUSAL_GROWTH_STATE_SCHEMA,
        }


def inspect_causal_growth_snapshot(encoded: bytes) -> None:
    """Validate the unkeyed structural boundary before keyed restore."""
    if (
        not isinstance(encoded, bytes)
        or not encoded
        or len(encoded) > MAX_CAUSAL_GROWTH_STATE_BYTES
    ):
        raise ValueError("causal growth state boundary changed")
    try:
        record = json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("causal growth state is unreadable") from error
    if (
        not isinstance(record, dict)
        or set(record) != {"payload", "state_hmac_sha256"}
        or not isinstance(record.get("payload"), dict)
    ):
        raise ValueError("causal growth state envelope changed")
    _require_sha256(
        record["state_hmac_sha256"],
        "causal growth state authority",
    )
    payload = record["payload"]
    if (
        set(payload)
        != {"allowed_organs", "max_pending", "pending", "schema"}
        or payload.get("schema") != CAUSAL_GROWTH_STATE_SCHEMA
        or not isinstance(payload.get("allowed_organs"), list)
        or not isinstance(payload.get("max_pending"), int)
        or isinstance(payload.get("max_pending"), bool)
        or payload["max_pending"] <= 0
        or not isinstance(payload.get("pending"), list)
        or len(payload["pending"]) > payload["max_pending"]
    ):
        raise ValueError("causal growth state extent changed")
