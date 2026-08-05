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

- ``POST /api/v1/curriculum/teach-card`` delivers one approved curriculum
  card (its physical surface luminance and its tutor audio pressure) as one
  admitted native episode.  The card's letter or number identity is never
  written into the organism; only the physical media samples are delivered.
- ``POST /sound_frame`` and the mono ``/api/v1/auditory/pcm`` session
  deliver caller-supplied PCM pressure as admitted native episodes carrying
  the whole mounted sensorium: both ear pressure ports plus all 27
  card-surface receptor sites at their true dark 0.0 luminance (ratified
  2026-08-05: no single-sense experiences).

Public observation is one cached, read-only projection per persisted native
generation.  Repeated reads do not call or advance the organism.  Every
accepted admitted intake (one lesson of hop transitions) commits its hops on
the in-process organism, persists and publishes the successor body exactly
once after its final hop, and only then refreshes this cache; readiness is
served under the same lock, so no surface ever reports unpersisted state.
"""

from __future__ import annotations

import base64
import binascii
from contextlib import asynccontextmanager
from fractions import Fraction
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import struct
import threading
from typing import Any, Iterable
import uuid
import wave

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    NativeJointSourceOccurrenceInput,
    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.native_resident_organism import (
    ResidentPrepareEvidence,
    create_native_resident_organism,
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
    NativeOrganismBinaryStoreError,
    RestoredNativeOrganism,
    publish_staged_native_organism,
    restore_current_native_organism,
    stage_active_native_organism,
)
from dsf_ai_service.substrate.native_resident_resource_admission import (
    NativeResidentResourceAdmission,
    derive_native_resident_resource_admission,
)


APP_SCHEMA = "guala.native_production_http.v1"
PUBLIC_OBSERVATION_SCHEMA = "guala.native.public_observation.v1"
PERSISTENCE_SCHEMA = "guala.native_organism_binary_store.v1"
STATE_ROOT = Path(
    os.environ.get("GUALA_NATIVE_ORGANISM_ROOT", "/app/guala/native-organism")
)
STATIC_ROOT = Path(__file__).resolve().parent / "static"
CURRICULUM_ROOT = Path(__file__).resolve().parents[1] / "guala_curriculum"
CARD_ROOT = CURRICULUM_ROOT / "cards"
AUDIO_ROOT = CURRICULUM_ROOT / "audio"

# Durable content-addressed hippocampal cold custody and the local mirror of
# the immutable generation object store both live beside the organism body.
HIPPOCAMPAL_COLD_DIRECTORY = "hippocampal-cold"
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
EAR_PORT_COUNT = 2
LESSON_PORT_COUNT = CARD_SURFACE_PORT_COUNT + EAR_PORT_COUNT
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
PCM_SESSION_MAX_SAMPLES = 16_000 * AMBIENT_INTAKE_MAX_SECONDS
# One presentation is delivered as successive short occurrences ("hops") on
# this app's declared 250 ms capture interval (the same sampling interval the
# visual capture contract below declares).  Longer single occurrences
# accumulate receptor gate work past the exact dissipation lattice and are
# refused by neuron physics, so the hop is a transport contract, not physics.
INTAKE_HOP_MILLISECONDS = 250
INTAKE_HOP_MAX_FRAMES = 256
assert (
    LESSON_PORT_COUNT * INTAKE_HOP_MAX_FRAMES
    <= MAX_NATIVE_SAMPLES_PER_SETTLEMENT
), "declared lesson hop exceeds the ratified settlement sample bound"
# Frame count of one quiescent (dark, silent) hop; the same timebase carries
# the partial-presentation glimpse hop below.
QUIESCENT_HOP_FRAME_COUNT = INTAKE_HOP_MAX_FRAMES // 2

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

_ORGANISM_IDENTITY_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)

_restored: RestoredNativeOrganism | None = None
_admission: NativeResidentResourceAdmission | None = None
_boot_error: str | None = None
_public_observation_body: bytes | None = None
_public_observation_etag: str | None = None
_last_transition_evidence: dict[str, Any] | None = None
_transition_lock = threading.Lock()
_pcm_sessions: dict[str, dict[str, Any]] = {}


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
    observed = restored.organism.readiness()
    return {
        "cognitive_mosaic_count": observed.cognitive_mosaic_count,
        "cognitive_ordinal": observed.cognitive_ordinal,
        "cognitive_trace_count": observed.cognitive_trace_count,
        "complete_neuron_count": getattr(observed, "complete_neuron_count", 0),
        "fabric_bytes": observed.fabric_bytes,
        "fabric_generation": observed.fabric_generation,
        "fabric_sha256": observed.fabric_sha256,
        "formation_activation_count": observed.formation_activation_count,
        "identity": observed.identity,
        "joint_field_count": observed.joint_field_count,
        "mounted_generation": observed.mounted_generation,
        "organism_tick": observed.organism_tick,
        "partial_cue_reassembly_count": observed.partial_cue_reassembly_count,
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
) -> None:
    for experience in experiences:
        for key in media_keys:
            item = experience.get(key)
            media_path = item.get("path") if isinstance(item, dict) else None
            if not isinstance(media_path, str):
                raise ValueError(f"curriculum {key} path changed")
            relative = media_path.removeprefix("guala_curriculum/")
            if not (CURRICULUM_ROOT / relative).is_file():
                raise ValueError(f"curriculum media is absent: {media_path}")


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
        _require_manifest_media(cards, ("surface", "tutor_audio"))
        _require_manifest_media(songs, ("audio",))
        if len(cards) != 36 or len(songs) != 3:
            raise ValueError("approved curriculum extent changed")
        return _section(
            True,
            "external_media_ready_native_tutoring_mounted",
            "36 card/audio pairs and three songs are present; one approved "
            "card and its tutor audio reach the resident organism as one "
            "admitted native episode via POST /api/v1/curriculum/teach-card; "
            "no label, identity, or meaning enters the organism",
            approved_card_experience_count=36,
            approved_song_experience_count=3,
            internal_identity_authority=False,
            internal_meaning_authority=False,
            manifest_path="/curriculum/card_experience_manifest-v1.json",
            teach_card_endpoint="/api/v1/curriculum/teach-card",
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


def _sensory_record() -> dict[str, object]:
    modalities = {
        "visual": _section(
            True,
            "curriculum_card_surface_transition_mounted",
            "approved curriculum card surfaces reach the resident organism "
            "as admitted 27-receptor luminance occurrences via "
            "/api/v1/curriculum/teach-card; no live camera transition is "
            "mounted",
        ),
        "auditory": _section(
            True,
            "lesson_audio_only_standalone_hearing_suspended",
            "tutor audio inside card lessons reaches the resident organism "
            "as admitted pressure occurrences; standalone hearing is "
            "suspended by the ratified two-real-signal doctrine until a "
            "live visual source mounts; the binaural transition is not "
            "mounted",
        ),
        "text": _unmounted("native rendered-light receptor transition is not mounted"),
        "touch": _unmounted("native touch receptor transition is not mounted"),
        "temperature": _unmounted("native temperature receptor transition is not mounted"),
        "smell": _unmounted("native smell receptor transition is not mounted"),
        "taste": _unmounted("native taste receptor transition is not mounted"),
        "vestibular": _unmounted("native vestibular receptor transition is not mounted"),
        "proprioception": _unmounted("native proprioceptive transition is not mounted"),
        "interoception": _unmounted("native interoceptive transition is not mounted"),
    }
    return _section(
        True,
        "partial_native_receptor_transitions",
        "admitted visual card-surface and mono auditory transitions are "
        "mounted; every other modality has no native receptor transition",
        **modalities,
    )


def _last_transition_record() -> dict[str, object]:
    if _last_transition_evidence is None:
        return _section(
            False,
            "no_transition_this_process",
            "no admitted native transition has been committed by this process",
        )
    return _section(
        True,
        "committed_admitted_transition",
        "facts of the most recent committed admitted transition in this process",
        **_last_transition_evidence,
    )


def _build_public_observation() -> dict[str, Any]:
    native = _native_record()
    last = _last_transition_record()
    last_fractal_count = (
        _last_transition_evidence["complete_neuron_fractal_count"]
        if _last_transition_evidence is not None
        else 0
    )
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
            build=_build_identity(),
            continuity="one raw native CURRENT lineage",
            value=native["identity"],
        ),
        "organism": _section(
            True,
            "native_current_with_admitted_sensory_transitions",
            "native state is restored; admitted curriculum and mono auditory "
            "transitions are mounted; autonomous thought and action are not",
            physical_transition_claimed=native["physical_transition_claimed"],
            state_bytes=native["state_bytes"],
            tick=native["organism_tick"],
        ),
        "capabilities": {
            "camera": _capability("native visual sensory transition is not mounted"),
            "microphone": _capability(
                "standalone hearing is not mounted: the two-real-signal "
                "doctrine requires a concurrent live visual source, which "
                "does not exist yet; tutor audio inside card lessons remains"
            ),
            "curriculum": _mounted_capability(
                "/api/v1/curriculum/teach-card",
                "one approved card surface and its tutor audio reach the "
                "resident organism as one admitted native episode",
            ),
            "text_visual": _capability("native rendered-light transition is not mounted"),
            "picture": _capability("native visual material presentation is not mounted"),
            "pdf": _capability("native paged visual presentation is not mounted"),
            "book": _capability("native paged visual presentation is not mounted"),
            "audio": _capability("native auditory material presentation is not mounted"),
            "song": _capability("native auditory material presentation is not mounted"),
            "gutenberg": _capability("bounded Gutenberg presentation is not mounted"),
            "youtube": _capability("bounded YouTube presentation is not mounted"),
            "khan_academy": _capability("bounded Khan Academy presentation is not mounted"),
            "pbs_kids": _capability("bounded PBS Kids presentation is not mounted"),
            "spotify": _capability("bounded Spotify presentation is not mounted"),
        },
        "sensory": _sensory_record(),
        "neuron_activity": _section(
            True,
            "retained_complete_neuron_state",
            "retained count is decoded native cognitive state; a live "
            "activity projection is not mounted",
            active_count=None,
            historical_reached_dsf_perspective_count=native[
                "reached_dsf_perspective_count"
            ],
            retained_count=native["complete_neuron_count"],
        ),
        "fractals": _section(
            _last_transition_evidence is not None,
            (
                "last_committed_transition_fractals"
                if _last_transition_evidence is not None
                else "no_transition_this_process"
            ),
            "complete-neuron fractal counts are per-transition step facts; "
            "the value reports the most recent committed transition in this "
            "process",
            count=last_fractal_count,
        ),
        "formations": _section(
            True,
            "physical_mosaic_state_only",
            "mosaic count is decoded native cognitive state; no higher "
            "formation is mounted",
            mosaic_count=native["cognitive_mosaic_count"],
            mosaic_of_mosaics_count=0,
            tapestry_count=0,
            tapestry_of_tapestries_count=0,
            weave_count=0,
        ),
        # Truth-coupled to the decoded native observation: the count is the
        # last committed transition's step fact, never a hardwired zero.
        "recall": _section(
            native["partial_cue_reassembly_count"] > 0,
            (
                "physical_partial_cue_reassembly_observed"
                if native["partial_cue_reassembly_count"] > 0
                else "no_reassembly_in_last_committed_transition"
            ),
            "partial-cue reassembly count is the decoded native observation "
            "of the last committed transition; no separate recall query "
            "surface is mounted",
            partial_cue_reassembly_count=native["partial_cue_reassembly_count"],
        ),
        "cognitive_capital": _section(
            False,
            "not_implemented",
            "no physical cognitive operation supplies capital evidence",
            credits=[],
            scalar_score_authority=False,
        ),
        "attention": _unmounted("no substrate attention operation is mounted"),
        "body": _unmounted("no native body, world, motor, or consequence transition is mounted"),
        "autonomy": _unmounted(
            "no native causal thought/action loop is mounted",
            action_observed=False,
            consequence=_unmounted("no autonomous action consequence exists"),
        ),
        "articulation": _unmounted(
            "no native articulation or emitted-sound transition is mounted"
        ),
        "expression": _unmounted(
            "no native gaze, face, or body expression actuator is mounted"
        ),
        "curriculum": _curriculum_media_record(),
        "last_transition": last,
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
    record["snapshot_receipt_sha256"] = _receipt(record)
    return record


def _refresh_public_observation_cache() -> None:
    global _public_observation_body, _public_observation_etag
    body = _canonical(_build_public_observation())
    _public_observation_body = body
    _public_observation_etag = f'"{hashlib.sha256(body).hexdigest()}"'


def _readiness() -> dict[str, Any]:
    native = _native_record()
    cognition_present = bool(
        native["cognitive_ordinal"]
        or native["cognitive_trace_count"]
        or native["cognitive_mosaic_count"]
    )
    return {
        "app_schema": APP_SCHEMA,
        "organism_tick": native["organism_tick"],
        "identity": native["identity"],
        "native_resident": {
            "available": True,
            **native,
            "complete_neuron_available": native["complete_neuron_count"] > 0,
            "genuine_neuronal_fractal_available": bool(
                _last_transition_evidence is not None
                and _last_transition_evidence["complete_neuron_fractal_count"] > 0
            ),
            "cognition_available": cognition_present,
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
        **_build_identity(),
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
        path = self._path(key)
        body = path.read_bytes()
        if len(body) != byte_count or hashlib.sha256(body).hexdigest() != sha256:
            raise NativeOrganismBinaryStoreError(
                "native object mirror retirement changed"
            )
        path.unlink()


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
        existing = self.client.head_object(Bucket=self.bucket, Key=key)
        if (
            existing.get("ContentLength") != byte_count
            or existing.get("Metadata", {}).get("sha256") != sha256
        ):
            raise NativeOrganismBinaryStoreError(
                "native remote predecessor changed"
            )
        self.client.delete_object(Bucket=self.bucket, Key=key)


def _object_store() -> Any:
    bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET")
    if bucket:
        import boto3

        return _S3ObjectStore(bucket=bucket, client=boto3.client("s3"))
    return _LocalDirectoryObjectStore(STATE_ROOT / LOCAL_OBJECT_MIRROR_DIRECTORY)


def _hippocampal_cold_root() -> Path:
    return STATE_ROOT / HIPPOCAMPAL_COLD_DIRECTORY


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


def _ear_ports(
    source_times: tuple[Fraction, ...],
    signal: tuple[float, ...],
) -> tuple[NativeSensorySubstreamInput, ...]:
    """Both co-located organism ears immersed in one ambient pressure field."""

    return tuple(
        _ear_pressure_substream(ear_index, source_times, signal)
        for ear_index in range(EAR_PORT_COUNT)
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
) -> NativeJointSourceOccurrenceInput:
    return NativeJointSourceOccurrenceInput(
        port_indices=port_indices,
        source_times=source_times,
        joint_intersample_profile_payload=(
            UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
        ),
        groups=(tuple(range(len(port_indices))),),
        joint_relevance_profile_payload=JOINT_RELEVANCE_PROFILE,
        joint_relevance=(Fraction(1),) * relevance_count,
    )


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
        PhysicalSense.SOUND: _ear_ports(times, quiescent),
    }
    return settle_native_joint_source_episode(
        assembly_id="guala-production-declared-anatomy",
        observed_substreams=observed,
        states=_sense_states(observed),
        occurrences=(
            _occurrence(tuple(range(LESSON_PORT_COUNT)), times, len(times)),
        ),
    )


def _authored_growth_dna() -> tuple[Any, list[tuple[list[int], list[tuple[int, int, int]]]]]:
    """Authored growth DNA over the app's declared roster.

    One seed group chains the 27 retinal card-surface receptor sites; under
    the ratified retinal receptor law only an exact optical occurrence can
    genesis a cohort, so the seed's sites are exactly that first reached
    cohort.  The ear sites carry no authored contacts; they join the grown
    cohort later by reached extension.  Every authored contact is the
    ratified authored 500 pS conductance, mirroring the ratified chain-seed
    growth fixtures.
    """

    episode = _declared_anatomy_episode()
    contacts = [
        (index - 1, index, AUTHORED_SEED_CONDUCTANCE_PICOSIEMENS)
        for index in range(1, CARD_SURFACE_PORT_COUNT)
    ]
    return (episode, [(list(range(CARD_SURFACE_PORT_COUNT)), contacts)])


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


def _commit_admitted_hop(
    organism: Any,
    episode: Any,
    maximum_causal_intervals: list[tuple[int, int]],
) -> dict[str, Any]:
    """Prepare and commit one admitted hop on the in-process organism only.

    No persistence happens here.  The caller holds ``_transition_lock`` and
    must durably publish the committed body before any observation surface
    reports it.  Returns only what the native observation actually says.
    """

    evidence: ResidentPrepareEvidence = organism.prepare_admitted(
        episode,
        maximum_causal_intervals,
        _hippocampal_cold_root(),
    )
    observed = organism.commit(evidence.token)
    return {
        "cognitive_mosaic_count": observed.cognitive_mosaic_count,
        "cognitive_trace_count": observed.cognitive_trace_count,
        "complete_neuron_count": getattr(
            observed, "complete_neuron_count", 0
        ),
        "complete_neuron_fractal_count": (
            evidence.complete_neuron_fractal_count
        ),
        "current_cohort_evaluation_count": (
            evidence.current_cohort_evaluation_count
        ),
        "dsf_delivery_count": evidence.dsf_delivery_count,
        "formation_activation_count": observed.formation_activation_count,
        "organism_tick": observed.organism_tick,
        "partial_cue_reassembly_count": (
            observed.partial_cue_reassembly_count
        ),
        "physically_transitioned_neuron_count": (
            evidence.physically_transitioned_neuron_count
        ),
        "recurrent_complete_neuron_fractal_count": (
            evidence.recurrent_complete_neuron_fractal_count
        ),
        "state_sha256": observed.state_sha256,
    }


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
    global _public_observation_body, _public_observation_etag

    try:
        staged = stage_active_native_organism(
            STATE_ROOT,
            organism,
            max_envelope_bytes=admission.max_envelope_bytes,
        )
        return publish_staged_native_organism(
            staged,
            expected_predecessor_sha256=predecessor_state_sha256,
            object_store=_object_store(),
            max_envelope_bytes=admission.max_envelope_bytes,
            max_fabric_bytes=admission.max_fabric_bytes,
            max_logical_peak_bytes=admission.max_logical_peak_bytes,
        )
    except BaseException as error:
        _restored = None
        _boot_error = (
            "committed native successor could not be published: "
            f"{type(error).__name__}: {error}"
        )
        _public_observation_body = None
        _public_observation_etag = None
        raise HTTPException(status_code=503, detail=_boot_error) from error


def _perform_admitted_intake(
    episodes: list[tuple[Any, list[tuple[int, int]]]],
    intake: str,
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

    global _restored, _last_transition_evidence

    totals = {
        "complete_neuron_fractal_count": 0,
        "current_cohort_evaluation_count": 0,
        "dsf_delivery_count": 0,
        "partial_cue_reassembly_count": 0,
        "physically_transitioned_neuron_count": 0,
        "recurrent_complete_neuron_fractal_count": 0,
    }
    with _transition_lock:
        restored, admission = _runtime()
        organism = restored.organism
        predecessor = restored.pointer
        last_hop: dict[str, Any] | None = None
        committed_hop_count = 0
        intake_error: Exception | None = None
        try:
            for episode, admissions in episodes:
                last_hop = _commit_admitted_hop(
                    organism, episode, admissions
                )
                committed_hop_count += 1
                for key in totals:
                    totals[key] += last_hop[key]
        except (RuntimeError, TypeError, ValueError) as error:
            intake_error = error
        if last_hop is None or committed_hop_count == 0:
            if intake_error is not None:
                raise intake_error
            raise RuntimeError("admitted intake carried no hop episodes")
        published = _publish_committed_organism(
            organism, admission, predecessor.state_sha256
        )
        _restored = RestoredNativeOrganism(
            organism=organism, pointer=published.pointer
        )
        _last_transition_evidence = {
            **last_hop,
            "hop_count": committed_hop_count,
            "intake": intake,
            "predecessor_state_sha256": predecessor.state_sha256,
            "totals": dict(totals),
        }
        _refresh_public_observation_cache()
        if intake_error is not None:
            raise intake_error
        return {
            "accepted": True,
            "ok": True,
            "hop_count": committed_hop_count,
            "observation": dict(_last_transition_evidence),
            "persisted": {
                "organism_tick": published.pointer.organism_tick,
                "predecessor_state_sha256": predecessor.state_sha256,
                "schema": PERSISTENCE_SCHEMA,
                "state_bytes": published.pointer.state_bytes,
                "state_sha256": published.pointer.state_sha256,
            },
            "schema": "guala.native_admitted_intake_result.v1",
            "totals": totals,
        }


def _card_surface_luminance(surface_path: Path) -> tuple[float, ...]:
    """Row-major area-averaged luminance of one approved card raster.

    Pillow BOX resampling integrates the true pixel field over each receptor
    site's area; the result is the physical mean luminance in [0, 1].
    """

    from PIL import Image

    with Image.open(surface_path) as image:
        reduced = image.convert("L").resize(
            (CARD_SURFACE_COLUMNS, CARD_SURFACE_ROWS),
            Image.Resampling.BOX,
        )
        values = tuple(reduced.tobytes())
    return tuple(value / 255.0 for value in values)


def _pcm_hops(
    samples: tuple[int, ...],
    sample_rate_hz: int,
) -> list[tuple[tuple[Fraction, ...], tuple[float, ...]]]:
    """Slice PCM into successive hop occurrences of true retained instants.

    Each hop covers at most ``INTAKE_HOP_MILLISECONDS`` of the capture.
    Decimation inside a hop keeps every stride-th physical sample with its
    exact within-hop source time; retained frames respect the ratified
    transport limits (``MAX_NATIVE_SAMPLES_PER_SUBSTREAM`` and the hop frame
    bound).  A trailing remainder with fewer than two retained samples cannot
    declare an occurrence and is dropped.
    """

    hop_samples = max(2, sample_rate_hz * INTAKE_HOP_MILLISECONDS // 1000)
    frame_budget = min(
        MAX_NATIVE_SAMPLES_PER_SUBSTREAM, INTAKE_HOP_MAX_FRAMES
    )
    hops: list[tuple[tuple[Fraction, ...], tuple[float, ...]]] = []
    for start in range(0, len(samples), hop_samples):
        window = samples[start : start + hop_samples]
        stride = max(1, -(-len(window) // frame_budget))
        indices = range(0, len(window), stride)
        if len(indices) < 2:
            continue
        times = tuple(Fraction(index, sample_rate_hz) for index in indices)
        signal = tuple(window[index] / 32768.0 for index in indices)
        hops.append((times, signal))
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

    return tuple(
        Fraction(index, QUIESCENT_HOP_FRAME_COUNT)
        * Fraction(INTAKE_HOP_MILLISECONDS, 1000)
        for index in range(QUIESCENT_HOP_FRAME_COUNT)
    )


def _whole_roster_hop_episode(
    assembly_id: str,
    times: tuple[Fraction, ...],
    surface_levels: tuple[float, ...],
    ear_signal: tuple[float, ...],
    *,
    separate_optical_occurrence: bool = False,
) -> Any:
    """One hop over the whole declared roster on one shared clock.

    ``surface_levels`` carries one constant luminance per card receptor site
    for the hop; dark sites carry their true 0.0 quiescent samples exactly as
    the ordinary ended hops do.

    ``separate_optical_occurrence`` declares the card surface and the ears as
    two co-clocked occurrences instead of one combined occurrence.  This
    matters physically, not cosmetically: the ratified retinal receptor law
    settles a reached cohort only for an EXACT optical occurrence (every port
    of the occurrence a retinal sight port), so a combined sight+sound
    occurrence delivers its samples without settling the cohort's receptor
    physics.  A presentation that must reach the retinal cohort — the first
    hop of a lesson and every partial-cue hop — declares the surface as its
    own exact optical occurrence.
    """

    frame_count = len(times)
    observed = {
        PhysicalSense.SIGHT: tuple(
            _card_surface_substream(
                row,
                column,
                times,
                (surface_levels[row * CARD_SURFACE_COLUMNS + column],)
                * frame_count,
            )
            for row in range(CARD_SURFACE_ROWS)
            for column in range(CARD_SURFACE_COLUMNS)
        ),
        PhysicalSense.SOUND: _ear_ports(times, ear_signal),
    }
    if separate_optical_occurrence:
        occurrences = (
            _occurrence(
                tuple(range(CARD_SURFACE_PORT_COUNT)), times, frame_count
            ),
            _occurrence(
                tuple(range(CARD_SURFACE_PORT_COUNT, LESSON_PORT_COUNT)),
                times,
                frame_count,
            ),
        )
    else:
        occurrences = (
            _occurrence(tuple(range(LESSON_PORT_COUNT)), times, frame_count),
        )
    return settle_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed,
        states=_sense_states(observed),
        occurrences=occurrences,
    )


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
    episodes: list[tuple[Any, list[tuple[int, int]]]] = [
        (
            _whole_roster_hop_episode(
                f"curriculum-card-{card_id}-partial-glimpse",
                times,
                _partial_presentation_levels(luminance),
                silence,
                separate_optical_occurrence=True,
            ),
            [(presentation_ms, 1000)] * 2,
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
                    separate_optical_occurrence=True,
                ),
                [(presentation_ms, 1000)] * 2,
            )
        )
    return episodes


def _card_lesson_hop_episodes(
    card_id: str,
    experience: dict[str, Any],
    presentation: str = "full",
) -> list[tuple[Any, list[tuple[int, int]]]]:
    presentation_ms = experience.get("presentation_milliseconds")
    if (
        isinstance(presentation_ms, bool)
        or not isinstance(presentation_ms, int)
        or presentation_ms <= 0
    ):
        raise ValueError("curriculum presentation window changed")
    surface_path = _verified_media_path(experience.get("surface"), "surface")
    audio_path = _verified_media_path(experience.get("tutor_audio"), "tutor_audio")
    if presentation == "partial":
        return _partial_card_lesson_hop_episodes(
            card_id,
            presentation_ms,
            _card_surface_luminance(surface_path),
        )
    tutor_audio = experience.get("tutor_audio")
    expected_samples = (
        tutor_audio.get("sample_count") if isinstance(tutor_audio, dict) else None
    )
    sample_rate, samples = _read_tutor_wav(audio_path, expected_samples)
    audio_seconds = Fraction(len(samples), sample_rate)
    presentation_seconds = Fraction(presentation_ms, 1000)
    if audio_seconds > presentation_seconds:
        raise ValueError("tutor audio exceeds the signed presentation window")

    luminance = _card_surface_luminance(surface_path)
    # One shared clock per hop: the tutor speaks while the static card
    # surface is lit, so every declared receptor site is co-observed on the
    # tutor audio's exact retained instants of that hop.
    hops = _pcm_hops(samples, sample_rate)
    if not hops:
        raise ValueError("tutor audio does not span one intake hop")
    episodes: list[tuple[Any, list[tuple[int, int]]]] = []
    for hop_index, (shared_times, audio_signal) in enumerate(hops):
        frame_count = len(shared_times)
        sight_ports = tuple(
            _card_surface_substream(
                row,
                column,
                shared_times,
                (luminance[row * CARD_SURFACE_COLUMNS + column],)
                * frame_count,
            )
            for row in range(CARD_SURFACE_ROWS)
            for column in range(CARD_SURFACE_COLUMNS)
        )
        observed = {
            PhysicalSense.SIGHT: sight_ports,
            PhysicalSense.SOUND: _ear_ports(shared_times, audio_signal),
        }
        # The card is physically lit for the WHOLE presentation, so every hop
        # of it declares the lit surface and the tutor pressure as two
        # co-clocked occurrences.  Under the ratified retinal receptor law
        # only an exact optical occurrence (every port of the occurrence a
        # retinal sight port) settles the retinal cohort's receptor physics,
        # so a hop that folded the surface into a combined sight+sound
        # occurrence delivered no light at all — the organism was told the
        # card went dark for 14 of the 15 seconds it was actually lit.  With
        # every lit hop declaring its optical occurrence, the receptor's
        # threshold-integrated accumulator integrates the light that really
        # falls on it for the whole presentation.  The ears still join the
        # grown cohort through their own co-clocked occurrence on every hop.
        occurrences = (
            _occurrence(
                tuple(range(CARD_SURFACE_PORT_COUNT)),
                shared_times,
                frame_count,
            ),
            _occurrence(
                tuple(range(CARD_SURFACE_PORT_COUNT, LESSON_PORT_COUNT)),
                shared_times,
                frame_count,
            ),
        )
        episode = settle_native_joint_source_episode(
            assembly_id=f"curriculum-card-{card_id}-hop-{hop_index}",
            observed_substreams=observed,
            states=_sense_states(observed),
            occurrences=occurrences,
        )
        # The maximum causal interval is the signed manifest's presentation
        # window: independent environment authority authored by the
        # curriculum, never derived from the occurrence.
        episodes.append((episode, [(presentation_ms, 1000)] * len(occurrences)))
    # The presentation genuinely ends: the surface is unlit and the tutor is
    # silent.  Two quiescent hops declare that real environment state so the
    # post-quiescence neuron physics can settle what was experienced.
    quiescent_times = _quiescent_hop_times()
    quiescent_signal = (0.0,) * len(quiescent_times)
    dark = (0.0,) * CARD_SURFACE_PORT_COUNT
    for ended_index in range(2):
        episode = _whole_roster_hop_episode(
            f"curriculum-card-{card_id}-ended-{ended_index}",
            quiescent_times,
            dark,
            quiescent_signal,
        )
        episodes.append((episode, [(presentation_ms, 1000)]))
    return episodes


def _mono_pcm_hop_episodes(
    *,
    assembly_prefix: str,
    samples: tuple[int, ...],
    sample_rate_hz: int,
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
    hops = _pcm_hops(samples, sample_rate_hz)
    if not hops:
        raise ValueError("mono PCM intake does not span one intake hop")
    dark = (0.0,) * CARD_SURFACE_PORT_COUNT
    episodes: list[tuple[Any, list[tuple[int, int]]]] = []
    for hop_index, (times, signal) in enumerate(hops):
        episode = _whole_roster_hop_episode(
            f"{assembly_prefix}-hop-{hop_index}",
            times,
            dark,
            signal,
            separate_optical_occurrence=True,
        )
        # The maximum causal interval is this app's declared ambient intake
        # window: transport contract authority, never derived from the
        # occurrence; one interval per declared occurrence.
        episodes.append((episode, [(AMBIENT_INTAKE_MAX_SECONDS, 1)] * 2))
    return episodes


def _parse_wav_body(body: bytes) -> tuple[int, tuple[int, ...]]:
    with wave.open(io.BytesIO(body), "rb") as stream:
        if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
            raise ValueError("sound intake requires mono pcm_s16le WAV")
        sample_rate = stream.getframerate()
        if not 1 <= sample_rate <= 48_000:
            raise ValueError("sound intake sample rate is outside 1..48000 Hz")
        frame_count = stream.getnframes()
        if frame_count > sample_rate * AMBIENT_INTAKE_MAX_SECONDS:
            raise ValueError(
                "sound intake exceeds the declared ambient intake window"
            )
        frames = stream.readframes(frame_count)
    return sample_rate, struct.unpack(f"<{frame_count}h", frames)


def _startup() -> None:
    global _restored, _admission, _boot_error
    global _public_observation_body, _public_observation_etag
    try:
        admission = derive_native_resident_resource_admission(STATE_ROOT)
        try:
            restored = restore_current_native_organism(
                STATE_ROOT,
                max_envelope_bytes=admission.max_envelope_bytes,
                max_fabric_bytes=admission.max_fabric_bytes,
                max_logical_peak_bytes=admission.max_logical_peak_bytes,
            )
        except NativeOrganismBinaryStoreError as error:
            if "CURRENT is absent" not in str(error):
                raise
            _perform_genesis(admission)
            restored = restore_current_native_organism(
                STATE_ROOT,
                max_envelope_bytes=admission.max_envelope_bytes,
                max_fabric_bytes=admission.max_fabric_bytes,
                max_logical_peak_bytes=admission.max_logical_peak_bytes,
            )
        observation = restored.organism.readiness()
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
        _boot_error = None
        _refresh_public_observation_cache()
    except BaseException as error:
        _restored = None
        _admission = None
        _public_observation_body = None
        _public_observation_etag = None
        _boot_error = f"{type(error).__name__}: {error}"
        raise


@asynccontextmanager
async def _lifespan(_application: FastAPI):
    _startup()
    yield


app = FastAPI(title="Guala native organism", version="1", lifespan=_lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready/guala", dependencies=[Depends(_require_secret)])
def ready_guala() -> dict[str, Any]:
    # Readiness reads the live organism, so it must never observe committed
    # hops whose lesson has not persisted yet: the transition lock is held
    # for a whole lesson (commit hops in-memory, persist once), and taking
    # it here means readiness serves only persisted state.
    with _transition_lock:
        return _readiness()


@app.get(
    "/api/v1/deployment/runtime-proof",
    dependencies=[Depends(_require_secret)],
)
def runtime_proof() -> dict[str, Any]:
    with _transition_lock:
        return _readiness()


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


@app.get("/api/v1/visual/capture-contract")
def visual_capture_contract() -> dict[str, Any]:
    return {
        "maximum_frames": 8,
        "minimum_frames": 4,
        "ok": True,
        "sampling_interval_ms": 250,
        "schema": "guala.visual_capture_transport.v1",
        "sensory_transition_available": False,
    }


@app.post("/api/v1/curriculum/teach-card")
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
    try:
        episodes = _card_lesson_hop_episodes(card_id, experience, presentation)
    except HTTPException:
        raise
    except (OSError, ValueError) as error:
        return _refusal(503, f"approved curriculum media refused: {error}")
    try:
        result = _perform_admitted_intake(
            episodes, f"curriculum-card:{card_id}:{presentation}"
        )
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted lesson transition refused: {error}")
    return JSONResponse(
        status_code=200,
        content={"card_id": card_id, "presentation": presentation, **result},
    )


@app.post("/sight_frame")
async def sight_frame(_request: Request) -> JSONResponse:
    return _unavailable("native visual sensory transition")


@app.post("/sound_frame")
async def sound_frame(request: Request) -> JSONResponse:
    # Ratified two-real-signal doctrine: refuse before reading the body —
    # no standalone-hearing experience may reach the organism at all.
    return _refusal(503, _SOUND_SUSPENSION_REASON)


_SOUND_SUSPENSION_REASON = (
    "standalone hearing is suspended by ratified doctrine (Joe, 2026-08-05): an experience requires at least two senses delivering real signal, and no live visual source is mounted yet; sound returns when the camera mounts, and tutor audio inside card lessons remains"
)


async def _suspended_sound_frame(request: Request) -> JSONResponse:
    try:
        body = await request.body()
    except BaseException:
        return _refusal(422, "sound intake requires a mono pcm_s16le WAV body")
    if not body:
        return _refusal(422, "sound intake requires a mono pcm_s16le WAV body")
    try:
        sample_rate, samples = _parse_wav_body(body)
        episodes = _mono_pcm_hop_episodes(
            assembly_prefix=f"sound-frame-{uuid.uuid4()}",
            samples=samples,
            sample_rate_hz=sample_rate,
        )
    except (EOFError, ValueError, wave.Error) as error:
        return _refusal(422, f"sound intake refused: {error}")
    try:
        result = _perform_admitted_intake(episodes, "sound-frame")
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted auditory transition refused: {error}")
    return JSONResponse(status_code=200, content=result)


@app.post("/api/v1/auditory/pcm/open")
def pcm_open(payload: dict[str, Any] | None = Body(default=None)) -> JSONResponse:
    return _refusal(503, _SOUND_SUSPENSION_REASON)


def _suspended_pcm_open(payload: dict[str, Any] | None = None) -> JSONResponse:
    sample_rate = 16_000
    if isinstance(payload, dict) and "sample_rate_hz" in payload:
        candidate = payload["sample_rate_hz"]
        if (
            isinstance(candidate, bool)
            or not isinstance(candidate, int)
            or not 1 <= candidate <= 48_000
        ):
            return _refusal(422, "pcm open sample_rate_hz is outside 1..48000")
        sample_rate = candidate
    session_id = str(uuid.uuid4())
    with _transition_lock:
        _pcm_sessions[session_id] = {
            "sample_rate_hz": sample_rate,
            "samples": bytearray(),
        }
    return JSONResponse(
        status_code=200,
        content={
            "accepted": True,
            "ok": True,
            "sample_rate_hz": sample_rate,
            "schema": "guala.native_pcm_session.v1",
            "session_id": session_id,
        },
    )


@app.post("/api/v1/auditory/pcm/chunk")
def pcm_chunk(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    session_id = payload.get("session_id")
    encoded = payload.get("pcm_s16le_base64")
    if not isinstance(session_id, str) or not isinstance(encoded, str):
        return _refusal(422, "pcm chunk requires session_id and pcm_s16le_base64")
    try:
        chunk = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return _refusal(422, "pcm chunk is not canonical base64")
    if len(chunk) % 2 != 0:
        return _refusal(422, "pcm chunk is not whole pcm_s16le samples")
    with _transition_lock:
        session = _pcm_sessions.get(session_id)
        if session is None:
            return _refusal(404, "pcm session is unknown or already closed")
        retained = session["samples"]
        if (len(retained) + len(chunk)) // 2 > PCM_SESSION_MAX_SAMPLES:
            return _refusal(
                422, "pcm session exceeds the declared ambient intake window"
            )
        retained.extend(chunk)
        sample_count = len(retained) // 2
    return JSONResponse(
        status_code=200,
        content={
            "accepted": True,
            "ok": True,
            "retained_sample_count": sample_count,
            "schema": "guala.native_pcm_session.v1",
            "session_id": session_id,
        },
    )


@app.post("/api/v1/auditory/pcm/close")
def pcm_close(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    return _refusal(503, _SOUND_SUSPENSION_REASON)


def _suspended_pcm_close(payload: dict[str, Any]) -> JSONResponse:
    session_id = payload.get("session_id") if isinstance(payload, dict) else None
    if not isinstance(session_id, str):
        return _refusal(422, "pcm close requires session_id")
    with _transition_lock:
        session = _pcm_sessions.pop(session_id, None)
    if session is None:
        return _refusal(404, "pcm session is unknown or already closed")
    body = bytes(session["samples"])
    if len(body) < 4:
        return _refusal(422, "pcm session closed without at least two samples")
    samples = struct.unpack(f"<{len(body) // 2}h", body)
    try:
        episodes = _mono_pcm_hop_episodes(
            assembly_prefix=f"pcm-session-{session_id}",
            samples=samples,
            sample_rate_hz=session["sample_rate_hz"],
        )
    except ValueError as error:
        return _refusal(422, f"pcm session intake refused: {error}")
    try:
        result = _perform_admitted_intake(
            episodes, f"pcm-session:{session_id}"
        )
    except HTTPException:
        raise
    except (RuntimeError, TypeError, ValueError) as error:
        return _refusal(422, f"admitted auditory transition refused: {error}")
    return JSONResponse(
        status_code=200, content={"session_id": session_id, **result}
    )


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
