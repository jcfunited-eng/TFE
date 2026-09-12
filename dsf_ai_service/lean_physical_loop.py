"""One native interval admitting current input and exact physical feedback."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
from typing import Any

from dsf_ai_service.guala_cochlea import one_self_hearing_hop
from dsf_ai_service.lean_embodiment_observation import lean_embodiment_observation
from dsf_ai_service.lean_sensory_occurrence import (
    LeanSensoryOccurrence, rgb_retina_luminance_u8, transmitted_rgb_retina_u8,
)
from dsf_ai_service.guala_motor_world import prepare_motor_consequence
from dsf_ai_service.guala_physical_return import PendingPhysicalReturn, PASSIVE_BODY_MAGIC
from dsf_ai_service.guala_physical_sensorium import (
    settle_physical_sensorium, settle_projected_physical_sensorium,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense, SENSE_ORDER
from dsf_ai_service.guala_world_sensorium import (
    consequence_source_times, passive_sensorium, prepare_passive_world_interval,
    retinal_carriage,
)
from dsf_ai_service.lean_actor import (
    MAX_PRESSURE_BYTES, PhysicalOccurrence, PhysicalSettlementFailure, SettlementResult,
)


PASSIVE_TIMES = tuple(Fraction(index, 16000) for index in range(0, 4001, 160))
PASSIVE_ADMISSION = ([(250, 1000)],)
MAX_NATIVE_INTERVALS_PER_OCCURRENCE = 1


def _requires_physical_return(evidence: Any) -> bool:
    body_sources = tuple(evidence.body_proprioceptive_sources)
    body_consequences = tuple(evidence.articulated_body_consequences)
    impulse_sources = tuple(source for source in body_sources
        if source.startswith((b"GLJSRC03", b"GLJSRC04")))
    if len(impulse_sources) > 1 or bool(impulse_sources) != bool(body_consequences):
        raise RuntimeError("native body consequence lost its impulse source")
    if any(not source.startswith((b"GLJSRC03", b"GLJSRC04", PASSIVE_BODY_MAGIC))
           for source in body_sources):
        raise RuntimeError("native body source format is not mounted")
    return bool(
        body_sources or evidence.motor_unit_recruitments
        or evidence.root_yaw_unit_recruitments
        or evidence.root_translation_unit_recruitments
        or evidence.articulatory_unit_recruitments
    )


class LeanPhysicalLoop:
    """One physical input boundary, never a private chain of cognitive calls."""

    @property
    def maximum_native_intervals_per_occurrence(self) -> int:
        return MAX_NATIVE_INTERVALS_PER_OCCURRENCE

    def settle(self, runtime: Any, world: Any, occurrence: PhysicalOccurrence) -> SettlementResult:
        if occurrence.kind == "unattended" and occurrence.payload is None:
            return self._advance(runtime, world, None)
        if occurrence.kind == "sensory" and isinstance(occurrence.payload, LeanSensoryOccurrence):
            return self._advance(runtime, world, occurrence.payload)
        raise ValueError("lean physical ingress kind is not mounted")

    def unattended(self, runtime: Any, world: Any) -> SettlementResult:
        return self._advance(runtime, world, None)

    def _advance(self, runtime: Any, world: Any, sensory: LeanSensoryOccurrence | None) -> SettlementResult:
        from guala_core import NativePhysicalInputRefused

        pending_pressure = runtime.in_flight_acoustic_pressure_s16le
        pending_body = runtime.in_flight_acoustic_body_s16le
        pending_source_tick = runtime.in_flight_acoustic_source_tick
        if (pending_pressure is None) != (pending_body is None) or (pending_pressure is None) != (pending_source_tick is None):
            raise PhysicalSettlementFailure("native in-flight acoustic state lost cardinality")
        start_tick = runtime.live_organism_tick
        before_native = runtime.readiness()
        before_axes = tuple(before_native.articulated_body_axes)
        returning = world.pending_physical_return
        primary_prepared = None
        uncommitted_prepared = None
        native_started = False
        motor_plan = None
        next_return = None
        self_heard_samples = 0
        self_hearing_source_tick = pending_source_tick
        external_heard_samples = 0
        external_rgb_retina_u8 = None
        try:
            if returning is None:
                primary_prepared = prepare_passive_world_interval(world)
                uncommitted_prepared = primary_prepared
                times = PASSIVE_TIMES
                primary_sensorium = passive_sensorium(
                    world=world, snapshot=primary_prepared.execution_receipt.after,
                    body_axes=before_axes, frame_count=len(times),
                    pending_execution=primary_prepared.execution_receipt,
                )
            else:
                observed = world.observation_snapshot()
                returning.validate_binding(
                    identity=before_native.identity, producer_tick=start_tick,
                    world_revision=observed.revision,
                    world_receipt=observed.authority_receipt_sha256,
                )
                times = consequence_source_times(PASSIVE_TIMES)
                primary_sensorium = returning.sensorium(times)

            if sensory is not None and sensory.retina_rgb_u8 is not None:
                _heading, transmission = retinal_carriage(before_axes)
                luminance = rgb_retina_luminance_u8(sensory.retina_rgb_u8)
                primary_sensorium = replace(primary_sensorium, retina=tuple(
                    (Fraction(value, 255) * transmission,) * len(times) for value in luminance
                ))
                external_rgb_retina_u8 = transmitted_rgb_retina_u8(sensory.retina_rgb_u8, transmission)

            sources = []
            admissions = []
            has_external_sound = sensory is not None and sensory.pressure_s16le is not None
            if has_external_sound:
                heard_times, legacy, cochleae, external_heard_samples = one_self_hearing_hop(sensory.pressure_s16le)
                if heard_times != PASSIVE_TIMES:
                    raise RuntimeError("external hearing changed its physical clock")
                hearing = replace(primary_sensorium, legacy_ears=(legacy, legacy), cochleae=cochleae)
                if returning is None:
                    primary_sensorium = hearing
                else:
                    sources.append(settle_projected_physical_sensorium(
                        assembly_id=f"guala-lean-external-hearing-{before_native.identity}-{start_tick + 1}",
                        source_times=PASSIVE_TIMES, sensorium=hearing, senses=(PhysicalSense.SOUND,),
                    ))
                    admissions.append([(250, 1000)])
            if pending_pressure is not None:
                pressure, body = bytes(pending_pressure), bytes(pending_body)
                heard_times, legacy, cochleae, self_heard_samples = one_self_hearing_hop(pressure)
                if heard_times != PASSIVE_TIMES:
                    raise RuntimeError("self-hearing changed its physical clock")
                hearing = replace(primary_sensorium, legacy_ears=(legacy, legacy), cochleae=cochleae)
                if returning is None and not has_external_sound:
                    primary_sensorium = hearing
                else:
                    sources.append(settle_projected_physical_sensorium(
                        assembly_id=f"guala-lean-coexisting-self-hearing-{before_native.identity}-{start_tick + 1}",
                        source_times=PASSIVE_TIMES, sensorium=hearing, senses=(PhysicalSense.SOUND,),
                    ))
                    admissions.append([(250, 1000)])
            assembly_id = (
                f"guala-lean-unattended-{before_native.identity}-{start_tick + 1}"
                if returning is None else "guala-lean-native-motor-" + returning.causal_transition_sha256
            )
            primary_episode = (
                settle_physical_sensorium(assembly_id=assembly_id, source_times=times, sensorium=primary_sensorium)
                if returning is None or (not has_external_sound and pending_pressure is None) else settle_projected_physical_sensorium(
                    assembly_id=assembly_id, source_times=times, sensorium=primary_sensorium,
                    senses=tuple(sense for sense in SENSE_ORDER if sense is not PhysicalSense.SOUND),
                )
            )
            sources.insert(0, primary_episode)
            admissions.insert(0, [(250, 1000)])
            if returning is not None:
                for source in returning.sources:
                    sources.append(source.restore(runtime=runtime))
                    admissions.append(list(source.admissions))

            native_started = True
            primary = runtime.advance_coexisting_admitted_interval_unsealed(
                tuple(sources), tuple(admissions),
                guided_vocal_drives=None if sensory is None else sensory.guided_vocal_drives,
                pressure_s16le=None if pending_pressure is None else pressure,
                body_s16le=None if pending_pressure is None else body,
                consumed_sample_count=None if pending_pressure is None else self_heard_samples,
                vestibular_motion=None if returning is None else returning.vestibular,
            )
            lived_tick_delta = runtime.live_organism_tick - start_tick
            if lived_tick_delta != 1:
                raise RuntimeError("physical occurrence did not settle exactly one native interval")
            if primary_prepared is not None:
                with world.prepared_action_visibility_transaction(primary_prepared):
                    world.commit_prepared_action(primary_prepared)
                uncommitted_prepared = None
            if _requires_physical_return(primary):
                successor_axes = tuple(runtime.readiness().articulated_body_axes)
                motor_plan = prepare_motor_consequence(
                    world=world, evidence=primary,
                    predecessor_state_sha256=before_native.state_sha256,
                    predecessor_body_axes=before_axes, successor_body_axes=successor_axes,
                )
                uncommitted_prepared = motor_plan.prepared_world
                after = motor_plan.prepared_world.execution_receipt.after
                next_return = PendingPhysicalReturn.capture(
                    identity=before_native.identity, producer_tick=runtime.live_organism_tick,
                    causal_transition_sha256=primary.causal_transition_sha256,
                    world_revision=after.revision,
                    world_observation_receipt_sha256=after.authority_receipt_sha256,
                    sensorium=motor_plan.sensorium, sources=motor_plan.sources,
                    vestibular=motor_plan.vestibular,
                )
                with world.prepared_action_visibility_transaction(motor_plan.prepared_world):
                    world.commit_prepared_action(
                        motor_plan.prepared_world,
                        expected_physical_return=returning, physical_return=next_return,
                    )
                uncommitted_prepared = None
            elif returning is not None:
                world.consume_physical_return(returning)

            pressure_body = runtime.in_flight_acoustic_pressure_s16le
            self_pressure_pending = pressure_body is not None
            pressure_record = None
            if pressure_body is not None:
                pressure_bytes = bytes(pressure_body)
                if not pressure_bytes or len(pressure_bytes) > MAX_PRESSURE_BYTES or len(pressure_bytes) % 2:
                    raise RuntimeError("native pressure exceeded its transport bound")
                pressure_record = hashlib.sha256(pressure_bytes).hexdigest(), pressure_bytes
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
                    "causal_transition_sha256": primary.causal_transition_sha256,
                    "dsf_delivery_count": primary.dsf_delivery_count,
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
                        if sensory is None or sensory.retina_rgb_u8 is None
                        else len(sensory.retina_rgb_u8) // 3
                    ),
                    "external_retinal_port_count": (
                        0
                        if sensory is None or sensory.retina_rgb_u8 is None
                        else len(primary_sensorium.retina)
                    ),
                    "external_rgb_retinal_u8": external_rgb_retina_u8,
                    "external_sensory_source": (
                        None if sensory is None else sensory.source
                    ),
                    "external_source_receipt_sha256": (
                        None
                        if sensory is None
                        else sensory.source_receipt_sha256
                    ),
                    "physically_transitioned_neuron_count": (
                        primary.physically_transitioned_neuron_count
                    ),
                    "primary_causal_transition_sha256": (
                        primary.causal_transition_sha256
                    ),
                    "python_callback_count": primary.python_callback_count,
                    "requested_world_action": (
                        None if motor_plan is None else motor_plan.requested_action
                    ),
                    "retinal_observer_kind": (
                        "achromatic-u8-projection-of-native-retinal-input"
                    ),
                    "retinal_u8": retinal_u8,
                    "latest_retinal_field_kind": (
                        "external-rgb"
                        if external_rgb_retina_u8 is not None
                        else "achromatic"
                    ),
                    "spectral_retinal_port_count": 0,
                    "spectral_retinal_u8": None,
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
                    "consumed_physical_return_tick": None if returning is None else returning.producer_tick,
                    "pending_physical_return_tick": None if next_return is None else next_return.producer_tick,
                    "physical_return_source_count": 0 if returning is None else len(returning.sources),
                    "vestibular_return_consumed": returning is not None and returning.vestibular is not None,
                    "world_action_refusal": (
                        None if motor_plan is None else motor_plan.refusal_reason
                    ),
                    "world_revision": world_snapshot.revision,
                },
                pressure=pressure_record,
            )
        except BaseException as error:
            if uncommitted_prepared is not None:
                try:
                    world.discard_prepared_action(uncommitted_prepared)
                except BaseException as cleanup_error:
                    raise PhysicalSettlementFailure("physical preparation cleanup failed") from cleanup_error
            if isinstance(error, NativePhysicalInputRefused):
                # No native mutation occurred; pending return remains available.
                raise
            if native_started or returning is not None:
                raise PhysicalSettlementFailure(
                    "physical settlement failed; recover the paired checkpoint, do not continue"
                ) from error
            raise
        return result
