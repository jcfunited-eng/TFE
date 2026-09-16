"""One beat of the functional organism: senses in, one decision, one world step.

The loop owns nothing: the world validates every act, the organism decides
from its own measured state, and the actor keeps the tick line and custody.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib

import numpy as np
import json
from typing import Any

from dsf_ai_service.guala_acoustic_gate import frames_of_cochleae
from dsf_ai_service.guala_caretaker_hand import nothing_left_to_bite, present_food, withdraw
from dsf_ai_service.guala_cochlea import one_self_hearing_hop
from dsf_ai_service.guala_vision_fovea import compute_saccadic_gaze
from dsf_ai_service.guala_functional_organism import (
    BEAT_MICROSECONDS, CAPACITY_MICROGRAMS, Decision, FunctionalOrganism, Sensed,
    _distance_mm, _region_of, cochlear_profile, door_crossing, syllable_pcm,
)
from dsf_ai_service.guala_world_sensorium import (
    _retinal_luminance, _sun_of, prepare_passive_world_interval, retinal_carriage,
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
import audioop
from fractions import Fraction


MAX_NATIVE_INTERVALS_PER_OCCURRENCE = 1
CAREGIVER_RETRY_BEATS = 16
OFFER_PATIENCE_BEATS = 40  # a toy is held out to her for ten seconds before it is carried home
READING_PATIENCE_BEATS = 128  # read to, the caregiver stays beside her this long after the reader's last word
# Sound from a thing in her world reaches her ears by the room's geometry: at one
# metre it is what the recording is; farther, it falls as one over the distance
# (sound pressure in the open); from another room it comes by the doorway, the
# path bent through the door, and a quarter of it (twelve decibels) gets through.
SOUND_REFERENCE_MM = 1_000
SOUND_THROUGH_DOOR = Fraction(1, 4)
CAMERA_FIELD_MILLIDEGREES = (60_000, 45_000)  # the declared camera field the page's pitch is measured against
GAZE_RECENTRE = 0.05  # each beat the gaze gives back a twentieth of its offset from the frame's centre
WORLD_RETINAL_SITES = 19335
PUPIL_GAIN_MAX = 16.0   # a pupil's range in area, about sixteen to one
PUPIL_MID_RANGE = 0.5   # the field's median light the pupil aims at, as a fraction of full
WORLD_FOCAL_SITES = 19200
WORLD_LEGACY_SITES = 27   # the 9 x 3 coarse field that precedes the wide field
WORLD_WIDE_SITES = 108    # the 18 x 6 wide field over 180 x 90 degrees
WORLD_FOCAL_VALUES = WORLD_FOCAL_SITES * 3
WORLD_RETINAL_VALUES = WORLD_RETINAL_SITES * 3


def _receipt(value: object) -> str:
    body = json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _self_body(snapshot: Any) -> Any:
    return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)


def _world_retina_u8(snapshot: Any, axes: tuple[Any, ...], sun: tuple[float, float, float, int] | None = None, pupil: bool = True) -> tuple[int, ...]:
    """Her world retina at this beat in full RGB colour: 3 channels per site across all
    19,335 sites (58,005 values). Red = mean(bands 0, 1), Green = mean(bands 2, 3),
    Blue = mean(bands 4, 5)."""

    heading, pitch, transmission = retinal_carriage(axes)
    pixels = retinal_irradiance_field(
        snapshot, retinal_heading_offset_millidegrees=heading,
        retinal_pitch_offset_millidegrees=pitch, include_focal=True, sun=sun,
    )
    # Every site's six bands at once: red is the mean of bands 0 and 1, green of 2 and 3,
    # blue of 4 and 5, at the retina's eight-bit grain through the eyelid's transmission.
    bands = np.array(pixels, dtype=np.float64)                         # sites x 6 (exact fractions become floats here, once)
    rgb = np.stack(((bands[:, 0] + bands[:, 1]) / 2.0, (bands[:, 2] + bands[:, 3]) / 2.0, (bands[:, 4] + bands[:, 5]) / 2.0), axis=1)
    if rgb.min() < 0.0 or rgb.max() > 1.0:
        raise RuntimeError("retinal observer left its physical range")
    # THE PUPIL LAW: in a dark room the pupil opens, up to sixteen times, so that the
    # field's middle light sits at mid-range; in a bright one it closes to one. Declared
    # once, decided by this beat's field alone (no state), the same field twice gives the
    # same gain; what the light does not reach stays dark, what is bright clips at full.
    middle = float(np.median(rgb))
    gain = 1.0 if (not pupil or middle <= 0.0) else min(PUPIL_GAIN_MAX, max(1.0, PUPIL_MID_RANGE / middle))
    values = np.rint(np.minimum(1.0, rgb * gain) * (255.0 * float(transmission))).astype(np.int64).reshape(-1).tolist()
    if len(values) != WORLD_RETINAL_VALUES:
        raise RuntimeError("world retina changed its site count")
    return tuple(values)


def _hearing(pressure: bytes) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...], int]:
    """One transduction of a sound at her ear: the hop's peak profile (her streams)
    and its 25 frames (her acoustic gate, Level 1)."""

    _times, _legacy, cochleae, consumed = one_self_hearing_hop(pressure)
    return cochlear_profile(cochleae), frames_of_cochleae(cochleae), consumed


def _profile(pressure: bytes) -> tuple[tuple[float, ...], int]:
    """Her own voice heard back: the profile alone (its frames open no event)."""

    profile, _frames, consumed = _hearing(pressure)
    return profile, consumed


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


def _thing_sound_gain(snapshot: Any, object_id: str) -> tuple[Fraction, int | None, str]:
    """How much of a thing's sound reaches her ears: (gain, distance in mm, path).
    The thing must be in her world; in her room the gain is one metre over the
    distance, capped at one; from another room the path goes through the doorway
    between them and a quarter of the sound gets through; no thing, no sound."""

    her = _self_body(snapshot)
    thing = next((item for item in snapshot.objects if item.object_id == object_id), None)
    if thing is None:
        # A body's voice (the caregiver's) sounds from where the body stands, by the same geometry.
        speaker = next((body for body in snapshot.bodies if body.body_id == object_id and body.body_id != snapshot.self_body_id), None)
        if speaker is None:
            return Fraction(0), None, "absent"
        position, radius_mm = speaker.pose.position, speaker.radius_mm
    else:
        position, radius_mm = thing.position, thing.radius_mm
        if position is None:
            holder = next((body for body in snapshot.bodies if body.body_id == thing.held_by_body_id), None)
            if holder is None:
                return Fraction(0), None, "absent"
            position = holder.pose.position
    her_region = _region_of(snapshot, her.pose.position, her.radius_mm)
    thing_region = _region_of(snapshot, position, radius_mm)
    if her_region is None or thing_region is None or her_region.region_id == thing_region.region_id:
        distance = max(1, int(round(_distance_mm(her.pose.position, position))))
        return min(Fraction(1), Fraction(SOUND_REFERENCE_MM, distance)), distance, "room"
    doors = [portal for portal in snapshot.portals if her_region.region_id in portal.region_ids and thing_region.region_id in portal.region_ids]
    if not doors:
        return Fraction(0), None, "no-door"
    best = None
    for portal in doors:
        before_door, past_door = door_crossing(snapshot, portal, her_region.region_id)
        path = _distance_mm(her.pose.position, before_door) + _distance_mm(before_door, past_door) + _distance_mm(past_door, position)
        if best is None or path < best:
            best = path
    distance = max(1, int(round(best)))
    return min(Fraction(1), Fraction(SOUND_REFERENCE_MM, distance)) * SOUND_THROUGH_DOOR, distance, "door"


def _caregiver_withdrawal(organism: FunctionalOrganism, world: Any) -> dict[str, object] | None:
    """The caregiver's law after a meal: when she is not feeding, or what is
    held out has nothing left to bite, the caregiver carries it home to the
    hallway, out of every doorway, and tidies eaten cores out of doorway
    approaches. One bounded stretch per beat; after a stretch that did not
    finish, it waits a few beats before the next. Never moves her."""

    tick = organism.live_organism_tick
    if tick < int(organism._state.get("caregiver_retry_tick", 0)):
        return None
    if tick < int(organism._state.get("reading_until_tick", 0)):
        return None   # being read to: the caregiver stays with the book beside her
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
                # The caregiver's act is not her beat: whatever goes wrong in it is a
                # refused presentation on the record, never the end of her.
                try:
                    presentation = present_food(world, sensory.present_food)
                except Exception as error:  # noqa: BLE001
                    presentation = {"object_id": sensory.present_food, "presented": False, "took_away": None, "delivered": None,
                                    "schema": "guala.caregiver_presentation.v1",
                                    "steps": [{"operation": "presentation", "reason": f"failed: {type(error).__name__}: {error}"[:200], "to": None}]}
                returning = world.pending_physical_return
            # The caregiver does not walk home on the beat it touched her; whether it
            # stays (holding on, beat after beat) or leaves is the caretaker's to give.
            if (presentation or {}).get("reading"):
                # Read to: the caregiver keeps the book beside her while the reading lasts.
                organism._state["reading_until_tick"] = start_tick + READING_PATIENCE_BEATS
            withdrawal = None
            if not (presentation or {}).get("touched"):
                try:
                    withdrawal = _caregiver_withdrawal(organism, world)
                except Exception as error:  # noqa: BLE001
                    withdrawal = {"schema": "guala.caregiver_withdrawal.v1", "set_down": None, "home": False, "fetched": None, "binned": None,
                                  "steps": [{"operation": "withdrawal", "reason": f"failed: {type(error).__name__}: {error}"[:200], "to": None}]}
                returning = world.pending_physical_return
            if withdrawal is not None:
                returning = world.pending_physical_return
            before = world.observation_snapshot()
            axes = organism.body_axes
            world_retina = _world_retina_u8(before, axes, _sun_of(world))
            external_rgb = None
            focal = world_retina[-WORLD_FOCAL_VALUES:]
            source = "world"
            external_sites = 0
            if sensory is not None and sensory.retina_rgb_u8 is not None:
                _heading, _pitch, transmission = retinal_carriage(axes)
                external_rgb = transmitted_rgb_retina_u8(sensory.retina_rgb_u8, transmission)
                external_sites = len(sensory.retina_rgb_u8) // 3
                if len(sensory.retina_rgb_u8) == EXTERNAL_RGB_FOCAL_VALUE_COUNT:
                    # The camera frame carries the 135 ambient sites first, then the 80 x 60 focal
                    # field (14,805 values); the focal part is tiled 2 x 2 into her 160 x 120 field.
                    arr = np.array(external_rgb[-80 * 60 * 3:], dtype=np.uint8).reshape(60, 80, 3)
                    scaled = np.repeat(np.repeat(arr, 2, axis=0), 2, axis=1).ravel()
                    focal = tuple(int(v) for v in scaled)
                elif len(external_rgb) == WORLD_FOCAL_VALUES:
                    focal = tuple(external_rgb)
                else:
                    focal = tuple(external_rgb)
                source = "camera"
            heard_profile = None
            heard_frames: tuple[tuple[float, ...], ...] = ()
            external_heard = 0
            room_sound = None
            if sensory is not None and sensory.pressure_s16le is not None:
                pressure = sensory.pressure_s16le
                if sensory.from_object is not None:
                    gain, distance_mm, path = _thing_sound_gain(before, sensory.from_object)
                    room_sound = {"from": sensory.from_object, "gain": round(float(gain), 6), "distance_mm": distance_mm, "path": path}
                    pressure = audioop.mul(pressure, 2, float(gain)) if gain > 0 else None
                if pressure is not None:
                    heard_profile, heard_frames, external_heard = _hearing(pressure)
            self_profile = None
            own_frames: tuple[tuple[float, ...], ...] = ()
            self_heard = 0
            own_voice = organism.pending_voice
            if own_voice is not None:
                self_profile, own_frames, self_heard = _hearing(own_voice)
            # The wide field (18 x 6 sites carried by her head) aims her head;
            # it is the world eye's, whichever source fills the focal field.
            wide_raw = world_retina[WORLD_LEGACY_SITES * 3:(WORLD_LEGACY_SITES + WORLD_WIDE_SITES) * 3]
            wide = tuple((wide_raw[i * 3] + wide_raw[i * 3 + 1] + wide_raw[i * 3 + 2]) // 3 for i in range(WORLD_WIDE_SITES))
            # Her skin this beat: the fraction of her mounted skin another body pressed
            # (from the caregiver's touch settled above) and her cutaneous temperature.
            skin_contact = 0.0
            contacts = (presentation or {}).get("contacts") or []
            if contacts:
                sites = world.body_surface_sites_for(before.self_body_id)
                skin_area = sum(4 * site.half_extent_u_micrometres * site.half_extent_v_micrometres for site in sites)
                if skin_area > 0:
                    skin_contact = min(1.0, sum(int(c.get("area_um2", 0)) for c in contacts) / float(skin_area))
            read_skin = getattr(world, "self_skin_temperature_millikelvin", None)
            skin_mk = None if read_skin is None else int(read_skin())
            touch_mk = max((int(c["surface_millikelvin"]) for c in contacts if c.get("surface_millikelvin") is not None), default=None)
            sensed = Sensed(before, focal, source, heard_profile, self_profile, wide, skin_contact, skin_mk, touch_mk, heard_frames=heard_frames, own_frames=own_frames)
            decision = organism.decide(sensed)
            prepared, applied, refusal, refused = _apply(world, decision, before)
            execution = prepared.execution_receipt
            intake = _oral_intake_micrograms(execution) if applied == "bite" else 0
            own_contact = 0.0
            own_contact_mk = None
            if applied == "reach_hand":
                # Her palm on the caregiver's hand: the skin of hers that met skin, as a fraction of her skin.
                sites = {site.site_id: site for site in world.body_surface_sites_for(before.self_body_id)}
                skin_area = sum(4 * site.half_extent_u_micrometres * site.half_extent_v_micrometres for site in sites.values())
                touched = 0
                for contact in world.body_surface_contacts_for_prepared_action(prepared):
                    physical = contact.physical
                    for body_id, site_id in ((physical.body_a_id, physical.site_a_id), (physical.body_b_id, physical.site_b_id)):
                        if body_id == before.self_body_id and site_id in sites:
                            touched += 4 * sites[site_id].half_extent_u_micrometres * sites[site_id].half_extent_v_micrometres
                own_contact = min(1.0, touched / float(skin_area)) if skin_area > 0 else 0.0
                # The caregiver's skin at its declared temperature (the site she reached).
                other_sites = {site.site_id: site for body_id in (b.body_id for b in before.bodies if b.body_id != before.self_body_id) for site in world.body_surface_sites_for(body_id)}
                for command in decision.commands:
                    for actuation in getattr(command, "actuations", ()):
                        site = other_sites.get(actuation.recipient_site_id)
                        if site is not None:
                            own_contact_mk = int(site.reference_temperature_millikelvin)
                            break
                    if own_contact_mk is not None:
                        break
            with world.prepared_action_visibility_transaction(prepared):
                world.commit_prepared_action(prepared, expected_physical_return=returning, physical_return=None)
            prepared = None
            spoke = syllable_pcm(decision.drive, start_tick) if decision.drive is not None else None
            if spoke is not None and (len(spoke) > MAX_PRESSURE_BYTES or len(spoke) % 2):
                raise RuntimeError("her voice exceeded its transport bound")
            organism.commit(
                decision, applied_action=applied, refusal=refusal, intake_micrograms=intake, spoke=spoke,
                heard_profile=heard_profile, self_profile=self_profile, tick_now=start_tick, contact_fraction=own_contact,
                contact_millikelvin=own_contact_mk,
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
                "room_sound": room_sound,
                "her_skin": {"contact": organism.contact["felt"], "temperature_millikelvin": skin_mk, "met_millikelvin": getattr(organism, "_met_mk", None),
                             "touched": (presentation or {}).get("touched"), "need": organism.contact["pressure"]},
                "her_ear": organism.ear,
                "her_eye": organism.eye,
                "her_moment": organism.moment,
                "kernel_novel": decision.novel,
                "kernel_signature": decision.signature,
                "latest_retinal_field_kind": "external-rgb" if external_rgb is not None else "world-rgb",
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
