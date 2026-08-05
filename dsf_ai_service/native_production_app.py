"""HTTP and observation transport for one native resident Guala organism.

The process restores only the raw binary ``CURRENT`` authority. It never
imports the retired Python Guala engine, generation stores, owner registries,
or cognition databases. HTTP, observation projection, and static media remain
outside cognition.

Public observation is one cached, read-only projection per committed native
generation. Repeated reads do not call or advance the organism. A future
native transition must refresh this cache only after committing its successor.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dsf_ai_service.substrate.native_organism_binary_store import (
    RestoredNativeOrganism,
    restore_current_native_organism,
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

_restored: RestoredNativeOrganism | None = None
_admission: NativeResidentResourceAdmission | None = None
_boot_error: str | None = None
_public_observation_body: bytes | None = None
_public_observation_etag: str | None = None


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
            "external_media_ready_neuron_ingress_unavailable",
            "36 card/audio pairs and three songs are present; no native lesson transition is mounted",
            approved_card_experience_count=36,
            approved_song_experience_count=3,
            internal_identity_authority=False,
            internal_meaning_authority=False,
            manifest_path="/curriculum/card_experience_manifest-v1.json",
            tutoring_transition_available=False,
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
        "visual": _unmounted("native visual receptor transition is not mounted"),
        "auditory": _unmounted("native binaural auditory transition is not mounted"),
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
        False,
        "no_native_receptor_transition",
        "no current sensory occurrence reaches the definitive native neuron",
        **modalities,
    )


def _build_public_observation() -> dict[str, Any]:
    native = _native_record()
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
            "native_current_transport_only",
            "native state is restored; definitive cognition and action are not mounted",
            physical_transition_claimed=native["physical_transition_claimed"],
            state_bytes=native["state_bytes"],
            tick=native["organism_tick"],
        ),
        "capabilities": {
            "camera": _capability("native visual sensory transition is not mounted"),
            "microphone": _capability("native binaural auditory transition is not mounted"),
            "curriculum": _capability("native lesson transition is not mounted"),
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
            False,
            "complete_neuron_not_mounted",
            "restored state has historical DSF perspectives, not definitive complete-neuron transitions",
            active_count=None,
            historical_reached_dsf_perspective_count=native[
                "reached_dsf_perspective_count"
            ],
            retained_count=None,
        ),
        "fractals": _section(
            False,
            "genuine_post_quiescence_fractal_not_mounted",
            "no definitive complete-neuron retained delta is mounted",
            count=0,
        ),
        "formations": _section(
            False,
            "not_implemented",
            "no lawful mosaic or higher formation is mounted",
            mosaic_count=0,
            mosaic_of_mosaics_count=0,
            tapestry_count=0,
            tapestry_of_tapestries_count=0,
            weave_count=0,
        ),
        "recall": _section(
            False,
            "not_implemented",
            "no hippocampal or distributed physical reassembly is mounted",
            partial_cue_reassembly_count=0,
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
        "full_dsf": _section(
            False,
            "not_observed",
            "no canonical reached UF v1.4 joint occurrence is mounted",
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
            "one raw native CURRENT generation was restored without fallback",
            boundary={
                "encoding": "raw_glorun01",
                "ordinary_restore": "CURRENT_only",
                "predecessor_fallback": False,
                "schema": PERSISTENCE_SCHEMA,
            },
            current_ref=native["state_sha256"],
            restart_continuity="not yet candidate-rehearsed for this worktree",
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
    return {
        "app_schema": APP_SCHEMA,
        "organism_tick": native["organism_tick"],
        "identity": native["identity"],
        "native_resident": {
            "available": True,
            **native,
            "complete_neuron_available": False,
            "genuine_neuronal_fractal_available": False,
            "cognition_available": False,
            "persistence": {
                "encoding": "raw_glorun01",
                "ordinary_restore": "CURRENT_only",
                "predecessor_fallback": False,
            },
            "persistence_schema": PERSISTENCE_SCHEMA,
        },
        "native_state": True,
        "ready": True,
        "ready_scope": "http_and_native_current_transport_only",
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


def _startup() -> None:
    global _restored, _admission, _boot_error
    global _public_observation_body, _public_observation_etag
    try:
        admission = derive_native_resident_resource_admission(STATE_ROOT)
        restored = restore_current_native_organism(
            STATE_ROOT,
            max_envelope_bytes=admission.max_envelope_bytes,
            max_fabric_bytes=admission.max_fabric_bytes,
            max_logical_peak_bytes=admission.max_logical_peak_bytes,
        )
        observation = restored.organism.readiness()
        if observation.python_callback_count != 0:
            raise RuntimeError("native organism reports a Python cognition callback")
        retired_counts = (
            observation.cognitive_mosaic_count,
            observation.cognitive_trace_count,
            observation.formation_activation_count,
            observation.partial_cue_reassembly_count,
        )
        if any(retired_counts):
            raise RuntimeError("native state contains retired cognitive counters")
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
    return _readiness()


@app.get(
    "/api/v1/deployment/runtime-proof",
    dependencies=[Depends(_require_secret)],
)
def runtime_proof() -> dict[str, Any]:
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


@app.post("/sight_frame")
async def sight_frame(_request: Request) -> JSONResponse:
    return _unavailable("native visual sensory transition")


@app.post("/sound_frame")
async def sound_frame(_request: Request) -> JSONResponse:
    return _unavailable("native auditory sensory transition")


@app.post("/api/v1/auditory/pcm/open")
def pcm_open() -> JSONResponse:
    return _unavailable("native auditory PCM stream")


@app.post("/api/v1/auditory/pcm/close")
def pcm_close() -> JSONResponse:
    return _unavailable("native auditory PCM stream")


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

