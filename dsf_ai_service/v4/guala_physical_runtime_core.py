"""Bounded deterministic physical Guala runtime.

No language, Chi, Atlas, corpus, recall, named sensory profile, or scripted
speech authority is defined in this module.
"""

import os

import sys

import json

import time

import contextlib

import copy as _copy_module

import functools

import queue as _queue

import hashlib as _hashlib

import weakref as _weakref

import hmac as _hmac

import threading

import numpy as np

from collections import OrderedDict, defaultdict

from dataclasses import dataclass, field, replace as dataclass_replace

from collections import deque

from dsf_ai_service.substrate.auditory_live_motif import (
    AUDITORY_LIVE_MOTIF_ENVELOPE_MAX_BYTES,
    AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA,
    AUDITORY_W1_BINAURAL_MOTIF_ENVELOPE_MAX_BYTES,
)

from dsf_ai_service.substrate.auditory_temporal_relation_assembly import (
    AUDITORY_TEMPORAL_RELATION_STATE_MAX_BYTES,
    TEMPORAL_ENVELOPE_SCHEMA,
)

from dsf_ai_service.substrate.full_field_prediction import (
    FULL_FIELD_PREDICTION_CONSUMER_ID,
)

from dsf_ai_service.substrate.engine_persistence_profile import (
    ENGINE_DIARY_EVENT_BYTES as OBSERVATIONAL_RECEIPT_MAX_BYTES,
    LEGACY_ENGINE_SNAPSHOT_RETAINED,
    OBSERVATIONAL_ERROR_TYPE_MAX_BYTES,
    OBSERVATIONAL_EVENT_KIND_MAX_BYTES,
    OBSERVATIONAL_FAILURE_KIND_MAX_BYTES,
    UINT64_MAX as ENGINE_STORAGE_UINT64_MAX,
)

from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceConsumerView,
    SettledExperienceCustody,
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)

from dsf_ai_service.substrate.window_manager import (
    WindowManager,
    physical_topology_fact,
)

AUTONOMOUS_CAUSAL_PLAY_STATE_MAX_BYTES = 128 * 1024

AUTONOMOUS_EXPERIENCE_DRIVER_STATE_MAX_BYTES = 2 * 1024 * 1024

WHOLE_ORGANISM_INTERNAL_REENTRY_STATE_MAX_BYTES = 4 * 1024 * 1024

ARTICULATORY_CONSEQUENCE_STATE_MAX_BYTES = 64 * 1024 * 1024

CUSTODY_NATIVE_TUTORING_STATE_MAX_BYTES = 128 * 1024 * 1024

CAUSAL_THING_LIVED_CONTEXT_STATE_MAX_BYTES = 64 * 1024 * 1024

ANONYMOUS_PASSIVE_WINDOW_STATE_MAX_BYTES = 16 * 1024 * 1024

CAUSAL_INQUIRY_STATE_MAX_BYTES = 64 * 1024 * 1024

LIVED_VOCAL_TEACHING_STATE_MAX_BYTES = 128 * 1024 * 1024

GROUNDED_ARTICULATORY_VOCAL_TURN_STATE_MAX_BYTES = 64 * 1024 * 1024

PHYSICAL_INTERNAL_BODY_STATE_MAX_BYTES = 16 * 1024 * 1024

WHOLE_ORGANISM_EPISODE_STATE_MAX_BYTES = 64 * 1024 * 1024

WHOLE_ORGANISM_RECOVERY_STATE_MAX_BYTES = 4 * 1024 * 1024

WHOLE_ORGANISM_STRUCTURAL_STATE_MAX_BYTES = 16 * 1024 * 1024

CAUSAL_MOSAIC_TAPESTRY_STATE_MAX_BYTES = 64 * 1024 * 1024

WHOLE_ORGANISM_THING_MOSAIC_LEARNING_STATE_MAX_BYTES = 64 * 1024 * 1024

ORGANISM_DREAM_WAKE_WEAVE_STATE_MAX_BYTES = 16 * 1024 * 1024

WHOLE_ORGANISM_NEURON_POPULATION_STATE_MAX_BYTES = 64 * 1024 * 1024
WHOLE_ORGANISM_NEURON_PROFILE_MIGRATION = (
    "whole_organism_neuron_population_profile_v1_to_v2"
)
NATIVE_MATERIALIZED_FABRIC_V4_MIGRATION = (
    "native_materialized_fabric_v2_or_v3_to_v4"
)
NATIVE_EXACT_ORGANISM_V1_MIGRATION = (
    "legacy_whole_organism_to_native_exact_v1"
)
LIVE_CAMERA_FIXATION_SUBSTREAM_COUNT = 3

# This one-call state materializes the same learned sensory population and
# therefore receives the population owner's existing byte allocation.  The
# boundary prevents runaway storage; it does not decide neuronal identity.
NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES = (
    WHOLE_ORGANISM_NEURON_POPULATION_STATE_MAX_BYTES
)

_NATIVE_WORKING_MEMORY_CGROUP_FILES = (
    (
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory.current",
    ),
    (
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        "/sys/fs/cgroup/memory/memory.usage_in_bytes",
    ),
)


def _native_transition_working_memory_bytes():
    """Return exact currently unoccupied bytes in the finite cgroup."""
    observations = []
    for ceiling_path, current_path in _NATIVE_WORKING_MEMORY_CGROUP_FILES:
        try:
            with open(ceiling_path, "rb") as stream:
                ceiling_raw = stream.read(64).strip()
            with open(current_path, "rb") as stream:
                current_raw = stream.read(64).strip()
        except FileNotFoundError:
            continue
        if ceiling_raw == b"max":
            continue
        try:
            ceiling = int(ceiling_raw)
            current = int(current_raw)
        except ValueError as error:
            raise RuntimeError(
                "native transition cgroup memory observation is invalid"
            ) from error
        if ceiling <= 0 or current < 0 or current >= ceiling:
            raise RuntimeError(
                "native transition cgroup has no finite available memory"
            )
        observations.append(ceiling - current)
    if not observations:
        raise RuntimeError(
            "native transition lacks a finite cgroup memory authority"
        )
    return min(observations)

WHOLE_ORGANISM_NEUROCHEMICAL_STATE_MAX_BYTES = 16 * 1024 * 1024

WHOLE_ORGANISM_REFLECTION_STATE_MAX_BYTES = 16 * 1024 * 1024

CAUSAL_RECOGNITION_ATTENTION_STATE_MAX_BYTES = 16 * 1024 * 1024

EMBODIED_OTHER_PERSPECTIVE_STATE_MAX_BYTES = 8 * 1024 * 1024

DURABLE_SENSED_CONSEQUENCE_STATE_MAX_BYTES = 32 * 1024 * 1024

EMBODIED_GLYPH_CURRICULUM_STATE_MAX_BYTES = 8 * 1024 * 1024

EMBODIED_READING_LESSON_CONTROLLER_STATE_MAX_BYTES = 2 * 1024 * 1024

TEACHING_STATE_MAX_BYTES = (
    AUTONOMOUS_CAUSAL_PLAY_STATE_MAX_BYTES
    + AUDITORY_LIVE_MOTIF_ENVELOPE_MAX_BYTES
    + AUDITORY_TEMPORAL_RELATION_STATE_MAX_BYTES
    + AUDITORY_W1_BINAURAL_MOTIF_ENVELOPE_MAX_BYTES
    + ARTICULATORY_CONSEQUENCE_STATE_MAX_BYTES
    + CUSTODY_NATIVE_TUTORING_STATE_MAX_BYTES
    + CAUSAL_THING_LIVED_CONTEXT_STATE_MAX_BYTES
    + ANONYMOUS_PASSIVE_WINDOW_STATE_MAX_BYTES
    + CAUSAL_INQUIRY_STATE_MAX_BYTES
    + LIVED_VOCAL_TEACHING_STATE_MAX_BYTES
    + GROUNDED_ARTICULATORY_VOCAL_TURN_STATE_MAX_BYTES
    + PHYSICAL_INTERNAL_BODY_STATE_MAX_BYTES
    + WHOLE_ORGANISM_EPISODE_STATE_MAX_BYTES
    + WHOLE_ORGANISM_RECOVERY_STATE_MAX_BYTES
    + WHOLE_ORGANISM_STRUCTURAL_STATE_MAX_BYTES
    + CAUSAL_MOSAIC_TAPESTRY_STATE_MAX_BYTES
    + WHOLE_ORGANISM_THING_MOSAIC_LEARNING_STATE_MAX_BYTES
    + ORGANISM_DREAM_WAKE_WEAVE_STATE_MAX_BYTES
    + WHOLE_ORGANISM_NEURON_POPULATION_STATE_MAX_BYTES
    + NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES
    + WHOLE_ORGANISM_NEUROCHEMICAL_STATE_MAX_BYTES
    + WHOLE_ORGANISM_REFLECTION_STATE_MAX_BYTES
    + AUTONOMOUS_EXPERIENCE_DRIVER_STATE_MAX_BYTES
    + WHOLE_ORGANISM_INTERNAL_REENTRY_STATE_MAX_BYTES
    + CAUSAL_RECOGNITION_ATTENTION_STATE_MAX_BYTES
    + EMBODIED_OTHER_PERSPECTIVE_STATE_MAX_BYTES
    + DURABLE_SENSED_CONSEQUENCE_STATE_MAX_BYTES
    + EMBODIED_GLYPH_CURRICULUM_STATE_MAX_BYTES
    + EMBODIED_READING_LESSON_CONTROLLER_STATE_MAX_BYTES
)

FULL_FIELD_PREDICTION_STATE_MAX_BYTES = 32 * 1024 * 1024


def whole_organism_neuron_anatomy_path_counts():
    """Return every distinct authenticated receptor path mounted today."""

    from dsf_ai_service.glew_runtime.native_sensory_full_field import (
        MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
        MAX_NATIVE_SOUND_SUBSTREAMS,
    )
    from dsf_ai_service.substrate.auditory_kernel_mount import (
        AUDITORY_KERNEL_COMPONENT_COUNT,
    )
    from dsf_ai_service.substrate.embodiment_world import (
        ODORANT_CHANNELS,
        TASTANT_CHANNELS,
    )
    from dsf_ai_service.substrate.visual_region_continuity import (
        RETINA_RECEPTOR_COUNT as LIVE_RETINA_RECEPTOR_COUNT,
    )
    from dsf_ai_service.substrate.w1_coupled_material_sensory_physics import (
        TOUCH_RECEPTOR_COUNT as MATERIAL_TOUCH_RECEPTOR_COUNT,
    )
    from dsf_ai_service.substrate.w1_physical_foveal_observation import (
        MAX_FOVEAL_FIXATIONS_PER_SCAN,
        OPTICAL_BANDS as FOVEAL_OPTICAL_BANDS,
    )
    from dsf_ai_service.substrate.w1_physical_receptors import (
        BODY_RECEPTOR_COUNT,
        RETINA_SUBSTREAM_COUNT,
        TOUCH_RECEPTOR_COUNT as PHYSICAL_TOUCH_RECEPTOR_COUNT,
    )

    foveal_segments = (
        MAX_FOVEAL_FIXATIONS_PER_SCAN
        + MAX_NATIVE_SAMPLES_PER_SUBSTREAM
        - 1
    ) // MAX_NATIVE_SAMPLES_PER_SUBSTREAM
    counts = {
        "browser_camera_retina": LIVE_RETINA_RECEPTOR_COUNT,
        "camera_saccade_fixations": (
            LIVE_CAMERA_FIXATION_SUBSTREAM_COUNT
        ),
        "microphone_cochlear_field": AUDITORY_KERNEL_COMPONENT_COUNT,
        "w1_binaural_cochlear_field": MAX_NATIVE_SOUND_SUBSTREAMS,
        "w1_body_displacement": BODY_RECEPTOR_COUNT,
        "w1_material_smell": ODORANT_CHANNELS,
        "w1_material_taste": TASTANT_CHANNELS,
        "w1_material_touch": MATERIAL_TOUCH_RECEPTOR_COUNT,
        "w1_physical_fovea": FOVEAL_OPTICAL_BANDS * foveal_segments,
        "w1_physical_touch": PHYSICAL_TOUCH_RECEPTOR_COUNT,
        "w1_retina": RETINA_SUBSTREAM_COUNT,
    }
    if (
        any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
            for value in counts.values()
        )
        or MAX_NATIVE_SOUND_SUBSTREAMS
        != 2 * AUDITORY_KERNEL_COMPONENT_COUNT
    ):
        raise RuntimeError(
            "whole-organism mounted receptor anatomy changed"
        )
    return counts


def _whole_organism_neuron_population_profile(*, legacy=False):
    raise RuntimeError(
        "legacy Python neuron-population profile is permanently retired"
    )

    if not isinstance(legacy, bool):
        raise TypeError("neuron population legacy profile flag must be boolean")
    max_neurons = (
        256
        if legacy
        else sum(whole_organism_neuron_anatomy_path_counts().values())
    )
    return NeuronPopulationProfile.create(
        profile_id=(
            "guala-live-whole-organism-neurons-v1"
            if legacy
            else "guala-live-whole-organism-neurons-v2"
        ),
        max_neurons=max_neurons,
        max_edges=(max_neurons * (max_neurons - 1)) // 2,
        max_tuples_per_neuron=1_024,
        max_response_history=16,
        max_state_bytes=(
            WHOLE_ORGANISM_NEURON_POPULATION_STATE_MAX_BYTES
        ),
    )

TEACHING_WITH_PREDICTION_MAX_BYTES = (
    TEACHING_STATE_MAX_BYTES + FULL_FIELD_PREDICTION_STATE_MAX_BYTES
)


def _build_live_whole_organism_episode_authority(
    root_key,
    *,
    available_mechanism_ids=(),
):
    """Mount the current truthful anatomy before any live episode begins."""

    from dsf_ai_service.glew_runtime.model import receipt_sha256
    from dsf_ai_service.glew_runtime.native_sensory_full_field import (
        PROFILE_PAYLOAD,
    )
    from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
        SENSE_ORDER,
    )
    from dsf_ai_service.substrate.native_evidence_custody import (
        NATIVE_EVIDENCE_CUSTODY_AUTHORITY_PAYLOAD,
    )
    raise RuntimeError(
        "legacy Python whole-organism episode graph is permanently retired"
    )

    authority_key = _hmac.new(
        root_key.encode("utf-8"),
        b"guala-live-whole-organism-episode-authority-v1",
        _hashlib.sha256,
    ).digest()
    transduction_receipt = receipt_sha256(PROFILE_PAYLOAD)
    custody_receipt = receipt_sha256(
        NATIVE_EVIDENCE_CUSTODY_AUTHORITY_PAYLOAD
    )
    mechanisms = []
    receptor_ids = []
    for receptor in SENSE_ORDER:
        mechanism_id = f"receptor:{receptor.value}"
        receptor_ids.append(mechanism_id)
        mechanisms.append(MountedMechanismSpec(
            mechanism_id=mechanism_id,
            kind=MechanismKind.RECEPTOR_FAMILY,
            availability=MechanismAvailability.AVAILABLE,
            evidence_schema=(
                "guala.live.whole_organism.receptor."
                f"{receptor.value}.v1"
            ),
            parent_mechanism_ids=(),
            sense=receptor.value,
            binds_full_field_roots=True,
            physical_quantity=(
                "provider-declared-native-physical-quantity"
            ),
            physical_unit="provider-declared-native-physical-unit",
            physical_extent="all-mounted-native-substreams",
            causal_clock="exact-rational-source-time",
            transduction_authority_receipt_sha256=(
                transduction_receipt
            ),
            custody_authority_receipt_sha256=custody_receipt,
        ))

    available_ids = frozenset(available_mechanism_ids)
    unavailable_reason = (
        "lawful_live_contribution_provider_not_yet_mounted"
    )

    def stateful(
        mechanism_id,
        parent_mechanism_ids,
        *,
        binds_full_field_roots=False,
        unavailable_reason_override=None,
    ):
        available = mechanism_id in available_ids
        mechanisms.append(MountedMechanismSpec(
            mechanism_id=mechanism_id,
            kind=MechanismKind.STATEFUL,
            availability=(
                MechanismAvailability.AVAILABLE
                if available
                else MechanismAvailability.UNAVAILABLE
            ),
            evidence_schema=(
                "guala.live.whole_organism."
                + mechanism_id.replace(":", ".")
                + ".v1"
            ),
            parent_mechanism_ids=tuple(sorted(parent_mechanism_ids)),
            binds_full_field_roots=binds_full_field_roots,
            unavailable_reason=(
                None
                if available
                else (
                    unavailable_reason_override
                    if unavailable_reason_override is not None
                    else unavailable_reason
                )
            ),
        ))

    stateful("state:embodiment", receptor_ids)
    stateful("state:internal-physical-chemical", ("state:embodiment",))
    stateful(
        "state:neurochemical-flow",
        ("state:internal-physical-chemical",),
        unavailable_reason_override=(
            "no_ratified_exact_species_quantities_or_kinetics"
        ),
    )
    stateful("state:needs", ("state:internal-physical-chemical",))
    stateful(
        "state:place-world-continuity",
        (*receptor_ids, "state:embodiment"),
        binds_full_field_roots=True,
    )
    stateful("growth:neuron-population", receptor_ids)
    stateful(
        "growth:mosaic",
        (
            "growth:neuron-population",
            "state:internal-physical-chemical",
            "state:place-world-continuity",
        ),
        binds_full_field_roots=True,
    )
    stateful("growth:mosaic-relations", ("growth:mosaic",))
    stateful("growth:tapestry", ("growth:mosaic-relations",))
    stateful("growth:tapestry-relations", ("growth:tapestry",))
    stateful(
        "state:recognition-attention",
        (
            "growth:tapestry-relations",
            "state:internal-physical-chemical",
            "state:neurochemical-flow",
            "state:needs",
        ),
        binds_full_field_roots=True,
    )
    stateful(
        "state:other-perspective-model",
        ("state:embodiment", "state:place-world-continuity"),
    )
    stateful(
        "state:recovery",
        ("state:internal-physical-chemical", "growth:mosaic-relations"),
    )
    stateful(
        "state:deliberation",
        ("state:needs", "growth:tapestry-relations", "state:recovery"),
    )
    stateful("action:embodied", ("state:deliberation",))
    stateful(
        "growth:play",
        ("action:embodied", "growth:mosaic-relations"),
    )
    stateful(
        "state:sensed-consequence",
        ("action:embodied", *receptor_ids),
        binds_full_field_roots=True,
    )
    stateful(
        "growth:dream-internally-simulated",
        (
            "growth:mosaic-relations",
            "growth:tapestry-relations",
            "state:recovery",
        ),
    )
    stateful(
        "growth:wake-test",
        (
            "growth:dream-internally-simulated",
            "state:sensed-consequence",
        ),
        binds_full_field_roots=True,
    )
    stateful(
        "growth:weave",
        ("growth:tapestry-relations", "growth:wake-test"),
    )
    stateful(
        "growth:embodied-glyph-curriculum",
        (
            "growth:mosaic",
            "state:sensed-consequence",
            "receptor:sight",
            "receptor:sound",
        ),
        binds_full_field_roots=True,
    )
    stateful(
        "settlement:l6",
        (
            "growth:weave",
            "state:sensed-consequence",
            "state:recovery",
        ),
        binds_full_field_roots=True,
    )
    topology_payload = json.dumps(
        {
            "mechanisms": [value.record() for value in mechanisms],
            "schema": "guala.live.whole_organism.topology.v1",
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    manifest = create_mounted_mechanism_manifest(
        authority_key=authority_key,
        manifest_id="guala-live-whole-organism-v1",
        topology_authority_receipt_sha256=(
            _hashlib.sha256(topology_payload).hexdigest()
        ),
        mechanisms=mechanisms,
    )
    return WholeOrganismEpisodeAuthority(
        authority_key=authority_key,
        manifest=manifest,
        max_episodes=64,
        max_state_bytes=WHOLE_ORGANISM_EPISODE_STATE_MAX_BYTES,
    )


def _build_live_physical_internal_body_authority(
    root_key,
    world,
    *,
    include_neurochemical_references=False,
):
    """Mount world-owned proprioception without retired owner references."""

    from fractions import Fraction
    from dsf_ai_service.substrate.physical_internal_body_state import (
        create_embodiment_proprioceptive_internal_body_authority,
    )

    if include_neurochemical_references:
        raise RuntimeError(
            "legacy owner-scoped neurochemical references are permanently "
            "retired"
        )

    observation = world.observation_snapshot()
    self_body = next(
        value
        for value in observation.bodies
        if value.body_id == observation.self_body_id
    )
    supported_load = 0
    if self_body.held_object_id is not None:
        supported_load = next(
            value.mass_grams
            for value in observation.objects
            if value.object_id == self_body.held_object_id
        )
    authority_key = _hmac.new(
        root_key.encode("utf-8"),
        b"guala-live-physical-internal-body-authority-v1",
        _hashlib.sha256,
    ).digest()
    return create_embodiment_proprioceptive_internal_body_authority(
        authority_key=authority_key,
        world_observation_receipt_sha256=(
            world.physical_body_mount_observation_receipt()
        ),
        position_x_mm=Fraction(self_body.pose.position.x),
        position_y_mm=Fraction(self_body.pose.position.y),
        position_z_mm=Fraction(self_body.pose.position.z),
        supported_load_grams=Fraction(supported_load),
        neurochemical_references=(),
    )


@dataclass(frozen=True, slots=True, weakref_slot=True)
class _SettledPredictionCustody:
    authority: SettledExperienceCustodyAuthority
    capability: SettledExperienceConsumerCapability
    custody: SettledExperienceCustody
    view: SettledExperienceConsumerView

def _engine_mutation_entry(method):
    """Make one public engine mutation participate in quiescence admission.

    The underlying scope is re-entrant per thread, so public entry points may
    call one another without double-counting or being rejected midway through
    an already-admitted operation.
    """
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        with self._engine_mutation_scope(
            method.__name__,
            advance_causal_tick=(
                method.__name__ != "load_full_state"
            ),
        ):
            return method(self, *args, **kwargs)
    return guarded

def _live_sensory_entry(method):
    """Give one physical sensory mutation uninterrupted causal ownership."""
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        self._enter_live_interaction()
        try:
            return method(self, *args, **kwargs)
        finally:
            self._exit_live_interaction()
    return guarded

class GualaBootStateIntegrityHalt(RuntimeError):
    """NAMED loud halt (P4): the state directory is internally inconsistent
    at boot (identity present with state files vanished, or state files
    present without an identity).  No flag overrides this; recovery is the
    operator's explicit restore command (tools/restore_from_s3.py), run while
    the service is stopped."""

class GualaBootIdentityUnreadableHalt(RuntimeError):
    """The durable identity exists but cannot be authenticated or decoded."""

ACTIVITY_TICK_BUDGETS = {
    "READING": 2000, "PLAYING": 1500, "SLEEPING": 2000, "DREAMING": 3000,
    "ATTENDING": 1000, "ATTENDING_VISUAL": 2000, "ATTENDING_AUDIO": 2000,
    "ATTENDING_VIDEO": 4000, "EMITTING": 100, "IDLE": 500,
    # DAYDREAMING removed GL-CMD-DAYDREAM-PARALLEL-42: now a background thread, not an activity
    # GL-CMD-REST-RETIRE-73: REST removed. _atick_rest kept for persisted-state tail-out only.
}

PLAY_CAUSAL_ADMISSION_SCHEMA = "guala.play.causal_admission.v1"

@dataclass
class Activity:
    kind: str
    target: object  # corpus_id, sensory_item_id, or None
    started_tick: int
    expected_end_tick: int
    metadata: dict = field(default_factory=dict)

    def snapshot(self):
        return {"kind": self.kind, "target": self.target,
                "started_tick": self.started_tick,
                "expected_end_tick": self.expected_end_tick,
                "metadata": dict(self.metadata)}









def _regular_asset_bytes(path):
    if not path or not os.path.exists(path):
        return 0
    if os.path.islink(path):
        raise ValueError("lifetime collection asset cannot be a symlink")
    if os.path.isfile(path):
        return os.path.getsize(path)
    if not os.path.isdir(path):
        raise ValueError("lifetime collection asset is not regular storage")
    total = 0
    for root, directories, files in os.walk(path):
        if any(os.path.islink(os.path.join(root, name))
               for name in [*directories, *files]):
            raise ValueError(
                "lifetime collection asset tree cannot contain symlinks")
        total += sum(
            os.path.getsize(os.path.join(root, name))
            for name in files)
    return total



@dataclass
class SubstrateEvent:
    sequence: int
    tick: int
    kind: str
    detail: dict = field(default_factory=dict)

class Guala:
    """Bounded deterministic physical substrate runtime."""
    SECTION_NAMES = ("listen", "subject", "verb", "object", "modifier", "ground", "intro")

    EPISODIC_MEMORY_MAX_PER_CONCEPT = 20

    EPISODIC_RECENT_CONTEXT_WINDOW = 50

    REFLECTION_MAX_HISTORY = 20

    REFLECTION_MIN_TICKS_BETWEEN = 500

    def __init__(
        self,
        *,
        physical_byte_authority=None,
        engine_persistence_profile_bytes=None,
        observational_receipt_hmac_key=None,
    ):
        if physical_byte_authority is not None:
            from dsf_ai_service.substrate.physical_byte_ceiling import (
                PhysicalByteCeilingAuthority,
            )
            if not isinstance(
                physical_byte_authority,
                PhysicalByteCeilingAuthority,
            ):
                raise TypeError(
                    "Guala physical-byte authority is not typed"
                )
            if (
                isinstance(engine_persistence_profile_bytes, bool)
                or not isinstance(engine_persistence_profile_bytes, int)
                or engine_persistence_profile_bytes <= 0
            ):
                raise ValueError(
                    "Guala engine persistence profile must be positive"
                )
            if (
                not isinstance(observational_receipt_hmac_key, bytes)
                or len(observational_receipt_hmac_key) < 32
            ):
                raise ValueError(
                    "Guala physical persistence requires a 32-byte "
                    "observational receipt HMAC key"
                )
        elif engine_persistence_profile_bytes is not None:
            raise ValueError(
                "Guala persistence profile has no physical-byte authority"
            )
        elif observational_receipt_hmac_key is not None:
            raise ValueError(
                "Guala observational receipt key has no physical-byte "
                "authority"
            )
        self._physical_byte_authority = physical_byte_authority
        self._engine_persistence_profile_bytes = (
            engine_persistence_profile_bytes
        )
        self._observational_receipt_hmac_key = (
            observational_receipt_hmac_key
        )
        self._identity_record = None
        # Caller-bounded physical causal-experience transactions.  These
        # entries are full native fields plus explicit sensor topology; they
        # settle atomically and are released immediately.
        self.window_manager = WindowManager(
            log_event_fn=self._log_substrate_event,
            get_tick_fn=lambda: self.tick,
            settle_window_fn=self._settle_causal_window,
        )
        self.tick = 0
        self.lock = threading.RLock()
        # GL-CMD-CAMERA-TURN-LATENCY: live-interaction priority gate (see
        # _defer_for_live_interaction below). A plain int counter guarded by a
        # dedicated micro-lock -- held only for the ~microsecond of an
        # increment/decrement, never during real work, so it introduces no
        # contention of its own. NOT persisted (save_full_state serializes
        # explicit fields only; this is live-only runtime state), NOT the same
        # lock as self.lock. Reads on the background hot path are lock-free
        # (a single GIL-atomic int load); only the counter writes take the
        # micro-lock.
        self._live_interaction_pending = 0
        self._live_interaction_lock = threading.Lock()
        # Persistence is a separate state domain from cognition.  Every
        # multi-file save, WaveAtlas write, event compaction, and snapshot
        # enters this one reentrant boundary so two generations can never
        # share or steal the same on-disk temporary files.  It must always be
        # acquired before ``self.lock`` when both are needed; save methods
        # retain their existing brief cognition-lock snapshot semantics.
        self._persistence_lock = threading.RLock()
        self._causal_play_condition = threading.Condition()
        self._causal_play_pending = False
        self._causal_play_stop = False
        self._causal_play_thread = None
        self._autonomous_experience_driver = None
        self._whole_organism_internal_reentry_authority = None
        self._latest_autonomous_internal_reentry = None
        self._latest_custody_native_tutoring_action_observation = None

        # Historical DeepAtlas/WaveAtlas/word/chi state has no active
        # cognition authority.  This handle names verified source bytes only;
        # it exposes no decoder or query surface and is copied byte-identically
        # into the authenticated migration archive on each cold generation.
        self._legacy_cognition_escrow_purged = False
        self._legacy_cognition_retirement_proof = None
        # GL-FIX-HOTCOLD-TICK-MANIFEST: the hot lane persists a small subset of
        # the state files every ~60s and advances core's save tick each time,
        # while the cold (full) lane rewrites the big stores (atlas, sections,
        # deep_atlas, survival, organism, tapestry) only every ~30 min or at
        # shutdown. The two lanes therefore leave the state directory with
        # files at DIFFERENT save ticks by design (e.g. core at 3357078,
        # atlas still at 3355078). The loader used to demand every state file
        # share ONE tick -- so any boot whose last save was a hot save was
        # rejected as inconsistent and silently time-travelled to a days-old
        # S3 backup. This map records, per persisted file, the tick it was
        # actually last written at, so the loader can validate each file
        # against its own real tick (proving the set is a legitimate hot/cold
        # mix) instead of against core's tick. Written into guala_core.json's
        # data on every save; read back at load and exposed to the envelope
        # validator via self._expected_file_ticks.
        self._state_file_ticks = {}
        self._expected_file_ticks = None
        self._cold_checkpoint_established = False
        self._owner_freeze_lineage = {}
        # One current event-driven physical activity may be active.
        self._current_activity = None
        self._activity_history = []
        self._substrate_events = deque(maxlen=1000)
        self._substrate_event_epoch = _hashlib.sha256(
            os.urandom(32)
        ).hexdigest()
        self._substrate_event_sequence = 0
        self._substrate_event_lock = threading.Lock()
        self._causal_settlement_accepted = 0
        self._causal_settlement_failed = 0
        self._latest_causal_settlement = None
        self._latest_auditory_l5_experience = None
        from dsf_ai_service.substrate.auditory_l5 import (
            AuditoryL5Owner as _AuditoryL5Owner)
        self._auditory_l5_owner = _AuditoryL5Owner(
            log_event=self._log_substrate_event,
            max_transitions=1024,
        )
        from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
            AuditoryFullFieldStreamRegistry as _AuditoryFullFieldStreamRegistry,
        )
        self._auditory_full_field_streams = _AuditoryFullFieldStreamRegistry()
        from dsf_ai_service.substrate.auditory_pcm_stream import (
            PCM_STREAM_CAPACITY as _AUDITORY_TRANSACTION_CAPACITY,
        )
        self._auditory_transaction_capacity = _AUDITORY_TRANSACTION_CAPACITY
        self._auditory_transaction_lock = threading.RLock()
        from dsf_ai_service.substrate.auditory_full_field_transaction_registry import (
            AuditoryFullFieldTransactionRegistry as
            _AuditoryFullFieldTransactionRegistry,
        )
        self._auditory_full_field_transactions = (
            _AuditoryFullFieldTransactionRegistry(
                max_streams=_AUDITORY_TRANSACTION_CAPACITY,
                max_pending_per_stream=_AUDITORY_TRANSACTION_CAPACITY,
                max_claims=_AUDITORY_TRANSACTION_CAPACITY,
                log_event=self._log_substrate_event,
            )
        )
        self._auditory_terminal_pipeline_lock = threading.RLock()
        self._auditory_terminal_worker_lock = threading.RLock()
        self._auditory_terminal_pipeline_pending = OrderedDict()
        self._auditory_terminal_pipeline_in_flight = None
        self._auditory_terminal_pipeline_capabilities = {}
        self._auditory_terminal_pipeline_receipts = {}
        self._auditory_terminal_pipeline_results = OrderedDict()
        self._auditory_terminal_pipeline_failures = OrderedDict()
        self._auditory_terminal_pipeline_worker_active = False
        self._auditory_terminal_pipeline_thread = None
        self._auditory_terminal_pipeline_worker_error = None
        self._auditory_terminal_pipeline_last_admitted = {}
        self._auditory_terminal_pipeline_last_settled = {}
        self._auditory_terminal_pipeline_admitted_count = 0
        self._auditory_terminal_pipeline_settled_count = 0
        self._auditory_terminal_pipeline_failed_count = 0
        self._auditory_q_process_owner = None
        self._auditory_q_process_status = None
        self._auditory_q_process_committed_state = None
        self._auditory_q_pending_by_stream = {}
        self._auditory_q_process_cached_through = {}
        self._auditory_capture_authorities = OrderedDict()
        self._auditory_l5_by_assembly = OrderedDict()
        self._latest_auditory_continuation_receipt = None
        self._auditory_prediction_transport_in_commit = None
        self._auditory_prediction_pcm_in_commit = None
        self._auditory_transaction_build_in_commit = None
        self._auditory_prediction_joint_by_transport = OrderedDict()
        self._auditory_verified_capability_by_transport = OrderedDict()
        self._latest_auditory_stream_settlement_receipt = None
        from dsf_ai_service.substrate.auditory_live_motif import (
            AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES as
            _AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES,
            AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES as
            _AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES,
        )
        from dsf_ai_service.substrate.auditory_recurrent_motif import (
            AuditoryMotifResourceProfile as
            _AuditoryMotifResourceProfile,
            AuditoryRecurrentMotifOwner as
            _AuditoryRecurrentMotifOwner,
        )
        self._auditory_recurrent_motif_owner = (
            _AuditoryRecurrentMotifOwner(
                _AuditoryMotifResourceProfile.create(
                    profile_id="guala-live-auditory-recurrent-motif-v1",
                    ear_count=1,
                    max_motif_neurons=12_096,
                    max_pending_experiences=1,
                    max_work_cells_per_observation=4_000_000,
                    max_exact_fraction_text_bytes=128,
                    encoded_state_allocation_bytes=(
                        _AUDITORY_LIVE_MONO_MOTIF_STATE_ALLOCATION_BYTES
                    ),
                ),
                log_event=self._log_substrate_event,
            )
        )
        self._auditory_w1_binaural_motif_owner = (
            _AuditoryRecurrentMotifOwner(
                _AuditoryMotifResourceProfile.create(
                    profile_id="guala-w1-binaural-auditory-motif-v1",
                    ear_count=2,
                    max_motif_neurons=24_192,
                    max_pending_experiences=1,
                    max_work_cells_per_observation=8_000_000,
                    max_exact_fraction_text_bytes=128,
                    encoded_state_allocation_bytes=(
                        _AUDITORY_W1_BINAURAL_MOTIF_STATE_ALLOCATION_BYTES
                    ),
                ),
                log_event=self._log_substrate_event,
                ear_ids=("left", "right"),
            )
        )
        self._auditory_recurrent_motif_key = None
        self._auditory_w1_binaural_motif_key = None
        self._auditory_temporal_relation_key = None
        self._auditory_receptor_terminal_by_stream = OrderedDict()
        self._auditory_receptor_bridge_streams = set()
        self._latest_auditory_recurrent_motif = None
        self._latest_auditory_recurrent_motif_experience = None
        self._latest_auditory_recurrent_motif_settlement = None
        from dsf_ai_service.substrate.auditory_incremental_terminal import (
            AuditoryIncrementalTerminalRegistry as
            _AuditoryIncrementalTerminalRegistry,
        )
        self._auditory_incremental_terminals = (
            _AuditoryIncrementalTerminalRegistry(
                reciprocity_owner=None,
                log_event=self._log_substrate_event,
            )
        )
        # One complete, receipt-bound auditory-language witness is retained as
        # current causal memory.  Historical Atlas bindings retain only its
        # identity and receipt; this is deliberately not a lifetime event
        # index and never re-grants live admission authority after restore.
        self._latest_auditory_causal_event_record = None
        self._latest_auditory_full_field_capture = None
        self._latest_auditory_incremental_advance = None
        self._latest_auditory_recognitions = ()
        self._latest_auditory_krimelack_recognition = None
        self._latest_auditory_recognition_boundary = "ambient"
        from dsf_ai_service.substrate.exact_causal_experience import (
            ExactCausalExperienceOwner as _ExactCausalExperienceOwner)
        self._causal_experience_owner = _ExactCausalExperienceOwner(
            on_settlement=self._accept_causal_settlement,
            log_event=self._log_substrate_event,
            max_transitions=1024,
        )
        # The modality-neutral cycle is the authoritative full-field
        # perception-to-action boundary.  The legacy auditory owner remains
        # restore-only during the state transition; it is not allowed to
        # decide identity for this owner.  Production admission requires the
        # same persisted authority key used by the already authenticated
        # auditory action state.  Narrow unit constructions without that key
        # expose an explicit unavailable owner instead of inventing a key.
        from dsf_ai_service.substrate.causal_action_cycle import (
            CausalActionCycle as _CausalActionCycle,
        )
        _causal_cycle_key = (
            os.environ.get("GUALA_CAUSAL_ACTION_KEY")
            or os.environ.get("GUALALOOM_API_KEY")
        )
        self._causal_cycle_key = _causal_cycle_key
        self._whole_organism_episode_authority = None
        self._whole_organism_episode_authority_key = None
        self._whole_organism_l6_authority_key = None
        self._whole_organism_recovery_owner = None
        self._whole_organism_recovery_authority_key = None
        self._whole_organism_structural_owner = None
        self._whole_organism_structural_authority_key = None
        self._causal_mosaic_relation_authority = None
        self._causal_mosaic_tapestry_owner = None
        self._causal_mosaic_tapestry_authority_key = None
        self._whole_organism_thing_learning_owner = None
        self._whole_organism_thing_learning_authority_key = None
        self._organism_dream_wake_weave_owner = None
        self._organism_dream_wake_weave_authority_key = None
        self._whole_organism_neuron_population_owner = None
        self._whole_organism_neuron_population_authority_key = None
        self._native_materialized_fabric_state = None
        self._native_materialized_fabric_reference = None
        self._latest_native_materialized_fabric_transition = None
        self._pending_native_materialized_fabric_transition = None
        self._whole_organism_neurochemical_owner = None
        self._whole_organism_neurochemical_authority_key = None
        self._whole_organism_reflection_owner = None
        self._whole_organism_reflection_authority_key = None
        self._causal_recognition_path_authority = None
        self._whole_organism_attention_context_authority = None
        self._causal_recognition_attention_owner = None
        self._causal_recognition_attention_authority_key = None
        self._other_body_access_authority = None
        self._embodied_other_perspective_owner = None
        self._embodied_other_perspective_authority_key = None
        self._durable_sensed_consequence_owner = None
        self._durable_sensed_consequence_authority_key = None
        self._embodied_glyph_curriculum_owner = None
        self._embodied_glyph_curriculum_authority_key = None
        self._embodied_reading_lesson_controller = None
        self._embodied_reading_material_authority = None
        self._embodied_reading_acoustic_authority = None
        self._latest_whole_organism_episode_resolution = {
            "reason": "whole_organism_authority_key_unavailable",
            "schema": "guala.live.whole_organism.mount_status.v1",
            "state": "unavailable",
        }
        if _causal_cycle_key:
            self._auditory_recurrent_motif_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-auditory-recurrent-motif-state-v1",
                _hashlib.sha256,
            ).digest()
            self._auditory_w1_binaural_motif_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-w1-binaural-auditory-motif-state-v1",
                _hashlib.sha256,
            ).digest()
            self._auditory_temporal_relation_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-auditory-temporal-relation-state-v1",
                _hashlib.sha256,
            ).digest()
        self._causal_action_cycle = (
            _CausalActionCycle(
                log_event=self._log_substrate_event,
                authority_key=_causal_cycle_key,
            )
            if _causal_cycle_key
            else None
        )
        from dsf_ai_service.substrate.embodiment_world import (
            EmbodimentWorldAuthority as _EmbodimentWorldAuthority,
        )
        self._embodiment_world = (
            _EmbodimentWorldAuthority(authority_key=_causal_cycle_key)
            if _causal_cycle_key
            else None
        )
        self._physical_internal_body_state = (
            _build_live_physical_internal_body_authority(
                _causal_cycle_key,
                self._embodiment_world,
            )
            if _causal_cycle_key
            else None
        )
        from dsf_ai_service.substrate.embodiment_sensory_outcome import (
            EmbodimentSensoryOutcomeAuthority as
            _EmbodimentSensoryOutcomeAuthority,
        )
        self._embodiment_sensory_outcome_authority = (
            _EmbodimentSensoryOutcomeAuthority(
                authority_key=_causal_cycle_key
            )
            if _causal_cycle_key
            else None
        )
        self._embodiment_outcome_causal_owner = (
            _ExactCausalExperienceOwner(
                on_settlement=lambda _settlement: None,
                log_event=self._log_substrate_event,
                max_transitions=64,
            )
            if _causal_cycle_key
            else None
        )
        self._w1_acoustic_emitter = None
        self._w1_binaural_auditory_l5_owner = None
        self._w1_anonymous_av_continuity_owner = None
        self._w1_physical_evidence = None
        self._w1_companion_vocal_experience = None
        self._w1_multi_emitter_capture = None
        self._w1_physical_key = None
        self._settled_experience_custody_key = None
        self._settled_experience_custody_profile = None
        self._live_settled_prediction_custodies = (
            _weakref.WeakValueDictionary()
        )
        if _causal_cycle_key:
            from dsf_ai_service.substrate.w1_acoustic_emitter import (
                W1AcousticEmitterAuthority as _W1AcousticEmitterAuthority,
            )
            from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
                W1AudiovisualPhysicalEvidenceAuthority as
                _W1AudiovisualPhysicalEvidenceAuthority,
            )
            from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
                W1BinauralAuditoryL5Owner as
                _W1BinauralAuditoryL5Owner,
            )
            from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
                W1AuthenticatedMultiEmitterCaptureOwner as
                _W1AuthenticatedMultiEmitterCaptureOwner,
            )
            from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
                W1AnonymousAudiovisualContinuityOwner as
                _W1AnonymousAudiovisualContinuityOwner,
            )
            _root_key = _causal_cycle_key.encode("utf-8")
            _w1_acoustic_key = _hmac.new(
                _root_key,
                b"guala-w1-authenticated-acoustic-emitter-v3",
                _hashlib.sha256,
            ).digest()
            _w1_physical_key = _hmac.new(
                _root_key,
                b"guala-w1-anonymous-multisensory-evidence-v8",
                _hashlib.sha256,
            ).digest()
            self._w1_physical_key = _w1_physical_key
            self._settled_experience_custody_key = _hmac.new(
                _root_key,
                b"guala-settled-experience-custody-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._settled_experience_custody_profile = (
                SettledExperienceCustodyProfile.create(
                    profile_id=(
                        "guala-multipurpose-settled-experience-v2"
                    ),
                    max_children=6,
                    max_snapshot_bytes=(
                        128 * 1024 * 1024
                    ),
                )
            )
            _w1_companion_key = _hmac.new(
                _root_key,
                b"guala-w1-companion-vocal-intent-v2",
                _hashlib.sha256,
            ).digest()
            _w1_continuity_key = _hmac.new(
                _root_key,
                b"guala-w1-anonymous-audiovisual-continuity-v1",
                _hashlib.sha256,
            ).digest()
            self._w1_acoustic_emitter = _W1AcousticEmitterAuthority(
                authority_key=_w1_acoustic_key,
                world_authority=self._embodiment_world,
            )
            self._w1_multi_emitter_capture = (
                _W1AuthenticatedMultiEmitterCaptureOwner(
                    authority_key=_hmac.new(
                        _root_key,
                        b"guala-w1-multi-emitter-room-capture-v1",
                        _hashlib.sha256,
                    ).digest(),
                    world_authority=self._embodiment_world,
                    acoustic_emitter=self._w1_acoustic_emitter,
                )
            )
            self._w1_binaural_auditory_l5_owner = (
                _W1BinauralAuditoryL5Owner(
                    max_transitions=64,
                )
            )
            self._w1_anonymous_av_continuity_owner = (
                _W1AnonymousAudiovisualContinuityOwner(
                    authority_key=_w1_continuity_key,
                    physical_authority_key=_w1_physical_key,
                    max_transitions=64,
                )
            )
            self._w1_physical_evidence = (
                _W1AudiovisualPhysicalEvidenceAuthority(
                    authority_key=_w1_physical_key,
                    world_authority=self._embodiment_world,
                    causal_owner=self._embodiment_outcome_causal_owner,
                    acoustic_emitter=self._w1_acoustic_emitter,
                    binaural_auditory_l5_owner=(
                        self._w1_binaural_auditory_l5_owner
                    ),
                    anonymous_av_continuity_owner=(
                        self._w1_anonymous_av_continuity_owner
                    ),
                )
            )
            from dsf_ai_service.substrate.w1_companion_vocal_experience import (
                W1CompanionVocalExperienceAuthority as
                _W1CompanionVocalExperienceAuthority,
            )
            self._w1_companion_vocal_experience = (
                _W1CompanionVocalExperienceAuthority(
                    authority_key=_w1_companion_key,
                    world_authority=self._embodiment_world,
                    physical_authority=self._w1_physical_evidence,
                )
            )
        self._thing_vocal_key = None
        self._thing_partition_authority = None
        self._causal_thing_mosaic_owner = None
        self._retained_audiovisual_custody = None
        self._causal_thing_sensory_expansion = None
        self._causal_thing_lived_context = None
        self._latest_retained_audiovisual_custody = None
        self._latest_live_sight_custody = None
        self._w1_self_acoustic_propagation = None
        self._fresh_articulatory_self_acoustic_custody = None
        self._articulatory_consequence_closure = None
        self._pending_articulatory_causal_attempt = None
        self._articulatory_exploration_selector = None
        self._consequence_evoked_articulatory_response = None
        self._articulatory_self_vocal_owner = None
        self._custody_native_tutoring_curriculum = None
        self._custody_native_tutoring_action_selector = None
        self._causal_thing_reciprocal_mosaic = None
        self._causal_thing_action_deliberation = None
        self._causal_thing_action_intent = None
        self._causal_thing_action_execution = None
        self._anonymous_passive_window_key = None
        self._anonymous_passive_window = None
        self._causal_inquiry_tutor_authority = None
        self._causal_inquiry_owner = None
        self._latest_causal_inquiry_observation = None
        self._w1_binaural_grounding_authority = None
        self._lived_vocal_teaching_authority = None
        self._grounded_articulatory_vocal_turn = None
        self._latest_executed_causal_thing_action = None
        self._latest_causal_thing_action = {
            "schema": "guala.causal_thing.action_engine_observation.v1",
            "state": "unobserved",
        }
        self._embodied_action_teaching_key = None
        self._embodied_action_teaching = None
        self._causal_deliberation_key = None
        self._causal_deliberation = None
        self._autonomous_causal_play = None
        self._causal_play_observation = None
        if _causal_cycle_key:
            from dsf_ai_service.substrate.embodied_action_teaching import (
                EmbodiedActionTeachingAuthority as
                _EmbodiedActionTeachingAuthority,
            )
            self._embodied_action_teaching_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-embodied-action-teaching-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._embodied_action_teaching = (
                _EmbodiedActionTeachingAuthority(
                    authority_key=self._embodied_action_teaching_key,
                    authorized_tutors=("joe", "wc"),
                    world_authority=self._embodiment_world,
                    action_cycle=self._causal_action_cycle,
                    demonstration_capacity=64,
                    max_command_bytes=4096,
                    max_encoded_state_bytes=2 * 1024 * 1024,
                )
            )
            from dsf_ai_service.substrate.causal_deliberation import (
                CausalDeliberation as _CausalDeliberation,
                DEFAULT_MAX_WITNESS_BYTES as
                _CAUSAL_DELIBERATION_MAX_WITNESS_BYTES,
            )
            self._causal_deliberation_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-causal-deliberation-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._causal_deliberation = _CausalDeliberation(
                authority_key=self._causal_deliberation_key,
                relation_capacity=64,
                max_witness_bytes=(
                    _CAUSAL_DELIBERATION_MAX_WITNESS_BYTES
                ),
                encoded_state_capacity=32 * 1024 * 1024,
            )
            from dsf_ai_service.substrate.autonomous_causal_play import (
                AutonomousCausalPlayOwner as _AutonomousCausalPlayOwner,
            )
            _autonomous_causal_play_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-autonomous-causal-play-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._autonomous_causal_play = _AutonomousCausalPlayOwner(
                authority_key=_autonomous_causal_play_key,
                relation_capacity=64,
                encoded_state_capacity=(
                    AUTONOMOUS_CAUSAL_PLAY_STATE_MAX_BYTES
                ),
            )
        self._causal_dispatcher_key = None
        self._causal_embodiment_executor_key = None
        self._causal_outcome_observer_key = None
        self._causal_action_dispatcher = None
        self._causal_embodiment_rejection_reason = None
        self._causal_embodiment_execution = None
        self._causal_last_dispatch_result = None
        if _causal_cycle_key:
            _root_key = _causal_cycle_key.encode("utf-8")
            self._causal_dispatcher_key = _hmac.new(
                _root_key,
                b"guala-causal-dispatcher-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._causal_embodiment_executor_key = _hmac.new(
                _root_key,
                b"guala-causal-embodiment-executor-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._causal_outcome_observer_key = _hmac.new(
                _root_key,
                b"guala-causal-outcome-observer-authority-v1",
                _hashlib.sha256,
            ).digest()
            from dsf_ai_service.substrate.causal_settlement_dispatcher import (
                CausalSettlementDispatcher as _CausalSettlementDispatcher,
            )
            self._causal_action_dispatcher = _CausalSettlementDispatcher(
                cycle=self._causal_action_cycle,
                authority_key=self._causal_dispatcher_key,
                embodiment_executor=self._execute_causal_embodiment_request,
                embodiment_executor_id="guala.embodiment.w1",
                embodiment_executor_authority_key=(
                    self._causal_embodiment_executor_key
                ),
                outcome_observer_id="guala.exact.sensory.outcome.v1",
                outcome_observer_authority_key=(
                    self._causal_outcome_observer_key
                ),
            )
        self._full_field_prediction_key = None
        self._full_field_prediction = None
        self._visual_region_continuity_key = None
        self._visual_region_continuity = None
        self._visual_exposure_epoch = None
        self._live_anonymous_encounter_continuity = None
        self._latest_visual_region_settlement = None
        self._latest_visual_region_observation = None
        self._latest_visual_region_rejection = None
        self._latest_sight_evoked_articulatory_occurrence = None
        self._latest_autonomous_articulatory_exploration = None
        self._latest_passive_sight_route_keys = None
        self._latest_passive_sight_world_receipt_sha256 = None
        self._prediction_conditioned_intent_receipt = None
        self._prediction_conditioned_binding_id = None
        self._latest_full_field_prediction_observation = None
        self._legacy_causal_prediction_disposition = None
        if _causal_cycle_key:
            from dsf_ai_service.substrate.full_field_prediction import (
                FullFieldPredictionAuthority as
                _FullFieldPredictionAuthority,
            )
            self._full_field_prediction_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-full-field-prediction-authority-v1",
                _hashlib.sha256,
            ).digest()
            self._full_field_prediction = _FullFieldPredictionAuthority(
                authority_key=self._full_field_prediction_key,
            )
            from dsf_ai_service.substrate.visual_region_continuity import (
                DeterministicVisualRegionContinuityAuthority as
                _DeterministicVisualRegionContinuityAuthority,
            )
            self._visual_region_continuity_key = _hmac.new(
                _causal_cycle_key.encode("utf-8"),
                b"guala-visual-region-continuity-authority-v1",
                _hashlib.sha256,
            ).digest()
            from dsf_ai_service.substrate.visual_exposure_epoch import (
                VisualExposureEpochAuthority as
                _VisualExposureEpochAuthority,
            )
            self._visual_exposure_epoch = _VisualExposureEpochAuthority(
                authority_key=_hmac.new(
                    _causal_cycle_key.encode("utf-8"),
                    b"guala-visual-exposure-epoch-authority-v1",
                    _hashlib.sha256,
                ).digest(),
            )
            self._visual_region_continuity = (
                _DeterministicVisualRegionContinuityAuthority(
                    authority_key=self._visual_region_continuity_key,
                    exposure_epoch_authority=self._visual_exposure_epoch,
                )
            )
            from dsf_ai_service.substrate.live_anonymous_encounter_continuity import (
                LiveAnonymousEncounterContinuityAuthority as
                _LiveAnonymousEncounterContinuityAuthority,
            )
            self._live_anonymous_encounter_continuity = (
                _LiveAnonymousEncounterContinuityAuthority(
                    authority_key=_hmac.new(
                        _causal_cycle_key.encode("utf-8"),
                        b"guala-live-anonymous-encounter-authority-v1",
                        _hashlib.sha256,
                    ).digest(),
                    visual_authority=self._visual_region_continuity,
                )
            )
        self._causal_cycle_bridge_lock = threading.RLock()
        self._causal_cycle_pending_review = None
        self._engine_quiesced = False
        self._engine_quiescence_complete = False
        self._engine_mutation_condition = threading.Condition()
        self._engine_mutation_admission_open = True
        self._engine_active_mutations = 0
        self._engine_settled_snapshot_requested = False
        self._engine_mutation_local = threading.local()
        self._engine_raw_threads = set()
        self._engine_raw_threads_started = 0
        self._engine_raw_threads_completed = 0

        # GL-CMD-175 P2 fix (root cause behind seams 1-2's near-zero
        # discrimination): the validated recall mechanism (embryo.py's own
        # seed_organism(), 100% at n=50/200) was never tested on a single
        # ("language" only) modality -- it always fed the FULL multi-modal
        # signal set via ExperiencePipeline._build_multi_modal_signals
        # (touch/smell/taste real waveform generators + visual/auditory
        # procedural placeholders, all deterministic-from-word). Confirmed
        # directly: switching observable (event_count vs resonant_spectral)
        # made no difference at 0/10 either way; feeding the SAME full
        # signal set restored 10/10 for BOTH observables. So the fix is
        # signal richness, not the observable. This reuses that exact,
        # already-validated pipeline -- not a new invention. Honesty flag:
        # touch/smell/taste/visual/auditory here are DETERMINISTIC,
        # WORD-DERIVED PROCEDURAL SIGNALS (SensoryTransducer + NullAtlasReader,
        # same as the model-side tests) -- NOT real sensory experience. No
        # vision/sound/touch/smell/taste tap into her real senses exists yet
        # (P1's own honest scope limit, unchanged by this fix). This gives
        # the recall substrate the channel richness it was actually built
        # and validated against; it does not simulate her having senses she
        # doesn't have.
        #
        # Performance: the model-side default (n_samples=200/channel) measured
        # at ~450ms per word end-to-end in her live process -- far too slow
        # for a live tick loop (baseline ~250ms/tick). Measured directly
        # (not guessed): n_samples=20 preserves 100% recall on both the
        # original 10-probe test AND a second, disjoint 20-word vocabulary
        # (generalization check), at ~15ms/word for the teach loop -- a
        # resolution/performance choice for a synthetic placeholder signal,
        # not a scoring constant tuned to flatter a number. See
        # _organism_signal below.
        self._organism_transducer = None

    _READING_PREDICTION_SOURCES = frozenset(
        {"corpus", "curriculum", "worldfeed", "gap_study"})

    def _ensure_engine_lifecycle_state(self):
        """Initialize lifecycle fields on narrow legacy/test constructions."""
        if hasattr(self, "_engine_mutation_condition"):
            with self._engine_mutation_condition:
                if not hasattr(
                    self,
                    "_engine_settled_snapshot_requested",
                ):
                    self._engine_settled_snapshot_requested = False
            return
        bootstrap_lock = self.__dict__.setdefault(
            "_engine_lifecycle_bootstrap_lock", threading.Lock())
        with bootstrap_lock:
            if hasattr(self, "_engine_mutation_condition"):
                return
            self._engine_quiesced = getattr(self, "_engine_quiesced", False)
            self._engine_quiescence_complete = False
            self._engine_mutation_condition = threading.Condition()
            self._engine_mutation_admission_open = True
            self._engine_active_mutations = 0
            self._engine_settled_snapshot_requested = False
            self._engine_mutation_local = threading.local()
            self._engine_raw_threads = set()
            self._engine_raw_threads_started = 0
            self._engine_raw_threads_completed = 0

    @contextlib.contextmanager
    def _engine_mutation_scope(self, owner, *, advance_causal_tick=True):
        """Atomically admit one engine mutation, including nested calls."""
        if not isinstance(advance_causal_tick, bool):
            raise TypeError("causal tick authority must be boolean")
        self._ensure_engine_lifecycle_state()
        depth = getattr(self._engine_mutation_local, "depth", 0)
        if depth:
            self._engine_mutation_local.depth = depth + 1
            try:
                yield
            finally:
                self._engine_mutation_local.depth = depth
            return

        with self._engine_mutation_condition:
            while self._engine_settled_snapshot_requested:
                if not self._engine_mutation_admission_open:
                    raise RuntimeError(
                        f"engine mutation rejected during quiescence: {owner}")
                self._engine_mutation_condition.wait()
            if not self._engine_mutation_admission_open:
                raise RuntimeError(
                    f"engine mutation rejected during quiescence: {owner}")
            self._engine_active_mutations += 1
        self._engine_mutation_local.depth = 1
        try:
            if advance_causal_tick:
                with self.lock:
                    if (
                        isinstance(self.tick, bool)
                        or not isinstance(self.tick, int)
                        or self.tick < 0
                    ):
                        raise RuntimeError(
                            "causal organism tick changed type or extent"
                        )
                    # Every transaction and hot save sees this causal time.
                    self.tick += 1
            yield
        finally:
            self._engine_mutation_local.depth = 0
            with self._engine_mutation_condition:
                if self._engine_active_mutations <= 0:
                    raise RuntimeError("engine mutation counter underflow")
                self._engine_active_mutations -= 1
                self._engine_mutation_condition.notify_all()

    def _start_engine_background_thread(self, target, *, name, args=(),
                                        daemon=True):
        """Start and retain an accepted engine continuation.

        Registration and mutation counting happen before ``Thread.start``.
        A continuation spawned by an already-admitted mutation remains part of
        that accepted operation even if quiescence closes admission between the
        foreground return and the continuation's work.
        """
        self._ensure_engine_lifecycle_state()
        inherited = getattr(self._engine_mutation_local, "depth", 0) > 0

        def run_registered():
            self._engine_mutation_local.depth = 1
            try:
                target(*args)
            finally:
                self._engine_mutation_local.depth = 0
                with self._engine_mutation_condition:
                    self._engine_raw_threads_completed += 1
                    if self._engine_active_mutations <= 0:
                        raise RuntimeError("engine background counter underflow")
                    self._engine_active_mutations -= 1
                    self._engine_mutation_condition.notify_all()

        thread = threading.Thread(target=run_registered, daemon=daemon,
                                  name=name)
        with self._engine_mutation_condition:
            while (
                self._engine_settled_snapshot_requested
                and not inherited
            ):
                if not self._engine_mutation_admission_open:
                    raise RuntimeError(
                        "engine background work rejected during quiescence: "
                        f"{name}"
                    )
                self._engine_mutation_condition.wait()
            if not self._engine_mutation_admission_open and not inherited:
                raise RuntimeError(
                    f"engine background work rejected during quiescence: {name}")
            self._engine_raw_threads = {
                registered
                for registered in self._engine_raw_threads
                if registered.is_alive()
            }
            self._engine_active_mutations += 1
            self._engine_raw_threads_started += 1
            self._engine_raw_threads.add(thread)
            try:
                thread.start()
            except Exception:
                self._engine_raw_threads.discard(thread)
                self._engine_raw_threads_started -= 1
                self._engine_active_mutations -= 1
                self._engine_mutation_condition.notify_all()
                raise
        return thread

    def _close_engine_mutation_admission(self):
        self._ensure_engine_lifecycle_state()
        with self._engine_mutation_condition:
            self._engine_mutation_admission_open = False
            self._engine_mutation_condition.notify_all()

    def _wait_for_engine_mutations(self, deadline):
        with self._engine_mutation_condition:
            while self._engine_active_mutations:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(
                        "engine quiescence timed out with "
                        f"{self._engine_active_mutations} mutation(s) active")
                self._engine_mutation_condition.wait(timeout=remaining)

    def _join_engine_raw_threads(self, deadline):
        with self._engine_mutation_condition:
            threads = tuple(self._engine_raw_threads)
        alive = []
        for thread in threads:
            if thread is threading.current_thread():
                alive.append(thread.name)
                continue
            thread.join(timeout=max(0.0, deadline - time.monotonic()))
            if thread.is_alive():
                alive.append(thread.name)
        if alive:
            raise RuntimeError(
                "engine quiescence timed out joining raw threads: "
                + ", ".join(sorted(alive)))
        with self._engine_mutation_condition:
            if (self._engine_raw_threads_completed
                    != self._engine_raw_threads_started):
                raise RuntimeError(
                    "engine raw-thread completion mismatch "
                    f"(started={self._engine_raw_threads_started}, "
                    f"completed={self._engine_raw_threads_completed})")
            self._engine_raw_threads.clear()
            return {
                "started": self._engine_raw_threads_started,
                "completed": self._engine_raw_threads_completed,
                "joined_at_quiescence": len(threads),
                "alive": [],
            }

    def settle_queues(self, budget_s=420.0, threshold=8):
        """Give accepted bounded owner work a pre-quiescence drain budget."""
        deadline = time.monotonic() + float(budget_s)
        queues = ()
        started = {name: q.unfinished_tasks for name, q in queues}
        while True:
            busy = {name: q.unfinished_tasks for name, q in queues
                    if q.unfinished_tasks > threshold}
            if not busy:
                remaining = {n: q.unfinished_tasks for n, q in queues}
                print(f"[GualaLoom][seal-settle] settled: started={started} "
                      f"remaining={remaining}", flush=True)
                return {"settled": True, "budget_s": float(budget_s),
                        "threshold": threshold, "started": started,
                        "remaining": remaining}
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "seal settle budget expired with backlog: "
                    + ", ".join(f"{n}={c}" for n, c in sorted(busy.items())))
            time.sleep(0.25)

    def quiesce_background_workers(self, timeout=120.0):
        """Stop, drain, and join every engine-owned mutation source.

        This is a lifecycle boundary, not a best-effort shutdown.  It either
        proves every engine thread/queue is quiet or raises with the exact
        owners still active; callers must not seal persistence after failure.
        """
        deadline = time.monotonic() + float(timeout)

        def remaining():
            return max(0.0, deadline - time.monotonic())

        self._engine_quiescence_complete = False
        autonomous_driver = self._autonomous_experience_driver
        if autonomous_driver is not None:
            autonomous_driver.quiesce(remaining())
        self._close_engine_mutation_admission()
        with self._causal_play_condition:
            self._causal_play_stop = True
            self._causal_play_pending = False
            self._causal_play_condition.notify_all()
            causal_play_thread = self._causal_play_thread
        if (
            causal_play_thread is not None
            and causal_play_thread is not threading.current_thread()
        ):
            causal_play_thread.join(timeout=remaining())
            if causal_play_thread.is_alive():
                raise RuntimeError(
                    "quiescence timed out joining causal play owner"
                )

        self._wait_for_engine_mutations(deadline)
        self.synchronize_auditory_q_process_state()
        terminal_authorities = (
            self._auditory_incremental_terminals.authority_counts()
        )
        if any(terminal_authorities.values()):
            raise RuntimeError(
                "engine quiescence rejected live auditory terminal authority: "
                f"issued={terminal_authorities['issued_terminal_authorities']}, "
                "in_flight="
                f"{terminal_authorities['in_flight_terminal_authorities']}"
            )
        full_field_transaction_authorities = (
            self._auditory_full_field_transactions.authority_counts()
        )
        if any(full_field_transaction_authorities.values()):
            raise RuntimeError(
                "engine quiescence rejected live auditory full-field "
                f"transaction authority: {full_field_transaction_authorities}"
            )
        terminal_pipeline = self.auditory_terminal_pipeline_status()
        if (
            terminal_pipeline["pending_count"]
            or terminal_pipeline["in_flight"]
            or terminal_pipeline["worker_active"]
        ):
            raise RuntimeError(
                "engine quiescence rejected undrained auditory terminal "
                f"pipeline: {terminal_pipeline}"
            )
        raw_thread_certificate = self._join_engine_raw_threads(deadline)

        # No foreground operation, accepted continuation, or engine loop can
        # now produce another queue item. Freeze the lazy queues before
        # measuring and draining their accepted work.
        self._engine_quiesced = True

        queues = ()
        for name, queue in queues:
            while queue.unfinished_tasks:
                if remaining() <= 0:
                    raise RuntimeError(
                        f"quiescence timed out draining {name} queue "
                        f"({queue.unfinished_tasks} unfinished)")
                time.sleep(min(0.05, remaining()))

        spike_certificate = {"enabled": False}

        queue_certificate = {
            name: {"unfinished": queue.unfinished_tasks, "queued": queue.qsize()}
            for name, queue in queues
        }
        self._engine_quiescence_complete = True
        return {
            "pending_turns": 0,
            "active_mutations": 0,
            "engine_threads_joined": True,
            "queues_drained": True,
            "raw_threads": raw_thread_certificate,
            "queues": queue_certificate,
            "spike_bus": spike_certificate,
        }

    def strict_shutdown(self, timeout=120.0):
        """Quiesce a discarded instance and propagate any incomplete proof."""
        return self.quiesce_background_workers(timeout=timeout)

    def shutdown(self):
        """Quiesce one discarded runtime and close auditory resources."""
        try:
            self.quiesce_background_workers(timeout=5.0)
        except Exception:
            # Test/process teardown fallback only.  Production sealing calls
            # quiesce_background_workers directly and must propagate failure.
            with self._causal_play_condition:
                self._causal_play_stop = True
                self._causal_play_pending = False
                self._causal_play_condition.notify_all()
        auditory_shutdown_errors = []
        try:
            self.wait_for_auditory_terminal_pipeline()
        except BaseException as error:
            auditory_shutdown_errors.append(error)
        with getattr(
            self,
            "_auditory_terminal_worker_lock",
            contextlib.nullcontext(),
        ):
            process_owner = getattr(
                self,
                "_auditory_q_process_owner",
                None,
            )
            if process_owner is not None:
                try:
                    process_owner.close()
                except BaseException as error:
                    auditory_shutdown_errors.append(error)
                    try:
                        process_owner.abandon()
                    except BaseException as abandon_error:
                        auditory_shutdown_errors.append(abandon_error)
                finally:
                    self._auditory_q_process_owner = None
        if len(auditory_shutdown_errors) == 1:
            raise auditory_shutdown_errors[0]
        if auditory_shutdown_errors:
            raise BaseExceptionGroup(
                "auditory terminal shutdown failed",
                auditory_shutdown_errors,
            )

    def _settled_prediction_custody(
        self,
        physical_mount,
        *,
        world_execution=None,
        world_observation=None,
    ):
        """Create one occurrence custody without invoking a W1 producer."""
        if (
            self._settled_experience_custody_key is None
            or self._settled_experience_custody_profile is None
            or self._w1_physical_key is None
            or self._causal_cycle_key is None
        ):
            raise RuntimeError(
                "settled experience custody authority is unavailable"
            )
        evidence = physical_mount.evidence_receipt
        if evidence is None:
            raise ValueError(
                "settled experience source mount has no physical receipt"
            )
        source_key = evidence.authority_receipt_sha256
        existing = self._live_settled_prediction_custodies.get(
            source_key
        )
        if existing is not None:
            if (
                existing.view.physical_evidence_receipt is not evidence
                or existing.view.causal_settlement
                is not physical_mount.causal_settlement
            ):
                raise RuntimeError(
                    "settled experience receipt crossed source occurrence"
                )
            return existing
        authority = SettledExperienceCustodyAuthority(
            authority_key=self._settled_experience_custody_key,
            w1_physical_authority_key=self._w1_physical_key,
            world_authority_key=self._causal_cycle_key,
            profile=self._settled_experience_custody_profile,
        )
        custody = authority.admit(
            physical_mount,
            world_execution,
            world_observation=world_observation,
        )
        capability = authority.issue_child(
            FULL_FIELD_PREDICTION_CONSUMER_ID
        )
        view = authority.open_child(capability)
        if (
            view.causal_settlement is not custody.causal_settlement
            or view.source_occurrence_id != custody.source_occurrence_id
        ):
            raise RuntimeError(
                "settled prediction custody changed parent occurrence"
            )
        result = _SettledPredictionCustody(
            authority=authority,
            capability=capability,
            custody=custody,
            view=view,
        )
        self._live_settled_prediction_custodies[source_key] = result
        return result

    def _commit_lived_context_partitions(
        self,
        settled_custodies,
        partitions,
        *,
        action_consequence=None,
    ):
        """Publish exact durable partition references into lived context."""
        lived = self._causal_thing_lived_context
        if lived is None:
            raise RuntimeError(
                "causal THING lived-context authority is unavailable"
            )
        if (
            not isinstance(settled_custodies, tuple)
            or not isinstance(partitions, tuple)
            or not settled_custodies
            or len(settled_custodies) != len(partitions)
            or (action_consequence is not None and len(partitions) != 1)
        ):
            raise ValueError(
                "lived-context partition transaction changed cardinality"
            )
        undos = []
        prepared = None
        try:
            for settled_custody, partition in zip(
                settled_custodies,
                partitions,
                strict=True,
            ):
                if not isinstance(
                    settled_custody,
                    _SettledPredictionCustody,
                ):
                    raise TypeError(
                        "lived context requires settled W1 custody"
                    )
                prepared = lived.prepare_admission(
                    settled_custody.custody,
                    durable_reference=partition,
                    action_consequence=action_consequence,
                )
                undos.append(
                    lived.commit_prepared_admission(prepared)
                )
                prepared = None
            return tuple(undos)
        except BaseException:
            if prepared is not None:
                lived.discard_prepared_admission(prepared)
            for undo in reversed(undos):
                lived.rollback_committed_admission(undo)
            raise

    def _rollback_lived_context_admissions(self, undos):
        """Restore the exact lived-context prefix in reverse commit order."""
        if not undos:
            return
        lived = self._causal_thing_lived_context
        if lived is None:
            raise RuntimeError(
                "causal THING lived-context authority is unavailable"
            )
        for undo in reversed(undos):
            lived.rollback_committed_admission(undo)

    def _commit_lived_context_expansion(
        self,
        expansion,
        *,
        custody_authority,
        custody_capability,
    ):
        """Publish one already-durable AV expansion reference."""
        lived = self._causal_thing_lived_context
        if lived is None:
            raise RuntimeError(
                "causal THING lived-context authority is unavailable"
            )
        prepared = lived.prepare_expansion_admission(
            expansion,
            custody_authority=custody_authority,
            custody_capability=custody_capability,
        )
        try:
            return lived.commit_prepared_admission(prepared)
        except BaseException:
            lived.discard_prepared_admission(prepared)
            raise

    def _admit_known_sight_expansion_with_lived_context(
        self,
        *,
        custody_authority,
        custody_capability,
    ):
        """Commit one exact AV expansion and lived reference together."""
        raise RuntimeError(
            "legacy Python THING sensory expansion is permanently retired"
        )
        expansion_owner = self._causal_thing_sensory_expansion
        if expansion_owner is None:
            raise RuntimeError(
                "causal THING sensory expansion authority is unavailable"
            )
        prepared = expansion_owner.prepare_known_sight_admission(
            custody_authority=custody_authority,
            custody_capability=custody_capability,
        )
        if isinstance(
            prepared,
            CausalThingSensoryExpansionAdmission,
        ):
            return prepared
        expansion_undo = None
        lived_undo = None
        try:
            expansion_undo = (
                expansion_owner.commit_prepared_admission(prepared)
            )
            if prepared.admission.expansion is None:
                raise RuntimeError(
                    "committed sensory expansion lacks its durable record"
                )
            lived_undo = self._commit_lived_context_expansion(
                prepared.admission.expansion,
                custody_authority=custody_authority,
                custody_capability=custody_capability,
            )
            return prepared.admission
        except BaseException:
            if lived_undo is not None:
                self._causal_thing_lived_context\
                    .rollback_committed_admission(lived_undo)
            if expansion_undo is not None:
                expansion_owner.rollback_committed_admission(
                    expansion_undo
                )
            else:
                expansion_owner.discard_prepared_admission(prepared)
            raise

    def _admit_thing_genesis_from_custody(
        self,
        settled_custody,
        *,
        state_dir=None,
    ):
        """Atomically retain first contact and its exact lived occurrence."""
        raise RuntimeError(
            "legacy Python THING encounter database is permanently retired"
        )
        if not isinstance(settled_custody, _SettledPredictionCustody):
            raise TypeError("THING genesis requires settled W1 custody")
        if (
            self._thing_partition_authority is None
            or self._causal_thing_mosaic_owner is None
        ):
            raise RuntimeError("causal THING mosaic authority is unavailable")
        capability = settled_custody.authority.issue_child(
            THING_MOSAIC_CONSUMER_ID
        )
        partition = (
            self._thing_partition_authority.partition_from_custody(
                custody_authority=settled_custody.authority,
                capability=capability,
            )
        )
        prepared = (
            self._causal_thing_mosaic_owner
            .prepare_custody_genesis_admission(partition)
        )
        thing_undo = None
        lived_undos = ()
        try:
            thing_undo = (
                self._causal_thing_mosaic_owner
                .commit_prepared_custody_genesis_admission(prepared)
            )
            lived_undos = self._commit_lived_context_partitions(
                (settled_custody,),
                (partition,),
            )
            if state_dir is not None:
                self.save_hot_state(state_dir)
            return prepared.staged_mosaic
        except BaseException:
            self._rollback_lived_context_admissions(lived_undos)
            if thing_undo is not None:
                (
                    self._causal_thing_mosaic_owner
                    .rollback_committed_custody_genesis_admission(
                        thing_undo
                    )
                )
            else:
                (
                    self._causal_thing_mosaic_owner
                    .discard_prepared_custody_genesis_admission(prepared)
                )
            raise

    def _admit_thing_continuation_from_custody(
        self,
        settled_custody,
    ):
        """Extend one held THING through its next physical action outcome."""
        raise RuntimeError(
            "legacy Python THING encounter database is permanently retired"
        )
        if not isinstance(settled_custody, _SettledPredictionCustody):
            raise TypeError(
                "THING continuation requires settled W1 custody"
            )
        if (
            self._thing_partition_authority is None
            or self._causal_thing_mosaic_owner is None
        ):
            raise RuntimeError(
                "causal THING continuation authority is unavailable"
            )
        view = settled_custody.authority.open_child(
            settled_custody.capability
        )
        execution = view.world_execution
        if execution is None:
            raise ValueError(
                "THING continuation requires an applied physical action"
            )
        held_before = tuple(
            value.object_id
            for value in execution.before.objects
            if value.held_by_body_id == execution.before.self_body_id
        )
        held_after = tuple(
            value.object_id
            for value in execution.after.objects
            if value.held_by_body_id == execution.after.self_body_id
        )
        if (
            len(held_before) != 1
            or held_after != held_before
        ):
            return None
        capability = settled_custody.authority.issue_child(
            THING_MOSAIC_CONSUMER_ID
        )
        continuity = (
            self._thing_partition_authority
            .entity_continuity_from_custody(
                custody_authority=settled_custody.authority,
                capability=capability,
            )
        )
        matches = tuple(
            mosaic
            for mosaic in self._causal_thing_mosaic_owner.mosaics
            if (
                mosaic.partitions[-1]
                .entity_continuity_hmac_sha256 == continuity
                and mosaic.partitions[-1].world_revision
                == execution.before.revision
                and mosaic.partitions[-1]
                .world_observation_receipt_sha256
                == execution.before.authority_receipt_sha256
            )
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise RuntimeError(
                "held physical continuity resolves multiple causal THINGs"
            )
        partition = (
            self._thing_partition_authority.partition_from_custody(
                custody_authority=settled_custody.authority,
                capability=capability,
                prior=matches[0].partitions[-1],
            )
        )
        prepared = (
            self._causal_thing_mosaic_owner
            .prepare_ordered_custody_continuation((partition,))
        )
        thing_undo = None
        lived_undos = ()
        try:
            thing_undo = (
                self._causal_thing_mosaic_owner
                .commit_prepared_ordered_custody_continuation(prepared)
            )
            lived_undos = self._commit_lived_context_partitions(
                (settled_custody,),
                (partition,),
            )
            return prepared.staged_mosaic
        except BaseException:
            self._rollback_lived_context_admissions(lived_undos)
            if thing_undo is not None:
                (
                    self._causal_thing_mosaic_owner
                    .rollback_committed_ordered_custody_continuation(
                        thing_undo
                    )
                )
            else:
                (
                    self._causal_thing_mosaic_owner
                    .discard_prepared_ordered_custody_continuation(
                        prepared
                    )
                )
            raise

    def _prepare_ordered_thing_continuation_from_custodies(
        self,
        settled_custodies,
    ):
        """Stage one exact continuation of a physically contacted THING."""

        raise RuntimeError(
            "legacy Python THING encounter database is permanently retired"
        )

        if (
            not isinstance(settled_custodies, tuple)
            or not settled_custodies
            or any(
                not isinstance(value, _SettledPredictionCustody)
                for value in settled_custodies
            )
        ):
            raise TypeError(
                "ordered THING continuation requires a nonempty "
                "immutable custody tuple"
            )
        if (
            self._thing_partition_authority is None
            or self._causal_thing_mosaic_owner is None
        ):
            raise RuntimeError(
                "causal THING continuation authority is unavailable"
            )
        views = tuple(
            custody.authority.open_child(custody.capability)
            for custody in settled_custodies
        )
        executions = tuple(view.world_execution for view in views)
        if any(execution is None for execution in executions):
            raise ValueError(
                "ordered THING continuation requires applied physical "
                "actions"
            )
        first_execution = executions[0]
        contact_before = (
            self._thing_partition_authority.contacted_entity_continuity(
                first_execution.before
            )
        )
        contact_after = (
            self._thing_partition_authority.contacted_entity_continuity(
                first_execution.after
            )
        )
        if contact_before is None or contact_after != contact_before:
            return None
        capabilities = tuple(
            custody.authority.issue_child(
                THING_MOSAIC_CONSUMER_ID
            )
            for custody in settled_custodies
        )
        continuity = (
            self._thing_partition_authority
            .entity_continuity_from_custody(
                custody_authority=settled_custodies[0].authority,
                capability=capabilities[0],
            )
        )
        matches = tuple(
            mosaic
            for mosaic in self._causal_thing_mosaic_owner.mosaics
            if (
                mosaic.partitions[-1]
                .entity_continuity_hmac_sha256
                == continuity
                and mosaic.partitions[-1].world_revision
                == first_execution.before.revision
                and mosaic.partitions[-1]
                .world_observation_receipt_sha256
                == first_execution.before.authority_receipt_sha256
            )
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise RuntimeError(
                "contacted physical continuity resolves multiple causal "
                "THINGs"
            )
        prior = matches[0].partitions[-1]
        partitions = []
        for custody, capability in zip(
            settled_custodies,
            capabilities,
            strict=True,
        ):
            partition = (
                self._thing_partition_authority
                .partition_from_custody(
                    custody_authority=custody.authority,
                    capability=capability,
                    prior=prior,
                )
            )
            partitions.append(partition)
            prior = partition
        return (
            self._causal_thing_mosaic_owner
            .prepare_ordered_custody_continuation(
                tuple(partitions)
            )
        )

    def _admit_tutoring_from_custody(
        self,
        settled_custody,
        *,
        return_committed_progression=False,
    ):
        """Admit one already-custodied lived occurrence to tutoring."""
        raise RuntimeError(
            "legacy Python custody tutoring is permanently retired"
        )
        if not isinstance(settled_custody, _SettledPredictionCustody):
            raise TypeError("tutoring requires settled W1 custody")
        curriculum = self._custody_native_tutoring_curriculum
        if curriculum is None:
            raise RuntimeError(
                "custody-native tutoring curriculum is unavailable"
            )
        capability = settled_custody.authority.issue_child(
            TUTORING_CURRICULUM_CONSUMER_ID
        )
        committed = curriculum.admit_experience_and_schedule(
            custody_authority=settled_custody.authority,
            custody_capability=capability,
        )
        admission = committed.admission
        scheduled = committed.scheduled
        observation = {
            "experience_receipt_sha256": (
                admission.experience.authority_receipt_sha256
            ),
            "resolved_active_opportunity": (
                admission.resolved_active_opportunity
            ),
            "scheduled": (
                scheduled.record() if scheduled is not None else None
            ),
        }
        return (
            (observation, committed)
            if return_committed_progression
            else observation
        )

    def _settled_self_acoustic_custody(
        self,
        self_acoustic_mount,
        *,
        world_execution,
    ):
        """Take one occurrence custody of an already-settled self sound."""
        if (
            self._settled_experience_custody_key is None
            or self._settled_experience_custody_profile is None
            or self._w1_physical_key is None
            or self._causal_cycle_key is None
            or self._thing_vocal_key is None
        ):
            raise RuntimeError(
                "settled self-acoustic custody authority is unavailable"
            )
        authority = SettledExperienceCustodyAuthority(
            authority_key=self._settled_experience_custody_key,
            w1_physical_authority_key=self._w1_physical_key,
            world_authority_key=self._causal_cycle_key,
            w1_self_acoustic_authority_key=self._thing_vocal_key,
            profile=self._settled_experience_custody_profile,
        )
        custody = authority.admit(
            self_acoustic_mount,
            world_execution,
        )
        capability = authority.issue_child(
            FULL_FIELD_PREDICTION_CONSUMER_ID
        )
        view = authority.open_child(capability)
        if (
            view.causal_settlement is not custody.causal_settlement
            or view.source_occurrence_id != custody.source_occurrence_id
        ):
            raise RuntimeError(
                "settled self-acoustic custody changed parent occurrence"
            )
        return _SettledPredictionCustody(
            authority=authority,
            capability=capability,
            custody=custody,
            view=view,
        )

    def _full_field_prediction_observe(
        self,
        settlement,
        *,
        prediction_transition=False,
        action_outcome=False,
        intake=None,
        token_sequence=None,
        language_episode=None,
        custody_authority=None,
        custody_capability=None,
        auditory_transport=None,
        auditory_cochlear=None,
        auditory_stream_settlement=None,
        verified_causal_transaction=None,
    ):
        """Admit one explicit prediction edge without temporal inference."""
        authority = self._full_field_prediction
        if authority is None:
            return None
        auditory_values = (intake, token_sequence)
        if any(value is not None for value in auditory_values) and not all(
            value is not None for value in auditory_values
        ):
            raise ValueError("prediction auditory attachment is incomplete")
        w1_values = (custody_authority, custody_capability)
        if any(value is not None for value in w1_values) and not all(
            value is not None for value in w1_values
        ):
            raise ValueError("prediction W1 attachment is incomplete")
        try:
            episode = authority.admit_episode(
                settlement,
                custody_authority=custody_authority,
                custody_capability=custody_capability,
                auditory_transport=auditory_transport,
                auditory_cochlear=auditory_cochlear,
                auditory_stream_settlement=auditory_stream_settlement,
                verified_transaction=verified_causal_transaction,
            )
        except RuntimeError as error:
            if str(error) != "prediction_capacity_full":
                raise
            self._latest_full_field_prediction_observation = {
                "reason": "prediction_capacity_full",
                "schema": "guala.full_field_prediction.engine_observation.v1",
                "settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "status": "capacity_full",
            }
            return None
        current = authority.current_episode()
        attempt = authority.current_attempt()
        transition = None
        if current is None or attempt is None:
            next_attempt = authority.open_context(episode)
            status = (
                "action_outcome_unconditioned"
                if action_outcome else "context_opened"
            )
        elif current.episode_id == episode.episode_id:
            next_attempt = attempt
            status = "duplicate_current_episode"
        elif (
            current.settlement_receipt_sha256
            == episode.settlement_receipt_sha256
        ):
            if authority.status()["armed_action"]:
                next_attempt = attempt
                status = "attachment_deferred_for_live_action"
            else:
                next_attempt = authority.replace_current_episode(episode)
                status = "current_episode_attachment_completed"
        elif attempt.mode == "action_conditioned":
            if not action_outcome:
                next_attempt = attempt
                status = "action_outcome_pending"
            else:
                binding_id = self._prediction_conditioned_binding_id
                if binding_id is None:
                    raise RuntimeError(
                        "conditioned prediction lost its action binding"
                    )
                closure = self._causal_action_cycle.latest_closure_record(
                    binding_id
                )
                if closure is None:
                    raise RuntimeError(
                        "conditioned prediction lacks its closed outcome"
                    )
                step = authority.observe_next(
                    episode,
                    action_cycle=self._causal_action_cycle,
                    closure_record=closure,
                )
                transition = step.transition
                next_attempt = step.next_prediction
                status = "action_outcome_observed"
                self._prediction_conditioned_intent_receipt = None
                self._prediction_conditioned_binding_id = None
        elif action_outcome:
            authority.stop_context()
            next_attempt = authority.open_context(episode)
            status = "action_outcome_unconditioned"
        elif authority.is_exact_passive_continuation(current, episode):
            step = authority.observe_next(episode)
            transition = step.transition
            next_attempt = step.next_prediction
            status = "exact_audiovisual_transition_observed"
        elif prediction_transition:
            step = authority.observe_next(episode)
            transition = step.transition
            next_attempt = step.next_prediction
            status = "passive_transition_observed"
        else:
            authority.stop_context()
            next_attempt = authority.open_context(episode)
            status = "context_rebased_without_relation"
        self._latest_full_field_prediction_observation = {
            "attempt_id": next_attempt.attempt_id,
            "attempt_status": next_attempt.status,
            "episode_id": episode.episode_id,
            "reason": status,
            "schema": "guala.full_field_prediction.engine_observation.v1",
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "status": "observed",
            "transition_id": (
                transition.transition_id if transition is not None else None
            ),
        }
        authority.compact_unreferenced_episodes()
        return episode

    def _condition_full_field_prediction_on_action(self, intent):
        authority = self._full_field_prediction
        if authority is None:
            return None
        attempt = authority.condition_on_action(
            intent=intent,
            action_cycle=self._causal_action_cycle,
        )
        self._prediction_conditioned_intent_receipt = (
            intent.authority_receipt_sha256
        )
        self._prediction_conditioned_binding_id = intent.binding_id
        self._latest_full_field_prediction_observation = {
            "attempt_id": attempt.attempt_id,
            "attempt_status": attempt.status,
            "binding_id": intent.binding_id,
            "intent_receipt_sha256": intent.authority_receipt_sha256,
            "reason": "action_conditioned_before_execution",
            "schema": "guala.full_field_prediction.engine_observation.v1",
            "status": "conditioned",
        }
        return attempt

    def _cancel_full_field_prediction_action(self):
        receipt = self._prediction_conditioned_intent_receipt
        if receipt is None or self._full_field_prediction is None:
            return None
        attempt = self._full_field_prediction.cancel_conditioned_action(
            receipt
        )
        self._prediction_conditioned_intent_receipt = None
        self._prediction_conditioned_binding_id = None
        self._latest_full_field_prediction_observation = {
            "attempt_id": attempt.attempt_id,
            "attempt_status": attempt.status,
            "reason": "executor_rejected_before_outcome",
            "schema": "guala.full_field_prediction.engine_observation.v1",
            "status": "cancelled",
        }
        return attempt

    def _record_causal_perception_without_dispatch(
        self,
        settlement,
        *,
        prediction_transition=False,
        action_outcome=False,
        already_recorded=False,
        intake=None,
        token_sequence=None,
        language_episode=None,
        custody_authority=None,
        custody_capability=None,
        publish_acceptance=True,
        auditory_transport=None,
        auditory_cochlear=None,
        auditory_stream_settlement=None,
        verified_causal_transaction=None,
    ):
        """Record one exact perception and one explicitly licensed edge."""
        if not isinstance(publish_acceptance, bool):
            raise TypeError("causal acceptance publication flag must be boolean")
        try:
            self._full_field_prediction_observe(
                settlement,
                prediction_transition=prediction_transition,
                action_outcome=action_outcome,
                intake=intake,
                token_sequence=token_sequence,
                language_episode=language_episode,
                custody_authority=custody_authority,
                custody_capability=custody_capability,
                auditory_transport=auditory_transport,
                auditory_cochlear=auditory_cochlear,
                auditory_stream_settlement=auditory_stream_settlement,
                verified_causal_transaction=verified_causal_transaction,
            )
        except RuntimeError as error:
            if str(error) != "prediction_capacity_full":
                raise
            if self._full_field_prediction is not None:
                self._full_field_prediction.stop_context()
            self._prediction_conditioned_intent_receipt = None
            self._prediction_conditioned_binding_id = None
            self._latest_full_field_prediction_observation = {
                "reason": "prediction_capacity_full",
                "schema": "guala.full_field_prediction.engine_observation.v1",
                "settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "status": "capacity_full",
            }
        self._latest_causal_settlement = settlement
        if not already_recorded:
            self._causal_settlement_accepted += 1
        else:
            return
        if publish_acceptance:
            self._publish_causal_experience_accepted(settlement)

    def _publish_causal_experience_accepted(
        self,
        settlement,
        *,
        autonomous_admitted=False,
    ):
        """Publish telemetry only after the owning authority has committed."""
        if not autonomous_admitted:
            self._admit_autonomous_experience_source(
                kind="causal_settlement",
                source_receipt_sha256=settlement.authority_receipt_sha256,
            )
        try:
            self._log_substrate_event(
                "causal_experience_accepted",
                event_id=settlement.event_id,
                structural_fingerprint=settlement.structural_fingerprint,
                observed_senses=[
                    item.sense for item in settlement.interpretations
                    if item.state == "observed"
                ],
            )
        except Exception as error:
            print(
                "[GualaLoom][causal-observer] "
                "causal_experience_accepted telemetry failed after "
                f"authority commit (non-fatal): {error}",
                file=sys.stderr,
                flush=True,
            )

    def _admit_settled_embodiment_thing(
        self,
        outcome_custody,
        world_execution,
    ):
        """Bind one committed physical outcome only at durable THING seams."""
        contact_before = (
            self._thing_partition_authority._contact_object_id(
                world_execution.before
            )
        )
        contact_after = (
            self._thing_partition_authority._contact_object_id(
                world_execution.after
            )
        )
        if contact_before is None and contact_after is not None:
            self._admit_thing_genesis_from_custody(outcome_custody)
        elif (
            contact_before is not None
            and contact_before == contact_after
        ):
            self._admit_thing_continuation_from_custody(
                outcome_custody
            )
        if self._causal_thing_mosaic_owner is not None:
            route = self._causal_thing_mosaic_owner.route(
                outcome_custody.view.causal_settlement
            )
            if route.state == "unique" and len(route.thing_ids) == 1:
                self._admit_tutoring_from_custody(outcome_custody)

    def _settle_executed_embodiment_outcome(
        self, dispatch_result, *, return_outcome=False
    ):
        pending = self._causal_embodiment_execution
        if pending is None:
            return (
                (dispatch_result, None)
                if return_outcome
                else dispatch_result
            )
        if (
            dispatch_result.status != "pending"
            or dispatch_result.phase != "outcome_observation"
            or dispatch_result.request_receipt_sha256
            != pending["request_receipt_sha256"]
            or dispatch_result.execution_receipt_sha256 is None
        ):
            raise RuntimeError(
                "embodiment execution lost its dispatcher authority"
            )
        if self._w1_physical_evidence is None:
            raise RuntimeError("W1 physical outcome authority is unavailable")
        world_execution = pending["world_execution"]
        embodied_outcome = None
        outcome_custody = None
        episode_token = (
            self._w1_physical_evidence.begin_atomic_episode()
        )
        try:
            embodied_outcome = (
                self._w1_physical_evidence.mount_action_outcome(
                    world_execution,
                    commit=False,
                    reserve=True,
                    source_time_start=(
                        pending["consequence_source_time_start"]
                    ),
                )
            )
            if (
                embodied_outcome.causal_settlement is None
                or embodied_outcome.evidence_receipt is None
                or embodied_outcome.state.value != "observed"
            ):
                raise RuntimeError(
                    "W1 action outcome did not produce causal physical evidence"
            )
            self._w1_physical_evidence.verify_mount(embodied_outcome)
            self._complete_live_whole_organism_action_consequence(
                authorization=pending["authorization"],
                settlement=embodied_outcome.causal_settlement,
                action_execution_receipt_sha256=(
                    world_execution.authority_receipt_sha256
                ),
            )
            outcome_custody = self._settled_prediction_custody(
                embodied_outcome,
                world_execution=world_execution,
            )
            from dsf_ai_service.substrate.causal_settlement_dispatcher import (
                authenticate_outcome_observation,
            )
            attestation = authenticate_outcome_observation(
                observer_id="guala.exact.sensory.outcome.v1",
                authority_key=self._causal_outcome_observer_key,
                execution_receipt_sha256=(
                    dispatch_result.execution_receipt_sha256
                ),
                outcome_settlement_receipt_sha256=(
                    embodied_outcome.causal_settlement
                    .authority_receipt_sha256
                ),
                observation_nonce=(
                    "w1-physical:" + embodied_outcome.observation_receipt
                    .authority_receipt_sha256
                ),
            )
            binding = self._causal_action_dispatcher.bind_outcome_observation(
                settlement=embodied_outcome.causal_settlement,
                attestation=attestation,
            )
            completed = self._causal_action_dispatcher.close_bound_outcome(
                binding=binding,
                settlement=embodied_outcome.causal_settlement,
            )
            self._record_causal_perception_without_dispatch(
                embodied_outcome.causal_settlement,
                action_outcome=True,
                custody_authority=outcome_custody.authority,
                custody_capability=outcome_custody.capability,
            )
            self._w1_physical_evidence.commit_prepared_mount(
                embodied_outcome
            )
        except BaseException:
            self._w1_physical_evidence.rollback_atomic_episode(
                episode_token
            )
            self._restore_live_whole_action_spine_snapshot(
                pending["whole_action_snapshot"]
            )
            raise
        try:
            self._admit_settled_embodiment_thing(
                outcome_custody,
                world_execution,
            )
            self._w1_physical_evidence.commit_atomic_episode(
                episode_token
            )
            self._causal_embodiment_execution = None
        except BaseException:
            self._w1_physical_evidence.rollback_atomic_episode(
                episode_token
            )
            self._restore_live_whole_action_spine_snapshot(
                pending["whole_action_snapshot"]
            )
            raise
        return (
            (completed, outcome_custody)
            if return_outcome
            else completed
        )

    @_engine_mutation_entry
    def attempt_autonomous_articulatory_exploration(
        self,
        *,
        state_dir=None,
    ):
        """Select and live one exact physical action without caller choice."""

        raise RuntimeError(
            "legacy owner-scoped articulatory exploration is permanently "
            "retired; native causal action authority is not yet implemented"
        )

        selector = self._articulatory_exploration_selector
        pending = self._pending_articulatory_causal_attempt
        world = self._embodiment_world
        things = self._causal_thing_mosaic_owner
        if any(
            value is None
            for value in (selector, pending, world, things)
        ):
            raise RuntimeError(
                "autonomous articulatory exploration is unavailable"
            )
        with self._causal_cycle_bridge_lock:
            pending_status = pending.status()
            if pending_status["stale_world"]:
                pending.invalidate_stale_world_attempt()
                pending_status = pending.status()
            if (
                pending_status["pending"]
                or pending_status["prepared"]
            ):
                return {
                    "reason": "awaiting_physical_consequence",
                    "schema": (
                        "guala.autonomous_articulatory_exploration."
                        "engine_observation.v1"
                    ),
                    "state": "waiting_consequence",
                }
            observation = world.observation_snapshot()
            held_object_ids = tuple(
                value.object_id
                for value in observation.objects
                if value.held_by_body_id == observation.self_body_id
            )
            matching_thing_ids = tuple(
                mosaic.thing_id
                for mosaic in things.mosaics
                if mosaic.partitions
                and mosaic.partitions[-1].world_revision
                == observation.revision
                and (
                    mosaic.partitions[-1]
                    .world_observation_receipt_sha256
                    == observation.authority_receipt_sha256
                )
            )
            if (
                len(held_object_ids) != 1
                or len(matching_thing_ids) != 1
            ):
                return {
                    "held_object_count": len(held_object_ids),
                    "matching_thing_count": len(
                        matching_thing_ids
                    ),
                    "reason": "no_unique_causally_held_thing",
                    "schema": (
                        "guala.autonomous_articulatory_exploration."
                        "engine_observation.v1"
                    ),
                    "state": "silent",
                }
            selection = selector.select()
            selector.verify_selection(selection)
            if selection.state is ArticulatoryExplorationState.SILENT:
                return {
                    "minimal_program_count": (
                        selection.minimal_program_count
                    ),
                    "reason": selection.reason,
                    "schema": (
                        "guala.autonomous_articulatory_exploration."
                        "engine_observation.v1"
                    ),
                    "state": "silent",
                    "unclosed_program_count": (
                        selection.unclosed_program_count
                    ),
                }
            attempt = self._experience_articulatory_program_attempt(
                selection,
                state_dir=state_dir,
            )
            return {
                "attempt": attempt,
                "physical_action": {
                    "laryngeal_excitation_travel_pcm": (
                        selection.physical_action
                        .laryngeal_excitation_travel_pcm
                    ),
                    "tract_section_area_travel_mm2": list(
                        selection.physical_action
                        .tract_section_area_travel_mm2
                    ),
                },
                "reason": selection.reason,
                "schema": (
                    "guala.autonomous_articulatory_exploration."
                    "engine_observation.v1"
                ),
                "state": "attempted",
                "thing_id": matching_thing_ids[0],
            }

    @_engine_mutation_entry
    def _experience_articulatory_program_attempt(
        self,
        selection,
        *,
        state_dir=None,
    ):
        """Live one selector-custodied action and retain it unresolved."""

        raise RuntimeError(
            "legacy owner-scoped articulatory exploration is permanently "
            "retired; native causal action authority is not yet implemented"
        )

        required = (
            self._articulatory_self_vocal_owner,
            self._w1_self_acoustic_propagation,
            self._fresh_articulatory_self_acoustic_custody,
            self._pending_articulatory_causal_attempt,
            self._causal_thing_mosaic_owner,
            self._embodiment_world,
            self._articulatory_exploration_selector,
        )
        if any(value is None for value in required):
            raise RuntimeError(
                "articulatory attempt transaction is unavailable"
            )
        selector = self._articulatory_exploration_selector
        selector.verify_selection(selection)
        if (
            selection.state is not ArticulatoryExplorationState.SELECTED
            or selection.program is None
            or selection.physical_action is None
        ):
            raise ValueError(
                "articulatory attempt requires one selector-custodied "
                "physical action"
            )
        program_id = selection.program.program_id
        if (
            state_dir is not None
            and not callable(getattr(
                self, "_authoritative_hot_generation_publisher", None
            ))
        ):
            raise RuntimeError(
                "authoritative articulatory attempt durability is "
                "unavailable"
            )
        from fractions import Fraction
        from dsf_ai_service.substrate.embodiment_world import (
            MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        )
        from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
            FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID,
        )

        articulatory = self._articulatory_self_vocal_owner
        acoustic = self._w1_self_acoustic_propagation
        fresh = self._fresh_articulatory_self_acoustic_custody
        pending = self._pending_articulatory_causal_attempt
        things = self._causal_thing_mosaic_owner
        with self._causal_cycle_bridge_lock, self.persistence_transaction():
            before = self._embodiment_world.observation_snapshot()
            if pending.status()["stale_world"]:
                pending.invalidate_stale_world_attempt()
            if pending.pending_attempt is not None:
                raise RuntimeError(
                    "one articulatory causal attempt is already pending"
                )
            prediction_snapshot = (
                self._full_field_prediction.encoded_snapshot()
                if self._full_field_prediction is not None else None
            )
            prior_prediction_intent = (
                self._prediction_conditioned_intent_receipt
            )
            prior_prediction_binding = (
                self._prediction_conditioned_binding_id
            )
            prior_prediction_observation = (
                self._latest_full_field_prediction_observation
            )
            prior_latest_settlement = self._latest_causal_settlement
            prior_accepted = self._causal_settlement_accepted
            prepared_mount = None
            acoustic_undo = None
            thing_continuation = None
            thing_undo = None
            thing_lived_undos = ()
            pending_prepared = None
            pending_undo = None
            try:
                synthesis = articulatory.synthesize(
                    program_id=program_id,
                    source_time_start=Fraction(
                        (
                            before.revision
                            * MAX_VOCAL_SAMPLE_COUNT
                        ),
                        VOCAL_SAMPLE_RATE_HZ,
                    ),
                )
                prepared_emission = (
                    articulatory.prepare_generated_emission(
                        synthesis=synthesis,
                        world_authority=self._embodiment_world,
                        causal_intent_receipt_sha256=(
                            synthesis.receipt
                            .authority_receipt_sha256
                        ),
                    )
                )
                prepared_mount = acoustic.prepare_articulatory(
                    prepared_emission,
                    articulatory_owner=articulatory,
                )
                emission, mount, acoustic_undo = (
                    acoustic.commit_prepared_articulatory(
                        prepared_mount
                    )
                )
                settled_custody = self._settled_self_acoustic_custody(
                    mount,
                    world_execution=emission.execution_receipt,
                )
                thing_continuation = (
                    self
                    ._prepare_ordered_thing_continuation_from_custodies(
                        (settled_custody,)
                    )
                )
                if thing_continuation is None:
                    raise ValueError(
                        "articulatory attempt requires one continuously "
                        "held causal THING"
                    )
                fresh_capability = (
                    settled_custody.authority.issue_child(
                        FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID
                    )
                )
                fresh_receipt = fresh.seal(
                    synthesis=synthesis,
                    emission=emission,
                    acoustic_mount=mount,
                    settled_custody_authority=(
                        settled_custody.authority
                    ),
                    settled_custody_capability=fresh_capability,
                )
                thing_undo = (
                    things
                    .commit_prepared_ordered_custody_continuation(
                        thing_continuation
                    )
                )
                thing_lived_undos = (
                    self._commit_lived_context_partitions(
                        (settled_custody,),
                        thing_continuation.partitions,
                    )
                )
                pending_prepared = pending.prepare_arm(
                    fresh_receipt
                )
                pending_undo = pending.commit_prepared_arm(
                    pending_prepared
                )
                if state_dir is not None:
                    self.save_hot_state(state_dir)
                self._publish_causal_experience_accepted(
                    mount.causal_settlement
                )
            except BaseException:
                if pending_undo is not None:
                    pending.rollback_committed_arm(pending_undo)
                elif pending_prepared is not None:
                    pending.discard_prepared(pending_prepared)
                self._rollback_lived_context_admissions(
                    thing_lived_undos
                )
                if thing_undo is not None:
                    (
                        things
                        .rollback_committed_ordered_custody_continuation(
                            thing_undo
                        )
                    )
                elif thing_continuation is not None:
                    (
                        things
                        .discard_prepared_ordered_custody_continuation(
                            thing_continuation
                        )
                    )
                if acoustic_undo is not None:
                    acoustic.rollback_committed_articulatory(
                        acoustic_undo
                    )
                elif prepared_mount is not None:
                    acoustic.discard_prepared_articulatory(
                        prepared_mount
                    )
                if (
                    prediction_snapshot is not None
                    and self._full_field_prediction is not None
                ):
                    self._full_field_prediction.restore_encoded(
                        prediction_snapshot
                    )
                self._prediction_conditioned_intent_receipt = (
                    prior_prediction_intent
                )
                self._prediction_conditioned_binding_id = (
                    prior_prediction_binding
                )
                self._latest_full_field_prediction_observation = (
                    prior_prediction_observation
                )
                self._latest_causal_settlement = prior_latest_settlement
                self._causal_settlement_accepted = prior_accepted
                raise
            appended = thing_continuation.partitions
            return {
                "causal_settlement_receipt_sha256": (
                    mount.causal_settlement
                    .authority_receipt_sha256
                ),
                "pending_attempt_receipt_sha256": (
                    fresh_receipt.authority_receipt_sha256
                ),
                "program_id": synthesis.program.program_id,
                "schema": (
                    "guala.articulatory_causal_attempt."
                    "engine_observation.v1"
                ),
                "state": "pending_consequence",
                "thing_id": (
                    thing_continuation.staged_mosaic.thing_id
                ),
                "thing_partition_receipt_sha256": (
                    appended[-1].authority_receipt_sha256
                ),
                "world_execution_receipt_sha256": (
                    emission.execution_receipt
                    .authority_receipt_sha256
                ),
                "world_revision_after": (
                    emission.execution_receipt.after.revision
                ),
                "world_revision_before": before.revision,
            }

    @_engine_mutation_entry
    def experience_companion_vocal_pressure(self, pcm_s16le):
        """Admit one bounded block through the canonical W1 episode path."""

        result = self.experience_companion_vocal_episode(pcm_s16le)
        if result["block_count"] != 1:
            raise RuntimeError(
                "single companion pressure produced multiple W1 blocks"
            )
        causal_play = result["causal_play"]
        return {
            "articulatory_consequence_learning": (
                result["articulatory_consequence_learning"]
            ),
            "binaural_auditory_l5_authority_receipt_sha256": (
                result["binaural_l5_authority_receipt_sha256s"][0]
            ),
            "causal_event_id": result["causal_event_ids"][0],
            "causal_play": causal_play,
            "causal_settlement_receipt_sha256": (
                result["causal_settlement_receipt_sha256s"][0]
            ),
            "custody_native_tutoring": (
                result["custody_native_tutoring"]
            ),
            "dispatch_status": (
                causal_play["dispatch_status"]
                if causal_play is not None else "unavailable"
            ),
            "schema": "guala.w1.companion_vocal_experience.v1",
            "sound_substream_count": (
                result["sound_substream_counts"][0]
            ),
            "thing_mosaic_growth": result["thing_mosaic_growth"],
            "world_execution_receipt_sha256": (
                result["world_execution_receipt_sha256s"][0]
            ),
            "world_revision_after": result["world_revision_after"],
            "world_revision_before": result["world_revision_before"],
        }

    @_engine_mutation_entry
    def experience_companion_vocal_episode(
        self,
        pcm_s16le,
        *,
        state_dir=None,
    ):
        """Admit one already-bounded vocal act as a full-field W1 episode.

        The exact byte extent is the physical terminal supplied by the caller.
        It is not inferred from a timeout, transcript, stream id, source tag,
        or chi.  Every W1 block settles atomically, while only the completed
        episode is published outside the transaction.  When ``state_dir`` is
        supplied, the completed physical episode crosses the authoritative hot
        durability barrier before autonomous play may begin.
        """
        authority = self._w1_companion_vocal_experience
        if authority is None or self._embodiment_world is None:
            raise RuntimeError(
                "companion vocal episode authority is unavailable"
            )
        pending_attempt_owner = (
            self._pending_articulatory_causal_attempt
        )
        consequence_owner = self._articulatory_consequence_closure
        if pending_attempt_owner is None or consequence_owner is None:
            raise RuntimeError(
                "articulatory consequence transaction is unavailable"
            )
        if not isinstance(pcm_s16le, bytes):
            raise TypeError("companion vocal episode pressure must be PCM16 bytes")
        if (
            state_dir is not None
            and not callable(getattr(
                self, "_authoritative_hot_generation_publisher", None
            ))
        ):
            raise RuntimeError(
                "authoritative companion experience durability is unavailable"
            )
        with self._causal_cycle_bridge_lock, self.persistence_transaction():
            before = self._embodiment_world.observation_snapshot()
            snapshotter = getattr(
                self,
                "_embodied_reading_transaction_snapshot",
                None,
            )
            restorer = getattr(
                self,
                "_restore_embodied_reading_transaction",
                None,
            )
            if not callable(snapshotter) or not callable(restorer):
                raise RuntimeError(
                    "whole-brain companion transaction custody is unavailable"
                )
            whole_brain_snapshot = snapshotter()
            prior_custody_keys = frozenset(
                self._live_settled_prediction_custodies
            )
            prior_mosaic_versions = {
                value.thing_id: (
                    value.version,
                    len(value.partitions),
                )
                for value in self._causal_thing_mosaic_owner.mosaics
            }
            prepared = None
            committed = False
            commit_undo = None
            pending_attempt = None
            pending_consume_prepared = None
            pending_consume_undo = None
            consequence_prepared = None
            consequence_commit = None
            prediction_custodies = []
            thing_continuation_prepared = None
            thing_continuation_undo = None
            thing_lived_undos = ()
            tutoring_observations = []
            tutoring_progressions = []
            try:
                if pending_attempt_owner.status()["stale_world"]:
                    pending_attempt_owner.invalidate_stale_world_attempt()
                pending_attempt = pending_attempt_owner.pending_attempt
                if pending_attempt is not None:
                    pending_consume_prepared = (
                        pending_attempt_owner.prepare_consume()
                    )
                if pending_attempt is None:
                    prepared = authority.prepare_episode(
                        pcm_s16le=pcm_s16le
                    )
                else:
                    prepared = authority.prepare_episode(
                        pcm_s16le=pcm_s16le,
                        causal_parent_receipt_sha256=(
                            pending_attempt.authority_receipt_sha256
                        ),
                    )
                episode = prepared.episode
                authority.verify_episode(episode)
                if pending_attempt is not None:
                    if len(prepared.prediction_blocks) != 1:
                        raise RuntimeError(
                            "articulatory consequence produced multiple "
                            "physical blocks"
                        )
                    consequence_prepared = consequence_owner.prepare(
                        pending_attempt,
                        prepared.prediction_blocks[0].execution_receipt,
                        companion_episode_intent=(
                            prepared.intent_receipt
                        ),
                    )
                after = self._embodiment_world.observation_snapshot()
                for block in prepared.prediction_blocks:
                    settled_custody = self._settled_prediction_custody(
                        block.physical_mount,
                        world_execution=block.execution_receipt,
                    )
                    prediction_custodies.append(settled_custody)
                thing_continuation_prepared = (
                    self
                    ._prepare_ordered_thing_continuation_from_custodies(
                        tuple(prediction_custodies)
                    )
                )
                commit_undo = authority.commit_episode(prepared)
                committed = True
                if thing_continuation_prepared is not None:
                    thing_continuation_undo = (
                        self._causal_thing_mosaic_owner
                        .commit_prepared_ordered_custody_continuation(
                            thing_continuation_prepared
                        )
                    )
                    thing_lived_undos = (
                        self._commit_lived_context_partitions(
                            tuple(prediction_custodies),
                            thing_continuation_prepared.partitions,
                        )
                    )
                for block, settled_custody in zip(
                    prepared.prediction_blocks,
                    prediction_custodies,
                    strict=True,
                ):
                    self._accept_causal_settlement(
                        block.causal_settlement,
                        custody_authority=settled_custody.authority,
                        custody_capability=settled_custody.capability,
                    )
                if consequence_prepared is not None:
                    consequence_commit = (
                        consequence_owner.commit_prepared(
                            consequence_prepared
                        )
                    )
                for settled_custody in prediction_custodies:
                    route = self._causal_thing_mosaic_owner.route(
                        settled_custody.view.causal_settlement
                    )
                    if (
                        route.state != "unique"
                        or len(route.thing_ids) != 1
                    ):
                        continue
                    (
                        tutoring_observation,
                        tutoring_progression,
                    ) = self._admit_tutoring_from_custody(
                        settled_custody,
                        return_committed_progression=True,
                    )
                    tutoring_observations.append(
                        tutoring_observation
                    )
                    tutoring_progressions.append(
                        tutoring_progression
                    )
                if pending_consume_prepared is not None:
                    if consequence_commit is None:
                        raise RuntimeError(
                            "pending articulatory consequence did not close"
                        )
                    pending_consume_undo = (
                        pending_attempt_owner.commit_prepared_consume(
                            pending_consume_prepared,
                            binding=consequence_commit.binding,
                        )
                    )
                if state_dir is not None:
                    self.save_hot_state(state_dir)
                for block in prepared.prediction_blocks:
                    self._publish_causal_experience_accepted(
                        block.causal_settlement
                    )
            except BaseException:
                for tutoring_progression in reversed(
                    tutoring_progressions
                ):
                    (
                        self._custody_native_tutoring_curriculum
                        .rollback_committed_progression(
                            tutoring_progression
                        )
                    )
                if consequence_commit is not None:
                    consequence_owner.rollback_committed(
                        consequence_commit.undo
                    )
                elif consequence_prepared is not None:
                    consequence_owner.discard_prepared(
                        consequence_prepared
                    )
                self._rollback_lived_context_admissions(
                    thing_lived_undos
                )
                if thing_continuation_undo is not None:
                    (
                        self._causal_thing_mosaic_owner
                        .rollback_committed_ordered_custody_continuation(
                            thing_continuation_undo
                        )
                    )
                elif thing_continuation_prepared is not None:
                    (
                        self._causal_thing_mosaic_owner
                        .discard_prepared_ordered_custody_continuation(
                            thing_continuation_prepared
                        )
                    )
                if commit_undo is not None and committed:
                    authority.rollback_committed_episode(commit_undo)
                elif prepared is not None and not committed:
                    try:
                        authority.discard_episode(prepared)
                    except ValueError:
                        pass
                if pending_consume_undo is not None:
                    pending_attempt_owner.rollback_committed_consume(
                        pending_consume_undo
                    )
                elif pending_consume_prepared is not None:
                    pending_attempt_owner.discard_prepared(
                        pending_consume_prepared
                    )
                restorer(whole_brain_snapshot)
                for source_key in tuple(
                    self._live_settled_prediction_custodies
                ):
                    if source_key not in prior_custody_keys:
                        del self._live_settled_prediction_custodies[
                            source_key
                        ]
                raise
            changed_mosaics = []
            for current_mosaic in (
                self._causal_thing_mosaic_owner.mosaics
            ):
                prior = prior_mosaic_versions.get(
                    current_mosaic.thing_id
                )
                prior_version = prior[0] if prior is not None else 0
                prior_partition_count = (
                    prior[1] if prior is not None else 0
                )
                if (
                    current_mosaic.version > prior_version
                    and len(current_mosaic.partitions)
                    > prior_partition_count
                ):
                    changed_mosaics.append((
                        current_mosaic,
                        prior_version,
                        current_mosaic.partitions[
                            prior_partition_count:
                        ],
                    ))
            if len(changed_mosaics) > 1:
                raise RuntimeError(
                    "one companion episode changed multiple physical THINGs"
                )
            if not changed_mosaics:
                thing_mosaic_growth = {
                    "appended_partition_count": 0,
                    "reason": "no_single_contacted_thing",
                    "schema": (
                        "guala.causal_thing."
                        "companion_vocal_growth.v1"
                    ),
                    "state": "not_applicable",
                }
            else:
                (
                    staged_mosaic,
                    prior_version,
                    appended_partitions,
                ) = changed_mosaics[0]
                thing_mosaic_growth = {
                    "appended_partition_count": len(
                        appended_partitions
                    ),
                    "causal_settlement_receipt_sha256s": [
                        value.settlement_receipt_sha256
                        for value in appended_partitions
                    ],
                    "partition_authority_receipt_sha256s": [
                        value.authority_receipt_sha256
                        for value in appended_partitions
                    ],
                    "prior_version": prior_version,
                    "schema": (
                        "guala.causal_thing."
                        "companion_vocal_growth.v1"
                    ),
                    "state": "expanded",
                    "thing_id": staged_mosaic.thing_id,
                    "version": staged_mosaic.version,
                }
            if not tutoring_observations:
                tutoring_progression_observation = {
                    "admissions": [],
                    "reason": "no_single_contacted_thing",
                    "resolved_active_opportunities": 0,
                    "schema": (
                        "guala.custody_native_tutoring."
                        "companion_progression.v1"
                    ),
                    "scheduled": None,
                    "state": "not_applicable",
                }
            else:
                tutoring_progression_observation = {
                    "admissions": tutoring_observations,
                    "resolved_active_opportunities": sum(
                        1
                        for value in tutoring_observations
                        if value["resolved_active_opportunity"]
                    ),
                    "schema": (
                        "guala.custody_native_tutoring."
                        "companion_progression.v1"
                    ),
                    "scheduled": tutoring_observations[-1][
                        "scheduled"
                    ],
                    "state": "admitted",
                }
            if consequence_commit is None:
                consequence_learning = {
                    "schema": (
                        "guala.articulatory_consequence."
                        "learning_observation.v1"
                    ),
                    "state": "not_applicable",
                    "reason": "no_pending_articulatory_attempt",
                }
            else:
                consequence_learning = {
                    "binding_authority_receipt_sha256": (
                        consequence_commit.binding
                        .authority_receipt_sha256
                    ),
                    "program_id": (
                        consequence_commit.binding.program_id
                    ),
                    "schema": (
                        "guala.articulatory_consequence."
                        "learning_observation.v1"
                    ),
                    "state": "closed",
                    "thing_id": (
                        consequence_commit.binding.thing_id
                    ),
                }
            causal_play = self._run_causal_play_episode(
                trigger="external_world_change",
                state_dir=state_dir,
                committed_custody=prediction_custodies[-1],
            )
            return {
                "block_count": len(episode.blocks),
                "binaural_l5_authority_receipt_sha256s": [
                    block.binaural_l5.authority_receipt_sha256
                    for block in episode.blocks
                ],
                "causal_event_ids": [
                    block.causal_settlement.event_id
                    for block in prepared.prediction_blocks
                ],
                "causal_settlement_receipt_sha256s": [
                    block.causal_settlement.authority_receipt_sha256
                    for block in prepared.prediction_blocks
                ],
                "episode_authority_receipt_sha256": (
                    episode.authority_receipt_sha256
                ),
                "episode_id": episode.episode_id,
                "custody_native_tutoring": (
                    tutoring_progression_observation
                ),
                "articulatory_consequence_learning": (
                    consequence_learning
                ),
                "causal_play": causal_play,
                "schema": "guala.w1.companion_vocal_episode.v1",
                "sound_substream_counts": [
                    len(next(
                        interpretation.substreams
                        for interpretation
                        in block.causal_settlement.interpretations
                        if interpretation.sense == "sound"
                    ))
                    for block in prepared.prediction_blocks
                ],
                "thing_mosaic_growth": thing_mosaic_growth,
                "total_sample_count": episode.total_sample_count,
                "world_execution_receipt_sha256s": [
                    block.execution_receipt.authority_receipt_sha256
                    for block in prepared.prediction_blocks
                ],
                "world_revision_after": (
                    self._embodiment_world.observation_snapshot().revision
                ),
                "world_revision_before": before.revision,
            }

    def _run_causal_play_episode(
        self,
        *,
        trigger,
        state_dir=None,
        committed_custody=None,
    ):
        """Run one bounded exact W1 causal chain without scalar scheduling.

        A committed external W1 event may supply its exact settled custody.
        That occurrence remains the causal trigger; it is never remounted or
        re-admitted.
        """

        required = (
            self._embodiment_world,
            self._w1_physical_evidence,
            self._embodied_action_teaching,
            self._causal_deliberation,
            self._causal_action_dispatcher,
        )
        if any(item is None for item in required):
            return None
        with self._causal_cycle_bridge_lock:
            if self._causal_action_dispatcher.status()["active"]:
                return None
            if (
                committed_custody is not None
                and not isinstance(
                    committed_custody,
                    _SettledPredictionCustody,
                )
            ):
                raise TypeError(
                    "committed W1 deliberation custody is not typed"
                )
            if committed_custody is None:
                before = self._embodiment_world.observation_snapshot()
                embodied = (
                    self._w1_physical_evidence
                    .mount_current_observation(commit=True)
                )
                if (
                    embodied.causal_settlement is None
                    or embodied.observation_receipt is None
                ):
                    raise RuntimeError(
                        "W1 current physical field did not settle"
                )
                self._w1_physical_evidence.verify_mount(embodied)
                trigger_custody = self._settled_prediction_custody(
                    embodied,
                    world_observation=before,
                )
                self._record_causal_perception_without_dispatch(
                    embodied.causal_settlement,
                    custody_authority=trigger_custody.authority,
                    custody_capability=trigger_custody.capability,
                )
            else:
                verified_view = committed_custody.authority.open_child(
                    committed_custody.capability
                )
                if (
                    verified_view.source_occurrence_id
                    != committed_custody.view.source_occurrence_id
                    or verified_view.causal_settlement
                    is not committed_custody.view.causal_settlement
                    or verified_view.world_observation
                    is not committed_custody.view.world_observation
                    or verified_view.world_execution
                    is not committed_custody.view.world_execution
                    or verified_view.physical_evidence_receipt
                    is not committed_custody.view
                    .physical_evidence_receipt
                    or self._embodiment_world.observation_snapshot()
                    .authority_receipt_sha256
                    != verified_view.world_observation
                    .authority_receipt_sha256
                ):
                    raise RuntimeError(
                        "committed W1 event lost physical authority"
                    )
                trigger_custody = committed_custody
                before = verified_view.world_observation
            trigger_settlement = trigger_custody.view.causal_settlement
            trigger_observation_receipt = (
                trigger_custody.view.physical_evidence_receipt
            )
            current_settlement = trigger_settlement
            current_observation_receipt = trigger_observation_receipt
            admitted = (
                self._embodied_action_teaching
                .verified_guided_relation_evidence()
            )
            turn = self._causal_deliberation.current_turn()
            if turn is None:
                turn = self._causal_deliberation.start(
                    trigger_settlement,
                    admitted_evidence=admitted,
                )
            else:
                active = self._causal_deliberation.active_episode_record()
                if (
                    active is None
                    or active["current"]["structural_fingerprint"]
                    != trigger_settlement.structural_fingerprint
                ):
                    evidence = _hashlib.sha256(
                        (
                            trigger_settlement
                            .authority_receipt_sha256
                            + ":restore-evidence-mismatch"
                        ).encode("ascii")
                    ).hexdigest()
                    turn = self._causal_deliberation.terminate_active(
                        reason="restore_evidence_mismatch",
                        evidence_receipt_sha256=evidence,
                    )

            steps = []
            last_dispatch = None
            while turn.status == "action":
                if len(steps) >= 65:
                    raise RuntimeError(
                        "causal play exceeded deliberation visit capacity"
                    )
                if (
                    turn.action.kind != "embodiment_port"
                    or turn.action.port_id != self._embodiment_world.port_id
                ):
                    evidence = _hashlib.sha256(
                        (
                            turn.action_receipt_sha256
                            + ":non-self-action"
                        ).encode("ascii")
                    ).hexdigest()
                    turn = self._causal_deliberation.terminate_active(
                        reason="dispatch_identity_mismatch",
                        evidence_receipt_sha256=evidence,
                    )
                    break
                cycle_snapshot = self._causal_action_cycle.encoded_snapshot()
                dispatcher_snapshot = (
                    self._causal_action_dispatcher.encoded_snapshot()
                )
                world_snapshot = self._embodiment_world.encoded_snapshot()
                prediction_snapshot = (
                    self._full_field_prediction.encoded_snapshot()
                    if self._full_field_prediction is not None
                    else None
                )
                prediction_observation = (
                    self._latest_full_field_prediction_observation
                )
                try:
                    selection = self._causal_action_cycle.select_expected(
                        current_settlement,
                        binding_id=turn.binding_id,
                        action_receipt_sha256=(
                            turn.action_receipt_sha256
                        ),
                    )
                    if selection.status != "committed":
                        raise ValueError(
                            "deliberation action was not causally selectable"
                        )
                    self._condition_full_field_prediction_on_action(
                        selection.intent
                    )
                    dispatch = self._causal_action_dispatcher \
                        .dispatch_expected(
                            current_settlement,
                            binding_id=turn.binding_id,
                            action_receipt_sha256=(
                                turn.action_receipt_sha256
                            ),
                        )
                except Exception as error:
                    dispatcher_active = (
                        self._causal_action_dispatcher.status()["active"]
                    )
                    if not dispatcher_active:
                        self._causal_action_cycle.restore_encoded(
                            cycle_snapshot
                        )
                        if (
                            prediction_snapshot is not None
                            and self._full_field_prediction is not None
                        ):
                            self._full_field_prediction.restore_encoded(
                                prediction_snapshot
                            )
                        self._prediction_conditioned_intent_receipt = None
                        self._prediction_conditioned_binding_id = None
                        self._latest_full_field_prediction_observation = (
                            prediction_observation
                        )
                    if dispatcher_active or not isinstance(error, ValueError):
                        raise
                    evidence = _hashlib.sha256(
                        (
                            turn.binding_id
                            + turn.action_receipt_sha256
                            + ":dispatch-identity-mismatch"
                        ).encode("ascii")
                    ).hexdigest()
                    turn = self._causal_deliberation.terminate_active(
                        reason="dispatch_identity_mismatch",
                        evidence_receipt_sha256=evidence,
                    )
                    break
                last_dispatch = dispatch
                if (
                    dispatch.binding_id != turn.binding_id
                    or dispatch.action_receipt_sha256
                    != turn.action_receipt_sha256
                ):
                    evidence = (
                        dispatch.request_receipt_sha256
                        or current_settlement.authority_receipt_sha256
                    )
                    turn = self._causal_deliberation.terminate_active(
                        reason="dispatch_identity_mismatch",
                        evidence_receipt_sha256=evidence,
                    )
                    break
                if dispatch.status == "rejected":
                    self._cancel_full_field_prediction_action()
                    turn = self._causal_deliberation.terminate_active(
                        reason="dispatcher_rejected",
                        evidence_receipt_sha256=(
                            dispatch
                            .executor_acknowledgement_receipt_sha256
                        ),
                    )
                    break
                if dispatch.status != "pending":
                    evidence = (
                        dispatch.request_receipt_sha256
                        or current_settlement.authority_receipt_sha256
                    )
                    turn = self._causal_deliberation.terminate_active(
                        reason="dispatch_identity_mismatch",
                        evidence_receipt_sha256=evidence,
                    )
                    break
                try:
                    completed, actual = (
                        self._settle_executed_embodiment_outcome(
                            dispatch,
                            return_outcome=True,
                        )
                    )
                except Exception:
                    self._embodiment_world.restore_encoded(world_snapshot)
                    self._causal_action_cycle.restore_encoded(cycle_snapshot)
                    self._causal_action_dispatcher.restore_encoded(
                        dispatcher_snapshot
                    )
                    if (
                        prediction_snapshot is not None
                        and self._full_field_prediction is not None
                    ):
                        self._full_field_prediction.restore_encoded(
                            prediction_snapshot
                        )
                    self._prediction_conditioned_intent_receipt = None
                    self._prediction_conditioned_binding_id = None
                    self._latest_full_field_prediction_observation = (
                        prediction_observation
                    )
                    self._causal_embodiment_execution = None
                    raise
                if (
                    actual is None
                    or completed.status != "completed"
                    or completed.binding_id != turn.binding_id
                    or completed.action_receipt_sha256
                    != turn.action_receipt_sha256
                ):
                    evidence = (
                        completed.request_receipt_sha256
                        or current_settlement.authority_receipt_sha256
                    )
                    turn = self._causal_deliberation.terminate_active(
                        reason="dispatch_identity_mismatch",
                        evidence_receipt_sha256=evidence,
                    )
                    break
                steps.append({
                    "action_receipt_sha256": turn.action_receipt_sha256,
                    "binding_id": turn.binding_id,
                    "closure_receipt_sha256": (
                        completed.closure_feedback_receipt_sha256
                    ),
                    "outcome_settlement_receipt_sha256": (
                        actual.view.causal_settlement
                        .authority_receipt_sha256
                    ),
                })
                current_settlement = actual.view.causal_settlement
                current_observation_receipt = (
                    actual.view.physical_evidence_receipt
                )
                admitted = (
                    self._embodied_action_teaching
                    .verified_guided_relation_evidence()
                )
                turn = self._causal_deliberation.advance(
                    actual.view.causal_settlement,
                    action_outcome=actual.view.causal_settlement,
                    admitted_evidence=admitted,
                )
                last_dispatch = completed
                if (
                    state_dir is not None
                    and callable(getattr(
                        self,
                        "_authoritative_hot_generation_publisher",
                        None,
                    ))
                ):
                    self.save_hot_state(state_dir)

            after = self._embodiment_world.observation_snapshot()
            stop_reason = turn.stop_reason
            dispatch_status = (
                last_dispatch.status
                if last_dispatch is not None
                else (
                    "unknown"
                    if stop_reason == "action_unknown"
                    else "ambiguous"
                    if stop_reason == "action_ambiguous"
                    else "stopped"
                )
            )
            record = {
                "causal_event_id": (
                    trigger_settlement.event_id
                ),
                "causal_settlement_receipt_sha256": (
                    trigger_settlement.authority_receipt_sha256
                ),
                "dispatch_phase": (
                    last_dispatch.phase
                    if last_dispatch is not None
                    else "selection"
                ),
                "dispatch_reason": (
                    stop_reason
                    or (
                        last_dispatch.reason
                        if last_dispatch is not None
                        else "deliberation_stopped"
                    )
                ),
                "dispatch_status": dispatch_status,
                "embodiment_rejection_reason": (
                    self._causal_embodiment_rejection_reason["reason"]
                    if (
                        dispatch_status == "rejected"
                        and isinstance(
                            self._causal_embodiment_rejection_reason,
                            dict,
                        )
                    )
                    else None
                ),
                "episode_id": turn.episode_id,
                "outcome_observation_receipt_sha256": (
                    current_observation_receipt.authority_receipt_sha256
                ),
                "schema": PLAY_CAUSAL_ADMISSION_SCHEMA,
                "steps": steps,
                "trigger": trigger,
                "world_observation_receipt_sha256": (
                    before.authority_receipt_sha256
                ),
                "world_revision_after": after.revision,
                "world_revision_before": before.revision,
            }
            self._causal_play_observation = record
            return record

    def _prepare_continuous_auditory_causal_authority(
        self,
        *,
        settlement,
        verified_causal_transaction,
    ):
        """Mount one complete live auditory graph inside its causal callback."""

        built = self._auditory_transaction_build_in_commit
        if built is None:
            return None, None, None
        event_boundary = self._latest_auditory_recognition_boundary
        if event_boundary not in {"ambient", "utterance"}:
            raise RuntimeError(
                "continuous auditory transaction has an invalid event boundary"
            )
        auditory_l5 = self._auditory_l5_owner.settle(
            built,
            event_boundary=event_boundary,
        )
        self._latest_auditory_l5_experience = auditory_l5
        transport = self._auditory_prediction_transport_in_commit
        pcm_s16le = self._auditory_prediction_pcm_in_commit
        if transport is None and pcm_s16le is None:
            return None, None, None
        if transport is None or pcm_s16le is None or auditory_l5 is None:
            raise RuntimeError(
                "continuous auditory transaction lost its live authority"
            )
        cochlear = self._latest_auditory_continuation_receipt
        capture = self._latest_auditory_full_field_capture
        if (
            cochlear is None
            or capture is None
            or auditory_l5.assembly_id != settlement.assembly_id
            or cochlear.transport_receipt_sha256
            != transport.receipt_sha256
        ):
            raise RuntimeError(
                "continuous auditory transaction crossed its causal boundary"
            )
        from dsf_ai_service.substrate.auditory_stream_settlement import (
            prepare_verified_auditory_transaction_graph,
        )
        verified_graph = prepare_verified_auditory_transaction_graph(
            built=built,
            auditory_l5_owner=self._auditory_l5_owner,
            causal_owner=self._causal_experience_owner,
            transport=transport,
            cochlear=cochlear,
            auditory_l5=auditory_l5,
            causal_settlement=settlement,
        )
        from dsf_ai_service.substrate.auditory_incremental_terminal import (
            AuditoryIncrementalTerminalOwner,
        )
        capability = (
            AuditoryIncrementalTerminalOwner.prepare_verified_settlement(
                pcm_s16le=pcm_s16le,
                capture=capture,
                transport=transport,
                cochlear=cochlear,
                auditory_l5=auditory_l5,
                causal_settlement=settlement,
                verified_transaction=verified_graph,
                verified_causal_transaction=(
                    verified_causal_transaction
                ),
            )
        )
        joint = capability.joint_settlement
        receipt_sha256 = transport.receipt_sha256
        with self._auditory_transaction_lock:
            self._auditory_l5_by_assembly[settlement.assembly_id] = (
                auditory_l5
            )
            self._auditory_prediction_joint_by_transport[receipt_sha256] = (
                joint
            )
            self._auditory_verified_capability_by_transport[receipt_sha256] = (
                capability
            )
            self._auditory_l5_by_assembly.move_to_end(
                settlement.assembly_id
            )
            self._auditory_prediction_joint_by_transport.move_to_end(
                receipt_sha256
            )
            self._auditory_verified_capability_by_transport.move_to_end(
                receipt_sha256
            )
            while (
                len(self._auditory_l5_by_assembly)
                > self._auditory_transaction_capacity
            ):
                self._auditory_l5_by_assembly.popitem(last=False)
            while (
                len(self._auditory_prediction_joint_by_transport)
                > self._auditory_transaction_capacity
            ):
                expired_receipt, _joint = (
                    self._auditory_prediction_joint_by_transport.popitem(
                        last=False
                    )
                )
                self._auditory_verified_capability_by_transport.pop(
                    expired_receipt,
                    None,
                )
        return transport, cochlear, joint

    def _continuous_auditory_causal_transaction(
        self,
        *,
        transport,
        settlement,
    ):
        """Return exact request-local causal authority for one live chunk."""
        if transport is None:
            return None
        with self._auditory_transaction_lock:
            authority = (
                self._auditory_verified_capability_by_transport.get(
                    transport.receipt_sha256
                )
            )
            if authority is None:
                return None
            authority.verify_linkage(
                pcm_s16le=authority.pcm_s16le,
                capture=authority.capture,
                auditory_l5=authority.auditory_l5,
                transport=transport,
                cochlear=authority.cochlear,
                causal_settlement=settlement,
                joint_settlement=authority.joint_settlement,
            )
            verified = authority.verified_causal_transaction
            if verified is None:
                return None
            verified.verify_linkage(settlement)
            return verified

    def durably_experience_embodied_action(
        self,
        *,
        tutor_id,
        nonce,
        port_id,
        command_payload,
        state_dir,
    ):
        """Refuse the retired owner-scoped action path before mutation."""
        del tutor_id, nonce, port_id, command_payload, state_dir
        raise RuntimeError(
            "native embodied action settlement is not yet mounted; "
            "the retired owner-scoped action path cannot be resurrected"
        )

    @_engine_mutation_entry
    def experience_oral_material_contact(
        self,
        *,
        tutor_id,
        nonce,
        object_id,
        duration_microseconds,
        state_dir=None,
    ):
        """Retain oral consequence as an existing held THING continuation."""
        if (
            self._embodiment_world is None
            or self._w1_physical_evidence is None
            or self._causal_thing_mosaic_owner is None
            or self._causal_thing_lived_context is None
        ):
            raise RuntimeError(
                "oral material lived-experience authority is unavailable"
            )
        if (
            state_dir is not None
            and not callable(getattr(
                self, "_authoritative_hot_generation_publisher", None
            ))
        ):
            raise RuntimeError(
                "authoritative oral material durability is unavailable"
            )
        if tutor_id not in ("joe", "wc"):
            raise PermissionError("oral contact tutor is not authorized")
        if (
            not isinstance(nonce, str)
            or nonce.strip() != nonce
            or len(nonce) < 16
            or len(nonce.encode("utf-8")) > 256
        ):
            raise ValueError("oral contact nonce is not bounded and canonical")
        observation = self._embodiment_world.observation_snapshot()
        body = next(
            value
            for value in observation.bodies
            if value.body_id == observation.self_body_id
        )
        if body.held_object_id != object_id:
            raise ValueError(
                "oral contact requires the exact object currently held"
            )
        from dsf_ai_service.substrate.embodiment_world import (
            OralContactCommand,
            encode_command,
        )
        command_payload = encode_command(OralContactCommand(
            object_id=object_id,
            duration_microseconds=duration_microseconds,
        ))
        port_id = next(
            port.port_id
            for port in self._embodiment_world.actor_ports
            if port.actor_body_id == observation.self_body_id
        )
        intent = _hashlib.sha256(
            self._canonical_persistence_bytes({
                "nonce": nonce,
                "port_id": port_id,
                "schema": "guala.embodied_oral_contact.intent.v3",
                "tutor_id": tutor_id,
            })
        ).hexdigest()
        retained = (
            self._embodiment_world
            .applied_execution_for_causal_intent(intent)
        )
        if retained is not None:
            if retained.command_sha256 != _hashlib.sha256(
                command_payload
            ).hexdigest():
                raise ValueError(
                    "oral contact nonce replay changed physical command"
                )
            matches = tuple(
                (mosaic, partition)
                for mosaic in self._causal_thing_mosaic_owner.mosaics
                for partition in mosaic.partitions
                if partition.execution_receipt_sha256
                == retained.authority_receipt_sha256
            )
            if len(matches) != 1:
                raise RuntimeError(
                    "retained oral execution lacks one durable THING "
                    "continuation"
                )
            mosaic, partition = matches[0]
            retained_version = mosaic.partitions.index(partition)
            return {
                "action_receipt_sha256": (
                    retained.authority_receipt_sha256
                ),
                "after_world_observation_receipt_sha256": (
                    retained.after.authority_receipt_sha256
                ),
                "before_world_observation_receipt_sha256": (
                    retained.before.authority_receipt_sha256
                ),
                "consequence_settlement_receipt_sha256": (
                    partition.settlement_receipt_sha256
                ),
                "full_field_root_commitments": [
                    {
                        "physical_value_sha256": (
                            value.physical_value_sha256
                        ),
                        "sense": value.sense,
                        "topology_index": value.topology_index,
                    }
                    for value in partition.full_field_roots
                ],
                "idempotent_replay": True,
                "object_id": object_id,
                "persistent_learned_state_created": True,
                "reason": (
                    "retained authenticated oral THING continuation"
                ),
                "schema": "guala.embodied_oral_contact.result.v3",
                "settlement_state": "consequence_learned",
                "thing_id": mosaic.thing_id,
                "thing_partition_receipt_sha256": (
                    partition.authority_receipt_sha256
                ),
                "thing_version": retained_version,
                "world_observation_receipt_sha256": (
                    retained.after.authority_receipt_sha256
                ),
            }

        persistence = (
            self.persistence_transaction()
            if state_dir is not None
            else contextlib.nullcontext()
        )
        with persistence, self._causal_cycle_bridge_lock:
            prior_world = self._embodiment_world.encoded_snapshot()
            whole_snapshot = self._live_whole_action_spine_snapshot()
            prediction_snapshot = (
                self._full_field_prediction.encoded_snapshot()
                if self._full_field_prediction is not None else None
            )
            prior_prediction_intent = (
                self._prediction_conditioned_intent_receipt
            )
            prior_prediction_binding = (
                self._prediction_conditioned_binding_id
            )
            prior_prediction_observation = (
                self._latest_full_field_prediction_observation
            )
            prior_latest_settlement = self._latest_causal_settlement
            prior_accepted = self._causal_settlement_accepted
            epoch = self._w1_physical_evidence.begin_atomic_episode()
            committed = None
            thing_prepared = None
            thing_undo = None
            lived_undos = ()
            unresolved_reason = None
            try:
                pre = self._w1_physical_evidence.mount_current_observation(
                    commit=True
                )
                if pre.causal_settlement is None:
                    raise RuntimeError(
                        "oral contact authorization field did not settle"
                    )
                authorization = (
                    self._begin_live_whole_organism_action_authorization(
                        settlement=pre.causal_settlement,
                        action_authority_receipt_sha256=intent,
                    )
                )
                action = self._embodiment_world.execute_port_command(
                    port_id=port_id,
                    command_payload=command_payload,
                    causal_intent_receipt_sha256=intent,
                    expected_revision=observation.revision,
                )
                if action.disposition != "applied":
                    raise RuntimeError(
                        "physical oral contact was not applied: "
                        + action.reason
                    )
                post = self._w1_physical_evidence.mount_action_outcome(
                    action,
                    commit=True,
                    source_time_start=(
                        pre.causal_settlement.source_time_end
                    ),
                )
                if (
                    post.causal_settlement is None
                    or post.evidence_receipt is None
                ):
                    raise RuntimeError(
                        "oral contact consequence field did not settle"
                    )
                self._w1_physical_evidence.verify_mount(pre)
                self._w1_physical_evidence.verify_mount(post)
                self._complete_live_whole_organism_action_consequence(
                    authorization=authorization,
                    settlement=post.causal_settlement,
                    action_execution_receipt_sha256=(
                        action.authority_receipt_sha256
                    ),
                )
                pre_custody = self._settled_prediction_custody(
                    pre,
                    world_observation=observation,
                )
                post_custody = self._settled_prediction_custody(
                    post,
                    world_execution=action,
                )
                thing_prepared = (
                    self
                    ._prepare_ordered_thing_continuation_from_custodies(
                        (post_custody,)
                    )
                )
                if thing_prepared is None:
                    unresolved_reason = (
                        "no_prior_authenticated_held_thing"
                    )
                    raise RuntimeError(unresolved_reason)
                self._record_causal_perception_without_dispatch(
                    pre.causal_settlement,
                    custody_authority=pre_custody.authority,
                    custody_capability=pre_custody.capability,
                )
                self._record_causal_perception_without_dispatch(
                    post.causal_settlement,
                    action_outcome=True,
                    custody_authority=post_custody.authority,
                    custody_capability=post_custody.capability,
                )
                thing_undo = (
                    self._causal_thing_mosaic_owner
                    .commit_prepared_ordered_custody_continuation(
                        thing_prepared
                    )
                )
                lived_undos = self._commit_lived_context_partitions(
                    (post_custody,),
                    thing_prepared.partitions,
                )
                committed = (
                    self._w1_physical_evidence
                    .commit_atomic_episode(epoch)
                )
                partition = thing_prepared.partitions[-1]
                mosaic = thing_prepared.staged_mosaic
                result = {
                    "action_receipt_sha256": (
                        action.authority_receipt_sha256
                    ),
                    "after_world_observation_receipt_sha256": (
                        action.after.authority_receipt_sha256
                    ),
                    "before_world_observation_receipt_sha256": (
                        action.before.authority_receipt_sha256
                    ),
                    "consequence_settlement_receipt_sha256": (
                        post.causal_settlement.authority_receipt_sha256
                    ),
                    "full_field_root_commitments": [
                        {
                            "physical_value_sha256": (
                                value.physical_value_sha256
                            ),
                            "sense": value.sense,
                            "topology_index": value.topology_index,
                        }
                        for value in partition.full_field_roots
                    ],
                    "idempotent_replay": False,
                    "object_id": object_id,
                    "persistent_learned_state_created": True,
                    "reason": (
                        "authenticated oral consequence continued one "
                        "held THING"
                    ),
                    "schema": "guala.embodied_oral_contact.result.v3",
                    "settlement_state": "consequence_learned",
                    "thing_id": mosaic.thing_id,
                    "thing_partition_receipt_sha256": (
                        partition.authority_receipt_sha256
                    ),
                    "thing_version": mosaic.version,
                    "world_observation_receipt_sha256": (
                        action.after.authority_receipt_sha256
                    ),
                }
                if state_dir is not None:
                    self.save_hot_state(state_dir)
                return result
            except BaseException:
                if committed is None:
                    self._w1_physical_evidence.rollback_atomic_episode(
                        epoch
                    )
                else:
                    (
                        self._w1_physical_evidence
                        .rollback_committed_atomic_episode(committed)
                    )
                self._rollback_lived_context_admissions(lived_undos)
                if thing_undo is not None:
                    (
                        self._causal_thing_mosaic_owner
                        .rollback_committed_ordered_custody_continuation(
                            thing_undo
                        )
                    )
                elif thing_prepared is not None:
                    (
                        self._causal_thing_mosaic_owner
                        .discard_prepared_ordered_custody_continuation(
                            thing_prepared
                        )
                    )
                self._embodiment_world.restore_encoded(prior_world)
                self._restore_live_whole_action_spine_snapshot(
                    whole_snapshot
                )
                if (
                    prediction_snapshot is not None
                    and self._full_field_prediction is not None
                ):
                    self._full_field_prediction.restore_encoded(
                        prediction_snapshot
                    )
                self._prediction_conditioned_intent_receipt = (
                    prior_prediction_intent
                )
                self._prediction_conditioned_binding_id = (
                    prior_prediction_binding
                )
                self._latest_full_field_prediction_observation = (
                    prior_prediction_observation
                )
                self._latest_causal_settlement = prior_latest_settlement
                self._causal_settlement_accepted = prior_accepted
                if unresolved_reason is not None:
                    return {
                        "action_receipt_sha256": None,
                        "after_world_observation_receipt_sha256": (
                            observation.authority_receipt_sha256
                        ),
                        "before_world_observation_receipt_sha256": (
                            observation.authority_receipt_sha256
                        ),
                        "consequence_settlement_receipt_sha256": None,
                        "full_field_root_commitments": [],
                        "idempotent_replay": False,
                        "object_id": object_id,
                        "persistent_learned_state_created": False,
                        "reason": unresolved_reason,
                        "schema": (
                            "guala.embodied_oral_contact.result.v3"
                        ),
                        "settlement_state": "unresolved",
                        "thing_id": None,
                        "thing_partition_receipt_sha256": None,
                        "thing_version": None,
                        "world_observation_receipt_sha256": (
                            observation.authority_receipt_sha256
                        ),
                    }
                raise

    @_engine_mutation_entry
    def durably_review_causal_action_binding(
        self,
        *,
        binding_id,
        decision,
        source,
        nonce,
        state_dir,
    ):
        """Publish explicit teacher review of one observed action binding."""
        if not callable(getattr(
                self, "_authoritative_hot_generation_publisher", None)):
            raise RuntimeError(
                "authoritative causal action durability is unavailable"
            )
        if source not in ("joe", "wc"):
            raise PermissionError("causal action reviewer is not authorized")
        with self.persistence_transaction():
            if self._causal_action_cycle is None:
                raise RuntimeError(
                    "causal action cycle authority is unavailable"
                )
            prior = self._causal_action_cycle.encoded_snapshot()
            try:
                feedback = (
                    self._causal_action_cycle.review_latest_closure(
                        binding_id=binding_id,
                        decision=decision,
                        source=source,
                        nonce=nonce,
                    )
                )
                self.save_hot_state(state_dir)
                return {
                    "binding_id": feedback.binding_id,
                    "decision": feedback.decision,
                    "ok": True,
                    "resulting_binding_status": (
                        feedback.resulting_binding_status
                    ),
                    "status": "applied",
                }
            except BaseException:
                self._causal_action_cycle.restore_encoded(prior)
                raise






    def auditory_l5_status(self):
        experience = self._latest_auditory_l5_experience
        latest = self._latest_auditory_recurrent_motif
        motif_owner = self._auditory_recurrent_motif_owner
        profile = motif_owner.resource_profile
        motif_neurons = motif_owner.motif_neurons
        legacy_status = {
            "active": False,
            "archive_present": False,
            "branch_counts": {},
            "class_counts": {},
        }
        legacy_krimelack_status = {
            "active": False,
            "archive_present": False,
        }
        from dsf_ai_service.substrate.auditory_live_motif import (
            AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA,
            AuditoryLiveMotifCompactReceipt,
        )
        latest_record = (
            latest.as_record_from_custody()
            if isinstance(latest, AuditoryLiveMotifCompactReceipt)
            else latest.as_record()
            if latest is not None
            else None
        )
        return {
            "provider": "causal_gammatone_erb_v1",
            "active_hearing_authority": "auditory_recurrent_motif",
            "latest_experience_id": (
                experience.experience_id if experience is not None else None),
            "latest_relation": (
                experience.relation if experience is not None else None),
            "recognition_boundary": self._latest_auditory_recognition_boundary,
            "recognition_attempted": False,
            "recognition_attempted_deprecated": (
                "presemantic motif firing is not recognition"
            ),
            "motif_firing_evaluated": latest is not None,
            "motif_learning_observation_attempted": (
                latest is not None
                and latest.learning_state
                != "awaiting_exact_window_composition"
            ),
            "continuous_streams": self._auditory_full_field_streams.status(),
            "full_field_transactions": (
                self._auditory_full_field_transactions.status()
            ),
            "terminal_pipeline": self.auditory_terminal_pipeline_status(),
            "recurrent_motif": {
                "active": True,
                "semantic_authority": False,
                "transcript_authority": False,
                "motif_neuron_count": len(motif_neurons),
                "pending_independent_experience_count": (
                    motif_owner.pending_experience_count
                ),
                "pending_independent_experience_capacity": (
                    profile.max_pending_experiences
                ),
                "pending_independent_experience_remaining": max(
                    0,
                    profile.max_pending_experiences
                    - motif_owner.pending_experience_count,
                ),
                "learning_capacity_exhausted": (
                    motif_owner.pending_experience_count
                    >= profile.max_pending_experiences
                ),
                "learning_lifetime": (
                    "bounded_finite_exact_comparison_pool"
                ),
                "pending_transport_units": sum(
                    len(value)
                    for value in (
                        self._auditory_receptor_terminal_by_stream.values()
                    )
                    if not isinstance(value, str)
                ),
                "max_pending_transport_units_per_stream": 4,
                "active_terminal_streams": sum(
                    not isinstance(value, str)
                    for value in (
                        self._auditory_receptor_terminal_by_stream.values()
                    )
                ),
                "cross_transport_unresolved_streams": sum(
                    isinstance(value, str)
                    for value in (
                        self._auditory_receptor_terminal_by_stream.values()
                    )
                ),
                "resource_profile": {
                    **profile.payload(),
                    "authority_receipt_sha256": (
                        profile.authority_receipt_sha256
                    ),
                },
                "persistence": {
                    "available": (
                        self._auditory_recurrent_motif_key is not None
                    ),
                    "authenticated": (
                        self._auditory_recurrent_motif_key is not None
                    ),
                    "canonical": True,
                    "schema": (
                        AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA
                    ),
                },
                "latest": (
                    latest_record
                ),
            },
            "thing_vocal_learning": {
                "active": all(
                    value is not None
                    for value in (
                        self._causal_thing_mosaic_owner,
                        self._w1_self_acoustic_propagation,
                        self._articulatory_self_vocal_owner,
                        (
                            self
                            ._fresh_articulatory_self_acoustic_custody
                        ),
                        self._articulatory_consequence_closure,
                        self._pending_articulatory_causal_attempt,
                        self._articulatory_exploration_selector,
                        (
                            self
                            ._consequence_evoked_articulatory_response
                        ),
                    )
                ),
                "full_dsf_field_preserved": True,
                "meaning_authority": (
                    "consequence_selected_articulatory_closure"
                ),
                "scripted_meaning": False,
                "transcript_authority": False,
                "thing_mosaic": (
                    self._causal_thing_mosaic_owner.status()
                    if self._causal_thing_mosaic_owner is not None
                    else None
                ),
                "fresh_articulatory_self_acoustic_custody": (
                    self
                    ._fresh_articulatory_self_acoustic_custody
                    .status()
                    if (
                        self
                        ._fresh_articulatory_self_acoustic_custody
                        is not None
                    )
                    else None
                ),
                "articulatory_self_vocal": (
                    self._articulatory_self_vocal_owner.status()
                    if self._articulatory_self_vocal_owner is not None
                    else None
                ),
                "articulatory_consequence_closure": (
                    self._articulatory_consequence_closure.status()
                    if self._articulatory_consequence_closure is not None
                    else None
                ),
                "pending_articulatory_causal_attempt": (
                    self._pending_articulatory_causal_attempt.status()
                    if (
                        self._pending_articulatory_causal_attempt
                        is not None
                    )
                    else None
                ),
                "articulatory_exploration_selector": (
                    self._articulatory_exploration_selector.status()
                    if (
                        self._articulatory_exploration_selector
                        is not None
                    )
                    else None
                ),
                "latest_autonomous_exploration": (
                    self._latest_autonomous_articulatory_exploration
                ),
                "consequence_response_bound": (
                    self._consequence_evoked_articulatory_response
                    is not None
                ),
            },
            "loom_neuron_full_field_bridge": {
                "active": False,
                "reason": "no production delivery path",
                "production_scope": None,
                "full_dsf_field_preserved": False,
                "legacy_wave_summary_used": False,
                "chi_identity": False,
                "psi_identity": False,
                "recognition_authority": False,
                "float_phase_authority": False,
                "exact_phase_winding_authority": False,
                "latest": None,
            },
            "w1_binaural_recurrent_motif": {
                "active": True,
                "ear_ids": ["left", "right"],
                "full_field_preserved": True,
                "persistence_available": (
                    self._auditory_w1_binaural_motif_key is not None
                ),
                "status": (
                    self._auditory_w1_binaural_motif_owner.status()
                ),
                "transcript_authority": False,
            },
            "krimelack_live": {
                **legacy_krimelack_status,
                "active": False,
                "migration_to_recurrent_motif": "unavailable",
                "reason": (
                    "legacy sign paths lack raw cumulative-phase receptor "
                    "evidence and are quarantined"
                ),
            },
            "krimelack_cognition": {
                "active": False,
                "meaning_from_text": False,
                "transcript_authority": False,
                "latest": None,
                "reason": "retired_sign_flattened_cognition",
            },
            "legacy_incremental_terminal": {
                "active": False,
                "reason": "retired_incompatible_capture_classifier",
            },
            "legacy_token_sequence": {
                "active": False,
                "available": False,
                "reason": "retired opaque teaching archive only",
            },
            "legacy_causal_language": {
                "active": False,
                "available": False,
                "reason": "retired opaque teaching archive only",
            },
            "latest_incremental_status": None,
            "latest_incremental_status_deprecated": (
                "retired incompatible capture classifier"
            ),
            "latest_motif_firing_state": (
                latest.firing_state if latest is not None else None
            ),
            "latest_motif_learning_state": (
                latest.learning_state if latest is not None else None
            ),
            "latest_stream_settlement_receipt_sha256": (
                self._latest_auditory_stream_settlement_receipt.authority_receipt_sha256
                if self._latest_auditory_stream_settlement_receipt is not None
                else None
            ),
            "l5_owner": self._auditory_l5_owner.status(),
            "legacy_reciprocity_archive": {
                "active": False,
                "status": legacy_status,
            },
            "reciprocity": {
                "active": False,
                "authority": "retired_incompatible_capture_classifier",
                "branch_counts": legacy_status["branch_counts"],
                "class_counts": legacy_status["class_counts"],
            },
            "live_anonymous_encounter": (
                self._live_anonymous_encounter_continuity.status()
                if self._live_anonymous_encounter_continuity is not None
                else {
                    "active": False,
                    "state": "unknown",
                    "reason": "authority_unavailable",
                    "acoustic_source": "unknown",
                    "source_attribution": (
                        "unavailable_without_physical_acoustic_source_"
                        "correspondence"
                    ),
                }
            ),
            "visual_exposure_epoch": (
                self._visual_exposure_epoch.status()
                if self._visual_exposure_epoch is not None
                else {
                    "active_streams": 0,
                    "identity_authority": False,
                    "persistence": "disabled",
                }
            ),
            "persistence_transition": {
                "active_envelope_schema": (
                    AUDITORY_LIVE_MOTIF_PERSISTENCE_SCHEMA
                ),
                "state": (
                    "motif_active"
                    if motif_owner.pending_experience_count
                    else "motif_empty"
                ),
                "legacy_archive_schema": None,
                "legacy_v4_preserved": False,
                "legacy_v4_envelope_sha256": None,
                "legacy_v4_encoded_payload_bytes": 0,
                "legacy_v4_applied": False,
                "legacy_v5_applied": False,
                "legacy_v5_preserved": False,
                "legacy_v5_migration": "unavailable",
                "quarantined_causal_action_present": False,
                "quarantined_terminal_event_present": False,
            },
            "recognitions": [],
        }

    WAVE_PROPOSAL_QUEUE_MAX = 64

    WAVE_PROPOSAL_DROP_LOG_EVERY = 50

    _CHI_ADDRESS_SPACE = 262144

    INTRO_RECENCY_BOOST = 2.0

    ACTIVITY_BOOST = 1.5

    AWARE_BLOCKED_ATTENUATION = 0.5

    PRIOR_WEIGHT_CAP = 5.0

    CONTEXT_WINDOW_COMMITS = 10

    CONTEXT_WINDOW_TICKS = 50

    INTROSPECTION_SCAN_TAIL = 200

    _EMISSION_SECTIONS = ("subject", "verb", "object", "modifier", "ground", "intro")

    def _observational_event_receipt(
            self, event_kind, detail, tick, timestamp, *, failure=None):
        """Compress one telemetry event to a fixed authenticated receipt."""
        if not isinstance(event_kind, str):
            raise ValueError("observational event kind must be text")
        try:
            event_kind_bytes = event_kind.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError(
                "observational event kind must use the ASCII event alphabet"
            ) from error
        if (
            not event_kind_bytes
            or len(event_kind_bytes) > OBSERVATIONAL_EVENT_KIND_MAX_BYTES
            or any(
                character not in (
                    "abcdefghijklmnopqrstuvwxyz"
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "0123456789_.:-"
                )
                for character in event_kind
            )
        ):
            raise ValueError(
                "observational event kind exceeds its declared alphabet "
                "or byte boundary"
            )
        if (
            isinstance(tick, bool)
            or not isinstance(tick, int)
            or not 0 <= tick <= ENGINE_STORAGE_UINT64_MAX
        ):
            raise ValueError("observational event tick is outside uint64")
        if (
            not isinstance(timestamp, str)
            or len(timestamp) != 20
        ):
            raise ValueError(
                "observational event timestamp is not fixed UTC text"
            )
        try:
            time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            timestamp.encode("ascii")
        except (ValueError, UnicodeEncodeError) as error:
            raise ValueError(
                "observational event timestamp is not fixed UTC text"
            ) from error
        if not isinstance(detail, dict):
            raise ValueError("observational event detail must be a mapping")
        detail_bytes = json.dumps(
            detail,
            allow_nan=True,
            default=str,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(detail_bytes) > ENGINE_STORAGE_UINT64_MAX:
            raise ValueError("observational detail exceeds uint64")
        receipt_values = sorted({
            value.lower()
            for key, value in detail.items()
            if isinstance(key, str)
            and (
                key.endswith("authority_receipt_sha256")
                or key.endswith("receipt_sha256")
            )
            and isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdefABCDEF"
                    for character in value)
        })
        if not receipt_values:
            authority_receipt_sha256 = None
        elif len(receipt_values) == 1:
            authority_receipt_sha256 = receipt_values[0]
        else:
            authority_receipt_sha256 = _hashlib.sha256(
                self._canonical_persistence_bytes(receipt_values)
            ).hexdigest()
        if failure is not None:
            if not isinstance(failure, dict) or set(failure) != {
                "failure_kind",
                "error_type",
                "error_message_sha256",
                "physical_byte_receipt_sha256",
            }:
                raise ValueError(
                    "observational failure receipt shape changed"
                )
            for name, maximum in (
                ("failure_kind", OBSERVATIONAL_FAILURE_KIND_MAX_BYTES),
                ("error_type", OBSERVATIONAL_ERROR_TYPE_MAX_BYTES),
            ):
                value = failure[name]
                if (
                    not isinstance(value, str)
                    or not value
                    or len(value.encode("ascii", errors="ignore"))
                    != len(value)
                    or len(value) > maximum
                ):
                    raise ValueError(
                        f"observational {name} exceeds its boundary"
                    )
            for name in (
                "error_message_sha256",
                "physical_byte_receipt_sha256",
            ):
                value = failure[name]
                if value is not None and (
                    not isinstance(value, str)
                    or len(value) != 64
                    or any(character not in "0123456789abcdef"
                           for character in value)
                ):
                    raise ValueError(
                        f"observational {name} is not a SHA-256 digest"
                    )
        unsigned = {
            "schema": "guala.observational_event_receipt.v1",
            "event_kind": event_kind,
            "tick": tick,
            "timestamp": timestamp,
            "detail_sha256": _hashlib.sha256(detail_bytes).hexdigest(),
            "detail_bytes": len(detail_bytes),
            "authority_receipt_sha256": authority_receipt_sha256,
            "failure": failure,
        }
        key = getattr(self, "_observational_receipt_hmac_key", None)
        authority_hmac = (
            _hmac.new(
                key,
                self._canonical_persistence_bytes(unsigned),
                _hashlib.sha256,
            ).hexdigest()
            if key is not None else None
        )
        receipt = {
            **unsigned,
            "authority_hmac_sha256": authority_hmac,
        }
        if (
            len(self._canonical_persistence_bytes(receipt)) + 1
            > self.OBSERVATIONAL_RECEIPT_MAX_BYTES
        ):
            raise RuntimeError(
                "observational receipt exceeds its derived schema maximum"
            )
        return receipt

    def _verify_observational_event_receipt(self, receipt):
        if not isinstance(receipt, dict) or set(receipt) != {
            "schema",
            "event_kind",
            "tick",
            "timestamp",
            "detail_sha256",
            "detail_bytes",
            "authority_receipt_sha256",
            "failure",
            "authority_hmac_sha256",
        }:
            raise ValueError("observational receipt shape changed")
        if receipt["schema"] != "guala.observational_event_receipt.v1":
            raise ValueError("observational receipt schema changed")
        encoded = self._canonical_persistence_bytes(receipt)
        if len(encoded) + 1 > self.OBSERVATIONAL_RECEIPT_MAX_BYTES:
            raise ValueError("observational receipt exceeds schema maximum")
        key = getattr(self, "_observational_receipt_hmac_key", None)
        supplied_hmac = receipt["authority_hmac_sha256"]
        unsigned = {
            name: value
            for name, value in receipt.items()
            if name != "authority_hmac_sha256"
        }
        if key is None:
            if supplied_hmac is not None:
                raise ValueError(
                    "unkeyed observational receipt claims authentication"
                )
        else:
            expected_hmac = _hmac.new(
                key,
                self._canonical_persistence_bytes(unsigned),
                _hashlib.sha256,
            ).hexdigest()
            if (
                not isinstance(supplied_hmac, str)
                or not _hmac.compare_digest(
                    supplied_hmac,
                    expected_hmac,
                )
            ):
                raise ValueError(
                    "observational receipt authentication changed"
                )
        return encoded

    def _log_substrate_event(self, event_kind, **detail):
        """Record one receipt-bound event in the bounded in-memory ring."""
        timestamp = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        observational_receipt = self._observational_event_receipt(
            event_kind,
            detail,
            self.tick,
            timestamp,
        )
        with self._substrate_event_lock:
            self._substrate_event_sequence += 1
            ev = SubstrateEvent(
                sequence=self._substrate_event_sequence,
                tick=self.tick,
                kind=event_kind,
                detail=observational_receipt,
            )
            self._substrate_events.append(ev)
        return ev

    DAYDREAM_LOCK_WAIT_P95_ALERT_MS = 50.0

    DAYDREAM_TICK_RATE_DROP_ALERT_FRACTION = 0.30

    DAYDREAM_TELEMETRY_EVERY_N = 60

    DAYDREAM_LOCK_WAIT_WINDOW = 240

    DAYDREAM_TICK_RATE_BASELINE_SAMPLES = 3

    _AUTONOMY_YIELD_SEC = 0.02

    def start_causal_play_loop(self):
        """Start one event-driven bounded physical play owner."""
        with self._causal_play_condition:
            current = self._causal_play_thread
            if current is not None and current.is_alive():
                return
            if self._causal_play_stop:
                raise RuntimeError(
                    "causal play owner cannot restart after quiescence"
                )

            def loop():
                while True:
                    with self._causal_play_condition:
                        self._causal_play_condition.wait_for(
                            lambda: (
                                self._causal_play_pending
                                or self._causal_play_stop
                            )
                        )
                        if self._causal_play_stop:
                            return
                        self._causal_play_pending = False
                    try:
                        with self._engine_mutation_scope(
                            "causal_play_event"
                        ):
                            activity = (
                                self._prepare_custody_native_tutoring_activity()
                                or self._prepare_autonomous_play_activity()
                            )
                            if activity is not None:
                                self._atick_playing(activity)
                    except Exception as error:
                        self._log_substrate_event(
                            "causal_play_event_failed",
                            error_type=type(error).__name__,
                            reason=str(error),
                        )

            self._causal_play_thread = threading.Thread(
                target=loop,
                daemon=True,
                name="guala-causal-play",
            )
            self._causal_play_thread.start()

    def _admit_autonomous_experience_source(
        self,
        *,
        kind,
        source_receipt_sha256,
        dependency_receipt_sha256s=(),
    ):
        """Admit one authenticated occurrence to the bounded owner."""

        driver = self._autonomous_experience_driver
        if driver is None:
            return "unavailable"
        work = driver.issue_work(
            kind=kind,
            source_receipt_sha256=source_receipt_sha256,
            dependency_receipt_sha256s=tuple(
                dependency_receipt_sha256s
            ),
        )
        return driver.admit(work)

    def _admit_autonomous_internal_dreams(
        self,
        dream_receipt_sha256s,
    ):
        """Atomically admit newly committed internal-transition receipts."""

        driver = self._autonomous_experience_driver
        if driver is None:
            raise RuntimeError(
                "autonomous experience authority is unavailable"
            )
        works = tuple(
            driver.issue_work(
                kind="internal_dream",
                source_receipt_sha256=receipt,
            )
            for receipt in dream_receipt_sha256s
        )
        return driver.admit_batch(works)

    def _resolve_autonomous_action_execution(self, receipt):
        """Resolve one action only from durable lived full-field custody."""

        lived = self._causal_thing_lived_context
        authority = self._causal_thing_action_execution
        if lived is None or authority is None:
            raise RuntimeError(
                "autonomous action consequence authority is unavailable"
            )
        execution = lived.resolve_action_execution(receipt)
        authority.verify(execution)
        return execution

    def _resolve_autonomous_body_evolution(self, receipt):
        """Resolve one body evolution only from retained physical history."""

        owner = self._physical_internal_body_state
        if owner is None:
            raise RuntimeError(
                "autonomous internal-body authority is unavailable"
            )
        return owner.resolve_transition(receipt)

    def _rebind_autonomous_action_restored_graph(self):
        """Reconnect exact authorities replaced by action rollback restore."""

        learning = self._whole_organism_thing_learning_owner
        neurons = self._whole_organism_neuron_population_owner
        episodes = self._whole_organism_episode_authority
        passive = getattr(
            self,
            "_passive_whole_organism_thing_learning",
            None,
        )
        ordered = getattr(
            self,
            "_organism_ordered_lived_experience_owner",
            None,
        )
        dream = self._organism_dream_wake_weave_owner
        reentry = self._whole_organism_internal_reentry_authority
        if any(
            value is None
            for value in (
                learning,
                neurons,
                episodes,
                passive,
                ordered,
                dream,
                reentry,
            )
        ):
            raise RuntimeError(
                "autonomous action rollback graph is not fully mounted"
            )
        learning.rebind_episode_authority(episodes)
        passive.rebind_neuron_owner(neurons)
        ordered.rebind_source_custody(
            self._ordered_lived_experience_source_custody()
        )
        dream.rebind_restored_authorities(
            structural_state_owner=self._whole_organism_structural_owner,
            learning_owner=learning,
            ordered_lived_experience_owner=ordered,
        )
        reentry.rebind_whole_organism_authorities(
            learning_owner=learning,
            neuron_owner=neurons,
            episode_authority=episodes,
        )

    def _execute_autonomous_causal_thing_intent(self, intent_receipt):
        """Execute one current learned intent as one rollbackable organism act."""

        intent_owner = self._causal_thing_action_intent
        execution_owner = self._causal_thing_action_execution
        world = self._embodiment_world
        body = self._physical_internal_body_state
        things = self._causal_thing_mosaic_owner
        if any(
            value is None
            for value in (
                intent_owner,
                execution_owner,
                world,
                body,
                things,
            )
        ):
            raise RuntimeError(
                "autonomous causal THING action spine is unavailable"
            )
        intent = intent_owner.resolve_live(intent_receipt)
        current_settlement = self._latest_causal_settlement
        if (
            current_settlement is None
            or current_settlement.authority_receipt_sha256
            != intent.current_witness.settlement_receipt_sha256
            or world.observation_snapshot().authority_receipt_sha256
            != intent.world_observation_receipt_sha256
        ):
            intent_owner.consume(
                intent_receipt_sha256=intent.authority_receipt_sha256
            )
            return ()

        whole_snapshot = self._live_whole_action_spine_snapshot()
        prediction_snapshot = (
            self._full_field_prediction.encoded_snapshot()
            if self._full_field_prediction is not None
            else None
        )
        prior_prediction_observation = (
            self._latest_full_field_prediction_observation
        )
        prior_latest_settlement = self._latest_causal_settlement
        prior_accepted = self._causal_settlement_accepted
        prior_custody_keys = frozenset(
            self._live_settled_prediction_custodies
        )
        prior_body_transition_receipts = frozenset(
            value.authority_receipt_sha256
            for value in body.transitions
        )
        executed = None
        continuation = None
        thing_undo = None
        lived_undos = ()
        try:
            authorization = (
                self._begin_live_whole_organism_action_authorization(
                    settlement=current_settlement,
                    action_authority_receipt_sha256=(
                        intent.authority_receipt_sha256
                    ),
                )
            )
            executed = execution_owner.execute(intent=intent)
            outcome = executed.physical_mount.causal_settlement
            if outcome is None:
                raise RuntimeError(
                    "autonomous action produced no full-field consequence"
                )
            self._complete_live_whole_organism_action_consequence(
                authorization=authorization,
                settlement=outcome,
                action_execution_receipt_sha256=(
                    executed.world_execution.authority_receipt_sha256
                ),
            )
            settled_custody = _SettledPredictionCustody(
                authority=executed.custody_authority,
                capability=executed.custody_capability,
                custody=executed.custody,
                view=executed.custody_view,
            )
            source_key = (
                executed.physical_mount.evidence_receipt
                .authority_receipt_sha256
            )
            self._live_settled_prediction_custodies[source_key] = (
                settled_custody
            )
            continuation = (
                self._prepare_ordered_thing_continuation_from_custodies(
                    (settled_custody,)
                )
            )
            if (
                continuation is None
                or continuation.staged_mosaic.thing_id != intent.thing_id
            ):
                raise RuntimeError(
                    "autonomous action consequence lost its causal THING"
                )
            thing_undo = (
                things.commit_prepared_ordered_custody_continuation(
                    continuation
                )
            )
            lived_undos = self._commit_lived_context_partitions(
                (settled_custody,),
                continuation.partitions,
                action_consequence=executed.execution,
            )
            self._record_causal_perception_without_dispatch(
                outcome,
                action_outcome=True,
                custody_authority=executed.custody_authority,
                custody_capability=executed.custody_capability,
                publish_acceptance=False,
            )
            body_transition_receipts = tuple(
                value.authority_receipt_sha256
                for value in body.transitions
                if value.authority_receipt_sha256
                not in prior_body_transition_receipts
            )
            driver = self._autonomous_experience_driver
            if driver is None:
                raise RuntimeError(
                    "autonomous experience authority is unavailable"
                )
            works = [
                driver.issue_work(
                    kind="action_execution",
                    source_receipt_sha256=(
                        executed.execution.authority_receipt_sha256
                    ),
                    dependency_receipt_sha256s=(
                        intent.authority_receipt_sha256,
                    ),
                )
            ]
            works.extend(
                driver.issue_work(
                    kind="body_evolution",
                    source_receipt_sha256=receipt,
                    dependency_receipt_sha256s=(
                        executed.execution.authority_receipt_sha256,
                        outcome.authority_receipt_sha256,
                    ),
                )
                for receipt in body_transition_receipts
            )
            works.append(driver.issue_work(
                kind="causal_settlement",
                source_receipt_sha256=outcome.authority_receipt_sha256,
            ))
            driver.admit_batch(tuple(works))
            self._publish_causal_experience_accepted(
                outcome,
                autonomous_admitted=True,
            )
            return tuple((
                executed.execution.authority_receipt_sha256,
                executed.world_execution.authority_receipt_sha256,
                outcome.authority_receipt_sha256,
                *body_transition_receipts,
            ))
        except BaseException:
            self._rollback_lived_context_admissions(lived_undos)
            if thing_undo is not None:
                things.rollback_committed_ordered_custody_continuation(
                    thing_undo
                )
            elif continuation is not None:
                things.discard_prepared_ordered_custody_continuation(
                    continuation
                )
            if executed is not None:
                execution_owner.rollback_committed_execution(
                    executed.undo
                )
            self._restore_live_whole_action_spine_snapshot(whole_snapshot)
            self._rebind_autonomous_action_restored_graph()
            if (
                prediction_snapshot is not None
                and self._full_field_prediction is not None
            ):
                self._full_field_prediction.restore_encoded(
                    prediction_snapshot
                )
            self._latest_full_field_prediction_observation = (
                prior_prediction_observation
            )
            self._latest_causal_settlement = prior_latest_settlement
            self._causal_settlement_accepted = prior_accepted
            for source_key in tuple(
                self._live_settled_prediction_custodies
            ):
                if source_key not in prior_custody_keys:
                    del self._live_settled_prediction_custodies[source_key]
            raise

    def _handle_autonomous_experience_work(self, work):
        """Advance exactly the occurrence carried by one driver receipt."""

        if work.kind == "internal_dream":
            authority = self._whole_organism_internal_reentry_authority
            if authority is None:
                raise RuntimeError(
                    "whole-organism internal re-entry is unavailable"
                )
            record = authority.record_dream(
                work.source_receipt_sha256
            )
            self._latest_autonomous_internal_reentry = record
            return (record.authority_receipt_sha256,)
        if work.kind == "action_intent":
            with self._engine_mutation_scope("autonomous_action_intent"):
                with (
                    self.lock,
                    self._causal_cycle_bridge_lock,
                    self.persistence_transaction(),
                ):
                    return self._execute_autonomous_causal_thing_intent(
                        work.source_receipt_sha256
                    )
        if work.kind == "action_execution":
            execution = self._resolve_autonomous_action_execution(
                work.source_receipt_sha256
            )
            return (
                execution.actual_outcome_settlement_receipt_sha256,
                execution.intent_receipt_sha256,
                execution.outcome_custody_receipt_sha256,
                execution.world_execution_receipt_sha256,
            )
        if work.kind == "body_evolution":
            transition = self._resolve_autonomous_body_evolution(
                work.source_receipt_sha256
            )
            return (
                transition.after_state_receipt_sha256,
                transition.before_state_receipt_sha256,
                transition.physical_source_receipt_sha256,
            )
        if work.kind != "causal_settlement":
            raise RuntimeError(
                f"autonomous work kind is not mounted: {work.kind}"
            )
        with self._engine_mutation_scope("autonomous_experience"):
            activity = (
                self._prepare_custody_native_tutoring_activity()
                or self._prepare_autonomous_play_activity()
            )
            if activity is None:
                return ()
            if not self._start_activity(activity):
                return ()
            try:
                self._atick_playing(activity)
                outputs = []
                autonomous = activity.metadata.get(
                    "_autonomous_play_completion"
                )
                if autonomous is not None:
                    outputs.append(
                        autonomous["causal_play_receipt_sha256"]
                    )
                tutoring = activity.metadata.get(
                    "_custody_native_tutoring_action_result"
                )
                if tutoring is not None:
                    outputs.extend((
                        tutoring["action_selection_receipt_sha256"],
                        tutoring["experience_receipt_sha256"],
                        tutoring["outcome_settlement_receipt_sha256"],
                        tutoring["world_execution_receipt_sha256"],
                    ))
                return tuple(outputs)
            finally:
                self._end_activity()

    def start_autonomous_experience_driver(self):
        """Start receipt-driven experience or report its truthful absence."""

        driver = self._autonomous_experience_driver
        if driver is None:
            return {
                "lifecycle": "unavailable",
                "reason": "legacy_python_autonomy_retired",
                "schema": "guala.autonomous_experience.unavailable.v1",
            }
        driver.start(
            self._handle_autonomous_experience_work,
            transition_scope=lambda: self._engine_mutation_scope(
                "autonomous_experience_driver_work"
            ),
        )
        return driver.status()

    def _notify_causal_play(self):
        """Coalesce causal commits into one bounded physical play wake."""
        with self._causal_play_condition:
            if self._causal_play_stop:
                return
            self._causal_play_pending = True
            self._causal_play_condition.notify()

    def _enter_live_interaction(self):
        """Mark one live human interaction (a converse turn or a real sight/
        sound frame) as in progress, so background lock-hogs defer their
        self.lock acquisition until it clears. Counter, not a boolean: several
        live interactions can overlap (a turn plus concurrent camera frames).
        Callers MUST pair this with _exit_live_interaction in a try/finally so
        the count is always released even if processing raises."""
        # Defensive getattr: a Guala reconstructed by a path that somehow
        # skipped these __init__ attributes still degrades to "never defer"
        # rather than raising, so the priority gate can never itself break a
        # live turn or a save.
        lock = getattr(self, "_live_interaction_lock", None)
        if lock is None:
            return
        with lock:
            self._live_interaction_pending = getattr(
                self, "_live_interaction_pending", 0) + 1

    def _exit_live_interaction(self):
        """Release one live-interaction mark taken by _enter_live_interaction.
        Clamped at zero so a stray extra release can never drive the counter
        negative and permanently suppress deferral."""
        lock = getattr(self, "_live_interaction_lock", None)
        if lock is None:
            return
        with lock:
            self._live_interaction_pending = max(
                0, getattr(self, "_live_interaction_pending", 0) - 1)

    def _defer_for_live_interaction(self, site):
        """Return True if this background site (identified by `site`) should
        SKIP acquiring self.lock this cycle to let a pending live interaction
        through first; False if it should proceed normally. The interaction's
        balanced try/finally scope is the exact end condition; a timer cannot
        split one physical experience into competing scheduler intervals."""
        lock = getattr(self, "_live_interaction_lock", None)
        if lock is None:
            return False
        # Defer if EITHER "live interaction" counter is positive:
        #  - _live_interaction_pending: physical /sight_frame and /sound_frame
        #    work, plus app-level scopes enclosing a whole audiovisual event.
        #  - _live_converse_pending: the PRE-EXISTING per-turn counter that
        #    converse() self-increments (under _live_converse_state_lock; see
        #    line ~5120) and that _try_acquire_autonomous_emission already
        #    honors for the emission LOCK. We only READ it here -- never write
        #    it -- so this self.lock priority gate mirrors/extends that
        #    existing attribute without changing its semantics or its
        #    underflow-checked write path.
        with lock:
            return (getattr(self, "_live_interaction_pending", 0)
                    + getattr(self, "_live_converse_pending", 0)) > 0

    RECENCY_RECOVERY_TICKS = 50_000

    def _prepare_autonomous_play_activity(self):
        """Issue one exact play activity from current full-field W1 authority."""
        required = (
            self._autonomous_causal_play,
            self._embodiment_world,
            self._w1_physical_evidence,
            self._embodied_action_teaching,
            self._causal_action_dispatcher,
        )
        if (
            any(item is None for item in required)
            or self._causal_action_dispatcher.status()["active"]
        ):
            return None
        before = self._embodiment_world.observation_snapshot()
        mounted = self._w1_physical_evidence.mount_current_observation(
            commit=False
        )
        if (
            mounted.causal_settlement is None
            or mounted.observation_receipt is None
        ):
            return None
        self._w1_physical_evidence.verify_mount(mounted)
        if (
            mounted.observation_receipt
            .world_observation_after_receipt_sha256
            != before.authority_receipt_sha256
            or self._embodiment_world.observation_snapshot()
            .authority_receipt_sha256
            != before.authority_receipt_sha256
        ):
            raise RuntimeError(
                "autonomous play preparation changed current W1 authority"
            )
        opportunity = self._autonomous_causal_play.prepare(
            evidence=(
                self._embodied_action_teaching
                .verified_guided_relation_evidence()
            ),
            world_structural_fingerprint=(
                mounted.causal_settlement.structural_fingerprint
            ),
            world_observation_receipt_sha256=(
                before.authority_receipt_sha256
            ),
        )
        if opportunity is None:
            return None
        return Activity(
            kind="PLAYING",
            target=None,
            started_tick=self.tick,
            expected_end_tick=self.tick + 1,
            metadata={
                "_autonomous_play_ticket": opportunity.as_record(),
                "trigger": "exact_causal_opportunity",
            },
        )

    def _prepare_custody_native_tutoring_activity(self):
        """Issue one exact material action for one fresh tutoring need."""

        curriculum = self._custody_native_tutoring_curriculum
        selector = self._custody_native_tutoring_action_selector
        if curriculum is None or selector is None:
            return None
        opportunity = curriculum.schedule()
        if opportunity is None:
            return None
        self._latest_custody_native_tutoring_action_observation = {
            "opportunity_receipt_sha256": (
                opportunity.authority_receipt_sha256
            ),
            "reason": "physical_motor_duration_intent_missing",
            "schema": (
                "guala.custody_native_tutoring."
                "action_observation.v1"
            ),
            "state": "unavailable",
        }
        return None

    @staticmethod
    def _verify_play_causal_admission_record(value):
        expected = {
            "causal_event_id",
            "causal_settlement_receipt_sha256",
            "dispatch_phase",
            "dispatch_reason",
            "dispatch_status",
            "embodiment_rejection_reason",
            "episode_id",
            "outcome_observation_receipt_sha256",
            "schema",
            "steps",
            "trigger",
            "world_observation_receipt_sha256",
            "world_revision_after",
            "world_revision_before",
        }
        if (
            not isinstance(value, dict)
            or set(value) != expected
            or value.get("schema") != PLAY_CAUSAL_ADMISSION_SCHEMA
            or value.get("dispatch_status") not in {
                "ambiguous", "completed", "pending", "rejected", "stopped",
                "unknown"
            }
            or value.get("dispatch_phase") not in {
                "closed", "executor_acknowledgement", "outcome_observation",
                "selection",
            }
            or not isinstance(value.get("dispatch_reason"), str)
            or not value["dispatch_reason"]
            or len(value["dispatch_reason"].encode("utf-8")) > 256
            or value.get("trigger") not in {
                "autonomous_play",
                "boot_reconciliation",
                "external_world_change",
                "guided_demonstration",
                "manual_observation",
            }
            or not isinstance(value.get("steps"), list)
            or len(value["steps"]) > 65
            or (
                value.get("embodiment_rejection_reason") is not None
                and (
                    not isinstance(
                        value["embodiment_rejection_reason"], str
                    )
                    or not value["embodiment_rejection_reason"]
                    or len(
                        value["embodiment_rejection_reason"].encode("utf-8")
                    ) > 256
                )
            )
        ):
            raise ValueError("PLAYING causal admission record changed")
        if value.get("episode_id") is not None:
            receipt = value["episode_id"]
            if (
                not isinstance(receipt, str)
                or len(receipt) != 64
                or any(item not in "0123456789abcdef" for item in receipt)
            ):
                raise ValueError("PLAYING episode identity changed")
        for step in value["steps"]:
            if (
                not isinstance(step, dict)
                or set(step) != {
                    "action_receipt_sha256",
                    "binding_id",
                    "closure_receipt_sha256",
                    "outcome_settlement_receipt_sha256",
                }
            ):
                raise ValueError("PLAYING causal step changed")
            for receipt in step.values():
                if (
                    not isinstance(receipt, str)
                    or len(receipt) != 64
                    or any(
                        item not in "0123456789abcdef"
                        for item in receipt
                    )
                ):
                    raise ValueError("PLAYING causal step identity changed")
        for name in (
            "causal_event_id",
            "causal_settlement_receipt_sha256",
            "outcome_observation_receipt_sha256",
            "world_observation_receipt_sha256",
        ):
            receipt = value.get(name)
            if (
                not isinstance(receipt, str)
                or len(receipt) != 64
                or any(character not in "0123456789abcdef" for character in receipt)
            ):
                raise ValueError(
                    f"PLAYING causal admission {name} changed"
                )
        for name in ("world_revision_before", "world_revision_after"):
            revision = value.get(name)
            if (
                isinstance(revision, bool)
                or not isinstance(revision, int)
                or revision < 0
                or revision > (1 << 63) - 1
            ):
                raise ValueError(
                    f"PLAYING causal admission {name} changed"
                )
        if value["world_revision_after"] < value["world_revision_before"]:
            raise ValueError("PLAYING causal admission revision order changed")
        if (
            value["dispatch_status"] != "rejected"
            and value["embodiment_rejection_reason"] is not None
        ):
            raise ValueError(
                "PLAYING causal admission carries a false embodiment rejection"
            )
        return dict(value)

    def _admit_playing_world_experience(self, activity):
        """Verify that PLAYING carries the owner's exact one-use ticket."""
        if activity.kind != "PLAYING":
            raise ValueError("PLAYING admission received another activity")
        existing = activity.metadata.get("_causal_play_admission")
        if existing is not None:
            self._verify_play_causal_admission_record(existing)
            return True
        ticket = activity.metadata.get("_autonomous_play_ticket")
        if ticket is None:
            record = self._run_causal_play_episode(
                trigger="manual_observation",
            )
            if record is None:
                return False
            activity.metadata["_causal_play_admission"] = (
                self._verify_play_causal_admission_record(record)
            )
            return True
        if self._autonomous_causal_play is None:
            return False
        opportunity = self._autonomous_causal_play.verify_opportunity(ticket)
        current = self._embodiment_world.observation_snapshot()
        if (
            current.authority_receipt_sha256
            != opportunity.world_observation_receipt_sha256
        ):
            self._autonomous_causal_play.cancel(opportunity)
            return False
        return True

    def _start_activity(self, activity):
        if activity.kind in {"READING", "EMITTING"}:
            self._log_substrate_event(
                "retired_activity_refused",
                kind=activity.kind,
                target=activity.target,
            )
            return False
        if (
            activity.kind == "PLAYING"
            and not self._admit_playing_world_experience(activity)
        ):
            return False
        self._current_activity = activity
        self._log_substrate_event("activity_started",
                                 kind=activity.kind, target=activity.target)
        return True

    def _reflect_whole_organism(self):
        owner = self._ensure_whole_organism_reflection_owner_binding()
        if owner is None:
            raise RuntimeError(
                "whole-organism reflection authority is unavailable"
            )
        prepared = owner.prepare()
        owner.commit(prepared)
        reflection = owner.current_reflection
        self._log_substrate_event(
            "whole_organism_reflected",
            changed_owner_ids=list(reflection.changed_owner_ids),
            meta_health=reflection.meta_health,
            moment_state=reflection.moment_state,
            receipt_sha256=reflection.authority_receipt_sha256,
            sequence=reflection.sequence,
        )
        return reflection

    def _end_activity(self):
        if self._current_activity:
            self._log_substrate_event("activity_ended",
                                     kind=self._current_activity.kind,
                                     target=self._current_activity.target,
                                     duration=self.tick - self._current_activity.started_tick)
            self._activity_history.append(self._current_activity)
            if len(self._activity_history) > 500:
                self._activity_history = self._activity_history[-200:]
            _ended_activity = self._current_activity
            self._current_activity = None
            # GL-RPT-WAL-BLOAT F2 (2026-07-15): an activity end is the real
            # experience boundary for every attending-episode BindingWindow
            # -- and the only recurring boundary already-leaked contexts
            # will ever see.  Close them by EXPLICIT context id; see the
            # method's own comment for why this must never rely on this
            # thread's bound contextvar.
            self._close_boundary_window_contexts(_ended_activity)
            self._reflect_whole_organism()

    _BOUNDARY_WINDOW_CONTEXT_PREFIXES = (
        "episode:episode:attending_", "implicit:")

    def _close_boundary_window_contexts(self, ended_activity):
        """GL-RPT-WAL-BLOAT F2 (2026-07-15): close attending-episode and
        implicit BindingWindow contexts at their real boundary -- this
        activity end -- by EXPLICIT context id.

        The old close path resolved its target through the CLOSING
        thread's bound contextvar; _end_activity runs from the autonomy
        tick, converse auto-wake (wake_from_sleep), manual_sleep and the
        admin force endpoints -- routinely a DIFFERENT thread than the one
        that opened the context -- so the close silently no-oped.  Live
        cost when found: 170 never-closed contexts / 30,507 entries /
        24.5MB re-embedded into every ~60s save manifest, dominated by 4
        episode:episode:attending_audio giants (one reached 8,910 entries).

        NO TTL/timeout policy here (forbidden: a timer would fabricate an
        experience boundary she never had).  This fires only on a real
        boundary event and closes only context classes proven
        activity/stream-bounded (see _BOUNDARY_WINDOW_CONTEXT_PREFIXES).

        The closes run on a background engine thread because end_context
        durably appends the closed record to the WAL with an fsync (EFS
        can take seconds for a giant record) and _end_activity's callers
        hold self.lock -- the same off-lock discipline as the dream-gate
        write in _end_activity above.  end_context returning None means
        another boundary already closed that context: a benign race, never
        an error.  Closed windows stay write-once: a straggler entry with
        a recurring context id starts a NEW window, never mutates the
        closed record.
        """
        wm = getattr(self, "window_manager", None)
        if wm is None:
            return
        to_close = []
        for _prefix in self._BOUNDARY_WINDOW_CONTEXT_PREFIXES:
            to_close.extend(wm.open_context_ids(_prefix))
        if not to_close:
            return
        _ep_ref = None
        if ended_activity is not None:
            _ep_ref = (ended_activity.metadata or {}).get("_episode_ref")
        _own_context_id = f"episode:{_ep_ref}" if _ep_ref else None

        def _close_all():
            for _cid in to_close:
                try:
                    wm.end_context(
                        _cid,
                        "activity_ended" if _cid == _own_context_id
                        else "activity_boundary")
                except Exception as _close_err:
                    self._log_substrate_event(
                        "window_boundary_close_error",
                        context_id=_cid, error=str(_close_err))

        try:
            self._start_engine_background_thread(
                _close_all, daemon=True, name="window-boundary-close")
        except RuntimeError:
            # Quiescence rejected a new thread (deploy drain): close
            # inline -- draining exactly these is what the seal wants.
            _close_all()

    IMAGINE_PLAY_INTERVAL_TICKS = 500

    IMAGINE_TOP_K = 3

    IMAGINE_MAX_CONCEPTS = 48

    IMAGINE_OP_TAGS = ("sc", "sf", "aff", "em")


    def _atick_playing(self, a):
        """Execute one owner-issued exact W1 causal play opportunity."""
        if a.metadata.get("_causal_play_admission") is not None:
            self._verify_play_causal_admission_record(
                a.metadata["_causal_play_admission"]
            )
            return
        tutoring_ticket = a.metadata.get(
            "_custody_native_tutoring_action_ticket"
        )
        if tutoring_ticket is not None:
            result = self._execute_custody_native_tutoring_action(
                tutoring_ticket
            )
            a.metadata["_custody_native_tutoring_action_result"] = (
                result
            )
            return
        ticket = a.metadata.get("_autonomous_play_ticket")
        if ticket is None:
            return
        if self._autonomous_causal_play is None:
            raise RuntimeError("PLAYING lost autonomous causal authority")
        opportunity = self._autonomous_causal_play.verify_opportunity(ticket)
        before = self._embodiment_world.observation_snapshot()
        if (
            before.authority_receipt_sha256
            != opportunity.world_observation_receipt_sha256
        ):
            self._autonomous_causal_play.cancel(opportunity)
            raise RuntimeError(
                "PLAYING world changed after exact opportunity admission"
            )
        mounted = self._w1_physical_evidence.mount_current_observation(
            commit=True
        )
        if (
            mounted.causal_settlement is None
            or mounted.observation_receipt is None
        ):
            self._autonomous_causal_play.cancel(opportunity)
            raise RuntimeError("PLAYING current physical field did not settle")
        self._w1_physical_evidence.verify_mount(mounted)
        if (
            mounted.causal_settlement.structural_fingerprint
            != opportunity.trigger_structural_fingerprint
            or mounted.observation_receipt
            .world_observation_after_receipt_sha256
            != before.authority_receipt_sha256
        ):
            self._autonomous_causal_play.cancel(opportunity)
            raise RuntimeError("PLAYING full-field trigger authority changed")
        settled_custody = self._settled_prediction_custody(
            mounted,
            world_observation=before,
        )
        try:
            self._record_causal_perception_without_dispatch(
                mounted.causal_settlement,
                custody_authority=settled_custody.authority,
                custody_capability=settled_custody.capability,
            )
            record = self._run_causal_play_episode(
                trigger="autonomous_play",
                committed_custody=settled_custody,
            )
            if record is None:
                raise RuntimeError(
                    "PLAYING causal dispatcher became unavailable"
                )
            completion = self._autonomous_causal_play.complete(
                opportunity,
                causal_play_record=record,
            )
        except BaseException:
            if self._autonomous_causal_play.status()["active"]:
                self._autonomous_causal_play.cancel(opportunity)
            raise
        a.metadata["_causal_play_admission"] = (
            self._verify_play_causal_admission_record(record)
        )
        a.metadata["_autonomous_play_completion"] = completion.as_record()

    @_engine_mutation_entry
    def _execute_custody_native_tutoring_action(self, ticket):
        """Live one selector-issued material action and verify its outcome."""

        raise RuntimeError(
            "legacy Python custody tutoring is permanently retired"
        )

        curriculum = self._custody_native_tutoring_curriculum
        selector = self._custody_native_tutoring_action_selector
        world = self._embodiment_world
        physical = self._w1_physical_evidence
        things = self._causal_thing_mosaic_owner
        if any(
            value is None
            for value in (
                curriculum,
                selector,
                world,
                physical,
                things,
            )
        ):
            raise RuntimeError(
                "custody-native tutoring action is unavailable"
            )
        opportunity = curriculum.schedule()
        if opportunity is None:
            raise RuntimeError(
                "custody-native tutoring opportunity disappeared"
            )
        import base64
        command_payload_text = (
            ticket.get("command_payload_base64")
            if isinstance(ticket, dict)
            else None
        )
        if not isinstance(command_payload_text, str):
            raise ValueError(
                "custody-native tutoring ticket has no motor duration"
            )
        try:
            command_record = json.loads(
                base64.b64decode(
                    command_payload_text,
                    validate=True,
                ).decode("ascii")
            )
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError(
                "custody-native tutoring command is unreadable"
            ) from error
        duration = command_record.get("duration_microseconds")
        selection = selector.select(
            opportunity,
            duration_microseconds=duration,
        )
        selector.verify_selection(
            selection,
            opportunity=opportunity,
        )
        if (
            selection.state is not TutoringActionSelectionState.SELECTED
            or selection.command_payload is None
            or selection.record() != ticket
        ):
            raise ValueError(
                "custody-native tutoring action ticket changed"
            )
        if (
            world.observation_snapshot().authority_receipt_sha256
            != selection.world_observation_receipt_sha256
        ):
            raise RuntimeError(
                "custody-native tutoring world changed before action"
            )

        with self._causal_cycle_bridge_lock, self.persistence_transaction():
            world_snapshot = world.encoded_snapshot()
            prediction_snapshot = (
                self._full_field_prediction.encoded_snapshot()
                if self._full_field_prediction is not None
                else None
            )
            prior_prediction_observation = (
                self._latest_full_field_prediction_observation
            )
            prior_latest_settlement = self._latest_causal_settlement
            prior_accepted = self._causal_settlement_accepted
            whole_action_snapshot = (
                self._live_whole_action_spine_snapshot()
            )
            epoch_token = physical.begin_atomic_episode()
            committed_epoch_undo = None
            mount = None
            mount_committed = False
            settled_custody = None
            thing_continuation = None
            thing_undo = None
            thing_lived_undos = ()
            tutoring_progression = None
            try:
                before = world.observation_snapshot()
                pre_mount = physical.mount_current_observation(
                    commit=True
                )
                if pre_mount.causal_settlement is None:
                    raise RuntimeError(
                        "tutoring action authorization did not settle"
                    )
                authorization = (
                    self._begin_live_whole_organism_action_authorization(
                        settlement=pre_mount.causal_settlement,
                        action_authority_receipt_sha256=(
                            selection.authority_receipt_sha256
                        ),
                    )
                )
                execution = world.execute_port_command(
                    port_id=world.port_id,
                    command_payload=selection.command_payload,
                    causal_intent_receipt_sha256=(
                        selection.authority_receipt_sha256
                    ),
                    expected_revision=before.revision,
                )
                if execution.disposition != "applied":
                    raise RuntimeError(
                        "selected tutoring action was not physically applied"
                    )
                mount = physical.mount_action_outcome(
                    execution,
                    commit=True,
                    reserve=False,
                    source_time_start=(
                        pre_mount.causal_settlement.source_time_end
                    ),
                )
                if (
                    mount.causal_settlement is None
                    or mount.evidence_receipt is None
                    or mount.state.value != "observed"
                ):
                    raise RuntimeError(
                        "tutoring action produced no full-field outcome"
                    )
                physical.verify_mount(mount)
                self._complete_live_whole_organism_action_consequence(
                    authorization=authorization,
                    settlement=mount.causal_settlement,
                    action_execution_receipt_sha256=(
                        execution.authority_receipt_sha256
                    ),
                )
                settled_custody = self._settled_prediction_custody(
                    mount,
                    world_execution=execution,
                )
                thing_continuation = (
                    self
                    ._prepare_ordered_thing_continuation_from_custodies(
                        (settled_custody,)
                    )
                )
                if (
                    thing_continuation is None
                    or thing_continuation.staged_mosaic.thing_id
                    != opportunity.thing_id
                ):
                    raise RuntimeError(
                        "tutoring action lost its held causal THING"
                    )
                thing_undo = (
                    things
                    .commit_prepared_ordered_custody_continuation(
                        thing_continuation
                    )
                )
                thing_lived_undos = (
                    self._commit_lived_context_partitions(
                        (settled_custody,),
                        thing_continuation.partitions,
                    )
                )
                outcome = mount.causal_settlement
                route = things.route(outcome)
                if (
                    route.state != "unique"
                    or route.thing_ids != (opportunity.thing_id,)
                ):
                    raise RuntimeError(
                        "tutoring action outcome did not route to its THING"
                    )
                interpretation = next(
                    value
                    for value in outcome.interpretations
                    if value.sense == opportunity.target_sense
                )
                target_observed = (
                    interpretation.state == "observed"
                    and interpretation.relation
                    == opportunity.target_relation
                )
                self._record_causal_perception_without_dispatch(
                    outcome,
                    action_outcome=True,
                    custody_authority=settled_custody.authority,
                    custody_capability=settled_custody.capability,
                    publish_acceptance=False,
                )
                (
                    tutoring_observation,
                    tutoring_progression,
                ) = self._admit_tutoring_from_custody(
                    settled_custody,
                    return_committed_progression=True,
                )
                if (
                    tutoring_observation[
                        "resolved_active_opportunity"
                    ]
                    != target_observed
                ):
                    raise RuntimeError(
                        "tutoring action resolution changed observation"
                    )
                committed_epoch_undo = (
                    physical.commit_atomic_episode(epoch_token)
                )
                mount_committed = True
                self._publish_causal_experience_accepted(outcome)
            except BaseException:
                if tutoring_progression is not None:
                    curriculum.rollback_committed_progression(
                        tutoring_progression
                    )
                self._rollback_lived_context_admissions(
                    thing_lived_undos
                )
                if thing_undo is not None:
                    (
                        things
                        .rollback_committed_ordered_custody_continuation(
                            thing_undo
                        )
                    )
                elif thing_continuation is not None:
                    (
                        things
                        .discard_prepared_ordered_custody_continuation(
                            thing_continuation
                        )
                    )
                if committed_epoch_undo is None:
                    physical.rollback_atomic_episode(epoch_token)
                else:
                    physical.rollback_committed_atomic_episode(
                        committed_epoch_undo
                    )
                if settled_custody is not None:
                    source_key = (
                        settled_custody.view
                        .physical_evidence_receipt
                        .authority_receipt_sha256
                    )
                    if (
                        self._live_settled_prediction_custodies.get(
                            source_key
                        )
                        is settled_custody
                    ):
                        del self._live_settled_prediction_custodies[
                            source_key
                        ]
                world.restore_encoded(world_snapshot)
                self._restore_live_whole_action_spine_snapshot(
                    whole_action_snapshot
                )
                if (
                    prediction_snapshot is not None
                    and self._full_field_prediction is not None
                ):
                    self._full_field_prediction.restore_encoded(
                        prediction_snapshot
                    )
                self._latest_full_field_prediction_observation = (
                    prior_prediction_observation
                )
                self._latest_causal_settlement = prior_latest_settlement
                self._causal_settlement_accepted = prior_accepted
                raise
            return {
                "action_selection_receipt_sha256": (
                    selection.authority_receipt_sha256
                ),
                "experience_receipt_sha256": (
                    tutoring_observation[
                        "experience_receipt_sha256"
                    ]
                ),
                "outcome_settlement_receipt_sha256": (
                    outcome.authority_receipt_sha256
                ),
                "physical_dimensions": (
                    selection.physical_dimensions.record()
                ),
                "schema": (
                    "guala.custody_native_tutoring."
                    "action_result.v1"
                ),
                "state": (
                    "resolved"
                    if target_observed
                    else "lived_but_target_unresolved"
                ),
                "target_relation": opportunity.target_relation,
                "target_sense": opportunity.target_sense,
                "thing_id": opportunity.thing_id,
                "world_execution_receipt_sha256": (
                    execution.authority_receipt_sha256
                ),
            }

    @_engine_mutation_entry
    def record_live_visual_rejection(self, *, error_type, reason):
        """Publish a bounded transport rejection without admitting sight."""
        if not isinstance(error_type, str) or not error_type:
            raise ValueError("visual rejection error type is required")
        if not isinstance(reason, str) or not reason:
            raise ValueError("visual rejection reason is required")
        if len(error_type.encode("utf-8")) > 128 or len(
            reason.encode("utf-8")
        ) > 1024:
            raise ValueError("visual rejection description exceeds its boundary")
        self._latest_visual_region_rejection = {
            "schema": "guala.visual_region_rejection.v1",
            "error_type": error_type,
            "reason": reason,
        }
        return dict(self._latest_visual_region_rejection)

    @_engine_mutation_entry
    @_live_sensory_entry
    def process_live_visual_region_sequence(
        self,
        frames,
        *,
        source_time_start_ns=None,
        source_time_end_ns=None,
        auditory_pcm_continuity=None,
    ):
        """Bind one complete temporal camera field as one atomic window fact.

        Preparation retains every declared 8x8 receptor trajectory and is
        pure.  Region continuity is committed later, from the single combined
        verified L4 settlement in ``_build_causal_window_settlement``.  The
        legacy random-fovea visual motif path is deliberately absent.
        """
        authority = self._visual_region_continuity
        if authority is None:
            raise RuntimeError("visual region continuity authority is unavailable")
        prior_visual_rejection = self._latest_visual_region_rejection
        settlement_started = False
        try:
            canonical_frames = tuple(frames)
            prepared = authority.prepare_retinotopic_inputs(canonical_frames)
            exposure_evidence = None
            if auditory_pcm_continuity is not None:
                if self._visual_exposure_epoch is None:
                    raise RuntimeError(
                        "visual exposure epoch authority is unavailable"
                    )
                exposure_evidence = self._visual_exposure_epoch.prepare(
                    auditory=auditory_pcm_continuity,
                    frame_receipt_sha256s=prepared.frame_receipt_sha256s,
                    preparation_receipt_sha256=(
                        prepared.preparation_receipt_sha256
                    ),
                )
            frame_times_ns = tuple(
                value.source_time_ns for value in canonical_frames
            )
            if not frame_times_ns:
                raise ValueError("visual sequence is empty")
            if source_time_start_ns is None:
                source_time_start_ns = int(
                    prepared.source_time_start * 1_000_000_000
                )
            if source_time_end_ns is None:
                source_time_end_ns = frame_times_ns[-1]
            if (
                isinstance(source_time_start_ns, bool)
                or not isinstance(source_time_start_ns, int)
                or isinstance(source_time_end_ns, bool)
                or not isinstance(source_time_end_ns, int)
                or source_time_end_ns <= source_time_start_ns
                or frame_times_ns[0] < source_time_start_ns
                or frame_times_ns[-1] > source_time_end_ns
            ):
                raise ValueError(
                    "visual sequence lies outside its authoritative interval"
                )
            native_records = prepared.native_records()
            context_id = self.window_manager.active_context_id
            owns_context = context_id is None
            if owns_context:
                context_id = f"sense:sight:retina:{time.time_ns():x}"
                self.window_manager.begin_context(
                    context_id,
                    "sight",
                    context_detail={
                        "experience_origin": "live_retinotopic_sight",
                        "source_time_start_ns": source_time_start_ns,
                        "source_time_end_ns": source_time_end_ns,
                        "sensor_unavailable": [
                            "sound", "touch", "smell", "taste", "body"
                        ],
                    },
                )
            try:
                self.window_manager.add_entry(
                    modality="sight",
                    topology=physical_topology_fact(list(native_records)),
                    full_field=list(native_records),
                    tick=self.tick,
                    source_tag="camera:live-retina",
                    context_id=context_id,
                    detail={
                        "visual_preparation_receipt_sha256": (
                            prepared.preparation_receipt_sha256
                        ),
                        "visual_exposure_epoch_evidence": (
                            exposure_evidence.as_record()
                            if exposure_evidence is not None
                            else None
                        ),
                    },
                )
                if owns_context:
                    settlement_started = True
                    closed_window_id, settlement = self.window_manager.end_context(
                        context_id,
                        "visual_region_sequence_complete",
                        return_settlement=True,
                    )
                else:
                    closed_window_id, settlement = None, None
            except Exception:
                if owns_context:
                    self.window_manager.discard_unsettled_context(
                        context_id, "visual_region_sequence_failed"
                    )
                raise
            self._last_frame_tick = self.tick
            articulatory_act = None
            articulatory_observation = {
                "reason": (
                    "camera_sequence_is_part_of_an_open_audiovisual_window"
                    if settlement is None
                    else "physical_response_authority_unavailable"
                ),
                "schema": (
                    "guala.live_visual."
                    "articulatory_response_observation.v1"
                ),
                "state": (
                    "not_applicable"
                    if settlement is None
                    else "unavailable"
                ),
            }
            if (
                settlement is not None
                and self._retained_audiovisual_custody is not None
            ):
                raise RuntimeError(
                    "legacy retained-sight cognition is permanently retired; "
                    "native exact-field settlement remains authoritative"
                )
                retained_sight = (
                    self._retained_audiovisual_custody.admit(
                        settlement=settlement,
                        frame_sha256s=(
                            prepared.frame_receipt_sha256s
                        ),
                        canonical_audio_sha256=None,
                    )
                )
                grounding_capability = (
                    self._retained_audiovisual_custody.issue_child(
                        retained_sight,
                        THING_SENSORY_EXPANSION_CONSUMER_ID,
                    )
                )
                self._latest_live_sight_custody = (
                    retained_sight,
                    grounding_capability,
                )
                if (
                    self._consequence_evoked_articulatory_response
                    is not None
                ):
                    response_capability = (
                        self._retained_audiovisual_custody.issue_child(
                            retained_sight,
                            (
                                RETAINED_VISUAL_ARTICULATORY_RESPONSE_CONSUMER_ID
                            ),
                        )
                    )
                    try:
                        response_result = (
                            self
                            ._consequence_evoked_articulatory_response
                            .respond(
                                custody_authority=(
                                    self._retained_audiovisual_custody
                                ),
                                custody_capability=response_capability,
                            )
                        )
                    except BaseException as response_error:
                        error_detail = str(response_error)
                        encoded_detail = error_detail.encode("utf-8")
                        articulatory_observation = {
                            "error_detail_sha256": (
                                _hashlib.sha256(
                                    encoded_detail
                                ).hexdigest()
                            ),
                            "error_type": type(response_error).__name__,
                            "reason": (
                                error_detail
                                if len(encoded_detail) <= 1024
                                else encoded_detail[:1024].decode(
                                    "utf-8",
                                    errors="replace",
                                )
                            ),
                            "reason_truncated": (
                                len(encoded_detail) > 1024
                            ),
                            "schema": (
                                "guala.live_visual."
                                "articulatory_response_observation.v1"
                            ),
                            "state": "error",
                        }
                    else:
                        response = (
                            response_result.response
                            if isinstance(
                                response_result,
                                CommittedConsequenceEvokedArticulatoryAct,
                            )
                            else response_result
                        )
                        self._latest_sight_evoked_articulatory_occurrence = (
                            response_result
                        )
                        articulatory_observation = {
                            "response_authority_receipt_sha256": (
                                response.authority_receipt_sha256
                            ),
                            "schema": (
                                "guala.live_visual."
                                "articulatory_response_observation.v1"
                            ),
                            "state": response.state,
                            "thing_ids": list(response.thing_ids),
                        }
                        if isinstance(
                            response_result,
                            CommittedConsequenceEvokedArticulatoryAct,
                        ):
                            articulatory_act = response_result
            result = {
                "accepted": True,
                "articulatory_response": articulatory_observation,
                "entries_bound": 1,
                "receptor_count": len(native_records),
                "preparation_receipt_sha256": (
                    prepared.preparation_receipt_sha256
                ),
                "context_id": context_id,
                "closed_window_id": closed_window_id,
                "settlement": settlement,
                "visual_region": self._latest_visual_region_observation,
            }
            if articulatory_act is not None:
                result["articulatory_act"] = articulatory_act
            return result
        except Exception as error:
            if settlement_started:
                self._latest_visual_region_rejection = prior_visual_rejection
            else:
                error_type = type(error).__name__
                reason = str(error)
                if len(error_type.encode("utf-8")) > 128:
                    error_type = "VisualRejection"
                if len(reason.encode("utf-8")) > 1024:
                    reason = (
                        "visual rejection description exceeded its telemetry "
                        "boundary"
                    )
                self._latest_visual_region_rejection = {
                    "schema": "guala.visual_region_rejection.v1",
                    "error_type": error_type,
                    "reason": reason,
                }
            raise

    @_engine_mutation_entry
    @_live_sensory_entry
    def process_sight_frame(
            self, grid, source_anchor_ns=None, source_time_start_ns=None,
            source_time_end_ns=None):
        """GL-BRIEF-SENSORY-IO Part C: feed a transient camera frame into
        sight krimelack. No PictureItem, no storage. Just krimelack + atlas.

        GL-CMD-LOCK-CONTENTION-FIX-182 L1: view_picture() (the saccade/
        fixation simulation) touches no shared state -- fresh, local
        SaccadeController + AdaptingFoveaKrimelack per call -- so it now
        runs OUTSIDE self.lock. Measured live holding the lock for up to
        ~93s per call while camera+mic streamed continuously, starving
        converse() and everything else that needs self.lock. Only the
        actual state write (process_viewing's motif update/commit,
        _atlas_record, the event log) stays inside, and that lock is now
        bounded to just that write."""
        if source_anchor_ns is None:
            source_anchor_ns = time.time_ns()
        if (isinstance(source_anchor_ns, bool)
                or not isinstance(source_anchor_ns, int)):
            raise ValueError("sight source anchor must be integer nanoseconds")
        interval_supplied = (
            source_time_start_ns is not None or source_time_end_ns is not None)
        if interval_supplied:
            if (isinstance(source_time_start_ns, bool)
                    or not isinstance(source_time_start_ns, int)
                    or isinstance(source_time_end_ns, bool)
                    or not isinstance(source_time_end_ns, int)
                    or source_time_end_ns <= source_time_start_ns
                    or source_anchor_ns < source_time_start_ns
                    or source_anchor_ns >= source_time_end_ns):
                raise ValueError(
                    "sight source interval must contain its source anchor")
        _source_started_ns = source_anchor_ns
        _tick_snapshot = self.tick
        from dsf_ai_service.visual_krimelack import (
            view_picture,
            visual_fragment_receipt,
        )
        fragments = view_picture(grid, source_id="camera_stream",
                                 born_tick=_tick_snapshot, seed=_tick_snapshot % 10000,
                                 n_fixations=(
                                     LIVE_CAMERA_FIXATION_SUBSTREAM_COUNT
                                 ), ticks_per_fixation=50)
        if not fragments:
            return
        visual_offsets_ns = tuple(
            int(item["t"] - _tick_snapshot) * 20_000_000
            for fragment in fragments for item in fragment.signal_records)
        if interval_supplied and (
                source_anchor_ns + min(visual_offsets_ns)
                < source_time_start_ns
                or source_anchor_ns + max(visual_offsets_ns)
                > source_time_end_ns):
            raise ValueError(
                "sight foveation falls outside the authoritative causal interval")

        self._last_frame_tick = _tick_snapshot
        # GL-CMD-SENSES-TO-BRAIN-EVE-20260705-191 N1: real signal, not
        # synthesized -- a bounded subsample of her ACTUAL camera frame
        # (real pixel intensities), cached only after the producer proves its
        # full unmodified foveation timeline fits the causal interval.
        try:
            _flat = np.asarray(grid).ravel()
            _step = max(1, len(_flat) // 100)
            self._last_sight_signal = _flat[::_step][:100].copy()
            self._last_sight_wall_time = time.time()
        except Exception as _sfe:
            print(f"[GualaLoom] process_sight_frame: sight signal cache failed "
                  f"(non-fatal, senses stay honestly absent): {_sfe}")
        # GL-RPT-WAL-BLOAT F2 (2026-07-15): explicit per-frame context, same
        # reasoning as process_sound_frame below -- the implicit-context
        # fallback leaked one never-closable open context per camera-frame
        # job (app.py's per-job contextvar isolation discards the only
        # binding that could have closed it).
        # A per-frame context applies only when no caller-owned causal
        # experience is bound. A timed audiovisual capture owns one enclosing
        # context, so its sight fragments and sound ports settle together.
        # The frame path closes only contexts it created itself.
        _bound_experience = self.window_manager.active_context_id
        _frame_context_id = (
            _bound_experience if _bound_experience is not None
            else f"sense:sight:camera_stream:{time.time_ns():x}")
        _frame_owns_context = _bound_experience is None
        if _frame_owns_context:
            self.window_manager.begin_context(
                _frame_context_id,
                "sight",
                context_detail={
                    "experience_origin": "live_sight",
                    "source_time_start_ns": _source_started_ns,
                    "source_time_end_ns": (
                        _source_started_ns
                        + sum(len(value.signal_records) for value in fragments)
                        * 20_000_000),
                    "sensor_unavailable": [
                        "sound", "touch", "smell", "taste", "body"],
                },
            )
        _frame_entries_bound = 0
        try:
            with self.lock:
                # The former SightSection reduced these complete receptor
                # fragments to normalized chi bins and a tuned overlap
                # threshold.  That reduced proxy is not visual identity.
                # Preserve every native receptor record and leave identity
                # unavailable until a full-field causal relation grows.
                derived_transition = None
                for topology_index, fragment in enumerate(fragments):
                    native_full_field_input = {
                        "schema": "guala.native_sensory_input.v1",
                        "sense": "sight",
                        "sensor_id": "camera-fovea",
                        "substream_id": f"fixation-{topology_index}",
                        "topology_index": topology_index,
                        "coordinates": [
                            ["fixation-row", str(int(
                                fragment.fixation_coord[0]))],
                            ["fixation-column", str(int(
                                fragment.fixation_coord[1]))],
                        ],
                        "physical_quantity": "light-intensity",
                        "physical_unit": "normalized-intensity",
                        "source_anchor_ns": source_anchor_ns,
                        "causal_offsets_ns": [
                            int(item["t"] - _tick_snapshot) * 20_000_000
                            for item in fragment.signal_records
                        ],
                        "normalized_signal": [
                            float(item["s"])
                            for item in fragment.signal_records
                        ],
                        "phase_turns": [
                            int(item["phase_turns"])
                            for item in fragment.signal_records
                        ],
                    }
                    self.window_manager.add_entry(
                        modality="sight",
                        topology=physical_topology_fact(
                            native_full_field_input
                        ),
                        full_field=native_full_field_input,
                        tick=self.tick,
                        source_tag="cam:live",
                        context_id=_frame_context_id,
                        detail={
                            "source_tick": _tick_snapshot,
                            "derived_visual_transition": derived_transition,
                        },
                    )
                    _frame_entries_bound += 1
                self._log_substrate_event(
                    "sight_frame_bound",
                    motif_id=None,
                    fragment_count=len(fragments),
                    is_new=False,
                    visual_identity="unavailable_full_field_grounding_pending",
                )
        finally:
            # Close OUTSIDE self.lock (WAL fsync; see process_sound_frame).
            # Never close a caller-owned bound experience -- its owner ends
            # it at the experience's real boundary.
            # F4 (review 2026-07-16): close on "I created it", not "I bound
            # entries" -- add_entry creates the context BEFORE entry
            # validation, so a first-entry validation raise left an open
            # context forever under the entries>0 gate.  end_context on a
            # context that was never created is a benign no-op (None).
            if _frame_owns_context:
                _closed_window_id, _settlement = (
                    self.window_manager.end_context(
                        _frame_context_id,
                        "sight_frame_complete",
                        return_settlement=True,
                    )
                )
            else:
                _closed_window_id = None
                _settlement = None
        return {
            "accepted": _frame_entries_bound > 0,
            "entries_bound": _frame_entries_bound,
            "context_id": _frame_context_id,
            "closed_window_id": _closed_window_id,
            "settlement": _settlement,
        }





    def _settle_auditory_recurrent_motif_terminal(self, stream_id):
        pending = self._auditory_receptor_terminal_by_stream.pop(
            stream_id,
            None,
        )
        bridge_only = (
            stream_id in self._auditory_receptor_bridge_streams
            and isinstance(pending, list)
            and len(pending) == 1
        )
        self._auditory_receptor_bridge_streams.discard(stream_id)
        if bridge_only:
            return None
        if not pending or isinstance(pending, str):
            return None
        from dsf_ai_service.substrate.auditory_live_motif import (
            build_live_motif_result,
        )
        from dsf_ai_service.substrate.auditory_recurrent_motif import (
            compose_contiguous_receptor_experiences,
        )
        for index, (
            transport,
            joint,
            _experience,
            causal_settlement,
        ) in enumerate(pending):
            transport.verify()
            joint.verify()
            causal_settlement.verify()
            if (
                transport.stream_id != stream_id
                or joint.stream_id != stream_id
                or joint.transport_receipt_sha256
                != transport.receipt_sha256
            ):
                raise ValueError(
                    "auditory motif terminal belongs to another stream"
                )
            if index:
                (
                    prior_transport,
                    prior_joint,
                    _prior_experience,
                    _prior_settlement,
                ) = (
                    pending[index - 1]
                )
                if (
                    transport.sequence != prior_transport.sequence + 1
                    or transport.first_sample_index
                    != (
                        prior_transport.first_sample_index
                        + prior_transport.sample_count
                    )
                    or joint.prior_transport_receipt_sha256
                    != prior_transport.receipt_sha256
                    or joint.prior_cochlear_state_receipt_sha256
                    != prior_joint.cochlear_receipt_sha256
                    or joint.source_time_start != prior_joint.source_time_end
                ):
                    raise ValueError(
                        "auditory motif terminal continuity changed"
                    )
        composed = compose_contiguous_receptor_experiences(
            tuple(value[2] for value in pending),
            continuity_receipt_sha256s=tuple(
                value[1].authority_receipt_sha256
                for value in pending
            ),
        )
        prepared = self._auditory_recurrent_motif_owner.prepare(
            composed
        )
        try:
            firing = self._auditory_recurrent_motif_owner.fire(prepared)
            observation = self._auditory_recurrent_motif_owner.observe(
                prepared
            )
        finally:
            self._auditory_recurrent_motif_owner.discard_prepared(
                prepared
            )
        result = build_live_motif_result(
            experience=composed,
            firing=firing,
            observation=observation,
        )
        self._latest_auditory_recurrent_motif = result
        self._latest_auditory_recurrent_motif_experience = composed
        self._latest_auditory_recurrent_motif_settlement = pending[-1][3]
        return result

    @_engine_mutation_entry
    def close_auditory_pcm_stream(self, stream_id, *, release_terminal=True):
        """Close one stream and discard transient auditory composition state."""
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("auditory PCM stream id is required")
        with self._auditory_terminal_pipeline_lock:
            in_flight = self._auditory_terminal_pipeline_in_flight
            if (
                any(
                    value.transport.stream_id == stream_id
                    for value
                    in self._auditory_terminal_pipeline_pending.values()
                )
                or (
                    in_flight is not None
                    and in_flight.transport.stream_id == stream_id
                )
            ):
                raise RuntimeError(
                    "auditory PCM stream has unsettled terminal tasks"
                )
        motif_terminal = (
            self._settle_auditory_recurrent_motif_terminal(stream_id)
            if release_terminal
            else None
        )
        if not release_terminal:
            self._auditory_receptor_terminal_by_stream.pop(
                stream_id,
                None,
            )
            self._auditory_receptor_bridge_streams.discard(stream_id)
        self._auditory_full_field_transactions.close_stream(stream_id)
        with self._auditory_terminal_worker_lock:
            if self._auditory_q_process_owner is not None:
                self._auditory_q_process_committed_state = (
                    self._auditory_q_process_owner.close_stream(stream_id)
                )
            elif self._auditory_q_process_committed_state is not None:
                self._auditory_q_process_committed_state = (
                    self._auditory_q_process_committed_state.without_stream(
                        stream_id
                    )
                )
            self._auditory_q_pending_by_stream.pop(stream_id, None)
            self._auditory_q_process_cached_through.pop(stream_id, None)
        field_closed = self._auditory_full_field_streams.close(stream_id)
        with self._auditory_transaction_lock:
            for receipt_sha256, value in tuple(
                self._auditory_capture_authorities.items()
            ):
                if value[0].stream_id == stream_id:
                    del self._auditory_capture_authorities[receipt_sha256]
                    self._auditory_prediction_joint_by_transport.pop(
                        receipt_sha256,
                        None,
                    )
                    self._auditory_verified_capability_by_transport.pop(
                        receipt_sha256,
                        None,
                    )
            if self._live_anonymous_encounter_continuity is not None:
                self._live_anonymous_encounter_continuity.clear_stream(
                    stream_id
                )
            if self._visual_exposure_epoch is not None:
                self._visual_exposure_epoch.clear(stream_id)
        self._latest_auditory_incremental_advance = None
        with self._auditory_terminal_pipeline_lock:
            for key in tuple(self._auditory_terminal_pipeline_results):
                if key[0] == stream_id:
                    del self._auditory_terminal_pipeline_results[key]
            for key in tuple(self._auditory_terminal_pipeline_failures):
                if key[0] == stream_id:
                    del self._auditory_terminal_pipeline_failures[key]
            for key in tuple(self._auditory_terminal_pipeline_receipts):
                if key[0] == stream_id:
                    del self._auditory_terminal_pipeline_receipts[key]
            self._auditory_terminal_pipeline_last_admitted.pop(
                stream_id,
                None,
            )
            self._auditory_terminal_pipeline_last_settled.pop(
                stream_id,
                None,
            )
        return {
            "closed": (
                field_closed
                or motif_terminal is not None
            ),
            "terminal": motif_terminal,
        }

    def reject_auditory_pcm_stream(self, stream_id):
        """Drain accepted terminal custody, then reject one broken stream."""
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("auditory PCM rejection stream id is required")
        pipeline_status = self.wait_for_auditory_terminal_pipeline()
        observed = self.poll_continuous_auditory_terminals(
            stream_id=stream_id,
            after_sequence=-1,
        )
        acknowledged_sequences = [
            value["sequence"] for value in observed["results"]
        ] + [
            value["sequence"] for value in observed["failures"]
        ]
        if acknowledged_sequences:
            self.poll_continuous_auditory_terminals(
                stream_id=stream_id,
                after_sequence=max(acknowledged_sequences),
            )
        closed = self.close_auditory_pcm_stream(
            stream_id,
            release_terminal=False,
        )
        return {
            "closed": closed["closed"],
            "pipeline_failures": observed["failures"],
            "pipeline_status": pipeline_status,
            "schema": "guala.auditory.rejected_pcm_stream.v1",
            "settled_result_count": len(observed["results"]),
            "stream_id": stream_id,
        }

    @_engine_mutation_entry
    def submit_continuous_auditory_terminal(
            self, *, pcm_s16le, transport, settlement):
        """Admit one immutable terminal task to the ordered finite pipeline."""
        from dsf_ai_service.substrate.auditory_terminal_pipeline import (
            AuditoryTerminalAdmission,
            AuditoryTerminalTask,
        )
        from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
            AuditoryReceptorEventState,
            settle_auditory_receptor_event,
        )

        with self._auditory_terminal_pipeline_lock:
            existing = next(
                (
                    value
                    for value
                    in self._auditory_terminal_pipeline_receipts.values()
                    if (
                        value.transport.receipt_sha256
                        == transport.receipt_sha256
                    )
                ),
                None,
            )
            if existing is not None:
                if (
                    existing.transport != transport
                    or existing.pcm_s16le != pcm_s16le
                    or existing.settlement != settlement
                ):
                    raise ValueError(
                        "auditory terminal replay changed admitted authority"
                    )
                return AuditoryTerminalAdmission.create(
                    state="queued",
                    stream_id=transport.stream_id,
                    sequence=transport.sequence,
                    task_id=existing.task_id,
                    pending_count=(
                        len(self._auditory_terminal_pipeline_pending)
                        + int(
                            self._auditory_terminal_pipeline_in_flight
                            is not None
                        )
                    ),
                    capacity=self._auditory_transaction_capacity,
                    reason="exact auditory terminal task is already admitted",
                )
        with self._auditory_transaction_lock:
            mounted_capture = self._auditory_capture_authorities.get(
                transport.receipt_sha256
            )
            auditory_l5 = self._auditory_l5_by_assembly.get(
                settlement.assembly_id
            )
            joint_settlement = (
                self._auditory_prediction_joint_by_transport.get(
                    transport.receipt_sha256
                )
            )
            verified_capability = (
                self._auditory_verified_capability_by_transport.get(
                    transport.receipt_sha256
                )
            )
        if (
            mounted_capture is None
            or auditory_l5 is None
            or joint_settlement is None
            or verified_capability is None
        ):
            raise RuntimeError(
                "auditory terminal pipeline lacks full-field authority"
            )
        mounted_transport, capture, _cochlear, mounted_pcm = mounted_capture
        if (
            mounted_transport is not transport
            or mounted_pcm is not pcm_s16le
        ):
            raise RuntimeError(
                "auditory terminal pipeline transfer identity changed"
            )
        verified_capability.verify_linkage(
            pcm_s16le=pcm_s16le,
            capture=capture,
            auditory_l5=auditory_l5,
            transport=transport,
            cochlear=_cochlear,
            causal_settlement=settlement,
            joint_settlement=joint_settlement,
        )
        verified_causal_transaction = (
            verified_capability.verified_causal_transaction
        )
        if verified_causal_transaction is not None:
            verified_causal_transaction.verify_linkage(settlement)
        receptor_boundary = settle_auditory_receptor_event(
            capture=capture,
            auditory_l5=auditory_l5,
            verified_settlement_capability=verified_capability,
        )
        if (
            receptor_boundary.state is not AuditoryReceptorEventState.OBSERVED
            or receptor_boundary.event is None
            or receptor_boundary.verified_capability is None
        ):
            raise RuntimeError(
                "auditory terminal pipeline full-field event unresolved: "
                f"{receptor_boundary.reason}"
            )
        task = AuditoryTerminalTask.create_from_verified_custody(
            pcm_s16le=pcm_s16le,
            transport=transport,
            joint_settlement=joint_settlement,
            full_field_event=receptor_boundary.event,
            settlement=settlement,
            receptor_capability=receptor_boundary.verified_capability,
            settlement_capability=verified_capability,
        )
        capacity = self._auditory_transaction_capacity
        start_worker = False
        prior_admitted = None
        with self._auditory_terminal_pipeline_lock:
            existing = self._auditory_terminal_pipeline_receipts.get(
                (transport.stream_id, transport.sequence)
            )
            if existing is not None:
                if existing != task:
                    raise ValueError(
                        "auditory terminal replay changed admitted task"
                    )
                return AuditoryTerminalAdmission.create(
                    state="queued",
                    stream_id=transport.stream_id,
                    sequence=transport.sequence,
                    task_id=task.task_id,
                    pending_count=(
                        len(self._auditory_terminal_pipeline_pending)
                        + int(
                            self._auditory_terminal_pipeline_in_flight
                            is not None
                        )
                    ),
                    capacity=capacity,
                    reason="exact auditory terminal task is already admitted",
                )
            occupied = (
                len(self._auditory_terminal_pipeline_pending)
                + int(
                    self._auditory_terminal_pipeline_in_flight is not None
                )
                + len(self._auditory_terminal_pipeline_results)
                + len(self._auditory_terminal_pipeline_failures)
            )
            if occupied >= capacity:
                return AuditoryTerminalAdmission.create(
                    state="indeterminate_capacity",
                    stream_id=transport.stream_id,
                    sequence=transport.sequence,
                    task_id=None,
                    pending_count=occupied,
                    capacity=capacity,
                    reason=(
                        "bounded auditory terminal pipeline is full; "
                        "the exact task remains unadmitted"
                    ),
                )
            prior_admitted = (
                self._auditory_terminal_pipeline_last_admitted.get(
                    transport.stream_id
                )
            )
            if prior_admitted is None:
                if transport.sequence != 0:
                    raise ValueError(
                        "auditory terminal pipeline begins without sequence zero"
                    )
            elif (
                transport.sequence != prior_admitted.sequence + 1
                or transport.first_sample_index
                != (
                    prior_admitted.first_sample_index
                    + prior_admitted.sample_count
                )
                or transport.prior_receipt_sha256
                != prior_admitted.receipt_sha256
            ):
                raise ValueError(
                    "auditory terminal pipeline continuity changed"
                )
            self._auditory_terminal_pipeline_pending[task.task_id] = task
            self._auditory_terminal_pipeline_receipts[
                (transport.stream_id, transport.sequence)
            ] = task
            with self._auditory_transaction_lock:
                if (
                    self._auditory_capture_authorities.get(
                        transport.receipt_sha256
                    )
                    is not mounted_capture
                    or self._auditory_l5_by_assembly.get(
                        settlement.assembly_id
                    )
                    is not auditory_l5
                    or self._auditory_prediction_joint_by_transport.get(
                        transport.receipt_sha256
                    )
                    is not joint_settlement
                    or self._auditory_verified_capability_by_transport.get(
                        transport.receipt_sha256
                    )
                    is not verified_capability
                ):
                    self._auditory_terminal_pipeline_pending.pop(
                        task.task_id
                    )
                    self._auditory_terminal_pipeline_receipts.pop(
                        (transport.stream_id, transport.sequence),
                        None,
                    )
                    raise RuntimeError(
                        "auditory terminal pipeline transfer left custody"
                    )
                del self._auditory_capture_authorities[
                    transport.receipt_sha256
                ]
                del self._auditory_l5_by_assembly[settlement.assembly_id]
                del self._auditory_prediction_joint_by_transport[
                    transport.receipt_sha256
                ]
                del self._auditory_verified_capability_by_transport[
                    transport.receipt_sha256
                ]
                self._auditory_terminal_pipeline_capabilities[
                    task.task_id
                ] = (
                    mounted_capture,
                    auditory_l5,
                    joint_settlement,
                    verified_capability,
                    receptor_boundary.verified_capability,
                )
            self._auditory_terminal_pipeline_last_admitted[
                transport.stream_id
            ] = transport
            self._auditory_terminal_pipeline_admitted_count += 1
            if not self._auditory_terminal_pipeline_worker_active:
                self._auditory_terminal_pipeline_worker_active = True
                self._auditory_terminal_pipeline_worker_error = None
                start_worker = True
            admission = AuditoryTerminalAdmission.create(
                state="queued",
                stream_id=transport.stream_id,
                sequence=transport.sequence,
                task_id=task.task_id,
                pending_count=occupied + 1,
                capacity=capacity,
                    reason=(
                    "immutable full-field terminal task admitted in exact order"
                ),
            )
        if start_worker:
            try:
                worker_thread = self._start_engine_background_thread(
                    self._drain_auditory_terminal_pipeline,
                    daemon=True,
                    name="auditory-full-field-terminal-pipeline",
                )
                with self._auditory_terminal_pipeline_lock:
                    self._auditory_terminal_pipeline_thread = worker_thread
            except BaseException:
                with self._auditory_terminal_pipeline_lock:
                    self._auditory_terminal_pipeline_pending.pop(
                        task.task_id,
                        None,
                    )
                    self._auditory_terminal_pipeline_receipts.pop(
                        (transport.stream_id, transport.sequence),
                        None,
                    )
                    capability = (
                        self._auditory_terminal_pipeline_capabilities.pop(
                            task.task_id,
                            None,
                        )
                    )
                    if capability is not None:
                        (
                            restored_capture,
                            restored_l5,
                            restored_joint,
                            restored_verified,
                            _restored_receptor_capability,
                        ) = capability
                        with self._auditory_transaction_lock:
                            self._auditory_capture_authorities[
                                transport.receipt_sha256
                            ] = restored_capture
                            self._auditory_l5_by_assembly[
                                settlement.assembly_id
                            ] = restored_l5
                            self._auditory_prediction_joint_by_transport[
                                transport.receipt_sha256
                            ] = restored_joint
                            self._auditory_verified_capability_by_transport[
                                transport.receipt_sha256
                            ] = restored_verified
                    if prior_admitted is None:
                        self._auditory_terminal_pipeline_last_admitted.pop(
                            transport.stream_id,
                            None,
                        )
                    else:
                        self._auditory_terminal_pipeline_last_admitted[
                            transport.stream_id
                        ] = prior_admitted
                    self._auditory_terminal_pipeline_worker_active = False
                    self._auditory_terminal_pipeline_admitted_count -= 1
                raise
        return admission

    def synchronize_auditory_q_process_state(self):
        """Copy the drained process-owned q bank into persistence authority."""
        with self._auditory_terminal_pipeline_lock:
            if (
                self._auditory_terminal_pipeline_pending
                or self._auditory_terminal_pipeline_in_flight is not None
                or self._auditory_terminal_pipeline_worker_active
            ):
                raise RuntimeError(
                    "auditory q state cannot synchronize before pipeline drain"
                )
        with self._auditory_terminal_worker_lock:
            committed_state = self._auditory_q_process_committed_state
            if committed_state is None:
                return False
            committed_state.verify()
            from dsf_ai_service.substrate.auditory_recurrent_motif import (
                AuditoryRecurrentMotifOwner,
            )
            restored = AuditoryRecurrentMotifOwner.restore_encoded(
                committed_state.owner_state
            )
            self._auditory_recurrent_motif_owner = restored
            self._auditory_q_process_status = restored.status()
            return True

    def retain_latest_auditory_temporal_exposure(
        self,
        exposure_receipt_sha256,
    ):
        """Persist the latest full q activation witness for later learning."""

        self.wait_for_auditory_terminal_pipeline()
        with self._auditory_terminal_worker_lock:
            owner = self._auditory_q_process_owner
            if owner is None:
                raise RuntimeError(
                    "auditory temporal retention has no live q owner"
                )
            state = owner.retain_temporal_exposure(
                exposure_receipt_sha256
            )
            self._auditory_q_process_committed_state = state
            return {
                "exposure_receipt_sha256": (
                    exposure_receipt_sha256
                ),
                "schema": (
                    "guala.auditory.temporal_exposure_retention.v1"
                ),
                "temporal_state_sha256": _hashlib.sha256(
                    state.temporal_state
                ).hexdigest(),
            }

    def learn_auditory_temporal_acoustic_contrast(
        self,
        *,
        positive_exposure_receipt_sha256s,
        contrast_exposure_receipt_sha256s,
    ):
        """Learn one exact presemantic ordered acoustic distinction."""

        self.wait_for_auditory_terminal_pipeline()
        with self._auditory_terminal_worker_lock:
            owner = self._auditory_q_process_owner
            if owner is None:
                raise RuntimeError(
                    "auditory temporal learning has no live q owner"
                )
            assembly, state = owner.learn_temporal_acoustic_contrast(
                positive_exposure_receipt_sha256s=tuple(
                    positive_exposure_receipt_sha256s
                ),
                contrast_exposure_receipt_sha256s=tuple(
                    contrast_exposure_receipt_sha256s
                ),
            )
            self._auditory_q_process_committed_state = state
            return assembly

    def poll_continuous_auditory_terminals(
            self, *, stream_id, after_sequence=-1):
        """Return bounded settled results and explicit failures after a cursor."""
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("auditory terminal poll stream id is required")
        if (
            isinstance(after_sequence, bool)
            or not isinstance(after_sequence, int)
            or after_sequence < -1
        ):
            raise ValueError("auditory terminal poll cursor is invalid")
        with self._auditory_terminal_pipeline_lock:
            acknowledged = set()
            for key in tuple(self._auditory_terminal_pipeline_results):
                if key[0] == stream_id and key[1] <= after_sequence:
                    del self._auditory_terminal_pipeline_results[key]
                    acknowledged.add(key)
            for key in tuple(self._auditory_terminal_pipeline_failures):
                if key[0] == stream_id and key[1] <= after_sequence:
                    del self._auditory_terminal_pipeline_failures[key]
                    acknowledged.add(key)
            for key in acknowledged:
                self._auditory_terminal_pipeline_receipts.pop(key, None)
            results = tuple(
                {
                    "auditory_motif": result.as_record(),
                    "auditory_temporal_relations": temporal_firing,
                    "sequence": sequence,
                    "stream_settlement": (
                        joint.payload()
                        | {
                            "authority_receipt_sha256": (
                                joint.authority_receipt_sha256
                            )
                        }
                    ),
                }
                for (
                    result_stream_id,
                    sequence,
                ), (
                    joint,
                    result,
                    temporal_firing,
                )
                in self._auditory_terminal_pipeline_results.items()
                if (
                    result_stream_id == stream_id
                    and sequence > after_sequence
                )
            )
            failures = tuple(
                dict(value)
                for (failure_stream_id, sequence), value
                in self._auditory_terminal_pipeline_failures.items()
                if (
                    failure_stream_id == stream_id
                    and sequence > after_sequence
                )
            )
            in_flight = self._auditory_terminal_pipeline_in_flight
            pending_count = sum(
                value.transport.stream_id == stream_id
                for value in (
                    *self._auditory_terminal_pipeline_pending.values(),
                    *((in_flight,) if in_flight is not None else ()),
                )
            )
        return {
            "failures": list(failures),
            "pending_count": pending_count,
            "results": list(results),
            "schema": "guala.auditory.terminal_pipeline_poll.v1",
            "stream_id": stream_id,
        }

    def auditory_terminal_pipeline_status(self):
        with self._auditory_terminal_pipeline_lock:
            return {
                "admitted_count": (
                    self._auditory_terminal_pipeline_admitted_count
                ),
                "capacity": self._auditory_transaction_capacity,
                "failed_count": self._auditory_terminal_pipeline_failed_count,
                "in_flight": (
                    self._auditory_terminal_pipeline_in_flight is not None
                ),
                "pending_count": len(
                    self._auditory_terminal_pipeline_pending
                ),
                "retained_failure_count": len(
                    self._auditory_terminal_pipeline_failures
                ),
                "retained_result_count": len(
                    self._auditory_terminal_pipeline_results
                ),
                "schema": "guala.auditory.terminal_pipeline_status.v1",
                "settled_count": (
                    self._auditory_terminal_pipeline_settled_count
                ),
                "worker_active": (
                    self._auditory_terminal_pipeline_worker_active
                ),
                "worker_error": (
                    None
                    if self._auditory_terminal_pipeline_worker_error is None
                    else {
                        "error": str(
                            self._auditory_terminal_pipeline_worker_error
                        ),
                        "error_type": type(
                            self._auditory_terminal_pipeline_worker_error
                        ).__name__,
                    }
                ),
            }

    def wait_for_auditory_terminal_pipeline(self):
        """Join the one accepted terminal continuation to final settlement."""
        with self._auditory_terminal_pipeline_lock:
            worker = self._auditory_terminal_pipeline_thread
        if worker is not None and worker is not threading.current_thread():
            worker.join()
        status = self.auditory_terminal_pipeline_status()
        if status["worker_error"] is not None:
            raise RuntimeError(
                "auditory terminal worker failed: "
                f"{status['worker_error']}"
            )
        if (
            status["pending_count"]
            or status["in_flight"]
            or status["worker_active"]
        ):
            raise RuntimeError(
                "auditory terminal worker ended before final settlement: "
                f"{status}"
            )
        return status

    @_engine_mutation_entry
    def advance_continuous_auditory_terminal(
            self, *, pcm_s16le, transport, settlement,
            token_teacher=None):
        """Synchronous compatibility entry for one exact terminal task."""
        return self._advance_continuous_auditory_terminal_inline(
            pcm_s16le=pcm_s16le,
            transport=transport,
            settlement=settlement,
            token_teacher=token_teacher,
        )

    def _advance_continuous_auditory_terminal_inline(
            self, *, pcm_s16le, transport, settlement,
            token_teacher=None, _terminal_task=None):
        """Fire exact motif neurons and stage only explicit terminal learning."""
        from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
            OBSERVATION_HOP_SAMPLES,
        )

        if token_teacher is not None:
            raise RuntimeError(
                "legacy auditory token teaching is retired; tutor designation "
                "cannot designate presemantic motif neurons"
            )
        if (
            transport.first_sample_index % OBSERVATION_HOP_SAMPLES
            or transport.sample_count % OBSERVATION_HOP_SAMPLES
        ):
            self._auditory_receptor_terminal_by_stream.pop(
                transport.stream_id,
                None,
            )
            self._auditory_receptor_bridge_streams.discard(
                transport.stream_id
            )
            raise ValueError(
                "continuous auditory motif intake requires transport boundaries "
                "aligned to complete physical cochlear observation hops"
            )
        terminal_lock = (
            self._auditory_terminal_worker_lock
            if _terminal_task is not None
            else self._auditory_transaction_lock
        )
        with terminal_lock:
            if _terminal_task is None:
                mounted_capture = self._auditory_capture_authorities.get(
                    transport.receipt_sha256
                )
                auditory_l5 = self._auditory_l5_by_assembly.get(
                    settlement.assembly_id
                )
                joint = self._auditory_prediction_joint_by_transport.get(
                    transport.receipt_sha256
                )
                verified_capability = (
                    self._auditory_verified_capability_by_transport.get(
                        transport.receipt_sha256
                    )
                )
            else:
                with self._auditory_terminal_pipeline_lock:
                    transferred = (
                        self._auditory_terminal_pipeline_capabilities.get(
                            _terminal_task.task_id
                        )
                    )
                if transferred is None:
                    raise RuntimeError(
                        "continuous auditory terminal transfer is absent"
                    )
                (
                    mounted_capture,
                    auditory_l5,
                    joint,
                    verified_capability,
                    receptor_capability,
                ) = transferred
            if mounted_capture is None or auditory_l5 is None:
                raise RuntimeError(
                    "continuous auditory terminal lacks full-field authority"
                )
            mounted_transport, capture, cochlear, mounted_pcm = mounted_capture
            if (
                mounted_transport.receipt_sha256 != transport.receipt_sha256
                or mounted_pcm is not pcm_s16le
            ):
                raise RuntimeError(
                    "continuous auditory transport authority changed"
                )
            if joint is None or verified_capability is None:
                raise RuntimeError(
                    "continuous auditory transaction lost verified authority"
                )
            if (
                _terminal_task is not None
                and (
                    _terminal_task.joint_settlement is not joint
                    or _terminal_task.transport is not transport
                    or _terminal_task.settlement is not settlement
                    or _terminal_task.pcm_s16le is not pcm_s16le
                )
            ):
                raise RuntimeError(
                    "continuous auditory terminal transfer changed"
                )
            verified_capability.verify_linkage(
                pcm_s16le=pcm_s16le,
                capture=capture,
                auditory_l5=auditory_l5,
                transport=transport,
                cochlear=cochlear,
                causal_settlement=settlement,
                joint_settlement=joint,
            )
            verified_causal_transaction = (
                verified_capability.verified_causal_transaction
            )
            if verified_causal_transaction is not None:
                verified_causal_transaction.verify_linkage(settlement)
            encounter_snapshot = None
            encounter_owner = self._live_anonymous_encounter_continuity
            if encounter_owner is not None:
                encounter_snapshot = encounter_owner.snapshot_encoded()
            prepared_encounter = None
            full_field_transaction = None
            full_field_claim = None
            try:
                if encounter_owner is not None:
                    visual = self._latest_visual_region_settlement
                    if (
                        visual is not None
                        and visual.assembly_id == joint.assembly_id
                    ):
                        prepared_encounter = encounter_owner.prepare(
                            visual=visual,
                            auditory=joint,
                            causal_settlement=settlement,
                        )
                from dsf_ai_service.substrate.auditory_live_motif import (
                    build_live_motif_result,
                )
                from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
                    AuditoryReceptorEventState,
                    settle_auditory_receptor_event,
                )
                from dsf_ai_service.substrate.auditory_recurrent_motif import (
                    MAX_AUDITORY_RECEPTOR_FRAMES,
                    receptor_experience_from_full_field_event,
                )
                if _terminal_task is None:
                    receptor_boundary = settle_auditory_receptor_event(
                        capture=capture,
                        auditory_l5=auditory_l5,
                        verified_settlement_capability=(
                            verified_capability
                        ),
                    )
                    if (
                        receptor_boundary.state
                        is not AuditoryReceptorEventState.OBSERVED
                        or receptor_boundary.event is None
                        or receptor_boundary.verified_capability is None
                    ):
                        raise RuntimeError(
                            "auditory receptor event unresolved: "
                            f"{receptor_boundary.reason}"
                        )
                    receptor_event = receptor_boundary.event
                    receptor_capability = (
                        receptor_boundary.verified_capability
                    )
                else:
                    receptor_event = _terminal_task.full_field_event
                full_field_transaction = (
                    self._auditory_full_field_transactions.stage(
                        full_field_event=receptor_event,
                        stream_settlement=joint,
                        prepared_causal_settlement=settlement,
                        verified_receptor_capability=(
                            receptor_capability
                        ),
                        verified_settlement_capability=(
                            verified_capability
                        ),
                    )
                )
                full_field_claim = (
                    self._auditory_full_field_transactions.claim(
                        full_field_transaction
                    )
                )
                experience = receptor_experience_from_full_field_event(
                    self._auditory_full_field_transactions
                    .full_field_from_claim(full_field_claim),
                    verified_capability=receptor_capability,
                )
                firing = self._auditory_recurrent_motif_owner.fire(
                    experience
                )
                learning_state = "awaiting_exact_window_composition"
                learning_reason = (
                    "exact continued receptor interval retained within the "
                    "bounded four-unit physical window"
                )
                pending = self._auditory_receptor_terminal_by_stream.get(
                    transport.stream_id
                )
                result = None
                if isinstance(pending, str):
                    learning_state = "cross_transport_learning_unresolved"
                    learning_reason = pending
                else:
                    pending = list(pending or ())
                    if pending:
                        (
                            prior_transport,
                            prior_joint,
                            _prior,
                            _prior_settlement,
                        ) = pending[-1]
                        contiguous = (
                            transport.sequence
                            == prior_transport.sequence + 1
                            and transport.first_sample_index
                            == (
                                prior_transport.first_sample_index
                                + prior_transport.sample_count
                            )
                            and joint.prior_transport_receipt_sha256
                            == prior_transport.receipt_sha256
                            and joint.prior_cochlear_state_receipt_sha256
                            == prior_joint.cochlear_receipt_sha256
                            and joint.source_time_start
                            == prior_joint.source_time_end
                        )
                    else:
                        contiguous = True
                    frame_count = experience.source_frame_count + sum(
                        value[2].source_frame_count for value in pending
                    )
                    if not contiguous:
                        learning_state = (
                            "cross_transport_learning_unresolved"
                        )
                        learning_reason = (
                            "cross_transport_learning_unresolved: exact "
                            "transport or cochlear continuation changed"
                        )
                        self._auditory_receptor_terminal_by_stream[
                            transport.stream_id
                        ] = learning_reason
                        self._auditory_receptor_bridge_streams.discard(
                            transport.stream_id
                        )
                    elif frame_count > MAX_AUDITORY_RECEPTOR_FRAMES:
                        learning_state = (
                            "cross_transport_learning_unresolved"
                        )
                        learning_reason = (
                            "cross_transport_learning_unresolved: receptor "
                            "window frame allocation exhausted"
                        )
                        self._auditory_receptor_terminal_by_stream[
                            transport.stream_id
                        ] = learning_reason
                        self._auditory_receptor_bridge_streams.discard(
                            transport.stream_id
                        )
                    else:
                        if pending:
                            self._auditory_receptor_bridge_streams.discard(
                                transport.stream_id
                            )
                        pending.append((
                            transport,
                            joint,
                            experience,
                            settlement,
                        ))
                        if len(pending) == 4:
                            from dsf_ai_service.substrate.auditory_recurrent_motif import (
                                compose_contiguous_receptor_experiences,
                            )
                            composed = (
                                compose_contiguous_receptor_experiences(
                                    tuple(value[2] for value in pending),
                                    continuity_receipt_sha256s=tuple(
                                        value[1].authority_receipt_sha256
                                        for value in pending
                                    ),
                                )
                            )
                            prepared_composed = (
                                self._auditory_recurrent_motif_owner.prepare(
                                    composed
                                )
                            )
                            try:
                                composed_firing = (
                                    self._auditory_recurrent_motif_owner.fire(
                                        prepared_composed
                                    )
                                )
                                observation = (
                                    self._auditory_recurrent_motif_owner.observe(
                                        prepared_composed
                                    )
                                )
                            finally:
                                self._auditory_recurrent_motif_owner.discard_prepared(
                                    prepared_composed
                                )
                            result = build_live_motif_result(
                                experience=composed,
                                firing=composed_firing,
                                observation=observation,
                            )
                            self._auditory_receptor_terminal_by_stream[
                                transport.stream_id
                            ] = [pending[-1]]
                            self._auditory_receptor_bridge_streams.add(
                                transport.stream_id
                            )
                            self._latest_auditory_recurrent_motif_experience = (
                                composed
                            )
                            self._latest_auditory_recurrent_motif_settlement = (
                                settlement
                            )
                        else:
                            self._auditory_receptor_terminal_by_stream[
                                transport.stream_id
                            ] = pending
                if result is None:
                    result = build_live_motif_result(
                        experience=experience,
                        firing=firing,
                        observation=None,
                        learning_state=learning_state,
                        learning_reason=learning_reason,
                    )
                def commit_full_field_settlement():
                    if encounter_owner is not None:
                        if prepared_encounter is not None:
                            encounter_owner.commit(prepared_encounter)
                        else:
                            encounter_owner.clear_live_continuity()

                self._auditory_full_field_transactions.complete_claim(
                    full_field_claim,
                    commit_settlement=commit_full_field_settlement,
                )
                full_field_claim = None
                full_field_transaction = None
            except BaseException as auditory_error:
                cleanup_errors = []
                if full_field_claim is not None:
                    try:
                        self._auditory_full_field_transactions.rollback_claim(
                            full_field_claim
                        )
                    except BaseException as cleanup_error:
                        cleanup_errors.append(cleanup_error)
                if full_field_transaction is not None:
                    try:
                        self._auditory_full_field_transactions.discard(
                            full_field_transaction
                        )
                    except BaseException as cleanup_error:
                        cleanup_errors.append(cleanup_error)
                if encounter_snapshot is not None:
                    try:
                        encounter_owner.rollback_encoded(encounter_snapshot)
                    except BaseException as cleanup_error:
                        cleanup_errors.append(cleanup_error)
                self._auditory_receptor_terminal_by_stream.pop(
                    transport.stream_id,
                    None,
                )
                self._auditory_receptor_bridge_streams.discard(
                    transport.stream_id
                )
                if cleanup_errors:
                    raise BaseExceptionGroup(
                        "auditory full-field transaction and cleanup failed",
                        [auditory_error, *cleanup_errors],
                    )
                raise auditory_error
            self._latest_auditory_stream_settlement_receipt = joint
            if _terminal_task is None:
                del self._auditory_capture_authorities[
                    transport.receipt_sha256
                ]
                del self._auditory_l5_by_assembly[settlement.assembly_id]
                self._auditory_prediction_joint_by_transport.pop(
                    transport.receipt_sha256,
                    None,
                )
                self._auditory_verified_capability_by_transport.pop(
                    transport.receipt_sha256,
                    None,
                )
            self._latest_auditory_incremental_advance = None
            self._latest_auditory_krimelack_recognition = None
            self._latest_auditory_recurrent_motif = result
            return joint, result

    @_engine_mutation_entry
    @_live_sensory_entry
    def admit_live_audiovisual_thing_sensory_expansion(
        self,
        *,
        settlement,
        frame_receipt_sha256s,
        pcm_s16le,
        auditory_transport,
    ):
        """Retain one live AV field only under already-known sight custody.

        A browser microphone proves one captured pressure mixture, not which
        visible entity produced it.  This bridge therefore cannot create a
        THING, select one from sound, or name an acoustic source.  It may only
        add the complete co-occurring sight/sound roots when the exact sight
        field already resolves one contact-grounded causal THING.
        """
        raise RuntimeError(
            "legacy audiovisual THING cognition is permanently retired; "
            "native exact-field settlement remains authoritative"
        )
        import hashlib

        from dsf_ai_service.substrate.auditory_pcm_stream import (
            AuditoryPCMContinuityReceipt,
        )
        from dsf_ai_service.substrate.exact_causal_experience import (
            CausalExperienceSettlement,
        )
        from dsf_ai_service.substrate.visual_region_continuity import (
            MAX_VISUAL_FRAMES,
            MIN_VISUAL_FRAMES,
        )

        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "live audiovisual sensory expansion requires a causal "
                "settlement"
            )
        settlement.verify()
        if (
            not isinstance(frame_receipt_sha256s, tuple)
            or not (
                MIN_VISUAL_FRAMES
                <= len(frame_receipt_sha256s)
                <= MAX_VISUAL_FRAMES
            )
            or any(
                not isinstance(value, str)
                or len(value) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in value
                )
                for value in frame_receipt_sha256s
            )
        ):
            raise ValueError(
                "live audiovisual frame custody changed"
            )
        if not isinstance(pcm_s16le, bytes) or not pcm_s16le:
            raise ValueError(
                "live audiovisual PCM custody is absent"
            )
        if not isinstance(
            auditory_transport,
            AuditoryPCMContinuityReceipt,
        ):
            raise TypeError(
                "live audiovisual transport custody is not typed"
            )
        auditory_transport.verify()
        pcm_sha256 = hashlib.sha256(pcm_s16le).hexdigest()
        if (
            pcm_sha256 != auditory_transport.pcm_sha256
            or len(pcm_s16le)
            != auditory_transport.sample_count * 2
        ):
            raise ValueError(
                "live audiovisual PCM differs from its transport custody"
            )
        verified = self._continuous_auditory_causal_transaction(
            transport=auditory_transport,
            settlement=settlement,
        )
        if verified is None:
            raise RuntimeError(
                "live audiovisual settlement lacks its auditory causal "
                "transaction"
            )
        verified.verify_linkage(settlement)
        visual = self._latest_visual_region_settlement
        if (
            visual is None
            or self._visual_region_continuity is None
        ):
            raise RuntimeError(
                "live audiovisual settlement lacks visual L5 custody"
            )
        self._visual_region_continuity.verify_settlement(visual)
        if (
            visual.assembly_id != settlement.assembly_id
            or visual.source_time_start != settlement.source_time_start
            or visual.source_time_end != settlement.source_time_end
            or visual.full_field_receipt_sha256
            != settlement.assembly_receipt_sha256
        ):
            raise ValueError(
                "live audiovisual visual custody crossed its causal window"
            )
        observed = {
            interpretation.sense
            for interpretation in settlement.interpretations
            if interpretation.state == "observed"
        }
        if observed != {"sight", "sound"}:
            raise ValueError(
                "live audiovisual sensory expansion requires exact sight "
                "and sound"
            )
        if (
            self._retained_audiovisual_custody is None
            or self._causal_thing_sensory_expansion is None
        ):
            raise RuntimeError(
                "live audiovisual THING sensory custody is unavailable"
            )
        custody = self._retained_audiovisual_custody.admit(
            settlement=settlement,
            frame_sha256s=frame_receipt_sha256s,
            canonical_audio_sha256=pcm_sha256,
        )
        capability = self._retained_audiovisual_custody.issue_child(
            custody,
            THING_SENSORY_EXPANSION_CONSUMER_ID,
        )
        admission = (
            self._admit_known_sight_expansion_with_lived_context(
                custody_authority=self._retained_audiovisual_custody,
                custody_capability=capability,
            )
        )
        self._latest_retained_audiovisual_custody = (
            custody,
            capability,
        )
        self._latest_live_sight_custody = (
            custody,
            capability,
        )
        expansion = admission.expansion
        return {
            "acoustic_source": "unknown",
            "expansion_authority_receipt_sha256": (
                expansion.authority_receipt_sha256
                if expansion is not None else None
            ),
            "meaning_authority": False,
            "schema": (
                "guala.live_audiovisual."
                "thing_sensory_expansion.v1"
            ),
            "source_separation_authority": False,
            "state": admission.state,
            "thing_ids": list(admission.thing_ids),
            "word_recognition_authority": False,
        }

    @staticmethod
    def _lived_contact_sight_grounding_observation(expansion):
        """Project one bounded receipt-only view of physical grounding."""
        senses = sorted({
            root.sense for root in expansion.full_field_roots
        })
        return {
            "admission_basis": expansion.admission_basis,
            "expansion_authority_receipt_sha256": (
                expansion.authority_receipt_sha256
            ),
            "full_field_root_count": len(expansion.full_field_roots),
            "grounding_contact_custody_receipt_sha256": (
                expansion.grounding_contact_custody_receipt_sha256
            ),
            "grounding_contact_settlement_receipt_sha256": (
                expansion.grounding_contact_settlement_receipt_sha256
            ),
            "meaning_authority": False,
            "reduced_approximation": False,
            "schema": (
                "guala.live_sight.lived_contact_grounding."
                "observation.v1"
            ),
            "senses": senses,
            "source_occurrence_id": expansion.source_occurrence_id,
            "state": "grounded",
            "thing_id": expansion.thing_id,
        }

    @_engine_mutation_entry
    @_live_sensory_entry
    def durably_ground_latest_retained_sight_to_contact(
        self,
        *,
        state_dir,
    ):
        """Ground latest retained sight only through current contact custody."""
        raise RuntimeError(
            "legacy retained-sight cognition is permanently retired; "
            "native exact-field settlement remains authoritative"
        )
        if not callable(getattr(
            self,
            "_authoritative_hot_generation_publisher",
            None,
        )):
            raise RuntimeError(
                "authoritative sight grounding durability is unavailable"
            )
        media_authority = self._retained_audiovisual_custody
        expansion_owner = self._causal_thing_sensory_expansion
        physical = self._w1_physical_evidence
        world = self._embodiment_world
        latest = self._latest_live_sight_custody
        if any(
            value is None
            for value in (
                media_authority,
                expansion_owner,
                physical,
                world,
            )
        ):
            raise RuntimeError(
                "lived contact sight grounding authority is unavailable"
            )
        if (
            not isinstance(latest, tuple)
            or len(latest) != 2
        ):
            raise ValueError(
                "no retained live sight occurrence is available"
            )
        media_custody, media_capability = latest
        verified_media = media_authority.open_child(
            media_capability
        )
        if verified_media is not media_custody:
            raise RuntimeError(
                "latest retained sight crossed audiovisual custody"
            )

        def existing_grounding():
            matches = tuple(
                value
                for value in expansion_owner.expansions
                if value.source_occurrence_id
                == media_custody.source_occurrence_id
            )
            if len(matches) > 1:
                raise RuntimeError(
                    "retained sight occurrence crossed sensory expansions"
                )
            return matches[0] if matches else None

        with self.persistence_transaction():
            with self._causal_cycle_bridge_lock:
                existing = existing_grounding()
                if existing is not None:
                    self.save_hot_state(state_dir)
                    return self._lived_contact_sight_grounding_observation(
                        existing
                    )
                prior_expansion = expansion_owner.snapshot_encoded()
                prediction_snapshot = (
                    self._full_field_prediction.encoded_snapshot()
                    if self._full_field_prediction is not None
                    else None
                )
                prior_prediction_intent = (
                    self._prediction_conditioned_intent_receipt
                )
                prior_prediction_binding = (
                    self._prediction_conditioned_binding_id
                )
                prior_prediction_observation = (
                    self._latest_full_field_prediction_observation
                )
                prior_latest_settlement = self._latest_causal_settlement
                prior_accepted = self._causal_settlement_accepted
                prior_live_custody_keys = frozenset(
                    self._live_settled_prediction_custodies
                )
                epoch_token = physical.begin_atomic_episode()
                committed_undo = None
                lived_undo = None
                try:
                    contact_observation = world.observation_snapshot()
                    contact_mount = (
                        physical.mount_authenticated_observation(
                            contact_observation,
                            commit=True,
                        )
                    )
                    if (
                        contact_mount.causal_settlement is None
                        or contact_mount.evidence_receipt is None
                    ):
                        raise RuntimeError(
                            "current contact did not settle W1 custody"
                        )
                    physical.verify_mount(contact_mount)
                    contact_custody = self._settled_prediction_custody(
                        contact_mount,
                        world_observation=contact_observation,
                    )
                    contact_capability = (
                        contact_custody.authority.issue_child(
                            THING_SENSORY_GROUNDING_CONSUMER_ID
                        )
                    )
                    grounded = expansion_owner.admit_lived_contact_tutor(
                        custody_authority=media_authority,
                        custody_capability=media_capability,
                        contact_custody_authority=(
                            contact_custody.authority
                        ),
                        contact_custody_capability=contact_capability,
                    )
                    lived_undo = self._commit_lived_context_expansion(
                        grounded,
                        custody_authority=media_authority,
                        custody_capability=media_capability,
                    )
                    committed_undo = physical.commit_atomic_episode(
                        epoch_token
                    )
                    self.save_hot_state(state_dir)
                    return (
                        self._lived_contact_sight_grounding_observation(
                            grounded
                        )
                    )
                except BaseException as operation_error:
                    cleanup_errors = []
                    if lived_undo is not None:
                        try:
                            self._causal_thing_lived_context\
                                .rollback_committed_admission(
                                    lived_undo
                                )
                        except BaseException as cleanup_error:
                            cleanup_errors.append(cleanup_error)
                    try:
                        expansion_owner.restore_encoded(
                            prior_expansion
                        )
                    except BaseException as cleanup_error:
                        cleanup_errors.append(cleanup_error)
                    try:
                        if committed_undo is None:
                            physical.rollback_atomic_episode(
                                epoch_token
                            )
                        else:
                            physical.rollback_committed_atomic_episode(
                                committed_undo
                            )
                    except BaseException as cleanup_error:
                        cleanup_errors.append(cleanup_error)
                    if (
                        prediction_snapshot is not None
                        and self._full_field_prediction is not None
                    ):
                        try:
                            self._full_field_prediction.restore_encoded(
                                prediction_snapshot
                            )
                        except BaseException as cleanup_error:
                            cleanup_errors.append(cleanup_error)
                    self._prediction_conditioned_intent_receipt = (
                        prior_prediction_intent
                    )
                    self._prediction_conditioned_binding_id = (
                        prior_prediction_binding
                    )
                    self._latest_full_field_prediction_observation = (
                        prior_prediction_observation
                    )
                    self._latest_causal_settlement = (
                        prior_latest_settlement
                    )
                    self._causal_settlement_accepted = prior_accepted
                    for source_key in tuple(
                        self._live_settled_prediction_custodies
                    ):
                        if source_key not in prior_live_custody_keys:
                            del self._live_settled_prediction_custodies[
                                source_key
                            ]
                    if cleanup_errors:
                        raise BaseExceptionGroup(
                            "sight grounding and rollback failed",
                            [operation_error, *cleanup_errors],
                        )
                    raise

    def settle_live_audiovisual_context(
        self,
        context_id,
        close_reason,
        *,
        auditory_transport,
        auditory_pcm_s16le,
    ):
        """Close one caller-owned AV window with exact microphone custody."""

        if auditory_transport is None or not isinstance(
            auditory_pcm_s16le,
            bytes,
        ):
            raise ValueError(
                "live audiovisual settlement requires PCM transport custody"
            )
        with self._auditory_transaction_lock:
            if (
                self._auditory_prediction_transport_in_commit is not None
                or self._auditory_prediction_pcm_in_commit is not None
            ):
                raise RuntimeError(
                    "another live auditory settlement owns the transaction"
                )
            self._auditory_prediction_transport_in_commit = (
                auditory_transport
            )
            self._auditory_prediction_pcm_in_commit = auditory_pcm_s16le
        try:
            return self.window_manager.end_context(
                context_id,
                close_reason,
                return_settlement=True,
            )
        finally:
            with self._auditory_transaction_lock:
                self._auditory_prediction_transport_in_commit = None
                self._auditory_prediction_pcm_in_commit = None

    @_engine_mutation_entry
    @_live_sensory_entry
    def process_sound_frame(
            self, audio_bytes, source="mic:live", source_anchor_ns=None,
            source_time_end_ns=None, auditory_event_boundary="ambient",
            auditory_pcm_continuity=None, auditory_pcm_s16le=None):
        """Bind one native 16 kHz microphone capture into the auditory field.

        The physical provider preserves synchronized cochlear-channel
        pressure envelope, carrier phase, and causal timing.  It performs no speech,
        source, word, or semantic decision.  Source is provenance only; chi is
        routing only.  The resulting independent ports enter the frozen exact
        L0--L4 boundary without a legacy vector or atlas identity write.
        """
        import io, wave, numpy as np
        if auditory_event_boundary not in ("ambient", "utterance"):
            raise ValueError(
                "auditory event boundary must be ambient or utterance")
        # A valid new capture supersedes the status surface immediately.
        # If decode/transduction/settlement fails, old recognition must not
        # remain visible as though it belonged to this physical event.
        self._latest_auditory_recognition_boundary = auditory_event_boundary
        self._latest_auditory_l5_experience = None
        self._latest_auditory_recognitions = ()
        self._latest_auditory_stream_settlement_receipt = None
        self._latest_auditory_full_field_capture = None
        self._latest_auditory_recurrent_motif = None
        self._latest_auditory_recurrent_motif_experience = None
        self._latest_auditory_recurrent_motif_settlement = None
        if source_anchor_ns is None:
            source_anchor_ns = time.time_ns()
        if (isinstance(source_anchor_ns, bool)
                or not isinstance(source_anchor_ns, int)):
            raise ValueError("sound source anchor must be integer nanoseconds")
        if source_time_end_ns is not None and (
                isinstance(source_time_end_ns, bool)
                or not isinstance(source_time_end_ns, int)
                or source_time_end_ns <= source_anchor_ns):
            raise ValueError("sound source end must follow its source anchor")
        _source_started_ns = source_anchor_ns
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            raw = wf.readframes(n_frames)
        if channels != 1 or sample_width != 2:
            raise ValueError("auditory field requires 16-bit mono PCM WAV")
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
        from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
            transduce_auditory_full_field,
        )
        if auditory_pcm_continuity is None:
            if auditory_pcm_s16le is not None:
                raise ValueError(
                    "auditory PCM bytes require a continuity receipt")
            auditory_field = transduce_auditory_full_field(
                samples, sample_rate_hz=sr)
            auditory_field_source_anchor_ns = source_anchor_ns
            self._latest_auditory_continuation_receipt = None
        else:
            if not isinstance(auditory_pcm_s16le, bytes):
                raise ValueError(
                    "auditory continuity requires canonical PCM bytes")
            if raw != auditory_pcm_s16le:
                raise ValueError(
                    "auditory WAV samples differ from the continuous PCM payload")
            auditory_field, continuation_receipt = (
                self._auditory_full_field_streams.advance(
                    auditory_pcm_s16le, auditory_pcm_continuity
                )
            )
            auditory_field_source_anchor_ns = (
                auditory_pcm_continuity.source_epoch_start_ns
            )
            self._latest_auditory_continuation_receipt = continuation_receipt
        from fractions import Fraction
        from dsf_ai_service.substrate.auditory_kernel_mount import (
            auditory_kernel_mount,
        )
        auditory_mount = auditory_kernel_mount(
            auditory_field,
            source_anchor=Fraction(
                auditory_field_source_anchor_ns, 1_000_000_000
            ),
        )
        auditory_kernel_records = auditory_mount.records
        self._latest_auditory_full_field_capture = auditory_field

        # The retired one-dimensional organism cache cannot represent this
        # topology without flattening it.  Do not route the full field through
        # that compatibility path; auditory L5 consumes the structured field.
        self._last_sound_signal = None
        self._last_sound_wall_time = None
        # GL-RPT-WAL-BLOAT F2 (2026-07-15): this frame is one complete
        # sensory moment, so it gets an EXPLICIT per-frame context, opened
        # and closed right here.  Relying on the implicit-context fallback
        # leaked one never-closable open context per mic chunk: app.py's
        # _run_lifecycle_executor runs every job in a fresh COPIED
        # contextvars.Context that is discarded at job end, so the implicit
        # binding could never be resolved by any later close.  Same entries,
        # same provenance, same per-job window grouping as before -- the
        # window simply closes at its real boundary now.
        # 2026-07-16 correction (same as process_sight_frame above): the
        # per-frame context applies ONLY when no caller-owned experience
        # context is bound; a frame arriving inside a bound experience binds
        # into the caller's window, and only self-created contexts are
        # closed here.
        _bound_experience = self.window_manager.active_context_id
        _frame_context_id = (
            _bound_experience if _bound_experience is not None
            else f"sense:sound:{source}:{time.time_ns():x}")
        _frame_owns_context = _bound_experience is None
        if _frame_owns_context:
            self.window_manager.begin_context(
                _frame_context_id,
                "sound",
                context_detail={
                    "experience_origin": "live_sound",
                    "auditory_event_boundary": auditory_event_boundary,
                    "source_time_start_ns": _source_started_ns,
                    "source_time_end_ns": (
                        source_time_end_ns
                        if source_time_end_ns is not None
                        else _source_started_ns
                        + len(samples) * 1_000_000_000 // sr),
                    "sensor_unavailable": [
                        "sight", "touch", "smell", "taste", "body"],
                },
            )
        n_bands_observed = len(auditory_field.channels)
        n_bands_fired = sum(
            any(value != 0.0 for value in channel.pressure_envelope_full_scale)
            for channel in auditory_field.channels
        )
        try:
            with self.lock:
                auditory_entry_indices = []
                for native_record in auditory_kernel_records:
                    auditory_entry_indices.append(
                        self.window_manager.add_entry(
                            modality="sound",
                            topology=physical_topology_fact(native_record),
                            full_field=native_record,
                            tick=self.tick,
                            source_tag=source,
                            context_id=_frame_context_id,
                        )
                    )
                self.window_manager.bind_settlement_custody(
                    _frame_context_id,
                    auditory_entry_indices,
                    auditory_mount,
                )
                self._log_substrate_event("sound_frame_bound",
                    n_bands=n_bands_fired,
                    n_bands_observed=n_bands_observed,
                    duration_s=round(len(samples)/sr, 2),
                    source=source,
                    auditory_provider="causal_gammatone_erb_v1")
        finally:
            # Close OUTSIDE self.lock: end_context durably appends the closed
            # record to the WAL with an fsync, and EFS latency must never
            # ride under the engine lock (GL-CMD-LOCK-CONTENTION-FIX-182
            # discipline).  In finally so a mid-loop error still closes the
            # partially-bound frame at its boundary instead of leaking it.
            # Never close a caller-owned bound experience (see sight above).
            # F4 (review 2026-07-16): close on ownership, not bands-fired --
            # a first-entry validation raise has already created the
            # context; end_context on a never-created one is a no-op.
            if _frame_owns_context:
                self._auditory_prediction_transport_in_commit = (
                    auditory_pcm_continuity
                )
                self._auditory_prediction_pcm_in_commit = auditory_pcm_s16le
                try:
                    _closed_window_id, _settlement = (
                        self.window_manager.end_context(
                            _frame_context_id,
                            "sound_frame_complete",
                            return_settlement=True,
                        )
                    )
                finally:
                    self._auditory_prediction_transport_in_commit = None
                    self._auditory_prediction_pcm_in_commit = None
            else:
                _closed_window_id = None
                _settlement = None
        if auditory_pcm_continuity is not None:
            with self._auditory_transaction_lock:
                receipt_sha256 = auditory_pcm_continuity.receipt_sha256
                self._auditory_capture_authorities[receipt_sha256] = (
                    auditory_pcm_continuity,
                    auditory_field,
                    self._latest_auditory_continuation_receipt,
                    auditory_pcm_s16le,
                )
                self._auditory_capture_authorities.move_to_end(receipt_sha256)
                while (
                    len(self._auditory_capture_authorities)
                    > self._auditory_transaction_capacity
                ):
                    expired_receipt, _authority = (
                        self._auditory_capture_authorities.popitem(last=False)
                    )
                    self._auditory_prediction_joint_by_transport.pop(
                        expired_receipt,
                        None,
                    )
                    self._auditory_verified_capability_by_transport.pop(
                        expired_receipt,
                        None,
                    )
        return {
            "accepted": n_bands_observed > 0,
            "entries_bound": len(auditory_kernel_records),
            "context_id": _frame_context_id,
            "closed_window_id": _closed_window_id,
            "settlement": _settlement,
            "auditory_continuation_receipt": (
                {
                    **self._latest_auditory_continuation_receipt.payload(),
                    "receipt_sha256": (
                        self._latest_auditory_continuation_receipt.receipt_sha256
                    ),
                }
                if self._latest_auditory_continuation_receipt is not None
                else None
            ),
        }

    def persistence_transaction(self):
        """Return the single reentrant boundary for durable state changes.

        Compound callers deliberately hold this context across offset capture,
        save, compaction, WaveAtlas persistence, and snapshot creation.  Each
        individual persistence method also enters it, so direct callers are
        safe and nested compound operations remain deadlock-free.
        """
        return self._persistence_lock

    @contextlib.contextmanager
    def settled_external_persistence_transaction(self):
        """Own one exact settled-state boundary for an external save.

        Periodic persistence is not an organism mutation.  It must therefore
        close new mutation admission temporarily, wait for every already
        admitted mutation and inherited continuation to finish, and retain
        that exclusive boundary until the durable transaction ends.  The
        snapshot itself is counted as an active engine operation so permanent
        quiescence cannot complete while persistence is still running.
        """
        self._ensure_engine_lifecycle_state()
        if getattr(self._engine_mutation_local, "depth", 0):
            raise RuntimeError(
                "external settled persistence cannot begin inside an "
                "engine mutation"
            )
        with self._engine_mutation_condition:
            while self._engine_settled_snapshot_requested:
                if not self._engine_mutation_admission_open:
                    raise RuntimeError(
                        "external settled persistence rejected during "
                        "quiescence"
                    )
                self._engine_mutation_condition.wait()
            if not self._engine_mutation_admission_open:
                raise RuntimeError(
                    "external settled persistence rejected during quiescence"
                )
            self._engine_settled_snapshot_requested = True
            self._engine_active_mutations += 1
            while self._engine_active_mutations != 1:
                self._engine_mutation_condition.wait()
        try:
            with self._persistence_lock:
                yield
        finally:
            with self._engine_mutation_condition:
                if (
                    not self._engine_settled_snapshot_requested
                    or self._engine_active_mutations <= 0
                ):
                    raise RuntimeError(
                        "settled persistence ownership changed"
                    )
                self._engine_active_mutations -= 1
                self._engine_settled_snapshot_requested = False
                self._engine_mutation_condition.notify_all()

    def settled_hot_persistence_checkpoint_required(self):
        """Return whether one settled causal mutation remains unpersisted.

        Every admitted organism mutation advances ``tick`` exactly once at
        its outer engine-mutation boundary.  The autonomous work driver keeps
        its pending-to-completed transition inside that same boundary.  Under
        the exclusive settled-snapshot admission held by the caller, equality
        between the live tick and the last durable tick therefore proves that
        serializing the whole organism again would publish no new experience.
        """

        self._ensure_engine_lifecycle_state()
        with self._engine_mutation_condition:
            if (
                not self._engine_settled_snapshot_requested
                or self._engine_active_mutations != 1
            ):
                raise RuntimeError(
                    "hot persistence dirtiness requires exclusive settled "
                    "snapshot authority"
                )
        with self.lock:
            live_tick = self.tick
            durable_tick = self._last_save_tick
            if (
                isinstance(live_tick, bool)
                or not isinstance(live_tick, int)
                or live_tick < 0
                or isinstance(durable_tick, bool)
                or not isinstance(durable_tick, int)
                or durable_tick < 0
                or durable_tick > live_tick
            ):
                raise RuntimeError(
                    "hot persistence causal tick lineage changed"
                )
            return (
                self._last_save_timestamp is None
                or live_tick != durable_tick
            )

    def settled_cold_persistence_checkpoint_required(self):
        """Return whether the cold safety generation is causally stale."""

        self._ensure_engine_lifecycle_state()
        with self._engine_mutation_condition:
            if (
                not self._engine_settled_snapshot_requested
                or self._engine_active_mutations != 1
            ):
                raise RuntimeError(
                    "cold persistence dirtiness requires exclusive settled "
                    "snapshot authority"
                )
        with self.lock:
            live_tick = self.tick
            durable_tick = self._last_cold_save_tick
            if (
                isinstance(live_tick, bool)
                or not isinstance(live_tick, int)
                or live_tick < 0
                or isinstance(durable_tick, bool)
                or not isinstance(durable_tick, int)
                or durable_tick < 0
                or durable_tick > live_tick
            ):
                raise RuntimeError(
                    "cold persistence causal tick lineage changed"
                )
            return (
                not getattr(self, "_cold_checkpoint_established", False)
                or live_tick != durable_tick
            )

    def get_recent_events(
        self,
        since_tick=-1,
        limit=50,
        *,
        since_sequence=None,
    ):
        """Return one exact bounded event suffix.

        Sequence is the lossless cursor inside this process epoch.  Tick is
        retained only for older diagnostic callers; it cannot distinguish
        multiple events emitted on the same engine tick.
        """
        if since_sequence is not None and (
            isinstance(since_sequence, bool)
            or not isinstance(since_sequence, int)
            or since_sequence < 0
        ):
            raise ValueError("event sequence cursor is invalid")
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            raise ValueError("event result limit is invalid")
        with self._substrate_event_lock:
            snapshot = tuple(self._substrate_events)
        events = [
            {
                "sequence": e.sequence,
                "tick": e.tick,
                "kind": e.kind,
                "detail": e.detail,
            }
            for e in snapshot
            if (
                e.sequence > since_sequence
                if since_sequence is not None
                else e.tick > since_tick
            )
        ]
        return events[-limit:]

    def event_stream_status(self):
        """Return the process-local exact cursor identity for observers."""
        with self._substrate_event_lock:
            return {
                "capacity": self._substrate_events.maxlen,
                "epoch": self._substrate_event_epoch,
                "latest_sequence": self._substrate_event_sequence,
                "schema": "guala.substrate_event_stream.v1",
            }

    SCHEMA_VERSION = "physical-runtime-v1"

    STATE_FILES = ["guala_core.json"]

    # One organism has one persistence boundary. Cognitive mechanisms remain
    # independently active in memory, but they are never frozen, receipted, or
    # committed as separately owned persistence artifacts.
    FULL_SAVE_MANIFEST_FILES = ("guala_core.json",)

    HOT_SAVE_MANIFEST_FILES = ("guala_core.json",)

    WHOLE_ORGANISM_STATE_CONTRACT = "guala.native_exact_organism_state.v2"
    LEGACY_WHOLE_ORGANISM_STATE_CONTRACT = (
        "guala.whole_organism_state.v1"
    )
    NATIVE_EXACT_ORGANISM_SCHEMA = "guala.native_exact_organism.v1"

    IDENTITY_FILE = "guala_identity.json"

    ENGINE_CONTINUITY_CONTRACT = "engine_continuity_v1"

    BINARY_BINDING_CONTRACT = "guala_binary_binding_v1"

    BINARY_BINDING_SUFFIX = ".binding.json"

    SLEEPING_MARKER = ".sleeping"

    MAX_SNAPSHOTS = 0

    OBSERVATIONAL_RECEIPT_MAX_BYTES = OBSERVATIONAL_RECEIPT_MAX_BYTES

    _last_save_tick = 0

    _last_cold_save_tick = 0   # GL-CMD-DEEP-STORE-PHYSICS-86 P2: updated only on full/cold save

    _last_save_timestamp = None

    _load_successful = False

    _load_errors = []

    _integrity_errors = []

    _events_replayed_at_boot = 0

    _guala_identity = None

    RETIRED_BOOT_FILES = frozenset({
        "guala_atlas.json",
        "guala_bucket.json",
        "guala_coordinator.json",
        "guala_deep_atlas.json",
        "guala_episodic.json",
        "guala_needs.json",
        "guala_organism.sgr",
        "guala_organism.sgr.binding.json",
        "guala_sections.json",
        "guala_sight_motifs.json",
        "guala_sounds.json",
        "guala_survival.json",
        "guala_tapestry.sgr",
        "guala_tapestry.sgr.binding.json",
        "guala_teaching.json",
        "guala_videos.json",
        "guala_visual.json",
        "wave_atlas.npz",
        "wave_atlas.npz.binding.json",
    })

    def _native_materialized_fabric_persistence_record(self):
        state_bytes = self._native_materialized_fabric_state
        reference = self._native_materialized_fabric_reference
        if state_bytes is None and reference is None:
            return None
        if state_bytes is None or reference is None:
            raise RuntimeError(
                "native materialized fabric state and reference diverged"
            )
        if len(state_bytes) > NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES:
            raise RuntimeError(
                "native materialized fabric exceeds its organism storage boundary"
            )
        from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
            VerifiedMaterializedFabricTransition,
        )

        return VerifiedMaterializedFabricTransition(
            reference=reference,
            state_bytes=state_bytes,
        ).persistence_record()

    def _teaching_persistence_payload(self):
        """Freeze only the native exact-field organism state."""
        return {
            "native_materialized_fabric": (
                self._native_materialized_fabric_persistence_record()
            ),
            "schema": self.NATIVE_EXACT_ORGANISM_SCHEMA,
        }

    def _bounded_owner_state_bodies(self):
        raise RuntimeError(
            "legacy owner-scoped persistence is permanently retired"
        )

    def _whole_organism_persistence_payload(self):
        state = self._teaching_persistence_payload()
        encoded = self._canonical_persistence_bytes(state)
        if len(encoded) > TEACHING_WITH_PREDICTION_MAX_BYTES:
            raise RuntimeError(
                "whole-organism state exceeds its aggregate byte boundary"
            )
        return state

    def _whole_organism_core(
        self,
        organism_state,
        *,
        saved_at_timestamp,
        state_file_ticks,
    ):
        organism_bytes = self._canonical_persistence_bytes(organism_state)
        return self._envelope({
            "continuity_contract": self.WHOLE_ORGANISM_STATE_CONTRACT,
            "organism_state": organism_state,
            "organism_state_bytes": len(organism_bytes),
            "organism_state_sha256": _hashlib.sha256(
                organism_bytes
            ).hexdigest(),
            "state_file_ticks": dict(state_file_ticks),
            "tick": self.tick,
        }, saved_at_timestamp=saved_at_timestamp)

    def _save_whole_organism_state(
        self,
        state_dir,
        *,
        include_organism,
        publish_generation,
    ):
        self.synchronize_auditory_q_process_state()
        with self.persistence_transaction():
            authoritative_stage = (
                include_organism
                and getattr(
                    self,
                    "_active_persistence_admission",
                    None,
                ) is not None
            )
            if authoritative_stage:
                with self.lock:
                    if getattr(
                        self,
                        "_prepared_authoritative_full_checkpoint",
                        None,
                    ) is not None:
                        raise RuntimeError(
                            "an authoritative full checkpoint is already "
                            "prepared"
                        )
                    self._prepared_authoritative_full_checkpoint = {
                        "phase": "preparing",
                        "prior_owner_freeze_lineage": {
                            owner_id: dict(receipt)
                            for owner_id, receipt in (
                                self._owner_freeze_lineage.items()
                            )
                        },
                    }
            with self.lock:
                os.makedirs(state_dir, exist_ok=True)
                if self._guala_identity is None:
                    self._generate_genesis_identity(state_dir)
                else:
                    self._ensure_identity_in_target(state_dir)
            with self.staged_persistence_flip():
                with self.lock:
                    organism_state = (
                        self._whole_organism_persistence_payload()
                    )
                    save_tick = self.tick
                    save_timestamp = (
                        self._last_save_timestamp
                        if (
                            self._last_save_tick == save_tick
                            and self._last_save_timestamp is not None
                        )
                        else time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ",
                            time.gmtime(),
                        )
                    )
                    manifest = (
                        self.FULL_SAVE_MANIFEST_FILES
                        if include_organism
                        else self.HOT_SAVE_MANIFEST_FILES
                    )
                    state_file_ticks = {
                        relative: save_tick
                        for relative in manifest
                    }
                    core = self._whole_organism_core(
                        organism_state,
                        saved_at_timestamp=save_timestamp,
                        state_file_ticks=state_file_ticks,
                    )

                self._atomic_write(
                    os.path.join(state_dir, "guala_core.json"),
                    core,
                )

                results = {
                    "guala_core.json": os.path.getsize(
                        os.path.join(state_dir, "guala_core.json.tmp")
                    ),
                }
                if publish_generation:
                    self._publish_state_generation(
                        state_dir,
                        save_tick,
                        manifest_files=(
                            manifest
                            if not include_organism
                            else None
                        ),
                    )
                else:
                    self._commit_staged_persistence()

            with self.lock:
                if authoritative_stage:
                    prior_lineage = (
                        self._prepared_authoritative_full_checkpoint.get(
                            "prior_owner_freeze_lineage"
                        )
                    )
                    self._prepared_authoritative_full_checkpoint = {
                        "phase": "prepared",
                        "prior_owner_freeze_lineage": prior_lineage,
                        "saved_at_timestamp": save_timestamp,
                        "state_file_ticks": dict(
                            state_file_ticks
                        ),
                        "tick": save_tick,
                    }
                else:
                    self._state_file_ticks = dict(state_file_ticks)
                    self._last_save_tick = save_tick
                    self._last_save_timestamp = save_timestamp
                    if include_organism:
                        self._last_cold_save_tick = save_tick
                        self._cold_checkpoint_established = True
            return results

    def _publish_state_generation(
        self,
        state_dir,
        save_tick,
        *,
        manifest_files=None,
    ):
        """Publish exactly one staged whole-organism state generation."""
        authoritative = getattr(
            self,
            "_authoritative_hot_generation_publisher",
            None,
        )
        if manifest_files is not None and authoritative is not None:
            staged = getattr(self, "_persist_stage_renames", None)
            if not staged:
                raise RuntimeError(
                    "authoritative owner-state generation has no staged files"
                )
            state_root = os.path.realpath(state_dir)
            staged_by_relative = {}
            for temporary, destination in staged:
                destination_real = os.path.realpath(destination)
                if os.path.commonpath(
                    (state_root, destination_real)
                ) != state_root:
                    raise RuntimeError(
                        "owner-state stage escaped the active state directory"
                    )
                relative = os.path.relpath(
                    destination_real,
                    state_root,
                ).replace(os.sep, "/")
                if relative in staged_by_relative:
                    raise RuntimeError(
                        "owner-state stage has a duplicate destination"
                    )
                staged_by_relative[relative] = temporary
            if set(staged_by_relative) != set(manifest_files):
                raise RuntimeError(
                    "owner-state staged files differ from the manifest"
                )
            authoritative(
                save_tick=int(save_tick),
                identity=self._guala_identity,
                manifest_files=tuple(manifest_files),
                files=staged_by_relative,
            )
            for temporary in staged_by_relative.values():
                os.remove(temporary)
            staged.clear()
            return
        self._commit_staged_persistence()

    def save_hot_state(self, state_dir="state"):
        """Persist the current organism through one atomic boundary."""
        return self._save_whole_organism_state(
            state_dir,
            include_organism=False,
            publish_generation=True,
        )

    def save_full_state(
        self,
        state_dir="state",
        *,
        publish_generation=True,
    ):
        """Persist the exact whole organism through one atomic boundary."""
        return self._save_whole_organism_state(
            state_dir,
            include_organism=True,
            publish_generation=publish_generation,
        )

    def _read_owner_scoped_state(self, state_dir, core):
        del state_dir, core
        raise RuntimeError(
            "legacy owner-scoped persistence is permanently retired and "
            "cannot be restored"
        )

    def _read_whole_organism_state(
        self,
        state_dir,
        core,
        *,
        allow_authenticated_legacy_import,
    ):
        data = self._unwrap(core, "guala_core.json")
        if (
            isinstance(data, dict)
            and data.get("continuity_contract")
            == "guala.physical_runtime.v1"
        ):
            if not allow_authenticated_legacy_import:
                raise ValueError(
                    "owner-scoped persistence requires the explicit "
                    "one-way migration authority"
                )
            return self._read_owner_scoped_state(state_dir, core)
        if (
            isinstance(data, dict)
            and data.get("continuity_contract")
            == self.LEGACY_WHOLE_ORGANISM_STATE_CONTRACT
        ):
            if not allow_authenticated_legacy_import:
                raise ValueError(
                    "legacy whole-organism persistence requires explicit "
                    "one-way native-state migration authority"
                )
            if (
                set(data) != {
                    "continuity_contract",
                    "organism_state",
                    "organism_state_bytes",
                    "organism_state_sha256",
                    "state_file_ticks",
                    "tick",
                }
                or isinstance(data.get("tick"), bool)
                or not isinstance(data.get("tick"), int)
                or data["tick"] < 0
                or not isinstance(data.get("organism_state"), dict)
            ):
                raise ValueError(
                    "legacy whole-organism state contract changed"
                )
            legacy_bytes = self._canonical_persistence_bytes(
                data["organism_state"]
            )
            if (
                data.get("organism_state_bytes") != len(legacy_bytes)
                or data.get("organism_state_sha256")
                != _hashlib.sha256(legacy_bytes).hexdigest()
                or data.get("state_file_ticks")
                != {"guala_core.json": data["tick"]}
            ):
                raise ValueError(
                    "legacy whole-organism state integrity changed"
                )
            self._authenticated_current_schema_migrations = (
                *getattr(
                    self,
                    "_authenticated_current_schema_migrations",
                    (),
                ),
                NATIVE_EXACT_ORGANISM_V1_MIGRATION,
            )
            predecessor_native_record = data["organism_state"].get(
                "native_materialized_fabric"
            )
            migrated_native_record = None
            if predecessor_native_record is not None:
                from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
                    VerifiedMaterializedFabricTransition,
                    extract_authenticated_predecessor_fabric_bytes,
                )
                from dsf_ai_service.glew_runtime.native_materialized_fabric import (
                    migrate_native_materialized_fabric,
                )

                predecessor_native_bytes = (
                    extract_authenticated_predecessor_fabric_bytes(
                        predecessor_native_record
                    )
                )
                migrated_native_record = (
                    VerifiedMaterializedFabricTransition.from_native(
                        migrate_native_materialized_fabric(
                            prior_state=predecessor_native_bytes,
                            max_state_bytes=(
                                NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES
                            ),
                            max_working_bytes=(
                                _native_transition_working_memory_bytes()
                            ),
                        )
                    ).persistence_record()
                )
            return data["tick"], {
                "native_materialized_fabric": migrated_native_record,
                "schema": self.NATIVE_EXACT_ORGANISM_SCHEMA,
            }
        if (
            not isinstance(data, dict)
            or set(data) != {
                "continuity_contract",
                "organism_state",
                "organism_state_bytes",
                "organism_state_sha256",
                "state_file_ticks",
                "tick",
            }
            or data.get("continuity_contract")
            != self.WHOLE_ORGANISM_STATE_CONTRACT
            or isinstance(data.get("tick"), bool)
            or not isinstance(data.get("tick"), int)
            or data["tick"] < 0
            or not isinstance(data.get("organism_state"), dict)
            or set(data["organism_state"]) != {
                "native_materialized_fabric",
                "schema",
            }
            or data["organism_state"].get("schema")
            != self.NATIVE_EXACT_ORGANISM_SCHEMA
        ):
            raise ValueError("whole-organism state contract changed")
        organism_bytes = self._canonical_persistence_bytes(
            data["organism_state"]
        )
        if (
            data.get("organism_state_bytes") != len(organism_bytes)
            or data.get("organism_state_sha256")
            != _hashlib.sha256(organism_bytes).hexdigest()
            or data.get("state_file_ticks")
            != {"guala_core.json": data["tick"]}
        ):
            raise ValueError("whole-organism state integrity changed")
        return data["tick"], data["organism_state"]

    def _restore_whole_organism_state(self, state):
        """Restore only the single native exact-field organism snapshot."""
        if (
            not isinstance(state, dict)
            or set(state) != {"native_materialized_fabric", "schema"}
            or state.get("schema") != self.NATIVE_EXACT_ORGANISM_SCHEMA
        ):
            raise ValueError("native exact organism state changed")
        native_fabric = state["native_materialized_fabric"]
        if native_fabric is not None:
            from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
                VerifiedMaterializedFabricTransition,
            )

            restored_native_fabric = (
                VerifiedMaterializedFabricTransition.from_persistence_record(
                    native_fabric
                )
            )
            if (
                restored_native_fabric.reference.byte_count
                > NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES
            ):
                raise ValueError(
                    "native materialized cold state exceeds its organism storage boundary"
                )
            from dsf_ai_service.glew_runtime.native_materialized_fabric import (
                migrate_native_materialized_fabric,
            )

            migrated_native_fabric = (
                VerifiedMaterializedFabricTransition.from_native(
                    migrate_native_materialized_fabric(
                        prior_state=restored_native_fabric.state_bytes,
                        max_state_bytes=(
                            NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES
                        ),
                        max_working_bytes=(
                            _native_transition_working_memory_bytes()
                        ),
                    )
                )
            )
            migration_changed_state = (
                migrated_native_fabric.state_bytes
                != restored_native_fabric.state_bytes
            )
            if migration_changed_state and not getattr(
                self,
                "_allow_authenticated_current_schema_migration",
                False,
            ):
                raise ValueError(
                    "native materialized fabric requires an authenticated "
                    "v2/v3-to-v4 migration"
                )
            if migration_changed_state:
                self._authenticated_current_schema_migrations = (
                    *getattr(
                        self,
                        "_authenticated_current_schema_migrations",
                        (),
                    ),
                    NATIVE_MATERIALIZED_FABRIC_V4_MIGRATION,
                )
            self._native_materialized_fabric_state = (
                migrated_native_fabric.state_bytes
            )
            self._native_materialized_fabric_reference = (
                migrated_native_fabric.reference
            )
            self._latest_native_materialized_fabric_transition = {
                **migrated_native_fabric.reference.record(),
                "transition": (
                    "cold_restore_one_way_migration"
                    if migration_changed_state
                    else "cold_restore_exact"
                ),
            }
            self._pending_native_materialized_fabric_transition = None

        return

    def load_full_state(
        self,
        state_dir="state",
        *,
        require_exact_binary=False,
        allow_authenticated_legacy_pickle=False,
        allow_authenticated_current_schema_migration=False,
    ):
        """Load one exact whole-organism physical generation."""
        del allow_authenticated_legacy_pickle
        if not isinstance(require_exact_binary, bool):
            raise TypeError("require_exact_binary must be boolean")
        if not isinstance(
            allow_authenticated_current_schema_migration,
            bool,
        ):
            raise TypeError(
                "authenticated current-schema migration authority must "
                "be boolean"
            )
        os.makedirs(state_dir, exist_ok=True)
        present = {
            entry
            for entry in os.listdir(state_dir)
            if entry in self.RETIRED_BOOT_FILES
        }
        if present:
            raise GualaBootStateIntegrityHalt(
                "retired cognition state requires the explicit one-way "
                "migration tool before physical runtime boot: "
                + ", ".join(sorted(present))
            )
        identity_path = os.path.join(state_dir, self.IDENTITY_FILE)
        core_path = os.path.join(state_dir, "guala_core.json")
        if not os.path.exists(identity_path) and not os.path.exists(core_path):
            self._generate_genesis_identity(state_dir)
            self._load_successful = True
            return
        if not os.path.isfile(identity_path) or not os.path.isfile(core_path):
            raise GualaBootStateIntegrityHalt(
                "physical runtime identity/core pair is incomplete"
            )
        try:
            self._guala_identity = self._load_identity(state_dir)
            if not self._guala_identity:
                raise ValueError("identity is absent")
            with open(core_path, encoding="utf-8") as source:
                core = json.load(source)
            restored_save_timestamp = core.get(
                "saved_at_timestamp"
            )
            if (
                not isinstance(restored_save_timestamp, str)
                or len(restored_save_timestamp) != 20
            ):
                raise ValueError(
                    "guala_core.json has an invalid save timestamp"
                )
            try:
                time.strptime(
                    restored_save_timestamp,
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                restored_save_timestamp.encode("ascii")
            except (ValueError, UnicodeEncodeError) as error:
                raise ValueError(
                    "guala_core.json has an invalid save timestamp"
                ) from error
            self._authenticated_current_schema_migrations = ()
            tick, organism_state = self._read_whole_organism_state(
                state_dir,
                core,
                allow_authenticated_legacy_import=(
                    allow_authenticated_current_schema_migration
                ),
            )
            prior_schema_migration_authority = getattr(
                self,
                "_allow_authenticated_current_schema_migration",
                False,
            )
            self._allow_authenticated_current_schema_migration = (
                allow_authenticated_current_schema_migration
            )
            try:
                self._restore_whole_organism_state(organism_state)
            finally:
                self._allow_authenticated_current_schema_migration = (
                    prior_schema_migration_authority
                )
            self.tick = tick
            self._last_save_tick = tick
            self._last_save_timestamp = restored_save_timestamp
            self._last_cold_save_tick = 0
            self._cold_checkpoint_established = False
            self._load_successful = True
            self._load_errors = []
        except Exception as error:
            self._load_successful = False
            self._load_errors = [str(error)]
            raise GualaBootStateIntegrityHalt(
                f"physical runtime restore failed: {error}"
            ) from error

    def establish_loaded_cold_checkpoint(self, *, authoritative_tick):
        """Bind a verified cold baseline beneath the loaded live state.

        A materialized boot directory may contain a newer authenticated hot
        recovery overlay over an older immutable cold generation.  Loading
        proves the hot state but cannot infer which tick has cold authority;
        the boot coordinator supplies that independently verified baseline
        only after identity and materialization checks have succeeded.
        """
        if (
            isinstance(authoritative_tick, bool)
            or not isinstance(authoritative_tick, int)
            or authoritative_tick < 0
        ):
            raise ValueError(
                "loaded cold checkpoint tick must be a non-negative integer"
            )
        with self.persistence_transaction():
            with self.lock:
                if (
                    not self._load_successful
                    or self._last_save_timestamp is None
                ):
                    raise RuntimeError(
                        "cold checkpoint authority requires a loaded durable "
                        "organism"
                    )
                if authoritative_tick > self.tick:
                    raise RuntimeError(
                        "cold checkpoint authority is newer than the loaded "
                        "organism"
                    )
                self._last_cold_save_tick = authoritative_tick
                self._cold_checkpoint_established = True

    def _generate_genesis_identity(self, state_dir):
        """First boot ever. Generate her identity. This never changes."""
        import uuid
        os.makedirs(state_dir, exist_ok=True)
        self._guala_identity = str(uuid.uuid4())
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        identity_data = {
            "schema_version": self.SCHEMA_VERSION,
            "guala_identity": self._guala_identity,
            "first_boot_timestamp": ts,
            "first_boot_notes": (
                "Physical genesis. No learned sensory or semantic state."
            ),
        }
        self._identity_record = dict(identity_data)
        self._atomic_write(os.path.join(state_dir, self.IDENTITY_FILE), identity_data)
        print(f"[GualaLoom] GENESIS: identity={self._guala_identity} at {ts}")

    def _load_identity(self, state_dir):
        """Load identity from disk. Returns identity string or None."""
        path = os.path.join(state_dir, self.IDENTITY_FILE)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            d = json.load(f)
        self._identity_record = dict(d)
        return d.get("guala_identity")

    def _ensure_identity_in_target(self, state_dir):
        """Write this same identity into every fresh full-state target.

        A generation staging directory is intentionally empty.  Identity is
        therefore copied from the loaded identity record rather than being
        skipped merely because ``_guala_identity`` is already populated in
        memory.
        """
        path = os.path.join(state_dir, self.IDENTITY_FILE)
        if os.path.exists(path):
            with open(path) as fh:
                existing = json.load(fh)
            if existing.get("guala_identity") != self._guala_identity:
                raise ValueError(
                    f"{self.IDENTITY_FILE}: identity "
                    f"{existing.get('guala_identity')} != {self._guala_identity}")
            return
        if not self._guala_identity:
            raise ValueError("cannot persist state without a Guala identity")
        record = dict(self._identity_record or {})
        record["schema_version"] = self.SCHEMA_VERSION
        record["guala_identity"] = self._guala_identity
        record.setdefault(
            "first_boot_notes",
            "Identity continuity copy; genesis metadata unavailable in memory.")
        self._atomic_write(path, record)
        self._identity_record = dict(record)

    def _envelope(
        self,
        data,
        *,
        saved_at_tick=None,
        saved_at_timestamp=None,
    ):
        """Wrap data dict with identity + schema + timestamp."""
        envelope_tick = self.tick if saved_at_tick is None else saved_at_tick
        if (isinstance(envelope_tick, bool)
                or not isinstance(envelope_tick, int)
                or envelope_tick < 0):
            raise ValueError(f"invalid envelope tick: {envelope_tick!r}")
        if saved_at_timestamp is None:
            saved_at_timestamp = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(),
            )
        if (
            not isinstance(saved_at_timestamp, str)
            or len(saved_at_timestamp) != 20
        ):
            raise ValueError("invalid envelope timestamp")
        try:
            time.strptime(
                saved_at_timestamp,
                "%Y-%m-%dT%H:%M:%SZ",
            )
            saved_at_timestamp.encode("ascii")
        except (ValueError, UnicodeEncodeError) as error:
            raise ValueError("invalid envelope timestamp") from error
        return {
            "schema_version": self.SCHEMA_VERSION,
            "guala_identity": self._guala_identity,
            "saved_at_tick": envelope_tick,
            "saved_at_timestamp": saved_at_timestamp,
            "data": data,
        }

    @staticmethod
    def _canonical_persistence_bytes(value):
        try:
            return json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise ValueError("persistence value is not canonical JSON") from error

    def _freeze_owner_payload(self, owner_id, payload):
        """Advance one owner's exact checkpoint lineage only on state change."""
        if not isinstance(owner_id, str) or not owner_id:
            raise ValueError("owner freeze requires an owner id")
        if not isinstance(payload, dict):
            raise ValueError("owner freeze payload must be an object")
        body = dict(payload)
        body.pop("owner_freeze_receipt", None)
        body_sha256 = _hashlib.sha256(
            self._canonical_persistence_bytes(body)
        ).hexdigest()
        prior = self._owner_freeze_lineage.get(owner_id)
        if (
            isinstance(prior, dict)
            and prior.get("semantic_body_sha256") == body_sha256
        ):
            mutation_root = prior["mutation_root_sha256"]
        else:
            prior_root = (
                prior["mutation_root_sha256"]
                if isinstance(prior, dict)
                else _hashlib.sha256(
                    b"guala-owner-freeze-genesis-v1\0"
                    + owner_id.encode("utf-8")
                ).hexdigest()
            )
            mutation_root = _hashlib.sha256(
                b"guala-owner-freeze-mutation-v1\0"
                + owner_id.encode("utf-8")
                + bytes.fromhex(prior_root)
                + bytes.fromhex(body_sha256)
            ).hexdigest()
        receipt = {
            "mutation_root_sha256": mutation_root,
            "owner_id": owner_id,
            "schema": "guala.owner_freeze_receipt.v1",
            "semantic_body_sha256": body_sha256,
        }
        self._owner_freeze_lineage[owner_id] = dict(receipt)
        body["owner_freeze_receipt"] = receipt
        return body

    def _restore_owner_payload(self, owner_id, payload):
        """Verify and retain one owner-issued checkpoint lineage receipt."""
        if not isinstance(payload, dict):
            raise ValueError("owner restore payload must be an object")
        body = dict(payload)
        receipt = body.pop("owner_freeze_receipt", None)
        if not isinstance(receipt, dict) or set(receipt) != {
            "mutation_root_sha256",
            "owner_id",
            "schema",
            "semantic_body_sha256",
        }:
            raise ValueError(f"{owner_id} owner freeze receipt is absent")
        if (
            receipt.get("owner_id") != owner_id
            or receipt.get("schema") != "guala.owner_freeze_receipt.v1"
        ):
            raise ValueError(f"{owner_id} owner freeze receipt changed")
        semantic = _hashlib.sha256(
            self._canonical_persistence_bytes(body)
        ).hexdigest()
        for field in ("semantic_body_sha256", "mutation_root_sha256"):
            value = receipt.get(field)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError(f"{owner_id} owner freeze receipt changed")
        if receipt["semantic_body_sha256"] != semantic:
            raise ValueError(f"{owner_id} owner freeze body changed")
        self._owner_freeze_lineage[owner_id] = dict(receipt)
        return body

    def _restore_or_adopt_owner_payload(self, owner_id, payload):
        if payload.get("owner_freeze_receipt") is not None:
            return self._restore_owner_payload(owner_id, payload)
        adopted = self._freeze_owner_payload(owner_id, payload)
        adopted.pop("owner_freeze_receipt")
        return adopted

    COMPATIBLE_SCHEMAS = {
        "v5.5.0", "v6.0.0", "v7.0.0", "v7.1.0", "v7.2.0", "v7.3.0",
        "v7.4.0", "physical-runtime-v1",
    }

    def _unwrap(self, raw, filename):
        """Validate envelope, return data dict. Raises on mismatch."""
        sv = raw.get("schema_version", "unknown")
        gi = raw.get("guala_identity", "unknown")
        if sv not in self.COMPATIBLE_SCHEMAS:
            raise ValueError(f"{filename}: schema {sv} not in {self.COMPATIBLE_SCHEMAS}")
        if gi != self._guala_identity:
            raise ValueError(f"{filename}: identity {gi} != {self._guala_identity}")
        return raw.get("data", raw)

    @staticmethod
    def _sha256_regular_file(path):
        """Hash one persistence artifact without accepting link indirection."""
        import stat

        info = os.lstat(path)
        if (not stat.S_ISREG(info.st_mode)
                or os.path.islink(path)):
            raise ValueError(f"persistence artifact is not a regular file: {path}")
        digest = _hashlib.sha256()
        size = 0
        with open(path, "rb") as artifact:
            for block in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        if size != info.st_size:
            raise ValueError(
                f"persistence artifact changed while hashing: {path}")
        return digest.hexdigest(), size

    @classmethod
    def _binary_binding_path(cls, artifact_path):
        return artifact_path + cls.BINARY_BINDING_SUFFIX

    @staticmethod
    def _binary_artifact_owner_id(filename):
        return None

    def _write_binary_binding(
        self,
        artifact_path,
        saved_at_tick,
        *,
        saved_at_timestamp=None,
    ):
        """Bind one opaque state artifact to this identity and save tick.

        The immutable deployment generation separately hashes this receipt.
        This inner receipt prevents a valid binary from a different engine
        save from being substituted into an otherwise valid state tree.
        """
        digest, size = self._sha256_regular_file(artifact_path)
        filename = os.path.basename(artifact_path)
        binding_path = self._binary_binding_path(artifact_path)
        binding_payload = {
            "binding_contract": self.BINARY_BINDING_CONTRACT,
            "artifact": filename,
            "sha256": digest,
            "bytes": size,
        }
        owner_id = self._binary_artifact_owner_id(filename)
        if owner_id is not None:
            binding_payload = self._freeze_owner_payload(
                owner_id,
                binding_payload,
            )
        binding_payload["saved_at_tick"] = saved_at_tick
        self._atomic_write(
            binding_path,
            self._envelope(
                binding_payload,
                saved_at_tick=saved_at_tick,
                saved_at_timestamp=saved_at_timestamp,
            ))
        return binding_path

    def _verify_binary_binding(self, artifact_path, expected_tick):
        """Verify the exact receipt and bytes for one required artifact."""
        filename = os.path.basename(artifact_path)
        binding_path = self._binary_binding_path(artifact_path)
        if not os.path.isfile(binding_path) or os.path.islink(binding_path):
            raise ValueError(f"required binary binding is missing: {filename}")
        with open(binding_path) as binding_file:
            raw = json.load(binding_file)
        self._validate_exact_envelope(raw, os.path.basename(binding_path), expected_tick)
        data = self._unwrap(raw, os.path.basename(binding_path))
        if not isinstance(data, dict):
            raise ValueError(f"{filename}: binary binding payload must be an object")
        owner_id = self._binary_artifact_owner_id(filename)
        if owner_id is not None:
            binding_tick = data.pop("saved_at_tick", None)
            data = self._restore_or_adopt_owner_payload(
                owner_id,
                data,
            )
            data["saved_at_tick"] = binding_tick
        if data.get("binding_contract") != self.BINARY_BINDING_CONTRACT:
            raise ValueError(f"{filename}: unknown binary binding contract")
        if data.get("artifact") != filename:
            raise ValueError(f"{filename}: binary binding artifact mismatch")
        # 2026-07-16 boot incident: this payload check demanded exact
        # equality with core's tick, contradicting the manifest-aware
        # hot/cold acceptance _validate_exact_envelope already grants the
        # SAME file two calls earlier. Cold-cycle artifacts (organism,
        # tapestry) legitimately carry the tick of their own last cold
        # save; a failed later save leaves them older than core, which is
        # recoverable-by-design, not a tear. Resolve through the same
        # manifest the envelope check uses; without a manifest row, accept
        # strictly-older (never newer) loudly -- content integrity is
        # fully enforced by the hash+size checks below either way.
        _binding_tick = data.get("saved_at_tick")
        _overrides = self._expected_file_ticks
        _manifest_tick = None
        if isinstance(_overrides, dict):
            _manifest_tick = _overrides.get(os.path.basename(binding_path))
            if _manifest_tick is None:
                _manifest_tick = _overrides.get(filename)
        if _manifest_tick is not None:
            if _binding_tick != _manifest_tick:
                raise ValueError(f"{filename}: binary binding tick mismatch")
        elif _binding_tick != expected_tick:
            if (isinstance(_binding_tick, int)
                    and not isinstance(_binding_tick, bool)
                    and 0 <= _binding_tick < expected_tick):
                print(f"[GualaLoom][cold-skew] {filename}: binding tick "
                      f"{_binding_tick} older than core {expected_tick} -- "
                      f"accepted as this artifact's last cold save "
                      f"(hash-verified below)", flush=True)
            else:
                raise ValueError(f"{filename}: binary binding tick mismatch")
        expected_size = data.get("bytes")
        expected_digest = data.get("sha256")
        if (isinstance(expected_size, bool)
                or not isinstance(expected_size, int)
                or expected_size < 0):
            raise ValueError(f"{filename}: invalid binary binding byte count")
        if (not isinstance(expected_digest, str)
                or len(expected_digest) != 64
                or any(ch not in "0123456789abcdef" for ch in expected_digest)):
            raise ValueError(f"{filename}: invalid binary binding digest")
        actual_digest, actual_size = self._sha256_regular_file(artifact_path)
        if actual_size != expected_size:
            raise ValueError(
                f"{filename}: binary size {actual_size} != bound {expected_size}")
        if actual_digest != expected_digest:
            raise ValueError(f"{filename}: binary digest differs from binding")

    _INTRA_CYCLE_TICK_SKEW = 1200

    def _validate_exact_envelope(self, raw, filename, expected_tick):
        """Prove that one JSON component belongs to a legitimate save set.

        GL-FIX-HOTCOLD-TICK-MANIFEST: the hot and cold save lanes deliberately
        leave the state directory with files at different save ticks (see the
        _state_file_ticks docstring in __init__). ``expected_tick`` is core's
        own save tick; it remains the exact requirement for guala_core.json and
        for any file whose tick the manifest does not describe. For every other
        file we validate against the tick the manifest (carried in core) says
        that file was actually written at -- an exact, torn-save-detecting
        check that also accepts the by-design hot/cold tick skew. When there is
        no manifest entry (legacy state written before this fix), we accept any
        valid tick that is not NEWER than core: a file newer than the core that
        was written after it is the signature of a torn save and is rejected,
        while an older cold file under a newer hot core is the normal, valid
        hot/cold mix and is accepted.
        """
        if not isinstance(raw, dict):
            raise ValueError(f"{filename}: envelope must be an object")
        if "data" not in raw or "guala_identity" not in raw:
            raise ValueError(f"{filename}: exact restore requires an envelope")
        saved_tick = raw.get("saved_at_tick")
        if (isinstance(saved_tick, bool)
                or not isinstance(saved_tick, int)
                or saved_tick < 0):
            raise ValueError(f"{filename}: invalid saved_at_tick {saved_tick!r}")
        overrides = self._expected_file_ticks
        manifest_tick = (overrides.get(filename)
                         if isinstance(overrides, dict) else None)
        if manifest_tick is not None:
            if saved_tick != manifest_tick:
                # 2026-07-16 (:662 supersede): the same intra-cycle write
                # skew d357b57 accepted for pre-manifest saves occurs INSIDE
                # manifest-bearing saves too -- the manifest row is recorded
                # when core is written, and a file that lands a moment later
                # in the SAME save cycle legitimately stamps one tick ahead.
                # Accept the bounded forward skew loudly; genuinely mixed
                # save sets differ by thousands of ticks and still halt.
                if (isinstance(saved_tick, int)
                        and not isinstance(saved_tick, bool)
                        and saved_tick > manifest_tick
                        and saved_tick - manifest_tick
                        <= self._INTRA_CYCLE_TICK_SKEW):
                    print(
                        f"[GualaLoom][manifest-skew] {filename}: "
                        f"saved_at_tick {saved_tick} is "
                        f"{saved_tick - manifest_tick} tick(s) ahead of its "
                        f"manifest row {manifest_tick} -- accepted as "
                        f"intra-cycle write skew (same save cycle, real "
                        f"data; bounded)",
                        flush=True,
                    )
                else:
                    raise ValueError(
                        f"{filename}: saved_at_tick {saved_tick} != "
                        f"{manifest_tick} (state-file-ticks manifest) -- "
                        f"torn or mixed save set")
        elif filename == "guala_core.json":
            if saved_tick != expected_tick:
                raise ValueError(
                    f"{filename}: saved_at_tick {saved_tick} != {expected_tick}")
        elif saved_tick > expected_tick:
            # GL-FIX-LEGACY-INTRA-CYCLE-SKEW: legacy (pre-manifest) hot saves
            # stamp each file's saved_at_tick at its own write moment while the
            # tick loop keeps advancing, so a file written seconds after core
            # can legitimately record a slightly NEWER tick (observed live:
            # guala_teaching.json exactly 1 tick ahead, 2026-07-15). That is
            # real data from the same save cycle, not a tear. Accept a forward
            # skew bounded by one save-cycle's worth of ticks, loudly, and
            # still reject genuinely mixed save sets (different eras differ by
            # thousands of ticks). Manifest-bearing saves (the branch above)
            # never reach here, so this acceptance retires with legacy state.
            if saved_tick - expected_tick <= self._INTRA_CYCLE_TICK_SKEW:
                print(
                    f"[GualaLoom][legacy-skew] {filename}: saved_at_tick "
                    f"{saved_tick} is {saved_tick - expected_tick} tick(s) "
                    f"ahead of core {expected_tick} -- accepted as intra-cycle "
                    "write skew from a pre-manifest hot save (real data, same "
                    "save cycle; bounded)",
                    flush=True,
                )
            else:
                raise ValueError(
                    f"{filename}: saved_at_tick {saved_tick} is newer than core "
                    f"{expected_tick} by more than one save cycle -- torn or "
                    "mixed save set")
        if not isinstance(raw.get("data"), dict):
            raise ValueError(f"{filename}: envelope data must be an object")






    def _write_canonical_binary_file(self, path, payload):
        """Write already-canonical bytes into a private generation stage."""
        if not isinstance(payload, bytes):
            raise TypeError("canonical persistence payload must be bytes")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        admission = getattr(
            self,
            "_active_persistence_admission",
            None,
        )
        if admission is not None:
            with admission.open_binary(path) as target:
                target.write(payload)
            return
        tmp = path + ".tmp"
        with open(tmp, "wb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        staged = getattr(
            self,
            "_persist_stage_renames",
            None,
        )
        if staged is not None:
            staged.append((tmp, path))
            return
        os.replace(tmp, path)



    @contextlib.contextmanager
    def bounded_persistence_admission(self, admission):
        """Bind one synchronous storage admission to every cold-save writer."""
        if admission is None:
            raise TypeError("bounded persistence admission is required")
        for method in (
            "open_binary",
            "open_text",
            "copy_regular_file",
        ):
            if not callable(getattr(admission, method, None)):
                raise TypeError(
                    "bounded persistence admission is missing "
                    f"{method}()")
        prior = getattr(
            self,
            "_active_persistence_admission",
            None,
        )
        if prior is not None:
            if prior is not admission:
                raise RuntimeError(
                    "a different bounded persistence admission is active")
            yield
            return
        self._active_persistence_admission = admission
        try:
            yield
        except BaseException:
            if getattr(
                self,
                "_prepared_authoritative_full_checkpoint",
                None,
            ) is not None:
                self.discard_prepared_authoritative_full_checkpoint()
            raise
        finally:
            self._active_persistence_admission = None

    def finalize_authoritative_full_checkpoint(
            self, *, expected_tick, state_file_ticks):
        """Advance live bookkeeping only after the outer cold commit succeeds.

        A save into an authoritative private stage is preparation, not durable
        authority.  The caller invokes this method only after the immutable
        generation, remote read-back, signed seal, and live-recovery rebase
        have all completed.  A rejected candidate therefore cannot teach a
        later hot checkpoint to depend on cold files that were never published.
        """
        if (
            isinstance(expected_tick, bool)
            or not isinstance(expected_tick, int)
            or expected_tick < 0
        ):
            raise ValueError(
                "authoritative checkpoint tick must be a non-negative integer")
        if not isinstance(state_file_ticks, dict):
            raise ValueError(
                "authoritative checkpoint state_file_ticks must be a mapping")
        expected_files = set(self.FULL_SAVE_MANIFEST_FILES)
        supplied_files = set(state_file_ticks)
        if supplied_files != expected_files:
            raise ValueError(
                "authoritative checkpoint state-file contract changed")
        validated_ticks = {}
        for relative, tick in state_file_ticks.items():
            if (
                isinstance(tick, bool)
                or not isinstance(tick, int)
                or tick != expected_tick
            ):
                raise ValueError(
                    "authoritative checkpoint contains a nonmatching "
                    f"state-file tick: {relative}")
            validated_ticks[relative] = tick

        with self.persistence_transaction():
            with self.lock:
                prepared = getattr(
                    self,
                    "_prepared_authoritative_full_checkpoint",
                    None,
                )
                if not isinstance(prepared, dict):
                    raise RuntimeError(
                        "no prepared authoritative full checkpoint exists")
                if prepared.get("phase") != "prepared":
                    raise RuntimeError(
                        "authoritative full checkpoint preparation is "
                        "incomplete")
                if prepared.get("tick") != expected_tick:
                    raise RuntimeError(
                        "prepared authoritative checkpoint tick changed")
                if prepared.get("state_file_ticks") != validated_ticks:
                    raise RuntimeError(
                        "prepared authoritative state-file lineage changed")
                saved_at_timestamp = prepared.get(
                    "saved_at_timestamp"
                )
                if (
                    not isinstance(saved_at_timestamp, str)
                    or len(saved_at_timestamp) != 20
                ):
                    raise RuntimeError(
                        "prepared authoritative checkpoint timestamp changed"
                    )
                self._state_file_ticks = validated_ticks
                self._last_save_tick = expected_tick
                self._last_cold_save_tick = expected_tick
                self._last_save_timestamp = saved_at_timestamp
                self._cold_checkpoint_established = True
                self._prepared_authoritative_full_checkpoint = None
                self._log_substrate_event(
                    "authoritative_full_checkpoint_finalized",
                    tick=expected_tick,
                )

    def discard_prepared_authoritative_full_checkpoint(self):
        """Discard non-authoritative staging bookkeeping after outer failure."""
        with self.persistence_transaction():
            prepared = getattr(
                self,
                "_prepared_authoritative_full_checkpoint",
                None,
            )
            if isinstance(prepared, dict):
                prior_lineage = prepared.get(
                    "prior_owner_freeze_lineage"
                )
                if isinstance(prior_lineage, dict):
                    self._owner_freeze_lineage = {
                        owner_id: dict(receipt)
                        for owner_id, receipt in prior_lineage.items()
                    }
            self._prepared_authoritative_full_checkpoint = None

    def diary_persistence_status(self):
        """Report that the retired disk diary has no runtime authority."""
        return {
            "schema": "guala.diary_persistence_status.v2",
            "status": "retired",
            "available": False,
            "reason": "bounded_in_memory_observation_ring_is_authoritative",
            "learned_state_authority": False,
            "disk_writes": 0,
            "queue_depth": 0,
            "worker_thread": False,
        }

    def _atomic_write(self, path, data, fsync=False):
        tmp = path + ".tmp"
        admission = getattr(
            self,
            "_active_persistence_admission",
            None,
        )
        authority = self._physical_byte_authority
        if admission is None and authority is not None:
            encoded = json.dumps(data).encode("utf-8")
            authority.atomic_replace_bytes(
                tmp,
                encoded,
                operation="guala_engine_atomic_prepare",
            )
        elif admission is None:
            with open(tmp, "w") as f:
                json.dump(data, f)
                # GL-CMD-PERSIST-FIX-74: always flush before rename. On EFS (NFSv4)
                # the kernel page cache is not flushed to the server at close() time,
                # so os.rename finds no tmp file (ENOENT) despite it being written.
                # f.flush() pushes Python buffer to OS; fsync() commits to NFS server.
                f.flush()
                os.fsync(f.fileno())
        else:
            with admission.open_text(
                    tmp,
                    logical_path=path) as f:
                json.dump(data, f)
        size = os.path.getsize(tmp)
        # GL-FIX-STAGED-SET-FLIP-20260718 (Joe: "break the saves up into
        # manageable chunks or put packet ids on the saves"): inside a
        # staged flip, the durable tmp is RECORDED instead of renamed —
        # the whole save-cycle set then flips into place in milliseconds
        # at commit (manifest-bearing core last), so a kill mid-save can
        # no longer leave a mixed set written over minutes.  Outside a
        # flip, behavior is unchanged.
        staged = getattr(self, "_persist_stage_renames", None)
        # .binding.json companions travel WITH their binary pickles, which
        # write immediately (outside staging) and read the companion back
        # in the same pass — staging them would split the pair.  Their
        # pairing has its own tick validation; the staged flip protects
        # the JSON manifest set, which is where the observed tears live.
        if staged is not None and not path.endswith(".binding.json"):
            staged.append((tmp, path))
            return size
        # GL-FIX-ATOMIC-RENAME-RETRY-20260713: the fsync above still leaves a
        # real, observed gap on EFS -- os.rename() has been seen raising
        # ENOENT immediately after a successful fsync (confirmed live: a
        # dozen "HOT SAVE CRITICAL FAILURE" events over ~30h, all "No such
        # file or directory: '...tmp' -> '...'", clustered every time
        # several hot-lane files rename concurrently into the same
        # directory -- a directory-entry visibility lag on the NFS client,
        # not a really-missing file; the data is already durably fsync'd
        # above, only the rename's own lookup is stale). A short bounded
        # retry is safe here specifically because nothing else in this
        # process deletes its own just-fsynced .tmp file out from under it
        # -- the only failure mode ever observed is transient ENOENT, never
        # a persistent one -- so exhausting the retries still re-raises
        # rather than silently swallowing a real failure.
        for attempt in range(4):
            try:
                os.rename(tmp, path)
                return size
            except FileNotFoundError:
                if attempt == 3:
                    raise
                time.sleep(0.05 * (attempt + 1))
        return size

    def _causal_thing_loom_observation(self):
        """Return a sealed read-only view of authenticated THING owners."""
        required = (
            self._thing_vocal_key,
            self._causal_thing_mosaic_owner,
            self._causal_thing_reciprocal_mosaic,
            self._causal_thing_sensory_expansion,
            self._autonomous_causal_play,
        )
        if any(value is None for value in required):
            return {
                "authorities": {
                    "cognition": False,
                    "decision": False,
                    "meaning": False,
                },
                "full_field_preserved_upstream": True,
                "reason": "causal_thing_owner_unavailable",
                "reduced_approximation": False,
                "schema": (
                    "guala.truthful_loom.causal_thing_observation.v1"
                ),
                "status": "unavailable",
            }
        from dsf_ai_service.substrate.truthful_loom_observation_projection import (
            project_causal_thing_loom_observation,
        )
        projection_key = _hmac.new(
            self._thing_vocal_key,
            b"guala-truthful-loom-causal-thing-view-v1",
            _hashlib.sha256,
        ).digest()
        for attempt in range(2):
            try:
                latest_play = (
                    self._verify_play_causal_admission_record(
                        self._causal_play_observation
                    )
                    if self._causal_play_observation is not None
                    else None
                )
                return project_causal_thing_loom_observation(
                    authority_key=projection_key,
                    thing_owner=self._causal_thing_mosaic_owner,
                    reciprocal_owner=(
                        self._causal_thing_reciprocal_mosaic
                    ),
                    sensory_expansion_owner=(
                        self._causal_thing_sensory_expansion
                    ),
                    autonomous_play_owner=(
                        self._autonomous_causal_play
                    ),
                    latest_settlement=self._latest_causal_settlement,
                    latest_play=latest_play,
                )
            except RuntimeError as error:
                if (
                    str(error)
                    != "causal THING owners changed during Loom observation"
                    or attempt == 1
                ):
                    if str(error) != (
                        "causal THING owners changed during Loom observation"
                    ):
                        raise
                    return {
                        "authorities": {
                            "cognition": False,
                            "decision": False,
                            "meaning": False,
                        },
                        "full_field_preserved_upstream": True,
                        "reason": (
                            "owner_state_changed_during_observation"
                        ),
                        "reduced_approximation": False,
                        "schema": (
                            "guala.truthful_loom."
                            "causal_thing_observation.v1"
                        ),
                        "status": "unavailable",
                    }

    def _sight_evoked_articulatory_loom_observation(self):
        """Report that retired owner-scoped articulation is unavailable."""

        return {
            "authorities": {
                "cognition": False,
                "decision": False,
                "label": False,
                "legacy_route": False,
                "meaning": False,
                "speech_understanding": False,
                "transcript": False,
                "word": False,
            },
            "reason": "legacy_python_cognition_retired",
            "schema": (
                "guala.truthful_loom."
                "consequence_evoked_articulatory_observation.v1"
            ),
            "status": "unavailable",
        }

    def observation_snapshot(self):
        """Return one truthful read-only body, world, and field snapshot."""
        with self.lock:
            tick = self.tick
            identity = self._guala_identity
            activity = (
                self._current_activity.snapshot()
                if self._current_activity is not None
                else None
            )

        if self._embodiment_world is None:
            embodiment = {
                "status": "unavailable",
                "reason": "embodiment_authority_unavailable",
            }
            action = {
                "status": "unavailable",
                "reason": "embodiment_authority_unavailable",
            }
        else:
            world = self._embodiment_world.observation_snapshot()
            latest_action = self._embodiment_world.latest_execution_snapshot()
            embodiment = {
                "status": "observed",
                "location": {
                    "region_id": world.room_id,
                    "revision": world.revision,
                },
                "self_body_id": world.self_body_id,
                "bodies": [item.as_record() for item in world.bodies],
                "objects": [item.as_record() for item in world.objects],
                "room_bounds": world.room_bounds.as_record(),
                "topology": {
                    "current_region_id": world.room_id,
                    "portals": [
                        item.as_record() for item in world.portals
                    ],
                    "regions": [
                        item.as_record() for item in world.regions
                    ],
                },
                "ownership": {
                    "status": "unlearned",
                    "relations": [],
                },
                "authority_receipt_sha256": (
                    world.authority_receipt_sha256
                ),
            }
            action = (
                {
                    "status": "idle",
                    "world_revision": world.revision,
                }
                if latest_action is None
                else {
                    "execution": latest_action.as_record(),
                    "status": "completed",
                    "disposition": latest_action.disposition,
                    "reason": latest_action.reason,
                    "lifecycle": list(latest_action.lifecycle),
                    "actor_body_id": latest_action.actor_body_id,
                    "port_id": latest_action.port_id,
                    "before_revision": latest_action.before.revision,
                    "after_revision": latest_action.after.revision,
                    "authority_receipt_sha256": (
                        latest_action.authority_receipt_sha256
                    ),
                }
            )
        current_prediction_episode = (
            self._full_field_prediction.current_episode()
            if self._full_field_prediction is not None
            else None
        )
        auditory_status = self.auditory_l5_status()
        recurrent_motif = auditory_status.get("recurrent_motif", {})
        l5_status = auditory_status.get("l5_owner", {})
        auditory_physical_experience = {
            "active_hearing_authority": auditory_status.get(
                "active_hearing_authority"
            ),
            "available": True,
            "continuous_streams": auditory_status.get(
                "continuous_streams"
            ),
            "full_field_transactions": auditory_status.get(
                "full_field_transactions"
            ),
            "latest_experience_id": auditory_status.get(
                "latest_experience_id"
            ),
            "latest_relation": auditory_status.get("latest_relation"),
            "latest_stream_settlement_receipt_sha256": (
                auditory_status.get(
                    "latest_stream_settlement_receipt_sha256"
                )
            ),
            "motif": {
                "latest": recurrent_motif.get("latest"),
                "learning_state": auditory_status.get(
                    "latest_motif_learning_state"
                ),
                "motif_neuron_count": recurrent_motif.get(
                    "motif_neuron_count"
                ),
                "pending_independent_experience_count": (
                    recurrent_motif.get(
                        "pending_independent_experience_count"
                    )
                ),
                "firing_state": auditory_status.get(
                    "latest_motif_firing_state"
                ),
            },
            "provider": auditory_status.get("provider"),
            "recognition_authority": False,
            "recognition_boundary": auditory_status.get(
                "recognition_boundary"
            ),
            "settled_l5_experience_count": l5_status.get("settled"),
            "terminal_pipeline": auditory_status.get(
                "terminal_pipeline"
            ),
            "transcript_authority": False,
            "word_authority": False,
        }
        full_field_authority = {
            "available": current_prediction_episode is not None,
            "episode_id": (
                current_prediction_episode.episode_id
                if current_prediction_episode is not None else None
            ),
            "settlement_receipt_sha256": (
                current_prediction_episode.settlement_receipt_sha256
                if current_prediction_episode is not None else None
            ),
            "senses": (
                [
                    {
                        "sense": sense.get("sense"),
                        "state": sense.get("state"),
                        "substreams": [
                            {
                                "coordinates": substream.get(
                                    "coordinates"
                                ),
                                "fields": (
                                    substream.get("field_tuples", [])[-1]
                                    .get("fields", [])
                                ),
                                "physical_quantity": substream.get(
                                    "physical_quantity"
                                ),
                                "physical_unit": substream.get(
                                    "physical_unit"
                                ),
                                "substream_id": substream.get(
                                    "substream_id"
                                ),
                                "topology_index": substream.get(
                                    "topology_index"
                                ),
                                "total_temporal_tuples": len(
                                    substream.get("field_tuples", [])
                                ),
                                "tuple_index": substream.get(
                                    "field_tuples", [])[-1].get(
                                    "tuple_index"
                                ),
                            }
                            for substream in sense.get("substreams", [])
                            if substream.get("field_tuples")
                        ],
                    }
                    for sense in current_prediction_episode
                    .settlement_witness.get("interpretations", [])
                ]
                if current_prediction_episode is not None else []
            ),
            "status": (
                "observed"
                if current_prediction_episode is not None
                else "not_observed"
            ),
            "view_contract": {
                "decision_authority": False,
                "projection": "latest_exact_tuple_per_substream",
                "projection_loss": (
                    "earlier temporal tuples are omitted from this bounded "
                    "observation view; prediction evaluates the complete field"
                ),
                "required_fields": [
                    "D_k", "M_k", "R_rev_k", "U_star_k",
                    "C_k", "P_k", "B_k",
                ],
            },
        }
        payload = {
            "schema": "guala.observation_snapshot.v5",
            "observed_at_tick": tick,
            "identity": identity,
            "embodiment": embodiment,
            "embodied_action": action,
            "embodied_action_teaching": (
                self._embodied_action_teaching.status()
                if self._embodied_action_teaching is not None
                else {"available": False}
            ),
            "physical_material_senses": (
                {
                    "authority": "embodiment_world",
                    "available": self._embodiment_world is not None,
                }
            ),
            "custody_native_tutoring": (
                {
                    **self._custody_native_tutoring_curriculum.status(),
                    "physical_action_selector": (
                        self._custody_native_tutoring_action_selector
                        .status()
                        if self
                        ._custody_native_tutoring_action_selector
                        is not None
                        else {"available": False}
                    ),
                }
                if self._custody_native_tutoring_curriculum is not None
                else {"available": False}
            ),
            "integrated_thing_memory": (
                self._causal_thing_loom_observation()
            ),
            "causal_thing_lived_context": (
                {
                    **self._causal_thing_lived_context.status(),
                    "available": True,
                }
                if self._causal_thing_lived_context is not None
                else {
                    "available": False,
                    "reason": "lived_context_authority_unavailable",
                }
            ),
            "sight_evoked_articulatory_action": (
                self._sight_evoked_articulatory_loom_observation()
            ),
            "multi_emitter_room_hearing": (
                {
                    **self._w1_multi_emitter_capture.status(),
                    "available": True,
                }
                if self._w1_multi_emitter_capture is not None
                else {"available": False}
            ),
            "auditory_physical_experience": (
                auditory_physical_experience
            ),
            "causal_deliberation": (
                {
                    **self._causal_deliberation.status(),
                    "autonomous_play": (
                        self._autonomous_causal_play.status()
                        if self._autonomous_causal_play is not None
                        else {"available": False}
                    ),
                    "latest_play": self._causal_play_observation,
                }
                if self._causal_deliberation is not None
                else {"available": False}
            ),
            "event_stream": self.event_stream_status(),
            "diary_persistence": self.diary_persistence_status(),
            "causal_action": {
                "cycle": (
                    self._causal_action_cycle.status()
                    if self._causal_action_cycle is not None
                    else {"available": False}
                ),
                "dispatcher": (
                    self._causal_action_dispatcher.status()
                    if self._causal_action_dispatcher is not None
                    else {"available": False}
                ),
            },
            "causal_thing_action": {
                "active": all(
                    value is not None
                    for value in (
                        self._causal_thing_reciprocal_mosaic,
                        self._causal_thing_action_deliberation,
                        self._causal_thing_action_intent,
                        self._causal_thing_action_execution,
                    )
                ),
                "full_dsf_field_preserved": True,
                "reduced_approximation": False,
                "intent": (
                    self._causal_thing_action_intent.status()
                    if self._causal_thing_action_intent is not None
                    else {"available": False}
                ),
                "latest": dict(self._latest_causal_thing_action),
            },
            "cognition_activity": (
                {"status": "observed", "activity": activity}
                if activity is not None
                else {
                    "status": "unavailable",
                    "reason": "no_scheduler_activity_observed",
                }
            ),
            "participants": {
                "status": "unavailable",
                "reason": "participant_presence_authority_unavailable",
            },
            "full_field_prediction": (
                {
                    **self._full_field_prediction.status(),
                    "available": True,
                    "latest": self._latest_full_field_prediction_observation,
                    "observer": (
                        self._full_field_prediction.observer_summary()
                    ),
                    "status": (
                        self._full_field_prediction.status()["pending_status"]
                        or "inactive"
                    ),
                }
                if self._full_field_prediction is not None
                else {"available": False}
            ),
            "full_field_authority": full_field_authority,
            "visual_region_authority": (
                {
                    **self._visual_region_continuity.status(),
                    "available": True,
                    "exposure_epoch": (
                        self._visual_exposure_epoch.status()
                        if self._visual_exposure_epoch is not None
                        else {"active_streams": 0}
                    ),
                    "latest_rejection": self._latest_visual_region_rejection,
                }
                if self._visual_region_continuity is not None
                else {"available": False}
            ),
            "live_anonymous_encounter": (
                {
                    **self._live_anonymous_encounter_continuity.status(),
                    "available": True,
                }
                if self._live_anonymous_encounter_continuity is not None
                else {"available": False, "state": "unknown"}
            ),
        }
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return {
            **payload,
            "snapshot_receipt_sha256": _hashlib.sha256(encoded).hexdigest(),
        }

    @contextlib.contextmanager
    def staged_persistence_flip(self):
        """GL-FIX-STAGED-SET-FLIP-20260718: all-or-nothing save-set commit.

        Joe's chunked/packet-id instinct, applied where the tears actually
        happen: every file already carries its save-cycle stamp (the
        packet id) and boot already refuses mixed sets — but files were
        renamed into place ONE BY ONE over a multi-second window, so a
        kill mid-sequence produced exactly the torn sets that cost four
        restore fallbacks tonight.  Inside this context, _atomic_write
        stages durable tmps; at exit the whole set flips via renames in
        milliseconds, with the manifest-bearing guala_core.json LAST as
        the single commit point.  On exception, staged tmps are removed
        and the previous complete set remains untouched.  Reentrant:
        an inner flip defers to the outer one."""
        if getattr(self, "_persist_stage_renames", None) is not None:
            yield
            return
        self._persist_stage_renames = []
        staged = self._persist_stage_renames
        try:
            yield
        except BaseException:
            self._persist_stage_renames = None
            for tmp, _dst in staged:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            raise
        self._persist_stage_renames = None
        self._flip_staged_renames(staged)

    def _flip_staged_renames(self, staged):
        """Rename a staged set into place fast, guala_core.json last, and
        clear the list in place (a mid-save commit and the context exit
        share the same list — clearing prevents a double flip)."""
        # A path written more than once in one save shares one tmp — a
        # single rename carries the LAST write's content; duplicates in
        # the queue would find the tmp already moved.
        deduped = {}
        for tmp, dst in staged:
            deduped[dst] = tmp
        ordered = sorted(
            ((tmp, dst) for dst, tmp in deduped.items()),
            key=lambda item: os.path.basename(item[1]) == "guala_core.json")
        staged.clear()
        for tmp, dst in ordered:
            for attempt in range(4):
                try:
                    os.rename(tmp, dst)
                    break
                except FileNotFoundError:
                    if attempt == 3:
                        raise
                    time.sleep(0.05 * (attempt + 1))

    def _commit_staged_persistence(self):
        """Flip any currently staged save-set NOW (used before generation
        publish, which hard-links the flat files).  Later writes in the
        same save keep staging and flip at the context exit."""
        staged = getattr(self, "_persist_stage_renames", None)
        if staged:
            self._flip_staged_renames(staged)


    def _settle_causal_window(self, record):
        try:
            return self._build_causal_window_settlement(record)
        except Exception:
            self._causal_settlement_failed += 1
            raise

    def _import_current_sensory_state_into_native_fabric(self):
        raise RuntimeError(
            "legacy sensory database import is permanently retired"
        )

    def _advance_native_materialized_fabric(self, source):
        from dsf_ai_service.glew_runtime.native_materialized_fabric import (
            transition_native_materialized_fabric,
        )
        from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
            VerifiedMaterializedFabricTransition,
        )

        try:
            transitioned = VerifiedMaterializedFabricTransition.from_native(
                transition_native_materialized_fabric(
                    prior_state=self._native_materialized_fabric_state,
                    source=source,
                    max_state_bytes=(
                        NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES
                    ),
                    max_working_bytes=(
                        _native_transition_working_memory_bytes()
                    ),
                )
            )
        except ValueError as error:
            if "admitted" not in str(error):
                raise
            raise RuntimeError(
                "native materialized transition exceeds its organism "
                f"storage boundary: {error}"
            ) from error
        if (
            transitioned.reference.byte_count
            > NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES
        ):
            raise RuntimeError(
                "native materialized transition exceeds its organism storage boundary"
            )
        self._native_materialized_fabric_state = transitioned.state_bytes
        self._native_materialized_fabric_reference = transitioned.reference
        self._latest_native_materialized_fabric_transition = {
            **transitioned.reference.record(),
            "transition": "physical_sensory_settlement",
        }
        self._pending_native_materialized_fabric_transition = transitioned
        return transitioned

    def _commit_pending_native_organism_transition(self):
        """Finalize the prepared native transition after sensory settlement."""

        self._pending_native_materialized_fabric_transition = None

    def _discard_pending_native_organism_transition(self):
        """Discard a prepared transition after another causal member fails."""

        return None

    def _build_causal_window_settlement(self, record):
        """Settle one current physical window without semantic authority."""
        from fractions import Fraction

        from dsf_ai_service.glew_runtime.native_sensory_full_field import (
            NativeSensorySubstreamInput,
            build_transaction_owned_six_sense_full_field,
        )
        from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
            NativeAxisCoordinate,
            PhysicalSense,
            SENSE_ORDER,
            SenseBoundaryState,
        )
        from dsf_ai_service.substrate.auditory_kernel_mount import (
            BoundAuditoryKernelMount,
        )
        from dsf_ai_service.substrate.w1_physical_foveal_observation import (
            BoundPhysicalFovealObservation,
        )
        from dsf_ai_service.substrate.visual_exposure_epoch import (
            VisualExposureEpochEvidence,
        )

        owner = self._causal_experience_owner
        if owner is None:
            raise RuntimeError("causal experience owner is not initialized")
        if not isinstance(record, dict):
            raise TypeError("causal sensory window record is not a mapping")

        def exact_fraction_pair(value, label):
            if (
                not isinstance(value, (list, tuple))
                or len(value) != 2
                or any(
                    isinstance(item, bool) or not isinstance(item, int)
                    for item in value
                )
                or value[1] <= 0
            ):
                raise RuntimeError(f"{label} is not a rational pair")
            result = Fraction(value[0], value[1])
            if tuple(value) != (result.numerator, result.denominator):
                raise RuntimeError(f"{label} is not canonical")
            return result

        detail = record.get("context_detail")
        if not isinstance(detail, dict):
            raise RuntimeError("causal sensory context detail changed shape")
        has_ns_interval = any(
            key in detail
            for key in ("source_time_start_ns", "source_time_end_ns")
        )
        has_fraction_interval = any(
            key in detail
            for key in (
                "source_time_start_fraction",
                "source_time_end_fraction",
            )
        )
        if has_ns_interval and has_fraction_interval:
            raise RuntimeError(
                "causal sensory window mixes ns and rational source intervals"
            )
        if has_fraction_interval:
            if not all(
                key in detail
                for key in (
                    "source_time_start_fraction",
                    "source_time_end_fraction",
                )
            ):
                raise RuntimeError(
                    "causal sensory rational source interval is incomplete"
                )
            source_time_start = exact_fraction_pair(
                detail["source_time_start_fraction"],
                "causal sensory source start",
            )
            source_time_end = exact_fraction_pair(
                detail["source_time_end_fraction"],
                "causal sensory source end",
            )
        elif has_ns_interval:
            if not all(
                key in detail
                for key in ("source_time_start_ns", "source_time_end_ns")
            ):
                raise RuntimeError(
                    "causal sensory ns source interval is incomplete"
                )
            start_ns = detail["source_time_start_ns"]
            end_ns = detail["source_time_end_ns"]
            if (
                isinstance(start_ns, bool)
                or not isinstance(start_ns, int)
                or isinstance(end_ns, bool)
                or not isinstance(end_ns, int)
            ):
                raise RuntimeError(
                    "causal sensory window has an invalid ns source interval"
                )
            source_time_start = Fraction(start_ns, 1_000_000_000)
            source_time_end = Fraction(end_ns, 1_000_000_000)
        else:
            raise RuntimeError(
                "causal sensory window has no authoritative source interval"
            )
        if source_time_end <= source_time_start:
            raise RuntimeError(
                "causal sensory window has a non-positive source interval"
            )

        entries = record.get("entries")
        if not isinstance(entries, list):
            raise RuntimeError("causal sensory window entries changed shape")
        entries_by_index = {}
        for expected_index, entry in enumerate(entries):
            if (
                not isinstance(entry, dict)
                or entry.get("entry_index") != expected_index
            ):
                raise RuntimeError(
                    "causal sensory window entry order changed"
                )
            entries_by_index[expected_index] = entry

        auditory_by_index = {}
        visual_by_index = {}
        for custody in self.window_manager._settlement_custodies_for_record(
            record
        ):
            if isinstance(custody, BoundPhysicalFovealObservation):
                for entry_index, native_input in custody.inputs_for_settlement(
                    window_id=str(record.get("window_id") or ""),
                    context_id=str(record.get("context_id") or ""),
                ):
                    entry = entries_by_index.get(entry_index)
                    if (
                        entry is None
                        or entry.get("modality") != "sight"
                        or physical_topology_fact(entry.get("full_field"))
                        != entry.get("topology")
                        or native_input.sense is not PhysicalSense.SIGHT
                    ):
                        raise RuntimeError(
                            "foveal settlement custody crossed its public field"
                        )
                    visual_by_index.setdefault(entry_index, []).append(
                        native_input
                    )
                continue
            if not isinstance(custody, BoundAuditoryKernelMount):
                raise RuntimeError(
                    "causal sensory window has an unknown typed custody"
                )
            for entry_index, native_input in custody.inputs_for_settlement(
                window_id=str(record.get("window_id") or ""),
                context_id=str(record.get("context_id") or ""),
            ):
                if entry_index in auditory_by_index:
                    raise RuntimeError(
                        "auditory settlement custody repeated an entry"
                    )
                entry = entries_by_index.get(entry_index)
                if (
                    entry is None
                    or entry.get("modality") != "sound"
                    or physical_topology_fact(entry.get("full_field"))
                    != entry.get("topology")
                    or native_input.sense is not PhysicalSense.SOUND
                ):
                    raise RuntimeError(
                        "auditory settlement custody crossed its public field"
                    )
                auditory_by_index[entry_index] = native_input

        def native_from_record(value, *, entry_index):
            if not isinstance(value, dict):
                raise RuntimeError(
                    "visual native sensory input changed shape"
                )
            schema = value.get("schema")
            if schema not in {
                "guala.native_sensory_input.v1",
                "guala.native_sensory_input.v2",
                "guala.native_sensory_input.v3",
            }:
                raise RuntimeError(
                    "visual native sensory input has the wrong schema"
                )
            try:
                sense = PhysicalSense(str(value["sense"]))
            except (KeyError, ValueError) as error:
                raise RuntimeError(
                    "visual native sensory input has an invalid sense"
                ) from error
            if sense is not PhysicalSense.SIGHT:
                raise RuntimeError(
                    "visual native sensory input crossed its modality"
                )
            try:
                signals = tuple(
                    float(item) for item in value["normalized_signal"]
                )
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise RuntimeError(
                    "visual native sensory samples changed shape"
                ) from error
            try:
                if schema.endswith(".v3"):
                    if "phase_turns" in value:
                        raise RuntimeError(
                            "visual v3 sensory input mixes phase authorities"
                        )
                    raw_phases = value["phase_turns_fraction"]
                    if not isinstance(raw_phases, (list, tuple)):
                        raise RuntimeError(
                            "visual v3 phase extent changed"
                        )
                    phases = tuple(
                        exact_fraction_pair(
                            item,
                            f"visual native phase {index}",
                        )
                        for index, item in enumerate(raw_phases)
                    )
                else:
                    if "phase_turns_fraction" in value:
                        raise RuntimeError(
                            "legacy visual input mixes phase authorities"
                        )
                    phases = tuple(
                        Fraction.from_float(float(item))
                        for item in value["phase_turns"]
                    )
            except (
                KeyError,
                TypeError,
                ValueError,
                OverflowError,
            ) as error:
                raise RuntimeError(
                    "visual native sensory phases changed shape"
                ) from error
            if schema.endswith(".v1"):
                if any(
                    key in value
                    for key in (
                        "source_anchor_fraction",
                        "causal_offsets_fraction",
                    )
                ):
                    raise RuntimeError(
                        "visual v1 sensory input mixes timing authorities"
                    )
                try:
                    anchor_ns = value["source_anchor_ns"]
                    offsets_ns = value["causal_offsets_ns"]
                except KeyError as error:
                    raise RuntimeError(
                        "visual v1 sensory timing is incomplete"
                    ) from error
                if (
                    isinstance(anchor_ns, bool)
                    or not isinstance(anchor_ns, int)
                    or not isinstance(offsets_ns, (list, tuple))
                    or any(
                        isinstance(item, bool) or not isinstance(item, int)
                        for item in offsets_ns
                    )
                ):
                    raise RuntimeError(
                        "visual v1 sensory timing is invalid"
                    )
                anchor = Fraction(anchor_ns, 1_000_000_000)
                offsets = tuple(
                    Fraction(item, 1_000_000_000)
                    for item in offsets_ns
                )
            else:
                if any(
                    key in value
                    for key in ("source_anchor_ns", "causal_offsets_ns")
                ):
                    raise RuntimeError(
                        "visual v2 sensory input mixes timing authorities"
                    )
                try:
                    anchor = exact_fraction_pair(
                        value["source_anchor_fraction"],
                        "visual native source anchor",
                    )
                    raw_offsets = value["causal_offsets_fraction"]
                except KeyError as error:
                    raise RuntimeError(
                        "visual v2 sensory timing is incomplete"
                    ) from error
                if not isinstance(raw_offsets, (list, tuple)):
                    raise RuntimeError(
                        "visual v2 sensory offsets changed shape"
                    )
                offsets = tuple(
                    exact_fraction_pair(
                        item,
                        f"visual native causal offset {index}",
                    )
                    for index, item in enumerate(raw_offsets)
                )
            if not (
                offsets
                and len(signals) == len(phases) == len(offsets)
                and offsets[0] >= 0
                and all(
                    right > left
                    for left, right in zip(offsets, offsets[1:])
                )
            ):
                raise RuntimeError(
                    "visual native sensory timing is incomplete"
                )
            try:
                coordinates = tuple(
                    NativeAxisCoordinate(str(axis), str(coordinate))
                    for axis, coordinate in value["coordinates"]
                )
                topology_index = int(value["topology_index"])
                native = NativeSensorySubstreamInput(
                    sense=sense,
                    sensor_id=str(value["sensor_id"]),
                    substream_id=str(value["substream_id"]),
                    topology_index=topology_index,
                    coordinates=coordinates,
                    physical_quantity=str(value["physical_quantity"]),
                    physical_unit=str(value["physical_unit"]),
                    source_times=tuple(anchor + offset for offset in offsets),
                    normalized_signal=signals,
                    phase_turns=phases,
                )
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError(
                    f"visual native sensory entry {entry_index} is invalid"
                ) from error
            return native

        observed = {}
        retinotopic_entry = None
        for entry_index, entry in entries_by_index.items():
            modality = entry.get("modality")
            if modality == "sound":
                native = auditory_by_index.get(entry_index)
                if native is None:
                    raise RuntimeError(
                        "auditory field lacks its typed settlement custody"
                    )
                observed.setdefault(PhysicalSense.SOUND, []).append(native)
                continue
            if modality != "sight":
                continue
            public_field = entry.get("full_field")
            if physical_topology_fact(public_field) != entry.get("topology"):
                raise RuntimeError(
                    "visual public topology changed before settlement"
                )
            typed_visual = visual_by_index.get(entry_index)
            if typed_visual is None:
                values = (
                    public_field
                    if isinstance(public_field, list)
                    else [public_field]
                )
                native_values = tuple(
                    native_from_record(value, entry_index=entry_index)
                    for value in values
                )
            else:
                native_values = tuple(typed_visual)
            if (
                native_values
                and native_values[0].sensor_id
                == "browser-camera-retina-8x8"
            ):
                if retinotopic_entry is not None:
                    raise RuntimeError(
                        "causal window contains multiple retinal fields"
                    )
                retinotopic_entry = entry
            observed.setdefault(PhysicalSense.SIGHT, []).extend(
                native_values
            )

        if set(auditory_by_index) != {
            index
            for index, entry in entries_by_index.items()
            if entry.get("modality") == "sound"
        }:
            raise RuntimeError(
                "auditory settlement custody does not cover its full field"
            )
        if not observed:
            return None
        ordered_observed = {
            sense: tuple(
                sorted(values, key=lambda value: value.topology_index)
            )
            for sense, values in observed.items()
        }
        for sense, values in ordered_observed.items():
            topology_indices = tuple(
                value.topology_index for value in values
            )
            if topology_indices != tuple(range(len(values))):
                raise RuntimeError(
                    f"{sense.value} topology is not complete and ordered"
                )

        raw_unavailable = detail.get("sensor_unavailable", ())
        if (
            not isinstance(raw_unavailable, (list, tuple))
            or any(not isinstance(value, str) for value in raw_unavailable)
        ):
            raise RuntimeError(
                "causal sensor-unavailable declaration changed shape"
            )
        try:
            unavailable = {
                PhysicalSense(value) for value in raw_unavailable
            }
        except ValueError as error:
            raise RuntimeError(
                "causal sensor-unavailable declaration is invalid"
            ) from error
        if unavailable.intersection(ordered_observed):
            raise RuntimeError(
                "an observed sense was declared sensor-unavailable"
            )
        raw_quiescent = detail.get("sensor_quiescent", ())
        if (
            not isinstance(raw_quiescent, (list, tuple))
            or any(not isinstance(value, str) for value in raw_quiescent)
        ):
            raise RuntimeError(
                "causal sensor-quiescent declaration changed shape"
            )
        try:
            quiescent = {
                PhysicalSense(value) for value in raw_quiescent
            }
        except ValueError as error:
            raise RuntimeError(
                "causal sensor-quiescent declaration is invalid"
            ) from error
        if (
            quiescent.intersection(ordered_observed)
            or quiescent.intersection(unavailable)
        ):
            raise RuntimeError(
                "a causal sense has conflicting boundary states"
            )
        states = {
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in ordered_observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
                if sense in unavailable
                else SenseBoundaryState.QUIESCENT
                if sense in quiescent
                else SenseBoundaryState.UNKNOWN
            )
            for sense in SENSE_ORDER
        }
        assembly_id = f"causal-{record['window_id']}"
        built = build_transaction_owned_six_sense_full_field(
            assembly_id=assembly_id,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            observed_substreams=ordered_observed,
            states=states,
        )
        prior_native_fabric_state = self._native_materialized_fabric_state
        prior_native_fabric_reference = (
            self._native_materialized_fabric_reference
        )
        prior_native_fabric_observation = (
            self._latest_native_materialized_fabric_transition
        )
        prior_pending_native_fabric = (
            self._pending_native_materialized_fabric_transition
        )
        visual_snapshot = None
        exposure_snapshot = None
        visual_settlement = None
        exposure_evidence = None
        if retinotopic_entry is not None:
            if self._visual_region_continuity is None:
                raise RuntimeError("visual L5 authority is unavailable")
            retinotopic_inputs = ordered_observed.get(
                PhysicalSense.SIGHT, ()
            )
            if (
                len(retinotopic_inputs) != 64
                or any(
                    value.sensor_id != "browser-camera-retina-8x8"
                    for value in retinotopic_inputs
                )
            ):
                raise RuntimeError(
                    "retinotopic settlement lost its complete receptor field"
                )
            entry_detail = retinotopic_entry.get("detail")
            if not isinstance(entry_detail, dict):
                raise RuntimeError(
                    "retinotopic settlement detail changed shape"
                )
            preparation_receipt = entry_detail.get(
                "visual_preparation_receipt_sha256"
            )
            if (
                not isinstance(preparation_receipt, str)
                or len(preparation_receipt) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in preparation_receipt
                )
                or any(
                    value.get("visual_preparation_receipt_sha256")
                    != preparation_receipt
                    for value in retinotopic_entry["full_field"]
                )
            ):
                raise RuntimeError(
                    "retinotopic preparation authority changed"
                )
            exposure_record = entry_detail.get(
                "visual_exposure_epoch_evidence"
            )
            if exposure_record is not None:
                if (
                    self._visual_exposure_epoch is None
                    or not isinstance(exposure_record, dict)
                    or exposure_record.get("schema")
                    != "guala.visual_exposure_epoch.v1"
                ):
                    raise RuntimeError(
                        "visual exposure evidence changed shape"
                    )
                evidence_values = dict(exposure_record)
                evidence_values.pop("schema")
                try:
                    exposure_evidence = VisualExposureEpochEvidence(
                        **evidence_values
                    )
                except TypeError as error:
                    raise RuntimeError(
                        "visual exposure evidence fields changed"
                    ) from error
                self._visual_exposure_epoch.verify(exposure_evidence)
            visual_snapshot = (
                self._visual_region_continuity.snapshot_encoded()
            )
            if self._visual_exposure_epoch is not None:
                exposure_snapshot = (
                    self._visual_exposure_epoch.snapshot_encoded()
                )

        try:
            self._advance_native_materialized_fabric(
                built.native_joint_source_episode
            )
            if retinotopic_entry is not None:
                visual_settlement = (
                    self._visual_region_continuity.settle_l5(
                        built.boundary,
                        built.receipt_registry,
                        exposure_evidence=exposure_evidence,
                        preparation_receipt_sha256=preparation_receipt,
                    )
                )
                if exposure_evidence is not None:
                    self._visual_exposure_epoch.commit(exposure_evidence)
            if self._auditory_transaction_build_in_commit is not None:
                raise RuntimeError(
                    "causal settlement already owns a sensory transaction"
                )
            self._auditory_transaction_build_in_commit = built
            try:
                settlement = owner.settle(
                    built,
                    recognized_language_record=None,
                    routing_chis=(),
                    source_tags=(),
                    commit=True,
                    reserve=False,
                )
            finally:
                self._auditory_transaction_build_in_commit = None
            self._commit_pending_native_organism_transition()
        except BaseException:
            self._discard_pending_native_organism_transition()
            self._native_materialized_fabric_state = (
                prior_native_fabric_state
            )
            self._native_materialized_fabric_reference = (
                prior_native_fabric_reference
            )
            self._latest_native_materialized_fabric_transition = (
                prior_native_fabric_observation
            )
            self._pending_native_materialized_fabric_transition = (
                prior_pending_native_fabric
            )
            if visual_snapshot is not None:
                self._visual_region_continuity.rollback_encoded(
                    visual_snapshot
                )
            if exposure_snapshot is not None:
                self._visual_exposure_epoch.rollback_encoded(
                    exposure_snapshot
                )
            raise
        if visual_settlement is not None:
            self._latest_visual_region_settlement = visual_settlement
            self._latest_visual_region_observation = (
                visual_settlement.as_record()
            )
            self._latest_visual_region_rejection = None
        self._publish_causal_experience_accepted(settlement)
        return settlement

    def _execute_causal_embodiment_request(self, request):
        """Execute one exact W1 command; sensory settlement follows its ack."""
        from dsf_ai_service.substrate.causal_settlement_dispatcher import (
            authenticate_executor_acknowledgement,
        )
        request.verify(self._causal_dispatcher_key)
        if request.action.kind != "embodiment_port":
            raise ValueError("embodiment executor received a non-body action")
        if self._embodiment_world is None:
            unavailable = _hashlib.sha256(
                b"guala-embodiment-unavailable-v1\0"
                + request.authority_receipt_sha256.encode("ascii")
            ).hexdigest()
            return authenticate_executor_acknowledgement(
                request=request,
                executor_id="guala.embodiment.w1",
                authority_key=self._causal_embodiment_executor_key,
                executor_action_receipt_sha256=unavailable,
                disposition="rejected",
            )
        if request.action.port_id != self._embodiment_world.port_id:
            unavailable = _hashlib.sha256(
                b"guala-self-embodiment-port-rejected-v2\0"
                + request.authority_receipt_sha256.encode("ascii")
            ).hexdigest()
            self._causal_embodiment_rejection_reason = {
                "reason": "self_action_port_mismatch",
                "request_receipt_sha256": request.authority_receipt_sha256,
            }
            return authenticate_executor_acknowledgement(
                request=request,
                executor_id="guala.embodiment.w1",
                authority_key=self._causal_embodiment_executor_key,
                executor_action_receipt_sha256=unavailable,
                disposition="rejected",
            )
        observation = self._embodiment_world.observation_snapshot()
        authorization_settlement = self._latest_causal_settlement
        if authorization_settlement is None:
            raise RuntimeError(
                "embodiment action lacks a settled whole-organism trigger"
            )
        if self._causal_embodiment_execution is not None:
            raise RuntimeError(
                "causal embodiment execution capacity is full"
            )
        whole_action_snapshot = (
            self._live_whole_action_spine_snapshot()
        )
        whole_action_authorization = (
            self._begin_live_whole_organism_action_authorization(
                settlement=authorization_settlement,
                action_authority_receipt_sha256=(
                    request.intent_receipt_sha256
                ),
            )
        )
        try:
            world_execution = self._embodiment_world.execute_port_command(
                port_id=request.action.port_id,
                command_payload=request.action.command_payload,
                causal_intent_receipt_sha256=request.intent_receipt_sha256,
                expected_revision=observation.revision,
            )
        except BaseException:
            self._restore_live_whole_action_spine_snapshot(
                whole_action_snapshot
            )
            raise
        if world_execution.disposition == "applied":
            self._causal_embodiment_rejection_reason = None
            self._causal_embodiment_execution = {
                "authorization": whole_action_authorization,
                "consequence_source_time_start": (
                    authorization_settlement.source_time_end
                ),
                "request_receipt_sha256": request.authority_receipt_sha256,
                "whole_action_snapshot": whole_action_snapshot,
                "world_execution": world_execution,
            }
            disposition = "executed"
        else:
            self._restore_live_whole_action_spine_snapshot(
                whole_action_snapshot
            )
            self._causal_embodiment_rejection_reason = {
                "reason": world_execution.reason,
                "request_receipt_sha256": (
                    request.authority_receipt_sha256
                ),
            }
            disposition = "rejected"
        return authenticate_executor_acknowledgement(
            request=request,
            executor_id="guala.embodiment.w1",
            authority_key=self._causal_embodiment_executor_key,
            executor_action_receipt_sha256=(
                world_execution.authority_receipt_sha256
            ),
            disposition=disposition,
        )

    @staticmethod
    def _verify_full_field_prediction_engine_observation(record):
        if not isinstance(record, dict) or record.get("schema") != (
            "guala.full_field_prediction.engine_observation.v1"
        ):
            raise ValueError("full-field prediction observation is malformed")
        status = record.get("status")
        expected = {
            "deferred": {
                "reason", "schema", "settlement_receipt_sha256", "status",
            },
            "capacity_full": {
                "reason", "schema", "settlement_receipt_sha256", "status",
            },
            "observed": {
                "attempt_id", "attempt_status", "episode_id", "reason",
                "schema", "settlement_receipt_sha256", "status",
                "transition_id",
            },
            "conditioned": {
                "attempt_id", "attempt_status", "binding_id",
                "intent_receipt_sha256", "reason", "schema", "status",
            },
            "cancelled": {
                "attempt_id", "attempt_status", "reason", "schema", "status",
            },
        }
        if status not in expected or set(record) != expected[status]:
            raise ValueError("full-field prediction observation fields changed")
        for field in (
            "attempt_id",
            "binding_id",
            "episode_id",
            "intent_receipt_sha256",
            "settlement_receipt_sha256",
            "transition_id",
        ):
            if field not in record or record[field] is None:
                continue
            value = record[field]
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError(
                    f"full-field prediction observation {field} changed"
                )
        if (
            not isinstance(record.get("reason"), str)
            or not record["reason"]
            or (
                "attempt_status" in record
                and record["attempt_status"]
                not in {"unknown", "predicted", "ambiguous"}
            )
            or len(json.dumps(
                record,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")) > 4096
        ):
            raise ValueError("full-field prediction observation changed")
        return record

    @staticmethod
    def _whole_organism_custodied_state(
        provider_id,
        *,
        semantic_state,
        cold_state=None,
        authority_receipt_sha256=None,
    ):
        if isinstance(cold_state, dict):
            cold_bytes = json.dumps(
                cold_state,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        elif isinstance(cold_state, bytes):
            cold_bytes = cold_state
        elif cold_state is None:
            cold_bytes = json.dumps(
                semantic_state,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        else:
            raise TypeError("whole-organism provider state is not canonical")
        receipt = (
            authority_receipt_sha256
            if authority_receipt_sha256 is not None
            else _hashlib.sha256(cold_bytes).hexdigest()
        )
        return {
            "cold_state_bytes": len(cold_bytes),
            "cold_state_sha256": _hashlib.sha256(cold_bytes).hexdigest(),
            "provider_id": provider_id,
            "semantic_state": semantic_state,
        }, receipt

    def _whole_organism_available_state(self, mechanism_id, settlement):
        if mechanism_id in {
            "state:embodiment",
            "state:place-world-continuity",
        }:
            observation = self._embodiment_world.observation_snapshot()
            return self._whole_organism_custodied_state(
                "embodiment_world",
                semantic_state=observation.as_record(),
                cold_state=self._embodiment_world.encoded_snapshot(),
                authority_receipt_sha256=(
                    observation.authority_receipt_sha256
                ),
            )
        if mechanism_id == "state:internal-physical-chemical":
            state = self._physical_internal_body_state.state
            return self._whole_organism_custodied_state(
                "physical_internal_body_state",
                semantic_state=state.record(),
                cold_state=(
                    self._physical_internal_body_state.snapshot_encoded()
                ),
                authority_receipt_sha256=(
                    state.authority_receipt_sha256
                ),
            )
        if mechanism_id == "state:neurochemical-flow":
            owner = self._whole_organism_neurochemical_owner
            if owner is None:
                raise RuntimeError(
                    "whole-organism neurochemical provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "whole_organism_neurochemical_flow",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "state:needs":
            state = self._causal_inquiry_owner.status()
            return self._whole_organism_custodied_state(
                "causal_inquiry",
                semantic_state=state,
                cold_state=self._causal_inquiry_owner.snapshot_encoded(),
            )
        if mechanism_id == "state:recovery":
            owner = self._whole_organism_recovery_owner
            if owner is None:
                raise RuntimeError(
                    "whole-organism recovery provider is unavailable"
                )
            state = owner.state
            return self._whole_organism_custodied_state(
                "whole_organism_recovery",
                semantic_state=state.record(),
                cold_state=owner.snapshot_encoded(),
                authority_receipt_sha256=(
                    state.authority_receipt_sha256
                ),
            )
        if mechanism_id == "growth:neuron-population":
            owner = self._whole_organism_neuron_population_owner
            if owner is None:
                raise RuntimeError(
                    "whole-organism neuron population provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "whole_organism_neuron_population",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "growth:mosaic":
            return self._whole_organism_custodied_state(
                "causal_thing_mosaic",
                semantic_state=self._causal_thing_mosaic_owner.status(),
                cold_state=(
                    self._causal_thing_mosaic_owner.snapshot_encoded()
                ),
            )
        if mechanism_id == "growth:mosaic-relations":
            semantic_state = (
                self._causal_thing_reciprocal_mosaic.status()
            )
            return self._whole_organism_custodied_state(
                "causal_thing_reciprocal_mosaic",
                semantic_state=semantic_state,
                cold_state=semantic_state,
            )
        if mechanism_id in {
            "growth:tapestry",
            "growth:tapestry-relations",
        }:
            owner = self._causal_mosaic_tapestry_owner
            if owner is None:
                raise RuntimeError(
                    "causal mosaic tapestry provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "causal_mosaic_tapestry",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id in {
            "growth:dream-internally-simulated",
            "growth:wake-test",
            "growth:weave",
        }:
            owner = self._organism_dream_wake_weave_owner
            if owner is None:
                raise RuntimeError(
                    "organism dream/wake/weave provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "organism_dream_wake_weave",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "state:deliberation":
            return self._whole_organism_custodied_state(
                "causal_deliberation",
                semantic_state=self._causal_deliberation.status(),
                cold_state=self._causal_deliberation.encoded_snapshot(),
            )
        if mechanism_id == "action:embodied":
            return self._whole_organism_custodied_state(
                "causal_action_cycle",
                semantic_state=self._causal_action_cycle.status(),
                cold_state=self._causal_action_cycle.encoded_snapshot(),
            )
        if mechanism_id == "growth:play":
            return self._whole_organism_custodied_state(
                "autonomous_causal_play",
                semantic_state=self._autonomous_causal_play.status(),
                cold_state=self._autonomous_causal_play.encoded_snapshot(),
            )
        if mechanism_id == "state:sensed-consequence":
            owner = self._durable_sensed_consequence_owner
            if owner is None:
                raise RuntimeError(
                    "durable sensed-consequence provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "durable_sensed_consequence",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "state:recognition-attention":
            owner = self._causal_recognition_attention_owner
            if owner is None:
                raise RuntimeError(
                    "causal recognition-attention provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "causal_recognition_attention",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "state:other-perspective-model":
            owner = self._embodied_other_perspective_owner
            if owner is None:
                raise RuntimeError(
                    "embodied other-perspective provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "embodied_other_perspective",
                semantic_state=owner.status(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "growth:embodied-glyph-curriculum":
            owner = self._embodied_glyph_curriculum_owner
            if owner is None:
                raise RuntimeError(
                    "embodied glyph-curriculum provider is unavailable"
                )
            return self._whole_organism_custodied_state(
                "embodied_glyph_curriculum",
                semantic_state=owner.observation_projection(),
                cold_state=owner.snapshot_encoded(),
            )
        if mechanism_id == "settlement:l6":
            state = {
                "disposition": "unresolved",
                "settlement_authority_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
            }
            return self._whole_organism_custodied_state(
                "whole_organism_passive_l6",
                semantic_state=state,
            )
        raise RuntimeError(
            "whole-organism available mechanism has no exact provider"
        )

    def _synchronize_physical_internal_body_state(self, settlement):
        """Advance only world-owned proprioceptive quantities."""

        owner = self._physical_internal_body_state
        if owner is None:
            raise RuntimeError("physical internal-body authority unavailable")
        from fractions import Fraction
        from dsf_ai_service.substrate.physical_internal_body_state import (
            InternalBodyEvolutionRequest,
            InternalQuantityChange,
        )
        observation = self._embodiment_world.observation_snapshot()
        self_body = next(
            value
            for value in observation.bodies
            if value.body_id == observation.self_body_id
        )
        supported_load = 0
        if self_body.held_object_id is not None:
            supported_load = next(
                value.mass_grams
                for value in observation.objects
                if value.object_id == self_body.held_object_id
            )
        targets = {
            "quantity:proprioception:position_x": Fraction(
                self_body.pose.position.x
            ),
            "quantity:proprioception:position_y": Fraction(
                self_body.pose.position.y
            ),
            "quantity:proprioception:position_z": Fraction(
                self_body.pose.position.z
            ),
            "quantity:proprioception:supported_load": Fraction(
                supported_load
            ),
        }
        current = dict(owner.state.quantity_values)
        changes = tuple(
            InternalQuantityChange(
                quantity_id=quantity_id,
                delta=target - current[quantity_id],
            )
            for quantity_id, target in sorted(targets.items())
            if target != current[quantity_id]
        )
        if not changes:
            return None
        if settlement.source_time_end <= owner.state.source_time:
            raise RuntimeError(
                "proprioceptive change is outside internal structural time"
            )
        prepared = owner.prepare_evolution(InternalBodyEvolutionRequest(
            source_kind="authenticated-embodiment-world-settlement",
            physical_source_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            source_time_start=owner.state.source_time,
            source_time_end=settlement.source_time_end,
            expected_state_receipt_sha256=(
                owner.state.authority_receipt_sha256
            ),
            changes=changes,
        ))
        return owner.commit_prepared(prepared)

    def _prepare_live_whole_organism_contributions(
        self,
        draft,
        settlement,
        *,
        perturbed_overrides=None,
    ):
        raise RuntimeError(
            "legacy owner-scoped whole-organism cognition is permanently "
            "retired; native exact-field settlement remains authoritative"
        )
        authority = self._whole_organism_episode_authority
        overrides = (
            {} if perturbed_overrides is None else perturbed_overrides
        )
        contributions = []
        for spec in authority.manifest.mechanisms:
            capability = authority.mechanism_capability(
                draft,
                spec.mechanism_id,
            )
            if spec.kind is MechanismKind.RECEPTOR_FAMILY:
                contribution = authority.prepare_receptor_contribution(
                    draft,
                    capability,
                )
            elif spec.availability.value == "available":
                if spec.mechanism_id == "state:recovery":
                    recovery_owner = self._whole_organism_recovery_owner
                    if recovery_owner is None:
                        raise RuntimeError(
                            "mounted recovery mechanism lacks its owner"
                        )
                    recovery_state = recovery_owner.state
                    if (
                        recovery_state.settlement_authority_receipt_sha256
                        != settlement.authority_receipt_sha256
                    ):
                        raise RuntimeError(
                            "recovery state does not own this settlement"
                        )
                    if recovery_state.is_recovery:
                        contribution = (
                            authority.prepare_recovery_contribution(
                                draft,
                                capability,
                                stable_state=recovery_state.record(),
                                l1_n_gate_coordinates=(
                                    recovery_state
                                    .l1_n_gate_coordinates
                                ),
                                recovery_authority_receipt_sha256=(
                                    recovery_state
                                    .authority_receipt_sha256
                                ),
                            )
                        )
                    else:
                        contribution = (
                            authority.prepare_quiescent_contribution(
                                draft,
                                capability,
                                quiescent_state=recovery_state.record(),
                                quiescent_authority_receipt_sha256=(
                                    recovery_state
                                    .authority_receipt_sha256
                                ),
                            )
                        )
                    contributions.append(contribution)
                    continue
                if spec.mechanism_id in {
                    "growth:tapestry",
                    "growth:tapestry-relations",
                }:
                    tapestry_owner = self._causal_mosaic_tapestry_owner
                    if tapestry_owner is None:
                        raise RuntimeError(
                            "mounted tapestry mechanism lacks its owner"
                        )
                    state, provider_receipt = (
                        self._whole_organism_available_state(
                            spec.mechanism_id,
                            settlement,
                        )
                    )
                    active = (
                        bool(tapestry_owner.tapestries)
                        if spec.mechanism_id == "growth:tapestry"
                        else bool(tapestry_owner.relations)
                    )
                    if active:
                        contribution = (
                            authority
                            .prepare_current_perturbation_contribution(
                                draft,
                                capability,
                                current_state=state,
                                current_state_authority_receipt_sha256=(
                                    provider_receipt
                                ),
                            )
                        )
                    else:
                        contribution = (
                            authority.prepare_quiescent_contribution(
                                draft,
                                capability,
                                quiescent_state=state,
                                quiescent_authority_receipt_sha256=(
                                    provider_receipt
                                ),
                            )
                        )
                    contributions.append(contribution)
                    continue
                if spec.mechanism_id in {
                    "growth:dream-internally-simulated",
                    "growth:wake-test",
                    "growth:weave",
                }:
                    dream_owner = self._organism_dream_wake_weave_owner
                    if dream_owner is None:
                        raise RuntimeError(
                            "mounted dream/wake/weave mechanism "
                            "lacks its owner"
                        )
                    state, provider_receipt = (
                        self._whole_organism_available_state(
                            spec.mechanism_id,
                            settlement,
                        )
                    )
                    dream_status = dream_owner.status()
                    active = {
                        "growth:dream-internally-simulated": (
                            dream_status["dreams"] > 0
                        ),
                        "growth:wake-test": (
                            dream_status["wake_tests"] > 0
                        ),
                        "growth:weave": (
                            dream_status["weaves"] > 0
                        ),
                    }[spec.mechanism_id]
                    if active:
                        contribution = (
                            authority
                            .prepare_current_perturbation_contribution(
                                draft,
                                capability,
                                current_state=state,
                                current_state_authority_receipt_sha256=(
                                    provider_receipt
                                ),
                            )
                        )
                    else:
                        contribution = (
                            authority.prepare_quiescent_contribution(
                                draft,
                                capability,
                                quiescent_state=state,
                                quiescent_authority_receipt_sha256=(
                                    provider_receipt
                                ),
                            )
                        )
                    contributions.append(contribution)
                    continue
                override = overrides.get(spec.mechanism_id)
                state, provider_receipt = (
                    override
                    if override is not None
                    else self._whole_organism_available_state(
                        spec.mechanism_id,
                        settlement,
                    )
                )
                if spec.mechanism_id == "growth:neuron-population":
                    neuron_status = (
                        self._whole_organism_neuron_population_owner
                        .status()
                    )
                    owner_state_is_perturbed = (
                        neuron_status["quiescent_neurons"]
                        < neuron_status["neurons"]
                    )
                elif spec.mechanism_id == "state:sensed-consequence":
                    owner_state_is_perturbed = (
                        self._durable_sensed_consequence_owner
                        .status()["mechanism_state"] == "perturbed"
                    )
                elif spec.mechanism_id == "state:recognition-attention":
                    owner_state_is_perturbed = (
                        self._causal_recognition_attention_owner
                        .status()["mechanism_state"] == "perturbed"
                    )
                elif spec.mechanism_id == "state:other-perspective-model":
                    owner_state_is_perturbed = (
                        self._embodied_other_perspective_owner
                        .status()["self_world_revision"] is not None
                    )
                elif (
                    spec.mechanism_id
                    == "growth:embodied-glyph-curriculum"
                ):
                    owner_state_is_perturbed = (
                        self._embodied_glyph_curriculum_owner
                        .observation_projection()["lesson_count"] > 0
                    )
                else:
                    owner_state_is_perturbed = False
                if owner_state_is_perturbed or (
                    spec.mechanism_id
                    == "state:internal-physical-chemical"
                    and self._physical_internal_body_state
                    .state.causal_source_receipt_sha256
                    == settlement.authority_receipt_sha256
                ) or override is not None:
                    contribution = (
                        authority
                        .prepare_current_perturbation_contribution(
                            draft,
                            capability,
                            current_state=state,
                            current_state_authority_receipt_sha256=(
                                provider_receipt
                            ),
                        )
                    )
                else:
                    contribution = authority.prepare_quiescent_contribution(
                        draft,
                        capability,
                        quiescent_state=state,
                        quiescent_authority_receipt_sha256=(
                            provider_receipt
                        ),
                    )
            else:
                contribution = authority.prepare_unavailable_contribution(
                    draft,
                    capability,
                )
            contributions.append(contribution)
        return tuple(contributions)

    def _advance_live_neuron_perspective_attention(self, settlement):
        del settlement
        raise RuntimeError(
            "legacy owner/database attention path is permanently retired"
        )


    def _retain_current_causal_thing_action_intent(self, settlement):
        """Retain one exact learned intent without executing any action."""

        attention_owner = self._causal_recognition_attention_owner
        perspective_owner = self._embodied_other_perspective_owner
        deliberation = self._causal_thing_action_deliberation
        intent_owner = self._causal_thing_action_intent
        if (
            attention_owner is None
            or perspective_owner is None
            or deliberation is None
            or intent_owner is None
        ):
            raise RuntimeError(
                "causal THING action admission owners are not fully mounted"
            )
        attention = attention_owner.state
        if (
            attention is None
            or attention.attention_state != "focused_action"
        ):
            return None
        if (
            attention.recognition_state != "settled"
            or attention.focused_relation_receipt_sha256 is None
        ):
            raise RuntimeError(
                "focused action attention is not causally settled"
            )
        self_world_state = perspective_owner.self_world_state
        if self_world_state is None:
            raise RuntimeError(
                "focused action attention lacks current self-world custody"
            )
        perspective_models = perspective_owner.models
        resolution = deliberation.resolve(
            settlement,
            cue_senses=attention.participating_senses,
            recognition_attention_owner=attention_owner,
            attention_state=attention,
            perspective_owner=perspective_owner,
            self_world_state=self_world_state,
            perspective_models=perspective_models,
        )
        if (
            resolution is None
            or resolution.state != "ready"
            or resolution.selected is None
        ):
            raise RuntimeError(
                "focused action attention did not resolve one ready relation"
            )
        return intent_owner.issue(
            settlement=settlement,
            resolution=resolution,
            recognition_attention_owner=attention_owner,
            attention_state=attention,
            perspective_owner=perspective_owner,
            self_world_state=self_world_state,
            perspective_models=perspective_models,
        )

    def _live_whole_action_spine_snapshot(self):
        return {
            "body": self._physical_internal_body_state.snapshot_encoded(),
            "durable": (
                self._durable_sensed_consequence_owner.snapshot_encoded()
            ),
            "episode": (
                self._whole_organism_episode_authority.snapshot_encoded()
            ),
            "neuron": (
                self._whole_organism_neuron_population_owner
                .snapshot_encoded()
            ),
            "neurochemical": (
                self._whole_organism_neurochemical_owner
                .snapshot_encoded()
            ),
            "perspective": (
                self._embodied_other_perspective_owner.snapshot_encoded()
            ),
            "recognition": (
                self._causal_recognition_attention_owner.snapshot_encoded()
            ),
            "recovery": (
                self._whole_organism_recovery_owner.snapshot_encoded()
            ),
            "reflection": (
                self._whole_organism_reflection_owner.snapshot_encoded()
            ),
        }

    def _restore_live_whole_action_spine_snapshot(self, snapshot):
        from dsf_ai_service.substrate.physical_internal_body_state import (
            PhysicalInternalBodyStateAuthority,
        )
        internal_key = _hmac.new(
            self._causal_cycle_key.encode("utf-8"),
            b"guala-live-physical-internal-body-authority-v1",
            _hashlib.sha256,
        ).digest()
        self._physical_internal_body_state = (
            PhysicalInternalBodyStateAuthority.restore_encoded(
                authority_key=internal_key,
                manifest=self._physical_internal_body_state.manifest,
                encoded=snapshot["body"],
            )
        )
        self._restore_whole_organism_recovery_snapshot(
            snapshot["recovery"]
        )
        self._restore_whole_organism_episode_snapshot(
            snapshot["episode"]
        )
        self._restore_whole_organism_neurochemical_snapshot(
            snapshot["neurochemical"]
        )
        self._restore_whole_organism_neuron_population_snapshot(
            snapshot["neuron"]
        )
        self._restore_embodied_other_perspective_snapshot(
            snapshot["perspective"]
        )
        self._restore_causal_recognition_attention_snapshot(
            snapshot["recognition"]
        )
        self._restore_durable_sensed_consequence_snapshot(
            snapshot["durable"]
        )
        self._restore_whole_organism_reflection_snapshot(
            snapshot["reflection"]
        )

    def _begin_live_whole_organism_action_authorization(
        self,
        *,
        settlement,
        action_authority_receipt_sha256,
    ):
        self._synchronize_physical_internal_body_state(settlement)
        recovery = self._whole_organism_recovery_owner
        if (
            recovery.state.settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
        ):
            recovery.commit_prepared(
                recovery.prepare_observation(settlement)
            )
        self._whole_organism_neurochemical_owner.advance(settlement)
        self._advance_live_neuron_perspective_attention(settlement)
        authority = self._whole_organism_episode_authority
        draft = authority.begin_action_authorization(
            chain_id=(
                "live-embodied-action:"
                + action_authority_receipt_sha256
            ),
            settlement=settlement,
            action_authority_receipt_sha256=(
                action_authority_receipt_sha256
            ),
        )
        resolution = authority.resolve(
            draft,
            self._prepare_live_whole_organism_contributions(
                draft,
                settlement,
            ),
        )
        if resolution.state != "resolved" or resolution.capability is None:
            raise RuntimeError(
                "whole-organism action authorization did not resolve"
            )
        return resolution.capability

    def _complete_live_whole_organism_action_consequence(
        self,
        *,
        authorization,
        settlement,
        action_execution_receipt_sha256,
    ):
        raise RuntimeError(
            "legacy owner-scoped whole-organism cognition is permanently "
            "retired; native exact-field settlement remains authoritative"
        )
        self._synchronize_physical_internal_body_state(settlement)
        recovery = self._whole_organism_recovery_owner
        if (
            recovery.state.settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
        ):
            recovery.commit_prepared(
                recovery.prepare_observation(settlement)
            )
        self._whole_organism_neurochemical_owner.advance(settlement)
        self._advance_live_neuron_perspective_attention(settlement)
        l6_payload = {
            "action_execution_receipt_sha256": (
                action_execution_receipt_sha256
            ),
            "rule": "authenticated-embodied-action-physical-consequence",
            "schema": "guala.live.embodied_action_consequence_l6.v1",
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
        }
        encoded = json.dumps(
            l6_payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = _hmac.new(
            self._whole_organism_l6_authority_key,
            b"guala-live-embodied-action-consequence-l6-v1\0" + encoded,
            _hashlib.sha256,
        ).hexdigest()
        l6_receipt = _hashlib.sha256(json.dumps(
            {
                "authority_hmac_sha256": signature,
                "payload": l6_payload,
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()
        authority = self._whole_organism_episode_authority
        draft = authority.begin_consequence(
            authorization=authorization,
            settlement=settlement,
            action_execution_receipt_sha256=(
                action_execution_receipt_sha256
            ),
            l6_disposition=L6Disposition.SETTLED,
            l6_authority_receipt_sha256=l6_receipt,
        )
        resolution = authority.resolve(
            draft,
            self._prepare_live_whole_organism_contributions(
                draft,
                settlement,
            ),
        )
        if resolution.state != "resolved" or resolution.capability is None:
            raise RuntimeError(
                "whole-organism action consequence did not resolve"
            )
        durable = self._durable_sensed_consequence_owner
        durable.commit(durable.prepare(resolution.capability))
        return resolution.capability

    def _observe_whole_organism_settlement(self, settlement):
        """Verify every mounted contribution without granting false learning."""

        raise RuntimeError(
            "legacy owner-scoped whole-organism cognition is permanently "
            "retired; native exact-field settlement remains authoritative"
        )

        authority = self._whole_organism_episode_authority
        if authority is None:
            raise RuntimeError(
                "whole-organism episode authority is unavailable"
            )
        recovery_owner = self._whole_organism_recovery_owner
        if recovery_owner is None:
            raise RuntimeError(
                "whole-organism observation lacks recovery owner"
            )
        recovery_undo = None
        if (
            recovery_owner.state
            .settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
        ):
            prepared_recovery = recovery_owner.prepare_observation(
                settlement
            )
            recovery_undo = recovery_owner.commit_prepared(
                prepared_recovery
            )
        try:
            draft = authority.begin_observation(
                chain_id=(
                    "live-observation:"
                    + settlement.authority_receipt_sha256
                ),
                settlement=settlement,
                l6_disposition=L6Disposition.UNRESOLVED,
                l6_authority_receipt_sha256=None,
            )
            contributions = (
                self._prepare_live_whole_organism_contributions(
                    draft,
                    settlement,
                )
            )
            resolution = authority.resolve(draft, contributions)
            if (
                resolution.state != "unresolved"
                or resolution.reasons != ("l6_unresolved",)
                or resolution.record is not None
                or resolution.capability is not None
            ):
                raise RuntimeError(
                    "whole-organism observation did not fail closed at L6"
                )
        except BaseException:
            if recovery_undo is not None:
                recovery_owner.rollback_committed(recovery_undo)
            raise
        self._latest_whole_organism_episode_resolution = {
            "contribution_states": {
                value.mechanism_id: value.state.value
                for value in contributions
            },
            "manifest_receipt_sha256": (
                authority.manifest.authority_receipt_sha256
            ),
            "reason": "l6_unresolved",
            "schema": "guala.live.whole_organism.observation_status.v1",
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "state": "unresolved",
            "recovery": self._whole_organism_recovery_owner.status(),
            "structural_state_authority_receipt_sha256": (
                self._whole_organism_structural_owner
                .current_state.authority_receipt_sha256
            ),
            "causal_mosaic_tapestry": (
                self._causal_mosaic_tapestry_owner.status()
            ),
        }
        return resolution

    def _settle_whole_organism_passive_learning(
        self,
        settlement,
        passive_record,
    ):
        """Settle only one prepared two-sense physical-THING transition."""

        raise RuntimeError(
            "legacy owner-scoped whole-organism cognition is permanently "
            "retired; native exact-field settlement remains authoritative"
        )

        authority = self._whole_organism_episode_authority
        if (
            authority is None
            or self._whole_organism_l6_authority_key is None
            or passive_record.story.settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
            or passive_record.story.settlement_structural_fingerprint
            != settlement.structural_fingerprint
            or len(passive_record.observed_senses) < 2
        ):
            raise RuntimeError(
                "passive L6 lacks one prepared multisensory physical THING"
            )
        if any(
            value.state == "unknown"
            for value in settlement.interpretations
        ):
            raise RuntimeError(
                "passive L6 cannot settle an ambiguous receptor boundary"
            )
        recovery_owner = self._whole_organism_recovery_owner
        if recovery_owner is None:
            raise RuntimeError(
                "passive L6 lacks whole-organism recovery owner"
            )
        if (
            recovery_owner.state
            .settlement_authority_receipt_sha256
            != settlement.authority_receipt_sha256
        ):
            if (
                recovery_owner.state
                .settlement_authority_receipt_sha256
                != settlement.authority_receipt_sha256
            ):
                prepared_recovery = recovery_owner.prepare_observation(
                    settlement
                )
                recovery_owner.commit_prepared(prepared_recovery)
        l6_payload = {
            "manifest_receipt_sha256": (
                authority.manifest.authority_receipt_sha256
            ),
            "passive_learning_receipt_sha256": (
                passive_record.authority_receipt_sha256
            ),
            "settlement_authority_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "target_partition_authority_receipt_sha256": (
                passive_record.story
                .target_partition_authority_receipt_sha256
            ),
            "thing_id": passive_record.thing_id,
            "rule": (
                "prepared-two-sense-unique-physical-thing-complete"
            ),
            "schema": "guala.live.whole_organism.passive_l6.v1",
        }
        encoded_l6 = json.dumps(
            l6_payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = _hmac.new(
            self._whole_organism_l6_authority_key,
            b"guala-live-whole-organism-passive-l6-v1\0" + encoded_l6,
            _hashlib.sha256,
        ).hexdigest()
        l6_receipt = _hashlib.sha256(json.dumps(
            {
                "authority_hmac_sha256": signature,
                "payload": l6_payload,
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()
        draft = authority.begin_observation(
            chain_id=(
                "live-passive-learning:"
                + settlement.authority_receipt_sha256
            ),
            settlement=settlement,
            l6_disposition=L6Disposition.SETTLED,
            l6_authority_receipt_sha256=l6_receipt,
        )
        mosaic_state = self._whole_organism_custodied_state(
            "passive_whole_organism_thing_learning",
            semantic_state={
                "observed_receptor_families": list(
                    passive_record.observed_senses
                ),
                "passive_learning_receipt_sha256": (
                    passive_record.authority_receipt_sha256
                ),
                "passive_story": passive_record.story.payload(),
                "target_mosaic_state": (
                    self._causal_thing_mosaic_owner.status()
                ),
                "thing_id": passive_record.thing_id,
            },
            authority_receipt_sha256=(
                passive_record.authority_receipt_sha256
            ),
        )
        l6_state = self._whole_organism_custodied_state(
            "whole_organism_passive_l6",
            semantic_state={
                "authority_hmac_sha256": signature,
                "payload": l6_payload,
            },
            authority_receipt_sha256=l6_receipt,
        )
        contributions = self._prepare_live_whole_organism_contributions(
            draft,
            settlement,
            perturbed_overrides={
                "growth:mosaic": mosaic_state,
                "settlement:l6": l6_state,
            },
        )
        resolution = authority.resolve(draft, contributions)
        if (
            resolution.state != "resolved"
            or resolution.record is None
            or resolution.capability is None
        ):
            raise RuntimeError(
                "passive whole-organism L6 did not settle"
            )
        authority.require(
            resolution.capability,
            DownstreamAuthority.LEARNING,
        )
        structural_owner = self._whole_organism_structural_owner
        if structural_owner is None:
            raise RuntimeError(
                "settled whole-organism episode lacks structural owner"
            )
        structural_preparation = structural_owner.prepare(
            resolution.capability
        )
        if (
            structural_preparation.state != "prepared"
            or structural_preparation.prepared is None
        ):
            raise RuntimeError(
                "settled whole-organism structural transfer did not prepare: "
                + ",".join(structural_preparation.reasons)
            )
        structural_resolution = structural_owner.commit(
            structural_preparation.prepared
        )
        if structural_resolution.state not in {
            "changed",
            "no_durable_change",
        }:
            structural_owner.rollback(
                structural_preparation.prepared
            )
            raise RuntimeError(
                "settled whole-organism structural transfer did not commit: "
                + ",".join(structural_resolution.reasons)
            )
        self._latest_whole_organism_episode_resolution = {
            "episode_receipt_sha256": (
                resolution.record.authority_receipt_sha256
            ),
            "l6_authority_receipt_sha256": l6_receipt,
            "manifest_receipt_sha256": (
                authority.manifest.authority_receipt_sha256
            ),
            "passive_learning_receipt_sha256": (
                passive_record.authority_receipt_sha256
            ),
            "schema": "guala.live.whole_organism.observation_status.v1",
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "state": "settled",
            "structural_disposition": structural_resolution.state,
            "structural_state_authority_receipt_sha256": (
                structural_owner.current_state
                .authority_receipt_sha256
            ),
            "causal_mosaic_tapestry": (
                self._causal_mosaic_tapestry_owner.status()
            ),
        }
        return resolution

    def _restore_whole_organism_episode_snapshot(
        self,
        encoded,
        *,
        structural_encoded=None,
    ):
        raise RuntimeError(
            "legacy Python whole-organism episode graph is permanently retired"
        )
        current = self._whole_organism_episode_authority
        if current is None:
            raise RuntimeError(
                "whole-organism episode rollback authority is unavailable"
            )
        if (
            structural_encoded is None
            and self._whole_organism_structural_owner is not None
        ):
            structural_encoded = (
                self._whole_organism_structural_owner.snapshot_encoded()
            )
        self._whole_organism_episode_authority = (
            WholeOrganismEpisodeAuthority.restore_encoded(
                authority_key=self._whole_organism_episode_authority_key,
                manifest=current.manifest,
                encoded=encoded,
            )
        )
        if structural_encoded is not None:
            self._restore_whole_organism_structural_snapshot(
                structural_encoded
            )

    def _restore_whole_organism_recovery_snapshot(self, encoded):
        raise RuntimeError(
            "legacy Python recovery owner is permanently retired"
        )
        if (
            self._whole_organism_recovery_authority_key is None
            or self._physical_internal_body_state is None
        ):
            raise RuntimeError(
                "whole-organism recovery rollback authority is unavailable"
            )
        self._whole_organism_recovery_owner = (
            ExactWholeOrganismRecoveryOwner.restore_encoded(
                authority_key=(
                    self._whole_organism_recovery_authority_key
                ),
                physical_body_authority=(
                    self._physical_internal_body_state
                ),
                encoded=encoded,
            )
        )

    def _restore_whole_organism_structural_snapshot(self, encoded):
        raise RuntimeError(
            "legacy Python structural owner is permanently retired"
        )
        if (
            self._whole_organism_structural_authority_key is None
            or self._whole_organism_episode_authority is None
        ):
            raise RuntimeError(
                "whole-organism structural rollback authority is unavailable"
            )
        self._whole_organism_structural_owner = (
            WholeOrganismStructuralPerturbationOwner.restore_encoded(
                authority_key=(
                    self._whole_organism_structural_authority_key
                ),
                episode_authority=(
                    self._whole_organism_episode_authority
                ),
                encoded=encoded,
            )
        )

    def _restore_causal_mosaic_tapestry_snapshot(self, encoded):
        raise RuntimeError(
            "legacy Python mosaic/tapestry graph is permanently retired"
        )
        current = self._causal_mosaic_tapestry_owner
        if (
            current is None
            or self._causal_mosaic_tapestry_authority_key is None
            or self._causal_mosaic_relation_authority is None
        ):
            raise RuntimeError(
                "causal mosaic tapestry rollback authority is unavailable"
            )
        self._causal_mosaic_tapestry_owner = (
            CausalMosaicTapestryOwner.restore_encoded(
                authority_key=(
                    self._causal_mosaic_tapestry_authority_key
                ),
                profile=current._profile,
                relation_authority=(
                    self._causal_mosaic_relation_authority
                ),
                encoded=encoded,
            )
        )

    def _restore_whole_organism_thing_learning_snapshot(
        self,
        encoded=None,
    ):
        raise RuntimeError(
            "legacy Python THING/mosaic learning is permanently retired"
        )
        current = self._whole_organism_thing_learning_owner
        if (
            current is None
            or self._whole_organism_thing_learning_authority_key is None
            or self._whole_organism_episode_authority is None
            or self._thing_partition_authority is None
            or self._causal_thing_mosaic_owner is None
            or self._whole_organism_neuron_population_owner is None
        ):
            raise RuntimeError(
                "whole-organism THING learning rollback authority "
                "is unavailable"
            )
        arguments = {
            "authority_key": (
                self._whole_organism_thing_learning_authority_key
            ),
            "profile": current._profile,
            "episode_authority": (
                self._whole_organism_episode_authority
            ),
            "partition_authority": self._thing_partition_authority,
            "thing_owner": self._causal_thing_mosaic_owner,
            "neuron_owner": (
                self._whole_organism_neuron_population_owner
            ),
        }
        if encoded is None:
            self._whole_organism_thing_learning_owner = (
                WholeOrganismThingMosaicLearningOwner(**arguments)
            )
        else:
            self._whole_organism_thing_learning_owner = (
                WholeOrganismThingMosaicLearningOwner.restore_encoded(
                    **arguments,
                    encoded=encoded,
                )
            )

    def _restore_organism_dream_wake_weave_snapshot(
        self,
        encoded=None,
    ):
        raise RuntimeError(
            "legacy Python dream/wake/weave graph is permanently retired"
        )
        current = self._organism_dream_wake_weave_owner
        if (
            current is None
            or self._organism_dream_wake_weave_authority_key is None
            or self._causal_mosaic_tapestry_owner is None
            or self._whole_organism_structural_owner is None
            or self._whole_organism_thing_learning_owner is None
            or self._causal_thing_action_intent is None
            or self._causal_thing_action_execution is None
        ):
            raise RuntimeError(
                "organism dream/wake/weave rollback authority "
                "is unavailable"
            )
        arguments = {
            "authority_key": (
                self._organism_dream_wake_weave_authority_key
            ),
            "profile": current._profile,
            "tapestry_owner": self._causal_mosaic_tapestry_owner,
            "structural_state_owner": (
                self._whole_organism_structural_owner
            ),
            "learning_owner": (
                self._whole_organism_thing_learning_owner
            ),
            "action_intent_owner": self._causal_thing_action_intent,
            "action_execution_authority": (
                self._causal_thing_action_execution
            ),
        }
        if encoded is None:
            self._organism_dream_wake_weave_owner = (
                OrganismDreamWakeWeaveOwner(**arguments)
            )
        else:
            self._organism_dream_wake_weave_owner = (
                OrganismDreamWakeWeaveOwner.restore_encoded(
                    **arguments,
                    encoded=encoded,
                )
            )

    def _restore_whole_organism_neuron_population_snapshot(self, encoded):
        raise RuntimeError(
            "legacy Python neuron-population owner is permanently retired"
        )
        current = self._whole_organism_neuron_population_owner
        if (
            current is None
            or self._whole_organism_neuron_population_authority_key is None
            or self._whole_organism_episode_authority is None
        ):
            raise RuntimeError(
                "whole-organism neuron rollback authority is unavailable"
            )
        restore_arguments = {
            "authority_key": (
                self._whole_organism_neuron_population_authority_key
            ),
            "manifest_authority_key": (
                self._whole_organism_episode_authority_key
            ),
            "manifest": self._whole_organism_episode_authority.manifest,
            "local_receptor_verifier": (
                self._whole_organism_neurochemical_owner
                .local_receptor_verifier
            ),
        }
        try:
            restored = WholeOrganismNeuronPopulationOwner.restore_encoded(
                **restore_arguments,
                profile=current._profile,
                encoded=encoded,
            )
        except ValueError:
            if not getattr(
                self,
                "_allow_authenticated_current_schema_migration",
                False,
            ):
                raise
            migrated = (
                WholeOrganismNeuronPopulationOwner
                .migrate_authenticated_runtime_profile_v1_to_v2_encoded(
                    **restore_arguments,
                    legacy_profile=(
                        _whole_organism_neuron_population_profile(
                            legacy=True
                        )
                    ),
                    current_profile=current._profile,
                    encoded=encoded,
                )
            )
            restored = WholeOrganismNeuronPopulationOwner.restore_encoded(
                **restore_arguments,
                profile=current._profile,
                encoded=migrated,
            )
            self._authenticated_current_schema_migrations = (
                *getattr(
                    self,
                    "_authenticated_current_schema_migrations",
                    (),
                ),
                WHOLE_ORGANISM_NEURON_PROFILE_MIGRATION,
            )
        learning_owner = self._whole_organism_thing_learning_owner
        if learning_owner is not None:
            learning_owner.rebind_neuron_owner(restored)
        self._whole_organism_neuron_population_owner = restored

    def _restore_whole_organism_neurochemical_snapshot(self, encoded):
        raise RuntimeError(
            "legacy owner-scoped neurochemical state is permanently retired "
            "and cannot be restored"
        )
        current = self._whole_organism_neurochemical_owner
        if (
            current is None
            or self._whole_organism_neurochemical_authority_key is None
            or self._physical_internal_body_state is None
        ):
            raise RuntimeError(
                "neurochemical rollback authority is unavailable"
            )
        try:
            envelope = json.loads(encoded)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "neurochemical rollback state is unreadable"
            ) from error
        if (
            isinstance(envelope, dict)
            and envelope.get("schema")
            == "guala.unavailable_neurochemical_flow.state.v1"
        ):
            from dsf_ai_service.substrate.unavailable_neurochemical_flow import (
                UnavailableNeurochemicalFlowOwner,
            )
            UnavailableNeurochemicalFlowOwner.restore_encoded(
                authority_key=(
                    self._whole_organism_neurochemical_authority_key
                ),
                internal_body_owner=self._physical_internal_body_state,
                encoded=encoded,
                max_state_bytes=(
                    WHOLE_ORGANISM_NEUROCHEMICAL_STATE_MAX_BYTES
                ),
            )
            self._whole_organism_neurochemical_owner = (
                LiveAENeurochemicalFlowOwner(
                    root_key=self._causal_cycle_key,
                    body_authority=self._physical_internal_body_state,
                    recovery_owner=self._whole_organism_recovery_owner,
                    max_state_bytes=(
                        WHOLE_ORGANISM_NEUROCHEMICAL_STATE_MAX_BYTES
                    ),
                )
            )
            return
        self._whole_organism_neurochemical_owner = (
            LiveAENeurochemicalFlowOwner.restore_encoded(
                root_key=self._causal_cycle_key,
                body_authority=self._physical_internal_body_state,
                recovery_owner=self._whole_organism_recovery_owner,
                encoded=encoded,
                max_state_bytes=(
                    WHOLE_ORGANISM_NEUROCHEMICAL_STATE_MAX_BYTES
                ),
            )
        )

    def _whole_organism_reflection_owners(self):
        return {
            "action": self._causal_thing_action_intent,
            "attention-recognition": (
                self._causal_recognition_attention_owner
            ),
            "body-chemical": self._whole_organism_neurochemical_owner,
            "recovery": self._whole_organism_recovery_owner,
            "sensed-consequence": (
                self._durable_sensed_consequence_owner
            ),
            "structural": self._whole_organism_structural_owner,
            "tapestry": self._causal_mosaic_tapestry_owner,
        }

    def _ensure_whole_organism_reflection_owner_binding(self):
        owner = self._whole_organism_reflection_owner
        if owner is None:
            return None
        live_owners = self._whole_organism_reflection_owners()
        bound_owners = owner._owners
        if (
            set(bound_owners) == set(live_owners)
            and all(
                bound_owners[owner_id] is live_owner
                for owner_id, live_owner in live_owners.items()
            )
        ):
            return owner
        encoded = owner.snapshot_encoded()
        self._restore_whole_organism_reflection_snapshot(encoded)
        return self._whole_organism_reflection_owner

    def _restore_whole_organism_reflection_snapshot(self, encoded):
        raise RuntimeError(
            "legacy owner-scoped reflection state is permanently retired "
            "and cannot be restored"
        )
        if (
            self._whole_organism_reflection_owner is None
            or self._whole_organism_reflection_authority_key is None
        ):
            raise RuntimeError(
                "whole-organism reflection rollback authority is unavailable"
            )
        self._whole_organism_reflection_owner = (
            WholeOrganismReflectionMonitorOwner.restore_encoded(
                authority_key=(
                    self._whole_organism_reflection_authority_key
                ),
                owners=self._whole_organism_reflection_owners(),
                encoded=encoded,
                max_state_bytes=(
                    WHOLE_ORGANISM_REFLECTION_STATE_MAX_BYTES
                ),
            )
        )

    def _restore_causal_recognition_attention_snapshot(self, encoded):
        raise RuntimeError(
            "legacy Python recognition/attention graph is permanently retired"
        )
        current = self._causal_recognition_attention_owner
        if (
            current is None
            or self._causal_recognition_attention_authority_key is None
            or self._causal_mosaic_tapestry_owner is None
            or self._whole_organism_attention_context_authority is None
        ):
            raise RuntimeError(
                "recognition-attention rollback authority is unavailable"
            )
        self._causal_recognition_path_authority = (
            CausalThingRelationPathAuthority(
                authority_key=(
                    self._causal_recognition_attention_authority_key
                ),
                tapestry_owner=self._causal_mosaic_tapestry_owner,
            )
        )
        self._causal_recognition_attention_owner = (
            CausalRecognitionAttentionOwner.restore_encoded(
                authority_key=(
                    self._causal_recognition_attention_authority_key
                ),
                profile=current._profile,
                path_authority=self._causal_recognition_path_authority,
                context_authority=(
                    self._whole_organism_attention_context_authority
                ),
                encoded=encoded,
            )
        )

    def _restore_embodied_other_perspective_snapshot(self, encoded):
        from dsf_ai_service.substrate.embodied_other_perspective import (
            EmbodiedOtherPerspectiveOwner,
        )
        current = self._embodied_other_perspective_owner
        if (
            current is None
            or self._embodied_other_perspective_authority_key is None
            or self._other_body_access_authority is None
        ):
            raise RuntimeError(
                "other-perspective rollback authority is unavailable"
            )
        self._embodied_other_perspective_owner = (
            EmbodiedOtherPerspectiveOwner.restore_encoded(
                authority_key=(
                    self._embodied_other_perspective_authority_key
                ),
                profile=current._profile,
                world_authority=self._embodiment_world,
                access_authority=self._other_body_access_authority,
                encoded=encoded,
            )
        )

    def _restore_durable_sensed_consequence_snapshot(self, encoded):
        raise RuntimeError(
            "legacy owner-scoped sensed-consequence state is permanently "
            "retired and cannot be restored"
        )
        current = self._durable_sensed_consequence_owner
        if (
            current is None
            or self._durable_sensed_consequence_authority_key is None
            or self._whole_organism_episode_authority is None
        ):
            raise RuntimeError(
                "sensed-consequence rollback authority is unavailable"
            )
        self._durable_sensed_consequence_owner = (
            DurableSensedConsequenceOwner.restore_encoded(
                authority_key=(
                    self._durable_sensed_consequence_authority_key
                ),
                episode_authority=self._whole_organism_episode_authority,
                encoded=encoded,
                max_records=current._max_records,
                max_state_bytes=current._max_bytes,
            )
        )

    def _restore_embodied_glyph_curriculum_snapshot(self, encoded):
        raise RuntimeError(
            "legacy Python glyph curriculum is permanently retired"
        )
        current = self._embodied_glyph_curriculum_owner
        if (
            current is None
            or self._embodied_glyph_curriculum_authority_key is None
        ):
            raise RuntimeError(
                "embodied glyph rollback authority is unavailable"
            )
        self._embodied_glyph_curriculum_owner = (
            restore_embodied_glyph_tutoring_curriculum(
                authority_key=(
                    self._embodied_glyph_curriculum_authority_key
                ),
                encoded=encoded,
            )
        )

    def _restore_embodied_reading_lesson_controller_snapshot(
        self,
        encoded=None,
    ):
        raise RuntimeError(
            "legacy owner-scoped reading controller is permanently retired "
            "and cannot be restored"
        )
        current = self._embodied_reading_lesson_controller
        if (
            current is None
            or self._embodied_glyph_curriculum_authority_key is None
        ):
            raise RuntimeError(
                "embodied reading rollback authority is unavailable"
            )
        if encoded is None:
            self._embodied_reading_lesson_controller = (
                EmbodiedReadingLessonController(
                    authority_key=(
                        self._embodied_glyph_curriculum_authority_key
                    ),
                    max_records=current._max_records,
                    max_state_bytes=current._max_state_bytes,
                )
            )
            return
        self._embodied_reading_lesson_controller = (
            restore_embodied_reading_lesson_controller(
                authority_key=(
                    self._embodied_glyph_curriculum_authority_key
                ),
                encoded=encoded,
            )
        )

    def _accept_causal_settlement(
        self,
        settlement,
        *,
        custody_authority=None,
        custody_capability=None,
    ):
        """Record one passive physical settlement, then route uncertainty."""
        if self._engine_quiesced:
            raise RuntimeError("causal settlement rejected after quiescence")
        if not self._causal_experience_owner.verify_active_transaction(
            settlement
        ):
            settlement.verify()
            verified_causal_transaction = None
        else:
            verified_causal_transaction = (
                self._causal_experience_owner
                .active_transaction_capability(settlement)
            )
        pending_lived_transaction = getattr(
            self, "_pending_physical_surface_learning", None
        )
        outer_rollback_owned = (
            isinstance(pending_lived_transaction, dict)
            and pending_lived_transaction.get("outer_rollback_snapshot")
            is not None
        )
        prediction_snapshot = (
            self._full_field_prediction.encoded_snapshot()
            if not outer_rollback_owned and self._full_field_prediction is not None
            else None
        )
        anonymous_snapshot = (
            self._anonymous_passive_window.snapshot_encoded()
            if not outer_rollback_owned and self._anonymous_passive_window is not None
            else None
        )
        inquiry_snapshot = (
            self._causal_inquiry_owner.snapshot_encoded()
            if not outer_rollback_owned and self._causal_inquiry_owner is not None
            else None
        )
        internal_body_snapshot = (
            self._physical_internal_body_state.snapshot_encoded()
            if not outer_rollback_owned and self._physical_internal_body_state is not None
            else None
        )
        recovery_snapshot = (
            self._whole_organism_recovery_owner.snapshot_encoded()
            if not outer_rollback_owned and self._whole_organism_recovery_owner is not None
            else None
        )
        whole_organism_episode_snapshot = (
            self._whole_organism_episode_authority.snapshot_encoded()
            if not outer_rollback_owned and self._whole_organism_episode_authority is not None
            else None
        )
        structural_snapshot = (
            self._whole_organism_structural_owner.snapshot_encoded()
            if not outer_rollback_owned and self._whole_organism_structural_owner is not None
            else None
        )
        tapestry_snapshot = (
            self._causal_mosaic_tapestry_owner.snapshot_encoded()
            if not outer_rollback_owned and self._causal_mosaic_tapestry_owner is not None
            else None
        )
        dream_snapshot = (
            self._organism_dream_wake_weave_owner.snapshot_encoded()
            if not outer_rollback_owned and self._organism_dream_wake_weave_owner is not None
            else None
        )
        neuron_snapshot = (
            self._whole_organism_neuron_population_owner.snapshot_encoded()
            if not outer_rollback_owned and self._whole_organism_neuron_population_owner is not None
            else None
        )
        neurochemical_snapshot = (
            self._whole_organism_neurochemical_owner.snapshot_encoded()
            if not outer_rollback_owned and self._whole_organism_neurochemical_owner is not None
            else None
        )
        recognition_snapshot = (
            self._causal_recognition_attention_owner.snapshot_encoded()
            if not outer_rollback_owned and self._causal_recognition_attention_owner is not None
            else None
        )
        perspective_snapshot = (
            self._embodied_other_perspective_owner.snapshot_encoded()
            if not outer_rollback_owned and self._embodied_other_perspective_owner is not None
            else None
        )
        action_intent_snapshot = (
            self._causal_thing_action_intent.snapshot_encoded()
            if not outer_rollback_owned and self._causal_thing_action_intent is not None
            else None
        )
        prior_latest_settlement = self._latest_causal_settlement
        prior_accepted = self._causal_settlement_accepted
        prior_prediction_observation = (
            self._latest_full_field_prediction_observation
        )
        prior_conditioned_intent = (
            self._prediction_conditioned_intent_receipt
        )
        prior_conditioned_binding = (
            self._prediction_conditioned_binding_id
        )
        prior_inquiry_observation = (
            self._latest_causal_inquiry_observation
        )
        prior_whole_organism_resolution = (
            self._latest_whole_organism_episode_resolution
        )
        auditory_l5_snapshot = (
            self._auditory_l5_owner.transaction_state()
        )
        prior_latest_auditory_l5 = (
            self._latest_auditory_l5_experience
        )
        with self._auditory_transaction_lock:
            prior_auditory_l5_by_assembly = tuple(
                self._auditory_l5_by_assembly.items()
            )
            prior_auditory_joints = tuple(
                self._auditory_prediction_joint_by_transport.items()
            )
            prior_auditory_capabilities = tuple(
                self._auditory_verified_capability_by_transport.items()
            )
        try:
            (
                auditory_transport,
                auditory_cochlear,
                auditory_stream_settlement,
            ) = self._prepare_continuous_auditory_causal_authority(
                settlement=settlement,
                verified_causal_transaction=(
                    verified_causal_transaction
                ),
            )
            self._synchronize_physical_internal_body_state(settlement)
            with self._causal_cycle_bridge_lock:
                self._record_causal_perception_without_dispatch(
                    settlement,
                    prediction_transition=False,
                    publish_acceptance=False,
                    custody_authority=custody_authority,
                    custody_capability=custody_capability,
                    auditory_transport=auditory_transport,
                    auditory_cochlear=auditory_cochlear,
                    auditory_stream_settlement=(
                        auditory_stream_settlement
                    ),
                    verified_causal_transaction=(
                        verified_causal_transaction
                    ),
                )
        except BaseException as error:
            rollback_errors = []
            try:
                self._auditory_l5_owner.rollback_transaction_state(
                    auditory_l5_snapshot
                )
                self._latest_auditory_l5_experience = (
                    prior_latest_auditory_l5
                )
                with self._auditory_transaction_lock:
                    self._auditory_l5_by_assembly = OrderedDict(
                        prior_auditory_l5_by_assembly
                    )
                    self._auditory_prediction_joint_by_transport = (
                        OrderedDict(prior_auditory_joints)
                    )
                    self._auditory_verified_capability_by_transport = (
                        OrderedDict(prior_auditory_capabilities)
                    )
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)
            if prediction_snapshot is not None:
                try:
                    self._full_field_prediction.restore_encoded(
                        prediction_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if anonymous_snapshot is not None:
                try:
                    self._restore_anonymous_passive_window_snapshot(
                        anonymous_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if inquiry_snapshot is not None:
                try:
                    self._restore_causal_inquiry_owner_snapshot(
                        inquiry_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if internal_body_snapshot is not None:
                try:
                    from dsf_ai_service.substrate.physical_internal_body_state import (
                        PhysicalInternalBodyStateAuthority,
                    )
                    internal_key = _hmac.new(
                        self._causal_cycle_key.encode("utf-8"),
                        b"guala-live-physical-internal-body-authority-v1",
                        _hashlib.sha256,
                    ).digest()
                    self._physical_internal_body_state = (
                        PhysicalInternalBodyStateAuthority.restore_encoded(
                            authority_key=internal_key,
                            manifest=(
                                self._physical_internal_body_state.manifest
                            ),
                            encoded=internal_body_snapshot,
                        )
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if recovery_snapshot is not None:
                try:
                    self._restore_whole_organism_recovery_snapshot(
                        recovery_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if whole_organism_episode_snapshot is not None:
                try:
                    self._restore_whole_organism_episode_snapshot(
                        whole_organism_episode_snapshot,
                        structural_encoded=structural_snapshot,
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if tapestry_snapshot is not None:
                try:
                    self._restore_causal_mosaic_tapestry_snapshot(
                        tapestry_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if dream_snapshot is not None:
                try:
                    self._restore_organism_dream_wake_weave_snapshot(
                        dream_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if neuron_snapshot is not None:
                try:
                    self._restore_whole_organism_neuron_population_snapshot(
                        neuron_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if neurochemical_snapshot is not None:
                try:
                    self._restore_whole_organism_neurochemical_snapshot(
                        neurochemical_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if recognition_snapshot is not None:
                try:
                    self._restore_causal_recognition_attention_snapshot(
                        recognition_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if perspective_snapshot is not None:
                try:
                    self._restore_embodied_other_perspective_snapshot(
                        perspective_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            if action_intent_snapshot is not None:
                try:
                    self._causal_thing_action_intent.restore_encoded(
                        action_intent_snapshot
                    )
                except BaseException as rollback_error:
                    rollback_errors.append(rollback_error)
            self._latest_causal_settlement = prior_latest_settlement
            self._causal_settlement_accepted = prior_accepted
            self._latest_full_field_prediction_observation = (
                prior_prediction_observation
            )
            self._prediction_conditioned_intent_receipt = (
                prior_conditioned_intent
            )
            self._prediction_conditioned_binding_id = (
                prior_conditioned_binding
            )
            self._latest_causal_inquiry_observation = (
                prior_inquiry_observation
            )
            self._latest_whole_organism_episode_resolution = (
                prior_whole_organism_resolution
            )
            if rollback_errors:
                raise BaseExceptionGroup(
                    "causal settlement and rollback failed",
                    [error, *rollback_errors],
                )
            raise
        try:
            self._log_substrate_event(
                "causal_settlement_dispatched",
                settlement_receipt_sha256=(
                    settlement.authority_receipt_sha256
                ),
                dispatch_status="passive_physical_intake",
                dispatch_phase="observation",
            )
        except Exception as error:
            print(
                "[GualaLoom][causal-observer] "
                "causal_settlement_dispatched telemetry failed after "
                f"authority commit (non-fatal): {error}",
                file=sys.stderr,
                flush=True,
            )
        return None

    def admit_anonymous_causal_inquiry_window(
        self,
        *,
        settlement,
        window_id,
    ):
        """Transfer one anonymous multisensory window into inquiry custody."""
        raise RuntimeError(
            "legacy owner-scoped causal inquiry is permanently retired; "
            "native exact-field settlement remains authoritative"
        )
        settlement.verify()
        route = self._causal_thing_mosaic_owner.route(settlement)
        if route.state == "unique":
            return {
                "inquiry_state": "thing_owned",
                "meaning_authority": False,
                "schema": "guala.causal_inquiry.admission.v1",
                "settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "thing_ids": list(route.thing_ids),
                "word_authority": False,
            }
        prepared_window = self._anonymous_passive_window.prepare(
            window_id=window_id,
            settlement=settlement,
            world_observation=(
                self._embodiment_world.observation_snapshot()
            ),
        )
        custody = SettledExperienceCustodyAuthority(
            authority_key=self._settled_experience_custody_key,
            w1_physical_authority_key=self._w1_physical_key,
            world_authority_key=self._causal_cycle_key,
            anonymous_passive_window_authority_key=(
                self._anonymous_passive_window_key
            ),
            profile=SettledExperienceCustodyProfile.create(
                profile_id=(
                    "guala-anonymous-inquiry-"
                    + settlement.authority_receipt_sha256[:16]
                ),
                max_children=1,
                max_snapshot_bytes=128 * 1024 * 1024,
            ),
        )
        custody.admit(prepared_window.mount)
        capability = custody.issue_child(CAUSAL_INQUIRY_CONSUMER_ID)
        try:
            prepared_inquiry = self._causal_inquiry_owner.prepare_witness(
                custody_authority=custody,
                custody_capability=capability,
            )
        except BaseException:
            self._anonymous_passive_window.discard_prepared(
                prepared_window
            )
            raise
        try:
            window_undo = self._anonymous_passive_window.commit_prepared(
                prepared_window
            )
        except BaseException:
            self._causal_inquiry_owner.discard_prepared(
                prepared_inquiry
            )
            raise
        try:
            witness_undo = self._causal_inquiry_owner.commit_prepared(
                prepared_inquiry
            )
        except BaseException:
            self._anonymous_passive_window.rollback_committed(
                window_undo
            )
            raise
        witness = prepared_inquiry.result
        need = self._causal_inquiry_owner.retained_need_for_witness(
            witness
        )
        active_need = self._causal_inquiry_owner.active_need
        if need != active_need:
            if active_need is None:
                raise RuntimeError(
                    "queued causal inquiry need lost its active predecessor"
                )
            return {
                "active_need_receipt_sha256": (
                    active_need.authority_receipt_sha256
                ),
                "decision_reason": "older_witness_need_active",
                "decision_state": "queued",
                "inquiry_state": "witness_queued",
                "meaning_authority": False,
                "need_receipt_sha256": (
                    need.authority_receipt_sha256
                ),
                "opportunity_receipt_sha256": None,
                "schema": "guala.causal_inquiry.admission.v1",
                "settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "thing_ids": list(witness.thing_ids),
                "witness_receipt_sha256": (
                    witness.authority_receipt_sha256
                ),
                "word_authority": False,
            }
        try:
            resolution = self._causal_inquiry_owner.prepare_resolution(
                need
            )
            if isinstance(
                resolution,
                PreparedCausalInquiryMutation,
            ):
                try:
                    self._causal_inquiry_owner.commit_prepared(
                        resolution
                    )
                except BaseException:
                    self._causal_inquiry_owner.discard_prepared(
                        resolution
                    )
                    raise
                decision = resolution.result
            else:
                decision = resolution
        except BaseException:
            self._causal_inquiry_owner.rollback_committed(
                witness_undo
            )
            self._anonymous_passive_window.rollback_committed(
                window_undo
            )
            raise
        return {
            "decision_reason": decision.reason,
            "decision_state": decision.state,
            "inquiry_state": "witness_admitted",
            "meaning_authority": False,
            "need_receipt_sha256": need.authority_receipt_sha256,
            "opportunity_receipt_sha256": (
                decision.opportunity.authority_receipt_sha256
                if decision.opportunity is not None
                else None
            ),
            "schema": "guala.causal_inquiry.admission.v1",
            "settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "thing_ids": list(witness.thing_ids),
            "witness_receipt_sha256": (
                witness.authority_receipt_sha256
            ),
            "word_authority": False,
        }

    def _restore_causal_inquiry_owner_snapshot(self, encoded):
        """Replace one failed inquiry transaction with its exact prior bytes."""
        raise RuntimeError(
            "legacy owner-scoped causal inquiry is permanently retired and "
            "cannot be restored"
        )

        current = self._causal_inquiry_owner
        if current is None:
            raise RuntimeError(
                "causal inquiry rollback authority is unavailable"
            )
        owner = CausalInquiryOwner.restore_encoded(
            authority_key=_hmac.new(
                self._causal_cycle_key.encode("utf-8"),
                b"guala-causal-inquiry-owner-v1",
                _hashlib.sha256,
            ).digest(),
            profile=current._profile,
            encoded=encoded,
            thing_owner=self._causal_thing_mosaic_owner,
            articulatory_owner=self._articulatory_self_vocal_owner,
            fresh_articulatory_authority=(
                self._fresh_articulatory_self_acoustic_custody
            ),
            companion_vocal_authority=(
                self._w1_companion_vocal_experience
            ),
            world_authority=self._embodiment_world,
            tutor_authorization_verifier=(
                self._causal_inquiry_tutor_authority.verifier()
            ),
        )
        if owner.snapshot_encoded() != encoded:
            raise RuntimeError(
                "causal inquiry rollback changed prior owner bytes"
            )
        self._causal_inquiry_owner = owner

    def _restore_anonymous_passive_window_snapshot(self, encoded):
        """Replace one failed passive-window mutation with its prior bytes."""
        from dsf_ai_service.substrate.anonymous_passive_window import (
            AnonymousPassiveWindowAuthority,
            MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES,
        )

        current = self._anonymous_passive_window
        if current is None:
            raise RuntimeError(
                "anonymous passive-window rollback authority is unavailable"
            )
        owner = AnonymousPassiveWindowAuthority.restore_encoded(
            authority_key=self._anonymous_passive_window_key,
            profile=current._profile,
            world_authority=self._embodiment_world,
            encoded=encoded,
            max_transfer_bytes=(
                MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES
            ),
        )
        if owner.snapshot_encoded() != encoded:
            raise RuntimeError(
                "anonymous passive-window rollback changed prior owner bytes"
            )
        self._anonymous_passive_window = owner

    @_engine_mutation_entry
    def durably_bootstrap_causal_inquiry(
        self,
        *,
        nonce,
        companion_pcm_s16le,
        state_dir,
    ):
        """Learn one physical attention-seeking act without symbolic input."""
        raise RuntimeError(
            "legacy owner-scoped causal inquiry is permanently retired; "
            "native exact-field settlement remains authoritative"
        )
        required = (
            self._causal_inquiry_owner,
            self._causal_inquiry_tutor_authority,
            self._articulatory_exploration_selector,
            self._articulatory_self_vocal_owner,
            self._w1_self_acoustic_propagation,
            self._fresh_articulatory_self_acoustic_custody,
            self._articulatory_consequence_closure,
            self._w1_companion_vocal_experience,
            self._causal_thing_mosaic_owner,
            self._causal_thing_lived_context,
            self._embodiment_world,
        )
        if any(value is None for value in required):
            raise RuntimeError(
                "causal inquiry tutor transaction is unavailable"
            )
        if (
            not isinstance(nonce, bytes)
            or len(nonce) != 32
        ):
            raise ValueError(
                "causal inquiry tutor nonce must be exactly 32 bytes"
            )
        if (
            not isinstance(companion_pcm_s16le, bytes)
            or not companion_pcm_s16le
        ):
            raise ValueError(
                "causal inquiry tutor response must be physical PCM16"
            )
        if (
            state_dir is not None
            and not callable(getattr(
                self,
                "_authoritative_hot_generation_publisher",
                None,
            ))
        ):
            raise RuntimeError(
                "authoritative causal inquiry durability is unavailable"
            )

        from fractions import Fraction
        from dsf_ai_service.substrate.embodiment_world import (
            MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        )
        from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
            FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID,
        )

        owner = self._causal_inquiry_owner
        selector = self._articulatory_exploration_selector
        articulatory = self._articulatory_self_vocal_owner
        acoustic = self._w1_self_acoustic_propagation
        fresh_authority = (
            self._fresh_articulatory_self_acoustic_custody
        )
        things = self._causal_thing_mosaic_owner
        companion = self._w1_companion_vocal_experience
        consequence = self._articulatory_consequence_closure
        world = self._embodiment_world

        with self._causal_cycle_bridge_lock, self.persistence_transaction():
            need = owner.active_need
            if need is None:
                raise ValueError(
                    "causal inquiry tutor control requires one active need"
                )
            if owner.bindings:
                raise ValueError(
                    "causal inquiry tutor bootstrap is already learned"
                )
            witness = next(
                value
                for value in owner.witnesses
                if value.authority_receipt_sha256
                == need.witness_receipt_sha256
            )
            before = world.observation_snapshot()
            if (
                before.authority_receipt_sha256
                != witness.world_observation_receipt_sha256
            ):
                raise ValueError(
                    "causal inquiry world changed after its active need"
                )
            selection = selector.select()
            selector.verify_selection(selection)
            if (
                selection.state
                is not ArticulatoryExplorationState.SELECTED
                or selection.program is None
                or selection.physical_action is None
            ):
                raise ValueError(
                    "causal inquiry has no unique physical articulation"
                )
            authorization = (
                self._causal_inquiry_tutor_authority.issue(
                    need_receipt_sha256=(
                        need.authority_receipt_sha256
                    ),
                    world_observation_receipt_sha256=(
                        witness.world_observation_receipt_sha256
                    ),
                    program_id=selection.program.program_id,
                    nonce=nonce,
                )
            )
            inquiry_before = owner.snapshot_encoded()
            prepared_acoustic = None
            acoustic_undo = None
            self_thing_prepared = None
            self_thing_undo = None
            self_lived_undos = ()
            episode_prepared = None
            episode_undo = None
            response_custody = None
            response_thing_prepared = None
            response_thing_undo = None
            response_lived_undos = ()
            consequence_prepared = None
            consequence_committed = None
            try:
                synthesis = articulatory.synthesize(
                    program_id=selection.program.program_id,
                    source_time_start=Fraction(
                        before.revision
                        * MAX_VOCAL_SAMPLE_COUNT,
                        VOCAL_SAMPLE_RATE_HZ,
                    ),
                )
                prepared_emission = (
                    articulatory.prepare_generated_emission(
                        synthesis=synthesis,
                        world_authority=world,
                        causal_intent_receipt_sha256=(
                            authorization.authority_receipt_sha256
                        ),
                    )
                )
                prepared_acoustic = acoustic.prepare_articulatory(
                    prepared_emission,
                    articulatory_owner=articulatory,
                )
                emission, self_mount, acoustic_undo = (
                    acoustic.commit_prepared_articulatory(
                        prepared_acoustic
                    )
                )
                self_custody = self._settled_self_acoustic_custody(
                    self_mount,
                    world_execution=emission.execution_receipt,
                )
                self_thing_prepared = (
                    self
                    ._prepare_ordered_thing_continuation_from_custodies(
                        (self_custody,)
                    )
                )
                if self_thing_prepared is None:
                    raise ValueError(
                        "causal inquiry articulation has no continuously "
                        "held physical THING"
                    )
                self_thing_undo = (
                    things
                    .commit_prepared_ordered_custody_continuation(
                        self_thing_prepared
                    )
                )
                self_lived_undos = (
                    self._commit_lived_context_partitions(
                        (self_custody,),
                        self_thing_prepared.partitions,
                    )
                )
                fresh_capability = (
                    self_custody.authority.issue_child(
                        FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID
                    )
                )
                fresh_receipt = fresh_authority.seal(
                    synthesis=synthesis,
                    emission=emission,
                    acoustic_mount=self_mount,
                    settled_custody_authority=(
                        self_custody.authority
                    ),
                    settled_custody_capability=fresh_capability,
                )
                prepared_attempt = owner.prepare_attempt(
                    need=need,
                    fresh_articulatory_receipt=fresh_receipt,
                    tutor_authorization=authorization,
                    exploration_selector=selector,
                    exploration_selection=selection,
                )
                owner.commit_prepared(prepared_attempt)

                episode_prepared = companion.prepare_episode(
                    pcm_s16le=companion_pcm_s16le,
                    causal_parent_receipt_sha256=(
                        fresh_receipt.authority_receipt_sha256
                    ),
                )
                if len(episode_prepared.prediction_blocks) != 1:
                    raise ValueError(
                        "causal inquiry tutor response must be one "
                        "physical vocal block"
                    )
                response_block = (
                    episode_prepared.prediction_blocks[0]
                )
                response_custody = self._settled_prediction_custody(
                    response_block.physical_mount,
                    world_execution=response_block.execution_receipt,
                )
                response_thing_prepared = (
                    self
                    ._prepare_ordered_thing_continuation_from_custodies(
                        (response_custody,)
                    )
                )
                if response_thing_prepared is None:
                    raise ValueError(
                        "causal inquiry tutor response lost physical "
                        "THING continuity"
                    )
                inquiry_capability = (
                    response_custody.authority.issue_child(
                        CAUSAL_INQUIRY_CONSUMER_ID
                    )
                )
                prepared_closure = owner.prepare_closure(
                    attempt=prepared_attempt.result,
                    tutor_response=response_block.execution_receipt,
                    later_custody_authority=(
                        response_custody.authority
                    ),
                    later_custody_capability=inquiry_capability,
                    companion_episode_intent=(
                        episode_prepared.intent_receipt
                    ),
                )
                consequence_prepared = consequence.prepare(
                    fresh_receipt,
                    response_block.execution_receipt,
                    companion_episode_intent=(
                        episode_prepared.intent_receipt
                    ),
                )
                episode_undo = companion.commit_episode(
                    episode_prepared
                )
                consequence_committed = consequence.commit_prepared(
                    consequence_prepared
                )
                owner.commit_prepared(prepared_closure)
                response_thing_undo = (
                    things
                    .commit_prepared_ordered_custody_continuation(
                        response_thing_prepared
                    )
                )
                response_lived_undos = (
                    self._commit_lived_context_partitions(
                        (response_custody,),
                        response_thing_prepared.partitions,
                    )
                )
                result = {
                    "authorization_receipt_sha256": (
                        authorization.authority_receipt_sha256
                    ),
                    "binding_receipt_sha256": (
                        prepared_closure.result
                        .authority_receipt_sha256
                    ),
                    "full_dsf_field_preserved": True,
                    "label_authority": False,
                    "meaning_authority": False,
                    "nonce_sha256": authorization.nonce_sha256,
                    "program_id": selection.program.program_id,
                    "reduced_approximation": False,
                    "response_execution_receipt_sha256": (
                        response_block.execution_receipt
                        .authority_receipt_sha256
                    ),
                    "response_pcm_sha256": (
                        episode_prepared.intent_receipt.pcm_sha256
                    ),
                    "schema": (
                        "guala.causal_inquiry.tutor_bootstrap.v1"
                    ),
                    "self_hearing_receipt_sha256": (
                        fresh_receipt.authority_receipt_sha256
                    ),
                    "state": "learned_physical_attention_act",
                    "word_authority": False,
                    "world_revision_after": (
                        world.observation_snapshot().revision
                    ),
                    "world_revision_before": before.revision,
                }
                if state_dir is not None:
                    self.save_hot_state(state_dir)
                return result
            except BaseException:
                self._rollback_lived_context_admissions(
                    response_lived_undos
                )
                if response_thing_undo is not None:
                    (
                        things
                        .rollback_committed_ordered_custody_continuation(
                            response_thing_undo
                        )
                    )
                elif response_thing_prepared is not None:
                    (
                        things
                        .discard_prepared_ordered_custody_continuation(
                            response_thing_prepared
                        )
                    )
                self._restore_causal_inquiry_owner_snapshot(
                    inquiry_before
                )
                if consequence_committed is not None:
                    consequence.rollback_committed(
                        consequence_committed.undo
                    )
                elif consequence_prepared is not None:
                    consequence.discard_prepared(
                        consequence_prepared
                    )
                if episode_undo is not None:
                    companion.rollback_committed_episode(
                        episode_undo
                    )
                elif episode_prepared is not None:
                    companion.discard_episode(
                        episode_prepared
                    )
                self._rollback_lived_context_admissions(
                    self_lived_undos
                )
                if self_thing_undo is not None:
                    (
                        things
                        .rollback_committed_ordered_custody_continuation(
                            self_thing_undo
                        )
                    )
                elif self_thing_prepared is not None:
                    (
                        things
                        .discard_prepared_ordered_custody_continuation(
                            self_thing_prepared
                        )
                    )
                if acoustic_undo is not None:
                    acoustic.rollback_committed_articulatory(
                        acoustic_undo
                    )
                elif prepared_acoustic is not None:
                    acoustic.discard_prepared_articulatory(
                        prepared_acoustic
                    )
                if response_custody is not None:
                    source_key = (
                        response_custody.view
                        .physical_evidence_receipt
                        .authority_receipt_sha256
                    )
                    if (
                        self._live_settled_prediction_custodies.get(
                            source_key
                        )
                        is response_custody
                    ):
                        del self._live_settled_prediction_custodies[
                            source_key
                        ]
                raise

    def learn_grounded_articulatory_relation(self, occurrences):
        """Admit repeated lived teaching occurrences without semantic labels."""
        if self._grounded_articulatory_vocal_turn is None:
            raise RuntimeError(
                "grounded articulatory vocal authority is unavailable"
            )
        return self._grounded_articulatory_vocal_turn.learn(occurrences)

    def prepare_grounded_articulatory_vocal_turn(
        self,
        *,
        external_form,
        lived_context_event,
    ):
        """Prepare one exact learned physical vocal turn, or return silence."""
        if self._grounded_articulatory_vocal_turn is None:
            raise RuntimeError(
                "grounded articulatory vocal authority is unavailable"
            )
        return self._grounded_articulatory_vocal_turn.prepare_turn(
            external_form=external_form,
            lived_context_event=lived_context_event,
        )

    def commit_grounded_articulatory_vocal_turn(self, prepared):
        """Commit one prepared articulatory emission and self-hearing edge."""
        if self._grounded_articulatory_vocal_turn is None:
            raise RuntimeError(
                "grounded articulatory vocal authority is unavailable"
            )
        return self._grounded_articulatory_vocal_turn.commit_prepared(
            prepared
        )

    def discard_grounded_articulatory_vocal_turn(self, prepared):
        """Discard one prepared vocal turn without physical emission."""
        if self._grounded_articulatory_vocal_turn is None:
            raise RuntimeError(
                "grounded articulatory vocal authority is unavailable"
            )
        self._grounded_articulatory_vocal_turn.discard_prepared(
            prepared
        )

    def _drain_auditory_terminal_pipeline(self):
        """Drain and publish a terminal continuation's final lifecycle."""
        try:
            self._drain_auditory_terminal_pipeline_body()
        except BaseException as error:
            with self._auditory_terminal_pipeline_lock:
                self._auditory_terminal_pipeline_worker_error = error
            self._log_substrate_event(
                "auditory_terminal_pipeline_worker_failed",
                error_type=type(error).__name__,
                error=str(error),
            )
        finally:
            with self._auditory_terminal_pipeline_lock:
                abandoned = self._auditory_terminal_pipeline_in_flight
                if abandoned is not None:
                    self._auditory_terminal_pipeline_capabilities.pop(
                        abandoned.task_id,
                        None,
                    )
                self._auditory_terminal_pipeline_worker_active = False
                self._auditory_terminal_pipeline_in_flight = None
