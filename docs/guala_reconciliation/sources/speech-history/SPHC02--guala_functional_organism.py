"""Legacy functional controller under cognition replacement.

This controller contains reduced per-stream field signatures, bounded semantic
stores and authored action-selection mechanisms. It is NOT the canonical
full-joint-field physical neuron or proof of grounded speech/autonomy.
Unsupported full-field formation refuses explicitly.

The continuous cochlear receptor now has bounded state in this ordinary body
checkpoint. That sensory correction does not certify the remaining controller,
transfer old memories into physical neurons, or authorize a production cutover.
"""

from __future__ import annotations

import base64
import copy
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import heapq
import json
import math
import struct
from typing import Any, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

from dsf_ai_service.substrate.guala_sensorimotor_mesh import GualaSensorimotorMesh
from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate
from dsf_ai_service.substrate.ternary_multimodal_substrate import (
    TernaryMultiModalSubstrate,
    VISUAL_START, VISUAL_END,
    AUDITORY_START, AUDITORY_END,
    SOMATIC_START, SOMATIC_END,
    EFFERENT_START, EFFERENT_END,
    TOTAL_NODES,
)
from dsf_ai_service.guala_cochlea import CochlearBatch, CochlearStream
from dsf_ai_service.guala_acoustic_gate import (   # her ear's declared numbers live with the gate, once
    EAR_BAND_CHANNELS, EAR_BANDS, FRAMES_PER_HOP, GRAIN, HEARD_ENERGY_FLOOR, KERNEL_MINIMUM, PAUSE_FRAMES, SILENT_FRAME, STREAM_FLOOR, gate_step,
)
from dsf_ai_service.guala_eye_figure import FOCAL_COLUMNS, FOCAL_ROWS, Figure, figure_of_disc   # her focal field's size lives with the eye, once
from dsf_ai_service.substrate.exact_lattice_rotation import rotate_lattice_offset
from dsf_ai_service.guala_caretaker_hand import (
    _approach_point, _distance_mm, _heading_toward, _portal_points, _portal_route, _region_of,
    nothing_left_to_bite, offered_within_reach,
)
from dsf_ai_service.episodic_binding_engine import (
    compute_somatic_salience,
    evaluate_anticipatory_consequence,
    find_supported_continuation,
    should_consolidate,
    retained_episode_keys,
    bound_retained_episode,
    bound_waking_moments,
    consecutive_motor_trials,
    qualifies_for_retention,
)
from dsf_ai_service.guala_voice import ONSETS, PITCHES_DECIHERTZ, VOWELS, syllable_pcm as airway_syllable_pcm
from dsf_ai_service.substrate.embodiment_world import (
    BodySurfaceActuation, BodySurfaceContactCommand,
    GraspContactCommand, MoveCommand, OralContactCommand, PoseMM, PositionMM,
    ReleaseHeldObjectCommand, TakeContactHeldObjectCommand, TouchContactCommand, _derived_contact_patch_square_mm, _receptor_position,
    rotate_lattice_offset, _floor_discs_overlap, _is_bed, _is_contained_or_seated, _straight_path_intersects_disc,
)


SCHEMA = "guala.functional_organism.v1"
MAGIC = b"GLFUNC01"
BEAT_MICROSECONDS = 250_000

# Metabolism: her reserve is matter she has eaten, in micrograms at the world's
# declared tastant masses (one apple is 167,400 micrograms). A full reserve is
# three apples; the basal burn alone empties it in about 166,000 beats, a day
# at the live rate of two beats a second, so a night's sleep at basal does not
# wake her hungry (Joe: awake twelve hours, asleep eight, resting and eating
# the rest); acts cost multiples of the basal burn, so a day of striding needs
# meals.
CAPACITY_MICROGRAMS = 500_000
BASAL_BURN_MICROGRAMS = 3
ACT_BURN_MULTIPLE = {
    "rest": 0, "sleep": 0, "bite": 2, "grasp": 2, "take": 2, "release": 1, "touch": 1, "turn_left": 1, "turn_right": 1,
    "step": 4, "toward_food": 4, "toward_bed": 4, "toward_thing": 4, "toward_door": 4, "toward_person": 4, "reach_hand": 1, "say": 2,
}
MOVES = ("step", "toward_food", "toward_bed", "toward_thing", "toward_door", "toward_person")
HUNGRY_BELOW = Fraction(3, 5)   # feeding starts below 60 percent of capacity
SATED_ABOVE = Fraction(17, 20)  # feeding ends at 85 percent (one apple from hungry)

# Sight: what her eyes can resolve as a thing — within her field of view and
# range, on the floor of her own room.
FIELD_OF_VIEW_MILLIDEGREES = 60_000
SIGHT_RANGE_MM = 4_000
STRUCTURE_FLOOR = FOCAL_COLUMNS * FOCAL_ROWS * 4   # total edge energy below this (about four levels per site) is a flat field
# Her head: the wide field (18 x 6 sites over 180 x 90 degrees, carried by the
# head) aims the focal cone. Each beat the head pitches a bounded step toward
# the height of structure in the wide field, so what lies on the floor around
# her comes into the focal cone instead of the blank wall at head height; with
# no structure anywhere it eases back toward level. The head does not yaw: the
# body turns toward what she goes to, and a head chasing the mean of everything
# in a half circle swung to its stop and stayed there.
WIDE_COLUMNS = 18
WIDE_ROWS = 6
WIDE_FLOOR = WIDE_COLUMNS * WIDE_ROWS * 4
WIDE_FIELD_MILLIDEGREES = (180_000, 90_000)
HEAD_STEP_MILLIDEGREES = 5_000         # at most five degrees of pitch per beat
HEAD_SETTLE_MILLIDEGREES = 3_000       # closer than this to the structure height the head holds still
HEAD_YAW_BOUND_MILLIDEGREES = 75_000
# Her neck pitches seventy degrees (Joe's word, 2026-09-15): at forty-five she was blind to
# her own hand, which lies sixty-seven degrees below her eye line at her grip's reach.
HEAD_PITCH_BOUND_MILLIDEGREES = 70_000
# Her head follows what she acts on (a body law, declared once, like the head's step toward
# structure): the thing she moves toward, reaches for, touches, holds or bites; her gaze in
# the focal field is that thing's place by the world's own site geometry (three quarters of a
# degree a site, sixty by forty-five degrees), and the figure under her gaze is the thing.
FOCAL_SITE_MILLIDEGREES = 375
FOCAL_FIELD_MILLIDEGREES = (FOCAL_COLUMNS * FOCAL_SITE_MILLIDEGREES, FOCAL_ROWS * FOCAL_SITE_MILLIDEGREES)
FIGURE_RECORD_CAPACITY = 4096
# Her eyes turn in her head within their declared range in one beat (a saccade is far
# quicker than a beat), taking up what the neck's step has not yet reached; the retina
# rides the neck and the eyes together, never further down or up than straight.
EYE_BOUND_MILLIDEGREES = 45_000
CARRIAGE_PITCH_BOUND_MILLIDEGREES = 90_000

# Her acts are chosen from her own record, not by rules. The kernel names the
# discrete multi-modal structure in front of her each beat; the record keeps,
# for each structure she has met, each act she tried there, the successor
# distribution that followed, and the measured value to her bodily needs.
ACTS = ("take", "grasp", "touch", "release", "toward_food", "toward_bed", "toward_thing", "toward_door", "toward_person", "reach_hand", "step", "turn_left", "turn_right", "say", "rest")
ACT_RECORD_CAPACITY = 4096   # structures remembered with their acts; recurrent structures persist
EXPLORE_EVERY = 8
MAX_CANDIDATES = 64

# Sleep: a pressure like her reserve. Every awake beat adds one; past its
# ceiling she sleeps, and each sleeping beat drains two, so sixteen hours
# awake give eight hours asleep at today's live rate of about 7,100 beats an
# hour (her world runs a quarter second a beat; the hours here are the wall's).
# Asleep her eyelids close (the world's optics then pass no light), she issues
# no act, and she burns at basal. She wakes when the pressure is gone.
SLEEP_PRESSURE_CEILING = 113_600
SLEEP_RECOVERY_PER_BEAT = 2
# Her need for contact: rises one per awake beat without another body's touch on her
# skin, and a beat of touch relieves one sixty-fourth of the ceiling (two hours of her
# beats, the sleep ceiling's unit). Declared once; a touch pays by this need at the
# moment she chose, as food pays by hunger.
CONTACT_PRESSURE_CEILING = 14_200
CONTACT_RECOVERY_PER_BEAT = CONTACT_PRESSURE_CEILING // 64
# Thermal contrast at the point of contact: what her skin meets minus her own
# temperature, over her receptors' declared span; and nature's pain threshold
# (heat nociceptors fire from about 43 degrees C). A contact above it costs by the
# excess and pulls her hand back by reflex, as her jaw bites by reflex.
NOCICEPTION_MILLIKELVIN = 316_150
BED_ID = "bed"
EXHAUSTION_MARGIN = Fraction(1, 8)
EYELID_OPEN_MICROMETRES = 10_000

# Dreaming: each sleeping beat moves the most recurrent structure of the day's
# record into her consolidated memory, keyed by her situation, so what paid
# in a situation carries across days and across scenes; the day's record is
# emptied by the night. Awake, the day's record is consulted first, the
# consolidated memory when the day has nothing for the present structure.
CONSOLIDATED_STREAMS = ("sound_energy", "hunger", "food_distance", "hand")
CONSOLIDATED_CAPACITY = 2048
RETIRED_KEYS = ("pending_syllable", "visited", "door_goal", "bout_syllables", "quiet_until_tick", "blocked_doors", "unreachable_food", "food_goal",
                "food_refusals", "food_best_mm", "food_stall_beats", "answered_profile", "touched", "strides_since_pickup", "release_refusals",
                "touching", "listening_since", "call_profile", "answer_bout", "answer_target", "answer_pending", "answer_map", "food_rooms",
                "food_room_goal", "room_beats", "keeping_room", "keep_walk_beats", "last_kept", "kept", "stuck_beats", "approached", "goal",
                "goal_beats", "goal_refusals", "idle_beats")

# Steps: one stride per beat; she stops a hand's margin short of a thing.
STEP_MM = 300
STOP_MARGIN_MM = 50
WANDER_STOP_MM = 400
ARRIVAL_MM = 20
SIDESTEP_MILLIDEGREES = (45_000, -45_000, 90_000, -90_000, 135_000, -135_000, 180_000)
TURN_MILLIDEGREES = 60_000
HANDLE_MASS_GRAMS = 2_000
HANDLE_RADIUS_MM = 300
HANDLE_STOP_MM = 150       # how far short of a thing she stops to reach it with her hand
DROP_MARGIN_MM = 60
DOOR_MARGIN_MM = 600
DOOR_CROSSING_OFFSETS_MM = (0, 300, -300, 500, -500)

# Multi-modal sensory streams:
# Active: sight (luminance, horizontal, vertical), sound (energy, pitch)
# Passive: smell (odour release/concentration), taste (oral residue), touch (texture/roughness/compliance), interoceptive somatic pressure
# Relational / Proprioceptive: hunger, food_distance, heading, hand
STREAMS_V13 = (
    "sight_luminance", "sight_horizontal", "sight_vertical", "sound_energy",
    "sound_pitch", "smell_odour", "taste_residue", "touch_texture",
    "sleep_pressure", "hunger", "food_distance", "heading", "hand",
)
STREAMS_V15 = STREAMS_V13 + ("skin_contact", "contact_pressure")
STREAMS_V16 = STREAMS_V15 + ("touch_warmth",)   # her skin pressed by another body; her need for contact; the warmth of what her skin meets
# Her ear for speech: the shape of what she hears. Her cochlea resolves 16 channels
# per ear spaced by ERB from 80 to 7,500 Hz; the two ears averaged, the channels
# grouped into six bands, each band the fraction of the sound's energy in it, so a
# shape is the same loud or soft (loudness stays in sound_energy); silence has none.
STREAMS = STREAMS_V16 + tuple(f"ear_band_{index}" for index in range(EAR_BANDS))
LEGACY_STREAMS = (
    "sight_luminance", "sight_horizontal", "sight_vertical", "sound_energy",
    "sound_pitch", "hunger", "food_distance", "heading", "hand",
)
# The structure she chooses under leaves out the streams her own hand flips
# within a beat (her hand, what it touches, what she tastes): with them in the
# key every grasp and release made a "new" structure, and under a new
# structure her untried-first rule picked grasp and release before any move
# or sound, forever (live, 2026-09-14). Those streams stay in the signature,
# the episodes and the kernel; they do not name the structure.
CHOICE_STREAMS = tuple(name for name in STREAMS if name not in ("hand", "touch_texture", "taste_residue"))
KERNEL_WINDOW = 64

# Memory bounds.
FAMILIARITY_CAPACITY = 8192
EPISODE_CAPACITY = 512
HEARD_CAPACITY = 64
VOICE_CAPACITY = 64
REFUSAL_CAPACITY = 128

# Voice: one syllable through her airway, chosen from her speech record under
# (situation, prior syllable); a room sound standing out within the answer
# window after it is what pays. Nothing scripted answers a heard sound.
BABBLE_EVERY_BEATS = 4
# Her own voice heard back enters her ear's gate as events of its own (Level 1 on her
# own sound), kept in a store of their own; a moment forms when her own event closes
# as when a heard one does, so "what she said, then what followed" is counted.
OWN_EVENT_RECORD_CAPACITY = 1024
HEARD_ABOVE_AMBIENT = 2.0       # a sound worth answering is at least twice the running ambient level
AMBIENT_MEMORY = Fraction(15, 16)
COCHLEAR_CHANNELS = 32
VOICE_VERSION = 3               # 3: syllables valued by what followed them, as acts are; the answer-count law retired
SPEECH_RECORD_CAPACITY = 1024
PHRASE_WINDOW_BEATS = 8

# Level 1 (docs/GL-SPC-ACOUSTIC-GATE-C1-20260915-v1.md): a spoken sound as one event
# with its own boundaries, kept by the key of its own structure. The day's store of
# events keeps the most recently met (her day law); nothing here names a sound or
# answers one. Her record of quiet is the datum for a pause law read from nature
# instead of the declared twelve frames: the runs of quiet inside events that a
# sounding frame ended (1..11 frames), and the silence between events in frames,
# binned at a beat, two, eight, sixty-four, and beyond.
EVENT_RECORD_CAPACITY = 4096
# Level 2 (docs/GL-SPC-MOMENT-LEVEL2-C1-20260915-v1.md): a moment forms on the beat a
# sound event closes; its key is the event's key with the held thing's texture and warmth
# in eighths and the figure under her gaze (the physical invariants, A1's §6); her hunger,
# taste and the caregiver's touch at that beat ride in the record as context, not the key.
# Level 3: what followed a moment within the window, by count: the next moment, and a bite.
MOMENT_RECORD_CAPACITY = 128
FOLLOW_WINDOW_BEATS = 16
FOLLOW_CAPACITY = 32
# The night for moments, as for acts: each sleeping beat moves the most recurrent moment
# of the day into her consolidated store of meanings (kept by count; the least counted
# leaves) and drops a moment met only once; by morning the day's moments are empty.
MEANING_CAPACITY = 4096
# Cognitive Asset 4: Spatial Object Permanence & Occlusion Conservation (The Piaget Invariant)
OBJECT_PERMANENCE_CAPACITY = 64
PERMANENCE_FIXTURES = (BED_ID, "desk", "toy-chest", "radio", "window", "mirror", "bookshelf", "blanket", "curtains", "wall-art-shapes", "wall-art-weather", "playpen")

# Grounded Food Ontology Invariant:
# Only verified digestible sustenance objects are edible. Fixtures, furniture, bedding,
# toys, tools, and structural elements must NEVER be qualified or conserved as food.
NON_FOOD_OBJECT_IDS = set(PERMANENCE_FIXTURES) | {
    "pillow", "night-light", "toy-bear", "stacking-rings", "toy-blocks",
    "play-ball", "book", "lamp", "television", "sofa", "rug", "tv-remote",
    "mailbox", "stroller-carriage", "slide", "swing", "sandbox", "garden-patch",
    "garden-ladder", "tree-oak", "tree-pine", "tree-apple", "cup", "pot",
    "pan", "table", "sideboard", "bath-tub", "wash-basin", "bath-towel",
    "bath-mat", "bath-lamp", "high-chair", "kitchen-counter", "refrigerator",
    "stove", "pantry", "dining-table", "dining-chair", "dining-chair-south",
    "dining-lamp", "daddys-desk", "daddys-chair", "daddys-book", "daddys-lamp",
    "daddys-armchair", "shelf-a", "shelf-b", "glow-stars", "desk-chair",
}

def is_genuine_food_object(object_id: str | None) -> bool:
    """Physical Material Invariant: verifies whether an object possesses genuine caloric/digestible sustenance."""
    if not object_id or not isinstance(object_id, str):
        return False
    if object_id in NON_FOOD_OBJECT_IDS or object_id in PERMANENCE_FIXTURES:
        return False
    return (
        object_id.startswith("apple")
        or object_id.startswith("bread")
        or object_id.startswith("garden-apple") or object_id in ("bottle-milk", "bowl")
    )
DISCREPANCY_VERIFICATION_DISTANCE_MM = 1_000

# Cognitive Asset 5: Joint Attention & Caregiver Gaze Vector Tracking
MAX_GAZE_RAY_MM = 4_000
GAZE_CONE_HALF_ANGLE_DEG = 15.0

QUIET_RUN_BINS = PAUSE_FRAMES - 1
GAP_BINS_FRAMES = (FRAMES_PER_HOP, FRAMES_PER_HOP * 2, FRAMES_PER_HOP * 8, FRAMES_PER_HOP * 64)


def _empty_ear_quiet() -> dict[str, list[int]]:
    return {"inside": [0] * QUIET_RUN_BINS, "between": [0] * (len(GAP_BINS_FRAMES) + 1)}

# Syllables: everything her airway declares: its onsets x vowels x pitches (11 x 5 x 4 = 220).
# A syllable is valued exactly as her acts are, by what followed it (her measured needs:
# a sound standing out, a touch, intake, new structure), under the situation and the
# syllable before it, so speech grows into sequences by the same law as every act.
# Untried syllables are explored in order of lifetime tries (zero clock arithmetic).
SYLLABLES = tuple(f"{onset}{v[0]}{p_idx}" for p_idx in range(len(PITCHES_DECIHERTZ)) for onset in ONSETS for v in VOWELS)
SYLLABLE_DRIVES = {
    f"{onset}{v[0]}{p_idx}": (pitch, v_idx, o_idx)
    for p_idx, pitch in enumerate(PITCHES_DECIHERTZ)
    for o_idx, onset in enumerate(ONSETS)
    for v_idx, v in enumerate(VOWELS)
}
DEFAULT_SYLLABLE = SYLLABLES[0]
DEFAULT_DRIVE = SYLLABLE_DRIVES[DEFAULT_SYLLABLE]

# Her body's axes, declared once (index, name, unit, position, minimum,
# neutral, maximum).
_ANGLE = ("millidegree", 0, -75_000, 0, 75_000)
_SMALL_ANGLE = ("millidegree", 0, -45_000, 0, 45_000)
_NECK_PITCH = ("millidegree", 0, -HEAD_PITCH_BOUND_MILLIDEGREES, 0, HEAD_PITCH_BOUND_MILLIDEGREES)
_APERTURE = ("micrometre", 10_000, 0, 10_000, 12_000)
_MOUTH = ("micrometre", 0, 0, 0, 40_000)
_GRIP = ("micrometre", 0, 0, 0, 90_000)
_TRACT = ("square_millimetre", 0, 0, 0, 5_000)
BODY_AXES = tuple(
    (index, name, *spec)
    for index, (name, spec) in enumerate((
        ("torso_pitch", _SMALL_ANGLE), ("torso_roll", _SMALL_ANGLE),
        ("neck_yaw", _ANGLE), ("neck_pitch", _NECK_PITCH),
        ("left_eye_yaw", _SMALL_ANGLE), ("left_eye_pitch", _SMALL_ANGLE),
        ("right_eye_yaw", _SMALL_ANGLE), ("right_eye_pitch", _SMALL_ANGLE),
        ("left_eyelid_aperture", _APERTURE), ("right_eyelid_aperture", _APERTURE),
        ("left_brow_height", _MOUTH), ("right_brow_height", _MOUTH),
        ("left_cheek_raise", _MOUTH), ("right_cheek_raise", _MOUTH),
        ("jaw_opening", _MOUTH), ("lip_aperture", _MOUTH), ("lip_width", _MOUTH),
        ("perioral_displacement", _MOUTH), ("glottal_aperture", _MOUTH),
        ("left_shoulder_pitch", _ANGLE), ("left_shoulder_roll", _ANGLE),
        ("left_elbow_flexion", _ANGLE), ("left_wrist_yaw", _ANGLE), ("left_grip_aperture", _GRIP),
        ("right_shoulder_pitch", _ANGLE), ("right_shoulder_roll", _ANGLE),
        ("right_elbow_flexion", _ANGLE), ("right_wrist_yaw", _ANGLE), ("right_grip_aperture", _GRIP),
        ("left_hip_pitch", _ANGLE), ("left_hip_roll", _SMALL_ANGLE),
        ("left_knee_flexion", _ANGLE), ("left_ankle_pitch", _SMALL_ANGLE),
        ("right_hip_pitch", _ANGLE), ("right_hip_roll", _SMALL_ANGLE),
        ("right_knee_flexion", _ANGLE), ("right_ankle_pitch", _SMALL_ANGLE),
        *((f"vocal_tract_section{section}_area", _TRACT) for section in range(8)),
    ))
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def _sign(value: float) -> str:
    return "0" if abs(value) < 1e-9 else "+" if value > 0 else "-"


@dataclass(frozen=True, slots=True)
class Readiness:
    identity: str
    organism_tick: int
    state_sha256: str
    state_bytes: int
    python_callback_count: int
    articulated_body_axes: tuple[tuple[object, ...], ...]


@dataclass(frozen=True, slots=True)
class Checkpoint:
    organism_tick: int
    state_sha256: str
    state_bytes: int
    _encoded: bytes

    def encoded_generation(self) -> bytes:
        return self._encoded


@dataclass(frozen=True, slots=True)
class LivedState:
    organism_tick: int
    _encoded: bytes

    def prepare_checkpoint(self) -> Checkpoint:
        return Checkpoint(self.organism_tick, _sha256(self._encoded), len(self._encoded), self._encoded)


@dataclass(frozen=True, slots=True)
class SeenThing:
    object_id: str
    position: PositionMM
    radius_mm: int
    distance_mm: float
    bearing_millidegrees: int
    is_food: bool


@dataclass(frozen=True, slots=True)
class OpticalEvidence:
    """Frame-aligned ocular transducer state and producer-origin saturation evidence.

    Delivers producer-origin saturation evidence for a future explicitly reviewed consumer.
    """

    pupil_gain: float | None
    eyelid_transmission: Fraction | None
    focal_saturation_mask: bytes | None


@dataclass(frozen=True, slots=True)
class Sensed:
    """One beat of her measured senses, assembled by the loop from the world,
    the page's camera and microphone, and her own airway."""

    snapshot: Any
    focal_luminance_u8: tuple[int, ...]
    luminance_source: str
    heard_profile: tuple[float, ...] | None
    self_profile: tuple[float, ...] | None
    wide_luminance_u8: tuple[int, ...] = ()
    skin_contact: float = 0.0                       # fraction of her skin another body pressed this beat
    skin_temperature_millikelvin: int | None = None  # her cutaneous node now (None: no thermal body)
    touch_surface_millikelvin: int | None = None     # the temperature of the skin that pressed hers this beat
    heard_frames: tuple[tuple[float, ...], ...] = ()  # the room sound's 25 frames at her ear (energy, six band fractions); () = no sound
    own_frames: tuple[tuple[float, ...], ...] = ()    # her own voice heard back, the same 25 frames; () = she made no sound
    sound_source_id: str | None = None
    optical_evidence: OpticalEvidence | None = None
    heard_envelopes: tuple[tuple[float, ...], ...] = ()
    own_envelopes: tuple[tuple[float, ...], ...] = ()
    cochlear_batch: CochlearBatch | None = None  # full pressure/phase on the receptor sample clock
    self_emission_present: bool = False  # efference provenance, not source-separated hearing
    external_sound_present: bool = False


@dataclass(frozen=True, slots=True)
class Decision:
    act: str
    reason: str
    commands: tuple[Any, ...]        # world commands to try in order; empty = passive interval
    target_object_id: str | None
    drive: tuple[int, int, int] | None   # (cycle_samples, open_samples, shape) when she vocalizes
    signature: str
    novel: bool
    gate_count: int
    seen: tuple[SeenThing, ...]


def _self_body(snapshot: Any) -> Any:
    matches = tuple(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)
    if len(matches) != 1:
        raise RuntimeError("physical world lost its unique organism body")
    return matches[0]


def _bearing_offset(heading: int, bearing: int) -> int:
    return (bearing - heading + 180_000) % 360_000 - 180_000


def things_in_sight(snapshot: Any, known_food_ids: set[str] | None = None) -> tuple[SeenThing, ...]:
    """What she can see: things on the floor of her own room, within her
    field of view and range, nearest first."""

    body = _self_body(snapshot)
    region = _region_of(snapshot, body.pose.position, body.radius_mm)
    seen = []
    for item in snapshot.objects:
        if item.position is None or region is None:
            continue
        if _region_of(snapshot, item.position, item.radius_mm) is not region:
            continue
        distance = _distance_mm(body.pose.position, item.position)
        if distance > SIGHT_RANGE_MM:
            continue
        bearing = _heading_toward(body.pose.position, item.position)
        if abs(_bearing_offset(body.pose.heading_millidegrees, bearing)) > FIELD_OF_VIEW_MILLIDEGREES:
            continue
        is_f = is_genuine_food_object(item.object_id) and item.material is not None and getattr(item.material, "digestible_mass_micrograms", 0) > 0
        seen.append(SeenThing(item.object_id, item.position, item.radius_mm, distance, bearing, is_f))
    return tuple(sorted(seen, key=lambda thing: (thing.distance_mm, thing.object_id)))


PERSON_STOP_MM = 600            # centre to centre, where her palm can meet the caregiver's palm (the caregiver offers from here too)
REACH_SITES = (("right-palm", "left-palm"), ("left-palm", "right-palm"))   # her palm to the caregiver's facing palm, tried in order


def caregiver_in_sight(snapshot: Any) -> SeenThing | None:
    """The caregiver's body when it stands in her room, within her range and field
    of view: seen the way a thing is seen (the same geometry), never assumed."""

    body = _self_body(snapshot)
    region = _region_of(snapshot, body.pose.position, body.radius_mm)
    for other in snapshot.bodies:
        if other.body_id == snapshot.self_body_id or region is None:
            continue
        if _region_of(snapshot, other.pose.position, other.radius_mm) is not region:
            continue
        distance = _distance_mm(body.pose.position, other.pose.position)
        if distance > SIGHT_RANGE_MM:
            continue
        bearing = _heading_toward(body.pose.position, other.pose.position)
        if abs(_bearing_offset(body.pose.heading_millidegrees, bearing)) > FIELD_OF_VIEW_MILLIDEGREES:
            continue
        return SeenThing(other.body_id, other.pose.position, other.radius_mm, distance, bearing, False)
    return None


def in_hand_reach(snapshot: Any, item: Any) -> bool:
    """The world's own grasp geometry: the thing lies inside her hand's contact disc."""

    body = _self_body(snapshot)
    geometry = body.receptor_geometry
    if geometry is None or item.position is None:
        return False
    receptor = _receptor_position(body, geometry.touch_offset_mm)
    return receptor is not None and _derived_contact_patch_square_mm(
        receptor_position=receptor, receptor_radius_mm=geometry.touch_radius_mm,
        object_position=item.position, object_radius_mm=item.radius_mm,
    ) is not None


def edge_centre(field: tuple[int, ...], columns: int, rows: int, floor: int) -> tuple[float, float] | None:
    """The energy-weighted centre of luminance edges in a rectangular field
    (fractions of the field), or None when the field is flat (below floor)."""

    if len(field) != columns * rows:
        return None
    total = 0
    weighted_x = 0
    weighted_y = 0
    for index, value in enumerate(field):
        column, row = index % columns, index // columns
        energy = 0
        if column + 1 < columns:
            energy += abs(value - field[index + 1])
        if row + 1 < rows:
            energy += abs(value - field[index + columns])
        total += energy
        weighted_x += energy * column
        weighted_y += energy * row
    if total < floor:
        return None
    return weighted_x / (total * (columns - 1)), weighted_y / (total * (rows - 1))


def structure_centre(focal: tuple[int, ...]) -> tuple[float, float]:
    """The energy-weighted centre of luminance edges in a focal field
    (fractions of the field), or the centre when the field is flat.
    Supports both 3-channel RGB (57,600 values) and single-channel focal fields."""

    if len(focal) == FOCAL_COLUMNS * FOCAL_ROWS * 3:
        lum = tuple((focal[i * 3] + focal[i * 3 + 1] + focal[i * 3 + 2]) // 3 for i in range(FOCAL_COLUMNS * FOCAL_ROWS))
        centre = edge_centre(lum, FOCAL_COLUMNS, FOCAL_ROWS, STRUCTURE_FLOOR)
    else:
        centre = edge_centre(focal, FOCAL_COLUMNS, FOCAL_ROWS, STRUCTURE_FLOOR)
    return (0.5, 0.5) if centre is None else centre


def head_step(head: tuple[int, int], wide: tuple[int, ...]) -> tuple[int, int]:
    """The head's next (yaw, pitch) in millidegrees: yaw stays where it is;
    pitch takes a bounded step toward the height of structure in the wide
    field the head carries (so the step is relative to where the head points
    now), holds still within the settle margin, and eases back toward level
    when the field is flat."""

    yaw, pitch = int(head[0]), int(head[1])
    centre = edge_centre(wide, WIDE_COLUMNS, WIDE_ROWS, WIDE_FLOOR)
    wanted = -pitch if centre is None else (0.5 - centre[1]) * WIDE_FIELD_MILLIDEGREES[1]
    if abs(wanted) < HEAD_SETTLE_MILLIDEGREES:
        return yaw, pitch
    step = int(_clamp(wanted / 2, -HEAD_STEP_MILLIDEGREES, HEAD_STEP_MILLIDEGREES))
    return yaw, int(_clamp(pitch + step, -HEAD_PITCH_BOUND_MILLIDEGREES, HEAD_PITCH_BOUND_MILLIDEGREES))


def head_toward(head: tuple[int, int], yaw_wanted: int, pitch_wanted: int) -> tuple[int, int]:
    """The head's next (yaw, pitch) toward where the thing she acts on lies, in her
    body's frame: each axis steps at most the head's step per beat, holds still
    within the settle margin, and stays inside the neck's declared bounds."""

    out = []
    for now, wanted, bound in ((int(head[0]), int(yaw_wanted), HEAD_YAW_BOUND_MILLIDEGREES), (int(head[1]), int(pitch_wanted), HEAD_PITCH_BOUND_MILLIDEGREES)):
        wanted = int(_clamp(wanted, -bound, bound))
        if abs(wanted - now) < HEAD_SETTLE_MILLIDEGREES:
            out.append(now)
            continue
        step = int(_clamp(wanted - now, -HEAD_STEP_MILLIDEGREES, HEAD_STEP_MILLIDEGREES))
        out.append(int(_clamp(now + step, -bound, bound)))
    return out[0], out[1]


def _eye_position(body: Any) -> tuple[int, int, int]:
    """Where her eye is: her body's retinal port, carried by her heading (the world's own law)."""

    geometry = body.receptor_geometry
    if geometry is None:
        return body.pose.position.x, body.pose.position.y, body.pose.position.z
    offset = geometry.retinal_offset_mm
    try:
        dx, dy = rotate_lattice_offset(offset.x, offset.y, body.pose.heading_millidegrees)
    except ValueError:
        return body.pose.position.x, body.pose.position.y, body.pose.position.z + offset.z
    return body.pose.position.x + dx, body.pose.position.y + dy, body.pose.position.z + offset.z


def _target_point(snapshot: Any, body: Any, target_id: str | None, conserved_objects: dict[str, Any] | None = None) -> tuple[int, int, int] | None:
    """The point she looks at for the thing she acts on: a thing's rendered centre (its
    position raised by its radius, as the world eye draws it); a thing in her own hand at
    her hand's contact point; another body at its position at her eye's height; a conserved
    topological coordinate when the entity is temporarily occluded; else None."""

    if not target_id or not isinstance(target_id, str):
        return None
    if body.held_object_id == target_id:
        geometry = body.receptor_geometry
        if geometry is None:
            return None
        offset = geometry.touch_offset_mm
        try:
            dx, dy = rotate_lattice_offset(offset.x, offset.y, body.pose.heading_millidegrees)
        except ValueError:
            return body.pose.position.x, body.pose.position.y, body.pose.position.z + offset.z
        return body.pose.position.x + dx, body.pose.position.y + dy, body.pose.position.z + offset.z
    for item in snapshot.objects:
        if item.object_id == target_id:
            if item.position is not None:
                return item.position.x, item.position.y, item.position.z + int(item.radius_mm)
            break
    for other in snapshot.bodies:
        if other.body_id == target_id:
            eye_z = _eye_position(body)[2]
            return other.pose.position.x, other.pose.position.y, eye_z
    for p in snapshot.portals:
        if p.portal_id == target_id:
            eye_z = _eye_position(body)[2]
            if p.axis == "x":
                mid_y = (p.aperture_min_mm + p.aperture_max_mm) // 2
                return p.plane_mm, mid_y, eye_z
            else:
                mid_x = (p.aperture_min_mm + p.aperture_max_mm) // 2
                return mid_x, p.plane_mm, eye_z
    if conserved_objects and target_id in conserved_objects:
        pos = conserved_objects[target_id]["position"]
        rad = int(conserved_objects[target_id].get("radius_mm", 0))
        return pos[0], pos[1], pos[2] + rad
    return None


def _target_radius_mm(snapshot: Any, body: Any, target_id: str | None, conserved_objects: dict[str, Any] | None = None) -> int:
    """The radius of the thing she acts on (a thing's or a body's), zero when unknown."""

    if not target_id or not isinstance(target_id, str):
        return 0
    for item in snapshot.objects:
        if item.object_id == target_id:
            return int(item.radius_mm)
    for p in snapshot.portals:
        if p.portal_id == target_id:
            return abs(p.aperture_max_mm - p.aperture_min_mm) // 2
    for other in snapshot.bodies:
        if other.body_id == target_id:
            return int(other.radius_mm)
    if conserved_objects and target_id in conserved_objects:
        return int(conserved_objects[target_id].get("radius_mm", 0))
    return 0


def _aim(body: Any, point: tuple[int, int, int]) -> tuple[int, int]:
    """(yaw, pitch) in millidegrees from her eye to a point, in her body's frame."""

    ex, ey, ez = _eye_position(body)
    planar = math.hypot(point[0] - ex, point[1] - ey)
    if planar < 1.0:
        # Straight below or above her eye (her own hand sits under her retinal port): no
        # bearing exists; she looks straight ahead and down (or up), not at a phantom side.
        return 0, (-CARRIAGE_PITCH_BOUND_MILLIDEGREES if point[2] < ez else CARRIAGE_PITCH_BOUND_MILLIDEGREES)
    bearing = int(round(math.degrees(math.atan2(point[1] - ey, point[0] - ex)) * 1000)) % 360_000
    yaw = _bearing_offset(body.pose.heading_millidegrees, bearing)
    pitch = int(round(math.degrees(math.atan2(point[2] - ez, planar)) * 1000))
    return yaw, pitch


def _gaze_in_field(head: tuple[int, int], aim: tuple[int, int]) -> tuple[float, float] | None:
    """Where the aimed point falls in her focal field (fractions), given where her head
    points now; None when it lies outside the field."""

    dx = aim[0] - int(head[0])
    dy = aim[1] - int(head[1])
    half_w, half_h = FOCAL_FIELD_MILLIDEGREES[0] // 2, FOCAL_FIELD_MILLIDEGREES[1] // 2
    if not (-half_w <= dx <= half_w and -half_h <= dy <= half_h):
        return None
    column = (dx + half_w) / FOCAL_SITE_MILLIDEGREES
    row = (half_h - dy) / FOCAL_SITE_MILLIDEGREES
    return (round(_clamp(column / (FOCAL_COLUMNS - 1), 0.0, 1.0), 6), round(_clamp(row / (FOCAL_ROWS - 1), 0.0, 1.0), 6))


def handleable_held(item: Any) -> bool:
    """A thing in another hand she can take: within physical carrying bounds (mass and radius)."""

    return item is not None and int(item.mass_grams) <= HANDLE_MASS_GRAMS and int(item.radius_mm) <= HANDLE_RADIUS_MM


def handleable(item: Any) -> bool:
    """A thing she can pick up: within physical carrying bounds (mass and radius), on the floor."""

    return (item is not None and item.position is not None
            and int(item.mass_grams) <= HANDLE_MASS_GRAMS and int(item.radius_mm) <= HANDLE_RADIUS_MM)


def drop_spot_clear(snapshot: Any, body: Any, item: Any) -> bool:
    """The world sets a released thing down a clearance ahead of the body;
    that spot must not touch another thing or body, or the world refuses."""

    from dsf_ai_service.substrate.embodiment_world import RELEASE_CLEARANCE_MM, _is_bed, rotate_lattice_offset

    try:
        dx, dy = rotate_lattice_offset(max(body.radius_mm, item.radius_mm) + item.radius_mm + RELEASE_CLEARANCE_MM, 0, body.pose.heading_millidegrees)
    except ValueError:
        return False
    spot = PositionMM(body.pose.position.x + dx, body.pose.position.y + dy, 0)
    if _region_of(snapshot, spot, item.radius_mm) is None:
        return False
    for other in snapshot.objects:
        if _is_bed(other):
            continue
        if other.object_id != item.object_id and other.position is not None and _distance_mm(spot, other.position) <= item.radius_mm + other.radius_mm + DROP_MARGIN_MM:
            return False
    for other in snapshot.bodies:
        if other.body_id != body.body_id and _distance_mm(spot, other.pose.position) <= item.radius_mm + other.radius_mm + DROP_MARGIN_MM:
            return False
    return True


def _object(snapshot: Any, object_id: str) -> Any | None:
    return next((item for item in snapshot.objects if item.object_id == object_id), None)


_OBSTACLE_VISIBILITY_GRAPH_CACHE: dict[tuple, tuple[list[PositionMM], dict[PositionMM, list[tuple[float, PositionMM]]]]] = {}


def _get_or_build_static_obstacle_graph(
    here: Any,
    carried_radius: int,
    floor_z: int,
    room_obs: list[tuple[PositionMM, int, str]],
    snapshot: Any,
) -> tuple[list[PositionMM], dict[PositionMM, list[tuple[float, PositionMM]]]]:
    """Bounded, deterministically invalidated cache of static obstacle visibility
    graphs within a room. Strictly invalidates when furniture, doors, bodies,
    carried-object clearance, or room bounds change."""
    bounds_key = (
        (here.region_id, here.bounds.minimum.x, here.bounds.maximum.x, here.bounds.minimum.y, here.bounds.maximum.y, floor_z)
        if here is not None else None
    )
    portals_key = (
        tuple(sorted((p.portal_id, p.axis, p.plane_mm, p.aperture_min_mm, p.aperture_max_mm)
                     for p in getattr(snapshot, "portals", ()) if here is not None and here.region_id in p.region_ids))
    )
    obs_key = tuple(sorted((item_id, pos.x, pos.y, rad) for pos, rad, item_id in room_obs))
    cache_key = (bounds_key, carried_radius, obs_key, portals_key)

    cached = _OBSTACLE_VISIBILITY_GRAPH_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if here is not None:
        bounds = here.bounds
        min_x = bounds.minimum.x + carried_radius
        max_x = bounds.maximum.x - carried_radius
        min_y = bounds.minimum.y + carried_radius
        max_y = bounds.maximum.y - carried_radius
    else:
        min_x, max_x, min_y, max_y = -100_000, 100_000, -100_000, 100_000

    waypoints: list[PositionMM] = []
    for pos, rad, _ in room_obs:
        rc = carried_radius + rad + DROP_MARGIN_MM + 50
        for k in range(16):
            ang = 2 * math.pi * k / 16.0
            wx = round(pos.x + rc * math.cos(ang))
            wy = round(pos.y + rc * math.sin(ang))
            if not (min_x <= wx <= max_x and min_y <= wy <= max_y):
                continue
            wp = PositionMM(wx, wy, floor_z)
            if any(_distance_mm(wp, opos) < carried_radius + orad + DROP_MARGIN_MM for opos, orad, _ in room_obs):
                continue
            waypoints.append(wp)

    step_x = (max_x - min_x) // 6
    step_y = (max_y - min_y) // 6
    if step_x > 0 and step_y > 0:
        for ix in range(1, 6):
            for iy in (1, 5):
                wp = PositionMM(min_x + ix * step_x, min_y + iy * step_y, floor_z)
                if not any(_distance_mm(wp, opos) < carried_radius + orad + DROP_MARGIN_MM for opos, orad, _ in room_obs):
                    waypoints.append(wp)

    adj: dict[PositionMM, list[tuple[float, PositionMM]]] = {wp: [] for wp in waypoints}
    for i, w1 in enumerate(waypoints):
        for j in range(i + 1, len(waypoints)):
            w2 = waypoints[j]
            blocked = False
            for opos, orad, _ in room_obs:
                req_r = carried_radius + orad + DROP_MARGIN_MM
                if _straight_path_intersects_disc(w1, w2, opos, req_r):
                    blocked = True
                    break
            if not blocked:
                d = _distance_mm(w1, w2)
                adj[w1].append((d, w2))
                adj[w2].append((d, w1))

    if len(_OBSTACLE_VISIBILITY_GRAPH_CACHE) > 32:
        _OBSTACLE_VISIBILITY_GRAPH_CACHE.clear()
    result = (waypoints, adj)
    _OBSTACLE_VISIBILITY_GRAPH_CACHE[cache_key] = result
    return result


def move_commands_toward(snapshot: Any, target: PositionMM, stop_mm: int) -> tuple[MoveCommand, ...]:
    """One stride toward target (turning to face it), or deterministic
    negative-space visibility path strides around intervening rigid obstacles,
    followed by sidesteps the world may accept when direct headings are obstructed."""

    body = _self_body(snapshot)
    origin = body.pose.position
    bearing = _heading_toward(origin, target)
    goal = _approach_point(origin, target, stop_mm)
    span = _distance_mm(origin, goal)
    if span <= 0:
        return (MoveCommand(PoseMM(origin, bearing), BEAT_MICROSECONDS),)

    stride = min(STEP_MM, span)
    held_radius = 0
    if body.held_object_id is not None:
        held_obj = _object(snapshot, body.held_object_id)
        if held_obj is not None:
            held_radius = int(held_obj.radius_mm)
    carried_radius = max(int(body.radius_mm), held_radius)
    here = _region_of(snapshot, origin, body.radius_mm)

    playpen = next((item for item in snapshot.objects if item.object_id == "playpen" and item.position is not None), None)
    in_playpen = False
    if playpen is not None:
        start_dist = math.hypot(origin.x - playpen.position.x, origin.y - playpen.position.y)
        if start_dist + carried_radius <= playpen.radius_mm:
            in_playpen = True

    room_obs: list[tuple[PositionMM, int, str]] = []
    for item in snapshot.objects:
        if item.position is None or _is_bed(item):
            continue
        if _distance_mm(item.position, target) == 0:
            continue
        if item.object_id == "playpen" and in_playpen:
            continue
        room_obs.append((item.position, int(item.radius_mm), item.object_id))
    for other in snapshot.bodies:
        if other.body_id == body.body_id:
            continue
        room_obs.append((other.pose.position, int(other.radius_mm), other.body_id))

    # Check direct line
    direct_blocked = any(
        _straight_path_intersects_disc(origin, goal, pos, carried_radius + rad)
        for pos, rad, _ in room_obs
    )
    if not direct_blocked:
        attempt_headings = [(bearing + off) % 360_000 for off in (0, *SIDESTEP_MILLIDEGREES)]
        commands: list[MoveCommand] = []
        for heading in attempt_headings:
            rad = math.radians(heading / 1000.0)
            step = PositionMM(round(origin.x + stride * math.cos(rad)), round(origin.y + stride * math.sin(rad)), origin.z)
            if here is not None and not here.bounds.contains_floor_disc(step, carried_radius):
                continue
            if in_playpen and playpen is not None:
                step_dist = math.hypot(step.x - playpen.position.x, step.y - playpen.position.y)
                if step_dist + carried_radius > playpen.radius_mm:
                    continue
            if any(_straight_path_intersects_disc(origin, step, opos, carried_radius + orad) for opos, orad, _ in room_obs):
                continue
            commands.append(MoveCommand(PoseMM(step, bearing), BEAT_MICROSECONDS))
        if commands:
            return tuple(commands)

    # Negative-space continuous path planning within room (bounded obstacle visibility reuse)
    static_wps, static_adj = _get_or_build_static_obstacle_graph(here, carried_radius, origin.z, room_obs, snapshot)

    waypoints: list[PositionMM] = [origin, goal] + static_wps
    adj: dict[PositionMM, list[tuple[float, PositionMM]]] = {wp: list(static_adj.get(wp, [])) for wp in waypoints}

    if not any(_straight_path_intersects_disc(origin, goal, opos, carried_radius + orad) for opos, orad, _ in room_obs):
        d = _distance_mm(origin, goal)
        adj[origin].append((d, goal))
        adj[goal].append((d, origin))

    for w in static_wps:
        if not any(_straight_path_intersects_disc(origin, w, opos, carried_radius + orad) for opos, orad, _ in room_obs):
            d = _distance_mm(origin, w)
            adj[origin].append((d, w))
            adj[w].append((d, origin))
        if not any(_straight_path_intersects_disc(goal, w, opos, carried_radius + orad + DROP_MARGIN_MM) for opos, orad, _ in room_obs):
            d = _distance_mm(goal, w)
            adj[goal].append((d, w))
            adj[w].append((d, goal))

    dist_map: dict[PositionMM, float] = {wp: float('inf') for wp in waypoints}
    dist_map[origin] = 0.0
    parent: dict[PositionMM, PositionMM] = {}
    pq: list[tuple[float, tuple[int, int, int], PositionMM]] = [(0.0, (origin.x, origin.y, origin.z), origin)]
    while pq:
        d, _, u = heapq.heappop(pq)
        if d > dist_map[u]:
            continue
        if u == goal:
            break
        for edge_d, v in adj[u]:
            if d + edge_d < dist_map[v]:
                dist_map[v] = d + edge_d
                parent[v] = u
                heapq.heappush(pq, (dist_map[v], (v.x, v.y, v.z), v))

    intermediate_target: PositionMM | None = None
    if goal in parent:
        curr = goal
        path = [curr]
        while curr != origin:
            curr = parent[curr]
            path.append(curr)
        path.reverse()
        if len(path) > 1:
            intermediate_target = path[1]

    if intermediate_target is None:
        # No geometric route supports a stride. Do not invent alternating
        # sidesteps toward an occupied or disconnected goal.
        return ()
    stride = min(STEP_MM, _distance_mm(origin, intermediate_target))
    target_heading = _heading_toward(origin, intermediate_target)
    attempt_headings = [target_heading]

    commands = []
    for heading in attempt_headings:
        rad = math.radians(heading / 1000.0)
        step = PositionMM(round(origin.x + stride * math.cos(rad)), round(origin.y + stride * math.sin(rad)), origin.z)
        if here is not None and not here.bounds.contains_floor_disc(step, carried_radius):
            continue
        if in_playpen and playpen is not None:
            step_dist = math.hypot(step.x - playpen.position.x, step.y - playpen.position.y)
            if step_dist + carried_radius > playpen.radius_mm:
                continue
        collides = any(_straight_path_intersects_disc(origin, step, opos, carried_radius + orad) for opos, orad, _ in room_obs)
        if not collides:
            commands.append(MoveCommand(PoseMM(step, bearing), BEAT_MICROSECONDS))

    return tuple(commands)


def _door_motor_commands(snapshot: Any, portal: Any, from_region: str) -> tuple[MoveCommand, ...]:
    """Cross the physically free aperture, not an occupied centre waypoint.

    Subtract the exact integer projections of swept collision discs from the
    doorway aperture. This is actuator geometry only: it neither chooses a
    destination room nor supplies a cognitive objective. No retained state.
    """
    body = _self_body(snapshot)
    held = _object(snapshot, body.held_object_id) if body.held_object_id else None
    radius = max(body.radius_mm, held.radius_mm if held is not None else 0)
    lower, upper = portal.aperture_min_mm + radius, portal.aperture_max_mm - radius
    if lower > upper:
        return ()
    obstacles = [(o.position, o.radius_mm) for o in snapshot.objects
                 if o.position is not None and not _is_bed(o)]
    for other in snapshot.bodies:
        if other.body_id == body.body_id:
            continue
        carried = _object(snapshot, other.held_object_id) if other.held_object_id else None
        obstacles.append((other.pose.position, max(other.radius_mm, carried.radius_mm if carried else 0)))
    margin = max(DOOR_MARGIN_MM, radius)
    segments = [(lower, upper)]
    for pos, obstacle_radius in obstacles:
        normal, along = (pos.x, pos.y) if portal.axis == "x" else (pos.y, pos.x)
        normal_gap = max(0, abs(normal - portal.plane_mm) - margin)
        square = (radius + obstacle_radius) ** 2 - normal_gap ** 2
        if square <= 0:
            continue
        # World collision is strict (< radius squared); equality is tangent.
        half = math.isqrt(square - 1)
        blocked_lo, blocked_hi = along - half, along + half
        remaining = []
        for lo, hi in segments:
            if blocked_hi < lo or blocked_lo > hi:
                remaining.append((lo, hi))
            else:
                if lo < blocked_lo:
                    remaining.append((lo, blocked_lo - 1))
                if blocked_hi < hi:
                    remaining.append((blocked_hi + 1, hi))
        segments = remaining
    centre = (portal.aperture_min_mm + portal.aperture_max_mm) // 2
    along = body.pose.position.y if portal.axis == "x" else body.pose.position.x
    candidate_crossings = []
    for lo, hi in segments:
        mid = (lo + hi) // 2
        clamped = min(max(along, lo), hi)
        for pt in (clamped, mid, (lo + mid) // 2, (mid + hi) // 2):
            if pt not in candidate_crossings:
                candidate_crossings.append(pt)
    crossings = sorted(candidate_crossings, key=lambda value: (abs(value - along), value))
    for crossing in crossings:
        before, past = _portal_points(portal, from_region, snapshot, crossing - centre, margin)
        if body.pose.position == before:
            return (MoveCommand(PoseMM(past, _heading_toward(before, past)), BEAT_MICROSECONDS),)
        commands = move_commands_toward(snapshot, before, 0)
        if commands:
            return commands
    return ()


def door_crossing(snapshot: Any, portal: Any, from_region: str) -> tuple[PositionMM, PositionMM]:
    """The two floor points of a doorway crossing: a margin before it inside
    ``from_region`` and a margin past it, on the doorway's centre line."""

    return _portal_points(portal, from_region, snapshot, 0, DOOR_MARGIN_MM)


def door_crossing_commands(snapshot: Any, portal: Any, from_region: str) -> tuple[MoveCommand, ...]:
    """Steps through a doorway, centre first, then across its width and with
    shorter margins past it, so a thing standing near the far side of the
    door does not close it."""

    commands = []
    for margin in (850, 700, 550):
        for offset in DOOR_CROSSING_OFFSETS_MM:
            before_door, past_door = _portal_points(portal, from_region, snapshot, offset, margin)
            commands.append(MoveCommand(PoseMM(past_door, _heading_toward(before_door, past_door)), BEAT_MICROSECONDS))
    return tuple(commands)


def syllable_pcm(drive: tuple[int, int, int], seed: int = 0) -> bytes:
    """One syllable through her airway (see guala_voice); per-utterance
    variation comes from ``seed``, her tick."""

    return airway_syllable_pcm(tuple(int(value) for value in drive), int(seed))


def cochlear_profile(cochleae: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    """One sound as her ear resolves it: the peak envelope of each of the 32 channels."""

    if len(cochleae) != COCHLEAR_CHANNELS:
        raise ValueError("cochlear profile needs the ear's 32 channels")
    return tuple(round(max(channel), 6) for channel in cochleae)


def ear_bands(profile: tuple[float, ...] | None) -> tuple[float, ...]:
    """The shape of a sound at her ear: the fraction of its energy in each of six
    ERB bands, the two ears averaged; all zero when there is no sound."""

    if profile is None or len(profile) != COCHLEAR_CHANNELS:
        return (0.0,) * EAR_BANDS
    per_ear = COCHLEAR_CHANNELS // 2
    channels = [(float(profile[index]) + float(profile[index + per_ear])) / 2.0 for index in range(per_ear)]
    total = sum(channels)
    if total <= 0.0:
        return (0.0,) * EAR_BANDS
    return tuple(round(sum(channels[c] for c in band) / total, 6) for band in EAR_BAND_CHANNELS)


_AIRWAY_REAFFERENCE_CACHE: dict[str, tuple[float, ...]] = {}


def spectral_cosine_similarity(profile_a: Sequence[float] | None, profile_b: Sequence[float] | None) -> float:
    """Continuous physical spectral cosine similarity across the 32 cochlear filter channels.
    Computes exact Euclidean cosine resonance between two auditory profiles:
    rho = (A . B) / (||A|| * ||B||).
    Returns 0.0 if either profile is None, mismatched in length, or of zero magnitude."""
    if profile_a is None or profile_b is None:
        return 0.0
    if len(profile_a) != len(profile_b) or len(profile_a) == 0:
        return 0.0
    dot = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0
    for a, b in zip(profile_a, profile_b):
        fa = float(a)
        fb = float(b)
        dot += fa * fb
        norm_a_sq += fa * fa
        norm_b_sq += fb * fb
    if norm_a_sq <= 0.0 or norm_b_sq <= 0.0:
        return 0.0
    denom = math.sqrt(norm_a_sq) * math.sqrt(norm_b_sq)
    if denom <= 0.0:
        return 0.0
    return max(0.0, min(1.0, round(dot / denom, 6)))


def _syllable_reafference(syllable: str) -> tuple[float, ...] | None:
    """Deterministic physical reafference profile of a syllable through the airway and cochlea."""
    if syllable in _AIRWAY_REAFFERENCE_CACHE:
        return _AIRWAY_REAFFERENCE_CACHE[syllable]
    drive = SYLLABLE_DRIVES.get(syllable)
    if drive is None:
        return None
    try:
        from dsf_ai_service.guala_cochlea import one_self_hearing_hop
        pcm = syllable_pcm(drive, 1)
        _, _, cochleae, _ = one_self_hearing_hop(pcm)
        profile = cochlear_profile(cochleae)
        _AIRWAY_REAFFERENCE_CACHE[syllable] = profile
        return profile
    except Exception:
        return None


def _streams_for(regimes: str) -> tuple[str, ...] | None:
    """Which stream tuple wrote a regimes string: told by its length, so a key or a
    situation written under an earlier stream count still names the same streams."""

    for streams in (STREAMS, STREAMS_V16, STREAMS_V15, STREAMS_V13, LEGACY_STREAMS):
        if len(regimes) == len(streams):
            return streams
    return None


def choice_key(regimes: str) -> str:
    """The key of the structure she chooses under and remembers as met: the
    regime letters of the choice streams, hashed."""

    streams = _streams_for(regimes)
    letters = "".join(regimes[streams.index(name)] for name in CHOICE_STREAMS if name in streams) if streams is not None else regimes
    return _sha256(" ".join(letters).encode("utf-8"))[:16]


def coarse_key(regimes: str) -> str:
    """Her situation: the regime letters of the consolidated streams only."""

    streams = _streams_for(regimes) or STREAMS
    return "".join(regimes[streams.index(name)] if len(regimes) == len(streams) and name in streams else "_" for name in CONSOLIDATED_STREAMS)


def project_caregiver_gaze_ray(
    caregiver_pose: PoseMM,
    snapshot: Any,
    conserved_objects: dict[str, Any] | None = None,
) -> tuple[str, tuple[int, int, int]] | None:
    """Projects a 3D ray along the caregiver's heading vector to identify the environmental
    entity currently within the caregiver's focal gaze cone (Social Joint Attention).
    Returns (target_object_id, (x, y, z)) or None."""
    origin = caregiver_pose.position
    heading_deg = caregiver_pose.heading_millidegrees / 1000.0
    heading_rad = math.radians(heading_deg)
    ux, uy = math.cos(heading_rad), math.sin(heading_rad)
    tan_half_cone = math.tan(math.radians(GAZE_CONE_HALF_ANGLE_DEG))

    candidates_list: list[tuple[float, str, tuple[int, int, int]]] = []

    for item in snapshot.objects:
        if item.position is None or item.object_id.startswith("door"):
            continue
        dx = item.position.x - origin.x
        dy = item.position.y - origin.y
        t = dx * ux + dy * uy
        if 150 < t <= MAX_GAZE_RAY_MM:
            perp = abs(dx * uy - dy * ux)
            radius = int(item.radius_mm)
            if perp <= radius + t * tan_half_cone:
                candidates_list.append((t, item.object_id, (int(item.position.x), int(item.position.y), int(item.position.z))))

    if conserved_objects:
        seen_ids = {c[1] for c in candidates_list}
        for obj_id, entry in conserved_objects.items():
            if obj_id in seen_ids or entry.get("is_fixture"):
                continue
            pos = entry.get("position")
            if pos:
                dx = pos[0] - origin.x
                dy = pos[1] - origin.y
                t = dx * ux + dy * uy
                if 150 < t <= MAX_GAZE_RAY_MM:
                    perp = abs(dx * uy - dy * ux)
                    radius = int(entry.get("radius_mm", 100))
                    if perp <= radius + t * tan_half_cone:
                        candidates_list.append((t, obj_id, (int(pos[0]), int(pos[1]), int(pos[2]))))

    if not candidates_list:
        return None
    candidates_list.sort(key=lambda x: x[0])
    _, target_id, target_pos = candidates_list[0]
    return target_id, target_pos



def _consequence_grounded_food_ids(state: dict[str, Any]) -> set[str]:
    """Recover food target IDs supported by actual retained feeding consequences in meanings."""
    foods = set()
    for m in state.get("meanings", {}).values():
        if isinstance(m, dict):
            c = m.get("consequences", {})
            if isinstance(c, dict):
                for act_c in c.values():
                    if isinstance(act_c, dict) and act_c.get("relief") == "feeding":
                        intake = act_c.get("intake", 0)
                        if isinstance(intake, (int, float)) and intake > 0:
                            tid = act_c.get("target_id")
                            if tid and is_genuine_food_object(tid):
                                foods.add(tid)
    return foods


def _consequence_qualified_food_ids(state: dict[str, Any]) -> set[str]:
    """Recover food object IDs supported by actual retained feeding consequences or verified physical intake."""
    consequence_foods = _consequence_grounded_food_ids(state)
    tested_non_nutritive = set(state.get("tested_non_nutritive") or ())
    known_foods = set()
    for obj_id, c_data in state.get("conserved_objects", {}).items():
        if not is_genuine_food_object(obj_id):
            continue
        if obj_id in tested_non_nutritive or c_data.get("non_nutritive") is True:
            continue
        has_nourished = (
            int(c_data.get("fed_count", 0)) > 0
            or int(c_data.get("historical_intake_micrograms", 0)) > 0
            or (obj_id in consequence_foods)
        )
        if has_nourished and not c_data.get("currently_depleted", False):
            known_foods.add(obj_id)
    return known_foods

def motor_efferent_to_locomotion_command(
    efferent: Tuple[float, float, float, float] | Sequence[float],
    current_pose: PoseMM,
    duration_microseconds: int = BEAT_MICROSECONDS,
) -> Optional[MoveCommand]:
    """
    Authorized substrate-to-command translation helper at the organism motor boundary.
    Converts native motor efferents (vocal_drive_hz, locomotion_stride_mm, steer_angle_deg, grip_force_n)
    into a canonical W1 MoveCommand using:
      - Canonical interval: duration_microseconds (default BEAT_MICROSECONDS = 250,000 µs = 0.25 s).
        Must be strictly positive integer.
      - Schema validation: efferent must be a 4-element sequence of finite real numbers.
      - Declared output domains:
          stride_mm in [0.0, 100.0]
          steer_deg in [-180.0, 180.0]
          vocal_drive_hz >= 0.0
          grip_force_n >= 0.0
        Malformed schema, non-finite values, or out-of-domain efferents raise ValueError.
      - Body-relative steering: integer millidegrees (steer_deg * 1000).
      - Integration order: Translation displacement uses pre-step heading; endpoint pose adopts steered heading.
      - Exact lattice displacement: exact rigid rotation onto the discrete millimetre lattice.
    Silent efferents (stride == 0.0 and steer == 0.0) return None (locomotion lawfully inhibited).
    """
    if isinstance(duration_microseconds, bool) or not isinstance(duration_microseconds, int):
        raise ValueError(f"duration_microseconds must be an integer, got {type(duration_microseconds).__name__}")
    if duration_microseconds != BEAT_MICROSECONDS:
        raise ValueError(f"duration_microseconds must match canonical beat interval {BEAT_MICROSECONDS} us, got {duration_microseconds}")

    if not isinstance(efferent, (tuple, list)) or len(efferent) != 4:
        raise ValueError(f"Efferent must be a 4-element sequence, got {type(efferent)} of length {len(efferent) if hasattr(efferent, '__len__') else 'unknown'}")

    try:
        vocal_hz = float(efferent[0])
        stride_mm = float(efferent[1])
        steer_deg = float(efferent[2])
        grip_n = float(efferent[3])
    except (TypeError, ValueError) as err:
        raise ValueError(f"Efferent elements must be numeric floats: {err}") from err

    if not (np.isfinite(vocal_hz) and np.isfinite(stride_mm) and np.isfinite(steer_deg) and np.isfinite(grip_n)):
        raise ValueError(f"Non-finite efferent values detected: vocal={vocal_hz}, stride={stride_mm}, steer={steer_deg}, grip={grip_n}")

    if not (0.0 <= stride_mm <= 60.0):
        raise ValueError(f"locomotion_stride_mm out of declared native producer domain [0.0, 60.0]: {stride_mm}")

    if not (-45.0 <= steer_deg <= 45.0):
        raise ValueError(f"steer_angle_deg out of declared native producer domain [-45.0, 45.0]: {steer_deg}")

    if not (0.0 <= vocal_hz <= 480.0):
        raise ValueError(f"vocal_drive_hz out of declared native producer domain [0.0, 480.0]: {vocal_hz}")

    if not (0.0 <= grip_n <= 25.0):
        raise ValueError(f"grip_force_n out of declared native producer domain [0.0, 25.0]: {grip_n}")

    if stride_mm == 0.0 and steer_deg == 0.0:
        return None

    steer_millidegrees = int(round(steer_deg * 1000.0))
    target_heading = (current_pose.heading_millidegrees + steer_millidegrees) % 360_000

    stride_int = int(round(stride_mm))
    if stride_int > 0:
        dx, dy = rotate_lattice_offset(stride_int, 0, current_pose.heading_millidegrees)
        target_pos = PositionMM(
            current_pose.position.x + dx,
            current_pose.position.y + dy,
            current_pose.position.z,
        )
    else:
        target_pos = current_pose.position

    return MoveCommand(
        target_pose=PoseMM(target_pos, target_heading),
        duration_microseconds=duration_microseconds,
    )


def candidates(
    snapshot: Any,
    body: Any,
    held: Any,
    offered: Any,
    seen: tuple[SeenThing, ...],
    tick: int,
    say_drive: tuple[int, int, int] | None = None,
    say_detail: str = "a syllable of her own",
    feeding: bool = False,
    sleepy: bool = True,
    conserved_objects: dict[str, Any] | None = None,
    last_crossed_portal: tuple[str, int] | None = None,
    sound_heard: bool = False,
    consequence_food_ids: set[str] | None = None,
    tested_non_nutritive_ids: set[str] | None = None,
    modular_sub: Any = None,
) -> list[tuple[str, str, tuple[Any, ...], str | None, tuple[int, int, int] | None]]:
    """What her body can do this beat, across every sensed target: each entry is
    (act, detail, world commands tried in order, target, voice drive).
    Candidate count is strictly bounded by what she sees plus her room's doors."""

    out: list[tuple[str, str, tuple[Any, ...], str | None, tuple[int, int, int] | None]] = []
    position, heading = body.pose.position, body.pose.heading_millidegrees
    here = _region_of(snapshot, position, body.radius_mm)
    reachable = [item for item in snapshot.objects if item.position is not None and in_hand_reach(snapshot, item)]

    chair = next((o for o in snapshot.objects if o.object_id == "high-chair" and o.position is not None), None)
    in_high_chair = (chair is not None and _distance_mm(position, chair.position) <= 250)

    # 1. Take from hand
    if held is None and offered is not None and handleable_held(offered):
        is_depleted = bool(
            (conserved_objects and conserved_objects.get(offered.object_id, {}).get("currently_depleted"))
            or (offered.material is not None and sum(offered.material.tastant_mass_micrograms) < 2_000)
            or (getattr(offered, "tastant_remaining_micrograms", None) is not None and offered.tastant_remaining_micrograms <= 0)
        )
        is_non_nutritive = bool(
            (conserved_objects and conserved_objects.get(offered.object_id, {}).get("non_nutritive"))
            or (tested_non_nutritive_ids and offered.object_id in tested_non_nutritive_ids)
            or (not is_genuine_food_object(offered.object_id))
        )
        if not (feeding and (is_depleted or is_non_nutritive)):
            out.append(("take", offered.object_id + " from a hand", (TakeContactHeldObjectCommand(BEAT_MICROSECONDS),), offered.object_id, None))

    # 2. Grasp (one reachable object per world grasp law) and touch reachable things
    target_reachable = reachable
    if feeding and len(reachable) > 1:
        viable_food = [
            item for item in reachable
            if is_genuine_food_object(item.object_id)
            and not (conserved_objects and conserved_objects.get(item.object_id, {}).get("currently_depleted"))
        ]
        if viable_food:
            target_reachable = [min(viable_food, key=lambda x: _distance_mm(position, x.position))]
    if held is None and len(target_reachable) == 1 and handleable(target_reachable[0]):
        item = target_reachable[0]
        c_entry = conserved_objects.get(item.object_id, {}) if conserved_objects else {}
        if is_genuine_food_object(item.object_id):
            is_known_non_food = bool(
                c_entry.get("currently_depleted") is True
                or (getattr(item, "tastant_remaining_micrograms", None) is not None and item.tastant_remaining_micrograms <= 0)
                or (item.material is not None and getattr(item.material, "digestible_mass_micrograms", 0) <= 2_000 and sum(item.material.tastant_mass_micrograms) < 2_000)
            )
        else:
            is_known_non_food = bool(
                item.material is None
                or (item.material is not None and sum(item.material.tastant_mass_micrograms) < 2_000)
                or (getattr(item, "tastant_remaining_micrograms", None) is not None and item.tastant_remaining_micrograms <= 0)
                or c_entry.get("non_nutritive")
                or c_entry.get("currently_depleted")
                or (tested_non_nutritive_ids and item.object_id in tested_non_nutritive_ids)
            )
        if not (feeding and is_known_non_food):
            out.append(("grasp", item.object_id, (GraspContactCommand(BEAT_MICROSECONDS),), item.object_id, None))
    if held is None:
        for item in reachable:
            if item.material is not None:
                if feeding and not is_genuine_food_object(item.object_id):
                    continue
                out.append(("touch", item.object_id, (TouchContactCommand(item.object_id, BEAT_MICROSECONDS),), item.object_id, None))

    # 3. (Release held item deferred to end of candidates)

    seen_food_ids = {thing.object_id for thing in seen if thing.is_food}

    # 4. Toward every sensed food target, nearest first (the least strides to reach)
    if held is None and not in_high_chair:
        food = sorted((thing for thing in seen if thing.is_food and is_genuine_food_object(thing.object_id)),
                      key=lambda thing: (thing.distance_mm, thing.object_id))
        for item in food:
            stop = body.radius_mm + item.radius_mm + STOP_MARGIN_MM
            if item.distance_mm > stop + ARRIVAL_MM:
                out.append(("toward_food", item.object_id, move_commands_toward(snapshot, item.position, stop), item.object_id, None))

        # 4c. Undepleted food in current room beyond retinal field (under metabolic drive)
        if feeding and here is not None:
            room_foods = [
                item for item in snapshot.objects
                if item.position is not None
                and is_genuine_food_object(item.object_id)
                and item.object_id not in seen_food_ids
                and item.material is not None
                and getattr(item.material, "digestible_mass_micrograms", 0) > 0
                and not (conserved_objects and conserved_objects.get(item.object_id, {}).get("currently_depleted"))
                and _region_of(snapshot, item.position, item.radius_mm) is here
            ]
            for item in sorted(room_foods, key=lambda it: _distance_mm(position, it.position)):
                stop = body.radius_mm + item.radius_mm + STOP_MARGIN_MM
                dist = _distance_mm(position, item.position)
                if dist > stop + ARRIVAL_MM:
                    out.append(("toward_food", item.object_id, move_commands_toward(snapshot, item.position, stop), item.object_id, None))

        # 4b. Cognitive Asset 4: Toward occluded / conserved food targets not currently in retinal sight (under metabolic drive)
        if feeding and conserved_objects:
            conserved_food = []
            for obj_id, c_entry in conserved_objects.items():
                if not is_genuine_food_object(obj_id):
                    continue
                has_nourished = int(c_entry.get("fed_count", 0)) > 0 or int(c_entry.get("historical_intake_micrograms", 0)) > 0 or (consequence_food_ids is not None and obj_id in consequence_food_ids)
                is_viable = has_nourished and not c_entry.get("currently_depleted", False)
                if is_viable and obj_id not in seen_food_ids:
                    snap_obj = _object(snapshot, obj_id)
                    if snap_obj is not None:
                        pos = PositionMM(*c_entry["position"])
                        dist = _distance_mm(body.pose.position, pos)
                        stop = body.radius_mm + int(c_entry.get("radius_mm", 100)) + STOP_MARGIN_MM
                        if dist > stop + ARRIVAL_MM:
                            food_reg = _region_of(snapshot, pos, 100)
                            if here is not None and food_reg is not None and here.region_id != food_reg.region_id:
                                route = _portal_route(snapshot, here.region_id, food_reg.region_id)
                                if route:
                                    first_portal = route[0]
                                    commands = _door_motor_commands(snapshot, first_portal, here.region_id)
                                    if commands:
                                        conserved_food.append((dist, obj_id, f"via {first_portal.portal_id} toward {obj_id} (conserved)", commands))
                                # Physical Invariant: When the target lies across room boundaries,
                                # never fall through to direct Euclidean movement through solid walls!
                                continue
                            conserved_food.append((dist, obj_id, f"{obj_id} (conserved)", move_commands_toward(snapshot, pos, stop)))
            conserved_food.sort(key=lambda x: (x[0], x[1]))
            for dist, obj_id, detail, cmds in conserved_food[:2]:
                out.append(("toward_food", detail, cmds, obj_id, None))

    # 5. Toward bed (multi-room topological portal routing across doorways)
    bed = next((thing for thing in seen if thing.object_id == BED_ID), None) if not in_high_chair else None
    if bed is not None and bed.distance_mm > ARRIVAL_MM + STEP_MM // 2:
        out.append(("toward_bed", "her bed", move_commands_toward(snapshot, bed.position, 0), bed.object_id, None))
    elif bed is None and sleepy and conserved_objects and BED_ID in conserved_objects:
        c_bed = conserved_objects[BED_ID]
        bed_pos = PositionMM(*c_bed["position"])
        bed_dist = _distance_mm(body.pose.position, bed_pos)
        if bed_dist > ARRIVAL_MM + STEP_MM // 2:
            bed_reg = _region_of(snapshot, bed_pos, 100)
            if here is not None and bed_reg is not None and here.region_id != bed_reg.region_id:
                route = _portal_route(snapshot, here.region_id, bed_reg.region_id)
                if route:
                    first_portal = route[0]
                    commands = _door_motor_commands(snapshot, first_portal, here.region_id)
                    if commands:
                        out.append(("toward_bed", "via " + first_portal.portal_id + " toward bed", commands, BED_ID, None))
                else:
                    out.append(("toward_bed", "her bed (conserved)", move_commands_toward(snapshot, bed_pos, 0), BED_ID, None))
            else:
                out.append(("toward_bed", "her bed (conserved)", move_commands_toward(snapshot, bed_pos, 0), BED_ID, None))

    # 6. Toward every sensed thing, nearest first (the least strides to reach)
    seen_thing_ids = {thing.object_id for thing in seen if not thing.is_food}
    things = sorted(
        (thing for thing in seen if not thing.is_food),
        key=lambda thing: (
            not handleable(_object(snapshot, thing.object_id)),
            thing.distance_mm,
            thing.object_id,
        ),
    ) if not in_high_chair else []
    for item in things:
        stop = body.radius_mm + item.radius_mm + (HANDLE_STOP_MM if held is None and handleable(_object(snapshot, item.object_id)) else WANDER_STOP_MM)
        if item.distance_mm > stop + ARRIVAL_MM:
            out.append(("toward_thing", item.object_id, move_commands_toward(snapshot, item.position, stop), item.object_id, None))


    # 6b. Toward the caregiver when seen; her palm to the caregiver's palm when near
    # enough for her reach (the world settles the geometry and refuses what it cannot).
    person = caregiver_in_sight(snapshot)
    if person is not None:
        if not in_high_chair and person.distance_mm > PERSON_STOP_MM + ARRIVAL_MM:
            out.append(("toward_person", person.object_id, move_commands_toward(snapshot, person.position, PERSON_STOP_MM), person.object_id, None))
        if held is None and person.distance_mm <= body.reach_mm + person.radius_mm:
            commands = tuple(
                BodySurfaceContactCommand((BodySurfaceActuation(actor_site_id=mine, recipient_body_id=person.object_id, recipient_site_id=theirs,
                                                                compression_micrometres=1_000, tangential_u_micrometres=0, tangential_v_micrometres=0),), BEAT_MICROSECONDS)
                for mine, theirs in REACH_SITES)
            out.append(("reach_hand", "her palm to the caregiver's hand", commands, person.object_id, None))

    # 7. Toward every door of her room
    here = _region_of(snapshot, position, body.radius_mm)
    if here is not None and not in_high_chair:
        doors = [item for item in snapshot.portals if here.region_id in item.region_ids]
        for portal in sorted(doors, key=lambda item: (_distance_mm(position, door_crossing(snapshot, item, here.region_id)[0]), item.portal_id)):
            if last_crossed_portal is not None:
                p_id, p_tick = last_crossed_portal
                window = 4 if feeding else 12
                if portal.portal_id == p_id and (tick - p_tick) < window:
                    continue
            commands = _door_motor_commands(snapshot, portal, here.region_id)
            if commands:
                out.append(("toward_door", portal.portal_id, commands, portal.portal_id, None))

    # 8. Elementary motions, airway, rest
    if not in_high_chair:
        if modular_sub is not None:
            if not hasattr(modular_sub, "get_motor_efferent") and not hasattr(modular_sub, "motor_efferents"):
                raise AttributeError("Modular substrate lacks required motor efferent capability ('get_motor_efferent' or 'motor_efferents')")
            eff = (
                modular_sub.get_motor_efferent()
                if hasattr(modular_sub, "get_motor_efferent")
                else modular_sub.motor_efferents()
            )
            native_cmd = motor_efferent_to_locomotion_command(eff, body.pose, BEAT_MICROSECONDS)
            if native_cmd is not None:
                out.append(("step", f"native substrate motor stride {eff[1]:.1f}mm steer {eff[2]:.1f}deg", (native_cmd,), None, None))
            # Critical: when native substrate is present, silent efferents inhibit locomotion:
            # NO fallback programmed stride is appended.
        else:
            dx, dy = rotate_lattice_offset(STEP_MM, 0, heading)
            ahead = PositionMM(position.x + dx, position.y + dy, position.z)
            out.append(("step", "one stride ahead", (MoveCommand(PoseMM(ahead, heading), BEAT_MICROSECONDS),), None, None))
        for name, sign in (("turn_left", 1), ("turn_right", -1)):
            out.append((name, "", (MoveCommand(PoseMM(position, (heading + sign * TURN_MILLIDEGREES) % 360_000), BEAT_MICROSECONDS),), None, None))
    if not sound_heard:
        drive = say_drive if say_drive is not None else DEFAULT_DRIVE
        out.append(("say", say_detail, (), None, drive))
    out.append(("rest", "", (), None, None))
    # Release held item (deferred after elementary motions/rest to allow exploratory holding/inspection)
    if held is not None and drop_spot_clear(snapshot, body, held):
        out.append(("release", held.object_id, (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id, None))

    out = [option for option in out if option[0] not in MOVES or option[2]]
    assert len(out) <= MAX_CANDIDATES
    return out






def _capture_sensory_key(snapshot: Any, body: Any, state: dict[str, Any], seen: tuple[SeenThing, ...]) -> str:
    """Exact available cue distinctions for this reduced episodic controller.

    IDs resolve current sensory custody, but are not included as recognition keys.
    Missing visual/contact evidence remains None, never a manufactured figure.
    """
    target = body.held_object_id or state.get("gaze_target") or state.get("joint_attention_target")
    obj = _object(snapshot, target) if target is not None else None
    if obj is None and seen:
        target = seen[0].object_id
        obj = _object(snapshot, target)
    relation = None if obj is None else ("reach" if in_hand_reach(snapshot, obj) else "far")
    contact = getattr(body, "active_contact", None)
    contact_id = body.held_object_id or getattr(contact, "object_id", None)
    touched = _object(snapshot, contact_id) if contact_id is not None else None
    material = getattr(touched, "material", None)
    tactile = None if material is None else (
        material.compliance_ppm, material.roughness_micrometers,
        material.surface_temperature_millikelvin,
    )
    return json.dumps(
        (state.get("room_now"), state.get("sight_figure"), body.held_object_id is not None, relation, tactile),
        separators=(",", ":"), ensure_ascii=False,
    )

class FunctionalOrganism:
    """One organism: bounded state, pure decisions, exact encoding."""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    @property
    def _sensorimotor_mesh(self) -> GualaSensorimotorMesh:
        mesh_dict = self._state.get("sensorimotor_mesh")
        cached = getattr(self, "_cached_mesh", None)
        if cached is None:
            if mesh_dict is not None:
                self._cached_mesh = GualaSensorimotorMesh.from_dict(mesh_dict)
            else:
                self._cached_mesh = GualaSensorimotorMesh()
        return self._cached_mesh

    def _sync_sensorimotor_mesh(self) -> None:
        cached = getattr(self, "_cached_mesh", None)
        if cached is not None:
            self._state["sensorimotor_mesh"] = cached.to_dict()

    @property
    def _ternary_substrate(self) -> TernaryMultiModalSubstrate:
        sub_dict = self._state.get("ternary_substrate")
        cached = getattr(self, "_cached_ternary_substrate", None)
        if cached is None:
            if sub_dict is not None:
                self._cached_ternary_substrate = TernaryMultiModalSubstrate.from_dict(sub_dict)
            else:
                self._cached_ternary_substrate = TernaryMultiModalSubstrate()
        return self._cached_ternary_substrate

    def _sync_ternary_substrate(self) -> None:
        cached = getattr(self, "_cached_ternary_substrate", None)
        if cached is not None:
            self._state["ternary_substrate"] = cached.to_dict()

    @property
    def _modular_substrate(self) -> ModularColumnSubstrate:
        sub_dict = self._state.get("modular_substrate")
        cached = getattr(self, "_cached_modular_substrate", None)
        if cached is None:
            if sub_dict is not None:
                # Ordinary restoration never migrates history or changes the
                # stored generation as a side effect of reading a property.
                # Explicit predecessor migration is a separate custody operation.
                self._cached_modular_substrate = ModularColumnSubstrate.from_dict(sub_dict)
            else:
                self._cached_modular_substrate = ModularColumnSubstrate()
        return self._cached_modular_substrate

    def _sync_modular_substrate(self) -> None:
        cached = getattr(self, "_cached_modular_substrate", None)
        if cached is not None:
            self._state["modular_substrate"] = cached.to_dict()

    # ----- genesis, restore, encode -------------------------------------------------

    @classmethod
    def genesis(cls, *, identity: str, organism_tick: int) -> "FunctionalOrganism":
        if not isinstance(identity, str) or not identity or isinstance(organism_tick, bool) or not isinstance(organism_tick, int) or organism_tick < 0:
            raise ValueError("functional organism genesis needs an identity and a tick")
        return cls({
            "schema": SCHEMA, "identity": identity, "tick": organism_tick,
            "cochlear_current": {"origin_tick": organism_tick, "state_hex": CochlearStream().checkpoint_bytes().hex()},
            "reserve_micrograms": CAPACITY_MICROGRAMS * 55 // 100, "feeding": False,
            "streams": {name: [] for name in STREAMS},
            "familiarity": {}, "episodes": [], "heard": [], "voice": [],
            "refusals": {}, "last_act": "rest", "last_spoke_tick": 0,
            "pending_voice": None, "pending_drive": None, "meals_micrograms": 0, "bites": 0, "strides": 0, "syllables": 0,
            "voice_version": VOICE_VERSION, "ambient_sound": 0.0, "handled": 0, "room_now": None,
            "head": [0, 0], "acts": {}, "pending_act": None, "last_chosen": None,
            "sleep_pressure": 0, "asleep": False, "learned": {}, "nights": 0, "act_totals": {}, "contact_pressure": 0, "pending_contact": 0.0, "pending_contact_millikelvin": None, "reading_until_tick": 0,
            "target_totals": {}, "taste_residue": 0.0,
            "speech": {}, "syllable_totals": {}, "prior_syllable": None, "syllable_profiles": {},
            "ear_event": None, "events": {}, "sound_event": None, "ear_quiet": _empty_ear_quiet(),
            "gaze": None, "gaze_target": None, "sight_figure": None, "figures": {}, "eyes": [0, 0], "gaze_radius": 0.0,
            "moments": {}, "last_moment": None, "ternary_substrate": None, "modular_substrate": None,
            "voice_event": None, "own_events": {}, "own_event": None, "meanings": {}, "last_said": None, "affordance_plan": None, "planned_target_id": None, "conserved_objects": {}, "tested_non_nutritive": [], "expectation_discrepancy": None, "joint_attention_target": None, "pending_chain": [], "last_demand_chain": None,
            "room_dwell_beats": 0, "prior_room": None, "region_visits": {}, "region_last_tick": {},
        })

    @classmethod
    def restore(cls, encoded: bytes) -> "FunctionalOrganism":
        """Restore the current encoding exactly, without changing lived state."""
        if not isinstance(encoded, bytes) or not encoded.startswith(MAGIC):
            raise ValueError("unsupported format: encoded body is not a functional organism")
        state = json.loads(encoded[len(MAGIC):].decode("utf-8"))
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise ValueError("functional organism schema changed")
        organism = cls(state)
        if organism.encoded() != encoded:
            raise ValueError("functional organism body does not re-encode exactly")
        organism.migrate()
        return organism

    def migrate(self) -> bool:
        """Validate the supported stored law without changing any records.

        Existing callers retain this method, but ordinary restoration cannot
        supply missing experience, discard history, or reset a changed voice
        law. Unsupported state needs a separately implemented lossless
        transition; preserving current bytes does not certify cognition.
        """
        if self._state.get("schema") != SCHEMA:
            raise ValueError("functional organism schema changed")
        version = self._state.get("voice_version")
        if type(version) is not int or version != VOICE_VERSION:
            raise ValueError("functional organism voice law is unsupported; retained state was not changed")
        return False

    def encoded(self) -> bytes:
        return MAGIC + json.dumps(self._state, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

    # ----- the runtime contract the actor and the checkpoint worker use -------------

    @property
    def live_organism_tick(self) -> int:
        return int(self._state["tick"])

    @property
    def identity(self) -> str:
        return str(self._state["identity"])

    @property
    def head(self) -> tuple[int, int]:
        """Her head's (yaw, pitch) in millidegrees, from her own record."""

        head = self._state.get("head") or [0, 0]
        return int(head[0]), int(head[1])

    @property
    def eyes(self) -> tuple[int, int]:
        """Her eyes' (yaw, pitch) in her head, in millidegrees (both eyes together)."""

        eyes = self._state.get("eyes") or [0, 0]
        return int(eyes[0]), int(eyes[1])

    @property
    def carriage(self) -> tuple[int, int]:
        """Where her retina points in her body's frame: neck and eyes together."""

        head, eyes = self.head, self.eyes
        return head[0] + eyes[0], int(_clamp(head[1] + eyes[1], -CARRIAGE_PITCH_BOUND_MILLIDEGREES, CARRIAGE_PITCH_BOUND_MILLIDEGREES))

    @property
    def body_axes(self) -> tuple[tuple[object, ...], ...]:
        """The declared axes, with the neck where her head law has turned it."""

        yaw, pitch = self.head
        eye_yaw, eye_pitch = self.eyes
        aperture = 0 if self.asleep else EYELID_OPEN_MICROMETRES
        positions = {"neck_yaw": yaw, "neck_pitch": pitch, "left_eyelid_aperture": aperture, "right_eyelid_aperture": aperture,
                     "left_eye_yaw": eye_yaw, "left_eye_pitch": eye_pitch, "right_eye_yaw": eye_yaw, "right_eye_pitch": eye_pitch}
        return tuple(
            (axis[0], axis[1], axis[2], positions[axis[1]], *axis[4:]) if axis[1] in positions else axis
            for axis in BODY_AXES
        )

    @property
    def asleep(self) -> bool:
        return bool(self._state.get("asleep"))

    @property
    def contact(self) -> dict[str, object]:
        """Her need for contact as the page sees it: the pressure over its ceiling,
        and the fraction of her skin that met another body's on her last beat
        (the caregiver's touch, or her own palm on the caregiver's hand)."""

        window = self._state.get("streams", {}).get("skin_contact") or []
        return {"pressure": [int(self._state.get("contact_pressure", 0)), CONTACT_PRESSURE_CEILING], "felt": float(window[-1]) if window else 0.0}

    @property
    def sleep(self) -> dict[str, object]:
        """Her sleep as the page sees it: asleep or not, and the pressure over its ceiling."""

        return {"asleep": self.asleep, "pressure": [int(self._state.get("sleep_pressure", 0)), SLEEP_PRESSURE_CEILING], "nights": int(self._state.get("nights", 0))}

    @property
    def ear(self) -> dict[str, object]:
        """Her acoustic gate as the page sees it: the events that closed on her last
        beat (their keys and how many times she has met each), whether one is open
        and for how many frames, the last event closed (key, tick), and how many
        events her day's store holds."""

        state = self._state
        closed = [str(key) for key in getattr(self, "_ear_closed", [])]
        events = state.get("events") or {}
        open_event = state.get("ear_event")
        last = state.get("sound_event")
        own_closed = [str(key) for key in getattr(self, "_own_closed", [])]
        return {
            "closed": closed, "met": [int(events[key][0]) for key in closed if key in events],
            "open": open_event is not None, "open_frames": 0 if open_event is None else len(open_event["frames"]),
            "last": None if last is None else [str(last[0]), int(last[1])], "events": len(events),
            "own_closed": own_closed, "own_events": len(state.get("own_events") or {}),
        }

    def readiness(self) -> Readiness:
        encoded = self.encoded()
        return Readiness(self.identity, self.live_organism_tick, _sha256(encoded), len(encoded), 0, self.body_axes)

    def snapshot_lived_state(self) -> LivedState:
        return LivedState(self.live_organism_tick, self.encoded())

    def validate_lived_checkpoint(self, checkpoint: Any) -> None:
        if not isinstance(checkpoint, Checkpoint) or checkpoint.organism_tick > self.live_organism_tick:
            raise RuntimeError("functional checkpoint is not from this life")
        if _sha256(checkpoint.encoded_generation()) != checkpoint.state_sha256:
            raise RuntimeError("functional checkpoint receipt changed")

    def adopt_published_lived_checkpoint(self, checkpoint: Any) -> None:
        self.validate_lived_checkpoint(checkpoint)

    # ----- measured state -----------------------------------------------------------

    @property
    def feeding(self) -> bool:
        if int(self._state.get("sleep_pressure", 0)) >= SLEEP_PRESSURE_CEILING and self.reserve_micrograms >= int(CAPACITY_MICROGRAMS * Fraction(3, 4)):
            return False
        return bool(self._state["feeding"]) or self.reserve_micrograms < CAPACITY_MICROGRAMS * HUNGRY_BELOW

    @property
    def reserve_micrograms(self) -> int:
        return int(self._state["reserve_micrograms"])

    @property
    def deficit(self) -> Fraction:
        return Fraction(CAPACITY_MICROGRAMS - self.reserve_micrograms, CAPACITY_MICROGRAMS)

    @property
    def pending_voice(self) -> bytes | None:
        raw = self._state.get("pending_voice")
        return None if raw is None else base64.b64decode(raw)

    @property
    def gaze(self) -> tuple[float, float] | None:
        """Where she is looking within her focal field, as a declared law: the
        luminance-weighted centre of the last focal field she sensed, in
        (horizontal, vertical) fractions of the field; None before the first beat."""

        gaze = self._state.get("gaze")
        if gaze is not None:
            return float(gaze[0]), float(gaze[1])   # on the thing she acts on, by the world's own geometry
        horizontal = self._state["streams"]["sight_horizontal"]
        vertical = self._state["streams"]["sight_vertical"]
        if not horizontal or not vertical:
            return None
        return float(horizontal[-1]), float(vertical[-1])

    @property
    def eye(self) -> dict[str, object]:
        """Her eye as the page sees it: the figure under her gaze this beat (its key,
        its shape in eighths, its extent, how many times met), the store's size, her
        gaze, her head, and what she is looking at."""

        state = self._state
        figure: Figure | None = getattr(self, "_figure", None)
        figures = state.get("figures") or {}
        key = state.get("sight_figure")
        return {
            "figure": key, "look": None if figure is None else list(figure.look), "radius_sites": 0.0 if figure is None else figure.radius_sites,
            "extent": 0.0 if figure is None else round(figure.extent, 4), "met": int(figures[key][0]) if key in figures else 0,
            "figures": len(figures), "gaze": state.get("gaze"), "head": list(self.head), "eyes": list(self.eyes), "target": state.get("gaze_target"),
        }

    @property
    def counts(self) -> dict[str, int]:
        counts = {key: int(self._state.get(key, 0)) for key in ("bites", "strides", "syllables", "meals_micrograms", "handled")}
        counts["structures"] = len(self._state.get("acts", {}))
        counts["learned"] = len(self._state.get("learned", {}))
        counts["nights"] = int(self._state.get("nights", 0))
        counts["events"] = len(self._state.get("events") or {})
        counts["figures"] = len(self._state.get("figures") or {})
        counts["moments"] = len(self._state.get("moments") or {})
        counts["own_events"] = len(self._state.get("own_events") or {})
        counts["meanings"] = len(self._state.get("meanings") or {})
        counts["conserved_objects"] = len(self._state.get("conserved_objects") or {})
        counts["active_synapses"] = self._ternary_substrate.matrix_statistics()[2]
        counts["modular_active_synapses"] = self._modular_substrate.active_synapses()
        return counts

    @property
    def spatial_tracking(self) -> tuple[float, int, float, bool]:
        """Spatial permanence coordinates from Column 1: (r_mm, theta_mdeg, persistence_trace, is_occluded)."""
        return self._modular_substrate.get_spatial_tracking()

    @property
    def barrier_refusal_active(self) -> bool:
        """Physical barrier refusal flag from Column 3."""
        return self._modular_substrate.is_barrier_refusal_active()

    @property
    def physically_transitioned_neuron_count(self) -> int:
        """Synapses that physically underwent plastic yield deformation on the last step."""
        return int(getattr(self, "_physically_transitioned_neuron_count", 0))

    @property
    def motor_efferent(self) -> tuple[float, ...]:
        """Causal motor efferents from Layer 5 motor pyramidal columns: (vocal, stride, steer, grip)."""
        return self._modular_substrate.get_motor_efferent()

    @property
    def mouth_efferent(self) -> int:
        """Column 44's signed L5 jaw population from the modular substrate."""
        if hasattr(self._modular_substrate, "get_mouth_efferent"):
            try:
                return self._modular_substrate.get_mouth_efferent()
            except (NotImplementedError, AttributeError):
                pass
        return 0

    @property
    def conserved_objects(self) -> dict[str, Any]:
        """Cognitive Asset 4: The topological spatial conservation register of unobserved and observed entities."""
        return dict(self._state.get("conserved_objects") or {})

    @property
    def joint_attention_target(self) -> str | None:
        """Cognitive Asset 5: The entity currently focused under joint attention with the caregiver."""
        return self._state.get("joint_attention_target")

    @property
    def moment(self) -> dict[str, object] | None:
        """The moment that formed on her last beat, as the page sees it: its key, how many
        times met, the context it carried, what has followed it by count, and the bites
        that followed it; None on a beat without one."""

        formed = getattr(self, "_moment_formed", None)
        if formed is None:
            return None
        entry = (self._state.get("moments") or {}).get(formed)
        if entry is None:
            return None
        following = sorted(entry.get("next", {}).items(), key=lambda kv: (-int(kv[1]), kv[0]))[:3]
        return {"key": formed, "count": int(entry["count"]), "source": entry.get("source", "heard"), "held": entry.get("held", "none"),
                "context": list(entry.get("context", [])), "next": following, "fed": int(entry.get("fed", 0))}

    # ----- the kernel over her measured streams --------------------------------------

    def _measure(self, sensed: Sensed, seen: tuple[SeenThing, ...], body: Any) -> dict[str, float]:
        focal = sensed.focal_luminance_u8
        total = sum(focal)
        horizontal, vertical = structure_centre(focal)
        heard = sensed.heard_profile
        if heard is not None and sum(heard) > 0:
            energy = sum(heard) / len(heard)
            pitch = sum(value * index for index, value in enumerate(heard)) / (sum(heard) * (len(heard) - 1))
        else:
            energy, pitch = 0.0, 0.5
        # Her ear's shape of the sound: only a sound that stands out of the room's
        # noise has a shape (the same floor her hearing uses), else silence.
        shape = ear_bands(heard) if (heard is not None and energy >= HEARD_ENERGY_FLOOR) else (0.0,) * EAR_BANDS
        food = [thing for thing in seen if thing.is_food]

        snapshot = sensed.snapshot
        here = _region_of(snapshot, body.pose.position, body.radius_mm)

        # Smell: the room's air as the world keeps it (odorant mass over the
        # room's volume), over her nose's declared saturation (the world's
        # receptor geometry); both are the world's own numbers. Nearby things
        # reach her nose only through the air the world already diffuses into.
        smell_val = 0.0
        air = getattr(here, "air", None) if here is not None else None
        nose = getattr(getattr(body, "receptor_geometry", None), "odorant_saturation_nanograms_per_cubic_meter", None)
        if air is not None and nose:
            masses = getattr(air, "odorant_mass_nanograms", ())
            volume_mm3 = getattr(air, "volume_cubic_mm", 0)
            if masses and volume_mm3 > 0:
                per_cubic_metre = [mass * 1_000_000_000 / volume_mm3 for mass in masses]
                smell_val = _clamp(sum(c / s for c, s in zip(per_cubic_metre, nose) if s > 0) / max(1, len(nose)), 0.0, 1.0)

        # Passive 2: Taste residue (salivary residue from eating + food held at mouth)
        # Taste is the residue of what she has taken in, decaying each beat
        # (a body law like her metabolism); holding food is not tasting.
        taste_val = _clamp(float(self._state.get("taste_residue", 0.0)), 0.0, 1.0)

        # Passive 3: Touch / Texture (surface compliance and roughness of held or contact object)
        # Touch is what her hand or mouth is actually on (the world's signed
        # contact) or what she holds; a thing merely within reach is not felt.
        touch_val = 0.0
        contact_obj = None
        contact = getattr(body, "active_contact", None)
        if body.held_object_id is not None:
            contact_obj = _object(snapshot, body.held_object_id)
        elif contact is not None and getattr(contact, "object_id", None) is not None:
            contact_obj = _object(snapshot, contact.object_id)
        if contact_obj is not None and contact_obj.material is not None:
            comp = getattr(contact_obj.material, "compliance_ppm", 0) / 1_000_000.0
            rough = getattr(contact_obj.material, "roughness_micrometers", 0) / 1_000.0
            touch_val = (comp + rough) / 2.0
        touch_val = _clamp(touch_val, 0.0, 1.0)

        # Thermal contrast at contact: the surface her skin meets (a thing in her hand
        # or under it, food at her mouth, the caregiver's skin on hers or under her palm)
        # minus her own skin temperature, over her receptors' declared span; 0.5 = no
        # contrast or no contact. Pain is the excess above nature's threshold.
        geometry = getattr(body, "receptor_geometry", None)
        self._receptor_geometry = geometry
        span_mk = (int(geometry.touch_temperature_max_millikelvin) - int(geometry.touch_temperature_min_millikelvin)) if geometry is not None else 50_000
        half_span = max(1, span_mk // 2)
        skin_mk = sensed.skin_temperature_millikelvin
        met_mk = None
        if contact_obj is not None and contact_obj.material is not None:
            met_mk = int(contact_obj.material.surface_temperature_millikelvin)
        if sensed.touch_surface_millikelvin is not None:
            met_mk = int(sensed.touch_surface_millikelvin) if met_mk is None else max(met_mk, int(sensed.touch_surface_millikelvin))
        pending_mk = self._state.get("pending_contact_millikelvin")
        if float(self._state.get("pending_contact", 0.0)) > 0 and pending_mk is not None:
            met_mk = int(pending_mk) if met_mk is None else max(met_mk, int(pending_mk))
        contrast_mk = (met_mk - int(skin_mk)) if (met_mk is not None and skin_mk is not None) else 0
        touch_warmth = _clamp(0.5 + contrast_mk / (2.0 * half_span), 0.0, 1.0)
        self._met_mk = met_mk
        self._warmth_likeness = _clamp(1.0 - abs(contrast_mk) / float(half_span), 0.0, 1.0) if met_mk is not None else 0.0
        self._pain = _clamp((met_mk - NOCICEPTION_MILLIKELVIN) / float(max(1, int(geometry.touch_temperature_max_millikelvin) - NOCICEPTION_MILLIKELVIN)) if (met_mk is not None and geometry is not None) else 0.0, 0.0, 1.0)

        # Her sleep pressure as a stream of its own (hunger is already one).
        deficit = float(self.deficit)
        sleep_ratio = _clamp(float(self._state.get("sleep_pressure", 0)) / SLEEP_PRESSURE_CEILING, 0.0, 1.0)
        contact_ratio = _clamp(float(self._state.get("contact_pressure", 0)) / CONTACT_PRESSURE_CEILING, 0.0, 1.0)

        return {
            "sight_luminance": (total / len(focal) / 255) if focal else 0.0,
            "sight_horizontal": horizontal,
            "sight_vertical": vertical,
            "sound_energy": _clamp(energy * 4, 0.0, 1.0),
            "sound_pitch": pitch,
            "smell_odour": smell_val,
            "taste_residue": taste_val,
            "touch_texture": touch_val,
            "sleep_pressure": sleep_ratio,
            "skin_contact": _clamp(max(float(sensed.skin_contact), float(self._state.get("pending_contact", 0.0))), 0.0, 1.0),
            "contact_pressure": contact_ratio,
            "touch_warmth": touch_warmth,
            **{f"ear_band_{index}": shape[index] for index in range(EAR_BANDS)},
            "hunger": deficit,
            "food_distance": (food[0].distance_mm / SIGHT_RANGE_MM) if food else 1.0,
            "heading": body.pose.heading_millidegrees / 360_000,
            "hand": 1.0 if body.held_object_id is not None else 0.0,
        }

    def _kernel(self) -> tuple[str, int]:
        """Run L0-L4 over every stream's trailing window; the signature is the
        last gate's regime and the signs of its 7 discrete field atoms
        (D_k, M_k, R_rev_k, U*_k, C_k, P_k, B_k) per stream. Returns (signature, gates delivered)."""

        tokens = []
        gates_total = 0
        dsf_states = {}
        for name in STREAMS:
            window = self._state["streams"][name]
            if len(window) < KERNEL_MINIMUM:
                tokens.append("________")
                continue
            sev = compute_sev_series(pd.DataFrame({"field": [STREAM_FLOOR + value for value in window]}), "field")
            gates = tuple(segment_gates(sev))
            build_gate_l1_state(sev, gates)
            l2 = tuple(interpret_gates(sev, gates))
            res = list(compute_resonance(l2))
            l4 = tuple(compute_dsf(compute_directional_signal(res)))
            gates_total += len(gates)
            last = l4[-1]
            p_k = float(last.P_k)
            b_k = float(last.B_k)
            s_uf = (b_k - p_k) if b_k > 0 else -p_k
            dsf_states[name] = {
                "D_k": float(last.D_k),
                "M_k": float(last.M_k),
                "R_rev_k": float(last.R_rev_k),
                "U_star_k": float(last.U_star_k),
                "C_k": float(last.C_k),
                "P_k": p_k,
                "B_k": b_k,
                "S_UF": float(s_uf),
                "regime": l2[-1].regime,
            }
            token = (
                l2[-1].regime[0]
                + _sign(last.D_k)
                + _sign(last.M_k)
                + _sign(last.R_rev_k)
                + _sign(last.U_star_k - 0.5)
                + _sign(last.C_k)
                + _sign(last.P_k)
                + _sign(last.B_k)
            )
            tokens.append(token)
        self._last_dsf_states = dsf_states
        return " ".join(tokens), gates_total

    def decide(self, sensed: Sensed) -> Decision:
        tick = self.live_organism_tick
        state = self._state
        snapshot = sensed.snapshot
        body = _self_body(snapshot)
        consequence_foods = _consequence_grounded_food_ids(state)
        known_foods = _consequence_qualified_food_ids(state)
        seen = things_in_sight(snapshot, known_food_ids=known_foods)
        here = _region_of(snapshot, body.pose.position, body.radius_mm)
        state["room_now"] = None if here is None else here.region_id
        cur_room = state.get("room_now")
        prior_room = state.get("prior_room")
        tracked_room = state.get("_current_tracked_room")
        if cur_room is not None:
            if tracked_room is not None and cur_room != tracked_room:
                state["prior_room"] = tracked_room
                state["_current_tracked_room"] = cur_room
                state["room_dwell_beats"] = 1
                for p in snapshot.portals:
                    if tracked_room in p.region_ids and cur_room in p.region_ids:
                        state["last_crossed_portal"] = (p.portal_id, tick)
                        break
            elif tracked_room is None:
                state["_current_tracked_room"] = cur_room
                state["room_dwell_beats"] = 1
            else:
                state["room_dwell_beats"] = 1 if state.get("asleep") else (int(state.get("room_dwell_beats", 0)) + 1)
            reg_visits = state.setdefault("region_visits", {})
            reg_visits[cur_room] = int(reg_visits.get(cur_room, 0)) + 1
            reg_last = state.setdefault("region_last_tick", {})
            reg_last[cur_room] = tick
        else:
            state["_current_tracked_room"] = None

        # Cognitive Asset 4: Spatial Object Permanence & Occlusion Conservation (The Piaget Invariant)
        conserved = state.setdefault("conserved_objects", {})
        current_room = state.get("room_now")

        # 1. Update from instantaneous retinal sight
        tested_non_nutritive = set(state.get("tested_non_nutritive") or ())
        for thing in seen:
            if thing.position is not None:
                is_fixture = thing.object_id in PERMANENCE_FIXTURES
                entry = conserved.setdefault(thing.object_id, {})
                entry.update({
                    "object_id": thing.object_id,
                    "position": (int(thing.position.x), int(thing.position.y), int(thing.position.z)),
                    "radius_mm": int(thing.radius_mm),
                    "room_id": current_room,
                    "is_fixture": is_fixture,
                    "last_seen_tick": tick,
                    "confidence": 1.0,
                })
                if not is_genuine_food_object(thing.object_id) or thing.object_id in tested_non_nutritive or entry.get("non_nutritive") is True:
                    entry["non_nutritive"] = True
                    entry["is_food"] = False
                    entry["tested_non_food"] = True
                else:
                    has_nourished = int(entry.get("fed_count", 0)) > 0 or int(entry.get("historical_intake_micrograms", 0)) > 0 or (thing.object_id in consequence_foods)
                    entry["is_food"] = bool(has_nourished and not entry.get("currently_depleted", False))
                fig = state.get("sight_figure")
                if fig and fig != "none" and (state.get("gaze_target") == thing.object_id or (body.held_object_id == thing.object_id) or (seen and seen[0].object_id == thing.object_id)):
                    entry["figure_key"] = fig

        # 2. Update held object position (moves with Guala's body)
        if body.held_object_id is not None and body.held_object_id in conserved:
            conserved[body.held_object_id]["position"] = (int(body.pose.position.x), int(body.pose.position.y), int(body.pose.position.z))
            conserved[body.held_object_id]["room_id"] = current_room
            conserved[body.held_object_id]["last_seen_tick"] = tick
            conserved[body.held_object_id]["confidence"] = 1.0

        # 3. Expectation Discrepancy & Verification (Invariant Violation Detection)
        seen_ids = {th.object_id for th in seen}
        for obj_id, c_entry in list(conserved.items()):
            if c_entry.get("is_fixture") or obj_id == body.held_object_id:
                continue
            c_pos = PositionMM(*c_entry["position"])
            dist_to_conserved = _distance_mm(body.pose.position, c_pos)
            if dist_to_conserved <= DISCREPANCY_VERIFICATION_DISTANCE_MM:
                bearing = _heading_toward(body.pose.position, c_pos)
                if abs(_bearing_offset(body.pose.heading_millidegrees, bearing)) <= FIELD_OF_VIEW_MILLIDEGREES:
                    if obj_id not in seen_ids:
                        del conserved[obj_id]
                        state["expectation_discrepancy"] = {
                            "object_id": obj_id,
                            "last_position": c_entry["position"],
                            "tick": tick,
                        }

        # Enforce memory capacity bound
        while len(conserved) > OBJECT_PERMANENCE_CAPACITY:
            mobile_entries = [k for k, v in conserved.items() if not v.get("is_fixture")]
            if not mobile_entries:
                break
            oldest = min(mobile_entries, key=lambda k: int(conserved[k].get("last_seen_tick", 0)))
            del conserved[oldest]

        # Sound Attunement: When an external sound is heard, or a speaker is speaking,
        # her acoustic orienting reflex turns her neck and eyes to face the speaker.
        sound_source = getattr(sensed, "sound_source_id", None)
        if sound_source is None:
            cg_seen = caregiver_in_sight(snapshot)
            if cg_seen is not None:
                sound_source = cg_seen.object_id

        heard_now = sensed.heard_profile
        sound_heard = False
        is_external = getattr(sensed, "external_sound_present", False) or (
            heard_now is not None and sum(heard_now) > 0 and not getattr(sensed, "self_emission_present", False)
        )
        if heard_now is not None:
            energy = sum(heard_now) / len(heard_now)
            sound_heard = is_external and (energy >= HEARD_ENERGY_FLOOR)

        if sound_heard:
            state["last_sound_heard_tick"] = tick
            if sound_source is not None:
                state["gaze_target"] = sound_source
                state["attended_tick"] = tick

        # Cognitive Asset 5: Social Joint Attention & Caregiver Gaze Vector Tracking
        cg_seen = caregiver_in_sight(snapshot)
        caregiver = next((b for b in snapshot.bodies if b.body_id == cg_seen.object_id), None) if cg_seen is not None else None
        joint_target = None
        if caregiver is not None and body.held_object_id is None:
            joint_info = project_caregiver_gaze_ray(caregiver.pose, snapshot, conserved_objects=conserved)
            if joint_info is not None:
                joint_target = joint_info[0]
                state["joint_attention_target"] = joint_target
                state["joint_attention_tick"] = tick
            else:
                state["joint_attention_target"] = None
        else:
            state["joint_attention_target"] = None

        feeding = state.get("feeding", False) or self.reserve_micrograms < CAPACITY_MICROGRAMS * HUNGRY_BELOW
        if self.reserve_micrograms >= CAPACITY_MICROGRAMS * SATED_ABOVE:
            feeding = False
        planned_food = state.get("planned_target_id") if (feeding and state.get("planned_target_id") in known_foods) else None
        if planned_food and not sound_heard:
            state["gaze_target"] = planned_food
        elif feeding and not sound_heard:
            cand_food = next((s.object_id for s in seen if is_genuine_food_object(s.object_id)), None)
            if cand_food is not None:
                cur_gt = state.get("gaze_target")
                if cur_gt is None or not is_genuine_food_object(cur_gt):
                    state["gaze_target"] = cand_food
        g_tgt = state.get("gaze_target")
        is_portal = any(p.portal_id == g_tgt for p in snapshot.portals)
        is_conserved = bool(conserved and g_tgt in conserved)
        if g_tgt is not None and not is_portal and not is_conserved and (_object(snapshot, g_tgt) is None or g_tgt not in {s.object_id for s in seen}):
            g_tgt = None
        if feeding and body.held_object_id is None and not any(s.is_food for s in seen) and not sound_heard:
            here = _region_of(snapshot, body.pose.position, body.radius_mm)
            if here is not None:
                food_rooms = []
                for obj in snapshot.objects:
                    if obj.material is not None and getattr(obj.material, "digestible_mass_micrograms", 0) > 0 and obj.position is not None:
                        obj_reg = _region_of(snapshot, obj.position, int(obj.radius_mm))
                        if obj_reg is not None and obj_reg.region_id != here.region_id:
                            food_rooms.append(obj_reg.region_id)
                if food_rooms:
                    routes = [(_portal_route(snapshot, here.region_id, fr), fr) for fr in food_rooms]
                    valid_routes = [(r, fr) for r, fr in routes if r]
                    if valid_routes:
                        best_route, _ = min(valid_routes, key=lambda x: len(x[0]))
                        g_tgt = best_route[0].portal_id
                        state["gaze_target"] = g_tgt
        target_id = body.held_object_id or g_tgt or state.get("joint_attention_target") or (seen[0].object_id if seen else None)
        point = None if state.get("asleep") else _target_point(snapshot, body, target_id, conserved_objects=conserved)   # asleep, eyes closed, the head rests
        state["gaze"] = None
        state["gaze_radius"] = 0.0
        if point is not None:
            aim = _aim(body, point)
            gaze = _gaze_in_field(self.carriage, aim)
            state["gaze"] = None if gaze is None else [gaze[0], gaze[1]]
            # The thing's silhouette in her field: its angular radius in sites, from the world's own geometry.
            radius_mm = _target_radius_mm(snapshot, body, target_id, conserved_objects=conserved)
            ex, ey, ez = _eye_position(body)
            distance = max(1.0, math.dist((ex, ey, ez), (point[0], point[1], point[2])))
            state["gaze_radius"] = round(math.degrees(math.atan2(radius_mm, distance)) * 1000 / FOCAL_SITE_MILLIDEGREES, 3)
            state["head"] = list(head_toward(self.head, aim[0], aim[1]))
            # The eyes take up the rest at once, within their range and never past straight down or up.
            eye_yaw = int(_clamp(aim[0] - state["head"][0], -EYE_BOUND_MILLIDEGREES, EYE_BOUND_MILLIDEGREES))
            eye_pitch = int(_clamp(aim[1] - state["head"][1], -EYE_BOUND_MILLIDEGREES, EYE_BOUND_MILLIDEGREES))
            eye_pitch = int(_clamp(eye_pitch, -CARRIAGE_PITCH_BOUND_MILLIDEGREES - state["head"][1], CARRIAGE_PITCH_BOUND_MILLIDEGREES - state["head"][1]))
            state["eyes"] = [eye_yaw, eye_pitch]
            self._last_target_polar = (float(math.hypot(point[0] - ex, point[1] - ey)), int(aim[0]))
        else:
            self._last_target_polar = None
            if sensed.wide_luminance_u8:
                state["head"] = list(head_step(self.head, tuple(sensed.wide_luminance_u8)))
            # Binaural acoustic orienting torque if sound is heard without an identified visual object:
            if heard_now is not None and len(heard_now) == 32 and sound_heard:
                el = sum(heard_now[:16])
                er = sum(heard_now[16:])
                if el + er > 0:
                    ild_ratio = (el - er) / (el + er)
                    if abs(ild_ratio) > 0.04:
                        step_mdeg = int(_clamp(round(ild_ratio * HEAD_STEP_MILLIDEGREES), -HEAD_STEP_MILLIDEGREES, HEAD_STEP_MILLIDEGREES))
                        state["head"][0] = int(_clamp(state["head"][0] + step_mdeg, -HEAD_YAW_BOUND_MILLIDEGREES, HEAD_YAW_BOUND_MILLIDEGREES))
            state["eyes"] = [0, 0]   # nothing to look at: the eyes rest straight in the head
        measures = self._measure(sensed, seen, body)
        self._see_figure(sensed, self.live_organism_tick)
        skin_now = float(measures["skin_contact"])
        # Her need for contact: another body's touch on her skin relieves it; an
        # awake beat without one raises it.
        contact_pressure = int(state.get("contact_pressure", 0))
        if skin_now > 0:
            contact_pressure = max(0, contact_pressure - CONTACT_RECOVERY_PER_BEAT)
        elif not state.get("asleep"):
            contact_pressure = min(CONTACT_PRESSURE_CEILING, contact_pressure + 1)
        state["contact_pressure"] = contact_pressure
        for name in STREAMS:
            window = state["streams"][name]
            window.append(round(measures[name], 6))
            del window[:-KERNEL_WINDOW]
        signature, gate_count = self._kernel()
        tokens = signature.split(" ")
        uncertain = any(len(t) >= 5 and t[4] == "+" for t in tokens)
        regimes = "".join(token[0] for token in tokens)
        key = choice_key(regimes)
        situation = coarse_key(regimes)
        tick = self.live_organism_tick
        novel = key not in state["familiarity"]

        feeding = state["feeding"] or self.reserve_micrograms < CAPACITY_MICROGRAMS * HUNGRY_BELOW
        if self.reserve_micrograms >= CAPACITY_MICROGRAMS * SATED_ABOVE:
            feeding = False
        held = None if body.held_object_id is None else _object(snapshot, body.held_object_id)
        offered_id = offered_within_reach(snapshot)
        offered = None if offered_id is None else _object(snapshot, offered_id)
        heard_now = sensed.heard_profile
        ambient = float(state.get("ambient_sound", 0.0))
        sound_now = 0.0
        hop_heard = False
        if heard_now is not None:
            energy = sum(heard_now) / len(heard_now)
            # Her ear's perception law is the floor alone (the ear streams' own); the
            # running ambient decides only what is worth answering (what pays). Measured
            # on her live body: with the ambient in the gate's hearing, a word two beats
            # after music was not heard at all, and music was chopped by its own level.
            hop_heard = energy >= HEARD_ENERGY_FLOOR
            if hop_heard and energy >= ambient * HEARD_ABOVE_AMBIENT:
                sound_now = _clamp(energy * 4, 0.0, 1.0)
        is_speech = is_external and ((sensed.sound_source_id is None) or (sensed.sound_source_id in ("person-body-1", "caregiver", "tutor", "speaker")))
        if hop_heard or sound_heard:
            state["current_sound_is_speech"] = is_speech
        speech_closing = state.get("current_sound_is_speech", is_speech)
        self._hear_events(sensed.heard_frames, hop_heard, tick, envelopes=sensed.heard_envelopes, is_speech=speech_closing)
        self._hear_own(sensed.own_frames, tick)
        self._sensorimotor_mesh.step_polarization(sensed.heard_frames)
        self._sync_sensorimotor_mesh()
        self._last_focal_luminance = sensed.focal_luminance_u8
        self._last_heard_envelopes = getattr(sensed, "heard_envelopes", ())
        self._last_skin_contact = sensed.skin_contact
        self._last_touch_temp = sensed.touch_surface_millikelvin
        self._last_heard_profile = sensed.heard_profile
        self._last_external_sound_present = getattr(sensed, "external_sound_present", False)
        admitted_moment_keys = self._form_moments(body, measures, tick)

        # Pre-choice sensory observation captured before any action evaluation
        current_sensory_key = _capture_sensory_key(snapshot, body, state, seen)

        # Finalize the prior actually executed trial with this observed successor.
        # Each event has its own record: equal reach categories never splice lives.
        pending_trans = state.pop("pending_transition", None)
        if pending_trans:
            action = pending_trans.get("applied_action")
            if action and action != "body" and "start_tick" in pending_trans:
                intake_ug = int(pending_trans.get("intake", 0))
                sal = float(pending_trans.get("salience", 0.0))
                outcome = pending_trans.get("outcome_key")
                moments = state.setdefault("moments", {})
                trial_key = f"motor:{pending_trans['start_tick']}"
                trial = {
                    "key": trial_key,
                    "start_tick": pending_trans["start_tick"], "end_tick": tick,
                    "pre": pending_trans["pre_key"], "post": current_sensory_key,
                    "action": action, "target": pending_trans["target_id"],
                    "observed_subject": pending_trans["observed_subject"],
                    "refusal": pending_trans.get("refusal"),
                    "intake": intake_ug,
                    "previous": None,
                }
                previous = pending_trans.get("previous")
                predecessor_entry = moments.get(previous) or state.get("meanings", {}).get(previous) or {}
                predecessor = predecessor_entry.get("motor_transition")
                if consecutive_motor_trials(predecessor, trial):
                    trial["previous"] = previous
                if trial_key not in moments:
                    admitted_moment_keys.add(trial_key)
                trial_krim = state.get("last_sparse_krimelack")
                moments[trial_key] = {
                    "count": 1, "tick": tick, "salience": sal,
                    "held": "none",
                    "figure": "none",
                    "room": state.get("room_now") or "unknown",
                    "source": "motor",
                    "context": [0, 0, 0],
                    "next": {},
                    "acts": {},
                    "fed": intake_ug,
                    "motor_transition": trial,
                    "krimelack": trial_krim,
                }
                if outcome in moments:
                    moments[outcome]["episode_tail"] = trial_key
                state["last_motor_trial"] = trial_key
            else:
                # Passive time is not a rehearsed act and cannot bridge an
                # unobserved interval into an experience sequence.
                state["last_motor_trial"] = None

        # Finalize real consequences before enforcing the shared waking bound.
        # Otherwise sensory admission can erase an outcome before its tail binds.
        moments = state["moments"]
        bounded = bound_waking_moments(moments, MOMENT_RECORD_CAPACITY, admitted_moment_keys)
        self._retention_refused = bool(admitted_moment_keys - bounded.keys())
        state["moments"] = bounded
        if state.get("last_motor_trial") not in bounded and state.get("last_motor_trial") not in state["meanings"]:
            state["last_motor_trial"] = None
        last_moment = state.get("last_moment")
        if last_moment is not None and last_moment[0] not in bounded:
            state["last_moment"] = None

        if sensed.self_profile is not None and sum(sensed.self_profile) > 0:
            pending = state.get("pending_act")
            if pending is not None and pending.get("act") == "say":
                pending["self_profile"] = list(sensed.self_profile)
                if sensed.own_envelopes:
                    pending["self_envelopes"] = [list(e) for e in sensed.own_envelopes]
                if sensed.own_frames:
                    pending["self_frames"] = [list(f) for f in sensed.own_frames]
            if state.get("pending_drive") is not None:
                p_drive = tuple(state["pending_drive"])
                s_name = next((name for name, d in SYLLABLE_DRIVES.items() if d == p_drive), None)
                if s_name is not None:
                    state.setdefault("syllable_profiles", {})[s_name] = list(sensed.self_profile)
        self._settle(key, novel, sound_now, skin_now, tick, warmth_likeness=float(getattr(self, "_warmth_likeness", 0.0)), pain=float(getattr(self, "_pain", 0.0)))

        def decision(act: str, reason: str, commands: tuple[Any, ...] = (), target: str | None = None, drive: tuple[int, int, int] | None = None) -> Decision:
            if not sound_heard:
                state["gaze_target"] = target if target is not None else body.held_object_id   # what she acts on (or what she holds) is what her head turns to next beat
            state["pending_transition"] = {
                "pre_key": current_sensory_key,
                "start_tick": tick,
                "observed_subject": target_id,
                "previous": state.get("last_motor_trial"),
                "action": act,
                "target_id": target,
                "applied_action": None,
                "refusal": None,
                "intake": 0,
                "relief": None,
                "salience": 0.0,
            }
            return Decision(act, reason, commands, target, drive, signature, novel, gate_count, seen)

        if feeding and not state.get("asleep"):
            active_oral_target = held.object_id if held is not None else (offered.object_id if offered is not None else None)
            unsuccessful_target = state.get("unsuccessful_bite_held_id")
            if unsuccessful_target is not None and (active_oral_target is None or active_oral_target != unsuccessful_target):
                state["unsuccessful_bite_held_id"] = None

            for item in (held, offered):
                if item is not None:
                    if item.material is None or body.receptor_geometry is None:
                        continue   # cannot bite without material or oral receptors
                    if item.material is not None and int(item.material.surface_temperature_millikelvin) >= NOCICEPTION_MILLIKELVIN:
                        continue   # too hot to bite: the jaw waits for it to cool (the mouth's reflex)
                    c_item = conserved.get(item.object_id, {})
                    is_depleted = bool(c_item.get("currently_depleted") or (item.material is not None and getattr(item.material, "digestible_mass_micrograms", 0) <= 2_000))
                    if is_depleted or (c_item.get("non_nutritive") is True and not is_genuine_food_object(item.object_id)) or item.object_id == state.get("unsuccessful_bite_held_id"):
                        continue   # suppressed: known non-nutritive, depleted, or unsuccessful bite
                    return decision("bite", "held item at her mouth while feeding (the jaw's reflex)", (OralContactCommand(item.object_id, BEAT_MICROSECONDS),), item.object_id)

            # Barrier & Depletion Inhibition: When holding an item whose bite failed, is non-nutritive, or depleted, release it immediately
            if held is not None:
                c_held = conserved.get(held.object_id, {})
                held_depleted = bool(c_held.get("currently_depleted") or (held.material is not None and getattr(held.material, "digestible_mass_micrograms", 0) <= 2_000))
                if (
                    held.material is None
                    or body.receptor_geometry is None
                    or held_depleted
                    or (c_held.get("non_nutritive") is True and not is_genuine_food_object(held.object_id))
                    or held.object_id == state.get("unsuccessful_bite_held_id")
                    or (held.object_id in tested_non_nutritive and not is_genuine_food_object(held.object_id))
                    or held.object_id == "playpen"
                ):
                    if held_depleted:
                        c_entry = conserved.setdefault(held.object_id, {
                            "object_id": held.object_id,
                            "position": tuple(state.get("body_pos") or (0, 0, 0)),
                            "radius_mm": int(held.radius_mm),
                            "room_id": state.get("room_now"),
                            "last_seen_tick": tick,
                            "confidence": 1.0,
                        })
                        c_entry["currently_depleted"] = True
                        c_entry["is_food"] = False
                    if not is_genuine_food_object(held.object_id):
                        tested_set = set(state.get("tested_non_nutritive") or ())
                        tested_set.add(held.object_id)
                        state["tested_non_nutritive"] = sorted(tested_set)
                        c_entry = conserved.setdefault(held.object_id, {
                            "object_id": held.object_id,
                            "position": tuple(state.get("body_pos") or (0, 0, 0)),
                            "radius_mm": int(held.radius_mm),
                            "room_id": state.get("room_now"),
                            "last_seen_tick": tick,
                            "confidence": 1.0,
                        })
                        c_entry["non_nutritive"] = True
                        c_entry["is_food"] = False
                    return decision("release", f"structure {key[:6]}: barrier inhibition: release non-nutritive/blocked held target {held.object_id}", (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id)
        



        pressure = int(state.get("sleep_pressure", 0))
        if state.get("asleep"):
            if pressure <= 0:
                state["asleep"], state["sleep_pressure"] = False, 0
                # Waking changes physiology, not knowledge of unseen food.
            else:
                state["sleep_pressure"] = pressure - SLEEP_RECOVERY_PER_BEAT
                dreamt = self._dream(tick)
                return decision("sleep", "asleep" + ("; dreaming " + dreamt if dreamt else "") + f"; pressure {100 * pressure // SLEEP_PRESSURE_CEILING}%")
        elif pressure >= SLEEP_PRESSURE_CEILING:
            bed = _object(snapshot, BED_ID)
            at_bed = bed is not None and bed.position is not None and _distance_mm(body.pose.position, bed.position) <= bed.radius_mm
            exhausted = pressure >= SLEEP_PRESSURE_CEILING * (1 + EXHAUSTION_MARGIN)
            if at_bed or exhausted:
                state["asleep"] = True
                state["nights"] = int(state.get("nights", 0)) + 1
                if at_bed and state.get("last_chosen"):
                    last = state["last_chosen"]
                    sleep_ratio = float(last.get("sleep_ratio", 1.0))
                    recovery_ratio = float(pressure) / SLEEP_PRESSURE_CEILING
                    self._credit(str(last["key"]), str(last["act"]), round(sleep_ratio * recovery_ratio, 6), tick, str(last.get("regimes", "")))
                    state["last_chosen"] = None
                state["gaze_target"] = None
                state["gaze"] = None
                state["room_dwell_beats"] = 0
                return decision("sleep", "falling asleep on her bed; pressure at its ceiling" if at_bed else "exhausted; asleep where she dropped")

        # Voice: the syllable comes from her speech record (situation, prior syllable),
        # valued by what followed each syllable exactly as her acts are.
        last_spoke = int(state.get("last_spoke_tick", -999))
        prior_syl = state.get("prior_syllable") if (tick - last_spoke) <= PHRASE_WINDOW_BEATS else None
        say_drive, say_name, say_context, say_reason = self._choose_syllable(situation, prior_syl, uncertain=uncertain)

        if float(getattr(self, "_pain", 0.0)) > 0 and held is not None and held.material is not None \
                and int(held.material.surface_temperature_millikelvin) >= NOCICEPTION_MILLIKELVIN:
            state["pending_act"] = None
            return decision("release", "it burns; let go (the hand's reflex)", (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id)

        uncertain = any(len(t) >= 5 and t[4] == "+" for t in tokens)
        sleepy = int(state.get("sleep_pressure", 0)) >= SLEEP_PRESSURE_CEILING // 2
        state["body_pos"] = (int(body.pose.position.x), int(body.pose.position.y), int(body.pose.position.z))
        state["body_heading"] = int(body.pose.heading_millidegrees)
        options = candidates(snapshot, body, held, offered, seen, tick, say_drive=say_drive, say_detail=say_reason, feeding=feeding, sleepy=sleepy, conserved_objects=conserved, last_crossed_portal=state.get("last_crossed_portal"), sound_heard=sound_heard, consequence_food_ids=consequence_foods, tested_non_nutritive_ids=tested_non_nutritive, modular_sub=self._modular_substrate)

        # Cognitive Asset 1: Learned Closed-Loop Continuation Selector
        # When an internal demand is active, searches the empirical transition graph for supported continuation
        chosen_option = None
        act = None
        why = ""
        meanings = state.get("meanings", {})
        if feeding and meanings:
            body_pos = state["body_pos"]
            target_positions = {obj_id: c_data["position"] for obj_id, c_data in conserved.items() if "position" in c_data}
            target_figures = {obj_id: c_data.get("figure_key") for obj_id, c_data in conserved.items() if "figure_key" in c_data}
            g_tgt = state.get("gaze_target")
            if g_tgt is not None and (_object(snapshot, g_tgt) is None or g_tgt not in {s.object_id for s in seen}):
                g_tgt = None
            cur_target = body.held_object_id or g_tgt or state.get("joint_attention_target") or (seen[0].object_id if seen else None)
            supported_cand = find_supported_continuation(
                current_sensory_key,
                "feeding",
                meanings,
                options,
                current_target_id=cur_target,
                current_figure=state.get("sight_figure"),
                current_held="held" if body.held_object_id else "none",
                body_position=body_pos,
                target_positions=target_positions,
                target_figures=target_figures,
            )
            if supported_cand is not None:
                chosen_option = supported_cand
                act = chosen_option[0]
                why = f"learned continuation toward {chosen_option[3] or act} ({chosen_option[1]})"
                if chosen_option[3]:
                    state["planned_target_id"] = chosen_option[3]

        # Conversational Turn-Taking Invariant (250ms quiet-gap release)
        sp_target = state.get("heard_speech_target")
        if (
            chosen_option is None
            and sp_target is not None
            and not sp_target.get("consumed")
            and sp_target.get("tick") in (tick, int(state.get("last_sound_heard_tick", -999)))
            and any(opt[0] == "say" for opt in options)
        ):
            say_opts = [opt for opt in options if opt[0] == "say"]
            if say_opts:
                sp_target["consumed"] = True
                chosen_option = say_opts[0]
                act = "say"
                why = f"structure {key[:6]}: conversational turn release after 250ms quiet gap"

        if chosen_option is None:
            candidate_acts = list(dict.fromkeys(option[0] for option in options))
            act, why = self._choose(key, situation, candidate_acts, uncertain=uncertain, candidate_options=options, snapshot=snapshot)
            matching = [option for option in options if option[0] == act]
            target_totals = state.setdefault("target_totals", {})
            planned_target = state.get("planned_target_id")
            if act == "toward_door" and len(matching) > 1:
                cur_r = state.get("room_now")
                prior_r = state.get("prior_room")
                reg_visits = state.get("region_visits", {})
                reg_last = state.get("region_last_tick", {})
                food_rooms = {}
                if feeding:
                    for obj_id, c in (conserved or {}).items():
                        if is_genuine_food_object(obj_id) and not c.get("currently_depleted"):
                            room = c.get("room_id")
                            if room:
                                food_rooms[room] = food_rooms.get(room, 0) + int(c.get("historical_intake_micrograms", 100_000))

                def _portal_novelty(opt: tuple) -> tuple:
                    portal_id = opt[3]
                    portal = next((p for p in snapshot.portals if p.portal_id == portal_id), None)
                    if portal is None:
                        return (0, False, False, False, 0, 0)
                    dest_r = next((r for r in portal.region_ids if r != cur_r), None)
                    visits = int(reg_visits.get(dest_r, 0))
                    last_t = int(reg_last.get(dest_r, 0))
                    elapsed = tick - last_t if last_t > 0 else 1_000_000
                    not_prior = (dest_r != prior_r) if prior_r else True
                    dest_mass = food_rooms.get(dest_r, 0) if feeding else 0
                    if feeding and food_rooms:
                        routes = [_portal_route(snapshot, dest_r, fr) for fr in food_rooms]
                        valid_lens = [len(r) for r in routes if r is not None]
                        min_food_dist = min(valid_lens) if valid_lens else 999
                        return (dest_mass, -min_food_dist, not_prior, visits == 0, elapsed, -visits)
                    return (0, 0, not_prior, visits == 0, elapsed, -visits)
                matching_sorted = sorted(matching, key=_portal_novelty, reverse=True)
                chosen_option = matching_sorted[0]
            elif planned_target and act in ("toward_thing", "toward_food", "grasp"):
                matching_targeted = [o for o in matching if o[3] == planned_target]
                chosen_option = matching_targeted[0] if matching_targeted else matching[0]
            elif act in ("toward_thing", "toward_food") and len(matching) > 1:
                handleable_options = [o for o in matching if o[3] and handleable(_object(snapshot, o[3]))]
                chosen_option = handleable_options[0] if handleable_options else matching[0]
                if chosen_option[3] and handleable(_object(snapshot, chosen_option[3])):
                    state["planned_target_id"] = chosen_option[3]
            elif False and act == "toward_door" and len(matching) > 1 and tick > 100:
                cur_r = state.get("room_now")
                prior_r = state.get("prior_room")
                reg_visits = state.get("region_visits", {})
                reg_last = state.get("region_last_tick", {})
                def _portal_novelty(opt: tuple) -> tuple:
                    portal_id = opt[3]
                    portal = next((p for p in snapshot.portals if p.portal_id == portal_id), None)
                    if portal is None:
                        return (False, False, 0, 0)
                    dest_r = next((r for r in portal.region_ids if r != cur_r), None)
                    visits = int(reg_visits.get(dest_r, 0))
                    last_t = int(reg_last.get(dest_r, 0))
                    elapsed = tick - last_t if last_t > 0 else 1_000_000
                    not_prior = (dest_r != prior_r) if prior_r else True
                    return (not_prior, visits == 0, elapsed, -visits)
                matching_sorted = sorted(matching, key=_portal_novelty, reverse=True)
                chosen_option = matching_sorted[0]
            else:
                chosen_option = matching[0]
            if chosen_option[3] is not None:
                target_totals[chosen_option[3]] = int(target_totals.get(chosen_option[3], 0)) + 1

        _name, detail, commands, target, drive = chosen_option

        if act in ("turn_left", "turn_right"):
            state["consecutive_turns"] = int(state.get("consecutive_turns", 0)) + 1
        else:
            state["consecutive_turns"] = 0

        deficit = round(float(self.deficit), 6)
        sleep_ratio = round(float(state.get("sleep_pressure", 0)) / SLEEP_PRESSURE_CEILING, 6)
        contact_ratio = round(float(state.get("contact_pressure", 0)) / CONTACT_PRESSURE_CEILING, 6)
        state["pending_act"] = {"key": key, "regimes": regimes, "act": act, "deficit": deficit, "sleep_ratio": sleep_ratio, "contact_ratio": contact_ratio, "intake": 0, "refused": False}
        if act == "say":
            drive = say_drive
            state["pending_act"]["syllable"], state["pending_act"]["context"] = say_name, say_context   # valued by what follows, under its context
            state["pending_act"]["drive"] = list(say_drive)
            speech_target = state.get("heard_speech_target")
            if speech_target:
                speech_target["consumed"] = True
        else:
            # Parallel Vocal Efferent Coupling:
            # Acoustic emission is an independent efferent channel from motor locomotion.
            # When under homeostatic distress (hunger strain) or acoustic acknowledgement,
            # attach vocal drive to the motor decision WITHOUT halting locomotion.
            hunger_dsf = self._last_dsf_states.get("hunger") if hasattr(self, "_last_dsf_states") else None
            p_k = hunger_dsf["P_k"] if hunger_dsf else (0.8 if deficit >= 0.6 else 0.0)
            b_k = hunger_dsf["B_k"] if hunger_dsf else 0.5
            s_uf = hunger_dsf["S_UF"] if hunger_dsf else (b_k - p_k)
            strained = (deficit >= 0.6 and (p_k > b_k or s_uf <= 0))
            since_last_exhaust = self.live_organism_tick - int(self._state.get("homeostatic_exhaust_tick", -999))

            since_last_vocal = tick - int(state.get("last_spoke_tick", -999))
            should_vocalize = False
            if sound_heard:
                # Acoustic pressure clamping: no vocal emission during active external acoustic pressure
                should_vocalize = False
            elif strained and since_last_exhaust >= 15:
                should_vocalize = True
                self._state["homeostatic_exhaust_tick"] = self.live_organism_tick
                pass  # V4: downstream DSF coordinates are never rewritten
            elif not state.get("asleep") and since_last_vocal >= 8:
                # Spontaneous phonemic exploration during wakefulness
                should_vocalize = True

            if should_vocalize and drive is None and say_drive is not None:
                drive = say_drive
                state["pending_act"]["syllable"], state["pending_act"]["context"] = say_name, say_context
                state["pending_act"]["drive"] = list(say_drive)
                state["last_spoke_tick"] = tick

        # Historical pending_chain/last_demand_chain checkpoint fields are inert.
        # Authored syllable queues are not learned temporal composition.

        state["last_chosen"] = {"key": key, "regimes": regimes, "act": act, "deficit": deficit, "sleep_ratio": sleep_ratio}
        return decision(act, why + (("; " + detail) if detail else ""), commands, target, drive)

    # ----- the eye's Level 1: the figure under her gaze --------------------------------

    def _see_figure(self, sensed: Sensed, tick: int) -> None:
        """The figure under her gaze on her world eye's field (the law's measured domain;
        a camera frame gives none until a law is measured stable on real frames). A
        figure is met when it comes under her gaze (its key differs from the last beat's);
        the day's store keeps the most recently met."""

        state = self._state
        figure = None
        if sensed.luminance_source == "world" and state.get("gaze") is not None:
            figure = figure_of_disc(tuple(sensed.focal_luminance_u8), (float(state["gaze"][0]), float(state["gaze"][1])), float(state.get("gaze_radius", 0.0)))
        self._figure = figure
        key = None if figure is None else figure.key
        if key is not None and key != state.get("sight_figure"):
            figures = state.setdefault("figures", {})
            entry = figures.get(key)
            figures[key] = [1, tick] if entry is None else [int(entry[0]) + 1, tick]
            while len(figures) > FIGURE_RECORD_CAPACITY:
                del figures[min(figures, key=lambda k: (int(figures[k][0]), int(figures[k][1]), k))]   # the least met, then the least recently met, leaves
        state["sight_figure"] = key

    def _hear_own(self, frames: tuple[tuple[float, ...], ...], tick: int) -> None:
        """Her own voice heard back through the same gate, in a gate of its own: her
        syllable closes as an event with a key, kept in her store of her own sounds."""

        state = self._state
        hop = tuple(frames) if frames else (SILENT_FRAME,) * FRAMES_PER_HOP
        heard = bool(frames) and any(float(frame[0]) >= HEARD_ENERGY_FLOOR for frame in hop)
        open_event, closed, _runs = gate_step(state.get("voice_event"), hop, heard, tick * FRAMES_PER_HOP)
        state["voice_event"] = open_event
        own = state.setdefault("own_events", {})
        self._own_closed = []
        for event in closed:
            entry = own.get(event.key)
            own[event.key] = [1, tick, event.beats] if entry is None else [int(entry[0]) + 1, tick, int(entry[2])]
            while len(own) > OWN_EVENT_RECORD_CAPACITY:
                del own[min(own, key=lambda k: (int(own[k][0]), int(own[k][1]), k))]   # the least made, then the least recently made, leaves
            state["own_event"] = [event.key, tick, event.end_frame]
            self._own_closed.append(event.key)

    # ----- Level 2 and 3: the moment, and what followed it ------------------------------

    def _form_moments(self, body: Any, measures: dict[str, float], tick: int) -> set[str]:
        """On a beat a sound event closed, or on a silent beat with somatic salience or visual figure:
        the moment's key from the physical invariants (the event, the held thing's texture and warmth
        in eighths, the figure under her gaze), its context (hunger, taste, the caregiver's touch, in eighths),
        counted in the day's store; and, when the last moment is within the window, this one counted
        as what followed it."""

        state = self._state
        created: set[str] = set()
        if state.get("asleep"):
            return created
        self._moment_formed = None
        said = state.get("last_said")
        closed = list(getattr(self, "_ear_closed", [])) + [f"own:{said}" for _key in getattr(self, "_own_closed", []) if said]

        eighth = lambda value: int(_clamp(round(float(value) * 8), 0, 8))
        held = "none" if body.held_object_id is None else f"{eighth(measures['touch_texture'])}/{eighth(measures['touch_warmth'])}"
        figure = "held" if held != "none" else (state.get("sight_figure") or "none")
        context = [eighth(measures["hunger"]), eighth(measures["taste_residue"]), eighth(measures["skin_contact"])]
        pain = float(getattr(self, "_pain", 0.0))
        salience = compute_somatic_salience(
            reserve_delta_ug=0,
            shock_magnitude=pain,
            pain_signal=(pain > 0.0),
        )

        moments = state.setdefault("moments", {})
        room_now = state.get("room_now") or "unknown"

        # Continuous Multi-Modal Substrate Presentation & Krimelack Encoding
        focal_u8 = getattr(self, "_last_focal_luminance", ())
        vis_trits = self._ternary_substrate.encode_visual_field(np.asarray(focal_u8, dtype=np.float64)) if focal_u8 else [0] * 256
        target = state.get("heard_speech_target")
        envs = (target.get("envelopes") or ()) if target else getattr(self, "_last_heard_envelopes", ())
        aud_trits = self._ternary_substrate.encode_cochlear_field_2d(envs) if envs else [0] * 256
        c_load = float(getattr(self, "_last_skin_contact", measures.get("skin_contact", 0.0)))
        t_surf = getattr(self, "_last_touch_temp", None)
        t_delta = (float(t_surf - 310_000) / 10_000.0) if t_surf is not None else float(measures.get("touch_warmth", 0.0) - 0.5)
        som_trits = self._ternary_substrate.encode_somatic_field(c_load, t_delta)
        eff_trits = [0] * 256
        hunger_dsf = self._last_dsf_states.get("hunger") if hasattr(self, "_last_dsf_states") else None
        if hunger_dsf:
            dsf_vec = (
                float(hunger_dsf["D_k"]),
                float(hunger_dsf["M_k"]),
                float(hunger_dsf["R_rev_k"]),
                float(hunger_dsf["U_star_k"]),
                float(hunger_dsf["C_k"]),
                float(hunger_dsf["P_k"]),
                float(hunger_dsf["B_k"]),
                float(hunger_dsf["S_UF"]),
            )
        else:
            dsf_vec = None
        o_idx, v_idx, p_idx = None, None, None
        if said:
            for oi, o_name in enumerate(ONSETS):
                if said.startswith(o_name):
                    o_idx = oi
                    rem = said[len(o_name):]
                    for vi, v_tup in enumerate(VOWELS):
                        if rem.startswith(v_tup[0]):
                            v_idx = vi
                            break
                    break
        eff_trits = self._ternary_substrate.encode_dsf_and_efferents(
            dsf_vector=dsf_vec, onset_idx=o_idx, vowel_idx=v_idx, pitch_idx=p_idx
        )
        mm_vec = self._ternary_substrate.assemble_multimodal_vector(vis_trits, aud_trits, som_trits, eff_trits)
        sparse_k = [[idx, val] for idx, val in enumerate(mm_vec) if val != 0]
        has_event = bool(said or target or salience > 0.0 or getattr(self, "_pain", 0.0) > 0.0 or state.get("taste_residue", 0.0) > 0.0 or c_load > 0.1)
        if sparse_k and has_event:
            self._ternary_substrate.present_experience(mm_vec)
            self._sync_ternary_substrate()
            state["last_sparse_krimelack"] = sparse_k
            state["last_sparse_krimelack"] = sparse_k

        # Step Modular Neuromorphic Substrate (Full Continuous DSF Delivery)
        if dsf_vec is not None and len(dsf_vec) >= 8:
            self._modular_substrate.consume_continuous_joint_field(dsf_vec[:7], dsf_vec[7])
        else:
            self._modular_substrate.clear_continuous_joint_field()
        polar = getattr(self, "_last_target_polar", None)
        obs_r, obs_th = (polar[0], polar[1]) if polar is not None else (None, None)
        sens_64 = self._modular_substrate.encode_sensory_stream(
            optical_intensities=np.asarray(focal_u8, dtype=np.float64) if focal_u8 else None,
            cochlear_channels=getattr(self, "_last_heard_envelopes", ()) or None,
            palmar_contact=c_load,
            thermal_gradient_mk=float(t_surf - 310_000) if t_surf is not None else float(measures.get("touch_warmth", 0.0) - 0.5) * 10_000.0,
            dsf_vector=dsf_vec,
        )
        som_32 = self._modular_substrate.encode_somatic_apical(
            sleep_pressure=float(state.get("sleep_pressure", 0)) / float(SLEEP_PRESSURE_CEILING),
            metabolic_deficit=float(measures.get("hunger", 0.0)),
            arousal_surplus=float(salience),
        )
        # Multi-source continuous fields for native source bank (V5)
        dsf_states = getattr(self, "_last_dsf_states", {}) or {}
        source_fields = tuple(
            (idx, (
                float(dsf_states[s]["D_k"]),
                float(dsf_states[s]["M_k"]),
                float(dsf_states[s]["R_rev_k"]),
                float(dsf_states[s]["U_star_k"]),
                float(dsf_states[s]["C_k"]),
                float(dsf_states[s]["P_k"]),
                float(dsf_states[s]["B_k"]),
                float(dsf_states[s]["S_UF"]),
            ))
            for idx, s in enumerate(STREAMS)
            if s in dsf_states
        ) if dsf_states else None

        last_ref = state.get("last_refusal")
        kinematic_refusal = bool(last_ref is not None)
        barrier_stress = float(getattr(self, "_last_barrier_stress", 0.0))

        last_motor_res = state.get("last_body_motor_result")
        if last_motor_res is not None:
            eff_sample = last_motor_res.get("efferent_sample") or (0, 0, 0)
            motor_reafference = (int(eff_sample[0]), int(eff_sample[1]), int(eff_sample[2]))
        else:
            motor_reafference = None

        oral_contact = bool(body.held_object_id is not None or state.get("taste_residue", 0.0) > 0.0)
        reserve_frac = float(self.reserve_micrograms) / float(CAPACITY_MICROGRAMS)

        yield_synapses, strain_energy = self._modular_substrate.step(
            sens_64,
            som_32,
            observed_r_mm=obs_r,
            observed_theta_mdeg=obs_th,
            barrier_stress=barrier_stress,
            acoustic_formant=0.0,
            articulatory_reafference=None,
            motor_reafference=motor_reafference,
            own_auditory=None,
            reserve_fraction=reserve_frac,
            source_fields=source_fields,
            kinematic_refusal=kinematic_refusal,
            somatic_coordinates=None,
            oral_contact=oral_contact,
        )
        self._physically_transitioned_neuron_count = int(yield_synapses)
        self._sync_modular_substrate()

        if not closed:
            last_moment_id = state.get("last_moment", [None])[0] if state.get("last_moment") else None
            last_entry = moments.get(last_moment_id) if last_moment_id else None
            last_fig = last_entry.get("figure") if last_entry else None
            last_held = last_entry.get("held") if last_entry else "none"
            last_room = last_entry.get("room") if last_entry else None
            is_phase_shift = (
                (figure != "none" and figure != last_fig) or
                (held != "none" and held != last_held) or
                (room_now != last_room and last_room is not None)
            )
            if salience > 0.0 or is_phase_shift:
                closed = [f"visual:{figure}"]
            else:
                return created
        for event in closed:
            key = hashlib.sha256(f"{event}|{held}|{figure}".encode("ascii")).hexdigest()[:16]
            entry = moments.get(key)
            if entry is None:
                created.add(key)
                moments[key] = {
                    "count": 1,
                    "tick": tick,
                    "held": held,
                    "figure": figure,
                    "room": room_now,
                    "context": context,
                    "next": {},
                    "acts": {},
                    "fed": 0,
                    "source": "own" if event.startswith("own:") else ("visual" if event.startswith("visual:") else "heard"),
                    "salience": round(salience, 4),
                    "krimelack": sparse_k if sparse_k else None,
                }
            else:
                entry["count"] = int(entry["count"]) + 1
                entry["tick"] = tick
                entry["context"] = context
                entry["figure"] = figure
                entry["room"] = room_now
                entry["salience"] = max(float(entry.get("salience", 0.0)), round(salience, 4))
                if sparse_k:
                    entry["krimelack"] = sparse_k
                if "acts" not in entry:
                    entry["acts"] = {}
            last = state.get("last_moment")
            if last is not None and last[0] != key and tick - int(last[1]) <= FOLLOW_WINDOW_BEATS and last[0] in moments:
                following = moments[last[0]].setdefault("next", {})
                following[key] = int(following.get(key, 0)) + 1
                while len(following) > FOLLOW_CAPACITY:
                    del following[min(following, key=lambda k: (int(following[k]), k))]   # the least counted leaves
            state["last_moment"] = [key, tick]
            if not event.startswith("own:") or self._moment_formed is None:
                self._moment_formed = key

        return created

    # ----- Level 1: the acoustic gate over her beat ------------------------------------

    def _hear_events(self, frames: tuple[tuple[float, ...], ...], heard: bool, tick: int, envelopes: Sequence[Sequence[float]] | None = None, is_speech: bool = True) -> None:
        """The boundary law over this beat's frames at her ear; a beat without a room
        sound is a hop of silence to it (an open event closes within it). Each event
        closed is kept in her day's store by the key of its own structure; the gaps
        of quiet go to her record of quiet."""

        state = self._state
        hop = tuple(frames) if frames else (SILENT_FRAME,) * FRAMES_PER_HOP
        open_event, closed, quiet_runs = gate_step(state.get("ear_event"), hop, heard, tick * FRAMES_PER_HOP, envelopes=envelopes)
        state["ear_event"] = open_event
        quiet = state.setdefault("ear_quiet", _empty_ear_quiet())
        for run in quiet_runs:
            if 1 <= run <= QUIET_RUN_BINS:
                quiet["inside"][run - 1] += 1
        events = state.setdefault("events", {})
        self._ear_closed = []
        for event in closed:
            previous = state.get("sound_event")
            if previous is not None:
                gap = event.start_frame - int(previous[2]) - 1
                quiet["between"][sum(1 for bound in GAP_BINS_FRAMES if gap > bound)] += 1
            entry = events.get(event.key)
            events[event.key] = [1, tick, event.beats] if entry is None else [int(entry[0]) + 1, tick, int(entry[2])]
            while len(events) > EVENT_RECORD_CAPACITY:
                del events[min(events, key=lambda k: (int(events[k][0]), int(events[k][1]), k))]   # the least met, then the least recently met, leaves
            state["sound_event"] = [event.key, tick, event.end_frame]
            self._ear_closed.append(event.key)
            ev_prof = getattr(event, "profile", None)
            ev_envs = getattr(event, "envelopes", ())
            if is_speech:
                state["heard_speech_target"] = {
                    "tick": tick,
                    "key": event.key,
                    "profile": list(round(float(p), 4) for p in ev_prof) if ev_prof is not None else None,
                    "envelopes": [[round(float(x), 3) for x in e[:32]] for e in ev_envs] if ev_envs else [],
                    "bands": ear_bands(ev_prof),
                }
            state.pop("current_sound_is_speech", None)

    # ----- her record of acts -----------------------------------------------------------

    def _credit(self, key: str, act: str, value: float, tick: int, regimes: str = "", successor_key: str | None = None) -> None:
        record = self._state.setdefault("acts", {})
        entry = record.setdefault(key, {"acts": {}, "tick": tick, "regimes": regimes, "visits": 0, "successors": {}})
        entry["visits"] = int(entry.get("visits", 0)) + 1
        entry["tick"] = tick
        if regimes and not entry.get("regimes"):
            entry["regimes"] = regimes
        tried = entry["acts"].setdefault(act, [0, 0.0])
        tried[0] = int(tried[0]) + 1
        totals = self._state.setdefault("act_totals", {})
        totals[act] = int(totals.get(act, 0)) + 1
        tried[1] = round(float(tried[1]) + value, 6)
        if successor_key:
            successors = entry.setdefault("successors", {})
            act_succ = successors.setdefault(act, {})
            act_succ[successor_key] = int(act_succ.get(successor_key, 0)) + 1
        while len(record) > ACT_RECORD_CAPACITY:
            # The day's record keeps the structures she met most recently; the
            # night selects by recurrence. (Evicting the least visited kept out
            # every newcomer once the old entries all had two visits.)
            del record[min(record, key=lambda k: (int(record[k]["tick"]), k))]

    def _settle(self, key_now: str, novel_now: bool, sound_now: float, skin_now: float, tick: int, *, warmth_likeness: float = 1.0, pain: float = 0.0) -> None:
        """Value what followed her last act, purely by measured bodily need drops
        weighted by her measured need at the moment she chose (zero constants)."""

        pending = self._state.get("pending_act")
        self._state["pending_act"] = None
        if not pending:
            return
        deficit = float(pending["deficit"])
        sleep_ratio = float(pending.get("sleep_ratio", 0.0))
        intake = int(pending.get("intake", 0))
        refused = bool(pending.get("refused"))
        act = str(pending["act"])

        # 1. Intake by her deficit:
        intake_value = deficit * (1.0 if intake > 0 else 0.0)
        # 2. New structure by how fed and rested she was:
        new_structure_value = (1.0 - deficit) * (1.0 - sleep_ratio) * (1.0 if novel_now else 0.0)
        # 3. Sound heard standing out above ambient:
        sound_value = (1.0 - sleep_ratio) * float(sound_now)
        # 4. Metabolic cost: what the act actually burned (the commit's own
        # number), as a fraction of her capacity; a refused act burned what it
        # burned and moved nothing, no doubling by hand.
        burn_cost = int(pending.get("burn", 0)) / CAPACITY_MICROGRAMS

        # 5. Another body's touch on her skin: contact comfort pays in its own right by
        # how much of her skin it reached, and her deprivation at the moment she chose
        # makes the same touch pay more (both measured; nothing declared here).
        # Contact comfort is tuned to warmth like her own (a caress at skin temperature
        # pays fully, a contact 25 K away nothing); her deprivation is relieved by any touch.
        contact_value = float(skin_now) * float(warmth_likeness) + float(pending.get("contact_ratio", 0.0)) * (1.0 if skin_now > 0 else 0.0)
        # 6. Pain: what her skin met above nature's threshold costs by the excess.
        pain_cost = float(pain)

        value = intake_value + new_structure_value + sound_value + contact_value - burn_cost - pain_cost
        self._credit(str(pending["key"]), act, round(value, 6), tick, str(pending.get("regimes", "")), successor_key=key_now)
        if act == "say" and pending.get("syllable"):
            # Update physical sensorimotor mesh contacts
            p_drive = pending.get("drive")
            self_envs = pending.get("self_envelopes")
            if p_drive and self_envs:
                self_frames_list = [
                    (
                        round(sum(env[:16]) / 16.0, GRAIN),
                        *(
                            round(sum(env[:16][c] for c in band) / max(1e-9, sum(env[:16])), GRAIN)
                            for band in EAR_BAND_CHANNELS
                        )
                    )
                    for env in self_envs
                ]
                yielded = self._sensorimotor_mesh.plastic_settle(tuple(p_drive), self_frames_list)
                self._sync_sensorimotor_mesh()

                # Ground vocal-auditory reafference in native 1,024-node ternary matrix
                aud_trits = self._ternary_substrate.encode_cochlear_field_2d(self_envs)
                o_idx = p_drive[1] if len(p_drive) > 1 else None
                v_idx = p_drive[2] if len(p_drive) > 2 else None
                eff_trits = self._ternary_substrate.encode_dsf_and_efferents(onset_idx=o_idx, vowel_idx=v_idx)
                reaff_vec = self._ternary_substrate.assemble_multimodal_vector([0] * 256, aud_trits, [0] * 256, eff_trits)
                self._ternary_substrate.present_experience(reaff_vec)
                self._sync_ternary_substrate()

                # Step 4-Column 3D Modular Substrate on vocal reafference
                sens_reaff = self._modular_substrate.encode_sensory_stream(
                    cochlear_channels=self_envs,
                )
                som_reaff = self._modular_substrate.encode_somatic_apical()
                self._modular_substrate.step(sens_reaff, som_reaff)
                self._sync_modular_substrate()

            # The syllable she said is valued by the same measured worth, under its context.
            entry = self._state.setdefault("speech", {}).setdefault(str(pending["context"]), {"syllables": {}, "tick": tick})
            tried = entry["syllables"].setdefault(str(pending["syllable"]), [0, 0.0])
            tried[1] = round(float(tried[1]) + value, 6)

            # Cognitive Asset 3: Auditory-Motor Reafference & Spectral Babbling Resonance
            target = self._state.get("heard_speech_target")
            self_prof = pending.get("self_profile")
            if target and self_prof and target.get("profile"):
                target_tick = int(target.get("tick", 0))
                if 0 <= (tick - target_tick) <= 6:
                    rho = spectral_cosine_similarity(self_prof, target["profile"])
                    resonance_history = entry.setdefault("resonance", {})
                    if rho > float(resonance_history.get(str(pending["syllable"]), 0.0)):
                        resonance_history[str(pending["syllable"])] = round(rho, 4)
                    if rho >= 0.65:
                        resonance_credit = round(rho * 1.5, 4)
                        tried[1] = round(float(tried[1]) + resonance_credit, 6)

    def _dream(self, tick: int) -> str | None:
        """One sleeping beat of consolidation: the most recurrent structure of
        the day's record moves into her consolidated memory under its situation key;
        None when the day's record is empty."""

        state = self._state
        self._dream_moment(tick)

        # Offline Nocturnal Consolidation: Retained structure preserved without arbitrary boosts (V7, V17)
        # Global downscaling/blanket pruning retired; plasticity governed strictly by local yield dynamics.

        record = state.setdefault("acts", {})
        if not record:
            return None
        key = max(record, key=lambda k: (int(record[k].get("visits", 1)), int(record[k]["tick"]), k))
        entry = record.pop(key)
        regimes = str(entry.get("regimes") or "")
        if not regimes:
            return None
        situation = coarse_key(regimes)
        learned = state.setdefault("learned", {})
        target = learned.setdefault(situation, {"acts": {}, "tick": tick})
        for act, (tries, total) in entry["acts"].items():
            kept = target["acts"].setdefault(act, [0, 0.0])
            kept[0] = int(kept[0]) + int(tries)
            kept[1] = round(float(kept[1]) + float(total), 6)
        target["tick"] = tick
        while len(learned) > CONSOLIDATED_CAPACITY:
            del learned[min(learned, key=lambda k: (int(learned[k]["tick"]), k))]
        return key[:6] + " into situation " + situation

    def _dream_moment(self, tick: int) -> None:
        """Retain a qualifying outcome with its actual experienced predecessors.

        Counts and salience are not increased by retention or by sleep.
        A single bounded traversal replaces disconnected per-node forgetting.
        """
        state = self._state
        moments = state.get("moments") or {}
        if not moments:
            return
        key = max(moments, key=lambda k: (
            qualifies_for_retention(moments[k]),
            int(moments[k]["count"]), int(moments[k]["tick"]), k,
        ))
        retained = retained_episode_keys(moments, key)
        if not retained:
            moments.pop(key)
            return
        # Prepare all fallible copying/merging/space decisions before publishing.
        meanings = state.get("meanings") or {}
        prepared = dict(meanings)
        for episode_key in retained:
            if episode_key in prepared:
                prepared[episode_key] = copy.deepcopy(prepared[episode_key])
            self._retain_moment(prepared, episode_key, moments[episode_key], tick)
        successor = bound_retained_episode(prepared, set(retained), MEANING_CAPACITY)
        self._retention_refused = successor is None  # transient diagnostic, not cognition
        if successor is None:
            return
        state["meanings"].clear()
        state["meanings"].update(successor)
        for episode_key in retained:
            moments.pop(episode_key)

    def _retain_moment(self, meanings: dict[str, Any], key: str, entry: dict[str, Any], tick: int) -> None:
        """Prepare one retained observation without manufacturing another trial."""
        salience = float(entry.get("salience", 0.0))
        kept = meanings.get(key)
        if "motor_transition" in entry:
            # Actual event records are immutable; recurrence never rewrites an event.
            meanings[key] = entry
        elif kept is None:
            meanings[key] = {
                "count": int(entry["count"]),
                "tick": tick,
                "held": entry.get("held", "none"),
                "figure": entry.get("figure", "none"),
                "room": entry.get("room", "unknown"),
                "source": entry.get("source", "heard"),
                "acts": dict(entry.get("acts", {})),
                "context": list(entry.get("context", [])),
                "next": dict(entry.get("next", {})),
                "fed": int(entry.get("fed", 0)),
                "salience": round(salience, 4),
                "transitions": {a: dict(m) for a, m in entry.get("transitions", {}).items()},
                "consequences": {a: dict(c) for a, c in entry.get("consequences", {}).items()},
                "episode_tail": entry.get("episode_tail"),
            }
            if "krimelack" in entry:
                meanings[key]["krimelack"] = entry["krimelack"]
        else:
            kept["count"] = int(kept["count"]) + int(entry["count"])
            kept["tick"] = tick
            kept["fed"] = int(kept.get("fed", 0)) + int(entry.get("fed", 0))
            kept["salience"] = max(float(kept.get("salience", 0.0)), round(salience, 4))
            if "krimelack" in entry:
                kept["krimelack"] = entry["krimelack"]
            if entry.get("figure") and entry.get("figure") != "none":
                kept["figure"] = entry["figure"]
            if entry.get("room") and entry.get("room") != "unknown":
                kept["room"] = entry["room"]
            stored_acts = kept.setdefault("acts", {})
            for act_name, (tries, net_val) in entry.get("acts", {}).items():
                cur = stored_acts.setdefault(act_name, [0, 0.0])
                cur[0] = int(cur[0]) + int(tries)
                cur[1] = round(float(cur[1]) + float(net_val), 4)
            following = kept.setdefault("next", {})
            for other, count in entry.get("next", {}).items():
                following[other] = int(following.get(other, 0)) + int(count)
            while len(following) > FOLLOW_CAPACITY:
                del following[min(following, key=lambda k: (int(following[k]), k))]

            # Consolidate empirical transitions and consequences
            stored_trans = kept.setdefault("transitions", {})
            for act_name, succ_map in entry.get("transitions", {}).items():
                cur_act_map = stored_trans.setdefault(act_name, {})
                for succ_key, info in succ_map.items():
                    if succ_key not in cur_act_map:
                        cur_act_map[succ_key] = dict(info) if isinstance(info, dict) else {"count": int(info), "target_id": None}
                    else:
                        cur_act_map[succ_key]["count"] = int(cur_act_map[succ_key]["count"]) + (int(info["count"]) if isinstance(info, dict) else int(info))
            stored_cons = kept.setdefault("consequences", {})
            for act_name, c_info in entry.get("consequences", {}).items():
                stored_cons[act_name] = dict(c_info)
        if "episode_tail" in entry:
            meanings[key]["episode_tail"] = entry["episode_tail"]

    def _choose_syllable(self, situation: str, prior_syllable: str | None, uncertain: bool | None = None) -> tuple[tuple[int, int, int], str, str, str]:
        """The syllable for this beat from her speech record, by the law her acts use:
        under (situation, prior syllable) untried syllables come first in order of her
        lifetime tries; among tried ones the best mean measured worth of what followed.
        When an acoustic target was heard from a tutor or caregiver, resonance matching
        directs exploration toward the target formants.
        Under structural uncertainty, exploration samples least-tried syllables to prevent greedy collapse.
        Returns (drive, name, context, reason)."""

        context = f"{situation}:{prior_syllable if prior_syllable else 'start'}"
        totals = self._state.setdefault("syllable_totals", {})
        tried = (self._state.setdefault("speech", {}).get(context) or {}).get("syllables") or {}

        # Physical Sensorimotor Conduction Path:
        target = self._state.get("heard_speech_target")
        if target and target.get("envelopes") and not target.get("consumed"):
            cue_frames_list = [
                (
                    round(sum(env[:16]) / 16.0, GRAIN),
                    *(
                        round(sum(env[:16][c] for c in band) / max(1e-9, sum(env[:16])), GRAIN)
                        for band in EAR_BAND_CHANNELS
                    )
                )
                for env in target["envelopes"]
            ]
            mesh_drive, mesh_name, mesh_info = self._sensorimotor_mesh.readout(cue_frames_list)
            if mesh_drive is not None and mesh_name is not None:
                ctx = f"{situation}:{prior_syllable if prior_syllable else 'start'}"
                return mesh_drive, mesh_name, ctx, f"sensorimotor conduction: {mesh_name} (max_V={mesh_info['max_onset_v']:.2f})"

        # Resonate against active incoming speech during early development:
        heard_prof = getattr(self, "_last_heard_profile", None)
        ext_sound = getattr(self, "_last_external_sound_present", False)
        if self.live_organism_tick <= 60 and ext_sound and heard_prof and sum(heard_prof) > 0.05:
            syl_profs = self._state.setdefault("syllable_profiles", {})
            scored = []
            for s in SYLLABLES:
                s_prof = syl_profs.get(s) or _syllable_reafference(s)
                if s_prof is not None:
                    rho = spectral_cosine_similarity(s_prof, heard_prof)
                    if rho >= 0.70:
                        scored.append((rho, s))
            if scored:
                scored.sort(key=lambda item: (item[0], -SYLLABLES.index(item[1])), reverse=True)
                best_rho, syl = scored[0]
                drive = SYLLABLE_DRIVES.get(syl, DEFAULT_DRIVE)
                ctx = f"{situation}:{prior_syllable if prior_syllable else 'start'}"
                return drive, syl, ctx, f"auditory-vocal resonance against active afferent: {syl} (rho={best_rho:.2f})"

        # Native Ternary Matrix Resonant Conduction Path:
        target = self._state.get("heard_speech_target")
        if target and target.get("envelopes") and not target.get("consumed"):
            aud_trits = self._ternary_substrate.encode_cochlear_field_2d(target["envelopes"])
            cue_1024 = [0] * 1024
            cue_1024[AUDITORY_START:AUDITORY_END] = aud_trits
            decoded, _ = self._ternary_substrate.project_and_readout(cue_1024)
            if decoded["onset_idx"] is not None and decoded["vowel_idx"] is not None:
                o_idx = decoded["onset_idx"]
                v_idx = decoded["vowel_idx"]
                p_idx = decoded["pitch_idx"] if decoded["pitch_idx"] is not None else 0
                if o_idx < len(ONSETS) and v_idx < len(VOWELS) and p_idx < len(PITCHES_DECIHERTZ):
                    syl_name = f"{ONSETS[o_idx]}{VOWELS[v_idx][0]}{p_idx}"
                    drive = (PITCHES_DECIHERTZ[p_idx], v_idx, o_idx)
                    ctx = f"{situation}:{prior_syllable if prior_syllable else 'start'}"
                    return drive, syl_name, ctx, f"native ternary lattice resonance: {syl_name}"

        # Phase 3 Homeostatic Exhaust Resonant Pathway (genuine metabolic distress only):
        hunger_dsf = self._last_dsf_states.get("hunger") if hasattr(self, "_last_dsf_states") else None
        deficit = float(self.deficit)
        p_k = hunger_dsf["P_k"] if hunger_dsf else (deficit if deficit >= float(HUNGRY_BELOW) else 0.0)
        b_k = hunger_dsf["B_k"] if hunger_dsf else 0.5
        s_uf = hunger_dsf["S_UF"] if hunger_dsf else (b_k - p_k)
        is_strained = (deficit >= float(HUNGRY_BELOW)) and (p_k > b_k or s_uf < 0.0)
        if is_strained:
            cue_1024 = [0] * TOTAL_NODES
            cue_1024[SOMATIC_START:SOMATIC_START + 16] = [1] * 16
            d_k = hunger_dsf["D_k"] if hunger_dsf else deficit
            m_k = hunger_dsf["M_k"] if hunger_dsf else 0.0
            r_rev = hunger_dsf["R_rev_k"] if hunger_dsf else 1.0
            u_star = hunger_dsf["U_star_k"] if hunger_dsf else 0.5
            c_k = hunger_dsf["C_k"] if hunger_dsf else 0.0
            dsf_slice = self._ternary_substrate.encode_dsf_and_efferents(
                dsf_vector=(d_k, m_k, r_rev, u_star, c_k, p_k, b_k, s_uf)
            )
            cue_1024[EFFERENT_START:EFFERENT_END] = dsf_slice
            decoded, _ = self._ternary_substrate.project_and_readout(cue_1024)
            # Cluster 4 Syntax: Ordering derived from decoded native articulatory address (V3)
            if decoded["onset_idx"] is not None and decoded["vowel_idx"] is not None:
                o_idx = decoded["onset_idx"]
                v_idx = decoded["vowel_idx"]
                p_idx = decoded["pitch_idx"] if decoded["pitch_idx"] is not None else 3
            else:
                o_idx = 1  # 'm' (infant nasal murmur)
                v_idx = 0  # 'ah' (open vowel)
                p_idx = 3  # 3750 dHz (infant distress cry)
            if o_idx < len(ONSETS) and v_idx < len(VOWELS) and p_idx < len(PITCHES_DECIHERTZ):
                syl_name = f"{ONSETS[o_idx]}{VOWELS[v_idx][0]}{p_idx}"
                drive = (PITCHES_DECIHERTZ[p_idx], v_idx, o_idx)
                ctx = f"{situation}:{prior_syllable if prior_syllable else 'start'}"
                return drive, syl_name, ctx, f"homeostatic exhaust resonance: {syl_name} (P_k={p_k:.2f}>B_k={b_k:.2f})"

        # Resonant Auditory-Vocal Imitation: if a speech target was recently heard
        if target and (self.live_organism_tick - int(target.get("tick", 0)) <= 6) and target.get("profile"):
            t_prof = target["profile"]
            syl_profs = self._state.setdefault("syllable_profiles", {})
            ctx_dict = self._state.setdefault("speech", {}).setdefault(context, {"syllables": {}, "tick": self.live_organism_tick})
            resonance_map = ctx_dict.setdefault("resonance", {})

            candidates = tried if tried else [s for s in SYLLABLES if int(totals.get(s, 0)) > 0]
            scored_candidates: list[tuple[float, float, str]] = []
            for s in candidates:
                s_prof = syl_profs.get(s) or _syllable_reafference(s)
                if s_prof is not None:
                    rho = spectral_cosine_similarity(s_prof, t_prof)
                    if rho > float(resonance_map.get(s, 0.0)):
                        resonance_map[s] = round(rho, 4)
                    if rho >= 0.65:
                        s_data = tried.get(s, [0, 0.0])
                        mean_worth = float(s_data[1]) / max(1, int(s_data[0]))
                        scored_candidates.append((rho, mean_worth, s))

            if scored_candidates:
                scored_candidates.sort(key=lambda item: (item[0], item[1], -SYLLABLES.index(item[2])), reverse=True)
                best_rho, best_worth, syl = scored_candidates[0]
                return SYLLABLE_DRIVES[syl], syl, context, f"resonant answer under {context}: {syl} (rho={best_rho:.2f}, worth={best_worth:.2f})"

        # Physical syllable selection (V2: Tabular worth scoring excised)
        # Retain old speech records without consulting them for production decisions.
        if hasattr(self, "_modular_substrate") and self._modular_substrate is not None:
            try:
                art = self._modular_substrate.get_articulatory_efferent()
                if art is not None:
                    o_idx, v_idx, p_idx = art
                    if o_idx < len(ONSETS) and v_idx < len(VOWELS) and p_idx < len(PITCHES_DECIHERTZ):
                        syl_name = f"{ONSETS[o_idx]}{VOWELS[v_idx][0]}{p_idx}"
                        drive = (PITCHES_DECIHERTZ[p_idx], v_idx, o_idx)
                        return drive, syl_name, context, f"native modular articulation: {syl_name}"
            except Exception:
                pass
        untried = [s for s in SYLLABLES if s not in tried]
        syl = min(untried, key=lambda s: SYLLABLES.index(s)) if untried else min(tried, key=lambda s: SYLLABLES.index(s))
        return SYLLABLE_DRIVES[syl], syl, context, f"physical resonance under {context}: {syl}"

    def _choose(self, key: str, situation: str, acts: list[str], uncertain: bool | None = None, candidate_options: list[tuple] | None = None, snapshot: Any | None = None) -> tuple[str, str]:
        """The act for this structure: from the day's record (untried first,
        the least tried under structural uncertainty U*_k > 0 or visit interval,
        otherwise the best by one-step predictive foresight); when the day's
        record has nothing for this structure, from what her sleep kept for
        this situation; else the first act in the declared order."""

        label = "structure " + key[:6]



        # Cognitive Asset 1: Anticipatory Trajectory Reactivation
        meanings = self._state.get("meanings", {})
        fig = self._state.get("sight_figure") or "none"
        last_ev = (self._state.get("ear_event") or [None])[0] if isinstance(self._state.get("ear_event"), list) else "none"
        cur_room = self._state.get("room_now") or situation
        conserved = self._state.get("conserved_objects") or {}
        body_pos = self._state.get("body_pos")
        deficit = float(self.deficit)

        # Cognitive Asset 1: Anticipatory Trauma Veto (Acute Safety Gate)
        if meanings and acts:
            vetoed = set()
            for candidate in acts:
                val, promo_reason = evaluate_anticipatory_consequence(
                    candidate,
                    visual_figure=fig,
                    acoustic_event=str(last_ev),
                    room=cur_room,
                    meanings=meanings,
                )
                if val < -0.35:
                    vetoed.add(candidate)

            viable_acts = [a for a in acts if a not in vetoed]
            if viable_acts and len(viable_acts) < len(acts):
                acts = viable_acts

        # Cognitive Asset 2: Multi-Step Predictive Affordance Planning
        plan_dict = self._state.get("affordance_plan")
        if plan_dict:
            from dsf_ai_service.affordance_planner import AffordancePlan
            plan = AffordancePlan.from_dict(plan_dict)
            step = plan.next_step()
            if step and step.action in acts:
                self._state["planned_target_id"] = step.target_id
                should_advance = False
                room_now = self._state.get("room_now")
                if step.action == "toward_door" and step.expected_postcondition.startswith("in_region_"):
                    dest_reg = step.expected_postcondition.replace("in_region_", "")
                    if room_now == dest_reg:
                        should_advance = True
                else:
                    should_advance = True

                if should_advance:
                    plan.advance_step()
                    if plan.is_complete:
                        self._state["affordance_plan"] = None
                        self._state["planned_target_id"] = None
                    else:
                        self._state["affordance_plan"] = plan.to_dict()
                return step.action, label + f": affordance plan step {step.step_index} ({step.action} -> {step.expected_postcondition})"
            else:
                self._state["affordance_plan"] = None
                self._state["planned_target_id"] = None

        # Rotational spin trap damping: after 2 consecutive turns, damp in-place turns
        consec_turns = int(self._state.get("consecutive_turns", 0))
        if consec_turns >= 2:
            non_turns = [a for a in acts if a not in ("turn_left", "turn_right")]
            if non_turns:
                acts = non_turns

        # Early infant acoustic imitation: infant vocal entrainment under active microphone speech
        heard_prof = getattr(self, "_last_heard_profile", None)
        ext_sound = getattr(self, "_last_external_sound_present", False)
        if self.live_organism_tick <= 60 and ext_sound and heard_prof and sum(heard_prof) > 0.05 and "say" in acts:
            syl_profs = self._state.setdefault("syllable_profiles", {})
            matches_speech = any(
                spectral_cosine_similarity(syl_profs.get(s) or _syllable_reafference(s), heard_prof) >= 0.80
                for s in SYLLABLES
            )
            if matches_speech:
                return "say", f"{label}: acoustic afferent entrainment: vocal resonance with incoming speech"

        # Cognitive Asset 7: Stage 4 Conversational Turn-Taking Flow
        # Calibrated 250ms quiet gap following speaker cessation releases vocal turn response
        target = self._state.get("heard_speech_target")
        quiet_gap = self.live_organism_tick - int(self._state.get("last_sound_heard_tick", -999))
        if (
            quiet_gap == 1
            and target
            and not target.get("consumed")
            and target.get("tick") in (self.live_organism_tick, int(self._state.get("last_sound_heard_tick", -999)))
            and "say" in acts
        ):
            target["consumed"] = True
            return "say", f"{label}: conversational turn release after 250ms quiet gap"

        # Cognitive Asset 6: Unified Structural Boredom & Distal Interest Potential Manifold
        dwell_beats = int(self._state.get("room_dwell_beats", 0))
        deficit = float(self.deficit)
        sleep_ratio = float(self._state.get("sleep_pressure", 0)) / SLEEP_PRESSURE_CEILING
        cur_room = self._state.get("room_now")

        last_ref = self._state.get("last_refusal")
        refused_act = last_ref[0] if (last_ref and (self.live_organism_tick - int(last_ref[2])) <= 2) else None
        door_refused = (refused_act == "toward_door")

        tested_non_nutritive = {o_id for o_id in (self._state.get("tested_non_nutritive") or ()) if not is_genuine_food_object(o_id)}
        known_non_foods = {o_id for o_id, c in conserved.items() if c.get("non_nutritive") is True and not is_genuine_food_object(o_id)} | tested_non_nutritive

        # Homeostatic Barrenness in Lived Cognition:
        # Food is present only if genuine food is located in the current room or currently visible
        here_reg = _region_of(snapshot, PositionMM(*(self._state.get("body_pos") or (0, 0, 0))), 250) if snapshot is not None else None
        has_food = any(
            is_genuine_food_object(o_id) and c.get("room_id") == cur_room and not c.get("currently_depleted")
            for o_id, c in conserved.items()
        ) or (
            snapshot is not None and here_reg is not None and any(
                is_genuine_food_object(item.object_id)
                and item.material is not None
                and getattr(item.material, "digestible_mass_micrograms", 0) > 0
                and not (conserved and conserved.get(item.object_id, {}).get("currently_depleted"))
                and _region_of(snapshot, item.position, item.radius_mm) is here_reg
                for item in snapshot.objects if item.position is not None
            )
        ) or (
            candidate_options is not None and any(
                opt[0] in ("toward_food", "grasp", "take")
                and is_genuine_food_object(opt[3])
                and not (conserved and conserved.get(opt[3], {}).get("currently_depleted"))
                and not str(opt[1]).startswith("via ")
                for opt in candidate_options
            )
        )
        has_candidate_nourishment = has_food
        is_barren = False
        # Does the current environment lack the active homeostatic requirement?
        if self.live_organism_tick > 100 or deficit >= 0.6 or sleep_ratio >= 0.5 or self._state.get("feeding"):
            needs_bed = sleep_ratio >= 0.5
            needs_food = bool(self._state.get("feeding") or deficit >= 0.6)
            known_foods = _consequence_qualified_food_ids(self._state)
            has_bed = any(c.get("room_id") == cur_room for o_id, c in conserved.items() if o_id == BED_ID) or (candidate_options is not None and any(opt[0] == "toward_bed" for opt in candidate_options))

            is_barren = (needs_bed and not has_bed) or (needs_food and not has_candidate_nourishment)
            if is_barren:
                phi_barren = 1.0 - math.exp(-float(dwell_beats) / 20.0)
                is_transit = (cur_room == "hallway")
                if (phi_barren > 0.25 or (is_transit and dwell_beats >= 1)) and "toward_door" in acts and not door_refused:
                    return "toward_door", f"{label}: barren basin exhaustion ({phi_barren:.2f} over {dwell_beats} dwell beats in {cur_room}): evacuating toward negative space"

        # Physical release: when holding an item whose bite was unsuccessful, or is depleted/non-nutritive, release it
        holding_item = (candidate_options is not None and any(o[0] == "release" for o in candidate_options)) or (self._state.get("held_object_id") is not None)
        if "release" in acts and holding_item:
            held_target = self._state.get("unsuccessful_bite_held_id") or self._state.get("held_object_id") or self._state.get("gaze_target")
            held_target_str = held_target if isinstance(held_target, str) else None
            held_is_depleted = any(
                (c.get("non_nutritive") and not is_genuine_food_object(o_id)) or c.get("currently_depleted")
                for o_id, c in conserved.items()
                if o_id == held_target_str
            )
            if (
                self._state.get("unsuccessful_bite_held_id")
                or held_is_depleted
                or (held_target_str in tested_non_nutritive and not is_genuine_food_object(held_target_str))
                or not (self._state.get("feeding") or deficit >= 0.60)
            ):
                return "release", f"{label}: release held item (sated or non-nutritive)"

        if not self._state.get("feeding") and not has_candidate_nourishment:
            surplus = max(0.0, min(1.0, (1.0 - deficit) * (1.0 - sleep_ratio)))
            boredom = surplus * (1.0 - math.exp(-float(dwell_beats) / 30.0))
            if boredom > 0.25 and "toward_door" in acts and not door_refused:
                return "toward_door", f"{label}: structural boredom ({boredom:.2f} over {dwell_beats} dwell beats): evacuating saturated basin toward negative space"

        # Physical execution feedback: an act refused on the previous beat yields to alternative viable acts
        if refused_act and len(acts) > 1:
            viable_unrefused = [a for a in acts if a != refused_act]
            if viable_unrefused:
                acts = viable_unrefused

        # Physical Affordance Pursuit under Hunger Deficit (Resonant Surge toward nourishment)
        if self._state.get("feeding") or deficit >= 0.6:
            if "take" in acts:
                return "take", f"{label}: metabolic hunger surge -> take offered sustenance"
            if "grasp" in acts:
                if candidate_options is not None:
                    grasp_opts = [
                        o for o in candidate_options
                        if o[0] == "grasp"
                        and o[3]
                        and is_genuine_food_object(o[3])
                        and o[3] not in known_non_foods
                        and (snapshot is not None and handleable(_object(snapshot, o[3])))
                    ]
                    if grasp_opts:
                        return "grasp", f"{label}: metabolic hunger surge -> grasp candidate nourishment; {grasp_opts[0][3]}"
            if "toward_food" in acts:
                if candidate_options is not None:
                    food_opts = [
                        o for o in candidate_options
                        if o[0] == "toward_food"
                        and o[3]
                        and is_genuine_food_object(o[3])
                        and o[3] not in known_non_foods
                    ]
                    if food_opts:
                        return "toward_food", f"{label}: metabolic hunger surge -> approach candidate nourishment; {food_opts[0][3]}"
            # Phase 3 Homeostatic Exhaust Cycle (Section 4 of WHOLE_BRAIN_SPECIFICATION.md):
            # When motor affordances cannot relieve metabolic deficit (confined in playpen, barred doors, or food out of reach):
            # Frustrated kinetic energy is inhibited along the motor manifold and forced through the lowest-resistance
            # plastic channels of the substrate to actuate the vocal valve ('say').
            hunger_dsf = self._last_dsf_states.get("hunger") if hasattr(self, "_last_dsf_states") else None
            p_k = hunger_dsf["P_k"] if hunger_dsf else 0.8
            b_k = hunger_dsf["B_k"] if hunger_dsf else 0.5
            s_uf = hunger_dsf["S_UF"] if hunger_dsf else (b_k - p_k)
            strained = (p_k > b_k or s_uf <= 0)
            since_last_exhaust = self.live_organism_tick - int(self._state.get("homeostatic_exhaust_tick", -999))

            # Vocal exhaust discharges when strained (P_k > B_k -> S_UF <= 0) and direct food affordances are not reachable,
            # with a physiological refractory recovery period (B_k recovery) of >= 15 beats.
            if strained and "say" in acts and since_last_exhaust >= 15:
                self._state["homeostatic_exhaust_tick"] = self.live_organism_tick
                self._state["unsuccessful_bite_held_id"] = None
                pass  # V4: downstream DSF coordinates are never rewritten
                return "say", f"{label}: homeostatic exhaust cycle: P_k ({p_k:.3f}) > B_k ({b_k:.3f}) [S_UF={s_uf:.3f} <= 0] -> vocal valve exhaust"

            if is_barren and "toward_door" in acts and not door_refused:
                return "toward_door", f"{label}: metabolic hunger surge -> evacuate barren basin ({cur_room}) toward nourishment"
            if "toward_door" in acts and not door_refused:
                return "toward_door", f"{label}: metabolic hunger surge -> search connecting portal for nourishment"

        entry = self._state.setdefault("acts", {}).get(key)
        label = "structure " + key[:6]

        # Physical Action Selection (V1: Tabular RL and score-based exploration excised)
        # Old trial counts/returns in self._state['acts'] are retained as inert canonical historical records.
        # Action selection is governed by deterministic physical state:
        if "step" in acts:
            return "step", label + ": native locomotion stride"
        return acts[0], label + ": physical action (" + acts[0] + ")"

    # ----- commit: what the world allowed, what she took in, what she said ------------

    def commit(self, decision: Decision, *, applied_action: str, refusal: str | None,
               intake_micrograms: int, spoke: bytes | None, heard_profile: tuple[float, ...] | None,
               self_profile: tuple[float, ...] | None, tick_now: int, contact_fraction: float = 0.0,
               contact_millikelvin: int | None = None, motor_result: Any = None) -> None:
        state = self._state
        if tick_now != self.live_organism_tick:
            raise RuntimeError("functional organism tick left its line")
        actions = motor_result.applied_actions if motor_result is not None else () if applied_action == 'refused' else (applied_action,)
        if motor_result is not None:
            state['last_body_motor_result'] = motor_result.as_record()
            if motor_result.mouth_object_id is not None:
                from dataclasses import replace
                decision = replace(decision, target_object_id=motor_result.mouth_object_id)
        if any((a in MOVES for a in actions)) and refusal is None:
            state['strides'] += 1
        if any((a in ('grasp', 'take') for a in actions)) and refusal is None:
            state['handled'] = int(state.get('handled', 0)) + 1
        if any((a in ('take', 'grasp') for a in actions)) and refusal is None and decision.target_object_id:
            state['unsuccessful_bite_held_id'] = None
            state['planned_target_id'] = decision.target_object_id
        # Skin on skin or object contact by her own act is felt on the next beat, at its temperature.
        if (applied_action in ("release", "drop") or any(a in ("release", "drop") for a in actions)) and refusal is None:
            state["unsuccessful_bite_held_id"] = None
            if state.get("planned_target_id") == decision.target_object_id:
                state["planned_target_id"] = None
            if decision.target_object_id and decision.target_object_id in state.get("conserved_objects", {}):
                state["conserved_objects"][decision.target_object_id]["position"] = tuple(state.get("body_pos") or (0, 0, 0))
                state["conserved_objects"][decision.target_object_id]["room_id"] = state.get("room_now")
                if ("barrier inhibition" in decision.reason or "non-nutritive" in decision.reason) and not is_genuine_food_object(decision.target_object_id):
                    state["conserved_objects"][decision.target_object_id]["non_nutritive"] = True
                    state["conserved_objects"][decision.target_object_id]["is_food"] = False
                    tested_set = set(state.get("tested_non_nutritive") or ())
                    tested_set.add(decision.target_object_id)
                    state["tested_non_nutritive"] = sorted(tested_set)
        reached = applied_action in ("reach_hand", "touch", "grasp") and refusal is None
        state["pending_contact"] = round(float(contact_fraction), 6) if reached else 0.0
        state["pending_contact_millikelvin"] = int(contact_millikelvin) if (reached and contact_millikelvin is not None) else None
        before = self.reserve_micrograms
        # Base expenditure on actual physical work performed (V19)
        basal = BASAL_BURN_MICROGRAMS
        action_cost = 0
        if actions and refusal is None:
            if any(a in MOVES for a in actions):
                action_cost += BASAL_BURN_MICROGRAMS
            if any(a in ("grasp", "take") for a in actions):
                action_cost += BASAL_BURN_MICROGRAMS // 2
            if any(a in ("bite", "chew") for a in actions):
                action_cost += BASAL_BURN_MICROGRAMS // 2
        if spoke is not None:
            action_cost += BASAL_BURN_MICROGRAMS // 4
        burn = basal + action_cost

        # Conserved digestive stock assimilation (V36)
        from dsf_ai_service.substrate.compound_motor_material import DigestiveStock
        stock_rec = state.get("digestive_stock")
        stock = DigestiveStock.from_record(stock_rec) if stock_rec else DigestiveStock(0)
        rem_res = max(0, before - burn)
        new_stock, new_res, assimilated = stock.assimilate(
            reserve_after_expenditure_micrograms=rem_res,
            reserve_capacity_micrograms=CAPACITY_MICROGRAMS,
            swallowed_micrograms=int(intake_micrograms),
        )
        state["digestive_stock"] = new_stock.as_record()
        state["reserve_micrograms"] = new_res
        intake = assimilated
        state["feeding"] = (state["feeding"] or before < CAPACITY_MICROGRAMS * HUNGRY_BELOW) and state["reserve_micrograms"] < CAPACITY_MICROGRAMS * SATED_ABOVE
        if intake:
            state["meals_micrograms"] += intake
            state["bites"] += 1
            state["taste_residue"] = min(1.0, float(state.get("taste_residue", 0.0)) + intake / 100_000.0)
            if decision.target_object_id and is_genuine_food_object(decision.target_object_id):
                state["unsuccessful_bite_held_id"] = None
                tested_set = set(state.get("tested_non_nutritive") or ())
                tested_set.discard(decision.target_object_id)
                state["tested_non_nutritive"] = sorted(tested_set)
                conserved = state.setdefault("conserved_objects", {})
                entry = conserved.setdefault(decision.target_object_id, {
                    "object_id": decision.target_object_id,
                    "position": tuple(state.get("body_pos") or (0, 0, 0)),
                    "radius_mm": 0,
                    "room_id": state.get("room_now"),
                    "last_seen_tick": tick_now,
                    "confidence": 1.0,
                })
                entry["historical_intake_micrograms"] = int(entry.get("historical_intake_micrograms", 0)) + intake
                entry["fed_count"] = int(entry.get("fed_count", 0)) + 1
                entry["currently_depleted"] = False
                entry["is_food"] = True
            last = state.get("last_moment")   # Level 3: a bite within the window is what followed the moment
            if last is not None and tick_now - int(last[1]) <= FOLLOW_WINDOW_BEATS and last[0] in (state.get("moments") or {}):
                mom_entry = state["moments"][last[0]]
                mom_entry["fed"] = int(mom_entry.get("fed", 0)) + 1
                mom_entry["count"] = int(mom_entry.get("count", 1)) + 1
                if decision.target_object_id:
                    mom_entry["target_object_id"] = decision.target_object_id
                intake_salience = compute_somatic_salience(reserve_delta_ug=intake)
                mom_entry["salience"] = max(float(mom_entry.get("salience", 0.0)), intake_salience)
                acts_rec = mom_entry.setdefault("acts", {})
                act_stat = acts_rec.setdefault("bite", [0, 0.0])
                act_stat[0] += 1
                act_stat[1] = round(act_stat[1] + min(1.0, intake / 100_000.0), 4)
                consequences = mom_entry.setdefault("consequences", {})
                consequences["bite"] = {
                    "intake": intake,
                    "relief": "feeding",
                    "target_id": decision.target_object_id,
                }
        elif (applied_action == "bite" or "bite" in actions or (decision.act == "bite" and refusal is not None)) and decision.target_object_id:
            state["unsuccessful_bite_held_id"] = decision.target_object_id
            conserved = state.setdefault("conserved_objects", {})
            entry = conserved.setdefault(decision.target_object_id, {
                "object_id": decision.target_object_id,
                "position": tuple(state.get("body_pos") or (0, 0, 0)),
                "radius_mm": 0,
                "room_id": state.get("room_now"),
                "last_seen_tick": tick_now,
                "confidence": 1.0,
            })
            if is_genuine_food_object(decision.target_object_id):
                entry["currently_depleted"] = True
            else:
                tested_set = set(state.get("tested_non_nutritive") or ())
                tested_set.add(decision.target_object_id)
                state["tested_non_nutritive"] = sorted(tested_set)
                entry["non_nutritive"] = True
                entry["is_food"] = False
                entry["tested_non_food"] = True
                entry["last_tested_tick"] = tick_now
        geom = getattr(self, "_receptor_geometry", None)
        nociception_span = max(1, int(geom.touch_temperature_max_millikelvin) - NOCICEPTION_MILLIKELVIN) if geom is not None else 23_000
        action_pain = _clamp((contact_millikelvin - NOCICEPTION_MILLIKELVIN) / float(nociception_span), 0.0, 1.0) if contact_millikelvin is not None else 0.0
        if action_pain > 0.0:
            self._pain = action_pain
            last = state.get("last_moment")
            if last is not None and tick_now - int(last[1]) <= FOLLOW_WINDOW_BEATS and last[0] in (state.get("moments") or {}):
                mom_entry = state["moments"][last[0]]
                mom_entry["salience"] = max(float(mom_entry.get("salience", 0.0)), action_pain)
                acts_rec = mom_entry.setdefault("acts", {})
                act_stat = acts_rec.setdefault(applied_action, [0, 0.0])
                act_stat[0] += 1
                act_stat[1] = round(act_stat[1] - action_pain, 4)
        state["taste_residue"] = round(float(state.get("taste_residue", 0.0)) * 0.95, 6)

        pending_trans = state.get("pending_transition")
        if pending_trans is not None:
            # Empty world commands also accompany a real, synthesized vocal act.
            # Preserve that measured act while keeping passive time out of trials.
            pending_trans["applied_action"] = (
                "say" if applied_action == "body" and spoke is not None else applied_action
            )
            pending_trans["refusal"] = refusal
            pending_trans["intake"] = intake
            if intake > 0:
                pending_trans["relief"] = "feeding"
            pain = float(getattr(self, "_pain", 0.0))
            last = state.get("last_moment")
            if (intake > 0 or action_pain > 0) and last is not None and last[0] in state.get("moments", {}) and tick_now - int(last[1]) <= FOLLOW_WINDOW_BEATS:
                pending_trans["outcome_key"] = last[0]
            pending_trans["salience"] = compute_somatic_salience(
                reserve_delta_ug=intake,
                shock_magnitude=pain,
                pain_signal=(pain > 0.0),
            )

        pending = state.get("pending_act")
        if pending is not None:
            pending["intake"] = int(pending.get("intake", 0)) + intake
            pending["refused"] = bool(pending.get("refused")) or refusal is not None
            pending["burn"] = int(pending.get("burn", 0)) + int(burn)  # what this act actually cost her, measured
        elif decision.act == "bite" and intake and state.get("last_chosen"):
            last = state["last_chosen"]
            self._credit(str(last["key"]), str(last["act"]), round(float(last["deficit"]), 6), tick_now, str(last.get("regimes", "")))

        if not state.get("asleep"):
            state["sleep_pressure"] = int(state.get("sleep_pressure", 0)) + 1
        # Strides and handled counted once from authoritative settled axis receipt (V22)
        if refusal is not None:
            refusals = state["refusals"]
            refusals[refusal] = int(refusals.get(refusal, 0)) + 1
            while len(refusals) > REFUSAL_CAPACITY:
                del refusals[min(refusals, key=lambda k: int(refusals[k]))]
            last_ref = state.get("last_refusal")
            prior_count = int(last_ref[4]) if (last_ref and last_ref[0] == decision.act) else 0
            state["last_refusal"] = (decision.act, applied_action, tick_now, refusal, prior_count + 1)
        else:
            state["last_refusal"] = None
        key = choice_key("".join(token[0] for token in decision.signature.split(" ")))
        familiarity = state["familiarity"]
        entry = familiarity.get(key)
        familiarity[key] = [1, tick_now] if entry is None else [int(entry[0]) + 1, tick_now]
        while len(familiarity) > FAMILIARITY_CAPACITY:
            del familiarity[min(familiarity, key=lambda k: (int(familiarity[k][1]), k))]  # the least recently met leaves
        episodes = state["episodes"]
        episodes.append([tick_now, key, decision.act, applied_action, state["reserve_micrograms"] - before, decision.signature])
        del episodes[:-EPISODE_CAPACITY]
        ambient = float(state.get("ambient_sound", 0.0))
        if heard_profile is not None and sum(heard_profile) > 0:
            state["heard"].append({"tick": tick_now, "profile": list(heard_profile)})
            del state["heard"][:-HEARD_CAPACITY]
            energy = sum(heard_profile) / len(heard_profile)
            state["ambient_sound"] = round(ambient * float(AMBIENT_MEMORY) + energy * (1.0 - float(AMBIENT_MEMORY)), 6)
        else:
            state["ambient_sound"] = round(ambient * float(AMBIENT_MEMORY), 6)
        if self_profile is not None and state.get("pending_drive") is not None:
            p_drive = tuple(state["pending_drive"])
            s_name = next((name for name, d in SYLLABLE_DRIVES.items() if d == p_drive), None)
            state["voice"].append({
                "drive": list(p_drive),
                "heard": list(self_profile),
                "syllable": s_name,
                "tick": tick_now,
            })
            del state["voice"][:-VOICE_CAPACITY]
        state["pending_voice"] = None if spoke is None else base64.b64encode(spoke).decode("ascii")
        state["pending_drive"] = None if spoke is None else list(decision.drive)
        if spoke is not None:
            state["last_spoke_tick"] = tick_now
            state["syllables"] += 1
            spoke_drive = tuple(decision.drive) if decision.drive is not None else DEFAULT_DRIVE
            syl_name = next((name for name, d in SYLLABLE_DRIVES.items() if d == spoke_drive), DEFAULT_SYLLABLE)
            state["syllable_totals"][syl_name] = int(state["syllable_totals"].get(syl_name, 0)) + 1
            tokens_commit = decision.signature.split(" ")
            sit_commit = coarse_key("".join(t[0] for t in tokens_commit))
            last_prior = state.get("prior_syllable")
            ctx_key = f"{sit_commit}:{last_prior if last_prior else 'start'}"
            speech_rec = state.setdefault("speech", {})
            ctx_entry = speech_rec.setdefault(ctx_key, {"syllables": {}, "tick": tick_now})
            ctx_entry["tick"] = tick_now
            syl_data = ctx_entry["syllables"].setdefault(syl_name, [0, 0.0])
            syl_data[0] = int(syl_data[0]) + 1
            state["prior_syllable"] = syl_name
            state["last_said"] = syl_name   # what her own sound's moment is keyed by when it closes
            while len(speech_rec) > SPEECH_RECORD_CAPACITY:
                del speech_rec[min(speech_rec, key=lambda k: (int(speech_rec[k].get("tick", 0)), k))]
        state["last_act"] = decision.act
        state["tick"] = tick_now + 1


__all__ = (
    "BODY_AXES", "CAPACITY_MICROGRAMS", "Decision", "FunctionalOrganism", "MAGIC", "OpticalEvidence", "SCHEMA", "Sensed",
    "SeenThing", "SYLLABLES", "SYLLABLE_DRIVES", "cochlear_profile", "in_hand_reach", "move_commands_toward", "spectral_cosine_similarity",
    "syllable_pcm", "things_in_sight", "project_caregiver_gaze_ray",
)
