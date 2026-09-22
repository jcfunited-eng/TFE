"""Durable ordering for externally guided physical-surface lessons.

This mechanism governs occurrence order only.  It does not carry pixels,
labels, words, transcripts, pronunciation, meaning, or recognition.  Every
step names one already-mounted opaque W1 object and binds one exact WAV digest;
the existing physical lesson path remains responsible for receptor
transduction and complete causal settlement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping, Sequence


PLAN_SCHEMA = "guala.physical_surface_tutoring.plan.v1"
PREPARATION_SCHEMA = "guala.physical_surface_tutoring.preparation.v1"
PROGRESSION_SCHEMA = "guala.physical_surface_tutoring.progression.v1"
STATE_SCHEMA = "guala.physical_surface_tutoring.state.v1"
STATE_ENVELOPE_SCHEMA = "guala.physical_surface_tutoring.state_hmac.v1"
STATUS_SCHEMA = "guala.physical_surface_tutoring.status.v1"
MAX_PLAN_STEPS = 36
MAX_STATE_BYTES = 128 * 1024
CARD_EXPOSURE_NS = 15_000_000_000
APPROVED_PHYSICAL_SURFACE_IDS = tuple(
    f"W1-optical-surface-{index:02d}"
    for index in range(1, 37)
)

_PLAN_DOMAIN = b"guala-physical-surface-tutoring-plan-v1\0"
_PREPARATION_DOMAIN = b"guala-physical-surface-tutoring-preparation-v1\0"
_PROGRESSION_DOMAIN = b"guala-physical-surface-tutoring-progression-v1\0"
_STATE_DOMAIN = b"guala-physical-surface-tutoring-state-v1\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


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
        or value != value.strip()
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} changed")
    return value


def _uint63(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= 2**63 - 1
    ):
        raise ValueError(f"{label} changed")
    return value


def _positive_capacity(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RuntimeError(f"{label} is exhausted")
    return value


def _authority_key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("physical tutoring authority key changed")
    return raw


def _receipt(domain: bytes, payload: Mapping[str, object]) -> str:
    return hashlib.sha256(domain + _canonical(payload)).hexdigest()


def _signature(
    key: bytes,
    domain: bytes,
    payload: Mapping[str, object],
) -> str:
    return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceTutoringPlanStep:
    target_object_id: str
    source_media_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        target_object_id: str,
        source_media_receipt_sha256: str,
    ) -> "PhysicalSurfaceTutoringPlanStep":
        return cls(
            target_object_id=_identifier(
                target_object_id,
                "tutor-mounted physical surface",
            ),
            source_media_receipt_sha256=_sha(
                source_media_receipt_sha256,
                "tutor WAV receipt",
            ),
        )

    def record(self) -> dict[str, object]:
        return {
            "source_media_receipt_sha256": self.source_media_receipt_sha256,
            "target_object_id": self.target_object_id,
        }


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceTutoringPlan:
    initial_source_time_ns: int
    prior_plan_progression_receipt_sha256: str | None
    steps: tuple[PhysicalSurfaceTutoringPlanStep, ...]
    authority_receipt_sha256: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "authority_boundary": {
                "meaning_authority": False,
                "recognition_authority": False,
                "transcript_authority": False,
                "word_authority": False,
            },
            "initial_source_time_ns": self.initial_source_time_ns,
            "prior_plan_progression_receipt_sha256": (
                self.prior_plan_progression_receipt_sha256
            ),
            "presentation": "tutor_mounted_physical_surface",
            "schema": PLAN_SCHEMA,
            "steps": [step.record() for step in self.steps],
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedPhysicalSurfaceTutoringStep:
    plan_receipt_sha256: str
    step_index: int
    prior_progression_receipt_sha256: str | None
    context_id: str
    source_time_start_ns: int
    target_object_id: str
    source_media_receipt_sha256: str
    authority_receipt_sha256: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "context_id": self.context_id,
            "plan_receipt_sha256": self.plan_receipt_sha256,
            "prior_progression_receipt_sha256": (
                self.prior_progression_receipt_sha256
            ),
            "schema": PREPARATION_SCHEMA,
            "source_media_receipt_sha256": self.source_media_receipt_sha256,
            "source_time_start_ns": self.source_time_start_ns,
            "step_index": self.step_index,
            "target_object_id": self.target_object_id,
        }

    def runtime_arguments(self, *, wav_bytes: bytes) -> dict[str, object]:
        if (
            not isinstance(wav_bytes, bytes)
            or not wav_bytes
            or hashlib.sha256(wav_bytes).hexdigest()
            != self.source_media_receipt_sha256
        ):
            raise ValueError("tutor WAV differs from the prepared occurrence")
        return {
            "context_id": self.context_id,
            "source_time_start_ns": self.source_time_start_ns,
            "target_object_id": self.target_object_id,
            "wav_bytes": wav_bytes,
        }


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceTutoringProgression:
    plan_receipt_sha256: str
    step_index: int
    prior_progression_receipt_sha256: str | None
    source_time_start_ns: int
    source_time_end_ns: int
    target_object_id: str
    source_media_receipt_sha256: str
    settlement_receipt_sha256: str
    whole_organism_episode_receipt_sha256: str
    passive_learning_receipt_sha256: str
    thing_id: str
    authority_receipt_sha256: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "passive_learning_receipt_sha256": (
                self.passive_learning_receipt_sha256
            ),
            "plan_receipt_sha256": self.plan_receipt_sha256,
            "prior_progression_receipt_sha256": (
                self.prior_progression_receipt_sha256
            ),
            "schema": PROGRESSION_SCHEMA,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "source_media_receipt_sha256": self.source_media_receipt_sha256,
            "source_time_end_ns": self.source_time_end_ns,
            "source_time_start_ns": self.source_time_start_ns,
            "step_index": self.step_index,
            "target_object_id": self.target_object_id,
            "thing_id": self.thing_id,
            "whole_organism_episode_receipt_sha256": (
                self.whole_organism_episode_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class PhysicalSurfaceTutoringConductor:
    """One bounded, replay-safe external tutoring progression."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        approved_surface_ids: Sequence[str],
        max_plan_steps: int = MAX_PLAN_STEPS,
        max_state_bytes: int = MAX_STATE_BYTES,
    ) -> None:
        raw_key = _authority_key(authority_key)
        approved = tuple(
            _identifier(value, "approved physical surface")
            for value in approved_surface_ids
        )
        if not approved or len(approved) != len(set(approved)):
            raise ValueError("approved physical surface inventory changed")
        if (
            isinstance(max_plan_steps, bool)
            or not isinstance(max_plan_steps, int)
            or not 1 <= max_plan_steps <= MAX_PLAN_STEPS
            or isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 1 <= max_state_bytes <= MAX_STATE_BYTES
        ):
            raise ValueError("physical tutoring capacity changed")
        self._plan_key = hashlib.sha256(_PLAN_DOMAIN + raw_key).digest()
        self._preparation_key = hashlib.sha256(
            _PREPARATION_DOMAIN + raw_key
        ).digest()
        self._progression_key = hashlib.sha256(
            _PROGRESSION_DOMAIN + raw_key
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + raw_key).digest()
        self._approved_surface_ids = approved
        self._max_plan_steps = max_plan_steps
        self._max_state_bytes = max_state_bytes
        self._plan: PhysicalSurfaceTutoringPlan | None = None
        self._next_step_index = 0
        self._tail: PhysicalSurfaceTutoringProgression | None = None
        self._in_flight: PreparedPhysicalSurfaceTutoringStep | None = None
        self._lock = threading.RLock()

    @property
    def active_plan(self) -> PhysicalSurfaceTutoringPlan | None:
        with self._lock:
            return self._plan

    @property
    def progression_tail(self) -> PhysicalSurfaceTutoringProgression | None:
        with self._lock:
            return self._tail

    def _verify_plan(self, plan: PhysicalSurfaceTutoringPlan) -> None:
        if not isinstance(plan, PhysicalSurfaceTutoringPlan):
            raise TypeError("physical tutoring plan is not typed")
        if (
            not 1 <= len(plan.steps) <= self._max_plan_steps
            or any(
                step.target_object_id not in self._approved_surface_ids
                for step in plan.steps
            )
            or plan.authority_receipt_sha256
            != _receipt(_PLAN_DOMAIN, plan.payload())
            or not hmac.compare_digest(
                plan.authority_hmac_sha256,
                _signature(self._plan_key, _PLAN_DOMAIN, plan.payload()),
            )
        ):
            raise ValueError("physical tutoring plan authority changed")

    def issue_plan(
        self,
        *,
        steps: Sequence[PhysicalSurfaceTutoringPlanStep],
        initial_source_time_ns: int | None,
        prior_progression_receipt_sha256: str | None = None,
    ) -> PhysicalSurfaceTutoringPlan:
        ordered = tuple(steps)
        if not 1 <= len(ordered) <= self._max_plan_steps:
            raise ValueError("physical tutoring plan extent changed")
        for step in ordered:
            if not isinstance(step, PhysicalSurfaceTutoringPlanStep):
                raise TypeError("physical tutoring plan step is not typed")
            if step.target_object_id not in self._approved_surface_ids:
                raise ValueError("physical tutoring target is not approved")
        with self._lock:
            if self._in_flight is not None:
                raise RuntimeError("physical tutoring occurrence is in flight")
            if self._plan is not None and self._next_step_index < len(
                self._plan.steps
            ):
                raise RuntimeError("physical tutoring plan is still active")
            if self._plan is None:
                if prior_progression_receipt_sha256 is not None:
                    raise ValueError(
                        "initial physical tutoring plan gained a prior receipt"
                    )
                source_start = _uint63(
                    initial_source_time_ns,
                    "physical tutoring initial source time",
                )
                prior_plan_tail = None
            else:
                if self._tail is None:
                    raise RuntimeError(
                        "completed physical tutoring plan has no progression"
                    )
                expected_prior = self._tail.authority_receipt_sha256
                if prior_progression_receipt_sha256 != expected_prior:
                    raise ValueError("physical tutoring plan prior is stale")
                if initial_source_time_ns is not None:
                    raise ValueError(
                        "continued physical tutoring source time is derived"
                    )
                source_start = self._tail.source_time_end_ns
                prior_plan_tail = expected_prior
            provisional = PhysicalSurfaceTutoringPlan(
                initial_source_time_ns=source_start,
                prior_plan_progression_receipt_sha256=prior_plan_tail,
                steps=ordered,
                authority_receipt_sha256="0" * 64,
                authority_hmac_sha256="0" * 64,
            )
            plan = PhysicalSurfaceTutoringPlan(
                initial_source_time_ns=provisional.initial_source_time_ns,
                prior_plan_progression_receipt_sha256=(
                    provisional.prior_plan_progression_receipt_sha256
                ),
                steps=provisional.steps,
                authority_receipt_sha256=_receipt(
                    _PLAN_DOMAIN,
                    provisional.payload(),
                ),
                authority_hmac_sha256=_signature(
                    self._plan_key,
                    _PLAN_DOMAIN,
                    provisional.payload(),
                ),
            )
            self._plan = plan
            self._next_step_index = 0
            self._tail = None
            self._verify_state_locked()
            self._encoded_locked()
        return plan

    def _verify_prepared(
        self,
        prepared: PreparedPhysicalSurfaceTutoringStep,
    ) -> None:
        if (
            not isinstance(prepared, PreparedPhysicalSurfaceTutoringStep)
            or prepared.authority_receipt_sha256
            != _receipt(_PREPARATION_DOMAIN, prepared.payload())
            or not hmac.compare_digest(
                prepared.authority_hmac_sha256,
                _signature(
                    self._preparation_key,
                    _PREPARATION_DOMAIN,
                    prepared.payload(),
                ),
            )
        ):
            raise ValueError("physical tutoring preparation authority changed")

    def prepare_step(
        self,
        *,
        plan_receipt_sha256: str,
        step_index: int,
        prior_progression_receipt_sha256: str | None,
        wav_bytes: bytes,
        remaining_episode_slots: int,
        remaining_passive_slots: int,
        remaining_thing_partition_slots: int,
    ) -> PreparedPhysicalSurfaceTutoringStep:
        _positive_capacity(remaining_episode_slots, "episode capacity")
        _positive_capacity(remaining_passive_slots, "passive learning capacity")
        _positive_capacity(
            remaining_thing_partition_slots,
            "THING partition capacity",
        )
        if not isinstance(wav_bytes, bytes) or not wav_bytes:
            raise ValueError("physical tutoring WAV changed")
        media_receipt = hashlib.sha256(wav_bytes).hexdigest()
        with self._lock:
            plan = self._plan
            if plan is None:
                raise RuntimeError("physical tutoring plan is unavailable")
            self._verify_plan(plan)
            if self._in_flight is not None:
                raise RuntimeError("physical tutoring occurrence is in flight")
            if _sha(plan_receipt_sha256, "physical tutoring plan") != (
                plan.authority_receipt_sha256
            ):
                raise ValueError("physical tutoring plan is stale")
            if (
                isinstance(step_index, bool)
                or not isinstance(step_index, int)
                or step_index != self._next_step_index
                or step_index >= len(plan.steps)
            ):
                raise ValueError("physical tutoring step is stale or complete")
            expected_prior = (
                self._tail.authority_receipt_sha256
                if self._tail is not None
                else plan.prior_plan_progression_receipt_sha256
            )
            if prior_progression_receipt_sha256 != expected_prior:
                raise ValueError("physical tutoring prior receipt is stale")
            step = plan.steps[step_index]
            if media_receipt != step.source_media_receipt_sha256:
                raise ValueError("physical tutoring WAV changed from its plan")
            source_start = (
                self._tail.source_time_end_ns
                if self._tail is not None
                else plan.initial_source_time_ns
            )
            context_payload = {
                "plan_receipt_sha256": plan.authority_receipt_sha256,
                "prior_progression_receipt_sha256": expected_prior,
                "source_time_start_ns": source_start,
                "step_index": step_index,
            }
            provisional = PreparedPhysicalSurfaceTutoringStep(
                plan_receipt_sha256=plan.authority_receipt_sha256,
                step_index=step_index,
                prior_progression_receipt_sha256=expected_prior,
                context_id=_receipt(_PREPARATION_DOMAIN, context_payload),
                source_time_start_ns=source_start,
                target_object_id=step.target_object_id,
                source_media_receipt_sha256=step.source_media_receipt_sha256,
                authority_receipt_sha256="0" * 64,
                authority_hmac_sha256="0" * 64,
            )
            prepared = PreparedPhysicalSurfaceTutoringStep(
                plan_receipt_sha256=provisional.plan_receipt_sha256,
                step_index=provisional.step_index,
                prior_progression_receipt_sha256=(
                    provisional.prior_progression_receipt_sha256
                ),
                context_id=provisional.context_id,
                source_time_start_ns=provisional.source_time_start_ns,
                target_object_id=provisional.target_object_id,
                source_media_receipt_sha256=(
                    provisional.source_media_receipt_sha256
                ),
                authority_receipt_sha256=_receipt(
                    _PREPARATION_DOMAIN,
                    provisional.payload(),
                ),
                authority_hmac_sha256=_signature(
                    self._preparation_key,
                    _PREPARATION_DOMAIN,
                    provisional.payload(),
                ),
            )
            self._verify_prepared(prepared)
            self._in_flight = prepared
            return prepared

    def commit_step(
        self,
        prepared: PreparedPhysicalSurfaceTutoringStep,
        result: Mapping[str, object],
    ) -> PhysicalSurfaceTutoringProgression:
        self._verify_prepared(prepared)
        if not isinstance(result, Mapping):
            raise TypeError("physical tutoring lesson result changed")
        if (
            result.get("schema") != "guala.physical_surface_lesson.result.v1"
            or result.get("retained_pcm_bytes") != 0
            or result.get("visual_exposure_duration_ns") != CARD_EXPOSURE_NS
        ):
            raise ValueError("physical tutoring lesson result changed")
        settlement = _sha(
            result.get("settlement_receipt_sha256"),
            "physical tutoring settlement",
        )
        episode = _sha(
            result.get("whole_organism_episode_receipt_sha256"),
            "physical tutoring whole-organism episode",
        )
        passive = _sha(
            result.get("passive_learning_receipt_sha256"),
            "physical tutoring passive learning",
        )
        thing_id = _identifier(result.get("thing_id"), "physical tutoring THING")
        with self._lock:
            if self._in_flight != prepared:
                raise ValueError("physical tutoring preparation is stale")
            if self._plan is None or self._next_step_index != prepared.step_index:
                raise RuntimeError("physical tutoring progression changed")
            provisional = PhysicalSurfaceTutoringProgression(
                plan_receipt_sha256=prepared.plan_receipt_sha256,
                step_index=prepared.step_index,
                prior_progression_receipt_sha256=(
                    prepared.prior_progression_receipt_sha256
                ),
                source_time_start_ns=prepared.source_time_start_ns,
                source_time_end_ns=(
                    prepared.source_time_start_ns + CARD_EXPOSURE_NS
                ),
                target_object_id=prepared.target_object_id,
                source_media_receipt_sha256=(
                    prepared.source_media_receipt_sha256
                ),
                settlement_receipt_sha256=settlement,
                whole_organism_episode_receipt_sha256=episode,
                passive_learning_receipt_sha256=passive,
                thing_id=thing_id,
                authority_receipt_sha256="0" * 64,
                authority_hmac_sha256="0" * 64,
            )
            progression = PhysicalSurfaceTutoringProgression(
                plan_receipt_sha256=provisional.plan_receipt_sha256,
                step_index=provisional.step_index,
                prior_progression_receipt_sha256=(
                    provisional.prior_progression_receipt_sha256
                ),
                source_time_start_ns=provisional.source_time_start_ns,
                source_time_end_ns=provisional.source_time_end_ns,
                target_object_id=provisional.target_object_id,
                source_media_receipt_sha256=(
                    provisional.source_media_receipt_sha256
                ),
                settlement_receipt_sha256=(
                    provisional.settlement_receipt_sha256
                ),
                whole_organism_episode_receipt_sha256=(
                    provisional.whole_organism_episode_receipt_sha256
                ),
                passive_learning_receipt_sha256=(
                    provisional.passive_learning_receipt_sha256
                ),
                thing_id=provisional.thing_id,
                authority_receipt_sha256=_receipt(
                    _PROGRESSION_DOMAIN,
                    provisional.payload(),
                ),
                authority_hmac_sha256=_signature(
                    self._progression_key,
                    _PROGRESSION_DOMAIN,
                    provisional.payload(),
                ),
            )
            self._tail = progression
            self._next_step_index += 1
            self._in_flight = None
            self._verify_state_locked()
            self._encoded_locked()
            return progression

    def abort_step(self, prepared: PreparedPhysicalSurfaceTutoringStep) -> None:
        self._verify_prepared(prepared)
        with self._lock:
            if self._in_flight != prepared:
                raise ValueError("physical tutoring preparation is stale")
            self._in_flight = None

    def _state_payload_locked(self) -> dict[str, object]:
        return {
            "approved_surface_ids": list(self._approved_surface_ids),
            "max_plan_steps": self._max_plan_steps,
            "max_state_bytes": self._max_state_bytes,
            "next_step_index": self._next_step_index,
            "plan": self._plan.record() if self._plan is not None else None,
            "progression_tail": (
                self._tail.record() if self._tail is not None else None
            ),
            "schema": STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        if self._in_flight is not None:
            raise RuntimeError("cannot freeze an in-flight tutoring occurrence")
        payload = self._state_payload_locked()
        encoded = _canonical({
            "authority_hmac_sha256": _signature(
                self._state_key,
                _STATE_DOMAIN,
                payload,
            ),
            "payload": payload,
            "schema": STATE_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError("physical tutoring state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            self._verify_state_locked()
            return self._encoded_locked()

    def _verify_progression(
        self,
        progression: PhysicalSurfaceTutoringProgression,
    ) -> None:
        if (
            progression.authority_receipt_sha256
            != _receipt(_PROGRESSION_DOMAIN, progression.payload())
            or not hmac.compare_digest(
                progression.authority_hmac_sha256,
                _signature(
                    self._progression_key,
                    _PROGRESSION_DOMAIN,
                    progression.payload(),
                ),
            )
            or progression.source_time_end_ns
            - progression.source_time_start_ns
            != CARD_EXPOSURE_NS
        ):
            raise ValueError("physical tutoring progression authority changed")

    def _verify_state_locked(self) -> None:
        if self._plan is None:
            if self._next_step_index != 0 or self._tail is not None:
                raise ValueError("empty physical tutoring state changed")
            return
        self._verify_plan(self._plan)
        if not 0 <= self._next_step_index <= len(self._plan.steps):
            raise ValueError("physical tutoring progression extent changed")
        if self._next_step_index == 0:
            if self._tail is not None:
                raise ValueError("physical tutoring tail appeared before a step")
            return
        if self._tail is None:
            raise ValueError("physical tutoring progression tail is absent")
        self._verify_progression(self._tail)
        step = self._plan.steps[self._next_step_index - 1]
        if (
            self._tail.plan_receipt_sha256
            != self._plan.authority_receipt_sha256
            or self._tail.step_index != self._next_step_index - 1
            or self._tail.target_object_id != step.target_object_id
            or self._tail.source_media_receipt_sha256
            != step.source_media_receipt_sha256
        ):
            raise ValueError("physical tutoring progression left its plan")

    @staticmethod
    def _plan_from_record(value: Mapping[str, object]) -> PhysicalSurfaceTutoringPlan:
        steps = tuple(
            PhysicalSurfaceTutoringPlanStep.create(
                target_object_id=item["target_object_id"],
                source_media_receipt_sha256=item[
                    "source_media_receipt_sha256"
                ],
            )
            for item in value["steps"]
        )
        return PhysicalSurfaceTutoringPlan(
            initial_source_time_ns=value["initial_source_time_ns"],
            prior_plan_progression_receipt_sha256=value[
                "prior_plan_progression_receipt_sha256"
            ],
            steps=steps,
            authority_receipt_sha256=value["authority_receipt_sha256"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
        )

    @staticmethod
    def _progression_from_record(
        value: Mapping[str, object],
    ) -> PhysicalSurfaceTutoringProgression:
        return PhysicalSurfaceTutoringProgression(
            plan_receipt_sha256=value["plan_receipt_sha256"],
            step_index=value["step_index"],
            prior_progression_receipt_sha256=value[
                "prior_progression_receipt_sha256"
            ],
            source_time_start_ns=value["source_time_start_ns"],
            source_time_end_ns=value["source_time_end_ns"],
            target_object_id=value["target_object_id"],
            source_media_receipt_sha256=value[
                "source_media_receipt_sha256"
            ],
            settlement_receipt_sha256=value["settlement_receipt_sha256"],
            whole_organism_episode_receipt_sha256=value[
                "whole_organism_episode_receipt_sha256"
            ],
            passive_learning_receipt_sha256=value[
                "passive_learning_receipt_sha256"
            ],
            thing_id=value["thing_id"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
        )

    @classmethod
    def restore_encoded(
        cls,
        encoded: bytes,
        *,
        authority_key: bytes | str,
        approved_surface_ids: Sequence[str],
    ) -> "PhysicalSurfaceTutoringConductor":
        if not isinstance(encoded, bytes) or len(encoded) > MAX_STATE_BYTES:
            raise ValueError("physical tutoring state changed")
        try:
            envelope = json.loads(encoded.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("physical tutoring state is invalid") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"authority_hmac_sha256", "payload", "schema"}
            or envelope.get("schema") != STATE_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("physical tutoring state envelope changed")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("physical tutoring state payload changed")
        owner = cls(
            authority_key=authority_key,
            approved_surface_ids=approved_surface_ids,
            max_plan_steps=payload.get("max_plan_steps"),
            max_state_bytes=payload.get("max_state_bytes"),
        )
        if (
            payload.get("schema") != STATE_SCHEMA
            or payload.get("approved_surface_ids")
            != list(owner._approved_surface_ids)
            or not hmac.compare_digest(
                str(envelope.get("authority_hmac_sha256")),
                _signature(owner._state_key, _STATE_DOMAIN, payload),
            )
        ):
            raise ValueError("physical tutoring state authority changed")
        plan_record = payload.get("plan")
        tail_record = payload.get("progression_tail")
        owner._plan = (
            owner._plan_from_record(plan_record)
            if isinstance(plan_record, dict)
            else None
        )
        owner._tail = (
            owner._progression_from_record(tail_record)
            if isinstance(tail_record, dict)
            else None
        )
        owner._next_step_index = payload.get("next_step_index")
        owner._verify_state_locked()
        if owner._encoded_locked() != encoded:
            raise ValueError("physical tutoring state is not canonical")
        return owner

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "active": (
                    self._plan is not None
                    and self._next_step_index < len(self._plan.steps)
                ),
                "in_flight": self._in_flight is not None,
                "next_step_index": self._next_step_index,
                "plan_receipt_sha256": (
                    self._plan.authority_receipt_sha256
                    if self._plan is not None
                    else None
                ),
                "plan_step_count": (
                    len(self._plan.steps) if self._plan is not None else 0
                ),
                "progression_tail_receipt_sha256": (
                    self._tail.authority_receipt_sha256
                    if self._tail is not None
                    else None
                ),
                "retained_pcm_bytes": 0,
                "schema": STATUS_SCHEMA,
            }


__all__ = (
    "CARD_EXPOSURE_NS",
    "APPROVED_PHYSICAL_SURFACE_IDS",
    "MAX_PLAN_STEPS",
    "PhysicalSurfaceTutoringConductor",
    "PhysicalSurfaceTutoringPlan",
    "PhysicalSurfaceTutoringPlanStep",
    "PhysicalSurfaceTutoringProgression",
    "PreparedPhysicalSurfaceTutoringStep",
)
