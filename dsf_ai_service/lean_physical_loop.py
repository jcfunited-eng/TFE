"""Minimal native-world causal loop for the lean Guala shell."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
from typing import Any

from dsf_ai_service.guala_cochlea import one_self_hearing_hop
from dsf_ai_service.lean_embodiment_observation import (
    lean_embodiment_observation,
)
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.guala_motor_world import prepare_motor_consequence
from dsf_ai_service.guala_physical_sensorium import (
    settle_physical_sensorium,
    settle_projected_physical_sensorium,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.guala_world_sensorium import (
    passive_sensorium,
    prepare_passive_world_interval,
    retinal_carriage,
)
from dsf_ai_service.lean_actor import (
    MAX_PRESSURE_BYTES,
    PhysicalOccurrence,
    SettlementResult,
)


PASSIVE_TIMES = tuple(Fraction(index, 16_000) for index in range(0, 4_001, 160))
PASSIVE_ADMISSION = ([(250, 1_000)],)
MAX_NATIVE_INTERVALS_PER_OCCURRENCE = 4


def _commit_prepared(world: Any, prepared: Any) -> Any:
    with world.prepared_action_visibility_transaction(prepared):
        return world.commit_prepared_action(prepared)


def _requires_physical_return(evidence: Any) -> bool:
    body_sources = tuple(evidence.body_proprioceptive_sources)
    body_consequences = tuple(evidence.articulated_body_consequences)
    if bool(body_sources) != bool(body_consequences):
        raise RuntimeError("native body consequence lost its physical source")
    return bool(
        body_sources
        or evidence.motor_unit_recruitments
        or evidence.root_yaw_unit_recruitments
        or evidence.root_translation_unit_recruitments
        or evidence.articulatory_unit_recruitments
    )


def _abort_occurrence(
    *,
    runtime: Any,
    world: Any,
    predecessor_world: bytes,
    uncommitted_prepared: Any | None,
) -> None:
    errors: list[BaseException] = []
    if uncommitted_prepared is not None:
        try:
            world.discard_prepared_action(uncommitted_prepared)
        except BaseException as error:
            errors.append(error)
    try:
        runtime.abort_unsealed_trajectory()
    except (RuntimeError, ValueError) as error:
        if "no pending candidate" not in str(error):
            errors.append(error)
    try:
        world.restore_encoded(predecessor_world)
        if bytes(world.encoded_snapshot()) != predecessor_world:
            raise RuntimeError("physical world rollback changed exact bytes")
    except BaseException as error:
        errors.append(error)
    if errors:
        raise RuntimeError("native/world occurrence rollback failed") from errors[0]


class LeanPhysicalLoop:
    """One direct full-field interval and every immediate physical return."""

    @property
    def maximum_native_intervals_per_occurrence(self) -> int:
        return MAX_NATIVE_INTERVALS_PER_OCCURRENCE

    def settle(
        self,
        runtime: Any,
        world: Any,
        occurrence: PhysicalOccurrence,
    ) -> SettlementResult:
        if occurrence.kind == "unattended" and occurrence.payload is None:
            return self._advance(runtime, world, None)
        if occurrence.kind == "sensory" and isinstance(
            occurrence.payload, LeanSensoryOccurrence
        ):
            return self._advance(runtime, world, occurrence.payload)
        raise ValueError("lean physical ingress kind is not mounted")

    def unattended(self, runtime: Any, world: Any) -> SettlementResult:
        return self._advance(runtime, world, None)

    def _advance(
        self,
        runtime: Any,
        world: Any,
        sensory: LeanSensoryOccurrence | None,
    ) -> SettlementResult:
        pending_pressure = runtime.in_flight_acoustic_pressure_s16le
        pending_body = runtime.in_flight_acoustic_body_s16le
        pending_source_tick = runtime.in_flight_acoustic_source_tick
        if (pending_pressure is None) != (pending_body is None) or (
            pending_pressure is None
        ) != (pending_source_tick is None):
            raise RuntimeError("native in-flight acoustic state lost cardinality")
        if (
            sensory is not None
            and sensory.pressure_s16le is not None
            and pending_pressure is not None
        ):
            raise RuntimeError(
                "external pressure refused while body-owned pressure awaits hearing"
            )

        start_tick = runtime.live_organism_tick
        before_native = runtime.readiness()
        predecessor_world = bytes(world.encoded_snapshot())
        primary_prepared = prepare_passive_world_interval(world)
        uncommitted_prepared: Any | None = primary_prepared
        self_heard_samples = 0
        self_hearing_source_tick = pending_source_tick
        immediately_heard_pressure: bytes | None = None
        motor_plan = None
        try:
            primary_sensorium = passive_sensorium(
                world=world,
                snapshot=primary_prepared.execution_receipt.after,
                body_axes=tuple(before_native.articulated_body_axes),
                frame_count=len(PASSIVE_TIMES),
                pending_execution=primary_prepared.execution_receipt,
            )
            external_heard_samples = 0
            if sensory is not None and sensory.retina_u8 is not None:
                _heading, transmission = retinal_carriage(
                    tuple(before_native.articulated_body_axes)
                )
                primary_sensorium = replace(
                    primary_sensorium,
                    retina=tuple(
                        (Fraction(value, 255) * transmission,) * len(PASSIVE_TIMES)
                        for value in sensory.retina_u8
                    ),
                )
            if sensory is not None and sensory.pressure_s16le is not None:
                times, legacy, cochleae, external_heard_samples = (
                    one_self_hearing_hop(sensory.pressure_s16le)
                )
                if times != PASSIVE_TIMES:
                    raise RuntimeError("external hearing changed the passive clock")
                primary_sensorium = replace(
                    primary_sensorium,
                    legacy_ears=(legacy, legacy),
                    cochleae=cochleae,
                )
            if pending_pressure is not None:
                pressure = bytes(pending_pressure)
                body = bytes(pending_body)
                times, legacy, cochleae, self_heard_samples = one_self_hearing_hop(
                    pressure
                )
                if times != PASSIVE_TIMES:
                    raise RuntimeError("self-hearing changed the passive clock")
                primary_sensorium = replace(
                    primary_sensorium,
                    legacy_ears=(legacy, legacy),
                    cochleae=cochleae,
                )
            primary_episode = settle_physical_sensorium(
                assembly_id=(
                    "guala-lean-unattended-"
                    f"{before_native.identity}-{runtime.live_organism_tick + 1}"
                ),
                source_times=PASSIVE_TIMES,
                sensorium=primary_sensorium,
            )
            if sensory is not None and sensory.guided_vocal_drives is not None:
                primary = runtime.advance_guided_vocal_interval_unsealed(
                    (primary_episode,),
                    PASSIVE_ADMISSION,
                    sensory.guided_vocal_drives,
                )
            elif pending_pressure is None:
                primary = runtime.advance_admitted_trajectory_unsealed(
                    (primary_episode,), PASSIVE_ADMISSION
                )
            else:
                primary = runtime.advance_in_flight_self_hearing_unsealed(
                    (primary_episode,),
                    PASSIVE_ADMISSION,
                    pressure,
                    body,
                    False,
                    self_heard_samples,
                )
            _commit_prepared(world, primary_prepared)
            uncommitted_prepared = None

            final = primary
            if _requires_physical_return(primary):
                successor_axes = tuple(runtime.readiness().articulated_body_axes)
                return_pressure = runtime.in_flight_acoustic_pressure_s16le
                return_body = runtime.in_flight_acoustic_body_s16le
                return_source_tick = runtime.in_flight_acoustic_source_tick
                if (return_pressure is None) != (return_body is None) or (
                    return_pressure is None
                ) != (return_source_tick is None):
                    raise RuntimeError(
                        "native return acoustic state lost cardinality"
                    )
                return_hearing = None
                return_heard_samples = 0
                if return_pressure is not None:
                    immediately_heard_pressure = bytes(return_pressure)
                    (
                        heard_times,
                        heard_legacy,
                        heard_cochleae,
                        return_heard_samples,
                    ) = one_self_hearing_hop(
                        bytes(return_pressure),
                    )
                    if heard_times != PASSIVE_TIMES:
                        raise RuntimeError(
                            "return self-hearing changed its protected clock"
                        )
                    hearing_sensorium = replace(
                        primary_sensorium,
                        legacy_ears=(heard_legacy, heard_legacy),
                        cochleae=heard_cochleae,
                    )
                    return_hearing = settle_projected_physical_sensorium(
                        assembly_id=(
                            "guala-lean-immediate-self-hearing-"
                            + primary.causal_transition_sha256
                        ),
                        source_times=PASSIVE_TIMES,
                        sensorium=hearing_sensorium,
                        senses=(PhysicalSense.SOUND,),
                    )
                motor_plan = prepare_motor_consequence(
                    world=world,
                    evidence=primary,
                    predecessor_state_sha256=before_native.state_sha256,
                    predecessor_body_axes=tuple(before_native.articulated_body_axes),
                    successor_body_axes=successor_axes,
                    passive_times=PASSIVE_TIMES,
                    exclude_sound=return_hearing is not None,
                )
                uncommitted_prepared = motor_plan.prepared_world
                with world.prepared_action_visibility_transaction(
                    motor_plan.prepared_world
                ):
                    world.commit_prepared_action(motor_plan.prepared_world)
                    uncommitted_prepared = None
                    if return_pressure is None:
                        final = runtime.advance_coexisting_admitted_interval_unsealed(
                            motor_plan.sources, motor_plan.admissions
                        )
                    else:
                        final = runtime.advance_in_flight_self_hearing_unsealed(
                            (*motor_plan.sources, return_hearing),
                            (*motor_plan.admissions, [(250, 1_000)]),
                            bytes(return_pressure),
                            bytes(return_body),
                            True,
                            return_heard_samples,
                        )
                        self_heard_samples += return_heard_samples
                        self_hearing_source_tick = return_source_tick
                    if motor_plan.vestibular is not None:
                        final = runtime.advance_vestibular_trajectory_unsealed(
                            *motor_plan.vestibular
                        )

            lived_tick_delta = runtime.live_organism_tick - start_tick
            if (
                lived_tick_delta <= 0
                or lived_tick_delta > MAX_NATIVE_INTERVALS_PER_OCCURRENCE
            ):
                raise RuntimeError("physical occurrence exceeded its interval bound")
            self_pressure_pending = (
                runtime.in_flight_acoustic_pressure_s16le is not None
            )
            pressure_body = runtime.in_flight_acoustic_pressure_s16le
            if pressure_body is None:
                pressure_body = immediately_heard_pressure
            pressure_record = None
            if pressure_body is not None:
                pressure_bytes = bytes(pressure_body)
                if (
                    not pressure_bytes
                    or len(pressure_bytes) > MAX_PRESSURE_BYTES
                    or len(pressure_bytes) % 2
                ):
                    raise RuntimeError("native pressure exceeded its transport bound")
                pressure_record = (
                    hashlib.sha256(pressure_bytes).hexdigest(),
                    pressure_bytes,
                )
            body_consequences = tuple(primary.articulated_body_consequences)
            world_snapshot = world.observation_snapshot()
            retinal_u8 = []
            for trajectory in primary_sensorium.retina:
                value = Fraction(trajectory[-1]).limit_denominator(1_000_000)
                if not Fraction(0) <= value <= Fraction(1):
                    raise RuntimeError("retinal observer left its physical range")
                retinal_u8.append(round(value * 255))
            result = SettlementResult(
                native_interval_count=lived_tick_delta,
                observation={
                    "actual_root_motion": (
                        (0, 0, 0)
                        if motor_plan is None
                        else motor_plan.actual_root_motion
                    ),
                    "body_consequence_count": len(body_consequences),
                    "causal_transition_sha256": final.causal_transition_sha256,
                    "dsf_delivery_count": final.dsf_delivery_count,
                    "embodiment": lean_embodiment_observation(
                        world_snapshot,
                        tuple(runtime.readiness().articulated_body_axes),
                    ),
                    "external_heard_sample_count": external_heard_samples,
                    "external_guided_vocal_axis_count": (
                        0
                        if sensory is None
                        or sensory.guided_vocal_drives is None
                        else len(sensory.guided_vocal_drives)
                    ),
                    "external_retinal_site_count": (
                        0
                        if sensory is None or sensory.retina_u8 is None
                        else len(sensory.retina_u8)
                    ),
                    "external_sensory_source": (
                        None if sensory is None else sensory.source
                    ),
                    "external_source_receipt_sha256": (
                        None
                        if sensory is None
                        else sensory.source_receipt_sha256
                    ),
                    "physically_transitioned_neuron_count": (
                        final.physically_transitioned_neuron_count
                    ),
                    "primary_causal_transition_sha256": (
                        primary.causal_transition_sha256
                    ),
                    "python_callback_count": final.python_callback_count,
                    "requested_world_action": (
                        None if motor_plan is None else motor_plan.requested_action
                    ),
                    "retinal_observer_kind": (
                        "achromatic-u8-projection-of-native-retinal-input"
                    ),
                    "retinal_u8": retinal_u8,
                    "requested_root_motion": (
                        (0, 0, 0)
                        if motor_plan is None
                        else motor_plan.requested_root_motion
                    ),
                    "self_hearing_source_tick": (
                        None
                        if self_hearing_source_tick is None
                        else int(self_hearing_source_tick)
                    ),
                    "self_heard_sample_count": self_heard_samples,
                    "self_pressure_pending": self_pressure_pending,
                    "world_action_refusal": (
                        None if motor_plan is None else motor_plan.refusal_reason
                    ),
                    "world_revision": world_snapshot.revision,
                },
                pressure=pressure_record,
            )
        except BaseException:
            _abort_occurrence(
                runtime=runtime,
                world=world,
                predecessor_world=predecessor_world,
                uncommitted_prepared=uncommitted_prepared,
            )
            raise
        return result
