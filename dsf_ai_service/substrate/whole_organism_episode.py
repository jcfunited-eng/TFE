"""Fail-closed authority for one contiguous whole-organism episode.

This owner is the typed post-mount boundary required by
``docs/WHOLE_ORGANISM_CONTIGUITY_LAW.md``.  Raw settlements, component
receipts, and caller-selected mechanism subsets cannot grant downstream
authority.

The mounted-mechanism manifest is authenticated before an episode begins.
Every resolution must carry exactly one contribution for every manifest row.
Perturbed receptor families are verified from the exact causal settlement and
its complete L0--L4 THING roots.  Quiescence is the mounted mechanism's true
uncommitted zero and carries no fabricated L0--L4 trajectory.  Physical
recovery is a perturbation and retains its actual ``N_gate`` evidence.
Unavailable state is explicit and cannot masquerade as quiescence.

An authorized action is not learned experience.  It grants only execution and
consequence-binding authority.  Learning, certainty, speech, and L6 release
exist only after a later physical consequence is completely sensed, joined to
the same causal chain, and settled by L6.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Mapping, Sequence

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.native_evidence_custody import (
    NativeEvidenceTransitionIndex,
)


MANIFEST_SCHEMA = "guala.whole_organism.mounted_manifest.v1"
CONTRIBUTION_SCHEMA = "guala.whole_organism.contribution.v1"
EPISODE_SCHEMA = "guala.whole_organism.episode.v2"
CAPABILITY_SCHEMA = "guala.whole_organism.capability.v1"
STATE_SCHEMA = "guala.whole_organism.state.v1"
STATE_ENVELOPE_SCHEMA = "guala.whole_organism.state_hmac.v1"

_MANIFEST_DOMAIN = b"guala-whole-organism-manifest-v1\0"
_CONTRIBUTION_DOMAIN = b"guala-whole-organism-contribution-v1\0"
_EPISODE_DOMAIN = b"guala-whole-organism-episode-v1\0"
_CAPABILITY_DOMAIN = b"guala-whole-organism-capability-v1\0"
_STATE_DOMAIN = b"guala-whole-organism-state-v1\0"
_DRAFT_AUTHORITY = object()
_VERIFIED_DRAFT_CUSTODY_AUTHORITY = object()
_MECHANISM_CAPABILITY_AUTHORITY = object()
_PREPARED_CONTRIBUTION_AUTHORITY = object()

MAX_MANIFEST_MECHANISMS = 512
MAX_EPISODES = 4_096
MAX_STATE_BYTES = 256 * 1024 * 1024
MAX_CANONICAL_STATE_BYTES = 4 * 1024 * 1024
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


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("whole-organism authority key is invalid")
    return raw


def _fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, Fraction):
        raise TypeError(f"{label} must be an exact Fraction")
    return value


def _fraction_text(value: Fraction) -> str:
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


def _canonical_state(value: object, label: str) -> str:
    try:
        encoded = _canonical(value)
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not canonical JSON state") from error
    if not isinstance(decoded, (dict, list)):
        raise ValueError(f"{label} must be structured JSON state")
    if len(encoded) > MAX_CANONICAL_STATE_BYTES:
        raise ValueError(f"{label} exceeds its exact byte boundary")
    return encoded.decode("utf-8")


def _verify_canonical_state(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not canonical JSON text")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is not readable") from error
    if _canonical(decoded).decode("utf-8") != value:
        raise ValueError(f"{label} is not canonical")
    if not isinstance(decoded, (dict, list)):
        raise ValueError(f"{label} must be structured JSON state")
    if len(value.encode("utf-8")) > MAX_CANONICAL_STATE_BYTES:
        raise ValueError(f"{label} exceeds its exact byte boundary")
    return value


class MechanismKind(str, Enum):
    RECEPTOR_FAMILY = "receptor_family"
    STATEFUL = "stateful"


class MechanismAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ContributionState(str, Enum):
    PERTURBED = "perturbed"
    QUIESCENT = "quiescent"
    UNAVAILABLE = "unavailable"


class WholeOrganismEpisodePhase(str, Enum):
    OBSERVATION_COMPLETED = "observation_completed"
    ACTION_AUTHORIZED = "action_authorized"
    CONSEQUENCE_COMPLETED = "consequence_completed"


class L6Disposition(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    SETTLED = "settled"
    UNRESOLVED = "unresolved"


class DownstreamAuthority(str, Enum):
    ACTION_EXECUTION = "action_execution"
    CONSEQUENCE_BINDING = "consequence_binding"
    LEARNING = "learning"
    CERTAINTY = "certainty"
    SPEECH = "speech"
    L6_COMMIT = "l6_commit"


@dataclass(frozen=True, slots=True)
class MountedMechanismSpec:
    mechanism_id: str
    kind: MechanismKind
    availability: MechanismAvailability
    evidence_schema: str
    parent_mechanism_ids: tuple[str, ...]
    sense: str | None = None
    binds_full_field_roots: bool = False
    unavailable_reason: str | None = None
    physical_quantity: str | None = None
    physical_unit: str | None = None
    physical_extent: str | None = None
    causal_clock: str | None = None
    transduction_authority_receipt_sha256: str | None = None
    custody_authority_receipt_sha256: str | None = None
    quiescent_semantics: str = "mounted-uncommitted-zero"
    unavailable_semantics: str = "explicit-provider-unavailable"
    max_evidence_bytes: int = MAX_CANONICAL_STATE_BYTES

    def verify(self, prior_ids: frozenset[str]) -> None:
        _identifier(self.mechanism_id, "mounted mechanism id")
        if not isinstance(self.kind, MechanismKind):
            raise TypeError("mounted mechanism kind is not typed")
        if not isinstance(self.availability, MechanismAvailability):
            raise TypeError("mounted mechanism availability is not typed")
        _identifier(self.evidence_schema, "mechanism evidence schema")
        if (
            not isinstance(self.parent_mechanism_ids, tuple)
            or tuple(sorted(set(self.parent_mechanism_ids)))
            != self.parent_mechanism_ids
            or any(value not in prior_ids for value in self.parent_mechanism_ids)
        ):
            raise ValueError(
                "mounted mechanism parents are not a predeclared causal prefix"
            )
        if not isinstance(self.binds_full_field_roots, bool):
            raise TypeError("full-field root binding flag is not boolean")
        _identifier(
            self.quiescent_semantics,
            "mounted mechanism quiescent semantics",
        )
        _identifier(
            self.unavailable_semantics,
            "mounted mechanism unavailable semantics",
        )
        if (
            isinstance(self.max_evidence_bytes, bool)
            or not isinstance(self.max_evidence_bytes, int)
            or not 1 <= self.max_evidence_bytes
            <= MAX_CANONICAL_STATE_BYTES
        ):
            raise ValueError("mounted mechanism evidence bound changed")
        if self.kind is MechanismKind.RECEPTOR_FAMILY:
            _identifier(self.sense, "mounted receptor family")
            if self.binds_full_field_roots is not True:
                raise ValueError(
                    "receptor family must bind its complete roots"
                )
            for value, label in (
                (self.physical_quantity, "receptor physical quantity"),
                (self.physical_unit, "receptor physical unit"),
                (self.physical_extent, "receptor physical extent"),
                (self.causal_clock, "receptor causal clock"),
            ):
                _identifier(value, label)
            for value, label in (
                (
                    self.transduction_authority_receipt_sha256,
                    "receptor transduction authority",
                ),
                (
                    self.custody_authority_receipt_sha256,
                    "receptor custody authority",
                ),
            ):
                _sha(value, label)
        elif self.sense is not None:
            raise ValueError(
                "nonreceptor mechanism names a receptor family"
            )
        elif any(
            value is not None
            for value in (
                self.physical_quantity,
                self.physical_unit,
                self.physical_extent,
                self.causal_clock,
                self.transduction_authority_receipt_sha256,
                self.custody_authority_receipt_sha256,
            )
        ):
            raise ValueError(
                "nonreceptor mechanism carries receptor physics"
            )
        if self.availability is MechanismAvailability.UNAVAILABLE:
            _identifier(
                self.unavailable_reason,
                "predeclared unavailable reason",
            )
        elif self.unavailable_reason is not None:
            raise ValueError(
                "available mechanism carries an unavailable declaration"
            )

    def record(self) -> dict[str, object]:
        return {
            "availability": self.availability.value,
            "binds_full_field_roots": self.binds_full_field_roots,
            "evidence_schema": self.evidence_schema,
            "kind": self.kind.value,
            "mechanism_id": self.mechanism_id,
            "max_evidence_bytes": self.max_evidence_bytes,
            "parent_mechanism_ids": list(self.parent_mechanism_ids),
            "physical_extent": self.physical_extent,
            "physical_quantity": self.physical_quantity,
            "physical_unit": self.physical_unit,
            "causal_clock": self.causal_clock,
            "custody_authority_receipt_sha256": (
                self.custody_authority_receipt_sha256
            ),
            "quiescent_semantics": self.quiescent_semantics,
            "sense": self.sense,
            "transduction_authority_receipt_sha256": (
                self.transduction_authority_receipt_sha256
            ),
            "unavailable_reason": self.unavailable_reason,
            "unavailable_semantics": self.unavailable_semantics,
        }


@dataclass(frozen=True, slots=True)
class MountedMechanismManifest:
    manifest_id: str
    topology_authority_receipt_sha256: str
    mechanisms: tuple[MountedMechanismSpec, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "mechanisms": [value.record() for value in self.mechanisms],
            "schema": MANIFEST_SCHEMA,
            "topology_authority_receipt_sha256": (
                self.topology_authority_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        _identifier(self.manifest_id, "mounted manifest id")
        _sha(
            self.topology_authority_receipt_sha256,
            "mounted topology authority",
        )
        if (
            not isinstance(self.mechanisms, tuple)
            or not self.mechanisms
            or len(self.mechanisms) > MAX_MANIFEST_MECHANISMS
        ):
            raise ValueError("mounted mechanism manifest cardinality is invalid")
        prior: set[str] = set()
        receptor_families = []
        for mechanism in self.mechanisms:
            if not isinstance(mechanism, MountedMechanismSpec):
                raise TypeError("mounted mechanism manifest is not typed")
            mechanism.verify(frozenset(prior))
            if mechanism.mechanism_id in prior:
                raise ValueError("mounted mechanism manifest repeats identity")
            prior.add(mechanism.mechanism_id)
            if mechanism.sense is not None:
                receptor_families.append(mechanism.sense)
        if (
            not receptor_families
            or len(set(receptor_families)) != len(receptor_families)
        ):
            raise ValueError(
                "mounted manifest receptor families are absent or repeated"
            )
        payload = self.payload()
        manifest_key = hashlib.sha256(
            _MANIFEST_DOMAIN + _key(authority_key)
        ).digest()
        expected_hmac = hmac.new(
            manifest_key,
            _MANIFEST_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            self.authority_hmac_sha256 != expected_hmac
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("mounted mechanism manifest authority changed")


def create_mounted_mechanism_manifest(
    *,
    authority_key: bytes | str,
    manifest_id: str,
    topology_authority_receipt_sha256: str,
    mechanisms: Sequence[MountedMechanismSpec],
) -> MountedMechanismManifest:
    provisional = MountedMechanismManifest(
        manifest_id=manifest_id,
        topology_authority_receipt_sha256=(
            topology_authority_receipt_sha256
        ),
        mechanisms=tuple(mechanisms),
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    payload = provisional.payload()
    manifest_key = hashlib.sha256(
        _MANIFEST_DOMAIN + _key(authority_key)
    ).digest()
    signature = hmac.new(
        manifest_key,
        _MANIFEST_DOMAIN + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    result = MountedMechanismManifest(
        manifest_id=provisional.manifest_id,
        topology_authority_receipt_sha256=(
            provisional.topology_authority_receipt_sha256
        ),
        mechanisms=provisional.mechanisms,
        authority_hmac_sha256=signature,
        authority_receipt_sha256=_digest({
            "authority_hmac_sha256": signature,
            "payload": payload,
        }),
    )
    result.verify(authority_key)
    return result


def _root_receipt(root: FullFieldSensoryRoot) -> str:
    root.verify()
    return _digest(root.record())


def _root_from_record(value: object) -> FullFieldSensoryRoot:
    if not isinstance(value, dict) or set(value) != {
        "full_evidence_json",
        "physical_value_sha256",
        "schema",
        "sense",
        "topology_index",
    }:
        raise ValueError("whole-organism full-field root record changed")
    root = FullFieldSensoryRoot(
        sense=value["sense"],
        topology_index=value["topology_index"],
        physical_value_sha256=value["physical_value_sha256"],
        full_evidence_json=value["full_evidence_json"],
    )
    root.verify()
    _verify_root_field(root)
    return root


def _verify_root_field(root: FullFieldSensoryRoot) -> None:
    root.verify()


def _verified_roots(
    settlement: CausalExperienceSettlement,
) -> tuple[FullFieldSensoryRoot, ...]:
    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError("whole-organism episode requires an exact settlement")
    roots = full_field_sensory_roots(settlement)
    for root in roots:
        _verify_root_field(root)
    return roots


@dataclass(frozen=True, slots=True)
class WholeOrganismMechanismCapability:
    episode_id: str
    manifest_receipt_sha256: str
    mechanism_id: str
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class _VerifiedDraftCustody:
    settlement: CausalExperienceSettlement = field(
        repr=False,
        compare=False,
    )
    roots: tuple[FullFieldSensoryRoot, ...] = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class WholeOrganismEpisodeDraft:
    episode_id: str
    chain_id: str
    phase: WholeOrganismEpisodePhase
    settlement: CausalExperienceSettlement = field(repr=False, compare=False)
    source_time_start: Fraction
    source_time_end: Fraction
    manifest_receipt_sha256: str
    action_authority_receipt_sha256: str | None
    prior_episode_receipt_sha256: str | None
    action_execution_receipt_sha256: str | None
    l6_disposition: L6Disposition
    l6_authority_receipt_sha256: str | None
    _verified_custody: _VerifiedDraftCustody = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PreparedMechanismContribution:
    episode_id: str
    mechanism_id: str
    state: ContributionState
    source_time_start: Fraction
    source_time_end: Fraction
    semantic_evidence_json: str
    semantic_evidence_receipt_sha256: str
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class WholeOrganismMechanismContribution:
    episode_id: str
    mechanism_id: str
    state: ContributionState
    source_time_start: Fraction
    source_time_end: Fraction
    parent_contribution_receipts: tuple[tuple[str, str], ...]
    semantic_evidence_json: str
    semantic_evidence_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "mechanism_id": self.mechanism_id,
            "parent_contribution_receipts": [
                list(value) for value in self.parent_contribution_receipts
            ],
            "schema": CONTRIBUTION_SCHEMA,
            "semantic_evidence_json": self.semantic_evidence_json,
            "semantic_evidence_receipt_sha256": (
                self.semantic_evidence_receipt_sha256
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "state": self.state.value,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismEpisodeRecord:
    episode_id: str
    chain_id: str
    phase: WholeOrganismEpisodePhase
    manifest_receipt_sha256: str
    settlement_event_id: str
    settlement_authority_receipt_sha256: str
    settlement_structural_fingerprint: str
    source_time_start: Fraction
    source_time_end: Fraction
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    native_evidence_transition: NativeEvidenceTransitionIndex
    contributions: tuple[WholeOrganismMechanismContribution, ...]
    action_authority_receipt_sha256: str | None
    prior_episode_receipt_sha256: str | None
    action_execution_receipt_sha256: str | None
    l6_disposition: L6Disposition
    l6_authority_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_authority_receipt_sha256": (
                self.action_authority_receipt_sha256
            ),
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256
            ),
            "chain_id": self.chain_id,
            "contributions": [value.record() for value in self.contributions],
            "episode_id": self.episode_id,
            "full_field_roots": [
                value.record() for value in self.full_field_roots
            ],
            "native_evidence_transition": (
                self.native_evidence_transition.record()
            ),
            "l6_authority_receipt_sha256": (
                self.l6_authority_receipt_sha256
            ),
            "l6_disposition": self.l6_disposition.value,
            "manifest_receipt_sha256": self.manifest_receipt_sha256,
            "phase": self.phase.value,
            "prior_episode_receipt_sha256": (
                self.prior_episode_receipt_sha256
            ),
            "schema": EPISODE_SCHEMA,
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "settlement_event_id": self.settlement_event_id,
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismEpisodeCapability:
    episode_id: str
    episode_authority_receipt_sha256: str
    phase: WholeOrganismEpisodePhase
    authorities: tuple[DownstreamAuthority, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "authorities": [value.value for value in self.authorities],
            "episode_authority_receipt_sha256": (
                self.episode_authority_receipt_sha256
            ),
            "episode_id": self.episode_id,
            "phase": self.phase.value,
            "schema": CAPABILITY_SCHEMA,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismEpisodeResolution:
    state: str
    reasons: tuple[str, ...]
    record: WholeOrganismEpisodeRecord | None
    capability: WholeOrganismEpisodeCapability | None


class WholeOrganismEpisodeAuthority:
    """Own bounded completed episodes and issue phase-limited capabilities."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        manifest: MountedMechanismManifest,
        max_episodes: int = 64,
        max_state_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        raw_key = _key(authority_key)
        manifest.verify(raw_key)
        if (
            isinstance(max_episodes, bool)
            or not isinstance(max_episodes, int)
            or not 1 <= max_episodes <= MAX_EPISODES
        ):
            raise ValueError("whole-organism episode capacity is invalid")
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 1 <= max_state_bytes <= MAX_STATE_BYTES
        ):
            raise ValueError("whole-organism state byte capacity is invalid")
        self._manifest_key = hashlib.sha256(
            _MANIFEST_DOMAIN + raw_key
        ).digest()
        self._contribution_key = hashlib.sha256(
            _CONTRIBUTION_DOMAIN + raw_key
        ).digest()
        self._episode_key = hashlib.sha256(
            _EPISODE_DOMAIN + raw_key
        ).digest()
        self._capability_key = hashlib.sha256(
            _CAPABILITY_DOMAIN + raw_key
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + raw_key
        ).digest()
        self._manifest = manifest
        self._max_episodes = max_episodes
        self._max_state_bytes = max_state_bytes
        self._episodes: dict[str, WholeOrganismEpisodeRecord] = {}
        self._draft_authority = object()
        self._lock = threading.RLock()

    @property
    def manifest(self) -> MountedMechanismManifest:
        return self._manifest

    @property
    def episodes(self) -> tuple[WholeOrganismEpisodeRecord, ...]:
        with self._lock:
            return tuple(
                self._episodes[value] for value in sorted(self._episodes)
            )

    def _episode_identity(
        self,
        *,
        chain_id: str,
        phase: WholeOrganismEpisodePhase,
        settlement: CausalExperienceSettlement,
        action_authority_receipt_sha256: str | None,
        prior_episode_receipt_sha256: str | None,
        action_execution_receipt_sha256: str | None,
    ) -> str:
        return _digest({
            "action_authority_receipt_sha256": (
                action_authority_receipt_sha256
            ),
            "action_execution_receipt_sha256": (
                action_execution_receipt_sha256
            ),
            "chain_id": chain_id,
            "manifest_receipt_sha256": (
                self._manifest.authority_receipt_sha256
            ),
            "phase": phase.value,
            "prior_episode_receipt_sha256": prior_episode_receipt_sha256,
            "settlement_authority_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "source_time_end": _fraction_text(settlement.source_time_end),
            "source_time_start": _fraction_text(settlement.source_time_start),
        })

    def _draft(
        self,
        *,
        chain_id: str,
        phase: WholeOrganismEpisodePhase,
        settlement: CausalExperienceSettlement,
        action_authority_receipt_sha256: str | None,
        prior_episode_receipt_sha256: str | None,
        action_execution_receipt_sha256: str | None,
        l6_disposition: L6Disposition,
        l6_authority_receipt_sha256: str | None,
    ) -> WholeOrganismEpisodeDraft:
        _identifier(chain_id, "whole-organism causal chain id")
        verified_roots = _verified_roots(settlement)
        if not isinstance(phase, WholeOrganismEpisodePhase):
            raise TypeError("whole-organism episode phase is not typed")
        if not isinstance(l6_disposition, L6Disposition):
            raise TypeError("whole-organism L6 disposition is not typed")
        for value, label in (
            (action_authority_receipt_sha256, "action authority"),
            (prior_episode_receipt_sha256, "prior episode"),
            (action_execution_receipt_sha256, "action execution"),
            (l6_authority_receipt_sha256, "L6 authority"),
        ):
            if value is not None:
                _sha(value, label)
        if phase is WholeOrganismEpisodePhase.ACTION_AUTHORIZED:
            if (
                action_authority_receipt_sha256 is None
                or prior_episode_receipt_sha256 is not None
                or action_execution_receipt_sha256 is not None
                or l6_disposition is not L6Disposition.NOT_APPLICABLE
                or l6_authority_receipt_sha256 is not None
            ):
                raise ValueError("action authorization phase changed shape")
        elif phase is WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED:
            if (
                action_authority_receipt_sha256 is None
                or prior_episode_receipt_sha256 is None
                or action_execution_receipt_sha256 is None
            ):
                raise ValueError("consequence phase lacks its causal prefix")
        elif (
            action_authority_receipt_sha256 is not None
            or prior_episode_receipt_sha256 is not None
            or action_execution_receipt_sha256 is not None
        ):
            raise ValueError("observation phase carries action authority")
        return WholeOrganismEpisodeDraft(
            episode_id=self._episode_identity(
                chain_id=chain_id,
                phase=phase,
                settlement=settlement,
                action_authority_receipt_sha256=(
                    action_authority_receipt_sha256
                ),
                prior_episode_receipt_sha256=(
                    prior_episode_receipt_sha256
                ),
                action_execution_receipt_sha256=(
                    action_execution_receipt_sha256
                ),
            ),
            chain_id=chain_id,
            phase=phase,
            settlement=settlement,
            source_time_start=settlement.source_time_start,
            source_time_end=settlement.source_time_end,
            manifest_receipt_sha256=(
                self._manifest.authority_receipt_sha256
            ),
            action_authority_receipt_sha256=(
                action_authority_receipt_sha256
            ),
            prior_episode_receipt_sha256=prior_episode_receipt_sha256,
            action_execution_receipt_sha256=(
                action_execution_receipt_sha256
            ),
            l6_disposition=l6_disposition,
            l6_authority_receipt_sha256=l6_authority_receipt_sha256,
            _verified_custody=_VerifiedDraftCustody(
                settlement=settlement,
                roots=verified_roots,
                _owner_authority=self._draft_authority,
                _construction_authority=(
                    _VERIFIED_DRAFT_CUSTODY_AUTHORITY
                ),
            ),
            _owner_authority=self._draft_authority,
            _construction_authority=_DRAFT_AUTHORITY,
        )

    def begin_observation(
        self,
        *,
        chain_id: str,
        settlement: CausalExperienceSettlement,
        l6_disposition: L6Disposition,
        l6_authority_receipt_sha256: str | None,
    ) -> WholeOrganismEpisodeDraft:
        return self._draft(
            chain_id=chain_id,
            phase=WholeOrganismEpisodePhase.OBSERVATION_COMPLETED,
            settlement=settlement,
            action_authority_receipt_sha256=None,
            prior_episode_receipt_sha256=None,
            action_execution_receipt_sha256=None,
            l6_disposition=l6_disposition,
            l6_authority_receipt_sha256=l6_authority_receipt_sha256,
        )

    def begin_action_authorization(
        self,
        *,
        chain_id: str,
        settlement: CausalExperienceSettlement,
        action_authority_receipt_sha256: str,
    ) -> WholeOrganismEpisodeDraft:
        return self._draft(
            chain_id=chain_id,
            phase=WholeOrganismEpisodePhase.ACTION_AUTHORIZED,
            settlement=settlement,
            action_authority_receipt_sha256=(
                action_authority_receipt_sha256
            ),
            prior_episode_receipt_sha256=None,
            action_execution_receipt_sha256=None,
            l6_disposition=L6Disposition.NOT_APPLICABLE,
            l6_authority_receipt_sha256=None,
        )

    def begin_consequence(
        self,
        *,
        authorization: WholeOrganismEpisodeCapability,
        settlement: CausalExperienceSettlement,
        action_execution_receipt_sha256: str,
        l6_disposition: L6Disposition,
        l6_authority_receipt_sha256: str | None,
    ) -> WholeOrganismEpisodeDraft:
        prior = self.require(
            authorization,
            DownstreamAuthority.CONSEQUENCE_BINDING,
        )
        if prior.phase is not WholeOrganismEpisodePhase.ACTION_AUTHORIZED:
            raise ValueError("consequence predecessor is not an authorization")
        if settlement.source_time_start < prior.source_time_end:
            raise ValueError(
                "physical consequence begins before authorization closes"
            )
        return self._draft(
            chain_id=prior.chain_id,
            phase=WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED,
            settlement=settlement,
            action_authority_receipt_sha256=(
                prior.action_authority_receipt_sha256
            ),
            prior_episode_receipt_sha256=(
                prior.authority_receipt_sha256
            ),
            action_execution_receipt_sha256=(
                action_execution_receipt_sha256
            ),
            l6_disposition=l6_disposition,
            l6_authority_receipt_sha256=l6_authority_receipt_sha256,
        )

    def _verify_draft(self, draft: WholeOrganismEpisodeDraft) -> None:
        if (
            not isinstance(draft, WholeOrganismEpisodeDraft)
            or draft._construction_authority is not _DRAFT_AUTHORITY
            or draft._owner_authority is not self._draft_authority
            or draft.manifest_receipt_sha256
            != self._manifest.authority_receipt_sha256
            or not isinstance(
                draft._verified_custody,
                _VerifiedDraftCustody,
            )
            or draft._verified_custody._construction_authority
            is not _VERIFIED_DRAFT_CUSTODY_AUTHORITY
            or draft._verified_custody._owner_authority
            is not self._draft_authority
            or draft._verified_custody.settlement is not draft.settlement
        ):
            raise ValueError("whole-organism draft changed authority")
        if (
            draft.source_time_start != draft.settlement.source_time_start
            or draft.source_time_end != draft.settlement.source_time_end
            or draft.episode_id
            != self._episode_identity(
                chain_id=draft.chain_id,
                phase=draft.phase,
                settlement=draft.settlement,
                action_authority_receipt_sha256=(
                    draft.action_authority_receipt_sha256
                ),
                prior_episode_receipt_sha256=(
                    draft.prior_episode_receipt_sha256
                ),
                action_execution_receipt_sha256=(
                    draft.action_execution_receipt_sha256
                ),
            )
        ):
            raise ValueError("whole-organism draft changed episode identity")

    def _draft_roots(
        self,
        draft: WholeOrganismEpisodeDraft,
    ) -> tuple[FullFieldSensoryRoot, ...]:
        self._verify_draft(draft)
        return draft._verified_custody.roots

    def mechanism_capability(
        self,
        draft: WholeOrganismEpisodeDraft,
        mechanism_id: str,
    ) -> WholeOrganismMechanismCapability:
        self._verify_draft(draft)
        if mechanism_id not in {
            value.mechanism_id for value in self._manifest.mechanisms
        }:
            raise ValueError("mechanism capability names an unmounted mechanism")
        return WholeOrganismMechanismCapability(
            episode_id=draft.episode_id,
            manifest_receipt_sha256=(
                self._manifest.authority_receipt_sha256
            ),
            mechanism_id=mechanism_id,
            _owner_authority=self._draft_authority,
            _construction_authority=_MECHANISM_CAPABILITY_AUTHORITY,
        )

    def _spec(
        self,
        capability: WholeOrganismMechanismCapability,
        draft: WholeOrganismEpisodeDraft,
    ) -> MountedMechanismSpec:
        self._verify_draft(draft)
        if (
            not isinstance(capability, WholeOrganismMechanismCapability)
            or capability._construction_authority
            is not _MECHANISM_CAPABILITY_AUTHORITY
            or capability._owner_authority is not self._draft_authority
            or capability.episode_id != draft.episode_id
            or capability.manifest_receipt_sha256
            != self._manifest.authority_receipt_sha256
        ):
            raise ValueError("mechanism capability crossed episode authority")
        matches = tuple(
            value for value in self._manifest.mechanisms
            if value.mechanism_id == capability.mechanism_id
        )
        if len(matches) != 1:
            raise ValueError("mechanism capability lost its manifest row")
        return matches[0]

    def _prepared(
        self,
        *,
        draft: WholeOrganismEpisodeDraft,
        spec: MountedMechanismSpec,
        state: ContributionState,
        evidence: Mapping[str, object],
    ) -> PreparedMechanismContribution:
        semantic = _canonical(dict(evidence)).decode("utf-8")
        return PreparedMechanismContribution(
            episode_id=draft.episode_id,
            mechanism_id=spec.mechanism_id,
            state=state,
            source_time_start=draft.source_time_start,
            source_time_end=draft.source_time_end,
            semantic_evidence_json=semantic,
            semantic_evidence_receipt_sha256=hashlib.sha256(
                semantic.encode("utf-8")
            ).hexdigest(),
            _owner_authority=self._draft_authority,
            _construction_authority=_PREPARED_CONTRIBUTION_AUTHORITY,
        )

    def prepare_receptor_contribution(
        self,
        draft: WholeOrganismEpisodeDraft,
        capability: WholeOrganismMechanismCapability,
    ) -> PreparedMechanismContribution:
        spec = self._spec(capability, draft)
        if spec.kind is not MechanismKind.RECEPTOR_FAMILY:
            raise ValueError(
                "receptor contribution names a nonreceptor mechanism"
            )
        interpretations = tuple(
            value for value in draft.settlement.interpretations
            if value.sense == spec.sense
        )
        if len(interpretations) != 1:
            raise ValueError(
                "receptor family requires explicit provider contribution"
            )
        interpretation = interpretations[0]
        roots = tuple(
            value for value in self._draft_roots(draft)
            if value.sense == spec.sense
        )
        common = {
            "episode_id": draft.episode_id,
            "mechanism_id": spec.mechanism_id,
            "schema": spec.evidence_schema,
            "sense": spec.sense,
            "settlement_authority_receipt_sha256": (
                draft.settlement.authority_receipt_sha256
            ),
            "source_time_end": _fraction_text(draft.source_time_end),
            "source_time_start": _fraction_text(draft.source_time_start),
        }
        if interpretation.state == "sensor_unavailable":
            if roots:
                raise ValueError(
                    "unavailable receptor produced contradictory evidence"
                )
            return self._prepared(
                draft=draft,
                spec=spec,
                state=ContributionState.UNAVAILABLE,
                evidence={
                    **common,
                    "boundary_receipt_sha256": (
                        interpretation.boundary_receipt_sha256
                    ),
                    "unavailable_reason": (
                        spec.unavailable_reason
                        if spec.availability
                        is MechanismAvailability.UNAVAILABLE
                        else spec.unavailable_semantics
                    ),
                    "unavailable_semantics": (
                        spec.unavailable_semantics
                    ),
                    "root_receipt_sha256s": [],
                    "state": ContributionState.UNAVAILABLE.value,
                },
            )
        if interpretation.state in {"unknown", "quiescent"}:
            if roots:
                raise ValueError(
                    "quiescent receptor produced field perturbation"
                )
            return self._prepared(
                draft=draft,
                spec=spec,
                state=ContributionState.QUIESCENT,
                evidence={
                    **common,
                    "boundary_receipt_sha256": (
                        interpretation.boundary_receipt_sha256
                    ),
                    "quiescent_semantics": spec.quiescent_semantics,
                    "root_receipt_sha256s": [],
                    "rule": "mounted_receptor_uncommitted_zero",
                    "state": ContributionState.QUIESCENT.value,
                },
            )
        if spec.availability is MechanismAvailability.UNAVAILABLE:
            raise ValueError(
                "predeclared unavailable receptor claims perturbation"
            )
        if interpretation.state != "observed" or not roots:
            raise ValueError(
                "available sensory lane lacks complete perturbation evidence"
            )
        return self._prepared(
            draft=draft,
            spec=spec,
            state=ContributionState.PERTURBED,
            evidence={
                **common,
                "boundary_receipt_sha256": (
                    interpretation.boundary_receipt_sha256
                ),
                "root_receipt_sha256s": [
                    _root_receipt(value) for value in roots
                ],
                "state": ContributionState.PERTURBED.value,
            },
        )

    def prepare_perturbed_contribution(
        self,
        draft: WholeOrganismEpisodeDraft,
        capability: WholeOrganismMechanismCapability,
        *,
        state_before: object,
        state_after: object,
    ) -> PreparedMechanismContribution:
        spec = self._spec(capability, draft)
        if (
            spec.kind is not MechanismKind.STATEFUL
            or spec.availability is not MechanismAvailability.AVAILABLE
        ):
            raise ValueError("perturbation requires an available stateful mechanism")
        before = _canonical_state(state_before, "mechanism state before")
        after = _canonical_state(state_after, "mechanism state after")
        if before == after:
            raise ValueError("perturbed mechanism did not physically change")
        roots = self._draft_roots(draft)
        root_receipts = (
            tuple(_root_receipt(value) for value in roots)
            if spec.binds_full_field_roots else ()
        )
        return self._prepared(
            draft=draft,
            spec=spec,
            state=ContributionState.PERTURBED,
            evidence={
                "after_state_json": after,
                "after_state_sha256": hashlib.sha256(
                    after.encode("utf-8")
                ).hexdigest(),
                "before_state_json": before,
                "before_state_sha256": hashlib.sha256(
                    before.encode("utf-8")
                ).hexdigest(),
                "episode_id": draft.episode_id,
                "full_field_root_receipt_sha256s": list(root_receipts),
                "mechanism_id": spec.mechanism_id,
                "rule": "authenticated_before_then_after",
                "schema": spec.evidence_schema,
                "settlement_authority_receipt_sha256": (
                    draft.settlement.authority_receipt_sha256
                ),
                "source_time_end": _fraction_text(draft.source_time_end),
                "source_time_start": _fraction_text(draft.source_time_start),
                "state": ContributionState.PERTURBED.value,
            },
        )

    def prepare_current_perturbation_contribution(
        self,
        draft: WholeOrganismEpisodeDraft,
        capability: WholeOrganismMechanismCapability,
        *,
        current_state: object,
        current_state_authority_receipt_sha256: str,
    ) -> PreparedMechanismContribution:
        """Bind an authenticated currently active state without inventing before."""

        spec = self._spec(capability, draft)
        if (
            spec.kind is not MechanismKind.STATEFUL
            or spec.availability is not MechanismAvailability.AVAILABLE
        ):
            raise ValueError(
                "current perturbation requires an available stateful mechanism"
            )
        state = _canonical_state(
            current_state,
            "current mechanism perturbation state",
        )
        _sha(
            current_state_authority_receipt_sha256,
            "current mechanism perturbation authority",
        )
        roots = self._draft_roots(draft)
        root_receipts = (
            tuple(_root_receipt(value) for value in roots)
            if spec.binds_full_field_roots else ()
        )
        return self._prepared(
            draft=draft,
            spec=spec,
            state=ContributionState.PERTURBED,
            evidence={
                "current_state_authority_receipt_sha256": (
                    current_state_authority_receipt_sha256
                ),
                "current_state_json": state,
                "current_state_sha256": hashlib.sha256(
                    state.encode("utf-8")
                ).hexdigest(),
                "episode_id": draft.episode_id,
                "full_field_root_receipt_sha256s": list(root_receipts),
                "mechanism_id": spec.mechanism_id,
                "rule": "authenticated_current_state_perturbation",
                "schema": spec.evidence_schema,
                "settlement_authority_receipt_sha256": (
                    draft.settlement.authority_receipt_sha256
                ),
                "source_time_end": _fraction_text(draft.source_time_end),
                "source_time_start": _fraction_text(draft.source_time_start),
                "state": ContributionState.PERTURBED.value,
            },
        )

    def prepare_recovery_contribution(
        self,
        draft: WholeOrganismEpisodeDraft,
        capability: WholeOrganismMechanismCapability,
        *,
        stable_state: object,
        l1_n_gate_coordinates: Sequence[Fraction],
        recovery_authority_receipt_sha256: str,
    ) -> PreparedMechanismContribution:
        spec = self._spec(capability, draft)
        if (
            spec.kind is not MechanismKind.STATEFUL
            or spec.availability is not MechanismAvailability.AVAILABLE
        ):
            raise ValueError(
                "Negative Space requires an available stateful mechanism"
            )
        state = _canonical_state(stable_state, "Negative Space stable state")
        coordinates = tuple(l1_n_gate_coordinates)
        if (
            not coordinates
            or any(
                not isinstance(value, Fraction) or value != Fraction(1)
                for value in coordinates
            )
        ):
            raise ValueError(
                "Negative Space requires every actual L1 N_gate to equal one"
            )
        _sha(
            recovery_authority_receipt_sha256,
            "Negative Space recovery authority",
        )
        roots = self._draft_roots(draft)
        root_receipts = (
            tuple(_root_receipt(value) for value in roots)
            if spec.binds_full_field_roots else ()
        )
        return self._prepared(
            draft=draft,
            spec=spec,
            state=ContributionState.PERTURBED,
            evidence={
                "episode_id": draft.episode_id,
                "full_field_root_receipt_sha256s": list(root_receipts),
                "l1_n_gate_coordinates": [
                    _fraction_text(value) for value in coordinates
                ],
                "mechanism_id": spec.mechanism_id,
                "recovery_authority_receipt_sha256": (
                    recovery_authority_receipt_sha256
                ),
                "rule": "authenticated_recovery_with_actual_n_gate",
                "schema": spec.evidence_schema,
                "settlement_authority_receipt_sha256": (
                    draft.settlement.authority_receipt_sha256
                ),
                "source_time_end": _fraction_text(draft.source_time_end),
                "source_time_start": _fraction_text(draft.source_time_start),
                "stable_state_json": state,
                "stable_state_sha256": hashlib.sha256(
                    state.encode("utf-8")
                ).hexdigest(),
                "state": ContributionState.PERTURBED.value,
            },
        )

    def prepare_quiescent_contribution(
        self,
        draft: WholeOrganismEpisodeDraft,
        capability: WholeOrganismMechanismCapability,
        *,
        quiescent_state: object,
        quiescent_authority_receipt_sha256: str,
    ) -> PreparedMechanismContribution:
        spec = self._spec(capability, draft)
        if spec.availability is not MechanismAvailability.AVAILABLE:
            raise ValueError(
                "quiescence requires an available mounted mechanism"
            )
        state = _canonical_state(
            quiescent_state,
            "mounted quiescent state",
        )
        _sha(
            quiescent_authority_receipt_sha256,
            "mounted quiescent authority",
        )
        roots = self._draft_roots(draft)
        root_receipts = (
            tuple(_root_receipt(value) for value in roots)
            if spec.binds_full_field_roots else ()
        )
        return self._prepared(
            draft=draft,
            spec=spec,
            state=ContributionState.QUIESCENT,
            evidence={
                "episode_id": draft.episode_id,
                "full_field_root_receipt_sha256s": list(root_receipts),
                "mechanism_id": spec.mechanism_id,
                "quiescent_authority_receipt_sha256": (
                    quiescent_authority_receipt_sha256
                ),
                "quiescent_semantics": spec.quiescent_semantics,
                "quiescent_state_json": state,
                "quiescent_state_sha256": hashlib.sha256(
                    state.encode("utf-8")
                ).hexdigest(),
                "rule": "authenticated_mounted_uncommitted_zero",
                "schema": spec.evidence_schema,
                "settlement_authority_receipt_sha256": (
                    draft.settlement.authority_receipt_sha256
                ),
                "source_time_end": _fraction_text(draft.source_time_end),
                "source_time_start": _fraction_text(
                    draft.source_time_start
                ),
                "state": ContributionState.QUIESCENT.value,
            },
        )

    def prepare_unavailable_contribution(
        self,
        draft: WholeOrganismEpisodeDraft,
        capability: WholeOrganismMechanismCapability,
    ) -> PreparedMechanismContribution:
        spec = self._spec(capability, draft)
        if (
            spec.availability is not MechanismAvailability.UNAVAILABLE
        ):
            raise ValueError(
                "unavailable contribution was not predeclared before episode"
            )
        return self._prepared(
            draft=draft,
            spec=spec,
            state=ContributionState.UNAVAILABLE,
            evidence={
                "episode_id": draft.episode_id,
                "mechanism_id": spec.mechanism_id,
                "predeclared_unavailable_reason": spec.unavailable_reason,
                "schema": spec.evidence_schema,
                "source_time_end": _fraction_text(draft.source_time_end),
                "source_time_start": _fraction_text(draft.source_time_start),
                "state": ContributionState.UNAVAILABLE.value,
            },
        )

    def _verify_prepared(
        self,
        draft: WholeOrganismEpisodeDraft,
        prepared: PreparedMechanismContribution,
        spec: MountedMechanismSpec,
        roots: tuple[FullFieldSensoryRoot, ...],
    ) -> None:
        if (
            not isinstance(prepared, PreparedMechanismContribution)
            or prepared._construction_authority
            is not _PREPARED_CONTRIBUTION_AUTHORITY
            or prepared._owner_authority is not self._draft_authority
            or prepared.episode_id != draft.episode_id
            or prepared.mechanism_id != spec.mechanism_id
            or prepared.source_time_start != draft.source_time_start
            or prepared.source_time_end != draft.source_time_end
        ):
            raise ValueError("prepared contribution crossed episode authority")
        try:
            evidence = json.loads(prepared.semantic_evidence_json)
        except json.JSONDecodeError as error:
            raise ValueError("semantic mechanism evidence is unreadable") from error
        if (
            not isinstance(evidence, dict)
            or _canonical(evidence).decode("utf-8")
            != prepared.semantic_evidence_json
            or hashlib.sha256(
                prepared.semantic_evidence_json.encode("utf-8")
            ).hexdigest()
            != prepared.semantic_evidence_receipt_sha256
            or evidence.get("schema") != spec.evidence_schema
            or evidence.get("episode_id") != draft.episode_id
            or evidence.get("mechanism_id") != spec.mechanism_id
            or evidence.get("state") != prepared.state.value
            or evidence.get("source_time_start")
            != _fraction_text(draft.source_time_start)
            or evidence.get("source_time_end")
            != _fraction_text(draft.source_time_end)
        ):
            raise ValueError("semantic mechanism evidence changed")
        all_root_receipts = tuple(_root_receipt(value) for value in roots)
        if spec.kind is MechanismKind.RECEPTOR_FAMILY:
            interpretations = tuple(
                value for value in draft.settlement.interpretations
                if value.sense == spec.sense
            )
            if len(interpretations) != 1:
                raise ValueError(
                    "receptor family lacks explicit provider evidence"
                )
            interpretation = interpretations[0]
            sense_roots = tuple(
                value for value in roots if value.sense == spec.sense
            )
            expected_state = (
                ContributionState.PERTURBED
                if interpretation.state == "observed"
                else ContributionState.UNAVAILABLE
                if interpretation.state == "sensor_unavailable"
                else ContributionState.QUIESCENT
                if interpretation.state in {"unknown", "quiescent"}
                else None
            )
            if (
                expected_state is None
                or
                prepared.state is not expected_state
                or evidence.get("boundary_receipt_sha256")
                != interpretation.boundary_receipt_sha256
                or tuple(evidence.get("root_receipt_sha256s", ()))
                != tuple(_root_receipt(value) for value in sense_roots)
                or (
                    expected_state is ContributionState.PERTURBED
                    and not sense_roots
                )
                or (
                    expected_state is ContributionState.UNAVAILABLE
                    and (
                        sense_roots
                        or evidence.get("unavailable_semantics")
                        != spec.unavailable_semantics
                    )
                )
                or (
                    expected_state is ContributionState.QUIESCENT
                    and (
                        sense_roots
                        or evidence.get("quiescent_semantics")
                        != spec.quiescent_semantics
                        or evidence.get("rule")
                        != "mounted_receptor_uncommitted_zero"
                    )
                )
            ):
                raise ValueError(
                    "receptor contribution is not its mounted state"
                )
            return
        expected_roots = (
            all_root_receipts if spec.binds_full_field_roots else ()
        )
        if spec.availability is MechanismAvailability.UNAVAILABLE:
            if (
                prepared.state is not ContributionState.UNAVAILABLE
                or evidence.get("predeclared_unavailable_reason")
                != spec.unavailable_reason
            ):
                raise ValueError(
                    "unavailable mechanism differs from predeclared manifest"
                )
            return
        if prepared.state is ContributionState.PERTURBED and (
            evidence.get("rule") == "authenticated_before_then_after"
        ):
            before = _verify_canonical_state(
                evidence.get("before_state_json"),
                "perturbed before state",
            )
            after = _verify_canonical_state(
                evidence.get("after_state_json"),
                "perturbed after state",
            )
            if (
                before == after
                or evidence.get("before_state_sha256")
                != hashlib.sha256(before.encode("utf-8")).hexdigest()
                or evidence.get("after_state_sha256")
                != hashlib.sha256(after.encode("utf-8")).hexdigest()
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != draft.settlement.authority_receipt_sha256
            ):
                raise ValueError("stateful perturbation is not semantic evidence")
            return
        if prepared.state is ContributionState.PERTURBED and (
            evidence.get("rule")
            == "authenticated_recovery_with_actual_n_gate"
        ):
            stable = _verify_canonical_state(
                evidence.get("stable_state_json"),
                "recovery stable state",
            )
            raw_coordinates = evidence.get("l1_n_gate_coordinates")
            if (
                not isinstance(raw_coordinates, list)
                or not raw_coordinates
                or any(
                    _fraction_from_text(value, "recovery N_gate")
                    != Fraction(1)
                    for value in raw_coordinates
                )
                or evidence.get("stable_state_sha256")
                != hashlib.sha256(stable.encode("utf-8")).hexdigest()
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != draft.settlement.authority_receipt_sha256
            ):
                raise ValueError("recovery perturbation is not proved")
            _sha(
                evidence.get("recovery_authority_receipt_sha256"),
                "recovery perturbation authority",
            )
            return
        if prepared.state is ContributionState.PERTURBED and (
            evidence.get("rule")
            == "authenticated_current_state_perturbation"
        ):
            current = _verify_canonical_state(
                evidence.get("current_state_json"),
                "current perturbed state",
            )
            if (
                evidence.get("current_state_sha256")
                != hashlib.sha256(current.encode("utf-8")).hexdigest()
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != draft.settlement.authority_receipt_sha256
            ):
                raise ValueError(
                    "current perturbation is not proved"
                )
            _sha(
                evidence.get(
                    "current_state_authority_receipt_sha256"
                ),
                "current perturbation authority",
            )
            return
        if prepared.state is ContributionState.QUIESCENT:
            state = _verify_canonical_state(
                evidence.get("quiescent_state_json"),
                "mounted quiescent state",
            )
            if (
                evidence.get("quiescent_state_sha256")
                != hashlib.sha256(state.encode("utf-8")).hexdigest()
                or evidence.get("quiescent_semantics")
                != spec.quiescent_semantics
                or evidence.get("rule")
                != "authenticated_mounted_uncommitted_zero"
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != draft.settlement.authority_receipt_sha256
            ):
                raise ValueError("mounted quiescence is not proved")
            _sha(
                evidence.get("quiescent_authority_receipt_sha256"),
                "mounted quiescent authority",
            )
            return
        raise ValueError("available mechanism supplied unavailable evidence")

    def _seal_contribution(
        self,
        prepared: PreparedMechanismContribution,
        spec: MountedMechanismSpec,
        completed: Mapping[str, WholeOrganismMechanismContribution],
    ) -> WholeOrganismMechanismContribution:
        parents = tuple(
            (parent, completed[parent].authority_receipt_sha256)
            for parent in spec.parent_mechanism_ids
        )
        provisional = WholeOrganismMechanismContribution(
            episode_id=prepared.episode_id,
            mechanism_id=prepared.mechanism_id,
            state=prepared.state,
            source_time_start=prepared.source_time_start,
            source_time_end=prepared.source_time_end,
            parent_contribution_receipts=parents,
            semantic_evidence_json=prepared.semantic_evidence_json,
            semantic_evidence_receipt_sha256=(
                prepared.semantic_evidence_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._contribution_key,
            _CONTRIBUTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismMechanismContribution(
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
                "payload": payload,
            }),
        )

    def _verify_contribution(
        self,
        contribution: WholeOrganismMechanismContribution,
        spec: MountedMechanismSpec,
        completed: Mapping[str, WholeOrganismMechanismContribution],
    ) -> None:
        if not isinstance(contribution, WholeOrganismMechanismContribution):
            raise TypeError("whole-organism contribution is not typed")
        payload = contribution.payload()
        expected_hmac = hmac.new(
            self._contribution_key,
            _CONTRIBUTION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        expected_parents = tuple(
            (parent, completed[parent].authority_receipt_sha256)
            for parent in spec.parent_mechanism_ids
        )
        if (
            contribution.mechanism_id != spec.mechanism_id
            or contribution.parent_contribution_receipts
            != expected_parents
            or contribution.authority_hmac_sha256 != expected_hmac
            or contribution.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("whole-organism contribution authority changed")

    def _verify_contribution_semantics(
        self,
        *,
        record: WholeOrganismEpisodeRecord,
        contribution: WholeOrganismMechanismContribution,
        spec: MountedMechanismSpec,
    ) -> None:
        try:
            evidence = json.loads(contribution.semantic_evidence_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "stored mechanism evidence is unreadable"
            ) from error
        if (
            not isinstance(evidence, dict)
            or _canonical(evidence).decode("utf-8")
            != contribution.semantic_evidence_json
            or hashlib.sha256(
                contribution.semantic_evidence_json.encode("utf-8")
            ).hexdigest()
            != contribution.semantic_evidence_receipt_sha256
            or evidence.get("schema") != spec.evidence_schema
            or evidence.get("episode_id") != record.episode_id
            or evidence.get("mechanism_id") != spec.mechanism_id
            or evidence.get("state") != contribution.state.value
            or evidence.get("source_time_start")
            != _fraction_text(record.source_time_start)
            or evidence.get("source_time_end")
            != _fraction_text(record.source_time_end)
        ):
            raise ValueError("stored mechanism evidence changed semantics")
        all_root_receipts = tuple(
            _root_receipt(value) for value in record.full_field_roots
        )
        if spec.kind is MechanismKind.RECEPTOR_FAMILY:
            sense_roots = tuple(
                value for value in record.full_field_roots
                if value.sense == spec.sense
            )
            if (
                evidence.get("settlement_authority_receipt_sha256")
                != record.settlement_authority_receipt_sha256
                or tuple(evidence.get("root_receipt_sha256s", ()))
                != tuple(_root_receipt(value) for value in sense_roots)
            ):
                raise ValueError(
                    "stored receptor contribution changed meaning"
                )
            _sha(
                evidence.get("boundary_receipt_sha256"),
                "stored receptor boundary",
            )
            if contribution.state is ContributionState.PERTURBED:
                if not sense_roots:
                    raise ValueError(
                        "stored receptor perturbation lost its roots"
                    )
            elif contribution.state is ContributionState.UNAVAILABLE:
                if (
                    sense_roots
                    or evidence.get("unavailable_semantics")
                    != spec.unavailable_semantics
                ):
                    raise ValueError(
                        "stored unavailable receptor changed semantics"
                    )
            elif contribution.state is ContributionState.QUIESCENT:
                if (
                    sense_roots
                    or evidence.get("quiescent_semantics")
                    != spec.quiescent_semantics
                    or evidence.get("rule")
                    != "mounted_receptor_uncommitted_zero"
                ):
                    raise ValueError(
                        "stored quiescent receptor changed semantics"
                    )
            else:
                raise ValueError(
                    "stored receptor state is not lawful"
                )
            return
        expected_roots = (
            all_root_receipts if spec.binds_full_field_roots else ()
        )
        if spec.availability is MechanismAvailability.UNAVAILABLE:
            if (
                contribution.state is not ContributionState.UNAVAILABLE
                or evidence.get("predeclared_unavailable_reason")
                != spec.unavailable_reason
            ):
                raise ValueError(
                    "stored unavailable mechanism changed declaration"
                )
            return
        if contribution.state is ContributionState.PERTURBED and (
            evidence.get("rule") == "authenticated_before_then_after"
        ):
            before = _verify_canonical_state(
                evidence.get("before_state_json"),
                "stored perturbed before state",
            )
            after = _verify_canonical_state(
                evidence.get("after_state_json"),
                "stored perturbed after state",
            )
            if (
                before == after
                or evidence.get("before_state_sha256")
                != hashlib.sha256(before.encode("utf-8")).hexdigest()
                or evidence.get("after_state_sha256")
                != hashlib.sha256(after.encode("utf-8")).hexdigest()
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != record.settlement_authority_receipt_sha256
            ):
                raise ValueError(
                    "stored stateful perturbation changed semantics"
                )
            return
        if contribution.state is ContributionState.PERTURBED and (
            evidence.get("rule")
            == "authenticated_recovery_with_actual_n_gate"
        ):
            stable = _verify_canonical_state(
                evidence.get("stable_state_json"),
                "stored recovery state",
            )
            raw_coordinates = evidence.get("l1_n_gate_coordinates")
            if (
                not isinstance(raw_coordinates, list)
                or not raw_coordinates
                or any(
                    _fraction_from_text(
                        value,
                        "stored recovery N_gate",
                    )
                    != Fraction(1)
                    for value in raw_coordinates
                )
                or evidence.get("stable_state_sha256")
                != hashlib.sha256(stable.encode("utf-8")).hexdigest()
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != record.settlement_authority_receipt_sha256
            ):
                raise ValueError("stored recovery changed semantics")
            _sha(
                evidence.get("recovery_authority_receipt_sha256"),
                "stored recovery authority",
            )
            return
        if contribution.state is ContributionState.PERTURBED and (
            evidence.get("rule")
            == "authenticated_current_state_perturbation"
        ):
            current = _verify_canonical_state(
                evidence.get("current_state_json"),
                "stored current perturbed state",
            )
            if (
                evidence.get("current_state_sha256")
                != hashlib.sha256(current.encode("utf-8")).hexdigest()
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != record.settlement_authority_receipt_sha256
            ):
                raise ValueError(
                    "stored current perturbation changed semantics"
                )
            _sha(
                evidence.get(
                    "current_state_authority_receipt_sha256"
                ),
                "stored current perturbation authority",
            )
            return
        if contribution.state is ContributionState.QUIESCENT:
            state = _verify_canonical_state(
                evidence.get("quiescent_state_json"),
                "stored mounted quiescent state",
            )
            if (
                evidence.get("quiescent_state_sha256")
                != hashlib.sha256(state.encode("utf-8")).hexdigest()
                or evidence.get("quiescent_semantics")
                != spec.quiescent_semantics
                or evidence.get("rule")
                != "authenticated_mounted_uncommitted_zero"
                or tuple(
                    evidence.get("full_field_root_receipt_sha256s", ())
                )
                != expected_roots
                or evidence.get("settlement_authority_receipt_sha256")
                != record.settlement_authority_receipt_sha256
            ):
                raise ValueError("stored quiescence changed semantics")
            _sha(
                evidence.get("quiescent_authority_receipt_sha256"),
                "stored quiescent authority",
            )
            return
        raise ValueError(
            "stored available mechanism supplied unavailable evidence"
        )

    @staticmethod
    def _authorities_for_phase(
        phase: WholeOrganismEpisodePhase,
    ) -> tuple[DownstreamAuthority, ...]:
        if phase is WholeOrganismEpisodePhase.ACTION_AUTHORIZED:
            return (
                DownstreamAuthority.ACTION_EXECUTION,
                DownstreamAuthority.CONSEQUENCE_BINDING,
            )
        return (
            DownstreamAuthority.LEARNING,
            DownstreamAuthority.CERTAINTY,
            DownstreamAuthority.SPEECH,
            DownstreamAuthority.L6_COMMIT,
        )

    def _capability(
        self,
        record: WholeOrganismEpisodeRecord,
    ) -> WholeOrganismEpisodeCapability:
        provisional = WholeOrganismEpisodeCapability(
            episode_id=record.episode_id,
            episode_authority_receipt_sha256=(
                record.authority_receipt_sha256
            ),
            phase=record.phase,
            authorities=self._authorities_for_phase(record.phase),
            authority_hmac_sha256="0" * 64,
        )
        signature = hmac.new(
            self._capability_key,
            _CAPABILITY_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismEpisodeCapability(
            episode_id=provisional.episode_id,
            episode_authority_receipt_sha256=(
                provisional.episode_authority_receipt_sha256
            ),
            phase=provisional.phase,
            authorities=provisional.authorities,
            authority_hmac_sha256=signature,
        )

    def _seal_episode(
        self,
        draft: WholeOrganismEpisodeDraft,
        roots: tuple[FullFieldSensoryRoot, ...],
        contributions: tuple[WholeOrganismMechanismContribution, ...],
    ) -> WholeOrganismEpisodeRecord:
        provisional = WholeOrganismEpisodeRecord(
            episode_id=draft.episode_id,
            chain_id=draft.chain_id,
            phase=draft.phase,
            manifest_receipt_sha256=draft.manifest_receipt_sha256,
            settlement_event_id=draft.settlement.event_id,
            settlement_authority_receipt_sha256=(
                draft.settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                draft.settlement.structural_fingerprint
            ),
            source_time_start=draft.source_time_start,
            source_time_end=draft.source_time_end,
            full_field_roots=roots,
            native_evidence_transition=(
                draft.settlement.native_evidence_witness
                .transition_index()
            ),
            contributions=contributions,
            action_authority_receipt_sha256=(
                draft.action_authority_receipt_sha256
            ),
            prior_episode_receipt_sha256=(
                draft.prior_episode_receipt_sha256
            ),
            action_execution_receipt_sha256=(
                draft.action_execution_receipt_sha256
            ),
            l6_disposition=draft.l6_disposition,
            l6_authority_receipt_sha256=(
                draft.l6_authority_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._episode_key,
            _EPISODE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismEpisodeRecord(
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
                "payload": payload,
            }),
        )

    def _verify_episode_record(
        self,
        record: WholeOrganismEpisodeRecord,
    ) -> None:
        if not isinstance(record, WholeOrganismEpisodeRecord):
            raise TypeError("whole-organism episode record is not typed")
        if (
            record.manifest_receipt_sha256
            != self._manifest.authority_receipt_sha256
            or tuple(
                value.mechanism_id for value in record.contributions
            )
            != tuple(
                value.mechanism_id for value in self._manifest.mechanisms
            )
            or record.source_time_end <= record.source_time_start
        ):
            raise ValueError("whole-organism episode record changed shape")
        for root in record.full_field_roots:
            _verify_root_field(root)
        if not isinstance(
            record.native_evidence_transition,
            NativeEvidenceTransitionIndex,
        ):
            raise TypeError(
                "whole-organism native evidence witness is not typed"
            )
        record.native_evidence_transition.verify()
        completed: dict[str, WholeOrganismMechanismContribution] = {}
        for spec, contribution in zip(
            self._manifest.mechanisms,
            record.contributions,
            strict=True,
        ):
            if (
                contribution.episode_id != record.episode_id
                or contribution.source_time_start != record.source_time_start
                or contribution.source_time_end != record.source_time_end
            ):
                raise ValueError("episode contribution left its causal interval")
            self._verify_contribution(contribution, spec, completed)
            self._verify_contribution_semantics(
                record=record,
                contribution=contribution,
                spec=spec,
            )
            completed[spec.mechanism_id] = contribution
        if record.phase is WholeOrganismEpisodePhase.ACTION_AUTHORIZED:
            if (
                record.action_authority_receipt_sha256 is None
                or record.prior_episode_receipt_sha256 is not None
                or record.action_execution_receipt_sha256 is not None
                or record.l6_disposition is not L6Disposition.NOT_APPLICABLE
                or record.l6_authority_receipt_sha256 is not None
            ):
                raise ValueError("restored action authorization changed phase")
        else:
            if (
                record.l6_disposition is not L6Disposition.SETTLED
                or record.l6_authority_receipt_sha256 is None
            ):
                raise ValueError("completed episode lacks settled L6 authority")
        if record.phase is WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED:
            prior = self._episodes.get(record.prior_episode_receipt_sha256)
            if (
                prior is None
                or prior.phase
                is not WholeOrganismEpisodePhase.ACTION_AUTHORIZED
                or prior.chain_id != record.chain_id
                or prior.action_authority_receipt_sha256
                != record.action_authority_receipt_sha256
                or record.source_time_start < prior.source_time_end
                or record.action_execution_receipt_sha256 is None
            ):
                raise ValueError("consequence episode lost its authorization")
        payload = record.payload()
        expected_hmac = hmac.new(
            self._episode_key,
            _EPISODE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            record.authority_hmac_sha256 != expected_hmac
            or record.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("whole-organism episode authority changed")

    def resolve(
        self,
        draft: WholeOrganismEpisodeDraft,
        contributions: Sequence[PreparedMechanismContribution],
    ) -> WholeOrganismEpisodeResolution:
        """Atomically resolve or refuse without mutating retained state."""

        reasons: list[str] = []
        try:
            roots = self._draft_roots(draft)
        except (TypeError, ValueError) as error:
            return WholeOrganismEpisodeResolution(
                state="unresolved",
                reasons=(f"invalid_draft:{error}",),
                record=None,
                capability=None,
            )
        if draft.l6_disposition is L6Disposition.UNRESOLVED:
            reasons.append("l6_unresolved")
        elif (
            draft.phase is not WholeOrganismEpisodePhase.ACTION_AUTHORIZED
            and (
                draft.l6_disposition is not L6Disposition.SETTLED
                or draft.l6_authority_receipt_sha256 is None
            )
        ):
            reasons.append("l6_settlement_missing")
        values = tuple(contributions)
        by_id: dict[str, PreparedMechanismContribution] = {}
        for value in values:
            mechanism_id = getattr(value, "mechanism_id", "<untyped>")
            if mechanism_id in by_id:
                reasons.append(f"duplicate_contribution:{mechanism_id}")
            else:
                by_id[mechanism_id] = value
        expected = tuple(
            value.mechanism_id for value in self._manifest.mechanisms
        )
        for mechanism_id in expected:
            if mechanism_id not in by_id:
                reasons.append(f"missing_contribution:{mechanism_id}")
        for mechanism_id in sorted(set(by_id).difference(expected)):
            reasons.append(f"unmounted_contribution:{mechanism_id}")
        sealed: dict[str, WholeOrganismMechanismContribution] = {}
        contribution_shape_invalid = any(
            reason.startswith((
                "duplicate_contribution:",
                "missing_contribution:",
                "unmounted_contribution:",
            ))
            for reason in reasons
        )
        if not contribution_shape_invalid:
            for spec in self._manifest.mechanisms:
                prepared = by_id[spec.mechanism_id]
                try:
                    self._verify_prepared(draft, prepared, spec, roots)
                    contribution = self._seal_contribution(
                        prepared,
                        spec,
                        sealed,
                    )
                    self._verify_contribution(
                        contribution,
                        spec,
                        sealed,
                    )
                    sealed[spec.mechanism_id] = contribution
                except (TypeError, ValueError) as error:
                    reasons.append(
                        f"invalid_contribution:{spec.mechanism_id}:{error}"
                    )
                    break
        if reasons:
            return WholeOrganismEpisodeResolution(
                state="unresolved",
                reasons=tuple(sorted(reasons)),
                record=None,
                capability=None,
            )
        record = self._seal_episode(
            draft,
            roots,
            tuple(sealed[value] for value in expected),
        )
        with self._lock:
            existing = self._episodes.get(record.authority_receipt_sha256)
            if existing is not None:
                if existing != record:
                    raise ValueError("whole-organism episode receipt changed")
                return WholeOrganismEpisodeResolution(
                    state="resolved",
                    reasons=(),
                    record=existing,
                    capability=self._capability(existing),
                )
            if len(self._episodes) >= self._max_episodes:
                return WholeOrganismEpisodeResolution(
                    state="unresolved",
                    reasons=("episode_capacity_full",),
                    record=None,
                    capability=None,
                )
            staged = dict(self._episodes)
            staged[record.authority_receipt_sha256] = record
            try:
                self._encoded(staged)
            except ValueError as error:
                return WholeOrganismEpisodeResolution(
                    state="unresolved",
                    reasons=(str(error),),
                    record=None,
                    capability=None,
                )
            prior = self._episodes
            self._episodes = staged
            try:
                self._verify_episode_record(record)
            except BaseException:
                self._episodes = prior
                raise
        return WholeOrganismEpisodeResolution(
            state="resolved",
            reasons=(),
            record=record,
            capability=self._capability(record),
        )

    def require(
        self,
        capability: WholeOrganismEpisodeCapability,
        authority: DownstreamAuthority,
    ) -> WholeOrganismEpisodeRecord:
        if not isinstance(capability, WholeOrganismEpisodeCapability):
            raise TypeError("whole-organism capability is not typed")
        if not isinstance(authority, DownstreamAuthority):
            raise TypeError("requested downstream authority is not typed")
        expected_hmac = hmac.new(
            self._capability_key,
            _CAPABILITY_DOMAIN + _canonical(capability.payload()),
            hashlib.sha256,
        ).hexdigest()
        with self._lock:
            record = self._episodes.get(
                capability.episode_authority_receipt_sha256
            )
            if (
                record is None
                or record.episode_id != capability.episode_id
                or record.phase is not capability.phase
                or capability.authorities
                != self._authorities_for_phase(record.phase)
                or capability.authority_hmac_sha256 != expected_hmac
                or authority not in capability.authorities
            ):
                raise PermissionError(
                    "whole-organism episode does not grant requested authority"
                )
            return record

    def capability_for(
        self,
        episode_authority_receipt_sha256: str,
    ) -> WholeOrganismEpisodeCapability:
        _sha(
            episode_authority_receipt_sha256,
            "whole-organism episode authority",
        )
        with self._lock:
            record = self._episodes.get(episode_authority_receipt_sha256)
            if record is None:
                raise PermissionError(
                    "whole-organism episode is not retained by this authority"
                )
            return self._capability(record)

    def _state_payload(
        self,
        episodes: Mapping[str, WholeOrganismEpisodeRecord],
    ) -> dict[str, object]:
        phase_order = {
            WholeOrganismEpisodePhase.OBSERVATION_COMPLETED: 0,
            WholeOrganismEpisodePhase.ACTION_AUTHORIZED: 1,
            WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED: 2,
        }
        ordered = sorted(
            episodes.values(),
            key=lambda value: (
                value.source_time_start,
                value.source_time_end,
                phase_order[value.phase],
                value.authority_receipt_sha256,
            ),
        )
        return {
            "episodes": [value.record() for value in ordered],
            "manifest_receipt_sha256": (
                self._manifest.authority_receipt_sha256
            ),
            "max_episodes": self._max_episodes,
            "max_state_bytes": self._max_state_bytes,
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        episodes: Mapping[str, WholeOrganismEpisodeRecord],
    ) -> bytes:
        payload = self._state_payload(episodes)
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
            "schema": STATE_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise ValueError("whole-organism state capacity full")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._episodes)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        manifest: MountedMechanismManifest,
        encoded: bytes,
    ) -> "WholeOrganismEpisodeAuthority":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("whole-organism cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("whole-organism cold state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {
                "authority_hmac_sha256",
                "payload",
                "schema",
            }
            or envelope.get("schema") != STATE_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("whole-organism cold envelope changed")
        payload = envelope.get("payload")
        if (
            not isinstance(payload, dict)
            or set(payload) != {
                "episodes",
                "manifest_receipt_sha256",
                "max_episodes",
                "max_state_bytes",
                "schema",
            }
            or payload.get("schema") != STATE_SCHEMA
            or payload.get("manifest_receipt_sha256")
            != manifest.authority_receipt_sha256
        ):
            raise ValueError("whole-organism cold payload changed")
        owner = cls(
            authority_key=authority_key,
            manifest=manifest,
            max_episodes=payload.get("max_episodes"),
            max_state_bytes=payload.get("max_state_bytes"),
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if envelope.get("authority_hmac_sha256") != expected_hmac:
            raise ValueError("whole-organism cold state authority changed")
        raw_episodes = payload.get("episodes")
        if not isinstance(raw_episodes, list):
            raise ValueError("whole-organism cold episode collection changed")
        for raw in raw_episodes:
            record = owner._episode_from_record(raw)
            if record.authority_receipt_sha256 in owner._episodes:
                raise ValueError("whole-organism cold state repeats episode")
            owner._episodes[record.authority_receipt_sha256] = record
            owner._verify_episode_record(record)
        if owner.snapshot_encoded() != encoded:
            raise ValueError("whole-organism cold round-trip changed state")
        return owner

    def _contribution_from_record(
        self,
        raw: object,
    ) -> WholeOrganismMechanismContribution:
        if not isinstance(raw, dict) or set(raw) != {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "episode_id",
            "mechanism_id",
            "parent_contribution_receipts",
            "schema",
            "semantic_evidence_json",
            "semantic_evidence_receipt_sha256",
            "source_time_end",
            "source_time_start",
            "state",
        } or raw.get("schema") != CONTRIBUTION_SCHEMA:
            raise ValueError("cold contribution record changed")
        parents = raw.get("parent_contribution_receipts")
        if (
            not isinstance(parents, list)
            or any(not isinstance(value, list) or len(value) != 2 for value in parents)
        ):
            raise ValueError("cold contribution parents changed")
        return WholeOrganismMechanismContribution(
            episode_id=raw["episode_id"],
            mechanism_id=raw["mechanism_id"],
            state=ContributionState(raw["state"]),
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold contribution source start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold contribution source end",
            ),
            parent_contribution_receipts=tuple(
                (value[0], value[1]) for value in parents
            ),
            semantic_evidence_json=raw["semantic_evidence_json"],
            semantic_evidence_receipt_sha256=(
                raw["semantic_evidence_receipt_sha256"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    def _episode_from_record(
        self,
        raw: object,
    ) -> WholeOrganismEpisodeRecord:
        expected = {
            "action_authority_receipt_sha256",
            "action_execution_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "chain_id",
            "contributions",
            "episode_id",
            "full_field_roots",
            "l6_authority_receipt_sha256",
            "l6_disposition",
            "manifest_receipt_sha256",
            "native_evidence_transition",
            "phase",
            "prior_episode_receipt_sha256",
            "schema",
            "settlement_authority_receipt_sha256",
            "settlement_event_id",
            "settlement_structural_fingerprint",
            "source_time_end",
            "source_time_start",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != EPISODE_SCHEMA
            or not isinstance(raw.get("full_field_roots"), list)
            or not isinstance(raw.get("contributions"), list)
        ):
            raise ValueError("cold whole-organism episode record changed")
        return WholeOrganismEpisodeRecord(
            episode_id=raw["episode_id"],
            chain_id=raw["chain_id"],
            phase=WholeOrganismEpisodePhase(raw["phase"]),
            manifest_receipt_sha256=raw["manifest_receipt_sha256"],
            settlement_event_id=raw["settlement_event_id"],
            settlement_authority_receipt_sha256=(
                raw["settlement_authority_receipt_sha256"]
            ),
            settlement_structural_fingerprint=(
                raw["settlement_structural_fingerprint"]
            ),
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold episode source start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold episode source end",
            ),
            full_field_roots=tuple(
                _root_from_record(value)
                for value in raw["full_field_roots"]
            ),
            native_evidence_transition=(
                NativeEvidenceTransitionIndex.from_record(
                    raw["native_evidence_transition"]
                )
            ),
            contributions=tuple(
                self._contribution_from_record(value)
                for value in raw["contributions"]
            ),
            action_authority_receipt_sha256=(
                raw["action_authority_receipt_sha256"]
            ),
            prior_episode_receipt_sha256=(
                raw["prior_episode_receipt_sha256"]
            ),
            action_execution_receipt_sha256=(
                raw["action_execution_receipt_sha256"]
            ),
            l6_disposition=L6Disposition(raw["l6_disposition"]),
            l6_authority_receipt_sha256=(
                raw["l6_authority_receipt_sha256"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )


__all__ = (
    "ContributionState",
    "DownstreamAuthority",
    "L6Disposition",
    "MechanismAvailability",
    "MechanismKind",
    "MountedMechanismManifest",
    "MountedMechanismSpec",
    "PreparedMechanismContribution",
    "WholeOrganismEpisodeAuthority",
    "WholeOrganismEpisodeCapability",
    "WholeOrganismEpisodeDraft",
    "WholeOrganismEpisodePhase",
    "WholeOrganismEpisodeRecord",
    "WholeOrganismEpisodeResolution",
    "WholeOrganismMechanismCapability",
    "WholeOrganismMechanismContribution",
    "create_mounted_mechanism_manifest",
)
