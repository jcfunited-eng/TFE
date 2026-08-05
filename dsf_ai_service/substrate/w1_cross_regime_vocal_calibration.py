"""Exact external-to-self W1 vocal-form calibration.

Each physical action-field alternative must have at least two source-disjoint
external hearings and two source-disjoint self hearings, carried by exact
imitation episodes.  Each alternative must also retain one distinct,
physically admitted motor exemplar.

The cross-regime diagnostic is the intersection of every episode's exact
external/self q-cell intersection minus the union of all alternative-form
cells.  Empty or overlapping diagnostics are rejected.  No label, intended
word, transcript, threshold, score, or approximate similarity is admitted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.w1_binaural_controlled_distinction import (
    W1DiagnosticCell,
)
from dsf_ai_service.substrate.w1_external_self_imitation import (
    W1ExternalSelfImitation,
    W1ExternalSelfImitationAuthority,
)


W1_CROSS_REGIME_CALIBRATION_PROFILE_SCHEMA = (
    "guala.w1.cross_regime_vocal_calibration.profile.v1"
)
W1_CROSS_REGIME_CALIBRATION_SCHEMA = (
    "guala.w1.cross_regime_vocal_calibration.v1"
)
_CALIBRATION_DOMAIN = (
    b"guala-w1-cross-regime-vocal-calibration-v1\0"
)
_HEX = frozenset("0123456789abcdef")
_MINIMUM_HEARINGS_PER_REGIME = 2


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
        raise TypeError("W1 vocal calibration key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 vocal calibration key changed")
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


def _action_identity(
    roots: tuple[GroundingRoot, ...],
) -> str:
    return _digest({
        "complete_dynamic_action_roots": [
            [root.root_id, root.value_sha256]
            for root in roots
        ]
    })


@dataclass(frozen=True, slots=True)
class W1CrossRegimeCalibrationResourceProfile:
    profile_id: str
    max_calibrations: int
    max_imitation_episodes_per_calibration: int
    max_forms_per_calibration: int
    max_roots_per_form: int
    max_diagnostic_cells_per_form: int
    max_calibration_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_calibrations: int,
        max_imitation_episodes_per_calibration: int,
        max_forms_per_calibration: int,
        max_roots_per_form: int,
        max_diagnostic_cells_per_form: int,
        max_calibration_bytes: int,
    ) -> "W1CrossRegimeCalibrationResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("W1 vocal calibration profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_calibrations=_positive(
                max_calibrations, "W1 vocal calibration capacity"
            ),
            max_imitation_episodes_per_calibration=_positive(
                max_imitation_episodes_per_calibration,
                "W1 calibration imitation capacity",
            ),
            max_forms_per_calibration=_positive(
                max_forms_per_calibration,
                "W1 calibration form capacity",
            ),
            max_roots_per_form=_positive(
                max_roots_per_form,
                "W1 calibration root capacity",
            ),
            max_diagnostic_cells_per_form=_positive(
                max_diagnostic_cells_per_form,
                "W1 calibration diagnostic capacity",
            ),
            max_calibration_bytes=_positive(
                max_calibration_bytes,
                "W1 calibration byte capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_calibrations=provisional.max_calibrations,
            max_imitation_episodes_per_calibration=(
                provisional.max_imitation_episodes_per_calibration
            ),
            max_forms_per_calibration=(
                provisional.max_forms_per_calibration
            ),
            max_roots_per_form=provisional.max_roots_per_form,
            max_diagnostic_cells_per_form=(
                provisional.max_diagnostic_cells_per_form
            ),
            max_calibration_bytes=provisional.max_calibration_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_calibration_bytes": self.max_calibration_bytes,
            "max_calibrations": self.max_calibrations,
            "max_diagnostic_cells_per_form": (
                self.max_diagnostic_cells_per_form
            ),
            "max_forms_per_calibration": (
                self.max_forms_per_calibration
            ),
            "max_imitation_episodes_per_calibration": (
                self.max_imitation_episodes_per_calibration
            ),
            "max_roots_per_form": self.max_roots_per_form,
            "profile_id": self.profile_id,
            "schema": W1_CROSS_REGIME_CALIBRATION_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        for value, name in (
            (self.max_calibrations, "W1 vocal calibration capacity"),
            (
                self.max_imitation_episodes_per_calibration,
                "W1 calibration imitation capacity",
            ),
            (
                self.max_forms_per_calibration,
                "W1 calibration form capacity",
            ),
            (self.max_roots_per_form, "W1 calibration root capacity"),
            (
                self.max_diagnostic_cells_per_form,
                "W1 calibration diagnostic capacity",
            ),
            (
                self.max_calibration_bytes,
                "W1 calibration byte capacity",
            ),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "W1 vocal calibration profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError(
                "W1 vocal calibration profile authority changed"
            )


@dataclass(frozen=True, slots=True)
class W1CalibratedVocalForm:
    action_roots: tuple[GroundingRoot, ...]
    motor_id: str
    diagnostic_cells: tuple[W1DiagnosticCell, ...]
    positive_imitation_receipt_sha256s: tuple[str, ...]

    @property
    def action_field_identity(self) -> str:
        return _action_identity(self.action_roots)

    def record(self) -> dict[str, object]:
        return {
            "action_field_identity": self.action_field_identity,
            "action_roots": [
                value.as_record() for value in self.action_roots
            ],
            "diagnostic_cells": [
                value.record() for value in self.diagnostic_cells
            ],
            "motor_id": self.motor_id,
            "positive_imitation_receipt_sha256s": list(
                self.positive_imitation_receipt_sha256s
            ),
        }


@dataclass(frozen=True, slots=True)
class W1CrossRegimeVocalCalibration:
    calibration_id: str
    controlled_before_world_state_sha256: str
    forms: tuple[W1CalibratedVocalForm, ...]
    source_imitation_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "controlled_before_world_state_sha256": (
                self.controlled_before_world_state_sha256
            ),
            "forms": [value.record() for value in self.forms],
            "schema": W1_CROSS_REGIME_CALIBRATION_SCHEMA,
            "source_imitation_receipt_sha256s": list(
                self.source_imitation_receipt_sha256s
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "calibration_id": self.calibration_id,
        }


class W1CrossRegimeVocalCalibrationOwner:
    """Bounded exact owner of externally grounded self-producible forms."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1CrossRegimeCalibrationResourceProfile,
        imitation_authority: W1ExternalSelfImitationAuthority,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(
            imitation_authority, W1ExternalSelfImitationAuthority
        ):
            raise TypeError("W1 calibration requires imitation authority")
        if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
            raise TypeError("W1 calibration requires motor authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._calibration_key = hashlib.sha256(
            _CALIBRATION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._imitation = imitation_authority
        self._motor = motor_owner
        self._calibrations: dict[
            str, W1CrossRegimeVocalCalibration
        ] = {}
        self._lock = threading.RLock()

    def _verify_form(self, form: W1CalibratedVocalForm) -> None:
        _sha256(form.motor_id, "W1 calibrated motor")
        if (
            not form.action_roots
            or len(form.action_roots)
            > self._profile.max_roots_per_form
            or not form.diagnostic_cells
            or len(form.diagnostic_cells)
            > self._profile.max_diagnostic_cells_per_form
            or form.diagnostic_cells
            != tuple(sorted(set(form.diagnostic_cells)))
            or len(form.positive_imitation_receipt_sha256s)
            < _MINIMUM_HEARINGS_PER_REGIME
            or form.positive_imitation_receipt_sha256s
            != tuple(sorted(set(
                form.positive_imitation_receipt_sha256s
            )))
        ):
            raise ValueError("W1 calibrated vocal form changed")
        for root in form.action_roots:
            root.verify()
        for cell in form.diagnostic_cells:
            cell.verify()
        for receipt in form.positive_imitation_receipt_sha256s:
            _sha256(receipt, "W1 positive imitation")

    def verify(
        self,
        calibration: W1CrossRegimeVocalCalibration,
    ) -> None:
        if not isinstance(
            calibration, W1CrossRegimeVocalCalibration
        ):
            raise TypeError("W1 vocal calibration is not typed")
        for value, name in (
            (calibration.calibration_id, "W1 vocal calibration"),
            (
                calibration.controlled_before_world_state_sha256,
                "W1 vocal calibration controlled world",
            ),
            (
                calibration.authority_hmac_sha256,
                "W1 vocal calibration HMAC",
            ),
            (
                calibration.authority_receipt_sha256,
                "W1 vocal calibration authority",
            ),
        ):
            _sha256(value, name)
        if (
            not 2
            <= len(calibration.forms)
            <= self._profile.max_forms_per_calibration
            or calibration.forms
            != tuple(sorted(
                calibration.forms,
                key=lambda value: value.action_field_identity,
            ))
            or calibration.source_imitation_receipt_sha256s
            != tuple(sorted(set(
                calibration.source_imitation_receipt_sha256s
            )))
            or len(calibration.source_imitation_receipt_sha256s)
            > self._profile.max_imitation_episodes_per_calibration
        ):
            raise ValueError("W1 vocal calibration changed")
        used_episodes: set[str] = set()
        used_motors: set[str] = set()
        used_cells: set[W1DiagnosticCell] = set()
        retained_motors = {
            value.motor_id for value in self._motor.exemplars
        }
        for form in calibration.forms:
            self._verify_form(form)
            if (
                form.motor_id not in retained_motors
                or form.motor_id in used_motors
                or used_episodes.intersection(
                    form.positive_imitation_receipt_sha256s
                )
                or used_cells.intersection(form.diagnostic_cells)
            ):
                raise ValueError(
                    "W1 calibration forms are not independent"
                )
            used_motors.add(form.motor_id)
            used_episodes.update(
                form.positive_imitation_receipt_sha256s
            )
            used_cells.update(form.diagnostic_cells)
        if used_episodes != set(
            calibration.source_imitation_receipt_sha256s
        ):
            raise ValueError("W1 calibration lost imitation episodes")
        payload = calibration.payload()
        signature = hmac.new(
            self._calibration_key,
            _CALIBRATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            calibration.calibration_id != _digest(payload)
            or len(_canonical(payload))
            > self._profile.max_calibration_bytes
            or not hmac.compare_digest(
                signature, calibration.authority_hmac_sha256
            )
            or calibration.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 vocal calibration authority changed")

    def calibrate(
        self,
        episodes: tuple[W1ExternalSelfImitation, ...],
    ) -> W1CrossRegimeVocalCalibration:
        if (
            not isinstance(episodes, tuple)
            or not episodes
            or len(episodes)
            > self._profile.max_imitation_episodes_per_calibration
        ):
            raise ValueError("W1 calibration episode boundary changed")
        for episode in episodes:
            self._imitation.verify(episode)
        sources = tuple(sorted(
            episode.authority_receipt_sha256 for episode in episodes
        ))
        if len(sources) != len(set(sources)):
            raise ValueError(
                "W1 calibration requires source-disjoint imitations"
            )
        physical_sources = tuple(
            source
            for episode in episodes
            for source in (
                episode.lesson_receipt_sha256,
                episode.external_execution_receipt_sha256,
                episode.self_execution_receipt_sha256,
                episode.self_emission_receipt_sha256,
                episode.self_acoustic_receipt_sha256,
            )
        )
        if len(physical_sources) != len(set(physical_sources)):
            raise ValueError(
                "W1 calibration reuses an underlying physical source"
            )
        controlled = {
            value.action_before_world_state_sha256
            for value in episodes
        }
        if len(controlled) != 1:
            raise ValueError(
                "W1 calibration controlled world changed"
            )
        controlled_before = controlled.pop()
        groups: dict[str, list[W1ExternalSelfImitation]] = {}
        for episode in episodes:
            groups.setdefault(
                _action_identity(episode.action_roots), []
            ).append(episode)
        if (
            not 2
            <= len(groups)
            <= self._profile.max_forms_per_calibration
            or any(
                len(values) < _MINIMUM_HEARINGS_PER_REGIME
                for values in groups.values()
            )
        ):
            raise ValueError(
                "W1 calibration requires two external and two self "
                "hearings per form"
            )
        all_cells = {
            identity: tuple(
                frozenset(episode.cross_regime_cells)
                for episode in values
            )
            for identity, values in groups.items()
        }
        forms = []
        for identity in sorted(groups):
            values = groups[identity]
            motors = {value.motor_id for value in values}
            if len(motors) != 1:
                raise ValueError(
                    "W1 form requires one exact motor exemplar"
                )
            positive = set(all_cells[identity][0])
            for cells in all_cells[identity][1:]:
                positive.intersection_update(cells)
            contrasts: set[W1DiagnosticCell] = set()
            for other_identity, cell_sets in all_cells.items():
                if other_identity == identity:
                    continue
                for cells in cell_sets:
                    contrasts.update(cells)
            diagnostic = tuple(sorted(
                positive.difference(contrasts)
            ))
            if not diagnostic:
                raise ValueError(
                    "W1 cross-regime diagnostic conjunction is empty"
                )
            forms.append(W1CalibratedVocalForm(
                action_roots=values[0].action_roots,
                motor_id=motors.pop(),
                diagnostic_cells=diagnostic,
                positive_imitation_receipt_sha256s=tuple(sorted(
                    value.authority_receipt_sha256
                    for value in values
                )),
            ))
        provisional = W1CrossRegimeVocalCalibration(
            calibration_id="0" * 64,
            controlled_before_world_state_sha256=controlled_before,
            forms=tuple(forms),
            source_imitation_receipt_sha256s=sources,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._calibration_key,
            _CALIBRATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1CrossRegimeVocalCalibration(
            calibration_id=_digest(payload),
            controlled_before_world_state_sha256=controlled_before,
            forms=provisional.forms,
            source_imitation_receipt_sha256s=sources,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result)
        with self._lock:
            existing = self._calibrations.get(result.calibration_id)
            if existing is not None:
                return existing
            if (
                len(self._calibrations)
                >= self._profile.max_calibrations
            ):
                raise RuntimeError("W1 calibration capacity exhausted")
            self._calibrations[result.calibration_id] = result
        return result

    def resolve_self_cells(
        self,
        *,
        calibration: W1CrossRegimeVocalCalibration,
        active_cells: frozenset[W1DiagnosticCell],
    ) -> W1CalibratedVocalForm:
        self.verify(calibration)
        for cell in active_cells:
            cell.verify()
        matches = tuple(
            form
            for form in calibration.forms
            if set(form.diagnostic_cells).issubset(active_cells)
        )
        if len(matches) != 1:
            raise ValueError(
                "W1 self vocal form is incomplete or ambiguous"
            )
        return matches[0]

    def status(self) -> dict[str, int]:
        with self._lock:
            return {
                "calibrations": len(self._calibrations),
                "forms": sum(
                    len(value.forms)
                    for value in self._calibrations.values()
                ),
            }


__all__ = [
    "W1CalibratedVocalForm",
    "W1CrossRegimeCalibrationResourceProfile",
    "W1CrossRegimeVocalCalibration",
    "W1CrossRegimeVocalCalibrationOwner",
]
