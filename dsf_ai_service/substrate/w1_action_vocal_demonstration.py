"""Fresh full-field W1 action-to-self-vocal demonstrations.

A demonstration is admitted only when a newly settled dynamic action outcome
is followed immediately by the exact calibrated self-vocal motor and its
authenticated two-ear hearing.  The challenge is resolved by equality of the
complete retained action-field roots.  The response is resolved by the full
calibrated left/right q conjunction.  No external cue, label, transcript,
score, coordinate lookup, or partial match is admitted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import EmbodimentWorldAuthority
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    is_dynamic_grounding_root,
)
from dsf_ai_service.substrate.w1_binaural_controlled_distinction import (
    W1DiagnosticCell,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralActivationEvidence,
)
from dsf_ai_service.substrate.w1_cross_regime_vocal_calibration import (
    W1CalibratedVocalForm,
    W1CrossRegimeVocalCalibration,
    W1CrossRegimeVocalCalibrationOwner,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticState,
)


W1_ACTION_VOCAL_DEMONSTRATION_PROFILE_SCHEMA = (
    "guala.w1.action_vocal_demonstration.profile.v1"
)
W1_ACTION_VOCAL_DEMONSTRATION_SCHEMA = (
    "guala.w1.action_vocal_demonstration.v1"
)
_DEMONSTRATION_DOMAIN = (
    b"guala-w1-action-vocal-demonstration-v1\0"
)
_HEX = frozenset("0123456789abcdef")
W1_ACTION_VOCAL_DEMONSTRATION_ACTION_CONSUMER_ID = (
    "w1-action-vocal-demonstration.action"
)
W1_ACTION_VOCAL_DEMONSTRATION_SELF_CONSUMER_ID = (
    "w1-action-vocal-demonstration.self"
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
        raise TypeError("W1 demonstration key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 demonstration key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("W1 demonstration time must be exact")
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class W1ActionVocalDemonstrationResourceProfile:
    profile_id: str
    max_demonstrations: int
    max_action_roots: int
    max_self_activations: int
    max_demonstration_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_demonstrations: int,
        max_action_roots: int,
        max_self_activations: int,
        max_demonstration_bytes: int,
    ) -> "W1ActionVocalDemonstrationResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("W1 demonstration profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_demonstrations=_positive(
                max_demonstrations,
                "W1 demonstration capacity",
            ),
            max_action_roots=_positive(
                max_action_roots,
                "W1 demonstration action-root capacity",
            ),
            max_self_activations=_positive(
                max_self_activations,
                "W1 demonstration activation capacity",
            ),
            max_demonstration_bytes=_positive(
                max_demonstration_bytes,
                "W1 demonstration byte capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_demonstrations=provisional.max_demonstrations,
            max_action_roots=provisional.max_action_roots,
            max_self_activations=provisional.max_self_activations,
            max_demonstration_bytes=(
                provisional.max_demonstration_bytes
            ),
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_action_roots": self.max_action_roots,
            "max_demonstration_bytes": self.max_demonstration_bytes,
            "max_demonstrations": self.max_demonstrations,
            "max_self_activations": self.max_self_activations,
            "profile_id": self.profile_id,
            "schema": W1_ACTION_VOCAL_DEMONSTRATION_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_demonstrations, "W1 demonstration capacity"),
            (
                self.max_action_roots,
                "W1 demonstration action-root capacity",
            ),
            (
                self.max_self_activations,
                "W1 demonstration activation capacity",
            ),
            (
                self.max_demonstration_bytes,
                "W1 demonstration byte capacity",
            ),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 demonstration profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 demonstration profile authority changed")


@dataclass(frozen=True, slots=True)
class W1ActionVocalDemonstration:
    demonstration_id: str
    calibration_receipt_sha256: str
    calibrated_action_field_identity: str
    motor_id: str
    action_execution_receipt_sha256: str
    action_evidence_receipt_sha256: str
    action_settlement_receipt_sha256: str
    self_execution_receipt_sha256: str
    self_emission_receipt_sha256: str
    self_acoustic_receipt_sha256: str
    action_before_world_state_sha256: str
    action_before_revision: int
    junction_revision: int
    self_after_revision: int
    action_source_time_start: Fraction
    action_source_time_end: Fraction
    self_source_time_start: Fraction
    self_source_time_end: Fraction
    action_roots: tuple[GroundingRoot, ...]
    self_activations: tuple[W1BinauralActivationEvidence, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def self_cells(self) -> frozenset[W1DiagnosticCell]:
        return frozenset(
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in self.self_activations
        )

    def payload(self) -> dict[str, object]:
        return {
            "action_before_revision": self.action_before_revision,
            "action_before_world_state_sha256": (
                self.action_before_world_state_sha256
            ),
            "action_evidence_receipt_sha256": (
                self.action_evidence_receipt_sha256
            ),
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256
            ),
            "action_roots": [
                value.as_record() for value in self.action_roots
            ],
            "action_settlement_receipt_sha256": (
                self.action_settlement_receipt_sha256
            ),
            "action_source_time_end": _fraction_text(
                self.action_source_time_end
            ),
            "action_source_time_start": _fraction_text(
                self.action_source_time_start
            ),
            "calibrated_action_field_identity": (
                self.calibrated_action_field_identity
            ),
            "calibration_receipt_sha256": (
                self.calibration_receipt_sha256
            ),
            "junction_revision": self.junction_revision,
            "motor_id": self.motor_id,
            "schema": W1_ACTION_VOCAL_DEMONSTRATION_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self.self_acoustic_receipt_sha256
            ),
            "self_activations": [
                value.record() for value in self.self_activations
            ],
            "self_after_revision": self.self_after_revision,
            "self_emission_receipt_sha256": (
                self.self_emission_receipt_sha256
            ),
            "self_execution_receipt_sha256": (
                self.self_execution_receipt_sha256
            ),
            "self_source_time_end": _fraction_text(
                self.self_source_time_end
            ),
            "self_source_time_start": _fraction_text(
                self.self_source_time_start
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "demonstration_id": self.demonstration_id,
        }


class W1ActionVocalDemonstrationOwner:
    """Bounded exact owner of fresh action-to-self-vocal proofs."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1ActionVocalDemonstrationResourceProfile,
        world_authority: EmbodimentWorldAuthority,
        motor_owner: SelfVocalPCMMotorOwner,
        calibration_owner: W1CrossRegimeVocalCalibrationOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 demonstration requires its world")
        if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
            raise TypeError("W1 demonstration requires motor authority")
        if not isinstance(
            calibration_owner,
            W1CrossRegimeVocalCalibrationOwner,
        ):
            raise TypeError("W1 demonstration requires calibration authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._demonstration_key = hashlib.sha256(
            _DEMONSTRATION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._world = world_authority
        self._motor = motor_owner
        self._calibration = calibration_owner
        self._demonstrations: dict[
            str, W1ActionVocalDemonstration
        ] = {}
        self._used_sources: set[str] = set()
        self._lock = threading.RLock()

    def _verify(
        self,
        demonstration: W1ActionVocalDemonstration,
    ) -> None:
        for value, name in (
            (demonstration.demonstration_id, "W1 demonstration"),
            (
                demonstration.calibration_receipt_sha256,
                "W1 demonstration calibration",
            ),
            (
                demonstration.calibrated_action_field_identity,
                "W1 demonstration action field",
            ),
            (demonstration.motor_id, "W1 demonstration motor"),
            (
                demonstration.action_execution_receipt_sha256,
                "W1 demonstration action execution",
            ),
            (
                demonstration.action_evidence_receipt_sha256,
                "W1 demonstration action evidence",
            ),
            (
                demonstration.action_settlement_receipt_sha256,
                "W1 demonstration action settlement",
            ),
            (
                demonstration.self_execution_receipt_sha256,
                "W1 demonstration self execution",
            ),
            (
                demonstration.self_emission_receipt_sha256,
                "W1 demonstration self emission",
            ),
            (
                demonstration.self_acoustic_receipt_sha256,
                "W1 demonstration self hearing",
            ),
            (
                demonstration.action_before_world_state_sha256,
                "W1 demonstration controlled world",
            ),
            (
                demonstration.authority_hmac_sha256,
                "W1 demonstration HMAC",
            ),
            (
                demonstration.authority_receipt_sha256,
                "W1 demonstration authority",
            ),
        ):
            _sha256(value, name)
        if (
            demonstration.action_before_revision < 0
            or demonstration.junction_revision
            != demonstration.action_before_revision + 1
            or demonstration.self_after_revision
            != demonstration.junction_revision + 1
            or demonstration.action_source_time_end
            <= demonstration.action_source_time_start
            or demonstration.self_source_time_end
            <= demonstration.self_source_time_start
            or not demonstration.action_roots
            or len(demonstration.action_roots)
            > self._profile.max_action_roots
            or not demonstration.self_activations
            or len(demonstration.self_activations)
            > self._profile.max_self_activations
        ):
            raise ValueError("W1 demonstration boundary changed")
        for root in demonstration.action_roots:
            root.verify()
            if not is_dynamic_grounding_root(root):
                raise ValueError("W1 demonstration retained a static root")
        for activation in demonstration.self_activations:
            activation.verify()
        payload = demonstration.payload()
        signature = hmac.new(
            self._demonstration_key,
            _DEMONSTRATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            demonstration.demonstration_id != _digest(payload)
            or len(_canonical(payload))
            > self._profile.max_demonstration_bytes
            or not hmac.compare_digest(
                signature, demonstration.authority_hmac_sha256
            )
            or demonstration.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 demonstration authority changed")

    def admit(
        self,
        *,
        calibration: W1CrossRegimeVocalCalibration,
        action_custody_authority: SettledExperienceCustodyAuthority,
        action_custody_capability: SettledExperienceConsumerCapability,
        self_custody_authority: SettledExperienceCustodyAuthority,
        self_custody_capability: SettledExperienceConsumerCapability,
    ) -> W1ActionVocalDemonstration:
        self._calibration.verify(calibration)
        if (
            not isinstance(
                action_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                self_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                action_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or not isinstance(
                self_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or action_custody_capability.consumer_id
            != W1_ACTION_VOCAL_DEMONSTRATION_ACTION_CONSUMER_ID
            or self_custody_capability.consumer_id
            != W1_ACTION_VOCAL_DEMONSTRATION_SELF_CONSUMER_ID
        ):
            raise ValueError(
                "W1 demonstration requires its purpose-bound custody"
            )
        action_view = action_custody_authority.open_child(
            action_custody_capability
        )
        self_view = self_custody_authority.open_child(
            self_custody_capability
        )
        action_execution = action_view.world_execution
        action_receipt = action_view.physical_evidence_receipt
        self_execution = self_view.world_execution
        self_receipt = self_view.self_acoustic_receipt
        self_firing = self_view.self_acoustic_prelearning_firing
        exemplars = tuple(
            value for value in self._motor.exemplars
            if self_receipt is not None
            and value.motor_id == self_receipt.motor_id
        )
        if len(exemplars) != 1:
            raise ValueError("W1 demonstration self motor is not owned")
        self_exemplar = exemplars[0]
        self._motor.verify_exemplar(self_exemplar)
        if (
            action_view.source_kind
            is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            or self_view.source_kind
            is not SettledExperienceSourceKind.SELF_ACOUSTIC
            or action_execution is None
            or action_receipt is None
            or self_execution is None
            or self_receipt is None
            or self_firing is None
            or action_receipt.acoustic_emission_receipt_sha256s
            or action_receipt.world_execution_receipt_sha256
            != action_execution.authority_receipt_sha256
            or action_execution.before.state_sha256
            != calibration.controlled_before_world_state_sha256
            or action_execution.after != self_execution.before
            or self_execution.after.revision
            != action_execution.after.revision + 1
            or self_receipt.state
            is not W1SelfAcousticState.OBSERVED
            or self_receipt.world_execution_receipt_sha256
            != self_execution.authority_receipt_sha256
            or self_receipt.motor_id != self_exemplar.motor_id
        ):
            raise ValueError(
                "W1 demonstration physical revision chain changed"
            )
        action_roots = tuple(
            root
            for root in grounding_roots_from_settlement(
                action_view.causal_settlement
            )
            if is_dynamic_grounding_root(root)
        )
        forms = tuple(
            form for form in calibration.forms
            if form.action_roots == action_roots
        )
        if len(forms) != 1:
            raise ValueError(
                "W1 challenge action field is absent or ambiguous"
            )
        expected_form: W1CalibratedVocalForm = forms[0]
        self_activations = tuple(
            W1BinauralActivationEvidence.from_activation(value)
            for value in self_firing.activations
        )
        active_cells = frozenset(
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in self_activations
        )
        resolved = self._calibration.resolve_self_cells(
            calibration=calibration,
            active_cells=active_cells,
        )
        if (
            resolved != expected_form
            or self_exemplar.motor_id != expected_form.motor_id
        ):
            raise ValueError(
                "W1 challenge received the wrong calibrated response"
            )
        if (
            len(action_roots) > self._profile.max_action_roots
            or len(self_activations)
            > self._profile.max_self_activations
        ):
            raise RuntimeError("W1 demonstration capacity exhausted")
        source_receipts = {
            action_execution.authority_receipt_sha256,
            action_receipt.authority_receipt_sha256,
            action_view.causal_settlement.authority_receipt_sha256,
            action_view.parent_custody_receipt_sha256,
            action_custody_capability.authority_receipt_sha256,
            self_execution.authority_receipt_sha256,
            self_receipt.self_vocal_emission_receipt_sha256,
            self_receipt.authority_receipt_sha256,
            self_view.parent_custody_receipt_sha256,
            self_custody_capability.authority_receipt_sha256,
        }
        if len(source_receipts) != 10:
            raise ValueError("W1 demonstration source identities overlap")
        provisional = W1ActionVocalDemonstration(
            demonstration_id="0" * 64,
            calibration_receipt_sha256=(
                calibration.authority_receipt_sha256
            ),
            calibrated_action_field_identity=(
                expected_form.action_field_identity
            ),
            motor_id=expected_form.motor_id,
            action_execution_receipt_sha256=(
                action_execution.authority_receipt_sha256
            ),
            action_evidence_receipt_sha256=(
                action_receipt.authority_receipt_sha256
            ),
            action_settlement_receipt_sha256=(
                action_view.causal_settlement.authority_receipt_sha256
            ),
            self_execution_receipt_sha256=(
                self_execution.authority_receipt_sha256
            ),
            self_emission_receipt_sha256=(
                self_receipt.self_vocal_emission_receipt_sha256
            ),
            self_acoustic_receipt_sha256=(
                self_receipt.authority_receipt_sha256
            ),
            action_before_world_state_sha256=(
                action_execution.before.state_sha256
            ),
            action_before_revision=action_execution.before.revision,
            junction_revision=action_execution.after.revision,
            self_after_revision=self_execution.after.revision,
            action_source_time_start=action_receipt.source_time_start,
            action_source_time_end=action_receipt.source_time_end,
            self_source_time_start=self_receipt.source_time_start,
            self_source_time_end=self_receipt.source_time_end,
            action_roots=action_roots,
            self_activations=self_activations,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._demonstration_key,
            _DEMONSTRATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1ActionVocalDemonstration(
            demonstration_id=_digest(payload),
            calibration_receipt_sha256=(
                provisional.calibration_receipt_sha256
            ),
            calibrated_action_field_identity=(
                provisional.calibrated_action_field_identity
            ),
            motor_id=provisional.motor_id,
            action_execution_receipt_sha256=(
                provisional.action_execution_receipt_sha256
            ),
            action_evidence_receipt_sha256=(
                provisional.action_evidence_receipt_sha256
            ),
            action_settlement_receipt_sha256=(
                provisional.action_settlement_receipt_sha256
            ),
            self_execution_receipt_sha256=(
                provisional.self_execution_receipt_sha256
            ),
            self_emission_receipt_sha256=(
                provisional.self_emission_receipt_sha256
            ),
            self_acoustic_receipt_sha256=(
                provisional.self_acoustic_receipt_sha256
            ),
            action_before_world_state_sha256=(
                provisional.action_before_world_state_sha256
            ),
            action_before_revision=provisional.action_before_revision,
            junction_revision=provisional.junction_revision,
            self_after_revision=provisional.self_after_revision,
            action_source_time_start=(
                provisional.action_source_time_start
            ),
            action_source_time_end=provisional.action_source_time_end,
            self_source_time_start=provisional.self_source_time_start,
            self_source_time_end=provisional.self_source_time_end,
            action_roots=provisional.action_roots,
            self_activations=provisional.self_activations,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self._verify(result)
        with self._lock:
            if self._used_sources.intersection(source_receipts):
                raise ValueError(
                    "W1 demonstration reuses a physical source"
                )
            if (
                len(self._demonstrations)
                >= self._profile.max_demonstrations
            ):
                raise RuntimeError("W1 demonstration capacity exhausted")
            self._demonstrations[result.demonstration_id] = result
            self._used_sources.update(source_receipts)
        return result

    def verify(
        self,
        demonstration: W1ActionVocalDemonstration,
    ) -> None:
        if not isinstance(
            demonstration,
            W1ActionVocalDemonstration,
        ):
            raise TypeError("W1 demonstration is not typed")
        self._verify(demonstration)

    @property
    def demonstrations(
        self,
    ) -> tuple[W1ActionVocalDemonstration, ...]:
        with self._lock:
            return tuple(
                self._demonstrations[key]
                for key in sorted(self._demonstrations)
            )


__all__ = [
    "W1_ACTION_VOCAL_DEMONSTRATION_ACTION_CONSUMER_ID",
    "W1_ACTION_VOCAL_DEMONSTRATION_SELF_CONSUMER_ID",
    "W1ActionVocalDemonstration",
    "W1ActionVocalDemonstrationOwner",
    "W1ActionVocalDemonstrationResourceProfile",
]
