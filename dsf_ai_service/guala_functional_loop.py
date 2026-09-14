"""One beat of the functional organism: senses in, one decision, one world step.

The loop owns nothing: the world validates every act, the organism decides
from its own measured state, and the actor keeps the tick line and custody.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from typing import Any

from dsf_ai_service.guala_caretaker_hand import nothing_left_to_bite, present_food, withdraw
from dsf_ai_service.guala_cochlea import one_self_hearing_hop
from dsf_ai_service.guala_vision_fovea import compute_saccadic_gaze
from dsf_ai_service.guala_functional_organism import (
    BEAT_MICROSECONDS, CAPACITY_MICROGRAMS, Decision, FunctionalOrganism, Sensed,
    cochlear_profile, syllable_pcm,
)
from dsf_ai_service.guala_world_sensorium import (
    _retinal_luminance, prepare_passive_world_interval, retinal_carriage,
)
from dsf_ai_service.lean_actor import (
    MAX_PRESSURE_BYTES, PhysicalOccurrence, PhysicalSettlementFailure, SettlementResult,
)
from dsf_ai_service.lean_embodiment_observation import lean_embodiment_observation
from dsf_ai_service.lean_sensory_occurrence import (
    EXTERNAL_RGB_FOCAL_VALUE_COUNT, LeanSensoryOccurrence, focal_retina_luminance_u8,
    rgb_retina_luminance_u8, transmitted_rgb_retina_u8,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt, NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM,
    PORT_ID, PreparedActionExecution, encode_command,
)
from dsf_ai_service.substrate.w1_physical_receptors import retinal_irradiance_field


MAX_NATIVE_INTERVALS_PER_OCCURRENCE = 1
CAREGIVER_RETRY_BEATS = 16
OFFER_PATIENCE_BEATS = 40  # a toy is held out to her for ten seconds before it is carried home
CAMERA_FIELD_MILLIDEGREES = (60_000, 45_000)  # the declared camera field the page's pitch is measured against
GAZE_RECENTRE = 0.05  # each beat the gaze gives back a twentieth of its offset from the frame's centre
WORLD_RETINAL_SITES = 4935
WORLD_FOCAL_SITES = 4800
WORLD_LEGACY_SITES = 27   # the 9 x 3 coarse field that precedes the wide field
WORLD_WIDE_SITES = 108    # the 18 x 6 wide field over 180 x 90 degrees


def _receipt(value: object) -> str:
    body = json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _self_body(snapshot: Any) -> Any:
    return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)


def _world_retina_u8(snapshot: Any, axes: tuple[Any, ...]) -> tuple[int, ...]:
    heading, pitch, transmission = retinal_carriage(axes)
    pixels = retinal_irradiance_field(
        snapshot, retinal_heading_offset_millidegrees=heading,
        retinal_pitch_offset_millidegrees=pitch, include_focal=True,
    )
    values = []
    for luminance in _retinal_luminance(pixels):
        value = Fraction(luminance) * transmission
        if not Fraction(0) <= value <= Fraction(1):
            raise RuntimeError("retinal observer left its physical range")
        values.append(round(value * 255))
    if len(values) != WORLD_RETINAL_SITES:
        raise RuntimeError("world retina changed its site count")
    return tuple(values)


def _profile(pressure: bytes) -> tuple[tuple[float, ...], int]:
    _times, _legacy, cochleae, consumed = one_self_hearing_hop(pressure)
    return cochlear_profile(cochleae), consumed


def _oral_intake_micrograms(execution: ActionExecutionReceipt) -> int:
    after = _self_body(execution.after)
    contact = getattr(after, "active_contact", None)
    if contact is None or contact.kind != "oral":
        return 0
    return sum(int(value) for value in contact.dissolved_tastant_micrograms)


def _gaze_frame(sensory: Any, gaze: tuple[float, float]) -> list[float]:
    """Her gaze in the camera frame. The page sends the whole frame held still
    (its field is the declared camera field), so her gaze within the field is
    her gaze in the frame. A page that still sends a narrower crop gets the
    older law: a bounded step from the crop's origin toward the structure she
    saw, then a small pull back toward the frame's centre."""

    crop_fraction = (
        (sensory.focal_pitch_millidegrees[0] / CAMERA_FIELD_MILLIDEGREES[0],
         sensory.focal_pitch_millidegrees[1] / CAMERA_FIELD_MILLIDEGREES[1])
        if sensory.focal_pitch_millidegrees else (80 / 640.0, 60 / 480.0)
    )
    if crop_fraction[0] >= 1.0 and crop_fraction[1] >= 1.0:
        return [round(value, 4) for value in gaze]
    stepped = compute_saccadic_gaze(tuple(sensory.focal_origin), gaze, crop_fraction=crop_fraction)
    return [round(value + (0.5 - value) * GAZE_RECENTRE, 4) for value in stepped]


def _said(drive: tuple[int, int, int]) -> str:
    """The syllable as letters (onset + vowel) and its pitch, for the page."""

    from dsf_ai_service.guala_voice import ONSETS, VOWELS

    pitch, vowel, onset = drive
    return f"{ONSETS[onset]}{VOWELS[vowel][0]} at {pitch / 10:.0f} Hz"


def _caregiver_withdrawal(organism: FunctionalOrganism, world: Any) -> dict[str, object] | None:
    """The caregiver's law after a meal: when she is not feeding, or what is
    held out has nothing left to bite, the caregiver carries it home to the
    hallway, out of every doorway, and tidies eaten cores out of doorway
    approaches. One bounded stretch per beat; after a stretch that did not
    finish, it waits a few beats before the next. Never moves her."""

    tick = organism.live_organism_tick
    if tick < int(organism._state.get("caregiver_retry_tick", 0)):
        return None
    snapshot = world.observation_snapshot()
    her = next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
    others = tuple(body for body in snapshot.bodies if body.body_id != snapshot.self_body_id)
    if len(others) != 1:
        return None
    person = others[0]
    if person.held_object_id is not None:
        held = next((item for item in snapshot.objects if item.object_id == person.held_object_id), None)
        if held is not None and not held.object_id.startswith("apple"):
            # A toy held out to her: the caregiver keeps offering it for a
            # while; if she does not take it, it is carried home and set down.
            since = organism._state.get("offer_since_tick")
            if since is None:
                organism._state["offer_since_tick"] = tick
                return None
            if tick - int(since) < OFFER_PATIENCE_BEATS:
                return None
        else:
            meal_over = not organism.feeding or held is None or held.material is None or nothing_left_to_bite(her, held)
            if not meal_over:
                return None
        contact = getattr(her, "active_contact", None)
        if contact is not None and contact.object_id == person.held_object_id:
            return None  # her mouth or hand is still on it; her next own act clears the contact, then the caregiver steps back
    else:
        organism._state["offer_since_tick"] = None
    record = withdraw(world)
    if record is not None and not (record["home"] or record["fetched"]):
        organism._state["caregiver_retry_tick"] = tick + CAREGIVER_RETRY_BEATS
    return record


def _apply(world: Any, decision: Decision, before: Any) -> tuple[PreparedActionExecution, str, str | None, list[str]]:
    """Offer her commands to the world in order; the first the world accepts
    is prepared. When every one is refused, or she has none, the world only
    advances time."""

    refused = []
    for command in decision.commands:
        intent = _receipt({
            "act": decision.act, "reason": decision.reason, "schema": "guala.functional_act_intent.v1",
            "target": decision.target_object_id, "world_revision": before.revision,
            "world_state_before_sha256": before.state_sha256,
        })
        prepared = world.prepare_port_command(
            port_id=PORT_ID, command_payload=encode_command(command),
            causal_intent_receipt_sha256=intent, expected_revision=before.revision,
        )
        if isinstance(prepared, ActionExecutionReceipt):
            refused.append(prepared.reason)
            continue
        if not isinstance(prepared, PreparedActionExecution):
            raise RuntimeError("functional act lost prepared custody")
        return prepared, decision.act, None, refused
    prepared = prepare_passive_world_interval(world)
    return prepared, ("refused" if decision.commands else "body"), (refused[-1] if refused else None), refused


class FunctionalPhysicalLoop:
    """The physical settlement boundary for the functional organism."""

    @property
    def maximum_native_intervals_per_occurrence(self) -> int:
        return MAX_NATIVE_INTERVALS_PER_OCCURRENCE

    def settle(self, runtime: Any, world: Any, occurrence: PhysicalOccurrence) -> SettlementResult:
        if occurrence.kind == "unattended" and occurrence.payload is None:
            return self._advance(runtime, world, None)
        if occurrence.kind == "sensory" and isinstance(occurrence.payload, LeanSensoryOccurrence):
            return self._advance(runtime, world, occurrence.payload)
        raise ValueError("functional physical ingress kind is not mounted")

    def unattended(self, runtime: Any, world: Any) -> SettlementResult:
        return self._advance(runtime, world, None)

    def _advance(self, organism: FunctionalOrganism, world: Any, sensory: LeanSensoryOccurrence | None) -> SettlementResult:
        if not isinstance(organism, FunctionalOrganism):
            raise TypeError("functional loop needs the functional organism")
        start_tick = organism.live_organism_tick
        returning = world.pending_physical_return
        prepared = None
        presentation = None
        withdrawal = None
        try:
            if sensory is not None and sensory.present_food is not None:
                presentation = present_food(world, sensory.present_food)
                returning = world.pending_physical_return
            withdrawal = _caregiver_withdrawal(organism, world)
            if withdrawal is not None:
                returning = world.pending_physical_return
            before = world.observation_snapshot()
            axes = organism.body_axes
            world_retina = _world_retina_u8(before, axes)
            external_rgb = None
            focal = world_retina[-WORLD_FOCAL_SITES:]
            source = "world"
            external_sites = 0
            if sensory is not None and sensory.retina_rgb_u8 is not None:
                _heading, _pitch, transmission = retinal_carriage(axes)
                external_rgb = transmitted_rgb_retina_u8(sensory.retina_rgb_u8, transmission)
                external_sites = len(sensory.retina_rgb_u8) // 3
                camera_focal = focal_retina_luminance_u8(external_rgb)
                if len(sensory.retina_rgb_u8) == EXTERNAL_RGB_FOCAL_VALUE_COUNT and camera_focal:
                    focal = tuple(camera_focal)
                else:
                    focal = tuple(rgb_retina_luminance_u8(external_rgb))
                source = "camera"
            heard_profile = None
            external_heard = 0
            if sensory is not None and sensory.pressure_s16le is not None:
                heard_profile, external_heard = _profile(sensory.pressure_s16le)
            self_profile = None
            self_heard = 0
            own_voice = organism.pending_voice
            if own_voice is not None:
                self_profile, self_heard = _profile(own_voice)
            # The wide field (18 x 6 sites carried by her head) aims her head;
            # it is the world eye's, whichever source fills the focal field.
            wide = tuple(world_retina[WORLD_LEGACY_SITES:WORLD_LEGACY_SITES + WORLD_WIDE_SITES])
            sensed = Sensed(before, focal, source, heard_profile, self_profile, wide)
            decision = organism.decide(sensed)
            prepared, applied, refusal, refused = _apply(world, decision, before)
            execution = prepared.execution_receipt
            intake = _oral_intake_micrograms(execution) if applied == "bite" else 0
            with world.prepared_action_visibility_transaction(prepared):
                world.commit_prepared_action(prepared, expected_physical_return=returning, physical_return=None)
            prepared = None
            spoke = syllable_pcm(decision.drive, start_tick) if decision.drive is not None else None
            if spoke is not None and (len(spoke) > MAX_PRESSURE_BYTES or len(spoke) % 2):
                raise RuntimeError("her voice exceeded its transport bound")
            organism.commit(
                decision, applied_action=applied, refusal=refusal, intake_micrograms=intake, spoke=spoke,
                heard_profile=heard_profile, self_profile=self_profile, tick_now=start_tick,
            )
            if organism.live_organism_tick != start_tick + 1:
                raise RuntimeError("functional beat did not advance exactly one tick")
            after = world.observation_snapshot()
            before_body, after_body = _self_body(before), _self_body(after)
            motion = (
                (after_body.pose.heading_millidegrees - before_body.pose.heading_millidegrees + 180_000) % 360_000 - 180_000,
                after_body.pose.position.x - before_body.pose.position.x,
                after_body.pose.position.y - before_body.pose.position.y,
            )
            deficit = organism.deficit
            observation = {
                "actual_root_motion": motion,
                "act_reason": decision.reason,
                "body_consequence_count": 0,
                "caregiver_presentation": presentation,
                "caregiver_withdrawal": withdrawal,
                "causal_transition_sha256": execution.authority_receipt_sha256,
                "dsf_delivery_count": decision.gate_count,
                "embodiment": lean_embodiment_observation(after, axes),
                "external_guided_vocal_axis_count": 0,
                "external_heard_sample_count": external_heard,
                "external_retinal_port_count": external_sites,
                "external_retinal_site_count": external_sites,
                "external_rgb_retinal_u8": None if external_rgb is None else list(external_rgb),
                "external_sensory_source": None if sensory is None else sensory.source,
                # Her gaze within the focal field (horizontal, vertical fractions),
                # the luminance-weighted centre of what she last saw; the page's
                # camera crop follows this, never the other way round (A1's lane).
                "gaze_focal": None if organism.gaze is None else list(organism.gaze),
                "gaze_focal_source": source,
                # Frame-relative gaze (A1's vision lane): the page says where its
                # crop came from (focal_origin, a frame fraction) and how wide it
                # is in angle (focal_pitch_millidegrees); her gaze within the crop
                # moves the next crop by a bounded step, never a jump. The crop's
                # share of the frame is its pitch over the declared camera field.
                "gaze_frame": (
                    None
                    if sensory is None or sensory.focal_origin is None or organism.gaze is None
                    else _gaze_frame(sensory, organism.gaze)
                ),
                "external_source_receipt_sha256": None if sensory is None else sensory.source_receipt_sha256,
                "her_act": decision.act,
                "her_counts": organism.counts,
                "her_sleep": organism.sleep,
                "kernel_novel": decision.novel,
                "kernel_signature": decision.signature,
                "latest_retinal_field_kind": "external-rgb" if external_rgb is not None else "achromatic",
                "metabolic_need_reserve_deficit": [deficit.numerator, deficit.denominator],
                "metabolic_need_thermal_load": [0, 1],
                "organism_kind": "functional",
                "physically_transitioned_neuron_count": 0,
                "primary_causal_transition_sha256": execution.authority_receipt_sha256,
                "python_callback_count": 0,
                "real_nutrition_intake_zeptojoules": intake * NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM,
                "requested_root_motion": motion,
                "requested_world_action": applied,
                "reserve_micrograms": organism.reserve_micrograms,
                "reserve_capacity_micrograms": CAPACITY_MICROGRAMS,
                "retinal_observer_kind": "achromatic-u8-projection-of-world-light",
                "retinal_u8": list(world_retina),
                "said": None if decision.drive is None else _said(decision.drive),
                "said_drive": None if decision.drive is None else list(decision.drive),
                "seen": [thing.object_id for thing in decision.seen],
                "self_heard_sample_count": self_heard,
                "self_pressure_pending": spoke is not None,
                "spectral_retinal_port_count": 0,
                "spectral_retinal_u8": None,
                "vocal_founder_refusal_count": 0,
                "world_action_refusal": refusal,
                "world_action_refusals_tried": refused,
                "world_revision": after.revision,
            }
            pressure = None if spoke is None else (hashlib.sha256(spoke).hexdigest(), spoke)
            return SettlementResult(native_interval_count=1, observation=observation, pressure=pressure)
        except BaseException as error:
            if prepared is not None:
                try:
                    world.discard_prepared_action(prepared)
                except BaseException as cleanup_error:
                    raise PhysicalSettlementFailure("physical preparation cleanup failed") from cleanup_error
            raise PhysicalSettlementFailure("functional beat failed; recover the paired checkpoint") from error


__all__ = ("FunctionalPhysicalLoop", "MAX_NATIVE_INTERVALS_PER_OCCURRENCE")
