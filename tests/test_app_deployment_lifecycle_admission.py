"""Executable lifecycle contracts for the production FastAPI surface.

These tests are intentionally stricter than the current application.  They
name the admission guarantees required before the deploy program may trust a
SEALED response.  No production route is modified or called over the network.
"""

import asyncio
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod
from dsf_ai_service.substrate import v7_engine


class _BlockingGuala:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.is_asleep = False
        self.tick = 41
        self.vocab = {"known"}
        self._pictures = {}

    def converse(self, text, source):
        self.started.set()
        if not self.release.wait(3.0):
            raise RuntimeError("test conversation was not released")
        return SimpleNamespace(
            response="complete",
            response_source="v5_commit",
            emission_id="emission-1",
            committed_sections=("intro",),
            source_turn_index=1,
            recalled_pictures=(),
        )

    def log_event(self, *_args, **_kwargs):
        return None


class _SleepProbe:
    def __init__(self):
        self.calls = 0
        self.tick = 73
        self.vocab = {"known"}

    def manual_sleep(self, state_dir):
        self.calls += 1


@pytest.fixture
def isolated_app(monkeypatch):
    lifecycle = appmod._DeploymentLifecycle()
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_converse_tasks", {})
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    return lifecycle


def _run(coro):
    return asyncio.run(coro)


def test_background_converse_keeps_mutation_ownership_until_terminal_state(
        isolated_app, monkeypatch):
    """A 202 response must not release ownership of its executor mutation."""
    guala = _BlockingGuala()
    monkeypatch.setattr(appmod, "_guala", guala)

    async def scenario():
        transport = httpx.ASGITransport(app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/gualaloom",
                json={"text": "please answer", "source": "joe"},
            )
            assert response.status_code == 202
            task_id = response.json()["task_id"]
            assert await asyncio.to_thread(guala.started.wait, 2.0)
            try:
                snapshot = isolated_app.snapshot()
                assert snapshot["state"] == "RUNNING"
                assert snapshot["active_mutations"] == 1, (
                    "the HTTP request returned 202 and released lifecycle ownership "
                    "while its conversation executor was still mutating")
            finally:
                guala.release.set()

            deadline = time.monotonic() + 2.0
            while appmod._converse_tasks[task_id]["status"] not in {"complete", "error"}:
                assert time.monotonic() < deadline
                await asyncio.sleep(0.01)
            assert isolated_app.snapshot()["active_mutations"] == 0

    _run(scenario())


def test_get_v7_state_never_creates_or_registers_a_session(
        isolated_app, monkeypatch):
    """GET may read an existing session, but absence must remain absence."""
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace(vocab={"known"}))
    sessions = {}
    monkeypatch.setattr(v7_engine, "_sessions", sessions)
    calls = []

    class _Session:
        def get_state(self, engine=None):
            return {"session_id": "read-must-not-create"}

    def creating_lookup(session_id, engine=None):
        calls.append(session_id)
        sessions[session_id] = _Session()
        return sessions[session_id]

    monkeypatch.setattr(v7_engine, "get_or_create_session", creating_lookup)

    async def scenario():
        transport = httpx.ASGITransport(app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/v7/state", params={"session_id": "read-must-not-create"})
        assert calls == [], "GET /v7/state called the mutating get_or_create_session path"
        assert "read-must-not-create" not in sessions
        assert response.status_code == 404
        assert isolated_app.snapshot()["active_mutations"] == 0

    _run(scenario())


def test_quiescence_with_unfinished_mutation_fails_without_sleep_or_seal(
        isolated_app, monkeypatch):
    """A failed drain cannot publish success or touch the persistence boundary."""
    probe = _SleepProbe()
    monkeypatch.setattr(appmod, "_guala", probe)
    assert isolated_app.admit_mutation()

    wait_called = []

    def fail_wait(timeout):
        wait_called.append(timeout)
        raise RuntimeError("one mutating request did not finish")

    monkeypatch.setattr(isolated_app, "wait_for_mutations", fail_wait)

    async def scenario():
        transport = httpx.ASGITransport(app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sleep_for_deploy",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-a",
                },
                json={"deploy_nonce": "nonce-a"},
            )
        assert response.status_code == 503
        assert response.json()["ok"] is False
        assert wait_called, "control route never attempted to drain admitted mutations"
        assert probe.calls == 0, "persistence ran despite failed mutation drain"
        snapshot = isolated_app.snapshot()
        assert snapshot["state"] == "RUNNING"
        assert snapshot["certificate"] is None
        assert snapshot["active_mutations"] == 1

    try:
        _run(scenario())
    finally:
        isolated_app.finish_mutation()


@pytest.mark.parametrize(
    ("headers", "body", "expected_status"),
    [
        ({"X-Deploy-Nonce": "nonce-a"}, {"deploy_nonce": "nonce-a"}, 401),
        (
            {"X-API-Key": "wrong", "X-Deploy-Nonce": "nonce-a"},
            {"deploy_nonce": "nonce-a"},
            401,
        ),
        ({"X-API-Key": "control-secret"}, {}, 400),
        (
            {"X-API-Key": "control-secret", "X-Deploy-Nonce": "nonce-a"},
            {"deploy_nonce": "nonce-b"},
            400,
        ),
    ],
)
def test_quiescence_control_auth_and_nonce_are_strict(
        isolated_app, monkeypatch, headers, body, expected_status):
    probe = _SleepProbe()
    monkeypatch.setattr(appmod, "_guala", probe)

    async def scenario():
        transport = httpx.ASGITransport(app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sleep_for_deploy", headers=headers, json=body)
        assert response.status_code == expected_status
        assert probe.calls == 0, "unauthorized or nonce-invalid control request mutated state"
        snapshot = isolated_app.snapshot()
        assert snapshot["state"] == "RUNNING"
        assert snapshot["active_mutations"] == 0
        assert snapshot["certificate"] is None

    _run(scenario())
