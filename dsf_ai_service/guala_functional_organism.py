"""The functional organism (Joe, 2026-09-14): no neurons, no charge, no muscles.

Her senses come in as measured streams across multi-modal active and passive
modalities; the DSF-AI kernel (uf_core L0-L4) reads the discrete structural
geometry of those streams every beat; a bounded memory keeps what exact discrete
structures (7-atom sign gates) she has met, what she did, and what her own voice
sounds like; her acts are chosen via one-step predictive foresight over recorded
successors and measured bodily need satisfaction, with exploration governed by
structural uncertainty (U*_k > 0); her airway synthesis closes the sensorimotor
loop via acoustic self-hearing and situational prosody. Everything here is a
function of her state; nothing is scripted meaning, nothing is flattened into
continuous approximations, and nothing speaks for her.

Bounds (the lean doctrine): every store below has a fixed capacity and the
encoded body is a few tens of kilobytes at any age.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import struct
from typing import Any

import pandas as pd
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

from dsf_ai_service.guala_caretaker_hand import (
    _approach_point, _distance_mm, _heading_toward, _portal_points, _portal_route, _region_of,
    nothing_left_to_bite, offered_within_reach,
)
from dsf_ai_service.guala_voice import ONSETS, PITCHES_DECIHERTZ, VOWELS, syllable_pcm as airway_syllable_pcm
from dsf_ai_service.substrate.embodiment_world import (
    BodySurfaceActuation, BodySurfaceContactCommand,
    GraspContactCommand, MoveCommand, OralContactCommand, PoseMM, PositionMM,
    ReleaseHeldObjectCommand, TakeContactHeldObjectCommand, TouchContactCommand, _derived_contact_patch_square_mm, _receptor_position,
    rotate_lattice_offset,
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
FOCAL_COLUMNS = 80
FOCAL_ROWS = 60
STRUCTURE_FLOOR = 4800 * 4   # total edge energy below this (about four levels per site) is a flat field
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
HEAD_PITCH_BOUND_MILLIDEGREES = 45_000

# Her acts are chosen from her own record, not by rules. The kernel names the
# discrete multi-modal structure in front of her each beat; the record keeps,
# for each structure she has met, each act she tried there, the successor
# distribution that followed, and the measured value to her bodily needs.
ACTS = ("take", "grasp", "touch", "release", "toward_food", "toward_bed", "toward_thing", "toward_door", "toward_person", "reach_hand", "step", "turn_left", "turn_right", "say", "rest")
ACT_RECORD_CAPACITY = 256   # structures remembered with their acts; recurrent structures persist
EXPLORE_EVERY = 8
MAX_CANDIDATES = 32

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
CONSOLIDATED_CAPACITY = 64
RETIRED_KEYS = ("visited", "door_goal", "bout_syllables", "quiet_until_tick", "blocked_doors", "attended_tick", "unreachable_food", "food_goal",
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
EAR_BANDS = 6
EAR_BAND_CHANNELS = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11), (12, 13), (14, 15))
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
KERNEL_MINIMUM = 24
STREAM_FLOOR = 0.05

# Memory bounds.
FAMILIARITY_CAPACITY = 512
EPISODE_CAPACITY = 64
HEARD_CAPACITY = 8
VOICE_CAPACITY = 16
REFUSAL_CAPACITY = 32

# Voice: one syllable through her airway, chosen from her speech record under
# (situation, prior syllable); a room sound standing out within the answer
# window after it is what pays. Nothing scripted answers a heard sound.
BABBLE_EVERY_BEATS = 4
HEARD_ENERGY_FLOOR = 0.004      # below this mean cochlear envelope, a sound is room noise
HEARD_ABOVE_AMBIENT = 2.0       # a sound worth answering is at least twice the running ambient level
AMBIENT_MEMORY = Fraction(15, 16)
COCHLEAR_CHANNELS = 32
VOICE_VERSION = 2
SPEECH_RECORD_CAPACITY = 64
ANSWER_WINDOW_BEATS = 4
PHRASE_WINDOW_BEATS = 8

# Syllables: her airway's onsets x vowels (2 x 5 = 10), at its first pitch (the
# other three pitches are not in the record yet: a reduction, stated here).
# Syllables are chosen from her own record of which sounds got answered,
# keyed by situation and prior syllable so speech can grow into syntax.
# Untried syllables are explored in order of lifetime tries (zero clock arithmetic).
SYLLABLES = tuple(f"{onset}{v[0]}" for onset in ONSETS for v in VOWELS)
SYLLABLE_DRIVES = {
    f"{onset}{v[0]}": (PITCHES_DECIHERTZ[0], v_idx, o_idx)
    for o_idx, onset in enumerate(ONSETS)
    for v_idx, v in enumerate(VOWELS)
}
DEFAULT_SYLLABLE = SYLLABLES[0]
DEFAULT_DRIVE = SYLLABLE_DRIVES[DEFAULT_SYLLABLE]

# Her body's axes, declared once (index, name, unit, position, minimum,
# neutral, maximum).
_ANGLE = ("millidegree", 0, -75_000, 0, 75_000)
_SMALL_ANGLE = ("millidegree", 0, -45_000, 0, 45_000)
_APERTURE = ("micrometre", 10_000, 0, 10_000, 12_000)
_MOUTH = ("micrometre", 0, 0, 0, 40_000)
_GRIP = ("micrometre", 0, 0, 0, 90_000)
_TRACT = ("square_millimetre", 0, 0, 0, 5_000)
BODY_AXES = tuple(
    (index, name, *spec)
    for index, (name, spec) in enumerate((
        ("torso_pitch", _SMALL_ANGLE), ("torso_roll", _SMALL_ANGLE),
        ("neck_yaw", _ANGLE), ("neck_pitch", _SMALL_ANGLE),
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


def _is_food(item: Any) -> bool:
    return item.material is not None and item.object_id.startswith("apple")


def _bearing_offset(heading: int, bearing: int) -> int:
    return (bearing - heading + 180_000) % 360_000 - 180_000


def things_in_sight(snapshot: Any) -> tuple[SeenThing, ...]:
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
        seen.append(SeenThing(item.object_id, item.position, item.radius_mm, distance, bearing, _is_food(item)))
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
    (fractions of the field), or the centre when the field is flat."""

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


def handleable_held(item: Any) -> bool:
    """A thing in another hand she can take: light, small, not food."""

    return item is not None and not _is_food(item) and int(item.mass_grams) <= HANDLE_MASS_GRAMS and int(item.radius_mm) <= HANDLE_RADIUS_MM


def handleable(item: Any) -> bool:
    """A thing she can pick up: light, small, on the floor, and not food."""

    return (item is not None and item.position is not None and not _is_food(item)
            and int(item.mass_grams) <= HANDLE_MASS_GRAMS and int(item.radius_mm) <= HANDLE_RADIUS_MM)


def drop_spot_clear(snapshot: Any, body: Any, item: Any) -> bool:
    """The world sets a released thing down a clearance ahead of the body;
    that spot must not touch another thing or body, or the world refuses."""

    from dsf_ai_service.substrate.embodiment_world import RELEASE_CLEARANCE_MM, _is_bed, rotate_lattice_offset

    dx, dy = rotate_lattice_offset(max(body.radius_mm, item.radius_mm) + item.radius_mm + RELEASE_CLEARANCE_MM, 0, body.pose.heading_millidegrees)
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


def move_commands_toward(snapshot: Any, target: PositionMM, stop_mm: int) -> tuple[MoveCommand, ...]:
    """One stride toward ``target`` (turning to face it), then sidesteps the
    world may accept instead when the straight stride is blocked."""

    body = _self_body(snapshot)
    origin = body.pose.position
    bearing = _heading_toward(origin, target)
    goal = _approach_point(origin, target, stop_mm)
    span = _distance_mm(origin, goal)
    commands = []
    if span <= 0:
        return (MoveCommand(PoseMM(origin, bearing), BEAT_MICROSECONDS),)
    stride = min(STEP_MM, span)
    for offset in (0, *SIDESTEP_MILLIDEGREES):
        heading = (bearing + offset) % 360_000
        radians = math.radians(heading / 1000)
        step = PositionMM(round(origin.x + stride * math.cos(radians)), round(origin.y + stride * math.sin(radians)), origin.z)
        commands.append(MoveCommand(PoseMM(step, bearing), BEAT_MICROSECONDS))
    return tuple(commands)


def door_crossing(snapshot: Any, portal: Any, from_region: str) -> tuple[PositionMM, PositionMM]:
    """The two floor points of a doorway crossing: a margin before it inside
    ``from_region`` and a margin past it, on the doorway's centre line."""

    return _portal_points(portal, from_region, snapshot, 0, DOOR_MARGIN_MM)


def door_crossing_commands(snapshot: Any, portal: Any, from_region: str) -> tuple[MoveCommand, ...]:
    """Steps through a doorway, centre first, then across its width and with
    shorter margins past it, so a thing standing near the far side of the
    door does not close it."""

    commands = []
    for margin in (DOOR_MARGIN_MM, 450, 350):
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


def candidates(
    snapshot: Any,
    body: Any,
    held: Any,
    offered: Any,
    seen: tuple[SeenThing, ...],
    tick: int,
    say_drive: tuple[int, int, int] | None = None,
    say_detail: str = "a syllable of her own",
) -> list[tuple[str, str, tuple[Any, ...], str | None, tuple[int, int, int] | None]]:
    """What her body can do this beat, across every sensed target: each entry is
    (act, detail, world commands tried in order, target, voice drive).
    Candidate count is strictly bounded by what she sees plus her room's doors."""

    out: list[tuple[str, str, tuple[Any, ...], str | None, tuple[int, int, int] | None]] = []
    position, heading = body.pose.position, body.pose.heading_millidegrees
    reachable = [item for item in snapshot.objects if item.position is not None and in_hand_reach(snapshot, item)]

    # 1. Take from hand
    if held is None and offered is not None and handleable_held(offered):
        out.append(("take", offered.object_id + " from a hand", (TakeContactHeldObjectCommand(BEAT_MICROSECONDS),), offered.object_id, None))

    # 2. Grasp (one reachable object per world grasp law) and touch reachable things
    if held is None and len(reachable) == 1 and (handleable(reachable[0]) or _is_food(reachable[0])):
        out.append(("grasp", reachable[0].object_id, (GraspContactCommand(BEAT_MICROSECONDS),), reachable[0].object_id, None))
    if held is None:
        for item in reachable:
            if item.material is not None:
                out.append(("touch", item.object_id, (TouchContactCommand(item.object_id, BEAT_MICROSECONDS),), item.object_id, None))

    # 3. Release held item
    if held is not None and drop_spot_clear(snapshot, body, held):
        out.append(("release", held.object_id, (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id, None))

    # 4. Toward every sensed food target, nearest first (the least strides to reach)
    if held is None:
        food = sorted((thing for thing in seen if thing.is_food and not nothing_left_to_bite(body, _object(snapshot, thing.object_id))),
                      key=lambda thing: (thing.distance_mm, thing.object_id))
        for item in food:
            stop = body.radius_mm + item.radius_mm + STOP_MARGIN_MM
            if item.distance_mm > stop + ARRIVAL_MM:
                out.append(("toward_food", item.object_id, move_commands_toward(snapshot, item.position, stop), item.object_id, None))

    # 5. Toward bed
    bed = next((thing for thing in seen if thing.object_id == BED_ID), None)
    if bed is not None and bed.distance_mm > ARRIVAL_MM + STEP_MM // 2:
        out.append(("toward_bed", "her bed", move_commands_toward(snapshot, bed.position, 0), bed.object_id, None))

    # 6. Toward every sensed thing, nearest first (the least strides to reach)
    things = sorted((thing for thing in seen if not thing.is_food), key=lambda thing: (thing.distance_mm, thing.object_id))
    for item in things:
        stop = body.radius_mm + item.radius_mm + (HANDLE_STOP_MM if held is None and handleable(_object(snapshot, item.object_id)) else WANDER_STOP_MM)
        if item.distance_mm > stop + ARRIVAL_MM:
            out.append(("toward_thing", item.object_id, move_commands_toward(snapshot, item.position, stop), item.object_id, None))

    # 6b. Toward the caregiver when seen; her palm to the caregiver's palm when near
    # enough for her reach (the world settles the geometry and refuses what it cannot).
    person = caregiver_in_sight(snapshot)
    if person is not None:
        if person.distance_mm > PERSON_STOP_MM + ARRIVAL_MM:
            out.append(("toward_person", person.object_id, move_commands_toward(snapshot, person.position, PERSON_STOP_MM), person.object_id, None))
        if held is None and person.distance_mm <= body.reach_mm + person.radius_mm:
            commands = tuple(
                BodySurfaceContactCommand((BodySurfaceActuation(actor_site_id=mine, recipient_body_id=person.object_id, recipient_site_id=theirs,
                                                                compression_micrometres=1_000, tangential_u_micrometres=0, tangential_v_micrometres=0),), BEAT_MICROSECONDS)
                for mine, theirs in REACH_SITES)
            out.append(("reach_hand", "her palm to the caregiver's hand", commands, person.object_id, None))

    # 7. Toward every door of her room
    here = _region_of(snapshot, position, body.radius_mm)
    if here is not None:
        doors = [item for item in snapshot.portals if here.region_id in item.region_ids]
        for portal in sorted(doors, key=lambda item: (_distance_mm(position, door_crossing(snapshot, item, here.region_id)[0]), item.portal_id)):
            before_door, _past = door_crossing(snapshot, portal, here.region_id)
            if _distance_mm(position, before_door) <= ARRIVAL_MM + STEP_MM // 2:
                out.append(("toward_door", "through " + portal.portal_id, door_crossing_commands(snapshot, portal, here.region_id), portal.portal_id, None))
            else:
                out.append(("toward_door", portal.portal_id, move_commands_toward(snapshot, before_door, 0), portal.portal_id, None))

    # 8. Elementary motions, airway, rest
    dx, dy = rotate_lattice_offset(STEP_MM, 0, heading)
    ahead = PositionMM(position.x + dx, position.y + dy, position.z)
    out.append(("step", "one stride ahead", (MoveCommand(PoseMM(ahead, heading), BEAT_MICROSECONDS),), None, None))
    for name, sign in (("turn_left", 1), ("turn_right", -1)):
        out.append((name, "", (MoveCommand(PoseMM(position, (heading + sign * TURN_MILLIDEGREES) % 360_000), BEAT_MICROSECONDS),), None, None))
    drive = say_drive if say_drive is not None else DEFAULT_DRIVE
    out.append(("say", say_detail, (), None, drive))
    out.append(("rest", "", (), None, None))

    assert len(out) <= MAX_CANDIDATES
    return out





class FunctionalOrganism:
    """One organism: bounded state, pure decisions, exact encoding."""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    # ----- genesis, restore, encode -------------------------------------------------

    @classmethod
    def genesis(cls, *, identity: str, organism_tick: int) -> "FunctionalOrganism":
        if not isinstance(identity, str) or not identity or isinstance(organism_tick, bool) or not isinstance(organism_tick, int) or organism_tick < 0:
            raise ValueError("functional organism genesis needs an identity and a tick")
        return cls({
            "schema": SCHEMA, "identity": identity, "tick": organism_tick,
            "reserve_micrograms": CAPACITY_MICROGRAMS * 55 // 100, "feeding": False,
            "streams": {name: [] for name in STREAMS},
            "familiarity": {}, "episodes": [], "heard": [], "voice": [],
            "refusals": {}, "last_act": "rest", "last_spoke_tick": -BABBLE_EVERY_BEATS,
            "pending_voice": None, "pending_drive": None, "meals_micrograms": 0, "bites": 0, "strides": 0, "syllables": 0,
            "voice_version": VOICE_VERSION, "ambient_sound": 0.0, "handled": 0, "room_now": None,
            "head": [0, 0], "acts": {}, "pending_act": None, "last_chosen": None,
            "sleep_pressure": 0, "asleep": False, "learned": {}, "nights": 0, "act_totals": {}, "contact_pressure": 0, "pending_contact": 0.0, "pending_contact_millikelvin": None, "reading_until_tick": 0,
            "target_totals": {}, "taste_residue": 0.0,
            "speech": {}, "syllable_totals": {}, "prior_syllable": None, "pending_syllable": None,
        })

    @classmethod
    def restore(cls, encoded: bytes) -> "FunctionalOrganism":
        if not isinstance(encoded, bytes) or not encoded.startswith(MAGIC):
            raise ValueError("encoded body is not a functional organism")
        state = json.loads(encoded[len(MAGIC):].decode("utf-8"))
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise ValueError("functional organism schema changed")
        organism = cls(state)
        if organism.encoded() != encoded:
            raise ValueError("functional organism body does not re-encode exactly")
        organism.migrate()
        return organism

    def migrate(self) -> bool:
        """Bring an older functional body to this build's laws; True when
        anything changed (the caller republishes)."""

        state = self._state
        changed = False
        if state.get("voice_version") != VOICE_VERSION:
            state["voice"], state["heard"], state["pending_voice"], state["pending_drive"] = [], [], None, None
            state["voice_version"] = VOICE_VERSION
            changed = True
        for key, empty in (("ambient_sound", 0.0), ("handled", 0), ("room_now", None), ("head", [0, 0]), ("acts", {}), ("pending_act", None), ("last_chosen", None),
                           ("sleep_pressure", 0), ("asleep", False), ("learned", {}), ("nights", 0), ("taste_residue", 0.0)):
            if key not in state:
                state[key] = empty
                changed = True
        for name in STREAMS:
            if name not in state["streams"]:
                state["streams"][name] = []
                changed = True
        for name in [name for name in state["streams"] if name not in STREAMS]:
            del state["streams"][name]  # a stream this build does not read (e.g. a blend of two others)
            changed = True
        # A record entry keyed under a retired key law can never be met again:
        # it is not her day's record. Drop it (idempotent: live entries match).
        stale = [k for k, entry in state.get("acts", {}).items() if entry.get("regimes") and choice_key(str(entry["regimes"])) != k]
        for k in stale:
            del state["acts"][k]
        changed = changed or bool(stale)
        if "act_totals" not in state:
            # Her lifetime tries per act, summed from the record she already has.
            totals: dict[str, int] = {}
            for entry in state.get("acts", {}).values():
                for act, (tries, _total) in entry.get("acts", {}).items():
                    totals[act] = totals.get(act, 0) + int(tries)
            state["act_totals"] = totals
            changed = True
        if "contact_pressure" not in state:
            state["contact_pressure"] = 0
            changed = True
        if "pending_contact" not in state:
            state["pending_contact"] = 0.0
            changed = True
        if "pending_contact_millikelvin" not in state:
            state["pending_contact_millikelvin"] = None
            changed = True
        if "reading_until_tick" not in state:
            state["reading_until_tick"] = 0
            changed = True
        if "target_totals" not in state:
            state["target_totals"] = {}
            changed = True
        if "speech" not in state:
            state["speech"] = {}
            changed = True
        if "syllable_totals" not in state:
            state["syllable_totals"] = {}
            changed = True
        if "prior_syllable" not in state:
            state["prior_syllable"] = None
            changed = True
        if "pending_syllable" not in state:
            state["pending_syllable"] = None
            changed = True
        for key in RETIRED_KEYS:
            if key in state:
                del state[key]
                changed = True
        return changed

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
    def body_axes(self) -> tuple[tuple[object, ...], ...]:
        """The declared axes, with the neck where her head law has turned it."""

        yaw, pitch = self.head
        aperture = 0 if self.asleep else EYELID_OPEN_MICROMETRES
        positions = {"neck_yaw": yaw, "neck_pitch": pitch, "left_eyelid_aperture": aperture, "right_eyelid_aperture": aperture}
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

        horizontal = self._state["streams"]["sight_horizontal"]
        vertical = self._state["streams"]["sight_vertical"]
        if not horizontal or not vertical:
            return None
        return float(horizontal[-1]), float(vertical[-1])

    @property
    def counts(self) -> dict[str, int]:
        counts = {key: int(self._state.get(key, 0)) for key in ("bites", "strides", "syllables", "meals_micrograms", "handled")}
        counts["structures"] = len(self._state.get("acts", {}))
        counts["learned"] = len(self._state.get("learned", {}))
        counts["nights"] = int(self._state.get("nights", 0))
        return counts

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
        for name in STREAMS:
            window = self._state["streams"][name]
            if len(window) < KERNEL_MINIMUM:
                tokens.append("________")
                continue
            sev = compute_sev_series(pd.DataFrame({"field": [STREAM_FLOOR + value for value in window]}), "field")
            gates = tuple(segment_gates(sev))
            build_gate_l1_state(sev, gates)
            l2 = tuple(interpret_gates(sev, gates))
            l4 = tuple(compute_dsf(compute_directional_signal(list(compute_resonance(l2)))))
            gates_total += len(gates)
            last = l4[-1]
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
        return " ".join(tokens), gates_total

    def decide(self, sensed: Sensed) -> Decision:
        state = self._state
        snapshot = sensed.snapshot
        body = _self_body(snapshot)
        seen = things_in_sight(snapshot)
        here = _region_of(snapshot, body.pose.position, body.radius_mm)
        state["room_now"] = None if here is None else here.region_id
        if sensed.wide_luminance_u8:
            state["head"] = list(head_step(self.head, tuple(sensed.wide_luminance_u8)))
        measures = self._measure(sensed, seen, body)
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
        if heard_now is not None:
            energy = sum(heard_now) / len(heard_now)
            if energy >= HEARD_ENERGY_FLOOR and energy >= ambient * HEARD_ABOVE_AMBIENT:
                sound_now = _clamp(energy * 4, 0.0, 1.0)
        self._settle(key, novel, sound_now, skin_now, tick, warmth_likeness=float(getattr(self, "_warmth_likeness", 0.0)), pain=float(getattr(self, "_pain", 0.0)))

        def decision(act: str, reason: str, commands: tuple[Any, ...] = (), target: str | None = None, drive: tuple[int, int, int] | None = None) -> Decision:
            return Decision(act, reason, commands, target, drive, signature, novel, gate_count, seen)

        if feeding:
            for item in (held, offered):
                if item is not None and _is_food(item) and not nothing_left_to_bite(body, item):
                    if item.material is not None and int(item.material.surface_temperature_millikelvin) >= NOCICEPTION_MILLIKELVIN:
                        continue   # too hot to bite: the jaw waits for it to cool (the mouth's reflex)
                    return decision("bite", "food at her mouth while feeding (the jaw's reflex)", (OralContactCommand(item.object_id, BEAT_MICROSECONDS),), item.object_id)
        pressure = int(state.get("sleep_pressure", 0))
        if state.get("asleep"):
            if pressure <= 0:
                state["asleep"], state["sleep_pressure"] = False, 0
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
                return decision("sleep", "falling asleep on her bed; pressure at its ceiling" if at_bed else "exhausted; asleep where she dropped")

        # Check if previous pending syllable got answered by environmental sound
        pending_syl = state.get("pending_syllable")
        if pending_syl is not None:
            if (sound_now > 0 or skin_now > 0) and tick - int(pending_syl.get("tick", 0)) <= ANSWER_WINDOW_BEATS:
                s_key = pending_syl["key"]
                s_name = pending_syl["syllable"]
                s_entry = state.setdefault("speech", {}).get(s_key)
                if s_entry is not None and s_name in s_entry.get("syllables", {}):
                    s_entry["syllables"][s_name][1] = int(s_entry["syllables"][s_name][1]) + 1
                state["pending_syllable"] = None
            elif tick - int(pending_syl.get("tick", 0)) > ANSWER_WINDOW_BEATS:
                state["pending_syllable"] = None

        # Voice: the syllable comes from her speech record (situation, prior syllable).
        last_spoke = int(state.get("last_spoke_tick", -999))
        prior_syl = state.get("prior_syllable") if (tick - last_spoke) <= PHRASE_WINDOW_BEATS else None
        say_drive, say_reason = self._choose_syllable(situation, prior_syl)

        if float(getattr(self, "_pain", 0.0)) > 0 and held is not None and held.material is not None \
                and int(held.material.surface_temperature_millikelvin) >= NOCICEPTION_MILLIKELVIN:
            state["pending_act"] = None
            return decision("release", "it burns; let go (the hand's reflex)", (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id)

        uncertain = any(len(t) >= 5 and t[4] == "+" for t in tokens)
        options = candidates(snapshot, body, held, offered, seen, tick, say_drive=say_drive, say_detail=say_reason)
        candidate_acts = list(dict.fromkeys(option[0] for option in options))
        act, why = self._choose(key, situation, candidate_acts, uncertain=uncertain)
        matching = [option for option in options if option[0] == act]
        target_totals = state.setdefault("target_totals", {})
        # Of the targets of the chosen kind, the one that costs the least to reach:
        # candidates of a kind are listed nearest first, and a move's burn is per
        # stride. (Spreading her over the targets by her counts sent each door move
        # toward a different door, and she never crossed one.) The counts stay as record.
        chosen_option = matching[0]
        if chosen_option[3] is not None:
            target_totals[chosen_option[3]] = int(target_totals.get(chosen_option[3], 0)) + 1
        _name, detail, commands, target, drive = chosen_option

        deficit = round(float(self.deficit), 6)
        sleep_ratio = round(float(state.get("sleep_pressure", 0)) / SLEEP_PRESSURE_CEILING, 6)
        contact_ratio = round(float(state.get("contact_pressure", 0)) / CONTACT_PRESSURE_CEILING, 6)
        state["pending_act"] = {"key": key, "regimes": regimes, "act": act, "deficit": deficit, "sleep_ratio": sleep_ratio, "contact_ratio": contact_ratio, "intake": 0, "refused": False}
        state["last_chosen"] = {"key": key, "regimes": regimes, "act": act, "deficit": deficit, "sleep_ratio": sleep_ratio}
        return decision(act, why + (("; " + detail) if detail else ""), commands, target, drive)

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

    def _dream(self, tick: int) -> str | None:
        """One sleeping beat of consolidation: the most recurrent structure of
        the day's record moves into her consolidated memory under its situation key;
        None when the day's record is empty."""

        state = self._state
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

    def _choose_syllable(
        self,
        situation: str,
        prior_syllable: str | None,
    ) -> tuple[tuple[int, int, int], str]:
        """Choose an airway syllable drive from her speech record:
        - Under (situation, prior_syllable): untried syllables come first ordered by her lifetime tries (never a clock formula or random hash).
        - When syllables have been tried, the one with the highest answer rate is chosen.
        - Speech transitions (prior_syllable -> next_syllable) grow syntax from reinforced answers."""

        context = f"{situation}:{prior_syllable if prior_syllable else 'start'}"
        speech = self._state.setdefault("speech", {})
        totals = self._state.setdefault("syllable_totals", {})
        entry = speech.get(context)

        if entry is None or not entry.get("syllables"):
            syl = min(SYLLABLES, key=lambda s: (int(totals.get(s, 0)), SYLLABLES.index(s)))
            return SYLLABLE_DRIVES[syl], f"first try of {syl} under {context} (tried {int(totals.get(syl, 0))} in her life)"

        tried = entry["syllables"]
        answered = [s for s, data in tried.items() if int(data[1]) > 0]
        if answered:
            syl = max(answered, key=lambda s: (float(tried[s][1]) / int(tried[s][0]), int(tried[s][1]), -int(totals.get(s, 0))))
            rate = float(tried[syl][1]) / int(tried[syl][0])
            return SYLLABLE_DRIVES[syl], f"best answered under {context}: {syl} ({rate:.2f} answered)"

        untried = [s for s in SYLLABLES if s not in tried]
        if untried:
            untried.sort(key=lambda s: (int(totals.get(s, 0)), SYLLABLES.index(s)))
            syl = untried[0]
            return SYLLABLE_DRIVES[syl], f"first try of {syl} under {context} (tried {int(totals.get(syl, 0))} in her life)"

        syl = min(SYLLABLES, key=lambda s: (int(tried[s][0]), SYLLABLES.index(s)))
        return SYLLABLE_DRIVES[syl], f"least tried under {context}: {syl}"

    def _choose(self, key: str, situation: str, acts: list[str], uncertain: bool | None = None) -> tuple[str, str]:
        """The act for this structure: from the day's record (untried first,
        the least tried under structural uncertainty U*_k > 0 or visit interval,
        otherwise the best by one-step predictive foresight); when the day's
        record has nothing for this structure, from what her sleep kept for
        this situation; else the first act in the declared order."""

        entry = self._state.setdefault("acts", {}).get(key)
        label = "structure " + key[:6]
        if entry is None:
            learned = self._state.setdefault("learned", {}).get(situation)
            known = [act for act in acts if learned is not None and act in learned["acts"]]
            if known:
                tried = learned["acts"]
                act = max(known, key=lambda a: (float(tried[a][1]) / int(tried[a][0]), -acts.index(a)))
                mean = float(tried[act][1]) / int(tried[act][0])
                return act, label + ", new today; from her sleep, situation " + situation + ": " + act + f" ({mean:+.2f} over {int(tried[act][0])})"
            # Nothing known here or in her sleep: the act she has tried least in
            # her whole life (her own counts, never a written order).
            totals = self._state.get("act_totals", {})
            act = min(acts, key=lambda a: (int(totals.get(a, 0)), acts.index(a)))
            return act, label + ": first try of " + act + f" (tried {int(totals.get(act, 0))} times in her life)"

        tried = entry["acts"]
        untried = [act for act in acts if act not in tried]
        if untried:
            # Among the acts not yet tried under this structure, the one she has
            # tried least in her whole life comes first (her own counts, not a
            # written order): a fixed order sent her round grasp and release
            # forever, each flipping what her eye saw into a "new" structure.
            totals = self._state.get("act_totals", {})
            untried.sort(key=lambda a: (int(totals.get(a, 0)), acts.index(a)))
            return untried[0], label + ": first try of " + untried[0] + f" (tried {int(totals.get(untried[0], 0))} times in her life)"

        visits = sum(int(tried[act][0]) for act in acts)
        if uncertain is True:
            act = min(acts, key=lambda a: (int(tried[a][0]), acts.index(a)))
            return act, label + ": least tried, " + act
        elif uncertain is None and visits % EXPLORE_EVERY == 0:
            act = min(acts, key=lambda a: (int(tried[a][0]), acts.index(a)))
            return act, label + ": least tried, " + act

        # One-step predictive foresight through recorded successors
        def _score(a: str) -> float:
            tries = int(tried[a][0])
            mean_immediate = float(tried[a][1]) / tries if tries > 0 else 0.0
            successors = entry.get("successors", {}).get(a, {})
            v_next = 0.0
            if successors:
                dominant_next = max(successors, key=lambda s: (int(successors[s]), s))
                next_entry = self._state.setdefault("acts", {}).get(dominant_next)
                if next_entry and next_entry.get("acts"):
                    next_means = [float(t[1]) / int(t[0]) for t in next_entry["acts"].values() if int(t[0]) > 0]
                    if next_means:
                        v_next = max(next_means)
            return mean_immediate + 0.5 * v_next

        act = max(acts, key=lambda a: (_score(a), -acts.index(a)))
        mean = float(tried[act][1]) / int(tried[act][0])
        return act, label + ": best so far, " + act + f" ({mean:+.2f} over {int(tried[act][0])})"

    # ----- commit: what the world allowed, what she took in, what she said ------------

    def commit(self, decision: Decision, *, applied_action: str, refusal: str | None,
               intake_micrograms: int, spoke: bytes | None, heard_profile: tuple[float, ...] | None,
               self_profile: tuple[float, ...] | None, tick_now: int, contact_fraction: float = 0.0,
               contact_millikelvin: int | None = None) -> None:
        state = self._state
        if tick_now != self.live_organism_tick:
            raise RuntimeError("functional organism tick left its line")
        # Skin on skin by her own act (her palm on the caregiver's hand) is felt on the next beat, at its temperature.
        reached = applied_action == "reach_hand" and refusal is None
        state["pending_contact"] = round(float(contact_fraction), 6) if reached else 0.0
        state["pending_contact_millikelvin"] = int(contact_millikelvin) if (reached and contact_millikelvin is not None) else None
        before = self.reserve_micrograms
        burn = BASAL_BURN_MICROGRAMS * (1 + ACT_BURN_MULTIPLE.get(decision.act, 1)) if applied_action != "refused" else BASAL_BURN_MICROGRAMS
        intake = max(0, min(int(intake_micrograms), CAPACITY_MICROGRAMS - before))
        reserve = max(0, before - burn) + intake
        state["reserve_micrograms"] = min(CAPACITY_MICROGRAMS, reserve)
        state["feeding"] = (state["feeding"] or before < CAPACITY_MICROGRAMS * HUNGRY_BELOW) and state["reserve_micrograms"] < CAPACITY_MICROGRAMS * SATED_ABOVE
        if intake:
            state["meals_micrograms"] += intake
            state["bites"] += 1
            state["taste_residue"] = min(1.0, float(state.get("taste_residue", 0.0)) + intake / 100_000.0)
        state["taste_residue"] = round(float(state.get("taste_residue", 0.0)) * 0.95, 6)

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
        if applied_action in MOVES and refusal is None:
            state["strides"] += 1
        if applied_action in ("grasp", "take") and refusal is None:
            state["handled"] = int(state.get("handled", 0)) + 1
        if refusal is not None:
            refusals = state["refusals"]
            refusals[refusal] = int(refusals.get(refusal, 0)) + 1
            while len(refusals) > REFUSAL_CAPACITY:
                del refusals[min(refusals, key=lambda k: int(refusals[k]))]
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
            syl_data = ctx_entry["syllables"].setdefault(syl_name, [0, 0])
            syl_data[0] = int(syl_data[0]) + 1
            state["pending_syllable"] = {"key": ctx_key, "syllable": syl_name, "tick": tick_now}
            state["prior_syllable"] = syl_name
            while len(speech_rec) > SPEECH_RECORD_CAPACITY:
                del speech_rec[min(speech_rec, key=lambda k: (int(speech_rec[k].get("tick", 0)), k))]
        state["last_act"] = decision.act
        state["tick"] = tick_now + 1


__all__ = (
    "BODY_AXES", "CAPACITY_MICROGRAMS", "Decision", "FunctionalOrganism", "MAGIC", "SCHEMA", "Sensed",
    "SeenThing", "SYLLABLES", "SYLLABLE_DRIVES", "cochlear_profile", "in_hand_reach", "move_commands_toward",
    "syllable_pcm", "things_in_sight",
)
