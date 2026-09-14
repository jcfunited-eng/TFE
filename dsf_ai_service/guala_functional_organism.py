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
    _approach_point, _distance_mm, _heading_toward, _portal_points, _region_of,
    nothing_left_to_bite, offered_within_reach,
)
from dsf_ai_service.guala_voice import ONSETS, PITCHES_DECIHERTZ, VOWELS, syllable_pcm as airway_syllable_pcm
from dsf_ai_service.substrate.embodiment_world import (
    GraspContactCommand, MoveCommand, OralContactCommand, PoseMM, PositionMM,
    ReleaseHeldObjectCommand, _derived_contact_patch_square_mm, _receptor_position,
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
    "rest": 0, "attend": 0, "bite": 2, "grasp": 2, "release": 1, "turn": 1,
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
            "voice_version": VOICE_VERSION, "visited": {}, "door_goal": None, "bout_syllables": 0, "quiet_until_tick": 0, "blocked_doors": {}, "attended_tick": -ATTEND_REFRACTORY_BEATS - 1, "unreachable_food": {}, "food_goal": None, "food_refusals": 0, "food_best_mm": 0, "food_stall_beats": 0, "ambient_sound": 0.0, "answered_profile": None,
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
        for key, empty in (("visited", {}), ("door_goal", None), ("bout_syllables", 0), ("quiet_until_tick", 0), ("blocked_doors", {}), ("attended_tick", -ATTEND_REFRACTORY_BEATS - 1), ("unreachable_food", {}), ("food_goal", None), ("food_refusals", 0), ("food_best_mm", 0), ("food_stall_beats", 0), ("ambient_sound", 0.0), ("answered_profile", None)):
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
    def body_axes(self) -> tuple[tuple[object, ...], ...]:
        return BODY_AXES

    def readiness(self) -> Readiness:
        encoded = self.encoded()
        return Readiness(self.identity, self.live_organism_tick, _sha256(encoded), len(encoded), 0, BODY_AXES)

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
        return {key: int(self._state[key]) for key in ("bites", "strides", "syllables", "meals_micrograms")}

    # ----- the kernel over her measured streams --------------------------------------

    def _measure(self, sensed: Sensed, seen: tuple[SeenThing, ...], body: Any) -> dict[str, float]:
        focal = sensed.focal_luminance_u8
        total = sum(focal)
        if len(focal) == FOCAL_COLUMNS * FOCAL_ROWS and total:
            horizontal = sum(value * (index % FOCAL_COLUMNS) for index, value in enumerate(focal)) / (total * (FOCAL_COLUMNS - 1))
            vertical = sum(value * (index // FOCAL_COLUMNS) for index, value in enumerate(focal)) / (total * (FOCAL_ROWS - 1))
        else:
            horizontal = vertical = 0.5
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
        # this beat (not while her mouth is busy eating): a heard sound is
        # answered once with her nearest own syllable; otherwise she babbles
        # in bouts, walking or still.
        voice_drive = None
        voice_reason = ""
        spoke_recently = tick - int(state["last_spoke_tick"]) < BABBLE_EVERY_BEATS
        in_quiet_spell = tick < int(state.get("quiet_until_tick", 0))
        # A sound worth answering stands out from the room (louder than the
        # running ambient level) and is not the sound she just answered; a
        # microphone left open does not make her repeat one syllable forever.
        ambient = float(state.get("ambient_sound", 0.0))
        answered_profile = state.get("answered_profile")
        unanswered = []
        for entry in state["heard"]:
            if tick - int(entry["tick"]) > HEARD_RECENT_BEATS or entry.get("answered"):
                continue
            energy = sum(entry["profile"]) / len(entry["profile"])
            if energy < HEARD_ENERGY_FLOOR or energy < ambient * HEARD_ABOVE_AMBIENT:
                entry["answered"] = True  # part of the room, not a call to her
                continue
            if answered_profile is not None and _profile_distance(tuple(entry["profile"]), tuple(answered_profile)) < SAME_SOUND_DISTANCE:
                entry["answered"] = True  # the same sound again
                continue
            unanswered.append(entry)
        # An answer does not wait for her babble's quiet spell; a constant
        # sound stops being answered once it has become the room's level.
        if unanswered and not spoke_recently and state["voice"]:
            target_profile = tuple(unanswered[-1]["profile"])
            best = min(state["voice"], key=lambda entry: _profile_distance(tuple(entry["heard"]), target_profile))
            voice_drive, voice_reason = tuple(best["drive"]), "answering a sound she heard with the nearest sound of her own"
            unanswered[-1]["answered"] = True
            state["answered_profile"] = list(target_profile)
        elif not spoke_recently and not in_quiet_spell:
            voice_drive, voice_reason = _new_drive(tick), "trying a sound of her own"
        if voice_drive is not None:
            state["bout_syllables"] = int(state.get("bout_syllables", 0)) + 1
            if int(state["bout_syllables"]) >= BOUT_SYLLABLES:
                state["bout_syllables"], state["quiet_until_tick"] = 0, tick + QUIET_BEATS

        def decision(act: str, reason: str, commands: tuple[Any, ...] = (), target: str | None = None, drive: tuple[int, int, int] | None = None) -> Decision:
            if drive is None and voice_drive is not None and act in ("rest", "attend", "turn", "wander"):
                if act == "rest":
                    act, reason = ("imitate" if unanswered else "babble"), voice_reason
                else:
                    reason = reason + "; " + voice_reason
                drive = voice_drive
            return Decision(act, reason, commands, target, drive, signature, novel, gate_count, seen)

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
        if novel and gate_count:
            state["attended_tick"] = tick
            return decision("attend", "a structure she has not met before")
        # Where she is: the room she stands in, remembered as visited now.
        here = _region_of(snapshot, body.pose.position, body.radius_mm)
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
            stop = body.radius_mm + goal.radius_mm + WANDER_STOP_MM
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
                if thing.distance_mm <= body.radius_mm + thing.radius_mm + WANDER_STOP_MM + ARRIVAL_MM:
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
                portal = min(doors, key=lambda item: (int(visited.get(far_room(item), -1)), item.portal_id))
                state["door_goal"], state["goal_beats"], state["goal_refusals"] = {"portal_id": portal.portal_id, "from_region": here.region_id}, 0, 0
                before_door, _past = door_crossing(snapshot, portal, here.region_id)
                why = ("hungry, searching the next room; " if feeding else "nothing here she has not seen; ") + "going through " + portal.portal_id
                return decision("wander", why, move_commands_toward(snapshot, before_door, 0), portal.portal_id)
        if goal is not None:
            why = "hungry, searching for food; going to look at " if feeding else "nothing pressing; going to look at "
            stop = body.radius_mm + goal.radius_mm + WANDER_STOP_MM
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
        if applied_action in ("approach", "wander") and refusal is None:
            state["strides"] += 1
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
        if heard_profile is not None and sum(heard_profile) > 0:
            state["heard"].append({"tick": tick_now, "profile": list(heard_profile)})
            del state["heard"][:-HEARD_CAPACITY]
            energy = sum(heard_profile) / len(heard_profile)
            ambient = float(state.get("ambient_sound", 0.0))
            state["ambient_sound"] = round(ambient * float(AMBIENT_MEMORY) + energy * (1.0 - float(AMBIENT_MEMORY)), 6)
        if self_profile is not None and state.get("pending_drive") is not None:
            state["voice"].append({"drive": list(state["pending_drive"]), "heard": list(self_profile), "tick": tick_now})
            del state["voice"][:-VOICE_CAPACITY]
        state["pending_voice"] = None if spoke is None else base64.b64encode(spoke).decode("ascii")
        state["pending_drive"] = None if spoke is None else list(decision.drive)
        if spoke is not None:
            state["last_spoke_tick"] = tick_now
            state["syllables"] += 1
        state["idle_beats"] = int(state["idle_beats"]) + 1 if decision.act in ("rest", "attend", "turn", "babble", "imitate") else 0
        # A heard sound answered this beat stays answered; older entries fall out of the ring.
        state["last_act"] = decision.act
        state["tick"] = tick_now + 1


__all__ = (
    "BODY_AXES", "CAPACITY_MICROGRAMS", "Decision", "FunctionalOrganism", "MAGIC", "SCHEMA", "Sensed",
    "SeenThing", "cochlear_profile", "in_hand_reach", "move_commands_toward", "syllable_pcm", "things_in_sight",
)
