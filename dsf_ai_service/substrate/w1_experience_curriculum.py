"""Persistent production owner for experience-grown W1 plumbing evidence.

The owner retains only authenticated calibration and fresh-demonstration
evidence.  It never creates curriculum evidence during construction or
restore.  Its acceptance artifact is an exact conjunction over retained
source-disjoint records and explicitly makes no human developmental-age
claim.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
)
from dsf_ai_service.substrate.w1_action_vocal_demonstration import (
    W1ActionVocalDemonstration,
    W1ActionVocalDemonstrationOwner,
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


W1_EXPERIENCE_CURRICULUM_PROFILE_SCHEMA = (
    "guala.w1.experience_curriculum.profile.v1"
)
W1_EXPERIENCE_CURRICULUM_STATE_SCHEMA = (
    "guala.w1.experience_curriculum.state.v1"
)
W1_EXPERIENCE_CURRICULUM_ENVELOPE_SCHEMA = (
    "guala.w1.experience_curriculum.state_hmac.v1"
)
W1_EXPERIENCE_CURRICULUM_ACCEPTANCE_SCHEMA = (
    "guala.w1.experience_curriculum.acceptance.v1"
)
_STATE_DOMAIN = b"guala-w1-experience-curriculum-state-v1\0"
_ACCEPTANCE_DOMAIN = (
    b"guala-w1-experience-curriculum-acceptance-v1\0"
)
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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 curriculum key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 curriculum key boundary changed")
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


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not an exact fraction") from error
    if f"{result.numerator}/{result.denominator}" != value:
        raise ValueError(f"{name} is not canonically encoded")
    return result


def _root(raw: object) -> GroundingRoot:
    if not isinstance(raw, Mapping) or set(raw) != {
        "root_id",
        "value_json",
        "value_sha256",
    }:
        raise ValueError("W1 curriculum grounding root changed")
    result = GroundingRoot(
        root_id=raw.get("root_id"),
        value_sha256=raw.get("value_sha256"),
        value_json=raw.get("value_json"),
    )
    result.verify()
    return result


def _cell(raw: object) -> W1DiagnosticCell:
    if not isinstance(raw, Mapping) or set(raw) != {
        "ear_id",
        "neuron_id",
    }:
        raise ValueError("W1 curriculum diagnostic cell changed")
    result = W1DiagnosticCell(
        ear_id=raw.get("ear_id"),
        neuron_id=raw.get("neuron_id"),
    )
    result.verify()
    return result


def _activation(raw: object) -> W1BinauralActivationEvidence:
    if not isinstance(raw, Mapping) or set(raw) != {
        "activation_json",
        "authority_receipt_sha256",
        "ear_id",
        "neuron_id",
    }:
        raise ValueError("W1 curriculum activation changed")
    result = W1BinauralActivationEvidence(
        ear_id=raw.get("ear_id"),
        neuron_id=raw.get("neuron_id"),
        activation_json=raw.get("activation_json"),
        authority_receipt_sha256=raw.get(
            "authority_receipt_sha256"
        ),
    )
    result.verify()
    return result


def _calibration(
    raw: object,
    owner: W1CrossRegimeVocalCalibrationOwner,
) -> W1CrossRegimeVocalCalibration:
    expected = {
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "calibration_id",
        "controlled_before_world_state_sha256",
        "forms",
        "schema",
        "source_imitation_receipt_sha256s",
    }
    if (
        not isinstance(raw, Mapping)
        or set(raw) != expected
        or not isinstance(raw.get("forms"), list)
        or not isinstance(
            raw.get("source_imitation_receipt_sha256s"), list
        )
    ):
        raise ValueError("W1 curriculum calibration record changed")
    forms = []
    for form in raw["forms"]:
        if (
            not isinstance(form, Mapping)
            or set(form)
            != {
                "action_field_identity",
                "action_roots",
                "diagnostic_cells",
                "motor_id",
                "positive_imitation_receipt_sha256s",
            }
            or not isinstance(form.get("action_roots"), list)
            or not isinstance(form.get("diagnostic_cells"), list)
            or not isinstance(
                form.get("positive_imitation_receipt_sha256s"), list
            )
        ):
            raise ValueError("W1 curriculum calibrated form changed")
        value = W1CalibratedVocalForm(
            action_roots=tuple(_root(item) for item in form["action_roots"]),
            motor_id=form.get("motor_id"),
            diagnostic_cells=tuple(
                _cell(item) for item in form["diagnostic_cells"]
            ),
            positive_imitation_receipt_sha256s=tuple(
                form["positive_imitation_receipt_sha256s"]
            ),
        )
        if value.action_field_identity != form.get(
            "action_field_identity"
        ):
            raise ValueError("W1 curriculum action-field identity changed")
        forms.append(value)
    result = W1CrossRegimeVocalCalibration(
        calibration_id=raw.get("calibration_id"),
        controlled_before_world_state_sha256=raw.get(
            "controlled_before_world_state_sha256"
        ),
        forms=tuple(forms),
        source_imitation_receipt_sha256s=tuple(
            raw["source_imitation_receipt_sha256s"]
        ),
        authority_hmac_sha256=raw.get("authority_hmac_sha256"),
        authority_receipt_sha256=raw.get(
            "authority_receipt_sha256"
        ),
    )
    owner.verify(result)
    if result.record() != dict(raw):
        raise ValueError("W1 curriculum calibration is not canonical")
    return result


def _demonstration(
    raw: object,
    owner: W1ActionVocalDemonstrationOwner,
) -> W1ActionVocalDemonstration:
    expected = {
        "action_before_revision",
        "action_before_world_state_sha256",
        "action_evidence_receipt_sha256",
        "action_execution_receipt_sha256",
        "action_roots",
        "action_settlement_receipt_sha256",
        "action_source_time_end",
        "action_source_time_start",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "calibrated_action_field_identity",
        "calibration_receipt_sha256",
        "demonstration_id",
        "junction_revision",
        "motor_id",
        "schema",
        "self_acoustic_receipt_sha256",
        "self_activations",
        "self_after_revision",
        "self_emission_receipt_sha256",
        "self_execution_receipt_sha256",
        "self_source_time_end",
        "self_source_time_start",
    }
    if (
        not isinstance(raw, Mapping)
        or set(raw) != expected
        or not isinstance(raw.get("action_roots"), list)
        or not isinstance(raw.get("self_activations"), list)
    ):
        raise ValueError("W1 curriculum demonstration record changed")
    result = W1ActionVocalDemonstration(
        demonstration_id=raw.get("demonstration_id"),
        calibration_receipt_sha256=raw.get(
            "calibration_receipt_sha256"
        ),
        calibrated_action_field_identity=raw.get(
            "calibrated_action_field_identity"
        ),
        motor_id=raw.get("motor_id"),
        action_execution_receipt_sha256=raw.get(
            "action_execution_receipt_sha256"
        ),
        action_evidence_receipt_sha256=raw.get(
            "action_evidence_receipt_sha256"
        ),
        action_settlement_receipt_sha256=raw.get(
            "action_settlement_receipt_sha256"
        ),
        self_execution_receipt_sha256=raw.get(
            "self_execution_receipt_sha256"
        ),
        self_emission_receipt_sha256=raw.get(
            "self_emission_receipt_sha256"
        ),
        self_acoustic_receipt_sha256=raw.get(
            "self_acoustic_receipt_sha256"
        ),
        action_before_world_state_sha256=raw.get(
            "action_before_world_state_sha256"
        ),
        action_before_revision=raw.get("action_before_revision"),
        junction_revision=raw.get("junction_revision"),
        self_after_revision=raw.get("self_after_revision"),
        action_source_time_start=_fraction(
            raw.get("action_source_time_start"),
            "W1 curriculum action start",
        ),
        action_source_time_end=_fraction(
            raw.get("action_source_time_end"),
            "W1 curriculum action end",
        ),
        self_source_time_start=_fraction(
            raw.get("self_source_time_start"),
            "W1 curriculum self start",
        ),
        self_source_time_end=_fraction(
            raw.get("self_source_time_end"),
            "W1 curriculum self end",
        ),
        action_roots=tuple(_root(item) for item in raw["action_roots"]),
        self_activations=tuple(
            _activation(item) for item in raw["self_activations"]
        ),
        authority_hmac_sha256=raw.get("authority_hmac_sha256"),
        authority_receipt_sha256=raw.get(
            "authority_receipt_sha256"
        ),
    )
    owner.verify(result)
    if result.record() != dict(raw):
        raise ValueError("W1 curriculum demonstration is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class W1ExperienceCurriculumResourceProfile:
    profile_id: str
    max_calibrations: int
    max_demonstrations: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_calibrations: int,
        max_demonstrations: int,
        max_state_bytes: int,
    ) -> "W1ExperienceCurriculumResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("W1 curriculum profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_calibrations=_positive(
                max_calibrations, "W1 curriculum calibration capacity"
            ),
            max_demonstrations=_positive(
                max_demonstrations,
                "W1 curriculum demonstration capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes, "W1 curriculum state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_calibrations=provisional.max_calibrations,
            max_demonstrations=provisional.max_demonstrations,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_calibrations": self.max_calibrations,
            "max_demonstrations": self.max_demonstrations,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": W1_EXPERIENCE_CURRICULUM_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        _positive(
            self.max_calibrations,
            "W1 curriculum calibration capacity",
        )
        _positive(
            self.max_demonstrations,
            "W1 curriculum demonstration capacity",
        )
        _positive(self.max_state_bytes, "W1 curriculum state capacity")
        _sha256(
            self.authority_receipt_sha256,
            "W1 curriculum profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 curriculum profile authority changed")


@dataclass(frozen=True, slots=True)
class W1ExperienceCurriculumAcceptance:
    state: str
    developmental_equivalence: str
    calibration_count: int
    calibrated_form_count: int
    external_hearing_count: int
    self_hearing_count: int
    distinct_motor_count: int
    demonstration_count: int
    demonstrated_form_count: int
    evidence_receipts_disjoint: bool
    capacity_available: bool
    unsatisfied_conditions: tuple[str, ...]
    retained_calibration_receipt_sha256s: tuple[str, ...]
    retained_demonstration_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "calibrated_form_count": self.calibrated_form_count,
            "calibration_count": self.calibration_count,
            "capacity_available": self.capacity_available,
            "demonstrated_form_count": self.demonstrated_form_count,
            "demonstration_count": self.demonstration_count,
            "developmental_equivalence": self.developmental_equivalence,
            "distinct_motor_count": self.distinct_motor_count,
            "evidence_receipts_disjoint": (
                self.evidence_receipts_disjoint
            ),
            "external_hearing_count": self.external_hearing_count,
            "retained_calibration_receipt_sha256s": list(
                self.retained_calibration_receipt_sha256s
            ),
            "retained_demonstration_receipt_sha256s": list(
                self.retained_demonstration_receipt_sha256s
            ),
            "schema": W1_EXPERIENCE_CURRICULUM_ACCEPTANCE_SCHEMA,
            "self_hearing_count": self.self_hearing_count,
            "state": self.state,
            "unsatisfied_conditions": list(
                self.unsatisfied_conditions
            ),
        }


class W1ExperienceCurriculumOwner:
    """Persisted authority over learned W1 calibration plumbing."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1ExperienceCurriculumResourceProfile,
        calibration_owner: W1CrossRegimeVocalCalibrationOwner,
        demonstration_owner: W1ActionVocalDemonstrationOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(
            calibration_owner,
            W1CrossRegimeVocalCalibrationOwner,
        ):
            raise TypeError("W1 curriculum requires calibration authority")
        if not isinstance(
            demonstration_owner,
            W1ActionVocalDemonstrationOwner,
        ):
            raise TypeError("W1 curriculum requires demonstration authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._acceptance_key = hashlib.sha256(
            _ACCEPTANCE_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._calibration_owner = calibration_owner
        self._demonstration_owner = demonstration_owner
        self._calibrations: dict[
            str, W1CrossRegimeVocalCalibration
        ] = {}
        self._demonstrations: dict[
            str, W1ActionVocalDemonstration
        ] = {}
        self._lock = threading.RLock()

    def admit_calibration(
        self,
        calibration: W1CrossRegimeVocalCalibration,
    ) -> None:
        self._calibration_owner.verify(calibration)
        with self._lock:
            if calibration.calibration_id in self._calibrations:
                return
            if len(self._calibrations) >= self._profile.max_calibrations:
                raise RuntimeError(
                    "W1 curriculum calibration capacity exhausted"
                )
            candidate = dict(self._calibrations)
            candidate[calibration.calibration_id] = calibration
            self._encoded(candidate, self._demonstrations)
            self._calibrations = candidate

    def admit_demonstration(
        self,
        demonstration: W1ActionVocalDemonstration,
    ) -> None:
        self._demonstration_owner.verify(demonstration)
        with self._lock:
            calibrations = {
                value.authority_receipt_sha256: value
                for value in self._calibrations.values()
            }
            calibration = calibrations.get(
                demonstration.calibration_receipt_sha256
            )
            if calibration is None:
                raise ValueError(
                    "W1 demonstration calibration is not retained"
                )
            matching = tuple(
                form for form in calibration.forms
                if (
                    form.action_field_identity
                    == demonstration.calibrated_action_field_identity
                    and form.motor_id == demonstration.motor_id
                )
            )
            if len(matching) != 1:
                raise ValueError(
                    "W1 demonstration does not resolve a retained form"
                )
            if demonstration.demonstration_id in self._demonstrations:
                return
            if (
                len(self._demonstrations)
                >= self._profile.max_demonstrations
            ):
                raise RuntimeError(
                    "W1 curriculum demonstration capacity exhausted"
                )
            used = {
                source
                for value in self._demonstrations.values()
                for source in (
                    value.action_execution_receipt_sha256,
                    value.action_evidence_receipt_sha256,
                    value.action_settlement_receipt_sha256,
                    value.self_execution_receipt_sha256,
                    value.self_emission_receipt_sha256,
                    value.self_acoustic_receipt_sha256,
                )
            }
            sources = {
                demonstration.action_execution_receipt_sha256,
                demonstration.action_evidence_receipt_sha256,
                demonstration.action_settlement_receipt_sha256,
                demonstration.self_execution_receipt_sha256,
                demonstration.self_emission_receipt_sha256,
                demonstration.self_acoustic_receipt_sha256,
            }
            if used.intersection(sources):
                raise ValueError(
                    "W1 curriculum reuses demonstration evidence"
                )
            candidate = dict(self._demonstrations)
            candidate[demonstration.demonstration_id] = demonstration
            self._encoded(self._calibrations, candidate)
            self._demonstrations = candidate

    def _body(
        self,
        calibrations: Mapping[
            str, W1CrossRegimeVocalCalibration
        ],
        demonstrations: Mapping[
            str, W1ActionVocalDemonstration
        ],
    ) -> dict[str, object]:
        return {
            "calibrations": [
                calibrations[key].record()
                for key in sorted(calibrations)
            ],
            "demonstrations": [
                demonstrations[key].record()
                for key in sorted(demonstrations)
            ],
            "resource_profile": self._profile.record(),
            "schema": W1_EXPERIENCE_CURRICULUM_STATE_SCHEMA,
        }

    def _encoded(
        self,
        calibrations: Mapping[
            str, W1CrossRegimeVocalCalibration
        ],
        demonstrations: Mapping[
            str, W1ActionVocalDemonstration
        ],
    ) -> bytes:
        body = self._body(calibrations, demonstrations)
        encoded = _canonical({
            "body": body,
            "schema": W1_EXPERIENCE_CURRICULUM_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("W1 curriculum state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(
                self._calibrations, self._demonstrations
            )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
        calibration_owner: W1CrossRegimeVocalCalibrationOwner,
        demonstration_owner: W1ActionVocalDemonstrationOwner,
    ) -> "W1ExperienceCurriculumOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("W1 curriculum state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "W1 curriculum state is not canonical JSON"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            != W1_EXPERIENCE_CURRICULUM_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("W1 curriculum state envelope changed")
        body = envelope["body"]
        if (
            set(body)
            != {
                "calibrations",
                "demonstrations",
                "resource_profile",
                "schema",
            }
            or body.get("schema")
            != W1_EXPERIENCE_CURRICULUM_STATE_SCHEMA
            or not isinstance(body.get("calibrations"), list)
            or not isinstance(body.get("demonstrations"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("W1 curriculum state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_calibrations",
            "max_demonstrations",
            "max_state_bytes",
            "profile_id",
            "schema",
        }:
            raise ValueError("W1 curriculum profile record changed")
        profile = W1ExperienceCurriculumResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_calibrations=raw_profile.get("max_calibrations"),
            max_demonstrations=raw_profile.get("max_demonstrations"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
            calibration_owner=calibration_owner,
            demonstration_owner=demonstration_owner,
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError("W1 curriculum state HMAC changed")
        for raw in body["calibrations"]:
            value = _calibration(raw, calibration_owner)
            if value.calibration_id in owner._calibrations:
                raise ValueError(
                    "W1 curriculum calibration is duplicated"
                )
            owner._calibrations[value.calibration_id] = value
        for raw in body["demonstrations"]:
            value = _demonstration(raw, demonstration_owner)
            owner.admit_demonstration(value)
        if (
            len(owner._calibrations) > profile.max_calibrations
            or len(owner._demonstrations) > profile.max_demonstrations
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("W1 curriculum restored state changed")
        return owner

    def acceptance(self) -> W1ExperienceCurriculumAcceptance:
        with self._lock:
            calibrations = tuple(
                self._calibrations[key]
                for key in sorted(self._calibrations)
            )
            demonstrations = tuple(
                self._demonstrations[key]
                for key in sorted(self._demonstrations)
            )
            forms = tuple(
                (calibration, form)
                for calibration in calibrations
                for form in calibration.forms
            )
            demonstrated = {
                (
                    value.calibration_receipt_sha256,
                    value.calibrated_action_field_identity,
                )
                for value in demonstrations
            }
            expected = {
                (
                    calibration.authority_receipt_sha256,
                    form.action_field_identity,
                )
                for calibration, form in forms
            }
            evidence_receipts = tuple(
                value
                for calibration in calibrations
                for value in (
                    *calibration.source_imitation_receipt_sha256s,
                )
            ) + tuple(
                source
                for value in demonstrations
                for source in (
                    value.action_execution_receipt_sha256,
                    value.action_evidence_receipt_sha256,
                    value.action_settlement_receipt_sha256,
                    value.self_execution_receipt_sha256,
                    value.self_emission_receipt_sha256,
                    value.self_acoustic_receipt_sha256,
                )
            )
            disjoint = len(evidence_receipts) == len(
                set(evidence_receipts)
            )
            capacity = (
                len(calibrations) < self._profile.max_calibrations
                and len(demonstrations)
                < self._profile.max_demonstrations
                and len(self.snapshot_encoded())
                < self._profile.max_state_bytes
            )
            conditions = (
                (
                    bool(calibrations),
                    "no_authenticated_cross_regime_calibration",
                ),
                (
                    len(forms) >= 2,
                    "fewer_than_two_calibrated_action_vocal_forms",
                ),
                (
                    all(
                        len(form.positive_imitation_receipt_sha256s)
                        >= 2
                        for _calibration_value, form in forms
                    ),
                    "a_form_lacks_two_external_and_two_self_hearings",
                ),
                (
                    len({form.motor_id for _, form in forms})
                    == len(forms),
                    "calibrated_forms_do_not_have_distinct_motors",
                ),
                (
                    expected == demonstrated,
                    "not_every_calibrated_form_has_a_fresh_demonstration",
                ),
                (
                    disjoint,
                    "curriculum_evidence_receipts_are_reused",
                ),
                (
                    capacity,
                    "curriculum_growth_capacity_is_exhausted",
                ),
            )
            failures = tuple(
                reason
                for accepted, reason in conditions
                if not accepted
            )
            provisional = W1ExperienceCurriculumAcceptance(
                state=(
                    "authenticated_w1_action_vocal_plumbing_ready"
                    if not failures
                    else "not_ready"
                ),
                developmental_equivalence=(
                    "not_claimed_no_validated_human_age_mapping"
                ),
                calibration_count=len(calibrations),
                calibrated_form_count=len(forms),
                external_hearing_count=sum(
                    len(form.positive_imitation_receipt_sha256s)
                    for _, form in forms
                ),
                self_hearing_count=sum(
                    len(form.positive_imitation_receipt_sha256s)
                    for _, form in forms
                ),
                distinct_motor_count=len({
                    form.motor_id for _, form in forms
                }),
                demonstration_count=len(demonstrations),
                demonstrated_form_count=len(
                    expected.intersection(demonstrated)
                ),
                evidence_receipts_disjoint=disjoint,
                capacity_available=capacity,
                unsatisfied_conditions=failures,
                retained_calibration_receipt_sha256s=tuple(
                    value.authority_receipt_sha256
                    for value in calibrations
                ),
                retained_demonstration_receipt_sha256s=tuple(
                    value.authority_receipt_sha256
                    for value in demonstrations
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            payload = provisional.payload()
            signature = hmac.new(
                self._acceptance_key,
                _ACCEPTANCE_DOMAIN + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            return W1ExperienceCurriculumAcceptance(
                state=provisional.state,
                developmental_equivalence=(
                    provisional.developmental_equivalence
                ),
                calibration_count=provisional.calibration_count,
                calibrated_form_count=(
                    provisional.calibrated_form_count
                ),
                external_hearing_count=(
                    provisional.external_hearing_count
                ),
                self_hearing_count=provisional.self_hearing_count,
                distinct_motor_count=provisional.distinct_motor_count,
                demonstration_count=provisional.demonstration_count,
                demonstrated_form_count=(
                    provisional.demonstrated_form_count
                ),
                evidence_receipts_disjoint=(
                    provisional.evidence_receipts_disjoint
                ),
                capacity_available=provisional.capacity_available,
                unsatisfied_conditions=(
                    provisional.unsatisfied_conditions
                ),
                retained_calibration_receipt_sha256s=(
                    provisional.retained_calibration_receipt_sha256s
                ),
                retained_demonstration_receipt_sha256s=(
                    provisional.retained_demonstration_receipt_sha256s
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
            )

    def verify_acceptance(
        self,
        acceptance: W1ExperienceCurriculumAcceptance,
    ) -> None:
        if not isinstance(
            acceptance, W1ExperienceCurriculumAcceptance
        ):
            raise TypeError("W1 curriculum acceptance is not typed")
        for value, name in (
            (
                acceptance.authority_hmac_sha256,
                "W1 curriculum acceptance HMAC",
            ),
            (
                acceptance.authority_receipt_sha256,
                "W1 curriculum acceptance authority",
            ),
        ):
            _sha256(value, name)
        for value in (
            *acceptance.retained_calibration_receipt_sha256s,
            *acceptance.retained_demonstration_receipt_sha256s,
        ):
            _sha256(value, "W1 curriculum retained evidence")
        payload = acceptance.payload()
        signature = hmac.new(
            self._acceptance_key,
            _ACCEPTANCE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature, acceptance.authority_hmac_sha256
            )
            or acceptance.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
            or acceptance != self.acceptance()
        ):
            raise ValueError("W1 curriculum acceptance authority changed")

    @property
    def calibrations(
        self,
    ) -> tuple[W1CrossRegimeVocalCalibration, ...]:
        with self._lock:
            return tuple(
                self._calibrations[key]
                for key in sorted(self._calibrations)
            )

    @property
    def demonstrations(
        self,
    ) -> tuple[W1ActionVocalDemonstration, ...]:
        with self._lock:
            return tuple(
                self._demonstrations[key]
                for key in sorted(self._demonstrations)
            )

    def status(self) -> dict[str, object]:
        acceptance = self.acceptance()
        with self._lock:
            state_bytes = len(
                self._encoded(
                    self._calibrations,
                    self._demonstrations,
                )
            )
            return {
                "acceptance_authority_receipt_sha256": (
                    acceptance.authority_receipt_sha256
                ),
                "acceptance_state": acceptance.state,
                "calibration_capacity": (
                    self._profile.max_calibrations
                ),
                "calibration_count": len(self._calibrations),
                "demonstration_capacity": (
                    self._profile.max_demonstrations
                ),
                "demonstration_count": len(self._demonstrations),
                "developmental_equivalence": (
                    acceptance.developmental_equivalence
                ),
                "state_bytes": state_bytes,
                "state_capacity_bytes": self._profile.max_state_bytes,
                "state_bytes_remaining": (
                    self._profile.max_state_bytes - state_bytes
                ),
                "unsatisfied_conditions": (
                    acceptance.unsatisfied_conditions
                ),
            }


__all__ = [
    "W1ExperienceCurriculumAcceptance",
    "W1ExperienceCurriculumOwner",
    "W1ExperienceCurriculumResourceProfile",
]
