"""Authenticated bounded self-vocal PCM motor exemplars.

The motor stores replayable physical pressure, never text.  An exemplar is
admitted only when its exact PCM16 bytes reproduce the mounted auditory
receptor capture and fire verified recurrent motif neurons.  Execution uses
the canonical W1 self-body ``VocalizeCommand``.  A release is complete only
after the emitted bytes are transduced again and reproduce the exemplar's
exact motif co-firing set.

Motor identity is the PCM digest and sample extent.  Motif firing is retained
as sensory validation, not semantic identity.  State is fixed-capacity,
canonical, HMAC-authenticated, and never silently evicts an exemplar.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import struct
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

import numpy as np

from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorEventState,
    AuditoryReceptorFullFieldEvent,
    _capture_payload,
    settle_auditory_receptor_event,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifObservationState,
    AuditoryReceptorExperience,
    AuditoryRecurrentMotifOwner,
    receptor_experience_from_full_field_event,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    MIN_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    transduce_auditory_full_field,
)


SELF_VOCAL_PROFILE_SCHEMA = "guala.self_vocal_pcm.profile.v1"
SELF_VOCAL_EXEMPLAR_SCHEMA = "guala.self_vocal_pcm.exemplar.v1"
SELF_VOCAL_EMISSION_SCHEMA = "guala.self_vocal_pcm.emission.v1"
SELF_VOCAL_HEARING_SCHEMA = "guala.self_vocal_pcm.hearing.v1"
SELF_VOCAL_STATE_SCHEMA = "guala.self_vocal_pcm.state.v1"
SELF_VOCAL_ENVELOPE_SCHEMA = "guala.self_vocal_pcm.state_hmac.v1"

_EXEMPLAR_DOMAIN = b"guala-self-vocal-pcm-exemplar-v1\0"
_EMISSION_DOMAIN = b"guala-self-vocal-pcm-emission-v1\0"
_HEARING_DOMAIN = b"guala-self-vocal-pcm-hearing-v1\0"
_STATE_DOMAIN = b"guala-self-vocal-pcm-state-v1\0"
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
    elif isinstance(value, bytes):
        result = value
    else:
        raise TypeError("self-vocal authority key must be bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError("self-vocal authority key has an invalid boundary")
    return result


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(key, domain + _canonical(value), hashlib.sha256).hexdigest()


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _pcm_sample_count(value: bytes) -> int:
    if not isinstance(value, bytes) or len(value) % 2:
        raise ValueError("self-vocal pressure must be immutable PCM16 bytes")
    count = len(value) // 2
    if (
        not MIN_VOCAL_SAMPLE_COUNT <= count <= MAX_VOCAL_SAMPLE_COUNT
        or count % OBSERVATION_HOP_SAMPLES
    ):
        raise ValueError("self-vocal pressure left its physical sample boundary")
    tuple(struct.iter_unpack("<h", value))
    return count


def _exact_capture_receipt(pcm_s16le: bytes) -> str:
    capture = transduce_auditory_full_field(
        np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float64)
        / 32768.0,
        sample_rate_hz=VOCAL_SAMPLE_RATE_HZ,
    )
    return receipt_sha256(_capture_payload(capture))


def _verified_firing(
    motif_owner: AuditoryRecurrentMotifOwner,
    experience: AuditoryReceptorExperience,
):
    if not isinstance(motif_owner, AuditoryRecurrentMotifOwner):
        raise TypeError("self-vocal motor requires the recurrent motif owner")
    if not isinstance(experience, AuditoryReceptorExperience):
        raise TypeError("self-vocal motor requires a receptor experience")
    experience.verify()
    before = motif_owner.snapshot_encoded()
    firing = motif_owner.fire(experience)
    after = motif_owner.snapshot_encoded()
    if before != after:
        raise RuntimeError("motif bank changed during self-vocal verification")
    if firing.state is not AuditoryMotifObservationState.OBSERVED:
        raise RuntimeError(firing.reason)
    neurons = {
        value.neuron_id: value for value in motif_owner.motif_neurons
    }
    for activation in firing.activations:
        neuron = neurons.get(activation.neuron_id)
        if neuron is None:
            raise ValueError("self-vocal activation names an absent motif")
        activation.verify(neuron, experience)
    if (
        tuple(sorted(set(firing.firing_motif_neuron_ids)))
        != firing.firing_motif_neuron_ids
        or {value.neuron_id for value in firing.activations}
        != set(firing.firing_motif_neuron_ids)
    ):
        raise ValueError("self-vocal firing lost activation authority")
    return firing, hashlib.sha256(before).hexdigest()


@dataclass(frozen=True, slots=True)
class SelfVocalMotorResourceProfile:
    profile_id: str
    max_exemplars: int
    max_total_pcm_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_exemplars: int,
        max_total_pcm_bytes: int,
        max_state_bytes: int,
    ) -> "SelfVocalMotorResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("self-vocal profile identifier is invalid")
        provisional = cls(
            profile_id=profile_id,
            max_exemplars=_positive(
                max_exemplars, "self-vocal exemplar capacity"
            ),
            max_total_pcm_bytes=_positive(
                max_total_pcm_bytes, "self-vocal PCM capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "self-vocal state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        if provisional.max_state_bytes < provisional.max_total_pcm_bytes:
            raise ValueError(
                "self-vocal state cannot be smaller than its PCM allocation"
            )
        return cls(
            profile_id=provisional.profile_id,
            max_exemplars=provisional.max_exemplars,
            max_total_pcm_bytes=provisional.max_total_pcm_bytes,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_exemplars": self.max_exemplars,
            "max_state_bytes": self.max_state_bytes,
            "max_total_pcm_bytes": self.max_total_pcm_bytes,
            "profile_id": self.profile_id,
            "schema": SELF_VOCAL_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _positive(self.max_exemplars, "self-vocal exemplar capacity")
        _positive(self.max_total_pcm_bytes, "self-vocal PCM capacity")
        _positive(self.max_state_bytes, "self-vocal state capacity")
        _sha256(
            self.authority_receipt_sha256,
            "self-vocal profile authority",
        )
        if (
            self.max_state_bytes < self.max_total_pcm_bytes
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError("self-vocal resource profile changed")


@dataclass(frozen=True, slots=True)
class SelfVocalPCMExemplar:
    motor_id: str
    pcm_sha256: str
    sample_count: int
    pcm_s16le: bytes
    capture_receipt_sha256: str
    receptor_event_receipt_sha256: str
    receptor_experience_receipt_sha256: str
    motif_bank_state_sha256: str
    firing_motif_neuron_ids: tuple[str, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "firing_motif_neuron_ids": list(
                self.firing_motif_neuron_ids
            ),
            "motif_bank_state_sha256": self.motif_bank_state_sha256,
            "pcm_base64": base64.b64encode(self.pcm_s16le).decode("ascii"),
            "pcm_sha256": self.pcm_sha256,
            "capture_receipt_sha256": self.capture_receipt_sha256,
            "receptor_event_receipt_sha256": (
                self.receptor_event_receipt_sha256
            ),
            "receptor_experience_receipt_sha256": (
                self.receptor_experience_receipt_sha256
            ),
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": SELF_VOCAL_EXEMPLAR_SCHEMA,
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.motor_id, "self-vocal motor"),
            (self.pcm_sha256, "self-vocal PCM"),
            (
                self.capture_receipt_sha256,
                "self-vocal capture",
            ),
            (
                self.receptor_event_receipt_sha256,
                "self-vocal receptor event",
            ),
            (
                self.receptor_experience_receipt_sha256,
                "self-vocal receptor experience",
            ),
            (self.motif_bank_state_sha256, "self-vocal motif bank"),
        ):
            _sha256(value, name)
        if (
            _pcm_sample_count(self.pcm_s16le) != self.sample_count
            or hashlib.sha256(self.pcm_s16le).hexdigest()
            != self.pcm_sha256
            or _exact_capture_receipt(self.pcm_s16le)
            != self.capture_receipt_sha256
            or not self.firing_motif_neuron_ids
            or tuple(sorted(set(self.firing_motif_neuron_ids)))
            != self.firing_motif_neuron_ids
        ):
            raise ValueError("self-vocal exemplar changed physical evidence")
        for value in self.firing_motif_neuron_ids:
            _sha256(value, "self-vocal firing motif")
        expected_motor = _digest({
            "pcm_sha256": self.pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
        })
        if (
            self.motor_id != expected_motor
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(key, _EXEMPLAR_DOMAIN, self.payload()),
            )
        ):
            raise ValueError("self-vocal exemplar authority changed")

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "motor_id": self.motor_id,
        }


@dataclass(frozen=True, slots=True)
class SelfVocalEmissionReceipt:
    motor_id: str
    pcm_sha256: str
    sample_count: int
    self_port_id: str
    self_body_id: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    command_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "command_sha256": self.command_sha256,
            "motor_id": self.motor_id,
            "pcm_sha256": self.pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": SELF_VOCAL_EMISSION_SCHEMA,
            "self_body_id": self.self_body_id,
            "self_port_id": self.self_port_id,
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.motor_id, "self-vocal emission motor"),
            (self.pcm_sha256, "self-vocal emission PCM"),
            (self.world_before_receipt_sha256, "self-vocal world before"),
            (self.world_after_receipt_sha256, "self-vocal world after"),
            (
                self.world_execution_receipt_sha256,
                "self-vocal world execution",
            ),
            (self.command_sha256, "self-vocal command"),
            (self.authority_receipt_sha256, "self-vocal emission"),
        ):
            _sha256(value, name)
        if (
            self.self_port_id != PORT_ID
            or not isinstance(self.self_body_id, str)
            or not self.self_body_id
            or not MIN_VOCAL_SAMPLE_COUNT
            <= self.sample_count
            <= MAX_VOCAL_SAMPLE_COUNT
        ):
            raise ValueError("self-vocal emission left the self body")
        signature = _sign(key, _EMISSION_DOMAIN, self.payload())
        if (
            not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })
        ):
            raise ValueError("self-vocal emission authority changed")


@dataclass(frozen=True, slots=True)
class PreparedSelfVocalEmission:
    exemplar: SelfVocalPCMExemplar
    pcm_s16le: bytes
    execution_receipt: ActionExecutionReceipt
    emission_receipt: SelfVocalEmissionReceipt


@dataclass(frozen=True, slots=True)
class SelfVocalHearingReceipt:
    motor_id: str
    emission_receipt_sha256: str
    receptor_event_receipt_sha256: str
    receptor_experience_receipt_sha256: str
    firing_motif_neuron_ids: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "emission_receipt_sha256": self.emission_receipt_sha256,
            "firing_motif_neuron_ids": list(
                self.firing_motif_neuron_ids
            ),
            "motor_id": self.motor_id,
            "receptor_event_receipt_sha256": (
                self.receptor_event_receipt_sha256
            ),
            "receptor_experience_receipt_sha256": (
                self.receptor_experience_receipt_sha256
            ),
            "schema": SELF_VOCAL_HEARING_SCHEMA,
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.motor_id, "self-heard motor"),
            (self.emission_receipt_sha256, "self-heard emission"),
            (self.receptor_event_receipt_sha256, "self-heard event"),
            (
                self.receptor_experience_receipt_sha256,
                "self-heard experience",
            ),
            (self.authority_receipt_sha256, "self-hearing authority"),
        ):
            _sha256(value, name)
        if (
            not self.firing_motif_neuron_ids
            or tuple(sorted(set(self.firing_motif_neuron_ids)))
            != self.firing_motif_neuron_ids
        ):
            raise ValueError("self-hearing lost motif activation")
        signature = _sign(key, _HEARING_DOMAIN, self.payload())
        if (
            not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })
        ):
            raise ValueError("self-hearing authority changed")

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class SelfVocalPCMMotorOwner:
    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: SelfVocalMotorResourceProfile,
    ) -> None:
        if not isinstance(resource_profile, SelfVocalMotorResourceProfile):
            raise TypeError("self-vocal motor requires a resource profile")
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._exemplar_key = hashlib.sha256(
            _EXEMPLAR_DOMAIN + root
        ).digest()
        self._emission_key = hashlib.sha256(
            _EMISSION_DOMAIN + root
        ).digest()
        self._hearing_key = hashlib.sha256(
            _HEARING_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._exemplars: dict[str, SelfVocalPCMExemplar] = {}
        self._lock = threading.RLock()

    @property
    def exemplars(self) -> tuple[SelfVocalPCMExemplar, ...]:
        with self._lock:
            return tuple(
                self._exemplars[key] for key in sorted(self._exemplars)
            )

    def verify_exemplar(self, exemplar: SelfVocalPCMExemplar) -> None:
        if not isinstance(exemplar, SelfVocalPCMExemplar):
            raise TypeError("self-vocal exemplar has the wrong type")
        exemplar.verify(self._exemplar_key)
        with self._lock:
            if self._exemplars.get(exemplar.motor_id) != exemplar:
                raise ValueError("self-vocal exemplar is not owned")

    def verify_hearing(self, hearing: SelfVocalHearingReceipt) -> None:
        if not isinstance(hearing, SelfVocalHearingReceipt):
            raise TypeError("self-hearing receipt has the wrong type")
        hearing.verify(self._hearing_key)
        with self._lock:
            exemplar = self._exemplars.get(hearing.motor_id)
        if (
            exemplar is None
            or exemplar.firing_motif_neuron_ids
            != hearing.firing_motif_neuron_ids
        ):
            raise ValueError("self-hearing is not owned by its motor exemplar")

    def verify_emission(
        self,
        emission: PreparedSelfVocalEmission,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Verify one applied self-body emission for a physical renderer."""

        if not isinstance(emission, PreparedSelfVocalEmission):
            raise TypeError("prepared self-vocal emission is required")
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("self-vocal emission requires W1 world authority")
        self.verify_exemplar(emission.exemplar)
        emission.emission_receipt.verify(self._emission_key)
        world_authority.verify_execution_receipt(
            emission.execution_receipt
        )
        receipt = emission.emission_receipt
        execution = emission.execution_receipt
        if (
            emission.pcm_s16le != emission.exemplar.pcm_s16le
            or receipt.motor_id != emission.exemplar.motor_id
            or receipt.pcm_sha256 != emission.exemplar.pcm_sha256
            or receipt.sample_count != emission.exemplar.sample_count
            or receipt.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or receipt.world_before_receipt_sha256
            != execution.before.authority_receipt_sha256
            or receipt.world_after_receipt_sha256
            != execution.after.authority_receipt_sha256
            or receipt.self_body_id != execution.actor_body_id
            or receipt.self_body_id != execution.after.self_body_id
            or receipt.self_port_id != execution.port_id
            or receipt.command_sha256 != execution.command_sha256
            or execution.disposition != "applied"
        ):
            raise ValueError(
                "prepared self-vocal emission changed physical authority"
            )

    def cross_validate_restored(
        self,
        *,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> None:
        """Rerun every retained motor through frozen hearing after restore."""

        for exemplar in self.exemplars:
            exemplar.verify(self._exemplar_key)
            capture = transduce_auditory_full_field(
                np.frombuffer(
                    exemplar.pcm_s16le, dtype="<i2"
                ).astype(np.float64)
                / 32768.0,
                sample_rate_hz=VOCAL_SAMPLE_RATE_HZ,
            )
            if receipt_sha256(
                _capture_payload(capture)
            ) != exemplar.capture_receipt_sha256:
                raise ValueError(
                    "restored self-vocal PCM changed receptor capture"
                )
            components = auditory_kernel_component_inputs(
                capture,
                source_anchor=Fraction(0),
            )
            built = build_transaction_owned_six_sense_full_field(
                assembly_id=(
                    f"self-vocal-cold-validation-{exemplar.motor_id}"
                ),
                source_time_start=Fraction(0),
                source_time_end=Fraction(
                    capture.input_sample_count,
                    VOCAL_SAMPLE_RATE_HZ,
                ),
                observed_substreams={
                    PhysicalSense.SOUND: components
                },
                states={
                    sense: (
                        SenseBoundaryState.OBSERVED
                        if sense is PhysicalSense.SOUND
                        else SenseBoundaryState.SENSOR_UNAVAILABLE
                    )
                    for sense in SENSE_ORDER
                },
                # Every cochlear kernel component re-hears the one retained
                # self-vocal motor emission: one joint acoustic occurrence.
                occurrences=declare_joint_source_occurrences(
                    observed_substreams={
                        PhysicalSense.SOUND: components
                    },
                    declared_units=(
                        tuple(
                            (PhysicalSense.SOUND, port.topology_index)
                            for port in components
                        ),
                    ),
                ),
            )
            auditory_l5 = AuditoryL5Owner(
                log_event=lambda *_args, **_kwargs: None
            ).settle(built, event_boundary="utterance")
            if auditory_l5 is None:
                raise ValueError(
                    "restored self-vocal PCM did not settle auditory L5"
                )
            boundary = settle_auditory_receptor_event(
                capture=capture,
                auditory_l5=auditory_l5,
            )
            if (
                boundary.state is not AuditoryReceptorEventState.OBSERVED
                or boundary.event is None
            ):
                raise ValueError(
                    "restored self-vocal PCM did not settle receptors"
                )
            experience = receptor_experience_from_full_field_event(
                boundary.event
            )
            firing, _bank_digest = _verified_firing(
                motif_owner, experience
            )
            if firing.firing_motif_neuron_ids != (
                exemplar.firing_motif_neuron_ids
            ):
                raise ValueError(
                    "restored self-vocal PCM changed motif assembly"
                )

    def admit_exemplar(
        self,
        *,
        pcm_s16le: bytes,
        receptor_event: AuditoryReceptorFullFieldEvent,
        receptor_experience: AuditoryReceptorExperience,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> SelfVocalPCMExemplar:
        count = _pcm_sample_count(pcm_s16le)
        if not isinstance(receptor_event, AuditoryReceptorFullFieldEvent):
            raise TypeError("self-vocal exemplar requires a receptor event")
        receptor_event.verify()
        receptor_experience.verify()
        if (
            _exact_capture_receipt(pcm_s16le)
            != receptor_event.capture_receipt_sha256
            or receptor_experience.source_event_receipt_sha256
            != receptor_event.authority_receipt_sha256
        ):
            raise ValueError(
                "self-vocal PCM differs from its receptor experience"
            )
        firing, bank_digest = _verified_firing(
            motif_owner, receptor_experience
        )
        if not firing.firing_motif_neuron_ids:
            raise ValueError("self-vocal exemplar has no recurrent motif")
        pcm_sha = hashlib.sha256(pcm_s16le).hexdigest()
        motor_id = _digest({
            "pcm_sha256": pcm_sha,
            "sample_count": count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
        })
        provisional = SelfVocalPCMExemplar(
            motor_id=motor_id,
            pcm_sha256=pcm_sha,
            sample_count=count,
            pcm_s16le=pcm_s16le,
            capture_receipt_sha256=(
                receptor_event.capture_receipt_sha256
            ),
            receptor_event_receipt_sha256=(
                receptor_event.authority_receipt_sha256
            ),
            receptor_experience_receipt_sha256=(
                receptor_experience.authority_receipt_sha256
            ),
            motif_bank_state_sha256=bank_digest,
            firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
            authority_hmac_sha256="",
        )
        exemplar = SelfVocalPCMExemplar(
            motor_id=provisional.motor_id,
            pcm_sha256=provisional.pcm_sha256,
            sample_count=provisional.sample_count,
            pcm_s16le=provisional.pcm_s16le,
            capture_receipt_sha256=provisional.capture_receipt_sha256,
            receptor_event_receipt_sha256=(
                provisional.receptor_event_receipt_sha256
            ),
            receptor_experience_receipt_sha256=(
                provisional.receptor_experience_receipt_sha256
            ),
            motif_bank_state_sha256=(
                provisional.motif_bank_state_sha256
            ),
            firing_motif_neuron_ids=(
                provisional.firing_motif_neuron_ids
            ),
            authority_hmac_sha256=_sign(
                self._exemplar_key,
                _EXEMPLAR_DOMAIN,
                provisional.payload(),
            ),
        )
        exemplar.verify(self._exemplar_key)
        with self._lock:
            existing = self._exemplars.get(motor_id)
            if existing is not None:
                if existing != exemplar:
                    raise ValueError("self-vocal motor identity conflicted")
                return existing
            if len(self._exemplars) >= self._profile.max_exemplars:
                raise SelfVocalCapacityError(
                    "self-vocal exemplar capacity exhausted"
                )
            if sum(
                len(value.pcm_s16le)
                for value in self._exemplars.values()
            ) + len(pcm_s16le) > self._profile.max_total_pcm_bytes:
                raise SelfVocalCapacityError(
                    "self-vocal PCM capacity exhausted"
                )
            staged = dict(self._exemplars)
            staged[motor_id] = exemplar
            self._encoded(staged)
            self._exemplars = staged
        return exemplar

    def execute(
        self,
        *,
        motor_id: str,
        world_authority: EmbodimentWorldAuthority,
        causal_intent_receipt_sha256: str,
    ) -> PreparedSelfVocalEmission:
        """Execute the retained pressure exemplar through the self body."""

        with self._lock:
            exemplar = self._exemplars.get(motor_id)
        if exemplar is None:
            raise KeyError("self-vocal motor exemplar is unavailable")
        exemplar.verify(self._exemplar_key)
        return self._execute_owned_pressure(
            exemplar=exemplar,
            pcm_s16le=exemplar.pcm_s16le,
            world_authority=world_authority,
            causal_intent_receipt_sha256=(
                causal_intent_receipt_sha256
            ),
        )

    def _execute_owned_pressure(
        self,
        *,
        exemplar: SelfVocalPCMExemplar,
        pcm_s16le: bytes,
        world_authority: EmbodimentWorldAuthority,
        causal_intent_receipt_sha256: str,
    ) -> PreparedSelfVocalEmission:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("self-vocal execution requires W1 world authority")
        _sha256(causal_intent_receipt_sha256, "self-vocal causal intent")
        exemplar.verify(self._exemplar_key)
        if (
            not isinstance(pcm_s16le, bytes)
            or pcm_s16le != exemplar.pcm_s16le
        ):
            raise ValueError(
                "self-vocal pressure differs from learned motor authority"
            )
        motor_id = exemplar.motor_id
        before = world_authority.observation_snapshot()
        if world_authority.port_id != PORT_ID:
            raise ValueError("W1 self vocal port changed")
        epoch = _digest({
            "motor_id": motor_id,
            "world_before_receipt_sha256": before.authority_receipt_sha256,
        })
        command = VocalizeCommand(
            epoch_commitment_sha256=epoch,
            sequence=before.revision,
            source_sample_start=0,
            pcm_sha256=exemplar.pcm_sha256,
            sample_count=exemplar.sample_count,
        )
        command_payload = encode_command(command)
        execution = world_authority.execute_port_command(
            port_id=PORT_ID,
            command_payload=command_payload,
            causal_intent_receipt_sha256=causal_intent_receipt_sha256,
            expected_revision=before.revision,
        )
        world_authority.verify_execution_receipt(execution)
        after = world_authority.observation_snapshot()
        if (
            execution.disposition != "applied"
            or execution.actor_body_id != before.self_body_id
            or execution.port_id != PORT_ID
            or execution.before.authority_receipt_sha256
            != before.authority_receipt_sha256
            or execution.after.authority_receipt_sha256
            != after.authority_receipt_sha256
            or execution.command_sha256
            != hashlib.sha256(command_payload).hexdigest()
        ):
            raise ValueError("self-vocal action was not applied by self body")
        payload = {
            "command_sha256": execution.command_sha256,
            "motor_id": motor_id,
            "pcm_sha256": exemplar.pcm_sha256,
            "sample_count": exemplar.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": SELF_VOCAL_EMISSION_SCHEMA,
            "self_body_id": before.self_body_id,
            "self_port_id": PORT_ID,
            "world_after_receipt_sha256": (
                after.authority_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                before.authority_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                execution.authority_receipt_sha256
            ),
        }
        signature = _sign(
            self._emission_key, _EMISSION_DOMAIN, payload
        )
        receipt = SelfVocalEmissionReceipt(
            motor_id=motor_id,
            pcm_sha256=exemplar.pcm_sha256,
            sample_count=exemplar.sample_count,
            self_port_id=PORT_ID,
            self_body_id=before.self_body_id,
            world_before_receipt_sha256=(
                before.authority_receipt_sha256
            ),
            world_after_receipt_sha256=after.authority_receipt_sha256,
            world_execution_receipt_sha256=(
                execution.authority_receipt_sha256
            ),
            command_sha256=execution.command_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        receipt.verify(self._emission_key)
        return PreparedSelfVocalEmission(
            exemplar=exemplar,
            pcm_s16le=pcm_s16le,
            execution_receipt=execution,
            emission_receipt=receipt,
        )

    def close_self_hearing(
        self,
        *,
        emission: PreparedSelfVocalEmission,
        receptor_event: AuditoryReceptorFullFieldEvent,
        receptor_experience: AuditoryReceptorExperience,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> SelfVocalHearingReceipt:
        if not isinstance(emission, PreparedSelfVocalEmission):
            raise TypeError("self-hearing requires a prepared emission")
        emission.exemplar.verify(self._exemplar_key)
        emission.emission_receipt.verify(self._emission_key)
        if (
            emission.exemplar.motor_id
            != emission.emission_receipt.motor_id
            or emission.pcm_s16le != emission.exemplar.pcm_s16le
            or receptor_event.authority_receipt_sha256
            == emission.exemplar.receptor_event_receipt_sha256
            or receptor_experience.authority_receipt_sha256
            == emission.exemplar.receptor_experience_receipt_sha256
            or _exact_capture_receipt(emission.pcm_s16le)
            != receptor_event.capture_receipt_sha256
            or receptor_experience.source_event_receipt_sha256
            != receptor_event.authority_receipt_sha256
        ):
            raise ValueError("self-heard pressure differs from emission")
        receptor_event.verify()
        firing, _bank_digest = _verified_firing(
            motif_owner, receptor_experience
        )
        if firing.firing_motif_neuron_ids != (
            emission.exemplar.firing_motif_neuron_ids
        ):
            raise ValueError(
                "self-heard motif assembly differs from motor exemplar"
            )
        payload = {
            "emission_receipt_sha256": (
                emission.emission_receipt.authority_receipt_sha256
            ),
            "firing_motif_neuron_ids": list(
                firing.firing_motif_neuron_ids
            ),
            "motor_id": emission.exemplar.motor_id,
            "receptor_event_receipt_sha256": (
                receptor_event.authority_receipt_sha256
            ),
            "receptor_experience_receipt_sha256": (
                receptor_experience.authority_receipt_sha256
            ),
            "schema": SELF_VOCAL_HEARING_SCHEMA,
        }
        signature = _sign(
            self._hearing_key, _HEARING_DOMAIN, payload
        )
        result = SelfVocalHearingReceipt(
            motor_id=emission.exemplar.motor_id,
            emission_receipt_sha256=(
                emission.emission_receipt.authority_receipt_sha256
            ),
            receptor_event_receipt_sha256=(
                receptor_event.authority_receipt_sha256
            ),
            receptor_experience_receipt_sha256=(
                receptor_experience.authority_receipt_sha256
            ),
            firing_motif_neuron_ids=firing.firing_motif_neuron_ids,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._hearing_key)
        return result

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            encoded = self._encoded(self._exemplars)
            pcm_bytes = sum(
                len(value.pcm_s16le)
                for value in self._exemplars.values()
            )
            return {
                "exemplar_count": len(self._exemplars),
                "exemplar_capacity": self._profile.max_exemplars,
                "exemplar_capacity_exhausted": (
                    len(self._exemplars) >= self._profile.max_exemplars
                ),
                "retained_pcm_bytes": pcm_bytes,
                "pcm_byte_capacity": self._profile.max_total_pcm_bytes,
                "pcm_bytes_remaining": (
                    self._profile.max_total_pcm_bytes - pcm_bytes
                ),
                "encoded_state_bytes": len(encoded),
                "state_byte_capacity": self._profile.max_state_bytes,
            }

    def _encoded(
        self,
        exemplars: Mapping[str, SelfVocalPCMExemplar],
    ) -> bytes:
        body = {
            "exemplars": [
                exemplars[key].as_record() for key in sorted(exemplars)
            ],
            "resource_profile": (
                self._profile.payload()
                | {
                    "authority_receipt_sha256": (
                        self._profile.authority_receipt_sha256
                    )
                }
            ),
            "schema": SELF_VOCAL_STATE_SCHEMA,
        }
        envelope = {
            "body": body,
            "schema": SELF_VOCAL_ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(
                self._state_key, _STATE_DOMAIN, body
            ),
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._profile.max_state_bytes:
            raise SelfVocalCapacityError(
                "self-vocal state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._exemplars)

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
    ) -> "SelfVocalPCMMotorOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("self-vocal state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("self-vocal state is not canonical JSON") from exc
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != SELF_VOCAL_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("self-vocal state envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"exemplars", "resource_profile", "schema"}
            or body.get("schema") != SELF_VOCAL_STATE_SCHEMA
            or not isinstance(body.get("exemplars"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("self-vocal state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_exemplars",
            "max_state_bytes",
            "max_total_pcm_bytes",
            "profile_id",
            "schema",
        }:
            raise ValueError("self-vocal resource profile record changed")
        profile = SelfVocalMotorResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_exemplars=raw_profile.get("max_exemplars"),
            max_total_pcm_bytes=raw_profile.get("max_total_pcm_bytes"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
        )
        if not hmac.compare_digest(
            envelope["state_hmac_sha256"],
            _sign(owner._state_key, _STATE_DOMAIN, body),
        ):
            raise ValueError("self-vocal state HMAC changed")
        for raw in body["exemplars"]:
            if (
                not isinstance(raw, Mapping)
                or set(raw)
                != {
                    "authority_hmac_sha256",
                    "capture_receipt_sha256",
                    "firing_motif_neuron_ids",
                    "motif_bank_state_sha256",
                    "motor_id",
                    "pcm_base64",
                    "pcm_sha256",
                    "receptor_event_receipt_sha256",
                    "receptor_experience_receipt_sha256",
                    "sample_count",
                    "sample_rate_hz",
                    "schema",
                }
                or raw.get("schema") != SELF_VOCAL_EXEMPLAR_SCHEMA
                or raw.get("sample_rate_hz") != VOCAL_SAMPLE_RATE_HZ
                or not isinstance(
                    raw.get("firing_motif_neuron_ids"), list
                )
            ):
                raise ValueError("self-vocal exemplar record changed")
            try:
                pcm = base64.b64decode(
                    raw.get("pcm_base64"), validate=True
                )
            except (binascii.Error, TypeError, ValueError) as exc:
                raise ValueError(
                    "self-vocal exemplar PCM is not canonical base64"
                ) from exc
            exemplar = SelfVocalPCMExemplar(
                motor_id=raw.get("motor_id"),
                pcm_sha256=raw.get("pcm_sha256"),
                sample_count=raw.get("sample_count"),
                pcm_s16le=pcm,
                capture_receipt_sha256=raw.get(
                    "capture_receipt_sha256"
                ),
                receptor_event_receipt_sha256=raw.get(
                    "receptor_event_receipt_sha256"
                ),
                receptor_experience_receipt_sha256=raw.get(
                    "receptor_experience_receipt_sha256"
                ),
                motif_bank_state_sha256=raw.get(
                    "motif_bank_state_sha256"
                ),
                firing_motif_neuron_ids=tuple(
                    raw["firing_motif_neuron_ids"]
                ),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
            )
            exemplar.verify(owner._exemplar_key)
            if (
                exemplar.as_record() != dict(raw)
                or exemplar.motor_id in owner._exemplars
            ):
                raise ValueError(
                    "self-vocal exemplar is not canonical or is duplicated"
                )
            owner._exemplars[exemplar.motor_id] = exemplar
        if (
            len(owner._exemplars) > profile.max_exemplars
            or sum(
                len(value.pcm_s16le)
                for value in owner._exemplars.values()
            )
            > profile.max_total_pcm_bytes
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("self-vocal restored state changed")
        return owner


class SelfVocalCapacityError(RuntimeError):
    pass


__all__ = (
    "PreparedSelfVocalEmission",
    "SelfVocalCapacityError",
    "SelfVocalEmissionReceipt",
    "SelfVocalHearingReceipt",
    "SelfVocalMotorResourceProfile",
    "SelfVocalPCMExemplar",
    "SelfVocalPCMMotorOwner",
)
