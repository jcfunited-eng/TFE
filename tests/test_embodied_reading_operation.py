from __future__ import annotations

import hashlib

import pytest

from dsf_ai_service.embodied_reading_operation import (
    EMBODIED_READING_OPERATION_STATUS_SCHEMA,
    EmbodiedReadingOperationCapacityError,
    EmbodiedReadingOperationRegistry,
    EmbodiedReadingOperationUnavailableError,
    EmbodiedReadingOperationUnknownError,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class _Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        return self.value


def test_registry_is_bounded_expires_and_never_holds_lesson_material() -> None:
    clock = _Clock()
    tokens = iter(("1" * 64, "2" * 64))
    registry = EmbodiedReadingOperationRegistry(
        max_operations=1,
        max_tombstones=1,
        ttl_seconds=5,
        monotonic_now=clock,
        token_factory=lambda: next(tokens),
    )
    first = registry.create(_sha("physical-request"))
    with pytest.raises(EmbodiedReadingOperationCapacityError):
        registry.create(_sha("second-request"))

    operation = registry._operations[first]
    assert set(operation.__dict__) == {
        "expires_monotonic",
        "failure_code",
        "request_sha256",
        "result_json",
        "state",
    }
    assert "wav" not in repr(operation).lower()
    assert "geometry" not in repr(operation).lower()

    clock.value = 20.0
    assert registry.mark_running(first) is False
    with pytest.raises(EmbodiedReadingOperationUnavailableError):
        registry.poll(first)
    assert registry.create(_sha("second-request")) == "2" * 64

    restarted = EmbodiedReadingOperationRegistry()
    with pytest.raises(EmbodiedReadingOperationUnknownError):
        restarted.poll("2" * 64)


def test_running_operation_owns_slot_until_bounded_result_is_consumed() -> None:
    clock = _Clock()
    registry = EmbodiedReadingOperationRegistry(
        max_operations=1,
        max_tombstones=1,
        ttl_seconds=5,
        monotonic_now=clock,
        token_factory=lambda: "3" * 64,
    )
    operation_id = registry.create(_sha("slow-reading-request"))
    assert registry.mark_running(operation_id) is True

    clock.value = 100.0
    status_code, running = registry.poll(operation_id)
    assert status_code == 202
    assert running["state"] == "running"
    assert running["schema"] == EMBODIED_READING_OPERATION_STATUS_SCHEMA
    with pytest.raises(EmbodiedReadingOperationCapacityError):
        registry.create(_sha("cannot-overtake-running-work"))

    receipt = {
        "retained_pcm_bytes": 0,
        "schema": "receipt-only",
    }
    assert registry.complete(operation_id, receipt) is True
    status_code, completed = registry.poll(operation_id)
    assert status_code == 200
    assert completed["state"] == "completed"
    assert completed["result"] == receipt
    with pytest.raises(EmbodiedReadingOperationUnavailableError):
        registry.poll(operation_id)


@pytest.mark.parametrize(
    ("result", "failure_code"),
    (
        ({"too_large": "value"}, "response_bound_exceeded"),
        ({"not_json": b"\x00\x01"}, "result_not_json"),
    ),
)
def test_registry_fails_closed_on_nontransport_or_oversize_result(
    result: dict[str, object],
    failure_code: str,
) -> None:
    registry = EmbodiedReadingOperationRegistry(
        max_result_bytes=2,
        token_factory=lambda: "4" * 64,
    )
    operation_id = registry.create(_sha("bounded-result"))
    registry.mark_running(operation_id)
    registry.complete(operation_id, result)

    status_code, failure = registry.poll(operation_id)
    assert status_code == 409
    assert failure["state"] == "failed"
    assert failure["failure_code"] == failure_code


def test_invalid_or_unknown_operation_ids_are_not_interpreted() -> None:
    registry = EmbodiedReadingOperationRegistry()
    for operation_id in ("word", "G" * 64, "0" * 63):
        with pytest.raises(EmbodiedReadingOperationUnknownError):
            registry.poll(operation_id)
