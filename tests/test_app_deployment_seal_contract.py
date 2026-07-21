"""Focused production handoff contracts for the FastAPI deployment owner.

The tests use isolated in-memory collaborators.  They exercise orchestration
and fail-closed behavior without creating a real Guala, writing EFS, or using
AWS.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod
from dsf_ai_service.substrate import deployment_generation
import dsf_ai_service.substrate_runner as substrate_runner


def _run(coroutine):
    return asyncio.run(coroutine)


def _certificate():
    return {
        "generation_uuid": "11111111-1111-4111-8111-111111111111",
        "identity": "guala-identity",
        "tick": 73,
        "manifest_sha256": "a" * 64,
        "seal_hmac_sha256": "b" * 64,
    }


class _OrderedGuala:
    IDENTITY_FILE = "guala_identity.json"

    def __init__(self, events):
        self.events = events
        self.tick = 73
        self.vocab = {"known"}
        self._guala_identity = "guala-identity"

    def manual_sleep(self, state_dir):
        self.events.append("manual_sleep")

    def settle_queues(self, budget_s=420.0, threshold=8):
        raise AssertionError("production sealing must not use threshold settle")

    def quiesce_background_workers(self, timeout):
        assert timeout == 540.0
        self.events.append("engine_strict_stop")
        return {"engine_quiesced": True, "queues": {
            "organism": {"unfinished": 0, "queued": 0},
            "tapestry": {"unfinished": 0, "queued": 0},
        }}


@pytest.fixture
def ordered_handoff(monkeypatch, tmp_path):
    events = []
    lifecycle = appmod._DeploymentLifecycle()
    guala = _OrderedGuala(events)

    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(appmod, "_guala", guala)
    monkeypatch.setattr(appmod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(appmod, "_converse_tasks", {})
    monkeypatch.setenv("SEAL_SETTLE_BUDGET_S", "420")

    real_auth = appmod._require_deploy_control

    async def ordered_auth(request):
        events.append("auth")
        return await real_auth(request)

    monkeypatch.setattr(appmod, "_require_deploy_control", ordered_auth)

    drain_count = 0

    def drain(_timeout):
        nonlocal drain_count
        drain_count += 1
        events.append(f"admission_drain_{drain_count}")

    monkeypatch.setattr(lifecycle, "wait_for_mutations", drain)

    async def stop_app_tasks(timeout):
        assert timeout == 120.0
        events.append("app_task_stop")
        return {"app_tasks_stopped": 0}

    monkeypatch.setattr(appmod, "_stop_app_lifecycle_tasks", stop_app_tasks)
    monkeypatch.setattr(
        appmod,
        "_fail_inflight_converse_tasks",
        lambda _reason: events.append("converse_task_terminalization"),
    )
    monkeypatch.setattr(
        appmod,
        "_flush_v7_sessions_for_seal",
        lambda: events.append("v7_flush") or {"v7_sessions_flushed": 2},
    )
    monkeypatch.setattr(
        appmod,
        "_stop_embedded_persistence_components",
        lambda timeout: events.append("persistence_stops")
        or {"persistence_components_stopped": ["save_coordinator"]},
    )
    monkeypatch.setattr(
        substrate_runner,
        "quiesce_background_loops",
        lambda timeout: events.append("runner_strict_stop")
        or {"runner_quiesced": True},
    )

    real_seal = lifecycle.seal

    def ordered_seal(proof):
        events.append("sealed")
        real_seal(proof)

    monkeypatch.setattr(lifecycle, "seal", ordered_seal)
    return SimpleNamespace(
        events=events,
        lifecycle=lifecycle,
        guala=guala,
    )


def test_authenticated_handoff_orders_every_writer_before_seal(
        ordered_handoff, monkeypatch):
    """SEALED is published only after every admitted writer and remote proof."""

    def stage_and_prove(nonce):
        assert nonce == "nonce-a"
        ordered_handoff.events.append("stage_and_remote_proof")
        return _certificate()

    monkeypatch.setattr(appmod, "_seal_runtime_generation", stage_and_prove)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-a",
                },
                json={"deploy_nonce": "nonce-a"},
            )

    response = _run(scenario())

    assert response.status_code == 200
    assert response.json()["state"] == "SEALED"
    # GL-RPT-RAM-FIXES-DEPLOYED-AND-SEAL-DEFECTS defect 2 (2026-07-15):
    # in-flight converse turns hold background mutation slots and can await
    # engine progress that quiescence pauses, so they are terminalized (and
    # their tasks cancelled) BEFORE the first drain — otherwise the drain
    # deadlocks on them.  The original post-stop terminalization remains as
    # defense in depth, so the event appears twice.
    assert ordered_handoff.events == [
        "auth",
        "converse_task_terminalization",
        "admission_drain_1",
        "app_task_stop",
        "admission_drain_2",
        "converse_task_terminalization",
        "v7_flush",
        "persistence_stops",
        "runner_strict_stop",
        "manual_sleep",
        "engine_strict_stop",
        "stage_and_remote_proof",
        "sealed",
    ]
    snapshot = ordered_handoff.lifecycle.snapshot()
    assert snapshot["state"] == "SEALED"
    assert snapshot["certificate"]["generation_uuid"] == _certificate()[
        "generation_uuid"]


def test_late_generation_proof_failure_stays_quiescing_without_certificate(
        ordered_handoff, monkeypatch):
    """A failure after strict stops must never reopen or claim a false seal."""

    def fail_late(_nonce):
        ordered_handoff.events.append("stage_and_remote_proof_failed")
        raise RuntimeError("remote read-back differs from staged generation")

    monkeypatch.setattr(appmod, "_seal_runtime_generation", fail_late)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-late-failure",
                },
                json={"deploy_nonce": "nonce-late-failure"},
            )

    response = _run(scenario())

    assert response.status_code == 503
    assert response.json()["ok"] is False
    assert "seal_hmac_sha256" not in response.json()
    snapshot = ordered_handoff.lifecycle.snapshot()
    assert snapshot["state"] == "QUIESCING"
    assert snapshot["certificate"] is None
    assert snapshot["failure"] == (
        "remote read-back differs from staged generation")
    assert ordered_handoff.events[-1] == "stage_and_remote_proof_failed"
    assert "sealed" not in ordered_handoff.events


def test_engine_drain_failure_stays_quiescing_and_never_stages(
        ordered_handoff, monkeypatch):
    """A non-zero engine boundary cannot create or publish a generation."""

    def fail_engine_drain(timeout):
        assert timeout == 540.0
        ordered_handoff.events.append("engine_strict_stop_failed")
        raise RuntimeError("quiescence timed out draining tapestry queue")

    def forbidden_stage(_nonce):
        raise AssertionError("generation staged after failed exact-zero drain")

    monkeypatch.setattr(
        ordered_handoff.guala,
        "quiesce_background_workers",
        fail_engine_drain,
    )
    monkeypatch.setattr(appmod, "_seal_runtime_generation", forbidden_stage)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": "nonce-drain-failure",
                },
                json={"deploy_nonce": "nonce-drain-failure"},
            )

    response = _run(scenario())

    assert response.status_code == 503
    assert response.json()["ok"] is False
    assert "tapestry" in response.json()["error"]
    snapshot = ordered_handoff.lifecycle.snapshot()
    assert snapshot["state"] == "QUIESCING"
    assert snapshot["certificate"] is None
    assert "sealed" not in ordered_handoff.events


@pytest.mark.parametrize("value", ["not-a-number", "-1", "nan", "inf"])
def test_invalid_settle_budget_fails_closed_before_engine_drain(
        ordered_handoff, monkeypatch, value):
    monkeypatch.setenv("SEAL_SETTLE_BUDGET_S", value)

    def forbidden_stage(_nonce):
        raise AssertionError("invalid timeout reached generation staging")

    monkeypatch.setattr(appmod, "_seal_runtime_generation", forbidden_stage)

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.post(
                "/internal/deployment/quiesce",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": f"nonce-{value}",
                },
                json={"deploy_nonce": f"nonce-{value}"},
            )

    response = _run(scenario())

    assert response.status_code == 503
    assert "finite non-negative" in response.json()["error"]
    assert ordered_handoff.lifecycle.snapshot()["state"] == "QUIESCING"
    assert "engine_strict_stop" not in ordered_handoff.events


def test_sealed_shutdown_writes_nothing_and_releases_owner(monkeypatch):
    events = []
    lifecycle = appmod._DeploymentLifecycle()
    lifecycle.begin_quiescence("shutdown-nonce")
    lifecycle.seal(_certificate())

    class Owner:
        acquired = True

        def release(self):
            events.append("owner_release")
            self.acquired = False

    class NoWriteGuala:
        def __getattr__(self, name):
            if name in {
                    "manual_sleep", "save_full_state", "_save_wave_atlas",
                    "quiesce_background_workers", "strict_shutdown",
                    "settle_queues"}:
                def forbidden(*_args, **_kwargs):
                    events.append(name)
                    raise AssertionError(f"sealed shutdown called {name}")
                return forbidden
            raise AttributeError(name)

    owner = Owner()
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_generation_owner_lock", owner)
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_guala", NoWriteGuala())
    monkeypatch.setattr(appmod, "_converse_tasks", {})
    monkeypatch.setattr(
        appmod, "_fail_inflight_converse_tasks", lambda _reason: None)

    _run(appmod.shutdown())

    assert events == ["owner_release"]
    assert lifecycle.snapshot()["state"] == "RETIRED"
    assert appmod._generation_owner_lock is None


@pytest.mark.parametrize(
    ("mismatch", "error_fragment"),
    [
        ("owner", "owner lease"),
        ("build", "git SHA"),
        ("task", "task definition"),
        ("image", "image digest"),
        ("generation", "generation_uuid mismatch"),
        ("manifest", "manifest_sha256 mismatch"),
        ("identity", "live Guala identity"),
        ("nonce", "nonce mismatch"),
    ],
)
def test_deep_readiness_rejects_every_runtime_identity_mismatch(
        monkeypatch, mismatch, error_fragment):
    """No build, task, image, generation, or owner mismatch may return 200."""
    lifecycle = appmod._DeploymentLifecycle()
    generation = SimpleNamespace(
        generation_uuid=_certificate()["generation_uuid"],
        identity=_certificate()["identity"],
        manifest_sha256=_certificate()["manifest_sha256"],
        tick=_certificate()["tick"],
    )
    owner = SimpleNamespace(acquired=mismatch != "owner")
    guala_identity = (
        "different-live-identity"
        if mismatch == "identity"
        else generation.identity)

    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "control-secret")
    monkeypatch.setattr(appmod, "_init_complete", True)
    monkeypatch.setattr(appmod, "_init_error", None)
    monkeypatch.setattr(
        appmod,
        "_guala",
        SimpleNamespace(_guala_identity=guala_identity, tick=generation.tick),
    )
    monkeypatch.setattr(appmod, "_generation_owner_lock", owner)
    monkeypatch.setattr(appmod, "_loaded_generation", generation)

    actual_git = "1" * 40
    expected_git = "2" * 40 if mismatch == "build" else actual_git
    actual_task = "dsf-ai:41"
    expected_task = "dsf-ai:42" if mismatch == "task" else actual_task
    actual_image = "sha256:" + "3" * 64
    expected_image = (
        "sha256:" + "4" * 64 if mismatch == "image" else actual_image)
    monkeypatch.setenv("DEPLOY_EXPECTED_GIT_SHA", expected_git)
    monkeypatch.setenv("DEPLOY_EXPECTED_TASK_DEFINITION", expected_task)
    monkeypatch.setenv("DEPLOY_EXPECTED_IMAGE_DIGEST", expected_image)
    monkeypatch.setattr(appmod, "_read_build_git_sha", lambda: actual_git)
    monkeypatch.setattr(
        appmod,
        "_ecs_task_runtime_identity",
        lambda: {
            "task_definition": actual_task,
            "image_digest": actual_image,
        },
    )

    certificate = _certificate()
    if mismatch == "generation":
        certificate["generation_uuid"] = (
            "22222222-2222-4222-8222-222222222222")
    elif mismatch == "manifest":
        certificate["manifest_sha256"] = "9" * 64

    def load_seal(_root, *, hmac_key, expected_nonce):
        assert hmac_key == appmod._deploy_hmac_key()
        if mismatch == "nonce" or expected_nonce != "readiness-nonce":
            raise RuntimeError("deployment seal nonce mismatch")
        return certificate

    monkeypatch.setattr(
        deployment_generation,
        "load_and_verify_deployment_seal",
        load_seal,
    )

    nonce = "wrong-nonce" if mismatch == "nonce" else "readiness-nonce"

    async def scenario():
        transport = httpx.ASGITransport(
            app=appmod.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://test") as client:
            return await client.get(
                "/internal/deployment/readiness",
                headers={
                    "X-API-Key": "control-secret",
                    "X-Deploy-Nonce": nonce,
                },
            )

    response = _run(scenario())
    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert error_fragment in response.json()["error"]
