"""Full-field recognition and attention over causal mosaic relations.

Recognition is convergence in retained causal topology, never signal
comparison.  Two or more independent authenticated tapestry paths must end at
the same retained THING mosaic and jointly carry at least two physical senses.
Unknown, conflicting, and one-sense evidence remain explicitly unresolved.

Attention retains the complete current field, needs, body, chemical state,
causal context, and every candidate path.  A unique lawful action or inquiry
receipt may become a focus pointer; nothing outside that pointer is discarded
or converted into a scalar salience score.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import FullFieldSensoryRoot


PROFILE_SCHEMA = "guala.causal_recognition_attention.profile.v1"
PATH_SCHEMA = "guala.causal_recognition.mosaic_relation_path.v1"
CONTEXT_SCHEMA = "guala.whole_organism.attention_context.v1"
STATE_SCHEMA = "guala.causal_recognition_attention.state.v1"
PREPARED_SCHEMA = "guala.causal_recognition_attention.prepared.v1"
OWNER_SCHEMA = "guala.causal_recognition_attention.owner_state.v1"
ENVELOPE_SCHEMA = "guala.causal_recognition_attention.owner_state_hmac.v1"

_PATH_DOMAIN = b"guala-causal-recognition-path-v1\0"
_CONTEXT_DOMAIN = b"guala-whole-organism-attention-context-v1\0"
_STATE_DOMAIN = b"guala-causal-recognition-attention-state-v1\0"
_PREPARED_DOMAIN = b"guala-causal-recognition-attention-prepared-v1\0"
_OWNER_DOMAIN = b"guala-causal-recognition-attention-owner-v1\0"
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
    return hashlib.sha256(label.encode() + b"\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode()) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("recognition time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not exact")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not exact") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not canonical")
    return result


def _canonical_state(value: object, label: str) -> str:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a structured state")
    encoded = _canonical(value)
    if len(encoded) > 1_048_576:
        raise ValueError(f"{label} exceeds its per-state bound")
    return encoded.decode()


def _verify_state(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} changed")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is unreadable") from error
    if not isinstance(decoded, dict) or _canonical(decoded).decode() != value:
        raise ValueError(f"{label} is not canonical")
    return value


def _verify_root(root: FullFieldSensoryRoot) -> None:
    if not isinstance(root, FullFieldSensoryRoot):
        raise TypeError("recognition root is not typed")
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
        raise ValueError("cold recognition root changed")
    result = FullFieldSensoryRoot(
        sense=raw["sense"],
        topology_index=raw["topology_index"],
        physical_value_sha256=raw["physical_value_sha256"],
        full_evidence_json=raw["full_evidence_json"],
    )
    _verify_root(result)
    return result


@dataclass(frozen=True, slots=True)
class CausalRecognitionAttentionProfile:
    profile_id: str
    max_paths: int
    max_roots: int
    max_action_relations: int
    max_inquiry_relations: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_paths: int,
        max_roots: int,
        max_action_relations: int,
        max_inquiry_relations: int,
        max_state_bytes: int,
    ) -> "CausalRecognitionAttentionProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "recognition profile id"),
            max_paths=_positive(max_paths, "recognition path capacity"),
            max_roots=_positive(max_roots, "recognition root capacity"),
            max_action_relations=_positive(
                max_action_relations, "action relation capacity"
            ),
            max_inquiry_relations=_positive(
                max_inquiry_relations, "inquiry relation capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "recognition state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name != "authority_receipt_sha256"
            },
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_action_relations": self.max_action_relations,
            "max_inquiry_relations": self.max_inquiry_relations,
            "max_paths": self.max_paths,
            "max_roots": self.max_roots,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "recognition profile id")
        for value, label in (
            (self.max_paths, "recognition path capacity"),
            (self.max_roots, "recognition root capacity"),
            (self.max_action_relations, "action relation capacity"),
            (self.max_inquiry_relations, "inquiry relation capacity"),
            (self.max_state_bytes, "recognition state capacity"),
        ):
            _positive(value, label)
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("recognition profile authority changed")


@dataclass(frozen=True, slots=True)
class CausalThingRelationPath:
    tapestry_receipt_sha256: str
    thing_mosaic_receipt_sha256: str
    chain_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    contributing_senses: tuple[str, ...]
    candidate_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    complete_tapestry_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_full_field_roots": [
                value.record() for value in self.candidate_full_field_roots
            ],
            "chain_id": self.chain_id,
            "complete_tapestry_full_field_roots": [
                value.record()
                for value in self.complete_tapestry_full_field_roots
            ],
            "contributing_senses": list(self.contributing_senses),
            "schema": PATH_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "tapestry_receipt_sha256": self.tapestry_receipt_sha256,
            "thing_mosaic_receipt_sha256": (
                self.thing_mosaic_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class CausalThingRelationPathAuthority:
    """Bind recognition paths to exact retained tapestry targets."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        tapestry_owner: CausalMosaicTapestryOwner,
    ) -> None:
        if not isinstance(tapestry_owner, CausalMosaicTapestryOwner):
            raise TypeError("recognition paths require a tapestry owner")
        self._key = _key(authority_key, "recognition relation path")
        self._tapestries = tapestry_owner

    def bind(self, tapestry_receipt_sha256: str) -> CausalThingRelationPath:
        tapestry = self._tapestries.require_settled_tapestry(
            tapestry_receipt_sha256
        )
        observation = tapestry.observation
        roots = observation.target_full_field_roots
        senses = tuple(sorted({value.sense for value in roots}))
        provisional = CausalThingRelationPath(
            tapestry_receipt_sha256=tapestry.authority_receipt_sha256,
            thing_mosaic_receipt_sha256=(
                observation.target_mosaic_receipt_sha256
            ),
            chain_id=observation.chain_id,
            source_time_start=observation.source_time_start,
            source_time_end=observation.target_time_end,
            contributing_senses=senses,
            candidate_full_field_roots=roots,
            complete_tapestry_full_field_roots=tapestry.full_field_roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _PATH_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = CausalThingRelationPath(
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

    def verify(self, value: CausalThingRelationPath) -> None:
        if not isinstance(value, CausalThingRelationPath):
            raise TypeError("recognition relation path is not typed")
        tapestry = self._tapestries.require_settled_tapestry(
            value.tapestry_receipt_sha256
        )
        observation = tapestry.observation
        expected_senses = tuple(sorted({
            root.sense for root in observation.target_full_field_roots
        }))
        if (
            value.thing_mosaic_receipt_sha256
            != observation.target_mosaic_receipt_sha256
            or value.chain_id != observation.chain_id
            or value.source_time_start != observation.source_time_start
            or value.source_time_end != observation.target_time_end
            or value.contributing_senses != expected_senses
            or value.candidate_full_field_roots
            != observation.target_full_field_roots
            or value.complete_tapestry_full_field_roots
            != tapestry.full_field_roots
            or not value.candidate_full_field_roots
        ):
            raise ValueError("recognition path left its causal tapestry")
        for root in value.complete_tapestry_full_field_roots:
            _verify_root(root)
        expected = hmac.new(
            self._key,
            _PATH_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("recognition relation path authority changed")


@dataclass(frozen=True, slots=True)
class WholeOrganismAttentionContext:
    context_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    current_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    needs_state_json: str
    body_state_json: str
    chemical_state_json: str
    causal_context_json: str
    lawful_action_relation_receipts: tuple[str, ...]
    lawful_inquiry_relation_receipts: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "body_state_json": self.body_state_json,
            "causal_context_json": self.causal_context_json,
            "chemical_state_json": self.chemical_state_json,
            "context_id": self.context_id,
            "current_full_field_roots": [
                value.record() for value in self.current_full_field_roots
            ],
            "lawful_action_relation_receipts": list(
                self.lawful_action_relation_receipts
            ),
            "lawful_inquiry_relation_receipts": list(
                self.lawful_inquiry_relation_receipts
            ),
            "needs_state_json": self.needs_state_json,
            "schema": CONTEXT_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class WholeOrganismAttentionContextAuthority:
    def __init__(self, *, authority_key: bytes | str) -> None:
        self._key = _key(authority_key, "whole organism attention context")

    def observe(
        self,
        *,
        context_id: str,
        source_time_start: Fraction,
        source_time_end: Fraction,
        current_full_field_roots: tuple[FullFieldSensoryRoot, ...],
        needs_state: dict[str, object],
        body_state: dict[str, object],
        chemical_state: dict[str, object],
        causal_context: dict[str, object],
        lawful_action_relation_receipts: tuple[str, ...] = (),
        lawful_inquiry_relation_receipts: tuple[str, ...] = (),
    ) -> WholeOrganismAttentionContext:
        provisional = WholeOrganismAttentionContext(
            context_id=_identifier(context_id, "attention context id"),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            current_full_field_roots=current_full_field_roots,
            needs_state_json=_canonical_state(needs_state, "needs state"),
            body_state_json=_canonical_state(body_state, "body state"),
            chemical_state_json=_canonical_state(
                chemical_state, "chemical state"
            ),
            causal_context_json=_canonical_state(
                causal_context, "causal context"
            ),
            lawful_action_relation_receipts=tuple(sorted(set(
                lawful_action_relation_receipts
            ))),
            lawful_inquiry_relation_receipts=tuple(sorted(set(
                lawful_inquiry_relation_receipts
            ))),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        self._verify_payload(provisional)
        signature = hmac.new(
            self._key,
            _CONTEXT_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = WholeOrganismAttentionContext(
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
    def _verify_payload(value: WholeOrganismAttentionContext) -> None:
        if not isinstance(value, WholeOrganismAttentionContext):
            raise TypeError("attention context is not typed")
        _identifier(value.context_id, "attention context id")
        if (
            not isinstance(value.source_time_start, Fraction)
            or not isinstance(value.source_time_end, Fraction)
            or value.source_time_end <= value.source_time_start
            or not value.current_full_field_roots
        ):
            raise ValueError("attention context interval or field changed")
        for root in value.current_full_field_roots:
            _verify_root(root)
        for raw, label in (
            (value.needs_state_json, "needs state"),
            (value.body_state_json, "body state"),
            (value.chemical_state_json, "chemical state"),
            (value.causal_context_json, "causal context"),
        ):
            _verify_state(raw, label)
        for values, label in (
            (value.lawful_action_relation_receipts, "action relation"),
            (value.lawful_inquiry_relation_receipts, "inquiry relation"),
        ):
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{label} order changed")
            for receipt in values:
                _sha(receipt, label)

    def verify(self, value: WholeOrganismAttentionContext) -> None:
        self._verify_payload(value)
        expected = hmac.new(
            self._key,
            _CONTEXT_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("attention context authority changed")


@dataclass(frozen=True, slots=True)
class CausalRecognitionAttentionState:
    recognition_state: str
    recognized_thing_mosaic_receipt_sha256: str | None
    candidate_thing_mosaic_receipt_sha256s: tuple[str, ...]
    participating_senses: tuple[str, ...]
    paths: tuple[CausalThingRelationPath, ...]
    context: WholeOrganismAttentionContext
    attention_state: str
    focused_relation_receipt_sha256: str | None
    inquiry_authorized: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "attention_state": self.attention_state,
            "candidate_thing_mosaic_receipt_sha256s": list(
                self.candidate_thing_mosaic_receipt_sha256s
            ),
            "context": self.context.record(),
            "focused_relation_receipt_sha256": (
                self.focused_relation_receipt_sha256
            ),
            "inquiry_authorized": self.inquiry_authorized,
            "participating_senses": list(self.participating_senses),
            "paths": [value.record() for value in self.paths],
            "recognition_state": self.recognition_state,
            "recognized_thing_mosaic_receipt_sha256": (
                self.recognized_thing_mosaic_receipt_sha256
            ),
            "schema": STATE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedCausalRecognitionAttention:
    prior_state: CausalRecognitionAttentionState | None
    staged_state: CausalRecognitionAttentionState
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "prior_state_receipt_sha256": (
                None
                if self.prior_state is None
                else self.prior_state.authority_receipt_sha256
            ),
            "schema": PREPARED_SCHEMA,
            "staged_state_receipt_sha256": (
                self.staged_state.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class CausalRecognitionAttentionUndo:
    _prepared: PreparedCausalRecognitionAttention = field(repr=False)


class CausalRecognitionAttentionOwner:
    """Own the latest complete recognition and distributed attention state."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: CausalRecognitionAttentionProfile,
        path_authority: CausalThingRelationPathAuthority,
        context_authority: WholeOrganismAttentionContextAuthority,
    ) -> None:
        if not isinstance(profile, CausalRecognitionAttentionProfile):
            raise TypeError("recognition profile is not typed")
        profile.verify()
        if not isinstance(path_authority, CausalThingRelationPathAuthority):
            raise TypeError("recognition path authority is not typed")
        if not isinstance(
            context_authority, WholeOrganismAttentionContextAuthority
        ):
            raise TypeError("attention context authority is not typed")
        root = _key(authority_key, "causal recognition attention")
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._owner_key = hashlib.sha256(_OWNER_DOMAIN + root).digest()
        self._profile = profile
        self._paths = path_authority
        self._contexts = context_authority
        self._state: CausalRecognitionAttentionState | None = None
        self._prepared: PreparedCausalRecognitionAttention | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CausalRecognitionAttentionState | None:
        with self._lock:
            return self._state

    def _seal_state(
        self,
        context: WholeOrganismAttentionContext,
        paths: tuple[CausalThingRelationPath, ...],
    ) -> CausalRecognitionAttentionState:
        candidates = tuple(sorted({
            value.thing_mosaic_receipt_sha256 for value in paths
        }))
        senses = tuple(sorted({
            sense for value in paths for sense in value.contributing_senses
        }))
        if not paths:
            recognition = "unknown"
            recognized = None
        elif len(candidates) != 1:
            recognition = "ambiguous"
            recognized = None
        elif len(paths) < 2 or len(senses) < 2:
            recognition = "insufficient_multisensory_convergence"
            recognized = None
        else:
            recognition = "settled"
            recognized = candidates[0]
        unresolved = recognition != "settled"
        actions = context.lawful_action_relation_receipts
        inquiries = context.lawful_inquiry_relation_receipts
        if not unresolved and len(actions) == 1:
            attention = "focused_action"
            focused = actions[0]
            inquiry = False
        elif unresolved and len(inquiries) == 1:
            attention = "focused_inquiry"
            focused = inquiries[0]
            inquiry = True
        else:
            attention = (
                "distributed_unresolved"
                if unresolved
                else "distributed_recognized"
            )
            focused = None
            inquiry = False
        provisional = CausalRecognitionAttentionState(
            recognition_state=recognition,
            recognized_thing_mosaic_receipt_sha256=recognized,
            candidate_thing_mosaic_receipt_sha256s=candidates,
            participating_senses=senses,
            paths=paths,
            context=context,
            attention_state=attention,
            focused_relation_receipt_sha256=focused,
            inquiry_authorized=inquiry,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CausalRecognitionAttentionState(
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

    def _verify_state(
        self, value: CausalRecognitionAttentionState
    ) -> None:
        if not isinstance(value, CausalRecognitionAttentionState):
            raise TypeError("recognition attention state is not typed")
        self._contexts.verify(value.context)
        if (
            len(value.paths) > self._profile.max_paths
            or len(value.context.current_full_field_roots)
            > self._profile.max_roots
            or len(value.context.lawful_action_relation_receipts)
            > self._profile.max_action_relations
            or len(value.context.lawful_inquiry_relation_receipts)
            > self._profile.max_inquiry_relations
            or tuple(
                item.authority_receipt_sha256 for item in value.paths
            )
            != tuple(sorted({
                item.authority_receipt_sha256 for item in value.paths
            }))
        ):
            raise RuntimeError("recognition attention capacity changed")
        for path in value.paths:
            self._paths.verify(path)
        expected = self._seal_state(value.context, value.paths)
        if value != expected:
            raise ValueError("recognition attention state authority changed")

    def prepare(
        self,
        *,
        context: WholeOrganismAttentionContext,
        paths: tuple[CausalThingRelationPath, ...],
    ) -> PreparedCausalRecognitionAttention:
        self._contexts.verify(context)
        ordered = tuple(sorted(
            paths, key=lambda value: value.authority_receipt_sha256
        ))
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("recognition attention is already prepared")
            staged = self._seal_state(context, ordered)
            self._verify_state(staged)
            provisional = PreparedCausalRecognitionAttention(
                prior_state=self._state,
                staged_state=staged,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._prepared_key,
                _PREPARED_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            prepared = PreparedCausalRecognitionAttention(
                prior_state=provisional.prior_state,
                staged_state=provisional.staged_state,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._encoded(staged)
            self._prepared = prepared
            return prepared

    def _verify_prepared(
        self, value: PreparedCausalRecognitionAttention
    ) -> None:
        if not isinstance(value, PreparedCausalRecognitionAttention):
            raise TypeError("prepared recognition attention is not typed")
        self._verify_state(value.staged_state)
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
            raise ValueError("prepared recognition authority changed")

    def commit(
        self, prepared: PreparedCausalRecognitionAttention
    ) -> CausalRecognitionAttentionUndo:
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared != prepared or self._state != prepared.prior_state:
                raise ValueError("prepared recognition state is not current")
            self._state = prepared.staged_state
            self._prepared = None
            return CausalRecognitionAttentionUndo(prepared)

    def discard(self, prepared: PreparedCausalRecognitionAttention) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared != prepared:
                raise ValueError("prepared recognition state is not current")
            self._prepared = None

    def rollback(self, undo: CausalRecognitionAttentionUndo) -> None:
        if not isinstance(undo, CausalRecognitionAttentionUndo):
            raise TypeError("recognition undo is not typed")
        prepared = undo._prepared
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared is not None:
                raise RuntimeError("recognition mutation is in flight")
            if self._state != prepared.staged_state:
                raise ValueError("committed recognition state is not current")
            self._state = prepared.prior_state

    def _body(
        self, state: CausalRecognitionAttentionState | None
    ) -> dict[str, object]:
        return {
            "profile": self._profile.record(),
            "schema": OWNER_SCHEMA,
            "state": None if state is None else state.record(),
        }

    def _encoded(
        self, state: CausalRecognitionAttentionState | None
    ) -> bytes:
        if state is not None:
            self._verify_state(state)
        body = self._body(state)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._owner_key,
                _OWNER_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("recognition attention state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("recognition attention mutation is in flight")
            return self._encoded(self._state)

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded(self._state)
            current = self._state
            observation = {
                "full_field": True,
                "mechanism_state": (
                    "quiescent" if current is None else "perturbed"
                ),
                "observation_projection": (
                    "current authenticated attention pointer and field extent"
                ),
                "projection_loss": (
                    "candidate paths and explicit DSF root bodies remain in "
                    "the separately served full-field observation"
                ),
                "reduced_approximation": False,
                "schema": "guala.causal_recognition_attention.status.v1",
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }
            if current is None:
                return observation | {
                    "attention_state": "not_observed",
                    "candidate_thing_count": 0,
                    "context_id": None,
                    "current_full_field_root_count": 0,
                    "focused_relation_receipt_sha256": None,
                    "inquiry_authorized": False,
                    "participating_senses": [],
                    "path_count": 0,
                    "recognition_state": "unknown",
                    "recognized_thing_mosaic_receipt_sha256": None,
                    "state_authority_receipt_sha256": None,
                }
            return observation | {
                "attention_state": current.attention_state,
                "candidate_thing_count": len(
                    current.candidate_thing_mosaic_receipt_sha256s
                ),
                "context_id": current.context.context_id,
                "current_full_field_root_count": len(
                    current.context.current_full_field_roots
                ),
                "focused_relation_receipt_sha256": (
                    current.focused_relation_receipt_sha256
                ),
                "inquiry_authorized": current.inquiry_authorized,
                "participating_senses": list(current.participating_senses),
                "path_count": len(current.paths),
                "recognition_state": current.recognition_state,
                "recognized_thing_mosaic_receipt_sha256": (
                    current.recognized_thing_mosaic_receipt_sha256
                ),
                "state_authority_receipt_sha256": (
                    current.authority_receipt_sha256
                ),
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: CausalRecognitionAttentionProfile,
        path_authority: CausalThingRelationPathAuthority,
        context_authority: WholeOrganismAttentionContextAuthority,
        encoded: bytes,
    ) -> "CausalRecognitionAttentionOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("recognition cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("recognition cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("recognition cold envelope changed")
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body) != {"profile", "schema", "state"}
            or body.get("schema") != OWNER_SCHEMA
            or body.get("profile") != profile.record()
        ):
            raise ValueError("recognition cold payload changed")
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            path_authority=path_authority,
            context_authority=context_authority,
        )
        expected = hmac.new(
            owner._owner_key,
            _OWNER_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""), expected
        ):
            raise ValueError("recognition cold state authority changed")
        if body["state"] is not None:
            owner._state = owner._state_from_raw(body["state"])
        if owner.snapshot_encoded() != encoded:
            raise ValueError("recognition cold round-trip changed state")
        return owner

    def _path_from_raw(self, raw: object) -> CausalThingRelationPath:
        expected = set(CausalThingRelationPath.__dataclass_fields__) | {
            "schema"
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != PATH_SCHEMA
        ):
            raise ValueError("cold recognition path changed")
        return CausalThingRelationPath(
            tapestry_receipt_sha256=raw["tapestry_receipt_sha256"],
            thing_mosaic_receipt_sha256=(
                raw["thing_mosaic_receipt_sha256"]
            ),
            chain_id=raw["chain_id"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"], "cold path start"
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"], "cold path end"
            ),
            contributing_senses=tuple(raw["contributing_senses"]),
            candidate_full_field_roots=tuple(
                _root_from_raw(value)
                for value in raw["candidate_full_field_roots"]
            ),
            complete_tapestry_full_field_roots=tuple(
                _root_from_raw(value)
                for value in raw["complete_tapestry_full_field_roots"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    @staticmethod
    def _context_from_raw(raw: object) -> WholeOrganismAttentionContext:
        expected = set(WholeOrganismAttentionContext.__dataclass_fields__) | {
            "schema"
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != CONTEXT_SCHEMA
        ):
            raise ValueError("cold attention context changed")
        return WholeOrganismAttentionContext(
            context_id=raw["context_id"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"], "cold context start"
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"], "cold context end"
            ),
            current_full_field_roots=tuple(
                _root_from_raw(value)
                for value in raw["current_full_field_roots"]
            ),
            needs_state_json=raw["needs_state_json"],
            body_state_json=raw["body_state_json"],
            chemical_state_json=raw["chemical_state_json"],
            causal_context_json=raw["causal_context_json"],
            lawful_action_relation_receipts=tuple(
                raw["lawful_action_relation_receipts"]
            ),
            lawful_inquiry_relation_receipts=tuple(
                raw["lawful_inquiry_relation_receipts"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    def _state_from_raw(
        self, raw: object
    ) -> CausalRecognitionAttentionState:
        expected = set(CausalRecognitionAttentionState.__dataclass_fields__) | {
            "schema"
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != STATE_SCHEMA
        ):
            raise ValueError("cold recognition state changed")
        state = CausalRecognitionAttentionState(
            recognition_state=raw["recognition_state"],
            recognized_thing_mosaic_receipt_sha256=(
                raw["recognized_thing_mosaic_receipt_sha256"]
            ),
            candidate_thing_mosaic_receipt_sha256s=tuple(
                raw["candidate_thing_mosaic_receipt_sha256s"]
            ),
            participating_senses=tuple(raw["participating_senses"]),
            paths=tuple(self._path_from_raw(value) for value in raw["paths"]),
            context=self._context_from_raw(raw["context"]),
            attention_state=raw["attention_state"],
            focused_relation_receipt_sha256=(
                raw["focused_relation_receipt_sha256"]
            ),
            inquiry_authorized=raw["inquiry_authorized"],
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )
        self._verify_state(state)
        return state


__all__ = (
    "CausalRecognitionAttentionOwner",
    "CausalRecognitionAttentionProfile",
    "CausalRecognitionAttentionState",
    "CausalRecognitionAttentionUndo",
    "CausalThingRelationPath",
    "CausalThingRelationPathAuthority",
    "PreparedCausalRecognitionAttention",
    "WholeOrganismAttentionContext",
    "WholeOrganismAttentionContextAuthority",
)
