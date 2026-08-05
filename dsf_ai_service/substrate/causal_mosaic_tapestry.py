"""Bounded causal tapestry growth over authenticated mosaic relations.

A tapestry is retained only when one authenticated learned mosaic occurrence
is the exact predecessor of another within the same custody-derived physical
entity-continuity lane.  Episode history is not rewritten to express this
separate organism continuity.  The resulting structure preserves both
records' complete explicit D/M/R/U/C/P/B roots and causal order.  When two
retained tapestry edges themselves form an exact causal path, their relation
is retained as tapestry-to-tapestry topology.

Nothing in this owner names a concept, compares signals, counts repetitions,
or promotes a record because a threshold was crossed.  Re-admitting the same
observed relation is truthful quiescence.  Unrelated records cannot be sealed
as an observation.  State is fixed-capacity, atomic, and HMAC cold-restorable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import FullFieldSensoryRoot


PROFILE_SCHEMA = "guala.causal_mosaic_tapestry.profile.v1"
OBSERVATION_SCHEMA = "guala.causal_mosaic_relation.observation.v2"
TAPESTRY_SCHEMA = "guala.causal_mosaic_tapestry.v1"
TAPESTRY_RELATION_SCHEMA = "guala.causal_tapestry_relation.v1"
PREPARED_SCHEMA = "guala.causal_mosaic_tapestry.prepared.v1"
STATE_SCHEMA = "guala.causal_mosaic_tapestry.state.v1"
ENVELOPE_SCHEMA = "guala.causal_mosaic_tapestry.state_hmac.v1"

_OBSERVATION_DOMAIN = b"guala-causal-mosaic-observation-v2\0"
_TAPESTRY_DOMAIN = b"guala-causal-mosaic-tapestry-v1\0"
_RELATION_DOMAIN = b"guala-causal-tapestry-relation-v1\0"
_PREPARED_DOMAIN = b"guala-causal-mosaic-tapestry-prepared-v1\0"
_STATE_DOMAIN = b"guala-causal-mosaic-tapestry-state-v1\0"
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


def _key(value: bytes | str, label: str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(f"{label} key changed")
    return hashlib.sha256(label.encode("utf-8") + b"\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("causal mosaic time must be an exact Fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not canonical")
    return result


def _verify_full_root(root: FullFieldSensoryRoot) -> None:
    if not isinstance(root, FullFieldSensoryRoot):
        raise TypeError("tapestry evidence root is not typed")
    root.verify()


def _root_from_raw(raw: object) -> FullFieldSensoryRoot:
    expected = {
        "full_evidence_json",
        "physical_value_sha256",
        "schema",
        "sense",
        "topology_index",
    }
    if (
        not isinstance(raw, dict)
        or set(raw) != expected
        or raw.get("schema")
        != "guala.causal_thing_mosaic.full_field_root.v2"
    ):
        raise ValueError("cold tapestry root changed")
    result = FullFieldSensoryRoot(
        sense=raw["sense"],
        topology_index=raw["topology_index"],
        physical_value_sha256=raw["physical_value_sha256"],
        full_evidence_json=raw["full_evidence_json"],
    )
    _verify_full_root(result)
    return result


@dataclass(frozen=True, slots=True)
class CausalMosaicTapestryProfile:
    profile_id: str
    max_tapestries: int
    max_tapestry_relations: int
    max_roots_per_tapestry: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_tapestries: int,
        max_tapestry_relations: int,
        max_roots_per_tapestry: int,
        max_state_bytes: int,
    ) -> "CausalMosaicTapestryProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "tapestry profile id"),
            max_tapestries=_positive(
                max_tapestries, "tapestry capacity"
            ),
            max_tapestry_relations=_positive(
                max_tapestry_relations, "tapestry relation capacity"
            ),
            max_roots_per_tapestry=_positive(
                max_roots_per_tapestry, "tapestry root capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "tapestry state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_tapestries=provisional.max_tapestries,
            max_tapestry_relations=provisional.max_tapestry_relations,
            max_roots_per_tapestry=provisional.max_roots_per_tapestry,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_roots_per_tapestry": self.max_roots_per_tapestry,
            "max_state_bytes": self.max_state_bytes,
            "max_tapestries": self.max_tapestries,
            "max_tapestry_relations": self.max_tapestry_relations,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "tapestry profile id")
        _positive(self.max_tapestries, "tapestry capacity")
        _positive(
            self.max_tapestry_relations, "tapestry relation capacity"
        )
        _positive(
            self.max_roots_per_tapestry, "tapestry root capacity"
        )
        _positive(self.max_state_bytes, "tapestry state capacity")
        _sha(self.authority_receipt_sha256, "tapestry profile authority")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("tapestry profile authority changed")


@dataclass(frozen=True, slots=True)
class ObservedCausalMosaicRelation:
    chain_id: str
    entity_continuity_hmac_sha256: str
    source_mosaic_receipt_sha256: str
    target_mosaic_receipt_sha256: str
    source_learning_receipt_sha256: str
    target_learning_receipt_sha256: str
    source_episode_receipt_sha256: str
    continuity_predecessor_episode_receipt_sha256: str
    target_episode_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    target_time_start: Fraction
    target_time_end: Fraction
    source_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    target_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def full_field_roots(self) -> tuple[FullFieldSensoryRoot, ...]:
        return self.source_full_field_roots + self.target_full_field_roots

    def payload(self) -> dict[str, object]:
        return {
            "chain_id": self.chain_id,
            "continuity_predecessor_episode_receipt_sha256": (
                self.continuity_predecessor_episode_receipt_sha256
            ),
            "entity_continuity_hmac_sha256": (
                self.entity_continuity_hmac_sha256
            ),
            "schema": OBSERVATION_SCHEMA,
            "source_episode_receipt_sha256": (
                self.source_episode_receipt_sha256
            ),
            "source_full_field_roots": [
                value.record() for value in self.source_full_field_roots
            ],
            "source_learning_receipt_sha256": (
                self.source_learning_receipt_sha256
            ),
            "source_mosaic_receipt_sha256": (
                self.source_mosaic_receipt_sha256
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "target_episode_receipt_sha256": (
                self.target_episode_receipt_sha256
            ),
            "target_full_field_roots": [
                value.record() for value in self.target_full_field_roots
            ],
            "target_learning_receipt_sha256": (
                self.target_learning_receipt_sha256
            ),
            "target_mosaic_receipt_sha256": (
                self.target_mosaic_receipt_sha256
            ),
            "target_time_end": _fraction_text(self.target_time_end),
            "target_time_start": _fraction_text(self.target_time_start),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class ObservedCausalMosaicRelationAuthority:
    """Authenticate exact observed causal order between two mosaic records."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        self._key = _key(authority_key, "observed causal mosaic relation")

    def observe(
        self,
        *,
        chain_id: str,
        entity_continuity_hmac_sha256: str,
        source_mosaic_receipt_sha256: str,
        target_mosaic_receipt_sha256: str,
        source_learning_receipt_sha256: str,
        target_learning_receipt_sha256: str,
        source_episode_receipt_sha256: str,
        continuity_predecessor_episode_receipt_sha256: str,
        target_episode_receipt_sha256: str,
        source_time_start: Fraction,
        source_time_end: Fraction,
        target_time_start: Fraction,
        target_time_end: Fraction,
        source_full_field_roots: tuple[FullFieldSensoryRoot, ...],
        target_full_field_roots: tuple[FullFieldSensoryRoot, ...],
    ) -> ObservedCausalMosaicRelation:
        provisional = ObservedCausalMosaicRelation(
            chain_id=chain_id,
            entity_continuity_hmac_sha256=(
                entity_continuity_hmac_sha256
            ),
            source_mosaic_receipt_sha256=source_mosaic_receipt_sha256,
            target_mosaic_receipt_sha256=target_mosaic_receipt_sha256,
            source_learning_receipt_sha256=source_learning_receipt_sha256,
            target_learning_receipt_sha256=target_learning_receipt_sha256,
            source_episode_receipt_sha256=source_episode_receipt_sha256,
            continuity_predecessor_episode_receipt_sha256=(
                continuity_predecessor_episode_receipt_sha256
            ),
            target_episode_receipt_sha256=target_episode_receipt_sha256,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            target_time_start=target_time_start,
            target_time_end=target_time_end,
            source_full_field_roots=source_full_field_roots,
            target_full_field_roots=target_full_field_roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        self._verify_payload(provisional)
        signature = hmac.new(
            self._key,
            _OBSERVATION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = ObservedCausalMosaicRelation(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify(result)
        return result

    @staticmethod
    def _verify_payload(value: ObservedCausalMosaicRelation) -> None:
        if not isinstance(value, ObservedCausalMosaicRelation):
            raise TypeError("observed mosaic relation is not typed")
        _identifier(value.chain_id, "observed mosaic chain")
        for digest, label in (
            (
                value.entity_continuity_hmac_sha256,
                "physical entity continuity",
            ),
            (value.source_mosaic_receipt_sha256, "source mosaic"),
            (value.target_mosaic_receipt_sha256, "target mosaic"),
            (value.source_learning_receipt_sha256, "source learning"),
            (value.target_learning_receipt_sha256, "target learning"),
            (value.source_episode_receipt_sha256, "source episode"),
            (
                value.continuity_predecessor_episode_receipt_sha256,
                "continuity predecessor episode",
            ),
            (value.target_episode_receipt_sha256, "target episode"),
        ):
            _sha(digest, label)
        if (
            value.source_learning_receipt_sha256
            == value.target_learning_receipt_sha256
            or value.source_episode_receipt_sha256
            == value.target_episode_receipt_sha256
            or value.continuity_predecessor_episode_receipt_sha256
            != value.source_episode_receipt_sha256
            or value.chain_id
            != (
                "organism-lived-continuity:"
                + value.entity_continuity_hmac_sha256
            )
            or not isinstance(value.source_time_start, Fraction)
            or not isinstance(value.source_time_end, Fraction)
            or not isinstance(value.target_time_start, Fraction)
            or not isinstance(value.target_time_end, Fraction)
            or value.source_time_end <= value.source_time_start
            or value.target_time_end <= value.target_time_start
            or value.target_time_start < value.source_time_end
            or not value.source_full_field_roots
            or not value.target_full_field_roots
        ):
            raise ValueError(
                "mosaic records are not one observed causal predecessor pair"
            )
        for root in value.full_field_roots:
            _verify_full_root(root)

    def verify(self, value: ObservedCausalMosaicRelation) -> None:
        self._verify_payload(value)
        _sha(value.authority_hmac_sha256, "mosaic relation HMAC")
        _sha(value.authority_receipt_sha256, "mosaic relation authority")
        expected = hmac.new(
            self._key,
            _OBSERVATION_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("observed mosaic relation authority changed")


@dataclass(frozen=True, slots=True)
class CausalMosaicTapestry:
    observation: ObservedCausalMosaicRelation
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def full_field_roots(self) -> tuple[FullFieldSensoryRoot, ...]:
        return self.observation.full_field_roots

    @property
    def settled_state(self) -> str:
        return "causally_settled"

    @property
    def member_mosaic_receipt_sha256s(self) -> tuple[str, str]:
        return (
            self.observation.source_mosaic_receipt_sha256,
            self.observation.target_mosaic_receipt_sha256,
        )

    def payload(self) -> dict[str, object]:
        return {
            "observed_relation": self.observation.record(),
            "schema": TAPESTRY_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CausalTapestryRelation:
    chain_id: str
    source_tapestry_receipt_sha256: str
    target_tapestry_receipt_sha256: str
    junction_mosaic_receipt_sha256: str
    junction_episode_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "chain_id": self.chain_id,
            "junction_episode_receipt_sha256": (
                self.junction_episode_receipt_sha256
            ),
            "junction_mosaic_receipt_sha256": (
                self.junction_mosaic_receipt_sha256
            ),
            "schema": TAPESTRY_RELATION_SCHEMA,
            "source_tapestry_receipt_sha256": (
                self.source_tapestry_receipt_sha256
            ),
            "target_tapestry_receipt_sha256": (
                self.target_tapestry_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedCausalMosaicTapestryMutation:
    state: str
    observation_receipt_sha256: str
    prior_tapestries: tuple[CausalMosaicTapestry, ...]
    prior_relations: tuple[CausalTapestryRelation, ...]
    staged_tapestries: tuple[CausalMosaicTapestry, ...]
    staged_relations: tuple[CausalTapestryRelation, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "observation_receipt_sha256": (
                self.observation_receipt_sha256
            ),
            "prior_relation_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_relations
            ],
            "prior_tapestry_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_tapestries
            ],
            "schema": PREPARED_SCHEMA,
            "staged_relation_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_relations
            ],
            "staged_tapestry_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_tapestries
            ],
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class CausalMosaicTapestryUndo:
    _prepared: PreparedCausalMosaicTapestryMutation = field(
        repr=False
    )


class CausalMosaicTapestryOwner:
    """Own causal mosaic tapestries and their observed path topology."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: CausalMosaicTapestryProfile,
        relation_authority: ObservedCausalMosaicRelationAuthority,
    ) -> None:
        if not isinstance(profile, CausalMosaicTapestryProfile):
            raise TypeError("tapestry profile is not typed")
        profile.verify()
        if not isinstance(
            relation_authority, ObservedCausalMosaicRelationAuthority
        ):
            raise TypeError("tapestry relation authority is not typed")
        root = _key(authority_key, "causal mosaic tapestry")
        self._tapestry_key = hashlib.sha256(
            _TAPESTRY_DOMAIN + root
        ).digest()
        self._relation_key = hashlib.sha256(
            _RELATION_DOMAIN + root
        ).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._observations = relation_authority
        self._tapestries: tuple[CausalMosaicTapestry, ...] = ()
        self._relations: tuple[CausalTapestryRelation, ...] = ()
        self._prepared: PreparedCausalMosaicTapestryMutation | None = None
        self._lock = threading.RLock()

    @property
    def tapestries(self) -> tuple[CausalMosaicTapestry, ...]:
        with self._lock:
            return self._tapestries

    @property
    def relations(self) -> tuple[CausalTapestryRelation, ...]:
        with self._lock:
            return self._relations

    def require_settled_tapestry(
        self,
        authority_receipt_sha256: str,
    ) -> CausalMosaicTapestry:
        """Return one retained authenticated tapestry or fail closed."""

        _sha(authority_receipt_sha256, "required tapestry authority")
        with self._lock:
            matches = tuple(
                value
                for value in self._tapestries
                if value.authority_receipt_sha256
                == authority_receipt_sha256
            )
            if len(matches) != 1:
                raise ValueError(
                    "required settled tapestry is not retained"
                )
            self._verify_tapestry(matches[0])
            return matches[0]

    def relations_for_tapestry(
        self,
        authority_receipt_sha256: str,
    ) -> tuple[CausalTapestryRelation, ...]:
        """Return authenticated incident topology for one retained tapestry."""

        self.require_settled_tapestry(authority_receipt_sha256)
        with self._lock:
            selected = tuple(
                value
                for value in self._relations
                if authority_receipt_sha256
                in {
                    value.source_tapestry_receipt_sha256,
                    value.target_tapestry_receipt_sha256,
                }
            )
            by_receipt = {
                value.authority_receipt_sha256: value
                for value in self._tapestries
            }
            for value in selected:
                self._verify_relation(value, by_receipt)
            return selected

    def _seal_tapestry(
        self, observation: ObservedCausalMosaicRelation
    ) -> CausalMosaicTapestry:
        provisional = CausalMosaicTapestry(
            observation=observation,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._tapestry_key,
            _TAPESTRY_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CausalMosaicTapestry(
            observation=observation,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _seal_relation(
        self,
        source: CausalMosaicTapestry,
        target: CausalMosaicTapestry,
    ) -> CausalTapestryRelation:
        first = source.observation
        second = target.observation
        if (
            first.chain_id != second.chain_id
            or first.target_mosaic_receipt_sha256
            != second.source_mosaic_receipt_sha256
            or first.target_episode_receipt_sha256
            != second.source_episode_receipt_sha256
            or first.target_time_start != second.source_time_start
            or first.target_time_end != second.source_time_end
        ):
            raise ValueError("tapestries do not form one observed causal path")
        provisional = CausalTapestryRelation(
            chain_id=first.chain_id,
            source_tapestry_receipt_sha256=(
                source.authority_receipt_sha256
            ),
            target_tapestry_receipt_sha256=(
                target.authority_receipt_sha256
            ),
            junction_mosaic_receipt_sha256=(
                first.target_mosaic_receipt_sha256
            ),
            junction_episode_receipt_sha256=(
                first.target_episode_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._relation_key,
            _RELATION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CausalTapestryRelation(
            chain_id=provisional.chain_id,
            source_tapestry_receipt_sha256=(
                provisional.source_tapestry_receipt_sha256
            ),
            target_tapestry_receipt_sha256=(
                provisional.target_tapestry_receipt_sha256
            ),
            junction_mosaic_receipt_sha256=(
                provisional.junction_mosaic_receipt_sha256
            ),
            junction_episode_receipt_sha256=(
                provisional.junction_episode_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _verify_tapestry(self, value: CausalMosaicTapestry) -> None:
        if not isinstance(value, CausalMosaicTapestry):
            raise TypeError("tapestry is not typed")
        self._observations.verify(value.observation)
        if len(value.full_field_roots) > self._profile.max_roots_per_tapestry:
            raise RuntimeError("tapestry root capacity exhausted")
        expected = hmac.new(
            self._tapestry_key,
            _TAPESTRY_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("tapestry authority changed")

    def _verify_relation(
        self,
        value: CausalTapestryRelation,
        by_receipt: dict[str, CausalMosaicTapestry],
    ) -> None:
        if not isinstance(value, CausalTapestryRelation):
            raise TypeError("tapestry relation is not typed")
        source = by_receipt.get(value.source_tapestry_receipt_sha256)
        target = by_receipt.get(value.target_tapestry_receipt_sha256)
        if source is None or target is None:
            raise ValueError("tapestry relation left retained topology")
        expected_value = self._seal_relation(source, target)
        if value != expected_value:
            raise ValueError("tapestry relation authority changed")

    def _verify_extent(
        self,
        tapestries: tuple[CausalMosaicTapestry, ...],
        relations: tuple[CausalTapestryRelation, ...],
    ) -> None:
        if (
            len(tapestries) > self._profile.max_tapestries
            or len(relations) > self._profile.max_tapestry_relations
            or tuple(
                value.authority_receipt_sha256 for value in tapestries
            )
            != tuple(sorted({
                value.authority_receipt_sha256 for value in tapestries
            }))
            or tuple(
                value.authority_receipt_sha256 for value in relations
            )
            != tuple(sorted({
                value.authority_receipt_sha256 for value in relations
            }))
        ):
            raise RuntimeError("tapestry topology capacity or order changed")
        for value in tapestries:
            self._verify_tapestry(value)
        by_receipt = {
            value.authority_receipt_sha256: value for value in tapestries
        }
        for value in relations:
            self._verify_relation(value, by_receipt)

    def _state_body(
        self,
        tapestries: tuple[CausalMosaicTapestry, ...],
        relations: tuple[CausalTapestryRelation, ...],
    ) -> dict[str, object]:
        return {
            "profile": self._profile.record(),
            "relations": [value.record() for value in relations],
            "schema": STATE_SCHEMA,
            "tapestries": [value.record() for value in tapestries],
        }

    def _encoded(
        self,
        tapestries: tuple[CausalMosaicTapestry, ...],
        relations: tuple[CausalTapestryRelation, ...],
    ) -> bytes:
        self._verify_extent(tapestries, relations)
        body = self._state_body(tapestries, relations)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("tapestry state capacity exhausted")
        return encoded

    def prepare(
        self,
        observation: ObservedCausalMosaicRelation,
    ) -> PreparedCausalMosaicTapestryMutation:
        self._observations.verify(observation)
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("one tapestry mutation is already prepared")
            existing = {
                value.observation.authority_receipt_sha256: value
                for value in self._tapestries
            }
            if observation.authority_receipt_sha256 in existing:
                state = "quiescent"
                staged_tapestries = self._tapestries
                staged_relations = self._relations
            else:
                state = "perturbed"
                added = self._seal_tapestry(observation)
                staged_tapestries = tuple(sorted(
                    self._tapestries + (added,),
                    key=lambda value: value.authority_receipt_sha256,
                ))
                relations = {
                    value.authority_receipt_sha256: value
                    for value in self._relations
                }
                for source in staged_tapestries:
                    for target in staged_tapestries:
                        if source is target:
                            continue
                        try:
                            relation = self._seal_relation(source, target)
                        except ValueError:
                            continue
                        relations[relation.authority_receipt_sha256] = relation
                staged_relations = tuple(
                    relations[key] for key in sorted(relations)
                )
            self._encoded(staged_tapestries, staged_relations)
            provisional = PreparedCausalMosaicTapestryMutation(
                state=state,
                observation_receipt_sha256=(
                    observation.authority_receipt_sha256
                ),
                prior_tapestries=self._tapestries,
                prior_relations=self._relations,
                staged_tapestries=staged_tapestries,
                staged_relations=staged_relations,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._prepared_key,
                _PREPARED_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            prepared = PreparedCausalMosaicTapestryMutation(
                state=provisional.state,
                observation_receipt_sha256=(
                    provisional.observation_receipt_sha256
                ),
                prior_tapestries=provisional.prior_tapestries,
                prior_relations=provisional.prior_relations,
                staged_tapestries=provisional.staged_tapestries,
                staged_relations=provisional.staged_relations,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._prepared = prepared
            return prepared

    def _verify_prepared(
        self, value: PreparedCausalMosaicTapestryMutation
    ) -> None:
        if not isinstance(value, PreparedCausalMosaicTapestryMutation):
            raise TypeError("prepared tapestry mutation is not typed")
        if value.state not in {"perturbed", "quiescent"}:
            raise ValueError("prepared tapestry state changed")
        expected = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("prepared tapestry authority changed")
        self._verify_extent(
            value.staged_tapestries, value.staged_relations
        )

    def commit(
        self, prepared: PreparedCausalMosaicTapestryMutation
    ) -> CausalMosaicTapestryUndo:
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared != prepared:
                raise ValueError("prepared tapestry mutation is not current")
            if (
                self._tapestries != prepared.prior_tapestries
                or self._relations != prepared.prior_relations
            ):
                raise RuntimeError("tapestry state changed before commit")
            self._tapestries = prepared.staged_tapestries
            self._relations = prepared.staged_relations
            self._prepared = None
            return CausalMosaicTapestryUndo(prepared)

    def discard(
        self, prepared: PreparedCausalMosaicTapestryMutation
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared != prepared:
                raise ValueError("prepared tapestry mutation is not current")
            self._prepared = None

    def rollback(self, undo: CausalMosaicTapestryUndo) -> None:
        if not isinstance(undo, CausalMosaicTapestryUndo):
            raise TypeError("tapestry undo is not typed")
        prepared = undo._prepared
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared is not None:
                raise RuntimeError(
                    "cannot roll back through an in-flight tapestry mutation"
                )
            if (
                self._tapestries != prepared.staged_tapestries
                or self._relations != prepared.staged_relations
            ):
                raise ValueError("committed tapestry mutation is not current")
            self._tapestries = prepared.prior_tapestries
            self._relations = prepared.prior_relations

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "cannot snapshot an in-flight tapestry mutation"
                )
            return self._encoded(self._tapestries, self._relations)

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded(self._tapestries, self._relations)
            return {
                "full_field": True,
                "mechanism_state": (
                    "quiescent" if not self._tapestries else "perturbed"
                ),
                "reduced_approximation": False,
                "retained_roots": sum(
                    len(value.full_field_roots)
                    for value in self._tapestries
                ),
                "schema": "guala.causal_mosaic_tapestry.status.v1",
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "tapestries": len(self._tapestries),
                "tapestry_relations": len(self._relations),
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: CausalMosaicTapestryProfile,
        relation_authority: ObservedCausalMosaicRelationAuthority,
        encoded: bytes,
    ) -> "CausalMosaicTapestryOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("tapestry cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("tapestry cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("tapestry cold envelope changed")
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body) != {"profile", "relations", "schema", "tapestries"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
            or not isinstance(body.get("tapestries"), list)
            or not isinstance(body.get("relations"), list)
        ):
            raise ValueError("tapestry cold payload changed")
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            relation_authority=relation_authority,
        )
        expected = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""), expected
        ):
            raise ValueError("tapestry cold state authority changed")
        owner._tapestries = tuple(
            owner._tapestry_from_raw(value)
            for value in body["tapestries"]
        )
        owner._relations = tuple(
            owner._relation_from_raw(value) for value in body["relations"]
        )
        if owner.snapshot_encoded() != encoded:
            raise ValueError("tapestry cold round-trip changed state")
        return owner

    def _observation_from_raw(
        self, raw: object
    ) -> ObservedCausalMosaicRelation:
        expected = set(ObservedCausalMosaicRelation.__dataclass_fields__) | {
            "schema"
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != OBSERVATION_SCHEMA
            or not isinstance(raw.get("source_full_field_roots"), list)
            or not isinstance(raw.get("target_full_field_roots"), list)
        ):
            raise ValueError("cold mosaic relation observation changed")
        return ObservedCausalMosaicRelation(
            chain_id=raw["chain_id"],
            entity_continuity_hmac_sha256=(
                raw["entity_continuity_hmac_sha256"]
            ),
            source_mosaic_receipt_sha256=(
                raw["source_mosaic_receipt_sha256"]
            ),
            target_mosaic_receipt_sha256=(
                raw["target_mosaic_receipt_sha256"]
            ),
            source_learning_receipt_sha256=(
                raw["source_learning_receipt_sha256"]
            ),
            target_learning_receipt_sha256=(
                raw["target_learning_receipt_sha256"]
            ),
            source_episode_receipt_sha256=(
                raw["source_episode_receipt_sha256"]
            ),
            continuity_predecessor_episode_receipt_sha256=(
                raw[
                    "continuity_predecessor_episode_receipt_sha256"
                ]
            ),
            target_episode_receipt_sha256=(
                raw["target_episode_receipt_sha256"]
            ),
            source_time_start=_fraction_from_text(
                raw["source_time_start"], "cold source start"
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"], "cold source end"
            ),
            target_time_start=_fraction_from_text(
                raw["target_time_start"], "cold target start"
            ),
            target_time_end=_fraction_from_text(
                raw["target_time_end"], "cold target end"
            ),
            source_full_field_roots=tuple(
                _root_from_raw(value)
                for value in raw["source_full_field_roots"]
            ),
            target_full_field_roots=tuple(
                _root_from_raw(value)
                for value in raw["target_full_field_roots"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    def _tapestry_from_raw(self, raw: object) -> CausalMosaicTapestry:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "observed_relation",
            "schema",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != TAPESTRY_SCHEMA
        ):
            raise ValueError("cold tapestry changed")
        return CausalMosaicTapestry(
            observation=self._observation_from_raw(
                raw["observed_relation"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    @staticmethod
    def _relation_from_raw(raw: object) -> CausalTapestryRelation:
        expected = set(CausalTapestryRelation.__dataclass_fields__) | {
            "schema"
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != TAPESTRY_RELATION_SCHEMA
        ):
            raise ValueError("cold tapestry relation changed")
        return CausalTapestryRelation(
            chain_id=raw["chain_id"],
            source_tapestry_receipt_sha256=(
                raw["source_tapestry_receipt_sha256"]
            ),
            target_tapestry_receipt_sha256=(
                raw["target_tapestry_receipt_sha256"]
            ),
            junction_mosaic_receipt_sha256=(
                raw["junction_mosaic_receipt_sha256"]
            ),
            junction_episode_receipt_sha256=(
                raw["junction_episode_receipt_sha256"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )


__all__ = (
    "CausalMosaicTapestry",
    "CausalMosaicTapestryOwner",
    "CausalMosaicTapestryProfile",
    "CausalMosaicTapestryUndo",
    "CausalTapestryRelation",
    "ObservedCausalMosaicRelation",
    "ObservedCausalMosaicRelationAuthority",
    "PreparedCausalMosaicTapestryMutation",
)
