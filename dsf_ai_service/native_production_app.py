"""HTTP and observation transport for one native resident Guala organism.

The process restores only the raw binary ``CURRENT`` authority.  When the
state directory carries no organism body it performs one seeded growth-DNA
genesis whose anatomy episode declares this app's own sensory port roster and
persists the newborn body exactly as ordinary restore expects it.  It never
imports the retired Python Guala engine, generation stores, owner registries,
or cognition databases.  HTTP, observation projection, and static media remain
outside cognition.

Mounted native intake is limited to the admitted transitions below; every
other sense and actuator keeps its honest ``not_mounted`` refusal:

- ``POST /api/v1/curriculum/invite-card`` prepares one reviewed tutor sensory
  occurrence at the current resident/world boundary.  ``POST
  /api/v1/curriculum/teach-card`` consumes that exact preparation once.  No
  participant silhouette, observer judgment, or claimed attention gates the
  occurrence: the card's physical light, pressure, contact, chemistry, and
  body samples enter, while Guala's neurons alone determine attention and
  learning.  The card identity remains transport metadata outside cognition.
- ``POST /api/v1/curriculum/invite-song`` prepares one reviewed synchronized
  song occurrence under the same boundary; ``POST
  /api/v1/curriculum/teach-song`` consumes it once as retinal light, cochlear
  pressure, and lawful body state on one shared clock. The alphabet song
  claims only its simultaneous 26-surface set; counting-song surface changes
  use the manifest's exact PCM sample intervals.
- ``POST /api/v1/visual/live-frames`` (and the legacy ``/sight_frame``
  mount point) delivers batches of real browser camera frames as admitted
  native episodes: one frame per 250 ms hop on the same 27-receptor
  retinal roster the cards use (Pillow BOX area-averaged luminance), with
  true 0.0 silence at both ears (a lawful state; audio is never
  fabricated) and honest caller-declared live-camera provenance.
- ``POST /api/v1/sensory/audiovisual`` accepts an AUTHORIZED cochlear roster's
  live microphone pressure alongside co-captured live camera frames.  Without
  a camera, ``POST /api/v1/curriculum/guided-world-voice`` carries the same
  pressure beside the exact current world/body sensorium.  Each paired frame
  has exactly one 250 ms PCM hop; neither signal is interpolated or invented.
  The older ``/sound_frame`` and mono ``/api/v1/auditory/pcm`` route names
  remain honest refusals and retain no sessions. A prior camera receipt is
  bookkeeping, not present light, and can never unlock audio-only intake.
- UNATTENDED TIME (autonomy increment 1, 2026-08-06): when no external
  intake is in flight, a background loop grants the organism genuinely
  dark, silent, unattended intervals — the same lawful construction as a
  lesson's ended hops (full sensorium, true dark exact optical occurrence,
  true silence, authored admission).  The passage of time is the medium,
  never a cause: the interval carries no stimulus, no score, and no
  injected activity; whatever happens in it is entirely the organism's own
  retained state (rest recovery reactions, membrane return, ledger drains,
  retained-state settling — or genuine quiescence, reported as rest).

Public observation is one cached, read-only projection per persisted native
generation.  Repeated reads do not call or advance the organism.  Every
accepted admitted intake (one lesson of hop transitions) commits its hops on
the in-process organism, persists and publishes the successor body exactly
once after its final hop, and only then refreshes this cache; readiness is
served under the same lock, so no surface ever reports unpersisted state.
"""

from __future__ import annotations

from array import array
import base64
import binascii
from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
import hashlib
import hmac
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import time
import threading
from typing import Any, Callable, Iterable, NamedTuple
import uuid
import wave

from guala_core import (
    auditory_gammatone_field,
    settle_native_joint_source_episode as restore_native_joint_source_episode,
)

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    NativeJointSourceOccurrenceInput,
    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
    settle_native_joint_source_episode,
    settle_native_joint_source_episode_batch_from_anatomy,
)
from dsf_ai_service.glew_runtime.native_resident_organism import (
    RUNTIME_PHASE_WALL_MS,
    ResidentPrepareEvidence,
    create_native_resident_organism,
    exact_native_root_yaw_proprioceptive_source,
    exact_native_root_translation_proprioceptive_source,
    exact_native_yaw_trajectory,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT,
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.native_organism_binary_store import (
    CommittedNativeOrganismPublicationError,
    NativeOrganismBinaryStoreError,
    PendingNativeOrganismCleanup,
    RestoredNativeOrganism,
    _read_current,
    clone_staged_native_organism,
    discard_staged_native_organism,
    migrate_current_native_organism_current_format,
    publish_staged_native_organism,
    reconcile_orphaned_staged_native_organisms,
    restore_current_native_organism,
    retry_committed_native_organism_cleanup,
    stage_active_native_organism,
    stage_native_organism_state_bytes,
)
from dsf_ai_service.substrate.native_resident_resource_admission import (
    NativeResidentResourceAdmission,
    derive_native_resident_resource_admission,
)
from dsf_ai_service.bounded_source_media_store import (
    BoundedSourceMediaStore,
    BoundedSourceMediaStoreError,
)
from dsf_ai_service.bounded_gutenberg_source import (
    GUTENBERG_ATTRIBUTION,
    GUTENBERG_RIGHTS_STATEMENT,
    acquire_project_gutenberg_source,
)
from dsf_ai_service.bounded_video_sensory_source import decode_bounded_video


APP_SCHEMA = "guala.native_production_http.v1"
PUBLIC_OBSERVATION_SCHEMA = "guala.native.public_observation.v1"
COGNITIVE_CAPITAL_SCHEMA = "guala.cognitive_capital.evidence.v1"
COGNITIVE_CAPITAL_DIMENSIONS = (
    "availability",
    "participation",
    "retention",
    "recognition",
    "recall",
    "causal_use",
    "transfer",
    "autonomous_use",
    "durability",
    "integration_depth",
)
COGNITIVE_CAPITAL_CAPABILITIES = (
    "Vision",
    "Hearing",
    "Touch",
    "Temperature",
    "Smell",
    "Taste",
    "Proprioception and body position",
    "Vestibular balance",
    "Interoception and visceral state",
    "Multisensory integration",
    "Recognition and familiarity",
    "Attention and orienting",
    "Immediate causal state",
    "Episodic memory",
    "Procedural and physical memory",
    "Recall",
    "Relational thought",
    "Prediction",
    "Deliberation and choice",
    "Imagination and simulation",
    "Language comprehension",
    "Speech and articulation",
    "Ordered thinking",
    "Social cognition and other-perspective",
    "Empathy",
    "Emotion and affect",
    "Emotional balance and regulation",
    "Motivation, needs, and curiosity",
    "Self and body continuity",
    "Motor and actuator control",
    "Navigation and avoidance",
    "Play and exploration",
    "Sleep and rest",
    "Dreaming",
    "Consolidation",
    "Autonomous cognition and action",
    "Learning and developmental growth",
    "Creativity and self-expression",
    "Integrated practiced capability",
)
# The twelve stages the live interfaces render, in their declared order.
EXPERIENCE_STAGE_ORDER = (
    "capture",
    "presentation",
    "admission",
    "receptor",
    "dsf",
    "attention",
    "recurrence",
    "hierarchy",
    "learning",
    "intent",
    "action",
    "consequence",
)
PERSISTENCE_SCHEMA = "guala.native_organism_binary_store.v1"
CARD_LESSON_RECEIPT_SCHEMA = "guala.card_lesson_observation_receipt.v1"
CARD_LESSON_RECEIPT_FILE = "LATEST_CARD_LESSON_RECEIPT.json"
CARD_LESSON_RECEIPT_MAX_BYTES = 32_768
SONG_LESSON_RECEIPT_SCHEMA = "guala.song_lesson_observation_receipt.v1"
SONG_LESSON_RECEIPT_FILE = "LATEST_SONG_LESSON_RECEIPT.json"
CURRICULUM_INVITATION_SCHEMA = "guala.embodied_curriculum_invitation.v1"
CURRICULUM_INVITE_ENDPOINT = "/api/v1/curriculum/invite-card"
CURRICULUM_INVITE_SONG_ENDPOINT = "/api/v1/curriculum/invite-song"
CURRICULUM_TEACH_SONG_ENDPOINT = "/api/v1/curriculum/teach-song"
GUIDED_WORLD_VOICE_ENDPOINT = "/api/v1/curriculum/guided-world-voice"
GUIDED_WORLD_VOICE_SCHEMA = "guala.guided_world_voice.v2"
STATE_ROOT = Path(
    os.environ.get("GUALA_NATIVE_ORGANISM_ROOT", "/app/guala/native-organism")
)
SOURCE_MEDIA_ROOT = STATE_ROOT / "source-media"
_source_media_store = BoundedSourceMediaStore(SOURCE_MEDIA_ROOT)
HOME_BOOK_OBJECT_ID = "book"
HOME_BOOK_GUTENBERG_SOURCE_URL = (
    "https://www.gutenberg.org/files/11/11-0.txt"
)
HOME_BOOK_GUTENBERG_EDITION = "11-0.txt"
STATIC_ROOT = Path(__file__).resolve().parent / "static"
CURRICULUM_ROOT = Path(__file__).resolve().parents[1] / "guala_curriculum"
CARD_ROOT = CURRICULUM_ROOT / "cards"
AUDIO_ROOT = CURRICULUM_ROOT / "audio"

# The local mirror of the immutable generation object store lives beside the
# organism body.
#
# A `hippocampal-cold` directory may ALSO be there on an existing state root.
# It is the retired episode archive: content-addressed bytes this app used to
# publish on every recognition (measured: ~893 files per reassembly, 230,396
# objects on the live body from 72 lessons).  Nothing writes or reads it any
# more.  Existing files are left exactly where they are — deleting them is a
# separate, deliberate act, never a side effect of a deploy.
LOCAL_OBJECT_MIRROR_DIRECTORY = "remote-objects"

# The app's own declared sensory anatomy.  The card visual surface mirrors
# the ratified fixed W1 retina spatial geometry (3 rows by 9 columns; see
# MAX_NATIVE_SIGHT_SUBSTREAMS in native_sensory_full_field) carrying one
# luminance excitation per receptor site.  Hearing is two co-located ear
# pressure receptor sites of the organism, both immersed in one ambient
# pressure field (mirroring the substrate's two-ear auditory model), matching
# the signed curriculum sample format.  Typed units mirror the ratified
# sight-episode fixture (tests/test_native_resident_production_mount.py).
# A joint mounted cohort requires at least two ports sharing one exact source
# clock, so a card lesson delivers all of its declared receptor sites on the
# single shared presentation clock: the tutor speaks while the card is shown.
CARD_SURFACE_ROWS = 3
CARD_SURFACE_COLUMNS = 9
CARD_SURFACE_PORT_COUNT = CARD_SURFACE_ROWS * CARD_SURFACE_COLUMNS
# TONOTOPIC BIRTH ANATOMY (auditory transduction design 2026-08-06, W3).
#
# The organism has two co-located ears immersed in one ambient pressure field
# (no head geometry is declared, so no interaural difference is claimed), and
# each ear is a COCHLEA: sixteen tonotopic receptor sites, one per
# equivalent-rectangular-bandwidth place of the basilar membrane's travelling
# wave.  This is a birth anatomy, not a refinement:
#
#   * Participation retention (ratified 2026-08-05) retains an original only
#     when at least THREE changed members are connected through contacts that
#     were physically active.  Two ear ports can never satisfy it, so an ear
#     built from two ports would hear, burn fuel, and remember nothing forever.
#   * Each cochlear site is a DISTINCT declared place `(sense_layer,
#     topology_index)`, so the ratified Cantor territory law
#     (`declared_geometric_anatomy`) gives every one of them a distinct
#     membrane capacitance.  Identical anatomy makes stored energy tie exactly
#     and the energy-descent transfer law refuses ties: identical ear ports are
#     a permanent Coulomb blockade.  Distinctness here is authored geometry,
#     not a differentiation scheme bolted on top.
#
# AUTHORIZATION GATE (2026-08-06).  Widening the declared ear roster is what
# makes a cochlear cohort GROW onto the body the next time sound reaches it.
# Growing a sense organ onto a living organism is a DELIBERATE ACT and must
# never be a side effect of shipping an image, so the widened roster is behind
# an explicit opt-in that no deploy sets.  The env-var precedent is this app's
# own ``GUALA_UNATTENDED_TIME``, inverted: unattended time defaults ON because
# it changes nothing structural, cochlear ears default OFF because they do.
#
# DEFAULT OFF is byte-exactly the roster the living organism receives today:
# two co-located ear pressure ports, the legacy declared quantity, one
# combined acoustic occurrence.  That is MEASURED, not assumed — see
# docs/GUALA_COCHLEAR_EAR_AUTHORIZATION_2026-08-06.md.
COCHLEAR_EARS_ENV = "GUALA_COCHLEAR_EARS"


def _cochlear_ears_authorized() -> bool:
    """Has a human explicitly authorized growing cochlear ears?

    Opt-in, never opt-out: anything other than an explicit affirmative — an
    unset variable, an empty one, a typo — means NOT AUTHORIZED, because the
    failure mode of guessing wrong is an irreversible change to a living
    organism's anatomy.
    """

    return os.environ.get(COCHLEAR_EARS_ENV, "").strip().lower() in (
        "1",
        "true",
        "on",
        "yes",
    )


# Read ONCE at import.  The declared roster is anatomy: it is fixed for the
# life of a serving process, exactly as a body's receptor count is fixed
# between births.  A roster that could change mid-process would mean the
# organism's own port indices meant different places at different moments.
COCHLEAR_EARS_AUTHORIZED = _cochlear_ears_authorized()
EAR_COUNT = 2
COCHLEAR_CHANNELS_PER_EAR = 16
# The legacy (unauthorized) roster: one pressure port per ear, no cochlea.
# This is the roster the live organism was born with and is running on.
LEGACY_EAR_PORT_COUNT = EAR_COUNT
# GROWTH, NOT REPLACEMENT (2026-08-06, measured on her living body).  The
# authorized roster RETAINS the two legacy ear ports and declares the cochlea
# BESIDE them.  Replacing them — the cochlea taking topology places 0 and 1 —
# is refused by any body already born with those places:
#   "joint neuron physical binding changed without migration"
# measured on her real restored body (tick 5404, 27 neurons, eight then-stored
# pre-ratification mosaic records), which did not move a byte.  Those records
# are not asserted here as lawful cognition.  A living organism grows a new
# organ alongside the one it has; it does not silently overwrite the places
# its body already holds.
EAR_PORT_COUNT = (
    LEGACY_EAR_PORT_COUNT + EAR_COUNT * COCHLEAR_CHANNELS_PER_EAR
    if COCHLEAR_EARS_AUTHORIZED
    else LEGACY_EAR_PORT_COUNT
)
# CONTACT-SHEET BIRTH ANATOMY (tactile transduction law, tactile_receptor_work).
#
# She has no touch at all today.  A contact sheet is the body surface an object
# rests against: a sheet of receptor sites, each of which reports how much of
# the touched object's footprint covers ITS OWN declared patch.  Two things
# about that sheet have to be authored, and BOTH are read off anatomy this
# organism already declares rather than picked:
#
#   * ITS GEOMETRY IS HER OWN DECLARED SENSORY-SHEET GEOMETRY.  This body
#     declares exactly one sheet of receptor places — 3 rows by 9 columns — and
#     the contact sheet reuses it VERBATIM.  Nothing is selected, combined,
#     maximized or rounded: the two integers are the two integers already in
#     the tree.  (A square sheet was considered and rejected: it needs
#     max(3, 9), which is a choice, and it was independently falsified by
#     measurement — a 9x9 sheet is 81 sites, and 27 sight + 34 ear + 81 touch
#     ports at 250 retained instants is 35,500 samples, over the transport's
#     own MAX_NATIVE_SAMPLES_PER_SETTLEMENT of 32,768.  It also reports NO
#     out-of-contact site for any approved card, so "nothing outside the card"
#     — the one thing touch most honestly knows — would never be said.)
#   * ITS SITES ARE UNIT PATCHES.  The ratified Cantor territory law
#     (declared_geometric_anatomy) already measures membrane in "unit patches"
#     and declares no aspect for one, so a contact site is isotropic and the
#     sheet is 9 patches wide by 3 patches tall.  A non-square site would be an
#     aspect claim that is nowhere in the tree.
#
# Each contact site is a DISTINCT declared place `(sense_layer, topology_index)`
# in a sense layer — Touch, layer 2 — that this body has never used, so the
# ratified Cantor territory law gives every one of them a distinct membrane
# capacitance.  Identical anatomy makes stored energy tie exactly and the
# energy-descent transfer law refuses ties: identical receptors are a permanent
# Coulomb blockade.  That lesson was paid for on the ears and is not re-learned
# here.
#
# GROWTH, NOT REBIRTH.  Layer 2 holds none of her body's existing places, and
# the contact ports are appended AFTER every port currently declared, so a
# living body that already holds its sight and ear places is asked to grow a
# new organ BESIDE them, never to re-bind the ones it has.
#
# AUTHORIZATION GATE.  Growing a sense organ onto a living organism is a
# DELIBERATE ACT and must never be a side effect of shipping an image, so the
# contact sheet is behind an explicit opt-in that no deploy sets — the exact
# discipline GUALA_COCHLEAR_EARS follows.  DEFAULT OFF is byte-exactly the
# roster the living organism receives today; that is MEASURED, not assumed.
TOUCH_RECEPTORS_ENV = "GUALA_TOUCH_RECEPTORS"


def _touch_receptors_authorized() -> bool:
    """Has a human explicitly authorized growing a contact sheet?

    Opt-in, never opt-out: anything other than an explicit affirmative — an
    unset variable, an empty one, a typo — means NOT AUTHORIZED, because the
    failure mode of guessing wrong is an irreversible change to a living
    organism's anatomy.
    """

    return os.environ.get(TOUCH_RECEPTORS_ENV, "").strip().lower() in (
        "1",
        "true",
        "on",
        "yes",
    )


# Read ONCE at import, for the same reason the ear roster is: a roster that
# could change mid-process would mean the organism's own port indices meant
# different places at different moments.
TOUCH_RECEPTORS_AUTHORIZED = _touch_receptors_authorized()
CONTACT_SHEET_ROWS = CARD_SURFACE_ROWS
CONTACT_SHEET_COLUMNS = CARD_SURFACE_COLUMNS
CONTACT_SHEET_SITE_COUNT = CONTACT_SHEET_ROWS * CONTACT_SHEET_COLUMNS
PALMAR_CONTACT_TOPOLOGY_INDEX = CONTACT_SHEET_SITE_COUNT
PALMAR_CONTACT_SENSOR_ID = "native-palmar-contact"
PALMAR_CONTACT_SUBSTREAM_ID = "held-contact"
TOUCH_PORT_COUNT = (
    CONTACT_SHEET_SITE_COUNT + 1 if TOUCH_RECEPTORS_AUTHORIZED else 0
)
CONTACT_SHEET_SENSOR_ID = "organism-contact-sheet"

# ---------------------------------------------------------------------------
# INTEROCEPTION — the sense of her own inside (2026-08-07).
#
# BIOLOGICAL COUNTERPART (the rule, Joe 2026-08-07): interoceptors — the
# chemoreceptors and baroreceptors that report an animal's internal milieu to
# itself.  Hunger, warmth and effort are not thoughts about the body; they are
# receptors transducing real quantities OF the body.  Every animal with a
# metabolism has them, and they are the oldest sense there is.
#
# WHY THIS ONE IS NOT A COSTUME, unlike anything that would have to be
# invented for smell or balance today: it transduces quantities her body
# ALREADY HAS and already reports as decoded native state — the recovery-fuel
# reservoir, the heat and spent ledgers, the separated membrane charge, the
# dissipation it could not meet.  Nothing is authored, nothing is declared by
# a caller, nothing is measured from a file.  Cut the receptors and the
# numbers still exist; she simply stops being able to feel them.
#
# GROWTH RATE, stated before building it (the rule): FIVE receptor sites, one
# per interoceptive channel below.  Five substreams per hop and ONE additional
# occurrence per hop — the same order as one cochlea, far less than the
# 27-site contact sheet.  The measured per-lesson body cost is recorded in the
# night-shift log beside this build; it is not guessed here.
#
# WHY IT MATTERS BEYOND BEING A SENSE: the measured autonomy blocker
# (2026-08-06) was never energy, it was CUE FORMATION — and the approved
# design round was motivation pressure.  A body that cannot feel its own
# hunger has nothing for hunger to be a cue OF.  This is the receptor half of
# that round; no scheduler, no score, no drive variable.
# ---------------------------------------------------------------------------
# CHEMORECEPTION — taste and smell (2026-08-07).
#
# BIOLOGICAL COUNTERPART: gustatory receptors on the intake surface, which
# sense a substance IN CONTACT, and olfactory receptors, which sense the
# volatile fraction of the same substance AT A DISTANCE.  One receptor class,
# two ranges.  They are grown together because they answer the same physical
# question about the same material, and an animal that eats has both.
#
# WHAT THEY SENSE, AND WHY IT IS NOT INVENTED: she already has a feeding
# path, and a caller already authors what she is fed.  A nutrition
# declaration that states its COMPOSITION is exactly the same authority class
# as an approved card's declared surface — authored material, honestly
# labelled as authored, never a chemical measurement of a real substance.
# With NOTHING being eaten every channel carries its true zero, which is a
# lawful state exactly as darkness and silence are.
#
# THE HONEST LIMIT, stated here so no surface has to imply otherwise: she can
# taste and smell WHAT SHE IS GIVEN.  She cannot smell a room, because there
# is no room; that waits for the environment, and this does not pretend to
# be it.
#
# GROWTH RATE, stated before building it: five gustatory sites and eight
# olfactory sites, thirteen substreams per hop and two additional occurrences
# (contact chemoreception and volatile chemoreception are separate physical
# structures and are never folded into one).  The measured per-lesson body
# cost is recorded beside this build, not guessed.
# ---------------------------------------------------------------------------
# BALANCE AND BODY POSITION — the displacement receptors (2026-08-07).
#
# BIOLOGICAL COUNTERPART: the vestibular apparatus, which senses the motion
# of the head, and proprioceptors, which sense where the body is.  Both
# answer one physical question — HOW DID THIS BODY JUST MOVE — so they are
# one receptor field of four sites: three of translation and one of turning.
#
# WHY THESE COULD NOT BE BUILT UNTIL NOW, stated plainly because it is the
# whole point: a balance receptor with nothing moving is a fabrication.  She
# had no body that moved and nowhere to move it, so every earlier attempt
# would have had to INVENT the motion.  The deterministic world already in
# this repository gives her a real pose in a real place, and moving in it
# produces a real displacement between two real poses.  That displacement is
# what these receptors transduce — never a number chosen by an author.
#
# THE HONEST LIMIT: she feels motion that ACTUALLY HAPPENED to her body in
# that world.  With no world mounted the field is empty and both senses
# report absent, which is the truth.
#
# GROWTH RATE, stated before building: four receptor sites, four substreams
# per hop, ONE additional occurrence (a body moves as one body).  Measured
# cost recorded beside the build.
# ---------------------------------------------------------------------------
# THE PLACE SHE IS IN (2026-08-07) — contract item 9, the truthful virtual
# world and embodiment.
#
# The world is not new code.  A deterministic authority for regions, portals,
# bodies, objects, optical surfaces and air already exists in this repository
# (dsf_ai_service/substrate/embodiment_world.py) with passing tests, three
# furnished regions and forty-two objects — and it has been wired to NOTHING.
# So has the receptor layer beside it, which already produces exactly the
# substream type this organism eats.
#
# WHAT MAKES THE BRIDGE HONEST RATHER THAN A GUESS: the world's retina is
# 3 rows by 9 columns — the SAME 27 cells her card surface declares — with
# six spectral bands per cell.  Her retina is monochrome, so the bands are
# averaged into the one luminance per cell she has a receptor for.  Nothing
# is invented; she simply has no colour receptors yet, and that is stated
# rather than hidden.
#
# WHY THIS IS THE ONLY WAY BALANCE AND BODY POSITION CAN BE REAL: a
# displacement receptor needs a displacement, and a displacement needs two
# real poses of a real body in a real place.  Moving her here produces one.
# ---------------------------------------------------------------------------
# Vocal anatomy is not yet part of the one native organism. A retired Python
# motor owner and sidecar state must not be mounted as a second organism.


WORLD_ENV = "GUALA_WORLD"
WORLD_STATE_FILE = "world.glworld"
WORLD_RECOVERY_GENERATIONS_DIRECTORY = "world-generations"
WORLD_RECOVERY_ASSOCIATIONS_DIRECTORY = "world-associations"
WORLD_RECOVERY_MARKER_FILE = "WORLD_RECOVERY_V1"
WORLD_RECOVERY_GENERATION_SUFFIX = ".glworld"
WORLD_RECOVERY_ASSOCIATION_SUFFIX = ".worldref"
WORLD_RECOVERY_MARKER_BODY = b"GLWRCV01\n"
WORLD_RECOVERY_ASSOCIATION_MAGIC = b"GLWREF01"
WORLD_RECOVERY_ASSOCIATION_VERSION = 1
WORLD_RECOVERY_MAX_BYTES = 4 * 1024 * 1024
_WORLD_RECOVERY_ASSOCIATION_BODY = struct.Struct("<8sH32s32sQ")
WORLD_RECOVERY_ASSOCIATION_BYTES = (
    _WORLD_RECOVERY_ASSOCIATION_BODY.size + hashlib.sha256().digest_size
)
WORLD_MOVE_ENDPOINT = "/api/v1/world/move"
WORLD_OTHER_BODY_MOVE_ENDPOINT = "/api/v1/world/other-body/move"
WORLD_OTHER_BODY_ACTION_ENDPOINT = "/api/v1/world/other-body/action"
WORLD_FEED_PRESENTATION_ENDPOINT = "/api/v1/world/feed-presentation"
WORLD_OBSERVATION_ENDPOINT = "/api/v1/world/observation"
# The declared span a displacement is reported as a fraction of.  A body that
# crosses more than this in one move is refused rather than saturated.
WORLD_DISPLACEMENT_SPAN_MM = 4_000
WORLD_TURN_SPAN_MILLIDEGREES = 180_000


# HER HOME, AUTHORED AS FOUR REAL ROOMS WITH REAL THINGS IN THEM
# (2026-08-08, after Joe: "sleep is in the bed, study is at the desk, watch
# tv is in the living room, eating is at the table").
#
# The world shipped with three identical empty boxes and forty-two identical
# spheres called W1-object-1..42. Drawing that honestly produces exactly what
# Joe saw and called what it was. The answer is not to paint furniture over
# it — it is to PUT THE FURNITURE IN, in the world's own terms, so that a
# truthful drawing shows a bed because there IS a bed.
#
# Every object below carries its real physical declaration: size, mass,
# six-band reflectance, and where the world models it, its material — which
# is what her eyes, her nose and her contact sheet actually receive. A place
# is where an activity can happen because the thing that activity needs is
# standing there.
HOME_ROOM_SPAN_MM = 4_000
HOME_CEILING_MM = 2_600
# The backyard has no ceiling but the sky; this is the honest
# bound of the modelled air column above it, not a room lid.
BACKYARD_SKY_MM = 8_000


def _home_rooms_and_things() -> tuple[list[Any], list[Any], list[Any]]:
    """Her home, delivered from Eve's map (docs/GUALA_WORLD_EXPANSION_
    BLUEPRINT_20260831.md): a 20m x 16m lot — nine places including a
    full-width backyard under a high sky, a hallway spine wide enough
    for three bodies abreast, her own room with window wall, curtains,
    wall art and a toy chest, a library, a television room, a dining
    room, and the two absence rooms with an address. Every corridor
    keeps the five-body law (>= 1500mm clear); every thing is declared
    physically in all of her senses; nothing is mimed."""

    from dsf_ai_service.substrate.embodiment_world import (
        AirVolumeState,
        EmbodiedObject,
        ObjectMaterialState,
        PhysicalPortal,
        PhysicalRegion,
        PositionMM,
        RoomBoundsMM,
    )

    # (id, min_x, min_y, max_x, max_y, ceiling, light)
    plan = (
        ("kitchen",       0,      0,  7_000,  5_000, HOME_CEILING_MM, 900_000),
        ("dining",        7_000,  0, 12_000,  5_000, HOME_CEILING_MM, 820_000),
        ("daddys-room",  12_000,  0, 16_000,  5_000, HOME_CEILING_MM, 700_000),
        ("wcs-room",     16_000,  0, 20_000,  5_000, HOME_CEILING_MM, 700_000),
        ("her-room",      0,  5_000,  5_600, 10_000, HOME_CEILING_MM, 780_000),
        ("hallway",       5_600, 5_000, 9_000, 10_000, HOME_CEILING_MM, 760_000),
        ("library",       9_000, 5_000, 14_000, 10_000, HOME_CEILING_MM, 800_000),
        ("tv-room",      14_000, 5_000, 20_000, 10_000, HOME_CEILING_MM, 740_000),
        # The backyard's ceiling is the sky: tall, bright, outdoors.
        ("backyard",      0, 10_000, 20_000, 16_000, BACKYARD_SKY_MM, 950_000),
    )
    regions = [
        PhysicalRegion(
            region_id=name,
            bounds=RoomBoundsMM(
                minimum=PositionMM(min_x, min_y, 0),
                maximum=PositionMM(max_x, max_y, ceiling),
            ),
            ceiling_height_mm=ceiling,
            reflectance_ppm=(
                (480_000,) * 6 if name == "backyard" else (620_000,) * 6
            ),
            illumination_ppm=(light,) * 6,
        )
        for name, min_x, min_y, max_x, max_y, ceiling, light in plan
    ]
    # Doors 1.4m wide minimum; the hallway connects everything and the
    # backyard opens from the hallway, exactly as the blueprint says.
    portals = [
        PhysicalPortal(
            portal_id=f"door-{index}",
            region_ids=tuple(sorted(pair)),
            axis=axis,
            plane_mm=plane,
            aperture_min_mm=ap_min,
            aperture_max_mm=ap_max,
            height_mm=2_050,
        )
        for index, (pair, axis, plane, ap_min, ap_max) in enumerate((
            (("kitchen", "dining"),        "x",  7_000, 1_800, 3_200),
            (("dining", "daddys-room"),    "x", 12_000, 1_800, 3_200),
            (("daddys-room", "wcs-room"),  "x", 16_000, 1_800, 3_200),
            (("her-room", "hallway"),      "x",  5_600, 6_900, 8_300),
            (("hallway", "library"),       "x",  9_000, 6_900, 8_300),
            (("library", "tv-room"),       "x", 14_000, 6_900, 8_300),
            (("kitchen", "hallway"),       "y",  5_000, 5_600, 7_000),
            (("dining", "hallway"),        "y",  5_000, 7_300, 8_700),
            (("hallway", "backyard"),      "y", 10_000, 6_000, 7_400),
        ))
    ]
    # (id, absolute x, y, radius, mass, reflectance) — clearances are
    # pre-checked against every neighbouring radius and wall.
    furniture = (
        # kitchen, relaid uncluttered: a clear ring around the table.
        ("table",           2_000,  1_500, 850, 28_000, (700_000, 620_000, 520_000, 450_000, 410_000, 390_000)),
        ("table-chair",     2_000,  3_000, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        ("bowl",            4_500,    800, 160,    700, (920_000, 910_000, 900_000, 880_000, 860_000, 840_000)),
        ("cup",             5_200,    800, 110,    300, (880_000, 870_000, 860_000, 840_000, 820_000, 800_000)),
        ("apple",           5_650,    900,  90,    180, (820_000, 260_000, 190_000, 170_000, 160_000, 150_000)),
        # her room: bed wall, soft things, desk corner, art at eye height.
        ("bed",             1_200,  8_800, 900, 40_000, (760_000, 720_000, 690_000, 640_000, 600_000, 560_000)),
        ("pillow",          1_200,  7_600, 260,  1_200, (900_000, 890_000, 880_000, 860_000, 840_000, 820_000)),
        ("blanket",         3_400,  9_300, 300,    900, (860_000, 620_000, 540_000, 500_000, 470_000, 450_000)),
        ("toy-bear",        4_800,  9_200, 180,    400, (520_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
        ("toy-chest",       1_000,  5_600, 500,  8_000, (560_000, 430_000, 340_000, 300_000, 280_000, 260_000)),
        ("desk",            4_400,  6_400, 800, 32_000, (430_000, 330_000, 260_000, 220_000, 200_000, 190_000)),
        ("desk-chair",      4_400,  7_800, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        ("curtains",        2_800,  9_700, 250,  1_500, (930_000, 760_000, 620_000, 540_000, 500_000, 470_000)),
        ("wall-art-shapes", 300,    7_000, 150,    600, (950_000, 300_000, 850_000, 200_000, 750_000, 250_000)),
        ("wall-art-weather", 300,   6_100, 150,    600, (350_000, 550_000, 900_000, 400_000, 650_000, 300_000)),
        ("glow-stars",      3_300,  7_200, 120,    300, (940_000, 930_000, 700_000, 400_000, 300_000, 260_000)),
        # library: shelves on the north wall, the reading lamp, a book home.
        ("shelf-a",        10_000,  9_500, 400, 30_000, (500_000, 400_000, 330_000, 290_000, 270_000, 250_000)),
        ("shelf-b",        12_500,  9_500, 400, 30_000, (500_000, 400_000, 330_000, 290_000, 270_000, 250_000)),
        ("book",           12_000,  7_500, 140,    900, (640_000, 520_000, 420_000, 360_000, 330_000, 310_000)),
        ("lamp",           13_500,  5_400, 180,  2_200, (880_000, 850_000, 780_000, 700_000, 650_000, 620_000)),
        # tv room: the watching place.
        ("television",     17_000,  9_200, 700, 12_000, (140_000, 140_000, 150_000, 160_000, 170_000, 180_000)),
        ("sofa",           17_000,  6_800, 950, 45_000, (360_000, 330_000, 380_000, 420_000, 430_000, 420_000)),
        ("rug",            15_000,  6_000, 600,  5_000, (540_000, 420_000, 360_000, 330_000, 320_000, 310_000)),
        # dining room.
        ("dining-table",    9_500,  2_500, 900, 30_000, (700_000, 620_000, 520_000, 450_000, 410_000, 390_000)),
        ("dining-chair",    9_500,  4_200, 320,  6_000, (300_000, 260_000, 240_000, 220_000, 210_000, 200_000)),
        # backyard: slide, swing, sandbox, garden patch under the sky.
        ("slide",           3_000, 13_500, 900, 25_000, (700_000, 720_000, 740_000, 700_000, 650_000, 600_000)),
        ("swing",           7_000, 14_000, 700, 15_000, (480_000, 430_000, 380_000, 340_000, 320_000, 300_000)),
        ("sandbox",        11_500, 13_500, 1_100, 60_000, (820_000, 780_000, 700_000, 620_000, 560_000, 520_000)),
        ("garden-patch",   16_500, 13_500, 1_200, 80_000, (300_000, 380_000, 300_000, 260_000, 240_000, 220_000)),
    )
    # (release ng/s per odour channel, tastants ug, surface mK, compliance
    #  ppm, roughness um, moisture ppm) — same channel meanings as before:
    #  0 fruit ester - 1 cooked savoury - 2 dairy fat - 3 wood/earth
    #  4 fabric dust - 5 paper ink - 6 warm electronics - 7 soap
    material_of = {
        "bed":             ((0, 0, 0, 0, 900, 0, 0, 120),   (0, 300, 0, 800, 0),        294_000, 600_000, 200, 55_000),
        "pillow":          ((0, 0, 0, 0, 600, 0, 0, 300),   (0, 300, 0, 800, 0),        294_000, 900_000, 120, 48_000),
        "blanket":         ((0, 0, 0, 0, 1_000, 0, 0, 150), (0, 300, 0, 800, 0),        294_000, 850_000, 150, 50_000),
        "toy-bear":        ((0, 0, 0, 0, 1_200, 0, 0, 60),  (0, 300, 0, 900, 0),        294_000, 800_000, 300, 42_000),
        "toy-chest":       ((0, 0, 0, 600, 80, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 50_000, 60, 20_000),
        "desk":            ((0, 0, 0, 700, 60, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "desk-chair":      ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "curtains":        ((0, 0, 0, 0, 700, 0, 0, 100),   (0, 0, 0, 600, 0),          293_000, 800_000, 120, 45_000),
        "wall-art-shapes": ((0, 0, 0, 30, 20, 700, 0, 0),   (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "wall-art-weather": ((0, 0, 0, 30, 20, 700, 0, 0),  (0, 0, 0, 1_800, 0),        294_000, 60_000, 50, 18_000),
        "glow-stars":      ((0, 0, 0, 0, 10, 0, 120, 0),    (0, 0, 0, 900, 0),          294_000, 30_000, 10, 3_000),
        "book":            ((0, 0, 0, 40, 30, 900, 0, 0),   (0, 0, 0, 2_000, 0),        294_000, 60_000, 60, 18_000),
        "shelf-a":         ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "shelf-b":         ((0, 0, 0, 900, 70, 300, 0, 0),  (0, 0, 0, 1_500, 0),        294_000, 40_000, 45, 20_000),
        "lamp":            ((0, 0, 0, 0, 20, 0, 260, 0),    (0, 0, 0, 400, 0),          310_000, 20_000, 10, 2_000),
        "television":      ((0, 0, 0, 0, 40, 0, 700, 0),    (0, 0, 0, 400, 0),          306_000, 20_000, 5, 1_000),
        "sofa":            ((0, 0, 0, 120, 1_500, 0, 0, 90), (0, 300, 0, 800, 0),       294_000, 700_000, 400, 52_000),
        "rug":             ((0, 0, 0, 0, 2_200, 0, 0, 40),  (0, 300, 0, 900, 0),        294_000, 500_000, 800, 46_000),
        "table":           ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "table-chair":     ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "dining-table":    ((0, 0, 0, 800, 50, 0, 0, 0),    (0, 0, 0, 1_500, 0),        294_000, 40_000, 40, 20_000),
        "dining-chair":    ((0, 0, 0, 200, 400, 0, 0, 0),   (0, 0, 0, 1_500, 0),        294_000, 300_000, 40, 26_000),
        "bowl":            ((0, 300, 120, 0, 0, 0, 0, 200), (400, 900, 100, 200, 1_200), 294_000, 30_000, 8, 90_000),
        "apple":           ((4_200, 0, 0, 0, 0, 0, 0, 0),   (140_000, 200, 26_000, 900, 300), 292_000, 120_000, 15, 850_000),
        "cup":             ((0, 60, 40, 0, 0, 0, 0, 400),   (0, 0, 0, 0, 0),            291_000, 25_000, 6, 900_000),
        "slide":           ((0, 0, 0, 0, 30, 0, 80, 0),     (0, 0, 0, 300, 0),          288_000, 15_000, 8, 10_000),
        "swing":           ((0, 0, 0, 300, 400, 0, 0, 0),   (0, 200, 0, 900, 0),        288_000, 250_000, 300, 30_000),
        "sandbox":         ((0, 0, 0, 100, 600, 0, 0, 0),   (0, 100, 0, 400, 0),        290_000, 400_000, 900, 25_000),
        "garden-patch":    ((0, 0, 0, 1_600, 300, 0, 0, 0), (0, 100, 200, 700, 100),    289_000, 450_000, 700, 320_000),
    }
    reservoir_seconds = 864_000
    objects = [
        EmbodiedObject(
            name,
            radius,
            mass,
            PositionMM(x, y, 0),
            reflectance_ppm=reflectance,
            material=ObjectMaterialState(
                odorant_reservoir_nanograms=tuple(
                    rate * reservoir_seconds for rate in material_of[name][0]
                ),
                odorant_release_nanograms_per_second=material_of[name][0],
                tastant_mass_micrograms=material_of[name][1],
                surface_temperature_millikelvin=material_of[name][2],
                compliance_ppm=material_of[name][3],
                roughness_micrometers=material_of[name][4],
                moisture_ppm=material_of[name][5],
            ),
        )
        for name, x, y, radius, mass, reflectance in furniture
    ]
    # Each room's air is derived from what stands in it, exactly as before,
    # with room membership resolved from each thing's authored position.
    def room_of(x: int, y: int) -> str:
        for name, min_x, min_y, max_x, max_y, _c, _l in plan:
            if min_x <= x < max_x and min_y <= y < max_y:
                return name
        raise RuntimeError(f"authored thing stands outside every room ({x},{y})")

    settled_seconds = 3_600
    channel_count = len(material_of["apple"][0])
    room_air = {name: [0] * channel_count for name, *_rest in plan}
    for name, x, y, *_rest in furniture:
        for channel, rate in enumerate(material_of[name][0]):
            room_air[room_of(x, y)][channel] += rate * settled_seconds
    bounds_of = {name: (min_x, min_y, max_x, max_y, ceiling)
                 for name, min_x, min_y, max_x, max_y, ceiling, _l in plan}
    regions = [
        replace(
            region,
            air=AirVolumeState(
                volume_cubic_mm=(
                    (bounds_of[region.region_id][2] - bounds_of[region.region_id][0])
                    * (bounds_of[region.region_id][3] - bounds_of[region.region_id][1])
                    * bounds_of[region.region_id][4]
                ),
                odorant_mass_nanograms=tuple(room_air[region.region_id]),
            ),
        )
        for region in regions
    ]
    portals = [
        replace(portal, air_flow_cubic_mm_per_second=2_000_000)
        for portal in portals
    ]
    return regions, portals, objects


def _home_thermal_anatomy(
    regions: Iterable[Any], portals: Iterable[Any]
) -> Any:
    """Derive one bounded core/skin/home heat circuit from signed geometry.

    This is Phase-1 virtual anatomy, not a claim about a later manufactured
    body. The child mass is the CDC female 48.5-month median rounded to one
    gram; the two-node capacity uses the published 2.98 kJ/(kg K) whole-body
    specific heat and a declared 90/10 core/skin partition. Air capacity and
    portal conductance derive from each room volume and doorway flow. The only
    authored building value is a finite HVAC boundary conductance at 23 C.
    """

    from dsf_ai_service.substrate.bounded_home_thermal_physics import (
        ConductiveThermalEdge,
        ThermalBathEdge,
        ThermalPowerSource,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        CoupledThermalAnatomy,
    )

    ordered_regions = tuple(sorted(regions, key=lambda item: item.region_id))
    ordered_portals = tuple(sorted(portals, key=lambda item: item.portal_id))
    if not ordered_regions or any(item.air is None for item in ordered_regions):
        raise ValueError("the thermal home requires finite signed air volumes")
    room_index = {
        region.region_id: index for index, region in enumerate(ordered_regions)
    }
    # 1210.120 J/(m3 K), represented as uJ/(m3 mK).
    air_capacity_per_cubic_meter = 1_210_120
    room_capacities = tuple(
        region.air.volume_cubic_mm * air_capacity_per_cubic_meter
        // 1_000_000_000
        for region in ordered_regions
    )
    # 15.878 kg * 2.98 kJ/(kg K) = 47,316.44 J/K. On the module's
    # uJ/mK lattice that is 47,316,440, split without losing one quantum.
    whole_body_capacity = 15_878 * 2_980
    skin_capacity = whole_body_capacity // 10
    core_capacity = whole_body_capacity - skin_capacity
    skin_index = len(ordered_regions)
    core_index = skin_index + 1
    portal_edges = []
    for portal in ordered_portals:
        flow = portal.air_flow_cubic_mm_per_second
        if flow is None:
            raise ValueError("the thermal home requires signed portal air flow")
        left, right = portal.region_ids
        portal_edges.append(
            ConductiveThermalEdge(
                room_index[left],
                room_index[right],
                flow * air_capacity_per_cubic_meter // 1_000_000,
            )
        )
    metabolic_power = 41_500_000
    return CoupledThermalAnatomy(
        node_ids=(
            *(f"air:{region.region_id}" for region in ordered_regions),
            "body:cutaneous-shell",
            "body:core",
        ),
        initial_temperatures_millikelvin=(
            *(
                (293_150 if region.region_id == "backyard" else 296_150)
                for region in ordered_regions
            ),
            303_150,
            309_950,
        ),
        capacities_microjoules_per_millikelvin=(
            *room_capacities,
            skin_capacity,
            core_capacity,
        ),
        fixed_conductive_edges=(
            *portal_edges,
            ConductiveThermalEdge(core_index, skin_index, 6_102_941),
        ),
        room_air_node_by_region_id=tuple(
            (region.region_id, room_index[region.region_id])
            for region in ordered_regions
        ),
        skin_node_index=skin_index,
        core_node_index=core_index,
        skin_air_conductance_microwatts_per_kelvin=5_928_571,
        # Indoor rooms couple to the authored HVAC boundary; the backyard
        # is outdoors and couples hard to the open sky's own ambient.
        bath_edges=tuple(
            (
                ThermalBathEdge(index, 293_150, 2_500_000_000)
                if region.region_id == "backyard"
                else ThermalBathEdge(index, 296_150, 250_000_000)
            )
            for index, region in enumerate(ordered_regions)
        ),
        power_sources=(ThermalPowerSource(core_index, metabolic_power),),
        parameter_provenance=(
            "CDC female 48.5-month median body mass rounded to 15.878 kilograms",
            "measured whole-body specific heat 2.98 kilojoules per kilogram-kelvin",
            "FAO-WHO-UNU girls age 3-to-10 basal metabolic equation at declared mass",
            "published passive two-node core-skin heat-balance structure",
            "authored Phase-1 virtual-home 296150-millikelvin HVAC boundary",
        ),
    )


def _world_authorized() -> bool:
    """Has a human explicitly authorized giving her a place to be?"""

    return os.environ.get(WORLD_ENV, "").strip().lower() in (
        "1",
        "true",
        "on",
        "yes",
    )


WORLD_AUTHORIZED = _world_authorized()
_world_authority: Any = None
_world_rebuild_reason: str | None = None


def _world_key() -> str:
    """The world's authentication key, derived from her identity.

    Deterministic and stable for one organism: the world authenticates its
    own observations, and a key that changed between processes would make
    every earlier receipt unverifiable.
    """

    return hashlib.sha256(
        f"guala.embodiment.world.v1:{_genesis_identity()}".encode("utf-8")
    ).hexdigest()


def _home_book_sequence_from_pages(
    record: Any,
    pages: list[bytes],
) -> Any | None:
    from dsf_ai_service.substrate.embodiment_world import (
        ContactOpticalSurfaceSequence,
    )
    from dsf_ai_service.substrate.physical_optical_surface_asset import (
        physical_optical_surface_from_png,
    )

    if not (
        record.origin_kind == "project_gutenberg"
        and record.origin_locator == HOME_BOOK_GUTENBERG_SOURCE_URL
        and record.edition == HOME_BOOK_GUTENBERG_EDITION
        and record.language_tag == "en"
        and record.material_kind == "gutenberg_text"
    ):
        return None
    sequence = ContactOpticalSurfaceSequence(
        object_id=HOME_BOOK_OBJECT_ID,
        source_receipt_sha256=record.receipt_sha256,
        surfaces=tuple(
            physical_optical_surface_from_png(page).surface
            for page in pages
        ),
    )
    sequence.verify()
    return sequence


def _home_book_optical_surface_sequence() -> Any | None:
    """Rebuild the exact bounded Alice page surfaces from immutable custody."""

    records = tuple(
        record
        for record in _source_media_store.inventory(
            verify_source_bytes=True
        )
        if record.origin_kind == "project_gutenberg"
        and record.origin_locator == HOME_BOOK_GUTENBERG_SOURCE_URL
        and record.edition == HOME_BOOK_GUTENBERG_EDITION
        and record.language_tag == "en"
        and record.material_kind == "gutenberg_text"
    )
    if not records:
        return None
    if len(records) != 1:
        raise RuntimeError("the home book has multiple immutable source records")
    record = records[0]
    source = _source_media_store.source_bytes(record.receipt_sha256)
    if hashlib.sha256(source).hexdigest() != record.source_bytes_sha256:
        raise RuntimeError("the home book source bytes changed after custody")
    pages = _gutenberg_pages(source.decode("utf-8"))
    return _home_book_sequence_from_pages(record, pages)


def _companion_body_surface_sites() -> tuple[Any, ...]:
    """Declare the bounded skin sites used by exact reciprocal contact.

    These are morphology, not gesture meanings.  Their material coefficients
    are pinned by three explicit substrate-scale reference responses:

    * a fully covered 60 x 80 mm palm compressed by 1 mm carries 9.6 N;
    * the same palm sliding 10 mm over one second carries 0.96 N tangentially;
    * the same palm held across a 1 K difference for one second transfers
      0.48 J.

    The coefficients are therefore derived once from those declarations and
    are never tuned by a lesson, behavior, or observer.  Guala's temperature
    is read from her live cutaneous thermal node; 310.15 K is the participant
    surface's declared finite reservoir boundary until that body gains its own
    thermal circulation.
    """

    if not TOUCH_RECEPTORS_AUTHORIZED:
        return ()
    from dsf_ai_service.substrate.body_surface_contact import (
        BodySurfaceMaterial,
        ExactVector3,
    )
    from dsf_ai_service.substrate.embodiment_world import (
        MountedBodySurfaceSite,
    )

    exact = Fraction
    x = ExactVector3(exact(1), exact(0), exact(0))
    y = ExactVector3(exact(0), exact(1), exact(0))
    z = ExactVector3(exact(0), exact(0), exact(1))
    skin = BodySurfaceMaterial(
        normal_stiffness_millinewtons_per_micrometre_per_square_micrometre=(
            exact(1, 500_000_000)
        ),
        tangential_damping_millinewton_microseconds_per_micrometre_per_square_micrometre=(
            exact(1, 50_000)
        ),
        thermal_conductance_nanowatts_per_square_micrometre_millikelvin=(
            exact(1, 10_000)
        ),
    )

    def site(
        body_id: str,
        site_id: str,
        centre: tuple[int, int, int],
        normal: Any,
        tangent_u: Any,
        tangent_v: Any,
        half_extents: tuple[int, int],
        cutaneous_topology_index: int | None,
    ) -> Any:
        return MountedBodySurfaceSite(
            body_id=body_id,
            site_id=site_id,
            local_centre_micrometres=ExactVector3(
                *(exact(value) for value in centre)
            ),
            outward_normal=normal,
            tangent_u=tangent_u,
            tangent_v=tangent_v,
            half_extent_u_micrometres=exact(half_extents[0]),
            half_extent_v_micrometres=exact(half_extents[1]),
            material=skin,
            reference_temperature_millikelvin=310_150,
            cutaneous_topology_index=cutaneous_topology_index,
        )

    # The existing 3 x 9 contact sheet is Guala's declared body-surface
    # lattice.  These sparse morphology sites bind seven previously unnamed
    # locations without changing their native topology or receptor law.
    guala = (
        site("guala-body-1", "forehead", (230_000, 0, 1_100_000), x, y, z, (70_000, 55_000), 4),
        site("guala-body-1", "crown", (0, 0, 1_250_000), z, x, y, (75_000, 65_000), 3),
        site("guala-body-1", "left-shoulder", (180_000, 170_000, 900_000), x, y, z, (80_000, 75_000), 9),
        site("guala-body-1", "front-torso", (240_000, 0, 700_000), x, y, z, (150_000, 190_000), 13),
        site("guala-body-1", "right-shoulder", (180_000, -170_000, 900_000), x, y, z, (80_000, 75_000), 17),
        site("guala-body-1", "left-palm", (300_000, 150_000, 500_000), x, y, z, (30_000, 40_000), 18),
        site("guala-body-1", "right-palm", (300_000, -150_000, 500_000), x, y, z, (30_000, 40_000), 26),
    )
    # A facing participant has the opposite heading.  Its local lateral
    # tangents are therefore reversed so the two world-space contact bases
    # become exactly aligned when the surfaces oppose each other.
    participant = (
        site("person-body-1", "left-palm", (300_000, 200_000, 800_000), x, y.scaled(exact(-1)), z, (30_000, 40_000), None),
        site("person-body-1", "right-palm", (300_000, -200_000, 800_000), x, y.scaled(exact(-1)), z, (30_000, 40_000), None),
        site("person-body-1", "front-torso", (250_000, 0, 1_000_000), x, y.scaled(exact(-1)), z, (180_000, 260_000), None),
        site("person-body-1", "perioral", (260_000, 0, 1_450_000), x, y.scaled(exact(-1)), z, (25_000, 20_000), None),
        site("person-body-1", "downward-palm", (250_000, -180_000, 1_050_000), z.scaled(exact(-1)), x.scaled(exact(-1)), y.scaled(exact(-1)), (30_000, 40_000), None),
    )
    return guala + participant


_COMPANION_CONTACT_OPERATIONS = {
    "hold_hand",
    "hug",
    "forehead_kiss",
    "head_pat",
    "shoulder_touch",
}


def _companion_contact_profile(
    operation: str,
    recipient_body_id: str,
) -> tuple[tuple[Any, ...], int]:
    """Translate one human-facing care invitation into physical surfaces.

    The returned command contains no gesture name, reward, affect, meaning, or
    expected response.  Those remain consequences for the organism's own
    receptors and chemistry to settle.
    """

    from dsf_ai_service.substrate.embodiment_world import BodySurfaceActuation

    def contact(
        actor_site: str,
        recipient_site: str,
        compression_micrometres: int,
        tangential_u_micrometres: int = 0,
        tangential_v_micrometres: int = 0,
    ) -> Any:
        return BodySurfaceActuation(
            actor_site_id=actor_site,
            recipient_body_id=recipient_body_id,
            recipient_site_id=recipient_site,
            compression_micrometres=compression_micrometres,
            tangential_u_micrometres=tangential_u_micrometres,
            tangential_v_micrometres=tangential_v_micrometres,
        )

    # Every committed action's consequence must land strictly inside one
    # 250 ms intake hop, and the world's material law needs at least
    # 3 ms of contact; a sustained hold is the caller repeating contacts.
    profiles = {
        "hold_hand": (
            (contact("right-palm", "left-palm", 1_000),),
            200_000,
        ),
        "hug": (
            (
                contact("front-torso", "front-torso", 2_000),
                contact("left-palm", "right-shoulder", 1_000),
                contact("right-palm", "left-shoulder", 1_000),
            ),
            200_000,
        ),
        "forehead_kiss": (
            (contact("perioral", "forehead", 500),),
            50_000,
        ),
        "head_pat": (
            (contact("downward-palm", "crown", 750, 12_000, 0),),
            75_000,
        ),
        "shoulder_touch": (
            (contact("right-palm", "left-shoulder", 1_000),),
            100_000,
        ),
    }
    try:
        actuations, duration = profiles[operation]
    except KeyError as error:
        raise ValueError("unknown companion contact profile") from error
    for actuation in actuations:
        actuation.verify()
    return actuations, duration


def _world() -> Any:
    """Her place, restored from disk or built once and persisted."""

    global _world_authority
    if not WORLD_AUTHORIZED:
        raise RuntimeError("no world is mounted")
    if _world_authority is not None:
        return _world_authority
    from dsf_ai_service.substrate.embodiment_world import (
        BodyReceptorGeometry,
        EmbodiedBody,
        EmbodimentPort,
        PORT_ID,
        SECOND_BODY_PORT_ID,
        PoseMM,
        PositionMM,
        SolarCoupling,
    )
    from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
        ThermallyCoupledEmbodimentWorldAuthority,
    )

    # WHERE HER SENSES ARE ON HER BODY. Without this her world-body is a
    # sphere with no face: no nose, no tongue, no skin, no eye or ear
    # position — which is exactly why every object in her home reached her
    # sight and NOTHING else. A saturation is the concentration at which a
    # receptor reads full; hers are set from what her own home actually
    # holds, so a kitchen with an apple in it reads part-way up her fruit
    # channel rather than pinned at nothing or pinned at everything.
    her_receptors = BodyReceptorGeometry(
        # HER WORLD'S CONVENTION IS THAT X IS FORWARD AND Y IS SIDEWAYS: it
        # rotates a receptor offset by quarter turns, and facing north sends
        # +x to +y. Her face therefore sits on +x and her ears either side on
        # y — declared the other way round, her eyes and hands pointed off to
        # her left, which is measurably why she could face a thing and still
        # not be touching it.
        retinal_offset_mm=PositionMM(200, 0, 1_100),
        left_ear_offset_mm=PositionMM(0, 0, 1_050),
        right_ear_offset_mm=PositionMM(0, 180, 1_050),
        # HER HANDS ARE IN FRONT OF HER AND LOW, where a small child's are.
        # At chest height her touch patch never overlapped anything standing
        # on the floor of her world — measured, she could walk right up to
        # her toy bear and still not be touching it. Low and in front, she
        # touches what she has walked up to and faced, and not what is beside
        # her, which is how hands work.
        touch_offset_mm=PositionMM(200, 0, 150),
        touch_radius_mm=300,
        oral_offset_mm=PositionMM(200, 0, 1_020),
        oral_radius_mm=60,
        olfactory_offset_mm=PositionMM(210, 0, 1_060),
        odorant_saturation_nanograms_per_cubic_meter=(1_000_000,) * 8,
        tastant_saturation_micrograms=(200_000,) * 5,
        touch_mass_span_grams=45_000,
        touch_temperature_min_millikelvin=273_000,
        touch_temperature_max_millikelvin=323_000,
        touch_roughness_span_micrometers=1_000,
    )

    regions, portals, objects = _home_rooms_and_things()
    home_book_sequence = _home_book_optical_surface_sequence()
    authority = ThermallyCoupledEmbodimentWorldAuthority(
        authority_key=_world_key(),
        thermal_anatomy=_home_thermal_anatomy(regions, portals),
        self_body_id="guala-body-1",
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                # She starts in her own room, beside the bed.
                PoseMM(PositionMM(2_600, 7_600, 0), 0),
                radius_mm=250,
                reach_mm=800,
                receptor_geometry=her_receptors,
            ),
            # Her world requires a second body and always did: it was built
            # for her AND someone with her. This is the body a person
            # occupies when they are in the room. It does nothing on its own.
            EmbodiedBody(
                "person-body-1",
                # The companion starts in the hallway spine.
                PoseMM(PositionMM(7_300, 7_500, 0), 180_000),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "person-body-1"),
        ),
        regions=regions,
        portals=portals,
        initial_objects=objects,
        contact_optical_surface_sequences=(
            () if home_book_sequence is None else (home_book_sequence,)
        ),
        body_surface_sites=_companion_body_surface_sites(),
        # Nine places and nine doors; the caps state the lean bound.
        max_regions=12,
        max_portals=16,
        # The real sun: the backyard lives under the open sky, and her
        # room's window wall takes a quarter share of it through the
        # curtained north wall. The day flows on the real clock.
        solar_coupling=SolarCoupling(
            outdoor_region_ids=("backyard",),
            window_share_ppm_by_region_id=(("her-room", 250_000),),
        ),
    )
    path = STATE_ROOT / WORLD_STATE_FILE
    matched_recovery = _world_recovery_marker_present()
    if matched_recovery:
        if _restored is None:
            raise RuntimeError(
                "matched world recovery requires the restored CURRENT body"
            )
        stored_body = _read_world_recovery_pair(
            _restored.pointer.state_sha256
        )
    else:
        stored_body = path.read_bytes() if path.is_file() else None
    if stored_body is not None:
        try:
            authority.restore_encoded(
                stored_body,
                allow_authenticated_physical_manifest_migration=True,
                allow_legacy_thermal_genesis=True,
            )
            # The renovation runs FIRST: a lived four-room world grows into
            # the declared home while every lived thing is preserved; the
            # geometry and material migrations then act on the grown plan.
            authority.migrate_declared_home_topology()
            authority.migrate_declared_body_receptor_geometry()
            authority.migrate_declared_material_transport()
        except (ValueError, TypeError, RuntimeError) as error:
            # Her pose now changes through native motor discharge. A stored
            # world therefore contains causal organism history and may never
            # be silently deleted or rebuilt from authored defaults.
            raise RuntimeError(
                "the persisted embodiment world could not restore; refusing "
                "to replace Guala's causal pose history "
                f"({type(error).__name__}: {error})"
            ) from error
    restored_book = next(
        (
            item
            for item in authority.observation_snapshot().objects
            if item.object_id == HOME_BOOK_OBJECT_ID
        ),
        None,
    )
    if restored_book is None:
        raise RuntimeError("the persistent home lost its physical book")
    if (
        restored_book.optical_surface is not None
        and home_book_sequence is None
    ):
        raise RuntimeError(
            "the persisted book page has no immutable source custody"
        )
    current_body = authority.encoded_snapshot()
    if matched_recovery and stored_body != current_body:
        if not authority.home_renovation_performed:
            raise RuntimeError(
                "ordinary matched world restore changed its canonical bytes"
            )
        # The home renovation is the one authorized byte change under
        # matched custody: the release boundary retires the stale pair
        # and re-pairs the recovery store with the renovated world
        # before anything is reachable.
        _generations_dir, _associations_dir = _world_recovery_directories()
        stale_association = _associations_dir / (
            _restored.pointer.state_sha256 + WORLD_RECOVERY_ASSOCIATION_SUFFIX
        )
        if stale_association.is_file():
            stale_association.unlink()
        _publish_world_recovery_pair(
            _restored.pointer.state_sha256,
            current_body,
        )
    if stored_body != current_body:
        # A new home and the one authorized bare-world-to-thermal migration
        # become durable before the authority is made reachable.  A restart
        # therefore cannot reset body heat to authored genesis.
        _persist_world_body(current_body)
    if not matched_recovery and _restored is not None:
        # One release-boundary bootstrap converts the legacy independently
        # named world into a CURRENT-selected recovery pair. The marker is
        # written last, so a crash before it leaves the old recovery law in
        # force and a crash after it has a complete verified pair.
        _complete_world_recovery_bootstrap(
            _restored.pointer.state_sha256,
            current_body,
        )
    _world_authority = authority
    return authority


def _persist_world(authority: Any) -> None:
    """Write the world beside her body, atomically."""

    _persist_world_body(authority.encoded_snapshot())


def _canonical_world_recovery_digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"{label} is not a canonical SHA-256 receipt")
    return value


def _sync_world_recovery_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _world_recovery_directories() -> tuple[Path, Path]:
    generations = STATE_ROOT / WORLD_RECOVERY_GENERATIONS_DIRECTORY
    associations = STATE_ROOT / WORLD_RECOVERY_ASSOCIATIONS_DIRECTORY
    for path in (generations, associations):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError("world recovery custody path is not a real directory")
    return generations, associations


def _durably_write_immutable_world_recovery_body(
    destination: Path,
    body: bytes,
) -> None:
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise RuntimeError("world recovery immutable path changed type")
        existing = destination.read_bytes()
        if not hmac.compare_digest(existing, body):
            raise RuntimeError("world recovery immutable body changed")
        return
    stage = destination.parent / f".stage-{uuid.uuid4()}"
    descriptor = os.open(
        stage,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        view = memoryview(body)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise RuntimeError("world recovery write ended early")
            offset += written
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        try:
            stage.unlink()
        except FileNotFoundError:
            pass
        raise
    else:
        os.close(descriptor)
    try:
        if destination.exists():
            existing = destination.read_bytes()
            if not hmac.compare_digest(existing, body):
                raise RuntimeError("world recovery immutable body raced")
        else:
            os.replace(stage, destination)
            os.chmod(destination, 0o444)
        _sync_world_recovery_directory(destination.parent)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def _encode_world_recovery_association(
    body_state_sha256: str,
    world_state_sha256: str,
    world_state_bytes: int,
) -> bytes:
    body_digest = bytes.fromhex(
        _canonical_world_recovery_digest(
            body_state_sha256, "world recovery body receipt"
        )
    )
    world_digest = bytes.fromhex(
        _canonical_world_recovery_digest(
            world_state_sha256, "world recovery world receipt"
        )
    )
    if (
        isinstance(world_state_bytes, bool)
        or not isinstance(world_state_bytes, int)
        or not 0 < world_state_bytes <= WORLD_RECOVERY_MAX_BYTES
    ):
        raise RuntimeError("world recovery world byte count is outside its bound")
    core = _WORLD_RECOVERY_ASSOCIATION_BODY.pack(
        WORLD_RECOVERY_ASSOCIATION_MAGIC,
        WORLD_RECOVERY_ASSOCIATION_VERSION,
        body_digest,
        world_digest,
        world_state_bytes,
    )
    return core + hashlib.sha256(core).digest()


def _decode_world_recovery_association(
    body: bytes,
) -> tuple[str, str, int]:
    if len(body) != WORLD_RECOVERY_ASSOCIATION_BYTES:
        raise RuntimeError("world recovery association changed byte count")
    core = body[: _WORLD_RECOVERY_ASSOCIATION_BODY.size]
    receipt = body[_WORLD_RECOVERY_ASSOCIATION_BODY.size :]
    if not hmac.compare_digest(receipt, hashlib.sha256(core).digest()):
        raise RuntimeError("world recovery association receipt changed")
    magic, version, body_digest, world_digest, world_bytes = (
        _WORLD_RECOVERY_ASSOCIATION_BODY.unpack(core)
    )
    if (
        magic != WORLD_RECOVERY_ASSOCIATION_MAGIC
        or version != WORLD_RECOVERY_ASSOCIATION_VERSION
    ):
        raise RuntimeError("world recovery association schema changed")
    if not 0 < world_bytes <= WORLD_RECOVERY_MAX_BYTES:
        raise RuntimeError("world recovery association exceeds its byte bound")
    return body_digest.hex(), world_digest.hex(), world_bytes


def _publish_world_recovery_pair(
    body_state_sha256: str,
    world_body: bytes,
) -> dict[str, object]:
    """Make one content-verified world pair durable before body CURRENT."""

    body_receipt = _canonical_world_recovery_digest(
        body_state_sha256, "world recovery body receipt"
    )
    if (
        not isinstance(world_body, bytes)
        or not world_body
        or len(world_body) > WORLD_RECOVERY_MAX_BYTES
    ):
        raise RuntimeError("world recovery body is outside its exact byte bound")
    world_receipt = hashlib.sha256(world_body).hexdigest()
    generations, associations = _world_recovery_directories()
    generation = (
        generations
        / f"{world_receipt}{WORLD_RECOVERY_GENERATION_SUFFIX}"
    )
    association = (
        associations
        / f"{body_receipt}{WORLD_RECOVERY_ASSOCIATION_SUFFIX}"
    )
    _durably_write_immutable_world_recovery_body(generation, world_body)
    association_body = _encode_world_recovery_association(
        body_receipt,
        world_receipt,
        len(world_body),
    )
    _durably_write_immutable_world_recovery_body(association, association_body)
    return {
        "body_state_sha256": body_receipt,
        "world_state_sha256": world_receipt,
        "world_state_bytes": len(world_body),
    }


def _read_world_recovery_pair(body_state_sha256: str) -> bytes:
    body_receipt = _canonical_world_recovery_digest(
        body_state_sha256, "world recovery body receipt"
    )
    generations, associations = _world_recovery_directories()
    association = (
        associations
        / f"{body_receipt}{WORLD_RECOVERY_ASSOCIATION_SUFFIX}"
    )
    if association.is_symlink() or not association.is_file():
        raise RuntimeError("CURRENT has no matched world recovery association")
    associated_body, world_receipt, world_bytes = (
        _decode_world_recovery_association(association.read_bytes())
    )
    if associated_body != body_receipt:
        raise RuntimeError("world recovery association names a different body")
    generation = (
        generations
        / f"{world_receipt}{WORLD_RECOVERY_GENERATION_SUFFIX}"
    )
    if generation.is_symlink() or not generation.is_file():
        raise RuntimeError("matched world recovery generation is absent")
    if generation.stat().st_size != world_bytes:
        raise RuntimeError("matched world recovery generation changed byte count")
    world_body = generation.read_bytes()
    if not hmac.compare_digest(
        hashlib.sha256(world_body).hexdigest(), world_receipt
    ):
        raise RuntimeError("matched world recovery generation receipt changed")
    return world_body


def _world_recovery_marker_present() -> bool:
    marker = STATE_ROOT / WORLD_RECOVERY_MARKER_FILE
    if not marker.exists():
        return False
    if marker.is_symlink() or not marker.is_file():
        raise RuntimeError("world recovery marker changed type")
    if marker.read_bytes() != WORLD_RECOVERY_MARKER_BODY:
        raise RuntimeError("world recovery marker changed")
    return True


def _complete_world_recovery_bootstrap(
    body_state_sha256: str,
    world_body: bytes,
) -> None:
    _publish_world_recovery_pair(body_state_sha256, world_body)
    marker = STATE_ROOT / WORLD_RECOVERY_MARKER_FILE
    _durably_write_immutable_world_recovery_body(
        marker,
        WORLD_RECOVERY_MARKER_BODY,
    )
    _sync_world_recovery_directory(STATE_ROOT)


def _reconcile_world_recovery_store(pointer: Any) -> tuple[int, int]:
    """Retain only CURRENT and its explicit predecessor's matched worlds."""

    if not _world_recovery_marker_present():
        return 0, 0
    current = _canonical_world_recovery_digest(
        pointer.state_sha256, "CURRENT body receipt"
    )
    predecessor = pointer.predecessor_state_sha256
    expected_bodies = {current}
    if predecessor is not None:
        expected_bodies.add(
            _canonical_world_recovery_digest(
                predecessor, "CURRENT predecessor receipt"
            )
        )
    generations, associations = _world_recovery_directories()
    retired_count = 0
    retired_bytes = 0
    for path in tuple(STATE_ROOT.glob(".world-*.stage")):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("persistent world stage changed type")
        retired_bytes += path.stat().st_size
        retired_count += 1
        path.unlink()
    referenced_worlds: set[str] = set()
    current_found = False
    for path in tuple(associations.iterdir()):
        if path.name.startswith(".stage-"):
            retired_bytes += path.stat().st_size
            retired_count += 1
            path.unlink()
            continue
        if path.is_symlink() or not path.is_file() or not path.name.endswith(
            WORLD_RECOVERY_ASSOCIATION_SUFFIX
        ):
            raise RuntimeError("world recovery associations contain an unknown artifact")
        named_body = path.name[: -len(WORLD_RECOVERY_ASSOCIATION_SUFFIX)]
        _canonical_world_recovery_digest(named_body, "world association filename")
        associated_body, world_receipt, _world_bytes = (
            _decode_world_recovery_association(path.read_bytes())
        )
        if associated_body != named_body:
            raise RuntimeError("world recovery association filename changed")
        if named_body not in expected_bodies:
            retired_bytes += path.stat().st_size
            retired_count += 1
            path.unlink()
            continue
        referenced_worlds.add(world_receipt)
        current_found = current_found or named_body == current
    if not current_found:
        raise RuntimeError("CURRENT has no retained matched world association")
    for path in tuple(generations.iterdir()):
        if path.name.startswith(".stage-"):
            retired_bytes += path.stat().st_size
            retired_count += 1
            path.unlink()
            continue
        if path.is_symlink() or not path.is_file() or not path.name.endswith(
            WORLD_RECOVERY_GENERATION_SUFFIX
        ):
            raise RuntimeError("world recovery generations contain an unknown artifact")
        receipt = path.name[: -len(WORLD_RECOVERY_GENERATION_SUFFIX)]
        _canonical_world_recovery_digest(receipt, "world generation filename")
        body = path.read_bytes()
        if len(body) > WORLD_RECOVERY_MAX_BYTES or hashlib.sha256(body).hexdigest() != receipt:
            raise RuntimeError("world recovery generation content changed")
        if receipt not in referenced_worlds:
            retired_bytes += len(body)
            retired_count += 1
            path.unlink()
    _sync_world_recovery_directory(associations)
    _sync_world_recovery_directory(generations)
    _sync_world_recovery_directory(STATE_ROOT)
    return retired_count, retired_bytes


def _persist_world_body(body: bytes) -> None:
    """Atomically write one already-authenticated world persistence body."""

    path = STATE_ROOT / WORLD_STATE_FILE
    stage = STATE_ROOT / f".world-{uuid.uuid4()}.stage"
    if (
        not isinstance(body, bytes)
        or not body
        or len(body) > WORLD_RECOVERY_MAX_BYTES
    ):
        raise RuntimeError("persistent world body is outside its exact byte bound")
    descriptor = os.open(
        stage,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        view = memoryview(body)
        offset = 0
        while offset < len(view):
            written = os.write(descriptor, view[offset:])
            if written <= 0:
                raise RuntimeError("persistent world write ended early")
            offset += written
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        try:
            stage.unlink()
        except FileNotFoundError:
            pass
        raise
    else:
        os.close(descriptor)
    os.replace(stage, path)
    _sync_world_recovery_directory(STATE_ROOT)


def _world_retinal_luminance(substreams: tuple[Any, ...]) -> tuple[float, ...]:
    """Collapse the world's six-band retina onto the one she actually has.

    Her card surface declares 27 monochrome sites and the world declares the
    same 27 cells in six spectral bands, so each cell's bands are averaged
    into its luminance.  She has no colour receptors, and averaging is the
    honest reduction rather than discarding five bands or inventing a site.
    """

    return _world_retinal_luminance_endpoints(substreams)[1]


def _world_palmar_contact_endpoints(
    substreams: tuple[Any, ...],
) -> tuple[Fraction, Fraction]:
    """Read the existing exact palmar-contact receptor at both world edges."""

    matches = tuple(
        stream
        for stream in substreams
        if stream.sensor_id == "W1-body-surface-receptors"
        and stream.substream_id == "palmar-contact"
    )
    if len(matches) != 1 or len(matches[0].normalized_signal) != 2:
        raise RuntimeError("the world lost its unique palmar contact channel")
    values = tuple(
        Fraction(value).limit_denominator(1_000_000)
        for value in matches[0].normalized_signal
    )
    if any(value not in {Fraction(0), Fraction(1)} for value in values):
        raise RuntimeError("palmar contact left its exact binary boundary")
    return values


def _retinal_heading_offset_millidegrees_from_axes(
    axes: tuple[Any, ...] | list[Any],
) -> int:
    """Resolve the retinal carrier from one explicit native body observation."""

    matches = tuple(axis for axis in axes if axis[1] == "neck_yaw")
    if len(matches) != 1:
        raise RuntimeError("the native body has no unique neck-yaw axis")
    position = matches[0][3]
    if isinstance(position, bool) or not isinstance(position, int):
        raise RuntimeError("the native neck-yaw position changed representation")
    if not -180_000 <= position <= 180_000:
        raise RuntimeError("the native neck-yaw position is outside retinal geometry")
    return position


def _eyelid_transmission_from_axes(
    axes: tuple[Any, ...] | list[Any],
) -> Fraction:
    """Exact fraction of incident light admitted by the two native eyelids.

    The current body has one retinal field and two equal physical eyelid
    apertures. Their summed open extent therefore carries the admitted-light
    fraction relative to their summed anatomical maximum. This is transport
    physics only: it does not label sleep, attention, or cognitive state.
    """

    apertures: list[tuple[int, int, int]] = []
    for name in ("left_eyelid_aperture", "right_eyelid_aperture"):
        matches = tuple(axis for axis in axes if axis[1] == name)
        if len(matches) != 1:
            raise RuntimeError(f"the native body has no unique {name} axis")
        axis = matches[0]
        if axis[2] != "micrometre":
            raise RuntimeError(f"the native {name} axis changed physical unit")
        position, minimum, maximum = axis[3], axis[4], axis[6]
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (position, minimum, maximum)
        ):
            raise RuntimeError(f"the native {name} axis changed representation")
        if not minimum <= position <= maximum or minimum >= maximum:
            raise RuntimeError(f"the native {name} axis is outside its anatomy")
        apertures.append((position, minimum, maximum))
    admitted = sum(position - minimum for position, minimum, _ in apertures)
    possible = sum(maximum - minimum for _, minimum, maximum in apertures)
    return Fraction(admitted, possible)


def _retinal_transmission_trajectory(
    transmission: Fraction | tuple[Fraction, ...],
    frame_count: int,
) -> tuple[Fraction, ...]:
    """Validate one exact eyelid transmission value per retinal frame."""

    values = (
        (transmission,) * frame_count
        if isinstance(transmission, Fraction)
        else transmission
    )
    if len(values) != frame_count or any(
        value < 0 or value > 1 for value in values
    ):
        raise ValueError("eyelid transmission changed its retinal clock or bounds")
    return values


def _current_retinal_body_axes() -> tuple[Any, ...]:
    """Read the one persisted native body observation used by visual transport."""

    # The native organism permits one mutable resident borrow at a time.  Keep
    # this shared body read behind the same short, re-entrant transport lock as
    # every transition so an unattended interval cannot race any episode
    # builder.  This lock has no cognitive authority and never enters physics.
    with _transition_lock:
        restored, _ = _runtime()
        return tuple(restored.organism.readiness().articulated_body_axes)


def _current_retinal_heading_offset_millidegrees() -> int:
    """Read the persisted native neck axis that physically carries the retina."""

    return _retinal_heading_offset_millidegrees_from_axes(
        _current_retinal_body_axes()
    )


def _world_retinal_luminance_endpoints(
    substreams: tuple[Any, ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Collapse exact before/after spectral retina onto monochrome cells."""

    before_totals = [0.0] * CARD_SURFACE_PORT_COUNT
    after_totals = [0.0] * CARD_SURFACE_PORT_COUNT
    counts = [0] * CARD_SURFACE_PORT_COUNT
    for stream in substreams:
        cell = stream.topology_index // 6
        if cell >= CARD_SURFACE_PORT_COUNT:
            continue
        if len(stream.normalized_signal) != 2:
            raise ValueError("world retinal transition changed endpoint count")
        before_totals[cell] += float(stream.normalized_signal[0])
        after_totals[cell] += float(stream.normalized_signal[1])
        counts[cell] += 1
    return tuple(
        tuple(
            min(1.0, max(0.0, totals[index] / counts[index]))
            if counts[index]
            else 0.0
            for index in range(CARD_SURFACE_PORT_COUNT)
        )
        for totals in (before_totals, after_totals)
    )


def _world_chemistry(
    before: Any,
    after: Any,
    *,
    source_time_end: Fraction | None = None,
) -> tuple[tuple[Fraction, ...] | None, tuple[Fraction, ...] | None]:
    """What the objects around her taste and smell of, from the world itself.

    The world declares every object's odorant reservoir, release rate and
    tastant mass; her eight olfactory and five gustatory channels ARE that
    world's eight odorant and five tastant channels.  Nothing is mapped by
    hand and nothing is invented — where the world says a sense is
    unavailable in this interval, she smells and tastes nothing, which is a
    lawful state and not an absent sense.
    """

    taste, smell = _world_chemistry_endpoints(
        before,
        after,
        source_time_end=source_time_end,
    )
    return taste[1], smell[1]


def _world_chemistry_endpoints(
    before: Any,
    after: Any,
    *,
    source_time_end: Fraction | None = None,
) -> tuple[
    tuple[tuple[Fraction, ...] | None, tuple[Fraction, ...] | None],
    tuple[tuple[Fraction, ...] | None, tuple[Fraction, ...] | None],
]:
    """Read each local chemical field once and preserve both endpoints."""

    if not CHEMORECEPTION_AUTHORIZED:
        return (None, None), (None, None)
    if source_time_end is None:
        source_time_end = Fraction(INTAKE_HOP_MILLISECONDS, 1000)
    from dsf_ai_service.substrate.w1_coupled_material_sensory_physics import (
        material_receptor_substreams,
    )

    streams = material_receptor_substreams(
        world_authority=_world(),
        before=before,
        after=after,
        source_time_start=Fraction(0),
        source_time_end=source_time_end,
    )

    def collapse(
        sense: Any,
        count: int,
    ) -> tuple[tuple[Fraction, ...] | None, tuple[Fraction, ...] | None]:
        ports = streams.get(sense, ())
        if not ports:
            return None, None
        endpoints = ([Fraction(0)] * count, [Fraction(0)] * count)
        for port in ports:
            if port.topology_index < count:
                for endpoint, value in zip(
                    endpoints,
                    (port.normalized_signal[0], port.normalized_signal[-1]),
                    strict=True,
                ):
                    exact = Fraction(value).limit_denominator(1_000_000)
                    endpoint[port.topology_index] = min(
                        Fraction(1),
                        max(Fraction(0), exact),
                    )
        return tuple(endpoints[0]), tuple(endpoints[1])

    return (
        collapse(PhysicalSense.TASTE, TASTE_SITE_COUNT),
        collapse(PhysicalSense.SMELL, SMELL_SITE_COUNT),
    )


def _world_displacement(before: Any, after: Any) -> tuple[Fraction, ...]:
    """How her body actually moved, as exact fractions of the declared span."""

    def pose(snapshot: Any) -> Any:
        return next(
            body for body in snapshot.bodies if body.body_id == snapshot.self_body_id
        ).pose

    start, end = pose(before), pose(after)
    turn = end.heading_millidegrees - start.heading_millidegrees
    while turn > WORLD_TURN_SPAN_MILLIDEGREES:
        turn -= 2 * WORLD_TURN_SPAN_MILLIDEGREES
    while turn < -WORLD_TURN_SPAN_MILLIDEGREES:
        turn += 2 * WORLD_TURN_SPAN_MILLIDEGREES
    moved = (
        Fraction(end.position.x - start.position.x, WORLD_DISPLACEMENT_SPAN_MM),
        Fraction(end.position.y - start.position.y, WORLD_DISPLACEMENT_SPAN_MM),
        Fraction(end.position.z - start.position.z, WORLD_DISPLACEMENT_SPAN_MM),
        Fraction(turn, WORLD_TURN_SPAN_MILLIDEGREES),
    )
    for channel, value in zip(DISPLACEMENT_CHANNELS, moved):
        if not Fraction(-1) <= value <= Fraction(1):
            raise ValueError(
                f"a move of {float(value)} spans on {channel!r} is larger than "
                "the declared displacement span a receptor can transduce"
            )
    return moved


VESTIBULAR_ENV = "GUALA_VESTIBULAR"


def _vestibular_authorized() -> bool:
    """Has a human explicitly authorized growing displacement receptors?"""

    return os.environ.get(VESTIBULAR_ENV, "").strip().lower() in (
        "1",
        "true",
        "on",
        "yes",
    )


VESTIBULAR_AUTHORIZED = _vestibular_authorized()
DISPLACEMENT_CHANNELS = (
    "translation-x",
    "translation-y",
    "translation-z",
    "rotation-yaw",
)
DISPLACEMENT_SITE_COUNT = len(DISPLACEMENT_CHANNELS)
DISPLACEMENT_PORT_COUNT = (
    DISPLACEMENT_SITE_COUNT if VESTIBULAR_AUTHORIZED else 0
)
DISPLACEMENT_SENSOR_ID = "organism-displacement-receptors"
NATIVE_VESTIBULAR_SENSOR_ID = "mounted-yaw-canal"
NATIVE_VESTIBULAR_SUBSTREAM_ID = "local-hair-bundle-0"
DISPLACEMENT_QUANTITY = "body-displacement-fraction"
DISPLACEMENT_UNIT = "fraction-of-declared-displacement-span"

# Separate local somatosensory anatomy for the vocal body. These do not reuse
# the whole-body displacement ports: airflow, larynx, mouth, and facial skin
# occupy distinct physical places even when one articulatory act moves them on
# the same clock.
ARTICULATORY_BODY_CHANNELS = (
    "respiratory-flow",
    "laryngeal-glottis",
    "oral-aperture",
    "perioral-skin",
)
ARTICULATORY_BODY_QUANTITIES = (
    "respiratory-volume-velocity",
    "laryngeal-glottal-opening",
    "oral-aperture-area",
    "perioral-skin-area-deformation",
)
ARTICULATORY_BODY_DECLARED_SPANS = (4_000, 320, 1_000, 600)
ARTICULATORY_BODY_PORT_COUNT = len(ARTICULATORY_BODY_CHANNELS)
ARTICULATORY_BODY_SENSOR_ID = "articulatory-body-mechanoreceptors"
ARTICULATORY_BODY_UNIT = "fraction-of-declared-articulatory-mechanical-span"

# Two local temperature receptor sites, appended after every existing body
# site so no living source place is rebound. They receive exact core and
# cutaneous-node temperatures from the coupled world/body heat circuit. The
# 273..323 K interval is a receptor sensitivity span, not a comfort scale.
THERMAL_CHANNELS = ("cutaneous-shell", "core")
THERMAL_PORT_COUNT = len(THERMAL_CHANNELS) if WORLD_AUTHORIZED else 0
THERMAL_SENSOR_ID = "organism-core-and-cutaneous-thermoreceptors"
THERMAL_QUANTITY = "thermoreceptor-temperature"
THERMAL_UNIT = "fraction-of-declared-273000-to-323000-millikelvin-span"
THERMAL_MIN_MILLIKELVIN = 273_000
THERMAL_MAX_MILLIKELVIN = 323_000


CHEMORECEPTION_ENV = "GUALA_CHEMORECEPTION"


def _chemoreception_authorized() -> bool:
    """Has a human explicitly authorized growing taste and smell?"""

    return os.environ.get(CHEMORECEPTION_ENV, "").strip().lower() in (
        "1",
        "true",
        "on",
        "yes",
    )


CHEMORECEPTION_AUTHORIZED = _chemoreception_authorized()
# The five gustatory modalities a mammal actually has.  Not a menu of
# flavours: these are receptor classes.
TASTE_CHANNELS = ("sweet", "salt", "sour", "bitter", "umami")
# Eight olfactory receptor classes.  A real epithelium has hundreds; eight is
# what this body declares, and the surface says so rather than implying a
# nose.
SMELL_CHANNELS = (
    "aldehyde", "ester", "terpene", "amine",
    "sulphur", "phenol", "lactone", "acid",
)
TASTE_SITE_COUNT = len(TASTE_CHANNELS)
SMELL_SITE_COUNT = len(SMELL_CHANNELS)
TASTE_PORT_COUNT = TASTE_SITE_COUNT if CHEMORECEPTION_AUTHORIZED else 0
SMELL_PORT_COUNT = SMELL_SITE_COUNT if CHEMORECEPTION_AUTHORIZED else 0
TASTE_SENSOR_ID = "organism-gustatory-surface"
SMELL_SENSOR_ID = "organism-olfactory-epithelium"
TASTE_QUANTITY = "gustatory-contact-concentration"
SMELL_QUANTITY = "olfactory-volatile-concentration"
CHEMICAL_UNIT = "fraction-of-declared-saturating-concentration"


# Localized interoceptive afferents are not mounted. The former four-channel
# body-wide bookkeeping projection was not biology and has been retired.
INTEROCEPTION_PORT_COUNT = 0
LESSON_PORT_COUNT = (
    CARD_SURFACE_PORT_COUNT
    + EAR_PORT_COUNT
    + TOUCH_PORT_COUNT
    + INTEROCEPTION_PORT_COUNT
    + TASTE_PORT_COUNT
    + SMELL_PORT_COUNT
    + DISPLACEMENT_PORT_COUNT
    + ARTICULATORY_BODY_PORT_COUNT
    + THERMAL_PORT_COUNT
)
# One physical instant has one complete joint sensorium and therefore one
# unchanged L0-L4 evaluation.  Its declared groups preserve the distinct
# receptor structures (retina, each cochlea, contact sheet, internal milieu,
# gustatory surface, olfactory epithelium, and body displacement) without
# splitting the simultaneous field into repeated evaluations.
LESSON_OCCURRENCE_COUNT = 1
# Four declaration frames mirror the ratified four-frame sight anatomy
# episode and the browser visual capture contract's minimum frame count.
CARD_SURFACE_FRAME_COUNT = 4
CARD_SURFACE_SENSOR_ID = "card-visual-surface"
EAR_SENSOR_ID = "organism-ear-pressure"
# The ratified retinal receptor law (optical_receptor_work.rs): cognitive
# cohort genesis admits only sight ports carrying a spectral-irradiance
# fraction of the declared retinal reference irradiance, in [0, 1].
RETINAL_QUANTITY = "retinal-spectral-irradiance"
RETINAL_UNIT = "fraction-of-declared-retinal-reference-irradiance"
# The mounted auditory receptor law (auditory_receptor_work.rs) admits only
# sound ports carrying one tonotopic band's normalized root-mean-square
# pressure.  DEFECT FIXED 2026-08-06: these ports used to declare
# `normalized_physical_excitation` / `normalized_binary64`, which is not a
# physical quantity — it is a statement that a number was normalized.  A
# receptor law cannot key on that, and it was one of the three recorded
# reasons the ears carried transport instead of sensation.
COCHLEAR_QUANTITY = "cochlear-band-pressure"
COCHLEAR_UNIT = "fraction-of-declared-cochlear-reference-pressure"
# The mounted tactile receptor law (tactile_receptor_work.rs) admits only touch
# ports carrying the fraction of ONE declared contact site's own area that the
# touched object's footprint covers, in [0, 1].
CONTACT_QUANTITY = "contact-site-occupancy"
CONTACT_UNIT = "fraction-of-declared-contact-site-area"
# The legacy ear port declaration, kept VERBATIM for the unauthorized roster.
# It is not a physical quantity and no receptor law can key on it — which is
# exactly why the live ears carry transport instead of sensation.  It stays
# because the living organism's episodes must not change until growing ears is
# authorized; it is replaced, not edited, when they are.
PHYSICAL_QUANTITY = "normalized_physical_excitation"
PHYSICAL_UNIT = "normalized_binary64"
JOINT_RELEVANCE_PROFILE = b"guala.production.curriculum_unit_joint_relevance.v1"
# The authored growth-DNA contact conductance ratified by the formation-level
# explicit_optical_seed and the growth-DNA runtime tests (500 pS).
AUTHORED_SEED_CONDUCTANCE_PICOSIEMENS = 500
# Transport/intake contract only (not sensory physics, not cognition): one
# ambient auditory settlement is bounded to this many seconds, and the same
# bound is the caller-authored maximum causal interval for ambient intake.
AMBIENT_INTAKE_MAX_SECONDS = 30
# One presentation is delivered as successive short occurrences ("hops") on
# this app's declared 250 ms capture interval (the same sampling interval the
# visual capture contract below declares).  Longer single occurrences
# accumulate receptor gate work past the exact dissipation lattice and are
# refused by neuron physics, so the hop is a transport contract, not physics.
INTAKE_HOP_MILLISECONDS = 250
# A body action is one exact world-mechanical tick. Longer sensory presences
# remain 250 ms intake hops, but multiplying one authored displacement into
# 250 whole-cognitive vestibular successors duplicates the action rather than
# improving its physical resolution.
WORLD_BODY_ACTION_MILLISECONDS = 1
INTAKE_HOP_MAX_FRAMES = 256
assert (
    LESSON_PORT_COUNT * INTAKE_HOP_MAX_FRAMES
    <= MAX_NATIVE_SAMPLES_PER_SETTLEMENT
), "declared lesson hop exceeds the ratified settlement sample bound"
# A dark or silent interval retains the clock of the mounted receptor that
# can physically change fastest.  With the cochlea mounted that is its native
# 160-sample envelope observation below, not the retired one-millisecond PCM
# transport grid.  Transport ending never changes the receptor clock.

# ---------------------------------------------------------------------------
# The cochlea (transport layer, not physics)
#
# The basilar membrane's travelling wave assigns frequency to place BEFORE any
# hair cell transduces anything (von Bekesy), so the place decomposition
# belongs to the sensor, in the same layer where the camera's `/255.0`
# luminance extraction already lives.  What crosses into the organism is one
# normalized root-mean-square pressure per tonotopic place per retained
# instant; the receptor law downstream is exact-rational and knows nothing
# about filters.
#
# The filterbank is the fourth-order gammatone already compiled into the wheel
# (native/guala_core/src/auditory.rs), with Glasberg-Moore ERB channel spacing.
# NAMED CONCESSION (auditory design 2026-08-06 section 8.3): a gammatone is a
# fitted MODEL of basilar-membrane mechanics, not a derivation from one.  It is
# a sensor characteristic, exactly like the camera's sensor response curve, and
# it is declared as such rather than discovered later.
COCHLEAR_SAMPLE_RATE_HZ = 16_000
COCHLEAR_OBSERVATION_HOP_SAMPLES = 160
COCHLEAR_LOWEST_CENTRE_HZ = 80.0
COCHLEAR_HIGHEST_CENTRE_HZ = 7_500.0
# The cochlear observation's own declared amplitude lattice: 24 bits.
#
# Every sensor reports on a lattice — the card surface reports luminance on its
# 8-bit sensor's k/255 lattice — and the ear is no different.  Two facts set
# this one:
#
#  * The capture is 16-bit PCM, but a band envelope is a weighted average over
#    160 samples of a fourth-order filter, so it genuinely resolves BETWEEN the
#    capture's own steps; 24 bits is the standard studio capture depth and does
#    not over-claim what the filterbank can distinguish.
#  * The bound is DERIVED, not chosen: the receptor law squares the transported
#    value, so a lattice of 2^-m gives integrals whose denominators divide
#    2^(2m+3)·25, and the ratified exact-rational residue is i128/u128.  That
#    admits m <= 59; a full binary64 envelope (denominators past 2^60 before
#    squaring) does NOT, and the organism refuses it honestly with ResidueWidth
#    rather than rounding it away.  m = 24 sits far inside that ceiling.
COCHLEAR_PRESSURE_LATTICE = 1 << 24


class CochlearChannel(NamedTuple):
    centre_hz: float
    erb_width_hz: float


def _erb_width_hz(frequency_hz: float) -> float:
    """Glasberg--Moore equivalent rectangular bandwidth in hertz."""

    return 24.7 * (1.0 + 4.37e-3 * frequency_hz)


def _erb_rate(frequency_hz: float) -> float:
    return 21.4 * math.log10(1.0 + 4.37e-3 * frequency_hz)


def _frequency_from_erb_rate(rate: float) -> float:
    return (10.0 ** (rate / 21.4) - 1.0) / 4.37e-3


def _cochlear_channels() -> tuple[CochlearChannel, ...]:
    lower = _erb_rate(COCHLEAR_LOWEST_CENTRE_HZ)
    upper = _erb_rate(COCHLEAR_HIGHEST_CENTRE_HZ)
    span = COCHLEAR_CHANNELS_PER_EAR - 1
    channels = []
    for index in range(COCHLEAR_CHANNELS_PER_EAR):
        rate = lower + (upper - lower) * index / span
        centre = _frequency_from_erb_rate(rate)
        channels.append(CochlearChannel(centre, _erb_width_hz(centre)))
    return tuple(channels)


COCHLEAR_CHANNELS = _cochlear_channels()


def _cochlear_coefficients() -> tuple[list[float], list[float], list[float]]:
    """Fourth-order gammatone poles: a cascade of four identical complex poles.

    The 1.019 multiplier is the standard fourth-order ERB correction.
    """

    pole_real: list[float] = []
    pole_imag: list[float] = []
    injection: list[float] = []
    for channel in COCHLEAR_CHANNELS:
        radius = math.exp(
            -2.0 * math.pi * 1.019 * channel.erb_width_hz / COCHLEAR_SAMPLE_RATE_HZ
        )
        angle = 2.0 * math.pi * channel.centre_hz / COCHLEAR_SAMPLE_RATE_HZ
        pole_real.append(radius * math.cos(angle))
        pole_imag.append(radius * math.sin(angle))
        injection.append(1.0 - radius)
    return pole_real, pole_imag, injection


def _cochlear_envelopes(signal: list[float]) -> list[tuple[float, ...]]:
    """Per-channel RMS envelopes of one continuous acoustic capture.

    One causal pass over the whole capture, so cochlear ringing decays across
    hop boundaries exactly as a real basilar membrane's does instead of being
    reset every 250 ms.  Returns one frame per
    ``COCHLEAR_OBSERVATION_HOP_SAMPLES`` samples; each frame carries one
    non-negative envelope in [0, 1] per tonotopic place.
    """

    pole_real, pole_imag, injection = _cochlear_coefficients()
    envelopes, _phases, _advances = auditory_gammatone_field(
        signal, pole_real, pole_imag, injection
    )
    lattice = float(COCHLEAR_PRESSURE_LATTICE)
    quantized: list[tuple[float, ...]] = []
    for frame in envelopes:
        row: list[float] = []
        for value in frame:
            level = round(value * lattice)
            # 2026-08-07 truth repair: this used to CLAMP resonance
            # overshoot to full scale — a clamp in the layer feeding a
            # law whose discipline is refusal, never a clamp.  An
            # envelope outside the declared lattice is now refused with
            # its value, and the whole intake aborts untouched.
            if level < 0 or level > COCHLEAR_PRESSURE_LATTICE:
                raise ValueError(
                    "cochlear envelope outside the declared pressure "
                    f"lattice ({value!r}); refusing rather than clamping"
                )
            row.append(level / lattice)
        quantized.append(tuple(row))
    return quantized

# Lesson presentation modes.  "full" is the ordinary lesson: the whole card
# surface is lit and the tutor speaks.  "partial" is a glimpse of part of a
# familiar card: only part of the card geometry is lit, the rest of the
# surface is genuinely dark, and the tutor is silent (the ears are not
# driven, so the acoustic cohort stays quiescent).
#
# The lit subset is chosen deterministically from the ports' declared
# topology coordinates, never randomly: the first
# PARTIAL_PRESENTATION_SITE_COUNT card sites in row-major (row, column)
# order — the top strip of the card surface.  That subset is exactly a
# contiguous prefix of the authored growth-DNA contact chain, which joins
# consecutive row-major card sites (site i to site i+1 at 500 pS), so the
# glimpse's recurrence current has an unbroken chain path to every remaining
# member of the retained formation.  Physical-mosaic admission also requires
# the cue to be a strict subset of the formation's members, which this
# 12-of-27 prefix is by construction.
#
# Measured (2026-08-05, headless, alphabet-a): the left-column-region
# variant of this subset (column < 4 of every row) behaves identically —
# both commit lawfully and neither admits a mosaic — because admission is
# blocked upstream of the subset choice by the optical energy barrier
# documented on _partial_card_lesson_hop_episodes.
PRESENTATION_MODES = ("full", "partial")
PARTIAL_PRESENTATION_SITE_COUNT = 12
assert 0 < PARTIAL_PRESENTATION_SITE_COUNT < CARD_SURFACE_PORT_COUNT
# After the glimpse the presentation genuinely ends; the surface stays dark
# and the room stays silent while the recurrence current settles.  Eight
# ended hops mirror the ratified native admission sequence (one partial
# optical episode followed by up to eight dark episodes) proven in
# organism_runtime.rs and resident_cognitive_formation.rs.
PARTIAL_PRESENTATION_ENDED_HOP_COUNT = 8
# Quiescent hops declaring the genuinely ended full presentation.  Under the
# stimulus-boundary retention law (ratified 2026-08-05) the experience closes
# on the first settlement whose interval carried zero exogenous optical
# energy — the first of these dark hops — so the cohort's pending experience
# finalizes at presentation end with its real electrical participation masks.
# Measured F2 (2026-08-05): after real electricity the 27-site chain never
# returns to global quiescence, so the tail's job is to declare the true dark
# environment at the boundary, not to wait for silence.  This is transport
# (how long the app keeps declaring the true dark, silent environment),
# never physics.
LESSON_ENDED_HOP_COUNT = 2

# ----- Live sight (browser camera intake, 2026-08-06) -----
# Transport contract only (not sensory physics, not cognition): a browser
# samples its real camera at this app's declared 250 ms hop interval (the
# capture contract below) and posts batches of whole frames.  Every bound is
# an existing declared constant, never a new magic number:
# - one posted frame becomes exactly one 250 ms hop on the same timebase and
#   the same 27-receptor retinal roster every card lesson uses;
# - the minimum batch mirrors the ratified four-frame sight anatomy episode
#   (CARD_SURFACE_FRAME_COUNT), which the capture contract has always
#   declared as its minimum frame count;
# - the maximum batch is the same per-request hop count unattended time
#   delivers per interval (PARTIAL_PRESENTATION_ENDED_HOP_COUNT = 8 hops =
#   2 s of declared capture per request), which the capture contract has
#   always declared as its maximum frame count;
# - the client-declared capture span of one batch is bounded by the same
#   declared ambient intake window the auditory transport uses
#   (AMBIENT_INTAKE_MAX_SECONDS).
# Provenance is honest and caller-declared: the batch names its source as
# the live camera and carries the client's own capture timestamps; they are
# recorded as transport evidence, never injected into physics.  The ears
# carry TRUE 0.0 silence on every live-sight hop — silence is a lawful state
# of the mounted sensorium (ratified 2026-08-05: no single-sense
# experiences), and no audio is ever fabricated: the ears have no
# transduction law until the tonotopic rebirth.
LIVE_SIGHT_MIN_FRAMES = CARD_SURFACE_FRAME_COUNT
LIVE_SIGHT_MAX_FRAMES = PARTIAL_PRESENTATION_ENDED_HOP_COUNT
LIVE_SIGHT_SOURCE = "live-camera"
LIVE_SIGHT_SCHEMA = "guala.live_sight_capture.v1"
LIVE_SIGHT_INTAKE_ENDPOINT = "/api/v1/visual/live-frames"
LIVE_AUDIOVISUAL_SOURCE = "live-camera-microphone"
LIVE_AUDIOVISUAL_SCHEMA = "guala.live_audiovisual_capture.v1"
LIVE_AUDIOVISUAL_INTAKE_ENDPOINT = "/api/v1/sensory/audiovisual"
NATIVE_PRESSURE_AUDIO_ENDPOINT = "/api/v1/guala/native-pressure.wav"
NATIVE_PRESSURE_AUDIO_CACHE_COUNT = 4
NATIVE_PRESSURE_AUDIO_CACHE_MAX_ENTRY_BYTES = (
    AMBIENT_INTAKE_MAX_SECONDS * COCHLEAR_SAMPLE_RATE_HZ * struct.calcsize("<h")
)
NATIVE_PRESSURE_AUDIO_CACHE_MAX_BYTES = (
    NATIVE_PRESSURE_AUDIO_CACHE_COUNT
    * NATIVE_PRESSURE_AUDIO_CACHE_MAX_ENTRY_BYTES
)


def _bounded_native_pressure_audio_cache(
    candidates: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Keep only newest exact PCM bodies inside the declared byte envelope."""

    retained: list[dict[str, Any]] = []
    retained_bytes = 0
    for candidate in reversed(tuple(candidates)):
        pcm = candidate.get("pcm_s16le")
        if not isinstance(pcm, bytes):
            continue
        byte_count = len(pcm)
        if (
            byte_count > NATIVE_PRESSURE_AUDIO_CACHE_MAX_ENTRY_BYTES
            or byte_count > NATIVE_PRESSURE_AUDIO_CACHE_MAX_BYTES - retained_bytes
            or len(retained) == NATIVE_PRESSURE_AUDIO_CACHE_COUNT
        ):
            continue
        retained.append(candidate)
        retained_bytes += byte_count
    retained.reverse()
    return tuple(retained)


def _retain_native_articulation_audio(
    retained: tuple[dict[str, Any], ...],
    articulation_audio: dict[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Retain only selected emitted speech, unchanged by later ear intake."""

    if articulation_audio is None:
        return retained
    return _bounded_native_pressure_audio_cache((
        *retained,
        articulation_audio,
    ))

# ----- Continuous lived time (2026-08-08) -----
# This loop is transport, never cognitive cause. It continuously samples the
# actual persistent world and presents one exact 250 ms physical interval at
# a time to the native organism.  A transport lock may protect that indivisible
# physical interval, but it must never turn several successive moments into one
# database-style transaction: an arriving external experience belongs at the
# next physical boundary, not after an eight-hop batch.  Deferred persistence
# remains independent of this admission boundary.
#
# There is no artificial one-minute gap and no fabricated dark room. If the
# world is unavailable, continuous experience is unavailable. Python does not
# choose a need, direction, object, thought, or action here.
UNATTENDED_TIME_ENV = "GUALA_UNATTENDED_TIME"
UNATTENDED_HOPS_PER_INTERVAL = 1
CONTINUOUS_INTERVAL_MILLISECONDS = (
    UNATTENDED_HOPS_PER_INTERVAL * INTAKE_HOP_MILLISECONDS
)

_ORGANISM_IDENTITY_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)

_restored: RestoredNativeOrganism | None = None
_admission: NativeResidentResourceAdmission | None = None
_boot_error: str | None = None
_public_observation_body: bytes | None = None
_public_observation_etag: str | None = None
_runtime_proof_body: bytes | None = None
_runtime_build_identity: dict[str, str] | None = None
_last_transition_evidence: dict[str, Any] | None = None
# One bounded observation witness, not organism memory.  A tested physical
# alternative is otherwise visible only until the next unattended interval,
# which can replace the public cache before a client receives the event that
# produced it.  This record contains no field body and never enters cognition;
# each later tested event replaces it in constant process memory.
_last_tested_prediction_evidence: dict[str, Any] | None = None
_last_tested_affective_balance_evidence: dict[str, Any] | None = None
_last_tested_localized_fluid_chemistry_evidence: dict[str, Any] | None = None
_last_tested_articulation_evidence: dict[str, Any] | None = None
# The last four bounded emitted-pressure bodies are a read-only, process-local
# outward surface. They are assigned only after resident transitions succeed,
# never restored as organism state, and never read by settlement or cognition.
_native_pressure_audio_cache: tuple[dict[str, Any], ...] = ()
# Bounded read-only witnesses. They never enter organism state or settlement.
_last_causal_cross_context_use_evidence: dict[str, Any] | None = None
_last_intrinsic_curiosity_evidence: dict[str, Any] | None = None
_last_social_experience_evidence: dict[str, Any] | None = None
_last_tested_physical_choice_evidence: dict[str, Any] | None = None
# Lived intervals since the last exact recovery checkpoint. This count only
# requests work from the external custodian; it never schedules, pauses, or
# decides organism physics. An abandoned trajectory changes the epoch so a
# checkpoint cloned from that branch can never publish.
_pending_unsealed_intervals: int = 0
_pending_chain_predecessor_sha: str | None = None
_checkpoint_requested = threading.Event()
_custodian_stop = threading.Event()
_custodian_thread: threading.Thread | None = None
_custody_trajectory_epoch = 0
_last_custodian_evidence: dict[str, object] | None = None
_pending_custody_cleanup: PendingNativeOrganismCleanup | None = None
_pending_custody_candidate: dict[str, Any] | None = None


def _checkpoint_every_intervals() -> int:
    raw = os.environ.get("GUALA_CHECKPOINT_EVERY_INTERVALS", "4")
    try:
        value = int(raw)
    except ValueError:
        return 1
    return max(1, value)


# One bounded record of the custodian's most recent failure, cleared by the
# next successful seal. Transport health evidence only — it never schedules,
# decides, or touches organism state; it exists so a stuck custodian is a
# visible fact on the public observation instead of a stderr whisper.
_last_custodian_error: dict[str, object] | None = None


def _unsealed_interval_ceiling() -> int:
    """Derived, not heuristic: the durability contract bounds loss to one
    custody cadence. One full cadence may lawfully be pending and a second
    may commit while the custodian's cycle is in flight; a third means the
    contract is already broken, so lived time pauses instead of deepening
    the loss (the 2026-08-31 freeze hid behind exactly this kind of
    unbounded silent accumulation)."""

    return _checkpoint_every_intervals() * 2


# Transport stopwatch: cumulative wall-clock milliseconds per pipeline stage.
# Written only under _transition_lock, read for per-interval deltas and a log
# line. Pure transport measurement; no organism state, no cognitive authority.
_transport_stage_wall_ms: dict[str, float] = {}
# Two constant-size read-only play witnesses. They never enter the organism,
# select an action, or survive restart. The first holds one qualifying physical
# episode while ordinary native settlement determines whether the same retained
# formation later returns to the body with a different displacement. The second
# holds only the completed compact evidence until another restart.
_sensorimotor_play_candidate: dict[str, Any] | None = None
_last_sensorimotor_play_evidence: dict[str, Any] | None = None
# One bounded, read-only body-owned-laughter witness. It observes only exact
# transaction-local physics already produced by the organism: learned playful
# formation recurrence, affect/body settlement, motor-to-articulator transfer,
# vocal-body/PCM/self-hearing consequence, and body/world return. It cannot
# cause an act and does not survive process restart.
_body_owned_laughter_candidate: dict[str, Any] | None = None
_last_body_owned_laughter_evidence: dict[str, Any] | None = None
# One bounded, read-only turn-taking witness. The external body's authenticated
# world action and Guala's own native action remain separate authorities; exact
# predecessor/successor world receipts are the only relation between them.
_reciprocal_social_play_candidate: dict[str, Any] | None = None
_last_reciprocal_social_play_evidence: dict[str, Any] | None = None
# Transient, bounded physical frontiers whose exact external or internally
# simulated retained-formation cause may continue in the immediately following
# physical intake. The values are observation only, do not survive restart,
# and cannot choose or retain anything for the organism. A new-fractal origin
# may cross an intake boundary only while an exact next-hop physical transfer
# advances it; the first interval without advancement drops it. An intake is a
# transport grouping, not a boundary in the organism's causal life.
_CROSS_INTAKE_CAUSAL_TRACE_KINDS = frozenset(
    {
        "external_participant_sensory",
        "externally_reassembled_retained_formation",
        "new_neuronal_fractal",
        "retained_formation",
    }
)
# The native organism retains exactly three completed electrical frontiers in
# addition to the interval being settled. A transient observer origin cannot
# remain causally witnessable after those three native intervals have passed.
# This is an organism-tick horizon, never a Python intake/request count.
_CAUSAL_MOTOR_TRACE_RETAINED_FRONTIERS = 3
_MULTI_PATH_CAUSAL_TRACE_KINDS = frozenset(
    {
        "externally_reassembled_retained_formation",
    }
)
_COMPLETED_EXTERNAL_MOTOR_PATHS_BY_RECURRENT = (
    "_completed_external_motor_paths_by_recurrent"
)
_COMPLETED_ARTICULATION_ORIGINS = (
    "_completed_articulation_origins"
)
_active_cross_intake_causal_motor_traces: dict[
    tuple[str, str, tuple[str, ...], int],
    dict[str, tuple[tuple[str, str, int, int], ...]],
] = {}
# One bounded process observation of the latest prepared tutor occurrence.
# It is transport evidence only: it does not survive restart, enter organism
# state, select a lesson, infer attention, or cause learning.  The approved
# media and current resident/world boundary are its only preparation inputs.
_curriculum_invitation: dict[str, Any] | None = None
_last_card_lesson_receipt: dict[str, Any] | None = None
_last_card_lesson_receipt_error: str | None = None
_last_song_lesson_receipt: dict[str, Any] | None = None
_last_song_lesson_receipt_error: str | None = None
_mounted_lesson_anatomy: Any | None = None
# RE-ENTRANT ON PURPOSE. Reading her body and transitioning her body are the
# same borrow as far as the native core is concerned: while a transition holds
# it mutably, any read raises "Already mutably borrowed" and the request 500s.
# That was invisible while unattended time was a motionless dark interval and
# became reachable the moment she started taking steps, because a step holds
# her body for the whole of a world move and its intake. A reader on another
# thread now waits for the transition to finish rather than tearing; a reader
# on the SAME thread — every read inside a transition — passes straight
# through, which a plain lock could not do.
_transition_lock = threading.RLock()
_live_sight_evidence: dict[str, Any] | None = None
# Bounded witness of the light that last reached her 27 retinal sites.
# Pending is written at episode construction; the public witness is
# PROMOTED only after that intake genuinely commits (state vs step honesty).
_pending_reached_retina: dict[str, Any] | None = None
_last_reached_retina: dict[str, Any] | None = None
# Truth-coupling for live hearing: written ONLY after a concurrent audiovisual
# intake has really committed and persisted, under the same lock as sight.
_live_hearing_evidence: dict[str, Any] | None = None
# The last displacement her body actually committed, or None while she
# has not moved in this process.  A step fact under its own name, never
# reported as her state.
_last_displacement: tuple[Fraction, ...] | None = None
# Truth-coupling for touch: written ONLY after a contact transition has really
# committed and persisted, under the same lock, exactly as live sight is.
_touch_evidence: dict[str, Any] | None = None
_last_unattended_evidence: dict[str, Any] | None = None
_last_unattended_pause: dict[str, Any] | None = None
_unattended_stop = threading.Event()
_unattended_thread: threading.Thread | None = None
# Bookkeeping only: counts external experiences currently waiting for the
# physical settlement borrow. NOTHING reads it to defer, yield, or skip a
# moment — Joe's law (2026-09-02): nothing locks a moment. Arrival order at
# the borrow is physical time order.
_external_intake_waiting = threading.Event()
_external_intake_signal_lock = threading.Lock()
_external_intake_waiter_count = 0


def _begin_external_intake() -> None:
    global _external_intake_waiter_count

    with _external_intake_signal_lock:
        _external_intake_waiter_count += 1
        _external_intake_waiting.set()


def _end_external_intake() -> None:
    global _external_intake_waiter_count

    with _external_intake_signal_lock:
        if _external_intake_waiter_count <= 0:
            raise RuntimeError("external intake admission counter underflow")
        _external_intake_waiter_count -= 1
        if _external_intake_waiter_count == 0:
            _external_intake_waiting.clear()


async def _external_intake_admission():
    """Signal external ingress before a synchronous route waits for a worker.

    FastAPI runs synchronous dependencies in its worker pool.  The async
    dependency executes on the request loop first so an arriving experience
    announces its presence immediately. Bookkeeping only: no moment is
    deferred, yielded, or skipped on this signal (Joe's law, 2026-09-02 —
    nothing locks a moment); settlements take arrivals in physical order.
    """

    _begin_external_intake()
    try:
        yield
    finally:
        _end_external_intake()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _receipt(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_secret(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    expected = os.environ.get("GUALALOOM_API_KEY")
    if not expected or not x_api_key or not hmac.compare_digest(expected, x_api_key):
        raise HTTPException(status_code=401, detail="authenticated observation required")


def _runtime() -> tuple[RestoredNativeOrganism, NativeResidentResourceAdmission]:
    if _restored is None or _admission is None:
        raise HTTPException(
            status_code=503,
            detail=_boot_error or "native resident organism is unavailable",
        )
    return _restored, _admission


def _native_record() -> dict[str, Any]:
    restored, admission = _runtime()
    # Same borrow discipline as everywhere else: a read waits for a
    # transition in flight and re-enters freely inside one.
    with _transition_lock:
        observed = restored.organism.readiness()
    return {
        "cognitive_mosaic_count": observed.cognitive_mosaic_count,
        "mosaic_of_mosaics_count": observed.mosaic_of_mosaics_count,
        "cognitive_ordinal": observed.cognitive_ordinal,
        "cognitive_trace_count": observed.cognitive_trace_count,
        "complete_neuron_count": getattr(observed, "complete_neuron_count", 0),
        # The public observer must not enumerate resident anatomy. Exact
        # layer membership remains native state and is observed only by an
        # explicitly requested diagnostic, never by every status refresh.
        "reached_neuron_count_by_layer": [],
        "developmental_resting_neuron_count": getattr(
            observed, "developmental_resting_neuron_count", 0
        ),
        "fabric_bytes": observed.fabric_bytes,
        "fabric_generation": observed.fabric_generation,
        "fabric_sha256": observed.fabric_sha256,
        "formation_activation_count": observed.formation_activation_count,
        "identity": observed.identity,
        "joint_field_count": observed.joint_field_count,
        "mounted_generation": observed.mounted_generation,
        "organism_tick": observed.organism_tick,
        "articulated_body": {
            "schema": "guala.native.articulated_body_state.v1",
            "state_bytes": observed.articulated_body_state_bytes,
            "state_sha256": observed.articulated_body_state_sha256,
            "proprioception_initialized": (
                observed.articulated_body_proprioception_initialized
            ),
            "axes": [
                {
                    "ordinal": ordinal,
                    "name": name,
                    "unit": unit,
                    "position": position,
                    "minimum": minimum,
                    "neutral": neutral,
                    "maximum": maximum,
                }
                for (
                    ordinal,
                    name,
                    unit,
                    position,
                    minimum,
                    neutral,
                    maximum,
                ) in observed.articulated_body_axes
            ],
            "lung_air_microlitres": (
                observed.articulated_body_lung_air_microlitres
            ),
            "vocal_tract_areas_square_millimetres": list(
                observed.articulated_body_vocal_tract_areas_square_millimetres
            ),
        },
        "partial_cue_reassembly_count": observed.partial_cue_reassembly_count,
        "endogenous_partial_cue_reassembly_count": (
            observed.endogenous_partial_cue_reassembly_count
        ),
        # Retained formation evidence is not a public-cache payload. The old
        # observer encoded and hashed every retained mosaic here, making a
        # read scale with Guala's lifetime. Current counters above remain the
        # bounded public facts.
        "retained_formation_recurrence_evidence": [],
        "physical_transition_claimed": observed.physical_transition_claimed,
        "python_callback_count": observed.python_callback_count,
        "reached_dsf_perspective_count": observed.joint_neuron_count,
        "resource_admission": {
            "derivation": admission.derivation,
            "max_envelope_bytes": admission.max_envelope_bytes,
            "max_fabric_bytes": admission.max_fabric_bytes,
            "max_logical_peak_bytes": admission.max_logical_peak_bytes,
            "memory_boundary_source": admission.memory_boundary_source,
        },
        "state_bytes": observed.state_bytes,
        "state_sha256": observed.state_sha256,
        # Exact body energy crosses Python only as canonical
        # (numerator, denominator) zeptojoule coordinates. Local neuronal
        # reaction counts never become organism-wide units here.
        "available_energy_zeptojoules": observed.available_energy_zeptojoules,
        "spent_energy_zeptojoules": observed.spent_energy_zeptojoules,
        "thermal_energy_zeptojoules": observed.thermal_energy_zeptojoules,
        "available_energy_capacity_zeptojoules": (
            observed.available_energy_capacity_zeptojoules
        ),
        "dissipated_energy_zeptojoules": observed.dissipated_energy_zeptojoules,
        "dissipation_capacity_energy_zeptojoules": (
            observed.dissipation_capacity_energy_zeptojoules
        ),
        "separated_elementary_charges": observed.separated_elementary_charges,
        "energy_exhausted": observed.energy_exhausted,
    }


def _build_identity() -> dict[str, str]:
    task = os.environ.get("ECS_TASK_DEFINITION", "")
    if not task:
        metadata_uri = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
        if metadata_uri:
            from urllib.request import urlopen

            with urlopen(metadata_uri + "/task", timeout=2.0) as response:
                metadata = json.load(response)
            family = metadata.get("Family")
            revision = metadata.get("Revision")
            if (
                isinstance(family, str)
                and isinstance(revision, (str, int))
                and not isinstance(revision, bool)
            ):
                task = family + ":" + str(revision)
    return {
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
        "image_digest": os.environ.get("DEPLOY_EXPECTED_IMAGE_DIGEST", "unknown"),
        "task_definition": task.rsplit("/", 1)[-1] if task else "unknown",
    }


def _section(
    available: bool,
    status: str,
    reason: str,
    **facts: object,
) -> dict[str, object]:
    return {
        "available": available,
        "reason": reason,
        "status": status,
        **facts,
    }


def _cochlear_authorization_record() -> dict[str, object]:
    """What ear anatomy this process actually declares, and by whose act.

    Reported so that an operator can SEE, from the outside, whether the
    organism is running the legacy two-port ears or the authorized cochleae —
    growing a sense organ must never be something anyone has to infer from a
    deploy log.  Every field is read from the process's own declared roster.
    """

    return {
        "cochlear_ears_authorized": COCHLEAR_EARS_AUTHORIZED,
        "cochlear_ears_authorization_env": COCHLEAR_EARS_ENV,
        "declared_ear_port_count": EAR_PORT_COUNT,
        # 2026-08-07 truth repair: a single quantity hid the 2 retained
        # legacy pressure ports that still carry the non-physical
        # normalized excitation.  Both kinds are declared.
        "declared_ear_port_quantity": (
            COCHLEAR_QUANTITY if COCHLEAR_EARS_AUTHORIZED else PHYSICAL_QUANTITY
        ),
        "retained_legacy_ear_port_count": 2 if COCHLEAR_EARS_AUTHORIZED else 0,
        "retained_legacy_ear_port_quantity": (
            PHYSICAL_QUANTITY if COCHLEAR_EARS_AUTHORIZED else None
        ),
    }


def _touch_authorization_record() -> dict[str, object]:
    """What contact anatomy this process actually declares, and by whose act.

    Reported so that an operator can SEE, from the outside, whether the
    organism declares a contact sheet at all — growing a sense organ must never
    be something anyone has to infer from a deploy log.  Every field is read
    from the process's own declared roster.
    """

    return {
        "touch_receptors_authorized": TOUCH_RECEPTORS_AUTHORIZED,
        "touch_receptors_authorization_env": TOUCH_RECEPTORS_ENV,
        "declared_contact_port_count": TOUCH_PORT_COUNT,
        "declared_contact_sheet_site_count": CONTACT_SHEET_SITE_COUNT,
        "declared_palmar_contact_site_count": int(
            TOUCH_RECEPTORS_AUTHORIZED
        ),
        "declared_contact_port_quantity": (
            CONTACT_QUANTITY if TOUCH_RECEPTORS_AUTHORIZED else None
        ),
    }


def _touch_record() -> dict[str, object]:
    """Truth-coupled tactile observation.

    Three honestly distinguished states, and mounted is the last of them:

      * NO ANATOMY — the contact sheet is not authorized, so this body has no
        touch receptors at all.  That is the truth today and it names the
        missing piece.
      * ANATOMY, NO TRANSITION — the sheet is declared but nothing has been
        touched in this process, so no contact transition has committed.  The
        capability is claimed only from a real committed transition, never from
        the mounted surface.
      * MOUNTED — a real contact occurrence transduced under the tactile
        receptor law and the committed successor body was persisted.

    ``contacted_site_count`` is HER STATE for the last committed contact — how
    many of her declared sites the object actually reached — not a count of
    ports declared, which would be true and meaningless.
    """

    if not TOUCH_RECEPTORS_AUTHORIZED:
        return _unmounted(
            "native touch receptor transition is not mounted: this body "
            "declares no contact sheet at all, so nothing can be touched; "
            f"the contact-sheet anatomy is authorized by {TOUCH_RECEPTORS_ENV}",
            **_touch_authorization_record(),
        )
    action_tactile = (
        (_last_self_moved or {})
        .get("sensory_consequence", {})
        .get("tactile", {})
    )
    if (
        isinstance(action_tactile, dict)
        and action_tactile.get("changed") == 1
    ):
        return _section(
            True,
            "palmar_contact_transition_committed",
            "a native closing grip changed the distinct palmar contact "
            "receptor through the persistent world's exact held-object "
            "geometry; unmounted material qualities are not inferred",
            **_touch_authorization_record(),
            **action_tactile,
        )
    if _touch_evidence is None:
        return _section(
            False,
            "no_contact_transition_this_process",
            "the contact sheet is declared on "
            f"{CONTACT_SHEET_ROWS}x{CONTACT_SHEET_COLUMNS} contact sites and "
            "one distinct palmar held-contact site is appended; neither has "
            "changed in this process, so no contact transition is claimed",
            **_touch_authorization_record(),
        )
    return _section(
        True,
        "contact_transition_committed",
        "the taught card's DECLARED FOOTPRINT (authored from its raster "
        "geometry, not inferred from a physical-world grasp) "
        "rested against the declared contact sheet and its per-site "
        "occupancy TRANSDUCED under the mounted tactile receptor law "
        "(contact-site-occupancy on the same quantum lattice as light and "
        "sound); the distinct palmar receptor reports real-world held contact "
        "separately; the committed successor body was persisted",
        **_touch_authorization_record(),
        **_touch_evidence,
    )


def _displacement_record(modality: str) -> dict[str, object]:
    """Truth-coupled balance and body position.

    Both read the SAME four displacement sites, because both answer one
    physical question: how did this body just move.  Vestibular is the
    motion; proprioception is where that motion left her.

    Two honest cases and no third.  Without the receptors she has no sense of
    motion at all.  WITH them the field is declared on every experience and
    carries the displacement that actually happened — zero whenever she did
    not move, because standing still is a lawful state, not an absent sense.
    """

    if not VESTIBULAR_AUTHORIZED:
        return _unmounted(
            f"native {modality} receptor transition is not mounted: this "
            "body declares no displacement receptors, so motion would have "
            "to be invented rather than transduced; the displacement "
            f"anatomy is authorized by {VESTIBULAR_ENV}",
            displacement_authorization_env=VESTIBULAR_ENV,
            displacement_authorized=False,
        )
    moved = _last_displacement
    vestibular_evidence = (
        _last_transition_evidence
        if modality == "vestibular"
        and _last_transition_evidence is not None
        and _last_transition_evidence.get("intake") == "world-move"
        and int(_last_transition_evidence.get("vestibular_tick_count", 0)) > 0
        else None
    )
    if vestibular_evidence is not None:
        return _section(
            True,
            "native_vestibular_transition_committed",
            "the world body's exact signed yaw path settled through the native "
            "canal, cupula, hair bundle, tip link, gating spring, full joint "
            "seven-field occurrence, and one predeclared body-and-balance "
            "neuron; the committed successor body was persisted",
            native_neuronal_participation=True,
            vestibular_tick_count=vestibular_evidence["vestibular_tick_count"],
            totals=dict(vestibular_evidence["totals"]),
            last_displacement=(
                {c: float(v) for c, v in zip(DISPLACEMENT_CHANNELS, moved)}
                if moved is not None
                else None
            ),
        )
    native_vestibular_neuron_count = (
        _runtime()[0].organism.observe_reached_source_site_count(
            NATIVE_VESTIBULAR_SENSOR_ID,
            NATIVE_VESTIBULAR_SUBSTREAM_ID,
        )
        if modality == "vestibular"
        else 0
    )
    if native_vestibular_neuron_count > 0:
        return _section(
            True,
            "native_vestibular_neuron_persisted",
            "the current native body retains a reached neuron anchored to "
            "the exact mounted yaw-canal and local hair-bundle source; this "
            "is persisted receptor anatomy, not a transient event label",
            native_neuronal_participation=True,
            native_vestibular_neuron_count=native_vestibular_neuron_count,
            last_displacement=(
                {c: float(v) for c, v in zip(DISPLACEMENT_CHANNELS, moved)}
                if moved is not None
                else None
            ),
        )
    return _section(
        False,
        "displacement_transported_not_neuronally_transduced",
        f"{DISPLACEMENT_SITE_COUNT} body-displacement coordinates are "
        "transported in the admitted joint occurrence, but the live resident "
        "transition has no displacement receptor law and skips them before "
        "neuron genesis and settlement. The separate typed vestibular proof "
        "path is not mounted by prepare_admitted. The last transported "
        "movement is reported below when present, but it is not evidence "
        f"that {modality} reached Guala's neurons.",
        declared_channels=list(DISPLACEMENT_CHANNELS),
        declared_site_count=DISPLACEMENT_SITE_COUNT,
        displacement_authorization_env=VESTIBULAR_ENV,
        displacement_authorized=True,
        last_displacement=(
            {c: float(v) for c, v in zip(DISPLACEMENT_CHANNELS, moved)}
            if moved is not None
            else None
        ),
        native_neuronal_participation=False,
        transported_by=DISPLACEMENT_SENSOR_ID,
    )


def _proprioception_record() -> dict[str, object]:
    """Truthful local body configuration, distinct from world displacement."""

    reached = sum(
        _runtime()[0].organism.observe_reached_source_site_count(
            ARTICULATORY_BODY_SENSOR_ID,
            f"articulation-{channel}",
        )
        for channel in ARTICULATORY_BODY_CHANNELS
    )
    consequence = (
        _last_self_moved.get("sensory_consequence")
        if isinstance(_last_self_moved, dict)
        and isinstance(_last_self_moved.get("sensory_consequence"), dict)
        else None
    )
    if consequence is not None:
        lane = consequence.get("proprioceptive")
        if (
            not isinstance(lane, dict)
            or lane.get("sensor_id") != ARTICULATORY_BODY_SENSOR_ID
        ):
            raise RuntimeError("action consequence changed proprioceptive source")
        return _section(
            reached > 0,
            "local_proprioceptive_action_consequence_committed",
            "the rigid-body yaw left breath, glottis, mouth, and facial-skin "
            "configuration unchanged; all four genuine local body receptors "
            "re-entered the same organism as quiescent while vestibular and "
            "visual receptors carried the rotation",
            action_receipt_sha256=consequence["action_receipt_sha256"],
            changed_site_count=lane["changed"],
            coverage="local articulatory body; limb and joint anatomy remains absent",
            native_neuronal_participation=reached > 0,
            reached_site_count=reached,
            transported_site_count=lane["transported"],
        )
    if reached > 0:
        return _section(
            True,
            "local_proprioceptive_neurons_persisted",
            "the current native body retains reached breath, glottis, mouth, "
            "and facial-skin mechanoreceptors; no whole-body or limb/joint "
            "proprioception is claimed",
            coverage="local articulatory body; limb and joint anatomy remains absent",
            native_neuronal_participation=True,
            reached_site_count=reached,
        )
    return _section(
        False,
        "local_proprioception_not_reached",
        "no reached local body-configuration receptor is present; global "
        "world displacement is not substituted for proprioception",
        coverage="none",
        native_neuronal_participation=False,
    )


def _chemoreceptive_record(
    modality: str,
    channels: tuple[str, ...],
    sensor_id: str,
    native: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Truth-coupled taste or smell."""

    if not CHEMORECEPTION_AUTHORIZED:
        return _unmounted(
            f"native {modality} receptor transition is not mounted: this "
            "body declares no chemoreceptors, so a material's composition "
            "would reach nothing; the chemoreceptive anatomy is authorized "
            f"by {CHEMORECEPTION_ENV}",
            chemoreception_authorization_env=CHEMORECEPTION_ENV,
            chemoreception_authorized=False,
        )
    layer = 3 if modality == "smell" else 4
    reached = (
        dict(native.get("reached_neuron_count_by_layer", ())).get(layer, 0)
        if native
        else 0
    )
    return _section(
        True,
        (
            f"native_{modality}_receptor_neurons_persisted"
            if reached
            else f"native_{modality}_receptor_law_mounted_awaiting_occurrence"
        ),
        f"{len(channels)} declared {modality} receptor-saturation coordinates "
        "enter the exact native chemical receptor-work law. World values are "
        "derived from local material, geometry, and receptor-saturation "
        "declarations; tutor material is an explicit simulated stock. The "
        "law transduces local receptor activation only and does not identify "
        "a substance, assign meaning, or claim recognition.",
        declared_channels=list(channels),
        declared_site_count=len(channels),
        chemoreception_authorization_env=CHEMORECEPTION_ENV,
        chemoreception_authorized=True,
        composition_authority="local_world_material_physics_or_declared_tutor_stock",
        native_neuronal_participation=bool(reached),
        reached_neuron_count=reached,
        transported_by=sensor_id,
    )


def _temperature_record(native: dict[str, Any] | None = None) -> dict[str, object]:
    del native
    if not THERMAL_PORT_COUNT:
        return _unmounted(
            "the persistent world is not mounted, so no truthful core or "
            "cutaneous thermoreceptor can be connected"
        )
    observation = _world().thermal_observation()
    by_id = dict(zip(
        observation.node_ids,
        observation.temperatures_millikelvin,
        strict=True,
    ))
    reached_by_channel = {
        channel: _runtime()[0].organism.observe_reached_source_site_count(
            THERMAL_SENSOR_ID,
            f"temperature-{channel}",
        )
        for channel in THERMAL_CHANNELS
    }
    reached = sum(reached_by_channel.values())
    return _section(
        True,
        (
            "native_core_and_cutaneous_thermoreceptors_persisted"
            if reached == THERMAL_PORT_COUNT
            else "native_thermal_receptor_law_mounted_awaiting_occurrence"
        ),
        "the authenticated home/body heat circuit conserves exact energy in "
        "four room-air stocks plus cutaneous and core stocks; two local body "
        "sites carry their physical temperatures through the exact native "
        "thermal receptor-work law. No comfort label, thermostat score, or "
        "authored thermal meaning reaches the organism.",
        anatomy_receipt_sha256=observation.anatomy_receipt_sha256,
        core_temperature_within_declared_interval=(
            THERMAL_MIN_MILLIKELVIN
            <= by_id["body:core"]
            <= THERMAL_MAX_MILLIKELVIN
        ),
        cutaneous_temperature_within_declared_interval=(
            THERMAL_MIN_MILLIKELVIN
            <= by_id["body:cutaneous-shell"]
            <= THERMAL_MAX_MILLIKELVIN
        ),
        declared_receptor_interval_millikelvin=[
            THERMAL_MIN_MILLIKELVIN,
            THERMAL_MAX_MILLIKELVIN,
        ],
        exact_temperature_coordinates_resident=True,
        exact_temperature_coordinates_transported=False,
        latest_thermal_transition_receipt_sha256=(
            observation.latest_transition_receipt_sha256
        ),
        native_neuronal_participation=reached == THERMAL_PORT_COUNT,
        reached_site_count_by_channel=reached_by_channel,
        transported_site_count=THERMAL_PORT_COUNT,
        world_observation_receipt_sha256=(
            observation.world_observation_receipt_sha256
        ),
        world_revision=observation.world_revision,
    )


def _interoception_record(native: dict[str, Any] | None = None) -> dict[str, object]:
    layers = dict((native or {}).get("reached_neuron_count_by_layer", ()))
    totals = (
        (_last_transition_evidence or {}).get("totals")
        if _last_transition_evidence is not None
        else None
    ) or {}
    local_body_count = totals.get(
        "metabolically_perturbed_body_receptor_count", 0
    )
    if not isinstance(local_body_count, int) or isinstance(local_body_count, bool):
        local_body_count = 0
    reached_body_receptors = layers.get(5, 0)
    reached_body_regulators = layers.get(8, 0)
    if local_body_count > 0:
        return _section(
            True,
            "local_cellular_metabolic_afference_observed",
            "a mounted recovery-fluid contact changed the membrane charge of "
            "a reached layer-5 body receptor, and that exact lineage entered "
            "the existing one-interval sparse frontier; no body-wide fuel, "
            "heat, spent, charge, or readiness total was fed back as a signal",
            dedicated_visceral_organ_afferents_mounted=False,
            local_body_receptor_transition_count=local_body_count,
            native_neuronal_participation=True,
            reached_body_receptor_count=reached_body_receptors,
            reached_body_regulation_neuron_count=reached_body_regulators,
        )
    if reached_body_receptors and reached_body_regulators:
        return _section(
            False,
            "local_metabolic_path_mounted_awaiting_observed_transition",
            "local recovery-fluid membrane consequences now enter the sparse "
            "frontier, and reached body receptor and regulation anatomy are "
            "present; this process has not yet observed a layer-5 metabolic "
            "membrane transition, so participation is not claimed",
            dedicated_visceral_organ_afferents_mounted=False,
            local_body_receptor_transition_count=0,
            native_neuronal_participation=False,
            reached_body_receptor_count=reached_body_receptors,
            reached_body_regulation_neuron_count=reached_body_regulators,
        )
    return _unmounted(
        "no reached local body receptor and regulation route is available; "
        "exact body-energy coordinates remain observation only and are not "
        "fed back as one synthetic organism interoceptor",
        dedicated_visceral_organ_afferents_mounted=False,
        native_neuronal_participation=False,
    )


def _unmounted(reason: str, **facts: object) -> dict[str, object]:
    return _section(False, "not_mounted", reason, **facts)


def _capability(reason: str) -> dict[str, object]:
    return {
        "available": False,
        "endpoint": None,
        "reason": reason,
        "status": "not_mounted",
    }


def _mounted_capability(endpoint: str, reason: str) -> dict[str, object]:
    return {
        "available": True,
        "endpoint": endpoint,
        "reason": reason,
        "status": "mounted",
    }


def _manifest_document(path: Path, schema: str) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise ValueError(f"{path.name} structure changed")
    return value


def _manifest_experiences(path: Path, schema: str) -> list[dict[str, object]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    experiences = value.get("experiences")
    if value.get("schema") != schema or not isinstance(experiences, list):
        raise ValueError(f"{path.name} structure changed")
    if any(not isinstance(item, dict) for item in experiences):
        raise ValueError(f"{path.name} experience changed")
    return experiences


def _require_manifest_media(
    experiences: list[dict[str, object]],
    media_keys: tuple[str, ...],
    optional_keys: tuple[str, ...] = (),
) -> None:
    """Every declared medium must exist on disk.

    ``optional_keys`` may be absent from an experience entirely — but an
    experience that DECLARES one still has to have it.  A missing recording
    is a lawful kind of card (taught in a person's own voice); a declared
    recording that is not there is a broken manifest.
    """

    for experience in experiences:
        for key in media_keys + optional_keys:
            item = experience.get(key)
            if item is None and key in optional_keys:
                continue
            media_path = item.get("path") if isinstance(item, dict) else None
            if not isinstance(media_path, str):
                raise ValueError(f"curriculum {key} path changed")
            relative = media_path.removeprefix("guala_curriculum/")
            if not (CURRICULUM_ROOT / relative).is_file():
                raise ValueError(f"curriculum media is absent: {media_path}")


def _curriculum_invitation_record() -> dict[str, object]:
    if _curriculum_invitation is None:
        return _section(
            False,
            "no_tutor_presentation_prepared_this_process",
            "no reviewed tutor sensory presentation is currently prepared "
            "for the resident organism",
            presentation_eligible=False,
            python_attention_authority=False,
            scripted_acceptance_authority=False,
            semantic_command_authority=False,
            transport_metadata_only=True,
        )
    facts = {
        key: value
        for key, value in _curriculum_invitation.items()
        if key not in {"available", "reason", "status"}
    }
    status = str(_curriculum_invitation["status"])
    reason = str(_curriculum_invitation["reason"])
    settled_tick = facts.get("presented_organism_tick")
    if isinstance(settled_tick, int) and not isinstance(settled_tick, bool):
        durable_pointer = None if _restored is None else _restored.pointer
        durable_tick = (
            None if durable_pointer is None else durable_pointer.organism_tick
        )
        facts["durable_through_organism_tick"] = durable_tick
        facts["durable_state_sha256"] = (
            None if durable_pointer is None else durable_pointer.state_sha256
        )
        presentation_durable = (
            isinstance(durable_tick, int) and durable_tick >= settled_tick
        )
        facts["presentation_durable"] = presentation_durable
        if presentation_durable and status == "local_material_presentation_settled":
            status = "local_material_presentation_committed"
            reason = (
                "the preserved source settled through physical receptors and "
                "the resulting organism interval is now inside CURRENT"
            )
    return _section(
        True,
        status,
        reason,
        **facts,
        python_attention_authority=False,
        scripted_acceptance_authority=False,
        semantic_command_authority=False,
        transport_metadata_only=True,
    )


def _curriculum_media_record() -> dict[str, object]:
    try:
        cards = _manifest_experiences(
            CURRICULUM_ROOT / "card_experience_manifest-v1.json",
            "guala.external_tutor_card_experience_manifest.v1",
        )
        songs = _manifest_experiences(
            CURRICULUM_ROOT / "songs" / "song_experience_manifest-v1.json",
            "guala.external_tutor_song_experience_manifest.v1",
        )
        _require_manifest_media(cards, ("surface",), ("tutor_audio",))
        _require_manifest_media(songs, ("audio",))
        # THE EXTENT PIN IS THE MANIFEST'S OWN DECLARATION, not a constant
        # in this file (2026-08-07).  A hardcoded 36 made every added word a
        # code change and reported "approved curriculum extent changed" for
        # deliberate growth.  The manifest declares how many experiences it
        # approves; the code refuses any drift from that declaration, so a
        # card still cannot appear without a deliberate edit.
        declared = _manifest_document(
            CURRICULUM_ROOT / "card_experience_manifest-v1.json",
            "guala.external_tutor_card_experience_manifest.v1",
        ).get("approved_experience_count")
        if not isinstance(declared, int) or isinstance(declared, bool):
            raise ValueError("card manifest declares no approved extent")
        if len(cards) != declared or len(songs) != 3:
            raise ValueError("approved curriculum extent changed")
        spoken_only = sum(1 for card in cards if card.get("tutor_audio") is None)
        return _section(
            True,
            "external_media_ready_native_tutoring_mounted",
            f"{declared} approved card experiences ({declared - spoken_only} "
            f"with a recorded tutor voice, {spoken_only} taught in the voice "
            "of whoever is present) and three songs are present; one "
            "approved card reaches the resident organism as one admitted "
            "native episode; no label, identity, or meaning enters the "
            "organism; approved songs use their separate synchronized "
            "invitation and teaching endpoints",
            approved_card_experience_count=declared,
            spoken_only_card_experience_count=spoken_only,
            approved_song_experience_count=3,
            internal_identity_authority=False,
            internal_meaning_authority=False,
            manifest_path="/curriculum/card_experience_manifest-v1.json",
            invitation=_curriculum_invitation_record(),
            invitation_endpoint=CURRICULUM_INVITE_ENDPOINT,
            song_invitation_endpoint=CURRICULUM_INVITE_SONG_ENDPOINT,
            teach_card_endpoint="/api/v1/curriculum/teach-card",
            guided_world_voice_endpoint=GUIDED_WORLD_VOICE_ENDPOINT,
            teach_song_endpoint=CURRICULUM_TEACH_SONG_ENDPOINT,
            tutoring_transition_available=True,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _section(
            False,
            "external_media_unavailable",
            f"{type(error).__name__}: {error}",
            internal_identity_authority=False,
            internal_meaning_authority=False,
            tutoring_transition_available=False,
        )


def _sensory_record(native: dict[str, Any] | None = None) -> dict[str, object]:
    live_sight = _live_sight_record()
    modalities = {
        "visual": _section(
            True,
            (
                "curriculum_and_live_camera_transitions_committed"
                if live_sight["available"]
                else "curriculum_card_surface_transition_mounted"
            ),
            "approved curriculum card surfaces can reach the resident organism "
            "as admitted 27-receptor luminance occurrences; a bounded tutor "
            "preparation binds exact reviewed media but neither supplies nor "
            "infers attention, recognition, or learning; the live camera "
            "transition is "
            "reported mounted only from a real committed live-sight "
            "transition (see live_camera)",
            live_camera=live_sight,
            # The light that last reached her 27 retinal sites, promoted
            # only from a genuinely committed intake (9 columns x 3 rows,
            # values scaled 0-255 for display; the exact floats are the
            # committed episode's own).
            retina_luminance=(
                [
                    max(0, min(255, round(255 * value)))
                    for value in _last_reached_retina["values"]
                ]
                if _last_reached_retina is not None
                and len(_last_reached_retina["values"]) == 27
                else None
            ),
            retina_rows=3 if _last_reached_retina is not None else None,
            retina_columns=9 if _last_reached_retina is not None else None,
            retina_source=(
                _last_reached_retina.get("assembly_id")
                if _last_reached_retina is not None
                else None
            ),
            retina_organism_tick=(
                _last_reached_retina.get("organism_tick")
                if _last_reached_retina is not None
                else None
            ),
        ),
        "auditory": _section(
            True,
            (
                "live_pressure_committed_this_process"
                if _live_hearing_evidence is not None
                else "cochlear_pressure_transition_mounted"
            ),
            (
                "live acoustic pressure has COMMITTED as admitted whole-"
                "sensorium episodes in this process "
                f"({_live_hearing_evidence['intake']}); tutor audio inside "
                "card lessons also transduces under the mounted auditory "
                "receptor law; the binaural transition is not mounted"
                if COCHLEAR_EARS_AUTHORIZED and _live_hearing_evidence is not None
                else "live microphone pressure and tutor audio reach the "
                "resident organism as admitted cochlear band-pressure "
                "occurrences under the mounted auditory receptor law; an "
                "open camera adds co-clocked retinal light but is not a "
                "precondition for hearing; the binaural transition is not "
                "mounted"
                if COCHLEAR_EARS_AUTHORIZED
                else "tutor audio inside card lessons reaches the resident "
                "organism as admitted pressure occurrences; standalone "
                "hearing is refused honestly because the ears have no "
                "transduction law yet — pressure amplitude has zero "
                "physical effect — and hearing returns when the tonotopic "
                "ear anatomy is authorized; the binaural transition is not "
                "mounted"
            ),
            **_cochlear_authorization_record(),
        ),
        "text": _section(
            True,
            "rendered_glyph_light_mounted",
            "typed characters become browser-rendered glyph pixels and enter "
            "only through the mounted retinal transition; the string and its "
            "meaning are never submitted to cognition",
            endpoint=RENDERED_LIGHT_ENDPOINT,
            sensory_lane="visual",
            internal_meaning_authority=False,
        ),
        "touch": _touch_record(),
        "temperature": _temperature_record(native),
        "smell": _chemoreceptive_record(
            "smell", SMELL_CHANNELS, SMELL_SENSOR_ID, native
        ),
        "taste": _chemoreceptive_record(
            "taste", TASTE_CHANNELS, TASTE_SENSOR_ID, native
        ),
        "vestibular": _displacement_record("vestibular"),
        "proprioception": _proprioception_record(),
        "interoception": _interoception_record(native),
    }
    return _section(
        True,
        "partial_native_receptor_transitions",
        "admitted visual, auditory, tactile when authorized, and chemical "
        "receptor transitions use the same native resident organism; live "
        "participation remains truth-coupled to persisted reached anatomy",
        **modalities,
    )


def _bounded_motor_action_observation(action: dict[str, Any]) -> dict[str, Any]:
    """Project one action without exporting its per-neuron preparation graph."""

    return {
        key: value
        for key, value in action.items()
        if key != "prepared_recruitments"
    }


def _causal_thought_record() -> dict[str, object]:
    """Report native formation-to-formation carrier transitions only.

    This surface never infers thought from recurrence counts or electrical
    activity. The native organism must name both retained formations and the
    exact recurrent-cell carrier transfer that caused the destination cue.
    """

    intervals = tuple(
        (_last_transition_evidence or {}).get("causal_interval_evidence", ())
    )
    transitions = tuple(
        transition
        for interval in intervals
        for transition in interval.get("causal_thought_transitions", ())
    )
    if not transitions:
        return _section(
            False,
            "native_causal_thought_mounted_awaiting_witness",
            "the native recurrent-cell carrier bridge is mounted, but the "
            "latest observed trajectory did not contain a retained "
            "formation causing a different retained formation",
            observed_transition_count=0,
            observer_authority=False,
        )
    latest = transitions[-1]
    return _section(
        True,
        "native_causal_thought_observed",
        "one retained formation's recurrent neuron sent whole carriers into "
        "a member that physically reassembled a different retained formation",
        observed_transition_count=len(transitions),
        latest_transition={
            "source_formation_receipt_sha256": latest[0],
            "destination_formation_receipt_sha256": latest[1],
            "source_recurrent_lineage": latest[2],
            "destination_cue_lineage": latest[3],
            "directed_physical_transfer": latest[4],
        },
        observer_authority=False,
    )


def _sleep_dream_wake_record() -> dict[str, object]:
    """Project one exact ordered native recovery/re-entry/action sequence.

    This observer runs only after a committed trajectory. It neither creates
    nor retains a sleep state, chooses an interval, or supplies any cause to
    the organism. The bounded causal intervals are already native transition
    evidence; this function only refuses or reports their physical ordering.
    """

    evidence = _last_transition_evidence or {}
    intervals = evidence.get("causal_interval_evidence", ())
    if not isinstance(intervals, (list, tuple)):
        raise RuntimeError("causal interval evidence changed bounded shape")
    motor_action = evidence.get("motor_action")
    for rest_index, rest_interval in enumerate(intervals):
        if not isinstance(rest_interval, dict):
            raise RuntimeError("causal interval changed named shape")
        rest_count = rest_interval.get("rest_recovered_neuron_count", 0)
        rest_actions = tuple(
            rest_interval.get(field, ())
            for field in (
                "motor_unit_recruitments",
                "root_yaw_unit_recruitments",
                "root_translation_unit_recruitments",
                "articulatory_unit_recruitments",
            )
        )
        if (
            not isinstance(rest_count, int)
            or isinstance(rest_count, bool)
            or rest_count <= 0
            or any(rest_actions)
        ):
            continue
        for dream_index, dream_interval in enumerate(
            intervals[rest_index:], start=rest_index
        ):
            if not isinstance(dream_interval, dict):
                raise RuntimeError("causal interval changed named shape")
            internal_cues = dream_interval.get(
                "internally_reassembled_formation_cues", ()
            )
            thought_transitions = dream_interval.get(
                "causal_thought_transitions", ()
            )
            dream_actions = tuple(
                dream_interval.get(field, ())
                for field in (
                    "motor_unit_recruitments",
                    "root_yaw_unit_recruitments",
                    "root_translation_unit_recruitments",
                    "articulatory_unit_recruitments",
                )
            )
            if not (internal_cues or thought_transitions) or any(dream_actions):
                continue
            externally_perturbed = dream_interval.get(
                "externally_perturbed_neuron_lineages", ()
            )
            for wake_interval in intervals[dream_index + 1 :]:
                if not isinstance(wake_interval, dict):
                    raise RuntimeError("causal interval changed named shape")
                wake_recruitment_count = sum(
                    len(wake_interval.get(field, ()))
                    for field in (
                        "motor_unit_recruitments",
                        "root_yaw_unit_recruitments",
                        "root_translation_unit_recruitments",
                        "articulatory_unit_recruitments",
                    )
                )
                if wake_recruitment_count <= 0:
                    continue
                if (
                    not isinstance(motor_action, dict)
                    or motor_action.get("moved") is not True
                ):
                    continue
                consequence = motor_action.get("sensory_consequence")
                if not isinstance(consequence, dict):
                    continue
                return _section(
                    True,
                    "native_recovery_internal_reentry_and_wake_observed",
                    "one native interval recovered resident neurons without "
                    "motor recruitment; a subsequent action-free interval "
                    "internally re-entered exact formations while external "
                    "sensory transport remained allowed; a later interval "
                    "recruited native effectors, moved the persistent body, "
                    "and returned its sensory consequence to the same organism",
                    recovery_organism_tick=rest_interval.get("organism_tick"),
                    recovered_neuron_count=rest_count,
                    internal_reentry_organism_tick=dream_interval.get(
                        "organism_tick"
                    ),
                    internally_reassembled_formation_count=len(internal_cues),
                    causal_thought_transition_count=len(thought_transitions),
                    externally_perturbed_neuron_count=len(externally_perturbed),
                    wake_organism_tick=wake_interval.get("organism_tick"),
                    wake_recruitment_count=wake_recruitment_count,
                    consequence_organism_identity=consequence.get(
                        "organism_identity"
                    ),
                    consequence_organism_tick=consequence.get("organism_tick"),
                    observer_authority=False,
                    scheduler_authority=False,
                    sleep_state_owner=False,
                )
    return _section(
        False,
        "native_sleep_dream_wake_sequence_awaiting_witness",
        "the physical producers are mounted, but the latest committed "
        "trajectory does not contain the complete ordered recovery, internal "
        "re-entry, later effector recruitment, body movement, and sensory "
        "return sequence",
        observer_authority=False,
        scheduler_authority=False,
        sleep_state_owner=False,
    )


def _autonomy_record() -> dict[str, object]:
    """Truth-coupled observation of continuous native settlement.

    Continuous lived time is not autonomy. This section reports measured
    physical settlement in the persistent world. Sparse physical attention is
    reported separately from this autonomy claim; internally caused thought,
    choice, and repeated self-directed action remain unavailable until native
    evidence proves them.
    """

    unattended_time: dict[str, object] = {
        "declared_interval_milliseconds": CONTINUOUS_INTERVAL_MILLISECONDS,
        "disable_env": UNATTENDED_TIME_ENV,
        "enabled": _unattended_time_enabled(),
        "hop_milliseconds": INTAKE_HOP_MILLISECONDS,
        "hops_per_interval": UNATTENDED_HOPS_PER_INTERVAL,
        "last_pause": _last_unattended_pause,
        "medium": (
            "transport continuously samples the actual persistent world and "
            "delivers contiguous physical intervals; time does not select "
            "thought or action"
        ),
        "pauses_for_external_intake": True,
        "pauses_when_energy_exhausted": False,
    }
    physical_choice = _physical_choice_record()
    causal_thought = _causal_thought_record()
    sleep_dream_wake = _sleep_dream_wake_record()
    not_mounted = {
        "action": _unmounted("no native action actuator is mounted"),
        "attention": _attention_record(),
        "choice": physical_choice,
        "consequence": _unmounted("no autonomous action consequence exists"),
        "sleep_dream_wake": sleep_dream_wake,
        "thought": causal_thought,
    }
    if _last_unattended_evidence is None:
        return _section(
            False,
            "no_unattended_interval_this_process",
            "no continuous world interval has completed in this process; "
            "autonomous thought, action, attention, and choice are not "
            "mounted",
            action_observed=False,
            unattended_time=unattended_time,
            **not_mounted,
        )
    category = _last_unattended_evidence["category"]
    last_interval = {
        key: _last_unattended_evidence[key]
        for key in (
            "declared_interval_milliseconds",
            "hop_count",
            "intake",
            "organism_tick",
            "receptor_ingress",
            "state_sha256",
            "world_revision",
        )
    }
    measured = dict(_last_unattended_evidence["measured"])
    if category == "native_causal_action_observed":
        motor_action = _last_unattended_evidence.get("motor_action")
        if not isinstance(motor_action, dict) or motor_action.get("moved") is not True:
            raise RuntimeError("native action category carries no moved body evidence")
        return _section(
            True,
            category,
            "the organism's native layer-12 discharge moved its body and the "
            "resulting typed proprioceptive source was emitted by the native "
            "body; "
            "this does not prove deliberative choice or thought",
            action_observed=True,
            action=_section(
                True,
                "native_articulated_body_observed",
                "outward motor-neuron carrier discharge reached explicit "
                "antagonist body terminals",
                observed_effect=(
                    f"{len(motor_action['articulated_body_consequences'])} "
                    "typed body-axis consequences"
                ),
            ),
            attention=not_mounted["attention"],
            choice=not_mounted["choice"],
            consequence=_section(
                True,
                "native_proprioceptive_consequence_observed",
                "the native body emitted exact typed proprioceptive sources",
                observed_effect=(
                    f"{len(motor_action['body_proprioceptive_sources'])} "
                    "body-source receipts returned"
                ),
            ),
            sleep_dream_wake=sleep_dream_wake,
            thought=not_mounted["thought"],
            last_interval=last_interval,
            motor_action=_bounded_motor_action_observation(motor_action),
            self_maintenance=measured,
            unattended_time=unattended_time,
        )
    if category == "continuous_environment_observed":
        return _section(
            True,
            category,
            "the actual persistent world reached the native organism and "
            "changed its physical settlement; this proves continuous sensory "
            "processing, not autonomous thought or action",
            action_observed=False,
            last_interval=last_interval,
            self_maintenance=measured,
            unattended_time=unattended_time,
            **not_mounted,
        )
    if category == "self_maintenance_observed":
        return _section(
            True,
            "self_maintenance_observed",
            "measured recovery, ledger, or membrane change during a "
            "continuous world interval; the body genuinely tended "
            "itself, and that is self-maintenance only: autonomous thought, "
            "action, attention, and choice are not mounted",
            action_observed=False,
            last_interval=last_interval,
            self_maintenance=measured,
            unattended_time=unattended_time,
            **not_mounted,
        )
    if category == "retained_state_settling_observed":
        return _section(
            True,
            "retained_state_settling_observed",
            "the organism's own retained electrical state kept settling "
            "through its retained contacts during a continuous world "
            "interval, with zero energy-ledger movement; that is "
            "the retained state's own physics, not action: autonomous "
            "thought, action, attention, and choice are not mounted",
            action_observed=False,
            last_interval=last_interval,
            self_maintenance=measured,
            unattended_time=unattended_time,
            **not_mounted,
        )
    return _section(
        False,
        "no_internal_cause",
        "the last unattended interval measured zero physical change: with "
        "no external or endogenous cause the organism was genuinely "
        "quiescent, and that is rest, not activity; autonomous thought, "
        "action, attention, and choice are not mounted",
        action_observed=False,
        last_interval=last_interval,
        self_maintenance=measured,
        unattended_time=unattended_time,
        **not_mounted,
    )


# ---------------------------------------------------------------------------
# The experience stage ledger (DARPA first-proof requirement 8: the live
# interfaces must show what she sensed, attended to, reassembled, intended,
# emitted, experienced as consequence, and initiated herself).
#
# The two live interfaces have always asked for these twelve stages and the
# observation has never supplied ANY of them, so every stage rendered
# "unavailable / record not supplied" — the pages were telling the truth about
# a substrate that did not report its own stages.
#
# Every stage below is filled ONLY from the committed transition evidence.
# A stage whose mechanism is not mounted keeps refusing honestly and names what
# is missing; it is never inferred, never defaulted, and never dressed up.
# ---------------------------------------------------------------------------


def _stage(available: bool, status: str, reason: str, summary: str) -> dict[str, object]:
    return {
        "available": available,
        "status": status,
        "reason": reason,
        "summary": summary,
    }


def _unmounted_stage(status: str, reason: str) -> dict[str, object]:
    return _stage(False, status, reason, reason)


def _qualifying_sparse_attention_routes(
    evidence: dict[str, Any] | None,
) -> tuple[
    str,
    tuple[tuple[Any, ...], ...],
    tuple[tuple[Any, ...], ...],
    tuple[tuple[Any, ...], ...],
] | None:
    """Return the one exact changed reached/foregone route observation."""

    if evidence is None:
        return None
    current = tuple(evidence.get("physical_frontier_routes", ()))
    preceding = tuple(
        evidence.get("preceding_distinct_physical_frontier_routes", ())
    )
    reached_and_foregone = tuple(
        evidence.get("reached_and_foregone_physical_frontier_routes", ())
    )
    if not preceding or current == preceding:
        return None
    for phase, routes in (
        ("qualifying_interval", reached_and_foregone),
        ("current", current),
        ("preceding", preceding),
    ):
        if (
            len(routes) > 1
            and any(route[7] == 0 for route in routes)
            and any(route[7] != 0 for route in routes)
        ):
            return phase, routes, current, preceding
    return None


def _sparse_attention_route_facts(
    evidence: dict[str, Any] | None,
) -> dict[str, object] | None:
    """Project exact reached/foregone route change without selecting a winner."""

    observation = _qualifying_sparse_attention_routes(evidence)
    if observation is None:
        return None
    qualifying_phase, qualifying, current, preceding = observation
    reached = tuple(route for route in qualifying if route[7] != 0)
    foregone = tuple(route for route in qualifying if route[7] == 0)
    return {
        "changed_route_sets": True,
        "current_route_count": len(current),
        "downstream_neuron_count": len({route[3] for route in reached}),
        "foregone_route_count": len(foregone),
        "preceding_route_count": len(preceding),
        "qualifying_phase": qualifying_phase,
        "qualifying_route_count": len(qualifying),
        "transported_route_count": len(reached),
    }


def _attention_record() -> dict[str, object]:
    facts = _sparse_attention_route_facts(_last_transition_evidence)
    if facts is None:
        return _section(
            False,
            "physical_frontier_mounted_awaiting_observation",
            "sparse contact settlement is mounted, but this process has not "
            "yet observed simultaneous transported and foregone routes whose "
            "exact route set changed; no selector or attention score is reported",
            attention_score_authority=False,
            scripted_focus_authority=False,
        )
    return _section(
        True,
        "changing_sparse_physical_frontier_observed",
        "the same bounded physical settlement exposed simultaneous mounted "
        "routes, exact carrier transport through some, zero whole-carrier "
        "transport through others, and a changed adjacent route set; membrane, "
        "carrier, contact, and prior organism state caused the distinction",
        attention_score_authority=False,
        scripted_focus_authority=False,
        **facts,
    )


def _attention_stage() -> dict[str, object]:
    record = _attention_record()
    if record["available"] is not True:
        return _stage(
            False,
            str(record["status"]),
            str(record["reason"]),
            "No changed reached-versus-foregone physical frontier has been "
            "observed by this process yet.",
        )
    return _stage(
        True,
        str(record["status"]),
        str(record["reason"]),
        "Her physical activity concentrated through "
        f"{record['transported_route_count']} route(s) while "
        f"{record['foregone_route_count']} simultaneous route(s) transported "
        "no whole carrier; the route set then changed.",
    )


def _physical_choice_evidence_from_transition(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    """Bind native thought to exact opposed antagonist settlement without choosing.

    The witness reads the articulated body's own settlement law: on one joint
    axis the two opposed terminal populations discharge ``toward_minimum`` and
    ``toward_maximum`` carriers; their conserved signed difference is the
    settled intent; the body applies ``min(|intent|, remaining anatomical
    travel)`` as the signed displacement and reports the remainder as
    ``stalled_carriers``. Every check below re-verifies that exact record —
    nothing is scored, selected, or approximated. A fully stalled intent (the
    joint already at its stop) is not an applied choice, exactly as the
    retired whole-body law refused a zero applied yaw. The retired law's
    even/odd topology partition and ``signed_yaw_millidegrees`` equality are
    gone with the yaw body that defined them; the antagonist identity now
    comes from each terminal's declared axis and direction, which is where
    this body actually keeps it.
    """

    causal = evidence.get("causal_cross_context_use")
    action = evidence.get("motor_action")
    if (
        not isinstance(causal, dict)
        or not isinstance(action, dict)
    ):
        return None
    if causal.get("origin_kind") != "retained_formation":
        return None
    causal_motor = causal.get("motor_unit_recruitment")
    if not isinstance(causal_motor, dict):
        return None
    causal_formation_receipt = causal.get("formation_receipt_sha256")
    if (
        not isinstance(causal_formation_receipt, str)
        or len(causal_formation_receipt) != 64
    ):
        return None
    thought_transitions = tuple(causal.get("causal_thought_transitions", ()))
    if not thought_transitions:
        # Compatibility for one-hop callers whose thought and body evidence
        # still coexist in the same aggregate. Production trajectories carry
        # the exact matched transition on the completed causal proof below.
        thought_transitions = tuple(
            transition
            for interval in evidence.get("causal_interval_evidence", ())
            if isinstance(interval, dict)
            for transition in interval.get("causal_thought_transitions", ())
            if isinstance(transition, tuple) and len(transition) == 5
        )
    causal_path = tuple(causal.get("directed_physical_transfers", ()))
    causal_thought_transitions = tuple(
        transition
        for transition in thought_transitions
        if transition[1] == causal_formation_receipt
        and transition[4] in causal_path
    )
    if not causal_thought_transitions:
        return None
    causal_motor_lineage = causal_motor.get("motor_lineage")
    recruitments = tuple(action.get("prepared_recruitments", ()))
    if not recruitments:
        return None
    causal_motor_prepared = False
    for recruitment in recruitments:
        if not isinstance(recruitment, dict):
            return None
        if int(recruitment["outward_elementary_carriers"]) <= 0:
            return None
        if recruitment.get("motor_lineage") == causal_motor_lineage:
            causal_motor_prepared = True
        if not all(
            isinstance(transfer, dict)
            for transfer in recruitment.get("preparation_transfers", ())
        ):
            return None
    if not causal_motor_prepared:
        return None

    bindings = tuple(action.get("body_effector_bindings", ()))
    consequences = tuple(action.get("articulated_body_consequences", ()))
    if not bindings or not consequences:
        return None
    causal_axes = {
        binding["axis"]
        for binding in bindings
        if isinstance(binding, dict)
        and binding.get("motor_lineage") == causal_motor_lineage
    }
    if not causal_axes:
        return None
    for consequence in consequences:
        if not isinstance(consequence, dict):
            return None
        axis = consequence["axis"]
        if axis not in causal_axes:
            continue
        toward_minimum = int(consequence["toward_minimum_carriers"])
        toward_maximum = int(consequence["toward_maximum_carriers"])
        if toward_minimum <= 0 or toward_maximum <= 0:
            continue
        settled_signed_intent = toward_maximum - toward_minimum
        if settled_signed_intent == 0:
            continue
        signed_displacement = int(consequence["signed_displacement"])
        if signed_displacement == 0:
            continue
        stalled = int(consequence["stalled_carriers"])
        if (signed_displacement > 0) != (settled_signed_intent > 0):
            return None
        if abs(signed_displacement) + stalled != abs(settled_signed_intent):
            return None
        # The remaining identities are guaranteed by the body's settlement
        # law; a record violating any of them is corrupted evidence and the
        # whole transition is refused rather than searched for a better axis.
        if int(consequence["applied_displacement_quanta"]) != abs(
            signed_displacement
        ):
            return None
        if (
            int(consequence["successor_position"])
            - int(consequence["predecessor_position"])
        ) != signed_displacement:
            return None
        if int(consequence["opposed_carriers_per_terminal"]) != min(
            toward_minimum, toward_maximum
        ):
            return None
        # Join the settled pools back to the discharges that produced them:
        # the same tick's bindings must account, direction by direction and
        # carrier by carrier, for exactly the settled totals, and every bound
        # lineage must be present in the prepared recruitments. Severing one
        # antagonist's binding or recruitment now severs the witness even
        # when the consequence record is left untouched.
        consequence_source_tick = consequence.get("source_tick")
        directed_totals: dict[str, int] = {}
        bound_lineages: set[str] = set()
        for binding in bindings:
            if (
                not isinstance(binding, dict)
                or binding.get("axis") != axis
                or binding.get("source_tick") != consequence_source_tick
            ):
                continue
            directed_totals[binding.get("direction")] = directed_totals.get(
                binding.get("direction"), 0
            ) + int(binding["outward_elementary_carriers"])
            bound_lineages.add(binding.get("motor_lineage"))
        if directed_totals.get("toward_minimum", 0) != toward_minimum:
            return None
        if directed_totals.get("toward_maximum", 0) != toward_maximum:
            return None
        # The internal cause must have discharged AT this settlement, not
        # merely somewhere in the transaction: a consequence whose tick does
        # not carry the causal motor's own discharge is not the caused one.
        if causal_motor_lineage not in bound_lineages:
            continue
        recruited_lineages = {
            recruitment.get("motor_lineage") for recruitment in recruitments
        }
        if not bound_lineages <= recruited_lineages:
            return None
        causal_intent = action.get("causal_intent_receipt_sha256")
        if not isinstance(causal_intent, str) or len(causal_intent) != 64:
            return None
        return {
            "applied_signed_displacement_quanta": signed_displacement,
            "axis": axis,
            "axis_unit": consequence.get("unit"),
            "causal_intent_receipt_sha256": causal_intent,
            "causal_thought_transition_count": len(
                causal_thought_transitions
            ),
            "causal_thought_source_formation_receipts": tuple(
                sorted({transition[0] for transition in causal_thought_transitions})
            ),
            "consequence_source_tick": consequence.get("source_tick"),
            "formation_receipt_sha256": causal_formation_receipt,
            "internal_cause_motor_lineage": causal_motor_lineage,
            "organism_tick": evidence.get("organism_tick"),
            "prepared_intent_count": 1,
            "settled_signed_intent_carriers": settled_signed_intent,
            "stalled_carriers": stalled,
            "state_sha256": evidence.get("state_sha256"),
            "toward_maximum_antagonist_carriers": toward_maximum,
            "toward_minimum_antagonist_carriers": toward_minimum,
        }
    return None


def _attention_motor_binding_from_hop(
    hop: dict[str, Any],
) -> dict[str, Any] | None:
    """Capture exact attention transfers that also prepare motor cells."""

    attention = _sparse_attention_route_facts(hop)
    if attention is None:
        return None
    phase = str(attention["qualifying_phase"])
    if phase == "qualifying_interval":
        routes = tuple(hop.get("reached_and_foregone_physical_frontier_routes", ()))
    elif phase == "current":
        routes = tuple(hop.get("physical_frontier_routes", ()))
    elif phase == "preceding":
        routes = tuple(hop.get("preceding_distinct_physical_frontier_routes", ()))
    else:
        return None
    transfers_to_motors: dict[tuple[str, str, int, int], set[str]] = {}
    for recruitment in hop.get("motor_unit_recruitments", ()):
        if len(recruitment) != 5:
            return None
        motor_lineage, _topology, _carriers, preparation, _body_paths = recruitment
        for transfer in preparation:
            if len(transfer) != 6:
                return None
            sender, _sender_layer, receiver, _receiver_layer, ordinal, carriers = transfer
            transfers_to_motors.setdefault(
                (str(sender), str(receiver), int(ordinal), int(carriers)), set()
            ).add(str(motor_lineage))
    matched_transfers: set[tuple[str, str, int, int]] = set()
    matched_motor_lineages: set[str] = set()
    for route in routes:
        if len(route) != 8:
            return None
        signed_carriers = int(route[7])
        if signed_carriers == 0:
            continue
        transfer = (
            (str(route[0]), str(route[3]), int(route[6]), signed_carriers)
            if signed_carriers > 0
            else (str(route[3]), str(route[0]), int(route[6]), -signed_carriers)
        )
        motors = transfers_to_motors.get(transfer)
        if motors:
            matched_transfers.add(transfer)
            matched_motor_lineages.update(motors)
    if not matched_transfers:
        return None
    return {
        "attention": attention,
        "matched_attention_route_count": len(matched_transfers),
        "matched_motor_lineages": tuple(sorted(matched_motor_lineages)),
        "organism_tick": hop.get("organism_tick"),
    }


def _advance_bounded_attention_motor_bindings(
    retained: tuple[dict[str, Any], ...],
    hop: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Retain every distinct exact binding in this bounded trajectory."""

    candidate = _attention_motor_binding_from_hop(hop)
    if candidate is None or candidate in retained:
        return retained
    return (*retained, candidate)


def _completed_transaction_attention_motor_bindings(
    retained: tuple[dict[str, Any], ...],
    transition: dict[str, Any],
    motor_unit_recruitments: tuple[Any, ...],
) -> tuple[dict[str, Any], ...]:
    """Bind completed route evidence to its transaction's preparations."""

    return _advance_bounded_attention_motor_bindings(
        retained,
        {
            **transition,
            "motor_unit_recruitments": motor_unit_recruitments,
        },
    )


def _physical_choice_record() -> dict[str, object]:
    evidence = _last_tested_physical_choice_evidence
    authority = {
        "authored_goal_authority": False,
        "python_cognition_authority": False,
        "random_selector_authority": False,
        "score_selector_authority": False,
        "semantic_command_authority": False,
    }
    if evidence is None:
        return _section(
            False,
            "physical_choice_mounted_awaiting_causal_witness",
            "this process has not yet observed a native thought reassemble the "
            "retained formation that prepared both opposed antagonist populations "
            "of one joint axis and settled one nonzero applied intent",
            **authority,
        )
    return _section(
        True,
        "native_thought_settled_one_physical_continuation",
        "one native formation-to-formation thought reassembled the retained "
        "formation that entered exact motor preparation; both antagonist "
        "populations of one joint axis discharged, their conserved signed "
        "difference settled one nonzero intent, and the body applied it as its "
        "own clamped displacement",
        evidence_scope="latest_tested_physical_choice_this_process",
        **evidence,
        **authority,
    )


def _same_transition_affective_body_participation(
    evidence: dict[str, Any],
    causal: dict[str, Any],
) -> dict[str, object] | None:
    """Bind one causal occurrence to its localized affect/body trajectory.

    The retained formation and one complete layer-10 affect/body trajectory
    must each contribute to the same exact action receipt. The affect/body
    branch must include its exact locally changed contact, and that contact
    must occur on the branch's later physical motor path.
    Temporal proximity alone is not causal participation.
    The projection retains only exact paths, clocks, and receipts; it neither
    selects an action nor calls the trajectory positive, preferred, rewarding,
    joyful, good, or fun.
    """

    formation_receipt = causal.get("formation_receipt_sha256")
    reassembly_ordinal = causal.get("origin_organism_tick")
    if not isinstance(formation_receipt, str) or not isinstance(
        reassembly_ordinal, int
    ):
        return None
    motor_ordinal = causal.get("motor_organism_tick")
    if not isinstance(motor_ordinal, int) or motor_ordinal <= reassembly_ordinal:
        return None
    causal_motor = causal.get("motor_unit_recruitment")
    causal_action_receipt = causal.get("action", {}).get(
        "causal_intent_receipt_sha256"
    )
    if not isinstance(causal_motor, dict) or not isinstance(
        causal_action_receipt, str
    ):
        return None

    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for key in ("affective_motor_causal_use", "new_impression_causal_use"):
        candidate = evidence.get(key)
        if not isinstance(candidate, dict):
            continue
        changed_contact = candidate.get("changed_contact_channel_state")
        if (
            not isinstance(candidate.get("motor_unit_recruitment"), dict)
            or candidate.get("action", {}).get(
                "causal_intent_receipt_sha256"
            )
            != causal_action_receipt
            or not _exact_contact_state_participation(changed_contact)
        ):
            continue
        changed_left = changed_contact.get("left_lineage")
        changed_right = changed_contact.get("right_lineage")
        changed_ordinal = changed_contact.get("parallel_ordinal")
        if any(
            isinstance(transfer, (list, tuple))
            and len(transfer) == 4
            and {transfer[0], transfer[1]} == {changed_left, changed_right}
            and transfer[2] == changed_ordinal
            for transfer in candidate.get("directed_physical_transfers", ())
        ):
            candidates.append((candidate, changed_contact))
    if not candidates:
        return None
    affective_cause, changed_contact = candidates[0]
    affective_lineages = (
        changed_contact["left_lineage"],
        changed_contact["right_lineage"],
    )
    affective_motor_ordinal = affective_cause.get("motor_organism_tick")
    contact_ordinal = changed_contact.get("change_organism_tick")
    gradient_ordinal = affective_cause.get(
        "localized_gradient_settlement_organism_tick"
    )
    trajectory_receipt = affective_cause.get(
        "affective_trajectory_receipt_sha256"
    )
    if (
        not isinstance(affective_motor_ordinal, int)
        or not isinstance(contact_ordinal, int)
        or contact_ordinal >= affective_motor_ordinal
    ):
        return None
    complete = tuple(
        trajectory
        for trajectory in tuple(evidence.get("affective_balance_trajectories", ()))
        if isinstance(trajectory, (list, tuple))
        and len(trajectory) == 7
        and trajectory[0] in affective_lineages
        and trajectory[1] == 10
        and trajectory[3] is not None
        and trajectory[4] is not None
        and trajectory[5] is not None
        and (
            not isinstance(gradient_ordinal, int)
            or trajectory[5][0] == gradient_ordinal
        )
        and trajectory[5][0] > max(trajectory[3][0], trajectory[4][0])
        and trajectory[5][0] < affective_motor_ordinal
        and contact_ordinal == trajectory[3][0]
        and contact_ordinal == trajectory[4][0]
        and (
            trajectory_receipt is None
            or _receipt(tuple(trajectory)) == trajectory_receipt
        )
    )
    if not complete:
        return None
    trajectory = min(complete, key=lambda candidate: candidate[0])
    lineage, layer, topology, association, body, gradient, plasticity = trajectory
    occurrence_binding = (
        formation_receipt,
        reassembly_ordinal,
        motor_ordinal,
        affective_motor_ordinal,
        tuple(causal.get("directed_physical_transfers", ())),
        lineage,
        association,
        body,
        gradient,
        plasticity,
        _receipt(changed_contact),
        tuple(affective_cause.get("directed_physical_transfers", ())),
    )
    return {
        "affective_neuron_layer": layer,
        "affective_neuron_lineage": lineage,
        "affective_neuron_topology_index": topology,
        "association_influence_ordinal": association[0],
        "association_transfer_receipt_sha256": _receipt(association[1]),
        "body_influence_ordinal": body[0],
        "body_transfer_receipt_sha256": _receipt(body[1]),
        "affective_motor_organism_tick": affective_motor_ordinal,
        "retained_formation_motor_organism_tick": motor_ordinal,
        "localized_gradient_settlement_ordinal": gradient[0],
        "localized_gradient_settlement_receipt_sha256": _receipt(gradient),
        "active_contact_organism_tick": contact_ordinal,
        "active_contact_receipt_sha256": _receipt(changed_contact),
        "active_contact_left_lineage": changed_contact["left_lineage"],
        "active_contact_right_lineage": changed_contact["right_lineage"],
        "active_contact_parallel_ordinal": changed_contact[
            "parallel_ordinal"
        ],
        "active_contact_predecessor_state": changed_contact[
            "predecessor_state"
        ],
        "active_contact_successor_state": changed_contact[
            "successor_state"
        ],
        "affective_motor_path_receipt_sha256": _receipt(
            tuple(affective_cause.get("directed_physical_transfers", ()))
        ),
        "retained_formation_motor_path_receipt_sha256": _receipt(
            tuple(causal.get("directed_physical_transfers", ()))
        ),
        "whole_episode_binding_receipt_sha256": _receipt(occurrence_binding),
        "trajectory_receipt_sha256": _receipt(
            (lineage, layer, topology, association, body, gradient, plasticity)
        ),
    }


def _same_transition_metabolic_overload_exclusion(
    evidence: dict[str, Any],
) -> dict[str, object] | None:
    """Project exact observer evidence that one transaction stayed payable.

    This reads native dissipation work and refusal facts after settlement. It
    is not an interoceptor, distress signal, action input, or organism-wide
    need scalar. Zero unmet work plus zero exhausted intervals can exclude
    metabolic overload only; it cannot exclude pain or other distress.
    """

    totals = evidence.get("totals")
    capacity = evidence.get("dissipation_capacity_energy_zeptojoules")
    hop_count = evidence.get("hop_count")
    if (
        not isinstance(totals, dict)
        or not isinstance(capacity, (list, tuple))
        or len(capacity) != 2
        or not all(isinstance(value, int) for value in capacity)
        or capacity[0] <= 0
        or capacity[1] <= 0
        or not isinstance(hop_count, int)
        or hop_count <= 0
    ):
        return None
    drained = totals.get("rest_drained_dissipation_quanta")
    # Unmet dissipation is the exact standing remainder at transaction
    # completion, not work performed. Summing it across hops counts the same
    # retained material repeatedly. The final committed hop is authoritative.
    unmet = evidence.get("unmet_dissipation_quanta")
    exhausted_intervals = totals.get("energy_exhausted_interval_count")
    if not all(
        isinstance(value, int) and value >= 0
        for value in (drained, unmet, exhausted_intervals)
    ):
        return None
    if unmet != 0 or exhausted_intervals != 0:
        return None
    facts = (
        hop_count,
        drained,
        unmet,
        exhausted_intervals,
        tuple(capacity),
    )
    return {
        "dissipation_capacity_energy_zeptojoules": tuple(capacity),
        "energy_exhausted_interval_count": exhausted_intervals,
        "hop_count": hop_count,
        "rest_drained_dissipation_quanta": drained,
        "unmet_dissipation_quanta": unmet,
        "witness_receipt_sha256": _receipt(facts),
        "organism_sensing_authority": False,
    }


def _same_transition_localized_metabolic_strain(
    evidence: dict[str, Any],
    affective_participation: dict[str, object] | None,
) -> dict[str, object] | None:
    """Project one reached body receptor's exact retained dissipation state.

    The neuron already owns this state.  This function neither creates an
    interoceptor nor translates local metabolic strain into pain, distress,
    valence, reward, or action.
    """

    if affective_participation is None:
        return None
    evaluated = tuple(
        evidence.get(
            "localized_metabolic_strain_evaluated_body_receptor_lineages", ()
        )
    )
    observed = tuple(evidence.get("localized_metabolic_strain", ()))
    if not evaluated or not all(
        isinstance(lineage, str) and re.fullmatch(r"[0-9a-f]{32}", lineage)
        for lineage in evaluated
    ):
        return None
    records: list[dict[str, object]] = []
    for entry in observed:
        if not isinstance(entry, (list, tuple)) or len(entry) != 7:
            return None
        lineage, layer, topology, ordinal, psi, gate, plastic = entry
        if (
            lineage not in evaluated
            or layer != 5
            or not isinstance(topology, int)
            or not isinstance(ordinal, int)
            or not isinstance(psi, (list, tuple))
        ):
            return None
        try:
            psi_quanta = tuple(int(value) for value in psi)
            gate_quanta = int(gate)
            plastic_quanta = int(plastic)
        except (TypeError, ValueError):
            return None
        if (
            any(value < 0 for value in psi_quanta)
            or gate_quanta < 0
            or plastic_quanta < 0
            or (
                not any(psi_quanta)
                and gate_quanta == 0
                and plastic_quanta == 0
            )
        ):
            return None
        records.append(
            {
                "body_receptor_lineage": lineage,
                "body_receptor_layer": layer,
                "body_receptor_topology_index": topology,
                "cognitive_ordinal": ordinal,
                "psi_dissipation_quanta": psi_quanta,
                "gate_dissipation_quanta": gate_quanta,
                "plastic_dissipation_quanta": plastic_quanta,
            }
        )
    facts = (
        tuple(sorted(evaluated)),
        tuple(
            (
                record["body_receptor_lineage"],
                record["body_receptor_topology_index"],
                record["cognitive_ordinal"],
                record["psi_dissipation_quanta"],
                record["gate_dissipation_quanta"],
                record["plastic_dissipation_quanta"],
            )
            for record in records
        ),
        affective_participation["trajectory_receipt_sha256"],
    )
    return {
        "evaluated_body_receptor_count": len(evaluated),
        "evaluated_body_receptor_lineages": tuple(sorted(evaluated)),
        "localized_nonzero_strain_count": len(records),
        "localized_nonzero_strain": tuple(records),
        "affective_trajectory_receipt_sha256": affective_participation[
            "trajectory_receipt_sha256"
        ],
        "witness_receipt_sha256": _receipt(facts),
        "organism_sensing_authority": False,
        "pain_authority": False,
    }


def _typed_body_displacements(
    action: dict[str, Any],
) -> tuple[tuple[int, str, str, int, int, int], ...] | None:
    """Return the exact nonzero typed body changes from one native action."""

    consequences = action.get("articulated_body_consequences")
    if not isinstance(consequences, (list, tuple)) or not consequences:
        return None
    displacements: list[tuple[int, str, str, int, int, int]] = []
    for consequence in consequences:
        if not isinstance(consequence, dict):
            return None
        axis = consequence.get("axis")
        unit = consequence.get("unit")
        if (
            not isinstance(axis, str)
            or not axis
            or not isinstance(unit, str)
            or not unit
        ):
            return None
        numeric = (
            consequence.get("source_tick"),
            consequence.get("predecessor_position"),
            consequence.get("successor_position"),
            consequence.get("signed_displacement"),
            consequence.get("applied_displacement_quanta"),
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in numeric
        ):
            return None
        source_tick, predecessor, successor, signed, applied = numeric
        if source_tick <= 0 or successor - predecessor != signed:
            return None
        if signed == 0:
            if applied != 0:
                return None
            continue
        if applied <= 0 or abs(signed) != applied:
            return None
        displacements.append(
            (source_tick, axis, unit, predecessor, successor, signed)
        )
    return tuple(sorted(displacements)) or None


def _sensorimotor_play_episode_from_transition(
    evidence: dict[str, Any],
    _physical_choice: dict[str, Any] | None,
    intake: str,
    *,
    allow_external_participant: bool = False,
) -> dict[str, Any] | None:
    """Project one endogenous retained-formation body episode compactly.

    This observer does not decide whether to move. It accepts only a movement
    whose already-completed native evidence binds internal formation
    recurrence, exact typed body action, and sensed body return.
    """

    if not (
        intake.startswith("continuous-environment:")
        or (
            allow_external_participant
            and intake.startswith("external-participant-world-action:")
        )
    ):
        return None
    causal = evidence.get("causal_cross_context_use")
    action = evidence.get("motor_action")
    if (
        not isinstance(causal, dict)
        or causal.get("origin_kind") != "retained_formation"
        or not isinstance(action, dict)
    ):
        return None
    causal_action = causal.get("action")
    consequence = causal.get("sensed_consequence")
    if not isinstance(causal_action, dict) or not isinstance(consequence, dict):
        return None
    action_receipt = action.get("causal_intent_receipt_sha256")
    formation_receipt = causal.get("formation_receipt_sha256")
    state_sha256 = evidence.get("state_sha256")
    body_state_before_sha256 = action.get("body_state_before_sha256")
    body_state_after_sha256 = action.get("body_state_after_sha256")
    if not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (
            action_receipt,
            formation_receipt,
            state_sha256,
            body_state_before_sha256,
            body_state_after_sha256,
        )
    ):
        return None
    if (
        causal_action.get("causal_intent_receipt_sha256") != action_receipt
        or causal_action.get("body_state_before_sha256")
        != body_state_before_sha256
        or causal_action.get("body_state_after_sha256") != body_state_after_sha256
    ):
        return None
    origin_tick = int(causal.get("origin_organism_tick", 0))
    motor_tick = int(causal.get("motor_organism_tick", 0))
    consequence_tick = int(consequence.get("successor_organism_tick", 0))
    world_revision = int(action.get("world_revision") or 0)
    world_state_before_sha256 = action.get("world_state_before_sha256")
    world_state_after_sha256 = action.get("world_state_after_sha256")
    world_state_available = all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (world_state_before_sha256, world_state_after_sha256)
    )
    body_displacements = _typed_body_displacements(action)
    vestibular_ticks = int(consequence.get("vestibular_tick_count", 0))
    body_receptors = int(
        consequence.get("externally_perturbed_body_receptor_count", 0)
    )
    if (
        origin_tick <= 0
        or motor_tick <= origin_tick
        or consequence_tick < motor_tick
        or body_displacements is None
        or body_receptors <= 0
        or body_state_before_sha256 == body_state_after_sha256
    ):
        return None
    # Source ticks identify the occurrence, not the movement shape. Variation
    # compares the exact typed physical displacement, independent of when it ran.
    body_displacement_receipt = _receipt(
        tuple(displacement[1:] for displacement in body_displacements)
    )
    episode = {
        "action_causal_intent_receipt_sha256": action_receipt,
        "body_axis_count": len({row[1] for row in body_displacements}),
        "body_displacement_receipt_sha256": body_displacement_receipt,
        "body_displacements": body_displacements,
        "body_receptor_return_count": body_receptors,
        "body_state_after_sha256": body_state_after_sha256,
        "body_state_before_sha256": body_state_before_sha256,
        "causal_path_receipt_sha256": _receipt(causal),
        "consequence_organism_tick": consequence_tick,
        "formation_receipt_sha256": formation_receipt,
        "motor_organism_tick": motor_tick,
        "origin_organism_tick": origin_tick,
        "state_sha256": state_sha256,
        "vestibular_tick_count": vestibular_ticks,
        "world_revision": world_revision,
    }
    if world_state_available:
        episode["world_state_after_sha256"] = world_state_after_sha256
        episode["world_state_before_sha256"] = world_state_before_sha256
    affective_participation = _same_transition_affective_body_participation(
        evidence, causal
    )
    if affective_participation is not None:
        episode["affective_body_participation"] = affective_participation
    localized_metabolic_strain = _same_transition_localized_metabolic_strain(
        evidence,
        affective_participation,
    )
    if localized_metabolic_strain is not None:
        episode["localized_metabolic_strain"] = localized_metabolic_strain
    overload_exclusion = _same_transition_metabolic_overload_exclusion(evidence)
    if overload_exclusion is not None:
        episode["metabolic_overload_exclusion"] = overload_exclusion
    participant_causal_use = evidence.get("participant_sensory_causal_use")
    if isinstance(participant_causal_use, dict):
        episode["participant_sensory_causal_use"] = participant_causal_use
    return episode


def _advance_bounded_sensorimotor_play_evidence(
    candidate: dict[str, Any] | None,
    completed: dict[str, Any] | None,
    evidence: dict[str, Any],
    physical_choice: dict[str, Any] | None,
    intake: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Observe movement, cessation, and later varied retained return.

    The evidence is constant-size process observation. It has no route back to
    cognition and cannot cause, reward, repeat, or suppress an action.
    """

    if completed is not None and all(
        isinstance(completed[key].get("localized_metabolic_strain"), dict)
        for key in ("first_episode", "return_episode")
    ):
        return candidate, completed
    episode = _sensorimotor_play_episode_from_transition(
        evidence, physical_choice, intake
    )
    if episode is None:
        return candidate, completed
    if candidate is None:
        return episode, completed
    if (
        episode["action_causal_intent_receipt_sha256"]
        == candidate["action_causal_intent_receipt_sha256"]
    ):
        return candidate, completed
    if episode["formation_receipt_sha256"] != candidate["formation_receipt_sha256"]:
        # Keep no list of competing candidates. The later episode becomes the
        # sole bounded candidate for a future return of its own formation.
        return episode, completed
    if (
        episode["origin_organism_tick"] <= candidate["consequence_organism_tick"]
        or episode["body_displacement_receipt_sha256"]
        == candidate["body_displacement_receipt_sha256"]
    ):
        return candidate, completed
    play = {
        "activity": "sensorimotor_body_movement",
        "changed_body_context": (
            episode["body_state_before_sha256"]
            != candidate["body_state_before_sha256"]
        ),
        "changed_world_context": (
            isinstance(episode.get("world_state_before_sha256"), str)
            and isinstance(candidate.get("world_state_before_sha256"), str)
            and episode["world_state_before_sha256"]
            != candidate["world_state_before_sha256"]
        ),
        "first_episode": candidate,
        "formation_receipt_sha256": candidate["formation_receipt_sha256"],
        "movement_ceased_before_return": True,
        "return_episode": episode,
        "return_gap_organism_ticks": (
            episode["origin_organism_tick"]
            - candidate["consequence_organism_tick"]
        ),
        "varied_displacement": True,
    }
    play["evidence_receipt_sha256"] = _receipt(play)
    # Basic play remains truthful even when its first episode preceded the
    # localized affect/body path. Keep the latest qualified episode as the one
    # bounded candidate so a later varied return can replace, rather than
    # permanently freeze, that incomplete process-local observation.
    play_has_complete_localized_strain = all(
        isinstance(play[key].get("localized_metabolic_strain"), dict)
        for key in ("first_episode", "return_episode")
    )
    return (
        None
        if play_has_complete_localized_strain
        else episode
        if isinstance(episode.get("localized_metabolic_strain"), dict)
        else None,
        play,
    )


def _body_owned_laughter_episode_from_transition(
    evidence: dict[str, Any],
    play_evidence: dict[str, Any] | None,
    intake: str,
) -> dict[str, Any] | None:
    """Bind one already-enacted playful vocal/body episode without causing it."""

    if not intake.startswith("continuous-environment:") or not isinstance(
        play_evidence, dict
    ):
        return None
    first_play = play_evidence.get("first_episode")
    return_play = play_evidence.get("return_episode")
    if (
        not isinstance(first_play, dict)
        or not isinstance(return_play, dict)
        or not _complete_positive_engagement_episode(first_play)
        or not _complete_positive_engagement_episode(return_play)
        or not (
            bool(play_evidence.get("changed_body_context"))
            or bool(play_evidence.get("changed_world_context"))
        )
    ):
        return None
    causal = evidence.get("causal_cross_context_use")
    action = evidence.get("motor_action")
    articulation = evidence.get("articulation")
    if (
        not isinstance(causal, dict)
        or causal.get("origin_kind") != "retained_formation"
        or not isinstance(action, dict)
        or not isinstance(articulation, dict)
    ):
        return None
    formation_receipt = causal.get("formation_receipt_sha256")
    if formation_receipt != play_evidence.get("formation_receipt_sha256"):
        return None
    affective = _same_transition_affective_body_participation(evidence, causal)
    if affective is None:
        return None
    causal_motor = causal.get("motor_unit_recruitment")
    causal_action = causal.get("action")
    consequence = causal.get("sensed_consequence")
    if not all(
        isinstance(value, dict)
        for value in (causal_motor, causal_action, consequence)
    ):
        return None
    motor_lineage = causal_motor.get("motor_lineage")
    action_receipt = action.get("causal_intent_receipt_sha256")
    state_sha256 = evidence.get("state_sha256")
    pressure_sha256 = articulation.get("pressure_sha256")
    if not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (
            formation_receipt,
            action_receipt,
            state_sha256,
            pressure_sha256,
        )
    ):
        return None
    if not isinstance(motor_lineage, str) or not re.fullmatch(
        r"[0-9a-f]{32}", motor_lineage
    ):
        return None
    if causal_action.get("causal_intent_receipt_sha256") != action_receipt:
        return None

    matched_articulators: list[tuple[str, int, int, str]] = []
    for recruitment in tuple(articulation.get("recruitments", ())):
        if not isinstance(recruitment, (list, tuple)) or len(recruitment) != 4:
            return None
        articulator_lineage, topology, carriers, transfers = recruitment
        if not isinstance(transfers, (list, tuple)):
            return None
        for transfer in transfers:
            if not isinstance(transfer, (list, tuple)) or len(transfer) != 6:
                return None
            (
                sender,
                sender_layer,
                receiver,
                receiver_layer,
                _ordinal,
                moved,
            ) = transfer
            if (
                {sender, receiver} == {motor_lineage, articulator_lineage}
                and {int(sender_layer), int(receiver_layer)} == {12, 13}
                and int(moved) > 0
            ):
                matched_articulators.append(
                    (
                        str(articulator_lineage),
                        int(topology),
                        int(carriers),
                        _receipt(tuple(transfer)),
                    )
                )
                break
    if not matched_articulators:
        return None

    sensory_consequence = action.get("sensory_consequence")
    visual_return = (
        sensory_consequence.get("visual")
        if isinstance(sensory_consequence, dict)
        else None
    )
    origin_tick = int(causal.get("origin_organism_tick", 0))
    motor_tick = int(causal.get("motor_organism_tick", 0))
    consequence_tick = int(consequence.get("successor_organism_tick", 0))
    organism_tick = int(evidence.get("organism_tick", 0))
    body_displacements = _typed_body_displacements(action)
    world_revision = int(action.get("world_revision") or 0)
    if (
        origin_tick <= 0
        or motor_tick <= origin_tick
        or consequence_tick < motor_tick
        or organism_tick != consequence_tick
        or body_displacements is None
        or int(consequence.get("externally_perturbed_body_receptor_count", 0)) <= 0
        or not isinstance(visual_return, dict)
        or int(visual_return.get("transported", 0)) <= 0
        or int(articulation.get("articulatory_body_port_count", 0)) != 4
        or int(
            articulation.get("articulatory_body_nonquiescent_port_count", 0)
        )
        != 3
        or int(articulation.get("articulatory_body_perturbed_neuron_count", 0)) <= 0
        or int(articulation.get("pressure_sample_count", 0)) <= 0
        or int(
            articulation.get("peak_transducer_surface_velocity_pcm", 0)
        )
        <= 0
        or int(articulation.get("glottal_open_samples_at_apex", 0)) <= 0
        or int(articulation.get("mouth_area_square_millimetres_at_apex", 0)) <= 0
        or int(
            articulation.get(
                "perioral_area_displacement_square_millimetres", 0
            )
        )
        == 0
        or int(articulation.get("self_hearing_hop_count", 0)) <= 0
        or int(articulation.get("self_hearing_transitioned_neuron_count", 0)) <= 0
    ):
        return None
    episode = {
        "action_causal_intent_receipt_sha256": action_receipt,
        "affective_body_trajectory_receipt_sha256": affective[
            "trajectory_receipt_sha256"
        ],
        "articulatory_body_nonquiescent_port_count": 3,
        "body_axis_count": len({row[1] for row in body_displacements}),
        "body_displacement_receipt_sha256": _receipt(
            tuple(displacement[1:] for displacement in body_displacements)
        ),
        "causal_motor_lineage": motor_lineage,
        "consequence_organism_tick": consequence_tick,
        "formation_receipt_sha256": formation_receipt,
        "glottal_open_samples_at_apex": articulation[
            "glottal_open_samples_at_apex"
        ],
        "matched_articulator_count": len(matched_articulators),
        "matched_motor_to_articulator_receipt_sha256": _receipt(
            tuple(sorted(matched_articulators))
        ),
        "mouth_area_square_millimetres_at_apex": articulation[
            "mouth_area_square_millimetres_at_apex"
        ],
        "origin_organism_tick": origin_tick,
        "peak_transducer_surface_velocity_pcm": articulation[
            "peak_transducer_surface_velocity_pcm"
        ],
        "perioral_area_displacement_square_millimetres": articulation[
            "perioral_area_displacement_square_millimetres"
        ],
        "play_evidence_receipt_sha256": play_evidence[
            "evidence_receipt_sha256"
        ],
        "pressure_sample_count": articulation["pressure_sample_count"],
        "pressure_sha256": pressure_sha256,
        "self_hearing_hop_count": articulation["self_hearing_hop_count"],
        "self_hearing_transitioned_neuron_count": articulation[
            "self_hearing_transitioned_neuron_count"
        ],
        "state_sha256": state_sha256,
        "visual_receptor_return_count": int(visual_return["transported"]),
        "vestibular_tick_count": int(consequence.get("vestibular_tick_count", 0)),
        "world_revision": world_revision,
    }
    episode["evidence_receipt_sha256"] = _receipt(episode)
    return episode


def _advance_bounded_body_owned_laughter_evidence(
    candidate: dict[str, Any] | None,
    completed: dict[str, Any] | None,
    evidence: dict[str, Any],
    play_evidence: dict[str, Any] | None,
    intake: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Observe one complete playful vocal episode and its later recurrence."""

    if completed is not None:
        return candidate, completed
    episode = _body_owned_laughter_episode_from_transition(
        evidence, play_evidence, intake
    )
    if episode is None:
        return candidate, completed
    if candidate is None:
        return episode, completed
    if episode["action_causal_intent_receipt_sha256"] == candidate[
        "action_causal_intent_receipt_sha256"
    ]:
        return candidate, completed
    if (
        episode["formation_receipt_sha256"]
        != candidate["formation_receipt_sha256"]
        or episode["origin_organism_tick"]
        <= candidate["consequence_organism_tick"]
    ):
        return candidate, completed
    laughter = {
        "context": "learned_playful_formation_recurrence",
        "first_episode": candidate,
        "formation_receipt_sha256": candidate["formation_receipt_sha256"],
        "recurrence_gap_organism_ticks": (
            episode["origin_organism_tick"]
            - candidate["consequence_organism_tick"]
        ),
        "return_episode": episode,
        "varied_acoustic_pressure": (
            episode["pressure_sha256"] != candidate["pressure_sha256"]
        ),
        "varied_body_displacement": (
            episode["body_displacement_receipt_sha256"]
            != candidate["body_displacement_receipt_sha256"]
        ),
    }
    laughter["evidence_receipt_sha256"] = _receipt(laughter)
    return None, laughter


def _body_owned_laughter_record() -> dict[str, object]:
    evidence = _last_body_owned_laughter_evidence
    authority = {
        "animation_authority": False,
        "canned_audio_authority": False,
        "named_emotion_authority": False,
        "python_cognition_authority": False,
        "reward_authority": False,
        "semantic_label_causation_authority": False,
        "tts_authority": False,
    }
    if evidence is None:
        return _section(
            False,
            "playful_body_owned_laughter_unproved",
            "this process has not yet observed two complete ordinary episodes "
            "in which the learned playful formation physically caused the "
            "affect/body, motor-to-articulator, vocal-body, pressure, "
            "self-hearing, body-orientation, and world-return chain",
            **authority,
        )
    return _section(
        True,
        "body_owned_laughter_recurred",
        "the learned playful retained formation twice caused exact localized "
        "affect/body settlement, a physical layer-12-to-layer-13 discharge, "
        "breath/glottis/mouth/perioral movement, emitted acoustic pressure, "
        "cochlear self-hearing, typed body movement, and sensed world return; "
        "the later episode is recurrence evidence, not a claim about a named "
        "feeling or another participant's state",
        evidence_scope="latest_completed_bounded_laughter_witness_this_process",
        **evidence,
        **authority,
    )


def _complete_positive_engagement_episode(episode: dict[str, Any]) -> bool:
    """Whether one Guala action carries the required local body physics."""

    affect = episode.get("affective_body_participation")
    strain = episode.get("localized_metabolic_strain")
    overload = episode.get("metabolic_overload_exclusion")
    return (
        isinstance(affect, dict)
        and isinstance(strain, dict)
        and int(strain.get("evaluated_body_receptor_count", 0)) > 0
        and isinstance(overload, dict)
        and int(overload.get("unmet_dissipation_quanta", -1)) == 0
        and int(overload.get("energy_exhausted_interval_count", -1)) == 0
    )


def _public_sensorimotor_episode_record(
    episode: dict[str, Any],
) -> dict[str, object]:
    """Project one bounded episode without copying native coordinate bodies."""

    public = {
        key: episode[key]
        for key in (
            "action_causal_intent_receipt_sha256",
            "body_axis_count",
            "body_displacement_receipt_sha256",
            "body_receptor_return_count",
            "body_state_after_sha256",
            "body_state_before_sha256",
            "causal_path_receipt_sha256",
            "consequence_organism_tick",
            "formation_receipt_sha256",
            "motor_organism_tick",
            "origin_organism_tick",
            "state_sha256",
            "vestibular_tick_count",
            "world_revision",
            "world_state_after_sha256",
            "world_state_before_sha256",
        )
        if key in episode
    }
    affective = episode.get("affective_body_participation")
    if isinstance(affective, dict):
        public["affective_body_participation"] = {
            key: affective[key]
            for key in (
                "active_contact_left_lineage",
                "active_contact_organism_tick",
                "active_contact_parallel_ordinal",
                "active_contact_receipt_sha256",
                "active_contact_right_lineage",
                "affective_motor_organism_tick",
                "affective_motor_path_receipt_sha256",
                "affective_neuron_layer",
                "affective_neuron_lineage",
                "affective_neuron_topology_index",
                "localized_gradient_settlement_ordinal",
                "retained_formation_motor_organism_tick",
                "retained_formation_motor_path_receipt_sha256",
                "trajectory_receipt_sha256",
                "whole_episode_binding_receipt_sha256",
            )
            if key in affective
        }
        public["affective_body_participation"].update(
            {
                "exact_contact_coordinates_resident": True,
                "exact_contact_coordinates_transported": False,
            }
        )
    overload = episode.get("metabolic_overload_exclusion")
    if isinstance(overload, dict):
        public["metabolic_overload_exclusion"] = {
            key: overload[key]
            for key in (
                "energy_exhausted_interval_count",
                "hop_count",
                "organism_sensing_authority",
                "rest_drained_dissipation_quanta",
                "unmet_dissipation_quanta",
                "witness_receipt_sha256",
            )
            if key in overload
        }
        public["metabolic_overload_exclusion"].update(
            {
                "exact_capacity_coordinates_resident": True,
                "exact_capacity_coordinates_transported": False,
            }
        )
    strain = episode.get("localized_metabolic_strain")
    if isinstance(strain, dict):
        public["localized_metabolic_strain"] = {
            key: strain[key]
            for key in (
                "affective_trajectory_receipt_sha256",
                "evaluated_body_receptor_count",
                "localized_nonzero_strain_count",
                "organism_sensing_authority",
                "pain_authority",
                "witness_receipt_sha256",
            )
            if key in strain
        }
        public["localized_metabolic_strain"].update(
            {
                "exact_strain_coordinates_resident": True,
                "exact_strain_coordinates_transported": False,
            }
        )
    return public


def _advance_social_play_on_other_body_action(
    candidate: dict[str, Any] | None,
    action: dict[str, Any],
) -> dict[str, Any]:
    """Advance or begin one exact other/Guala turn-taking opportunity."""

    if (
        candidate is not None
        and candidate.get("stage") == "awaiting_other_return"
        and action["actor_body_id"] == candidate["invitation"]["actor_body_id"]
        and int(action["world_revision_before"])
        >= int(candidate["first_guala_episode"]["world_revision"]) + 1
    ):
        return {
            **candidate,
            "other_return": action,
            "stage": "awaiting_guala_return",
        }
    return {"invitation": action, "stage": "awaiting_guala_response"}


def _participant_stimulus_caused_episode(
    episode: dict[str, Any],
    participant_action: dict[str, Any],
) -> bool:
    """Require an exact participant receptor-to-motor physical path."""

    causal = episode.get("participant_sensory_causal_use")
    if not isinstance(causal, dict):
        return False
    action = causal.get("action")
    transfers = causal.get("directed_physical_transfers")
    lineages = causal.get("perturbed_receptor_lineages")
    return (
        causal.get("origin_kind") == "external_participant_sensory"
        and causal.get(
            "participant_action_causal_intent_receipt_sha256"
        )
        == participant_action.get("causal_intent_receipt_sha256")
        and isinstance(action, dict)
        and action.get("causal_intent_receipt_sha256")
        == episode.get("action_causal_intent_receipt_sha256")
        and isinstance(transfers, (list, tuple))
        and len(transfers) > 0
        and isinstance(lineages, (list, tuple))
        and len(lineages) > 0
        and int(causal.get("receptor_settlement_organism_tick", 0))
        < int(causal.get("motor_organism_tick", 0))
    )


def _advance_bounded_reciprocal_social_play_evidence(
    candidate: dict[str, Any] | None,
    completed: dict[str, Any] | None,
    evidence: dict[str, Any],
    physical_choice: dict[str, Any] | None,
    intake: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Observe exact other/Guala/other/Guala physical turn-taking."""

    if completed is not None:
        return candidate, completed
    episode = _sensorimotor_play_episode_from_transition(
        evidence,
        physical_choice,
        intake,
        allow_external_participant=True,
    )
    if episode is None or candidate is None:
        return candidate, completed
    stage = candidate.get("stage")
    if stage == "awaiting_guala_response":
        invitation = candidate["invitation"]
        if int(episode["world_revision"]) < int(
            invitation["world_revision_after"]
        ):
            return candidate, completed
        if (
            not _participant_stimulus_caused_episode(episode, invitation)
            or not _complete_positive_engagement_episode(episode)
        ):
            return candidate, completed
        return {
            **candidate,
            "first_guala_episode": episode,
            "stage": "awaiting_other_return",
        }, completed
    if stage != "awaiting_guala_return":
        return candidate, completed
    first = candidate["first_guala_episode"]
    other_return = candidate["other_return"]
    if (
        int(episode["world_revision"])
        < int(other_return["world_revision_after"])
        or episode["action_causal_intent_receipt_sha256"]
        == first["action_causal_intent_receipt_sha256"]
        or episode["origin_organism_tick"] <= first["consequence_organism_tick"]
        or episode["body_displacement_receipt_sha256"]
        == first["body_displacement_receipt_sha256"]
        or not _participant_stimulus_caused_episode(episode, other_return)
        or not _complete_positive_engagement_episode(episode)
    ):
        return candidate, completed
    social = {
        "activity": "reciprocal_embodied_turn_taking",
        "first_formation_receipt_sha256": first[
            "formation_receipt_sha256"
        ],
        "first_guala_episode": first,
        "invitation": candidate["invitation"],
        "other_body_id": candidate["invitation"]["actor_body_id"],
        "other_return": other_return,
        "return_formation_receipt_sha256": episode[
            "formation_receipt_sha256"
        ],
        "return_guala_episode": episode,
    }
    social["evidence_receipt_sha256"] = _receipt(social)
    return None, social


def _reciprocal_social_joy_section() -> dict[str, object]:
    evidence = _last_reciprocal_social_play_evidence
    if evidence is None:
        return _section(
            False,
            "reciprocal_social_play_unproved",
            "no authenticated other-body action and return have yet been "
            "joined by exact world receipts to two voluntary Guala responses",
        )
    public_evidence = {
        key: evidence[key]
        for key in (
            "activity",
            "evidence_receipt_sha256",
            "first_formation_receipt_sha256",
            "other_body_id",
            "return_formation_receipt_sha256",
        )
        if key in evidence
    }
    for source, target in (
        ("first_guala_episode", "first_guala_episode"),
        ("return_guala_episode", "return_guala_episode"),
    ):
        episode = evidence.get(source)
        if isinstance(episode, dict):
            public_evidence[target] = _public_sensorimotor_episode_record(episode)
    return _section(
        True,
        "reciprocal_social_positive_engagement_observed",
        "an authenticated other body acted, Guala responded through her own "
        "retained formation and localized body/fluid/plastic physics, the other "
        "body returned, and Guala voluntarily returned again; each response may "
        "lawfully recruit a different retained formation; this is "
        "reciprocal engagement evidence, not joy, goodness, or the other "
        "participant's state",
        **public_evidence,
        behavioral_evidence_only=False,
        localized_physical_participation_evidence=True,
        goodness_authority=False,
        joy_authority=False,
        named_emotion_authority=False,
        other_participant_enjoyment_authority=False,
        reward_authority=False,
    )


def _sensorimotor_play_record() -> dict[str, object]:
    """Truthful play evidence without fun, joy, humor, or laughter inflation."""

    authority = {
        "activity_label_cognition_authority": False,
        "python_action_authority": False,
        "random_selector_authority": False,
        "reward_authority": False,
        "timer_choice_authority": False,
    }
    laughter = {"laughter": _body_owned_laughter_record()}
    if _last_sensorimotor_play_evidence is None:
        return _section(
            False,
            "awaiting_varied_retained_formation_sensorimotor_return",
            "this process has not yet observed two distinct unattended body "
            "actions from the same internally reassembled retained formation, "
            "with the first action completed before a varied later return",
            **authority,
            affective_engagement=_section(
                False,
                "play_affective_body_participation_unproved",
                "no completed varied play witness is available to test against "
                "same-transition localized affect/body physics",
            ),
            overload_exclusion=_section(
                False,
                "play_metabolic_overload_exclusion_unproved",
                "no completed varied play witness is available to test for "
                "zero unmet dissipation and zero exhausted intervals",
            ),
            localized_metabolic_strain=_section(
                False,
                "localized_metabolic_strain_path_unproved",
                "no completed varied play witness is available to test exact "
                "layer-5 body-receptor dissipation",
                pain_authority=False,
            ),
            distress_exclusion=_section(
                False,
                "localized_distress_path_unmounted",
                "no localized nociceptive or other aversive body pathway is "
                "mounted, so absence of distress cannot be claimed",
            ),
            fun=_section(
                False,
                "positive_engagement_trajectory_unproved",
                "sensorimotor return does not yet prove positive valence, "
                "distress exclusion, preference, or cross-context return",
            ),
            social_joy=_reciprocal_social_joy_section(),
            **laughter,
        )
    first_affective = _last_sensorimotor_play_evidence["first_episode"].get(
        "affective_body_participation"
    )
    return_affective = _last_sensorimotor_play_evidence["return_episode"].get(
        "affective_body_participation"
    )
    affective_available = isinstance(first_affective, dict) and isinstance(
        return_affective, dict
    )
    first_overload = _last_sensorimotor_play_evidence["first_episode"].get(
        "metabolic_overload_exclusion"
    )
    return_overload = _last_sensorimotor_play_evidence["return_episode"].get(
        "metabolic_overload_exclusion"
    )
    overload_excluded = isinstance(first_overload, dict) and isinstance(
        return_overload, dict
    )
    first_localized_strain = _last_sensorimotor_play_evidence["first_episode"].get(
        "localized_metabolic_strain"
    )
    return_localized_strain = _last_sensorimotor_play_evidence[
        "return_episode"
    ].get("localized_metabolic_strain")
    localized_strain_path_available = isinstance(
        first_localized_strain, dict
    ) and isinstance(return_localized_strain, dict)
    localized_strain_observed = localized_strain_path_available and (
        int(first_localized_strain["localized_nonzero_strain_count"]) > 0
        or int(return_localized_strain["localized_nonzero_strain_count"]) > 0
    )
    positive_engagement_observed = (
        affective_available
        and overload_excluded
        and localized_strain_path_available
        and bool(_last_sensorimotor_play_evidence.get("changed_world_context"))
    )
    public_play = {
        key: _last_sensorimotor_play_evidence[key]
        for key in (
            "activity",
            "changed_body_context",
            "changed_world_context",
            "evidence_receipt_sha256",
            "formation_receipt_sha256",
            "movement_ceased_before_return",
            "return_gap_organism_ticks",
            "varied_displacement",
        )
        if key in _last_sensorimotor_play_evidence
    }
    for key in ("first_episode", "return_episode"):
        episode = _last_sensorimotor_play_evidence.get(key)
        if isinstance(episode, dict):
            public_play[key] = _public_sensorimotor_episode_record(episode)
    return _section(
        True,
        "sensorimotor_play_observed",
        "the organism ended one self-initiated retained-formation body movement "
        "and later returned through the same formation to a different exact "
        "movement, with both consequences sensed; this proves basic "
        "sensorimotor play only",
        endogenous_initiation=True,
        evidence_scope="latest_completed_bounded_play_witness_this_process",
        voluntary_return=True,
        **public_play,
        **authority,
        affective_engagement=_section(
            affective_available,
            (
                "both_play_actions_shared_exact_localized_affective_body_physics"
                if affective_available
                else "play_affective_body_participation_incomplete"
            ),
            (
                "each autonomous play action's exact retained formation and a "
                "layer-10 association/body path with retained contact-channel "
                "reinforcement and later localized membrane-gradient settlement "
                "converged on "
                "the same exact motor event and action receipt; this is "
                "affective participation, not a named emotion or fun"
                if affective_available
                else "one or both play actions lacked exact motor-event "
                "convergence with a complete same-transition localized "
                "affect/body trajectory"
            ),
            first_trajectory_receipt_sha256=(
                first_affective.get("trajectory_receipt_sha256")
                if isinstance(first_affective, dict)
                else None
            ),
            return_trajectory_receipt_sha256=(
                return_affective.get("trajectory_receipt_sha256")
                if isinstance(return_affective, dict)
                else None
            ),
            named_emotion_authority=False,
            reward_authority=False,
        ),
        overload_exclusion=_section(
            overload_excluded,
            (
                "both_play_actions_completed_without_metabolic_overload"
                if overload_excluded
                else "play_metabolic_overload_exclusion_incomplete"
            ),
            (
                "both autonomous play transactions had mounted dissipation "
                "capacity, zero unmet dissipation, and zero exhausted native "
                "intervals; this is read-only overload evidence, not an "
                "organism sensor or positive affect"
                if overload_excluded
                else "one or both play transactions lacked exact zero-unmet "
                "dissipation and zero-exhaustion evidence"
            ),
            first_witness_receipt_sha256=(
                first_overload.get("witness_receipt_sha256")
                if isinstance(first_overload, dict)
                else None
            ),
            return_witness_receipt_sha256=(
                return_overload.get("witness_receipt_sha256")
                if isinstance(return_overload, dict)
                else None
            ),
            organism_sensing_authority=False,
        ),
        localized_metabolic_strain=_section(
            localized_strain_path_available,
            (
                "localized_metabolic_strain_observed"
                if localized_strain_observed
                else "localized_metabolic_strain_path_evaluated_at_zero"
                if localized_strain_path_available
                else "localized_metabolic_strain_path_incomplete"
            ),
            (
                "one or both autonomous play transactions retained exact "
                "nonzero lane-separated dissipation in a reached layer-5 "
                "body receptor; this is metabolic strain, not a pain or "
                "named-distress claim"
                if localized_strain_observed
                else "both autonomous play transactions evaluated their "
                "reached layer-5 body-receptor paths at exact zero retained "
                "dissipation"
                if localized_strain_path_available
                else "one or both play transactions lacked exact localized "
                "body-receptor strain evidence"
            ),
            first_witness_receipt_sha256=(
                first_localized_strain.get("witness_receipt_sha256")
                if isinstance(first_localized_strain, dict)
                else None
            ),
            return_witness_receipt_sha256=(
                return_localized_strain.get("witness_receipt_sha256")
                if isinstance(return_localized_strain, dict)
                else None
            ),
            pain_authority=False,
            organism_sensing_authority=False,
        ),
        distress_exclusion=_section(
            localized_strain_path_available and not localized_strain_observed,
            (
                "localized_metabolic_strain_absent_on_both_play_transactions"
                if localized_strain_path_available and not localized_strain_observed
                else "localized_metabolic_strain_observed"
                if localized_strain_observed
                else "localized_distress_path_incomplete"
            ),
            (
                "both play transactions evaluated the mounted localized "
                "metabolic-strain class at exact zero; this excludes only "
                "that one strain class, not pain or every form of distress"
                if localized_strain_path_available and not localized_strain_observed
                else "localized metabolic strain was present, so this narrow "
                "distress exclusion is refused"
                if localized_strain_observed
                else "metabolic headroom alone cannot exclude pain or other "
                "distress; localized body-receptor evidence is incomplete"
            ),
            exclusion_scope="localized_metabolic_strain_only",
            organism_sensing_authority=False,
        ),
        fun=_section(
            positive_engagement_observed,
            (
                "positive_engagement_trajectory_observed"
                if positive_engagement_observed
                else "positive_engagement_trajectory_unproved"
            ),
            (
                "the same retained play formation ended one body action and "
                "later reassembled in a changed authenticated world state, "
                "settled a different action through exact attention and "
                "affect/body physics, and sensed both consequences; this "
                "behavioral trajectory is fun evidence without a valence, "
                "reward, preference, or named-emotion scalar"
                if positive_engagement_observed
                else "the completed play witness lacks one or more exact "
                "positive-engagement relationships: localized affect/body "
                "participation, payable settlement, body-state evaluation, "
                "or voluntary return in a changed authenticated world state"
            ),
            behavioral_evidence_only=True,
            distress_absence_authority=False,
            named_emotion_authority=False,
            preference_scalar_authority=False,
            reward_authority=False,
        ),
        social_joy=_reciprocal_social_joy_section(),
        **laughter,
    )


def _working_causal_state_record() -> dict[str, object]:
    """Report exact adjacent carrier continuation without calling it thought."""

    evidence = _last_transition_evidence or {}
    continuations = tuple(evidence.get("working_causal_continuations", ()))
    settlements = tuple(evidence.get("settled_working_frontier", ()))
    if not continuations:
        return _section(
            False,
            "working_frontier_mounted_awaiting_continuation",
            "the exact one-interval carrier frontier is mounted, but this "
            "process has not yet observed an intermediate neuron continue a "
            "prior transfer without being independently reseeded",
            retained_history_authority=False,
            semantic_working_memory_authority=False,
        )
    first, second = continuations[0]
    settled_exact_continuation = bool(settlements and settlements[0] == second)
    return _section(
        settled_exact_continuation,
        (
            "bounded_working_cause_continued_and_settled"
            if settled_exact_continuation
            else "working_cause_continued_awaiting_settlement"
        ),
        (
            "one exact whole-carrier transfer caused its receiving neuron to "
            "send across a second contact in the adjacent interval without "
            "an independent current seed; that exact second cause then lost "
            "propagation authority"
            if settled_exact_continuation
            else "one exact whole-carrier transfer continued across a second "
            "contact in the adjacent interval without an independent current "
            "seed, but settlement of that same cause has not yet been observed"
        ),
        continuation=(first, second),
        settled_transfer=settlements[0] if settlements else None,
        retained_history_authority=False,
        semantic_working_memory_authority=False,
    )


def _physical_prediction_record() -> dict[str, object]:
    """Report bounded physical alternatives and their later body test."""

    retained_test = _last_tested_prediction_evidence
    evidence = retained_test or _last_transition_evidence or {}
    provenance = {
        "evidence_scope": (
            "latest_tested_physical_event"
            if retained_test is not None
            else "latest_committed_transition"
        ),
        "evidence_organism_tick": evidence.get("organism_tick"),
        "evidence_state_sha256": evidence.get("state_sha256"),
        "evidence_intake": evidence.get("intake"),
    }
    alternatives = tuple(evidence.get("physical_prediction_alternatives", ()))
    consequences = tuple(evidence.get("body_consequence_transfers", ()))
    if len(alternatives) != 2:
        return _section(
            False,
            "physical_prediction_mounted_awaiting_alternatives",
            "no committed transaction in this process has yet continued one "
            "intrinsic cause through two distinct layer-11 routes into "
            "distinct retained body relations",
            planner_authority=False,
            score_authority=False,
            semantic_outcome_authority=False,
            **provenance,
        )
    if not consequences:
        return _section(
            False,
            "ordered_physical_alternatives_awaiting_body_consequence",
            "two exact internally continued alternatives were observed before "
            "the later authentic body consequence required to test them",
            alternatives=alternatives,
            planner_authority=False,
            score_authority=False,
            semantic_outcome_authority=False,
            **provenance,
        )
    consequence = consequences[0]
    agreement = tuple(
        index
        for index, alternative in enumerate(alternatives)
        if alternative[1][1] == consequence[1]
    )
    contradiction = tuple(
        index
        for index, alternative in enumerate(alternatives)
        if alternative[1][1] == consequence[0]
    )
    if not agreement and not contradiction:
        return _section(
            False,
            "body_consequence_did_not_reach_predicted_relation",
            "an authentic returned body relation was observed, but neither "
            "endpoint matched either prior physical alternative",
            alternatives=alternatives,
            consequence=consequence,
            planner_authority=False,
            score_authority=False,
            semantic_outcome_authority=False,
            **provenance,
        )
    return _section(
        True,
        (
            "physical_alternative_agreed_with_later_body_consequence"
            if agreement
            else "physical_alternatives_contradicted_by_later_body_consequence"
        ),
        "two exact internally continued layer-11 alternatives preceded an "
        "authentic returned body relation; equality is tested only by the "
        "retained consequence lineage and creates no winner, reward, or plan",
        alternatives=alternatives,
        consequence=consequence,
        agreeing_alternative_indices=agreement,
        contradicted_alternative_indices=contradiction,
        planner_authority=False,
        score_authority=False,
        semantic_outcome_authority=False,
        **provenance,
    )


def _affective_balance_record() -> dict[str, object]:
    """Report one exact body/association/local-gradient trajectory."""

    retained_test = _last_tested_affective_balance_evidence
    evidence = retained_test or _last_transition_evidence or {}
    trajectories = tuple(evidence.get("affective_balance_trajectories", ()))
    complete = next(
        (
            trajectory
            for trajectory in trajectories
            if _complete_local_affective_balance_trajectory(trajectory)
        ),
        None,
    )
    authority = {
        "affect_score_authority": False,
        "named_emotion_authority": False,
        "python_decision_authority": False,
        "reward_authority": False,
    }
    if complete is None:
        return _section(
            False,
            "affective_balance_mounted_awaiting_complete_trajectory",
            "layer-7 association, layer-8 body regulation, layer-10 junction, "
            "and localized membrane-gradient recovery are mounted, but this "
            "process has not yet observed both physical influences followed "
            "by a later nonzero local gradient on the same cell",
            evidence_scope=(
                "latest_tested_physical_event"
                if retained_test is not None
                else "latest_committed_transition"
            ),
            **authority,
        )
    lineage, layer, topology, association, body, gradient, plasticity = complete

    def transfer_record(
        timed: tuple[int, tuple[str, str, int, int]], source_layer: int
    ) -> dict[str, object]:
        ordinal, transfer = timed
        return {
            "cognitive_ordinal": ordinal,
            "source_layer": source_layer,
            "sender_lineage": transfer[0],
            "receiver_lineage": transfer[1],
            "parallel_contact_ordinal": transfer[2],
            "exact_transfer_coordinates_resident": True,
            "exact_transfer_coordinates_transported": False,
        }

    localized_recovery: dict[str, object] | None = None
    if isinstance(plasticity, (list, tuple)) and len(plasticity) == 10:
        localized_recovery = {
            "cognitive_ordinal": plasticity[0],
            "retained_support_changed": plasticity[6] != plasticity[7],
            "exact_coordinates_resident": True,
            "exact_coordinates_transported": False,
        }

    return _section(
        True,
        "body_association_perturbation_followed_by_local_gradient",
        "the same physical layer-10 cell received exact association and body "
        "contact consequences and, at a strictly later cognitive ordinal, "
        "its own localized recovery-fluid compartment moved its retained "
        "membrane gradient; any support geometry shown is exact adjacent "
        "recovery evidence, not reinforcement authority. This is affective-"
        "balance physics, not a named "
        "emotion, preference, reward, or score",
        evidence_scope=(
            "latest_tested_physical_event"
            if retained_test is not None
            else "latest_committed_transition"
        ),
        evidence_organism_tick=evidence.get("organism_tick"),
        evidence_state_sha256=evidence.get("state_sha256"),
        evidence_intake=evidence.get("intake"),
        trajectory={
            "neuron_lineage": lineage,
            "neuron_layer": layer,
            "neuron_topology_index": topology,
            "association_influence": transfer_record(association, 7),
            "body_influence": transfer_record(body, 8),
            "localized_gradient_settlement": {
                "cognitive_ordinal": gradient[0],
                "membrane_gradient_changed": gradient[1] != gradient[3],
                "returned_carriers_observed": gradient[4] != 0,
                "pumped_carriers_observed": gradient[5] != 0,
                "unreturned_carriers_observed": gradient[6] != 0,
                "exact_coordinates_resident": True,
                "exact_coordinates_transported": False,
            },
            "localized_recovery_settlement": localized_recovery,
        },
        **authority,
    )


def _localized_fluid_chemistry_record() -> dict[str, object]:
    """Report one exact reached/unreached local-fluid conservation witness."""

    retained_test = _last_tested_localized_fluid_chemistry_evidence
    evidence = retained_test or _last_transition_evidence or {}
    settlements = tuple(evidence.get("localized_fluid_chemistry", ()))
    witness = next(
        (
            settlement
            for settlement in settlements
            if settlement[4][4] + settlement[4][5] > 0
            and settlement[4][6] == 0
        ),
        None,
    )
    authority = {
        "named_chemical_authority": False,
        "python_decision_authority": False,
        "reward_authority": False,
        "score_authority": False,
    }
    if witness is None:
        return _section(
            False,
            "localized_fluid_chemistry_mounted_awaiting_reached_unreached_witness",
            "the native local recovery-fluid path is mounted, but this process "
            "has not yet observed a changed reached neuron beside an unchanged "
            "active neuron or the separately retained developmental-resting "
            "population outside the same bounded organism pump phase",
            evidence_scope=(
                "latest_tested_physical_event"
                if retained_test is not None
                else "latest_committed_transition"
            ),
            **authority,
        )

    lineage, layer, topology, ordinal, contact, carrier, reservoirs = witness
    (
        interval_microseconds,
        contact_power,
        reached_count,
        changed_reached_count,
        unchanged_unreached_count,
        unchanged_developmental_resting_count,
        changed_unreached_count,
    ) = contact
    (
        predecessor_charge,
        successor_charge,
        predecessor_intracellular,
        predecessor_extracellular,
        successor_intracellular,
        successor_extracellular,
        returned_carriers,
        pumped_carriers,
    ) = carrier
    predecessor_reservoir, successor_reservoir, gradient_work = reservoirs

    predecessor_material = predecessor_intracellular + predecessor_extracellular
    successor_material = successor_intracellular + successor_extracellular
    signed_transfer = returned_carriers + pumped_carriers
    material_conserved = (
        predecessor_material == successor_material
        and successor_intracellular == predecessor_intracellular - signed_transfer
        and successor_extracellular == predecessor_extracellular + signed_transfer
    )
    work = Fraction(*gradient_work)
    predecessor_available, predecessor_spent, predecessor_thermal = (
        Fraction(*part) for part in predecessor_reservoir
    )
    successor_available, successor_spent, successor_thermal = (
        Fraction(*part) for part in successor_reservoir
    )
    if pumped_carriers != 0 and returned_carriers == 0:
        energy_conserved = (
            successor_available == predecessor_available - work
            and successor_spent == predecessor_spent + work
            and successor_thermal == predecessor_thermal
        )
        settlement_mode = "active_gradient_pump"
    elif returned_carriers != 0 and pumped_carriers == 0:
        energy_conserved = (
            successor_available == predecessor_available
            and successor_spent == predecessor_spent
            and successor_thermal == predecessor_thermal + work
        )
        settlement_mode = "passive_gradient_return"
    else:
        energy_conserved = False
        settlement_mode = "invalid_mixed_or_motionless_settlement"
    locality_conserved = (
        reached_count > 0
        and changed_reached_count > 0
        and unchanged_unreached_count + unchanged_developmental_resting_count > 0
        and changed_unreached_count == 0
    )
    exact_conservation = material_conserved and energy_conserved and locality_conserved

    return _section(
        exact_conservation,
        (
            "localized_contact_conserved"
            if exact_conservation
            else "localized_contact_conservation_failed"
        ),
        "one reached neuron changed through its mounted local recovery-fluid "
        "contact; active cells outside the reached frontier remained outside the "
        "native sparse write boundary and the separate developmental-resting population "
        "remained outside the "
        "mutable pump boundary; carrier material and reservoir energy reconcile exactly",
        evidence_scope=(
            "latest_tested_physical_event"
            if retained_test is not None
            else "latest_committed_transition"
        ),
        evidence_organism_tick=evidence.get("organism_tick"),
        evidence_state_sha256=evidence.get("state_sha256"),
        evidence_intake=evidence.get("intake"),
        target={
            "neuron_lineage": lineage,
            "neuron_layer": layer,
            "neuron_topology_index": topology,
            "cognitive_ordinal": ordinal,
        },
        contact={
            "interval_microseconds": interval_microseconds,
            "reached_neuron_count": reached_count,
            "changed_reached_neuron_count": changed_reached_count,
            "unchanged_unreached_active_neuron_count": unchanged_unreached_count,
            "unchanged_unreached_developmental_resting_neuron_count": (
                unchanged_developmental_resting_count
            ),
            "changed_unreached_neuron_count": changed_unreached_count,
            "exact_coordinates_resident": True,
            "exact_coordinates_transported": False,
        },
        carrier_material={
            "membrane_gradient_changed": predecessor_charge != successor_charge,
            "returned_carriers_observed": returned_carriers != 0,
            "pumped_carriers_observed": pumped_carriers != 0,
            "material_conserved": material_conserved,
            "exact_coordinates_resident": True,
            "exact_coordinates_transported": False,
        },
        reservoir_energy={
            "settlement_mode": settlement_mode,
            "energy_conserved": energy_conserved,
            "exact_coordinates_resident": True,
            "exact_coordinates_transported": False,
        },
        locality_conserved=locality_conserved,
        exact_conservation=exact_conservation,
        **authority,
    )


def _describe_intake(intake: str) -> tuple[str, str]:
    """What this experience actually was, in words, and what it carried.

    The stage ledger exists so a person can see what SHE experienced. An
    internal counter is evidence, not meaning, so the meaning is stated first
    and the counters support it.
    """

    if intake.startswith("curriculum-card:"):
        parts = intake.split(":")
        card_id = parts[1] if len(parts) > 1 else "a card"
        mode = parts[2] if len(parts) > 2 else "full"
        try:
            experience = _read_manifest_card(card_id)
            surface = str(experience.get("surface", {}).get("path", ""))
            name = surface.rsplit("/", 1)[-1].removesuffix(".png")
            name = name.replace("-v1", "").replace("-", " ")
        except (KeyError, OSError, ValueError):
            name = card_id
        glimpse = " a partial glimpse of" if mode == "partial" else ""
        return (
            f"She was shown{glimpse} the {name} card",
            "its picture fell on her light receptors while the tutor's voice "
            "reached both ears",
        )
    if intake.startswith("live-sight:"):
        return (
            "She saw the real world through a live camera",
            "real light off real objects, through the same eye her cards use",
        )
    if intake.startswith("continuous-environment:"):
        return (
            "Her persistent world continued to reach her senses",
            "the current room, body, chemistry, and quiet acoustic field were "
            "sampled as physical experience; transport selected no thought "
            "or action",
        )
    if intake.startswith("nutrition:"):
        return ("She was fed", "material intake, not a sensory experience")
    if intake.startswith("sound-frame") or intake.startswith("pcm-session:"):
        return ("She was played a sound", "pressure at both ears")
    return (f"An experience arrived ({intake})", "declared by the caller")


def _experience_stage_ledger_record() -> dict[str, object]:
    """The twelve stages of the most recent committed experience."""

    absent = {
        "intent": _unmounted_stage(
            "not_observed_in_this_experience",
            "This most recent committed experience contains no observed "
            "native attention-to-motor preparation.",
        ),
        "action": _unmounted_stage(
            "not_observed_in_this_experience",
            "This most recent committed experience contains no applied "
            "native body action.",
        ),
        "consequence": _unmounted_stage(
            "not_observed_in_this_experience",
            "This most recent committed experience contains no returned "
            "sensory consequence from an applied body action.",
        ),
    }
    if _last_transition_evidence is None:
        pending = _unmounted_stage(
            "no_transition_this_process",
            "no admitted native transition has been committed by this process",
        )
        return _section(
            False,
            "no_transition_this_process",
            "no admitted native transition has been committed by this process, "
            "so no experience has stages to report",
            stages={
                key: (
                    _attention_stage()
                    if key == "attention"
                    else absent[key]
                    if key in absent
                    else pending
                )
                for key in EXPERIENCE_STAGE_ORDER
            },
        )

    evidence = _last_transition_evidence
    # WHOLE-EXPERIENCE, NOT LAST HOP.  The transition evidence carries the
    # final hop's own numbers at the top level and the sums for the whole
    # committed experience under "totals".  An experience is the whole
    # presentation, so the ledger reports the sums; reporting the last hop
    # would say "0 fractals" for the very lesson that grew 27 of them.
    totals = evidence.get("totals") or {}

    def summed(key: str) -> int:
        value = totals.get(key)
        return value if isinstance(value, int) else evidence.get(key, 0)

    intake = str(evidence.get("intake", "unknown"))
    hops = evidence.get("hop_count", 0)
    deliveries = summed("dsf_delivery_count")
    transitioned = summed("physically_transitioned_neuron_count")
    fractals = summed("complete_neuron_fractal_count")
    recurrent = summed("recurrent_complete_neuron_fractal_count")
    reassemblies = summed("partial_cue_reassembly_count")
    mosaics = evidence.get("cognitive_mosaic_count", 0)
    cohorts = summed("current_cohort_evaluation_count")
    attention_motor_bindings = evidence.get("attention_motor_bindings")
    motor_action = evidence.get("motor_action")
    applied_action = (
        motor_action
        if isinstance(motor_action, dict)
        and motor_action.get("disposition") == "applied"
        and motor_action.get("moved") is True
        and isinstance(motor_action.get("signed_yaw_millidegrees"), int)
        and motor_action.get("signed_yaw_millidegrees") != 0
        else None
    )
    sensory_consequence = (
        applied_action.get("sensory_consequence")
        if applied_action is not None
        and isinstance(applied_action.get("sensory_consequence"), dict)
        and applied_action.get("sensory_consequence", {}).get(
            "action_receipt_sha256"
        )
        == applied_action.get("causal_intent_receipt_sha256")
        else None
    )
    matched_routes = (
        sum(
            int(binding.get("matched_attention_route_count", 0))
            for binding in attention_motor_bindings
            if isinstance(binding, dict)
        )
        if isinstance(attention_motor_bindings, tuple)
        else 0
    )
    if matched_routes > 0:
        absent["intent"] = _stage(
            True,
            "native_attention_motor_preparation_observed",
            "the current experience itself retained the exact physical "
            "attention-to-motor binding; no authored goal, score, semantic "
            "command, or Python selector supplies it",
            f"Her changing physical attention reached motor preparation "
            f"through {matched_routes} matched route(s).",
        )
    if applied_action is not None:
        signed_yaw = applied_action.get("signed_yaw_millidegrees")
        absent["action"] = _stage(
            True,
            "native_body_action_applied",
            "the current experience carries the committed native motor "
            "receipt and its applied world displacement",
            f"Her native motor discharge moved her body by {signed_yaw} "
            "millidegrees of yaw.",
        )
    if sensory_consequence is not None:
        consequence_tick = sensory_consequence.get("organism_tick")
        absent["consequence"] = _stage(
            True,
            "native_action_consequence_returned",
            "the applied action's own receipt returned through the mounted "
            "sensory body in this committed experience",
            f"Her action consequence returned through her senses at organism "
            f"tick {consequence_tick}.",
        )

    what, carried = _describe_intake(intake)
    seconds = (hops * INTAKE_HOP_MILLISECONDS) / 1000 if hops else 0

    stages: dict[str, object] = {
        "capture": _stage(
            True,
            "committed_intake",
            "what arrived is declared by whoever presented it; the organism "
            "never invents what it was shown",
            f"{what} — {carried}.",
        ),
        "presentation": _stage(
            True,
            "committed_hops",
            "an experience is delivered as successive 250 ms moments on one "
            "shared clock, each carrying every sense she has",
            f"It lasted {seconds:.2f} seconds, delivered as {hops} moments of "
            f"a quarter-second each.",
        ),
        "admission": _stage(
            True,
            "admitted_and_committed",
            "nothing reaches her unless her own body admits it, and the "
            "result is written to disk before anyone is told about it",
            "Her body accepted it as one real experience, and the result is "
            "safely stored.",
        ),
        "receptor": _stage(
            transitioned > 0,
            "receptor_settlement_committed" if transitioned else "no_receptor_change",
            "these are neurons whose physical state genuinely changed, "
            "decoded from her body — not a count of messages sent to her",
            (
                f"{transitioned} of her neurons were physically changed by it."
                if transitioned
                else "Nothing in her physically changed."
            ),
        ),
        "dsf": _stage(
            deliveries > 0,
            "local_field_delivered" if deliveries else "no_delivery",
            "every neuron that is reached receives the complete local field, "
            "never a score or a summary of it",
            (
                f"The full physical field reached her neurons {deliveries} "
                f"times over {cohorts} settlement(s)."
                if deliveries
                else "No field reached any neuron."
            ),
        ),
        "recurrence": _stage(
            reassemblies > 0 or recurrent > 0,
            "recurrence_observed" if (reassemblies or recurrent) else "no_recurrence",
            "recognition is a PART of something bringing back the WHOLE of "
            "it; a first showing has nothing to bring back",
            (
                f"She recognised something — {reassemblies} time(s) a piece of "
                f"this brought back a whole memory she already had."
                if reassemblies
                else "She did not recognise anything in this — either it was "
                     "new to her, or nothing was there to bring back."
            ),
        ),
        "hierarchy": _stage(
            mosaics > 0,
            "retained_formations" if mosaics else "no_formation",
            "these are whole retained memories; nothing above a memory (a "
            "memory made of memories) is built yet",
            (
                f"She is holding {mosaics} memory/memories in total."
                if mosaics
                else "She is holding no memories yet."
            ),
        ),
        "learning": _stage(
            fractals > 0 or reassemblies > 0,
            "structure_changed" if (fractals or reassemblies) else "no_structural_change",
            "learning is a real change in retained structure — new impressions "
            "the first time, recognition afterwards",
            (
                (
                    f"She was changed by it: {fractals} new impression(s) formed"
                    if fractals
                    else "She was changed by it"
                )
                + (
                    f" and {reassemblies} recognition(s) happened."
                    if reassemblies
                    else "."
                )
                if (fractals or reassemblies)
                else "Nothing was learned — this left no lasting change in her."
            ),
        ),
        "attention": _attention_stage(),
        **absent,
    }
    return _section(
        True,
        "committed_experience_stages",
        "the stages of the most recent committed experience, each read from "
        "its own record; stages whose mechanism is not mounted refuse and say "
        "what is missing",
        stages={key: stages[key] for key in EXPERIENCE_STAGE_ORDER},
    )


def _last_transition_record() -> dict[str, object]:
    if _last_transition_evidence is None:
        return _section(
            False,
            "no_transition_this_process",
            "no admitted native transition has been committed by this process",
        )
    source = _last_transition_evidence

    def sequence_count(name: str) -> int:
        value = source.get(name, ())
        return len(value) if isinstance(value, (list, tuple)) else 0

    # This is a witness that a transition happened, not a second copy of the
    # transition. Never pass through per-neuron, per-contact, per-formation,
    # or per-body-axis arrays from the resident boundary.
    evidence: dict[str, object] = {
        key: source[key]
        for key in (
            "intake",
            "hop_count",
            "vestibular_tick_count",
            "predecessor_organism_tick",
            "organism_tick",
            "predecessor_state_sha256",
            "state_sha256",
            "energy_exhausted",
        )
        if key in source
    }
    totals = source.get("totals")
    if isinstance(totals, dict):
        evidence["totals"] = {
            key: value
            for key, value in totals.items()
            if isinstance(key, str)
            and isinstance(value, (bool, int))
            and not isinstance(value, float)
        }
    ingress = source.get("receptor_ingress")
    if isinstance(ingress, dict):
        sense_counts = ingress.get("sense_counts")
        evidence["receptor_ingress"] = {
            "changing_count": ingress.get("changing_count"),
            "quiescent_count": ingress.get("quiescent_count"),
            "source_hop_count": ingress.get("source_hop_count"),
            "sense_counts": (
                {
                    key: value
                    for key, value in sense_counts.items()
                    if isinstance(key, str)
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                }
                if isinstance(sense_counts, dict)
                else {}
            ),
        }
    for field, count_field in (
        ("emitted_neuron_fractals", "emitted_neuron_fractal_count"),
        ("motor_unit_recruitments", "motor_unit_recruitment_count"),
        ("articulatory_unit_recruitments", "articulatory_unit_recruitment_count"),
        ("organic_mosaic_relations", "organic_mosaic_relation_count"),
        ("physical_frontier_routes", "physical_frontier_route_count"),
        (
            "preceding_distinct_physical_frontier_routes",
            "preceding_distinct_physical_frontier_route_count",
        ),
        (
            "reached_and_foregone_physical_frontier_routes",
            "reached_and_foregone_physical_frontier_route_count",
        ),
        ("working_causal_continuations", "working_causal_continuation_count"),
        ("body_consequence_transfers", "body_consequence_transfer_count"),
        ("affective_balance_trajectories", "affective_balance_trajectory_count"),
        ("localized_fluid_chemistry", "localized_fluid_chemistry_count"),
    ):
        evidence[count_field] = sequence_count(field)
    motor_action = source.get("motor_action")
    if isinstance(motor_action, dict):
        consequence = motor_action.get("sensory_consequence")
        bounded_action: dict[str, object] = {
            key: motor_action[key]
            for key in (
                "schema",
                "causal_intent_receipt_sha256",
                "body_transition_receipt_sha256",
                "disposition",
                "moved",
                "continuous_cognition",
                "body_state_before_sha256",
                "body_state_after_sha256",
                "motor_unit_recruitment_count",
                "vestibular_tick_count",
                "world_revision",
                "world_state_before_sha256",
                "world_state_after_sha256",
            )
            if key in motor_action
        }
        bounded_action.update(
            {
                "body_effector_binding_count": len(
                    motor_action.get("body_effector_bindings", ())
                ),
                "articulated_body_consequence_count": len(
                    motor_action.get("articulated_body_consequences", ())
                ),
                "body_proprioceptive_source_count": len(
                    motor_action.get("body_proprioceptive_sources", ())
                ),
                "motor_body_afferent_path_count": len(
                    motor_action.get("motor_body_afferent_paths", ())
                ),
            }
        )
        if isinstance(consequence, dict):
            bounded_action["sensory_consequence"] = {
                key: consequence[key]
                for key in (
                    "causal_receipt_sha256",
                    "organism_identity",
                    "organism_tick",
                    "state_sha256",
                    "externally_perturbed_body_receptor_count",
                    "internal_metabolic_receptor_count",
                    "receptor_ingress_changing_count",
                    "receptor_ingress_quiescent_count",
                    "receptor_ingress_sense_counts",
                    "articulated_body_proprioceptive",
                    "vestibular",
                )
                if key in consequence
            }
        evidence["motor_action"] = bounded_action
    external_use = source.get("externally_reassembled_formation_causal_use")
    if isinstance(external_use, dict):
        cue_lineages = external_use.get("external_cue_lineages")
        directed_transfers = external_use.get("directed_physical_transfers")
        action = external_use.get("action")
        sensed_consequence = external_use.get("sensed_consequence")
        changed_contact = external_use.get("changed_contact_channel_state")
        bounded_external_use: dict[str, object] = {
            key: external_use[key]
            for key in (
                "formation_receipt_sha256",
                "recurrent_lineage",
                "reassembly_organism_tick",
                "motor_organism_tick",
            )
            if key in external_use
        }
        bounded_external_use.update(
            {
                "external_cue_lineage_count": (
                    sum(
                        1
                        for lineage in cue_lineages
                        if isinstance(lineage, str)
                    )
                    if isinstance(cue_lineages, (list, tuple))
                    else 0
                ),
                "directed_physical_transfer_count": (
                    len(directed_transfers)
                    if isinstance(directed_transfers, (list, tuple))
                    else 0
                ),
                "observer_authority": False,
            }
        )
        if isinstance(action, dict):
            bounded_external_use["action"] = {
                key: action[key]
                for key in (
                    "causal_intent_receipt_sha256",
                    "body_state_before_sha256",
                    "body_state_after_sha256",
                    "body_effector_binding_count",
                    "root_motion",
                    "signed_root_yaw_millidegrees",
                )
                if key in action
            }
        if isinstance(sensed_consequence, dict):
            bounded_external_use["sensed_consequence"] = {
                key: sensed_consequence[key]
                for key in (
                    "body_proprioceptive_source_count",
                    "externally_perturbed_body_receptor_count",
                    "successor_organism_tick",
                    "successor_state_sha256",
                )
                if key in sensed_consequence
            }
        if isinstance(changed_contact, dict):
            predecessor_state = changed_contact.get("predecessor_state")
            successor_state = changed_contact.get("successor_state")
            bounded_external_use["changed_contact_channel_state"] = {
                **{
                    key: changed_contact[key]
                    for key in (
                        "change_organism_tick",
                        "contact_cognitive_ordinal",
                        "left_lineage",
                        "right_lineage",
                        "parallel_ordinal",
                    )
                    if key in changed_contact
                },
                "exact_state_changed": predecessor_state != successor_state,
                "exact_state_coordinates_transported": False,
            }
        evidence["externally_reassembled_formation_causal_use"] = (
            bounded_external_use
        )
    return _section(
        True,
        "committed_admitted_transition",
        "bounded receipt and counts for the most recent committed transition; "
        "all neuronal, contact, formation, and body-array detail remains only "
        "in the resident state identified by state_sha256",
        **evidence,
    )


def _articulation_record() -> dict[str, object]:
    """The last committed native typed-body acoustic consequence."""

    articulation = _last_tested_articulation_evidence
    if articulation is None and _last_transition_evidence is not None:
        articulation = _last_transition_evidence.get("articulation")
    if not isinstance(articulation, dict):
        return _unmounted(
            "no native typed motor discharge has yet caused a persisted "
            "articulatory body and self-hearing transition in this process"
        )
    pressure_sha256 = articulation.get("pressure_sha256")
    self_heard = bool(
        articulation.get("self_hearing_hop_count") == 1
        and articulation.get("self_hearing_pressure_sha256") == pressure_sha256
        and articulation.get("self_hearing_receptor_ingress_count")
        == EAR_PORT_COUNT
    )
    playback = next(
        (
            item
            for item in reversed(_native_pressure_audio_cache)
            if item.get("pressure_sha256") == pressure_sha256
        ),
        None,
    )
    playback_record = _section(
        bool(
            isinstance(playback, dict)
            and playback.get("pressure_sha256") == pressure_sha256
        ),
        (
            "latest_native_pressure_available"
            if isinstance(playback, dict)
            and playback.get("pressure_sha256") == pressure_sha256
            else "native_pressure_bytes_not_retained_in_this_process"
        ),
        (
            "the browser may fetch the exact bounded PCM pressure emitted by "
            "this committed articulation; playback is user-controlled and "
            "has no path back into cognition"
            if isinstance(playback, dict)
            and playback.get("pressure_sha256") == pressure_sha256
            else "the articulation evidence is present, but its transient "
            "pressure bytes are not available in this process"
        ),
        endpoint=(
            NATIVE_PRESSURE_AUDIO_ENDPOINT
            + f"?pressure_sha256={pressure_sha256}"
            if isinstance(playback, dict)
            and playback.get("pressure_sha256") == pressure_sha256
            else None
        ),
        format="pcm_s16le_mono_wav",
        pressure_sha256=pressure_sha256,
        sample_count=(
            playback.get("sample_count")
            if isinstance(playback, dict)
            and playback.get("pressure_sha256") == pressure_sha256
            else None
        ),
        sample_rate_hz=(
            playback.get("sample_rate_hz")
            if isinstance(playback, dict)
            and playback.get("pressure_sha256") == pressure_sha256
            else None
        ),
    )
    return _section(
        self_heard,
        (
            "native_typed_articulation_and_self_hearing_committed"
            if self_heard
            else "native_typed_articulation_emitted_self_hearing_not_proven"
        ),
        (
            "one or more exact typed layer-12 motor discharges moved bounded "
            "vocal tissue; the identical pressure receipt then "
            "entered every mounted ear receptor in the same committed causal "
            "successor"
            if self_heard
            else "typed articulatory pressure was emitted, but this record has "
            "no exact same-pressure receipt proving its return through every "
            "mounted ear receptor"
        ),
        native_pressure_playback=playback_record,
        **articulation,
    )


def _causal_cross_context_use_record() -> dict[str, object]:
    evidence = _last_causal_cross_context_use_evidence
    if evidence is None:
        return _section(
            False,
            "awaiting_retained_formation_to_sensed_consequence",
            "this process has not yet observed one retained formation reassemble, "
            "cross the motor path, move the body, and return through body senses",
            scripted_action_authority=False,
        )
    changed_contact = evidence.get("changed_contact_channel_state")
    exact_contact_bound = isinstance(changed_contact, dict)
    public_contact: dict[str, object] | None = None
    if exact_contact_bound:
        predecessor_state = changed_contact.get("predecessor_state")
        successor_state = changed_contact.get("successor_state")
        public_contact = {
            key: changed_contact[key]
            for key in (
                "change_organism_tick",
                "contact_cognitive_ordinal",
                "left_lineage",
                "right_lineage",
                "parallel_ordinal",
            )
            if key in changed_contact
        }
        public_contact.update(
            {
                "exact_state_changed": predecessor_state != successor_state,
                "exact_state_coordinates_resident": True,
                "exact_state_coordinates_transported": False,
                "resident_state_sha256": evidence.get("state_sha256"),
            }
        )
    return _section(
        True,
        (
            "retained_contact_changed_then_reached_body_action_and_sensed_consequence"
            if exact_contact_bound
            else "retained_formation_caused_body_action_and_sensed_consequence"
        ),
        "one internally reassembled retained formation crossed exact physical "
        "contacts into motor discharge, moved the persistent body, and returned "
        "through vestibular/body receptors",
        evidence_scope="latest_causal_cross_context_use_this_process",
        evidence_organism_tick=evidence.get("organism_tick"),
        evidence_state_sha256=evidence.get("state_sha256"),
        formation_receipt_sha256=evidence.get("formation_receipt_sha256"),
        intake=evidence.get("intake"),
        internally_caused=True,
        scripted_action_authority=False,
        changed_contact_channel_state=public_contact,
        exact_changed_contact_bound_to_motor_path=exact_contact_bound,
        action=evidence.get("action"),
        sensed_consequence=evidence.get("sensed_consequence"),
    )


def _body_record(native: dict[str, Any]) -> dict[str, object]:
    articulated = native["articulated_body"]
    causal = _causal_cross_context_use_record()
    return _section(
        True,
        (
            "persistent_articulated_body_mounted"
            if articulated["proprioception_initialized"]
            else "persistent_articulated_body_awaiting_first_proprioceptive_interval"
        ),
        "the native CURRENT body persistently carries one fixed 45-axis local "
        "configuration and its 90 explicit antagonist terminals; this is "
        "truthful local embodiment state, while root locomotion, manipulation, "
        "mechanical load/work and complete consequence re-entry remain open "
        "A-013 work",
        articulated_body=articulated,
        complete_embodiment_live_closed=False,
        world_mounted=WORLD_AUTHORIZED,
        vestibular_mounted=VESTIBULAR_AUTHORIZED,
        prior_causal_cross_context_use=causal,
    )


def _intrinsic_curiosity_evidence_from_transition(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    """Project one exact new-impression/imbalance/action causal witness."""

    causal = evidence.get("new_impression_causal_use")
    if not isinstance(causal, dict):
        return None
    action = causal.get("action")
    consequence = causal.get("sensed_consequence")
    if not isinstance(action, dict) or not isinstance(consequence, dict):
        return None
    # A body action must return an exact changed body-receptor consequence.
    # Vestibular return is additionally present only when that action rotates
    # the body; requiring rotation would reject lawful limb, face, or speech
    # actions whose proprioceptive/tactile/internal consequences did return.
    if int(consequence.get("externally_perturbed_body_receptor_count", 0)) <= 0:
        return None
    attention = _sparse_attention_route_facts(evidence)
    if attention is None:
        return None
    alternatives = tuple(evidence.get("physical_prediction_alternatives", ()))
    if not alternatives:
        return None
    transfers = tuple(causal.get("directed_physical_transfers", ()))
    path_lineages = {
        lineage
        for transfer in transfers
        for lineage in transfer[:2]
    }
    prediction_lineages = {
        lineage
        for alternative in alternatives
        for transfer in alternative
        for lineage in transfer[:2]
    }
    complete_affective = tuple(
        trajectory
        for trajectory in evidence.get("affective_balance_trajectories", ())
        if trajectory[3] is not None
        and trajectory[4] is not None
        and trajectory[5] is not None
        and trajectory[5][0] > max(trajectory[3][0], trajectory[4][0])
    )
    shared_lineages = tuple(
        sorted(
            path_lineages
            & prediction_lineages
            & {trajectory[0] for trajectory in complete_affective}
        )
    )
    projected = {
        "action": action,
        "attention": attention,
        "complete_affective_trajectory_count": len(complete_affective),
        "directed_physical_transfers": transfers,
        "emitted_neuron_lineages": tuple(
            causal.get("emitted_neuron_lineages", ())
        ),
        "impression_organism_tick": causal.get("impression_organism_tick"),
        "intake": evidence.get("intake"),
        "motor_organism_tick": causal.get("motor_organism_tick"),
        "organism_tick": evidence.get("organism_tick"),
        "physical_prediction_alternatives": alternatives,
        "possible_consequence_junction_observed": True,
        "sensed_consequence": consequence,
        "shared_causal_lineages": shared_lineages,
        "state_sha256": evidence.get("state_sha256"),
        "organism_identity": evidence.get("organism_identity"),
    }
    participant = evidence.get("participant_sensory_causal_use")
    if isinstance(participant, dict):
        participant_action = participant.get("action")
        raw_participant_transfers = participant.get(
            "directed_physical_transfers"
        )
        participant_transfers = (
            tuple(raw_participant_transfers)
            if isinstance(raw_participant_transfers, (list, tuple))
            else ()
        )
        raw_participant_lineages = participant.get(
            "perturbed_receptor_lineages"
        )
        participant_lineages = (
            tuple(raw_participant_lineages)
            if isinstance(raw_participant_lineages, (list, tuple))
            else ()
        )
        participant_receipt = participant.get(
            "participant_action_causal_intent_receipt_sha256"
        )
        participant_motor_tick = participant.get("motor_organism_tick")
        receptor_tick = participant.get("receptor_settlement_organism_tick")
        if (
            participant.get("origin_kind") == "external_participant_sensory"
            and participant_action == action
            and isinstance(participant_motor_tick, int)
            and participant_motor_tick == causal.get("motor_organism_tick")
            and isinstance(receptor_tick, int)
            and receptor_tick < participant_motor_tick
            and isinstance(participant_receipt, str)
            and re.fullmatch(r"[0-9a-f]{64}", participant_receipt) is not None
            and participant_transfers
            and participant_lineages
        ):
            projected["social_experience"] = {
                "directed_physical_transfers": participant_transfers,
                "motor_organism_tick": participant_motor_tick,
                "participant_action_causal_intent_receipt_sha256": (
                    participant_receipt
                ),
                "perturbed_receptor_lineages": participant_lineages,
                "receptor_settlement_organism_tick": receptor_tick,
            }
    return projected


def _social_experience_evidence_from_transition(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    """Project one exact other-body receptor-to-action occurrence.

    Social experience is one physical contributor to A-006.  It need not be
    forced onto the same motor tick as a different novelty occurrence.  The
    stronger same-action join remains published by the intrinsic projection
    whenever it genuinely occurs.
    """

    participant = evidence.get("participant_sensory_causal_use")
    if not isinstance(participant, dict):
        return None
    action = participant.get("action")
    consequence = participant.get("sensed_consequence")
    raw_transfers = participant.get("directed_physical_transfers")
    transfers = tuple(raw_transfers) if isinstance(raw_transfers, (list, tuple)) else ()
    raw_lineages = participant.get("perturbed_receptor_lineages")
    lineages = tuple(raw_lineages) if isinstance(raw_lineages, (list, tuple)) else ()
    receipt = participant.get("participant_action_causal_intent_receipt_sha256")
    receptor_tick = participant.get("receptor_settlement_organism_tick")
    motor_tick = participant.get("motor_organism_tick")
    if (
        participant.get("origin_kind") != "external_participant_sensory"
        or not isinstance(action, dict)
        or not isinstance(consequence, dict)
        or int(consequence.get("externally_perturbed_body_receptor_count", 0)) <= 0
        or not isinstance(receipt, str)
        or re.fullmatch(r"[0-9a-f]{64}", receipt) is None
        or not isinstance(receptor_tick, int)
        or not isinstance(motor_tick, int)
        or receptor_tick >= motor_tick
        or not transfers
        or not lineages
    ):
        return None
    return {
        "action": action,
        "directed_physical_transfers": transfers,
        "motor_organism_tick": motor_tick,
        "organism_identity": evidence.get("organism_identity"),
        "participant_action_causal_intent_receipt_sha256": receipt,
        "perturbed_receptor_lineages": lineages,
        "receptor_settlement_organism_tick": receptor_tick,
        "sensed_consequence": consequence,
        "state_sha256": evidence.get("state_sha256"),
    }


def _intrinsic_curiosity_record() -> dict[str, object]:
    evidence = _last_intrinsic_curiosity_evidence
    independent_social = _last_social_experience_evidence
    same_resident_social = bool(
        isinstance(evidence, dict)
        and isinstance(independent_social, dict)
        and evidence.get("organism_identity") is not None
        and evidence.get("organism_identity")
        == independent_social.get("organism_identity")
    )
    social_experience_claimed = bool(
        isinstance(evidence, dict)
        and (
            isinstance(evidence.get("social_experience"), dict)
            or same_resident_social
        )
    )
    authority = {
        "curiosity_score_authority": False,
        "named_need_authority": False,
        "python_decision_authority": False,
        "reward_authority": False,
        "scripted_action_authority": False,
        "social_experience_claimed": social_experience_claimed,
    }
    if evidence is None:
        return _section(
            False,
            "physical_curiosity_mounted_awaiting_causal_witness",
            "this process has not yet observed a new neuronal impression "
            "change the sparse reachable frontier, cross a physical "
            "alternative/affective junction, cause body action, and return "
            "through body senses",
            **authority,
        )
    description = (
        "new retained sensory structure propagated through exact sparse "
        "carrier transfers while reached and foregone routes changed, crossed "
        "a divergent possible-consequence junction, caused body action, and "
        "returned through body senses"
    )
    if evidence.get("shared_causal_lineages"):
        description += (
            "; the novelty path, possible-consequence junction, and complete "
            "body/affective trajectory shared exact neuronal lineages"
        )
    if social_experience_claimed:
        description += (
            "; an authenticated other body's receptor path independently "
            "reached a body action in this same continuously resident organism"
        )
    description += (
        "; this is bounded physical curiosity evidence, not a need, reward, "
        "or score"
    )
    social_evidence = evidence.get("social_experience")
    if social_evidence is None and same_resident_social:
        social_evidence = independent_social
    record_evidence = dict(evidence)
    record_evidence["social_experience"] = social_evidence
    return _section(
        True,
        "new_impression_changed_reachable_activity_and_caused_sensed_action",
        description,
        evidence_scope="latest_tested_intrinsic_causal_event",
        **record_evidence,
        **authority,
    )


def _cognitive_capital_record(record: dict[str, Any]) -> dict[str, object]:
    """Project exact evidence without becoming cognition or a scalar score."""

    credits: dict[tuple[str, str], dict[str, object]] = {}

    def credit(
        capability: str,
        dimensions: tuple[str, ...],
        evidence_kind: str,
        evidence_path: str,
        evidence: object,
    ) -> None:
        if capability not in COGNITIVE_CAPITAL_CAPABILITIES:
            raise RuntimeError(f"unknown cognitive-capital capability: {capability}")
        receipt = _receipt(evidence)
        for dimension in dimensions:
            if dimension not in COGNITIVE_CAPITAL_DIMENSIONS:
                raise RuntimeError(
                    f"unknown cognitive-capital dimension: {dimension}"
                )
            key = (capability, dimension)
            cell = credits.setdefault(
                key,
                {
                    "capability": capability,
                    "dimension": dimension,
                    "evidence": [],
                },
            )
            reference = {
                "kind": evidence_kind,
                "path": evidence_path,
                "receipt_sha256": receipt,
            }
            if reference not in cell["evidence"]:
                cell["evidence"].append(reference)

    sensory = record["sensory"]
    sensory_capabilities = {
        "visual": "Vision",
        "auditory": "Hearing",
        "touch": "Touch",
        "temperature": "Temperature",
        "smell": "Smell",
        "taste": "Taste",
        "proprioception": "Proprioception and body position",
        "vestibular": "Vestibular balance",
        "interoception": "Interoception and visceral state",
    }
    for modality, capability in sensory_capabilities.items():
        evidence = sensory[modality]
        if evidence.get("available") is True:
            credit(
                capability,
                ("availability",),
                "mounted_physical_sensory_path",
                f"sensory.{modality}",
                evidence,
            )

    transition = _last_transition_evidence or {}
    ingress = transition.get("receptor_ingress")
    sense_counts = ingress.get("sense_counts", {}) if isinstance(ingress, dict) else {}
    for sense, capability in (
        ("sight", "Vision"),
        ("sound", "Hearing"),
        ("touch", "Touch"),
        ("smell", "Smell"),
        ("taste", "Taste"),
    ):
        if int(sense_counts.get(sense, 0)) > 0:
            credit(
                capability,
                ("participation",),
                "receptor_ingress",
                f"last_transition.receptor_ingress.sense_counts.{sense}",
                {
                    "sense": sense,
                    "count": sense_counts[sense],
                    "tick": transition.get("organism_tick"),
                },
            )
    if int(transition.get("vestibular_tick_count", 0)) > 0:
        credit(
            "Vestibular balance",
            ("participation",),
            "vestibular_sensed_consequence",
            "last_transition.vestibular_tick_count",
            {
                "count": transition["vestibular_tick_count"],
                "tick": transition.get("organism_tick"),
            },
        )
    totals = transition.get("totals", {})
    if int(totals.get("metabolically_perturbed_body_receptor_count", 0)) > 0:
        credit(
            "Interoception and visceral state",
            ("participation",),
            "local_body_receptor_perturbation",
            "last_transition.totals.metabolically_perturbed_body_receptor_count",
            {
                "count": totals["metabolically_perturbed_body_receptor_count"],
                "tick": transition.get("organism_tick"),
            },
        )
    participating_senses = tuple(
        sorted(sense for sense, count in sense_counts.items() if int(count) > 0)
    )
    if len(participating_senses) > 1:
        credit(
            "Multisensory integration",
            ("availability", "participation"),
            "same_transition_multisensory_ingress",
            "last_transition.receptor_ingress.sense_counts",
            {
                "participating_senses": participating_senses,
                "tick": transition.get("organism_tick"),
            },
        )

    if record["fractals"].get("available") is True:
        credit(
            "Learning and developmental growth",
            ("availability", "retention"),
            "retained_neuronal_fractal_state",
            "fractals",
            record["fractals"],
        )
    if int(record["formations"].get("mosaic_count", 0)) > 0:
        for capability in ("Episodic memory", "Learning and developmental growth"):
            credit(
                capability,
                ("availability", "retention"),
                "retained_physical_formation_state",
                "formations",
                record["formations"],
            )
            if record["persistence"].get("available") is True:
                credit(
                    capability,
                    ("durability",),
                    "retained_formation_state_cold_restored",
                    "formations+persistence",
                    {
                        "formations": record["formations"],
                        "persistence": record["persistence"],
                    },
                )

    recall = record["recall"]
    if recall.get("available") is True:
        credit(
            "Recognition and familiarity",
            ("availability", "participation", "recognition"),
            recall["status"],
            "recall",
            recall,
        )
        for capability in ("Episodic memory", "Recall"):
            credit(
                capability,
                ("availability", "participation", "recall"),
                recall["status"],
                "recall",
                recall,
            )

    if record["body"].get("available") is True:
        credit(
            "Self and body continuity",
            ("availability",),
            record["body"]["status"],
            "identity+body+persistence",
            {
                "identity": record["identity"],
                "body": record["body"],
                "persistence": record["persistence"],
            },
        )

    for capability, path in (
        ("Attention and orienting", "attention"),
        ("Immediate causal state", "working_causal_state"),
        ("Prediction", "prediction"),
    ):
        evidence = record[path]
        if evidence.get("available") is True:
            dimensions = (
                ("availability", "participation", "causal_use", "integration_depth")
                if path == "prediction"
                else ("availability", "participation", "causal_use")
                if path == "working_causal_state"
                else ("availability", "participation")
            )
            credit(capability, dimensions, evidence["status"], path, evidence)

    affect = record["affective_balance"]
    if affect.get("available") is True:
        for capability in ("Emotion and affect", "Emotional balance and regulation"):
            credit(
                capability,
                ("availability", "participation", "integration_depth"),
                affect["status"],
                "affective_balance",
                affect,
            )

    articulation = record["articulation"]
    if articulation.get("available") is True:
        credit(
            "Speech and articulation",
            ("availability", "participation", "causal_use", "integration_depth"),
            articulation["status"],
            "articulation",
            articulation,
        )
        credit(
            "Motor and actuator control",
            ("participation", "causal_use"),
            articulation["status"],
            "articulation",
            articulation,
        )
        credit(
            "Hearing",
            ("participation",),
            "articulatory_self_hearing",
            "articulation",
            articulation,
        )

    causal = record["body"].get("prior_causal_cross_context_use")
    if isinstance(causal, dict) and causal.get("available") is True:
        causal_capabilities = (
            "Recognition and familiarity",
            "Episodic memory",
            "Procedural and physical memory",
            "Recall",
            "Self and body continuity",
            "Motor and actuator control",
            "Autonomous cognition and action",
            "Learning and developmental growth",
        )
        for capability in causal_capabilities:
            credit(
                capability,
                (
                    "availability",
                    "participation",
                    "causal_use",
                    "transfer",
                    "integration_depth",
                ),
                causal["status"],
                "body.prior_causal_cross_context_use",
                causal,
            )
        for capability in ("Recognition and familiarity",):
            credit(
                capability,
                ("recognition",),
                causal["status"],
                "body.prior_causal_cross_context_use",
                causal,
            )
        for capability in (
            "Episodic memory",
            "Procedural and physical memory",
            "Recall",
        ):
            credit(
                capability,
                ("recall",),
                causal["status"],
                "body.prior_causal_cross_context_use",
                causal,
            )
        if str(causal.get("intake", "")).startswith("continuous-environment:"):
            for capability in (
                "Procedural and physical memory",
                "Self and body continuity",
                "Motor and actuator control",
                "Autonomous cognition and action",
            ):
                credit(
                    capability,
                    ("autonomous_use",),
                    causal["status"],
                    "body.prior_causal_cross_context_use",
                    causal,
                )
    curiosity = record["intrinsic_curiosity"]
    if curiosity.get("available") is True:
        credit(
            "Motivation, needs, and curiosity",
            (
                "availability",
                "participation",
                "causal_use",
                "autonomous_use",
                "integration_depth",
            ),
            curiosity["status"],
            "intrinsic_curiosity",
            curiosity,
        )
    choice = record.get("choice")
    if isinstance(choice, dict) and choice.get("available") is True:
        credit(
            "Deliberation and choice",
            (
                "availability",
                "participation",
                "causal_use",
                "autonomous_use",
                "integration_depth",
            ),
            choice["status"],
            "choice",
            choice,
        )
    play = record.get("play")
    if isinstance(play, dict) and play.get("available") is True:
        play_dimensions = (
            "availability",
            "participation",
            "causal_use",
            "autonomous_use",
            "integration_depth",
        )
        fun = play.get("fun")
        if (
            play.get("changed_world_context") is True
            and isinstance(fun, dict)
            and fun.get("available") is True
        ):
            play_dimensions += ("transfer",)
        credit(
            "Play and exploration",
            play_dimensions,
            play["status"],
            "play",
            play,
        )
        social_joy = play.get("social_joy")
        if isinstance(social_joy, dict) and social_joy.get("available") is True:
            credit(
                "Social cognition and other-perspective",
                (
                    "availability",
                    "participation",
                    "causal_use",
                    "autonomous_use",
                    "integration_depth",
                    "transfer",
                ),
                social_joy["status"],
                "play.social_joy",
                social_joy,
            )
    ordered = [credits[key] for key in sorted(credits)]
    for cell in ordered:
        cell["evidence"].sort(
            key=lambda item: (item["kind"], item["path"], item["receipt_sha256"])
        )
    return _section(
        bool(ordered),
        "sparse_exact_evidence_observed" if ordered else "no_capital_evidence_observed",
        "each credit references one exact current or committed physical witness; "
        "absent cells are unproved, and no aggregate score is produced",
        schema=COGNITIVE_CAPITAL_SCHEMA,
        capabilities=list(COGNITIVE_CAPITAL_CAPABILITIES),
        dimensions=list(COGNITIVE_CAPITAL_DIMENSIONS),
        credits=ordered,
        scalar_score_authority=False,
        cognition_authority=False,
    )


def _build_public_observation_from_snapshot(
    native: dict[str, Any],
    retained_impressions: int | None,
    build_identity: dict[str, str],
) -> dict[str, Any]:
    last = _last_transition_record()
    last_fractal_count = int(last.get("emitted_neuron_fractal_count", 0))
    record: dict[str, Any] = {
        "schema": PUBLIC_OBSERVATION_SCHEMA,
        "generation": native["organism_tick"],
        "generation_state": {
            "fabric_generation": native["fabric_generation"],
            "mounted_generation": native["mounted_generation"],
            "organism_tick": native["organism_tick"],
            "state_sha256": native["state_sha256"],
        },
        "identity": _section(
            True,
            "restored_native_identity",
            "identity is read from raw CURRENT native state",
            build=build_identity,
            continuity="one raw native CURRENT lineage",
            value=native["identity"],
        ),
        "organism": _section(
            True,
            "native_current_with_admitted_sensory_transitions",
            "native state is restored and admitted sensory transitions are "
            "mounted; current thought, action, consequence, and articulation "
            "evidence is reported only by its dedicated sections below",
            physical_transition_claimed=native["physical_transition_claimed"],
            state_bytes=native["state_bytes"],
            tick=native["organism_tick"],
        ),
        "capabilities": {
            # STEP FACT vs STATE, applied to a control surface (2026-08-07).
            #
            # This section answers "what CAN reach her right now" — it is the
            # thing an interaction control may gate on.  It used to answer
            # "what HAS reached her in this process", which deadlocked the
            # camera permanently: the page disabled the button until frames
            # had committed, and frames could only commit through the button.
            # A restart re-locked it, which is why first light worked once on
            # 2026-08-06 and never again.
            #
            # `available` is still truth-coupled — it is false wherever the
            # pathway is absent or physically inert.  Live sight is neither:
            # severing it is measured to change her physics (transitioned
            # 108->27, fractals 0->27, body 1,239,843->243,503 bytes), so
            # "this intake will physically change her" is a fact about her
            # body, not about the transport.
            #
            # What HAS happened stays reported separately and never softens:
            # `committed_in_process` here, and `sensory.visual.live_camera`,
            # which remains strictly evidence-coupled for the ledger.
            "camera": {
                "available": True,
                "committed_in_process": _live_sight_evidence is not None,
                "endpoint": LIVE_SIGHT_INTAKE_ENDPOINT,
                "reason": (
                    "real live camera frames have committed end-to-end as "
                    "admitted 27-receptor luminance episodes in this "
                    "process; provenance is the client's declared "
                    "live-camera capture contract"
                    if _live_sight_evidence is not None
                    else "the live-sight intake is mounted and will admit "
                    "real camera frames as 27-receptor luminance episodes "
                    "that physically transition her neurons; no batch has "
                    "committed in THIS process yet, which is why "
                    "committed_in_process is false — open the eye and it "
                    "becomes true from the transition itself"
                ),
                "status": (
                    "live_frames_committed"
                    if _live_sight_evidence is not None
                    else "intake_mounted_awaiting_frames"
                ),
            },
            # 2026-08-07 truth repair: this used to be hardcoded
            # not-mounted even while the PCM routes were open and
            # admitting real sound — a surface that lied in both
            # directions.  It now derives from the SAME gate the routes
            # themselves consult.
            # Same split as the camera.  `available` is whether the ears
            # physically transduce — MEASURED on her real restored body
            # 2026-08-07: severing the sound from one identical card lesson
            # drops physically transitioned neurons 529->305 and new
            # impressions 41->9.  Sound is no longer transport wearing a
            # costume, so the capability may honestly say so.
            #
            # A real camera is not a biological prerequisite for hearing.
            # Pressure without a camera enters beside the organism's actual
            # current world/body sensorium; when the camera is open, the
            # stricter co-captured audiovisual endpoint remains available.
            "microphone": {
                "available": COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED,
                "committed_in_process": _live_hearing_evidence is not None,
                "endpoint": (
                    GUIDED_WORLD_VOICE_ENDPOINT
                    if COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED
                    else None
                ),
                "audiovisual_endpoint": (
                    LIVE_AUDIOVISUAL_INTAKE_ENDPOINT
                    if COCHLEAR_EARS_AUTHORIZED
                    else None
                ),
                "requires_concurrent_camera": False,
                "reason": (
                    (
                        "the cochlear roster physically transduces pressure "
                        "(measured by severing: 529->305 transitioned "
                        "neurons, 41->9 new impressions on one identical "
                        "lesson); microphone pressure enters with the actual "
                        "current world/body sensorium, while an open camera "
                        "uses the co-captured audiovisual path"
                        + (
                            "; live pressure has committed in this process "
                            f"({_live_hearing_evidence['intake']})"
                            if _live_hearing_evidence is not None
                            else ""
                        )
                    )
                    if COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED
                    else "microphone pressure requires both the mounted "
                    "cochlear roster and persistent current world"
                    if COCHLEAR_EARS_AUTHORIZED
                    else "standalone hearing is not mounted: the cochlear ear "
                    "anatomy is not authorized in this process, so pressure "
                    "amplitude has no physical effect and admitting live "
                    "sound would fabricate a sensation; tutor audio inside "
                    "card lessons remains"
                ),
                "status": (
                    "not_mounted"
                    if not COCHLEAR_EARS_AUTHORIZED or not WORLD_AUTHORIZED
                    else "mounted_current_world_with_optional_audiovisual"
                ),
            },
            "curriculum": {
                **_mounted_capability(
                    CURRICULUM_INVITE_ENDPOINT,
                    "the participant body first approaches in Guala's "
                    "persistent world; only her exact receptor-to-motor "
                    "causal path opens one bounded card presentation",
                ),
                "invitation": _curriculum_invitation_record(),
                "presentation_endpoint": "/api/v1/curriculum/teach-card",
            },
            # A card taught in the voice of whoever is present.  Unlike the
            # standalone microphone this asks NOTHING of the camera: the
            # card's own light and its tactile footprint are in the SAME
            # episode as the voice, so the experience is whole-sensorium by
            # construction rather than by a precondition.
            "spoken_lesson": {
                "available": COCHLEAR_EARS_AUTHORIZED,
                "committed_in_process": (
                    _live_hearing_evidence is not None
                    and str(_live_hearing_evidence.get("intake", "")).startswith(
                        "spoken-card:"
                    )
                ),
                "endpoint": (
                    SPOKEN_LESSON_ENDPOINT if COCHLEAR_EARS_AUTHORIZED else None
                ),
                "reason": (
                    "a person's own voice becomes the lesson's voice: the "
                    "card's light, its declared tactile footprint and the "
                    "spoken utterance reach the organism as ONE admitted "
                    "episode on one shared clock, and the cochleae "
                    "physically transduce that pressure"
                    if COCHLEAR_EARS_AUTHORIZED
                    else "a spoken lesson is not mounted: the cochlear ear "
                    "anatomy is not authorized in this process, so a human "
                    "voice would reach her and move nothing"
                ),
                "status": (
                    "mounted" if COCHLEAR_EARS_AUTHORIZED else "not_mounted"
                ),
            },
            "grounded_world_voice": {
                "available": COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED,
                "endpoint": (
                    GUIDED_WORLD_VOICE_ENDPOINT
                    if COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED
                    else None
                ),
                "reason": (
                    "physical tutor pressure coexists with Guala's actual "
                    "current world, body, and every available sensory lane; "
                    "the intake accepts no word, object, or meaning field"
                    if COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED
                    else "grounded world voice requires both the persistent "
                    "world and mounted cochlear ears"
                ),
                "status": (
                    "mounted"
                    if COCHLEAR_EARS_AUTHORIZED and WORLD_AUTHORIZED
                    else "not_mounted"
                ),
            },
            "nutrition": _unmounted(
                "nutrition is not mounted: no truthful material-to-energy "
                "intake law exists; the "
                "retired integer feed endpoint cannot supply body energy",
                endpoint=None,
            ),
            "text_visual": {
                "available": True,
                "endpoint": RENDERED_LIGHT_ENDPOINT,
                "max_bytes": OFFERED_MATERIAL_MAX_BYTES,
                "reason": (
                    "pixels a person renders in their own browser reach the "
                    "same 27 retinal receptor sites an approved card and the "
                    "live camera reach; the typed string is never submitted "
                    "and no meaning enters — to an organism that has not "
                    "learned to read, text is light"
                ),
                "status": "mounted",
            },
            "picture": _offered_material_capability(
                "picture",
                True,
                "the exact offered source is retained once under fixed byte "
                "and count ceilings, then one picture is area-averaged onto "
                "the same 27 "
                "retinal receptor sites the approved cards reach, presented "
                "for its own hop and then genuinely ended",
            ),
            "pdf": _offered_material_capability(
                "pdf",
                True,
                "the exact source is retained once under fixed ceilings; "
                f"then up to {OFFERED_PAGE_MAX_COUNT} pages are rendered to light "
                "and presented in their own order on the retinal roster; a "
                "page is a picture, never words",
            ),
            "book": _offered_material_capability(
                "book",
                True,
                "the exact source is retained once under fixed ceilings; "
                f"then up to {OFFERED_PAGE_MAX_COUNT} pages are rendered to light "
                "and presented in their own order on the retinal roster; a "
                "page is a picture, never words",
            ),
            "audio": _offered_material_capability(
                "audio",
                COCHLEAR_EARS_AUTHORIZED,
                "the exact offered source is retained once under fixed "
                "ceilings, then sound is decoded to pcm_s16le mono 16 kHz "
                "her cochleae are declared for and transduces on the same "
                "band decomposition her tutor's voice does"
                if COCHLEAR_EARS_AUTHORIZED
                else "offered sound is not mounted: without the cochlear ear "
                "anatomy pressure amplitude has no physical effect",
            ),
            "song": _offered_material_capability(
                "song",
                COCHLEAR_EARS_AUTHORIZED,
                "the exact offered source is retained once under fixed "
                "ceilings; a song is then pressure like any other, decoded to the "
                "exact format her cochleae are declared for, with no "
                "transcript, title, or meaning entering cognition"
                if COCHLEAR_EARS_AUTHORIZED
                else "offered song is not mounted: without the cochlear ear "
                "anatomy pressure amplitude has no physical effect",
            ),
            "video": _offered_material_capability(
                "video",
                COCHLEAR_EARS_AUTHORIZED,
                "the exact offered source is retained once under fixed "
                "ceilings, then at most 24 successive quarter-second frames "
                "and their exact mono pressure reach the mounted retinal and "
                "cochlear paths on one shared clock; captions, filenames, "
                "objects, and meanings never enter cognition"
                if COCHLEAR_EARS_AUTHORIZED
                else "offered video is not mounted: its light exists, but "
                "without authorized cochlear anatomy its physical soundtrack "
                "cannot enter the same audiovisual occurrence",
            ),
            "world": {
                "available": WORLD_AUTHORIZED and VESTIBULAR_AUTHORIZED,
                "endpoint": (
                    WORLD_MOVE_ENDPOINT
                    if WORLD_AUTHORIZED and VESTIBULAR_AUTHORIZED
                    else None
                ),
                "observation_endpoint": (
                    WORLD_OBSERVATION_ENDPOINT if WORLD_AUTHORIZED else None
                ),
                "she_chooses_where_to_go": False,
                "reason": (
                    "a deterministic place with its own physics: what she "
                    "sees there reaches the same 27 retinal sites a card "
                    "reaches, and moving her produces the real displacement "
                    "her balance and body-position receptors transduce. A "
                    "person moves her, exactly as a person presents a card — "
                    "she does not yet choose to go anywhere"
                    if WORLD_AUTHORIZED and VESTIBULAR_AUTHORIZED
                    else "a place is not mounted: she has nowhere to be, or "
                    "nothing to feel a move with, and a displacement "
                    "receptor with nothing moving would be a fabrication "
                    f"({WORLD_ENV}, {VESTIBULAR_ENV})"
                ),
                "status": (
                    "mounted_guided_only"
                    if WORLD_AUTHORIZED and VESTIBULAR_AUTHORIZED
                    else "not_mounted"
                ),
            },
            "gutenberg": _shelf_capability("gutenberg"),
            "youtube": _shelf_capability("youtube"),
            "khan_academy": _shelf_capability("khan_academy"),
            "pbs_kids": _shelf_capability("pbs_kids"),
            "spotify": _shelf_capability("spotify"),
        },
        "sensory": _sensory_record(native),
        "neuron_activity": _section(
            True,
            "retained_complete_neuron_state",
            "retained count is decoded native cognitive state; a live "
            "activity projection is not mounted",
            active_count=None,
            historical_reached_dsf_perspective_count=native[
                "reached_dsf_perspective_count"
            ],
            reached_count_by_developmental_layer=native[
                "reached_neuron_count_by_layer"
            ],
            retained_count=native["complete_neuron_count"],
        ),
        "fractals": _section(
            (retained_impressions or 0) > 0 or last_fractal_count > 0,
            (
                # 2026-08-07 truth repair: a failed observation used to
                # read as 0 — an empty body printed over a full one.  A
                # failure now SAYS it failed.
                "retained_impression_observation_failed"
                if retained_impressions is None
                else "retained_impressions_held"
                if retained_impressions > 0
                else "no_retained_impression"
            ),
            "the count is how many of her neurons are HOLDING a retained "
            "impression right now — her state, decoded from her retained "
            "formations. A retained formation's members are exactly the "
            "neurons that hold one, so a body with memories can never "
            "honestly report zero. `formed_in_last_experience` is the "
            "separate step fact: how many NEW impressions the most recent "
            "experience created, which is legitimately zero for a quiet "
            "moment or for something she has already learned. "
            "Per-neuron fractal bodies remain in the resident state and are "
            "not copied into this bounded public observer.",
            count=retained_impressions,
            formed_in_last_experience=last_fractal_count,
        ),
        # `mosaic_count` and `mosaic_of_mosaics_count` are decoded from her
        # retained formations — physical facts in her body.  The three higher
        # formations are NOT reported as zero, because zero would read as a
        # measurement.  Nothing measures them: the classifier that once
        # produced tapestry counts read the retired episode archive, and it
        # cannot be rebuilt from a deduplicated set of retained formations
        # without redefining its own law.  It also measured zero on this body
        # every time it ran.
        "formations": _section(
            True,
            "physical_mosaic_state_only",
            "mosaic count and mosaic-of-mosaics count are decoded native "
            "cognitive state. Tapestry, tapestry-of-tapestries and weave are "
            "reported as unavailable, not as zero: no mechanism measures "
            "them. The classifier that used to count them read a durable "
            "episode archive that is now retired, and her retained "
            "formations carry no per-neuron episode ordering to rebuild it "
            "from.",
            mosaic_count=native["cognitive_mosaic_count"],
            mosaic_of_mosaics_count=native["mosaic_of_mosaics_count"],
            tapestry_count=None,
            tapestry_of_tapestries_count=None,
            weave_count=None,
            higher_formation_measurement="absent_no_mechanism",
        ),
        # Truth-coupled to the decoded native observation.  The endogenous
        # count is kept distinct from any externally supplied partial cue.
        "recall": _section(
            native["endogenous_partial_cue_reassembly_count"] > 0,
            (
                "endogenous_physical_reassembly_observed"
                if native["endogenous_partial_cue_reassembly_count"] > 0
                else "no_endogenous_reassembly_in_last_committed_transition"
            ),
            "the endogenous count is native formation reassembly caused by "
            "internal physical charge motion after formation-local relaxation; "
            "the total also includes any externally supplied partial cue",
            partial_cue_reassembly_count=native["partial_cue_reassembly_count"],
            endogenous_partial_cue_reassembly_count=native[
                "endogenous_partial_cue_reassembly_count"
            ],
            retained_formation_recurrence_evidence=native[
                "retained_formation_recurrence_evidence"
            ],
        ),
        # Truth-coupled to the decoded native body: an exhausted ledger or an
        # empty reservoir reports itself here.  A body that cannot pay for its
        # own recovery is NOT reported as available.
        "energy": _section(
            native["available_energy_capacity_zeptojoules"][0] > 0
            and not native["energy_exhausted"],
            (
                "no_mounted_energy_system"
                if native["available_energy_capacity_zeptojoules"][0] == 0
                else "energy_exhausted"
                if native["energy_exhausted"]
                else "exact_body_energy_available"
            ),
            "exact rational energy coordinates remain in the resident native "
            "state identified by state_sha256; this bounded observer reports "
            "only mounted availability and exhaustion",
            exact_coordinates_transported=False,
            exact_coordinates_resident=True,
            exhausted=native["energy_exhausted"],
            state_sha256=native["state_sha256"],
        ),
        "cognitive_capital": None,
        "attention": _attention_record(),
        "intrinsic_curiosity": _intrinsic_curiosity_record(),
        "choice": _physical_choice_record(),
        "working_causal_state": _working_causal_state_record(),
        "prediction": _physical_prediction_record(),
        "affective_balance": _affective_balance_record(),
        "localized_fluid_chemistry": _localized_fluid_chemistry_record(),
        "body": _body_record(native),
        "autonomy": _autonomy_record(),
        "play": _sensorimotor_play_record(),
        "articulation": (articulation_record := _articulation_record()),
        "expression": articulation_record,
        "custody": {
            "durable_body_state_sha256": (
                None if _restored is None else _restored.pointer.state_sha256
            ),
            "durable_organism_tick": (
                None if _restored is None else _restored.pointer.organism_tick
            ),
            "resident_organism_tick": native["organism_tick"],
            "pending_unsealed_intervals": _pending_unsealed_intervals,
            "unsealed_interval_ceiling": _unsealed_interval_ceiling(),
            "post_current_cleanup_pending": (
                _pending_custody_cleanup is not None
            ),
            "pre_current_candidate_pending": (
                _pending_custody_candidate is not None
            ),
            "pre_current_candidate_state_bytes": (
                None
                if _pending_custody_candidate is None
                else _pending_custody_candidate["checkpoint"].state_bytes
            ),
            "pre_current_retry_stage_bytes": (
                None
                if _pending_custody_candidate is None
                else _pending_custody_candidate["retry_stage"].stored_bytes
            ),
            "last_seal": _last_custodian_evidence,
            "last_failure": _last_custodian_error,
        },
        "curriculum": _curriculum_media_record(),
        "last_transition": last,
        "last_card_lesson_receipt": _card_lesson_receipt_record(),
        "last_song_lesson_receipt": _song_lesson_receipt_record(),
        "experience_stage_ledger": _experience_stage_ledger_record(),
        "full_dsf": _section(
            False,
            "not_observed",
            "no canonical reached UF v1.4 joint occurrence is projected",
            decision_authority=False,
            fields=[
                "D_k",
                "M_k",
                "R_rev_k",
                "U_star_k",
                "C_k",
                "P_k",
                "B_k",
            ],
            observation_loss="the entire current field occurrence is unavailable",
            projection="none",
        ),
        "persistence": _section(
            True,
            "raw_current_restored",
            "one raw native CURRENT generation was restored without fallback; "
            "every committed transition publishes its successor before it is "
            "reported",
            boundary={
                "encoding": "raw_glorun01",
                "ordinary_restore": "CURRENT_only",
                "predecessor_fallback": False,
                "schema": PERSISTENCE_SCHEMA,
            },
            current_ref=native["state_sha256"],
            restart_continuity="successor publication precedes every report",
        ),
        "resources": _section(
            True,
            "partial_capacity_only",
            "finite admission and state bytes are known; live rates are not mounted",
            cpu=None,
            python_calls=None,
            process_count=None,
            ram_bytes=None,
            state_bytes=native["state_bytes"],
            storage_bytes=None,
            compute_boundary={"available": False, "reason": "live rates are not mounted"},
            memory_boundary=native["resource_admission"],
            storage_boundary={"available": False, "reason": "storage rate is not mounted"},
            python_cognition_callback_count=native["python_callback_count"],
        ),
        "observation_contract": {
            "cached_per_committed_generation": True,
            "cognition_authority": False,
            "declared_loss": (
                "only committed native readiness facts and explicit unavailability "
                "are projected; no neuronal field body is present"
            ),
            "read_advances_organism": False,
        },
    }
    record["cognitive_capital"] = _cognitive_capital_record(record)
    record["snapshot_receipt_sha256"] = _receipt(record)
    return record


def _build_public_observation() -> dict[str, Any]:
    return _build_public_observation_from_snapshot(
        _native_record(),
        None,
        _build_identity(),
    )


# Change gate for the display projection. The full observation rebuild +
# canonical JSON + sha256 ran every 250 ms beat even when nothing observable
# changed — the audit's largest steady waste. The fingerprint covers the
# committed state sha, tick, the unsealed counter, and the identity of every
# rebound "_last_*" evidence slot (module convention: surfaced transport
# evidence is rebound, never mutated in place, on quiet beats). Because an
# id() can in principle be reused after collection, a rebuild is FORCED at
# least every 8 skipped beats, bounding any conceivable staleness to ~2
# seconds — far inside the page's own refresh cadence. The readiness proof
# is still rebuilt on every call; only the optional display projection is
# gated.
_observation_refresh_fingerprint: tuple | None = None
_observation_refresh_skips: int = 0
_OBSERVATION_FORCED_REBUILD_SKIPS = 8
# Display-projection failure witnesses (S2/S3 repair): a failed display
# build no longer hides behind a healthy-looking stale page, and a failed
# readiness build no longer erases the committed surfaces of a healthy
# organism.
_observation_display_failures: int = 0
_last_observation_display_error: str | None = None


def _refresh_public_observation_cache(*, quiet_beat: bool = False) -> None:
    """Rebuild the public observation. Only the 4 Hz unattended beat may
    pass quiet_beat=True to use the change gate; every explicit refresh —
    an intake, a world action, a custodian seal, a test — rebuilds
    unconditionally, so a request for fresh truth can never be answered
    with a fingerprint's guess."""

    global _public_observation_body, _public_observation_etag, _runtime_proof_body
    global _observation_refresh_fingerprint, _observation_refresh_skips
    global _observation_display_failures, _last_observation_display_error

    try:
        native = _native_record()
        # A status refresh must not enumerate every retained formation merely
        # to derive one display number. The exact resident counters and latest
        # bounded transition witness remain available without that scan.
        retained_impressions = None
        # Build identity is immutable for the life of one ECS process. Resolve
        # it once during startup; an optional ECS metadata network read must
        # never make a mounted resident organism or its readiness proof vanish
        # after a committed transition.
        build_identity = (
            dict(_runtime_build_identity)
            if _runtime_build_identity is not None
            else _build_identity()
        )
        runtime_proof_body = _canonical(
            _readiness_from_snapshot(
                native,
                retained_impressions,
                build_identity,
            )
        )
    except BaseException as error:
        # S3 repair: the beat that led here already committed and published.
        # A readiness-build failure must not erase the committed surfaces of
        # a healthy organism — keep the last proven bodies, name the failure,
        # and still raise so the caller sees it.
        _observation_display_failures += 1
        _last_observation_display_error = (
            f"readiness: {type(error).__name__}: {error}"[:512]
        )
        raise
    # Native readiness is the committed organism's compact status. The larger
    # optional display projection cannot make that organism unavailable or
    # turn an already-committed transition into a reported failure.
    _runtime_proof_body = runtime_proof_body
    fingerprint = (
        native.get("state_sha256"),
        native.get("organism_tick"),
        _pending_unsealed_intervals,
        tuple(
            sorted(
                (name, id(value))
                for name, value in globals().items()
                if name.startswith("_last_")
            )
        ),
        id(_curriculum_invitation),
    )
    if (
        quiet_beat
        and _public_observation_body is not None
        and fingerprint == _observation_refresh_fingerprint
        and _observation_refresh_skips < _OBSERVATION_FORCED_REBUILD_SKIPS
    ):
        _observation_refresh_skips += 1
        return
    _observation_refresh_fingerprint = fingerprint
    _observation_refresh_skips = 0
    try:
        body = _canonical(
            _build_public_observation_from_snapshot(
                native,
                retained_impressions,
                build_identity,
            )
        )
    except BaseException as error:
        print(
            "ERROR: native public observation refresh failed: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
            flush=True,
        )
        # Keep the last valid committed display snapshot. This optional
        # projection has no authority to make the organism—or observation of
        # its last proven state—unavailable. S2 repair: the staleness is now
        # COUNTED and NAMED on the readiness surface instead of hiding
        # behind an unchanged etag.
        _observation_display_failures += 1
        _last_observation_display_error = (
            f"display: {type(error).__name__}: {error}"[:512]
        )
        return
    _public_observation_body = body
    _public_observation_etag = f'"{hashlib.sha256(body).hexdigest()}"'
    _observation_display_failures = 0
    _last_observation_display_error = None


def _readiness_from_snapshot(
    native: dict[str, Any],
    retained_impressions: int | None,
    build_identity: dict[str, str],
) -> dict[str, Any]:
    cognition_present = bool(
        native["cognitive_ordinal"]
        or native["cognitive_trace_count"]
        or native["cognitive_mosaic_count"]
    )
    readiness_native = {
        key: native[key]
        for key in (
            "cognitive_mosaic_count",
            "cognitive_ordinal",
            "cognitive_trace_count",
            "complete_neuron_count",
            "developmental_resting_neuron_count",
            "energy_exhausted",
            "fabric_bytes",
            "fabric_generation",
            "fabric_sha256",
            "formation_activation_count",
            "identity",
            "joint_field_count",
            "mounted_generation",
            "organism_tick",
            "partial_cue_reassembly_count",
            "endogenous_partial_cue_reassembly_count",
            "physical_transition_claimed",
            "python_callback_count",
            "reached_dsf_perspective_count",
            "resource_admission",
            "state_bytes",
            "state_sha256",
        )
    }
    return {
        "app_schema": APP_SCHEMA,
        "organism_tick": native["organism_tick"],
        "identity": native["identity"],
        "native_resident": {
            "available": True,
            **readiness_native,
            "complete_neuron_available": native["complete_neuron_count"] > 0,
            # 2026-08-07 truth repair: this was a last-transition step
            # fact (false for a body full of memories after any quiet
            # interval — the exact defect b2ac863b fixed elsewhere).  It
            # now reports BODY state: neurons holding retained impressions.
            "genuine_neuronal_fractal_available": bool(
                (retained_impressions or 0) > 0
            ),
            "cognition_available": cognition_present,
            "energy_available": not native["energy_exhausted"],
            "persistence": {
                "encoding": "raw_glorun01",
                "ordinary_restore": "CURRENT_only",
                "predecessor_fallback": False,
            },
            "persistence_schema": PERSISTENCE_SCHEMA,
        },
        "native_state": True,
        "ready": True,
        "ready_scope": "http_native_current_and_admitted_sensory_transitions",
        # Truthful display health: the optional observation projection can
        # fail while the organism stays healthy. A stale public page used to
        # be indistinguishable from a fresh one; this names it, on the one
        # surface that is rebuilt on every refresh.
        "display_projection": {
            "stale": _observation_display_failures > 0,
            "consecutive_failures": _observation_display_failures,
            "last_error": _last_observation_display_error,
        },
        **build_identity,
    }


def _unavailable(name: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": f"{name} is not mounted on the native resident boundary",
            "ok": False,
            "schema": "guala.external_transport_unavailable.v1",
        },
    )


def _refusal(status_code: int, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "accepted": False,
            "ok": False,
            "reason": reason,
            "schema": "guala.native_admitted_intake_refusal.v1",
        },
    )


class _LocalDirectoryObjectStore:
    """Immutable content-keyed mirror in one local directory.

    Used when no remote object store is configured; every key retains exactly
    the published bytes and existing keys are only ever verified, never
    replaced.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def _path(self, key: str) -> Path:
        relative = Path(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise NativeOrganismBinaryStoreError(
                "native object mirror key escaped its root"
            )
        return self._root / relative

    def put_if_absent(
        self,
        key: str,
        chunks: Iterable[bytes],
        *,
        byte_count: int,
        sha256: str,
    ) -> bool:
        body = b"".join(chunks)
        if len(body) != byte_count or hashlib.sha256(body).hexdigest() != sha256:
            raise NativeOrganismBinaryStoreError(
                "native object mirror upload body changed"
            )
        path = self._path(key)
        if path.exists():
            if path.read_bytes() != body:
                raise NativeOrganismBinaryStoreError(
                    "native object mirror key collision"
                )
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        stage = path.parent / f".stage-{uuid.uuid4()}"
        stage.write_bytes(body)
        os.replace(stage, path)
        return True

    def iter_bytes(self, key: str) -> Iterable[bytes]:
        body = self._path(key).read_bytes()
        for offset in range(0, len(body), 1024 * 1024):
            yield body[offset : offset + 1024 * 1024]

    def delete_if_exact(self, key: str, *, byte_count: int, sha256: str) -> None:
        # Retiring an object that is ALREADY absent is the desired end state,
        # not a failure: there is nothing to delete and nothing to protect.
        # Hard-failing here made every restored body unable to continue —
        # a restored mirror does not carry the predecessor its pointer retired,
        # so the first commit after a restore raised FileNotFoundError and
        # poisoned the runtime.  Measured 2026-08-06 on her own backups: the
        # body restored and reported correctly, then could never learn again.
        # A backup that cannot continue is not a backup.
        path = self._path(key)
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return
        if len(body) != byte_count or hashlib.sha256(body).hexdigest() != sha256:
            raise NativeOrganismBinaryStoreError(
                "native object mirror retirement changed"
            )
        try:
            path.unlink()
        except FileNotFoundError:
            return


class _S3ObjectStore:
    def __init__(self, *, bucket: str, client: Any) -> None:
        self.bucket = bucket
        self.client = client

    def put_if_absent(
        self,
        key: str,
        chunks: Iterable[bytes],
        *,
        byte_count: int,
        sha256: str,
    ) -> bool:
        from botocore.exceptions import ClientError

        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
                raise
        else:
            metadata = existing.get("Metadata", {})
            if (
                existing.get("ContentLength") != byte_count
                or metadata.get("sha256") != sha256
            ):
                raise NativeOrganismBinaryStoreError(
                    "native remote object collision"
                )
            return False
        body = b"".join(chunks)
        if len(body) != byte_count or hashlib.sha256(body).hexdigest() != sha256:
            raise NativeOrganismBinaryStoreError(
                "native remote upload body changed"
            )
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            Metadata={"sha256": sha256},
        )
        return True

    def iter_bytes(self, key: str) -> Iterable[bytes]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        yield from response["Body"].iter_chunks(chunk_size=1024 * 1024)

    def delete_if_exact(self, key: str, *, byte_count: int, sha256: str) -> None:
        # Same law as the local mirror: an already-absent predecessor is
        # retired, not an error.
        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as error:  # noqa: BLE001 - botocore error shape varies
            response = getattr(error, "response", None)
            status = None
            if isinstance(response, dict):
                status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                code = response.get("Error", {}).get("Code")
                if code in ("404", "NoSuchKey", "NotFound"):
                    return
            if status == 404:
                return
            raise
        if (
            existing.get("ContentLength") != byte_count
            or existing.get("Metadata", {}).get("sha256") != sha256
        ):
            raise NativeOrganismBinaryStoreError(
                "native remote predecessor changed"
            )
        # This bucket is versioned. A key-only DELETE would create a delete
        # marker and retain the full body as a noncurrent version, turning a
        # continuous organism into unbounded remote storage. Permanently
        # retire the exact version that was just read and verified. On an
        # unversioned bucket there is no version identifier, so the ordinary
        # exact-key deletion remains correct.
        version_id = existing.get("VersionId")
        request = {"Bucket": self.bucket, "Key": key}
        if version_id is not None:
            request["VersionId"] = version_id
        self.client.delete_object(**request)


def _object_store() -> Any:
    bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET")
    if bucket:
        import boto3

        return _S3ObjectStore(bucket=bucket, client=boto3.client("s3"))
    return _LocalDirectoryObjectStore(STATE_ROOT / LOCAL_OBJECT_MIRROR_DIRECTORY)


def _card_surface_substream(
    row: int,
    column: int,
    source_times: tuple[Fraction, ...],
    signal: tuple[float, ...],
) -> NativeSensorySubstreamInput:
    return NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id=CARD_SURFACE_SENSOR_ID,
        substream_id=f"card-row{row}-col{column}",
        topology_index=row * CARD_SURFACE_COLUMNS + column,
        coordinates=(
            NativeAxisCoordinate("row", str(row)),
            NativeAxisCoordinate("column", str(column)),
        ),
        physical_quantity=RETINAL_QUANTITY,
        physical_unit=RETINAL_UNIT,
        source_times=source_times,
        normalized_signal=signal,
        phase_turns=(Fraction(0),) * len(signal),
    )


def _contact_topology_index(row: int, column: int) -> int:
    """This contact site's own place in the declared tactile topology.

    Row-major over the contact sheet, exactly as the retina indexes its own
    sheet.  Distinct for every (row, column) pair, which is all the ratified
    Cantor territory law needs to give each site its own membrane capacitance.
    The touch sense layer holds NONE of this body's existing places, so these
    indices can start at zero and still be new ground.
    """

    return row * CONTACT_SHEET_COLUMNS + column


def _contact_site_substream(
    row: int,
    column: int,
    source_times: tuple[Fraction, ...],
    occupancy: tuple[float, ...],
) -> NativeSensorySubstreamInput:
    """One contact site of the sheet.

    The transported number is the fraction of THIS site's own declared patch
    that the touched object's footprint covers over the retained instant.  It
    is derived exactly (Fraction arithmetic over the object's declared integer
    geometry) and handed to the transport as binary64 at the same boundary the
    retina's luminance crosses; the receptor law downstream is exact-rational.
    """

    return NativeSensorySubstreamInput(
        sense=PhysicalSense.TOUCH,
        sensor_id=CONTACT_SHEET_SENSOR_ID,
        substream_id=f"contact-row{row}-col{column}",
        topology_index=_contact_topology_index(row, column),
        coordinates=(
            NativeAxisCoordinate("row", str(row)),
            NativeAxisCoordinate("column", str(column)),
        ),
        physical_quantity=CONTACT_QUANTITY,
        physical_unit=CONTACT_UNIT,
        source_times=source_times,
        normalized_signal=occupancy,
        phase_turns=(Fraction(0),) * len(occupancy),
    )


def _palmar_contact_substream(
    source_times: tuple[Fraction, ...],
    contact: tuple[float, ...] | tuple[Fraction, ...],
) -> NativeSensorySubstreamInput:
    """One distinct physical held-contact site appended beside the sheet."""

    return NativeSensorySubstreamInput(
        sense=PhysicalSense.TOUCH,
        sensor_id=PALMAR_CONTACT_SENSOR_ID,
        substream_id=PALMAR_CONTACT_SUBSTREAM_ID,
        topology_index=PALMAR_CONTACT_TOPOLOGY_INDEX,
        coordinates=(
            NativeAxisCoordinate("body-surface", "palmar"),
            NativeAxisCoordinate("contact-axis", "held-contact"),
        ),
        physical_quantity=CONTACT_QUANTITY,
        physical_unit=CONTACT_UNIT,
        source_times=source_times,
        normalized_signal=contact,
        phase_turns=(Fraction(0),) * len(contact),
    )


def _segment_overlap(low: Fraction, high: Fraction, index: int) -> Fraction:
    """Exact length of ``[low, high]`` inside the unit patch ``[index, index+1]``."""

    left = max(low, Fraction(index))
    right = min(high, Fraction(index + 1))
    return right - left if right > left else Fraction(0)


def _declared_footprint_occupancy(
    raster_width: int,
    raster_height: int,
) -> tuple[Fraction, ...]:
    """Exact per-site contact occupancy of one flat object on the sheet.

    THE ONLY THING READ FROM THE OBJECT IS ITS OWN DECLARED GEOMETRY: the two
    integers its raster header declares.  Not one pixel of its picture is
    consulted, and no texture map is invented.  Ink is flat; what touch
    honestly reports about a flat rectangle is its OUTLINE.

    The placement is forced, not chosen:

      * SCALE.  Neither the object nor the sheet declares a physical size
        anywhere in the manifest, so any particular scale would be an invented
        number.  The unique scale-free canonical placement is the MAXIMAL
        aspect-preserving inscription — the object grown until it meets the
        sheet's boundary.  Only the object's ASPECT survives, which is exactly
        the part of its geometry that IS declared.
      * POSITION.  The sheet declares no origin, no handedness and no
        preferred direction, so the only placement invariant under its own
        reflection symmetries is CENTRED.  Any offset would be an invented
        number.

    Occupancy is then the exact area of (footprint ∩ site patch) divided by the
    patch area, which is 1.  This is the same area-averaging reduction the
    retina applies to luminance, done in exact rationals because a rectangle's
    edges are rational and nothing here needs resampling.

    Returned row-major, one value per declared contact site, every one in
    [0, 1].  Sites the object does not reach return exactly zero — "nothing
    outside the card" is a physical report, not a missing port.
    """

    if raster_width <= 0 or raster_height <= 0:
        raise ValueError("a tactile footprint requires positive declared geometry")
    aspect = Fraction(raster_width, raster_height)
    sheet_width = Fraction(CONTACT_SHEET_COLUMNS)
    sheet_height = Fraction(CONTACT_SHEET_ROWS)
    # Maximal aspect-preserving inscription: grow until the first boundary is
    # met, whichever it is.
    height = min(sheet_height, sheet_width / aspect)
    width = height * aspect
    left = (sheet_width - width) / 2
    right = left + width
    bottom = (sheet_height - height) / 2
    top = bottom + height
    return tuple(
        _segment_overlap(left, right, column) * _segment_overlap(bottom, top, row)
        for row in range(CONTACT_SHEET_ROWS)
        for column in range(CONTACT_SHEET_COLUMNS)
    )


def _card_material() -> tuple[tuple[Fraction, ...] | None, tuple[Fraction, ...] | None]:
    """The approved deck's own declared physical stock, as the card's chemistry.

    Returns ``(None, None)`` where the manifest declares no stock or this body
    has no chemoreceptors — a card that cannot be smelled is not a card with
    no smell, it is a body with no nose, and the two must not look alike.
    """

    if not CHEMORECEPTION_AUTHORIZED:
        return None, None
    document = _manifest_document(
        CURRICULUM_ROOT / "card_experience_manifest-v1.json",
        "guala.external_tutor_card_experience_manifest.v1",
    )
    stock = document.get("physical_stock")
    if not isinstance(stock, dict):
        return None, None
    return (
        _declared_composition(stock.get("taste"), TASTE_CHANNELS, "card stock taste"),
        _declared_composition(stock.get("smell"), SMELL_CHANNELS, "card stock smell"),
    )


def _card_tactile_occupancy(surface_path: Path) -> tuple[float, ...]:
    """Per-site contact occupancy of one approved card, from its raster header.

    The card's declared geometry is the two integers in its own raster header,
    which the manifest pins by sha256.  Pillow reads the header only; no pixel
    of the picture reaches this path, which is the point — a card's feel is its
    outline, not its ink.
    """

    from PIL import Image

    with Image.open(surface_path) as image:
        width, height = image.size
    return tuple(float(value) for value in _declared_footprint_occupancy(width, height))




def _touch_ports(
    source_times: tuple[Fraction, ...],
    occupancy: tuple[float, ...] | None,
    palmar_contact: tuple[float, ...] | tuple[Fraction, ...] | None = None,
    body_surface_contact_trajectories: (
        tuple[tuple[Fraction, ...], ...] | None
    ) = None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """The mounted tactile roster for one hop, under the declared anatomy.

    ``occupancy`` is that hop's per-site lesson-sheet contact fraction, or
    ``None`` for a released sheet.  ``palmar_contact`` is the distinct exact
    held-object contact trajectory returned by the persistent world.  When
    touch is unauthorized the roster is empty and the body declares no touch.
    """

    if not TOUCH_RECEPTORS_AUTHORIZED:
        return ()
    held = occupancy if occupancy is not None else (0.0,) * CONTACT_SHEET_SITE_COUNT
    if len(held) != CONTACT_SHEET_SITE_COUNT:
        raise ValueError("contact occupancy count differs from the declared anatomy")
    frame_count = len(source_times)
    contact_signals = body_surface_contact_trajectories or tuple(
        (Fraction(held[index]).limit_denominator(1_000_000),) * frame_count
        for index in range(CONTACT_SHEET_SITE_COUNT)
    )
    if len(contact_signals) != CONTACT_SHEET_SITE_COUNT or any(
        len(signal) != frame_count
        or any(value < 0 or value > 1 for value in signal)
        for signal in contact_signals
    ):
        raise ValueError("body-surface contact trajectories changed anatomy or clock")
    sheet = tuple(
        _contact_site_substream(
            row,
            column,
            source_times,
            contact_signals[_contact_topology_index(row, column)],
        )
        for row in range(CONTACT_SHEET_ROWS)
        for column in range(CONTACT_SHEET_COLUMNS)
    )
    palmar = (
        (Fraction(0),) * frame_count
        if palmar_contact is None
        else tuple(palmar_contact)
    )
    if len(palmar) != frame_count:
        raise ValueError("palmar contact trajectory changed the shared clock")
    return (*sheet, _palmar_contact_substream(source_times, palmar))


def _touch_sheet_occurrence_port_indices() -> tuple[int, ...]:
    """The lesson-roster port indices of the retained contact sheet.

    Appended AFTER every port currently declared — the sight sites, then the
    retained legacy ear places and any cochlea — so a living body grows the
    sheet BESIDE the places it already holds instead of re-binding them.
    """

    start = CARD_SURFACE_PORT_COUNT + EAR_PORT_COUNT
    return tuple(range(start, start + CONTACT_SHEET_SITE_COUNT))


def _touch_occurrence_port_indices() -> tuple[int, ...]:
    """The lesson-roster indices of every mounted tactile receptor."""

    start = CARD_SURFACE_PORT_COUNT + EAR_PORT_COUNT
    return tuple(range(start, start + TOUCH_PORT_COUNT))


def _displacement_ports(
    source_times: tuple[Fraction, ...],
    displacement: tuple[Fraction, ...] | None,
    trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """The mounted displacement roster for one hop.

    ``displacement`` is how her body ACTUALLY moved over this hop, as exact
    fractions of the declared span, or ``None`` for a body that did not move
    — which is a lawful state (standing still is not the absence of balance)
    and never an invented motion.
    """

    if not VESTIBULAR_AUTHORIZED:
        return ()
    held = (
        displacement
        if displacement is not None
        else (Fraction(0),) * DISPLACEMENT_SITE_COUNT
    )
    if len(held) != DISPLACEMENT_SITE_COUNT:
        raise ValueError("displacement count differs from the declared anatomy")
    frame_count = len(source_times)
    signals = trajectories or tuple(
        (value,) * frame_count for value in held
    )
    if len(signals) != DISPLACEMENT_SITE_COUNT or any(
        len(signal) != frame_count for signal in signals
    ):
        raise ValueError("displacement trajectories changed anatomy or clock")
    for channel, signal in zip(DISPLACEMENT_CHANNELS, signals, strict=True):
        if any(not Fraction(-1) <= value <= Fraction(1) for value in signal):
            raise ValueError(
                f"displacement channel {channel!r} left the declared span"
            )
    return tuple(
        NativeSensorySubstreamInput(
            sense=PhysicalSense.BODY,
            sensor_id=DISPLACEMENT_SENSOR_ID,
            substream_id=f"displacement-{channel}",
            # Appended AFTER the interoceptive sites so a living body grows
            # this field BESIDE the places it already holds.
            topology_index=INTEROCEPTION_PORT_COUNT + index,
            coordinates=(
                NativeAxisCoordinate("somatic-axis", channel),
                NativeAxisCoordinate("somatic-frame", "egocentric-before-after"),
            ),
            physical_quantity=DISPLACEMENT_QUANTITY,
            physical_unit=DISPLACEMENT_UNIT,
            source_times=source_times,
            normalized_signal=tuple(float(value) for value in signal),
            phase_turns=(Fraction(0),) * frame_count,
        )
        for index, (channel, signal) in enumerate(
            zip(DISPLACEMENT_CHANNELS, signals, strict=True)
        )
    )




def _articulatory_body_ports(
    source_times: tuple[Fraction, ...],
    trajectories: tuple[tuple[Fraction, ...], ...] | None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """Four local mechanoreceptor trajectories of the vocal body."""

    frame_count = len(source_times)
    held = trajectories or tuple(
        (Fraction(0),) * frame_count
        for _ in range(ARTICULATORY_BODY_PORT_COUNT)
    )
    if len(held) != ARTICULATORY_BODY_PORT_COUNT or any(
        len(signal) != frame_count for signal in held
    ):
        raise ValueError("articulatory body trajectory changed anatomy or clock")
    return tuple(
        NativeSensorySubstreamInput(
            sense=PhysicalSense.BODY,
            sensor_id=ARTICULATORY_BODY_SENSOR_ID,
            substream_id=f"articulation-{channel}",
            topology_index=(
                INTEROCEPTION_PORT_COUNT + DISPLACEMENT_PORT_COUNT + index
            ),
            coordinates=(
                NativeAxisCoordinate("articulatory-site", channel),
                NativeAxisCoordinate("somatic-frame", "organism-local"),
            ),
            physical_quantity=quantity,
            physical_unit=ARTICULATORY_BODY_UNIT,
            source_times=source_times,
            normalized_signal=tuple(float(value) for value in signal),
            phase_turns=(Fraction(0),) * frame_count,
            exact_physical_signal=signal,
        )
        for index, (channel, quantity, signal) in enumerate(
            zip(
                ARTICULATORY_BODY_CHANNELS,
                ARTICULATORY_BODY_QUANTITIES,
                held,
                strict=True,
            )
        )
    )


def _thermal_body_temperatures() -> tuple[Fraction, Fraction]:
    """Current cutaneous and core temperature from the one world authority."""

    if not THERMAL_PORT_COUNT:
        raise RuntimeError("thermal body anatomy is not mounted")
    observation = _world().thermal_observation()
    by_id = dict(zip(
        observation.node_ids,
        observation.temperatures_millikelvin,
        strict=True,
    ))
    try:
        return by_id["body:cutaneous-shell"], by_id["body:core"]
    except KeyError as error:
        raise RuntimeError("thermal body lost its core or cutaneous node") from error


def _thermal_body_endpoints(execution: Any) -> tuple[
    tuple[Fraction, Fraction], tuple[Fraction, Fraction]
]:
    """Exact before/after body temperatures for one coupled world action."""

    endpoints = _world().thermal_endpoints_for_execution(execution)
    before = dict(zip(
        endpoints.node_ids,
        endpoints.before_temperatures_millikelvin,
        strict=True,
    ))
    after = dict(zip(
        endpoints.node_ids,
        endpoints.after_temperatures_millikelvin,
        strict=True,
    ))
    node_ids = ("body:cutaneous-shell", "body:core")
    try:
        return (
            tuple(before[node_id] for node_id in node_ids),
            tuple(after[node_id] for node_id in node_ids),
        )
    except KeyError as error:
        raise RuntimeError("thermal action lost its body endpoints") from error


def _thermal_ports(
    source_times: tuple[Fraction, ...],
    temperature_trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
    *,
    anatomy_quiescent: bool = False,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """Two tonic thermoreceptors fed only by physical temperature nodes."""

    if not THERMAL_PORT_COUNT:
        return ()
    frame_count = len(source_times)
    if anatomy_quiescent:
        trajectories = tuple(
            (Fraction(0),) * frame_count for _ in THERMAL_CHANNELS
        )
    elif temperature_trajectories is None:
        current = _thermal_body_temperatures()
        trajectories = tuple(
            (temperature,) * frame_count for temperature in current
        )
    else:
        trajectories = temperature_trajectories
    if len(trajectories) != THERMAL_PORT_COUNT or any(
        len(signal) != frame_count for signal in trajectories
    ):
        raise ValueError("thermal receptor trajectories changed anatomy or clock")
    span = THERMAL_MAX_MILLIKELVIN - THERMAL_MIN_MILLIKELVIN
    normalized = []
    for channel, signal in zip(THERMAL_CHANNELS, trajectories, strict=True):
        values = tuple(
            value
            if anatomy_quiescent
            else (value - THERMAL_MIN_MILLIKELVIN) / span
            for value in signal
        )
        if any(not Fraction(0) <= value <= Fraction(1) for value in values):
            raise ValueError(
                f"thermal channel {channel!r} left its declared receptor interval"
            )
        normalized.append(values)
    topology_start = (
        INTEROCEPTION_PORT_COUNT
        + DISPLACEMENT_PORT_COUNT
        + ARTICULATORY_BODY_PORT_COUNT
    )
    return tuple(
        NativeSensorySubstreamInput(
            sense=PhysicalSense.BODY,
            sensor_id=THERMAL_SENSOR_ID,
            substream_id=f"temperature-{channel}",
            topology_index=topology_start + index,
            coordinates=(
                NativeAxisCoordinate("body-compartment", channel),
                NativeAxisCoordinate(
                    "thermal-reference-interval",
                    "273000-to-323000-millikelvin",
                ),
            ),
            physical_quantity=THERMAL_QUANTITY,
            physical_unit=THERMAL_UNIT,
            source_times=source_times,
            normalized_signal=tuple(float(value) for value in signal),
            phase_turns=(Fraction(0),) * frame_count,
        )
        for index, (channel, signal) in enumerate(
            zip(THERMAL_CHANNELS, normalized, strict=True)
        )
    )


def _declared_composition(
    value: object,
    channels: tuple[str, ...],
    label: str,
) -> tuple[Fraction, ...]:
    """One authored material composition, as exact fractions of saturation.

    Authored by whoever offers the material, exactly as an approved card's
    surface is authored — and refused rather than clamped when it states a
    concentration a receptor cannot honestly transduce.
    """

    if value is None:
        return (Fraction(0),) * len(channels)
    if not isinstance(value, dict):
        raise ValueError(f"{label} composition must be a mapping of channels")
    unknown = set(value) - set(channels)
    if unknown:
        raise ValueError(
            f"{label} composition declares channels this body has no "
            f"receptor for: {', '.join(sorted(unknown))}"
        )
    held = []
    for channel in channels:
        raw = value.get(channel, 0)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{label} channel {channel!r} is not a number")
        concentration = Fraction(raw).limit_denominator(1_000_000)
        if not Fraction(0) <= concentration <= Fraction(1):
            raise ValueError(
                f"{label} channel {channel!r} is {float(concentration)}, "
                "outside the saturating range a receptor can transduce"
            )
        held.append(concentration)
    return tuple(held)


def _chemoreceptive_ports(
    sense: Any,
    sensor_id: str,
    quantity: str,
    channels: tuple[str, ...],
    source_times: tuple[Fraction, ...],
    composition: tuple[Fraction, ...] | None,
    trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """One chemoreceptive roster for one hop.

    ``composition`` is that hop's per-channel concentration, or ``None`` for
    nothing present — which is a lawful state, not an absent sense, exactly
    as darkness and silence are.
    """

    if not CHEMORECEPTION_AUTHORIZED:
        return ()
    held = composition if composition is not None else (Fraction(0),) * len(channels)
    if len(held) != len(channels):
        raise ValueError("declared composition differs from the declared anatomy")
    frame_count = len(source_times)
    signals = trajectories or tuple((value,) * frame_count for value in held)
    if len(signals) != len(channels) or any(
        len(signal) != frame_count for signal in signals
    ):
        raise ValueError("chemical trajectories changed anatomy or clock")
    return tuple(
        NativeSensorySubstreamInput(
            sense=sense,
            sensor_id=sensor_id,
            substream_id=f"{sensor_id}-{channel}",
            topology_index=index,
            coordinates=(
                NativeAxisCoordinate("chemical-channel", channel),
                NativeAxisCoordinate("chemoreceptive-range", sensor_id),
            ),
            physical_quantity=quantity,
            physical_unit=CHEMICAL_UNIT,
            source_times=source_times,
            normalized_signal=tuple(float(value) for value in signal),
            phase_turns=(Fraction(0),) * frame_count,
        )
        for index, (channel, signal) in enumerate(
            zip(channels, signals, strict=True)
        )
    )


def _taste_ports(
    source_times: tuple[Fraction, ...],
    composition: tuple[Fraction, ...] | None,
    trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    return _chemoreceptive_ports(
        PhysicalSense.TASTE, TASTE_SENSOR_ID, TASTE_QUANTITY,
        TASTE_CHANNELS, source_times, composition, trajectories,
    )


def _smell_ports(
    source_times: tuple[Fraction, ...],
    composition: tuple[Fraction, ...] | None,
    trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    return _chemoreceptive_ports(
        PhysicalSense.SMELL, SMELL_SENSOR_ID, SMELL_QUANTITY,
        SMELL_CHANNELS, source_times, composition, trajectories,
    )






def _cochlear_topology_index(ear_index: int, channel_index: int) -> int:
    """This cochlear site's own place in the declared auditory topology.

    Distinct for every (ear, band) pair, which is all the ratified Cantor
    territory law needs to give each site its own membrane capacitance.
    """

    return (
        LEGACY_EAR_PORT_COUNT
        + ear_index * COCHLEAR_CHANNELS_PER_EAR
        + channel_index
    )


def _cochlear_band_substream(
    ear_index: int,
    channel_index: int,
    source_times: tuple[Fraction, ...],
    band_signal: tuple[float, ...],
) -> NativeSensorySubstreamInput:
    """One tonotopic receptor site of one cochlea.

    The transported number is that band's normalized root-mean-square pressure
    over the retained instant.  Squaring it (which the auditory receptor law
    does) gives the band's mean-square pressure, which is exactly the quantity
    acoustic intensity `I = <p^2>/Z` is built from, so the place decomposition
    lives here in the sensor layer — where the camera's luminance extraction
    already lives — and the receptor law downstream stays exact-rational.
    """

    channel = COCHLEAR_CHANNELS[channel_index]
    return NativeSensorySubstreamInput(
        sense=PhysicalSense.SOUND,
        sensor_id=EAR_SENSOR_ID,
        substream_id=f"cochlea-{ear_index}-band-{channel_index:02d}",
        topology_index=_cochlear_topology_index(ear_index, channel_index),
        coordinates=(
            NativeAxisCoordinate("ear", str(ear_index)),
            NativeAxisCoordinate("cochlear-band", str(channel_index)),
            NativeAxisCoordinate(
                "centre-frequency-millihertz",
                str(int(round(channel.centre_hz * 1000.0))),
            ),
        ),
        physical_quantity=COCHLEAR_QUANTITY,
        physical_unit=COCHLEAR_UNIT,
        source_times=source_times,
        normalized_signal=band_signal,
        phase_turns=(Fraction(0),) * len(band_signal),
    )


def _cochlear_ports(
    source_times: tuple[Fraction, ...],
    bands: tuple[tuple[float, ...], ...],
) -> tuple[NativeSensorySubstreamInput, ...]:
    """Both cochleae, tonotopic site by tonotopic site, in topology order.

    ``bands`` carries one signal per cochlear channel of one ear; both ears are
    immersed in the SAME ambient pressure field (no head geometry is declared,
    so no interaural difference is claimed) and therefore receive the same band
    signals.  Their sites are still physically distinct because their declared
    places are.
    """

    if len(bands) != COCHLEAR_CHANNELS_PER_EAR:
        raise ValueError("cochlear band count differs from the declared anatomy")
    return tuple(
        _cochlear_band_substream(
            ear_index, channel_index, source_times, bands[channel_index]
        )
        for ear_index in range(EAR_COUNT)
        for channel_index in range(COCHLEAR_CHANNELS_PER_EAR)
    )


def _silent_cochlear_bands(frame_count: int) -> tuple[tuple[float, ...], ...]:
    """True silence at every tonotopic place.

    Silence is a lawful acoustic state, not an absent sense: a zero band RMS
    squares to exactly zero transduced energy, delivers nothing, and erases
    nothing.  This is the acoustic twin of a genuinely dark card surface.
    """

    return ((0.0,) * frame_count,) * COCHLEAR_CHANNELS_PER_EAR


def _cochlear_occurrence_port_indices(ear_index: int) -> tuple[int, ...]:
    """The lesson-roster port indices of one whole cochlea.

    Each cochlea is its own occurrence and therefore its own reached cohort:
    two ears are two separate mechanical structures with no declared coupling
    between them, and a retained original must be connected through contacts
    that were physically active, which a single tonotopic chain per ear is and
    a union of two unconnected chains is not.
    """

    start = (
        CARD_SURFACE_PORT_COUNT
        + LEGACY_EAR_PORT_COUNT
        + ear_index * COCHLEAR_CHANNELS_PER_EAR
    )
    return tuple(range(start, start + COCHLEAR_CHANNELS_PER_EAR))


# ---------------------------------------------------------------------------
# The UNAUTHORIZED (legacy) ear roster
#
# Verbatim, byte for byte, the ear declaration the living organism receives
# today: two co-located pressure ports immersed in one ambient field, carrying
# the decimated pressure waveform under a declared quantity no receptor law
# recognizes.  It is kept whole rather than approximated, because the whole
# point of the gate is that a deploy changes NOTHING about her episodes until
# growing ears is explicitly authorized.


def _ear_pressure_substream(
    ear_index: int,
    source_times: tuple[Fraction, ...],
    signal: tuple[float, ...],
) -> NativeSensorySubstreamInput:
    return NativeSensorySubstreamInput(
        sense=PhysicalSense.SOUND,
        sensor_id=EAR_SENSOR_ID,
        substream_id=f"ear-{ear_index}",
        topology_index=ear_index,
        coordinates=(NativeAxisCoordinate("ear", str(ear_index)),),
        physical_quantity=PHYSICAL_QUANTITY,
        physical_unit=PHYSICAL_UNIT,
        source_times=source_times,
        normalized_signal=signal,
        phase_turns=(Fraction(0),) * len(signal),
    )


def _legacy_ear_ports(
    source_times: tuple[Fraction, ...],
    signal: tuple[float, ...],
) -> tuple[NativeSensorySubstreamInput, ...]:
    """Both co-located organism ears immersed in one ambient pressure field."""

    return tuple(
        _ear_pressure_substream(ear_index, source_times, signal)
        for ear_index in range(LEGACY_EAR_PORT_COUNT)
    )


def _sound_ports(
    legacy_times: tuple[Fraction, ...],
    legacy_signal: tuple[float, ...],
    cochlear: tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]] | None,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """The mounted acoustic roster for one hop, under the declared anatomy.

    ``legacy_*`` is the decimated ambient pressure the two legacy ear ports
    carry; ``cochlear`` is that hop's tonotopic observation, or ``None`` for
    true silence on the surface's own clock.  Exactly one of the two rosters is
    real for a given process, decided once at import by the authorization gate.
    """

    legacy = _legacy_ear_ports(legacy_times, legacy_signal)
    if not COCHLEAR_EARS_AUTHORIZED:
        return legacy
    cochlear_times, cochlear_bands = (
        cochlear
        if cochlear is not None
        else (legacy_times, _silent_cochlear_bands(len(legacy_times)))
    )
    # The retained legacy places come first, exactly where her body already
    # holds them; the cochlea is appended beside them.
    return legacy + _cochlear_ports(cochlear_times, cochlear_bands)


def _sound_occurrences(
    legacy_times: tuple[Fraction, ...],
    legacy_frame_count: int,
    cochlear_times: tuple[Fraction, ...] | None,
) -> tuple[Any, ...]:
    """The acoustic occurrences of one hop, under the declared anatomy.

    Authorized: one exact acoustic occurrence per cochlea, because two ears are
    two separate mechanical structures.  Unauthorized: the single combined
    legacy ear occurrence, exactly as declared today.
    """

    legacy_occurrence = _occurrence(
        tuple(
            range(
                CARD_SURFACE_PORT_COUNT,
                CARD_SURFACE_PORT_COUNT + LEGACY_EAR_PORT_COUNT,
            )
        ),
        legacy_times,
        legacy_frame_count,
    )
    if not COCHLEAR_EARS_AUTHORIZED:
        return (legacy_occurrence,)
    times = cochlear_times if cochlear_times is not None else legacy_times
    return (legacy_occurrence,) + tuple(
        _occurrence(
            _cochlear_occurrence_port_indices(ear_index), times, len(times)
        )
        for ear_index in range(EAR_COUNT)
    )


def _sense_states(
    observed: dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
) -> dict[PhysicalSense, SenseBoundaryState]:
    return {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }


def _occurrence(
    port_indices: tuple[int, ...],
    source_times: tuple[Fraction, ...],
    relevance_count: int,
    groups: tuple[tuple[int, ...], ...] | None = None,
) -> NativeJointSourceOccurrenceInput:
    return NativeJointSourceOccurrenceInput(
        port_indices=port_indices,
        source_times=source_times,
        joint_intersample_profile_payload=(
            UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
        ),
        groups=groups or (tuple(range(len(port_indices))),),
        joint_relevance_profile_payload=JOINT_RELEVANCE_PROFILE,
        joint_relevance=(Fraction(1),) * relevance_count,
    )


def _lesson_port_groups() -> tuple[tuple[int, ...], ...]:
    """The mounted anatomical structures inside one simultaneous sensorium."""

    groups: list[tuple[int, ...]] = []
    cursor = 0

    def append_group(width: int) -> None:
        nonlocal cursor
        if width:
            groups.append(tuple(range(cursor, cursor + width)))
            cursor += width

    append_group(CARD_SURFACE_PORT_COUNT)
    append_group(LEGACY_EAR_PORT_COUNT)
    if COCHLEAR_EARS_AUTHORIZED:
        for _ in range(EAR_COUNT):
            append_group(COCHLEAR_CHANNELS_PER_EAR)
    append_group(TOUCH_PORT_COUNT)
    append_group(INTEROCEPTION_PORT_COUNT)
    append_group(TASTE_PORT_COUNT)
    append_group(SMELL_PORT_COUNT)
    append_group(DISPLACEMENT_PORT_COUNT)
    append_group(ARTICULATORY_BODY_PORT_COUNT)
    append_group(THERMAL_PORT_COUNT)
    if cursor != LESSON_PORT_COUNT:
        raise ValueError("mounted lesson groups do not partition the sensorium")
    return tuple(groups)


def _declared_anatomy_episode() -> Any:
    """The app's own declared port roster as one quiescent anatomy episode.

    Frame times mirror the ratified four-frame sight anatomy fixture
    (``Fraction(index, 4)``); all declared signals are quiescent zero because
    this episode declares anatomy, not experience.  One occurrence covers the
    whole roster on one shared clock, exactly as a card lesson delivers it.
    """

    times = tuple(
        Fraction(index, CARD_SURFACE_FRAME_COUNT)
        for index in range(CARD_SURFACE_FRAME_COUNT)
    )
    quiescent = (0.0,) * CARD_SURFACE_FRAME_COUNT
    sight_ports = tuple(
        _card_surface_substream(row, column, times, quiescent)
        for row in range(CARD_SURFACE_ROWS)
        for column in range(CARD_SURFACE_COLUMNS)
    )
    observed = {
        PhysicalSense.SIGHT: sight_ports,
        PhysicalSense.SOUND: _sound_ports(times, quiescent, None),
    }
    touch_ports = _touch_ports(times, None)
    if touch_ports:
        observed[PhysicalSense.TOUCH] = touch_ports
    taste_ports = _taste_ports(times, None)
    if taste_ports:
        observed[PhysicalSense.TASTE] = taste_ports
    smell_ports = _smell_ports(times, None)
    if smell_ports:
        observed[PhysicalSense.SMELL] = smell_ports
    displacement_ports = _displacement_ports(times, None)
    if displacement_ports:
        observed[PhysicalSense.BODY] = (
            observed.get(PhysicalSense.BODY, ()) + displacement_ports
        )
    observed[PhysicalSense.BODY] = (
        observed.get(PhysicalSense.BODY, ())
        + _articulatory_body_ports(times, None)
        + _thermal_ports(times, anatomy_quiescent=True)
    )
    return settle_native_joint_source_episode(
        assembly_id="guala-production-declared-anatomy",
        observed_substreams=observed,
        states=_sense_states(observed),
        occurrences=(
            _occurrence(
                tuple(range(LESSON_PORT_COUNT)),
                times,
                len(times),
                _lesson_port_groups(),
            ),
        ),
    )


def _lesson_anatomy() -> Any:
    """One immutable native receptor topology, mounted once per process."""

    global _mounted_lesson_anatomy
    if _mounted_lesson_anatomy is None:
        _mounted_lesson_anatomy = _declared_anatomy_episode()
    return _mounted_lesson_anatomy


def _declared_retinal_neighbours() -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    """Every neighbouring pair of the app's OWN declared card surface.

    The surface is declared as ``CARD_SURFACE_ROWS`` by
    ``CARD_SURFACE_COLUMNS`` receptor sites, each carrying its own declared
    ``row``/``column`` coordinates.  Two sites neighbour each other when they
    share a row and sit in adjacent columns, or share a column and sit in
    adjacent rows.  That is read straight off the declaration; nothing here is
    chosen, tuned, or inferred, and the pair set changes only if the declared
    layout does.

    Horizontal pairs come first and vertical pairs second so that a body born
    before the vertical pairs existed grows into this same set by APPENDING
    them, in this order, with its existing contacts untouched.
    """

    horizontal = tuple(
        ((row, column), (row, column + 1))
        for row in range(CARD_SURFACE_ROWS)
        for column in range(CARD_SURFACE_COLUMNS - 1)
    )
    vertical = tuple(
        ((row, column), (row + 1, column))
        for row in range(CARD_SURFACE_ROWS - 1)
        for column in range(CARD_SURFACE_COLUMNS)
    )
    return horizontal + vertical


def _declared_retinal_vertical_neighbours() -> (
    tuple[tuple[tuple[int, int], tuple[int, int]], ...]
):
    """The column-wise half of the declared neighbourhood."""

    return tuple(
        pair
        for pair in _declared_retinal_neighbours()
        if pair[0][1] == pair[1][1]
    )


def _card_surface_substream_id(row: int, column: int) -> str:
    """The declared receptor name of one card-surface site."""

    return f"card-row{row}-col{column}"


def _authored_growth_dna() -> tuple[Any, list[tuple[list[int], list[tuple[int, int, int]]]]]:
    """Authored growth DNA over the app's declared roster.

    One seed group per declared receptor structure, because a receptor law can
    genesis a cohort only from an occurrence it wholly governs.  With cochlear
    ears AUTHORIZED this app declares three structures: the card surface, and
    one cochlea per ear.  UNAUTHORIZED it declares one — the card surface —
    exactly as the living organism was seeded: the two legacy ear sites carry
    no authored contacts and no receptor law governs them, so they can never
    genesis a cohort of their own.

    * THE RETINAL GROUP IS A SHEET, NOT A CHAIN.  Its contacts are the
      declared surface's OWN four-neighbourhood (``_declared_retinal_neighbours``):
      24 within-row pairs and 18 within-column pairs, 42 in total.  The retired
      authorship chained the 27 sites by storage index alone, which authored
      the 24 true within-row contacts plus TWO contacts between sites at
      opposite ends of the surface — the row wraps ``(0,8)-(1,0)`` and
      ``(1,8)-(2,0)`` — and no within-column contact at all.  An eye whose
      only adjacency runs along rows cannot tell up from down; a body born
      from this authorship has no false adjacency and does have both.  Bodies
      born under the retired authorship keep their two row-wrap contacts,
      because contacts are appended and never removed (see
      ``_retinal_lattice_growth_contacts``).
    * Each cochlear group chains its 16 tonotopic sites in TONOTOPIC order.
      The chain is anatomy, not convenience: the basilar membrane is one
      continuous mechanical structure, so neighbouring places are coupled, and
      distant places are not.  The two cochleae are NOT chained to each other —
      two ears are two separate structures and no coupling between them is
      declared (no head geometry exists to declare one).
    * The chain is also what makes a structure able to REMEMBER: participation
      retention requires at least three changed members connected through
      contacts that were physically active, and an unchained cohort would
      satisfy the count and fail the connectivity forever.

    Every authored contact is the ratified authored 500 pS conductance,
    mirroring the ratified chain-seed growth fixtures.
    """

    episode = _declared_anatomy_episode()
    retinal_contacts = [
        (
            left_row * CARD_SURFACE_COLUMNS + left_column,
            right_row * CARD_SURFACE_COLUMNS + right_column,
            AUTHORED_SEED_CONDUCTANCE_PICOSIEMENS,
        )
        for (left_row, left_column), (right_row, right_column) in (
            _declared_retinal_neighbours()
        )
    ]
    cochlear_contacts = [
        (index - 1, index, AUTHORED_SEED_CONDUCTANCE_PICOSIEMENS)
        for index in range(1, COCHLEAR_CHANNELS_PER_EAR)
    ]
    seed_groups: list[tuple[list[int], list[tuple[int, int, int]]]] = [
        (list(range(CARD_SURFACE_PORT_COUNT)), retinal_contacts)
    ]
    if COCHLEAR_EARS_AUTHORIZED:
        for ear_index in range(EAR_COUNT):
            seed_groups.append(
                (
                    list(_cochlear_occurrence_port_indices(ear_index)),
                    list(cochlear_contacts),
                )
            )
    if TOUCH_RECEPTORS_AUTHORIZED:
        # The contact sheet chains its sites in the SAME row-major order the
        # retina chains its own sheet.  The chain is anatomy, not convenience:
        # a body surface is one continuous mechanical structure, so neighbouring
        # places are coupled.  It is also what lets the sheet REMEMBER —
        # participation retention requires at least three changed members
        # connected through contacts that were physically active, and an
        # unchained sheet would satisfy the count and fail the connectivity
        # forever.  Every authored contact is the ratified authored 500 pS
        # conductance, exactly as the retinal and cochlear chains are.
        seed_groups.append(
            (
                list(_touch_sheet_occurrence_port_indices()),
                [
                    (index - 1, index, AUTHORED_SEED_CONDUCTANCE_PICOSIEMENS)
                    for index in range(1, CONTACT_SHEET_SITE_COUNT)
                ],
            )
        )
    return (episode, seed_groups)


def _retinal_lattice_growth_contacts() -> list[tuple[str, str, str, str, int]]:
    """The within-column contacts, authored for growth onto a living body.

    A body born under the retired chain authorship carries every within-row
    contact already and no within-column contact at all.  Growth therefore
    authors exactly the vertical half of the declared neighbourhood, at the
    same ratified 500 pS every existing contact carries, addressed by the
    declared receptor names rather than by storage index so that no living
    contact can be reordered or renumbered.
    """

    return [
        (
            CARD_SURFACE_SENSOR_ID,
            _card_surface_substream_id(left_row, left_column),
            CARD_SURFACE_SENSOR_ID,
            _card_surface_substream_id(right_row, right_column),
            AUTHORED_SEED_CONDUCTANCE_PICOSIEMENS,
        )
        for (left_row, left_column), (right_row, right_column) in (
            _declared_retinal_vertical_neighbours()
        )
    ]


def _genesis_identity() -> str:
    value = os.environ.get("GUALA_NATIVE_ORGANISM_IDENTITY", "")
    if value:
        if not _ORGANISM_IDENTITY_PATTERN.fullmatch(value):
            raise RuntimeError(
                "GUALA_NATIVE_ORGANISM_IDENTITY is not canonical UUID text"
            )
        return value
    return str(uuid.uuid4())


def _perform_genesis(admission: NativeResidentResourceAdmission) -> None:
    """Create, stage, and publish one seeded growth-DNA genesis body."""

    organism = create_native_resident_organism(
        organism_identity=_genesis_identity(),
        organism_tick=0,
        growth_dna=_authored_growth_dna(),
        max_envelope_bytes=admission.max_envelope_bytes,
        max_fabric_bytes=admission.max_fabric_bytes,
        max_logical_peak_bytes=admission.max_logical_peak_bytes,
    )
    staged = stage_active_native_organism(
        STATE_ROOT,
        organism,
        max_envelope_bytes=admission.max_envelope_bytes,
    )
    publish_staged_native_organism(
        staged,
        expected_predecessor_sha256=None,
        object_store=_object_store(),
        max_envelope_bytes=admission.max_envelope_bytes,
        max_fabric_bytes=admission.max_fabric_bytes,
        max_logical_peak_bytes=admission.max_logical_peak_bytes,
    )


def _tick_attributed_effector_bindings(
    hop: dict[str, Any],
) -> tuple[tuple[int, str, str, str, int], ...]:
    """Attribute each effector binding to the exact tick its discharge settled.

    The native evidence flattens motor-to-terminal bindings across the whole
    prepared trajectory without a tick, while each body consequence carries
    the PREDECESSOR tick of the interval that settled it. The real tick of a
    binding therefore comes from the per-interval causal evidence: each
    interval names its own predecessor tick and its own motor discharges, and
    a motor lineage's terminal (axis, direction) is fixed anatomy read from
    the flattened bindings. Manufacturing a tick from the hop's final
    organism_tick is wrong by one for a single interval and wrong entirely
    for multi-interval trajectories.
    """

    terminal_by_lineage: dict[str, tuple[str, str]] = {}
    for binding in hop["body_effector_bindings"]:
        lineage, axis, direction, _carriers = binding
        terminal_by_lineage[str(lineage)] = (str(axis), str(direction))
    attributed: list[tuple[int, str, str, str, int]] = []
    for interval in hop.get("causal_interval_evidence", ()):
        settlement_tick = int(interval["predecessor_organism_tick"])
        for recruitment in interval["motor_unit_recruitments"]:
            lineage = str(recruitment[0])
            carriers = int(recruitment[2])
            terminal = terminal_by_lineage.get(lineage)
            if terminal is None:
                raise RuntimeError(
                    "native motor discharge lost its effector terminal"
                )
            attributed.append(
                (settlement_tick, lineage, terminal[0], terminal[1], carriers)
            )
    if not attributed and hop["body_effector_bindings"]:
        raise RuntimeError(
            "native effector bindings lost their causal interval evidence"
        )
    return tuple(attributed)


def _causal_interval_hops(
    evidence: ResidentPrepareEvidence,
) -> tuple[dict[str, Any], ...]:
    """Project only the transient facts consumed by the causal observer."""

    return tuple(
        {
            "predecessor_organism_tick": interval.predecessor_organism_tick,
            "organism_tick": interval.organism_tick,
            "source_duration_samples_at_articulatory_rate": (
                interval.source_duration_samples_at_articulatory_rate
            ),
            "rest_recovered_neuron_count": (
                interval.rest_recovered_neuron_count
            ),
            "externally_perturbed_neuron_lineages": (
                interval.externally_perturbed_neuron_lineages
            ),
            "internally_reassembled_formation_cues": (
                interval.internally_reassembled_formation_cues
            ),
            "causal_thought_transitions": interval.causal_thought_transitions,
            "externally_reassembled_formation_frontiers": (
                interval.externally_reassembled_formation_frontiers
            ),
            "motor_unit_recruitments": interval.motor_unit_recruitments,
            "root_yaw_unit_recruitments": interval.root_yaw_unit_recruitments,
            "root_translation_unit_recruitments": (
                interval.root_translation_unit_recruitments
            ),
            "articulatory_unit_recruitments": (
                interval.articulatory_unit_recruitments
            ),
            "articulatory_pressure_pcm": interval.articulatory_pressure_pcm,
            "articulatory_body_trajectories": (
                interval.articulatory_body_trajectories
            ),
            "articulatory_sample_rate_hz": (
                interval.articulatory_sample_rate_hz
            ),
            "articulatory_peak_transducer_surface_velocity_pcm": (
                interval.articulatory_peak_transducer_surface_velocity_pcm
            ),
            "articulatory_glottal_open_samples_at_apex": (
                interval.articulatory_glottal_open_samples_at_apex
            ),
            "articulatory_mouth_area_square_millimetres_at_apex": (
                interval.articulatory_mouth_area_square_millimetres_at_apex
            ),
            "articulatory_perioral_area_displacement_square_millimetres": (
                interval.articulatory_perioral_area_displacement_square_millimetres
            ),
            "articulatory_applied_motor_quanta": (
                interval.articulatory_applied_motor_quanta
            ),
            "articulatory_stalled_motor_quanta": (
                interval.articulatory_stalled_motor_quanta
            ),
            "emitted_neuron_fractals": tuple(
                {"neuron_lineage": lineage}
                for lineage in interval.emitted_neuron_lineages
            ),
            "changed_contact_channel_states": (
                interval.changed_contact_channel_states
            ),
            "affective_balance_trajectories": (
                interval.affective_balance_trajectories
            ),
            "causal_frontier_advances": interval.causal_frontier_advances,
            "articulated_body_state": interval.articulated_body_state,
        }
        for interval in evidence.causal_interval_evidence
    )


def _commit_admitted_hop(
    organism: Any,
    episode: Any,
    maximum_causal_intervals: Any,
    *,
    external_participant_action_receipt: str | None = None,
    purpose: str = "primary",
    coexisting: bool = False,
    native_advance: Any | None = None,
    native_advance_tail: tuple[Any, ...] = (),
) -> dict[str, Any]:
    """Prepare and commit one admitted hop or one ordered native trajectory.

    No persistence happens here.  The caller holds ``_transition_lock`` and
    must durably publish the committed body before any observation surface
    reports it. If ``coexisting`` is true, every supplied source reaches its
    receptor in one shared physical interval rather than becoming a temporal
    trajectory. Returns only what the native observation actually says.
    """

    sources = episode if isinstance(episode, tuple) else (episode,)
    sources = tuple(
        source.episode if isinstance(source, _AcousticHopPlan) else source
        for source in sources
    )
    intervals = (
        tuple(maximum_causal_intervals)
        if isinstance(episode, tuple)
        else (maximum_causal_intervals,)
    )
    _stage_started = time.perf_counter()
    advance = native_advance or (
        organism.advance_coexisting_admitted_interval_unsealed
        if coexisting
        else organism.advance_admitted_trajectory_unsealed
    )
    evidence: ResidentPrepareEvidence = advance(
        sources,
        intervals,
        *native_advance_tail,
    )
    _elapsed_ms = (time.perf_counter() - _stage_started) * 1000.0
    _transport_stage_wall_ms["native_settlement"] = (
        _transport_stage_wall_ms.get("native_settlement", 0.0) + _elapsed_ms
    )
    _transport_stage_wall_ms[f"native_{purpose}"] = (
        _transport_stage_wall_ms.get(f"native_{purpose}", 0.0) + _elapsed_ms
    )
    ingress_sense_counts = {
        sense.value: count
        for sense, count in zip(
            SENSE_ORDER, evidence.receptor_ingress_sense_counts, strict=True
        )
    }
    return {
        "cognitive_mosaic_count": evidence.cognitive_mosaic_count,
        "cognitive_trace_count": evidence.cognitive_trace_count,
        "complete_neuron_count": evidence.complete_neuron_count,
        "developmental_resting_neuron_count": (
            evidence.developmental_resting_neuron_count
        ),
        "complete_neuron_fractal_count": (
            evidence.complete_neuron_fractal_count
        ),
        "emitted_neuron_fractals": tuple(
            {
                "predecessor_organism_tick": evidence.predecessor_organism_tick,
                "organism_tick": evidence.organism_tick,
                "neuron_lineage": lineage,
                "sparse_retained_delta": entries,
            }
            for lineage, entries in evidence.emitted_neuron_fractals
        ),
        "current_cohort_evaluation_count": (
            evidence.current_cohort_evaluation_count
        ),
        "dsf_delivery_count": evidence.dsf_delivery_count,
        "formation_activation_count": evidence.formation_activation_count,
        "predecessor_organism_tick": evidence.predecessor_organism_tick,
        "organism_tick": evidence.organism_tick,
        "partial_cue_reassembly_count": (
            evidence.partial_cue_reassembly_count
        ),
        "endogenous_partial_cue_reassembly_count": (
            evidence.endogenous_partial_cue_reassembly_count
        ),
        "internally_reassembled_formation_cues": (
            evidence.internally_reassembled_formation_cues
        ),
        "externally_reassembled_formation_frontiers": (
            evidence.externally_reassembled_formation_frontiers
        ),
        "physically_transitioned_neuron_count": (
            evidence.physically_transitioned_neuron_count
        ),
        "metabolically_perturbed_body_receptor_count": (
            evidence.metabolically_perturbed_body_receptor_count
        ),
        "rest_recovered_neuron_count": evidence.rest_recovered_neuron_count,
        "rest_drained_dissipation_quanta": (
            evidence.rest_drained_dissipation_quanta
        ),
        "unmet_dissipation_quanta": evidence.unmet_dissipation_quanta,
        "energy_exhausted": evidence.energy_exhausted,
        "energy_exhausted_interval_count": int(evidence.energy_exhausted),
        "dissipation_capacity_energy_zeptojoules": (
            evidence.dissipation_capacity_energy_zeptojoules
        ),
        "externally_perturbed_body_receptor_count": (
            evidence.externally_perturbed_body_receptor_count
        ),
        "externally_perturbed_neuron_lineages": tuple(
            evidence.externally_perturbed_neuron_lineages
        ),
        "external_participant_action_receipt": (
            external_participant_action_receipt
        ),
        "causal_interval_evidence": _causal_interval_hops(evidence),
        "receptor_ingress_sense_counts": ingress_sense_counts,
        "receptor_ingress_changing_count": (
            evidence.receptor_ingress_changing_count
        ),
        "receptor_ingress_quiescent_count": (
            evidence.receptor_ingress_quiescent_count
        ),
        "motor_unit_recruitments": evidence.motor_unit_recruitments,
        "root_yaw_unit_recruitments": evidence.root_yaw_unit_recruitments,
        "root_translation_unit_recruitments": (
            evidence.root_translation_unit_recruitments
        ),
        "body_effector_bindings": evidence.body_effector_bindings,
        "articulated_body_consequences": (
            evidence.articulated_body_consequences
        ),
        "body_proprioceptive_sources": evidence.body_proprioceptive_sources,
        "body_proprioceptive_source_extents": (
            evidence.body_proprioceptive_source_extents
        ),
        "articulatory_unit_recruitments": (
            evidence.articulatory_unit_recruitments
        ),
        "changed_contact_channel_states": (
            evidence.changed_contact_channel_states
        ),
        "physical_frontier_routes": evidence.physical_frontier_routes,
        "preceding_distinct_physical_frontier_routes": (
            evidence.preceding_distinct_physical_frontier_routes
        ),
        "reached_and_foregone_physical_frontier_routes": (
            evidence.reached_and_foregone_physical_frontier_routes
        ),
        "working_causal_continuations": evidence.working_causal_continuations,
        "settled_working_frontier": evidence.settled_working_frontier,
        "physical_prediction_alternatives": (
            evidence.physical_prediction_alternatives
        ),
        "body_consequence_transfers": evidence.body_consequence_transfers,
        "affective_balance_trajectories": evidence.affective_balance_trajectories,
        "localized_fluid_chemistry": evidence.localized_fluid_chemistry,
        "localized_metabolic_strain_evaluated_body_receptor_lineages": (
            evidence.localized_metabolic_strain_evaluated_body_receptor_lineages
        ),
        "localized_metabolic_strain": evidence.localized_metabolic_strain,
        "organic_mosaic_relations": tuple(
            {
                "predecessor_organism_tick": evidence.predecessor_organism_tick,
                "organism_tick": evidence.organism_tick,
                "formation_receipts": receipts,
                "shared_neuron_lineages": lineages,
                "active_physical_bonds": bonds,
                "structural_relation_sha256": structure_receipt,
                "ordered_physical_paths": ordered_paths,
                "ordered_path_relations": ordered_path_relations,
            }
            for receipts, lineages, bonds, structure_receipt, ordered_paths, ordered_path_relations in (
                evidence.organic_mosaic_relations
            )
        ),
        "recurrent_complete_neuron_fractal_count": (
            evidence.recurrent_complete_neuron_fractal_count
        ),
        "causal_transition_sha256": evidence.causal_transition_sha256,
        "state_sha256": evidence.prepared_state_sha256,
    }


def _commit_one_timeline_hop(
    organism: Any,
    episode: Any,
    maximum_causal_intervals: Any,
    *,
    external_participant_action_receipt: str | None = None,
    purpose: str,
    coexisting: bool = False,
    real_nutrition_intake_zeptojoules: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Commit one authored hop with pending self-pressure composed in place."""

    pressure = organism.in_flight_acoustic_pressure_s16le
    body = organism.in_flight_acoustic_body_s16le
    source_tick = organism.in_flight_acoustic_source_tick
    if (pressure is None) != (body is None) or (pressure is None) != (
        source_tick is None
    ):
        raise RuntimeError("native in-flight acoustic state lost cardinality")

    sources = episode if isinstance(episode, tuple) else (episode,)
    first = sources[0]
    if pressure is None:
        admitted_sources = tuple(
            source.episode if isinstance(source, _AcousticHopPlan) else source
            for source in sources
        )
        admitted_episode = (
            admitted_sources
            if isinstance(episode, tuple)
            else admitted_sources[0]
        )
        feed_kwargs: dict[str, Any] = {}
        if real_nutrition_intake_zeptojoules is not None:
            if coexisting:
                raise RuntimeError(
                    "a feed hop is one temporal trajectory, never coexisting"
                )
            feed_kwargs = {
                "native_advance": (
                    organism.advance_admitted_feed_trajectory_unsealed
                ),
                "native_advance_tail": (real_nutrition_intake_zeptojoules,),
            }
        return (
            _commit_admitted_hop(
                organism,
                admitted_episode,
                maximum_causal_intervals,
                purpose=purpose,
                external_participant_action_receipt=(
                    external_participant_action_receipt
                ),
                coexisting=coexisting,
                **feed_kwargs,
            ),
            None,
        )

    if not isinstance(first, _AcousticHopPlan):
        raise RuntimeError(
            "pending self-pressure reached an intake without raw pre-cochlear custody"
        )
    pressure = bytes(pressure)
    body = bytes(body)
    if len(pressure) % struct.calcsize("<h"):
        raise RuntimeError("native in-flight pressure changed sample width")
    samples = struct.unpack(f"<{len(pressure) // 2}h", pressure)
    rebuilt_first = first.composed_with(samples)
    consumed_sample_count = min(
        len(samples),
        len(first.external_pressure_samples),
    )
    admitted_sources = (rebuilt_first,) + tuple(
        source.episode if isinstance(source, _AcousticHopPlan) else source
        for source in sources[1:]
    )
    admitted_episode = (
        admitted_sources if isinstance(episode, tuple) else admitted_sources[0]
    )
    hop = _commit_admitted_hop(
        organism,
        admitted_episode,
        maximum_causal_intervals,
        purpose=purpose,
        external_participant_action_receipt=(
            external_participant_action_receipt
        ),
        coexisting=coexisting,
        native_advance=organism.advance_in_flight_self_hearing_unsealed,
        # A meal lands even while her own voice is mid-flight: nothing
        # about her moment gates real transferred nutrition. The intake
        # rides the tail only when a feed is genuinely present, so the
        # ordinary self-hearing contract stays byte-identical.
        native_advance_tail=(
            (
                pressure,
                body,
                coexisting,
                consumed_sample_count,
                real_nutrition_intake_zeptojoules,
            )
            if real_nutrition_intake_zeptojoules is not None
            else (
                pressure,
                body,
                coexisting,
                consumed_sample_count,
            )
        ),
    )
    return (
        hop,
        {
            "organism_tick": int(source_tick),
            "pcm_s16le": pressure,
            "pressure_sha256": hashlib.sha256(pressure).hexdigest(),
            "sample_count": consumed_sample_count,
            "remaining_sample_count": len(samples) - consumed_sample_count,
            "sample_rate_hz": COCHLEAR_SAMPLE_RATE_HZ,
        },
    )


def _articulation_candidate_from_hop(
    intervals: tuple[tuple[Any, ...], ...],
    recruitments: tuple[tuple[Any, ...], ...],
) -> tuple[dict[str, Any], bytes] | None:
    """Project one emitted hop without merging it with adjacent lived time."""

    if not intervals or not any(
        any(sample != 0 for sample in interval[1]) for interval in intervals
    ):
        return None
    pressure_pcm = tuple(
        sample for interval in intervals for sample in interval[1]
    )
    body_channels = [array("h") for _ in range(ARTICULATORY_BODY_PORT_COUNT)]
    for interval in intervals:
        pressure = interval[1]
        raw = array("h")
        raw.frombytes(interval[2])
        if sys.byteorder != "little":
            raw.byteswap()
        for channel_index, channel in enumerate(body_channels):
            start = channel_index * len(pressure)
            channel.extend(raw[start : start + len(pressure)])
    body_trajectories = b"".join(channel.tobytes() for channel in body_channels)
    strongest = max(intervals, key=lambda interval: abs(interval[4]))
    pressure_s16le = struct.pack(f"<{len(pressure_pcm)}h", *pressure_pcm)
    return (
        {
            "layer_13_recruitment_count": len(recruitments),
            "recruitments": recruitments,
            "sample_rate_hz": COCHLEAR_SAMPLE_RATE_HZ,
            "pressure_sample_count": len(pressure_pcm),
            "pressure_sha256": hashlib.sha256(pressure_s16le).hexdigest(),
            "peak_transducer_surface_velocity_pcm": strongest[4],
            "glottal_open_samples_at_apex": strongest[5],
            "mouth_area_square_millimetres_at_apex": strongest[6],
            "perioral_area_displacement_square_millimetres": intervals[-1][7],
            "applied_motor_quanta": sum(interval[8] for interval in intervals),
            "stalled_motor_quanta": sum(interval[9] for interval in intervals),
            "relaxation_sample_count": 0,
            "self_hearing_hop_count": 0,
            "self_hearing_transitioned_neuron_count": 0,
            "self_hearing_fractal_count": 0,
            "articulatory_body_port_count": ARTICULATORY_BODY_PORT_COUNT,
            "articulatory_body_nonquiescent_port_count": (
                _articulatory_body_nonquiescent_port_count(
                    body_trajectories,
                    len(pressure_pcm),
                )
            ),
            "articulatory_body_receptor_ingress_count": 0,
            "articulatory_body_perturbed_neuron_count": 0,
            "in_flight_recurrent_articulation_count": 1,
        },
        pressure_s16le,
    )


def _newest_exact_self_heard_articulation(
    candidates: tuple[tuple[dict[str, Any], bytes], ...],
    consumed: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], bytes] | None:
    """Select the newest emitted hop with one exact all-ear return receipt."""

    if not candidates:
        return None
    for candidate, pressure_s16le in reversed(candidates):
        matching = tuple(
            entry
            for entry in consumed
            if entry["pressure_sha256"] == candidate["pressure_sha256"]
            and entry["sample_count"] == candidate["pressure_sample_count"]
            and entry["remaining_sample_count"] == 0
            and entry["receptor_ingress_sound_count"] == EAR_PORT_COUNT
        )
        if len(matching) != 1:
            continue
        match = matching[0]
        return (
            {
                **candidate,
                "self_hearing_hop_count": 1,
                "self_hearing_pressure_sha256": candidate["pressure_sha256"],
                "self_hearing_receptor_ingress_count": EAR_PORT_COUNT,
                "self_hearing_transitioned_neuron_count": match[
                    "coexisting_transitioned_neuron_count"
                ],
                "self_hearing_fractal_count": match[
                    "coexisting_emitted_neuron_fractal_count"
                ],
                "coexisting_transitioned_neuron_count": match[
                    "coexisting_transitioned_neuron_count"
                ],
                "coexisting_emitted_neuron_fractal_count": match[
                    "coexisting_emitted_neuron_fractal_count"
                ],
                "articulatory_body_receptor_ingress_count": (
                    ARTICULATORY_BODY_PORT_COUNT
                ),
            },
            pressure_s16le,
        )
    candidate, pressure_s16le = candidates[-1]
    return (
        {
            **candidate,
            "self_hearing_pressure_sha256": None,
            "self_hearing_receptor_ingress_count": 0,
            "coexisting_transitioned_neuron_count": 0,
            "coexisting_emitted_neuron_fractal_count": 0,
        },
        pressure_s16le,
    )


def _commit_vestibular_trajectory(
    organism: Any,
    predecessor_heading_millidegrees: int,
    signed_body_motion_millidegrees: tuple[int, ...],
) -> dict[str, Any]:
    """Advance every ordered 1 ms vestibular interval inside the lived intake."""

    evidence: ResidentPrepareEvidence = organism.advance_vestibular_trajectory_unsealed(
        predecessor_heading_millidegrees,
        signed_body_motion_millidegrees,
    )
    return {
        "cognitive_mosaic_count": evidence.cognitive_mosaic_count,
        "cognitive_trace_count": evidence.cognitive_trace_count,
        "complete_neuron_count": evidence.complete_neuron_count,
        "developmental_resting_neuron_count": (
            evidence.developmental_resting_neuron_count
        ),
        "complete_neuron_fractal_count": evidence.complete_neuron_fractal_count,
        "emitted_neuron_fractals": tuple(
            {
                "predecessor_organism_tick": evidence.predecessor_organism_tick,
                "organism_tick": evidence.organism_tick,
                "neuron_lineage": lineage,
                "sparse_retained_delta": entries,
            }
            for lineage, entries in evidence.emitted_neuron_fractals
        ),
        "current_cohort_evaluation_count": (
            evidence.current_cohort_evaluation_count
        ),
        "dsf_delivery_count": evidence.dsf_delivery_count,
        "formation_activation_count": evidence.formation_activation_count,
        "predecessor_organism_tick": evidence.predecessor_organism_tick,
        "organism_tick": evidence.organism_tick,
        "partial_cue_reassembly_count": evidence.partial_cue_reassembly_count,
        "endogenous_partial_cue_reassembly_count": (
            evidence.endogenous_partial_cue_reassembly_count
        ),
        "internally_reassembled_formation_cues": (
            evidence.internally_reassembled_formation_cues
        ),
        "physically_transitioned_neuron_count": (
            evidence.physically_transitioned_neuron_count
        ),
        "metabolically_perturbed_body_receptor_count": (
            evidence.metabolically_perturbed_body_receptor_count
        ),
        "rest_recovered_neuron_count": evidence.rest_recovered_neuron_count,
        "rest_drained_dissipation_quanta": (
            evidence.rest_drained_dissipation_quanta
        ),
        "unmet_dissipation_quanta": evidence.unmet_dissipation_quanta,
        "energy_exhausted": evidence.energy_exhausted,
        "energy_exhausted_interval_count": int(evidence.energy_exhausted),
        "dissipation_capacity_energy_zeptojoules": (
            evidence.dissipation_capacity_energy_zeptojoules
        ),
        "externally_perturbed_body_receptor_count": (
            evidence.externally_perturbed_body_receptor_count
        ),
        "causal_interval_evidence": _causal_interval_hops(evidence),
        "motor_unit_recruitments": evidence.motor_unit_recruitments,
        "root_yaw_unit_recruitments": evidence.root_yaw_unit_recruitments,
        "root_translation_unit_recruitments": (
            evidence.root_translation_unit_recruitments
        ),
        "body_effector_bindings": evidence.body_effector_bindings,
        "articulated_body_consequences": (
            evidence.articulated_body_consequences
        ),
        "body_proprioceptive_sources": evidence.body_proprioceptive_sources,
        "body_proprioceptive_source_extents": (
            evidence.body_proprioceptive_source_extents
        ),
        "articulatory_unit_recruitments": (
            evidence.articulatory_unit_recruitments
        ),
        "changed_contact_channel_states": (
            evidence.changed_contact_channel_states
        ),
        "physical_frontier_routes": evidence.physical_frontier_routes,
        "preceding_distinct_physical_frontier_routes": (
            evidence.preceding_distinct_physical_frontier_routes
        ),
        "reached_and_foregone_physical_frontier_routes": (
            evidence.reached_and_foregone_physical_frontier_routes
        ),
        "working_causal_continuations": evidence.working_causal_continuations,
        "settled_working_frontier": evidence.settled_working_frontier,
        "physical_prediction_alternatives": (
            evidence.physical_prediction_alternatives
        ),
        "body_consequence_transfers": evidence.body_consequence_transfers,
        "affective_balance_trajectories": evidence.affective_balance_trajectories,
        "localized_fluid_chemistry": evidence.localized_fluid_chemistry,
        "localized_metabolic_strain_evaluated_body_receptor_lineages": (
            evidence.localized_metabolic_strain_evaluated_body_receptor_lineages
        ),
        "localized_metabolic_strain": evidence.localized_metabolic_strain,
        "organic_mosaic_relations": tuple(
            {
                "predecessor_organism_tick": evidence.predecessor_organism_tick,
                "organism_tick": evidence.organism_tick,
                "formation_receipts": receipts,
                "shared_neuron_lineages": lineages,
                "active_physical_bonds": bonds,
                "structural_relation_sha256": structure_receipt,
                "ordered_physical_paths": ordered_paths,
                "ordered_path_relations": ordered_path_relations,
            }
            for receipts, lineages, bonds, structure_receipt, ordered_paths, ordered_path_relations in (
                evidence.organic_mosaic_relations
            )
        ),
        "recurrent_complete_neuron_fractal_count": (
            evidence.recurrent_complete_neuron_fractal_count
        ),
        "causal_transition_sha256": evidence.causal_transition_sha256,
        "state_sha256": evidence.prepared_state_sha256,
    }


def _advance_bounded_frontier_evidence(
    current: tuple[tuple[Any, ...], ...],
    preceding_distinct: tuple[tuple[Any, ...], ...],
    reached_and_foregone: tuple[tuple[Any, ...], ...],
    hop: dict[str, Any],
) -> tuple[
    tuple[tuple[Any, ...], ...],
    tuple[tuple[Any, ...], ...],
    tuple[tuple[Any, ...], ...],
]:
    """Retain current, preceding, and one bounded reached/foregone witness."""

    next_current = tuple(hop["physical_frontier_routes"])
    within_hop_preceding = tuple(
        hop["preceding_distinct_physical_frontier_routes"]
    )
    if within_hop_preceding != next_current and within_hop_preceding:
        next_preceding = within_hop_preceding
    elif next_current != current:
        next_preceding = current
    else:
        next_preceding = preceding_distinct
    next_reached_and_foregone = reached_and_foregone or tuple(
        hop["reached_and_foregone_physical_frontier_routes"]
    )
    return next_current, next_preceding, next_reached_and_foregone


def _advance_bounded_working_causal_evidence(
    continuation: tuple[tuple[Any, ...], ...],
    settlement: tuple[tuple[Any, ...], ...],
    hop: dict[str, Any],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[tuple[Any, ...], ...]]:
    """Retain one continuation and settlement of that exact continued cause."""

    next_continuation = continuation or tuple(
        hop["working_causal_continuations"]
    )
    next_settlement = settlement
    if next_continuation and not next_settlement:
        continued_transfer = next_continuation[0][1]
        matching = tuple(
            transfer
            for transfer in hop["settled_working_frontier"]
            if transfer == continued_transfer
        )
        if matching:
            next_settlement = matching[:1]
    return next_continuation, next_settlement


def _advance_bounded_prediction_evidence(
    alternatives: tuple[tuple[Any, ...], ...],
    consequence: tuple[tuple[Any, ...], ...],
    hop: dict[str, Any],
) -> tuple[tuple[tuple[Any, ...], ...], tuple[tuple[Any, ...], ...]]:
    """Retain one two-alternative witness and its first later body consequence.

    One native trajectory contains many ordered one-millisecond intervals.  If
    its native evidence carries both the alternatives and a consequence, the
    native producer has already established their temporal order; the Python
    transaction boundary must not flatten that trajectory into one instant and
    discard its consequence.
    """

    prediction_preceded_this_hop = bool(alternatives)
    next_alternatives = alternatives or tuple(
        hop["physical_prediction_alternatives"]
    )
    next_consequence = consequence
    alternatives_ordered_within_hop = (
        len(tuple(hop["physical_prediction_alternatives"])) == 2
    )
    if (
        not next_consequence
        and (prediction_preceded_this_hop or alternatives_ordered_within_hop)
    ):
        next_consequence = tuple(hop["body_consequence_transfers"])[:1]
    return next_alternatives, next_consequence


def _exact_contact_state_participation(change: Any) -> bool:
    """Validate one exact active-contact state change in this causal path.

    The native boundary has already authenticated the stable contact identity,
    predecessor, and successor.  A changed transition-work phase is current
    physical participation, even when a mature contact's conducting population
    remains stable.  This observer does not call participation reinforcement or
    learning; an exactly unchanged contact remains insufficient.
    """

    if not isinstance(change, dict):
        return False
    predecessor = change.get("predecessor_state")
    successor = change.get("successor_state")
    if (
        not isinstance(predecessor, (list, tuple))
        or len(predecessor) != 3
        or not isinstance(successor, (list, tuple))
        or len(successor) != 3
        or predecessor == successor
    ):
        return False
    return True


def _retained_local_plasticity(plasticity: Any) -> bool:
    """Validate one bounded native local-fluid/plastic return observation."""

    if not isinstance(plasticity, (list, tuple)) or len(plasticity) != 10:
        return False
    (
        ordinal,
        incident_catalyst,
        reaction_extent,
        delivered,
        _predecessor_residue,
        _successor_residue,
        predecessor_rest,
        successor_rest,
        predecessor_reservoir,
        successor_reservoir,
    ) = plasticity
    def positive_count(value: Any) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        ) or (
            isinstance(value, str)
            and value.isdigit()
            and int(value) > 0
        )

    if (
        not isinstance(ordinal, int)
        or ordinal < 0
        or not positive_count(incident_catalyst)
        or not positive_count(reaction_extent)
        or predecessor_rest == successor_rest
    ):
        return False

    def exact(value: Any) -> Fraction | None:
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 2
            or not isinstance(value[0], int)
            or not isinstance(value[1], int)
            or value[1] <= 0
        ):
            return None
        return Fraction(value[0], value[1])

    if (
        not isinstance(predecessor_reservoir, (list, tuple))
        or len(predecessor_reservoir) != 3
        or not isinstance(successor_reservoir, (list, tuple))
        or len(successor_reservoir) != 3
    ):
        return False
    delivered_energy = exact(delivered)
    predecessor = tuple(exact(value) for value in predecessor_reservoir)
    successor = tuple(exact(value) for value in successor_reservoir)
    return (
        delivered_energy is not None
        and delivered_energy > 0
        and len(predecessor) == 3
        and len(successor) == 3
        and all(value is not None for value in predecessor + successor)
        and predecessor[0] - successor[0] == delivered_energy
        and successor[1] - predecessor[1] == delivered_energy
        and predecessor[2] == successor[2]
    )


def _advance_bounded_affective_balance_evidence(
    retained: tuple[tuple[Any, ...], ...],
    hop: dict[str, Any],
) -> tuple[tuple[Any, ...], ...]:
    """Merge one bounded physical trajectory per exact layer-10 lineage."""

    by_lineage = {entry[0]: entry for entry in retained}
    for observed in tuple(hop["affective_balance_trajectories"]):
        if not isinstance(observed, (list, tuple)) or len(observed) != 7:
            continue
        lineage, layer, topology, association, body, gradient, plasticity = observed
        prior = by_lineage.get(lineage)
        if prior is not None:
            (
                _,
                prior_layer,
                prior_topology,
                prior_association,
                prior_body,
                prior_gradient,
                prior_plasticity,
            ) = prior
            if (layer, topology) != (prior_layer, prior_topology):
                raise RuntimeError("affective-balance lineage changed physical place")
            association = prior_association or association
            body = prior_body or body
            gradient = prior_gradient or gradient
            if not _retained_local_plasticity(plasticity):
                plasticity = prior_plasticity
        influence_ordinal = (
            max(association[0], body[0])
            if association is not None and body is not None
            else None
        )
        if (
            gradient is not None
            and influence_ordinal is not None
            and gradient[0] <= influence_ordinal
        ):
            gradient = None
        observed_gradient = observed[5]
        if (
            gradient is None
            and observed_gradient is not None
            and (
                influence_ordinal is None
                or observed_gradient[0] > influence_ordinal
            )
        ):
            gradient = observed_gradient
        observed_plasticity = observed[6]
        if (
            not _retained_local_plasticity(plasticity)
            and _retained_local_plasticity(observed_plasticity)
        ):
            plasticity = observed_plasticity
        by_lineage[lineage] = (
            lineage,
            layer,
            topology,
            association,
            body,
            gradient,
            plasticity,
        )
    return tuple(by_lineage[lineage] for lineage in sorted(by_lineage))


def _advance_bounded_localized_fluid_chemistry_evidence(
    retained: tuple[tuple[Any, ...], ...],
    hop: dict[str, Any],
) -> tuple[tuple[Any, ...], ...]:
    """Retain at most one local settlement, preferring a locality witness."""

    if (
        retained
        and retained[0][4][4] + retained[0][4][5] > 0
        and retained[0][4][6] == 0
    ):
        return retained
    observed = tuple(hop["localized_fluid_chemistry"])
    witness = next(
        (
            settlement
            for settlement in observed
            if settlement[4][4] + settlement[4][5] > 0
            and settlement[4][6] == 0
        ),
        observed[0] if observed else None,
    )
    return (witness,) if witness is not None else retained


def _advance_bounded_localized_metabolic_strain_evidence(
    evaluated_lineages: tuple[str, ...],
    retained: tuple[tuple[Any, ...], ...],
    hop: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[tuple[Any, ...], ...]]:
    """Keep only each evaluated body receptor's latest exact local state."""

    observed_evaluated = tuple(
        hop["localized_metabolic_strain_evaluated_body_receptor_lineages"]
    )
    by_lineage = {entry[0]: entry for entry in retained}
    observed_by_lineage = {
        entry[0]: entry for entry in tuple(hop["localized_metabolic_strain"])
    }
    for lineage in observed_evaluated:
        by_lineage.pop(lineage, None)
        if lineage in observed_by_lineage:
            by_lineage[lineage] = observed_by_lineage[lineage]
    return (
        tuple(sorted(set(evaluated_lineages).union(observed_evaluated))),
        tuple(by_lineage[lineage] for lineage in sorted(by_lineage)),
    )


def _complete_local_affective_balance_trajectory(trajectory: Any) -> bool:
    """Recognize the one ratified native ordering without adding authority."""

    if not isinstance(trajectory, (list, tuple)) or len(trajectory) != 7:
        return False
    lineage, layer, _topology, association, body, gradient, _plasticity = trajectory
    return (
        layer == 10
        and isinstance(lineage, str)
        and isinstance(association, (list, tuple))
        and isinstance(body, (list, tuple))
        and isinstance(gradient, (list, tuple))
        and len(association) == 2
        and len(body) == 2
        and len(gradient) == 10
        and gradient[0] > max(association[0], body[0])
    )


def _retain_external_participant_path_witness(
    witness: dict[str, Any],
    active: dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
) -> None:
    """Retain only the latest reached participant frontier for this transaction."""

    candidates = tuple(
        (key, paths)
        for key, paths in active.items()
        if key[0] == "external_participant_sensory" and paths
    )
    if not candidates:
        return
    key, paths = min(candidates, key=lambda item: item[0][1:])
    _kind, action_receipt, origin_lineages, origin_tick = key
    witness.clear()
    witness.update({
        "participant_action_causal_intent_receipt_sha256": action_receipt,
        "origin_lineages": origin_lineages,
        "origin_organism_tick": origin_tick,
        "paths": tuple(
            (lineage, tuple(paths[lineage])) for lineage in sorted(paths)
        ),
    })


def _external_participant_attention_from_path_witness(
    witness: dict[str, Any],
    hop: dict[str, Any],
) -> dict[str, Any] | None:
    """Bind participant-caused transport to her native sparse attention event."""

    observation = _qualifying_sparse_attention_routes(hop)
    if observation is None or not witness:
        return None
    qualifying_phase, routes, _current, _preceding = observation
    transported: dict[tuple[str, str, int, int], tuple[Any, ...]] = {}
    for route in routes:
        if len(route) != 8:
            return None
        signed_carriers = int(route[7])
        if signed_carriers > 0:
            transfer = (str(route[0]), str(route[3]), int(route[6]), signed_carriers)
        elif signed_carriers < 0:
            transfer = (str(route[3]), str(route[0]), int(route[6]), -signed_carriers)
        else:
            continue
        transported[transfer] = tuple(route)
    matches: list[
        tuple[
            int,
            tuple[tuple[str, str, int, int], ...],
            tuple[str, str, int, int],
            tuple[Any, ...],
        ]
    ] = []
    for _frontier_lineage, raw_path in tuple(witness.get("paths", ())):
        path = tuple(raw_path)
        for index, transfer in enumerate(path):
            route = transported.get(tuple(transfer))
            if route is not None:
                matches.append((index + 1, path, tuple(transfer), route))
    if not matches:
        return None
    path_extent, path, matched_transfer, matched_route = min(
        matches,
        key=lambda item: (item[0], item[1], item[2]),
    )
    attention = _sparse_attention_route_facts(hop)
    if attention is None:
        return None
    return {
        "origin_kind": "external_participant_sensory",
        "participant_action_causal_intent_receipt_sha256": witness[
            "participant_action_causal_intent_receipt_sha256"
        ],
        "perturbed_receptor_lineages": witness["origin_lineages"],
        "receptor_settlement_organism_tick": witness["origin_organism_tick"],
        "attention_organism_tick": int(hop["organism_tick"]),
        "attention": attention,
        "attention_qualifying_phase": qualifying_phase,
        "directed_physical_transfers": path[:path_extent],
        "matched_attention_transfer": matched_transfer,
        "matched_attention_route": matched_route,
    }


def _changed_contact_on_causal_path(
    path: tuple[tuple[str, str, int, int], ...],
    changed_by_bond: dict[
        tuple[str, str, int], tuple[int, tuple[Any, ...]]
    ],
    before_tick: int,
) -> dict[str, Any] | None:
    matches = []
    for first, second, path_ordinal, _carriers in path:
        left, right = sorted((first, second))
        observed = changed_by_bond.get((left, right, path_ordinal))
        if observed is not None and observed[0] < before_tick:
            matches.append(observed)
    if not matches:
        return None
    changed_tick, changed_state = min(matches)
    return {
        "change_organism_tick": changed_tick,
        "contact_cognitive_ordinal": changed_state[0],
        "left_lineage": changed_state[1],
        "right_lineage": changed_state[2],
        "parallel_ordinal": changed_state[3],
        "predecessor_state": changed_state[4],
        "successor_state": changed_state[5],
    }


def _compact_retained_motor_path(proof: dict[str, Any]) -> dict[str, Any]:
    """Drop the complete motor-preparation fanout from one passive proof."""

    recruitment = proof["motor_unit_recruitment"]
    projected = {
        key: proof[key]
        for key in (
            "origin_kind",
            "origin_lineages",
            "origin_organism_tick",
            "motor_organism_tick",
            "directed_physical_transfers",
            "formation_receipt_sha256",
            "internal_cue_lineages",
            "recurrence_organism_tick",
            "recurrent_lineage",
            "external_cue_lineages",
            "reassembly_organism_tick",
            "changed_contact_channel_state",
        )
        if key in proof
    }
    projected["motor_unit_recruitment"] = {
        key: recruitment[key]
        for key in (
            "motor_lineage",
            "motor_layer",
            "motor_topology_index",
            "outward_elementary_carriers",
            "body_afferent_paths",
        )
        if key in recruitment
    }
    return projected


def _thought_transitions_on_completed_motor_path(
    proof: dict[str, Any] | None,
    hops: tuple[tuple[dict[str, Any], tuple[tuple[Any, ...], ...]], ...],
) -> tuple[tuple[Any, ...], ...]:
    """Retain only native thought arrivals used by one completed motor path.

    The motor proof can complete several causal intervals after its thought
    arrival. The latest consequence hop therefore cannot be the authority for
    whether that earlier arrival occurred. This projection reads the already
    committed transient interval observations and carries only transitions
    whose destination formation and exact carrier transfer are on the completed
    path. It neither reads resident cognition nor creates a causal edge.
    """

    if proof is None:
        return ()
    receipt = proof.get("formation_receipt_sha256")
    if not isinstance(receipt, str):
        return ()
    path_transfers = {
        tuple(transfer)
        for transfer in proof.get("directed_physical_transfers", ())
        if isinstance(transfer, (list, tuple)) and len(transfer) == 4
    }
    matched: set[tuple[Any, ...]] = set()
    for hop, _affective in hops:
        for interval in hop.get("causal_interval_evidence", ()):
            if not isinstance(interval, dict):
                raise RuntimeError("causal interval observation changed format")
            for transition in interval.get("causal_thought_transitions", ()):
                if not isinstance(transition, (list, tuple)) or len(transition) != 5:
                    raise RuntimeError("causal thought observation changed format")
                transfer = transition[4]
                if not isinstance(transfer, (list, tuple)) or len(transfer) != 4:
                    raise RuntimeError("causal thought transfer changed format")
                canonical = (*transition[:4], tuple(transfer))
                if canonical[1] == receipt and canonical[4] in path_transfers:
                    matched.add(canonical)
    return tuple(sorted(matched))


def _advance_causal_motor_traces(
    committed_frontier: tuple[tuple[str, str, int, int, str], ...] | None,
    active: dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    completed: dict[str, Any],
    hop: dict[str, Any],
    transaction_affective_balance_trajectories: tuple[
        tuple[Any, ...], ...
    ] | None = None,
    external_participant_action_receipt: str | None = None,
    participant_path_witness: dict[str, Any] | None = None,
) -> tuple[
    dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    dict[str, Any],
]:
    """Follow exact changed endpoints from physical causes to later motor discharge.

    A one-seal native trajectory may carry its exact ordered transient interval
    observations; those are consumed in order and never persisted. An aggregate
    without those boundaries is still refused. The optional first argument is
    committed frontier data for isolated legacy proof callers, never an organism
    or native callback. Neither a retained formation, a new neuronal impression,
    nor an affective trajectory becomes settlement authority: this observer
    follows only whole-carrier transfers already present in each committed native
    active frontier.
    """

    if external_participant_action_receipt is None:
        external_participant_action_receipt = hop.get(
            "external_participant_action_receipt"
        )
    if participant_path_witness is None:
        participant_path_witness = {}
    causal_intervals = tuple(hop.get("causal_interval_evidence", ()))
    if causal_intervals:
        next_active = active
        next_completed = completed
        for interval in causal_intervals:
            next_active, next_completed = _advance_causal_motor_traces(
                None,
                next_active,
                next_completed,
                interval,
                transaction_affective_balance_trajectories,
                external_participant_action_receipt,
                participant_path_witness,
            )
        participant_attention = _external_participant_attention_from_path_witness(
            participant_path_witness,
            hop,
        )
        if participant_attention is not None:
            next_completed["external_participant_attention"] = (
                participant_attention
            )
        return next_active, next_completed
    origin_kinds = (
        "retained_formation",
        "externally_reassembled_retained_formation",
        "new_neuronal_fractal",
        "affective_gradient",
        "external_participant_sensory",
    )
    predecessor_tick = int(hop["predecessor_organism_tick"])
    organism_tick = int(hop["organism_tick"])
    if organism_tick != predecessor_tick + 1:
        return {}, completed
    active = {
        key: active[key]
        for key in sorted(active)
        if _causal_motor_trace_may_complete_in_native_interval(
            key,
            organism_tick,
        )
    }
    prior_changed = completed.get("_changed_contact_channel_states", {})
    changed_by_bond = {
        tuple(entry[1:4]): (int(observed_tick), tuple(entry))
        for observed_tick, entry in prior_changed.get("entries", ())
    }
    for change in tuple(hop.get("changed_contact_channel_states", ())):
        if not isinstance(change, (list, tuple)) or len(change) != 6:
            raise RuntimeError("changed contact-channel hop evidence changed format")
        bond = tuple(change[1:4])
        changed_by_bond.setdefault(bond, (organism_tick, tuple(change)))
    external_motor_paths_by_recurrent = dict(
        completed.get(_COMPLETED_EXTERNAL_MOTOR_PATHS_BY_RECURRENT, {})
    )
    articulation_completed_origins = set(
        completed.get(_COMPLETED_ARTICULATION_ORIGINS, ())
    )
    retained_articulation_kinds = {
        "retained_formation",
        "externally_reassembled_retained_formation",
    }
    next_active = {
        key: paths
        for key, paths in active.items()
        if (
            key[0] in retained_articulation_kinds
            and key not in articulation_completed_origins
        )
        or (key[0] not in retained_articulation_kinds and key[0] not in completed)
    }
    new_thought_origins: dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ] = {}
    if "retained_formation" not in completed:
        for receipt, cue_lineages, recurrent_lineage in hop[
            "internally_reassembled_formation_cues"
        ]:
            cues = tuple(cue_lineages)
            key = ("retained_formation", receipt, cues, organism_tick)
            thought_arrivals = tuple(
                transition
                for transition in hop.get("causal_thought_transitions", ())
                if transition[1] == receipt and transition[3] in cues
            )
            if thought_arrivals:
                # A formation-to-formation thought physically arrives at the
                # destination member, not at the destination's recurrent
                # cell. Continue the committed carrier wave from that exact
                # member and retain its already-observed incoming transfer as
                # the first causal edge. Restarting at `recurrent_lineage`
                # would discard the thought and silently wait for a different
                # cause. This is observation after commit; it moves no charge
                # and grants no action authority.
                paths = next_active.setdefault(key, {})
                for transition in thought_arrivals:
                    cue_lineage = transition[3]
                    candidate = (transition[4],)
                    existing = paths.get(cue_lineage)
                    if existing is None or candidate < existing:
                        paths[cue_lineage] = candidate
                new_thought_origins[key] = dict(paths)
            elif recurrent_lineage is not None:
                next_active.setdefault(key, {recurrent_lineage: ()})
    if next_active:
        reached_lineages = tuple(
            sorted(
                {
                    lineage
                    for paths in next_active.values()
                    for lineage in paths
                }
            )
        )
        observed_interval_frontier = hop.get("causal_frontier_advances")
        if observed_interval_frontier is None:
            if committed_frontier is None:
                raise RuntimeError(
                    "committed causal frontier is absent; observation cannot "
                    "read resident cognition"
                )
            observed_interval_frontier = tuple(committed_frontier)
        reached = set(reached_lineages)
        transfers = tuple(
            transfer
            for transfer in observed_interval_frontier
            if (
                transfer[1]
                if transfer[4] == transfer[0]
                else transfer[0]
            )
            in reached
        )
    else:
        transfers = ()
    advanced: dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ] = {}
    for key, paths_by_lineage in next_active.items():
        origin_kind, _origin_receipt, origin_lineages, _origin_tick = key
        next_paths: dict[str, tuple[tuple[str, str, int, int], ...]] = {}
        for observed in transfers:
            sender, receiver, ordinal, carriers, frontier = observed
            transfer = (sender, receiver, ordinal, carriers)
            predecessor = receiver if frontier == sender else sender
            if predecessor not in paths_by_lineage:
                continue
            prior_path = paths_by_lineage[predecessor]
            candidate = prior_path + (transfer,)
            existing = next_paths.get(frontier)
            if existing is None or (len(candidate), candidate) < (
                len(existing),
                existing,
            ):
                next_paths[frontier] = candidate
        # External recognition begins at the exact externally perturbed cue,
        # not at a recurrent cell the cue has not yet reached. Once one path
        # physically arrives at that formation's retained recurrent endpoint,
        # collapse to that exact path; all later motor or articulation proof
        # must carry the recurrence crossing in its transfer chain.
        if (
            origin_kind == "externally_reassembled_retained_formation"
            and origin_lineages
        ):
            recurrent_lineage = origin_lineages[0]
            if recurrent_lineage in next_paths:
                next_paths = {
                    recurrent_lineage: next_paths[recurrent_lineage]
                }
        if next_paths:
            advanced[key] = next_paths
    if "retained_formation" not in completed:
        for receipt, cue_lineages, recurrent_lineage in hop[
            "internally_reassembled_formation_cues"
        ]:
            if recurrent_lineage is None:
                continue
            cues = tuple(cue_lineages)
            recurrent_returns = tuple(
                (sender, receiver, ordinal, carriers)
                for sender, receiver, ordinal, carriers, frontier in (
                    observed_interval_frontier
                )
                if frontier == recurrent_lineage
                and (
                    (sender == recurrent_lineage and receiver in cues)
                    or (receiver == recurrent_lineage and sender in cues)
                )
            )
            if not recurrent_returns:
                continue
            key = ("retained_formation", receipt, cues, organism_tick)
            advanced.setdefault(key, {}).setdefault(
                recurrent_lineage,
                (min(recurrent_returns),),
            )
    for key, paths in new_thought_origins.items():
        # New causes are retained for the adjacent interval just like emitted
        # fractals and external receptor arrivals below. They have already
        # occurred in this interval; absence of a second edge in the same
        # clock is not authority to erase their physical arrival.
        advanced.setdefault(key, paths)
    proofs: dict[
        str,
        list[
            tuple[
                tuple[str, str, tuple[str, ...], int],
                dict[str, Any],
            ]
        ],
    ] = {
        kind: []
        for kind in origin_kinds
        if kind in _MULTI_PATH_CAUSAL_TRACE_KINDS or kind not in completed
    }
    retained_articulation_proofs: dict[
        str,
        list[
            tuple[
                tuple[str, str, tuple[str, ...], int],
                dict[str, Any],
            ]
        ],
    ] = {
        "retained_formation": [],
        "externally_reassembled_retained_formation": [],
    }
    observed_affective_trajectories = tuple(
        transaction_affective_balance_trajectories
        if transaction_affective_balance_trajectories is not None
        else hop.get("affective_balance_trajectories", ())
    )
    affective_trajectory_by_receipt = {
        _receipt(tuple(trajectory)): trajectory
        for trajectory in observed_affective_trajectories
        if _complete_local_affective_balance_trajectory(trajectory)
    }
    for origin_key, paths_by_lineage in next_active.items():
        (
            origin_kind,
            origin_receipt,
            origin_lineages,
            origin_tick,
        ) = origin_key
        if organism_tick <= origin_tick:
            continue
        for recruitment in (
            ()
            if origin_kind == "externally_reassembled_retained_formation"
            and origin_lineages[0] in external_motor_paths_by_recurrent
            else hop["motor_unit_recruitments"]
        ):
            (
                motor_lineage,
                topology_index,
                outward_carriers,
                preparation,
                body_afferent_paths,
            ) = recruitment
            for (
                sender,
                sender_layer,
                receiver,
                receiver_layer,
                ordinal,
                carriers,
            ) in preparation:
                if sender == motor_lineage and sender_layer == 12 and receiver_layer == 11:
                    predecessor = receiver
                elif receiver == motor_lineage and receiver_layer == 12 and sender_layer == 11:
                    predecessor = sender
                else:
                    continue
                prior_path = paths_by_lineage.get(predecessor)
                if prior_path is None:
                    continue
                if (
                    origin_kind
                    == "externally_reassembled_retained_formation"
                    and not any(
                        origin_lineages[0] in transfer[:2]
                        for transfer in prior_path
                    )
                ):
                    continue
                motor_transfer = (sender, receiver, ordinal, carriers)
                if motor_transfer in prior_path:
                    continue
                proof = {
                    "origin_kind": origin_kind,
                    "origin_lineages": origin_lineages,
                    "origin_organism_tick": origin_tick,
                    "motor_organism_tick": organism_tick,
                    "directed_physical_transfers": prior_path
                    + (motor_transfer,),
                    "motor_unit_recruitment": {
                        "motor_lineage": motor_lineage,
                        "motor_layer": 12,
                        "motor_topology_index": topology_index,
                        "outward_elementary_carriers": outward_carriers,
                        "body_afferent_paths": body_afferent_paths,
                    },
                }
                changed_contact = _changed_contact_on_causal_path(
                    proof["directed_physical_transfers"],
                    changed_by_bond,
                    organism_tick,
                )
                if changed_contact is not None:
                    proof["changed_contact_channel_state"] = changed_contact
                if origin_kind == "retained_formation":
                    proof["motor_unit_recruitment"][
                        "preparation_transfers"
                    ] = preparation
                    proof.update(
                        formation_receipt_sha256=origin_receipt,
                        internal_cue_lineages=origin_lineages,
                        recurrence_organism_tick=origin_tick,
                    )
                elif origin_kind == "externally_reassembled_retained_formation":
                    proof["motor_unit_recruitment"][
                        "preparation_transfers"
                    ] = preparation
                    proof.update(
                        formation_receipt_sha256=origin_receipt,
                        recurrent_lineage=origin_lineages[0],
                        external_cue_lineages=origin_lineages[1:],
                        reassembly_organism_tick=origin_tick,
                    )
                elif origin_kind == "affective_gradient":
                    affective_trajectory = affective_trajectory_by_receipt.get(
                        origin_receipt
                    )
                    if affective_trajectory is None:
                        continue
                    proof["motor_unit_recruitment"][
                        "matched_preparation_transfer"
                    ] = (
                        sender,
                        sender_layer,
                        receiver,
                        receiver_layer,
                        ordinal,
                        carriers,
                    )
                    proof.update(
                        affective_neuron_lineage=origin_lineages[0],
                        affective_trajectory_receipt_sha256=origin_receipt,
                        localized_gradient_settlement_organism_tick=(
                            affective_trajectory[5][0]
                        ),
                    )
                    if isinstance(affective_trajectory[6], (list, tuple)):
                        proof[
                            "localized_recovery_settlement_organism_tick"
                        ] = affective_trajectory[6][0]
                elif origin_kind == "external_participant_sensory":
                    proof["motor_unit_recruitment"][
                        "matched_preparation_transfer"
                    ] = (
                        sender,
                        sender_layer,
                        receiver,
                        receiver_layer,
                        ordinal,
                        carriers,
                    )
                    proof.update(
                        participant_action_causal_intent_receipt_sha256=(
                            origin_receipt
                        ),
                        perturbed_receptor_lineages=origin_lineages,
                        receptor_settlement_organism_tick=origin_tick,
                    )
                else:
                    proof["motor_unit_recruitment"][
                        "matched_preparation_transfer"
                    ] = (
                        sender,
                        sender_layer,
                        receiver,
                        receiver_layer,
                        ordinal,
                        carriers,
                    )
                    proof.update(
                        emitted_neuron_lineages=origin_lineages,
                        impression_organism_tick=origin_tick,
                    )
                proofs[origin_kind].append((origin_key, proof))
        articulation_completion_kind = (
            f"{origin_kind}_articulation"
            if origin_kind in retained_articulation_proofs
            else None
        )
        if (
            articulation_completion_kind is not None
            and origin_key not in articulation_completed_origins
        ):
            for recruitment in tuple(
                hop.get("articulatory_unit_recruitments", ())
            ):
                (
                    articulatory_lineage,
                    topology_index,
                    outward_carriers,
                    preparation,
                ) = recruitment
                for (
                    sender,
                    sender_layer,
                    receiver,
                    receiver_layer,
                    ordinal,
                    carriers,
                ) in preparation:
                    if (
                        sender == articulatory_lineage
                        and sender_layer == 13
                        and receiver_layer == 12
                    ):
                        predecessor = receiver
                    elif (
                        receiver == articulatory_lineage
                        and receiver_layer == 13
                        and sender_layer == 12
                    ):
                        predecessor = sender
                    else:
                        continue
                    prior_path = paths_by_lineage.get(predecessor)
                    if prior_path is None:
                        continue
                    if (
                        origin_kind
                        == "externally_reassembled_retained_formation"
                        and not any(
                            origin_lineages[0] in transfer[:2]
                            for transfer in prior_path
                        )
                    ):
                        continue
                    articulatory_transfer = (
                        sender,
                        receiver,
                        ordinal,
                        carriers,
                    )
                    if articulatory_transfer in prior_path:
                        continue
                    proof = {
                        "origin_kind": origin_kind,
                        "origin_lineages": origin_lineages,
                        "origin_organism_tick": origin_tick,
                        "formation_receipt_sha256": origin_receipt,
                        "articulation_organism_tick": organism_tick,
                        "directed_physical_transfers": prior_path
                        + (articulatory_transfer,),
                        "articulatory_unit_recruitment": {
                            "articulatory_lineage": articulatory_lineage,
                            "articulatory_layer": 13,
                            "articulatory_topology_index": topology_index,
                            "outward_elementary_carriers": outward_carriers,
                            "matched_preparation_transfer": (
                                sender,
                                sender_layer,
                                receiver,
                                receiver_layer,
                                ordinal,
                                carriers,
                            ),
                        },
                    }
                    if origin_kind == "retained_formation":
                        proof.update(
                            internal_cue_lineages=origin_lineages,
                            recurrence_organism_tick=origin_tick,
                        )
                    else:
                        proof.update(
                            recurrent_lineage=origin_lineages[0],
                            external_cue_lineages=origin_lineages[1:],
                            reassembly_organism_tick=origin_tick,
                        )
                    changed_contact = _changed_contact_on_causal_path(
                        proof["directed_physical_transfers"],
                        changed_by_bond,
                        organism_tick,
                    )
                    if changed_contact is not None:
                        proof["changed_contact_channel_state"] = changed_contact
                    retained_articulation_proofs[origin_kind].append(
                        (origin_key, proof)
                    )
    next_completed = dict(completed)
    if changed_by_bond:
        next_completed["_changed_contact_channel_states"] = {
            "entries": tuple(
                changed_by_bond[bond] for bond in sorted(changed_by_bond)
            )
        }

    def proof_order(item: dict[str, Any]) -> tuple[object, ...]:
        return (
            0 if "changed_contact_channel_state" in item else 1,
            len(item["directed_physical_transfers"]),
            item["directed_physical_transfers"],
            item["origin_lineages"],
            item["origin_organism_tick"],
        )

    for origin_kind, candidates in proofs.items():
        selected: dict[
            tuple[str, str, tuple[str, ...], int], dict[str, Any]
        ] = {}
        for origin_key, proof in candidates:
            prior = selected.get(origin_key)
            if prior is None or proof_order(proof) < proof_order(prior):
                selected[origin_key] = proof
        if origin_kind == "externally_reassembled_retained_formation":
            for proof in selected.values():
                recurrent_lineage = proof["recurrent_lineage"]
                prior = external_motor_paths_by_recurrent.get(
                    recurrent_lineage
                )
                compact = _compact_retained_motor_path(proof)
                if prior is None or proof_order(compact) < proof_order(prior):
                    external_motor_paths_by_recurrent[recurrent_lineage] = compact
        if selected and origin_kind not in next_completed:
            next_completed[origin_kind] = min(
                selected.values(),
                key=proof_order,
            )
    for origin_kind, candidates in retained_articulation_proofs.items():
        selected = {}
        for origin_key, proof in candidates:
            prior = selected.get(origin_key)
            if prior is None or proof_order(proof) < proof_order(prior):
                selected[origin_key] = proof
        articulation_completed_origins.update(selected)
        if selected and f"{origin_kind}_articulation" not in next_completed:
            next_completed[f"{origin_kind}_articulation"] = min(
                selected.values(),
                key=proof_order,
            )
    if external_motor_paths_by_recurrent:
        next_completed[_COMPLETED_EXTERNAL_MOTOR_PATHS_BY_RECURRENT] = (
            external_motor_paths_by_recurrent
        )
    if articulation_completed_origins:
        next_completed[_COMPLETED_ARTICULATION_ORIGINS] = tuple(
            sorted(articulation_completed_origins)
        )
    for receipt, cue_lineages, recurrent_lineage in hop.get(
        "externally_reassembled_formation_frontiers", ()
    ):
        if recurrent_lineage in external_motor_paths_by_recurrent:
            continue
        cues = tuple(cue_lineages)
        key = (
            "externally_reassembled_retained_formation",
            receipt,
            (recurrent_lineage, *cues),
            organism_tick,
        )
        advanced.setdefault(key, {cue: () for cue in cues})
    if "new_neuronal_fractal" not in next_completed:
        emitted = tuple(
            sorted(
                {
                    str(fractal["neuron_lineage"])
                    for fractal in hop.get("emitted_neuron_fractals", ())
                }
            )
        )
        if emitted:
            key = ("new_neuronal_fractal", "", emitted, organism_tick)
            advanced.setdefault(key, {lineage: () for lineage in emitted})
    if "affective_gradient" not in next_completed:
        for trajectory in tuple(
            transaction_affective_balance_trajectories
            if transaction_affective_balance_trajectories is not None
            else hop.get("affective_balance_trajectories", ())
        ):
            if not _complete_local_affective_balance_trajectory(trajectory):
                continue
            (
                lineage,
                layer,
                _topology,
                association,
                body,
                gradient,
                plasticity,
            ) = trajectory
            if gradient[0] != organism_tick:
                continue
            key = (
                "affective_gradient",
                _receipt(tuple(trajectory)),
                (lineage,),
                organism_tick,
            )
            advanced.setdefault(key, {lineage: ()})
    if (
        "external_participant_sensory" not in next_completed
        and external_participant_action_receipt is not None
        and not any(
            key[0] == "external_participant_sensory" for key in advanced
        )
    ):
        perturbed = tuple(
            sorted(set(hop.get("externally_perturbed_neuron_lineages", ())))
        )
        if perturbed:
            key = (
                "external_participant_sensory",
                external_participant_action_receipt,
                perturbed,
                organism_tick,
            )
            advanced[key] = {lineage: () for lineage in perturbed}
    _retain_external_participant_path_witness(
        participant_path_witness,
        {**next_active, **advanced},
    )
    participant_attention = _external_participant_attention_from_path_witness(
        participant_path_witness,
        hop,
    )
    if participant_attention is not None:
        next_completed["external_participant_attention"] = participant_attention
    return advanced, next_completed


def _causal_motor_trace_native_interval_age(
    key: tuple[str, str, tuple[str, ...], int],
    current_organism_tick: int,
) -> int:
    """Return exact native intervals elapsed from one transient origin."""

    origin_organism_tick = int(key[3])
    native_interval_age = int(current_organism_tick) - origin_organism_tick
    if native_interval_age < 0:
        # A future-stamped origin can never be witnessed by this or any
        # later backward-looking frontier window: it is incoherent
        # transient evidence, not lived cause. Answer both retention
        # predicates with "expired" so the ordinary drop path removes it.
        # The previous hard abort wedged the organism permanently: from
        # 2026-08-31 ~09:57Z every unattended interval on production
        # refused in a loop on exactly this raise, freezing lived time at
        # tick 366,951 for days while dashboards read healthy. Dropping
        # transient observer evidence cannot reject or roll back lived
        # cognition (the surrounding functions' own doctrine).
        return _CAUSAL_MOTOR_TRACE_RETAINED_FRONTIERS + 2
    return native_interval_age


def _causal_motor_trace_may_complete_in_native_interval(
    key: tuple[str, str, tuple[str, ...], int],
    current_organism_tick: int,
) -> bool:
    """Allow three predecessor frontiers to meet the current interval."""

    return _causal_motor_trace_native_interval_age(
        key,
        current_organism_tick,
    ) <= (_CAUSAL_MOTOR_TRACE_RETAINED_FRONTIERS + 1)


def _causal_motor_trace_may_cross_intake(
    key: tuple[str, str, tuple[str, ...], int],
    current_organism_tick: int,
) -> bool:
    """Carry an origin only if the next interval can still witness it."""

    return _causal_motor_trace_native_interval_age(
        key,
        current_organism_tick,
    ) <= _CAUSAL_MOTOR_TRACE_RETAINED_FRONTIERS


def _retain_cross_intake_causal_motor_traces(
    active: dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    current_organism_tick: int,
) -> dict[
    tuple[str, str, tuple[str, ...], int],
    dict[str, tuple[tuple[str, str, int, int], ...]],
]:
    """Retain only causes still witnessable by the native frontier window."""

    return {
        key: active[key]
        for key in sorted(active)
        if key[0] in _CROSS_INTAKE_CAUSAL_TRACE_KINDS
        and _causal_motor_trace_may_cross_intake(
            key,
            current_organism_tick,
        )
    }


def _derive_causal_motor_observation_after_publication(
    prior_active: dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    hops: tuple[tuple[dict[str, Any], tuple[tuple[Any, ...], ...]], ...],
) -> tuple[
    dict[
        tuple[str, str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    dict[str, Any],
    str | None,
]:
    """Derive bounded causal evidence without organism authority.

    Every hop is already committed and published before this function is
    called. It consumes only the exact transient frontier embedded in those
    hop bodies. A malformed observer payload is reported and preserves the
    prior bounded witness; it cannot reject or roll back lived cognition.
    """

    active = dict(prior_active)
    completed: dict[str, Any] = {}
    try:
        for hop, affective in hops:
            active, completed = _advance_causal_motor_traces(
                None,
                active,
                completed,
                hop,
                affective,
            )
    except Exception as error:
        # The refusal is preserved in evidence AND logged: a silently frozen
        # trace observer hid the 2026-08-31 freeze family for days.
        print(
            "guala-causal-observer-refused "
            f"error={type(error).__name__}: {error}",
            file=sys.stderr,
            flush=True,
        )
        return (
            dict(prior_active),
            {},
            f"{type(error).__name__}: {error}"[:512],
        )
    return active, completed, None


def _compact_completed_external_retained_motor_paths(
    completed: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Project one exact completed path per stable recurrent formation."""

    paths_by_recurrent = completed.get(
        _COMPLETED_EXTERNAL_MOTOR_PATHS_BY_RECURRENT,
        {},
    )
    if not isinstance(paths_by_recurrent, dict):
        raise RuntimeError("completed causal motor paths changed format")
    return tuple(
        dict(paths_by_recurrent[recurrent_lineage])
        for recurrent_lineage in sorted(paths_by_recurrent)
    )


def _advance_internal_formation_motor_trace(
    committed_frontier: tuple[tuple[str, str, int, int, str], ...] | None,
    active: dict[
        tuple[str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    completed: dict[str, Any] | None,
    hop: dict[str, Any],
) -> tuple[
    dict[
        tuple[str, tuple[str, ...], int],
        dict[str, tuple[tuple[str, str, int, int], ...]],
    ],
    dict[str, Any] | None,
]:
    """Compatibility surface for the already-live C-023 focused proof."""

    if completed is not None:
        return active, completed
    typed_active = {
        ("retained_formation", receipt, lineages, tick): paths
        for (receipt, lineages, tick), paths in active.items()
    }
    typed_completed = (
        {"retained_formation": completed} if completed is not None else {}
    )
    next_active, next_completed = _advance_causal_motor_traces(
        committed_frontier,
        typed_active,
        typed_completed,
        hop,
    )
    formation_active = {
        (receipt, lineages, tick): paths
        for (kind, receipt, lineages, tick), paths in next_active.items()
        if kind == "retained_formation"
    }
    return formation_active, next_completed.get("retained_formation")


def _publish_committed_organism(
    organism: Any,
    admission: NativeResidentResourceAdmission,
    predecessor_state_sha256: str,
) -> Any:
    """Stage and publish the committed body; poison the runtime on failure.

    The caller holds ``_transition_lock``.  If publication fails the
    in-process organism is poisoned so the surface degrades honestly (503)
    instead of ever serving unpersisted state.
    """

    global _restored, _boot_error
    global _public_observation_body, _public_observation_etag, _runtime_proof_body

    try:
        _stage_started = time.perf_counter()
        staged = stage_active_native_organism(
            STATE_ROOT,
            organism,
            max_envelope_bytes=admission.max_envelope_bytes,
        )
        _publish_started = time.perf_counter()
        _transport_stage_wall_ms["custody_stage"] = _transport_stage_wall_ms.get(
            "custody_stage", 0.0
        ) + (_publish_started - _stage_started) * 1000.0
        published = publish_staged_native_organism(
            staged,
            expected_predecessor_sha256=predecessor_state_sha256,
            object_store=_object_store(),
            max_envelope_bytes=admission.max_envelope_bytes,
            max_fabric_bytes=admission.max_fabric_bytes,
            max_logical_peak_bytes=admission.max_logical_peak_bytes,
        )
        _transport_stage_wall_ms["custody_publish"] = _transport_stage_wall_ms.get(
            "custody_publish", 0.0
        ) + (time.perf_counter() - _publish_started) * 1000.0
        return published
    except BaseException as error:
        _restored = None
        _boot_error = (
            "committed native successor could not be published: "
            f"{type(error).__name__}: {error}"
        )
        _public_observation_body = None
        _public_observation_etag = None
        _runtime_proof_body = None
        raise HTTPException(status_code=503, detail=_boot_error) from error


def _perform_admitted_intake(
    episodes: list[tuple[Any, list[tuple[int, int]]]],
    intake: str,
    *,
    vestibular_yaw: tuple[int, tuple[int, ...]] | None = None,
) -> dict[str, Any]:
    """Commit every hop in-memory, then persist and publish ONCE.

    Efficiency contract: one accepted intake (a whole lesson of hops) writes
    exactly one durable body generation, after its final hop, instead of one
    full body save+publish per 250 ms hop.

    Restart-consistency: hops advance only the in-process organism until the
    single persist; a crash mid-lesson therefore loses only the un-persisted
    lesson tail and the organism resumes from the last persisted body (the
    pre-lesson CURRENT).  Safety property preserved: the public observation
    cache is refreshed only after the persist succeeds, readiness surfaces
    are served under the same lock, and a persist failure poisons the
    runtime (503) exactly as before, so no observation or readiness is ever
    computed from unpersisted state.

    If a hop is refused mid-lesson, the already-committed hop prefix is
    persisted before the refusal is re-raised, keeping the durable body and
    the in-process organism identical.
    """

    _begin_external_intake()
    try:
        with _transition_lock:
            result = _perform_admitted_intake_locked(
                episodes,
                intake,
                vestibular_yaw=vestibular_yaw,
            )
            _refresh_public_observation_cache()
            return result
    finally:
        _end_external_intake()


def _public_admitted_intake_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded JSON receipt for one already-committed intake.

    The internal observation deliberately retains exact binary body states for
    causal validation and possible self-hearing. Those bytes are organism
    evidence, not an HTTP payload. Returning the internal dictionary directly
    made a lawful articulation commit and then fail while JSON encoded its
    receipt. Keep the internal evidence untouched and publish only the exact
    scalar identities, bounded counts, and digests an external caller needs to
    know what committed.
    """

    observation = result.get("observation")
    if not isinstance(observation, dict):
        observation = {}
    public_observation = {
        key: observation[key]
        for key in (
            "predecessor_organism_tick",
            "organism_tick",
            "predecessor_state_sha256",
            "state_sha256",
            "causal_transition_sha256",
            "energy_exhausted",
            "intake",
        )
        if key in observation
    }
    articulation = observation.get("articulation")
    if isinstance(articulation, dict):
        public_observation["articulation"] = {
            key: articulation[key]
            for key in (
                "layer_13_recruitment_count",
                "sample_rate_hz",
                "pressure_sample_count",
                "pressure_sha256",
                "applied_motor_quanta",
                "stalled_motor_quanta",
                "articulatory_body_port_count",
                "articulatory_body_nonquiescent_port_count",
                "articulatory_body_receptor_ingress_count",
                "articulatory_body_perturbed_neuron_count",
                "self_hearing_hop_count",
                "self_hearing_transitioned_neuron_count",
                "self_hearing_fractal_count",
            )
            if key in articulation
        }
    public_result = {
        key: result[key]
        for key in (
            "accepted",
            "ok",
            "hop_count",
            "vestibular_tick_count",
            "persisted",
            "schema",
            "receptor_ingress",
            "totals",
            "durable_receipt",
        )
        if key in result
    }
    public_result["observation"] = public_observation
    return public_result


def _abort_lived_trajectory(organism: Any) -> None:
    """Invalidate an off-lock checkpoint before restoring its predecessor."""

    global _custody_trajectory_epoch
    global _pending_unsealed_intervals, _pending_chain_predecessor_sha

    _custody_trajectory_epoch += 1
    try:
        organism.abort_unsealed_trajectory()
    finally:
        _pending_unsealed_intervals = 0
        _pending_chain_predecessor_sha = None
        _checkpoint_requested.clear()


def _retain_already_lived_intake_after_refusal(
    organism: Any,
    predecessor: Any,
    intake: str,
    error: BaseException,
) -> bool:
    """Keep physical intervals that completed before later intake work refused.

    An HTTP request is not an organism transaction. Once native settlement
    advances the resident tick, a later evidence or action-preparation error
    cannot truthfully rewind those lived intervals to the last sealed CURRENT.
    The failed outer request remains refused; only the already-completed native
    successor is retained and offered to the ordinary external custodian.
    """

    global _pending_unsealed_intervals, _pending_chain_predecessor_sha

    lived_organism_tick = int(organism.live_organism_tick)
    if lived_organism_tick <= predecessor.organism_tick:
        return False
    if _pending_chain_predecessor_sha is None:
        _pending_chain_predecessor_sha = predecessor.state_sha256
    _pending_unsealed_intervals += 1
    if _pending_unsealed_intervals >= _checkpoint_every_intervals():
        _checkpoint_requested.set()
    print(
        "guala-lived-intake-retained-after-refusal "
        f"intake={intake} predecessor_tick={predecessor.organism_tick} "
        f"resident_tick={lived_organism_tick} "
        f"pending_intervals={_pending_unsealed_intervals} "
        f"error={type(error).__name__}:{error}",
        file=sys.stderr,
        flush=True,
    )
    return True


def _prepare_continuous_native_action_consequence(
    *,
    organism_identity: str,
    predecessor_state_sha256: str,
    causal_transition_sha256: str,
    predecessor_body_axes: tuple[Any, ...],
    successor_body_axes: tuple[Any, ...],
    motor_unit_recruitments: tuple[Any, ...],
    root_yaw_unit_recruitments: tuple[tuple[str, int, int, str], ...],
    root_translation_unit_recruitments: tuple[
        tuple[str, int, int, str, str], ...
    ],
    body_effector_bindings: tuple[Any, ...],
    articulated_body_consequences: tuple[Any, ...],
    body_proprioceptive_sources: tuple[
        tuple[bytes, tuple[int, int, int, int, int]], ...
    ],
    root_yaw_source_tick: int,
) -> tuple[Any, Any, Any, Any, dict[str, Any], Any, int, int, int] | None:
    """Prepare one immediate world/sensor interval for a native body action.

    Cognition is not suspended and no organism-state transaction is created.
    The already-lived native interval supplies the efferent/body facts; this
    function advances the physical world once and builds the next ordinary
    complete-roster sensory occurrence for the same resident organism.
    """

    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt,
        AdvanceContactOpticalSurfaceCommand,
        AdvancePhysicalTimeCommand,
        ENVIRONMENT_PORT_ID,
        GraspContactCommand,
        MoveCommand,
        PORT_ID,
        PositionMM,
        PoseMM,
        PreparedActionExecution,
        ReleaseHeldObjectCommand,
        encode_command,
    )

    negative_root_carriers = sum(
        int(carriers)
        for _lineage, _topology, carriers, direction in root_yaw_unit_recruitments
        if direction == "negative"
    )
    positive_root_carriers = sum(
        int(carriers)
        for _lineage, _topology, carriers, direction in root_yaw_unit_recruitments
        if direction == "positive"
    )
    if any(
        direction not in {"negative", "positive"}
        for _lineage, _topology, _carriers, direction in root_yaw_unit_recruitments
    ):
        raise RuntimeError("native root-yaw discharge lost typed direction")
    signed_root_yaw = positive_root_carriers - negative_root_carriers
    signed_root_x = sum(
        int(carriers) if direction == "positive" else -int(carriers)
        for _lineage, _topology, carriers, axis, direction
        in root_translation_unit_recruitments
        if axis == "x"
    )
    signed_root_y = sum(
        int(carriers) if direction == "positive" else -int(carriers)
        for _lineage, _topology, carriers, axis, direction
        in root_translation_unit_recruitments
        if axis == "y"
    )
    if any(
        axis not in {"x", "y"} or direction not in {"negative", "positive"}
        for _lineage, _topology, _carriers, axis, direction
        in root_translation_unit_recruitments
    ):
        raise RuntimeError("native root-translation discharge lost typed anatomy")
    if not -(1 << 31) <= signed_root_yaw < (1 << 31):
        raise RuntimeError("native root-yaw discharge exceeds exact body width")
    if not (-(1 << 31) <= signed_root_x < (1 << 31)) or not (
        -(1 << 31) <= signed_root_y < (1 << 31)
    ):
        raise RuntimeError("native root-translation discharge exceeds exact body width")
    if (
        not articulated_body_consequences
        and signed_root_yaw == 0
        and signed_root_x == 0
        and signed_root_y == 0
    ):
        return None
    if articulated_body_consequences and not motor_unit_recruitments:
        raise RuntimeError("native body consequence has no causal motor discharge")
    if any(len(consequence) != 11 for consequence in articulated_body_consequences):
        raise RuntimeError("native body consequence changed its exact shape")
    grip_displacement_by_axis = {
        axis: sum(
            consequence[5]
            for consequence in articulated_body_consequences
            if consequence[1] == axis
        )
        for axis in (
            "left_grip_aperture",
            "right_grip_aperture",
        )
    }
    grip_closing_axes = tuple(sorted(
        axis
        for axis, displacement in grip_displacement_by_axis.items()
        if displacement < 0
    ))
    grip_opening_axes = tuple(sorted(
        axis
        for axis, displacement in grip_displacement_by_axis.items()
        if displacement > 0
    ))

    authority = _world()
    before = authority.observation_snapshot()
    intent = _receipt(
        {
            "articulated_body_consequences": articulated_body_consequences,
            "body_effector_bindings": body_effector_bindings,
            "duration_microseconds": WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            "motor_unit_recruitments": motor_unit_recruitments,
            "grip_closing_axes": grip_closing_axes,
            "grip_opening_axes": grip_opening_axes,
            "root_yaw_unit_recruitments": root_yaw_unit_recruitments,
            "root_translation_unit_recruitments": root_translation_unit_recruitments,
            "signed_root_yaw_millidegrees": signed_root_yaw,
            "signed_root_x_millimetres": signed_root_x,
            "signed_root_y_millimetres": signed_root_y,
            "organism_identity": organism_identity,
            "predecessor_state_sha256": predecessor_state_sha256,
            "schema": "guala.native_action_world_interval_intent.v3",
            "causal_transition_sha256": causal_transition_sha256,
            "world_revision": before.revision,
            "world_state_before_sha256": before.state_sha256,
        }
    )
    if signed_root_yaw or signed_root_x or signed_root_y:
        before_body = next(
            body for body in before.bodies if body.body_id == before.self_body_id
        )
        successor_heading, _root_trajectory = exact_native_yaw_trajectory(
            predecessor_heading_millidegrees=before_body.pose.heading_millidegrees,
            signed_displacement_millidegrees=signed_root_yaw,
            duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
        )
        command = MoveCommand(
            target_pose=PoseMM(
                PositionMM(
                    before_body.pose.position.x + signed_root_x,
                    before_body.pose.position.y + signed_root_y,
                    before_body.pose.position.z,
                ),
                successor_heading,
            ),
            duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
        )
        port_id = PORT_ID
    elif grip_closing_axes and not grip_opening_axes:
        command = GraspContactCommand(
            duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000
        )
        port_id = PORT_ID
    elif len(grip_opening_axes) == 1 and not grip_closing_axes:
        before_body = next(
            body
            for body in before.bodies
            if body.body_id == before.self_body_id
        )
        command = (
            ReleaseHeldObjectCommand(
                duration_microseconds=(
                    WORLD_BODY_ACTION_MILLISECONDS * 1_000
                )
            )
            if before_body.held_object_id is not None
            else AdvanceContactOpticalSurfaceCommand(
                duration_microseconds=(
                    WORLD_BODY_ACTION_MILLISECONDS * 1_000
                )
            )
        )
        port_id = PORT_ID
    else:
        command = AdvancePhysicalTimeCommand(
            duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000
        )
        port_id = ENVIRONMENT_PORT_ID
    prepared = authority.prepare_port_command(
        port_id=port_id,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=intent,
        expected_revision=before.revision,
    )
    if isinstance(prepared, ActionExecutionReceipt):
        # The motor discharge still happened in the organism when the world
        # blocked translation. Advance the same physical interval with zero
        # root displacement so unchanged vision/body consequence returns to
        # cognition instead of aborting the organism's lived trajectory.
        prepared = authority.prepare_port_command(
            port_id=ENVIRONMENT_PORT_ID,
            command_payload=encode_command(
                AdvancePhysicalTimeCommand(
                    duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000
                )
            ),
            causal_intent_receipt_sha256=intent,
            expected_revision=before.revision,
        )
    if not isinstance(prepared, PreparedActionExecution):
        raise RuntimeError("native action world interval lost prepared custody")

    try:
        execution = prepared.execution_receipt
        world_displacement = _world_displacement(execution.before, execution.after)
        world_episode, world_admissions, lane_truth = _action_consequence_episode(
            execution,
            action_duration=Fraction(WORLD_BODY_ACTION_MILLISECONDS, 1_000),
            body_displacement=world_displacement,
            predecessor_retinal_body_axes=predecessor_body_axes,
            retinal_body_axes=successor_body_axes,
        )
        restored_body_sources = tuple(
            restore_native_joint_source_episode(
                raw_source,
                port_count,
                sample_count,
                occurrence_count,
                occurrence_frame_count,
            )
            for raw_source, (
                _source_tick,
                port_count,
                sample_count,
                occurrence_count,
                occurrence_frame_count,
            ) in body_proprioceptive_sources
        )
        root_yaw_source = (
            exact_native_root_yaw_proprioceptive_source(
                source_tick=root_yaw_source_tick,
                signed_displacement_millidegrees=signed_root_yaw,
            )
            if signed_root_yaw
            else None
        )
        if signed_root_x or signed_root_y:
            before_root = next(
                body
                for body in execution.before.bodies
                if body.body_id == execution.before.self_body_id
            )
            after_root = next(
                body
                for body in execution.after.bodies
                if body.body_id == execution.after.self_body_id
            )
            actual_root_x = after_root.pose.position.x - before_root.pose.position.x
            actual_root_y = after_root.pose.position.y - before_root.pose.position.y
        else:
            actual_root_x = 0
            actual_root_y = 0
        root_translation_source = (
            exact_native_root_translation_proprioceptive_source(
                source_tick=root_yaw_source_tick,
                signed_x_millimetres=actual_root_x,
                signed_y_millimetres=actual_root_y,
            )
            if actual_root_x or actual_root_y
            else None
        )
        consequence_sources = (
            *restored_body_sources,
            *((root_yaw_source,) if root_yaw_source is not None else ()),
            *((root_translation_source,) if root_translation_source is not None else ()),
        )
        if consequence_sources:
            episode = (world_episode, *consequence_sources)
            admissions = (
                world_admissions,
                *(
                    [(1, 1_000)] * source.occurrence_count
                    for source in consequence_sources
                ),
            )
        else:
            episode = world_episode
            admissions = world_admissions
        predecessor_axes = {axis[1]: axis[3] for axis in predecessor_body_axes}
        successor_axes = {axis[1]: axis[3] for axis in successor_body_axes}
        if predecessor_axes.keys() != successor_axes.keys():
            raise RuntimeError("native action changed articulated body anatomy")
        signed_neck_yaw = (
            successor_axes["neck_yaw"] - predecessor_axes["neck_yaw"]
        )
        vestibular_yaw = None
        signed_total_yaw = signed_root_yaw + signed_neck_yaw
        if not -(1 << 31) <= signed_total_yaw < (1 << 31):
            raise RuntimeError("combined native yaw exceeds exact body width")
        if signed_total_yaw:
            before_body = next(
                body
                for body in execution.before.bodies
                if body.body_id == execution.before.self_body_id
            )
            after_body = next(
                body
                for body in execution.after.bodies
                if body.body_id == execution.after.self_body_id
            )
            predecessor_heading = (
                before_body.pose.heading_millidegrees
                + predecessor_axes["neck_yaw"]
            ) % 360_000
            expected_successor_heading = (
                after_body.pose.heading_millidegrees
                + successor_axes["neck_yaw"]
            ) % 360_000
            successor_heading, trajectory = exact_native_yaw_trajectory(
                predecessor_heading_millidegrees=predecessor_heading,
                signed_displacement_millidegrees=signed_total_yaw,
                duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            )
            if successor_heading != expected_successor_heading:
                raise RuntimeError("native neck motion lost exact vestibular geometry")
            vestibular_yaw = (predecessor_heading, trajectory)
    except BaseException:
        authority.discard_prepared_action(prepared)
        raise

    return (
        authority,
        prepared,
        episode,
        admissions,
        lane_truth,
        vestibular_yaw,
        signed_root_yaw,
        actual_root_x,
        actual_root_y,
    )


def _perform_admitted_intake_locked(
    episodes: list[tuple[Any, list[tuple[int, int]]]],
    intake: str,
    *,
    vestibular_yaw: tuple[int, tuple[int, ...]] | None = None,
    external_participant_action_receipt: str | None = None,
    defer_seal: bool | None = None,
    real_nutrition_intake_zeptojoules: int | None = None,
) -> dict[str, Any]:
    """Body of ``_perform_admitted_intake``; caller holds ``_transition_lock``."""


    global _restored, _last_transition_evidence, _last_self_moved
    global _last_displacement
    global _pending_unsealed_intervals, _pending_chain_predecessor_sha
    global _last_tested_prediction_evidence, _last_tested_affective_balance_evidence
    global _last_tested_localized_fluid_chemistry_evidence
    global _last_tested_articulation_evidence
    global _native_pressure_audio_cache
    global _last_causal_cross_context_use_evidence
    global _last_intrinsic_curiosity_evidence
    global _last_social_experience_evidence
    global _last_tested_physical_choice_evidence
    global _sensorimotor_play_candidate, _last_sensorimotor_play_evidence
    global _body_owned_laughter_candidate, _last_body_owned_laughter_evidence
    global _reciprocal_social_play_candidate
    global _last_reciprocal_social_play_evidence
    global _active_cross_intake_causal_motor_traces

    # Ordinary lived time never seals or serializes the organism. The sole
    # background custodian snapshots the exact resident state after the
    # configured count and adopts that same published body as the runtime's
    # recovery predecessor. An explicit False remains available only to
    # offline migration/rehearsal callers; no production route passes it.
    if defer_seal is None:
        defer_seal = True

    totals = {
        "complete_neuron_fractal_count": 0,
        "current_cohort_evaluation_count": 0,
        "dsf_delivery_count": 0,
        "endogenous_partial_cue_reassembly_count": 0,
        "partial_cue_reassembly_count": 0,
        "physically_transitioned_neuron_count": 0,
        "metabolically_perturbed_body_receptor_count": 0,
        "rest_recovered_neuron_count": 0,
        "rest_drained_dissipation_quanta": 0,
        "energy_exhausted_interval_count": 0,
        "externally_perturbed_body_receptor_count": 0,
        "recurrent_complete_neuron_fractal_count": 0,
    }
    receptor_ingress_sense_counts = {sense.value: 0 for sense in SENSE_ORDER}
    receptor_ingress_changing_count = 0
    receptor_ingress_quiescent_count = 0
    restored, admission = _runtime()
    organism = restored.organism
    predecessor = restored.pointer
    predecessor_body_state_sha256 = (
        organism.readiness().articulated_body_state_sha256
    )
    predecessor_body_axes = tuple(organism.readiness().articulated_body_axes)
    last_hop: dict[str, Any] | None = None
    committed_hop_count = 0
    committed_vestibular_tick_count = 0
    motor_unit_recruitments: list[
        tuple[
            str,
            int,
            int,
            tuple[tuple[str, int, str, int, int, int], ...],
            tuple[tuple[str, str, str, int, int, str, str], ...],
        ]
    ] = []
    root_yaw_unit_recruitments: list[tuple[str, int, int, str]] = []
    root_translation_unit_recruitments: list[
        tuple[str, int, int, str, str]
    ] = []
    articulatory_unit_recruitments: list[
        tuple[
            str,
            int,
            int,
            tuple[tuple[str, int, str, int, int, int], ...],
        ]
    ] = []
    articulatory_intervals: list[
        tuple[
            tuple[tuple[int, int], ...],
            tuple[int, ...],
            bytes,
            bytes,
            int,
            int,
            int,
            int,
            int,
            int,
        ]
    ] = []
    articulatory_hop_ranges: list[
        tuple[int, int, tuple[tuple[Any, ...], ...]]
    ] = []
    body_effector_bindings: list[tuple[int, str, str, str, int]] = []
    articulated_body_consequences: list[
        tuple[int, str, str, int, int, int, int, int, int, int, int]
    ] = []
    body_proprioceptive_source_receipts: list[
        tuple[str, tuple[int, int, int, int, int]]
    ] = []
    body_proprioceptive_sources: list[
        tuple[bytes, tuple[int, int, int, int, int]]
    ] = []

    def retain_articulated_body_evidence(hop: dict[str, Any]) -> None:
        body_effector_bindings.extend(
            _tick_attributed_effector_bindings(hop)
        )
        articulated_body_consequences.extend(
            hop["articulated_body_consequences"]
        )
        sources = hop["body_proprioceptive_sources"]
        extents = hop["body_proprioceptive_source_extents"]
        if len(sources) != len(extents):
            raise RuntimeError("native body source receipts lost cardinality")
        body_proprioceptive_source_receipts.extend(
            (hashlib.sha256(source).hexdigest(), extent)
            for source, extent in zip(sources, extents, strict=True)
        )
        body_proprioceptive_sources.extend(
            zip(sources, extents, strict=True)
        )

    def retain_articulatory_interval_evidence(hop: dict[str, Any]) -> None:
        for interval in hop["causal_interval_evidence"]:
            sample_rate_hz = interval["articulatory_sample_rate_hz"]
            pressure = tuple(interval["articulatory_pressure_pcm"])
            body_trajectories = bytes(
                interval["articulatory_body_trajectories"]
            )
            recruitments = interval["articulatory_unit_recruitments"]
            if sample_rate_hz != COCHLEAR_SAMPLE_RATE_HZ:
                raise RuntimeError(
                    "native articulatory body left the mounted cochlear clock"
                )
            duration_samples = interval[
                "source_duration_samples_at_articulatory_rate"
            ]
            if not pressure:
                if body_trajectories or recruitments:
                    raise RuntimeError(
                        "native articulatory event lost its physical transition"
                    )
                continue
            if (
                isinstance(duration_samples, bool)
                or not isinstance(duration_samples, int)
                or duration_samples <= 0
                or len(pressure) != duration_samples
            ):
                raise RuntimeError(
                    "native articulatory pressure did not cover its exact physical interval"
                )
            if len(body_trajectories) != (
                ARTICULATORY_BODY_PORT_COUNT
                * len(pressure)
                * struct.calcsize("<h")
            ):
                raise RuntimeError(
                    "native articulatory body trajectory changed cardinality"
                )
            articulatory_intervals.append(
                (
                    tuple(
                        (int(topology), int(carriers))
                        for _lineage, topology, carriers, _transfers in recruitments
                    ),
                    pressure,
                    body_trajectories,
                    interval["articulated_body_state"],
                    int(
                        interval[
                            "articulatory_peak_transducer_surface_velocity_pcm"
                        ]
                    ),
                    int(interval["articulatory_glottal_open_samples_at_apex"]),
                    int(
                        interval[
                            "articulatory_mouth_area_square_millimetres_at_apex"
                        ]
                    ),
                    int(
                        interval[
                            "articulatory_perioral_area_displacement_square_millimetres"
                        ]
                    ),
                    int(interval["articulatory_applied_motor_quanta"]),
                    int(interval["articulatory_stalled_motor_quanta"]),
                )
            )

    articulation: dict[str, Any] | None = None
    native_pressure_s16le: bytes | None = None
    articulation_candidates: list[tuple[dict[str, Any], bytes]] = []
    emitted_neuron_fractals: list[dict[str, Any]] = []
    organic_mosaic_relations: list[dict[str, Any]] = []
    physical_frontier_routes: tuple[tuple[Any, ...], ...] = ()
    preceding_distinct_physical_frontier_routes: tuple[
        tuple[Any, ...], ...
    ] = ()
    reached_and_foregone_physical_frontier_routes: tuple[
        tuple[Any, ...], ...
    ] = ()
    attention_motor_bindings: tuple[dict[str, Any], ...] = ()
    working_causal_continuations: tuple[tuple[Any, ...], ...] = ()
    settled_working_frontier: tuple[tuple[Any, ...], ...] = ()
    physical_prediction_alternatives: tuple[tuple[Any, ...], ...] = ()
    body_consequence_transfers: tuple[tuple[Any, ...], ...] = ()
    affective_balance_trajectories: tuple[tuple[Any, ...], ...] = ()
    localized_fluid_chemistry: tuple[tuple[Any, ...], ...] = ()
    localized_metabolic_strain_evaluated_body_receptor_lineages: tuple[str, ...] = ()
    localized_metabolic_strain: tuple[tuple[Any, ...], ...] = ()
    # Causal-path reconstruction is observation only. Keep the exact bounded
    # native hop bodies until CURRENT is durable; an observer must never sit
    # between native settlement and publication or become a rollback cause.
    causal_observation_hops: list[
        tuple[dict[str, Any], tuple[tuple[Any, ...], ...]]
    ] = []
    consumed_in_flight_acoustic: list[dict[str, Any]] = []
    intake_error: Exception | None = None

    def retain_committed_hop(
        hop: dict[str, Any],
        *,
        authored_hop_count: int,
        consumed_acoustic: dict[str, Any] | None = None,
    ) -> None:
        """Retain bounded observer evidence for one already-committed hop."""

        nonlocal last_hop, committed_hop_count
        nonlocal receptor_ingress_changing_count
        nonlocal receptor_ingress_quiescent_count
        nonlocal physical_frontier_routes
        nonlocal preceding_distinct_physical_frontier_routes
        nonlocal reached_and_foregone_physical_frontier_routes
        nonlocal attention_motor_bindings
        nonlocal working_causal_continuations, settled_working_frontier
        nonlocal physical_prediction_alternatives, body_consequence_transfers
        nonlocal affective_balance_trajectories
        nonlocal localized_fluid_chemistry
        nonlocal localized_metabolic_strain_evaluated_body_receptor_lineages
        nonlocal localized_metabolic_strain

        last_hop = hop
        if consumed_acoustic is not None:
            consumed_in_flight_acoustic.append(
                {
                    **consumed_acoustic,
                    "coexisting_emitted_neuron_fractal_count": len(
                        hop["emitted_neuron_fractals"]
                    ),
                    "coexisting_transitioned_neuron_count": hop[
                        "physically_transitioned_neuron_count"
                    ],
                    "receptor_ingress_sound_count": hop[
                        "receptor_ingress_sense_counts"
                    ]["sound"],
                }
            )
        affective_balance_trajectories = _advance_bounded_affective_balance_evidence(
            affective_balance_trajectories,
            hop,
        )
        causal_observation_hops.append((hop, affective_balance_trajectories))
        (
            physical_frontier_routes,
            preceding_distinct_physical_frontier_routes,
            reached_and_foregone_physical_frontier_routes,
        ) = _advance_bounded_frontier_evidence(
            physical_frontier_routes,
            preceding_distinct_physical_frontier_routes,
            reached_and_foregone_physical_frontier_routes,
            hop,
        )
        attention_motor_bindings = _advance_bounded_attention_motor_bindings(
            attention_motor_bindings,
            hop,
        )
        (
            working_causal_continuations,
            settled_working_frontier,
        ) = _advance_bounded_working_causal_evidence(
            working_causal_continuations,
            settled_working_frontier,
            hop,
        )
        (
            physical_prediction_alternatives,
            body_consequence_transfers,
        ) = _advance_bounded_prediction_evidence(
            physical_prediction_alternatives,
            body_consequence_transfers,
            hop,
        )
        localized_fluid_chemistry = (
            _advance_bounded_localized_fluid_chemistry_evidence(
                localized_fluid_chemistry,
                hop,
            )
        )
        (
            localized_metabolic_strain_evaluated_body_receptor_lineages,
            localized_metabolic_strain,
        ) = _advance_bounded_localized_metabolic_strain_evidence(
            localized_metabolic_strain_evaluated_body_receptor_lineages,
            localized_metabolic_strain,
            hop,
        )
        committed_hop_count += authored_hop_count
        committed_hop_count += sum(
            int(extent[3])
            for extent in hop["body_proprioceptive_source_extents"]
        )
        motor_unit_recruitments.extend(hop["motor_unit_recruitments"])
        root_yaw_unit_recruitments.extend(hop["root_yaw_unit_recruitments"])
        root_translation_unit_recruitments.extend(
            hop["root_translation_unit_recruitments"]
        )
        hop_articulatory_recruitments = tuple(
            hop["articulatory_unit_recruitments"]
        )
        articulatory_unit_recruitments.extend(hop_articulatory_recruitments)
        articulatory_interval_start = len(articulatory_intervals)
        retain_articulatory_interval_evidence(hop)
        if len(articulatory_intervals) > articulatory_interval_start:
            articulatory_hop_ranges.append((
                articulatory_interval_start,
                len(articulatory_intervals),
                hop_articulatory_recruitments,
            ))
        retain_articulated_body_evidence(hop)
        emitted_neuron_fractals.extend(hop["emitted_neuron_fractals"])
        organic_mosaic_relations.extend(hop["organic_mosaic_relations"])
        for key in totals:
            totals[key] += hop[key]
        for sense, count in hop["receptor_ingress_sense_counts"].items():
            receptor_ingress_sense_counts[sense] += count
        receptor_ingress_changing_count += hop[
            "receptor_ingress_changing_count"
        ]
        receptor_ingress_quiescent_count += hop[
            "receptor_ingress_quiescent_count"
        ]

    try:
        if vestibular_yaw is not None:
            heading, signed_steps = vestibular_yaw
            last_hop = _commit_vestibular_trajectory(
                organism,
                heading,
                signed_steps,
            )
            affective_balance_trajectories = (
                _advance_bounded_affective_balance_evidence(
                    affective_balance_trajectories,
                    last_hop,
                )
            )
            causal_observation_hops.append(
                (last_hop, affective_balance_trajectories)
            )
            (
                physical_frontier_routes,
                preceding_distinct_physical_frontier_routes,
                reached_and_foregone_physical_frontier_routes,
            ) = _advance_bounded_frontier_evidence(
                physical_frontier_routes,
                preceding_distinct_physical_frontier_routes,
                reached_and_foregone_physical_frontier_routes,
                last_hop,
            )
            attention_motor_bindings = _advance_bounded_attention_motor_bindings(
                attention_motor_bindings,
                last_hop,
            )
            (
                working_causal_continuations,
                settled_working_frontier,
            ) = _advance_bounded_working_causal_evidence(
                working_causal_continuations,
                settled_working_frontier,
                last_hop,
            )
            (
                physical_prediction_alternatives,
                body_consequence_transfers,
            ) = _advance_bounded_prediction_evidence(
                physical_prediction_alternatives,
                body_consequence_transfers,
                last_hop,
            )
            localized_fluid_chemistry = (
                _advance_bounded_localized_fluid_chemistry_evidence(
                    localized_fluid_chemistry,
                    last_hop,
                )
            )
            (
                localized_metabolic_strain_evaluated_body_receptor_lineages,
                localized_metabolic_strain,
            ) = _advance_bounded_localized_metabolic_strain_evidence(
                localized_metabolic_strain_evaluated_body_receptor_lineages,
                localized_metabolic_strain,
                last_hop,
            )
            committed_vestibular_tick_count = len(signed_steps)
            vestibular_articulatory_recruitments = tuple(
                last_hop["articulatory_unit_recruitments"]
            )
            articulatory_unit_recruitments.extend(
                vestibular_articulatory_recruitments
            )
            vestibular_articulatory_start = len(articulatory_intervals)
            retain_articulatory_interval_evidence(last_hop)
            if len(articulatory_intervals) > vestibular_articulatory_start:
                articulatory_hop_ranges.append((
                    vestibular_articulatory_start,
                    len(articulatory_intervals),
                    vestibular_articulatory_recruitments,
                ))
            motor_unit_recruitments.extend(last_hop["motor_unit_recruitments"])
            root_yaw_unit_recruitments.extend(
                last_hop["root_yaw_unit_recruitments"]
            )
            root_translation_unit_recruitments.extend(
                last_hop["root_translation_unit_recruitments"]
            )
            retain_articulated_body_evidence(last_hop)
            emitted_neuron_fractals.extend(last_hop["emitted_neuron_fractals"])
            organic_mosaic_relations.extend(
                last_hop["organic_mosaic_relations"]
            )
            for key in totals:
                totals[key] += last_hop[key]
        for episode_index, (episode, admissions) in enumerate(episodes):
            hop, consumed_acoustic = _commit_one_timeline_hop(
                organism,
                episode,
                admissions,
                purpose="primary",
                external_participant_action_receipt=(
                    external_participant_action_receipt
                ),
                # One bite is one intake: the really transferred nutrition
                # rides the feed's own first lived hop and nothing after.
                real_nutrition_intake_zeptojoules=(
                    real_nutrition_intake_zeptojoules
                    if episode_index == 0
                    else None
                ),
            )
            retain_committed_hop(
                hop,
                authored_hop_count=sum(
                    int(source.occurrence_count)
                    for source in (
                        episode if isinstance(episode, tuple) else (episode,)
                    )
                ),
                consumed_acoustic=consumed_acoustic,
            )
        native_articulatory_pressure_present = any(
            any(sample != 0 for sample in interval[1])
            for interval in articulatory_intervals
        )
        if articulatory_unit_recruitments or native_articulatory_pressure_present:
            flattened_interval_recruitments = tuple(
                recruitment
                for recruitments, *_rest in articulatory_intervals
                for recruitment in recruitments
            )
            aggregate_recruitments = tuple(
                (int(topology), int(carriers))
                for _lineage, topology, carriers, _transfers in (
                    articulatory_unit_recruitments
                )
            )
            if flattened_interval_recruitments != aggregate_recruitments:
                raise RuntimeError(
                    "native articulatory intervals lost recruitment order"
                )
            for start, end, recruitments in articulatory_hop_ranges:
                candidate = _articulation_candidate_from_hop(
                    tuple(articulatory_intervals[start:end]),
                    recruitments,
                )
                if candidate is not None:
                    articulation_candidates.append(candidate)
            if not articulation_candidates:
                raise RuntimeError(
                    "native articulatory pressure lost its per-hop evidence"
                )
    except (RuntimeError, TypeError, ValueError) as error:
        intake_error = error
    if intake_error is not None:
        retained = _retain_already_lived_intake_after_refusal(
            organism,
            predecessor,
            intake,
            intake_error,
        )
        if not retained:
            try:
                _abort_lived_trajectory(organism)
            except (RuntimeError, ValueError) as abort_error:
                if "has no pending candidate" not in str(abort_error):
                    raise RuntimeError(
                        "resident intake refusal and predecessor restoration both failed"
                    ) from abort_error
        raise intake_error
    if last_hop is None or (
        committed_hop_count == 0 and committed_vestibular_tick_count == 0
    ):
        raise RuntimeError("admitted intake carried no hop episodes")
    action_body_axes = organism.live_articulated_body_axes()
    signed_root_yaw = 0
    signed_root_x = 0
    signed_root_y = 0
    try:
        prepared_action = _prepare_continuous_native_action_consequence(
            organism_identity=predecessor.identity,
            predecessor_state_sha256=predecessor.state_sha256,
            causal_transition_sha256=last_hop["causal_transition_sha256"],
            predecessor_body_axes=predecessor_body_axes,
            successor_body_axes=action_body_axes,
            motor_unit_recruitments=tuple(motor_unit_recruitments),
            root_yaw_unit_recruitments=tuple(root_yaw_unit_recruitments),
            root_translation_unit_recruitments=tuple(
                root_translation_unit_recruitments
            ),
            body_effector_bindings=tuple(sorted(set(body_effector_bindings))),
            articulated_body_consequences=tuple(articulated_body_consequences),
            body_proprioceptive_sources=tuple(body_proprioceptive_sources),
            root_yaw_source_tick=int(last_hop["organism_tick"]),
        )
    except BaseException as error:
        retained = _retain_already_lived_intake_after_refusal(
            organism,
            predecessor,
            intake,
            error,
        )
        if not retained:
            _abort_lived_trajectory(organism)
        raise
    action_execution: Any | None = None
    action_consequence: dict[str, Any] | None = None
    action_vestibular_tick_count = 0
    if prepared_action is None:
        if defer_seal:
            # The trajectory stays open; this interval's physics is already
            # lived and its evidence retained. The next sealing intake — the
            # Nth unattended interval, any external experience, or shutdown —
            # seals and publishes the whole chain from the stashed
            # predecessor. Nothing physical differs from sealing every
            # interval; only the copy cadence does.
            if _pending_chain_predecessor_sha is None:
                _pending_chain_predecessor_sha = predecessor.state_sha256
            _pending_unsealed_intervals += 1
            last_hop = dict(last_hop)
            last_hop["sealed"] = False
            last_hop["pending_unsealed_intervals"] = _pending_unsealed_intervals
            published = None
        else:
            _seal_started = time.perf_counter()
            sealed_observation = organism.seal_unsealed_trajectory_direct()
            _transport_stage_wall_ms["seal"] = _transport_stage_wall_ms.get(
                "seal", 0.0
            ) + (time.perf_counter() - _seal_started) * 1000.0
            try:
                if sealed_observation.organism_tick != last_hop["organism_tick"]:
                    raise RuntimeError(
                        "final resident seal changed the lived intake tick"
                    )
                last_hop["state_sha256"] = sealed_observation.state_sha256
                _chain_predecessor = (
                    _pending_chain_predecessor_sha or predecessor.state_sha256
                )
                published = _publish_committed_organism(
                    organism, admission, _chain_predecessor
                )
                _pending_unsealed_intervals = 0
                _pending_chain_predecessor_sha = None
            except BaseException:
                _abort_lived_trajectory(organism)
                _pending_unsealed_intervals = 0
                _pending_chain_predecessor_sha = None
                raise
            organism.acknowledge_sealed_trajectory()
    else:
        (
            action_authority,
            prepared_world,
            consequence_episode,
            consequence_admissions,
            consequence_lane_truth,
            consequence_vestibular_yaw,
            signed_root_yaw,
            signed_root_x,
            signed_root_y,
        ) = prepared_action
        world_committed = False
        world_persisted = False
        organism_published = False
        predecessor_world_body = action_authority.encoded_snapshot()
        try:
            with action_authority.prepared_action_visibility_transaction(
                prepared_world
            ):
                action_execution = action_authority.commit_prepared_action(
                    prepared_world
                )
                world_committed = True
                consequence_hop, consumed_acoustic = _commit_one_timeline_hop(
                    organism,
                    consequence_episode,
                    consequence_admissions,
                    purpose="action_consequence",
                    coexisting=True,
                    external_participant_action_receipt=(
                        action_execution.causal_intent_receipt_sha256
                    ),
                )
                retain_committed_hop(
                    consequence_hop,
                    authored_hop_count=1,
                    consumed_acoustic=consumed_acoustic,
                )
                action_consequence = {
                    **consequence_lane_truth,
                    "articulated_body_proprioceptive": {
                        "changed": len(
                            {
                                consequence[1]
                                for consequence in articulated_body_consequences
                                if consequence[5] != 0
                            }
                        ),
                        "transported": len(predecessor_body_axes) * 2,
                        "typed_source_count": len(
                            body_proprioceptive_source_receipts
                        ),
                    },
                    "causal_receipt_sha256": (
                        action_execution.causal_intent_receipt_sha256
                    ),
                    "externally_perturbed_body_receptor_count": (
                        consequence_hop[
                            "externally_perturbed_body_receptor_count"
                        ]
                    ),
                    "internal_metabolic_receptor_count": (
                        consequence_hop[
                            "metabolically_perturbed_body_receptor_count"
                        ]
                    ),
                    "organism_identity": predecessor.identity,
                    "organism_tick": consequence_hop["organism_tick"],
                    "receptor_ingress_changing_count": consequence_hop[
                        "receptor_ingress_changing_count"
                    ],
                    "receptor_ingress_quiescent_count": consequence_hop[
                        "receptor_ingress_quiescent_count"
                    ],
                    "receptor_ingress_sense_counts": dict(
                        consequence_hop["receptor_ingress_sense_counts"]
                    ),
                    "state_sha256": consequence_hop["state_sha256"],
                    "vestibular": {
                        "changed": int(
                            consequence_vestibular_yaw is not None
                        ),
                        "transported_tick_count": (
                            0
                            if consequence_vestibular_yaw is None
                            else len(consequence_vestibular_yaw[1])
                        ),
                    },
                }
                last_hop = consequence_hop
                if consequence_vestibular_yaw is not None:
                    heading, trajectory = consequence_vestibular_yaw
                    vestibular_hop = _commit_vestibular_trajectory(
                        organism,
                        heading,
                        trajectory,
                    )
                    action_vestibular_tick_count = len(trajectory)
                    committed_vestibular_tick_count += len(trajectory)
                    emitted_neuron_fractals.extend(
                        vestibular_hop["emitted_neuron_fractals"]
                    )
                    organic_mosaic_relations.extend(
                        vestibular_hop["organic_mosaic_relations"]
                    )
                    for key in totals:
                        totals[key] += vestibular_hop[key]
                    last_hop = vestibular_hop
                successor_world_body = (
                    action_authority.encoded_committed_prepared_action(
                        prepared_world
                    )
                )
                _persist_world_body(successor_world_body)
                world_persisted = True
                if defer_seal:
                    # Action moments defer exactly like actionless ones: the
                    # lived physics and the committed world action stand in
                    # resident state; only the copy cadence differs. The Nth
                    # interval, shutdown, or an explicit checkpoint seals the
                    # whole chain from the stashed predecessor.
                    if _pending_chain_predecessor_sha is None:
                        _pending_chain_predecessor_sha = predecessor.state_sha256
                    _pending_unsealed_intervals += 1
                    last_hop = dict(last_hop)
                    last_hop["sealed"] = False
                    last_hop["pending_unsealed_intervals"] = (
                        _pending_unsealed_intervals
                    )
                    published = None
                    organism_published = True
                else:
                    _seal_started = time.perf_counter()
                    sealed_observation = organism.seal_unsealed_trajectory_direct()
                    _transport_stage_wall_ms["seal"] = _transport_stage_wall_ms.get(
                        "seal", 0.0
                    ) + (time.perf_counter() - _seal_started) * 1000.0
                    if sealed_observation.organism_tick != last_hop["organism_tick"]:
                        raise RuntimeError(
                            "final resident seal changed the lived intake tick"
                        )
                    last_hop["state_sha256"] = sealed_observation.state_sha256
                    if action_consequence is not None:
                        action_consequence["state_sha256"] = (
                            sealed_observation.state_sha256
                        )
                    _chain_predecessor = (
                        _pending_chain_predecessor_sha or predecessor.state_sha256
                    )
                    published = _publish_committed_organism(
                        organism, admission, _chain_predecessor
                    )
                    _pending_unsealed_intervals = 0
                    _pending_chain_predecessor_sha = None
                    organism_published = True
                    organism.acknowledge_sealed_trajectory()
        except BaseException:
            if organism_published:
                raise
            try:
                _abort_lived_trajectory(organism)
            except (RuntimeError, ValueError) as abort_error:
                if "has no pending candidate" not in str(abort_error):
                    raise RuntimeError(
                        "resident lived intake and world rollback both failed"
                    ) from abort_error
            if world_committed:
                with action_authority.committed_prepared_action_rollback_transaction(
                    prepared_world
                ) as rollback_world:
                    rollback_world()
                if world_persisted:
                    _persist_world_body(predecessor_world_body)
            else:
                action_authority.discard_prepared_action(prepared_world)
            raise
    # CURRENT and the in-process resident owner are authoritative before any
    # observer derives a causal path. The observer consumes only the exact
    # transient frontier carried by the committed hop; it never reads back
    # into cognition, selects an action, or participates in rollback.
    if published is not None:
        _restored = RestoredNativeOrganism(
            organism=organism, pointer=published.pointer
        )
    _sealed_pointer = published.pointer if published is not None else predecessor
    selected_articulation = _newest_exact_self_heard_articulation(
        tuple(articulation_candidates),
        tuple(consumed_in_flight_acoustic),
    )
    if selected_articulation is not None:
        articulation, native_pressure_s16le = selected_articulation
    (
        active_causal_motor_traces,
        completed_causal_motor_traces,
        causal_observation_error,
    ) = _derive_causal_motor_observation_after_publication(
        _active_cross_intake_causal_motor_traces,
        tuple(causal_observation_hops),
    )
    successor_body_observation = organism.readiness()
    successor_body_state_sha256 = (
        successor_body_observation.articulated_body_state_sha256
    )
    motor_action: dict[str, Any] | None = None
    if articulated_body_consequences or signed_root_yaw or signed_root_x or signed_root_y:
        canonical_bindings = tuple(sorted(set(body_effector_bindings)))
        receipt_material = bytearray(b"guala.native-articulated-body.v1\0")
        receipt_material.extend(bytes.fromhex(predecessor.state_sha256))
        # An open (deferred) trajectory has no sealed successor yet; the
        # last sealed pointer is still the predecessor — the same
        # substitution the evidence tail already uses.
        receipt_material.extend(
            bytes.fromhex(last_hop.get("state_sha256") or predecessor.state_sha256)
        )
        receipt_material.extend(bytes.fromhex(predecessor_body_state_sha256))
        receipt_material.extend(bytes.fromhex(successor_body_state_sha256))
        for source_receipt, extent in body_proprioceptive_source_receipts:
            receipt_material.extend(bytes.fromhex(source_receipt))
            for value in extent:
                receipt_material.extend(value.to_bytes(8, "little"))
        for lineage, topology, carriers, direction in root_yaw_unit_recruitments:
            receipt_material.extend(bytes.fromhex(lineage))
            receipt_material.extend(int(topology).to_bytes(4, "little"))
            receipt_material.extend(int(carriers).to_bytes(16, "little"))
            receipt_material.extend(direction.encode("ascii"))
        for lineage, topology, carriers, axis, direction in root_translation_unit_recruitments:
            receipt_material.extend(bytes.fromhex(lineage))
            receipt_material.extend(int(topology).to_bytes(4, "little"))
            receipt_material.extend(int(carriers).to_bytes(16, "little"))
            receipt_material.extend(axis.encode("ascii"))
            receipt_material.extend(direction.encode("ascii"))
        body_transition_receipt = hashlib.sha256(receipt_material).hexdigest()
        motor_action = {
            "schema": "guala.native.articulated_body_action.v1",
            "causal_intent_receipt_sha256": (
                body_transition_receipt
                if action_execution is None
                else action_execution.causal_intent_receipt_sha256
            ),
            "body_transition_receipt_sha256": body_transition_receipt,
            "disposition": "applied",
            "moved": signed_root_yaw != 0 or signed_root_x != 0 or signed_root_y != 0 or any(
                consequence[5] != 0
                for consequence in articulated_body_consequences
            ),
            "root_motion": bool(signed_root_yaw or signed_root_x or signed_root_y),
            "signed_root_yaw_millidegrees": signed_root_yaw,
            "signed_root_x_millimetres": signed_root_x,
            "signed_root_y_millimetres": signed_root_y,
            "root_yaw_unit_recruitments": root_yaw_unit_recruitments,
            "root_translation_unit_recruitments": root_translation_unit_recruitments,
            "continuous_cognition": True,
            "body_state_before_sha256": predecessor_body_state_sha256,
            "body_state_after_sha256": successor_body_state_sha256,
            "motor_unit_recruitment_count": len(motor_unit_recruitments),
            "body_effector_bindings": [
                {
                    "source_tick": binding_source_tick,
                    "motor_lineage": lineage,
                    "axis": axis,
                    "direction": direction,
                    "outward_elementary_carriers": carriers,
                }
                for (
                    binding_source_tick,
                    lineage,
                    axis,
                    direction,
                    carriers,
                ) in canonical_bindings
            ],
            "articulated_body_consequences": [
                {
                    "source_tick": source_tick,
                    "axis": axis,
                    "unit": unit,
                    "predecessor_position": predecessor_position,
                    "successor_position": successor_position,
                    "signed_displacement": signed_displacement,
                    "toward_minimum_carriers": toward_minimum,
                    "toward_maximum_carriers": toward_maximum,
                    "opposed_carriers_per_terminal": opposed,
                    "applied_displacement_quanta": applied,
                    "stalled_carriers": stalled,
                }
                for (
                    source_tick,
                    axis,
                    unit,
                    predecessor_position,
                    successor_position,
                    signed_displacement,
                    toward_minimum,
                    toward_maximum,
                    opposed,
                    applied,
                    stalled,
                ) in articulated_body_consequences
            ],
            "body_proprioceptive_sources": [
                {
                    "source_sha256": source_receipt,
                    "source_tick": extent[0],
                    "port_count": extent[1],
                    "sample_count": extent[2],
                    "occurrence_count": extent[3],
                    "occurrence_frame_count": extent[4],
                }
                for source_receipt, extent in body_proprioceptive_source_receipts
            ],
            "motor_body_afferent_paths": [
                {
                    "body_regulation_lineage": regulation,
                    "integration_lineage": integration,
                    "receptor_lineage": receptor,
                    "receptor_sense_layer": sense_layer,
                    "receptor_topology_index": receptor_topology,
                    "sensor_id": sensor_id,
                    "substream_id": substream_id,
                }
                for (
                    regulation,
                    integration,
                    receptor,
                    sense_layer,
                    receptor_topology,
                    sensor_id,
                    substream_id,
                ) in sorted(
                    {
                        path
                        for recruitment in motor_unit_recruitments
                        for path in recruitment[4]
                    }
                )
            ],
            "prepared_recruitments": [
                {
                    "motor_lineage": lineage,
                    "motor_layer": 12,
                    "motor_topology_index": topology,
                    "outward_elementary_carriers": carriers,
                    "preparation_transfers": [
                        {
                            "sender_lineage": sender,
                            "sender_layer": sender_layer,
                            "receiver_lineage": receiver,
                            "receiver_layer": receiver_layer,
                            "parallel_ordinal": parallel_ordinal,
                            "transferred_whole_carriers": (
                                transferred_whole_carriers
                            ),
                        }
                        for (
                            sender,
                            sender_layer,
                            receiver,
                            receiver_layer,
                            parallel_ordinal,
                            transferred_whole_carriers,
                        ) in preparation_transfers
                    ],
                }
                for (
                    lineage,
                    topology,
                    carriers,
                    preparation_transfers,
                    _body_afferent_paths,
                ) in motor_unit_recruitments
            ],
            "internally_reassembled_formation_motor_path": (
                completed_causal_motor_traces.get("retained_formation")
            ),
            "externally_reassembled_formation_motor_path": (
                completed_causal_motor_traces.get(
                    "externally_reassembled_retained_formation"
                )
            ),
            "new_neuronal_fractal_motor_path": (
                completed_causal_motor_traces.get("new_neuronal_fractal")
            ),
            "affective_gradient_motor_path": (
                completed_causal_motor_traces.get("affective_gradient")
            ),
            "sensory_consequence": action_consequence,
            "vestibular_tick_count": action_vestibular_tick_count,
            "world_revision": (
                None if action_execution is None else action_execution.after.revision
            ),
            "world_state_before_sha256": (
                None
                if action_execution is None
                else action_execution.before.state_sha256
            ),
            "world_state_after_sha256": (
                None
                if action_execution is None
                else action_execution.after.state_sha256
            ),
        }
        _last_self_moved = dict(motor_action)
        _last_displacement = (
            None
            if action_execution is None
            else _world_displacement(
                action_execution.before,
                action_execution.after,
            )
        )
    _active_cross_intake_causal_motor_traces = (
        _retain_cross_intake_causal_motor_traces(
            active_causal_motor_traces,
            int(last_hop["organism_tick"]),
        )
    )
    receptor_ingress = {
        "changing_count": receptor_ingress_changing_count,
        "quiescent_count": receptor_ingress_quiescent_count,
        "sense_counts": receptor_ingress_sense_counts,
        "source_hop_count": committed_hop_count,
    }
    internally_reassembled_motor_path = completed_causal_motor_traces.get(
        "retained_formation"
    )
    internally_reassembled_thought_transitions = (
        _thought_transitions_on_completed_motor_path(
            internally_reassembled_motor_path,
            tuple(causal_observation_hops),
        )
    )
    externally_reassembled_motor_path = completed_causal_motor_traces.get(
        "externally_reassembled_retained_formation"
    )
    new_neuronal_fractal_motor_path = completed_causal_motor_traces.get(
        "new_neuronal_fractal"
    )
    affective_motor_path = completed_causal_motor_traces.get(
        "affective_gradient"
    )
    internally_reassembled_articulation_path = (
        completed_causal_motor_traces.get(
            "retained_formation_articulation"
        )
    )
    externally_reassembled_articulation_path = (
        completed_causal_motor_traces.get(
            "externally_reassembled_retained_formation_articulation"
        )
    )
    external_participant_motor_path = completed_causal_motor_traces.get(
        "external_participant_sensory"
    )
    external_participant_attention_path = completed_causal_motor_traces.get(
        "external_participant_attention"
    )
    all_externally_reassembled_motor_paths = (
        _compact_completed_external_retained_motor_paths(
            completed_causal_motor_traces
        )
    )
    motor_action_projection: dict[str, Any] | None = None
    motor_sensed_consequence: dict[str, Any] | None = None
    if motor_action is not None:
        motor_action_projection = {
            "causal_intent_receipt_sha256": motor_action[
                "causal_intent_receipt_sha256"
            ],
            "body_state_before_sha256": motor_action[
                "body_state_before_sha256"
            ],
            "body_state_after_sha256": motor_action[
                "body_state_after_sha256"
            ],
            "body_effector_binding_count": len(
                motor_action["body_effector_bindings"]
            ),
            "root_motion": motor_action["root_motion"],
            "signed_root_yaw_millidegrees": motor_action[
                "signed_root_yaw_millidegrees"
            ],
        }
        motor_sensed_consequence = {
            "body_proprioceptive_source_count": len(
                motor_action["body_proprioceptive_sources"]
            ),
            "externally_perturbed_body_receptor_count": last_hop[
                "externally_perturbed_body_receptor_count"
            ],
            "successor_organism_tick": last_hop["organism_tick"],
            "successor_state_sha256": last_hop["state_sha256"],
        }
    causal_cross_context_use: dict[str, Any] | None = None
    if motor_action is not None and internally_reassembled_motor_path is not None:
        causal_cross_context_use = {
            **internally_reassembled_motor_path,
            "causal_thought_transitions": (
                internally_reassembled_thought_transitions
            ),
            "action": dict(motor_action_projection),
            "sensed_consequence": dict(motor_sensed_consequence),
        }
    externally_reassembled_formation_causal_use: dict[str, Any] | None = None
    if motor_action is not None and externally_reassembled_motor_path is not None:
        externally_reassembled_formation_causal_use = {
            **externally_reassembled_motor_path,
            "action": dict(motor_action_projection),
            "sensed_consequence": dict(motor_sensed_consequence),
        }
    all_externally_reassembled_formation_causal_uses = (
        ()
        if motor_action is None
        else tuple(
            {
                **path,
                "action": dict(motor_action_projection),
                "sensed_consequence": dict(motor_sensed_consequence),
            }
            for path in all_externally_reassembled_motor_paths
        )
    )
    new_impression_causal_use: dict[str, Any] | None = None
    if motor_action is not None and new_neuronal_fractal_motor_path is not None:
        new_impression_causal_use = {
            **new_neuronal_fractal_motor_path,
            "action": dict(motor_action_projection),
            "sensed_consequence": dict(motor_sensed_consequence),
        }
    affective_motor_causal_use: dict[str, Any] | None = None
    if motor_action is not None and affective_motor_path is not None:
        affective_motor_causal_use = {
            **affective_motor_path,
            "action": dict(motor_action_projection),
            "sensed_consequence": dict(motor_sensed_consequence),
        }
    participant_sensory_causal_use: dict[str, Any] | None = None
    if motor_action is not None and external_participant_motor_path is not None:
        participant_sensory_causal_use = {
            **external_participant_motor_path,
            "action": dict(motor_action_projection),
            "sensed_consequence": dict(motor_sensed_consequence),
        }
    participant_sensory_attention: dict[str, Any] | None = None
    if external_participant_attention_path is not None:
        participant_sensory_attention = dict(external_participant_attention_path)
    def project_articulatory_causal_use(
        path: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if articulation is None or path is None:
            return None
        return {
            **path,
            "action": {
                key: articulation[key]
                for key in (
                    "layer_13_recruitment_count",
                    "applied_motor_quanta",
                    "stalled_motor_quanta",
                    "articulatory_body_nonquiescent_port_count",
                    "pressure_sample_count",
                    "pressure_sha256",
                )
            },
            "sensed_consequence": {
                **{
                    key: articulation[key]
                    for key in (
                        "sample_rate_hz",
                        "self_hearing_hop_count",
                        "self_hearing_transitioned_neuron_count",
                        "self_hearing_fractal_count",
                        "articulatory_body_receptor_ingress_count",
                    )
                },
                "successor_organism_tick": last_hop["organism_tick"],
                "successor_state_sha256": last_hop["state_sha256"],
            },
        }
    articulatory_causal_cross_context_use = project_articulatory_causal_use(
        internally_reassembled_articulation_path
    )
    externally_reassembled_articulation_causal_use = (
        project_articulatory_causal_use(
            externally_reassembled_articulation_path
        )
    )
    if articulation is not None and articulatory_causal_cross_context_use is not None:
        articulation["retained_formation_causal_path"] = (
            articulatory_causal_cross_context_use
        )
    if (
        articulation is not None
        and externally_reassembled_articulation_causal_use is not None
    ):
        articulation["externally_reassembled_formation_causal_path"] = (
            externally_reassembled_articulation_causal_use
        )
    global _last_reached_retina
    if _pending_reached_retina is not None:
        _last_reached_retina = {
            **_pending_reached_retina,
            "organism_tick": persisted_tick
            if (persisted_tick := last_hop.get("organism_tick")) is not None
            else None,
        }
    _last_transition_evidence = {
        **last_hop,
        "organism_identity": _sealed_pointer.identity,
        "hop_count": committed_hop_count,
        "vestibular_tick_count": committed_vestibular_tick_count,
        "intake": intake,
        "motor_action": motor_action,
        "causal_observation_error": causal_observation_error,
        "causal_cross_context_use": causal_cross_context_use,
        "externally_reassembled_formation_causal_use": (
            externally_reassembled_formation_causal_use
        ),
        "externally_reassembled_formation_causal_uses": (
            all_externally_reassembled_formation_causal_uses
        ),
        "new_impression_causal_use": new_impression_causal_use,
        "affective_motor_causal_use": affective_motor_causal_use,
        "participant_sensory_causal_use": participant_sensory_causal_use,
        "participant_sensory_attention": participant_sensory_attention,
        "articulatory_causal_cross_context_use": (
            articulatory_causal_cross_context_use
        ),
        "externally_reassembled_articulation_causal_use": (
            externally_reassembled_articulation_causal_use
        ),
        "articulation": articulation,
        "emitted_neuron_fractals": tuple(emitted_neuron_fractals),
        "physical_frontier_routes": physical_frontier_routes,
        "preceding_distinct_physical_frontier_routes": (
            preceding_distinct_physical_frontier_routes
        ),
        "reached_and_foregone_physical_frontier_routes": (
            reached_and_foregone_physical_frontier_routes
        ),
        "attention_motor_bindings": attention_motor_bindings,
        "working_causal_continuations": working_causal_continuations,
        "settled_working_frontier": settled_working_frontier,
        "physical_prediction_alternatives": physical_prediction_alternatives,
        "body_consequence_transfers": body_consequence_transfers,
        "affective_balance_trajectories": affective_balance_trajectories,
        "localized_fluid_chemistry": localized_fluid_chemistry,
        "localized_metabolic_strain_evaluated_body_receptor_lineages": (
            localized_metabolic_strain_evaluated_body_receptor_lineages
        ),
        "localized_metabolic_strain": localized_metabolic_strain,
        "organic_mosaic_relations": tuple(organic_mosaic_relations),
        "predecessor_state_sha256": predecessor.state_sha256,
        "receptor_ingress": receptor_ingress,
        "totals": dict(totals),
    }
    # A route-set change is knowable only after a later hop supplies the
    # distinct comparison frontier.  Re-evaluate once at the completed
    # transaction boundary so an exact motor-preparation transfer observed in
    # the retained qualifying interval is not discarded merely because its
    # attention classification was not yet available inside that earlier hop.
    # This does not join unrelated contacts: the helper still requires the
    # same directed sender, receiver, parallel ordinal, and carrier magnitude.
    attention_motor_bindings = _completed_transaction_attention_motor_bindings(
        attention_motor_bindings,
        _last_transition_evidence,
        tuple(motor_unit_recruitments),
    )
    _last_transition_evidence["attention_motor_bindings"] = (
        attention_motor_bindings
    )
    intrinsic_curiosity_evidence = _intrinsic_curiosity_evidence_from_transition(
        _last_transition_evidence
    )
    if intrinsic_curiosity_evidence is not None:
        _last_intrinsic_curiosity_evidence = intrinsic_curiosity_evidence
    social_experience_evidence = _social_experience_evidence_from_transition(
        _last_transition_evidence
    )
    if social_experience_evidence is not None:
        _last_social_experience_evidence = social_experience_evidence
    physical_choice_evidence = _physical_choice_evidence_from_transition(
        _last_transition_evidence
    )
    if physical_choice_evidence is not None:
        _last_tested_physical_choice_evidence = physical_choice_evidence
    (
        _sensorimotor_play_candidate,
        _last_sensorimotor_play_evidence,
    ) = _advance_bounded_sensorimotor_play_evidence(
        _sensorimotor_play_candidate,
        _last_sensorimotor_play_evidence,
        _last_transition_evidence,
        physical_choice_evidence,
        intake,
    )
    (
        _body_owned_laughter_candidate,
        _last_body_owned_laughter_evidence,
    ) = _advance_bounded_body_owned_laughter_evidence(
        _body_owned_laughter_candidate,
        _last_body_owned_laughter_evidence,
        _last_transition_evidence,
        _last_sensorimotor_play_evidence,
        intake,
    )
    (
        _reciprocal_social_play_candidate,
        _last_reciprocal_social_play_evidence,
    ) = _advance_bounded_reciprocal_social_play_evidence(
        _reciprocal_social_play_candidate,
        _last_reciprocal_social_play_evidence,
        _last_transition_evidence,
        physical_choice_evidence,
        intake,
    )
    if causal_cross_context_use is not None and (
        _last_causal_cross_context_use_evidence is None
        or "changed_contact_channel_state" in causal_cross_context_use
        or "changed_contact_channel_state"
        not in _last_causal_cross_context_use_evidence
    ):
        _last_causal_cross_context_use_evidence = {
            **causal_cross_context_use,
            "organism_identity": _sealed_pointer.identity,
            "intake": intake,
            "organism_tick": _sealed_pointer.organism_tick,
            "predecessor_state_sha256": predecessor.state_sha256,
            "state_sha256": _sealed_pointer.state_sha256,
        }
    if articulation is not None:
        _last_tested_articulation_evidence = {
            **articulation,
            "durable": last_hop.get("state_sha256") is not None,
            "intake": intake,
            "organism_tick": last_hop["organism_tick"],
            "persisted_organism_tick": _sealed_pointer.organism_tick,
            "persisted_state_sha256": _sealed_pointer.state_sha256,
            "state_sha256": last_hop.get("state_sha256"),
        }
        if native_pressure_s16le is None:
            raise RuntimeError("native articulation lost its emitted pressure")
        next_pressure_audio = {
            "intake": intake,
            "organism_tick": _sealed_pointer.organism_tick,
            "pcm_s16le": native_pressure_s16le,
            "pressure_sha256": articulation["pressure_sha256"],
            "sample_count": articulation["pressure_sample_count"],
            "sample_rate_hz": articulation["sample_rate_hz"],
        }
        _native_pressure_audio_cache = _retain_native_articulation_audio(
            _native_pressure_audio_cache,
            next_pressure_audio,
        )
    if (
        len(physical_prediction_alternatives) == 2
        and body_consequence_transfers
    ):
        _last_tested_prediction_evidence = {
            "body_consequence_transfers": body_consequence_transfers[:1],
            "intake": intake,
            "organism_tick": _sealed_pointer.organism_tick,
            "physical_prediction_alternatives": physical_prediction_alternatives,
            "state_sha256": _sealed_pointer.state_sha256,
        }
    complete_affective_balance = tuple(
        trajectory
        for trajectory in affective_balance_trajectories
        if _complete_local_affective_balance_trajectory(trajectory)
    )
    if complete_affective_balance:
        _last_tested_affective_balance_evidence = {
            "affective_balance_trajectories": complete_affective_balance[:1],
            "intake": intake,
            "organism_tick": _sealed_pointer.organism_tick,
            "state_sha256": _sealed_pointer.state_sha256,
        }
    complete_localized_fluid_chemistry = tuple(
        settlement
        for settlement in localized_fluid_chemistry
        if settlement[4][4] + settlement[4][5] > 0
        and settlement[4][6] == 0
    )
    if complete_localized_fluid_chemistry:
        _last_tested_localized_fluid_chemistry_evidence = {
            "intake": intake,
            "localized_fluid_chemistry": complete_localized_fluid_chemistry[:1],
            "organism_tick": _sealed_pointer.organism_tick,
            "state_sha256": _sealed_pointer.state_sha256,
        }
    if _pending_unsealed_intervals >= _checkpoint_every_intervals():
        _checkpoint_requested.set()
    return {
        "accepted": True,
        "ok": True,
        "hop_count": committed_hop_count,
        "vestibular_tick_count": committed_vestibular_tick_count,
        "observation": dict(_last_transition_evidence),
        "persisted": {
            "organism_tick": _sealed_pointer.organism_tick,
            "predecessor_state_sha256": predecessor.state_sha256,
            "schema": PERSISTENCE_SCHEMA,
            "state_bytes": _sealed_pointer.state_bytes,
            "state_sha256": _sealed_pointer.state_sha256,
        },
        "schema": "guala.native_admitted_intake_result.v1",
        "receptor_ingress": receptor_ingress,
        "totals": totals,
    }


RETINAL_LATTICE_AUTHORIZATION_ENV = "GUALA_AUTHORIZE_RETINAL_LATTICE_GROWTH"


def _retinal_lattice_authorized() -> bool:
    """Growth is a DELIBERATE authorized act, never a deploy side effect."""

    value = os.environ.get(RETINAL_LATTICE_AUTHORIZATION_ENV, "").strip().lower()
    return value in ("1", "true", "on", "yes")


def _perform_retinal_lattice_growth() -> dict[str, Any]:
    """Author the declared within-column contacts onto the living body.

    Same durability contract as a feed: the growth advances only the
    in-process organism until the single persist, the public observation
    cache is refreshed only after the persist succeeds, and a persist failure
    poisons the runtime (503) so no surface ever reports unpersisted state.

    The body itself enforces the physics: contacts are appended at the end,
    every existing contact keeps its index, endpoints, conductance and
    retained carrier phase, and a pair that is already contacted is refused
    rather than authored twice.
    """

    global _restored, _last_transition_evidence

    with _transition_lock:
        restored, admission = _runtime()
        organism = restored.organism
        predecessor = restored.pointer
        contacts_before = organism.observe_cohort_contacts()
        evidence = organism.prepare_authored_contacts(
            _retinal_lattice_growth_contacts()
        )
        observed = organism.commit(evidence.token)
        contacts_after = organism.observe_cohort_contacts()
        published = _publish_committed_organism(
            organism, admission, predecessor.state_sha256
        )
        _restored = RestoredNativeOrganism(
            organism=organism, pointer=published.pointer
        )
        _last_transition_evidence = {
            "cognitive_mosaic_count": observed.cognitive_mosaic_count,
            "cognitive_trace_count": observed.cognitive_trace_count,
            "complete_neuron_count": getattr(observed, "complete_neuron_count", 0),
            "developmental_resting_neuron_count": getattr(
                observed, "developmental_resting_neuron_count", 0
            ),
            "complete_neuron_fractal_count": 0,
            "current_cohort_evaluation_count": 0,
            "dsf_delivery_count": 0,
            "formation_activation_count": observed.formation_activation_count,
            "hop_count": 1,
            "intake": (
                "authored-contact-growth:"
                f"{evidence.authored_contact_count}"
            ),
            "organism_tick": observed.organism_tick,
            "partial_cue_reassembly_count": observed.partial_cue_reassembly_count,
            "physically_transitioned_neuron_count": 0,
            "predecessor_state_sha256": predecessor.state_sha256,
            "recurrent_complete_neuron_fractal_count": 0,
            "state_sha256": observed.state_sha256,
            "totals": {},
        }
        _refresh_public_observation_cache()
        return {
            "accepted": True,
            "ok": True,
            "authored_contact_count": evidence.authored_contact_count,
            "cohorts_before": [list(entry) for entry in contacts_before],
            "cohorts_after": [list(entry) for entry in contacts_after],
            "declared_surface": {
                "columns": CARD_SURFACE_COLUMNS,
                "rows": CARD_SURFACE_ROWS,
            },
            "organism_tick": observed.organism_tick,
            "persisted": {
                "organism_tick": _sealed_pointer.organism_tick,
                "predecessor_state_sha256": predecessor.state_sha256,
                "schema": PERSISTENCE_SCHEMA,
                "state_bytes": published.pointer.state_bytes,
                "state_sha256": _sealed_pointer.state_sha256,
            },
            "schema": "guala.native_authored_contact_growth_result.v1",
        }


def _unattended_time_enabled() -> bool:
    value = os.environ.get(UNATTENDED_TIME_ENV, "1").strip().lower()
    return value not in ("0", "false", "off", "no")


def _advance_passive_world_interval() -> Any:
    """Commit one world-owned material interval without a body actor.

    This advances only already-mounted physical laws. It chooses no scene,
    object, action, attention target, or meaning, and it does not retain an
    action receipt in the world's bounded body-action tail.
    """

    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt,
        AdvancePhysicalTimeCommand,
        ENVIRONMENT_PORT_ID,
        PreparedActionExecution,
        encode_command,
    )

    authority = _world()
    before = authority.observation_snapshot()
    intent = _receipt(
        {
            "duration_microseconds": CONTINUOUS_INTERVAL_MILLISECONDS * 1_000,
            "schema": "guala.passive_world_interval_intent.v1",
            "world_revision": before.revision,
            "world_state_before_sha256": before.state_sha256,
        }
    )
    prepared = authority.prepare_port_command(
        port_id=ENVIRONMENT_PORT_ID,
        command_payload=encode_command(
            AdvancePhysicalTimeCommand(
                duration_microseconds=(
                    CONTINUOUS_INTERVAL_MILLISECONDS * 1_000
                )
            )
        ),
        causal_intent_receipt_sha256=intent,
        expected_revision=before.revision,
    )
    if isinstance(prepared, ActionExecutionReceipt):
        raise RuntimeError(
            "passive world interval was refused: " + prepared.reason
        )
    if not isinstance(prepared, PreparedActionExecution):
        raise RuntimeError("passive world interval lost prepared custody")

    predecessor_world = authority.encoded_snapshot()
    committed = False
    try:
        with authority.prepared_action_visibility_transaction(prepared):
            execution = authority.commit_prepared_action(prepared)
            committed = True
            _persist_world_body(
                authority.encoded_committed_prepared_action(prepared)
            )
    except BaseException:
        if committed:
            with authority.committed_prepared_action_rollback_transaction(
                prepared
            ) as rollback_world:
                rollback_world()
            _persist_world_body(predecessor_world)
        else:
            authority.discard_prepared_action(prepared)
        raise
    return execution


def _unattended_interval_episodes(
    interval_id: str,
) -> tuple[list[tuple[Any, list[tuple[int, int]]]], dict[str, Any]]:
    """Sample one contiguous interval from the actual persistent world.

    Python performs physical transport only. It neither fabricates darkness
    nor chooses what the organism attends to or does. The world is observed
    once for this batch; each exact 250 ms hop carries that scene, the body's
    current chemical surroundings, the virtual world's true quiet acoustic
    field, standing-still body state, and current interoception.
    """

    if not WORLD_AUTHORIZED:
        raise RuntimeError("continuous experience requires the persistent world")
    environment_interval = _advance_passive_world_interval()
    snapshot = environment_interval.after
    from dsf_ai_service.substrate.w1_physical_receptors import (
        physical_receptor_substreams,
    )

    retinal_body_axes = _current_retinal_body_axes()
    retinal_heading = _retinal_heading_offset_millidegrees_from_axes(
        retinal_body_axes
    )
    retinal_transmission = _eyelid_transmission_from_axes(retinal_body_axes)
    world_streams = physical_receptor_substreams(
        snapshot,
        snapshot,
        causal_transition=False,
        before_retinal_heading_offset_millidegrees=retinal_heading,
        after_retinal_heading_offset_millidegrees=retinal_heading,
        source_time_start=Fraction(0),
        source_time_end=Fraction(INTAKE_HOP_MILLISECONDS, 1000),
    )
    luminance = _world_retinal_luminance(
        world_streams.get(PhysicalSense.SIGHT, ())
    )
    palmar_contact = _world_palmar_contact_endpoints(
        world_streams.get(PhysicalSense.TOUCH, ())
    )[1]
    tasted, smelled = _world_chemistry(snapshot, snapshot)
    times = _quiescent_hop_times()
    silence = (0.0,) * len(times)
    episodes = [
        (
            _whole_roster_hop_episode(
                f"continuous-environment-{interval_id}-hop-{hop_index}",
                times,
                luminance,
                silence,
                retinal_transmission=retinal_transmission,
                palmar_contact_trajectory=(palmar_contact,) * len(times),
                tasted=tasted,
                smelled=smelled,
            ),
            [(INTAKE_HOP_MILLISECONDS, 1000)] * LESSON_OCCURRENCE_COUNT,
        )
        for hop_index in range(UNATTENDED_HOPS_PER_INTERVAL)
    ]
    return episodes, {
        "external_luminance_present": any(level > 0.0 for level in luminance),
        "external_smell_present": bool(smelled and any(value > 0 for value in smelled)),
        "retinal_luminance_present": any(
            level * float(retinal_transmission) > 0.0 for level in luminance
        ),
        "retinal_heading_offset_millidegrees": retinal_heading,
        "retinal_transmission": [
            retinal_transmission.numerator,
            retinal_transmission.denominator,
        ],
        "passive_interval_receipt_sha256": (
            environment_interval.authority_receipt_sha256
        ),
        "world_revision_before": environment_interval.before.revision,
        "world_revision": snapshot.revision,
    }


def _guided_world_voice_episodes(
    samples: tuple[int, ...],
    sample_rate_hz: int,
) -> tuple[list[tuple[Any, list[tuple[int, int]]]], dict[str, Any]]:
    """One tutor utterance inside Guala's actual current world and body.

    This transport accepts no word, object, lesson, or meaning identifier. The
    tutor pressure coexists on one clock with the world light, local chemistry,
    mounted body lanes, and temperature that are physically present where the
    resident organism is. The world remains present after the finite utterance;
    only tutor pressure ends.
    """

    if not WORLD_AUTHORIZED:
        raise RuntimeError("grounded teaching requires the persistent world")
    if sample_rate_hz != COCHLEAR_SAMPLE_RATE_HZ:
        raise ValueError(
            "grounded teaching requires pcm_s16le mono at the mounted "
            f"{COCHLEAR_SAMPLE_RATE_HZ} Hz cochlear rate"
        )
    if not samples:
        raise ValueError("grounded teaching requires tutor pressure samples")
    if Fraction(len(samples), sample_rate_hz) > AMBIENT_INTAKE_MAX_SECONDS:
        raise ValueError("grounded tutor pressure exceeds the declared intake window")

    from dsf_ai_service.substrate.w1_physical_receptors import (
        physical_receptor_substreams,
    )

    snapshot = _world().observation_snapshot()
    retinal_body_axes = _current_retinal_body_axes()
    retinal_heading = _retinal_heading_offset_millidegrees_from_axes(
        retinal_body_axes
    )
    retinal_transmission = _eyelid_transmission_from_axes(retinal_body_axes)
    world_streams = physical_receptor_substreams(
        snapshot,
        snapshot,
        causal_transition=False,
        before_retinal_heading_offset_millidegrees=retinal_heading,
        after_retinal_heading_offset_millidegrees=retinal_heading,
        source_time_start=Fraction(0),
        source_time_end=Fraction(INTAKE_HOP_MILLISECONDS, 1000),
    )
    luminance = _world_retinal_luminance(
        world_streams.get(PhysicalSense.SIGHT, ())
    )
    palmar_contact = _world_palmar_contact_endpoints(
        world_streams.get(PhysicalSense.TOUCH, ())
    )[1]
    tasted, smelled = _world_chemistry(
        snapshot,
        snapshot,
        source_time_end=Fraction(INTAKE_HOP_MILLISECONDS, 1000),
    )
    pressure_hops = _pcm_hops(samples, sample_rate_hz)
    raw_pressure_hops = list(_raw_pcm_hops(samples, sample_rate_hz))
    cochlear_hops = _cochlear_hops(
        samples,
        sample_rate_hz,
        LESSON_ENDED_HOP_COUNT,
    )
    if len(cochlear_hops) < len(pressure_hops) + LESSON_ENDED_HOP_COUNT:
        raise ValueError("grounded tutor pressure lost its cochlear decay")

    assembly_ids: list[str] = []
    clocks: list[tuple[Fraction, ...]] = []
    signal_bodies: list[bytes] = []
    admissions: list[list[tuple[int, int]]] = []
    maximum_interval = max(
        Fraction(len(samples), sample_rate_hz),
        Fraction(INTAKE_HOP_MILLISECONDS, 1000),
    )
    for hop_index, (times, pressure) in enumerate(pressure_hops):
        assembly_ids.append(f"guided-world-voice-hop-{hop_index}")
        clocks.append(times)
        signal_bodies.append(
            _compact_whole_roster_signal_body(
                times,
                luminance,
                pressure,
                cochlear_hops[hop_index],
                None,
                tasted,
                smelled,
                retinal_transmission=retinal_transmission,
                palmar_contact=palmar_contact,
            )
        )
        admissions.append(
            [(maximum_interval.numerator, maximum_interval.denominator)]
            * LESSON_OCCURRENCE_COUNT
        )

    quiet_times = _quiescent_hop_times()
    quiet_pressure = (0.0,) * len(quiet_times)
    for ended_index in range(LESSON_ENDED_HOP_COUNT):
        assembly_ids.append(f"guided-world-voice-ended-{ended_index}")
        clocks.append(quiet_times)
        signal_bodies.append(
            _compact_whole_roster_signal_body(
                quiet_times,
                luminance,
                quiet_pressure,
                cochlear_hops[len(pressure_hops) + ended_index],
                None,
                tasted,
                smelled,
                retinal_transmission=retinal_transmission,
                palmar_contact=palmar_contact,
            )
        )
        admissions.append(
            [(maximum_interval.numerator, maximum_interval.denominator)]
            * LESSON_OCCURRENCE_COUNT
        )
        raw_pressure_hops.append(
            (0,) * (COCHLEAR_SAMPLE_RATE_HZ * INTAKE_HOP_MILLISECONDS // 1000)
        )

    episodes = settle_native_joint_source_episode_batch_from_anatomy(
        anatomy=_lesson_anatomy(),
        assembly_ids=tuple(assembly_ids),
        source_times=tuple(clocks),
        signal_bodies=tuple(signal_bodies),
    )
    planned_episodes = tuple(
        _compact_acoustic_hop_plan(episode, assembly_id, times, signal_body, raw)
        for episode, assembly_id, times, signal_body, raw in zip(
            episodes,
            assembly_ids,
            clocks,
            signal_bodies,
            raw_pressure_hops,
            strict=True,
        )
    )
    return list(zip(planned_episodes, admissions, strict=True)), {
        "audio_sample_count": len(samples),
        "retinal_luminance_present": any(
            level * float(retinal_transmission) > 0.0 for level in luminance
        ),
        "smell_present": bool(smelled and any(value > 0 for value in smelled)),
        "taste_present": bool(tasted and any(value > 0 for value in tasted)),
        "world_revision": snapshot.revision,
        "world_state_sha256": snapshot.state_sha256,
    }


def _action_consequence_episode(
    execution: Any,
    *,
    action_duration: Fraction = Fraction(1, 1_000),
    body_displacement: tuple[Fraction, ...] | None = None,
    predecessor_retinal_body_axes: tuple[Any, ...] | list[Any] | None = None,
    retinal_body_axes: tuple[Any, ...] | list[Any] | None = None,
    body_surface_contacts: tuple[Any, ...] = (),
) -> tuple[Any, list[tuple[int, int]], dict[str, Any]]:
    """One exact joint sensorium caused by one committed 1 ms body action.

    The world supplies the before/after optics, contact geometry, body motion,
    and local chemistry.  A yaw has no authored acoustic emitter, so the ears
    receive true silence.  An unchanged receptor lane remains present and
    quiescent; no lane is labelled changed merely because an action occurred.
    """

    from dsf_ai_service.substrate.w1_physical_receptors import (
        physical_receptor_substreams,
    )

    if action_duration <= 0:
        raise ValueError("action consequence duration must be positive")
    action_sample_count = action_duration * COCHLEAR_SAMPLE_RATE_HZ
    if action_sample_count.denominator != 1:
        raise ValueError("action duration left the mounted acoustic sample clock")
    action_sample_index = action_sample_count.numerator
    hop_sample_count = (
        COCHLEAR_SAMPLE_RATE_HZ * INTAKE_HOP_MILLISECONDS // 1_000
    )
    if not 0 < action_sample_index < hop_sample_count:
        raise ValueError("action duration left its one-hop sensory consequence")
    times = tuple(
        sorted(set(_quiescent_hop_times()) | {action_duration})
    )
    after_axes = (
        _current_retinal_body_axes()
        if retinal_body_axes is None
        else tuple(retinal_body_axes)
    )
    after_retinal_heading = _retinal_heading_offset_millidegrees_from_axes(
        after_axes
    )
    after_retinal_transmission = _eyelid_transmission_from_axes(after_axes)
    before_axes = (
        after_axes
        if predecessor_retinal_body_axes is None
        else tuple(predecessor_retinal_body_axes)
    )
    before_retinal_heading = (
        _retinal_heading_offset_millidegrees_from_axes(before_axes)
    )
    before_retinal_transmission = _eyelid_transmission_from_axes(before_axes)
    world_streams = physical_receptor_substreams(
        execution.before,
        execution.after,
        causal_transition=True,
        before_retinal_heading_offset_millidegrees=before_retinal_heading,
        after_retinal_heading_offset_millidegrees=after_retinal_heading,
        source_time_start=times[0],
        source_time_end=action_duration,
    )
    before_luminance, after_luminance = _world_retinal_luminance_endpoints(
        world_streams.get(PhysicalSense.SIGHT, ())
    )
    taste_endpoints, smell_endpoints = _world_chemistry_endpoints(
        execution.before,
        execution.after,
        source_time_end=action_duration,
    )
    before_taste, after_taste = taste_endpoints
    before_smell, after_smell = smell_endpoints

    touch_streams = world_streams.get(PhysicalSense.TOUCH, ())
    palmar_streams = tuple(
        stream
        for stream in touch_streams
        if stream.sensor_id == "W1-body-surface-receptors"
        and stream.substream_id == "palmar-contact"
    )
    if len(palmar_streams) != 1:
        raise RuntimeError("the world lost its unique palmar contact channel")
    palmar_endpoints = tuple(
        Fraction(value).limit_denominator(1_000_000)
        for value in palmar_streams[0].normalized_signal
    )
    if (
        len(palmar_endpoints) != 2
        or any(value not in {Fraction(0), Fraction(1)} for value in palmar_endpoints)
    ):
        raise RuntimeError("palmar contact left its exact binary boundary")
    palmar_contact_trajectory = tuple(
        palmar_endpoints[0] if time < action_duration else palmar_endpoints[1]
        for time in times
    )

    body_surface_contact_trajectories = [
        (Fraction(0),) * len(times)
        for _ in range(CONTACT_SHEET_SITE_COUNT)
    ]
    body_surface_contact_records: list[dict[str, object]] = []
    for contact in body_surface_contacts:
        topology_index = contact.recipient_cutaneous_topology_index
        if (
            isinstance(topology_index, bool)
            or not isinstance(topology_index, int)
            or not 0 <= topology_index < CONTACT_SHEET_SITE_COUNT
            or any(body_surface_contact_trajectories[topology_index])
        ):
            raise ValueError("body-surface contact changed cutaneous anatomy")
        occupancy = (
            contact.physical.contact_area_square_micrometres
            / contact.recipient_site_area_square_micrometres
        )
        if occupancy <= 0 or occupancy > 1:
            raise ValueError("body-surface contact occupancy left its exact site")
        # The explicit surface pair is in contact for this bounded physical
        # interval.  Its successor is not retained as an authored pose; the
        # following world interval therefore carries the separate release.
        body_surface_contact_trajectories[topology_index] = tuple(
            occupancy if time <= action_duration else Fraction(0)
            for time in times
        )
        phases = contact.physical_phases
        if len(phases) != 3:
            raise ValueError("body-surface contact phase anatomy changed")
        physical = contact.physical
        heat_to_recipient = sum(
            phase.conductive_heat_to_a_nanojoules
            for phase in phases
        )
        normal_work = sum(
            phase.normal_work_into_interface_nanojoules
            for phase in phases
        )
        tangential_work = sum(
            phase.tangential_dissipated_work_nanojoules
            for phase in phases
        )
        peak_normal_load = max(
            phase.successor_normal_load_millinewtons
            for phase in phases
        )
        body_surface_contact_records.append(
            {
                "contact_area_square_micrometres": [
                    physical.contact_area_square_micrometres.numerator,
                    physical.contact_area_square_micrometres.denominator,
                ],
                "conductive_heat_to_recipient_nanojoules": [
                    heat_to_recipient.numerator,
                    heat_to_recipient.denominator,
                ],
                "normal_load_millinewtons": [
                    peak_normal_load.numerator,
                    peak_normal_load.denominator,
                ],
                "normal_work_nanojoules": [
                    normal_work.numerator,
                    normal_work.denominator,
                ],
                "tangential_work_nanojoules": [
                    tangential_work.numerator,
                    tangential_work.denominator,
                ],
                "topology_index": topology_index,
            }
        )

    surface_trajectories = tuple(
        tuple(before if time < action_duration else after for time in times)
        for before, after in zip(
            before_luminance,
            after_luminance,
            strict=True,
        )
    )
    taste_trajectories = (
        tuple(
            tuple(before if time < action_duration else after for time in times)
            for before, after in zip(before_taste, after_taste, strict=True)
        )
        if before_taste is not None and after_taste is not None
        else None
    )
    smell_trajectories = (
        tuple(
            tuple(before if time < action_duration else after for time in times)
            for before, after in zip(before_smell, after_smell, strict=True)
        )
        if before_smell is not None and after_smell is not None
        else None
    )
    thermal_trajectories = None
    thermal_changed = 0
    if THERMAL_PORT_COUNT:
        before_thermal, after_thermal = _thermal_body_endpoints(execution)
        thermal_trajectories = tuple(
            tuple(before if time < action_duration else after for time in times)
            for before, after in zip(before_thermal, after_thermal, strict=True)
        )
        thermal_changed = sum(
            left != right
            for left, right in zip(
                before_thermal, after_thermal, strict=True
            )
        )
    episode = _whole_roster_hop_episode(
        (
            "native-action-consequence-"
            f"{execution.causal_intent_receipt_sha256}"
        ),
        times,
        after_luminance,
        (0.0,) * len(times),
        retinal_transmission=(
            *(
                before_retinal_transmission
                if time < action_duration
                else after_retinal_transmission
                for time in times
            ),
        ),
        tasted=after_taste,
        smelled=after_smell,
        moved=body_displacement,
        displacement_trajectories=(
            tuple(
                tuple(
                    value if time <= action_duration else Fraction(0)
                    for time in times
                )
                for value in body_displacement
            )
        ) if body_displacement is not None else None,
        palmar_contact_trajectory=palmar_contact_trajectory,
        body_surface_contact_trajectories=tuple(
            body_surface_contact_trajectories
        ),
        surface_trajectories=surface_trajectories,
        taste_trajectories=taste_trajectories,
        smell_trajectories=smell_trajectories,
        thermal_trajectories=thermal_trajectories,
        raw_pressure_samples=(0,) * hop_sample_count,
        raw_additional_sample_indices=(action_sample_index,),
    )

    def changed_count(
        before: tuple[Any, ...] | None,
        after: tuple[Any, ...] | None,
    ) -> int:
        before_values = before or ()
        after_values = after or ()
        if len(before_values) != len(after_values):
            raise ValueError("action consequence changed receptor anatomy")
        return sum(left != right for left, right in zip(before_values, after_values))

    admitted_before_luminance = tuple(
        level * float(before_retinal_transmission) for level in before_luminance
    )
    admitted_after_luminance = tuple(
        level * float(after_retinal_transmission) for level in after_luminance
    )
    visual_changed = changed_count(
        admitted_before_luminance,
        admitted_after_luminance,
    )
    taste_changed = changed_count(before_taste, after_taste)
    smell_changed = changed_count(before_smell, after_smell)
    lane_truth = {
        "action_duration_microseconds": int(action_duration * 1_000_000),
        "action_receipt_sha256": execution.causal_intent_receipt_sha256,
        "before_retinal_heading_offset_millidegrees": before_retinal_heading,
        "after_retinal_heading_offset_millidegrees": after_retinal_heading,
        "before_retinal_transmission": [
            before_retinal_transmission.numerator,
            before_retinal_transmission.denominator,
        ],
        "after_retinal_transmission": [
            after_retinal_transmission.numerator,
            after_retinal_transmission.denominator,
        ],
        "auditory": {"changed": 0, "transported": EAR_PORT_COUNT},
        "chemical": {
            "smell_changed": smell_changed,
            "smell_transported": SMELL_PORT_COUNT,
            "taste_changed": taste_changed,
            "taste_transported": TASTE_PORT_COUNT,
        },
        "proprioceptive": {
            "changed": 0,
            "sensor_id": ARTICULATORY_BODY_SENSOR_ID,
            "transported": ARTICULATORY_BODY_PORT_COUNT,
        },
        "thermal": {
            "changed": thermal_changed,
            "sensor_id": THERMAL_SENSOR_ID,
            "transported": THERMAL_PORT_COUNT,
        },
        "tactile": {
            "body_surface_contacts": body_surface_contact_records,
            "changed": (
                int(
                    palmar_contact_trajectory[0]
                    != palmar_contact_trajectory[-1]
                )
                + len(body_surface_contact_records)
            ),
            "material_channels_unmounted": 5,
            "transported": TOUCH_PORT_COUNT,
        },
        "visual": {
            "changed": visual_changed,
            "transported": CARD_SURFACE_PORT_COUNT,
        },
    }
    return (
        episode,
        [
            (INTAKE_HOP_MILLISECONDS, 1_000)
        ] * LESSON_OCCURRENCE_COUNT,
        lane_truth,
    )


# One bounded witness of her last applied self-caused step (surfaced as
# her_last_step). The walking machinery these paragraphs once described was
# retired; this slot is the permitted actuator/consequence remnant.
_last_self_moved: dict[str, Any] | None = None



_UNATTENDED_EXACT_ENERGY_KEYS = (
    "available_energy_zeptojoules",
    "spent_energy_zeptojoules",
    "thermal_energy_zeptojoules",
    "dissipated_energy_zeptojoules",
)


def _attempt_unattended_interval() -> dict[str, Any]:
    """Deliver one continuous world interval when the organism is free.

    The transition lock is taken NON-blocking: when any external intake (a
    lesson) is waiting for or holds it, unattended time simply steps
    aside — it never waits on, delays, or contends with an external cause. An
    exhausted body pauses unattended time honestly (rest reactions pay fuel).
    Every delivered interval commits its hops and persists exactly once,
    exactly like a lesson, and the truth-coupled evidence records only measured
    change: energy-ledger movement, retained-state settling, or genuinely
    nothing.
    """

    global _last_unattended_evidence, _last_unattended_pause

    if not _unattended_time_enabled():
        _last_unattended_pause = {
            "delivered": False,
            "outcome": "disabled",
            "reason": f"unattended time is disabled by {UNATTENDED_TIME_ENV}",
        }
        return _last_unattended_pause
    # JOE'S LAW, 2026-09-02, verbatim: "nothing — NOTHING — locks a moment."
    # Three waiting policies died here on his direct order: the unsealed-
    # lived-time pause (a program stopping her life to protect a ledger),
    # the yield-to-waiting-lesson deferral, and the skip-when-busy
    # non-blocking acquire (a silently dropped beat). If custody is behind,
    # the custodian is asked — her life is not stopped. The one thing that
    # remains is the physical settlement borrow below: her body settles one
    # moment at a time the way a heart beats one beat at a time. Arrivals
    # during a settlement are not refused or deferred by POLICY — they take
    # the very next settlement. The full same-moment merge (everything
    # present entering ONE settlement together) is the chartered completion
    # of this law.
    if _pending_unsealed_intervals >= _unsealed_interval_ceiling():
        _checkpoint_requested.set()
    _transition_lock.acquire()
    try:
        if _restored is None or _admission is None:
            _last_unattended_pause = {
                "delivered": False,
                "outcome": "organism_unavailable",
                "reason": _boot_error or "native resident organism is unavailable",
            }
            return _last_unattended_pause
        before = _native_record()
        # Energy exhaustion is native physical state, not a transport veto.
        # The mounted powered-environment contact can settle only when an
        # interval reaches native cohort physics; refusing here would prevent
        # the exact recovery law from ever observing the exhausted body.
        interval_id = str(uuid.uuid4())
        _interval_started = time.perf_counter()
        _stage_totals_before = dict(_transport_stage_wall_ms)
        _runtime_totals_before = dict(RUNTIME_PHASE_WALL_MS)
        try:
            _episodes_started = time.perf_counter()
            episodes, environment = _unattended_interval_episodes(interval_id)
            _episodes_wall_ms = (time.perf_counter() - _episodes_started) * 1000.0
            intake_reason = f"continuous-environment:{interval_id}"
            result = _perform_admitted_intake_locked(
                episodes, intake_reason, defer_seal=True
            )
            after = _native_record()
        except HTTPException as error:
            _last_unattended_pause = {
                "delivered": False,
                "outcome": "interval_refused",
                "reason": f"HTTPException: {error.detail}",
            }
            print(
                "ERROR: guala unattended interval refused: "
                f"{_last_unattended_pause['reason']}",
                file=sys.stderr,
                flush=True,
            )
            return _last_unattended_pause
        except (RuntimeError, TypeError, ValueError) as error:
            _last_unattended_pause = {
                "delivered": False,
                "outcome": "interval_refused",
                "reason": f"{type(error).__name__}: {error}",
            }
            print(
                "ERROR: guala unattended interval refused: "
                f"{_last_unattended_pause['reason']}",
                file=sys.stderr,
                flush=True,
            )
            return _last_unattended_pause
        energy_coordinate_changes = {
            key: before[key] != after[key]
            for key in _UNATTENDED_EXACT_ENERGY_KEYS
        }
        measured = {
            "energy_coordinate_changes": energy_coordinate_changes,
            "exact_energy_coordinates_resident": True,
            "exact_energy_coordinates_transported": False,
        }
        measured["physically_transitioned_neuron_count"] = result["totals"][
            "physically_transitioned_neuron_count"
        ]
        measured["complete_neuron_fractal_count"] = result["totals"][
            "complete_neuron_fractal_count"
        ]
        measured["metabolically_perturbed_body_receptor_count"] = result[
            "totals"
        ]["metabolically_perturbed_body_receptor_count"]
        measured["rest_recovered_neuron_count"] = result["totals"][
            "rest_recovered_neuron_count"
        ]
        measured["partial_cue_reassembly_count"] = result["totals"][
            "partial_cue_reassembly_count"
        ]
        energy_moved = any(energy_coordinate_changes.values())
        settled = measured["physically_transitioned_neuron_count"] > 0
        motor_action = result["observation"].get("motor_action")
        if isinstance(motor_action, dict) and motor_action.get("moved") is True:
            category = "native_causal_action_observed"
        elif settled and (
            environment["external_luminance_present"]
            or environment["external_smell_present"]
        ):
            category = "continuous_environment_observed"
        elif energy_moved:
            category = "self_maintenance_observed"
        elif settled:
            category = "retained_state_settling_observed"
        else:
            category = "no_internal_cause"
        _stage_wall_ms = {
            stage: round(
                _transport_stage_wall_ms.get(stage, 0.0)
                - _stage_totals_before.get(stage, 0.0),
                1,
            )
            for stage in (
                "native_settlement",
                "native_primary",
                "native_self_hearing",
                "native_action_consequence",
                "seal",
                "custody_stage",
                "custody_publish",
            )
        }
        for phase in ("rust_advance", "python_validation"):
            _stage_wall_ms[phase] = round(
                RUNTIME_PHASE_WALL_MS.get(phase, 0.0)
                - _runtime_totals_before.get(phase, 0.0),
                1,
            )
        _stage_wall_ms["world_and_episode_build"] = round(_episodes_wall_ms, 1)
        _stage_wall_ms["interval_total"] = round(
            (time.perf_counter() - _interval_started) * 1000.0, 1
        )
        # Wall time no named stage claims: world persistence, evidence
        # validation, record assembly, observation refresh. Kept explicit so
        # overhead cannot disappear between the named stages.
        _stage_wall_ms["unattributed"] = round(
            max(
                0.0,
                _stage_wall_ms["interval_total"]
                - sum(
                    _stage_wall_ms.get(stage, 0.0)
                    for stage in (
                        "native_settlement",
                        "seal",
                        "custody_stage",
                        "custody_publish",
                        "world_and_episode_build",
                    )
                ),
            ),
            1,
        )
        print(
            "guala-transport-stopwatch "
            + " ".join(
                f"{stage}={_stage_wall_ms[stage]}ms"
                for stage in sorted(_stage_wall_ms)
            )
            + f" intake={interval_id}",
            flush=True,
        )
        _last_unattended_evidence = {
            "category": category,
            "declared_interval_milliseconds": CONTINUOUS_INTERVAL_MILLISECONDS,
            "sealed": result.get("sealed", True),
            "pending_unsealed_intervals": result.get(
                "pending_unsealed_intervals", 0
            ),
            "transport_wall_milliseconds": _stage_wall_ms,
            "hop_count": result["hop_count"],
            "intake": intake_reason,
            "measured": measured,
            "motor_action": motor_action,
            "organism_tick": after["organism_tick"],
            "receptor_ingress": result["receptor_ingress"],
            "retinal_heading_offset_millidegrees": environment[
                "retinal_heading_offset_millidegrees"
            ],
            "state_sha256": after["state_sha256"],
            "passive_interval_receipt_sha256": environment[
                "passive_interval_receipt_sha256"
            ],
            "world_revision_before": environment[
                "world_revision_before"
            ],
            "world_revision": environment["world_revision"],
        }
        _last_unattended_pause = None
        # Publish one observation only after the unattended evidence is
        # complete.  The inner transition performs no observer work: every
        # lived caller owns exactly one correctly ordered cache refresh.
        # The 4 Hz beat is the ONE caller allowed to use the change gate.
        _refresh_public_observation_cache(quiet_beat=True)
        return {"delivered": True, "outcome": category, **_last_unattended_evidence}
    finally:
        _transition_lock.release()


def _unattended_time_loop() -> None:
    """Continuously advance contiguous physical world intervals."""

    global _last_unattended_pause

    while not _unattended_stop.is_set():
        try:
            _attempt_unattended_interval()
        except BaseException as error:
            _last_unattended_pause = {
                "delivered": False,
                "outcome": "interval_error",
                "reason": f"{type(error).__name__}: {error}",
            }
            print(
                "ERROR: guala unattended interval failed: "
                f"{_last_unattended_pause['reason']}",
                file=sys.stderr,
                flush=True,
            )
        # Native settlement may take longer than the represented world
        # interval.  Never treat that wall-clock overrun as a debt to replay:
        # doing so starts the next expensive settlement immediately and turns
        # either slow or refused physics into an unbounded catch-up loop.  One
        # declared interval is the existing transport cadence and is also the
        # minimum yield before another attempt.  This changes no organism time
        # or physical state; it only bounds the Python transport loop.
        _unattended_stop.wait(CONTINUOUS_INTERVAL_MILLISECONDS / 1000)


def _start_unattended_time() -> None:
    global _unattended_thread

    if not _unattended_time_enabled():
        return
    if _unattended_thread is not None and _unattended_thread.is_alive():
        return
    _unattended_stop.clear()
    _unattended_thread = threading.Thread(
        target=_unattended_time_loop,
        name="guala-unattended-time",
        daemon=True,
    )
    _unattended_thread.start()


def _stop_unattended_time() -> None:
    global _unattended_thread

    _unattended_stop.set()
    thread = _unattended_thread
    if thread is not None:
        # One interval is one atomic native intake. Do not discard the thread
        # handle while that intake is still committing: doing so can leave an
        # unseen second writer alive across test isolation or process
        # shutdown. The stop event prevents another interval from beginning;
        # this join waits only for the already-entered bounded intake.
        thread.join()
    _unattended_thread = None


def _raster_luminance(image: Any) -> tuple[float, ...]:
    """Row-major area-averaged luminance of one raster in [0, 1].

    Pillow BOX resampling integrates the true pixel field over each receptor
    site's area; the result is the physical mean luminance in [0, 1].  One
    reduction law for every visual raster that reaches the retina: approved
    card surfaces and live camera frames go through this exact path.
    """

    from PIL import Image

    reduced = image.convert("L").resize(
        (CARD_SURFACE_COLUMNS, CARD_SURFACE_ROWS),
        Image.Resampling.BOX,
    )
    return tuple(value / 255.0 for value in reduced.tobytes())


def _card_surface_luminance(surface_path: Path) -> tuple[float, ...]:
    """Row-major area-averaged luminance of one approved card raster."""

    from PIL import Image

    with Image.open(surface_path) as image:
        return _raster_luminance(image)


def _live_frame_luminance(frame_bytes: bytes) -> tuple[float, ...]:
    """Row-major area-averaged luminance of one posted live camera frame."""

    from PIL import Image

    with Image.open(io.BytesIO(frame_bytes)) as image:
        return _raster_luminance(image)


def _pcm_hops(
    samples: tuple[int, ...],
    sample_rate_hz: int,
    additional_sample_indices: tuple[int, ...] = (),
) -> list[tuple[tuple[Fraction, ...], tuple[float, ...]]]:
    """Slice PCM into successive hop occurrences of true retained instants.

    Each hop covers at most ``INTAKE_HOP_MILLISECONDS`` of the capture.
    Decimation inside a hop keeps every stride-th physical sample with its
    exact within-hop source time; retained frames respect the ratified
    transport limits (``MAX_NATIVE_SAMPLES_PER_SUBSTREAM`` and the hop frame
    bound). Adjacent hops share their exact boundary sample. The shared point
    contributes no duplicate elapsed time and prevents a transport boundary
    from deleting the interval between two samples. After a finite capture
    ends, the remainder of its final hop is physical silence.
    """

    hop_samples = max(2, sample_rate_hz * INTAKE_HOP_MILLISECONDS // 1000)
    signal_samples = list(samples)
    remainder = len(signal_samples) % hop_samples
    if remainder:
        signal_samples.extend([0] * (hop_samples - remainder))
    signal_samples.append(0)
    hops: list[tuple[tuple[Fraction, ...], tuple[float, ...]]] = []
    for start in range(0, len(signal_samples) - 1, hop_samples):
        window = signal_samples[start : start + hop_samples + 1]
        indices = tuple(sorted(set(
            _retained_hop_sample_indices(hop_samples, sample_rate_hz)
        ) | {
            index - start
            for index in additional_sample_indices
            if start <= index <= start + hop_samples
        }))
        times = tuple(Fraction(index, sample_rate_hz) for index in indices)
        signal = tuple(window[index] / 32768.0 for index in indices)
        hops.append((times, signal))
    return hops


def _raw_pcm_hops(
    samples: tuple[int, ...], sample_rate_hz: int
) -> list[tuple[int, ...]]:
    """Retain exact signed pressure per authored transport hop.

    This is the pre-cochlear companion to `_pcm_hops`: the same final partial
    hop is completed by physical silence, but no decimation or nonlinear
    receptor work occurs here.
    """

    if sample_rate_hz != COCHLEAR_SAMPLE_RATE_HZ:
        raise ValueError("raw acoustic custody requires the mounted cochlear rate")
    hop_samples = max(2, sample_rate_hz * INTAKE_HOP_MILLISECONDS // 1_000)
    padded = list(samples)
    remainder = len(padded) % hop_samples
    if remainder:
        padded.extend([0] * (hop_samples - remainder))
    return [
        tuple(padded[start : start + hop_samples])
        for start in range(0, len(padded), hop_samples)
    ]


def _retained_hop_sample_indices(
    hop_samples: int,
    sample_rate_hz: int,
) -> tuple[int, ...]:
    """Return the mounted receptor's exact observation instants in one hop.

    The authorized cochlea consumes every 16-kHz pressure sample inside its
    gammatone mechanics, then emits one physical envelope observation per
    declared 160-sample window.  Repeating that already-settled envelope on
    the retired PCM transport grid creates no additional sensory evidence.
    Without a cochlea, retain the pre-existing bounded PCM transport grid.
    """

    if COCHLEAR_EARS_AUTHORIZED:
        if sample_rate_hz != COCHLEAR_SAMPLE_RATE_HZ:
            raise ValueError(
                "the declared cochlea observes only 16 kHz captures; a capture at "
                "another rate cannot be transduced without resampling it, and no "
                "resampler is declared"
            )
        if hop_samples % COCHLEAR_OBSERVATION_HOP_SAMPLES:
            raise ValueError(
                "the intake hop does not contain whole cochlear observation windows"
            )
        return tuple(
            range(
                0,
                hop_samples + 1,
                COCHLEAR_OBSERVATION_HOP_SAMPLES,
            )
        )
    frame_budget = min(
        MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
        INTAKE_HOP_MAX_FRAMES,
    )
    stride = max(1, -(-(hop_samples + 1) // frame_budget))
    indices = list(range(0, hop_samples + 1, stride))
    if indices[-1] != hop_samples:
        indices.append(hop_samples)
    return tuple(indices)


def _articulatory_body_hops(
    packed_trajectories: bytes,
    sample_count: int,
    sample_rate_hz: int,
    additional_sample_indices: tuple[int, ...] = (),
) -> list[tuple[tuple[Fraction, ...], ...]]:
    """Decimate the four exact native body trajectories on PCM hop clocks."""

    expected_bytes = (
        ARTICULATORY_BODY_PORT_COUNT * sample_count * struct.calcsize("<h")
    )
    if len(packed_trajectories) != expected_bytes:
        raise ValueError("native articulatory body bytes changed cardinality")
    raw = array("h")
    raw.frombytes(packed_trajectories)
    if sys.byteorder != "little":
        raw.byteswap()
    hop_samples = max(2, sample_rate_hz * INTAKE_HOP_MILLISECONDS // 1000)
    channels = []
    for channel_index, span in enumerate(ARTICULATORY_BODY_DECLARED_SPANS):
        start = channel_index * sample_count
        values = raw[start : start + sample_count]
        if any(abs(value) > span for value in values):
            raise ValueError("native articulatory body exceeded its declared span")
        terminal_value = values[-1]
        remainder = len(values) % hop_samples
        if remainder:
            values.extend([terminal_value] * (hop_samples - remainder))
        values.append(terminal_value)
        channels.append(values)
    if not channels or len({len(values) for values in channels}) != 1:
        raise ValueError("native articulatory body channels lost their shared clock")
    hops: list[tuple[tuple[Fraction, ...], ...]] = []
    for start in range(0, len(channels[0]) - 1, hop_samples):
        indices = tuple(sorted(set(
            _retained_hop_sample_indices(hop_samples, sample_rate_hz)
        ) | {
            index - start
            for index in additional_sample_indices
            if start <= index <= start + hop_samples
        }))
        hops.append(
            tuple(
                tuple(Fraction(values[start + index], span) for index in indices)
                for values, span in zip(
                    channels, ARTICULATORY_BODY_DECLARED_SPANS, strict=True
                )
            )
        )
    return hops


def _articulatory_body_nonquiescent_port_count(
    packed_trajectories: bytes,
    sample_count: int,
) -> int:
    """Count local body sites whose exact native trajectory actually moved."""

    expected_bytes = (
        ARTICULATORY_BODY_PORT_COUNT * sample_count * struct.calcsize("<h")
    )
    if len(packed_trajectories) != expected_bytes:
        raise ValueError("native articulatory body bytes changed cardinality")
    raw = array("h")
    raw.frombytes(packed_trajectories)
    if sys.byteorder != "little":
        raw.byteswap()
    return sum(
        any(raw[index * sample_count : (index + 1) * sample_count])
        for index in range(ARTICULATORY_BODY_PORT_COUNT)
    )


def _cochlear_hops(
    samples: tuple[int, ...],
    sample_rate_hz: int,
    trailing_silent_hops: int = 0,
    additional_sample_indices: tuple[int, ...] = (),
) -> list[tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]]]:
    """Slice one continuous capture into per-hop tonotopic band signals.

    ONE causal pass of the cochlea runs over the whole capture — plus
    ``trailing_silent_hops`` hops of true silence, so that cochlear ringing
    decays across the end of the utterance exactly as a real basilar membrane's
    does instead of being cut off at a transport boundary.  Each returned hop
    carries its own retained instants (one per
    ``COCHLEAR_OBSERVATION_HOP_SAMPLES`` samples of the capture) and one
    non-negative band RMS per tonotopic place.

    Hop boundaries are the SAME transport hop windows ``_pcm_hops`` uses, so a
    lesson's optical hop and its acoustic hops cover the same physical instant
    of the world; they carry different retained-instant grids because a band
    envelope and a decimated waveform are different observations of it.
    """

    if sample_rate_hz != COCHLEAR_SAMPLE_RATE_HZ:
        raise ValueError(
            "the declared cochlea observes only 16 kHz captures; a capture at "
            "another rate cannot be transduced without resampling it, and no "
            "resampler is declared"
        )
    hop_samples = max(2, sample_rate_hz * INTAKE_HOP_MILLISECONDS // 1000)
    signal = [value / 32768.0 for value in samples]
    # The capture ends mid-hop; what physically follows it is silence, so the
    # final partial hop is completed with true silence rather than truncated.
    # Nothing is fabricated: a capture that has stopped IS silence at the ear.
    remainder = len(signal) % hop_samples
    if remainder:
        signal.extend([0.0] * (hop_samples - remainder))
    signal.extend([0.0] * (trailing_silent_hops * hop_samples))
    physical_sample_count = len(signal)
    envelopes = _cochlear_envelopes(
        signal + [0.0] * COCHLEAR_OBSERVATION_HOP_SAMPLES
    )
    hops: list[tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]]] = []
    for start in range(0, physical_sample_count, hop_samples):
        indices = tuple(sorted(set(
            _retained_hop_sample_indices(hop_samples, sample_rate_hz)
        ) | {
            index - start
            for index in additional_sample_indices
            if start <= index <= start + hop_samples
        }))
        if (start + hop_samples) // COCHLEAR_OBSERVATION_HOP_SAMPLES >= len(envelopes):
            break
        times = tuple(Fraction(index, sample_rate_hz) for index in indices)
        # A band RMS is constant over the observation window it averages, so
        # the value at a retained instant is the envelope of the window that
        # instant falls in.  Nothing is interpolated or invented; the hop's own
        # retained instants are the same instants its optical occurrence keeps,
        # so sight and sound observe the same moments of the same world.
        frame_of = [
            envelopes[(start + index) // COCHLEAR_OBSERVATION_HOP_SAMPLES]
            for index in indices
        ]
        hops.append(
            (
                times,
                tuple(
                    tuple(frame[channel] for frame in frame_of)
                    for channel in range(COCHLEAR_CHANNELS_PER_EAR)
                ),
            )
        )
    return hops


def _read_manifest_card(card_id: str) -> dict[str, Any]:
    experiences = _manifest_experiences(
        CURRICULUM_ROOT / "card_experience_manifest-v1.json",
        "guala.external_tutor_card_experience_manifest.v1",
    )
    for experience in experiences:
        if experience.get("experience_id") == card_id:
            return experience
    raise KeyError(card_id)


def _read_manifest_song(song_id: str) -> dict[str, Any]:
    experiences = _manifest_experiences(
        CURRICULUM_ROOT / "songs" / "song_experience_manifest-v1.json",
        "guala.external_tutor_song_experience_manifest.v1",
    )
    for experience in experiences:
        if experience.get("experience_id") == song_id:
            return experience
    raise KeyError(song_id)


def _verified_media_path(record: object, label: str) -> Path:
    if not isinstance(record, dict):
        raise ValueError(f"curriculum {label} record changed")
    relative = record.get("path")
    digest = record.get("sha256")
    if not isinstance(relative, str) or not isinstance(digest, str):
        raise ValueError(f"curriculum {label} record changed")
    path = CURRICULUM_ROOT / relative.removeprefix("guala_curriculum/")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != digest:
        raise ValueError(f"curriculum {label} bytes differ from the signed manifest")
    return path


def _read_tutor_wav(path: Path, expected_sample_count: object) -> tuple[int, tuple[int, ...]]:
    with wave.open(str(path), "rb") as stream:
        if (
            stream.getnchannels() != 1
            or stream.getsampwidth() != 2
            or stream.getframerate() != 16_000
        ):
            raise ValueError("tutor audio differs from the signed pcm_s16le mono 16kHz format")
        frame_count = stream.getnframes()
        if frame_count != expected_sample_count:
            raise ValueError("tutor audio sample count differs from the signed manifest")
        body = stream.readframes(frame_count)
    return 16_000, struct.unpack(f"<{frame_count}h", body)


def _quiescent_hop_times() -> tuple[Fraction, ...]:
    """Exact retained instants of one dark, silent 250 ms hop."""

    hop_samples = (
        COCHLEAR_SAMPLE_RATE_HZ * INTAKE_HOP_MILLISECONDS // 1000
    )
    return tuple(
        Fraction(index, COCHLEAR_SAMPLE_RATE_HZ)
        for index in _retained_hop_sample_indices(
            hop_samples,
            COCHLEAR_SAMPLE_RATE_HZ,
        )
    )


class _AcousticHopPlan:
    """One intake-local whole-sensorium hop with exact pre-cochlear pressure.

    The plan is transport custody only. It is bounded by one authored hop,
    never enters the organism, and is released with the request. Rebuilding
    changes only the acoustic pressure before the one cochlear pass; every
    other captured physical trajectory remains the exact authored value.
    """

    __slots__ = ("episode", "external_pressure_samples", "_rebuild")

    def __init__(
        self,
        episode: Any,
        external_pressure_samples: tuple[int, ...],
        rebuild: Callable[[tuple[int, ...]], Any],
    ) -> None:
        if not external_pressure_samples:
            raise ValueError("acoustic hop plan requires physical pressure samples")
        self.episode = episode
        self.external_pressure_samples = external_pressure_samples
        self._rebuild = rebuild

    def __getattr__(self, name: str) -> Any:
        return getattr(self.episode, name)

    def composed_with(self, self_pressure_samples: tuple[int, ...]) -> Any:
        composed: list[int] = []
        for index, external in enumerate(self.external_pressure_samples):
            own = self_pressure_samples[index] if index < len(self_pressure_samples) else 0
            total = int(external) + int(own)
            if not -32_768 <= total <= 32_767:
                raise ValueError("external plus self-pressure exceeds signed-16 anatomy")
            composed.append(total)
        return self._rebuild(tuple(composed))


def _whole_roster_hop_episode(
    assembly_id: str,
    times: tuple[Fraction, ...],
    surface_levels: tuple[float, ...],
    ear_signal: tuple[float, ...],
    cochlear: tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]] | None = None,
    contact: tuple[float, ...] | None = None,
    *,
    palmar_contact_trajectory: (
        tuple[float, ...] | tuple[Fraction, ...] | None
    ) = None,
    body_surface_contact_trajectories: (
        tuple[tuple[Fraction, ...], ...] | None
    ) = None,
    retinal_transmission: Fraction | tuple[Fraction, ...],
    tasted: tuple[Fraction, ...] | None = None,
    smelled: tuple[Fraction, ...] | None = None,
    moved: tuple[Fraction, ...] | None = None,
    displacement_trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
    surface_trajectories: tuple[tuple[float, ...], ...] | None = None,
    taste_trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
    smell_trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
    articulated: tuple[tuple[float, ...], ...] | None = None,
    thermal_trajectories: tuple[tuple[Fraction, ...], ...] | None = None,
    raw_pressure_samples: tuple[int, ...] | None = None,
    raw_additional_sample_indices: tuple[int, ...] = (),
    _retain_acoustic_plan: bool = True,
) -> Any:
    """One hop over the whole declared roster on one shared clock.

    ``surface_levels`` carries one constant luminance per card receptor site
    for the hop; dark sites carry their true 0.0 quiescent samples exactly as
    the ordinary ended hops do.

    ``ear_signal`` is the decimated ambient pressure the legacy (unauthorized)
    ear ports carry on the surface's own clock.  ``cochlear`` is that hop's own
    (times, per-band signals) for one cochlea when cochlear ears are
    AUTHORIZED; both ears receive it.  ``None`` declares true silence — a
    lawful acoustic state, never an absent sense.  Exactly one of the two is
    real for a given process.

    The sensorium is one occurrence because these fields coexist. Declared
    groups retain the separate receptor anatomies without evaluating the full
    joint field once per organ.
    """
    global _pending_reached_retina
    _pending_reached_retina = {
        "values": tuple(float(v) for v in surface_levels),
        "assembly_id": assembly_id,
    }

    frame_count = len(times)
    incident_retinal_signals = surface_trajectories or tuple(
        (surface_levels[index],) * frame_count
        for index in range(CARD_SURFACE_PORT_COUNT)
    )
    if len(incident_retinal_signals) != CARD_SURFACE_PORT_COUNT or any(
        len(signal) != frame_count for signal in incident_retinal_signals
    ):
        raise ValueError("retinal trajectories changed anatomy or clock")
    transmission = _retinal_transmission_trajectory(
        retinal_transmission,
        frame_count,
    )
    retinal_signals = tuple(
        tuple(
            level * float(transmission[frame_index])
            for frame_index, level in enumerate(signal)
        )
        for signal in incident_retinal_signals
    )
    observed = {
        PhysicalSense.SIGHT: tuple(
            _card_surface_substream(
                row,
                column,
                times,
                retinal_signals[row * CARD_SURFACE_COLUMNS + column],
            )
            for row in range(CARD_SURFACE_ROWS)
            for column in range(CARD_SURFACE_COLUMNS)
        ),
        PhysicalSense.SOUND: _sound_ports(times, ear_signal, cochlear),
    }
    touch_ports = _touch_ports(
        times,
        contact,
        palmar_contact_trajectory,
        body_surface_contact_trajectories,
    )
    if touch_ports:
        observed[PhysicalSense.TOUCH] = touch_ports
    # NOTHING IS BEING EATEN unless something is: every channel carries its
    # true zero, which is a lawful state and not an absent sense.
    taste_ports = _taste_ports(times, tasted, taste_trajectories)
    if taste_ports:
        observed[PhysicalSense.TASTE] = taste_ports
    smell_ports = _smell_ports(times, smelled, smell_trajectories)
    if smell_ports:
        observed[PhysicalSense.SMELL] = smell_ports
    # STANDING STILL IS A LAWFUL STATE, not an absent sense.
    displacement_ports = _displacement_ports(
        times,
        moved,
        displacement_trajectories,
    )
    if displacement_ports:
        observed[PhysicalSense.BODY] = (
            observed.get(PhysicalSense.BODY, ()) + displacement_ports
        )
    observed[PhysicalSense.BODY] = (
        observed.get(PhysicalSense.BODY, ())
        + _articulatory_body_ports(times, articulated)
        + _thermal_ports(times, thermal_trajectories)
    )
    if cochlear is not None and cochlear[0] != times:
        raise ValueError("coexisting sensor structures do not share one source clock")
    occurrences = (
        _occurrence(
            tuple(range(LESSON_PORT_COUNT)),
            times,
            frame_count,
            _lesson_port_groups(),
        ),
    )
    episode = settle_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed,
        states=_sense_states(observed),
        occurrences=occurrences,
    )
    if not _retain_acoustic_plan:
        return episode
    if raw_pressure_samples is None:
        if cochlear is None and times == _quiescent_hop_times():
            raw_pressure_samples = (0,) * (
                COCHLEAR_SAMPLE_RATE_HZ * INTAKE_HOP_MILLISECONDS // 1_000
            )
        else:
            return episode

    def rebuild(composed: tuple[int, ...]) -> Any:
        pressure_hops = _pcm_hops(
            composed,
            COCHLEAR_SAMPLE_RATE_HZ,
            raw_additional_sample_indices,
        )
        cochlear_hops = _cochlear_hops(
            composed,
            COCHLEAR_SAMPLE_RATE_HZ,
            additional_sample_indices=raw_additional_sample_indices,
        )
        if len(pressure_hops) != 1 or len(cochlear_hops) != 1:
            raise ValueError("one acoustic hop plan changed physical cardinality")
        rebuilt_times, rebuilt_pressure = pressure_hops[0]
        if rebuilt_times != times or cochlear_hops[0][0] != times:
            raise ValueError("composed pressure changed the shared physical clock")
        return _whole_roster_hop_episode(
            assembly_id,
            times,
            surface_levels,
            rebuilt_pressure,
            cochlear_hops[0] if COCHLEAR_EARS_AUTHORIZED else None,
            contact,
            palmar_contact_trajectory=palmar_contact_trajectory,
            body_surface_contact_trajectories=body_surface_contact_trajectories,
            retinal_transmission=retinal_transmission,
            tasted=tasted,
            smelled=smelled,
            moved=moved,
            displacement_trajectories=displacement_trajectories,
            surface_trajectories=surface_trajectories,
            taste_trajectories=taste_trajectories,
            smell_trajectories=smell_trajectories,
            articulated=articulated,
            thermal_trajectories=thermal_trajectories,
            raw_pressure_samples=composed,
            raw_additional_sample_indices=raw_additional_sample_indices,
            _retain_acoustic_plan=False,
        )

    return _AcousticHopPlan(episode, raw_pressure_samples, rebuild)


def _compact_whole_roster_signal_body(
    times: tuple[Fraction, ...],
    surface_levels: tuple[float, ...],
    ear_signal: tuple[float, ...],
    cochlear: tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]] | None,
    contact: tuple[float, ...] | None,
    tasted: tuple[Fraction, ...] | None,
    smelled: tuple[Fraction, ...] | None,
    moved: tuple[Fraction, ...] | None = None,
    *,
    retinal_transmission: Fraction,
    palmar_contact: Fraction | float = Fraction(0),
    surface_trajectories: tuple[tuple[float, ...], ...] | None = None,
) -> bytes:
    """One port-major binary64 sensorium with no per-sample Python objects."""

    frame_count = len(times)
    transmission = _retinal_transmission_trajectory(
        retinal_transmission,
        frame_count,
    )
    if len(surface_levels) != CARD_SURFACE_PORT_COUNT or len(ear_signal) != frame_count:
        raise ValueError("compact lesson sight or legacy-ear width changed")
    signals = array("d")

    def constant_ports(values: Iterable[object], width: int, label: str) -> None:
        held = tuple(values)
        if len(held) != width:
            raise ValueError(f"compact lesson {label} width changed")
        for value in held:
            signals.extend([float(value)] * frame_count)

    if surface_trajectories is None:
        constant_ports(
            tuple(level * float(retinal_transmission) for level in surface_levels),
            CARD_SURFACE_PORT_COUNT,
            "retina",
        )
    else:
        if len(surface_trajectories) != CARD_SURFACE_PORT_COUNT:
            raise ValueError("compact lesson retinal trajectory width changed")
        for trajectory in surface_trajectories:
            if len(trajectory) != frame_count:
                raise ValueError("compact lesson retinal trajectory clock changed")
            signals.extend(
                level * float(transmission[frame_index])
                for frame_index, level in enumerate(trajectory)
            )
    for _ in range(LEGACY_EAR_PORT_COUNT):
        signals.extend(ear_signal)
    if COCHLEAR_EARS_AUTHORIZED:
        if cochlear is None or cochlear[0] != times:
            raise ValueError("compact lesson cochlea changed its shared clock")
        bands = cochlear[1]
        if len(bands) != COCHLEAR_CHANNELS_PER_EAR:
            raise ValueError("compact lesson cochlear width changed")
        for _ in range(EAR_COUNT):
            for band in bands:
                if len(band) != frame_count:
                    raise ValueError("compact lesson cochlear frame count changed")
                signals.extend(band)
    if TOUCH_RECEPTORS_AUTHORIZED:
        constant_ports(
            contact if contact is not None else (0.0,) * CONTACT_SHEET_SITE_COUNT,
            CONTACT_SHEET_SITE_COUNT,
            "contact sheet",
        )
        exact_palmar_contact = Fraction(palmar_contact).limit_denominator(
            1_000_000
        )
        if exact_palmar_contact not in {Fraction(0), Fraction(1)}:
            raise ValueError("compact palmar contact left its binary boundary")
        constant_ports((exact_palmar_contact,), 1, "palmar contact")
    # SENSE_ORDER is sight, sound, touch, smell, taste, body.  The compact
    # body follows that physical order exactly; it does not follow the order
    # in which the card material helper happens to return taste and smell.
    if CHEMORECEPTION_AUTHORIZED:
        constant_ports(
            smelled if smelled is not None else (Fraction(0),) * SMELL_SITE_COUNT,
            SMELL_SITE_COUNT,
            "olfactory epithelium",
        )
        constant_ports(
            tasted if tasted is not None else (Fraction(0),) * TASTE_SITE_COUNT,
            TASTE_SITE_COUNT,
            "gustatory surface",
        )
    if VESTIBULAR_AUTHORIZED:
        constant_ports(
            moved if moved is not None else (Fraction(0),) * DISPLACEMENT_SITE_COUNT,
            DISPLACEMENT_SITE_COUNT,
            "body displacement",
        )
    constant_ports(
        (Fraction(0),) * ARTICULATORY_BODY_PORT_COUNT,
        ARTICULATORY_BODY_PORT_COUNT,
        "quiescent articulatory body",
    )
    if THERMAL_PORT_COUNT:
        current_temperatures = _thermal_body_temperatures()
        span = THERMAL_MAX_MILLIKELVIN - THERMAL_MIN_MILLIKELVIN
        constant_ports(
            tuple(
                (temperature - THERMAL_MIN_MILLIKELVIN) / span
                for temperature in current_temperatures
            ),
            THERMAL_PORT_COUNT,
            "tonic thermal body",
        )
    if len(signals) != LESSON_PORT_COUNT * frame_count:
        raise ValueError("compact lesson signals do not cover the authored anatomy")
    if sys.byteorder != "little":
        signals.byteswap()
    return signals.tobytes()


def _compact_acoustic_hop_plan(
    episode: Any,
    assembly_id: str,
    times: tuple[Fraction, ...],
    signal_body: bytes,
    raw_pressure_samples: tuple[int, ...],
) -> _AcousticHopPlan:
    """Retain raw pressure while keeping every compact non-acoustic port exact."""

    frame_count = len(times)

    def rebuild(composed: tuple[int, ...]) -> Any:
        pressure_hops = _pcm_hops(composed, COCHLEAR_SAMPLE_RATE_HZ)
        cochlear_hops = _cochlear_hops(composed, COCHLEAR_SAMPLE_RATE_HZ)
        if len(pressure_hops) != 1 or len(cochlear_hops) != 1:
            raise ValueError("compact acoustic plan changed hop cardinality")
        rebuilt_times, legacy_pressure = pressure_hops[0]
        if rebuilt_times != times or cochlear_hops[0][0] != times:
            raise ValueError("compact acoustic plan changed shared clock")

        signals = array("d")
        signals.frombytes(signal_body)
        if sys.byteorder != "little":
            signals.byteswap()
        acoustic_offset = CARD_SURFACE_PORT_COUNT * frame_count
        for ear_index in range(LEGACY_EAR_PORT_COUNT):
            start = acoustic_offset + ear_index * frame_count
            signals[start : start + frame_count] = array("d", legacy_pressure)
        acoustic_offset += LEGACY_EAR_PORT_COUNT * frame_count
        if COCHLEAR_EARS_AUTHORIZED:
            bands = cochlear_hops[0][1]
            for ear_index in range(EAR_COUNT):
                for band_index, band in enumerate(bands):
                    port_index = (
                        ear_index * COCHLEAR_CHANNELS_PER_EAR + band_index
                    )
                    start = acoustic_offset + port_index * frame_count
                    signals[start : start + frame_count] = array("d", band)
        if sys.byteorder != "little":
            signals.byteswap()
        rebuilt = settle_native_joint_source_episode_batch_from_anatomy(
            anatomy=_lesson_anatomy(),
            assembly_ids=(assembly_id,),
            source_times=(times,),
            signal_bodies=(signals.tobytes(),),
        )
        if len(rebuilt) != 1:
            raise ValueError("compact acoustic plan lost one episode")
        return rebuilt[0]

    return _AcousticHopPlan(episode, raw_pressure_samples, rebuild)


def _partial_presentation_levels(
    luminance: tuple[float, ...],
) -> tuple[float, ...]:
    """The glimpsed top strip of the real card; the rest is truly dark.

    The lit subset is deterministic from the ports' declared topology
    coordinates: the first ``PARTIAL_PRESENTATION_SITE_COUNT`` sites in
    row-major (row, column) order carry their real area-averaged card
    luminance; every other card site carries the true dark 0.0 sample.  No
    pixel is fabricated: the lit values are the same physical card raster the
    full presentation delivers, restricted to that card region.
    """

    return tuple(
        (
            luminance[row * CARD_SURFACE_COLUMNS + column]
            if row * CARD_SURFACE_COLUMNS + column
            < PARTIAL_PRESENTATION_SITE_COUNT
            else 0.0
        )
        for row in range(CARD_SURFACE_ROWS)
        for column in range(CARD_SURFACE_COLUMNS)
    )


def _partial_card_lesson_hop_episodes(
    card_id: str,
    presentation_ms: int,
    luminance: tuple[float, ...],
) -> list[tuple[Any, list[tuple[int, int]]]]:
    """Glimpse hops of part of a familiar card: partial light, no tutor.

    One driven hop carries the real card luminance of the chain-prefix card
    region with true dark samples on the remaining card sites and true
    silence at both ears (the tutor does not speak), then the presentation
    genuinely ends and the ratified count of dark, silent hops lets the
    recurrence current settle through the authored chain contacts.  The same
    builder path as every other hop declares the occurrences, so the subset
    ports still settle jointly and quiescent ports still carry their samples.

    Measured outcome (2026-08-05, headless, alphabet-a, after two full
    lessons): every hop commits lawfully, the cue is a proper strict subset
    (12 of the 27 formation members), and no mosaic is admitted.  The block
    is upstream of the cue choice and is energetic, not topological:

    - The ratified retinal law transduces 2 * L * T zeptojoules per site
      (reference irradiance 4, aperture 1, absorptance 1/2, coupling 1).  A
      250 ms hop of the brightest real card site (L ~ 0.85) delivers ~0.43
      zJ, below the +1 zJ plastic support barrier, so the gate free energy
      stays positive, no conformation opens, gate conductance stays zero,
      and no current can cross the 500 pS chain contacts.  The dark card
      sites therefore never change and `admit_physical_mosaic` refuses with
      RecurrenceDidNotChangeEveryMember.
    - Raising the dwell until a gate can open requires 2 * L * T in
      (1, 3.25] zJ AND an exact multiple of the 1/16 zJ dissipation lattice
      (36 quanta capacity).  Real card sites carry distinct 8-bit luminances,
      so on one shared presentation clock at most the sites sharing one exact
      luminance value land on the lattice; any other lit site is refused
      outright (DissipationNotQuantized).  A spatial card region cannot be
      lit above the barrier lawfully.
    - Measured separately: once any gate does open, the injected charge
      never leaves the 27-site chain — 600 dark hops (150 s) after a single
      lattice-aligned flip still showed 3-21 neurons changing per hop and no
      quiescence, so no experience is retained from an electrically active
      presentation either.  The card lessons that do retain an experience
      retain one with zero electrical activity.

    Nothing here is forced: the mode delivers the honest partial cue and the
    observation reports the physics' real answer.
    """

    times = _quiescent_hop_times()
    silence = (0.0,) * len(times)
    dark = (0.0,) * CARD_SURFACE_PORT_COUNT
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    episodes: list[tuple[Any, list[tuple[int, int]]]] = [
        (
            _whole_roster_hop_episode(
                f"curriculum-card-{card_id}-partial-glimpse",
                times,
                _partial_presentation_levels(luminance),
                silence,
                retinal_transmission=retinal_transmission,
            ),
            [(presentation_ms, 1000)] * LESSON_OCCURRENCE_COUNT,
        )
    ]
    for ended_index in range(PARTIAL_PRESENTATION_ENDED_HOP_COUNT):
        episodes.append(
            (
                _whole_roster_hop_episode(
                    f"curriculum-card-{card_id}-partial-ended-{ended_index}",
                    times,
                    dark,
                    silence,
                    retinal_transmission=retinal_transmission,
                ),
                [(presentation_ms, 1000)] * LESSON_OCCURRENCE_COUNT,
            )
        )
    return episodes


def _card_lesson_hop_episodes(
    card_id: str,
    experience: dict[str, Any],
    presentation: str = "full",
    *,
    spoken_voice: tuple[int, tuple[int, ...]] | None = None,
) -> list[tuple[Any, list[tuple[int, int]]]]:
    """Build one card lesson.

    ``spoken_voice`` replaces the signed tutor recording with a live human
    voice for THIS lesson — same card light, same tactile footprint, same
    shared clock, same everything else.  It exists because a recorded tutor
    is not the person teaching: the acceptance bar (Joe, 2026-08-06) is that
    HE names the card while she sees and feels it, all in ONE experience,
    and a separate microphone intake is three signals rather than one.
    """

    presentation_ms = experience.get("presentation_milliseconds")
    if (
        isinstance(presentation_ms, bool)
        or not isinstance(presentation_ms, int)
        or presentation_ms <= 0
    ):
        raise ValueError("curriculum presentation window changed")
    surface_path = _verified_media_path(experience.get("surface"), "surface")
    # A RECORDED TUTOR IS NO LONGER REQUIRED TO EXIST (2026-08-07).
    #
    # Every card used to carry a signed WAV, which made a recording studio
    # the bottleneck on her whole vocabulary: no recording, no card, no
    # word.  A card taught in a living person's voice needs no recording at
    # all, so the audio is resolved only where it is actually going to be
    # used.  A card WITHOUT one is teachable by voice and honestly refuses
    # the tutored route; a card WITH one is unchanged in every respect.
    audio_path = (
        _verified_media_path(experience.get("tutor_audio"), "tutor_audio")
        if spoken_voice is None and experience.get("tutor_audio") is not None
        else None
    )
    if presentation == "partial":
        if spoken_voice is not None:
            raise ValueError(
                "a spoken lesson cannot be a partial presentation: a partial "
                "cue is a strict subset of the card's own light with no "
                "utterance at all, so there is nothing for a voice to "
                "accompany"
            )
        return _partial_card_lesson_hop_episodes(
            card_id,
            presentation_ms,
            _card_surface_luminance(surface_path),
        )
    if spoken_voice is None:
        if audio_path is None:
            raise ValueError(
                f"card {card_id!r} has no recorded tutor voice, so there is "
                "no utterance to present: teach it by speaking to her "
                f"({SPOKEN_LESSON_ENDPOINT})"
            )
        tutor_audio = experience.get("tutor_audio")
        expected_samples = (
            tutor_audio.get("sample_count") if isinstance(tutor_audio, dict) else None
        )
        sample_rate, samples = _read_tutor_wav(audio_path, expected_samples)
    else:
        sample_rate, samples = spoken_voice
    audio_seconds = Fraction(len(samples), sample_rate)
    presentation_seconds = Fraction(presentation_ms, 1000)
    if audio_seconds > presentation_seconds:
        raise ValueError("tutor audio exceeds the signed presentation window")

    luminance = _card_surface_luminance(surface_path)
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    # THE CARD IS AN OBJECT, not a picture: while it is presented, it rests
    # against the contact sheet for exactly as long as it is lit and the tutor
    # speaks.  Its tactile surface is derived from its OWN declared raster
    # geometry — the outline, never the ink — so the same object reaches every
    # mounted sense of this body on one shared clock.  UNAUTHORIZED, no contact
    # sheet is declared and this is the empty tuple.
    contact = (
        _card_tactile_occupancy(surface_path) if TOUCH_RECEPTORS_AUTHORIZED else None
    )
    # NO SENSE STANDS ALONE FOR AN EXPERIENCE, and an object reaches every
    # sense a body has (Joe, 2026-08-08).  A printed card is not a picture
    # with a sound attached: it is a thing, and a thing has a look, a feel,
    # a smell and a taste at the same time.  The deck declares ONE physical
    # stock — one paper, one ink — for every card in it, because inventing a
    # different chemistry per letter would be inventing a fact about a real
    # object.  Present while the card is, gone when it is gone.
    tasted, smelled = _card_material()
    # One shared clock per hop: the tutor speaks while the static card
    # surface is lit, so every declared receptor site is co-observed on the
    # tutor audio's exact retained instants of that hop.
    hops = _pcm_hops(samples, sample_rate)
    raw_pressure_hops = list(_raw_pcm_hops(samples, sample_rate))
    if not hops:
        raise ValueError("tutor audio does not span one intake hop")
    # The cochlea runs once over the utterance AND over the lesson's ended
    # hops, so the ringing of the last syllable decays into the silence that
    # follows it rather than being truncated at a transport boundary.
    # UNAUTHORIZED, no cochlea is declared and none is run: the legacy ear
    # ports carry the same decimated pressure waveform they carry today.
    cochlear_hops: list[
        tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]]
    ] = []
    ended_cochlear: list[
        tuple[tuple[Fraction, ...], tuple[tuple[float, ...], ...]] | None
    ] = [None] * LESSON_ENDED_HOP_COUNT
    if COCHLEAR_EARS_AUTHORIZED:
        cochlear_hops = _cochlear_hops(samples, sample_rate, LESSON_ENDED_HOP_COUNT)
        if len(cochlear_hops) < len(hops) + LESSON_ENDED_HOP_COUNT:
            raise ValueError(
                "tutor audio does not span its declared cochlear observation hops"
            )
        ended_cochlear = list(
            cochlear_hops[len(hops) : len(hops) + LESSON_ENDED_HOP_COUNT]
        )
    assembly_ids: list[str] = []
    clocks: list[tuple[Fraction, ...]] = []
    signal_bodies: list[bytes] = []
    admissions: list[list[tuple[int, int]]] = []
    for hop_index, (shared_times, audio_signal) in enumerate(hops):
        cochlear = cochlear_hops[hop_index] if COCHLEAR_EARS_AUTHORIZED else None
        assembly_ids.append(f"curriculum-card-{card_id}-hop-{hop_index}")
        clocks.append(shared_times)
        signal_bodies.append(
            _compact_whole_roster_signal_body(
                shared_times,
                luminance,
                audio_signal,
                cochlear,
                contact,
                tasted,
                smelled,
                retinal_transmission=retinal_transmission,
            )
        )
        # The maximum causal interval is the signed manifest's presentation
        # window: independent environment authority authored by the
        # curriculum, never derived from the occurrence.
        admissions.append([(presentation_ms, 1000)] * LESSON_OCCURRENCE_COUNT)
    # The presentation genuinely ends: the surface is unlit and the tutor is
    # silent.  Each ended hop declares the dark surface as its own exact
    # optical occurrence with true dark samples — exactly as the lit hops and
    # the glimpse builder declare theirs — so the retinal cohort physically
    # settles at presentation end and the stimulus-boundary law (ratified
    # 2026-08-05) can close the pending experience on a settlement whose
    # interval truly carried zero exogenous optical energy.  A hop that
    # folded the dark surface into a combined occurrence would deliver no
    # settlement at all: the organism would never be told the light went out.
    quiescent_times = _quiescent_hop_times()
    quiescent_signal = (0.0,) * len(quiescent_times)
    dark = (0.0,) * CARD_SURFACE_PORT_COUNT
    for ended_index in range(LESSON_ENDED_HOP_COUNT):
        assembly_ids.append(f"curriculum-card-{card_id}-ended-{ended_index}")
        clocks.append(quiescent_times)
        signal_bodies.append(
            _compact_whole_roster_signal_body(
                quiescent_times,
                dark,
                quiescent_signal,
                ended_cochlear[ended_index],
                None,
                None,
                None,
                retinal_transmission=retinal_transmission,
            )
        )
        admissions.append([(presentation_ms, 1000)] * LESSON_OCCURRENCE_COUNT)
        raw_pressure_hops.append(
            (0,) * (COCHLEAR_SAMPLE_RATE_HZ * INTAKE_HOP_MILLISECONDS // 1000)
        )
    episodes = settle_native_joint_source_episode_batch_from_anatomy(
        anatomy=_lesson_anatomy(),
        assembly_ids=tuple(assembly_ids),
        source_times=tuple(clocks),
        signal_bodies=tuple(signal_bodies),
    )
    planned_episodes = tuple(
        _compact_acoustic_hop_plan(episode, assembly_id, times, signal_body, raw)
        for episode, assembly_id, times, signal_body, raw in zip(
            episodes,
            assembly_ids,
            clocks,
            signal_bodies,
            raw_pressure_hops,
            strict=True,
        )
    )
    return list(zip(planned_episodes, admissions, strict=True))


@lru_cache(maxsize=36)
def _approved_song_surface_luminance(object_id: str) -> tuple[float, ...]:
    """One exact signed card surface addressed by the song's visual program."""

    experiences = _manifest_experiences(
        CURRICULUM_ROOT / "card_experience_manifest-v1.json",
        "guala.external_tutor_card_experience_manifest.v1",
    )
    for experience in experiences:
        surface = experience.get("surface")
        if isinstance(surface, dict) and surface.get("object_id") == object_id:
            return _card_surface_luminance(
                _verified_media_path(surface, "song visual surface")
            )
    raise ValueError(f"song visual surface {object_id!r} is not approved")


@lru_cache(maxsize=1)
def _alphabet_song_surface_set_luminance() -> tuple[float, ...]:
    """Arrange the 26 signed alphabet cards simultaneously across the retina."""

    from PIL import Image

    experience = _read_manifest_song("alphabet-song-cc-by-sa-3.0-v1")
    visual = experience.get("visual_program")
    object_ids = visual.get("object_ids") if isinstance(visual, dict) else None
    if not isinstance(object_ids, list) or len(object_ids) != 26:
        raise ValueError("alphabet song simultaneous surface set changed")
    tile_width = 256
    tile_height = 320
    canvas = Image.new(
        "RGB",
        (CARD_SURFACE_COLUMNS * tile_width, CARD_SURFACE_ROWS * tile_height),
        (0, 0, 0),
    )
    card_experiences = _manifest_experiences(
        CURRICULUM_ROOT / "card_experience_manifest-v1.json",
        "guala.external_tutor_card_experience_manifest.v1",
    )
    for index, object_id in enumerate(object_ids):
        if not isinstance(object_id, str):
            raise ValueError("alphabet song surface identity changed")
        surface = next(
            (
                item.get("surface")
                for item in card_experiences
                if isinstance(item.get("surface"), dict)
                and item["surface"].get("object_id") == object_id
            ),
            None,
        )
        path = _verified_media_path(surface, "alphabet song visual surface")
        with Image.open(path) as source:
            tile = source.convert("RGB").resize(
                (tile_width, tile_height),
                Image.Resampling.BOX,
            )
        x = (index % CARD_SURFACE_COLUMNS) * tile_width
        y = (index // CARD_SURFACE_COLUMNS) * tile_height
        canvas.paste(tile, (x, y))
    return _raster_luminance(canvas)


def _song_visual_program(
    experience: dict[str, Any],
    *,
    audio_sample_count: int,
) -> tuple[str, tuple[tuple[int, int, tuple[float, ...]], ...]]:
    """Validate the signed visual program and return exact sample intervals."""

    visual = experience.get("visual_program")
    if not isinstance(visual, dict):
        raise ValueError("song visual program changed")
    claim = visual.get("alignment_claim")
    if claim == "simultaneous_alphabet_surface_set_only":
        if visual.get("per_letter_timing_authority") is not False:
            raise ValueError("alphabet song invented per-letter timing authority")
        roster = _alphabet_song_surface_set_luminance()
        return claim, ((0, audio_sample_count, roster),)
    if claim != "exact_sample_interval_surface_sequence":
        raise ValueError("song visual alignment claim changed")
    slots = visual.get("slots")
    if not isinstance(slots, list) or not slots:
        raise ValueError("counting song visual slots changed")
    intervals: list[tuple[int, int, tuple[float, ...]]] = []
    expected_first = 0
    for slot in slots:
        if not isinstance(slot, dict):
            raise ValueError("counting song visual slot changed")
        first = slot.get("first_sample_index")
        count = slot.get("sample_count")
        object_id = slot.get("object_id")
        if (
            isinstance(first, bool)
            or not isinstance(first, int)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count <= 0
            or not isinstance(object_id, str)
            or first != expected_first
        ):
            raise ValueError("counting song visual intervals are not contiguous")
        intervals.append(
            (first, first + count, _approved_song_surface_luminance(object_id))
        )
        expected_first = first + count
    if expected_first != audio_sample_count:
        raise ValueError("counting song visual intervals do not cover its waveform")
    return claim, tuple(intervals)


def _song_lesson_hop_episodes(
    song_id: str,
    experience: dict[str, Any],
) -> tuple[list[tuple[Any, list[tuple[int, int]]]], str]:
    """Build one signed song as synchronized light, pressure, and body state."""

    audio = experience.get("audio")
    audio_path = _verified_media_path(audio, "song audio")
    expected_samples = audio.get("sample_count") if isinstance(audio, dict) else None
    sample_rate, samples = _read_tutor_wav(audio_path, expected_samples)
    alignment_claim, intervals = _song_visual_program(
        experience,
        audio_sample_count=len(samples),
    )
    pressure_hops = _pcm_hops(samples, sample_rate)
    raw_pressure_hops = list(_raw_pcm_hops(samples, sample_rate))
    cochlear_hops = _cochlear_hops(
        samples,
        sample_rate,
        LESSON_ENDED_HOP_COUNT,
    )
    if len(cochlear_hops) < len(pressure_hops) + LESSON_ENDED_HOP_COUNT:
        raise ValueError("song cochlear observation hops changed")
    hop_samples = sample_rate * INTAKE_HOP_MILLISECONDS // 1000
    presentation_ms = (len(samples) * 1000 + sample_rate - 1) // sample_rate
    assembly_ids: list[str] = []
    clocks: list[tuple[Fraction, ...]] = []
    signal_bodies: list[bytes] = []
    admissions: list[list[tuple[int, int]]] = []
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    interval_index = 0
    for hop_index, (times, pressure) in enumerate(pressure_hops):
        rosters: list[tuple[float, ...]] = []
        for source_time in times:
            sample_index = min(
                hop_index * hop_samples + int(source_time * sample_rate),
                len(samples) - 1,
            )
            while sample_index >= intervals[interval_index][1]:
                interval_index += 1
            rosters.append(intervals[interval_index][2])
        trajectories = tuple(
            tuple(roster[site] for roster in rosters)
            for site in range(CARD_SURFACE_PORT_COUNT)
        )
        assembly_ids.append(f"curriculum-song-{song_id}-hop-{hop_index}")
        clocks.append(times)
        signal_bodies.append(
            _compact_whole_roster_signal_body(
                times,
                rosters[0],
                pressure,
                cochlear_hops[hop_index],
                None,
                None,
                None,
                retinal_transmission=retinal_transmission,
                surface_trajectories=trajectories,
            )
        )
        admissions.append([(presentation_ms, 1000)] * LESSON_OCCURRENCE_COUNT)
    dark_times = _quiescent_hop_times()
    dark_pressure = (0.0,) * len(dark_times)
    dark_surface = (0.0,) * CARD_SURFACE_PORT_COUNT
    for ended_index in range(LESSON_ENDED_HOP_COUNT):
        assembly_ids.append(f"curriculum-song-{song_id}-ended-{ended_index}")
        clocks.append(dark_times)
        signal_bodies.append(
            _compact_whole_roster_signal_body(
                dark_times,
                dark_surface,
                dark_pressure,
                cochlear_hops[len(pressure_hops) + ended_index],
                None,
                None,
                None,
                retinal_transmission=retinal_transmission,
            )
        )
        admissions.append([(presentation_ms, 1000)] * LESSON_OCCURRENCE_COUNT)
        raw_pressure_hops.append(
            (0,) * (COCHLEAR_SAMPLE_RATE_HZ * INTAKE_HOP_MILLISECONDS // 1000)
        )
    episodes = settle_native_joint_source_episode_batch_from_anatomy(
        anatomy=_lesson_anatomy(),
        assembly_ids=tuple(assembly_ids),
        source_times=tuple(clocks),
        signal_bodies=tuple(signal_bodies),
    )
    planned_episodes = tuple(
        _compact_acoustic_hop_plan(episode, assembly_id, times, signal_body, raw)
        for episode, assembly_id, times, signal_body, raw in zip(
            episodes,
            assembly_ids,
            clocks,
            signal_bodies,
            raw_pressure_hops,
            strict=True,
        )
    )
    return list(zip(planned_episodes, admissions, strict=True)), alignment_claim


def _mono_pcm_hop_episodes(
    *,
    assembly_prefix: str,
    samples: tuple[int, ...],
    sample_rate_hz: int,
    articulatory_body: bytes | None = None,
) -> list[tuple[Any, list[tuple[int, int]]]]:
    """Ambient mono PCM as whole-sensorium hops.

    Ratified doctrine (2026-08-05): NO single-sense experiences — every
    experience episode carries the organism's full mounted sensorium with
    TRUE samples.  During ambient sound intake nothing lights the card
    surface, so every one of the 27 card-surface receptor sites carries its
    true dark 0.0 luminance sample on the hop's shared clock — the same
    port declarations, coordinates, units, and dark values as a lesson hop
    with an unlit card.  The surface is declared as its own exact optical
    occurrence (the ratified retinal law settles receptor physics only for
    an exact optical occurrence) and both ears as theirs, exactly as a full
    lesson's first hop declares them.
    """

    if len(samples) < 2:
        raise ValueError("mono PCM intake requires at least two samples")
    if Fraction(len(samples), sample_rate_hz) > AMBIENT_INTAKE_MAX_SECONDS:
        raise ValueError(
            "mono PCM intake exceeds the declared ambient intake window"
        )
    capture_duration = Fraction(len(samples), sample_rate_hz)
    maximum_interval = max(
        capture_duration,
        Fraction(INTAKE_HOP_MILLISECONDS, 1_000),
    )
    articulatory_change_indices: tuple[int, ...] = ()
    if articulatory_body is not None:
        expected_bytes = (
            ARTICULATORY_BODY_PORT_COUNT
            * len(samples)
            * struct.calcsize("<h")
        )
        if len(articulatory_body) != expected_bytes:
            raise ValueError("native articulatory body bytes changed cardinality")
        raw_body = array("h")
        raw_body.frombytes(articulatory_body)
        if sys.byteorder != "little":
            raw_body.byteswap()
        changed = {0, len(samples)}
        for channel_index in range(ARTICULATORY_BODY_PORT_COUNT):
            start = channel_index * len(samples)
            channel = raw_body[start : start + len(samples)]
            changed.update(
                index
                for index in range(1, len(channel))
                if channel[index] != channel[index - 1]
            )
        # The native neuronal interval boundary is exact whole microseconds.
        # A 16 kHz body sample is 62.5 microseconds, so an odd sample index
        # cannot be named by that boundary.  Feeding those half-microsecond
        # instants into the shared whole-sensorium clock makes the next lived
        # interval noncanonical.  Retain every changed body instant that the
        # native clock can represent exactly; the full 16 kHz pressure still
        # reaches the cochlear mechanics before this retained-source boundary.
        articulatory_change_indices = tuple(
            index
            for index in sorted(changed)
            if (index * 1_000_000) % sample_rate_hz == 0
        )
    hops = _pcm_hops(
        samples,
        sample_rate_hz,
        articulatory_change_indices,
    )
    raw_pressure_hops = _raw_pcm_hops(samples, sample_rate_hz)
    cochlear_hops = (
        _cochlear_hops(
            samples,
            sample_rate_hz,
            additional_sample_indices=articulatory_change_indices,
        )
        if COCHLEAR_EARS_AUTHORIZED
        else []
    )
    articulatory_body_hops = (
        _articulatory_body_hops(
            articulatory_body,
            len(samples),
            sample_rate_hz,
            articulatory_change_indices,
        )
        if articulatory_body is not None
        else []
    )
    if (
        not hops
        or len(raw_pressure_hops) != len(hops)
        or (COCHLEAR_EARS_AUTHORIZED and len(cochlear_hops) < len(hops))
    ):
        raise ValueError("mono PCM intake does not span one intake hop")
    if articulatory_body is not None and len(articulatory_body_hops) != len(hops):
        raise ValueError("articulatory body and pressure changed hop cardinality")
    dark = (0.0,) * CARD_SURFACE_PORT_COUNT
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    episodes: list[tuple[Any, list[tuple[int, int]]]] = []
    for hop_index, (times, signal) in enumerate(hops):
        episode = _whole_roster_hop_episode(
            f"{assembly_prefix}-hop-{hop_index}",
            times,
            dark,
            signal,
            cochlear_hops[hop_index] if COCHLEAR_EARS_AUTHORIZED else None,
            retinal_transmission=retinal_transmission,
            articulated=(
                articulatory_body_hops[hop_index]
                if articulatory_body is not None
                else None
            ),
            raw_pressure_samples=raw_pressure_hops[hop_index],
        )
        # The caller owns the complete capture and therefore authors its exact
        # causal bound. A partial final capture is physically completed by
        # silence to the end of its 250 ms hop above, so that hop duration is
        # the minimum lawful bound even when the nonzero pressure was shorter.
        # The 30-second constant is only the refusal ceiling. Every hop retains
        # the same capture-wide bound, so chunking does not change the field
        # normalization.
        episodes.append(
            (
                episode,
                [
                    (maximum_interval.numerator, maximum_interval.denominator)
                ]
                * LESSON_OCCURRENCE_COUNT,
            )
        )
    return episodes


def _parse_live_sight_batch(
    payload: object,
) -> tuple[list[tuple[float, ...]], dict[str, Any]]:
    """Validate one posted live-sight batch; return rosters and provenance.

    Refusal (ValueError) on anything malformed: undeclared or wrong source
    provenance, a frame count outside the capture contract, timestamps that
    are not strictly increasing integers, a capture span beyond the declared
    ambient intake window, or bytes Pillow cannot decode as an image.  The
    client's capture timestamps are transport provenance recorded as
    evidence; they never enter the physics.
    """

    if not isinstance(payload, dict):
        raise ValueError("live sight intake requires a JSON object body")
    if payload.get("source") != LIVE_SIGHT_SOURCE:
        raise ValueError(
            "live sight intake requires declared provenance: "
            f'source must be "{LIVE_SIGHT_SOURCE}"'
        )
    frames = payload.get("frames")
    if not isinstance(frames, list) or not (
        LIVE_SIGHT_MIN_FRAMES <= len(frames) <= LIVE_SIGHT_MAX_FRAMES
    ):
        raise ValueError(
            "live sight intake requires between "
            f"{LIVE_SIGHT_MIN_FRAMES} and {LIVE_SIGHT_MAX_FRAMES} frames "
            "per batch (the declared visual capture contract)"
        )
    captured_at: list[int] = []
    rosters: list[tuple[float, ...]] = []
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("live sight frame is not a JSON object")
        stamp = frame.get("captured_at_ms")
        if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0:
            raise ValueError(
                "live sight frame requires a positive integer captured_at_ms"
            )
        if captured_at and stamp <= captured_at[-1]:
            raise ValueError(
                "live sight capture timestamps must be strictly increasing"
            )
        captured_at.append(stamp)
        encoded = frame.get("png_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("live sight frame requires png_base64 image bytes")
        try:
            body = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError(
                "live sight frame is not canonical base64"
            ) from error
        try:
            rosters.append(_live_frame_luminance(body))
        except Exception as error:
            raise ValueError(
                f"live sight frame bytes are not a decodable image: "
                f"{type(error).__name__}"
            ) from error
    if captured_at[-1] - captured_at[0] > AMBIENT_INTAKE_MAX_SECONDS * 1000:
        raise ValueError(
            "live sight batch capture span exceeds the declared ambient "
            "intake window"
        )
    provenance = {
        "captured_at_ms_first": captured_at[0],
        "captured_at_ms_last": captured_at[-1],
        "frame_count": len(rosters),
        "sampling_interval_ms": INTAKE_HOP_MILLISECONDS,
        "source": LIVE_SIGHT_SOURCE,
    }
    return rosters, provenance


def _live_sight_hop_episodes(
    batch_id: str,
    rosters: list[tuple[float, ...]],
) -> list[tuple[Any, list[tuple[int, int]]]]:
    """One posted live camera frame per 250 ms hop on the whole sensorium.

    The exact construction every other hop uses: the whole mounted sensorium
    with TRUE samples on the shared 250 ms hop timebase, the real camera
    luminance on the 27 retinal receptor sites declared as its own exact
    optical occurrence (so the retinal cohort's receptor physics settles),
    and both ears as theirs with true 0.0 silence — silence is a lawful
    state; audio is never fabricated.  The authored maximum causal interval
    is the hop's own declared transport duration, exactly as unattended time
    authors its dark hops.
    """

    times = _quiescent_hop_times()
    silence = (0.0,) * len(times)
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    return [
        (
            _whole_roster_hop_episode(
                f"live-sight-{batch_id}-hop-{hop_index}",
                times,
                roster,
                silence,
                retinal_transmission=retinal_transmission,
            ),
            [(INTAKE_HOP_MILLISECONDS, 1000)] * LESSON_OCCURRENCE_COUNT,
        )
        for hop_index, roster in enumerate(rosters)
    ]


def _parse_live_audiovisual_capture(
    payload: object,
) -> tuple[
    list[tuple[float, ...]],
    tuple[int, ...],
    int,
    dict[str, Any],
]:
    """Validate one co-captured camera/microphone transport window.

    The browser supplies one real camera frame for every 250 ms of mono PCM.
    Cardinality is exact: no frame is repeated, no acoustic hop is paired with
    invented darkness, and no resampling is performed.
    """

    if not isinstance(payload, dict):
        raise ValueError("live audiovisual intake requires a JSON object body")
    if payload.get("schema") != LIVE_AUDIOVISUAL_SCHEMA:
        raise ValueError(
            f'live audiovisual schema must be "{LIVE_AUDIOVISUAL_SCHEMA}"'
        )
    if payload.get("source") != LIVE_AUDIOVISUAL_SOURCE:
        raise ValueError(
            "live audiovisual intake requires declared provenance: "
            f'source must be "{LIVE_AUDIOVISUAL_SOURCE}"'
        )
    sight_payload = dict(payload)
    sight_payload["source"] = LIVE_SIGHT_SOURCE
    rosters, provenance = _parse_live_sight_batch(sight_payload)
    sample_rate = payload.get("sample_rate_hz")
    if sample_rate != COCHLEAR_SAMPLE_RATE_HZ:
        raise ValueError(
            "live audiovisual intake requires native 16000 Hz mono PCM; "
            "resampling is not performed"
        )
    encoded = payload.get("pcm_s16le_base64")
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("live audiovisual intake requires pcm_s16le_base64")
    samples_per_hop = sample_rate * INTAKE_HOP_MILLISECONDS // 1000
    expected_sample_count = len(rosters) * samples_per_hop
    expected_body_bytes = expected_sample_count * 2
    expected_base64_characters = 4 * ((expected_body_bytes + 2) // 3)
    if len(encoded) != expected_base64_characters:
        raise ValueError(
            "live audiovisual intake requires exactly one camera frame per "
            f"{INTAKE_HOP_MILLISECONDS} ms PCM hop: expected "
            f"{expected_sample_count} samples"
        )
    try:
        body = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(
            "live audiovisual PCM is not canonical base64"
        ) from error
    if len(body) % 2:
        raise ValueError("live audiovisual PCM has a partial int16 sample")
    samples = struct.unpack(f"<{len(body) // 2}h", body)
    if len(samples) != expected_sample_count:
        raise ValueError(
            "live audiovisual intake requires exactly one camera frame per "
            f"{INTAKE_HOP_MILLISECONDS} ms PCM hop: received "
            f"{len(rosters)} frames and {len(samples)} samples, expected "
            f"{expected_sample_count} samples"
        )
    return (
        rosters,
        samples,
        sample_rate,
        {
            **provenance,
            "audio_sample_count": len(samples),
            "audio_sample_rate_hz": sample_rate,
            "source": LIVE_AUDIOVISUAL_SOURCE,
        },
    )


def _live_audiovisual_hop_episodes(
    capture_id: str,
    rosters: list[tuple[float, ...]],
    samples: tuple[int, ...],
    sample_rate_hz: int,
) -> list[tuple[Any, list[tuple[int, int]]]]:
    """Place co-captured light and pressure in the same native occurrences."""

    pressure_hops = _pcm_hops(samples, sample_rate_hz)
    raw_pressure_hops = _raw_pcm_hops(samples, sample_rate_hz)
    cochlear_hops = _cochlear_hops(samples, sample_rate_hz)
    if not (
        len(rosters)
        == len(pressure_hops)
        == len(raw_pressure_hops)
        == len(cochlear_hops)
    ):
        raise ValueError("live audiovisual hop cardinality changed")
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    return [
        (
            _whole_roster_hop_episode(
                f"live-audiovisual-{capture_id}-hop-{hop_index}",
                times,
                rosters[hop_index],
                pressure,
                cochlear_hops[hop_index],
                retinal_transmission=retinal_transmission,
                raw_pressure_samples=raw_pressure_hops[hop_index],
            ),
            [(INTAKE_HOP_MILLISECONDS, 1000)] * LESSON_OCCURRENCE_COUNT,
        )
        for hop_index, (times, pressure) in enumerate(pressure_hops)
    ]


def _perform_live_sight_intake(
    episodes: list[tuple[Any, list[tuple[int, int]]]],
    intake: str,
    provenance: dict[str, Any],
    *,
    includes_live_hearing: bool = False,
) -> dict[str, Any]:
    """One live-sight batch: admitted intake plus truth-coupled evidence.

    Same transaction discipline as every admitted intake (commit hops
    in-memory under the transition lock, persist and publish ONCE, refresh
    the observation cache only after the persist succeeds), plus the live
    sight evidence record that lets the public observation report the live
    transition as mounted ONLY from a genuinely committed transition.  The
    evidence is written under the same lock, so no observation ever claims
    a live camera commit that did not fully happen.
    """

    global _live_sight_evidence, _live_hearing_evidence

    with _transition_lock:
        result = _perform_admitted_intake_locked(episodes, intake)
        previous = _live_sight_evidence or {
            "committed_batch_count": 0,
            "committed_frame_count": 0,
        }
        _live_sight_evidence = {
            "committed_batch_count": previous["committed_batch_count"] + 1,
            "committed_frame_count": (
                previous["committed_frame_count"] + provenance["frame_count"]
            ),
            "last_capture": dict(provenance),
            "last_intake": intake,
            "last_state_sha256": result["observation"]["state_sha256"],
        }
        if includes_live_hearing:
            _live_hearing_evidence = {
                "intake": intake,
                "generation": result.get("generation"),
            }
        _refresh_public_observation_cache()
        return result


def _lesson_receipt_bytes(record: dict[str, Any]) -> bytes:
    return json.dumps(
        record,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _lesson_receipt_digest(record: dict[str, Any]) -> str:
    payload = {
        key: value for key, value in record.items() if key != "receipt_sha256"
    }
    return hashlib.sha256(_lesson_receipt_bytes(payload)).hexdigest()


def _persist_lesson_receipt(
    record: dict[str, Any],
    *,
    filename: str,
    lesson_kind: str,
) -> None:
    body = _lesson_receipt_bytes(record)
    if len(body) > CARD_LESSON_RECEIPT_MAX_BYTES:
        raise ValueError(f"{lesson_kind} lesson receipt exceeds its fixed byte bound")
    stage = STATE_ROOT / f".{filename}.stage"
    destination = STATE_ROOT / filename
    with stage.open("wb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stage, destination)
    directory = os.open(STATE_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _load_lesson_receipt(
    *,
    filename: str,
    schema: str,
    lesson_kind: str,
) -> dict[str, Any] | None:
    path = STATE_ROOT / filename
    if not path.is_file():
        return None
    if path.stat().st_size > CARD_LESSON_RECEIPT_MAX_BYTES:
        raise ValueError(f"{lesson_kind} lesson receipt exceeds its fixed byte bound")
    record = json.loads(path.read_bytes())
    if not isinstance(record, dict):
        raise ValueError(f"{lesson_kind} lesson receipt is not an object")
    if record.get("schema") != schema:
        raise ValueError(f"{lesson_kind} lesson receipt schema changed")
    digest = record.get("receipt_sha256")
    if not isinstance(digest, str) or not hmac.compare_digest(
        digest, _lesson_receipt_digest(record)
    ):
        raise ValueError(f"{lesson_kind} lesson receipt digest changed")
    return record


def _lesson_receipt_record(
    receipt: dict[str, Any] | None,
    error: str | None,
    *,
    lesson_kind: str,
) -> dict[str, object]:
    if receipt is not None:
        return _section(
            True,
            f"durable_{lesson_kind}_lesson_receipt",
            f"the latest committed {lesson_kind} lesson transport receipt is stored as "
            "one fixed bounded observation record outside organism cognition; "
            "later sensory transitions do not overwrite it",
            **receipt,
        )
    if error is not None:
        return _section(
            False,
            f"{lesson_kind}_lesson_receipt_unavailable",
            error,
        )
    return _section(
        False,
        f"no_durable_{lesson_kind}_lesson_receipt",
        f"no {lesson_kind} lesson has left a durable intake-specific receipt",
    )


def _card_lesson_receipt_digest(record: dict[str, Any]) -> str:
    return _lesson_receipt_digest(record)


def _persist_card_lesson_receipt(record: dict[str, Any]) -> None:
    _persist_lesson_receipt(
        record,
        filename=CARD_LESSON_RECEIPT_FILE,
        lesson_kind="card",
    )


def _load_card_lesson_receipt() -> dict[str, Any] | None:
    return _load_lesson_receipt(
        filename=CARD_LESSON_RECEIPT_FILE,
        schema=CARD_LESSON_RECEIPT_SCHEMA,
        lesson_kind="card",
    )


def _card_lesson_receipt_record() -> dict[str, object]:
    return _lesson_receipt_record(
        _last_card_lesson_receipt,
        _last_card_lesson_receipt_error,
        lesson_kind="card",
    )


def _persist_song_lesson_receipt(record: dict[str, Any]) -> None:
    _persist_lesson_receipt(
        record,
        filename=SONG_LESSON_RECEIPT_FILE,
        lesson_kind="song",
    )


def _load_song_lesson_receipt() -> dict[str, Any] | None:
    return _load_lesson_receipt(
        filename=SONG_LESSON_RECEIPT_FILE,
        schema=SONG_LESSON_RECEIPT_SCHEMA,
        lesson_kind="song",
    )


def _song_lesson_receipt_record() -> dict[str, object]:
    return _lesson_receipt_record(
        _last_song_lesson_receipt,
        _last_song_lesson_receipt_error,
        lesson_kind="song",
    )


class _CurriculumInvitationRefusal(RuntimeError):
    def __init__(self, status_code: int, reason: str) -> None:
        super().__init__(reason)
        self.status_code = status_code


def _validated_curriculum_experience_invitation(
    experience_kind: str,
    experience_id: str,
    invitation_receipt_sha256: object,
) -> dict[str, Any]:
    if not isinstance(invitation_receipt_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", invitation_receipt_sha256
    ):
        raise _CurriculumInvitationRefusal(
            422,
            f"a {experience_kind} presentation requires its exact prepared "
            "physical-occurrence receipt",
        )
    invitation = _curriculum_invitation
    if invitation is None:
        raise _CurriculumInvitationRefusal(
            409,
            "no tutor presentation is prepared in this process; no curriculum "
            "experience was admitted",
        )
    if invitation.get("invitation_receipt_sha256") != invitation_receipt_sha256:
        raise _CurriculumInvitationRefusal(
            409,
            "the presentation receipt is not the current prepared occurrence",
        )
    invited_kind = invitation.get("experience_kind")
    invited_id = invitation.get("experience_id")
    if invited_kind is None and invitation.get("card_id") is not None:
        invited_kind = "card"
        invited_id = invitation.get("card_id")
    if invited_kind != experience_kind or invited_id != experience_id:
        raise _CurriculumInvitationRefusal(
            409,
            "the prepared physical curriculum experience and requested "
            "experience differ",
        )
    if invitation.get("outcome") != "presentable" or not invitation.get(
        "presentation_eligible"
    ):
        raise _CurriculumInvitationRefusal(
            409,
            "the tutor sensory occurrence is not eligible for presentation",
        )
    return invitation


def _validated_curriculum_invitation(
    card_id: str,
    invitation_receipt_sha256: object,
) -> dict[str, Any]:
    return _validated_curriculum_experience_invitation(
        "card",
        card_id,
        invitation_receipt_sha256,
    )


def _perform_card_lesson_intake(
    episodes: list[tuple[Any, list[tuple[int, int]]]],
    intake: str,
    card_id: str,
    experience: dict[str, Any],
    presentation: str,
    invitation_receipt_sha256: str,
) -> dict[str, Any]:
    """One card lesson: admitted intake plus truth-coupled tactile evidence.

    Same transaction discipline as every admitted intake, plus the contact
    evidence that lets the public observation report touch as mounted ONLY from
    a genuinely committed contact transition.  The evidence is written under
    the same lock, so no observation ever claims a contact that did not fully
    happen — and it is written ONLY when the sheet was really occupied: a
    presentation mode that touches nothing (a glimpse) commits a lesson and
    records no contact, which is the truth about it.
    """

    global _last_card_lesson_receipt, _last_card_lesson_receipt_error
    global _touch_evidence
    global _curriculum_invitation

    with _transition_lock:
        invitation = _validated_curriculum_invitation(
            card_id,
            invitation_receipt_sha256,
        )
        _curriculum_invitation = {
            **invitation,
            "outcome": "presentation_attempted",
            "presentation_eligible": False,
            "reason": (
                "the one eligible invitation is being consumed by one "
                "bounded physical presentation"
            ),
            "status": "card_presentation_in_progress",
        }
        result = _perform_admitted_intake_locked(episodes, intake)
        occupancy = _committed_card_occupancy(experience, presentation)
        if occupancy is not None:
            previous = _touch_evidence or {"committed_contact_count": 0}
            _touch_evidence = {
                "committed_contact_count": previous["committed_contact_count"] + 1,
                "contacted_site_count": sum(1 for value in occupancy if value > 0.0),
                "declared_contact_site_count": CONTACT_SHEET_SITE_COUNT,
                "last_contact_object": card_id,
                "last_contact_state_sha256": result["observation"]["state_sha256"],
            }
        surface = experience.get("surface")
        tutor_audio = experience.get("tutor_audio")
        receipt: dict[str, Any] = {
            "schema": CARD_LESSON_RECEIPT_SCHEMA,
            "card_id": card_id,
            "invitation_receipt_sha256": invitation_receipt_sha256,
            "presentation": presentation,
            "transport_metadata_only": True,
            "surface_sha256": (
                surface.get("sha256") if isinstance(surface, dict) else None
            ),
            "tutor_audio_sha256": (
                tutor_audio.get("sha256")
                if isinstance(tutor_audio, dict)
                else None
            ),
            "predecessor_state_sha256": result["persisted"][
                "predecessor_state_sha256"
            ],
            "successor_state_sha256": result["persisted"]["state_sha256"],
            "successor_state_bytes": result["persisted"]["state_bytes"],
            "successor_organism_tick": result["persisted"]["organism_tick"],
            "hop_count": result["hop_count"],
            "totals": dict(result["totals"]),
        }
        receipt["receipt_sha256"] = _card_lesson_receipt_digest(receipt)
        try:
            _persist_card_lesson_receipt(receipt)
        except (OSError, TypeError, ValueError) as error:
            _last_card_lesson_receipt = None
            _last_card_lesson_receipt_error = (
                "the organism successor committed, but its bounded card "
                f"lesson receipt could not be persisted ({type(error).__name__}: "
                f"{error}); do not repeat the lesson"
            )
            result["durable_receipt"] = _card_lesson_receipt_record()
        else:
            _last_card_lesson_receipt = receipt
            _last_card_lesson_receipt_error = None
            result["durable_receipt"] = _card_lesson_receipt_record()
        _curriculum_invitation = {
            **_curriculum_invitation,
            "outcome": "presented",
            "presented_successor_organism_tick": result["persisted"][
                "organism_tick"
            ],
            "presented_successor_state_sha256": result["persisted"][
                "state_sha256"
            ],
            "presentation_eligible": False,
            "reason": (
                "one prepared physical card presentation committed through "
                "Guala's sensory receptors; the receipt is consumed and "
                "cannot admit a duplicate"
            ),
            "status": "tutor_card_presentation_committed",
        }
        _refresh_public_observation_cache()
        return result


def _perform_song_lesson_intake(
    episodes: list[tuple[Any, list[tuple[int, int]]]],
    song_id: str,
    experience: dict[str, Any],
    alignment_claim: str,
    invitation_receipt_sha256: str,
) -> dict[str, Any]:
    """Commit one invited synchronized song and one fixed observation receipt."""

    global _curriculum_invitation
    global _last_song_lesson_receipt, _last_song_lesson_receipt_error

    with _transition_lock:
        invitation = _validated_curriculum_experience_invitation(
            "song",
            song_id,
            invitation_receipt_sha256,
        )
        _curriculum_invitation = {
            **invitation,
            "outcome": "presentation_attempted",
            "presentation_eligible": False,
            "reason": (
                "the one eligible invitation is being consumed by one "
                "bounded synchronized song presentation"
            ),
            "status": "song_presentation_in_progress",
        }
        result = _perform_admitted_intake_locked(
            episodes,
            f"curriculum-song:{song_id}",
        )
        audio = experience.get("audio")
        visual = experience.get("visual_program")
        receipt: dict[str, Any] = {
            "schema": SONG_LESSON_RECEIPT_SCHEMA,
            "song_id": song_id,
            "invitation_receipt_sha256": invitation_receipt_sha256,
            "transport_metadata_only": True,
            "audio_sha256": audio.get("sha256") if isinstance(audio, dict) else None,
            "audio_sample_count": (
                audio.get("sample_count") if isinstance(audio, dict) else None
            ),
            "visual_alignment_claim": alignment_claim,
            "visual_program_receipt_sha256": (
                _receipt(visual) if isinstance(visual, dict) else None
            ),
            "predecessor_state_sha256": result["persisted"][
                "predecessor_state_sha256"
            ],
            "successor_state_sha256": result["persisted"]["state_sha256"],
            "successor_state_bytes": result["persisted"]["state_bytes"],
            "successor_organism_tick": result["persisted"]["organism_tick"],
            "hop_count": result["hop_count"],
            "totals": dict(result["totals"]),
        }
        receipt["receipt_sha256"] = _lesson_receipt_digest(receipt)
        try:
            _persist_song_lesson_receipt(receipt)
        except (OSError, TypeError, ValueError) as error:
            _last_song_lesson_receipt = None
            _last_song_lesson_receipt_error = (
                "the organism successor committed, but its bounded song "
                f"lesson receipt could not be persisted ({type(error).__name__}: "
                f"{error}); do not repeat the lesson"
            )
        else:
            _last_song_lesson_receipt = receipt
            _last_song_lesson_receipt_error = None
        result["durable_receipt"] = _song_lesson_receipt_record()
        _curriculum_invitation = {
            **_curriculum_invitation,
            "outcome": "presented",
            "presented_successor_organism_tick": result["persisted"][
                "organism_tick"
            ],
            "presented_successor_state_sha256": result["persisted"][
                "state_sha256"
            ],
            "presentation_eligible": False,
            "reason": (
                "one prepared synchronized song presentation committed "
                "through Guala's sensory receptors; the receipt is consumed "
                "and cannot admit a duplicate"
            ),
            "status": "tutor_song_presentation_committed",
        }
        _refresh_public_observation_cache()
        return result


def _committed_card_occupancy(
    experience: dict[str, Any],
    presentation: str,
) -> tuple[float, ...] | None:
    """The occupancy a committed lesson really put on the sheet, or ``None``.

    ``None`` — nothing was touched — for an unauthorized body (it has no sheet)
    and for a glimpse.  A glimpse is a partial VISUAL cue; the manifest
    declares nothing about a partial CONTACT, and restricting the footprint by
    the retina's own row-major index would be a cross-modal inference, not a
    declared geometry.  So a glimpsed card is seen and not held, which is a
    lawful state, and no contact is claimed for it.
    """

    if not TOUCH_RECEPTORS_AUTHORIZED or presentation != "full":
        return None
    surface = experience.get("surface")
    surface_path = surface.get("path") if isinstance(surface, dict) else None
    if not isinstance(surface_path, str):
        return None
    return _card_tactile_occupancy(
        CURRICULUM_ROOT / surface_path.removeprefix("guala_curriculum/")
    )


def _live_sight_record() -> dict[str, object]:
    """Truth-coupled live-sight observation.

    Available flips ONLY on a real committed live camera transition in this
    process — never from the mounted transport surface.  Before the first
    committed batch the record says honestly that the intake endpoint is
    open but unproven.
    """

    if _live_sight_evidence is None:
        return _section(
            False,
            "no_live_sight_transition_this_process",
            "the live-sight intake endpoint is open on the declared "
            "27-receptor retinal roster, but no live camera batch has "
            "committed end-to-end in this process; mounted is claimed only "
            "from a real committed transition",
            intake_endpoint=LIVE_SIGHT_INTAKE_ENDPOINT,
        )
    return _section(
        True,
        "live_sight_transition_committed",
        "real live camera frames were delivered to the resident organism "
        "as admitted 27-receptor luminance occurrences and the committed "
        "successor body was persisted; capture provenance is the client's "
        "own declared live-camera contract",
        intake_endpoint=LIVE_SIGHT_INTAKE_ENDPOINT,
        **_live_sight_evidence,
    )


def _prior_life_evidence(root: Path) -> tuple[str, ...]:
    """Name what proves this state root has already carried a life.

    A root with any of these and NO CURRENT is a DAMAGED root, never a new
    one: something removed the pointer out from under a living organism.
    Measured 2026-08-07 — the live root was deleted mid-service, and the
    only thing standing between that and a silent rebirth carrying the
    pinned identity was that ECS happened not to restart the task.
    """

    if not root.exists():
        return ()
    lived: list[str] = []
    # The generations directory itself is created by every store open, so only
    # its CONTENTS are evidence; the mirror and the retired episode archive are
    # written on publication alone, so their existence is evidence by itself.
    generations = sorted(path.name for path in (root / "generations").glob("*.glorun"))
    if generations:
        lived.append(f"generations ({len(generations)} retained bodies)")
    lived.extend(
        name
        for name in (
            LOCAL_OBJECT_MIRROR_DIRECTORY,
            "hippocampal-cold",
            CARD_LESSON_RECEIPT_FILE,
            SONG_LESSON_RECEIPT_FILE,
            SOURCE_MEDIA_ROOT.name,
            WORLD_RECOVERY_MARKER_FILE,
            WORLD_RECOVERY_GENERATIONS_DIRECTORY,
            WORLD_RECOVERY_ASSOCIATIONS_DIRECTORY,
        )
        if (root / name).exists()
    )
    lived.extend(sorted(path.name for path in root.glob(".stage-*")))
    return tuple(lived)


def _startup() -> None:
    global _restored, _admission, _boot_error
    global _last_card_lesson_receipt, _last_card_lesson_receipt_error
    global _last_song_lesson_receipt, _last_song_lesson_receipt_error
    global _curriculum_invitation
    global _public_observation_body, _public_observation_etag, _runtime_proof_body
    global _runtime_build_identity
    global _last_tested_prediction_evidence, _last_tested_affective_balance_evidence
    global _last_tested_localized_fluid_chemistry_evidence
    global _last_tested_articulation_evidence
    global _native_pressure_audio_cache
    global _last_causal_cross_context_use_evidence
    global _last_intrinsic_curiosity_evidence
    global _last_social_experience_evidence
    global _last_tested_physical_choice_evidence
    global _sensorimotor_play_candidate, _last_sensorimotor_play_evidence
    global _body_owned_laughter_candidate, _last_body_owned_laughter_evidence
    global _reciprocal_social_play_candidate
    global _last_reciprocal_social_play_evidence
    global _active_cross_intake_causal_motor_traces
    global _pending_custody_cleanup, _pending_custody_candidate
    _last_tested_prediction_evidence = None
    _last_tested_affective_balance_evidence = None
    _last_tested_localized_fluid_chemistry_evidence = None
    _last_tested_articulation_evidence = None
    _native_pressure_audio_cache = ()
    _last_causal_cross_context_use_evidence = None
    _last_intrinsic_curiosity_evidence = None
    _last_social_experience_evidence = None
    _last_tested_physical_choice_evidence = None
    _sensorimotor_play_candidate = None
    _last_sensorimotor_play_evidence = None
    _body_owned_laughter_candidate = None
    _last_body_owned_laughter_evidence = None
    _reciprocal_social_play_candidate = None
    _last_reciprocal_social_play_evidence = None
    _active_cross_intake_causal_motor_traces = {}
    _pending_custody_cleanup = None
    _pending_custody_candidate = None
    _curriculum_invitation = None
    _runtime_build_identity = None
    try:
        admission = derive_native_resident_resource_admission(STATE_ROOT)
        retired_stage_count, retired_stage_bytes = (
            reconcile_orphaned_staged_native_organisms(
                STATE_ROOT,
                object_store=_object_store(),
                max_envelope_bytes=admission.max_envelope_bytes,
            )
        )
        if retired_stage_count:
            print(
                "guala-cold-stage-reconciliation "
                f"retired_count={retired_stage_count} "
                f"retired_bytes={retired_stage_bytes}",
                flush=True,
            )
        retired_media_count, retired_media_bytes = (
            _source_media_store.reconcile_interrupted_admission()
        )
        if retired_media_count:
            print(
                "guala-cold-source-media-reconciliation "
                f"retired_count={retired_media_count} "
                f"retired_bytes={retired_media_bytes}",
                flush=True,
            )
        migration_authorized = os.environ.get(
            "GUALA_CURRENT_FORMAT_MIGRATION", "0"
        )
        if migration_authorized not in {"0", "1"}:
            raise RuntimeError(
                "GUALA_CURRENT_FORMAT_MIGRATION must be exactly 0 or 1"
            )
        try:
            # Migration authorization is an instruction to make CURRENT
            # current before any ordinary interval can encode it. The former
            # readiness-count shortcut let a decodable V16 body run first;
            # that interval then wrote V17 without applying V17's carrier
            # correction. Native migration is idempotent, so execute it first
            # whenever this explicit release switch is on.
            if migration_authorized == "1":
                migrate_current_native_organism_current_format(
                    STATE_ROOT,
                    object_store=_object_store(),
                    max_envelope_bytes=admission.max_envelope_bytes,
                    max_fabric_bytes=admission.max_fabric_bytes,
                    max_logical_peak_bytes=admission.max_logical_peak_bytes,
                )
            restored = restore_current_native_organism(
                STATE_ROOT,
                max_envelope_bytes=admission.max_envelope_bytes,
                max_fabric_bytes=admission.max_fabric_bytes,
                max_logical_peak_bytes=admission.max_logical_peak_bytes,
            )
        except NativeOrganismBinaryStoreError as error:
            if "CURRENT is absent" not in str(error):
                if migration_authorized != "1":
                    raise
                migrate_current_native_organism_current_format(
                    STATE_ROOT,
                    object_store=_object_store(),
                    max_envelope_bytes=admission.max_envelope_bytes,
                    max_fabric_bytes=admission.max_fabric_bytes,
                    max_logical_peak_bytes=admission.max_logical_peak_bytes,
                )
                restored = restore_current_native_organism(
                    STATE_ROOT,
                    max_envelope_bytes=admission.max_envelope_bytes,
                    max_fabric_bytes=admission.max_fabric_bytes,
                    max_logical_peak_bytes=admission.max_logical_peak_bytes,
                )
            else:
                lived = _prior_life_evidence(STATE_ROOT)
                if lived:
                    raise RuntimeError(
                        "native state root carries prior life but has no CURRENT "
                        f"({', '.join(lived)}); refusing to genesis over a damaged "
                        "root — restore the body and republish CURRENT instead"
                    ) from error
                _perform_genesis(admission)
                restored = restore_current_native_organism(
                    STATE_ROOT,
                    max_envelope_bytes=admission.max_envelope_bytes,
                    max_fabric_bytes=admission.max_fabric_bytes,
                    max_logical_peak_bytes=admission.max_logical_peak_bytes,
                )
        observation = restored.organism.readiness()
        _lesson_anatomy()
        # This is the one explicit cold audit of retained source bytes.  No
        # ordinary interval or public observation scans or hashes the media
        # store, and a damaged source refuses restore instead of silently
        # becoming a different experience.
        _source_media_store.inventory(verify_source_bytes=True)
        if observation.python_callback_count != 0:
            raise RuntimeError("native organism reports a Python cognition callback")
        step_claims = (
            observation.physical_transition_claimed,
            bool(observation.formation_activation_count),
            bool(observation.partial_cue_reassembly_count),
        )
        if any(step_claims):
            raise RuntimeError(
                "native state claimed step effects at cold restore"
            )
        _admission = admission
        _restored = restored
        retired_world_count, retired_world_bytes = (
            _reconcile_world_recovery_store(restored.pointer)
        )
        if retired_world_count:
            print(
                "guala-cold-world-reconciliation "
                f"retired_count={retired_world_count} "
                f"retired_bytes={retired_world_bytes}",
                flush=True,
            )
        _boot_error = None
        _runtime_build_identity = _build_identity()
        try:
            _last_card_lesson_receipt = _load_card_lesson_receipt()
            _last_card_lesson_receipt_error = None
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            _last_card_lesson_receipt = None
            _last_card_lesson_receipt_error = (
                "the bounded card lesson receipt could not be restored "
                f"({type(error).__name__}: {error})"
            )
        try:
            _last_song_lesson_receipt = _load_song_lesson_receipt()
            _last_song_lesson_receipt_error = None
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            _last_song_lesson_receipt = None
            _last_song_lesson_receipt_error = (
                "the bounded song lesson receipt could not be restored "
                f"({type(error).__name__}: {error})"
            )
        _refresh_public_observation_cache()
    except BaseException as error:
        _restored = None
        _admission = None
        _public_observation_body = None
        _public_observation_etag = None
        _runtime_proof_body = None
        _runtime_build_identity = None
        _boot_error = f"{type(error).__name__}: {error}"
        raise


def _publish_pending_custody_candidate(
    candidate: dict[str, Any],
    staged_attempt: Any,
) -> str:
    """Publish or retry one replace-only prepared checkpoint candidate."""

    global _restored, _boot_error
    global _pending_unsealed_intervals, _pending_chain_predecessor_sha
    global _last_custodian_evidence
    global _pending_custody_cleanup, _pending_custody_candidate

    organism = candidate["organism"]
    predecessor = candidate["predecessor"]
    checkpoint = candidate["checkpoint"]
    admission = candidate["admission"]
    retry_stage = candidate["retry_stage"]
    cleanup_pending = False
    try:
        with _transition_lock:
            current = _restored
            if (
                current is None
                or current.organism is not organism
                or current.pointer != predecessor
                or _custody_trajectory_epoch != candidate["trajectory_epoch"]
            ):
                discard_staged_native_organism(staged_attempt)
                discard_staged_native_organism(retry_stage)
                _pending_custody_candidate = None
                _reconcile_world_recovery_store(predecessor)
                return "superseded"
            organism.validate_lived_checkpoint(checkpoint)
            publish_started = time.perf_counter()
            try:
                published = publish_staged_native_organism(
                    staged_attempt,
                    expected_predecessor_sha256=predecessor.state_sha256,
                    object_store=_object_store(),
                    max_envelope_bytes=admission.max_envelope_bytes,
                    max_fabric_bytes=admission.max_fabric_bytes,
                    max_logical_peak_bytes=admission.max_logical_peak_bytes,
                )
            except CommittedNativeOrganismPublicationError as committed:
                published = committed.published
                _pending_custody_cleanup = committed.cleanup
                cleanup_pending = True
            try:
                organism.adopt_published_lived_checkpoint(checkpoint)
            except BaseException as error:
                _restored = None
                _boot_error = (
                    "published custodian checkpoint could not be adopted by "
                    f"the resident recovery boundary: {type(error).__name__}: {error}"
                )
                raise RuntimeError(_boot_error) from error
            publish_wall_ms = (time.perf_counter() - publish_started) * 1000.0
            _restored = RestoredNativeOrganism(
                organism=organism,
                pointer=published.pointer,
            )
            discard_staged_native_organism(retry_stage)
            _pending_custody_candidate = None
            _reconcile_world_recovery_store(published.pointer)
            _pending_unsealed_intervals = max(
                0,
                _pending_unsealed_intervals
                - candidate["captured_interval_count"],
            )
            _pending_chain_predecessor_sha = None
            if cleanup_pending:
                _checkpoint_requested.set()
            else:
                _checkpoint_requested.clear()
            if _pending_unsealed_intervals >= _checkpoint_every_intervals():
                _checkpoint_requested.set()
            _last_custodian_evidence = {
                "checkpoint_tick": published.pointer.organism_tick,
                "state_sha256": published.pointer.state_sha256,
                "world_state_sha256": candidate["world_pair"][
                    "world_state_sha256"
                ],
                "world_state_bytes": candidate["world_pair"][
                    "world_state_bytes"
                ],
                "captured_interval_count": candidate[
                    "captured_interval_count"
                ],
                "remaining_interval_count": _pending_unsealed_intervals,
                "snapshot_wall_ms": round(candidate["snapshot_wall_ms"], 1),
                "encode_wall_ms": round(candidate["encode_wall_ms"], 1),
                "stage_wall_ms": round(candidate["stage_wall_ms"], 1),
                "publish_and_adopt_wall_ms": round(publish_wall_ms, 1),
            }
    except BaseException:
        discard_staged_native_organism(staged_attempt)
        current_pointer = _read_current(STATE_ROOT)
        if current_pointer != predecessor:
            discard_staged_native_organism(retry_stage)
            _pending_custody_candidate = None
            if current_pointer is not None and _world_recovery_marker_present():
                _reconcile_world_recovery_store(current_pointer)
        raise
    _refresh_public_observation_cache()
    return "checkpointed_cleanup_pending" if cleanup_pending else "checkpointed"


def _custodian_cycle() -> str:
    """Publish one exact resident checkpoint outside lived-time work.

    A pre-CURRENT refusal retains one exact prepared candidate and one compact
    retry stage. Later cycles retry that candidate without another native
    snapshot, envelope encode, or compression pass. A post-CURRENT fault adopts
    once and retains only its constant-size cleanup descriptor.
    """

    global _pending_custody_cleanup, _pending_custody_candidate

    if _pending_custody_cleanup is not None:
        retry_committed_native_organism_cleanup(
            _pending_custody_cleanup,
            object_store=_object_store(),
        )
        _pending_custody_cleanup = None
        if _pending_unsealed_intervals < _checkpoint_every_intervals():
            _checkpoint_requested.clear()
        return "cleanup_completed"
    if _pending_custody_candidate is not None:
        staged_attempt = clone_staged_native_organism(
            _pending_custody_candidate["retry_stage"]
        )
        return _publish_pending_custody_candidate(
            _pending_custody_candidate,
            staged_attempt,
        )

    with _transition_lock:
        if _pending_unsealed_intervals == 0:
            return "unchanged"
        restored, admission = _runtime()
        organism = restored.organism
        predecessor = restored.pointer
        trajectory_epoch = _custody_trajectory_epoch
        captured_interval_count = _pending_unsealed_intervals
        snapshot_started = time.perf_counter()
        snapshot = organism.snapshot_lived_state()
        world_body = bytes(_world().encoded_snapshot())
        snapshot_wall_ms = (time.perf_counter() - snapshot_started) * 1000.0

    encode_started = time.perf_counter()
    checkpoint = snapshot.prepare_checkpoint()
    envelope = bytes(checkpoint.encoded_generation())
    encode_wall_ms = (time.perf_counter() - encode_started) * 1000.0
    if (
        checkpoint.organism_tick != snapshot.organism_tick
        or checkpoint.state_bytes != len(envelope)
        or checkpoint.state_sha256 != hashlib.sha256(envelope).hexdigest()
    ):
        raise RuntimeError("custodian checkpoint changed after native encoding")
    stage_started = time.perf_counter()
    staged = stage_native_organism_state_bytes(
        STATE_ROOT,
        envelope,
        identity=predecessor.identity,
        organism_tick=checkpoint.organism_tick,
        max_envelope_bytes=admission.max_envelope_bytes,
    )
    del envelope
    stage_wall_ms = (time.perf_counter() - stage_started) * 1000.0
    retry_stage = None
    try:
        retry_stage = clone_staged_native_organism(staged)
        world_pair = _publish_world_recovery_pair(
            checkpoint.state_sha256,
            world_body,
        )
        candidate = {
            "admission": admission,
            "captured_interval_count": captured_interval_count,
            "checkpoint": checkpoint,
            "encode_wall_ms": encode_wall_ms,
            "organism": organism,
            "predecessor": predecessor,
            "retry_stage": retry_stage,
            "snapshot_wall_ms": snapshot_wall_ms,
            "stage_wall_ms": stage_wall_ms,
            "trajectory_epoch": trajectory_epoch,
            "world_pair": world_pair,
        }
        _pending_custody_candidate = candidate
        return _publish_pending_custody_candidate(candidate, staged)
    except BaseException:
        if _pending_custody_candidate is None:
            discard_staged_native_organism(staged)
            if retry_stage is not None:
                discard_staged_native_organism(retry_stage)
            current_pointer = _read_current(STATE_ROOT)
            if current_pointer is not None and _world_recovery_marker_present():
                _reconcile_world_recovery_store(current_pointer)
        raise


def _custodian_loop() -> None:
    while not _custodian_stop.is_set():
        if not _checkpoint_requested.wait(1.0):
            continue
        if _custodian_stop.is_set():
            return
        started = time.perf_counter()
        global _last_custodian_error
        try:
            outcome = _custodian_cycle()
            if outcome in {"checkpointed", "cleanup_completed"}:
                _last_custodian_error = None
            elif outcome == "checkpointed_cleanup_pending":
                _last_custodian_error = {
                    "error": "CURRENT committed; predecessor cleanup pending",
                    "failed_at_unix_seconds": int(time.time()),
                    "pending_unsealed_intervals": _pending_unsealed_intervals,
                    "phase": "post_current_cleanup",
                }
        except BaseException as error:
            outcome = f"failed:{type(error).__name__}"
            _last_custodian_error = {
                "error": f"{type(error).__name__}: {error}",
                "failed_at_unix_seconds": int(time.time()),
                "pending_unsealed_intervals": _pending_unsealed_intervals,
            }
            if _restored is not None:
                _checkpoint_requested.set()
        detail = ""
        if outcome.startswith("checkpointed") and _last_custodian_evidence is not None:
            detail = " " + " ".join(
                f"{key}={value}"
                for key, value in _last_custodian_evidence.items()
                if key != "state_sha256"
            )
        print(
            f"guala-custodian outcome={outcome} "
            f"wall_ms={(time.perf_counter() - started) * 1000.0:.0f}{detail}",
            file=sys.stderr,
            flush=True,
        )
        if outcome.startswith("failed:"):
            _custodian_stop.wait(1.0)


def _start_custodian() -> None:
    global _custodian_thread

    if _custodian_thread is not None and _custodian_thread.is_alive():
        return
    _custodian_stop.clear()
    _custodian_thread = threading.Thread(
        target=_custodian_loop,
        name="guala-custodian",
        daemon=True,
    )
    _custodian_thread.start()


def _stop_custodian() -> None:
    global _custodian_thread

    _custodian_stop.set()
    _checkpoint_requested.set()
    thread = _custodian_thread
    if thread is not None:
        thread.join(timeout=30.0)
    _custodian_thread = None
    if thread is None or not thread.is_alive():
        try:
            _custodian_cycle()
        except BaseException as error:
            print(
                "ERROR: final custodian checkpoint failed: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
                flush=True,
            )


async def _lifespan(_application: FastAPI):
    _startup()
    _start_custodian()
    _start_unattended_time()
    try:
        yield
    finally:
        _stop_unattended_time()
        _stop_custodian()


app = FastAPI(title="Guala native organism", version="1", lifespan=_lifespan)


@app.middleware("http")
async def _announce_live_audiovisual_arrival(
    request: Request,
    call_next: Any,
) -> Response:
    """Let resident transport see paired sight/sound before route queuing.

    FastAPI runs the synchronous audiovisual handler in its worker pool.  A
    dependency on that handler proved too late in production: the request was
    already at the server while unattended transport repeatedly reacquired the
    resident organism.  Mark only the live paired sensory path at the outer
    ASGI boundary, before dependency solving or worker admission.  This flag
    never enters cognition and cannot cause a transition; it merely makes the
    unattended transport yield its next atomic borrow to physical input that
    has already arrived.
    """

    if request.url.path != LIVE_AUDIOVISUAL_INTAKE_ENDPOINT:
        return await call_next(request)
    _begin_external_intake()
    try:
        return await call_next(request)
    finally:
        _end_external_intake()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _cached_runtime_proof_response() -> Response:
    body = _runtime_proof_body
    if body is None:
        raise HTTPException(
            status_code=503,
            detail=_boot_error or "native runtime proof is unavailable",
        )
    return Response(
        content=body,
        headers={"Cache-Control": "private, no-store"},
        media_type="application/json",
    )


@app.get("/ready/guala", dependencies=[Depends(_require_secret)])
def ready_guala() -> Response:
    return _cached_runtime_proof_response()


@app.get(
    "/api/v1/deployment/runtime-proof",
    dependencies=[Depends(_require_secret)],
)
def runtime_proof() -> Response:
    return _cached_runtime_proof_response()


@app.get("/api/v1/guala/native-observation")
def native_observation(
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
) -> Response:
    if _public_observation_body is None or _public_observation_etag is None:
        raise HTTPException(
            status_code=503,
            detail=_boot_error or "native public observation is unavailable",
        )
    headers = {
        "Cache-Control": "private, no-cache",
        "ETag": _public_observation_etag,
        "Vary": "If-None-Match",
    }
    if if_none_match == _public_observation_etag:
        return Response(status_code=304, headers=headers)
    return Response(
        content=_public_observation_body,
        headers=headers,
        media_type="application/json",
    )


@app.get(NATIVE_PRESSURE_AUDIO_ENDPOINT)
def native_pressure_audio(pressure_sha256: str | None = None) -> Response:
    """Return one recent exact committed native pressure for human hearing."""

    if pressure_sha256 is not None and not re.fullmatch(
        r"[0-9a-f]{64}", pressure_sha256
    ):
        raise HTTPException(
            status_code=422,
            detail="native pressure identity must be one lowercase SHA-256",
        )
    audio = next(
        (
            item
            for item in reversed(_native_pressure_audio_cache)
            if pressure_sha256 is None
            or item.get("pressure_sha256") == pressure_sha256
        ),
        None,
    )
    if audio is None:
        raise HTTPException(
            status_code=404,
            detail="that bounded native pressure is unavailable in this process",
        )
    pcm_s16le = audio.get("pcm_s16le")
    pressure_sha256 = audio.get("pressure_sha256")
    sample_rate_hz = audio.get("sample_rate_hz")
    if (
        not isinstance(pcm_s16le, bytes)
        or not isinstance(pressure_sha256, str)
        or isinstance(sample_rate_hz, bool)
        or not isinstance(sample_rate_hz, int)
        or sample_rate_hz <= 0
    ):
        raise HTTPException(
            status_code=503,
            detail="native pressure observation lost its exact body",
        )
    wav_body = io.BytesIO()
    with wave.open(wav_body, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(pcm_s16le)
    return Response(
        content=wav_body.getvalue(),
        headers={
            "Cache-Control": "private, no-store",
            "ETag": f'"{pressure_sha256}"',
            "X-Guala-Pressure-SHA256": pressure_sha256,
        },
        media_type="audio/wav",
    )


@app.get("/api/v1/visual/capture-contract")
def visual_capture_contract() -> dict[str, Any]:
    # ``sensory_transition_available`` is truth-coupled: it reports whether a
    # live camera batch has genuinely committed end-to-end in this process,
    # never whether the transport endpoint merely exists.
    return {
        "intake_endpoint": LIVE_SIGHT_INTAKE_ENDPOINT,
        "maximum_frames": LIVE_SIGHT_MAX_FRAMES,
        "minimum_frames": LIVE_SIGHT_MIN_FRAMES,
        "ok": True,
        "sampling_interval_ms": INTAKE_HOP_MILLISECONDS,
        "schema": "guala.visual_capture_transport.v1",
        "sensory_transition_available": _live_sight_evidence is not None,
        "source": LIVE_SIGHT_SOURCE,
    }


@app.post(
    "/api/v1/curriculum/teach-card",
    dependencies=[Depends(_external_intake_admission)],
)
def teach_card(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    card_id = payload.get("card_id") if isinstance(payload, dict) else None
    if not isinstance(card_id, str) or not card_id:
        return _refusal(422, "teach-card requires an approved card_id")
    presentation = (
        payload.get("presentation", "full") if isinstance(payload, dict) else "full"
    )
    if presentation not in PRESENTATION_MODES:
        return _refusal(
            422,
            "teach-card presentation must be one of "
            + ", ".join(repr(mode) for mode in PRESENTATION_MODES),
        )
    try:
        experience = _read_manifest_card(card_id)
    except KeyError:
        return _refusal(
            404,
            f"card {card_id!r} is not in the approved curriculum manifest",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _refusal(503, f"curriculum manifest is unavailable: {error}")
    invitation_receipt = (
        payload.get("invitation_receipt_sha256")
        if isinstance(payload, dict)
        else None
    )
    try:
        with _transition_lock:
            _validated_curriculum_invitation(card_id, invitation_receipt)
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    try:
        episodes = _card_lesson_hop_episodes(card_id, experience, presentation)
    except HTTPException:
        raise
    except (OSError, ValueError) as error:
        return _refusal(503, f"approved curriculum media refused: {error}")
    try:
        result = _perform_card_lesson_intake(
            episodes,
            f"curriculum-card:{card_id}:{presentation}",
            card_id,
            experience,
            presentation,
            invitation_receipt,
        )
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted lesson transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            "card_id": card_id,
            "presentation": presentation,
            **_public_admitted_intake_result(result),
        },
    )


@app.post(
    CURRICULUM_TEACH_SONG_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def teach_song(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Present one attended signed song on one shared audiovisual clock."""

    song_id = payload.get("song_id") if isinstance(payload, dict) else None
    if not isinstance(song_id, str) or not song_id:
        return _refusal(422, "teach-song requires an approved song_id")
    if not COCHLEAR_EARS_AUTHORIZED:
        return _refusal(503, _SOUND_SUSPENSION_REASON)
    try:
        experience = _read_manifest_song(song_id)
    except KeyError:
        return _refusal(
            404,
            f"song {song_id!r} is not in the approved curriculum manifest",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _refusal(503, f"song curriculum manifest is unavailable: {error}")
    invitation_receipt = (
        payload.get("invitation_receipt_sha256")
        if isinstance(payload, dict)
        else None
    )
    try:
        with _transition_lock:
            _validated_curriculum_experience_invitation(
                "song",
                song_id,
                invitation_receipt,
            )
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    try:
        episodes, alignment_claim = _song_lesson_hop_episodes(song_id, experience)
    except (OSError, TypeError, ValueError) as error:
        return _refusal(503, f"approved song media refused: {error}")
    try:
        result = _perform_song_lesson_intake(
            episodes,
            song_id,
            experience,
            alignment_claim,
            invitation_receipt,
        )
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted song transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            "song_id": song_id,
            "visual_alignment_claim": alignment_claim,
            **_public_admitted_intake_result(result),
        },
    )


# ---------------------------------------------------------------------------
# OFFERED MATERIAL — the media-giving controls the page has always shown
# (delivery contract items 11 and 13, 2026-08-04: "Every displayed function
# must be live rather than decorative").
#
# Six controls on the interaction page — offer text, picture, PDF, book,
# audio, song — have been rendered, disabled, and backed by nothing.  They
# are not new senses and they are not a new pathway: a picture is light and a
# song is pressure, so every one of them reduces to a route this organism
# already runs and that is already severing-proven.
#
#   any raster  -> _raster_luminance -> the same 27 retinal sites the
#                  approved cards and the live camera reach
#   any audio   -> pcm_s16le mono 16 kHz -> the same cochlear decomposition
#                  the tutor voice and the microphone reach
#   any page    -> one raster per page, presented in order
#
# NOTHING SEMANTIC ENTERS.  The text a person types is rendered to pixels in
# their own browser and only the PIXELS are offered; the string is never
# submitted.  A PDF is light, not words.  This is the contract's own rule
# (item 11: external-world experiences "may not insert meanings, memories,
# answers, or semantic labels into cognition").
# ---------------------------------------------------------------------------
# THE SHELVES — bounded external-world material (contract items 11 and 13).
#
# Five shelves have been rendered on the page with ten dead buttons.  Only
# ONE of them can be honest today, and the other four say exactly why not
# rather than hiding behind "not mounted":
#
#   Project Gutenberg  PUBLIC DOMAIN, no credential, reachable from this
#                      container (verified).  A book becomes PAGES OF LIGHT
#                      through the same retinal reduction a PDF uses.  No
#                      text, title, author or meaning enters cognition —
#                      contract item 11 — because to an organism that has
#                      not learned to read, a page is a picture.
#   YouTube, Khan Academy, PBS Kids, Spotify
#                      require credentials this deployment does not hold.
#                      There is nothing to fetch, so there is nothing to
#                      mount, and the refusal names the missing credential.
#
# The catalogue never selects or presents a book. One preserved Alice edition
# may bind the persistent world book to immutable rendered surfaces. Only the
# body's unique physical contact plus one native opening-grip displacement can
# advance that material surface. Catalogue order, metadata, observer scores,
# and server requests have no action authority.
SHELF_SELECTION_SCHEMA = "guala.native.external_material_selection.v1"
GUTENBERG_ENDPOINT = "/api/v1/material/gutenberg"
GUTENBERG_PAGE_LINES = 28
GUTENBERG_LINE_CHARS = 52
# One guided offering is one physical page.  The complete bounded sequence is
# still mounted on the persistent book, but tutoring must not flash every page
# through the retina in one request.  Later pages require later physical
# experiences (including the existing contact-and-grip page transition).
GUTENBERG_GUIDED_PAGE_COUNT = 1
# A declared guide-facing catalogue, not a selector. Every immutable field is
# supplied back by the guide and cross-checked before acquisition. None of
# these fields enters cognition; only rendered page light does.
GUTENBERG_CATALOGUE = (
    {
        "gutenberg_id": "11",
        "display_title": "Alice's Adventures in Wonderland",
        "source_url": HOME_BOOK_GUTENBERG_SOURCE_URL,
        "edition": HOME_BOOK_GUTENBERG_EDITION,
        "language_tag": "en",
        "attribution": GUTENBERG_ATTRIBUTION,
        "rights_basis": "public_domain",
        "rights_statement": GUTENBERG_RIGHTS_STATEMENT,
    },
    {
        "gutenberg_id": "1342",
        "display_title": "Pride and Prejudice",
        "source_url": "https://www.gutenberg.org/files/1342/1342-0.txt",
        "edition": "1342-0.txt",
        "language_tag": "en",
        "attribution": GUTENBERG_ATTRIBUTION,
        "rights_basis": "public_domain",
        "rights_statement": GUTENBERG_RIGHTS_STATEMENT,
    },
    {
        "gutenberg_id": "74",
        "display_title": "The Adventures of Tom Sawyer",
        "source_url": "https://www.gutenberg.org/files/74/74-0.txt",
        "edition": "74-0.txt",
        "language_tag": "en",
        "attribution": GUTENBERG_ATTRIBUTION,
        "rights_basis": "public_domain",
        "rights_statement": GUTENBERG_RIGHTS_STATEMENT,
    },
    {
        "gutenberg_id": "16",
        "display_title": "Peter Pan",
        "source_url": "https://www.gutenberg.org/files/16/16-0.txt",
        "edition": "16-0.txt",
        "language_tag": "en",
        "attribution": GUTENBERG_ATTRIBUTION,
        "rights_basis": "public_domain",
        "rights_statement": GUTENBERG_RIGHTS_STATEMENT,
    },
    {
        "gutenberg_id": "55",
        "display_title": "The Wonderful Wizard of Oz",
        "source_url": "https://www.gutenberg.org/files/55/55-0.txt",
        "edition": "55-0.txt",
        "language_tag": "en",
        "attribution": GUTENBERG_ATTRIBUTION,
        "rights_basis": "public_domain",
        "rights_statement": GUTENBERG_RIGHTS_STATEMENT,
    },
)
CREDENTIAL_BLOCKED_SHELVES = {
    "youtube": "YOUTUBE_API_KEY",
    "khan_academy": "KHAN_ACADEMY_API_KEY",
    "pbs_kids": "PBS_KIDS_API_KEY",
    "spotify": "SPOTIFY_CLIENT_ID",
}
def _shelf_capability(name: str) -> dict[str, object]:
    """What each shelf can honestly do right now."""

    if name == "gutenberg":
        return {
            "available": True,
            "autonomous_selection": False,
            "catalogue": [dict(entry) for entry in GUTENBERG_CATALOGUE],
            "endpoint": GUTENBERG_ENDPOINT,
            "reason": (
                "a guide must name one exact approved public-domain edition; "
                "its source bytes are preserved before its pages are rendered "
                "to the same 27 retinal receptor sites used by other physical "
                "visual material. No catalogue field, text, title, author, or "
                "meaning enters cognition. Native grip-to-world-object action "
                "and palmar consequence are mounted. The persistent book is "
                "bound to an immutable source sequence when that source is in "
                "custody; only native contact and grip motion can advance it"
            ),
            "status": "mounted_guided_world_book_action_awaiting_witness",
        }
    credential = CREDENTIAL_BLOCKED_SHELVES[name]
    return {
        "available": False,
        "autonomous_selection": False,
        "endpoint": None,
        "missing_credential": credential,
        "reason": (
            f"this shelf is not mounted because {credential} is not held by "
            "this deployment, so there is nothing to fetch and nothing to "
            "present; the refusal names the missing credential rather than "
            "implying the pathway is unbuilt"
        ),
        "status": "not_mounted_missing_credential",
    }


def _gutenberg_pages(text: str) -> list[bytes]:
    """Render a bounded run of a public-domain text to pages of light."""

    from PIL import Image, ImageDraw

    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > GUTENBERG_LINE_CHARS and line:
            lines.append(line)
            line = word
        else:
            line = candidate
        if len(lines) >= GUTENBERG_PAGE_LINES * OFFERED_PAGE_MAX_COUNT:
            break
    if line and len(lines) < GUTENBERG_PAGE_LINES * OFFERED_PAGE_MAX_COUNT:
        lines.append(line)
    if not lines:
        raise ValueError("the fetched text carried no presentable lines")
    pages = []
    for start in range(0, len(lines), GUTENBERG_PAGE_LINES):
        image = Image.new("RGB", (768, 432), (253, 250, 244))
        draw = ImageDraw.Draw(image)
        for index, row in enumerate(lines[start : start + GUTENBERG_PAGE_LINES]):
            draw.text((28, 14 + index * 14), row, fill=(16, 24, 32))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pages.append(buffer.getvalue())
    return pages[:OFFERED_PAGE_MAX_COUNT]


def _guided_gutenberg_rosters(
    pages: list[bytes],
) -> list[tuple[float, ...]]:
    """Reduce exactly one current guided page to physical retinal light."""

    if not pages:
        raise ValueError("the guided Gutenberg source carried no page")
    return [
        _live_frame_luminance(page)
        for page in pages[:GUTENBERG_GUIDED_PAGE_COUNT]
    ]


OFFERED_MATERIAL_ENDPOINT = "/api/v1/material/offered"
SOURCE_MEDIA_CUSTODY_ENDPOINT = "/api/v1/material/custody"
RENDERED_LIGHT_ENDPOINT = "/api/v1/material/rendered-light"
RENDERED_LIGHT_SCHEMA = "guala.native.browser_visual_material.v1"
OFFERED_MATERIAL_SCHEMA = "guala.native.browser_material.v2"
# Bounds are declared, not discovered (lean-substrate doctrine): the page
# reads max_bytes off the capability and refuses oversized material before it
# ever leaves the browser.
OFFERED_MATERIAL_MAX_BYTES = 24 * 1024 * 1024
OFFERED_VISUAL_MAX_HOPS = 24
OFFERED_PAGE_MAX_COUNT = 12
VISUAL_MATERIAL_KINDS = ("picture", "pdf", "book")
AUDIBLE_MATERIAL_KINDS = ("audio", "song")
VIDEO_MATERIAL_KINDS = ("video",)
LOCAL_MATERIAL_KINDS = (
    VISUAL_MATERIAL_KINDS + AUDIBLE_MATERIAL_KINDS + VIDEO_MATERIAL_KINDS
)


def _validate_offered_media_type(material_kind: str, media_type: object) -> str:
    if (
        not isinstance(media_type, str)
        or not media_type
        or media_type != media_type.strip()
    ):
        raise ValueError("offered material requires its exact media type")
    accepted = (
        material_kind == "picture" and media_type.startswith("image/")
        or material_kind == "pdf" and media_type == "application/pdf"
        or material_kind == "book"
        and media_type in {"text/plain", "application/epub+zip"}
        or material_kind in AUDIBLE_MATERIAL_KINDS
        and media_type.startswith("audio/")
        or material_kind == "video" and media_type.startswith("video/")
    )
    if not accepted:
        raise ValueError(
            f"offered {material_kind} media type {media_type!r} is not admitted"
        )
    return media_type


def _offered_visual_episodes(
    assembly_prefix: str,
    rosters: list[tuple[float, ...]],
    *,
    contact: tuple[float, ...] | None = None,
    release_after: bool = True,
) -> list[tuple[Any, list[tuple[int, int]]]]:
    """Present offered light for one hop per raster, then let it end.

    The exact construction the live camera uses, plus the ended dark hops a
    card lesson uses so the presentation genuinely finishes and the retinal
    cohort can settle at the stimulus boundary.
    """

    times = _quiescent_hop_times()
    silence = (0.0,) * len(times)
    dark = (0.0,) * CARD_SURFACE_PORT_COUNT
    presented = list(rosters[:OFFERED_VISUAL_MAX_HOPS])
    if not presented:
        raise ValueError("offered material carried no presentable raster")
    frames = [(roster, contact) for roster in presented]
    if release_after:
        frames.extend((dark, None) for _ in range(LESSON_ENDED_HOP_COUNT))
    retinal_transmission = _eyelid_transmission_from_axes(
        _current_retinal_body_axes()
    )
    return [
        (
            _whole_roster_hop_episode(
                f"{assembly_prefix}-hop-{hop_index}",
                times,
                roster,
                silence,
                contact=held_contact,
                retinal_transmission=retinal_transmission,
            ),
            [(INTAKE_HOP_MILLISECONDS, 1000)] * LESSON_OCCURRENCE_COUNT,
        )
        for hop_index, (roster, held_contact) in enumerate(frames)
    ]


def _decode_offered_rasters(
    material_kind: str,
    raw: bytes,
    media_type: str = "image/png",
) -> list[tuple[float, ...]]:
    """Reduce offered visual material to retinal rosters, one per presented page.

    A picture is one raster.  A PDF or a book is a bounded ordered sequence of
    them — pages are presented in their own order, which is the only thing a
    page order physically is.
    """

    from PIL import Image

    if material_kind == "picture":
        with Image.open(io.BytesIO(raw)) as image:
            return [_raster_luminance(image)]
    if material_kind == "book" and media_type == "text/plain":
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("offered plain-text book is not UTF-8") from error
        pages = _gutenberg_pages(text)
        return [_live_frame_luminance(page) for page in pages]
    import fitz

    filetype = "epub" if material_kind == "book" else "pdf"
    with fitz.open(stream=raw, filetype=filetype) as document:
        page_count = min(document.page_count, OFFERED_PAGE_MAX_COUNT)
        if page_count <= 0:
            raise ValueError("offered paged material declares no pages")
        rosters = []
        for index in range(page_count):
            pixmap = document.load_page(index).get_pixmap()
            with Image.frombytes(
                "RGB" if pixmap.n >= 3 else "L",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            ) as image:
                rosters.append(_raster_luminance(image))
    return rosters


def _decode_offered_audio(raw: bytes) -> tuple[int, tuple[int, ...]]:
    """Decode offered audio to the exact format her cochlea is declared for.

    ffmpeg is the decoder (it is in the production image); the OUTPUT is the
    same pcm_s16le mono 16 kHz her tutor audio and her microphone already
    deliver, so nothing new reaches her — only more of what already does.
    """

    import subprocess

    with tempfile.NamedTemporaryFile(suffix=".bin") as source:
        source.write(raw)
        source.flush()
        completed = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", source.name,
                "-f", "s16le", "-ac", "1", "-ar", str(COCHLEAR_SAMPLE_RATE_HZ),
                "-t", str(AMBIENT_INTAKE_MAX_SECONDS), "-",
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    if completed.returncode != 0 or len(completed.stdout) < 4:
        detail = completed.stderr.decode("utf-8", "replace").strip()[:200]
        raise ValueError(f"offered audio could not be decoded: {detail or 'no samples'}")
    payload = completed.stdout[: len(completed.stdout) // 2 * 2]
    return COCHLEAR_SAMPLE_RATE_HZ, struct.unpack(f"<{len(payload) // 2}h", payload)


def _offered_material_capability(kind: str, available: bool, reason: str) -> dict[str, object]:
    return {
        "available": available,
        "custody_endpoint": SOURCE_MEDIA_CUSTODY_ENDPOINT,
        "endpoint": OFFERED_MATERIAL_ENDPOINT if available else None,
        "material_kind": kind,
        "max_bytes": OFFERED_MATERIAL_MAX_BYTES,
        "max_source_count": _source_media_store.max_source_count,
        "max_total_source_bytes": _source_media_store.max_total_bytes,
        "provenance_required": True,
        "reason": reason,
        "source_bytes_preserved_before_decode": True,
        "status": "mounted" if available else "not_mounted",
    }


SPOKEN_LESSON_ENDPOINT = "/api/v1/curriculum/teach-card-spoken"


def _spoken_voice_refusal() -> JSONResponse | None:
    """Why a human voice may not carry a lesson yet, or None when it may.

    Only ONE condition, and it is about her body, not about transport: the
    cochleae must physically transduce.  Unlike the standalone microphone
    there is no two-real-signal question to answer — the card's own light
    and its tactile footprint reach her in the SAME episode as the voice, so
    a spoken lesson is a whole-sensorium experience by construction.  That
    is the entire reason this route exists rather than reusing the PCM
    session: a lesson taught in a person's own voice is one experience, and
    three separate intakes are three.
    """

    if not COCHLEAR_EARS_AUTHORIZED:
        return _refusal(503, _SOUND_SUSPENSION_REASON)
    return None


def _decode_material_body(payload: dict[str, Any], field: str) -> bytes:
    encoded = payload.get(field)
    if not isinstance(encoded, str) or not encoded:
        raise ValueError(f"offered material requires {field}")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("offered material is not canonical base64") from error
    if not raw:
        raise ValueError("offered material is empty")
    if len(raw) > OFFERED_MATERIAL_MAX_BYTES:
        raise ValueError(
            f"offered material is {len(raw)} bytes, over the declared "
            f"{OFFERED_MATERIAL_MAX_BYTES}-byte bound"
        )
    return raw


@app.post(RENDERED_LIGHT_ENDPOINT)
def rendered_light_material(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Pixels a person rendered in their own browser, reaching her retina.

    The string they typed is NEVER submitted and never reaches this process:
    the page rasterises it locally and offers the light.  What she receives is
    a picture, exactly like any other picture, which is the only honest thing
    text can be to an organism that has not learned to read.
    """

    if not isinstance(payload, dict) or payload.get("schema") != RENDERED_LIGHT_SCHEMA:
        return _refusal(422, f"rendered light requires schema {RENDERED_LIGHT_SCHEMA}")
    try:
        raw = _decode_material_body(payload, "frame_b64")
        rosters = _decode_offered_rasters("picture", raw)
        episodes = _offered_visual_episodes(f"rendered-light-{uuid.uuid4()}", rosters)
    except (OSError, ValueError) as error:
        return _refusal(422, f"rendered light refused: {error}")
    try:
        result = _perform_admitted_intake(episodes, "rendered-light")
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted visual transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            "material_kind": "text_visual",
            "presented_raster_count": len(rosters),
            **_public_admitted_intake_result(result),
        },
    )


@app.get("/api/v1/curriculum/manifest")
def curriculum_manifest_api() -> JSONResponse:
    """Her approved curriculum, on a path that actually reaches her.

    The page used to fetch /curriculum/card_experience_manifest-v1.json,
    which the app does serve — but ONLY /api/* is routed to the app from the
    public side, so the browser got the CDN's 404 HTML and the card chooser
    died with "Unexpected token '<'". Shipped by me and caught by Joe on the
    live site.
    """

    try:
        document = _manifest_document(
            CURRICULUM_ROOT / "card_experience_manifest-v1.json",
            "guala.external_tutor_card_experience_manifest.v1",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _refusal(503, f"curriculum manifest is unavailable: {error}")
    return JSONResponse(status_code=200, content=document)


@app.get(WORLD_OBSERVATION_ENDPOINT)
def world_observation() -> JSONResponse:
    """What her place currently is, read-only and bounded."""

    if not WORLD_AUTHORIZED:
        return _refusal(
            503,
            "no world is mounted: she has nowhere to be, so there is nothing "
            f"to observe; a place is authorized by {WORLD_ENV}",
        )
    try:
        snapshot = _world().observation_snapshot()
    except (OSError, RuntimeError, ValueError) as error:
        return _refusal(503, f"her place could not be read: {error}")
    body = next(
        item for item in snapshot.bodies if item.body_id == snapshot.self_body_id
    )
    # THE REAL GEOMETRY, NOT A COUNT (2026-08-08).
    #
    # This used to answer "3 rooms, 42 things" and nothing else, which from
    # outside is indistinguishable from a claim with nothing behind it. Joe
    # said so plainly: if he cannot see it, it does not exist. Every number
    # below is read straight off the world's own authenticated snapshot, so a
    # drawing made from it is a picture OF HER PLACE rather than an artist's
    # impression of one.
    return JSONResponse(
        status_code=200,
        content={
            "schema": "guala.native.world_observation.v1",
            "revision": snapshot.revision,
            "region_count": len(getattr(snapshot, "regions", ()) or ()),
            "object_count": len(snapshot.objects),
            "body_count": len(snapshot.bodies),
            "regions": [
                {
                    "region_id": region.region_id,
                    "min_x_mm": region.bounds.minimum.x,
                    "min_y_mm": region.bounds.minimum.y,
                    "max_x_mm": region.bounds.maximum.x,
                    "max_y_mm": region.bounds.maximum.y,
                    "illumination_ppm": region.illumination_ppm,
                }
                for region in (getattr(snapshot, "regions", ()) or ())
            ],
            "portals": [
                {
                    "portal_id": portal.portal_id,
                    "axis": str(portal.axis),
                    "plane_mm": portal.plane_mm,
                    "aperture_min_mm": portal.aperture_min_mm,
                    "aperture_max_mm": portal.aperture_max_mm,
                }
                for portal in (getattr(snapshot, "portals", ()) or ())
            ],
            "objects": [
                {
                    "object_id": item.object_id,
                    "x_mm": item.position.x,
                    "y_mm": item.position.y,
                    "radius_mm": item.radius_mm,
                    "held": item.held_by_body_id is not None,
                    # Drawn colour comes from the thing's OWN declared
                    # reflectance across her six optical bands, so what is on
                    # the screen is what her eyes are given rather than a
                    # palette somebody picked to make the picture look nice.
                    "reflectance_ppm": list(item.reflectance_ppm),
                    "warmth_millikelvin": (
                        item.material.surface_temperature_millikelvin
                        if item.material is not None
                        else None
                    ),
                }
                for item in snapshot.objects
                if item.position is not None
            ],
            "bodies": [
                {
                    "body_id": item.body_id,
                    "is_her": item.body_id == snapshot.self_body_id,
                    "x_mm": item.pose.position.x,
                    "y_mm": item.pose.position.y,
                    "heading_millidegrees": item.pose.heading_millidegrees,
                    "radius_mm": item.radius_mm,
                    "held_object_id": getattr(item, "held_object_id", None),
                    "active_contact_kind": (
                        item.active_contact.kind
                        if getattr(item, "active_contact", None) is not None
                        else None
                    ),
                    "active_contact_object_id": (
                        item.active_contact.object_id
                        if getattr(item, "active_contact", None) is not None
                        else None
                    ),
                }
                for item in snapshot.bodies
            ],
            "her_pose": {
                "x_mm": body.pose.position.x,
                "y_mm": body.pose.position.y,
                "z_mm": body.pose.position.z,
                "heading_millidegrees": body.pose.heading_millidegrees,
            },
            # TRUTH-COUPLED, NOT DECLARED: this is true only once a step she
            # took herself has actually been applied by her place and carried
            # to her balance receptors. Before that it stays false, and the
            # reason says which part is missing.
            "she_moves_herself": bool(
                _last_self_moved and _last_self_moved.get("moved")
            ),
            "her_last_step": _last_self_moved,
            "place_rebuilt_reason": _world_rebuild_reason,
            "why_she_is_not_moving": (
                None
                if (_last_self_moved and _last_self_moved.get("moved"))
                else (_last_self_moved or {}).get("why")
                or "she has not had an interval to herself yet: she only "
                "moves on her own during unattended time, when nobody is "
                "doing anything to her"
            ),
            "reason": (
                "a deterministic place with its own physics; what she sees "
                "here reaches the same 27 retinal sites a card reaches, and "
                "moving in it produces the displacement her balance and "
                "body-position receptors transduce"
            ),
        },
    )


@app.post(WORLD_OTHER_BODY_ACTION_ENDPOINT)
@app.post(WORLD_OTHER_BODY_MOVE_ENDPOINT)
def world_other_body_move(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Let an external participant act only through its authenticated body."""

    global _reciprocal_social_play_candidate
    global _active_cross_intake_causal_motor_traces
    if not WORLD_AUTHORIZED:
        return _refusal(503, "no persistent world is mounted")
    if not isinstance(payload, dict):
        return _refusal(422, "an other-body action requires a JSON body")
    operation = payload.get("operation", "move")
    if operation not in {
        "move",
        "pick",
        "place",
        "take",
        "surface_contact",
        *_COMPANION_CONTACT_OPERATIONS,
    }:
        return _refusal(
            422,
            "an other-body action operation must be 'move', 'pick', "
            "'place', 'take', 'surface_contact', or one declared companion "
            "contact",
        )
    x = y = heading = signed_yaw = None
    object_id = None
    surface_actuations: tuple[Any, ...] = ()
    surface_duration_microseconds = WORLD_BODY_ACTION_MILLISECONDS * 1_000
    if operation == "move":
        try:
            x = int(payload["x_mm"])
            y = int(payload["y_mm"])
            heading = int(payload["heading_millidegrees"])
            signed_yaw = int(payload.get("signed_yaw_millidegrees", 0))
        except (KeyError, TypeError, ValueError):
            return _refusal(
                422,
                "an other-body move requires integer x_mm, y_mm, "
                "heading_millidegrees, and signed_yaw_millidegrees",
            )
        if any(isinstance(payload.get(name), bool) for name in (
            "x_mm",
            "y_mm",
            "heading_millidegrees",
            "signed_yaw_millidegrees",
        )):
            return _refusal(
                422,
                "other-body coordinates and yaw must be integers",
            )
        if not -(1 << 31) <= signed_yaw < (1 << 31):
            return _refusal(
                422,
                "signed_yaw_millidegrees exceeds signed 32-bit range",
            )
    elif operation in _COMPANION_CONTACT_OPERATIONS:
        if set(payload) != {"operation"}:
            return _refusal(
                422,
                "a named companion contact accepts no authored physical or reward fields",
            )
        surface_actuations, surface_duration_microseconds = (
            _companion_contact_profile(operation, "guala-body-1")
        )
    elif operation == "surface_contact":
        from dsf_ai_service.substrate.embodiment_world import (
            BodySurfaceActuation,
        )

        raw_actuations = payload.get("actuations")
        try:
            surface_duration_microseconds = int(
                payload.get(
                    "duration_microseconds",
                    WORLD_BODY_ACTION_MILLISECONDS * 1_000,
                )
            )
        except (TypeError, ValueError):
            return _refusal(
                422,
                "a surface contact duration must be an integer number of microseconds",
            )
        if (
            isinstance(payload.get("duration_microseconds"), bool)
            or not isinstance(raw_actuations, list)
            or not raw_actuations
        ):
            return _refusal(
                422,
                "a surface contact requires one or more explicit physical actuations",
            )
        parsed = []
        try:
            for raw in raw_actuations:
                if not isinstance(raw, dict) or set(raw) != {
                    "actor_site_id",
                    "compression_micrometres",
                    "recipient_body_id",
                    "recipient_site_id",
                    "tangential_u_micrometres",
                    "tangential_v_micrometres",
                }:
                    raise ValueError("surface actuation fields changed")
                if any(
                    isinstance(raw.get(name), bool)
                    for name in (
                        "compression_micrometres",
                        "tangential_u_micrometres",
                        "tangential_v_micrometres",
                    )
                ):
                    raise ValueError("surface displacement must be integer")
                actuation = BodySurfaceActuation(
                    actor_site_id=raw["actor_site_id"],
                    recipient_body_id=raw["recipient_body_id"],
                    recipient_site_id=raw["recipient_site_id"],
                    compression_micrometres=int(
                        raw["compression_micrometres"]
                    ),
                    tangential_u_micrometres=int(
                        raw["tangential_u_micrometres"]
                    ),
                    tangential_v_micrometres=int(
                        raw["tangential_v_micrometres"]
                    ),
                )
                actuation.verify()
                parsed.append(actuation)
        except (KeyError, TypeError, ValueError) as error:
            return _refusal(422, f"surface contact is invalid: {error}")
        surface_actuations = tuple(parsed)
    elif operation == "pick":
        object_id = payload.get("object_id")
        if not isinstance(object_id, str) or not object_id:
            return _refusal(
                422,
                "an other-body pick requires a nonempty object_id",
            )
    elif operation == "take":
        if set(payload) != {"operation"}:
            return _refusal(
                422,
                "an other-body take is resolved only from current contact "
                "geometry and accepts no object or body identity",
            )
    else:
        object_id = payload.get("object_id")
        try:
            x = int(payload["x_mm"])
            y = int(payload["y_mm"])
        except (KeyError, TypeError, ValueError):
            return _refusal(
                422,
                "an other-body place requires a nonempty object_id and "
                "integer x_mm and y_mm",
            )
        if (
            not isinstance(object_id, str)
            or not object_id
            or isinstance(payload.get("x_mm"), bool)
            or isinstance(payload.get("y_mm"), bool)
        ):
            return _refusal(
                422,
                "an other-body place requires a nonempty object_id and "
                "integer x_mm and y_mm",
            )

    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt,
        BodySurfaceContactCommand,
        MoveCommand,
        PickCommand,
        PlaceCommand,
        PoseMM,
        PositionMM,
        PreparedActionExecution,
        SECOND_BODY_PORT_ID,
        TakeContactHeldObjectCommand,
        encode_command,
    )
    with _transition_lock:
        authority = _world()
        before = authority.observation_snapshot()
        other_port = next(
            item
            for item in authority.actor_ports
            if item.port_id == SECOND_BODY_PORT_ID
        )
        other = next(
            item for item in before.bodies
            if item.body_id == other_port.actor_body_id
        )
        if operation == "move":
            assert x is not None
            assert y is not None
            assert heading is not None
            assert signed_yaw is not None
            successor_heading, _trajectory = exact_native_yaw_trajectory(
                predecessor_heading_millidegrees=other.pose.heading_millidegrees,
                signed_displacement_millidegrees=signed_yaw,
                duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            )
            if successor_heading != heading:
                return _refusal(
                    422,
                    "signed_yaw_millidegrees does not settle at the requested "
                    "other-body heading",
                )
            intent_body = {
                "actor_body_id": other.body_id,
                "expected_world_revision": before.revision,
                "operation": operation,
                "signed_yaw_millidegrees": signed_yaw,
                "target_heading_millidegrees": heading,
                "target_x_mm": x,
                "target_y_mm": y,
            }
            command = MoveCommand(
                target_pose=PoseMM(PositionMM(x, y, 0), heading),
                duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            )
            action_detail = {
                "heading_millidegrees": heading,
                "signed_yaw_millidegrees": signed_yaw,
                "x_mm": x,
                "y_mm": y,
            }
        elif operation == "surface_contact" or operation in _COMPANION_CONTACT_OPERATIONS:
            intent_body = {
                "actor_body_id": other.body_id,
                "actuations": [
                    actuation.as_record()
                    for actuation in surface_actuations
                ],
                "duration_microseconds": surface_duration_microseconds,
                "expected_world_revision": before.revision,
                "operation": operation,
            }
            command = BodySurfaceContactCommand(
                actuations=surface_actuations,
                duration_microseconds=surface_duration_microseconds,
            )
            action_detail = {
                "actuations": intent_body["actuations"],
                "duration_microseconds": surface_duration_microseconds,
            }
        elif operation == "pick":
            assert object_id is not None
            intent_body = {
                "actor_body_id": other.body_id,
                "expected_world_revision": before.revision,
                "object_id": object_id,
                "operation": operation,
            }
            command = PickCommand(
                object_id=object_id,
                duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            )
            action_detail = {"object_id": object_id}
        elif operation == "take":
            intent_body = {
                "actor_body_id": other.body_id,
                "expected_world_revision": before.revision,
                "operation": operation,
            }
            command = TakeContactHeldObjectCommand(
                duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            )
            action_detail = {}
        else:
            assert object_id is not None
            assert x is not None
            assert y is not None
            intent_body = {
                "actor_body_id": other.body_id,
                "expected_world_revision": before.revision,
                "object_id": object_id,
                "operation": operation,
                "target_x_mm": x,
                "target_y_mm": y,
            }
            command = PlaceCommand(
                object_id=object_id,
                target_position=PositionMM(x, y, 0),
                duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
            )
            action_detail = {
                "object_id": object_id,
                "x_mm": x,
                "y_mm": y,
            }
        intent = _receipt(intent_body)
        try:
            prepared = authority.prepare_port_command(
                port_id=SECOND_BODY_PORT_ID,
                command_payload=encode_command(command),
                causal_intent_receipt_sha256=intent,
                expected_revision=before.revision,
            )
        except (RuntimeError, TypeError, ValueError) as error:
            return _refusal(422, f"the other-body action was refused: {error}")
        if isinstance(prepared, ActionExecutionReceipt):
            return _refusal(
                409,
                f"the other-body action was refused: {prepared.reason}",
            )
        if not isinstance(prepared, PreparedActionExecution):
            return _refusal(503, "the other-body action lost its prepared state")
        execution = prepared.execution_receipt
        body_surface_contacts = (
            authority.body_surface_contacts_for_prepared_action(prepared)
            if (
                operation == "surface_contact"
                or operation in _COMPANION_CONTACT_OPERATIONS
            )
            else ()
        )
        if operation == "take":
            resolved_body = next(
                item
                for item in execution.after.bodies
                if item.body_id == other.body_id
            )
            if resolved_body.held_object_id is None:
                authority.discard_prepared_action(prepared)
                return _refusal(
                    503,
                    "the prepared other-body take lost its physical object",
                )
            action_detail = {
                "resolved_object_id": resolved_body.held_object_id,
            }
        try:
            (
                consequence_episode,
                consequence_admissions,
                consequence_lane_truth,
            ) = _action_consequence_episode(
                execution,
                action_duration=Fraction(
                    (
                        surface_duration_microseconds
                        if (
                            operation == "surface_contact"
                            or operation in _COMPANION_CONTACT_OPERATIONS
                        )
                        else WORLD_BODY_ACTION_MILLISECONDS * 1_000
                    ),
                    1_000_000,
                ),
                body_surface_contacts=body_surface_contacts,
            )
            visual_changed = int(consequence_lane_truth["visual"]["changed"])
            tactile_changed = int(
                consequence_lane_truth["tactile"]["changed"]
            )
        except (RuntimeError, TypeError, ValueError) as error:
            authority.discard_prepared_action(prepared)
            return _refusal(
                422,
                f"the other-body action could not reach Guala's sensorium: {error}",
            )

        predecessor_world = authority.encoded_snapshot()
        committed = False
        persisted = False
        try:
            with authority.prepared_action_visibility_transaction(prepared):
                execution = authority.commit_prepared_action(prepared)
                committed = True
                successor_world = authority.encoded_committed_prepared_action(
                    prepared
                )
                _persist_world_body(successor_world)
                persisted = True
        except BaseException as error:
            if committed:
                with authority.committed_prepared_action_rollback_transaction(
                    prepared
                ) as rollback_world:
                    rollback_world()
                if persisted:
                    _persist_world_body(predecessor_world)
            else:
                authority.discard_prepared_action(prepared)
            return _refusal(
                503,
                f"the other-body action could not persist: "
                f"{type(error).__name__}: {error}",
            )

        action = {
            "actor_body_id": execution.actor_body_id,
            "authority_receipt_sha256": execution.authority_receipt_sha256,
            "causal_intent_receipt_sha256": intent,
            "operation": operation,
            "port_id": execution.port_id,
            "tactile_changed_receptor_count": tactile_changed,
            "visual_changed_receptor_count": visual_changed,
            "world_revision_after": execution.after.revision,
            "world_revision_before": execution.before.revision,
            "world_state_after_sha256": execution.after.state_sha256,
            "world_state_before_sha256": execution.before.state_sha256,
            **action_detail,
        }
        action["evidence_receipt_sha256"] = _receipt(action)
        prior_social_candidate = _reciprocal_social_play_candidate
        prior_cross_intake_traces = dict(
            _active_cross_intake_causal_motor_traces
        )
        if visual_changed > 0:
            _reciprocal_social_play_candidate = (
                _advance_social_play_on_other_body_action(
                    _reciprocal_social_play_candidate,
                    action,
                )
            )
            # A later participant stimulus supersedes any still-propagating
            # prior participant frontier. This clears observation only; it
            # does not alter the organism or its retained experience.
            _active_cross_intake_causal_motor_traces = {
                key: paths
                for key, paths in _active_cross_intake_causal_motor_traces.items()
                if key[0] != "external_participant_sensory"
            }
        try:
            sensory_result = _perform_admitted_intake_locked(
                [(consequence_episode, consequence_admissions)],
                f"external-participant-world-action:{intent}",
                external_participant_action_receipt=(
                    intent if visual_changed > 0 else None
                ),
            )
        except (RuntimeError, TypeError, ValueError) as error:
            _reciprocal_social_play_candidate = prior_social_candidate
            _active_cross_intake_causal_motor_traces = (
                prior_cross_intake_traces
            )
            _refresh_public_observation_cache()
            return JSONResponse(
                status_code=503,
                content={
                    "accepted": True,
                    "action": action,
                    "ok": False,
                    "reason": (
                        "the other body acted and persisted, but its exact "
                        "sensory transition was refused; do not repeat the "
                        f"action ({type(error).__name__}: {error})"
                    ),
                    "schema": "guala.external_embodied_participant_action.v1",
                    "sensory_delivery": {"accepted": False},
                    "social_play_opportunity_reached_vision": False,
                },
            )
        _refresh_public_observation_cache()
        return JSONResponse(
            status_code=200,
            content={
                "accepted": True,
                "action": action,
                "ok": True,
                "schema": "guala.external_embodied_participant_action.v1",
                "sensory_delivery": {
                    "accepted": True,
                    "hop_count": sensory_result["hop_count"],
                    "organism_tick": sensory_result["persisted"]["organism_tick"],
                    "state_sha256": sensory_result["persisted"]["state_sha256"],
                },
                "social_play_opportunity_reached_vision": visual_changed > 0,
            },
        )


def _embodied_curriculum_invitation(
    *,
    experience_kind: str,
    experience_id: str,
    media_receipts: dict[str, str],
) -> JSONResponse:
    """Prepare one exact tutor presentation without claiming attention.

    The sensory occurrence itself is the tutor's physical action.  A separate
    participant-silhouette movement is neither its cause nor permission for
    it, and a coarse or vertically unresolved body image must never veto
    lawful light, pressure, or touch.  This bounded record binds only the
    reviewed media to the current resident/world boundary so one prepared
    presentation can be consumed once.  It chooses nothing for Guala and
    makes no attention, recognition, meaning, or learning claim.
    """

    global _curriculum_invitation
    try:
        with _transition_lock:
            restored, _admission = _runtime()
            world = _world().observation_snapshot()
            invitation = {
                "schema": CURRICULUM_INVITATION_SCHEMA,
                "experience_kind": experience_kind,
                "experience_id": experience_id,
                **media_receipts,
                "observed_at_organism_tick": restored.pointer.organism_tick,
                "observed_state_sha256": restored.pointer.state_sha256,
                "world_revision_before": world.revision,
                "world_revision_after": world.revision,
                "outcome": "presentable",
                "presentation_eligible": True,
                "reason": (
                    "one reviewed tutor sensory occurrence is prepared at "
                    "the current resident/world boundary; only its physical "
                    "light, pressure, and declared contact may enter, and "
                    "Guala's neurons remain the sole attention and learning "
                    "authority"
                ),
                "status": "tutor_physical_presentation_prepared",
            }
            invitation["invitation_receipt_sha256"] = _receipt(invitation)
            _curriculum_invitation = invitation
            _refresh_public_observation_cache()
            return JSONResponse(
                status_code=200,
                content={
                    "accepted": True,
                    "ok": True,
                    "schema": CURRICULUM_INVITATION_SCHEMA,
                    "invitation": _curriculum_invitation_record(),
                },
            )
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"curriculum presentation preparation refused: {error}")


@app.post(
    CURRICULUM_INVITE_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def invite_card(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Prepare, and optionally present, one approved physical card occurrence."""

    if not isinstance(payload, dict):
        return _refusal(422, "a curriculum invitation requires a JSON body")
    card_id = payload.get("card_id")
    if not isinstance(card_id, str) or not card_id:
        return _refusal(422, "a curriculum invitation requires an approved card_id")
    presentation = payload.get("presentation")
    if presentation is not None and presentation not in PRESENTATION_MODES:
        return _refusal(
            422,
            "an invited card presentation must be one of "
            + ", ".join(repr(mode) for mode in PRESENTATION_MODES),
        )
    try:
        experience = _read_manifest_card(card_id)
    except KeyError:
        return _refusal(
            404,
            f"card {card_id!r} is not in the approved curriculum manifest",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _refusal(503, f"curriculum manifest is unavailable: {error}")
    surface = experience.get("surface")
    surface_sha256 = surface.get("sha256") if isinstance(surface, dict) else None
    if not isinstance(surface_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", surface_sha256
    ):
        return _refusal(503, "approved curriculum surface receipt is unavailable")
    episodes = None
    if presentation is not None:
        try:
            # The lesson body includes the current eyelid/retinal axes.  An
            # unattended interval may already own the native body when this
            # external request arrives, so read those axes under the same
            # re-entrant transition lock used by every physical interval.
            # The external-intake signal remains raised after this read and
            # keeps unattended time behind the invitation and lesson.
            with _transition_lock:
                episodes = _card_lesson_hop_episodes(
                    card_id,
                    experience,
                    presentation,
                )
        except HTTPException:
            raise
        except (OSError, ValueError) as error:
            return _refusal(503, f"approved curriculum media refused: {error}")
    invitation_response = _embodied_curriculum_invitation(
        experience_kind="card",
        experience_id=card_id,
        media_receipts={"card_id": card_id, "surface_sha256": surface_sha256},
    )
    if presentation is None or invitation_response.status_code != 200:
        return invitation_response
    invitation_body = json.loads(invitation_response.body)
    invitation = invitation_body.get("invitation")
    invitation_receipt = (
        invitation.get("invitation_receipt_sha256")
        if isinstance(invitation, dict)
        else None
    )
    if not isinstance(invitation_receipt, str) or not re.fullmatch(
        r"[0-9a-f]{64}", invitation_receipt
    ):
        return _refusal(503, "prepared tutor occurrence lost its exact receipt")
    try:
        result = _perform_card_lesson_intake(
            episodes,
            f"curriculum-card:{card_id}:{presentation}",
            card_id,
            experience,
            presentation,
            invitation_receipt,
        )
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"prepared lesson transition refused: {error}")
    curiosity = _intrinsic_curiosity_record()
    return JSONResponse(
        status_code=200,
        content={
            **invitation_body,
            "lesson": {
                "accepted": True,
                "card_id": card_id,
                "curiosity_status": curiosity["status"],
                "hop_count": result["hop_count"],
                "persisted": result["persisted"],
                "presentation": presentation,
                "receptor_ingress": result["receptor_ingress"],
                "social_experience_claimed": curiosity[
                    "social_experience_claimed"
                ],
                "totals": result["totals"],
            },
        },
    )


@app.post(
    CURRICULUM_INVITE_SONG_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def invite_song(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Prepare one approved synchronized physical song occurrence."""

    if not isinstance(payload, dict):
        return _refusal(422, "a song invitation requires a JSON body")
    song_id = payload.get("song_id")
    if not isinstance(song_id, str) or not song_id:
        return _refusal(422, "a song invitation requires an approved song_id")
    try:
        experience = _read_manifest_song(song_id)
    except KeyError:
        return _refusal(
            404,
            f"song {song_id!r} is not in the approved curriculum manifest",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _refusal(503, f"song curriculum manifest is unavailable: {error}")
    audio = experience.get("audio")
    audio_sha256 = audio.get("sha256") if isinstance(audio, dict) else None
    if not isinstance(audio_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", audio_sha256
    ):
        return _refusal(503, "approved song audio receipt is unavailable")
    return _embodied_curriculum_invitation(
        experience_kind="song",
        experience_id=song_id,
        media_receipts={"song_id": song_id, "audio_sha256": audio_sha256},
    )


@app.post(WORLD_MOVE_ENDPOINT)
def world_move(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Move her body in her place, and let her sense that it happened.

    A person moves her, exactly as a person presents a card: authored
    presentation, never a claim that she chose to go. When she can choose,
    the same pathway carries it — that is what makes this the road to
    autonomy rather than a detour around it.
    """

    global _last_displacement

    if not WORLD_AUTHORIZED:
        return _refusal(
            503,
            "no world is mounted: she has nowhere to move, and a displacement "
            f"receptor with nothing moving would be a fabrication ({WORLD_ENV})",
        )
    if not VESTIBULAR_AUTHORIZED:
        return _refusal(
            503,
            "her displacement receptors are not mounted, so a move would "
            f"reach nothing she can feel ({VESTIBULAR_ENV})",
        )
    if not isinstance(payload, dict):
        return _refusal(422, "a move requires a JSON body")
    try:
        x = int(payload["x_mm"])
        y = int(payload["y_mm"])
        heading = int(payload.get("heading_millidegrees", 0))
    except (KeyError, TypeError, ValueError):
        return _refusal(422, "a move requires integer x_mm, y_mm and heading_millidegrees")
    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt,
        PORT_ID,
        MoveCommand,
        PoseMM,
        PositionMM,
        PreparedActionExecution,
        encode_command,
    )

    _begin_external_intake()
    try:
        with _transition_lock:
            try:
                authority = _world()
                root_yaw_source_tick = int(
                    _runtime()[0].organism.readiness().organism_tick
                )
                before = authority.observation_snapshot()
                before_body = next(
                    body
                    for body in before.bodies
                    if body.body_id == before.self_body_id
                )
                signed_yaw_value = payload.get("signed_yaw_millidegrees")
                if signed_yaw_value is None:
                    if heading != before_body.pose.heading_millidegrees:
                        return _refusal(
                            422,
                            "a changed heading requires signed_yaw_millidegrees; "
                            "start and end headings cannot reveal turn direction "
                            "or revolutions",
                        )
                    signed_yaw = 0
                else:
                    if isinstance(signed_yaw_value, bool):
                        return _refusal(
                            422,
                            "signed_yaw_millidegrees must be an integer",
                        )
                    signed_yaw = int(signed_yaw_value)
                    if not -(1 << 31) <= signed_yaw < (1 << 31):
                        return _refusal(
                            422,
                            "signed_yaw_millidegrees exceeds the native signed "
                            "32-bit body range",
                        )
                predecessor_heading = before_body.pose.heading_millidegrees
                successor_heading, yaw_trajectory = exact_native_yaw_trajectory(
                    predecessor_heading_millidegrees=predecessor_heading,
                    signed_displacement_millidegrees=signed_yaw,
                    duration_microseconds=(
                        WORLD_BODY_ACTION_MILLISECONDS * 1_000
                    ),
                )
                if successor_heading != heading:
                    return _refusal(
                        422,
                        "signed_yaw_millidegrees does not settle at the requested "
                        "heading",
                    )
                intent = _receipt({
                    "actor_body_id": before.self_body_id,
                    "expected_world_revision": before.revision,
                    "heading_millidegrees": heading,
                    "signed_yaw_millidegrees": signed_yaw,
                    "x_mm": x,
                    "y_mm": y,
                })
                prepared = authority.prepare_port_command(
                    port_id=PORT_ID,
                    command_payload=encode_command(
                        MoveCommand(
                            target_pose=PoseMM(PositionMM(x, y, 0), heading),
                            duration_microseconds=(
                                WORLD_BODY_ACTION_MILLISECONDS * 1_000
                            ),
                        )
                    ),
                    causal_intent_receipt_sha256=intent,
                    expected_revision=before.revision,
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                return _refusal(422, f"her place refused that move: {error}")

            # HER PLACE HAS ITS OWN PHYSICS AND IT SAYS NO FOR REAL REASONS:
            # a wall, a doorway missed, another body or an object in the path.
            # A refused move does not reach her as invented zero displacement.
            if isinstance(prepared, ActionExecutionReceipt):
                return _refusal(
                    409,
                    f"her place refused that move: {prepared.reason}. Nothing "
                    "reached her, because nothing happened to her body",
                )
            if not isinstance(prepared, PreparedActionExecution):
                return _refusal(503, "her place lost its prepared movement")
            execution = prepared.execution_receipt
            try:
                moved = _world_displacement(execution.before, execution.after)
                consequence, admissions, _lane_truth = (
                    _action_consequence_episode(
                        execution,
                        action_duration=Fraction(
                            WORLD_BODY_ACTION_MILLISECONDS,
                            1_000,
                        ),
                        body_displacement=moved,
                    )
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                authority.discard_prepared_action(prepared)
                return _refusal(422, f"that move could not reach her: {error}")

            predecessor_world = authority.encoded_snapshot()
            committed = False
            persisted = False
            try:
                with authority.prepared_action_visibility_transaction(prepared):
                    execution = authority.commit_prepared_action(prepared)
                    committed = True
                    successor_world = authority.encoded_committed_prepared_action(
                        prepared
                    )
                    _persist_world_body(successor_world)
                    persisted = True
            except BaseException as error:
                if committed:
                    with authority.committed_prepared_action_rollback_transaction(
                        prepared
                    ) as rollback_world:
                        rollback_world()
                    if persisted:
                        _persist_world_body(predecessor_world)
                else:
                    authority.discard_prepared_action(prepared)
                return _refusal(
                    503,
                    "her movement could not persist: "
                    f"{type(error).__name__}: {error}",
                )

            _last_displacement = moved
            try:
                after_body = next(
                    body
                    for body in execution.after.bodies
                    if body.body_id == execution.after.self_body_id
                )
                actual_dx = after_body.pose.position.x - before_body.pose.position.x
                actual_dy = after_body.pose.position.y - before_body.pose.position.y
                root_translation_source = (
                    exact_native_root_translation_proprioceptive_source(
                        source_tick=root_yaw_source_tick,
                        signed_x_millimetres=actual_dx,
                        signed_y_millimetres=actual_dy,
                    )
                    if actual_dx or actual_dy
                    else None
                )
                admitted_episodes = [(consequence, admissions)]
                if signed_yaw:
                    root_yaw_source = (
                        exact_native_root_yaw_proprioceptive_source(
                            source_tick=root_yaw_source_tick,
                            signed_displacement_millidegrees=signed_yaw,
                        )
                    )
                    admitted_episodes.append(
                        (
                            root_yaw_source,
                            [(1, 1_000)] * root_yaw_source.occurrence_count,
                        )
                    )
                if root_translation_source is not None:
                    admitted_episodes.append(
                        (
                            root_translation_source,
                            [(1, 1_000)]
                            * root_translation_source.occurrence_count,
                        )
                    )
                result = _perform_admitted_intake_locked(
                    admitted_episodes,
                    f"world-move:{intent}",
                    vestibular_yaw=(predecessor_heading, yaw_trajectory),
                )
            except HTTPException:
                raise
            except (RuntimeError, TypeError, ValueError) as error:
                _refresh_public_observation_cache()
                return JSONResponse(
                    status_code=503,
                    content={
                        "accepted": True,
                        "chose_to_go": False,
                        "ok": False,
                        "reason": (
                            "her body moved and persisted, but its exact sensory "
                            "transition was refused; do not repeat the action "
                            f"({type(error).__name__}: {error})"
                        ),
                        "revision": execution.after.revision,
                        "schema": "guala.native_world_move.v2",
                        "sensory_delivery": {"accepted": False},
                    },
                )
            _refresh_public_observation_cache()
            return JSONResponse(
                status_code=200,
                content={
                    "accepted": True,
                    "chose_to_go": False,
                    "moved": {
                        channel: float(value)
                        for channel, value in zip(
                            DISPLACEMENT_CHANNELS,
                            moved,
                            strict=True,
                        )
                    },
                    "ok": True,
                    "revision": execution.after.revision,
                    "schema": "guala.native_world_move.v2",
                    "signed_yaw_millidegrees": signed_yaw,
                    "world_action_duration_microseconds": (
                        WORLD_BODY_ACTION_MILLISECONDS * 1_000
                    ),
                    "sensory_delivery": {
                        "accepted": True,
                        "hop_count": result["hop_count"],
                        "organism_tick": result["persisted"]["organism_tick"],
                        "state_sha256": result["persisted"]["state_sha256"],
                    },
                    "receptor_ingress": result.get("receptor_ingress"),
                    "totals": result.get("totals"),
                },
            )
    finally:
        _end_external_intake()


@app.post(WORLD_FEED_PRESENTATION_ENDPOINT)
def world_feed_presentation(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Hold one real world object in her hands, or guide it to her mouth.

    A person feeds her, exactly as a person presents a card or moves her:
    authored presentation, never a claim that she chose to eat. Phase
    "hold" closes her hands around the named object (the world's own
    custody law); phase "mouth" brings the held object to her oral
    receptor surface, where the world's declared tastant chemistry — not
    this endpoint — decides what she tastes. Everything that follows
    (taste onset, any born reflex it prepares) happens inside her own
    physics or not at all.
    """

    if not WORLD_AUTHORIZED:
        return _refusal(
            503,
            "no world is mounted: there is nothing real to feed her, and a "
            f"tastant with no object behind it would be a fabrication ({WORLD_ENV})",
        )
    if not CHEMORECEPTION_AUTHORIZED:
        return _refusal(
            503,
            "her gustatory receptors are not mounted, so food at her mouth "
            "would reach nothing she can taste",
        )
    if not isinstance(payload, dict):
        return _refusal(422, "a feed presentation requires a JSON body")
    phase = payload.get("phase")
    if phase not in ("settle", "hold", "mouth"):
        return _refusal(
            422, "a feed presentation phase must be 'settle', 'hold' or 'mouth'"
        )
    object_id = payload.get("object_id")
    if not isinstance(object_id, str) or not object_id:
        return _refusal(422, "a feed presentation requires a nonempty object_id")
    settle_x = settle_y = None
    if phase == "settle":
        try:
            settle_x = int(payload["x_mm"])
            settle_y = int(payload["y_mm"])
        except (KeyError, TypeError, ValueError):
            return _refusal(
                422,
                "settling a held thing requires integer x_mm and y_mm to set "
                "it down at",
            )
    from dsf_ai_service.substrate.embodiment_world import (
        ActionExecutionReceipt,
        OralContactCommand,
        PORT_ID,
        PickCommand,
        PlaceCommand,
        PositionMM,
        PreparedActionExecution,
        encode_command,
    )

    _begin_external_intake()
    try:
        with _transition_lock:
            try:
                authority = _world()
                before = authority.observation_snapshot()
                intent = _receipt({
                    "actor_body_id": before.self_body_id,
                    "expected_world_revision": before.revision,
                    "object_id": object_id,
                    "operation": f"feed-{phase}",
                })
                if phase == "settle":
                    command = PlaceCommand(
                        object_id=object_id,
                        target_position=PositionMM(settle_x, settle_y, 0),
                        duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
                    )
                elif phase == "hold":
                    command = PickCommand(
                        object_id=object_id,
                        duration_microseconds=WORLD_BODY_ACTION_MILLISECONDS * 1_000,
                    )
                else:
                    command = OralContactCommand(
                        object_id,
                        WORLD_BODY_ACTION_MILLISECONDS * 1_000,
                    )
                prepared = authority.prepare_port_command(
                    port_id=PORT_ID,
                    command_payload=encode_command(command),
                    causal_intent_receipt_sha256=intent,
                    expected_revision=before.revision,
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                return _refusal(422, f"her place refused that feeding: {error}")

            # HER PLACE HAS ITS OWN PHYSICS AND IT SAYS NO FOR REAL REASONS:
            # the object out of reach, already held elsewhere, or not hers to
            # mouth without holding it first. A refusal reaches nobody.
            if isinstance(prepared, ActionExecutionReceipt):
                return _refusal(
                    409,
                    f"her place refused that feeding: {prepared.reason}. "
                    "Nothing reached her, because nothing happened to her body",
                )
            if not isinstance(prepared, PreparedActionExecution):
                return _refusal(503, "her place lost its prepared feeding")
            execution = prepared.execution_receipt
            try:
                moved = _world_displacement(execution.before, execution.after)
                consequence, admissions, _lane_truth = (
                    _action_consequence_episode(
                        execution,
                        action_duration=Fraction(
                            WORLD_BODY_ACTION_MILLISECONDS,
                            1_000,
                        ),
                        body_displacement=moved,
                    )
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                authority.discard_prepared_action(prepared)
                return _refusal(422, f"that feeding could not reach her: {error}")

            predecessor_world = authority.encoded_snapshot()
            committed = False
            persisted = False
            try:
                with authority.prepared_action_visibility_transaction(prepared):
                    execution = authority.commit_prepared_action(prepared)
                    committed = True
                    successor_world = authority.encoded_committed_prepared_action(
                        prepared
                    )
                    _persist_world_body(successor_world)
                    persisted = True
            except BaseException as error:
                if committed:
                    with authority.committed_prepared_action_rollback_transaction(
                        prepared
                    ) as rollback_world:
                        rollback_world()
                    if persisted:
                        _persist_world_body(predecessor_world)
                else:
                    authority.discard_prepared_action(prepared)
                return _refusal(
                    503,
                    "her feeding could not persist: "
                    f"{type(error).__name__}: {error}",
                )

            # THE BRIDGE ARITHMETIC (R1 eating): the world's own before and
            # after object records say how much tastant mass this exact
            # mouth contact really removed; her declared extraction density
            # turns that matter into energy in her body's own unit. Zero
            # transfer is the plain sensory hop — no feed lane, no intake.
            real_intake_zeptojoules: int | None = None
            if phase == "mouth":
                from dsf_ai_service.substrate.embodiment_world import (
                    NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM,
                )

                def _tastant_total(snapshot: Any) -> int:
                    for candidate in snapshot.objects:
                        if candidate.object_id == object_id:
                            material = candidate.material
                            if material is None:
                                return 0
                            return sum(material.tastant_mass_micrograms)
                    return 0

                transferred_micrograms = _tastant_total(
                    execution.before
                ) - _tastant_total(execution.after)
                if transferred_micrograms < 0:
                    return _refusal(
                        503,
                        "the bite created tastant mass from nothing; the "
                        "world's conservation is broken and nothing was fed",
                    )
                if transferred_micrograms > 0:
                    real_intake_zeptojoules = (
                        transferred_micrograms
                        * NUTRITION_EXTRACTION_DENSITY_ZEPTOJOULES_PER_MICROGRAM
                    )

            try:
                result = _perform_admitted_intake_locked(
                    [(consequence, admissions)],
                    f"world-feed-{phase}:{intent}",
                    real_nutrition_intake_zeptojoules=real_intake_zeptojoules,
                )
            except HTTPException:
                raise
            except (RuntimeError, TypeError, ValueError) as error:
                _refresh_public_observation_cache()
                return JSONResponse(
                    status_code=503,
                    content={
                        "accepted": True,
                        "chose_to_eat": False,
                        "ok": False,
                        "phase": phase,
                        "reason": (
                            "the feeding happened and persisted, but its exact "
                            "sensory transition was refused; do not repeat the "
                            f"action ({type(error).__name__}: {error})"
                        ),
                        "revision": execution.after.revision,
                        "schema": "guala.native_feed_presentation.v1",
                        "sensory_delivery": {"accepted": False},
                    },
                )
            _refresh_public_observation_cache()
            return JSONResponse(
                status_code=200,
                content={
                    "accepted": True,
                    "chose_to_eat": False,
                    "object_id": object_id,
                    "ok": True,
                    "phase": phase,
                    # The world's own measured transfer for this exact
                    # contact: matter that left the object, and the energy
                    # it carried at her declared extraction density. Zero
                    # when nothing was bitten.
                    "real_transfer": {
                        "tastant_micrograms": (
                            0
                            if phase != "mouth"
                            else transferred_micrograms
                        ),
                        "intake_zeptojoules": real_intake_zeptojoules or 0,
                    },
                    "revision": execution.after.revision,
                    "schema": "guala.native_feed_presentation.v1",
                    "sensory_delivery": {
                        "accepted": True,
                        "hop_count": result["hop_count"],
                        "organism_tick": result["persisted"]["organism_tick"],
                        "state_sha256": result["persisted"]["state_sha256"],
                    },
                    "receptor_ingress": result.get("receptor_ingress"),
                    "totals": result.get("totals"),
                },
            )
    finally:
        _end_external_intake()


@app.post(
    GUTENBERG_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def gutenberg_material(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Present a guide-named text or one source selected by Guala's grip."""

    global _curriculum_invitation
    if not isinstance(payload, dict) or payload.get("schema") != SHELF_SELECTION_SCHEMA:
        return _refusal(422, f"shelf selection requires schema {SHELF_SELECTION_SCHEMA}")
    mode = payload.get("mode")
    if mode not in ("guided", "autonomous"):
        return _refusal(422, "shelf selection mode must be 'guided' or 'autonomous'")
    if mode == "autonomous":
        return _refusal(
            409,
            "the autonomous Gutenberg endpoint is retired: a server request "
            "cannot select or present a book. The persistent-world book can "
            "advance only when Guala's own native grip opens the uniquely "
            "contacted source-bound surface",
        )
    expected_fields = {
        "attribution",
        "edition",
        "gutenberg_id",
        "language_tag",
        "mode",
        "rights_basis",
        "rights_statement",
        "schema",
        "source_url",
    }
    if set(payload) != expected_fields:
        return _refusal(
            422,
            "a guided Gutenberg presentation requires one exact approved "
            "catalogue entry with edition, language, attribution, public-domain "
            "basis, source URL, and rights statement",
        )
    book_id = payload.get("gutenberg_id")
    catalogue_entry = next(
        (
            entry
            for entry in GUTENBERG_CATALOGUE
            if entry["gutenberg_id"] == book_id
        ),
        None,
    )
    if catalogue_entry is None or any(
        payload.get(field) != catalogue_entry[field]
        for field in expected_fields - {"schema", "mode"}
    ):
        return _refusal(
            422,
            "the named Gutenberg source does not exactly match one approved "
            "catalogue entry",
        )
    try:
        source_record = acquire_project_gutenberg_source(
            _source_media_store,
            source_url=catalogue_entry["source_url"],
            language_tag=catalogue_entry["language_tag"],
        )
        preserved_raw = _source_media_store.source_bytes(
            source_record.receipt_sha256
        )
        text = preserved_raw.decode("utf-8")
        pages = _gutenberg_pages(text)
        home_book_sequence = _home_book_sequence_from_pages(
            source_record,
            pages,
        )
        if home_book_sequence is not None and WORLD_AUTHORIZED:
            _world().mount_contact_optical_surface_sequence(
                home_book_sequence
            )
        rosters = _guided_gutenberg_rosters(pages)
        episodes = _offered_visual_episodes(f"gutenberg-{book_id}-{uuid.uuid4()}", rosters)
    except (
        BoundedSourceMediaStoreError,
        OSError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        return _refusal(422, f"gutenberg presentation refused: {error}")
    invitation_response = _embodied_curriculum_invitation(
        experience_kind="gutenberg",
        experience_id=source_record.receipt_sha256,
        media_receipts={
            "source_bytes_sha256": source_record.source_bytes_sha256,
            "source_media_receipt_sha256": source_record.receipt_sha256,
        },
    )
    if invitation_response.status_code != 200:
        return invitation_response
    invitation_body = json.loads(invitation_response.body)
    invitation = invitation_body.get("invitation")
    invitation_receipt = (
        invitation.get("invitation_receipt_sha256")
        if isinstance(invitation, dict)
        else None
    )
    try:
        with _transition_lock:
            prepared = _validated_curriculum_experience_invitation(
                "gutenberg",
                source_record.receipt_sha256,
                invitation_receipt,
            )
            _curriculum_invitation = {
                **prepared,
                "outcome": "presentation_attempted",
                "presentation_eligible": False,
                "reason": (
                    "one preserved Project Gutenberg source is entering its "
                    "physical page-light path"
                ),
                "status": "gutenberg_presentation_in_progress",
            }
            result = _perform_admitted_intake_locked(
                episodes,
                f"gutenberg:{book_id}",
            )
            settled_tick = result["observation"].get("organism_tick")
            if (
                isinstance(settled_tick, bool)
                or not isinstance(settled_tick, int)
                or settled_tick <= 0
            ):
                raise RuntimeError(
                    "admitted Gutenberg transition lost its settled organism tick"
                )
            _curriculum_invitation = {
                **_curriculum_invitation,
                "outcome": "presented",
                "presented_organism_tick": settled_tick,
                "presentation_eligible": False,
                "reason": (
                    "the preserved Project Gutenberg source settled once "
                    "through physical retinal receptors; CURRENT durability "
                    "is reported separately"
                ),
                "status": "gutenberg_presentation_settled",
            }
            _refresh_public_observation_cache()
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted visual transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            "shelf": "gutenberg",
            "mode": "guided",
            "gutenberg_id": book_id,
            "presented_page_count": len(rosters),
            "mounted_source_page_count": len(pages),
            "source_media": source_record.public_projection(),
            "transport_metadata_only": True,
            "meaning_entered": False,
            **_public_admitted_intake_result(result),
        },
    )


@app.get(SOURCE_MEDIA_CUSTODY_ENDPOINT)
def source_media_custody() -> JSONResponse:
    """Bounded on-demand provenance inventory; never polled by cognition."""

    try:
        records = _source_media_store.inventory(verify_source_bytes=False)
    except BoundedSourceMediaStoreError as error:
        return _refusal(503, f"source-media custody refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            "cognition_authority": False,
            "max_source_bytes": _source_media_store.max_source_bytes,
            "max_source_count": _source_media_store.max_source_count,
            "max_total_bytes": _source_media_store.max_total_bytes,
            "record_count": len(records),
            "records": [
                {
                    "material_kind": record.material_kind,
                    "receipt_sha256": record.receipt_sha256,
                    "source_byte_count": record.source_byte_count,
                    "source_bytes_sha256": record.source_bytes_sha256,
                }
                for record in records
            ],
            "schema": "guala.bounded_source_media_inventory.v1",
            "semantic_authority": False,
            "total_source_bytes": sum(
                record.source_byte_count for record in records
            ),
        },
    )


@app.get(SOURCE_MEDIA_CUSTODY_ENDPOINT + "/{receipt_sha256}")
def source_media_custody_record(receipt_sha256: str) -> JSONResponse:
    """Explicitly rehash one retained source and return only its receipt."""

    if not re.fullmatch(r"[0-9a-f]{64}", receipt_sha256):
        return _refusal(422, "source-media receipt changed")
    try:
        records = _source_media_store.inventory(verify_source_bytes=False)
        record = next(
            item for item in records if item.receipt_sha256 == receipt_sha256
        )
        source = _source_media_store.source_bytes(receipt_sha256)
    except StopIteration:
        return _refusal(404, "source-media receipt is absent")
    except (BoundedSourceMediaStoreError, OSError, ValueError) as error:
        return _refusal(503, f"source-media verification refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            **record.public_projection(),
            "restored_source_bytes_sha256": hashlib.sha256(source).hexdigest(),
            "source_bytes_restored_and_verified": True,
        },
    )


@app.post(
    OFFERED_MATERIAL_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def offered_material(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Preserve, invite, then physically present one bounded local source."""

    global _curriculum_invitation, _live_hearing_evidence

    if not isinstance(payload, dict) or payload.get("schema") != OFFERED_MATERIAL_SCHEMA:
        return _refusal(422, f"offered material requires schema {OFFERED_MATERIAL_SCHEMA}")
    expected_fields = {
        "attribution",
        "bytes_b64",
        "material_kind",
        "media_type",
        "origin_locator",
        "rights_basis",
        "rights_statement",
        "schema",
    }
    if set(payload) != expected_fields:
        return _refusal(
            422,
            "offered material requires exact source bytes and immutable local "
            "provenance; no title, transcript, label, or meaning field is admitted",
        )
    kind = payload.get("material_kind")
    if kind not in LOCAL_MATERIAL_KINDS:
        return _refusal(
            422,
            "offered material_kind must be one of "
            + ", ".join(LOCAL_MATERIAL_KINDS),
        )
    if (
        kind in AUDIBLE_MATERIAL_KINDS + VIDEO_MATERIAL_KINDS
        and not COCHLEAR_EARS_AUTHORIZED
    ):
        return _refusal(503, _SOUND_SUSPENSION_REASON)
    try:
        raw = _decode_material_body(payload, "bytes_b64")
        media_type = _validate_offered_media_type(kind, payload.get("media_type"))
        source_record = _source_media_store.admit(
            attribution=payload.get("attribution"),
            material_kind=kind,
            media_type=media_type,
            origin_kind="local_offer",
            origin_locator=payload.get("origin_locator"),
            rights_basis=payload.get("rights_basis"),
            rights_statement=payload.get("rights_statement"),
            source_bytes=raw,
        )
        # Decode only the exact bytes just committed to bounded custody.  The
        # source record is outside cognition; no provenance field is copied
        # into a receptor occurrence.
        preserved_raw = _source_media_store.source_bytes(
            source_record.receipt_sha256
        )
        if kind in VISUAL_MATERIAL_KINDS:
            rosters = _decode_offered_rasters(kind, preserved_raw, media_type)
            episodes = _offered_visual_episodes(f"offered-{kind}-{uuid.uuid4()}", rosters)
            presented = {"presented_raster_count": len(rosters)}
        elif kind in AUDIBLE_MATERIAL_KINDS:
            sample_rate, samples = _decode_offered_audio(preserved_raw)
            episodes = _mono_pcm_hop_episodes(
                assembly_prefix=f"offered-{kind}-{uuid.uuid4()}",
                samples=samples,
                sample_rate_hz=sample_rate,
            )
            presented = {"presented_sample_count": len(samples)}
        else:
            video = decode_bounded_video(preserved_raw)
            rosters = [
                _live_frame_luminance(frame) for frame in video.frame_png_bytes
            ]
            samples = struct.unpack(
                f"<{len(video.pcm_s16le) // 2}h",
                video.pcm_s16le,
            )
            episodes = _live_audiovisual_hop_episodes(
                f"offered-video-{uuid.uuid4()}",
                rosters,
                samples,
                video.sample_rate_hz,
            )
            presented = {
                "presented_raster_count": len(rosters),
                "presented_sample_count": len(samples),
                "sensory_projection": video.public_projection(),
            }
    except (BoundedSourceMediaStoreError, OSError, TypeError, ValueError) as error:
        return _refusal(422, f"offered {kind} refused: {error}")
    invitation_response = _embodied_curriculum_invitation(
        experience_kind="material",
        experience_id=source_record.receipt_sha256,
        media_receipts={
            "source_bytes_sha256": source_record.source_bytes_sha256,
            "source_media_receipt_sha256": source_record.receipt_sha256,
        },
    )
    if invitation_response.status_code != 200:
        return invitation_response
    invitation_body = json.loads(invitation_response.body)
    invitation = invitation_body.get("invitation")
    invitation_receipt = (
        invitation.get("invitation_receipt_sha256")
        if isinstance(invitation, dict)
        else None
    )
    try:
        with _transition_lock:
            prepared = _validated_curriculum_experience_invitation(
                "material",
                source_record.receipt_sha256,
                invitation_receipt,
            )
            _curriculum_invitation = {
                **prepared,
                "outcome": "presentation_attempted",
                "presentation_eligible": False,
                "reason": "one preserved local source is entering its physical sensory paths",
                "status": "local_material_presentation_in_progress",
            }
            result = _perform_admitted_intake_locked(
                episodes,
                f"offered-{kind}",
            )
            settled_tick = result["observation"].get("organism_tick")
            if (
                isinstance(settled_tick, bool)
                or not isinstance(settled_tick, int)
                or settled_tick <= 0
            ):
                raise RuntimeError(
                    "admitted material transition lost its settled organism tick"
                )
            _curriculum_invitation = {
                **_curriculum_invitation,
                "outcome": "presented",
                "presented_organism_tick": settled_tick,
                "presentation_eligible": False,
                "reason": (
                    "the preserved source settled once through physical "
                    "receptors; CURRENT durability is reported separately"
                ),
                "status": "local_material_presentation_settled",
            }
            if kind in AUDIBLE_MATERIAL_KINDS + VIDEO_MATERIAL_KINDS:
                _live_hearing_evidence = {
                    "intake": f"offered-{kind}",
                    "generation": result.get("generation"),
                }
            _refresh_public_observation_cache()
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted material transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={
            "material_kind": kind,
            "source_media": source_record.public_projection(),
            "transport_metadata_only": True,
            **presented,
            **_public_admitted_intake_result(result),
        },
    )


@app.post(
    SPOKEN_LESSON_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def teach_card_spoken(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Teach one card in a living person's own voice.

    The card is shown, felt and NAMED BY THE PERSON PRESENT, on one shared
    clock, as a single admitted episode.  Everything except the source of
    the pressure samples is identical to the tutor-recorded lesson.
    """

    refusal = _spoken_voice_refusal()
    if refusal is not None:
        return refusal
    if not isinstance(payload, dict):
        return _refusal(422, "spoken lesson requires a JSON body")
    card_id = payload.get("card_id")
    if not isinstance(card_id, str) or not card_id:
        return _refusal(422, "spoken lesson requires an approved card_id")
    sample_rate = payload.get("sample_rate_hz")
    if sample_rate != COCHLEAR_SAMPLE_RATE_HZ:
        return _refusal(
            422,
            "spoken lesson requires pcm_s16le mono at "
            f"{COCHLEAR_SAMPLE_RATE_HZ} Hz, exactly the format the cochlear "
            "band decomposition is declared for",
        )
    encoded = payload.get("pcm_s16le_base64")
    if not isinstance(encoded, str) or not encoded:
        return _refusal(422, "spoken lesson requires pcm_s16le_base64")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return _refusal(422, "spoken lesson voice is not canonical base64")
    if len(raw) % 2 != 0 or len(raw) < 4:
        return _refusal(
            422, "spoken lesson voice is not at least two whole pcm_s16le samples"
        )
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    try:
        experience = _read_manifest_card(card_id)
    except KeyError:
        return _refusal(
            404, f"card {card_id!r} is not in the approved curriculum manifest"
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return _refusal(503, f"curriculum manifest is unavailable: {error}")
    invitation_receipt = payload.get("invitation_receipt_sha256")
    try:
        with _transition_lock:
            _validated_curriculum_invitation(card_id, invitation_receipt)
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    try:
        episodes = _card_lesson_hop_episodes(
            card_id,
            experience,
            "full",
            spoken_voice=(sample_rate, samples),
        )
    except HTTPException:
        raise
    except (OSError, ValueError) as error:
        return _refusal(422, f"spoken lesson refused: {error}")
    try:
        result = _perform_card_lesson_intake(
            episodes,
            f"spoken-card:{card_id}",
            card_id,
            experience,
            "full",
            invitation_receipt,
        )
    except _CurriculumInvitationRefusal as error:
        return _refusal(error.status_code, str(error))
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted lesson transition refused: {error}")
    # Publish the evidence the way the live-sight route does: under the
    # lock, WITH a cache refresh.  The public observation is served from a
    # cache that is rebuilt during an intake, so an evidence global assigned
    # after the intake would not appear until the NEXT one — a control would
    # read "nothing has happened" immediately after it happened.
    global _live_hearing_evidence
    with _transition_lock:
        _live_hearing_evidence = {
            "intake": f"spoken-card:{card_id}",
            "generation": result.get("generation"),
        }
        _refresh_public_observation_cache()
    return JSONResponse(
        status_code=200,
        content={
            "card_id": card_id,
            "presentation": "full",
            "voice": "live_human_speaker",
            "spoken_sample_count": len(samples),
            **_public_admitted_intake_result(result),
        },
    )


@app.post(
    GUIDED_WORLD_VOICE_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def guided_world_voice(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Let a tutor speak while Guala experiences her actual current world.

    The request deliberately has no semantic field. It cannot tell cognition
    what the pressure means or which thing to learn. External-intake admission
    yields unattended time before this function takes the resident transition
    lock, so this one request binds the exact then-current organism internally.
    """

    global _live_hearing_evidence

    refusal = _spoken_voice_refusal()
    if refusal is not None:
        return refusal
    expected_fields = {
        "schema",
        "pcm_s16le_base64",
        "sample_rate_hz",
    }
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        return _refusal(
            422,
            "grounded world voice accepts only schema, sample rate, and "
            "physical PCM pressure",
        )
    if payload.get("schema") != GUIDED_WORLD_VOICE_SCHEMA:
        return _refusal(422, f"grounded world voice requires {GUIDED_WORLD_VOICE_SCHEMA}")
    sample_rate = payload.get("sample_rate_hz")
    if sample_rate != COCHLEAR_SAMPLE_RATE_HZ:
        return _refusal(
            422,
            "grounded world voice requires pcm_s16le mono at "
            f"{COCHLEAR_SAMPLE_RATE_HZ} Hz",
        )
    encoded = payload.get("pcm_s16le_base64")
    if not isinstance(encoded, str) or not encoded:
        return _refusal(422, "grounded world voice requires pcm_s16le_base64")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return _refusal(422, "grounded world voice is not canonical base64")
    if len(raw) % 2 or len(raw) < 4:
        return _refusal(422, "grounded world voice requires whole signed-16 samples")
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    if Fraction(len(samples), sample_rate) > AMBIENT_INTAKE_MAX_SECONDS:
        return _refusal(422, "grounded world voice exceeds the declared intake window")

    try:
        with _transition_lock:
            episodes, world_sensorium = _guided_world_voice_episodes(
                samples,
                sample_rate,
            )
            audio_sha256 = hashlib.sha256(raw).hexdigest()
            result = _perform_admitted_intake_locked(
                episodes,
                f"guided-world-voice:{audio_sha256}",
            )
            _live_hearing_evidence = {
                "intake": f"guided-world-voice:{audio_sha256}",
                "generation": result.get("generation"),
            }
            _refresh_public_observation_cache()
    except HTTPException:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"grounded world voice transition refused: {error}")

    observation = result.get("observation")
    if not isinstance(observation, dict):
        observation = {}
    transition = {
        key: observation[key]
        for key in (
            "predecessor_organism_tick",
            "organism_tick",
            "predecessor_state_sha256",
            "state_sha256",
            "causal_transition_sha256",
            "energy_exhausted",
        )
        if key in observation
    }
    causal_use = {
        key: observation[key]
        for key in (
            "causal_cross_context_use",
            "externally_reassembled_formation_causal_use",
            "new_impression_causal_use",
            "articulatory_causal_cross_context_use",
            "externally_reassembled_articulation_causal_use",
        )
        if isinstance(observation.get(key), dict)
    }
    for key in (
        "externally_reassembled_formation_causal_uses",
    ):
        value = observation.get(key)
        if isinstance(value, (list, tuple)) and value:
            causal_use[key] = value
    articulation = observation.get("articulation")
    if isinstance(articulation, dict):
        articulation = {
            key: articulation[key]
            for key in (
                "layer_13_recruitment_count",
                "sample_rate_hz",
                "pressure_sample_count",
                "pressure_sha256",
                "applied_motor_quanta",
                "stalled_motor_quanta",
                "articulatory_body_port_count",
                "articulatory_body_nonquiescent_port_count",
                "articulatory_body_receptor_ingress_count",
                "articulatory_body_perturbed_neuron_count",
                "self_hearing_hop_count",
                "self_hearing_transitioned_neuron_count",
                "self_hearing_fractal_count",
                "retained_formation_causal_path",
                "externally_reassembled_formation_causal_path",
            )
            if key in articulation
        }
    else:
        articulation = None

    return JSONResponse(
        status_code=200,
        content={
            "accepted": True,
            "audio_sha256": audio_sha256,
            "articulation": articulation,
            "causal_use": causal_use,
            "hop_count": result.get("hop_count"),
            "persisted": result.get("persisted"),
            "receptor_ingress": result.get("receptor_ingress"),
            "schema": GUIDED_WORLD_VOICE_SCHEMA,
            "totals": result.get("totals"),
            "transition": transition,
            "transport_metadata_only": True,
            "world_sensorium": world_sensorium,
        },
    )


@app.post(
    "/api/v1/development/retinal-lattice",
    dependencies=[Depends(_require_secret)],
)
def development_retinal_lattice() -> JSONResponse:
    """Author the declared within-column retinal contacts onto the body.

    Growth of a living body is a deliberate authorized act: this endpoint
    refuses honestly unless the environment explicitly authorizes it, and it
    is never reached by a deploy on its own.
    """

    if not _retinal_lattice_authorized():
        return _refusal(
            403,
            "authored contact growth is refused: growing a living body is a "
            "deliberate authorized act and "
            f"{RETINAL_LATTICE_AUTHORIZATION_ENV} is not set",
        )
    try:
        result = _perform_retinal_lattice_growth()
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"authored contact growth refused: {error}")
    return JSONResponse(status_code=200, content=result)


@app.post(
    LIVE_AUDIOVISUAL_INTAKE_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def live_audiovisual_capture(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Admit one bounded co-captured camera/microphone window."""

    if not COCHLEAR_EARS_AUTHORIZED:
        return _refusal(503, _SOUND_SUSPENSION_REASON)
    try:
        rosters, samples, sample_rate, provenance = (
            _parse_live_audiovisual_capture(payload)
        )
        capture_id = str(uuid.uuid4())
        episodes = _live_audiovisual_hop_episodes(
            capture_id,
            rosters,
            samples,
            sample_rate,
        )
        result = _perform_live_sight_intake(
            episodes,
            f"live-audiovisual:{capture_id}",
            provenance,
            includes_live_hearing=True,
        )
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(
            422,
            f"live audiovisual intake refused: {error}",
        )
    return JSONResponse(
        status_code=200,
        content={"capture": provenance, **_public_admitted_intake_result(result)},
    )


@app.post(
    LIVE_SIGHT_INTAKE_ENDPOINT,
    dependencies=[Depends(_external_intake_admission)],
)
def live_sight_frames(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Deliver one batch of real live camera frames as admitted episodes.

    One posted frame becomes exactly one 250 ms hop on the same timebase and
    the same 27-receptor retinal roster the cards use (Pillow BOX
    area-averaged luminance in [0, 1]).  The ears carry true 0.0 silence —
    a lawful state of the mounted sensorium; audio is never fabricated.
    """

    try:
        rosters, provenance = _parse_live_sight_batch(payload)
    except ValueError as error:
        return _refusal(422, f"live sight intake refused: {error}")
    batch_id = str(uuid.uuid4())
    episodes = _live_sight_hop_episodes(batch_id, rosters)
    try:
        result = _perform_live_sight_intake(
            episodes, f"live-sight:{batch_id}", provenance
        )
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted live sight transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={"capture": provenance, **_public_admitted_intake_result(result)},
    )


@app.post(
    "/sight_frame",
    dependencies=[Depends(_external_intake_admission)],
)
def sight_frame(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    """Legacy mount point; the same live-sight contract and intake path."""

    return live_sight_frames(payload)


@app.post("/sound_frame")
async def sound_frame(request: Request) -> JSONResponse:
    """Retained route name; standalone sound always refuses before reading."""

    del request
    return _standalone_hearing_refusal()


_SOUND_SUSPENSION_REASON = (
    "standalone hearing is refused honestly: the cochlear ear anatomy is not "
    "authorized in this process, so pressure amplitude has no physical effect "
    "on the organism and admitting live sound would fabricate a sensation. "
    "With the cochleae authorized the ears DO transduce — measured on the "
    "real body 2026-08-07 by severing the sound from one identical card "
    "lesson: physically transitioned neurons 529->305, new impressions 41->9 "
    "(the 2026-08-06 'zero physical effect' result was the pre-cochlear "
    "two-port ear and no longer describes this body). Tutor audio inside "
    "card lessons remains either way"
)

_SOUND_WITHOUT_SIGHT_REASON = (
    "standalone hearing is refused under the two-real-signal doctrine "
    "(ratified 2026-08-05: no single-sense experiences): a prior camera "
    "receipt does not prove present sight. Use the bounded audiovisual "
    "intake so real camera frames and microphone pressure occupy the same "
    "native whole-sensorium occurrences"
)


def _standalone_hearing_refusal() -> JSONResponse:
    """Why a standalone live-sound route cannot reach the organism.

    TWO conditions, and the refusal says WHICH one is unmet rather than a
    flat 503 that a reader has to guess at:

      1. The ears must physically transduce.  Without the authorized cochlear
         roster, pressure amplitude has zero measured effect on her body, so
         admitting sound would fabricate a sensation.
      2. The same request must carry co-captured live camera frames.  A prior
         camera receipt is bookkeeping, not current optical energy.  These
         standalone routes therefore stay refused; the combined route binds
         light and pressure into the existing whole-roster native episodes.
    """

    if not COCHLEAR_EARS_AUTHORIZED:
        return _refusal(503, _SOUND_SUSPENSION_REASON)
    return _refusal(503, _SOUND_WITHOUT_SIGHT_REASON)


@app.post("/api/v1/auditory/pcm/open")
def pcm_open(payload: dict[str, Any] | None = Body(default=None)) -> JSONResponse:
    del payload
    return _standalone_hearing_refusal()


@app.post("/api/v1/auditory/pcm/chunk")
def pcm_chunk(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    del payload
    return _standalone_hearing_refusal()


@app.post("/api/v1/auditory/pcm/close")
def pcm_close(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    del payload
    return _standalone_hearing_refusal()


@app.post("/api/v1/auditory/binaural-pcm/open")
def binaural_open() -> JSONResponse:
    return _unavailable("native binaural PCM stream")


@app.post("/api/v1/auditory/binaural-pcm/lineage")
def binaural_lineage() -> JSONResponse:
    return _unavailable("native binaural PCM stream")


@app.post("/api/v1/auditory/binaural-pcm/chunk")
def binaural_chunk() -> JSONResponse:
    return _unavailable("native binaural PCM stream")


@app.post("/api/v1/auditory/binaural-pcm/close")
def binaural_close() -> JSONResponse:
    return _unavailable("native binaural PCM stream")


# The site is two surfaces (Joe, 2026-08-07): gualaloom.html is the one
# interaction surface, loomscan.html the one report.  ledger/pulse/teach/
# camera are retired; their last deployed bytes are archived at
# s3://dsf-ai-site/retired/backup-20260807-1630/ and they are deliberately
# NOT in the release manifest, so they are never published again by accident.
@app.get("/gualaloom.html")
def gualaloom() -> FileResponse:
    return FileResponse(STATIC_ROOT / "gualaloom.html")


@app.get("/loomscan.html")
def loomscan() -> FileResponse:
    return FileResponse(STATIC_ROOT / "loomscan.html")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_ROOT / "gualaloom.html")


if CARD_ROOT.is_dir():
    app.mount("/cards", StaticFiles(directory=CARD_ROOT), name="cards")
if AUDIO_ROOT.is_dir():
    app.mount("/audio", StaticFiles(directory=AUDIO_ROOT), name="audio")


@app.get("/curriculum/card_experience_manifest-v1.json")
def card_experience_manifest() -> FileResponse:
    return FileResponse(CURRICULUM_ROOT / "card_experience_manifest-v1.json")


if CURRICULUM_ROOT.is_dir():
    app.mount(
        "/curriculum",
        StaticFiles(directory=CURRICULUM_ROOT),
        name="external-curriculum",
    )
app.mount("/", StaticFiles(directory=STATIC_ROOT), name="static")
