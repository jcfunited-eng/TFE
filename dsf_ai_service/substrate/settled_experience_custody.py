"""Single-settlement custody for one already-observed W1 occurrence.

This boundary never transduces, builds, mounts, or settles sensory evidence.
It accepts one already-verified W1 physical evidence mount and exactly one
authenticated world occurrence: either the applied execution named by an
action mount or the passive observation named by a current-observation mount.
It then preserves the typed objects under one immutable parent identity and
issues bounded child capabilities that can only name that parent.

Persistence is deliberately rehydrating rather than reconstructive.  Restoring
custody requires the same already-verified typed W1 mount and world occurrence.
A serialized receipt is not allowed to manufacture physical authority after
the live objects have been lost.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.substrate.embodiment_world import (
    EXECUTION_DOMAIN,
    OBSERVATION_DOMAIN,
    ActionExecutionReceipt,
    ObservationSnapshot,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryBinauralMotifFiring,
    AuditoryBinauralMotifObservation,
)
from dsf_ai_service.substrate.anonymous_passive_window import (
    AnonymousPassiveWindowMount,
    AnonymousPassiveWindowReceipt,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1BinauralPCM,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
    W1PhysicalEvidenceReceipt,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticMount,
    W1SelfAcousticReceipt,
)


SETTLED_EXPERIENCE_CUSTODY_PROFILE_SCHEMA = (
    "guala.settled_experience_custody.profile.v1"
)
SETTLED_EXPERIENCE_OCCURRENCE_SCHEMA = (
    "guala.settled_experience_custody.occurrence.v2"
)
SETTLED_EXPERIENCE_CUSTODY_SCHEMA = (
    "guala.settled_experience_custody.v2"
)
SETTLED_EXPERIENCE_CHILD_SCHEMA = (
    "guala.settled_experience_custody.child.v1"
)
SETTLED_EXPERIENCE_STATE_SCHEMA = (
    "guala.settled_experience_custody.state.v2"
)
SETTLED_EXPERIENCE_ENVELOPE_SCHEMA = (
    "guala.settled_experience_custody.state_hmac.v1"
)
SETTLED_EXPERIENCE_BINAURAL_PRESSURE_CONSUMER_ID = (
    "self-vocal-motor-pressure"
)

_CUSTODY_DOMAIN = b"guala-settled-experience-custody-v1\0"
_CHILD_DOMAIN = b"guala-settled-experience-custody-child-v1\0"
_STATE_DOMAIN = b"guala-settled-experience-custody-state-v1\0"
_CONSTRUCTION_AUTHORITY = object()

# These are serialization safety ceilings, not learning or recognition
# thresholds.  The configured profile remains the actual resource authority.
MAX_CONSUMER_ID_BYTES = 256
MAX_PROFILE_ID_BYTES = 256
MAX_CONFIGURED_CHILDREN = 4_096
MAX_CONFIGURED_SNAPSHOT_BYTES = 256 * 1024 * 1024


class SettledExperienceSourceKind(str, Enum):
    PHYSICAL_EVIDENCE = "w1_physical_evidence"
    SELF_ACOUSTIC = "w1_self_acoustic"
    ANONYMOUS_PASSIVE_WINDOW = "anonymous_passive_window"


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


def _key(
    value: bytes | str,
    name: str,
    *,
    minimum_bytes: int = 32,
) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError(f"{name} must be bytes or text")
    if not minimum_bytes <= len(result) <= 4_096:
        raise ValueError(f"{name} is outside its exact key boundary")
    return result


def _identifier(value: object, name: str, *, max_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > max_bytes
    ):
        raise ValueError(f"{name} is outside its exact identifier boundary")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _capacity(
    value: object,
    name: str,
    *,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= maximum
    ):
        raise ValueError(f"{name} is outside its explicit capacity")
    return value


def _sign(key: bytes, domain: bytes, payload: Mapping[str, object]) -> str:
    return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()


def _verify_observation(
    observation: ObservationSnapshot,
    *,
    world_authority_key: bytes,
) -> None:
    if not isinstance(observation, ObservationSnapshot):
        raise TypeError("custody world observation is not typed")
    unsigned = observation.unsigned_record()
    state = dict(unsigned)
    if state.pop("schema", None) is None:
        raise ValueError("custody world observation lost its schema")
    state_sha256 = state.pop("state_sha256", None)
    if _digest(state) != state_sha256:
        raise ValueError("custody world observation state changed")
    expected_hmac = _sign(
        world_authority_key,
        OBSERVATION_DOMAIN,
        unsigned,
    )
    if (
        not hmac.compare_digest(
            expected_hmac,
            observation.authority_hmac_sha256,
        )
        or observation.authority_receipt_sha256
        != _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": unsigned,
        })
    ):
        raise ValueError("custody world observation authority changed")


def _verify_execution(
    execution: ActionExecutionReceipt,
    *,
    world_authority_key: bytes,
) -> None:
    if not isinstance(execution, ActionExecutionReceipt):
        raise TypeError("custody world execution is not typed")
    _verify_observation(
        execution.before,
        world_authority_key=world_authority_key,
    )
    _verify_observation(
        execution.after,
        world_authority_key=world_authority_key,
    )
    if (
        execution.disposition != "applied"
        or execution.reason != "applied"
        or execution.expected_revision != execution.before.revision
        or execution.observed_revision != execution.before.revision
        or execution.after.revision != execution.before.revision + 1
        or not execution.lifecycle
        or execution.lifecycle[-1] != "applied"
    ):
        raise ValueError("custody requires one applied world execution")
    unsigned = execution.unsigned_record()
    expected_hmac = _sign(
        world_authority_key,
        EXECUTION_DOMAIN,
        unsigned,
    )
    if (
        not hmac.compare_digest(
            expected_hmac,
            execution.authority_hmac_sha256,
        )
        or execution.authority_receipt_sha256
        != _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": unsigned,
        })
    ):
        raise ValueError("custody world execution authority changed")


def _settlement_payload(
    settlement: CausalExperienceSettlement,
) -> bytes:
    settlement.verify()
    payload = settlement.receipt_registry.resolve(
        settlement.authority_receipt_sha256,
        "settled experience causal settlement",
    )
    if receipt_sha256(payload) != settlement.authority_receipt_sha256:
        raise ValueError("custody causal settlement payload changed")
    return payload


@dataclass(frozen=True, slots=True)
class SettledExperienceCustodyProfile:
    profile_id: str
    max_children: int
    max_snapshot_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_children: int,
        max_snapshot_bytes: int,
    ) -> "SettledExperienceCustodyProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id,
                "settled experience custody profile",
                max_bytes=MAX_PROFILE_ID_BYTES,
            ),
            max_children=_capacity(
                max_children,
                "settled experience child capacity",
                maximum=MAX_CONFIGURED_CHILDREN,
            ),
            max_snapshot_bytes=_capacity(
                max_snapshot_bytes,
                "settled experience snapshot byte capacity",
                maximum=MAX_CONFIGURED_SNAPSHOT_BYTES,
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_children=provisional.max_children,
            max_snapshot_bytes=provisional.max_snapshot_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_children": self.max_children,
            "max_snapshot_bytes": self.max_snapshot_bytes,
            "profile_id": self.profile_id,
            "schema": SETTLED_EXPERIENCE_CUSTODY_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _identifier(
            self.profile_id,
            "settled experience custody profile",
            max_bytes=MAX_PROFILE_ID_BYTES,
        )
        _capacity(
            self.max_children,
            "settled experience child capacity",
            maximum=MAX_CONFIGURED_CHILDREN,
        )
        _capacity(
            self.max_snapshot_bytes,
            "settled experience snapshot byte capacity",
            maximum=MAX_CONFIGURED_SNAPSHOT_BYTES,
        )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("settled experience custody profile changed")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "SettledExperienceCustodyProfile":
        expected = {
            "authority_receipt_sha256",
            "max_children",
            "max_snapshot_bytes",
            "profile_id",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != SETTLED_EXPERIENCE_CUSTODY_PROFILE_SCHEMA
        ):
            raise ValueError("settled experience custody profile record changed")
        result = cls(
            profile_id=value.get("profile_id"),
            max_children=value.get("max_children"),
            max_snapshot_bytes=value.get("max_snapshot_bytes"),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        result.verify()
        if result.as_record() != dict(value):
            raise ValueError(
                "settled experience custody profile is not canonical"
            )
        return result


@dataclass(frozen=True, slots=True)
class SettledExperienceOccurrenceCounter:
    source_occurrence_id: str
    source_kind: SettledExperienceSourceKind
    authenticated_source_receipt_sha256: str
    world_execution_receipt_sha256: str | None
    world_observation_receipt_sha256: str
    physical_evidence_receipt_sha256: str | None
    self_acoustic_receipt_sha256: str | None
    full_field_assembly_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str | None
    binaural_receptor_receipt_sha256: str | None
    source_transduction_lineage_count: int
    full_field_build_lineage_count: int
    causal_settlement_lineage_count: int
    custody_count: int
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "authenticated_source_receipt_sha256": (
                self.authenticated_source_receipt_sha256
            ),
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "binaural_receptor_receipt_sha256": (
                self.binaural_receptor_receipt_sha256
            ),
            "causal_settlement_lineage_count": (
                self.causal_settlement_lineage_count
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "custody_count": self.custody_count,
            "full_field_assembly_receipt_sha256": (
                self.full_field_assembly_receipt_sha256
            ),
            "full_field_build_lineage_count": (
                self.full_field_build_lineage_count
            ),
            "physical_evidence_receipt_sha256": (
                self.physical_evidence_receipt_sha256
            ),
            "self_acoustic_receipt_sha256": (
                self.self_acoustic_receipt_sha256
            ),
            "source_kind": self.source_kind.value,
            "source_transduction_lineage_count": (
                self.source_transduction_lineage_count
            ),
            "schema": SETTLED_EXPERIENCE_OCCURRENCE_SCHEMA,
            "source_occurrence_id": self.source_occurrence_id,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def verify(self) -> None:
        for value, name in (
            (self.source_occurrence_id, "source occurrence"),
            (
                self.authenticated_source_receipt_sha256,
                "authenticated source",
            ),
            (
                self.world_observation_receipt_sha256,
                "world observation",
            ),
            (
                self.full_field_assembly_receipt_sha256,
                "full-field assembly",
            ),
            (
                self.causal_settlement_receipt_sha256,
                "causal settlement",
            ),
            (self.authority_receipt_sha256, "occurrence counter"),
        ):
            _sha256(value, f"settled experience {name}")
        if not isinstance(self.source_kind, SettledExperienceSourceKind):
            raise ValueError("settled experience source kind is not typed")
        expected_physical = (
            self.source_kind is SettledExperienceSourceKind.PHYSICAL_EVIDENCE
        )
        expected_self_acoustic = (
            self.source_kind is SettledExperienceSourceKind.SELF_ACOUSTIC
        )
        if (
            bool(self.physical_evidence_receipt_sha256)
            != expected_physical
            or bool(self.self_acoustic_receipt_sha256)
            != expected_self_acoustic
        ):
            raise ValueError(
                "settled experience occurrence split source authority"
            )
        for value, name in (
            (self.physical_evidence_receipt_sha256, "physical evidence"),
            (self.self_acoustic_receipt_sha256, "self acoustic"),
        ):
            if value is not None:
                _sha256(value, f"settled experience {name}")
        expected_source = (
            self.physical_evidence_receipt_sha256
            if expected_physical
            else self.self_acoustic_receipt_sha256
            if expected_self_acoustic
            else self.authenticated_source_receipt_sha256
        )
        if self.authenticated_source_receipt_sha256 != expected_source:
            raise ValueError(
                "settled experience authenticated source changed"
            )
        if self.world_execution_receipt_sha256 is not None:
            _sha256(
                self.world_execution_receipt_sha256,
                "settled experience world execution",
            )
        for value, name in (
            (self.binaural_l5_receipt_sha256, "binaural L5"),
            (
                self.binaural_receptor_receipt_sha256,
                "binaural receptor",
            ),
        ):
            if value is not None:
                _sha256(value, f"settled experience {name}")
        if bool(self.binaural_l5_receipt_sha256) != bool(
            self.binaural_receptor_receipt_sha256
        ):
            raise ValueError(
                "settled experience occurrence split auditory lineage"
            )
        if (
            self.source_transduction_lineage_count != 1
            or self.full_field_build_lineage_count != 1
            or self.causal_settlement_lineage_count != 1
            or self.custody_count != 1
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError(
                "settled experience occurrence has duplicate authority"
            )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class SettledExperienceCustody:
    profile: SettledExperienceCustodyProfile
    source_occurrence_id: str
    source_kind: SettledExperienceSourceKind
    world_execution: ActionExecutionReceipt | None
    world_observation: ObservationSnapshot
    physical_evidence_receipt: W1PhysicalEvidenceReceipt | None
    anonymous_passive_window_receipt: (
        AnonymousPassiveWindowReceipt | None
    )
    self_acoustic_receipt: W1SelfAcousticReceipt | None
    self_acoustic_prelearning_firing: (
        AuditoryBinauralMotifFiring | None
    )
    self_acoustic_observation: AuditoryBinauralMotifObservation | None
    causal_settlement: CausalExperienceSettlement
    binaural_auditory_l5: W1BinauralAuditoryL5Experience | None
    binaural_receptor_settlement: W1BinauralReceptorSettlement | None
    occurrence_counter: SettledExperienceOccurrenceCounter
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _construction_authority: object

    def payload(self) -> dict[str, object]:
        return {
            "authenticated_source_receipt_sha256": (
                self.physical_evidence_receipt.authority_receipt_sha256
                if self.physical_evidence_receipt is not None
                else self.self_acoustic_receipt.authority_receipt_sha256
                if self.self_acoustic_receipt is not None
                else self.anonymous_passive_window_receipt
                .authority_receipt_sha256
            ),
            "anonymous_passive_window_receipt_sha256": (
                self.anonymous_passive_window_receipt
                .authority_receipt_sha256
                if self.anonymous_passive_window_receipt is not None
                else None
            ),
            "binaural_l5_receipt_sha256": (
                self.binaural_auditory_l5.authority_receipt_sha256
                if self.binaural_auditory_l5 is not None else None
            ),
            "binaural_receptor_receipt_sha256": (
                self.binaural_receptor_settlement
                .authority_receipt_sha256
                if self.binaural_receptor_settlement is not None else None
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement.authority_receipt_sha256
            ),
            "occurrence_counter_receipt_sha256": (
                self.occurrence_counter.authority_receipt_sha256
            ),
            "physical_evidence_receipt_sha256": (
                self.physical_evidence_receipt.authority_receipt_sha256
                if self.physical_evidence_receipt is not None else None
            ),
            "profile_receipt_sha256": (
                self.profile.authority_receipt_sha256
            ),
            "schema": SETTLED_EXPERIENCE_CUSTODY_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self.self_acoustic_receipt.authority_receipt_sha256
                if self.self_acoustic_receipt is not None else None
            ),
            "self_acoustic_prelearning_firing_receipt_sha256": (
                self.self_acoustic_prelearning_firing
                .authority_receipt_sha256
                if self.self_acoustic_prelearning_firing is not None
                else None
            ),
            "self_acoustic_observation_receipt_sha256": (
                self.self_acoustic_observation.authority_receipt_sha256
                if self.self_acoustic_observation is not None else None
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "source_kind": self.source_kind.value,
            "world_execution_receipt_sha256": (
                self.world_execution.authority_receipt_sha256
                if self.world_execution is not None else None
            ),
            "world_observation_receipt_sha256": (
                self.world_observation.authority_receipt_sha256
            ),
        }

    def verify(
        self,
        *,
        authority_key: bytes | str,
        w1_physical_authority_key: bytes | str,
        world_authority_key: bytes | str,
        w1_self_acoustic_authority_key: bytes | str | None = None,
        anonymous_passive_window_authority_key: (
            bytes | str | None
        ) = None,
    ) -> None:
        custody_key = _key(
            authority_key,
            "settled experience custody authority key",
        )
        physical_key = _key(
            w1_physical_authority_key,
            "settled experience W1 physical authority key",
        )
        world_key = _key(
            world_authority_key,
            "settled experience world authority key",
            minimum_bytes=1,
        )
        if self._construction_authority is not _CONSTRUCTION_AUTHORITY:
            raise ValueError(
                "settled experience custody lacks construction authority"
            )
        self.profile.verify()
        _verify_observation(
            self.world_observation,
            world_authority_key=world_key,
        )
        if self.world_execution is not None:
            _verify_execution(
                self.world_execution,
                world_authority_key=world_key,
            )
        if not isinstance(self.source_kind, SettledExperienceSourceKind):
            raise ValueError("settled experience source kind is not typed")
        if (
            self.source_kind
            is SettledExperienceSourceKind.PHYSICAL_EVIDENCE
        ):
            if (
                self.physical_evidence_receipt is None
                or self.anonymous_passive_window_receipt is not None
                or self.self_acoustic_receipt is not None
                or self.self_acoustic_prelearning_firing is not None
                or self.self_acoustic_observation is not None
            ):
                raise ValueError(
                    "settled experience physical source variant changed"
                )
            self.physical_evidence_receipt.verify(physical_key)
        elif self.source_kind is SettledExperienceSourceKind.SELF_ACOUSTIC:
            if (
                self.self_acoustic_receipt is None
                or self.physical_evidence_receipt is not None
                or self.anonymous_passive_window_receipt is not None
                or self.self_acoustic_prelearning_firing is None
                or self.self_acoustic_observation is None
                or w1_self_acoustic_authority_key is None
            ):
                raise ValueError(
                    "settled experience self-acoustic source variant changed"
                )
            self.self_acoustic_receipt.verify(
                w1_self_acoustic_authority_key
            )
            self.self_acoustic_prelearning_firing.verify()
            self.self_acoustic_observation.verify()
            if (
                self.self_acoustic_receipt
                .prelearning_firing_receipt_sha256
                != self.self_acoustic_prelearning_firing
                .authority_receipt_sha256
                or self.self_acoustic_receipt
                .observation_receipt_sha256
                != self.self_acoustic_observation
                .authority_receipt_sha256
            ):
                raise ValueError(
                    "settled experience self-acoustic recurrent custody "
                    "changed"
                )
        else:
            if (
                self.source_kind
                is not SettledExperienceSourceKind.ANONYMOUS_PASSIVE_WINDOW
                or self.anonymous_passive_window_receipt is None
                or self.physical_evidence_receipt is not None
                or self.self_acoustic_receipt is not None
                or self.self_acoustic_prelearning_firing is not None
                or self.self_acoustic_observation is not None
                or anonymous_passive_window_authority_key is None
                or self.world_execution is not None
                or self.binaural_auditory_l5 is not None
                or self.binaural_receptor_settlement is not None
            ):
                raise ValueError(
                    "settled experience anonymous passive-window "
                    "variant changed"
                )
            self.anonymous_passive_window_receipt.verify(
                anonymous_passive_window_authority_key
            )
            if (
                self.anonymous_passive_window_receipt
                .settlement_receipt_sha256
                != self.causal_settlement.authority_receipt_sha256
                or self.anonymous_passive_window_receipt
                .world_observation_receipt_sha256
                != self.world_observation.authority_receipt_sha256
            ):
                raise ValueError(
                    "settled experience anonymous passive-window "
                    "linkage changed"
                )
        self.causal_settlement.verify()
        if self.binaural_auditory_l5 is not None:
            self.binaural_auditory_l5.verify()
        if self.binaural_receptor_settlement is not None:
            self.binaural_receptor_settlement.verify()
        self.occurrence_counter.verify()
        if (
            self.source_kind
            is SettledExperienceSourceKind.ANONYMOUS_PASSIVE_WINDOW
        ):
            if (
                self.occurrence_counter
                .authenticated_source_receipt_sha256
                != self.anonymous_passive_window_receipt
                .authority_receipt_sha256
                or self.occurrence_counter
                .world_execution_receipt_sha256
                is not None
                or self.occurrence_counter
                .world_observation_receipt_sha256
                != self.world_observation.authority_receipt_sha256
            ):
                raise ValueError(
                    "settled anonymous passive-window occurrence "
                    "changed"
                )
            _verify_full_field(self.causal_settlement)
        else:
            _verify_linkage(
                source_occurrence_id=self.source_occurrence_id,
                execution=self.world_execution,
                observation=self.world_observation,
                evidence=self.physical_evidence_receipt,
                self_acoustic=self.self_acoustic_receipt,
                settlement=self.causal_settlement,
                auditory_l5=self.binaural_auditory_l5,
                receptors=self.binaural_receptor_settlement,
                counter=self.occurrence_counter,
            )
        expected_hmac = _sign(
            custody_key,
            _CUSTODY_DOMAIN,
            self.payload(),
        )
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": self.payload(),
            })
        ):
            raise ValueError("settled experience custody authority changed")


@dataclass(frozen=True, slots=True)
class SettledExperienceConsumerCapability:
    consumer_id: str
    ordinal: int
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "consumer_id": self.consumer_id,
            "ordinal": self.ordinal,
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "schema": SETTLED_EXPERIENCE_CHILD_SCHEMA,
            "source_occurrence_id": self.source_occurrence_id,
        }

    def verify(
        self,
        custody: SettledExperienceCustody,
        *,
        authority_key: bytes | str,
    ) -> None:
        key = _key(
            authority_key,
            "settled experience custody authority key",
        )
        _identifier(
            self.consumer_id,
            "settled experience consumer",
            max_bytes=MAX_CONSUMER_ID_BYTES,
        )
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or not 0 <= self.ordinal < custody.profile.max_children
            or self.source_occurrence_id
            != custody.source_occurrence_id
            or self.parent_custody_receipt_sha256
            != custody.authority_receipt_sha256
        ):
            raise ValueError(
                "settled experience child names another parent"
            )
        expected_hmac = _sign(key, _CHILD_DOMAIN, self.payload())
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": self.payload(),
            })
        ):
            raise ValueError(
                "settled experience child authority changed"
            )

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class SettledExperienceConsumerView:
    """Read-only downstream surface with no remount/re-settlement authority."""

    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    source_kind: SettledExperienceSourceKind
    world_execution: ActionExecutionReceipt | None
    world_observation: ObservationSnapshot
    physical_evidence_receipt: W1PhysicalEvidenceReceipt | None
    anonymous_passive_window_receipt: (
        AnonymousPassiveWindowReceipt | None
    )
    self_acoustic_receipt: W1SelfAcousticReceipt | None
    self_acoustic_prelearning_firing: (
        AuditoryBinauralMotifFiring | None
    )
    self_acoustic_observation: AuditoryBinauralMotifObservation | None
    causal_settlement: CausalExperienceSettlement
    binaural_auditory_l5: W1BinauralAuditoryL5Experience | None
    binaural_receptor_settlement: W1BinauralReceptorSettlement | None
    occurrence_counter: SettledExperienceOccurrenceCounter


@dataclass(frozen=True, slots=True)
class SettledExperienceBinauralPressureView:
    """Capability-scoped transient pressure owned by one settled custody."""

    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    capability_receipt_sha256: str
    binaural_pcm: W1BinauralPCM


def _source_occurrence_id(
    *,
    execution: ActionExecutionReceipt | None,
    observation: ObservationSnapshot,
    evidence: W1PhysicalEvidenceReceipt | None,
    self_acoustic: W1SelfAcousticReceipt | None,
    settlement: CausalExperienceSettlement,
    auditory_l5: W1BinauralAuditoryL5Experience | None,
    receptors: W1BinauralReceptorSettlement | None,
) -> str:
    source_kind = (
        SettledExperienceSourceKind.PHYSICAL_EVIDENCE
        if evidence is not None
        else SettledExperienceSourceKind.SELF_ACOUSTIC
    )
    return _digest({
        "authenticated_source_receipt_sha256": (
            evidence.authority_receipt_sha256
            if evidence is not None
            else self_acoustic.authority_receipt_sha256
        ),
        "binaural_l5_receipt_sha256": (
            auditory_l5.authority_receipt_sha256
            if auditory_l5 is not None else None
        ),
        "binaural_receptor_receipt_sha256": (
            receptors.authority_receipt_sha256
            if receptors is not None else None
        ),
        "causal_settlement_receipt_sha256": (
            settlement.authority_receipt_sha256
        ),
        "physical_evidence_receipt_sha256": (
            evidence.authority_receipt_sha256
            if evidence is not None else None
        ),
        "schema": SETTLED_EXPERIENCE_OCCURRENCE_SCHEMA,
        "self_acoustic_receipt_sha256": (
            self_acoustic.authority_receipt_sha256
            if self_acoustic is not None else None
        ),
        "source_kind": source_kind.value,
        "world_execution_receipt_sha256": (
            execution.authority_receipt_sha256
            if execution is not None else None
        ),
        "world_observation_receipt_sha256": (
            observation.authority_receipt_sha256
        ),
    })


def _verify_full_field(settlement: CausalExperienceSettlement) -> None:
    observed = False
    for sense in settlement.interpretations:
        for substream in sense.substreams:
            for field_tuple in substream.field_tuples:
                observed = True
                if tuple(
                    name for name, _value in field_tuple.fields
                ) != DSF_FIELD_ORDER:
                    raise ValueError(
                        "settled experience custody lost full DSF field order"
                    )
    if not observed:
        raise ValueError(
            "settled experience custody has no observed full-field tuples"
        )


def _verify_linkage(
    *,
    source_occurrence_id: str,
    execution: ActionExecutionReceipt | None,
    observation: ObservationSnapshot,
    evidence: W1PhysicalEvidenceReceipt | None,
    self_acoustic: W1SelfAcousticReceipt | None,
    settlement: CausalExperienceSettlement,
    auditory_l5: W1BinauralAuditoryL5Experience | None,
    receptors: W1BinauralReceptorSettlement | None,
    counter: SettledExperienceOccurrenceCounter,
) -> None:
    if evidence is None and (
        self_acoustic is None
        or execution is None
        or auditory_l5 is None
        or receptors is None
    ):
        raise ValueError(
            "settled self-acoustic experience is incomplete"
        )
    expected_occurrence = _source_occurrence_id(
        execution=execution,
        observation=observation,
        evidence=evidence,
        self_acoustic=self_acoustic,
        settlement=settlement,
        auditory_l5=auditory_l5,
        receptors=receptors,
    )
    physical_source = evidence is not None
    acoustic = (
        bool(evidence.acoustic_emission_receipt_sha256s)
        if evidence is not None else True
    )
    if (
        source_occurrence_id != expected_occurrence
        or counter.source_occurrence_id != source_occurrence_id
        or counter.world_observation_receipt_sha256
        != observation.authority_receipt_sha256
        or counter.full_field_assembly_receipt_sha256
        != settlement.assembly_receipt_sha256
        or counter.causal_settlement_receipt_sha256
        != settlement.authority_receipt_sha256
    ):
        raise ValueError(
            "settled experience custody crossed occurrence authority"
        )
    if physical_source:
        if (
            self_acoustic is not None
            or evidence.state is not W1EvidenceState.OBSERVED
            or evidence.causal_settlement_receipt_sha256
            != settlement.authority_receipt_sha256
            or counter.source_kind
            is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            or counter.physical_evidence_receipt_sha256
            != evidence.authority_receipt_sha256
            or counter.self_acoustic_receipt_sha256 is not None
        ):
            raise ValueError(
                "settled physical experience crossed source authority"
            )
    elif (
        self_acoustic is None
        or self_acoustic.world_execution_receipt_sha256
        != execution.authority_receipt_sha256
        or self_acoustic.world_before_receipt_sha256
        != execution.before.authority_receipt_sha256
        or self_acoustic.world_after_receipt_sha256
        != execution.after.authority_receipt_sha256
        or self_acoustic.causal_settlement_receipt_sha256
        != settlement.authority_receipt_sha256
        or self_acoustic.binaural_l5_receipt_sha256
        != auditory_l5.authority_receipt_sha256
        or self_acoustic.receptor_settlement_receipt_sha256
        != receptors.authority_receipt_sha256
        or counter.source_kind
        is not SettledExperienceSourceKind.SELF_ACOUSTIC
        or counter.self_acoustic_receipt_sha256
        != self_acoustic.authority_receipt_sha256
        or counter.physical_evidence_receipt_sha256 is not None
    ):
        raise ValueError(
            "settled self-acoustic experience crossed source authority"
        )
    if execution is not None:
        if (
            observation is not execution.after
            or counter.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
        ):
            raise ValueError(
                "settled applied experience crossed execution authority"
            )
        if physical_source and (
            evidence.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or evidence.world_observation_before_receipt_sha256
            != execution.before.authority_receipt_sha256
            or evidence.world_observation_after_receipt_sha256
            != execution.after.authority_receipt_sha256
        ):
            raise ValueError(
                "settled applied physical experience crossed execution "
                "authority"
            )
    elif (
        not physical_source
        or evidence.world_execution_receipt_sha256 is not None
        or evidence.world_observation_before_receipt_sha256
        != observation.authority_receipt_sha256
        or evidence.world_observation_after_receipt_sha256
        != observation.authority_receipt_sha256
        or counter.world_execution_receipt_sha256 is not None
    ):
        raise ValueError(
            "settled passive experience fabricated execution authority"
        )
    if acoustic:
        if (
            auditory_l5 is None
            or receptors is None
            or auditory_l5.assembly_id != settlement.assembly_id
            or auditory_l5.source_time_start != settlement.source_time_start
            or auditory_l5.source_time_end != settlement.source_time_end
            or auditory_l5.upstream_causal_settlement_receipt_sha256
            != settlement.authority_receipt_sha256
            or receptors.upstream_w1_l5 is not auditory_l5
            or receptors.upstream_causal_settlement_receipt_sha256
            != settlement.authority_receipt_sha256
            or counter.binaural_l5_receipt_sha256
            != auditory_l5.authority_receipt_sha256
            or counter.binaural_receptor_receipt_sha256
            != receptors.authority_receipt_sha256
        ):
            raise ValueError(
                "settled acoustic experience lost auditory custody"
            )
        if (
            physical_source
            and evidence.binaural_auditory_l5_authority_receipt_sha256
            != auditory_l5.authority_receipt_sha256
        ):
            raise ValueError(
                "settled physical acoustic experience lost L5 custody"
            )
    elif (
        auditory_l5 is not None
        or receptors is not None
        or not physical_source
        or evidence.binaural_auditory_l5_authority_receipt_sha256 is not None
        or counter.binaural_l5_receipt_sha256 is not None
        or counter.binaural_receptor_receipt_sha256 is not None
    ):
        raise ValueError(
            "settled non-acoustic experience retained auditory custody"
        )
    _verify_full_field(settlement)


class SettledExperienceCustodyAuthority:
    """Capacity-one owner for one immutable settled occurrence custody."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        w1_physical_authority_key: bytes | str,
        world_authority_key: bytes | str,
        profile: SettledExperienceCustodyProfile,
        w1_self_acoustic_authority_key: bytes | str | None = None,
        anonymous_passive_window_authority_key: (
            bytes | str | None
        ) = None,
    ) -> None:
        self._key = _key(
            authority_key,
            "settled experience custody authority key",
        )
        self._w1_key = _key(
            w1_physical_authority_key,
            "settled experience W1 physical authority key",
        )
        self._world_key = _key(
            world_authority_key,
            "settled experience world authority key",
            minimum_bytes=1,
        )
        self._self_acoustic_key = (
            _key(
                w1_self_acoustic_authority_key,
                "settled experience W1 self-acoustic authority key",
            )
            if w1_self_acoustic_authority_key is not None else None
        )
        self._passive_window_key = (
            _key(
                anonymous_passive_window_authority_key,
                "settled experience anonymous passive-window "
                "authority key",
            )
            if anonymous_passive_window_authority_key is not None
            else None
        )
        if not isinstance(profile, SettledExperienceCustodyProfile):
            raise TypeError("settled experience custody profile is not typed")
        profile.verify()
        self._profile = profile
        self._custody: SettledExperienceCustody | None = None
        self._binaural_pcm: W1BinauralPCM | None = None
        self._settlement_payload_bytes: bytes | None = None
        self._children: tuple[
            SettledExperienceConsumerCapability, ...
        ] = ()
        self._lock = threading.RLock()

    @property
    def custody(self) -> SettledExperienceCustody | None:
        with self._lock:
            return self._custody

    @property
    def children(
        self,
    ) -> tuple[SettledExperienceConsumerCapability, ...]:
        with self._lock:
            return self._children

    def admit(
        self,
        source_mount: (
            W1PhysicalEvidenceMount
            | W1SelfAcousticMount
            | AnonymousPassiveWindowMount
        ),
        world_execution: ActionExecutionReceipt | None = None,
        *,
        world_observation: ObservationSnapshot | None = None,
    ) -> SettledExperienceCustody:
        """Take custody without calling any physical or causal producer."""

        if not isinstance(
            source_mount,
            (
                W1PhysicalEvidenceMount,
                W1SelfAcousticMount,
                AnonymousPassiveWindowMount,
            ),
        ):
            raise TypeError(
                "settled experience custody requires one typed W1 source "
                "variant"
            )
        self_acoustic_source = isinstance(
            source_mount, W1SelfAcousticMount
        )
        passive_window_source = isinstance(
            source_mount, AnonymousPassiveWindowMount
        )
        if passive_window_source and (
            world_execution is not None
            or world_observation is not None
            or self._passive_window_key is None
        ):
            raise ValueError(
                "anonymous passive-window custody uses only its mounted "
                "observation and explicit authority"
            )
        if self_acoustic_source and (
            world_execution is None
            or world_observation is not None
            or self._self_acoustic_key is None
        ):
            raise ValueError(
                "self-acoustic custody requires its applied execution and "
                "explicit source authority"
            )
        if (
            not passive_window_source
            and (world_execution is None) == (world_observation is None)
        ):
            raise ValueError(
                "settled experience custody requires exactly one world "
                "occurrence variant"
            )
        if passive_window_source:
            source_mount.receipt.verify(self._passive_window_key)
            observation = source_mount.world_observation
            _verify_observation(
                observation,
                world_authority_key=self._world_key,
            )
        elif world_execution is not None:
            if not isinstance(world_execution, ActionExecutionReceipt):
                raise TypeError(
                    "settled experience custody world execution is not typed"
                )
            _verify_execution(
                world_execution,
                world_authority_key=self._world_key,
            )
            observation = world_execution.after
        else:
            if not isinstance(world_observation, ObservationSnapshot):
                raise TypeError(
                    "settled experience custody world observation is not typed"
                )
            _verify_observation(
                world_observation,
                world_authority_key=self._world_key,
            )
            observation = world_observation
        if self_acoustic_source:
            source_mount.verify(self._self_acoustic_key)
            source_kind = SettledExperienceSourceKind.SELF_ACOUSTIC
            evidence = None
            binaural_pcm = source_mount.binaural_pcm
            self_acoustic = source_mount.receipt
            self_acoustic_prelearning = source_mount.prelearning_firing
            self_acoustic_observation = source_mount.observation
            settlement = source_mount.causal_settlement
            auditory_l5 = source_mount.binaural_l5
            receptors = source_mount.receptor_settlement
            passive_window = None
        elif passive_window_source:
            source_kind = (
                SettledExperienceSourceKind.ANONYMOUS_PASSIVE_WINDOW
            )
            evidence = None
            binaural_pcm = None
            self_acoustic = None
            self_acoustic_prelearning = None
            self_acoustic_observation = None
            settlement = source_mount.settlement
            auditory_l5 = None
            receptors = None
            passive_window = source_mount.receipt
        else:
            source_mount.verify(self._w1_key)
            source_kind = SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            evidence = source_mount.evidence_receipt
            binaural_pcm = source_mount.binaural_pcm
            self_acoustic = None
            self_acoustic_prelearning = None
            self_acoustic_observation = None
            settlement = source_mount.causal_settlement
            auditory_l5 = source_mount.binaural_auditory_l5
            receptors = source_mount.binaural_receptor_settlement
            passive_window = None
        if (
            settlement is None
            or (
                not self_acoustic_source
                and not passive_window_source
                and evidence is None
            )
        ):
            raise ValueError(
                "settled experience custody requires complete causal W1 "
                "evidence"
            )
        expected_binaural_commitment = (
            evidence.binaural_commitment
            if evidence is not None
            else self_acoustic.binaural_commitment
            if self_acoustic is not None
            else {}
        )
        if binaural_pcm is not None:
            binaural_pcm.verify()
        if (
            binaural_pcm.commitment_record()
            if binaural_pcm is not None else {}
        ) != dict(expected_binaural_commitment):
            raise ValueError(
                "settled experience custody pressure commitment changed"
            )
        authenticated_source_receipt = (
            evidence.authority_receipt_sha256
            if evidence is not None
            else self_acoustic.authority_receipt_sha256
            if self_acoustic is not None
            else passive_window.authority_receipt_sha256
        )
        occurrence_id = (
            _digest({
                "anonymous_passive_window_receipt_sha256": (
                    passive_window.authority_receipt_sha256
                ),
                "causal_settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "schema": SETTLED_EXPERIENCE_OCCURRENCE_SCHEMA,
                "world_observation_receipt_sha256": (
                    observation.authority_receipt_sha256
                ),
            })
            if passive_window_source
            else _source_occurrence_id(
                execution=world_execution,
                observation=observation,
                evidence=evidence,
                self_acoustic=self_acoustic,
                settlement=settlement,
                auditory_l5=auditory_l5,
                receptors=receptors,
            )
        )
        counter_payload = {
            "authenticated_source_receipt_sha256": (
                authenticated_source_receipt
            ),
            "binaural_l5_receipt_sha256": (
                auditory_l5.authority_receipt_sha256
                if auditory_l5 is not None else None
            ),
            "binaural_receptor_receipt_sha256": (
                receptors.authority_receipt_sha256
                if receptors is not None else None
            ),
            "causal_settlement_lineage_count": 1,
            "causal_settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "custody_count": 1,
            "full_field_assembly_receipt_sha256": (
                settlement.assembly_receipt_sha256
            ),
            "full_field_build_lineage_count": 1,
            "physical_evidence_receipt_sha256": (
                evidence.authority_receipt_sha256
                if evidence is not None else None
            ),
            "schema": SETTLED_EXPERIENCE_OCCURRENCE_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self_acoustic.authority_receipt_sha256
                if self_acoustic is not None else None
            ),
            "source_kind": source_kind.value,
            "source_occurrence_id": occurrence_id,
            "source_transduction_lineage_count": 1,
            "world_execution_receipt_sha256": (
                world_execution.authority_receipt_sha256
                if world_execution is not None else None
            ),
            "world_observation_receipt_sha256": (
                observation.authority_receipt_sha256
            ),
        }
        counter = SettledExperienceOccurrenceCounter(
            source_occurrence_id=occurrence_id,
            source_kind=source_kind,
            authenticated_source_receipt_sha256=(
                authenticated_source_receipt
            ),
            world_execution_receipt_sha256=(
                world_execution.authority_receipt_sha256
                if world_execution is not None else None
            ),
            world_observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            physical_evidence_receipt_sha256=(
                evidence.authority_receipt_sha256
                if evidence is not None else None
            ),
            self_acoustic_receipt_sha256=(
                self_acoustic.authority_receipt_sha256
                if self_acoustic is not None else None
            ),
            full_field_assembly_receipt_sha256=(
                settlement.assembly_receipt_sha256
            ),
            causal_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            binaural_l5_receipt_sha256=(
                auditory_l5.authority_receipt_sha256
                if auditory_l5 is not None else None
            ),
            binaural_receptor_receipt_sha256=(
                receptors.authority_receipt_sha256
                if receptors is not None else None
            ),
            source_transduction_lineage_count=1,
            full_field_build_lineage_count=1,
            causal_settlement_lineage_count=1,
            custody_count=1,
            authority_receipt_sha256=_digest(counter_payload),
        )
        unsigned = {
            "authenticated_source_receipt_sha256": (
                authenticated_source_receipt
            ),
            "anonymous_passive_window_receipt_sha256": (
                passive_window.authority_receipt_sha256
                if passive_window is not None else None
            ),
            "binaural_l5_receipt_sha256": (
                auditory_l5.authority_receipt_sha256
                if auditory_l5 is not None else None
            ),
            "binaural_receptor_receipt_sha256": (
                receptors.authority_receipt_sha256
                if receptors is not None else None
            ),
            "causal_settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "occurrence_counter_receipt_sha256": (
                counter.authority_receipt_sha256
            ),
            "physical_evidence_receipt_sha256": (
                evidence.authority_receipt_sha256
                if evidence is not None else None
            ),
            "profile_receipt_sha256": (
                self._profile.authority_receipt_sha256
            ),
            "schema": SETTLED_EXPERIENCE_CUSTODY_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self_acoustic.authority_receipt_sha256
                if self_acoustic is not None else None
            ),
            "self_acoustic_prelearning_firing_receipt_sha256": (
                self_acoustic_prelearning.authority_receipt_sha256
                if self_acoustic_prelearning is not None else None
            ),
            "self_acoustic_observation_receipt_sha256": (
                self_acoustic_observation.authority_receipt_sha256
                if self_acoustic_observation is not None else None
            ),
            "source_occurrence_id": occurrence_id,
            "source_kind": source_kind.value,
            "world_execution_receipt_sha256": (
                world_execution.authority_receipt_sha256
                if world_execution is not None else None
            ),
            "world_observation_receipt_sha256": (
                observation.authority_receipt_sha256
            ),
        }
        signature = _sign(self._key, _CUSTODY_DOMAIN, unsigned)
        custody = SettledExperienceCustody(
            profile=self._profile,
            source_occurrence_id=occurrence_id,
            source_kind=source_kind,
            world_execution=world_execution,
            world_observation=observation,
            physical_evidence_receipt=evidence,
            anonymous_passive_window_receipt=passive_window,
            self_acoustic_receipt=self_acoustic,
            self_acoustic_prelearning_firing=(
                self_acoustic_prelearning
            ),
            self_acoustic_observation=self_acoustic_observation,
            causal_settlement=settlement,
            binaural_auditory_l5=auditory_l5,
            binaural_receptor_settlement=receptors,
            occurrence_counter=counter,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": unsigned,
            }),
            _construction_authority=_CONSTRUCTION_AUTHORITY,
        )
        custody.verify(
            authority_key=self._key,
            w1_physical_authority_key=self._w1_key,
            world_authority_key=self._world_key,
            w1_self_acoustic_authority_key=self._self_acoustic_key,
            anonymous_passive_window_authority_key=(
                self._passive_window_key
            ),
        )
        settlement_payload = settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "settled experience causal settlement",
        )
        if (
            receipt_sha256(settlement_payload)
            != settlement.authority_receipt_sha256
        ):
            raise ValueError("custody causal settlement payload changed")
        with self._lock:
            if self._custody is not None:
                if (
                    self._custody.source_occurrence_id
                    == custody.source_occurrence_id
                    and self._custody.authority_receipt_sha256
                    == custody.authority_receipt_sha256
                ):
                    return self._custody
                raise RuntimeError(
                    "settled experience custody capacity is full"
                )
            self._custody = custody
            self._binaural_pcm = binaural_pcm
            self._settlement_payload_bytes = settlement_payload
            try:
                self._encoded_state_for(custody, self._children)
            except BaseException:
                self._custody = None
                self._binaural_pcm = None
                self._settlement_payload_bytes = None
                raise
            return custody

    def issue_child(
        self,
        consumer_id: str,
    ) -> SettledExperienceConsumerCapability:
        consumer = _identifier(
            consumer_id,
            "settled experience consumer",
            max_bytes=MAX_CONSUMER_ID_BYTES,
        )
        with self._lock:
            custody = self._custody
            if custody is None:
                raise RuntimeError(
                    "settled experience custody is not admitted"
                )
            existing = next(
                (
                    value
                    for value in self._children
                    if value.consumer_id == consumer
                ),
                None,
            )
            if existing is not None:
                existing.verify(custody, authority_key=self._key)
                return existing
            if len(self._children) >= self._profile.max_children:
                raise RuntimeError(
                    "settled experience child capacity is full"
                )
            ordinal = len(self._children)
            unsigned = {
                "consumer_id": consumer,
                "ordinal": ordinal,
                "parent_custody_receipt_sha256": (
                    custody.authority_receipt_sha256
                ),
                "schema": SETTLED_EXPERIENCE_CHILD_SCHEMA,
                "source_occurrence_id": custody.source_occurrence_id,
            }
            signature = _sign(self._key, _CHILD_DOMAIN, unsigned)
            capability = SettledExperienceConsumerCapability(
                consumer_id=consumer,
                ordinal=ordinal,
                source_occurrence_id=custody.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    custody.authority_receipt_sha256
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": unsigned,
                }),
            )
            capability.verify(custody, authority_key=self._key)
            prospective = (*self._children, capability)
            self._encoded_state_for(custody, prospective)
            self._children = prospective
            return capability

    def open_child(
        self,
        capability: SettledExperienceConsumerCapability,
    ) -> SettledExperienceConsumerView:
        if not isinstance(
            capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "settled experience child capability is not typed"
            )
        with self._lock:
            custody = self._custody
            if custody is None:
                raise RuntimeError(
                    "settled experience custody is not admitted"
                )
            capability.verify(custody, authority_key=self._key)
            if (
                capability.ordinal >= len(self._children)
                or self._children[capability.ordinal] is not capability
            ):
                raise ValueError(
                    "settled experience child left owner custody"
                )
            return SettledExperienceConsumerView(
                source_occurrence_id=custody.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    custody.authority_receipt_sha256
                ),
                source_kind=custody.source_kind,
                world_execution=custody.world_execution,
                world_observation=custody.world_observation,
                physical_evidence_receipt=(
                    custody.physical_evidence_receipt
                ),
                anonymous_passive_window_receipt=(
                    custody.anonymous_passive_window_receipt
                ),
                self_acoustic_receipt=(
                    custody.self_acoustic_receipt
                ),
                self_acoustic_prelearning_firing=(
                    custody.self_acoustic_prelearning_firing
                ),
                self_acoustic_observation=(
                    custody.self_acoustic_observation
                ),
                causal_settlement=custody.causal_settlement,
                binaural_auditory_l5=(
                    custody.binaural_auditory_l5
                ),
                binaural_receptor_settlement=(
                    custody.binaural_receptor_settlement
                ),
                occurrence_counter=custody.occurrence_counter,
            )

    def open_binaural_pressure(
        self,
        capability: SettledExperienceConsumerCapability,
    ) -> SettledExperienceBinauralPressureView:
        """Open exact PCM only for the dedicated bounded motor capability."""

        view = self.open_child(capability)
        if (
            capability.consumer_id
            != SETTLED_EXPERIENCE_BINAURAL_PRESSURE_CONSUMER_ID
        ):
            raise ValueError(
                "settled pressure requires its dedicated custody capability"
            )
        with self._lock:
            custody = self._custody
            binaural_pcm = self._binaural_pcm
            if custody is None or binaural_pcm is None:
                raise ValueError(
                    "settled custody has no exact binaural pressure"
                )
            binaural_pcm.verify()
            expected = (
                custody.physical_evidence_receipt.binaural_commitment
                if custody.physical_evidence_receipt is not None
                else custody.self_acoustic_receipt.binaural_commitment
            )
            if binaural_pcm.commitment_record() != dict(expected):
                raise ValueError(
                    "settled custody pressure authority changed"
                )
            return SettledExperienceBinauralPressureView(
                source_occurrence_id=view.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    view.parent_custody_receipt_sha256
                ),
                capability_receipt_sha256=(
                    capability.authority_receipt_sha256
                ),
                binaural_pcm=binaural_pcm,
            )

    def _state_payload(
        self,
        custody: SettledExperienceCustody,
        children: tuple[SettledExperienceConsumerCapability, ...],
    ) -> dict[str, object]:
        settlement_payload = self._settlement_payload_bytes
        if (
            custody is not self._custody
            or settlement_payload is None
            or receipt_sha256(settlement_payload)
            != custody.causal_settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "settled experience payload left verified owner custody"
            )
        return {
            "children": [value.as_record() for value in children],
            "custody": {
                **custody.payload(),
                "authority_hmac_sha256": custody.authority_hmac_sha256,
                "authority_receipt_sha256": (
                    custody.authority_receipt_sha256
                ),
            },
            "occurrence_counter": (
                custody.occurrence_counter.as_record()
            ),
            "physical_evidence": (
                custody.physical_evidence_receipt.as_record()
                if custody.physical_evidence_receipt is not None else None
            ),
            "anonymous_passive_window_receipt": (
                custody.anonymous_passive_window_receipt.record()
                if custody.anonymous_passive_window_receipt is not None
                else None
            ),
            "self_acoustic_receipt": (
                {
                    **custody.self_acoustic_receipt.payload(),
                    "authority_hmac_sha256": (
                        custody.self_acoustic_receipt
                        .authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        custody.self_acoustic_receipt
                        .authority_receipt_sha256
                    ),
                }
                if custody.self_acoustic_receipt is not None else None
            ),
            "self_acoustic_prelearning_firing": (
                {
                    "authority_receipt_sha256": (
                        custody.self_acoustic_prelearning_firing
                        .authority_receipt_sha256
                    ),
                    "payload": (
                        custody.self_acoustic_prelearning_firing.payload()
                    ),
                }
                if custody.self_acoustic_prelearning_firing is not None
                else None
            ),
            "self_acoustic_observation": (
                {
                    "authority_receipt_sha256": (
                        custody.self_acoustic_observation
                        .authority_receipt_sha256
                    ),
                    "payload": custody.self_acoustic_observation.payload(),
                }
                if custody.self_acoustic_observation is not None else None
            ),
            "profile": self._profile.as_record(),
            "schema": SETTLED_EXPERIENCE_STATE_SCHEMA,
            "settlement_payload_base64": base64.b64encode(
                settlement_payload
            ).decode("ascii"),
            "w1_binaural_l5": (
                custody.binaural_auditory_l5.persistence_record()
                if custody.binaural_auditory_l5 is not None else None
            ),
            "w1_binaural_receptors": (
                custody.binaural_receptor_settlement.authority_record()
                if custody.binaural_receptor_settlement is not None else None
            ),
            "world_execution": (
                custody.world_execution.as_record()
                if custody.world_execution is not None else None
            ),
            "world_observation": (
                custody.world_observation.as_record()
            ),
        }

    def _encoded_state_for(
        self,
        custody: SettledExperienceCustody,
        children: tuple[SettledExperienceConsumerCapability, ...],
    ) -> bytes:
        if len(children) > self._profile.max_children:
            raise RuntimeError(
                "settled experience child capacity is full"
            )
        payload = self._state_payload(custody, children)
        payload_bytes = _canonical(payload)
        signature = hmac.new(
            self._key,
            _STATE_DOMAIN + payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload_base64": base64.b64encode(
                payload_bytes
            ).decode("ascii"),
            "schema": SETTLED_EXPERIENCE_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._profile.max_snapshot_bytes:
            raise RuntimeError(
                "settled experience snapshot byte capacity is full"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._custody is None:
                raise RuntimeError(
                    "settled experience custody is not admitted"
                )
            return self._encoded_state_for(
                self._custody,
                self._children,
            )

    @classmethod
    def restore_encoded(
        cls,
        encoded: bytes,
        *,
        authority_key: bytes | str,
        w1_physical_authority_key: bytes | str,
        world_authority_key: bytes | str,
        source_mount: (
            W1PhysicalEvidenceMount
            | W1SelfAcousticMount
            | AnonymousPassiveWindowMount
        ),
        w1_self_acoustic_authority_key: bytes | str | None = None,
        anonymous_passive_window_authority_key: (
            bytes | str | None
        ) = None,
        world_execution: ActionExecutionReceipt | None = None,
        world_observation: ObservationSnapshot | None = None,
    ) -> "SettledExperienceCustodyAuthority":
        """Rehydrate exact custody; never reconstruct physical evidence."""

        key = _key(
            authority_key,
            "settled experience custody authority key",
        )
        if not isinstance(encoded, bytes) or not encoded:
            raise TypeError(
                "settled experience snapshot must be nonempty bytes"
            )
        if len(encoded) > MAX_CONFIGURED_SNAPSHOT_BYTES:
            raise ValueError(
                "settled experience snapshot exceeds its safety boundary"
            )
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "settled experience snapshot is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {
                "authority_hmac_sha256",
                "payload_base64",
                "schema",
            }
            or envelope.get("schema")
            != SETTLED_EXPERIENCE_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "settled experience snapshot envelope changed"
            )
        try:
            payload_bytes = base64.b64decode(
                envelope.get("payload_base64"),
                validate=True,
            )
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError(
                "settled experience snapshot payload is unreadable"
            ) from error
        expected_hmac = hmac.new(
            key,
            _STATE_DOMAIN + payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        if (
            not isinstance(payload, Mapping)
            or _canonical(payload) != payload_bytes
            or not hmac.compare_digest(
                expected_hmac,
                envelope.get("authority_hmac_sha256", ""),
            )
            or set(payload) != {
                "children",
                "anonymous_passive_window_receipt",
                "custody",
                "occurrence_counter",
                "physical_evidence",
                "profile",
                "schema",
                "self_acoustic_receipt",
                "self_acoustic_prelearning_firing",
                "self_acoustic_observation",
                "settlement_payload_base64",
                "w1_binaural_l5",
                "w1_binaural_receptors",
                "world_execution",
                "world_observation",
            }
            or payload.get("schema") != SETTLED_EXPERIENCE_STATE_SCHEMA
        ):
            raise ValueError(
                "settled experience snapshot authority changed"
            )
        profile = SettledExperienceCustodyProfile.from_record(
            payload.get("profile")
        )
        if len(encoded) > profile.max_snapshot_bytes:
            raise ValueError(
                "settled experience snapshot exceeds its profile"
            )
        authority = cls(
            authority_key=key,
            w1_physical_authority_key=w1_physical_authority_key,
            world_authority_key=world_authority_key,
            profile=profile,
            w1_self_acoustic_authority_key=(
                w1_self_acoustic_authority_key
            ),
            anonymous_passive_window_authority_key=(
                anonymous_passive_window_authority_key
            ),
        )
        custody = (
            authority.admit(source_mount)
            if isinstance(source_mount, AnonymousPassiveWindowMount)
            else authority.admit(
                source_mount,
                world_execution,
                world_observation=world_observation,
            )
        )
        children = payload.get("children")
        if (
            not isinstance(children, list)
            or len(children) > profile.max_children
        ):
            raise ValueError(
                "settled experience snapshot children changed"
            )
        for ordinal, value in enumerate(children):
            if (
                not isinstance(value, Mapping)
                or value.get("ordinal") != ordinal
            ):
                raise ValueError(
                    "settled experience snapshot child order changed"
                )
            capability = authority.issue_child(
                value.get("consumer_id")
            )
            if capability.as_record() != dict(value):
                raise ValueError(
                    "settled experience snapshot child changed"
                )
        expected_state = authority._state_payload(
            custody,
            authority._children,
        )
        if expected_state != dict(payload):
            raise ValueError(
                "settled experience snapshot names other live custody"
            )
        if authority.snapshot_encoded() != encoded:
            raise ValueError(
                "settled experience snapshot is not byte-identical"
            )
        return authority

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "admitted": self._custody is not None,
                "child_capacity": self._profile.max_children,
                "child_count": len(self._children),
                "max_snapshot_bytes": (
                    self._profile.max_snapshot_bytes
                ),
                "transient_binaural_pressure": (
                    self._binaural_pcm is not None
                ),
                "occurrence_counter": (
                    self._custody.occurrence_counter.as_record()
                    if self._custody is not None else None
                ),
                "schema": (
                    "guala.settled_experience_custody.status.v1"
                ),
                "source_occurrence_id": (
                    self._custody.source_occurrence_id
                    if self._custody is not None else None
                ),
            }


__all__ = (
    "MAX_CONFIGURED_CHILDREN",
    "MAX_CONFIGURED_SNAPSHOT_BYTES",
    "SETTLED_EXPERIENCE_BINAURAL_PRESSURE_CONSUMER_ID",
    "SettledExperienceBinauralPressureView",
    "SettledExperienceConsumerCapability",
    "SettledExperienceConsumerView",
    "SettledExperienceCustody",
    "SettledExperienceCustodyAuthority",
    "SettledExperienceCustodyProfile",
    "SettledExperienceOccurrenceCounter",
)
