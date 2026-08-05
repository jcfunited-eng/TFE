"""Isolated fail-closed ASGI boundary for clean GLEW conversation.

This module never imports or mounts the legacy application.  Startup mounts
the packaged production five-sense chemistry body through an exact runtime
HMAC key supplied by the process environment.  Conversation is unavailable
unless that mount succeeds and a typed clean engine has been injected.

The service owns transport only: POST accepts one immutable turn and returns
202, while GET polls its exact task result.  It does not perform cognition,
reinterpret a DSF field, fabricate text, or substitute a fallback response.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Protocol, runtime_checkable
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from .conversation import (
    ConversationStatus,
    ConversationTransactionResult,
)
from .model import ReceiptError, receipt_sha256, require_identifier
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryChemistryStatus,
    mount_production_story_chemistry_profile,
    production_story_chemistry_profile_payload,
)


STORY_RUNTIME_KEY_HEX_ENV = "GLEW_STORY_CHEMISTRY_RUNTIME_KEY_HEX"
STORY_RUNTIME_KEY_ID_ENV = "GLEW_STORY_CHEMISTRY_RUNTIME_KEY_ID"
CLEAN_CONVERSATION_POLL_INTERVAL_MS = 500
CLEAN_CONVERSATION_TURN_SCHEMA = "glew.clean_conversation.transport_turn.v1"

EnvironmentProvider = Callable[[], Mapping[str, str]]
ProfilePayloadProvider = Callable[[], bytes]


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def clean_conversation_turn_receipt_payload(
    *,
    task_id: str,
    text: str,
    source: str,
) -> bytes:
    if not isinstance(text, str) or not text:
        raise ReceiptError("clean conversation text must contain an experience")
    return _canonical_bytes(
        {
            "source": require_identifier(source, "clean conversation source"),
            "schema": CLEAN_CONVERSATION_TURN_SCHEMA,
            "task_id": require_identifier(task_id, "clean conversation task_id"),
            "text": text,
        }
    )


@dataclass(frozen=True, slots=True)
class CleanConversationTurn:
    task_id: str
    text: str
    source: str
    receipt_sha256: str
    receipt_payload: bytes

    def verify(self) -> None:
        expected = clean_conversation_turn_receipt_payload(
            task_id=self.task_id,
            text=self.text,
            source=self.source,
        )
        if (
            self.receipt_payload != expected
            or receipt_sha256(expected) != self.receipt_sha256
        ):
            raise ReceiptError(
                "clean conversation turn differs from its canonical receipt"
            )


@runtime_checkable
class CleanConversationEngine(Protocol):
    """Injected synchronous owner of one complete clean transaction."""

    def run_clean_conversation(
        self,
        *,
        turn: CleanConversationTurn,
        story_chemistry: StoryChemistryRuntime,
        is_final_scalar: bool = False,
        defer_persistence: bool = False,
    ) -> ConversationTransactionResult:
        """Return only the typed result of ``run_clean_conversation_transaction``.

        ``is_final_scalar`` is the real, structural end-of-message signal the
        ``MultiScalarTurnScheduler`` supplies for the last real Unicode scalar of
        a real per-request turn (``index == len(text) - 1``); it defaults to
        ``False`` so every other caller keeps the historical accumulate-only
        behaviour. Only a genuinely-final scalar that commits closes the
        accumulated expression (see ``clean_conversation_engine`` design section
        12).

        ``defer_persistence`` is the second scheduler-owned structural signal
        (utterance-transaction Milestone 1): ``True`` marks this call as one
        scalar of one real multi-scalar turn, so the engine batches its durable
        generation-store commit at that turn's final scalar (every learn still
        happens per scalar, in memory, with all receipt mechanisms unchanged;
        a turn that changes no learned state commits nothing). It defaults to
        ``False`` so every single-scalar caller keeps the historical
        commit-immediately behaviour.
        """


class CleanConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str
    source: str

    @field_validator("text")
    @classmethod
    def _text_contains_experience(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain an experience")
        return value

    @field_validator("source")
    @classmethod
    def _source_is_canonical(cls, value: str) -> str:
        try:
            return require_identifier(value, "source")
        except ReceiptError as error:
            raise ValueError(str(error)) from error


class ConversationTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass(slots=True)
class _ConversationTask:
    turn: CleanConversationTurn
    status: ConversationTaskStatus
    accepted_monotonic_ns: int
    started_monotonic_ns: int | None = None
    completed_monotonic_ns: int | None = None
    result: ConversationTransactionResult | None = None
    error_kind: str | None = None
    error_reason: str | None = None


@dataclass(frozen=True, slots=True)
class _ServiceFailure:
    kind: str
    reason: str


class CleanConversationServiceUnavailable(RuntimeError):
    """A required production authority is absent at this service boundary."""


def _runtime_authentication_key(
    environment: Mapping[str, str],
) -> tuple[bytes, str]:
    encoded = environment.get(STORY_RUNTIME_KEY_HEX_ENV)
    key_id = environment.get(STORY_RUNTIME_KEY_ID_ENV)
    if encoded is None or encoded == "":
        raise CleanConversationServiceUnavailable(
            f"required runtime secret {STORY_RUNTIME_KEY_HEX_ENV} is missing"
        )
    if (
        len(encoded) != 64
        or encoded.lower() != encoded
        or any(character not in "0123456789abcdef" for character in encoded)
    ):
        raise CleanConversationServiceUnavailable(
            f"{STORY_RUNTIME_KEY_HEX_ENV} must encode exactly 32 bytes as "
            "64 lowercase hexadecimal characters"
        )
    if key_id is None or key_id == "":
        raise CleanConversationServiceUnavailable(
            f"required runtime key id {STORY_RUNTIME_KEY_ID_ENV} is missing"
        )
    try:
        canonical_key_id = require_identifier(
            key_id,
            STORY_RUNTIME_KEY_ID_ENV,
        )
    except ReceiptError as error:
        raise CleanConversationServiceUnavailable(str(error)) from error
    return bytes.fromhex(encoded), canonical_key_id


class _CleanConversationServiceState:
    def __init__(
        self,
        *,
        engine: CleanConversationEngine | None,
        environment_provider: EnvironmentProvider,
        profile_payload_provider: ProfilePayloadProvider,
    ) -> None:
        self._injected_engine = engine
        self._environment_provider = environment_provider
        self._profile_payload_provider = profile_payload_provider
        self.chemistry: StoryChemistryRuntime | None = None
        self.engine: CleanConversationEngine | None = None
        self.failure: _ServiceFailure | None = None
        self.tasks: dict[str, _ConversationTask] = {}
        self._task_lock = asyncio.Lock()
        self._engine_lock = asyncio.Lock()
        self._workers: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        self.chemistry = None
        self.engine = None
        self.failure = None
        self.tasks = {}
        self._task_lock = asyncio.Lock()
        self._engine_lock = asyncio.Lock()
        self._workers = set()
        try:
            environment = self._environment_provider()
            if not isinstance(environment, Mapping):
                raise CleanConversationServiceUnavailable(
                    "runtime environment provider did not return a mapping"
                )
            authentication_key, key_id = _runtime_authentication_key(environment)
            profile_payload = self._profile_payload_provider()
            if not isinstance(profile_payload, bytes) or not profile_payload:
                raise CleanConversationServiceUnavailable(
                    "packaged production five-sense chemistry profile is missing"
                )
            mounted = mount_production_story_chemistry_profile(
                profile_body_payload=profile_payload,
                runtime_authentication_key=authentication_key,
                runtime_key_id=key_id,
            )
            if (
                mounted.status is not StoryChemistryStatus.MOUNTED
                or mounted.runtime is None
            ):
                raise CleanConversationServiceUnavailable(
                    "production five-sense chemistry mount failed: " + mounted.reason
                )
            self.chemistry = mounted.runtime
            engine = self._injected_engine
            if engine is None or not isinstance(engine, CleanConversationEngine):
                raise CleanConversationServiceUnavailable(
                    "typed clean conversation engine is not injected"
                )
            self.engine = engine
        except Exception as error:
            self.failure = _ServiceFailure(type(error).__name__, str(error))

    async def close(self) -> None:
        workers = tuple(self._workers)
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        self.engine = None
        self.chemistry = None

    def available(self) -> bool:
        return (
            self.failure is None
            and self.engine is not None
            and self.chemistry is not None
        )

    async def enqueue(self, request: CleanConversationRequest) -> CleanConversationTurn:
        if not self.available():
            raise CleanConversationServiceUnavailable(
                "clean conversation service is unavailable"
            )
        task_id = f"glew-conversation-{uuid4().hex}"
        payload = clean_conversation_turn_receipt_payload(
            task_id=task_id,
            text=request.text,
            source=request.source,
        )
        turn = CleanConversationTurn(
            task_id=task_id,
            text=request.text,
            source=request.source,
            receipt_sha256=receipt_sha256(payload),
            receipt_payload=payload,
        )
        turn.verify()
        async with self._task_lock:
            if task_id in self.tasks:
                raise ReceiptError("clean conversation task identity collided")
            self.tasks[task_id] = _ConversationTask(
                turn=turn,
                status=ConversationTaskStatus.QUEUED,
                accepted_monotonic_ns=time.monotonic_ns(),
            )
        worker = asyncio.create_task(
            self._execute(task_id),
            name=f"clean-conversation-{task_id}",
        )
        self._workers.add(worker)
        worker.add_done_callback(self._workers.discard)
        return turn

    async def _execute(self, task_id: str) -> None:
        async with self._engine_lock:
            async with self._task_lock:
                task = self.tasks[task_id]
                task.status = ConversationTaskStatus.RUNNING
                task.started_monotonic_ns = time.monotonic_ns()
            try:
                engine = self.engine
                chemistry = self.chemistry
                if engine is None or chemistry is None:
                    raise CleanConversationServiceUnavailable(
                        "clean conversation authorities disappeared after admission"
                    )
                result = await asyncio.to_thread(
                    engine.run_clean_conversation,
                    turn=task.turn,
                    story_chemistry=chemistry,
                )
                if not isinstance(result, ConversationTransactionResult):
                    raise ReceiptError(
                        "clean conversation engine returned an untyped result"
                    )
                result.verify()
                async with self._task_lock:
                    task.result = result
                    task.status = ConversationTaskStatus.COMPLETE
                    task.completed_monotonic_ns = time.monotonic_ns()
            except Exception as error:
                async with self._task_lock:
                    task.error_kind = type(error).__name__
                    task.error_reason = str(error)
                    task.status = ConversationTaskStatus.ERROR
                    task.completed_monotonic_ns = time.monotonic_ns()

    async def task(self, task_id: str) -> _ConversationTask | None:
        async with self._task_lock:
            return self.tasks.get(task_id)


def _unavailable_response(state: _CleanConversationServiceState) -> JSONResponse:
    failure = state.failure or _ServiceFailure(
        "CleanConversationServiceUnavailable",
        "clean conversation authorities are unavailable",
    )
    return JSONResponse(
        status_code=503,
        content={
            "status": "unavailable",
            "error": {"kind": failure.kind, "reason": failure.reason},
            "production_five_sense_chemistry_mounted": state.chemistry is not None,
            "typed_clean_conversation_engine_mounted": state.engine is not None,
        },
    )


def _elapsed_ms(task: _ConversationTask) -> int:
    end = task.completed_monotonic_ns or time.monotonic_ns()
    return max(0, end - task.accepted_monotonic_ns) // 1_000_000


def create_clean_conversation_application(
    *,
    engine: CleanConversationEngine | None = None,
    environment_provider: EnvironmentProvider | None = None,
    profile_payload_provider: ProfilePayloadProvider | None = None,
) -> FastAPI:
    """Create an isolated service; missing authorities remain explicit 503."""

    selected_environment_provider = (
        (lambda: os.environ)
        if environment_provider is None
        else environment_provider
    )
    selected_profile_provider = (
        production_story_chemistry_profile_payload
        if profile_payload_provider is None
        else profile_payload_provider
    )
    if not callable(selected_environment_provider):
        raise TypeError("environment_provider must be callable")
    if not callable(selected_profile_provider):
        raise TypeError("profile_payload_provider must be callable")

    state = _CleanConversationServiceState(
        engine=engine,
        environment_provider=selected_environment_provider,
        profile_payload_provider=selected_profile_provider,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        await state.start()
        application.state.clean_conversation = state
        try:
            yield
        finally:
            await state.close()

    application = FastAPI(
        title="Clean GLEW Conversation",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @application.post("/api/v1/gualaloom", response_model=None)
    async def start_clean_conversation(request: CleanConversationRequest):
        if not state.available():
            return _unavailable_response(state)
        try:
            turn = await state.enqueue(request)
        except (CleanConversationServiceUnavailable, ReceiptError) as error:
            state.failure = _ServiceFailure(type(error).__name__, str(error))
            return _unavailable_response(state)
        chemistry = state.chemistry
        if chemistry is None:
            state.failure = _ServiceFailure(
                "CleanConversationServiceUnavailable",
                "production five-sense chemistry disappeared after admission",
            )
            return _unavailable_response(state)
        return JSONResponse(
            status_code=202,
            content={
                "task_id": turn.task_id,
                "status": "accepted",
                "poll_url": f"/api/v1/gualaloom/task/{turn.task_id}",
                "retry_after_ms": CLEAN_CONVERSATION_POLL_INTERVAL_MS,
                "turn_receipt_sha256": turn.receipt_sha256,
                "story_chemistry_profile_receipt_sha256": (
                    chemistry.manifest.receipt_sha256
                ),
            },
        )

    @application.get("/api/v1/gualaloom/task/{task_id}", response_model=None)
    async def poll_clean_conversation(task_id: str):
        if not state.available():
            return _unavailable_response(state)
        task = await state.task(task_id)
        if task is None:
            return JSONResponse(
                status_code=404,
                content={
                    "task_id": task_id,
                    "status": "not_found",
                    "error": (
                        "task not found on this clean service instance; it may "
                        "belong to a prior restarted instance"
                    ),
                },
            )
        if task.status is ConversationTaskStatus.ERROR:
            return JSONResponse(
                status_code=200,
                content={
                    "task_id": task_id,
                    "status": "error",
                    "error": task.error_reason,
                    "error_kind": task.error_kind,
                    "elapsed_ms": _elapsed_ms(task),
                },
            )
        if task.status is ConversationTaskStatus.COMPLETE:
            result = task.result
            if result is None:
                return JSONResponse(
                    status_code=200,
                    content={
                        "task_id": task_id,
                        "status": "error",
                        "error": "completed task lacks a typed conversation result",
                        "error_kind": "ReceiptError",
                        "elapsed_ms": _elapsed_ms(task),
                    },
                )
            released = result.status is ConversationStatus.EXPRESSION_RELEASED
            motif_count = (
                0
                if result.initial_event_receipt_sha256 is None
                else 1 + len(result.transition_settlement_receipt_sha256s)
            )
            return JSONResponse(
                status_code=200,
                content={
                    "task_id": task_id,
                    "status": "complete",
                    "response": result.visible_text,
                    "response_source": result.status.value,
                    "motifs": motif_count,
                    "emission_id": result.receipt_sha256 if released else None,
                    "conversation_receipt_sha256": result.receipt_sha256,
                    "conversation_reason": result.reason,
                    "elapsed_ms": _elapsed_ms(task),
                },
            )
        return JSONResponse(
            status_code=200,
            content={
                "task_id": task_id,
                "status": task.status.value,
                "elapsed_ms": _elapsed_ms(task),
                "retry_after_ms": CLEAN_CONVERSATION_POLL_INTERVAL_MS,
            },
        )

    return application


app = create_clean_conversation_application()


__all__ = (
    "CLEAN_CONVERSATION_POLL_INTERVAL_MS",
    "CLEAN_CONVERSATION_TURN_SCHEMA",
    "CleanConversationEngine",
    "CleanConversationRequest",
    "CleanConversationServiceUnavailable",
    "CleanConversationTurn",
    "ConversationTaskStatus",
    "STORY_RUNTIME_KEY_HEX_ENV",
    "STORY_RUNTIME_KEY_ID_ENV",
    "app",
    "clean_conversation_turn_receipt_payload",
    "create_clean_conversation_application",
)
