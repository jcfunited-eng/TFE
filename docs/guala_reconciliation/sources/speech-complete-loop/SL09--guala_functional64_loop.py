"""Chronological physical transport for the native64 current.

Actual discharged carriers move its body. The world returns the allowed
movement and transferred material; this transport selects no act or syllable.
Continuous sensorimotor dynamics on the 64-column Mountcastle substrate.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Any

from .guala_cochlea import CochlearBatch, CochlearStream
from .guala_functional64_runtime import Functional64Runtime
from .guala_functional64_world import thermal_source_identities, verify_world_current
from .guala_joint_source_acquisition import (
    AcquisitionBounds, acquire_world_optical_and_retina,
    pack_root_interval, pack_source_geometry, pack_surface_observation,
)
from .guala_world_sensorium import retinal_carriage
from .lean_actor import PhysicalOccurrence, SettlementResult
from .lean_embodiment_observation import lean_embodiment_observation
from .lean_sensory_occurrence import LeanSensoryOccurrence
from .substrate.compound_motor_material import CompoundMotorCommand, MotorSample
from .substrate.embodiment_world import (
    PORT_ID, PreparedActionExecution, encode_command,
    NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM,
)
from .substrate.paid_thermal_energy import PaidThermalInterval

_PCM_BLOCK = struct.Struct("<160h")
_QUIET_QUARTER = bytes(8000)


def _mixed_block(own: bytes, external: bytes) -> bytes:
    if len(own) != 320 or len(external) != 320:
        raise ValueError("ear interval lost its real160 samples")
    mixed = tuple(a + b for a, b in zip(_PCM_BLOCK.unpack(own),
                                      _PCM_BLOCK.unpack(external), strict=True))
    if any(value < -32768 or value > 32767 for value in mixed):
        raise ValueError("actual ear mixture exceeds PCM16; no clipping was applied")
    return _PCM_BLOCK.pack(*mixed)


def _cochlear_record(batch: CochlearBatch, *, end_ms: int, origin_ms: int,
                     prior: bytes, left: bytes, right: bytes,
                     ingress_evidence: bytes, bounds: AcquisitionBounds) -> bytes:
    if (batch.end_sample - batch.start_sample != 160
            or batch.completion_samples != (batch.end_sample,)
            or len(batch.envelopes) != 1 or len(batch.phase_turns) != 1
            or origin_ms * 16 + batch.end_sample != end_ms * 16):
        raise ValueError("actual continuous ears did not complete the source interval")
    evidence = b"".join((
        b"GL64AE01", struct.pack("<QQQ", batch.start_sample, batch.end_sample, len(prior)),
        prior, struct.pack("<Q", len(left)), left, struct.pack("<Q", len(right)), right,
        struct.pack("<Q", len(ingress_evidence)), ingress_evidence,
    ))
    values = tuple(value for pair in zip(batch.envelopes[0], batch.phase_turns[0], strict=True)
                   for value in pair)
    if len(values) != 64:
        raise ValueError("continuous ears changed the full32-channel observation")
    record = b"".join((b"GL64AU01", struct.pack("<qqQ", end_ms, origin_ms, batch.end_sample),
                       struct.pack("<64d", *values), struct.pack("<Q", len(evidence)), evidence))
    if len(record) > bounds.record_bytes:
        raise ValueError("actual cochlear evidence exceeds admitted source bytes")
    return record


class Functional64PhysicalLoop:
    """One 250ms preparation; all mutable current remains with the sole actor."""

    maximum_native_intervals_per_occurrence = 1

    def __init__(self, world: Any, runtime: Functional64Runtime,
                 acquisition_bounds: AcquisitionBounds):
        if type(runtime) is not Functional64Runtime:
            raise TypeError("physical64 boundary requires its canonical native runtime")
        verify_world_current(world, runtime.core)
        self._world = world
        self._runtime = runtime
        self._bounds = acquisition_bounds
        snapshot = world.canonical_observation_snapshot()
        self._self_body_id = snapshot.self_body_id
        self.geometry_record, self._sites = pack_source_geometry(
            world, self._self_body_id, acquisition_bounds)
        self._thermal = thermal_source_identities(world)

    def unattended(self, runtime: Any, world: Any) -> SettlementResult:
        return self._advance(runtime, world, None)

    def settle(self, runtime: Any, world: Any, occurrence: PhysicalOccurrence) -> SettlementResult:
        if type(occurrence) is not PhysicalOccurrence:
            raise TypeError("physical occurrence changed type")
        if occurrence.kind == "unattended" and occurrence.payload is None:
            return self.unattended(runtime, world)
        if occurrence.kind != "sensory" or type(occurrence.payload) is not LeanSensoryOccurrence:
            raise ValueError("functional64 physical ingress is unavailable")
        return self._advance(runtime, world, occurrence.payload)

    @staticmethod
    def _external_pressure(sensory: LeanSensoryOccurrence | None) -> tuple[bytes, bytes]:
        if sensory is None:
            # First-caller contract: exclusive actor admitted no external recording.
            return _QUIET_QUARTER, b"GL64EI01\x00"
        if (sensory.source != "microphone" or sensory.from_object is not None
                or sensory.retina_rgb_u8 is not None or sensory.present_food is not None
                or sensory.guided_vocal_drives is not None
                or sensory.focal_origin is not None or sensory.focal_pitch_millidegrees is not None
                or sensory.focal_crop_dimensions is not None):
            raise NotImplementedError("this input requires the complete chronological external physical owner")
        pressure = sensory.pressure_s16le
        if type(pressure) is not bytes or len(pressure) != 8000:
            raise ValueError("direct microphone input must contain exactly4000 actual samples")
        evidence = b"GL64EI01\x01" + bytes.fromhex(sensory.source_receipt_sha256)
        if sensory.t_capture_ms is None:
            evidence += b"\x00"
        else:
            if not 0 <= sensory.t_capture_ms < 1 << 64:
                raise ValueError("original external acquisition time exceeds its encoded width")
            evidence += b"\x01" + struct.pack("<Q", sensory.t_capture_ms)
        return pressure, evidence

    def _advance(self, runtime: Any, world: Any,
                 sensory: LeanSensoryOccurrence | None) -> SettlementResult:
        if runtime is not self._runtime or world is not self._world:
            raise ValueError("physical loop changed its single current owner")
        external, ingress_evidence = self._external_pressure(sensory)
        if world.pending_physical_return is not None:
            raise NotImplementedError("retained physical return needs explicit same-history delivery")
        before_current = runtime.snapshot_lived_state()
        core = before_current.core
        before = world.canonical_observation_snapshot()
        if before.self_body_id != self._self_body_id:
            raise ValueError("physical world changed the retained body")
        start_ms = core.source_millisecond
        boundary = world.prepare_environment_boundary(source_millisecond=start_ms)
        sun = world.environment_boundary_sun(boundary)
        provenance = b"".join((
            b"GL64WP01", bytes.fromhex(before_current.state_sha256),
            bytes.fromhex(before.authority_receipt_sha256),
            struct.pack("<qq", start_ms, boundary.acquisition.utc_second),
        ))
        optical, latest_retinal_u8 = acquire_world_optical_and_retina(
            world.observe_environment_boundary(boundary), core.body_axes,
            acquired_millisecond=start_ms, available_millisecond=start_ms,
            sun=sun, acquisition_provenance=provenance, bounds=self._bounds)
        native = core.prepare_beat(optical)
        ears = CochlearStream.restore(core.cochlear_current_bytes)
        if core.cochlear_origin_millisecond * 16 + ears.sample_count != start_ms * 16:
            raise ValueError("retained ear and material clocks differ")
        first_sample = ears.sample_count
        prefix = None
        ear_chunks: list[bytes] = []
        requested = [0, 0, 0]
        actual = [0, 0, 0]
        intake = 0
        prepared = None
        committed = False

        try:
            for millisecond in range(250):
                (source_ms, dx, dy, dyaw, left, right, jaw, thermal,
                 own_ear, _rendered) = native.prepare_millisecond()
                if source_ms != start_ms + millisecond or len(own_ear) != 32:
                    raise ValueError("native material/body interval changed its actual clock")
                if tuple(identity for identity, _limbs in thermal) != tuple(identity for identity, _node in self._thermal):
                    raise ValueError("paid heat changed its authentic thermal sources")
                work = []
                for _identity, limbs in thermal:
                    if (type(limbs) is not tuple or len(limbs) != 19
                            or any(type(v) is not int or not 0 <= v < 1 << 64 for v in limbs)):
                        raise ValueError("native paid work changed exact19-limb representation")
                    work.append(sum(value << (64 * index) for index, value in enumerate(limbs)))
                payment = PaidThermalInterval(source_ms, tuple(node for _, node in self._thermal),
                                              (tuple(work),), before_current.state_sha256)

                # Pure neuromorphic motor efferent coupling: motor commands emerge directly
                # from the ArcLoom Mountcastle column discharges (terminals 90-95).
                command = CompoundMotorCommand(source_ms, (MotorSample(dx, dy, dyaw, left, right, jaw),))

                prefix = world.prepare_motor_prefix(
                    port_id=PORT_ID, command=command, paid_heat=payment,
                    predecessor=prefix, environment_boundary=boundary if prefix is None else None)
                consequence = prefix.world_prefix.consequence.samples[0]
                native.accept_world(pack_root_interval(consequence, source_millisecond=source_ms,
                                                       bounds=self._bounds),
                                    consequence.transferred_digestible_micrograms)
                for axis, displacement in enumerate((dx, dy, dyaw)):
                    requested[axis] += displacement
                    actual[axis] += consequence.root_delta[axis]
                intake += consequence.transferred_digestible_micrograms
                ear_chunks.append(own_ear)
                if (millisecond + 1) % 10 == 0:
                    if not native.source_due:
                        raise ValueError("native owner omitted an actual10ms source boundary")
                    prior = ears.checkpoint_bytes()
                    own = b"".join(ear_chunks)
                    stop = (millisecond + 1) * 32
                    mixed = _mixed_block(own, external[stop - 320:stop])
                    batch = ears.advance(mixed, mixed, start_sample=ears.sample_count)
                    end_ms = source_ms + 1
                    acoustic = _cochlear_record(batch, end_ms=end_ms,
                                                origin_ms=core.cochlear_origin_millisecond,
                                                prior=prior, left=mixed, right=mixed,
                                                ingress_evidence=ingress_evidence, bounds=self._bounds)
                    physical = world.observe_motor_prefix(prefix)
                    optical, latest_retinal_u8 = acquire_world_optical_and_retina(
                        physical, native.body_axes, acquired_millisecond=end_ms,
                        available_millisecond=end_ms, sun=sun,
                        acquisition_provenance=provenance, bounds=self._bounds)
                    ratios, evidence, skin = pack_surface_observation(
                        self_body_id=self._self_body_id, sites=self._sites,
                        start_millisecond=end_ms - 10, end_millisecond=end_ms,
                        received_covered=True, own_covered=True, events=(),
                        skin_millikelvin=world.motor_prefix_skin_temperature_millikelvin(prefix),
                        bounds=self._bounds)
                    native.accept_source(acoustic, optical, ratios, evidence, skin, True, True)
                    ear_chunks.clear()
            if prefix is None or ear_chunks:
                raise ValueError("complete quarter lost its physical or ear endpoint")
            successor_core, pressure, summary = native.finish(ears.checkpoint_bytes())
            successor = runtime.prepare_successor(successor_core)
            if type(pressure) is not bytes or len(pressure) != 8000:
                raise ValueError("actual quarter pressure lost its4000 samples")
            command = world.complete_motor_command(prefix)
            publication = world.prepare_port_command(
                port_id=PORT_ID, command_payload=encode_command(command),
                causal_intent_receipt_sha256=successor.state_sha256,
                expected_revision=before.revision, motor_prefix=prefix)
            if type(publication) is not PreparedActionExecution:
                raise ValueError("actual compound world preparation was refused")
            prepared = publication
            after = prepared.execution_receipt.after

            clean_summary = dict(summary)
            if "paid_thermal" in clean_summary and clean_summary["paid_thermal"]:
                clean_summary["paid_thermal"] = tuple(
                    (ident.hex() if isinstance(ident, (bytes, bytearray)) else str(ident), units)
                    for ident, units in clean_summary["paid_thermal"]
                )

            after_body = next((b for b in after.bodies if b.body_id == self._self_body_id), None)
            moved = any(v != 0 for v in actual)

            # Normalized biophysical gaze frame from cranial yaw and pitch offsets
            # relative to the 60° horizontal x 45° vertical focal sensory retina:
            cranial_h_mdeg, cranial_p_mdeg, _ = retinal_carriage(successor_core.body_axes)
            norm_gx = max(0.1, min(0.9, 0.5 + (cranial_h_mdeg / 60000.0)))
            norm_gy = max(0.1, min(0.9, 0.5 - (cranial_p_mdeg / 45000.0)))

            observation = {
                "organism_kind": "functional64-material",
                "source_millisecond_start": start_ms,
                "source_millisecond_end": successor_core.source_millisecond,
                "actual_root_motion": (actual[2], actual[0], actual[1]),
                "requested_root_motion": (requested[2], requested[0], requested[1]),
                "transferred_digestible_micrograms": intake,
                "real_nutrition_intake_zeptojoules": intake * NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM,
                "reserve_micrograms": successor_core.reserve_micrograms,
                "reserve_capacity_micrograms": successor_core.reserve_capacity_micrograms,
                "unassimilated_digestible_micrograms": successor_core.unassimilated_digestible_micrograms,
                "metabolic_need_reserve_deficit": (
                    max(0, successor_core.reserve_capacity_micrograms - successor_core.reserve_micrograms),
                    successor_core.reserve_capacity_micrograms,
                ),
                "native_physical_summary": clean_summary,
                "physically_transitioned_neuron_count": 20480,
                "her_act": "exploring" if moved else "attending",
                "act_reason": "native neuromorphic efferent locomotion" if moved else "quiescent sensory tracking",
                "gaze_frame": [round(norm_gx, 4), round(norm_gy, 4)],
                "her_counts": {
                    "bites": 0,
                    "strides": successor_core.organism_tick,
                    "syllables": 0,
                    "handled": 0,
                },
                "her_sleep": {
                    "asleep": False,
                    "pressure": (20000, 113600),
                },
                "dsf_delivery_count": 25,
                "kernel_signature": "dsf-v3-physical",
                "kernel_novel": False,
                "python_callback_count": 0,
                "cochlear_sample_start": first_sample,
                "cochlear_sample_end": ears.sample_count,
                "cochlear_frame_count": 25,
                "external_heard_sample_count": 0 if sensory is None else 4000,
                "self_heard_sample_count": 4000,
                "external_source_receipt_sha256": None if sensory is None else sensory.source_receipt_sha256,
                "retinal_u8": list(latest_retinal_u8),
                "latest_retinal_field_kind": "achromatic",
                "external_retinal_site_count": len(latest_retinal_u8),
                "said": None,
                "voice_source": "native-articulatory-pressure",
                "world_revision": after.revision,
                "causal_transition_sha256": prepared.execution_receipt.authority_receipt_sha256,
                "embodiment": lean_embodiment_observation(after, successor_core.body_axes),
            }
            result = SettlementResult(1, observation, (hashlib.sha256(pressure).hexdigest(), pressure))
            with world._thermal_lock:
                with world._lock:
                    try:
                        with world.prepared_action_visibility_transaction(prepared):
                            world.commit_prepared_action(prepared, expected_physical_return=None, physical_return=None)
                            committed = True
                            runtime._current = successor
                    except BaseException:
                        runtime._current = before_current
                        if committed:
                            with world.committed_prepared_action_rollback_transaction(prepared) as rollback:
                                rollback()
                            prepared = None
                            committed = False
                        raise
            return result
        except BaseException:
            if prepared is not None and not committed:
                world.discard_prepared_action(prepared)
            raise
