"""Cross-suite lifecycle invariants for real Guala engines."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _shutdown_every_test_engine(monkeypatch):
    """No test may leak a live cognition engine into the next test.

    A real ``Guala`` owns worker threads and structural graphs that reference
    the engine. Relying on garbage collection cannot reclaim an engine whose
    own threads still reference it. Track successful constructions during one
    test and close every instance at teardown, including instances a test
    forgot to close explicitly.
    """
    from dsf_ai_service.v4.guala_physical_runtime import Guala

    constructed = []
    original_init = Guala.__init__

    def tracked_init(instance, *args, **kwargs):
        original_init(instance, *args, **kwargs)
        constructed.append(instance)

    monkeypatch.setattr(Guala, "__init__", tracked_init)
    yield

    failures = []
    for instance in reversed(constructed):
        try:
            instance.shutdown()
        except BaseException as error:
            failures.append(error)
    if failures:
        raise BaseExceptionGroup(
            "test leaked engine cleanup failed",
            failures,
        )
