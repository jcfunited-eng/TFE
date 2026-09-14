"""The functional organism (Joe, 2026-09-14): no neurons, no charge, no muscles.

Her senses come in as measured streams; the DSF-AI kernel (uf_core L0-L4)
reads the structure of those streams every beat; a bounded memory keeps what
structures she has met, what she did, and what her own voice sounds like; her
acts are declared laws over her own measured state, issued straight to the
world. Everything here is a function of her state; nothing is scripted
meaning and nothing speaks for her.

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
    GraspContactCommand, MoveCommand, OralContactCommand, PoseMM, PositionMM,
    ReleaseHeldObjectCommand, TakeContactHeldObjectCommand, TouchContactCommand, _derived_contact_patch_square_mm, _receptor_position,
)


SCHEMA = "guala.functional_organism.v1"
MAGIC = b"GLFUNC01"
BEAT_MICROSECONDS = 250_000

# Metabolism: her reserve is matter she has eaten, in micrograms at the world's
# declared tastant masses (one apple is 167,400 micrograms). A full reserve is
# three apples; the basal burn empties it in 28,800 beats (two hours at four
# beats a second); acts cost multiples of the basal burn.
CAPACITY_MICROGRAMS = 500_000
BASAL_BURN_MICROGRAMS = 17
ACT_BURN_MULTIPLE = {
    "rest": 0, "attend": 0, "listen": 0, "bite": 2, "grasp": 2, "take": 2, "release": 1, "turn": 1, "touch": 1,
    "approach": 4, "wander": 4, "babble": 2, "imitate": 2,
}
HUNGRY_BELOW = Fraction(3, 5)   # feeding starts below 60 percent of capacity
SATED_ABOVE = Fraction(17, 20)  # feeding ends at 85 percent (one apple from hungry)

# Sight: what her eyes can resolve as a thing — within her field of view and
# range, on the floor of her own room.
FIELD_OF_VIEW_MILLIDEGREES = 60_000
SIGHT_RANGE_MM = 4_000
FOCAL_COLUMNS = 32
FOCAL_ROWS = 24
STRUCTURE_FLOOR = 768 * 4   # total edge energy below this (about four levels per site) is a flat field
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

# Steps: one stride per beat; she stops a hand's margin short of a thing.
STEP_MM = 300
STOP_MARGIN_MM = 50
WANDER_STOP_MM = 400
ARRIVAL_MM = 20
GOAL_PATIENCE_BEATS = 40
SIDESTEP_MILLIDEGREES = (45_000, -45_000, 90_000, -90_000, 135_000, -135_000, 180_000)
GOAL_REFUSAL_LIMIT = 6
TURN_MILLIDEGREES = 60_000
# Roaming: once everything in sight was looked at within this many beats, she
# leaves through the doorway to the room she visited least recently; the
# doorway is crossed in one step from a margin before it to a margin past it.
# Handling: a thing light enough and small enough to pick up is touched when
# her hand reaches it, then picked up, carried a while and set down somewhere
# else; what she has handled is known for a time and not handled again.
HANDLE_MASS_GRAMS = 2_000
HANDLE_RADIUS_MM = 300
HANDLE_STOP_MM = 150       # how far short of a thing she stops to reach it with her hand
CARRY_STRIDES = 12
DROP_MARGIN_MM = 60
# Her keeping place: the room she has spent the most beats in over her life.
# A thing she picks up is carried there and set down beside the last thing
# she kept; if the walk takes too long she sets it down where she is.
STUCK_BEATS = 8            # two seconds of every step refused: she is walled in
ROOM_BEATS_CAPACITY = 16
KEEP_WALK_PATIENCE_BEATS = 160
KEEP_BESIDE_MM = 450
TOUCHED_MEMORY_BEATS = 1_200
TOUCHED_CAPACITY = 64
PROGRESS_MM = 40           # a stride that brings her at least this much closer counts as progress
FOOD_STALL_BEATS = 12      # three seconds without progress toward food, and she leaves it for a while
ATTEND_REFRACTORY_BEATS = 8   # after pausing on something new, she does not pause again for two seconds
LOOKED_RECENTLY_BEATS = 240
DOOR_MARGIN_MM = 600
DOOR_CROSSING_OFFSETS_MM = (0, 300, -300, 500, -500)
VISITED_CAPACITY = 16
BLOCKED_DOOR_BEATS = 400   # a doorway she could not pass is left alone for this long

# The kernel reads a trailing window of each measured stream.
STREAMS = (
    "sight_luminance", "sight_horizontal", "sight_vertical", "sound_energy",
    "sound_pitch", "hunger", "food_distance", "heading", "hand",
)
KERNEL_WINDOW = 64
KERNEL_MINIMUM = 24
STREAM_FLOOR = 0.05

# Memory bounds.
FAMILIARITY_CAPACITY = 512
EPISODE_CAPACITY = 64
HEARD_CAPACITY = 8
VOICE_CAPACITY = 16
APPROACHED_CAPACITY = 64
REFUSAL_CAPACITY = 32

# Voice: one syllable through her airway, at most one every four beats; she
# imitates a sound heard within the last eight beats.
BABBLE_EVERY_BEATS = 4
IDLE_BEFORE_BABBLE = 2
HEARD_RECENT_BEATS = 8
# Babble comes in bouts, walking or still: up to this many syllables one
# every four beats, then a quiet spell. A heard sound is answered once.
BOUT_SYLLABLES = 5
QUIET_BEATS = 48
# Turn-taking: while a sound stands out she listens (stands still); when it
# ends she answers with a short bout. For each kind of sound she keeps the
# answer whose self-heard result landed nearest to it, trying a neighbouring
# sound every other time and keeping whichever did better.
LISTEN_CAP_BEATS = 24
ANSWER_BOUT_SYLLABLES = 3
ANSWER_MAP_CAPACITY = 32
FOOD_ROOMS_CAPACITY = 8
HEARD_ENERGY_FLOOR = 0.004      # below this mean cochlear envelope, a sound is room noise
HEARD_ABOVE_AMBIENT = 2.0       # a sound worth answering is at least twice the running ambient level
SAME_SOUND_DISTANCE = 0.08      # closer than this to the last answered profile is the same sound
AMBIENT_MEMORY = Fraction(15, 16)
COCHLEAR_CHANNELS = 32
# Her airway is the accepted voice (guala_voice); a drive is (pitch in tenths
# of a hertz, vowel, onset). Sound memory made with an older airway is
# forgotten on restore, because it no longer sounds like her.
VOICE_VERSION = 2

# Her body's axes, declared once (index, name, unit, position, minimum,
# neutral, maximum). The eyelids sit where they sat; the head faces forward.
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
    # The world eye's wide field (18 x 6 sites, carried by her head), which aims
    # her head; empty when the loop has none.
    wide_luminance_u8: tuple[int, ...] = ()


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
    # Half the way each beat (the wide field's coarse sites shift the measured
    # height as the head moves; a full step overshot and rocked five degrees).
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

    from dsf_ai_service.substrate.embodiment_world import RELEASE_CLEARANCE_MM, rotate_lattice_offset

    dx, dy = rotate_lattice_offset(max(body.radius_mm, item.radius_mm) + item.radius_mm + RELEASE_CLEARANCE_MM, 0, body.pose.heading_millidegrees)
    spot = PositionMM(body.pose.position.x + dx, body.pose.position.y + dy, 0)
    if _region_of(snapshot, spot, item.radius_mm) is None:
        return False
    for other in snapshot.objects:
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


def _profile_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    left_peak = max(max(left), 1e-9)
    right_peak = max(max(right), 1e-9)
    return sum((a / left_peak - b / right_peak) ** 2 for a, b in zip(left, right, strict=True))


def heard_key(profile: tuple[float, ...]) -> str:
    """A coarse name for a kind of sound: its loudest ear channel (in
    groups of four) and its loudness band."""

    peak = max(range(len(profile)), key=lambda index: profile[index])
    energy = sum(profile) / len(profile)
    band = 0
    level = HEARD_ENERGY_FLOOR
    while energy > level * 2 and band < 4:
        level *= 2
        band += 1
    return f"c{peak // 4}b{band}"


def neighbour_drive(drive: tuple[int, int, int], tries: int) -> tuple[int, int, int]:
    """A sound one step away from ``drive``: the pitch or the vowel moved
    by one, chosen by how many times this sound was tried."""

    pitch, vowel, onset = drive
    which = tries % 4
    if which == 0:
        index = PITCHES_DECIHERTZ.index(pitch)
        return PITCHES_DECIHERTZ[min(len(PITCHES_DECIHERTZ) - 1, index + 1)], vowel, onset
    if which == 1:
        return pitch, (vowel + 1) % len(VOWELS), onset
    if which == 2:
        index = PITCHES_DECIHERTZ.index(pitch)
        return PITCHES_DECIHERTZ[max(0, index - 1)], vowel, onset
    return pitch, (vowel - 1) % len(VOWELS), (onset + 1) % len(ONSETS)


def _new_drive(tick: int) -> tuple[int, int, int]:
    """A sound of her own she has not tried lately: vowel, onset and pitch
    walked in turn from her tick."""

    vowel = tick % len(VOWELS)
    onset = (tick // len(VOWELS)) % len(ONSETS)
    pitch = PITCHES_DECIHERTZ[(tick // (len(VOWELS) * len(ONSETS))) % len(PITCHES_DECIHERTZ)]
    return pitch, vowel, onset


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
            "familiarity": {}, "episodes": [], "heard": [], "voice": [], "approached": {},
            "refusals": {}, "idle_beats": 0, "last_act": "rest", "last_spoke_tick": -BABBLE_EVERY_BEATS, "goal": None, "goal_beats": 0, "goal_refusals": 0,
            "pending_voice": None, "pending_drive": None, "meals_micrograms": 0, "bites": 0, "strides": 0, "syllables": 0,
            "voice_version": VOICE_VERSION, "visited": {}, "door_goal": None, "bout_syllables": 0, "quiet_until_tick": 0, "blocked_doors": {}, "attended_tick": -ATTEND_REFRACTORY_BEATS - 1, "unreachable_food": {}, "food_goal": None, "food_refusals": 0, "food_best_mm": 0, "food_stall_beats": 0, "ambient_sound": 0.0, "answered_profile": None, "touched": {}, "strides_since_pickup": 0, "handled": 0, "release_refusals": 0, "touching": None,
            "listening_since": None, "call_profile": None, "answer_bout": 0, "answer_target": None, "answer_pending": None, "answer_map": {}, "food_rooms": {}, "food_room_goal": None, "room_now": None,
            "room_beats": {}, "keeping_room": None, "keep_walk_beats": 0, "last_kept": None, "kept": 0, "stuck_beats": 0,
            "head": [0, 0],
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
        for key, empty in (("visited", {}), ("door_goal", None), ("bout_syllables", 0), ("quiet_until_tick", 0), ("blocked_doors", {}), ("attended_tick", -ATTEND_REFRACTORY_BEATS - 1), ("unreachable_food", {}), ("food_goal", None), ("food_refusals", 0), ("food_best_mm", 0), ("food_stall_beats", 0), ("ambient_sound", 0.0), ("answered_profile", None), ("touched", {}), ("strides_since_pickup", 0), ("handled", 0), ("release_refusals", 0), ("touching", None),
                           ("listening_since", None), ("call_profile", None), ("answer_bout", 0), ("answer_target", None), ("answer_pending", None), ("answer_map", {}), ("food_rooms", {}), ("food_room_goal", None), ("room_now", None),
                           ("room_beats", {}), ("keeping_room", None), ("keep_walk_beats", 0), ("last_kept", None), ("kept", 0), ("stuck_beats", 0),
                           ("head", [0, 0])):
            if key not in state:
                state[key] = empty
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
        return tuple(
            (axis[0], axis[1], axis[2], yaw if axis[1] == "neck_yaw" else pitch, *axis[4:])
            if axis[1] in ("neck_yaw", "neck_pitch") else axis
            for axis in BODY_AXES
        )

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
        counts["answers_known"] = len(self._state.get("answer_map", {}))
        counts["kept"] = int(self._state.get("kept", 0))
        return counts

    # ----- the kernel over her measured streams --------------------------------------

    def _measure(self, sensed: Sensed, seen: tuple[SeenThing, ...], body: Any) -> dict[str, float]:
        focal = sensed.focal_luminance_u8
        total = sum(focal)
        # Where her gaze goes: the centre of STRUCTURE in the field (where
        # luminance changes between neighbouring sites), not of brightness.
        # A flat bright ceiling has no edges and holds no gaze; with too
        # little structure anywhere the gaze rests at the centre.
        horizontal, vertical = structure_centre(focal)
        heard = sensed.heard_profile
        if heard is not None and sum(heard) > 0:
            energy = sum(heard) / len(heard)
            pitch = sum(value * index for index, value in enumerate(heard)) / (sum(heard) * (len(heard) - 1))
        else:
            energy, pitch = 0.0, 0.5
        food = [thing for thing in seen if thing.is_food]
        return {
            "sight_luminance": (total / len(focal) / 255) if focal else 0.0,
            "sight_horizontal": horizontal, "sight_vertical": vertical,
            "sound_energy": _clamp(energy * 4, 0.0, 1.0), "sound_pitch": pitch,
            "hunger": float(self.deficit),
            "food_distance": (food[0].distance_mm / SIGHT_RANGE_MM) if food else 1.0,
            "heading": body.pose.heading_millidegrees / 360_000,
            "hand": 1.0 if body.held_object_id is not None else 0.0,
        }

    def _kernel(self) -> tuple[str, int]:
        """Run L0-L4 over every stream's trailing window; the signature is the
        last gate's regime and the signs of its directional, momentum and
        pressure fields, per stream. Returns (signature, gates delivered)."""

        tokens = []
        gates_total = 0
        for name in STREAMS:
            window = self._state["streams"][name]
            if len(window) < KERNEL_MINIMUM:
                tokens.append("____")
                continue
            sev = compute_sev_series(pd.DataFrame({"field": [STREAM_FLOOR + value for value in window]}), "field")
            gates = tuple(segment_gates(sev))
            build_gate_l1_state(sev, gates)
            l2 = tuple(interpret_gates(sev, gates))
            l4 = tuple(compute_dsf(compute_directional_signal(list(compute_resonance(l2)))))
            gates_total += len(gates)
            last = l4[-1]
            tokens.append(l2[-1].regime[0] + _sign(last.D_k) + _sign(last.M_k) + _sign(last.P_k))
        return " ".join(tokens), gates_total

    # ----- decide ---------------------------------------------------------------------

    def decide(self, sensed: Sensed) -> Decision:
        state = self._state
        snapshot = sensed.snapshot
        body = _self_body(snapshot)
        seen = things_in_sight(snapshot)
        # Where she is: the room she stands in; the room she has spent the most
        # beats in over her life is her keeping place.
        here = _region_of(snapshot, body.pose.position, body.radius_mm)
        state["room_now"] = None if here is None else here.region_id
        room_beats = state.setdefault("room_beats", {})
        if here is not None:
            room_beats[here.region_id] = int(room_beats.get(here.region_id, 0)) + 1
            while len(room_beats) > ROOM_BEATS_CAPACITY:
                del room_beats[min(room_beats, key=lambda k: int(room_beats[k]))]
        keeping_room = max(room_beats, key=lambda k: int(room_beats[k])) if room_beats else None
        state["keeping_room"] = keeping_room
        # Her head turns toward structure in the wide field it carries; the
        # world computes the next beat's eye from these axes.
        if sensed.wide_luminance_u8:
            state["head"] = list(head_step(self.head, tuple(sensed.wide_luminance_u8)))
        measures = self._measure(sensed, seen, body)
        for name in STREAMS:
            window = state["streams"][name]
            window.append(round(measures[name], 6))
            del window[:-KERNEL_WINDOW]
        signature, gate_count = self._kernel()
        # Familiarity is kept over the coarse structure (each stream's regime);
        # the full signature with its field signs goes into the episode record.
        key = _sha256(" ".join(token[0] for token in signature.split(" ")).encode("utf-8"))[:16]
        tick = self.live_organism_tick
        novel = key not in state["familiarity"] and tick - int(state.get("attended_tick", -ATTEND_REFRACTORY_BEATS - 1)) > ATTEND_REFRACTORY_BEATS

        feeding = state["feeding"] or self.reserve_micrograms < CAPACITY_MICROGRAMS * HUNGRY_BELOW
        if self.reserve_micrograms >= CAPACITY_MICROGRAMS * SATED_ABOVE:
            feeding = False
        held = None if body.held_object_id is None else _object(snapshot, body.held_object_id)
        offered_id = offered_within_reach(snapshot)
        offered = None if offered_id is None else _object(snapshot, offered_id)

        # Her voice, decided on its own and carried by whatever her body does
        # this beat (not while her mouth is busy eating). A sound that stands
        # out from the room is listened to (she stands still); when it ends
        # she answers with a short bout, using for that kind of sound the
        # answer that has landed nearest so far, trying a neighbour every
        # other time. Otherwise she babbles in bouts, walking or still.
        voice_drive = None
        voice_reason = ""
        spoke_recently = tick - int(state["last_spoke_tick"]) < BABBLE_EVERY_BEATS
        in_quiet_spell = tick < int(state.get("quiet_until_tick", 0))
        ambient = float(state.get("ambient_sound", 0.0))
        heard_now = sensed.heard_profile
        call_now = False
        if heard_now is not None:
            energy = sum(heard_now) / len(heard_now)
            call_now = energy >= HEARD_ENERGY_FLOOR and energy >= ambient * HEARD_ABOVE_AMBIENT
        listening_since = state.get("listening_since")
        answer_map = state.setdefault("answer_map", {})
        if call_now and (listening_since is None or tick - int(listening_since) < LISTEN_CAP_BEATS):
            if listening_since is None:
                state["listening_since"] = tick
            state["call_profile"] = list(heard_now)
            listening = True
        else:
            listening = False
            if listening_since is not None and state.get("call_profile") is not None:
                # The call ended: answer it.
                state["answer_bout"] = ANSWER_BOUT_SYLLABLES
                state["answer_target"] = state["call_profile"]
            state["listening_since"] = None
            state["call_profile"] = None
        if not listening and int(state.get("answer_bout", 0)) > 0 and not spoke_recently and state["voice"]:
            target_profile = tuple(state["answer_target"])
            key = heard_key(target_profile)
            known = answer_map.get(key)
            if known is None:
                best = min(state["voice"], key=lambda entry: _profile_distance(tuple(entry["heard"]), target_profile))
                voice_drive = tuple(best["drive"])
                voice_reason = "answering a sound she heard with the nearest sound of her own"
            elif int(known["tries"]) % 2 == 1:
                voice_drive = neighbour_drive(tuple(known["drive"]), int(known["tries"]))
                voice_reason = "answering a sound she heard; trying a sound one step away from her usual answer"
            else:
                voice_drive = tuple(known["drive"])
                voice_reason = "answering a sound she heard with her best answer so far"
            state["answer_bout"] = int(state["answer_bout"]) - 1
            state["answer_pending"] = {"key": key, "drive": list(voice_drive), "target": list(target_profile)}
        elif not listening and not spoke_recently and not in_quiet_spell and int(state.get("answer_bout", 0)) == 0:
            voice_drive, voice_reason = _new_drive(tick), "trying a sound of her own"
        if voice_drive is not None:
            state["bout_syllables"] = int(state.get("bout_syllables", 0)) + 1
            if int(state["bout_syllables"]) >= BOUT_SYLLABLES:
                state["bout_syllables"], state["quiet_until_tick"] = 0, tick + QUIET_BEATS
        for entry in state["heard"]:
            entry["answered"] = True  # the call itself is what she answers now; nothing else is imitated
        unanswered = []

        def decision(act: str, reason: str, commands: tuple[Any, ...] = (), target: str | None = None, drive: tuple[int, int, int] | None = None) -> Decision:
            if drive is None and voice_drive is not None and act in ("rest", "attend", "turn", "wander"):
                if act == "rest":
                    act, reason = ("imitate" if "answering" in voice_reason else "babble"), voice_reason
                else:
                    reason = reason + "; " + voice_reason
                drive = voice_drive
            return Decision(act, reason, commands, target, drive, signature, novel, gate_count, seen)

        # Listening: a sound that stands out holds her still while it lasts
        # (unless she is eating); it is answered when it ends.
        if listening and not (feeding and (held is not None or offered is not None)):
            return Decision("listen", "listening to a sound", (), None, None, signature, novel, gate_count, seen)

        # An eaten core in her hand is dropped whether or not she is hungry.
        if held is not None and (held.material is None or nothing_left_to_bite(body, held)):
            return decision("release", "the thing in her hand has nothing left to bite", (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id)
        if feeding:
            if held is not None and _is_food(held):
                return decision("bite", "hungry, food in her own hand", (OralContactCommand(held.object_id, BEAT_MICROSECONDS),), held.object_id)
            if offered is not None and _is_food(offered) and not nothing_left_to_bite(body, offered):
                return decision("bite", "hungry, food held out to her", (OralContactCommand(offered.object_id, BEAT_MICROSECONDS),), offered.object_id)
            if held is None:
                reachable = [item for item in snapshot.objects if _is_food(item) and item.position is not None and not nothing_left_to_bite(body, item) and in_hand_reach(snapshot, item)]
                if len(reachable) == 1:
                    return decision("grasp", "hungry, food within her hand's reach", (GraspContactCommand(BEAT_MICROSECONDS),), reachable[0].object_id)
                # Food she could not get to (every stride refused) is left alone
                # for a while, so a boxed-in apple does not hold her in place.
                unreachable = state.setdefault("unreachable_food", {})
                food = [thing for thing in seen if thing.is_food and not nothing_left_to_bite(body, _object(snapshot, thing.object_id))
                        and tick - int(unreachable.get(thing.object_id, -BLOCKED_DOOR_BEATS - 1)) > BLOCKED_DOOR_BEATS]
                if food:
                    nearest = food[0]
                    stop = body.radius_mm + nearest.radius_mm + STOP_MARGIN_MM
                    # Progress toward the food is measured; sidesteps that only
                    # circle it are not progress. No progress for a while, or
                    # every stride refused, and the food is left alone.
                    if state.get("food_goal") != nearest.object_id:
                        state["food_goal"], state["food_refusals"] = nearest.object_id, 0
                        state["food_best_mm"], state["food_stall_beats"] = int(nearest.distance_mm), 0
                    elif nearest.distance_mm < int(state.get("food_best_mm", 1 << 30)) - PROGRESS_MM:
                        state["food_best_mm"], state["food_stall_beats"] = int(nearest.distance_mm), 0
                    else:
                        state["food_stall_beats"] = int(state.get("food_stall_beats", 0)) + 1
                    if int(state["food_stall_beats"]) >= FOOD_STALL_BEATS:
                        unreachable[nearest.object_id] = tick
                        while len(unreachable) > VISITED_CAPACITY:
                            del unreachable[min(unreachable, key=lambda k: int(unreachable[k]))]
                        state["food_goal"], state["food_stall_beats"] = None, 0
                    else:
                        return decision("approach", "hungry, food in sight", move_commands_toward(snapshot, nearest.position, stop), nearest.object_id)
        # Handling: carry what she picked up for a while, then set it down;
        # touch, then pick up, a light thing her hand reaches that she has
        # not handled lately.
        touched = state.setdefault("touched", {})
        if held is not None and not _is_food(held):
            carried = int(state.get("strides_since_pickup", 0))
            keep_beats = int(state.get("keep_walk_beats", 0))
            state["keep_walk_beats"] = keep_beats + 1
            at_keeping_room = here is not None and keeping_room is not None and here.region_id == keeping_room
            last_kept = state.get("last_kept")
            beside = (
                last_kept is not None and last_kept.get("room") == keeping_room
                and _object(snapshot, last_kept["object_id"]) is not None and _object(snapshot, last_kept["object_id"]).position is not None
            )
            settle_here = keep_beats >= KEEP_WALK_PATIENCE_BEATS or keeping_room is None
            if not settle_here and not at_keeping_room and here is not None:
                # Carry it to her keeping place: through the doorway on the way there.
                route = _portal_route(snapshot, here.region_id, keeping_room)
                blocked = state.get("blocked_doors", {})
                if route and tick - int(blocked.get(route[0].portal_id, -BLOCKED_DOOR_BEATS - 1)) > BLOCKED_DOOR_BEATS:
                    portal = route[0]
                    before_door, past_door = door_crossing(snapshot, portal, here.region_id)
                    why = "carrying " + held.object_id + " to " + keeping_room + ", where she keeps things; going through " + portal.portal_id
                    if _distance_mm(body.pose.position, before_door) <= ARRIVAL_MM + STEP_MM // 2:
                        return decision("wander", why, door_crossing_commands(snapshot, portal, here.region_id), held.object_id)
                    return decision("wander", why, move_commands_toward(snapshot, before_door, 0), held.object_id)
                settle_here = True
            if not settle_here and at_keeping_room and beside:
                kept = _object(snapshot, last_kept["object_id"])
                if _distance_mm(body.pose.position, kept.position) > body.radius_mm + kept.radius_mm + KEEP_BESIDE_MM + ARRIVAL_MM:
                    return decision("wander", "carrying " + held.object_id + " to where she keeps things, beside " + kept.object_id, move_commands_toward(snapshot, kept.position, body.radius_mm + kept.radius_mm + KEEP_BESIDE_MM), held.object_id)
            if settle_here or at_keeping_room or carried >= CARRY_STRIDES:
                # Set it down where the floor ahead is clear; otherwise turn
                # a little and look again next beat.
                why = ("keeping " + held.object_id + " in " + keeping_room) if (at_keeping_room and keeping_room) else ("setting down " + held.object_id + " after carrying it")
                if drop_spot_clear(snapshot, body, held) and int(state.get("release_refusals", 0)) == 0:
                    return decision("release", why, (ReleaseHeldObjectCommand(BEAT_MICROSECONDS),), held.object_id)
                state["release_refusals"] = 0
                heading = (body.pose.heading_millidegrees + TURN_MILLIDEGREES) % 360_000
                return decision("turn", "looking for a clear place to set down " + held.object_id, (MoveCommand(PoseMM(body.pose.position, heading), BEAT_MICROSECONDS),), held.object_id)
        elif held is None and int(state.get("stuck_beats", 0)) >= STUCK_BEATS:
            # Walled in by things on the floor: pick up the nearest light
            # thing within reach to open a way, and carry it on.
            blockers = [item for item in snapshot.objects if handleable(item) and in_hand_reach(snapshot, item)]
            if blockers:
                reachable = [thing for thing in snapshot.objects if thing.position is not None and in_hand_reach(snapshot, thing)]
                item = min(blockers, key=lambda thing: _distance_mm(body.pose.position, thing.position))
                if len(reachable) == 1:
                    state["stuck_beats"] = 0
                    return decision("grasp", "clearing a way: picking up " + item.object_id, (GraspContactCommand(BEAT_MICROSECONDS),), item.object_id)
                heading = (body.pose.heading_millidegrees + TURN_MILLIDEGREES) % 360_000
                return decision("turn", "walled in; turning to find one thing to pick up", (MoveCommand(PoseMM(body.pose.position, heading), BEAT_MICROSECONDS),))
        elif held is None and not feeding:
            # Something held out to her that is not food: she takes it from
            # the caregiver's hand (the world's hand-to-hand law).
            if offered is not None and not _is_food(offered) and handleable_held(offered):
                return decision("take", "taking " + offered.object_id + " from the caregiver's hand", (TakeContactHeldObjectCommand(BEAT_MICROSECONDS),), offered.object_id)
            # What she felt with her own touch last beat (a set-down also
            # leaves a hand contact in the world; that is not a feel).
            under_hand = state.get("touching")
            fresh = [item for item in snapshot.objects if handleable(item) and in_hand_reach(snapshot, item)
                     and (item.object_id == under_hand
                          or tick - int(touched.get(item.object_id, -TOUCHED_MEMORY_BEATS - 1)) > TOUCHED_MEMORY_BEATS)]
            if fresh:
                item = min(fresh, key=lambda thing: (thing.object_id != under_hand, _distance_mm(body.pose.position, thing.position)))
                touched_now = item.object_id == under_hand
                if item.material is not None and not touched_now:
                    return decision("touch", "feeling " + item.object_id, (TouchContactCommand(item.object_id, BEAT_MICROSECONDS),), item.object_id)
                reachable = [thing for thing in snapshot.objects if thing.position is not None and in_hand_reach(snapshot, thing)]
                if len(reachable) == 1:
                    return decision("grasp", "picking up " + item.object_id, (GraspContactCommand(BEAT_MICROSECONDS),), item.object_id)
                touched[item.object_id] = tick  # too crowded to grasp it cleanly; known by touch
        if novel and gate_count:
            state["attended_tick"] = tick
            return decision("attend", "a structure she has not met before")
        # Where she is: the room she stands in, remembered as visited now.
        visited = state["visited"]
        if here is not None:
            visited[here.region_id] = tick
            while len(visited) > VISITED_CAPACITY:
                del visited[min(visited, key=lambda k: int(visited[k]))]
        # A doorway she is on her way through: first the margin before it,
        # then one step past it into the next room.
        door_goal = state.get("door_goal")
        if door_goal is not None and here is not None:
            portal = next((item for item in snapshot.portals if item.portal_id == door_goal["portal_id"]), None)
            if portal is None or here.region_id not in portal.region_ids or int(state.get("goal_beats", 0)) > GOAL_PATIENCE_BEATS or int(state.get("goal_refusals", 0)) >= GOAL_REFUSAL_LIMIT:
                if portal is not None:
                    blocked = state.setdefault("blocked_doors", {})
                    blocked[portal.portal_id] = tick
                    while len(blocked) > VISITED_CAPACITY:
                        del blocked[min(blocked, key=lambda k: int(blocked[k]))]
                state["door_goal"] = None
            elif here.region_id != door_goal["from_region"]:
                state["door_goal"] = None  # she is through
            else:
                state["goal_beats"] = int(state.get("goal_beats", 0)) + 1
                before_door, past_door = door_crossing(snapshot, portal, here.region_id)
                why = ("hungry, searching the next room; " if feeding else "nothing here she has not seen; ") + "going through " + portal.portal_id
                if _distance_mm(body.pose.position, before_door) <= ARRIVAL_MM + STEP_MM // 2:
                    return decision("wander", why, door_crossing_commands(snapshot, portal, here.region_id), portal.portal_id)
                return decision("wander", why, move_commands_toward(snapshot, before_door, 0), portal.portal_id)
        # Moving about: she keeps one goal until she arrives at it (or gives
        # up), then takes the thing in sight she has looked at least recently.
        # Hungry with no food in sight, the same walk is her search.
        approached = state["approached"]
        goal_id = state.get("goal")
        goal = None if goal_id is None else _object(snapshot, goal_id)
        if goal is not None and goal.position is not None and _region_of(snapshot, goal.position, goal.radius_mm) is _region_of(snapshot, body.pose.position, body.radius_mm):
            stop = body.radius_mm + goal.radius_mm + (HANDLE_STOP_MM if handleable(goal) and held is None else WANDER_STOP_MM)
            state["goal_beats"] = int(state.get("goal_beats", 0)) + 1
            if (
                _distance_mm(body.pose.position, goal.position) <= stop + ARRIVAL_MM
                or int(state["goal_beats"]) > GOAL_PATIENCE_BEATS
                or int(state.get("goal_refusals", 0)) >= GOAL_REFUSAL_LIMIT
            ):
                approached[goal_id] = tick
                state["goal"] = None
                goal = None
        else:
            state["goal"] = None
            goal = None
        if goal is None and seen:
            for thing in sorted(seen, key=lambda thing: (int(approached.get(thing.object_id, -1)), thing.distance_mm)):
                near_stop = HANDLE_STOP_MM if (held is None and handleable(_object(snapshot, thing.object_id))) else WANDER_STOP_MM
                if thing.distance_mm <= body.radius_mm + thing.radius_mm + near_stop + ARRIVAL_MM:
                    approached[thing.object_id] = tick
                    continue
                if tick - int(approached.get(thing.object_id, -LOOKED_RECENTLY_BEATS - 1)) <= LOOKED_RECENTLY_BEATS:
                    continue  # looked at lately; the room may be exhausted
                state["goal"], state["goal_beats"], state["goal_refusals"] = thing.object_id, 0, 0
                goal = _object(snapshot, thing.object_id)
                break
            while len(approached) > APPROACHED_CAPACITY:
                del approached[min(approached, key=lambda k: int(approached[k]))]
        if goal is None and here is not None:
            # Nothing new to look at here: leave for the room visited least recently.
            blocked = state.get("blocked_doors", {})
            doors = [item for item in snapshot.portals if here.region_id in item.region_ids and tick - int(blocked.get(item.portal_id, -BLOCKED_DOOR_BEATS - 1)) > BLOCKED_DOOR_BEATS]
            if doors:
                def far_room(item: Any) -> str:
                    return item.region_ids[0] if item.region_ids[1] == here.region_id else item.region_ids[1]
                portal = None
                food_rooms = state.get("food_rooms", {})
                if feeding and food_rooms:
                    # Hungry: toward the room where she ate most recently, by
                    # the doorways that lead there (her own recorded episodes).
                    for room in sorted(food_rooms, key=lambda r: -int(food_rooms[r])):
                        if room == here.region_id:
                            continue
                        route = _portal_route(snapshot, here.region_id, room)
                        if route and route[0] in doors:
                            portal, state["food_room_goal"] = route[0], room
                            break
                if portal is None:
                    portal = min(doors, key=lambda item: (int(visited.get(far_room(item), -1)), item.portal_id))
                state["door_goal"], state["goal_beats"], state["goal_refusals"] = {"portal_id": portal.portal_id, "from_region": here.region_id}, 0, 0
                before_door, _past = door_crossing(snapshot, portal, here.region_id)
                why = ("hungry, going toward " + state["food_room_goal"] + " where food was; " if (feeding and state.get("food_room_goal")) else "hungry, searching the next room; " if feeding else "nothing here she has not seen; ") + "going through " + portal.portal_id
                return decision("wander", why, move_commands_toward(snapshot, before_door, 0), portal.portal_id)
        if goal is not None:
            why = "hungry, searching for food; going to look at " if feeding else "nothing pressing; going to look at "
            stop = body.radius_mm + goal.radius_mm + (HANDLE_STOP_MM if handleable(goal) and held is None else WANDER_STOP_MM)
            return decision("wander", why + goal.object_id, move_commands_toward(snapshot, goal.position, stop), goal.object_id)
        if not seen or feeding or int(state["idle_beats"]) >= IDLE_BEFORE_BABBLE:
            heading = (body.pose.heading_millidegrees + TURN_MILLIDEGREES) % 360_000
            return decision("turn", "hungry, looking around for food" if feeding else "looking around", (MoveCommand(PoseMM(body.pose.position, heading), BEAT_MICROSECONDS),))
        return decision("rest", "resting")

    # ----- commit: what the world allowed, what she took in, what she said ------------

    def commit(self, decision: Decision, *, applied_action: str, refusal: str | None,
               intake_micrograms: int, spoke: bytes | None, heard_profile: tuple[float, ...] | None,
               self_profile: tuple[float, ...] | None, tick_now: int) -> None:
        state = self._state
        if tick_now != self.live_organism_tick:
            raise RuntimeError("functional organism tick left its line")
        before = self.reserve_micrograms
        burn = BASAL_BURN_MICROGRAMS * (1 + ACT_BURN_MULTIPLE[decision.act]) if applied_action != "refused" else BASAL_BURN_MICROGRAMS
        intake = max(0, min(int(intake_micrograms), CAPACITY_MICROGRAMS - before))
        reserve = max(0, before - burn) + intake
        state["reserve_micrograms"] = min(CAPACITY_MICROGRAMS, reserve)
        state["feeding"] = (state["feeding"] or before < CAPACITY_MICROGRAMS * HUNGRY_BELOW) and state["reserve_micrograms"] < CAPACITY_MICROGRAMS * SATED_ABOVE
        if intake:
            state["meals_micrograms"] += intake
            state["bites"] += 1
            if state.get("room_now"):
                food_rooms = state.setdefault("food_rooms", {})
                food_rooms[state["room_now"]] = tick_now
                while len(food_rooms) > FOOD_ROOMS_CAPACITY:
                    del food_rooms[min(food_rooms, key=lambda k: int(food_rooms[k]))]
        if applied_action in ("approach", "wander") and refusal is None:
            state["strides"] += 1
            state["strides_since_pickup"] = int(state.get("strides_since_pickup", 0)) + 1
        if applied_action in ("touch", "grasp", "take", "release") and refusal is None and decision.target_object_id is not None:
            touched = state.setdefault("touched", {})
            touched[decision.target_object_id] = tick_now
            while len(touched) > TOUCHED_CAPACITY:
                del touched[min(touched, key=lambda k: int(touched[k]))]
            if applied_action in ("grasp", "take"):
                state["strides_since_pickup"] = 0
                state["keep_walk_beats"] = 0
                state["handled"] = int(state.get("handled", 0)) + 1
            if applied_action == "release" and state.get("room_now") and state.get("keeping_room") == state.get("room_now"):
                state["last_kept"] = {"object_id": decision.target_object_id, "room": state["room_now"], "tick": tick_now}
                state["kept"] = int(state.get("kept", 0)) + 1
        if decision.act == "release" and refusal is not None:
            state["release_refusals"] = int(state.get("release_refusals", 0)) + 1
        state["touching"] = decision.target_object_id if (applied_action == "touch" and refusal is None) else None
        if refusal is not None and decision.act in ("wander", "approach"):
            state["stuck_beats"] = int(state.get("stuck_beats", 0)) + 1
        elif applied_action in ("wander", "approach") and refusal is None:
            state["stuck_beats"] = 0
        if refusal is not None:
            if decision.act == "wander":
                state["goal_refusals"] = int(state.get("goal_refusals", 0)) + 1
            if decision.act == "approach" and decision.target_object_id is not None:
                state["food_refusals"] = int(state.get("food_refusals", 0)) + 1
                if int(state["food_refusals"]) >= GOAL_REFUSAL_LIMIT:
                    unreachable = state.setdefault("unreachable_food", {})
                    unreachable[decision.target_object_id] = tick_now
                    while len(unreachable) > VISITED_CAPACITY:
                        del unreachable[min(unreachable, key=lambda k: int(unreachable[k]))]
                    state["food_goal"], state["food_refusals"] = None, 0
            refusals = state["refusals"]
            refusals[refusal] = int(refusals.get(refusal, 0)) + 1
            while len(refusals) > REFUSAL_CAPACITY:
                del refusals[min(refusals, key=lambda k: int(refusals[k]))]
        # Memory of structure: the coarse kernel structure she met this beat
        # (the full signature is kept in the episode).
        key = _sha256(" ".join(token[0] for token in decision.signature.split(" ")).encode("utf-8"))[:16]
        familiarity = state["familiarity"]
        entry = familiarity.get(key)
        familiarity[key] = [1, tick_now] if entry is None else [int(entry[0]) + 1, tick_now]
        while len(familiarity) > FAMILIARITY_CAPACITY:
            del familiarity[min(familiarity, key=lambda k: (int(familiarity[k][0]), int(familiarity[k][1])))]
        episodes = state["episodes"]
        episodes.append([tick_now, key, decision.act, applied_action, state["reserve_micrograms"] - before, decision.signature])
        del episodes[:-EPISODE_CAPACITY]
        # Memory of sound: what she heard, and what her own last syllable sounded like.
        ambient = float(state.get("ambient_sound", 0.0))
        if heard_profile is not None and sum(heard_profile) > 0:
            state["heard"].append({"tick": tick_now, "profile": list(heard_profile)})
            del state["heard"][:-HEARD_CAPACITY]
            energy = sum(heard_profile) / len(heard_profile)
            state["ambient_sound"] = round(ambient * float(AMBIENT_MEMORY) + energy * (1.0 - float(AMBIENT_MEMORY)), 6)
        else:
            # Silence lowers the room's level, so a call after a pause stands out again.
            state["ambient_sound"] = round(ambient * float(AMBIENT_MEMORY), 6)
        if self_profile is not None and state.get("pending_drive") is not None:
            state["voice"].append({"drive": list(state["pending_drive"]), "heard": list(self_profile), "tick": tick_now})
            del state["voice"][:-VOICE_CAPACITY]
            pending = state.get("answer_pending")
            if pending is not None and list(pending["drive"]) == list(state["pending_drive"]):
                # How near did her answer land to the sound she answered? Keep
                # the better of what she knew and what she just tried.
                distance = _profile_distance(tuple(self_profile), tuple(pending["target"]))
                answer_map = state.setdefault("answer_map", {})
                known = answer_map.get(pending["key"])
                if known is None or distance < float(known["distance"]):
                    answer_map[pending["key"]] = {"drive": list(pending["drive"]), "distance": round(distance, 6), "tries": (int(known["tries"]) + 1) if known else 1}
                else:
                    known["tries"] = int(known["tries"]) + 1
                while len(answer_map) > ANSWER_MAP_CAPACITY:
                    del answer_map[min(answer_map, key=lambda k: int(answer_map[k]["tries"]))]
                state["answer_pending"] = None
        state["pending_voice"] = None if spoke is None else base64.b64encode(spoke).decode("ascii")
        state["pending_drive"] = None if spoke is None else list(decision.drive)
        if spoke is not None:
            state["last_spoke_tick"] = tick_now
            state["syllables"] += 1
        state["idle_beats"] = int(state["idle_beats"]) + 1 if decision.act in ("rest", "attend", "turn", "babble", "imitate", "listen") else 0
        # A heard sound answered this beat stays answered; older entries fall out of the ring.
        state["last_act"] = decision.act
        state["tick"] = tick_now + 1


__all__ = (
    "BODY_AXES", "CAPACITY_MICROGRAMS", "Decision", "FunctionalOrganism", "MAGIC", "SCHEMA", "Sensed",
    "SeenThing", "cochlear_profile", "in_hand_reach", "move_commands_toward", "syllable_pcm", "things_in_sight",
)
