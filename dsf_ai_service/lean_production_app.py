"""Five-route production transport for one lean resident Guala organism."""

from __future__ import annotations

import asyncio
import base64
import binascii
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import LeanOrganismActor, PhysicalOccurrence
from dsf_ai_service.lean_physical_loop import LeanPhysicalLoop
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.paired_current_store import PairedCurrentStore


CHECKPOINT_EVERY_INTERVALS = 4
UNATTENDED_INTERVAL_SECONDS = 0.25
MAILBOX_CAPACITY = 1
MAX_OCCURRENCE_BODY_BYTES = 12_288
PUBLIC_API_PREFIX = "/api/v1/guala"
OBSERVATION_ROUTE = f"{PUBLIC_API_PREFIX}/observation"
OCCURRENCE_ROUTE = f"{PUBLIC_API_PREFIX}/occurrence"
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
        "guided-vocal-microphone",
        "media",
        "microphone",
        "text-light",
        "text-microphone",
    ]
    retina_u8: tuple[int, ...] | None = None
    pcm_s16le_base64: str | None = None
    guided_vocal_drives: tuple[GuidedVocalDriveBody, ...] | None = None


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
                detail="occurrence body exceeds 12288 bytes",
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

    from dsf_ai_service.glew_runtime.native_resident_organism import (
        restore_native_resident_organism,
    )
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
    store.reconcile(restored.pointer)
    runtime = restore_native_resident_organism(
        current_envelope=restored.body,
        max_envelope_bytes=admission.max_envelope_bytes,
        max_fabric_bytes=admission.max_fabric_bytes,
        max_logical_peak_bytes=admission.max_logical_peak_bytes,
    )
    world = home_world_authority(
        identity=restored.pointer.current.identity,
        encoded_world=restored.world,
    )
    return LeanOrganismActor(
        runtime=runtime,
        world=world,
        pointer=restored.pointer,
        store=store,
        physical=LeanPhysicalLoop(),
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
    return PhysicalOccurrence(
        "sensory",
        LeanSensoryOccurrence(
            source=payload.source,
            retina_u8=payload.retina_u8,
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
        ),
    )


def create_lean_production_app(
    actor_factory: Callable[[], LeanOrganismActor] | None = None,
) -> FastAPI:
    """Create the exact five-route surface without starting a second owner."""

    factory = _restore_production_actor if actor_factory is None else actor_factory

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        actor = factory()
        actor.start()
        application.state.guala_actor = actor
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
    async def observation(request: Request) -> dict[str, object]:
        return actor_for(request).observation()

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
    "app",
    "create_lean_production_app",
)
