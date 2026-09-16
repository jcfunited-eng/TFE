"""Bounded production transport for one lean resident Guala organism."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import FunctionalOrganism, MAGIC as FUNCTIONAL_MAGIC
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_vision_fovea import resample_focal_crop_rgb
from dsf_ai_service.lean_actor import LeanOrganismActor, PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore


# One full current-body custody has measured as high as 6.8 seconds on the
# production EFS. Thirty-two 250 ms physical intervals provide one eight-second
# lived custody span, so the sole worker can finish before another snapshot is
# due; the actor's existing two-span ceiling still bounds undurable life to
# sixteen seconds instead of blocking perception behind continuous encoding.
CHECKPOINT_EVERY_INTERVALS = 32
UNATTENDED_INTERVAL_SECONDS = 0.25
MAILBOX_CAPACITY = 1
# Occurrence envelope (vision upgrade, 2026-09-13; drive organ, 2026-09-13).
# The HTTP contract is JSON, not raw bytes: the worst admissible body is now
# guided-body-microphone carrying the 2,709-value retina (all 255) + 8,000 B
# PCM as base64 + 8 caregiver drives at maximum ints = 22,296 B compact /
# 33,371 B with indent=1 JSON spacing (guided-vocal-microphone: 22,712 /
# 25,507; card/camera-microphone: 21,603 / 24,319). Cap sized to the spaced
# worst case plus margin; anything larger is still refused.
MAX_OCCURRENCE_BODY_BYTES = 131_072   # a camera frame of 4,935 sites in red, green and blue as plain JSON is about 55 KB
PUBLIC_API_PREFIX = "/api/v1/guala"
OBSERVATION_ROUTE = f"{PUBLIC_API_PREFIX}/observation"
OBSERVATION_LONGPOLL_SECONDS = 20.0  # bounded hold for ?after=<tick>; declared, not tuned
OBSERVATION_WAITERS = 8  # bounded concurrent held observers; beyond it, immediate current projection
OCCURRENCE_ROUTE = f"{PUBLIC_API_PREFIX}/occurrence"
PRESSURE_FEED_ROUTE = f"{PUBLIC_API_PREFIX}/pressure"
PRESSURE_ROUTE = f"{PUBLIC_API_PREFIX}/pressure/{{receipt}}"


class GuidedVocalDriveBody(BaseModel):
    """One bounded external physical drive on a native body axis."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    axis_ordinal: int = Field(ge=0, le=44)
    direction_ordinal: Literal[0, 1]
    outward_elementary_carriers: int = Field(ge=1, le=(1 << 32) - 1)


class SensoryBody(BaseModel):
    """Bounded browser-side physical light and pressure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal[
        "camera",
        "camera-microphone",
        "card-microphone",
        "caretaker-food",
        "guided-body-microphone",
        "guided-vocal-microphone",
        "media",
        "microphone",
        "text-light",
        "text-microphone",
        "thing-sound",
    ]
    retina_rgb_u8: tuple[int, ...] | None = None
    pcm_s16le_base64: str | None = None
    guided_vocal_drives: tuple[GuidedVocalDriveBody, ...] | None = None
    present_food: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    # Sound from a thing in her world (source "thing-sound"): the thing it comes
    # from, so her ears hear it by the room's geometry.
    from_object: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    focal_origin: tuple[float, float] | None = None
    focal_pitch_millidegrees: tuple[int, int] | None = None
    focal_rgb_base64: str | None = None
    focal_crop_dimensions: tuple[int, int] | None = None


class OccurrenceBody(BaseModel):
    """One unattended interval or one bounded physical sensory occurrence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["sensory", "unattended"]
    payload: SensoryBody | None = None

    @model_validator(mode="after")
    def exact_payload_cardinality(self) -> "OccurrenceBody":
        if (self.kind == "unattended") != (self.payload is None):
            raise ValueError("occurrence kind and payload disagree")
        return self


def _positive_environment_integer(name: str) -> int:
    raw = os.environ.get(name)
    if raw is None:
        raise RuntimeError(f"{name} is required")
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError(f"{name} is not an integer") from error
    if value <= 0:
        raise RuntimeError(f"{name} is not positive")
    return value


async def _occurrence_body(request: Request) -> OccurrenceBody:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_OCCURRENCE_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"occurrence body exceeds {MAX_OCCURRENCE_BODY_BYTES} bytes",
            )
        body.extend(chunk)
    try:
        return OccurrenceBody.model_validate_json(bytes(body))
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=error.errors(include_input=False, include_url=False),
        ) from error


def _restore_production_actor() -> LeanOrganismActor:
    root_text = os.environ.get("GUALA_PAIRED_ROOT")
    if not root_text:
        raise RuntimeError("GUALA_PAIRED_ROOT is required")
    root = Path(root_text)

    from dsf_ai_service.substrate.native_resident_resource_admission import (
        derive_native_resident_resource_admission,
    )

    admission = derive_native_resident_resource_admission(root)
    store = PairedCurrentStore(
        root,
        max_body_bytes=admission.max_envelope_bytes,
        max_world_bytes=_positive_environment_integer(
            "GUALA_MAX_WORLD_BYTES"
        ),
    )
    restored = store.restore()
    current = restored.pointer.current
    # The functional organism (Joe, 2026-09-14). A CURRENT body that is still a
    # native neuron envelope is succeeded here, once, by a functional body at
    # the same identity and tick; the native envelope stays as the retained
    # predecessor generation and is never read for cognition again.
    converted = not restored.body.startswith(FUNCTIONAL_MAGIC)
    runtime = (
        FunctionalOrganism.genesis(identity=current.identity, organism_tick=current.organism_tick)
        if converted else FunctionalOrganism.restore(restored.body)
    )
    if runtime.identity != current.identity or runtime.live_organism_tick != current.organism_tick:
        raise RuntimeError("restored organism identity/tick differs from paired CURRENT")
    current_body = runtime.encoded()
    world = home_world_authority(
        identity=current.identity,
        encoded_world=restored.world,
        migrate_physical_return=True,
    )
    current_world = bytes(world.encoded_snapshot())
    # One startup-only receipt of the validated bytes actually read. It precedes
    # any migration publication and never participates in cognition or identity.
    print(json.dumps({
        "schema": "guala.paired_predecessor.v1",
        "identity": current.identity,
        "organism_tick": current.organism_tick,
        "body_sha256": current.body_sha256,
        "body_bytes": current.body_bytes,
        "world_sha256": current.world_sha256,
        "world_bytes": current.world_bytes,
        "functional_conversion": converted,
    }, sort_keys=True, separators=(",", ":")), flush=True)
    pointer = restored.pointer
    if current_body != restored.body or current_world != restored.world:
        pointer = store.publish(
            identity=current.identity,
            organism_tick=current.organism_tick,
            body=current_body,
            world=current_world,
            expected_current_body_sha256=current.body_sha256,
        )
    store.reconcile(pointer)
    return LeanOrganismActor(
        runtime=runtime,
        world=world,
        pointer=pointer,
        store=store,
        physical=FunctionalPhysicalLoop(),
        mailbox_capacity=MAILBOX_CAPACITY,
        checkpoint_every_intervals=CHECKPOINT_EVERY_INTERVALS,
        unattended_interval_seconds=UNATTENDED_INTERVAL_SECONDS,
    )


def _physical_occurrence(body: OccurrenceBody) -> PhysicalOccurrence:
    if body.kind == "unattended":
        return PhysicalOccurrence("unattended", None)
    payload = body.payload
    if payload is None:
        raise ValueError("sensory occurrence has no payload")
    pressure = None
    if payload.pcm_s16le_base64 is not None:
        try:
            pressure = base64.b64decode(
                payload.pcm_s16le_base64,
                validate=True,
            )
        except (binascii.Error, ValueError) as error:
            raise ValueError("sensory pressure is not canonical base64") from error
    retina_u8 = payload.retina_rgb_u8
    crop_dims = payload.focal_crop_dimensions
    if payload.focal_rgb_base64 is not None:
        try:
            raw_focal = base64.b64decode(
                payload.focal_rgb_base64,
                validate=True,
            )
        except (binascii.Error, ValueError) as error:
            raise ValueError("focal rgb is not canonical base64") from error
        if crop_dims is None:
            if len(raw_focal) == 80 * 60 * 3:
                crop_dims = (80, 60)
            elif len(raw_focal) == 64 * 48 * 3:
                crop_dims = (64, 48)
            elif len(raw_focal) == 32 * 24 * 3:
                crop_dims = (32, 24)
            else:
                raise ValueError("focal rgb bytes does not match standard crop dimensions")
        resampled_focal = resample_focal_crop_rgb(raw_focal, crop_dims[0], crop_dims[1])
        if retina_u8 is not None and len(retina_u8) >= 405:
            retina_u8 = tuple(retina_u8[:405]) + resampled_focal
        else:
            retina_u8 = (0,) * 405 + resampled_focal
    return PhysicalOccurrence(
        "sensory",
        LeanSensoryOccurrence(
            source=payload.source,
            retina_rgb_u8=retina_u8,
            pressure_s16le=pressure,
            guided_vocal_drives=(
                None
                if payload.guided_vocal_drives is None
                else tuple(
                    (
                        drive.axis_ordinal,
                        drive.direction_ordinal,
                        drive.outward_elementary_carriers,
                    )
                    for drive in payload.guided_vocal_drives
                )
            ),
            present_food=payload.present_food,
            from_object=payload.from_object,
            focal_origin=payload.focal_origin,
            focal_pitch_millidegrees=payload.focal_pitch_millidegrees,
            focal_crop_dimensions=crop_dims,
        ),
    )


def create_lean_production_app(
    actor_factory: Callable[[], LeanOrganismActor] | None = None,
) -> FastAPI:
    """Create the bounded surface without starting a second owner."""

    factory = _restore_production_actor if actor_factory is None else actor_factory

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        actor = factory()
        actor.start()
        application.state.guala_actor = actor
        application.state.observation_waiters = asyncio.Semaphore(OBSERVATION_WAITERS)
        try:
            yield
        finally:
            actor.close()

    application = FastAPI(
        title="Guala lean transport",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    def actor_for(request: Request) -> LeanOrganismActor:
        actor = getattr(request.app.state, "guala_actor", None)
        if not isinstance(actor, LeanOrganismActor):
            raise HTTPException(status_code=503, detail="organism is unavailable")
        return actor

    @application.get("/health")
    async def health(request: Request) -> Response:
        alive = bool(actor_for(request).observation()["available"])
        return Response(
            content=(
                b'{"alive":true,"schema":"guala.lean_health.v1"}'
                if alive
                else b'{"alive":false,"schema":"guala.lean_health.v1"}'
            ),
            status_code=200 if alive else 503,
            media_type="application/json",
        )

    @application.get("/ready")
    async def ready(request: Request) -> Response:
        observation = actor_for(request).observation()
        ready_now = bool(
            observation["available"]
            and not observation["durability_blocked"]
            and observation["checkpoint_error"] is None
            and observation["cleanup_error"] is None
        )
        return Response(
            content=(b'{"ready":true}' if ready_now else b'{"ready":false}'),
            status_code=200 if ready_now else 503,
            media_type="application/json",
        )

    @application.get(OBSERVATION_ROUTE)
    async def observation(
        request: Request,
        after: int | None = Query(default=None, ge=0),
    ) -> dict[str, object]:
        # Observer delivery (vision release, 2026-09-13): the same cached
        # projection, either immediately (no ``after``) or as a bounded
        # long-poll held until live_tick exceeds ``after`` or the bound
        # expires. It waits on the actor's own publication signal in a worker
        # thread — no polling, no runtime or world reads, no history, no
        # second clock. A disconnected client leaves nothing behind: the
        # waiter releases at the bound and the response is discarded.
        actor = actor_for(request)
        if after is None:
            return actor.observation()
        # Bounded observer admission: at most OBSERVATION_WAITERS held waits
        # at once; a caller past the bound receives the current projection
        # immediately (same shape, no wait) instead of queued worker backlog.
        # The permit is released when the wait ends — on delivery, at the
        # bound, or after a disconnected caller's wait expires — never leaked.
        waiters = request.app.state.observation_waiters
        if waiters.locked():
            return actor.observation()
        # The permit is held until the WORKER finishes, not until the awaiting
        # coroutine ends: a cancelled or disconnected caller does not free a
        # permit while its worker still runs, so at most OBSERVATION_WAITERS
        # real workers ever exist. Released exactly once by the done-callback,
        # or directly if submission itself fails before a future exists.
        await waiters.acquire()
        try:
            future = asyncio.get_running_loop().run_in_executor(
                None, actor.observation_after, after, OBSERVATION_LONGPOLL_SECONDS
            )
        except Exception:
            waiters.release()
            raise
        future.add_done_callback(lambda _done: waiters.release())
        return await asyncio.shield(future)

    @application.post(OCCURRENCE_ROUTE)
    async def occurrence(request: Request) -> dict[str, object]:
        body = await _occurrence_body(request)
        actor = actor_for(request)
        try:
            physical_occurrence = _physical_occurrence(body)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            offered = actor.offer(physical_occurrence)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        try:
            result = await asyncio.wrap_future(offered)
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {
            "native_interval_count": result.native_interval_count,
            "observation": actor.observation(),
            "pressure_sha256": (
                None if result.pressure is None else result.pressure[0]
            ),
            "schema": "guala.lean_occurrence_result.v1",
        }

    @application.get(PRESSURE_FEED_ROUTE)
    async def pressure_feed(
        request: Request,
        stream: str | None = Query(default=None, max_length=32, pattern=r"^[0-9a-f]{32}$"),
        after: int | None = Query(default=None, ge=0, lt=(1 << 64)),
    ) -> Response:
        try:
            record = actor_for(request).pressure_feed(stream, after)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return JSONResponse(record, headers={"Cache-Control": "no-store"})

    @application.get(PRESSURE_ROUTE)
    async def pressure(receipt: str, request: Request) -> Response:
        body = actor_for(request).pressure(receipt)
        if body is None:
            raise HTTPException(status_code=404, detail="pressure receipt not held")
        return Response(
            content=body,
            media_type="application/octet-stream",
            headers={
                "ETag": f'"{receipt}"',
                "X-Guala-PCM-Channels": "1",
                "X-Guala-PCM-Encoding": "signed-16-little-endian",
                "X-Guala-PCM-Sample-Rate-Hz": "16000",
            },
        )

    return application


app = create_lean_production_app()


__all__ = (
    "OBSERVATION_ROUTE",
    "OCCURRENCE_ROUTE",
    "PRESSURE_ROUTE",
    "PRESSURE_FEED_ROUTE",
    "app",
    "create_lean_production_app",
)
