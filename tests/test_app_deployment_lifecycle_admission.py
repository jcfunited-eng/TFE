"""Current production route boundary; retired cognition stays unmounted."""

from __future__ import annotations

import asyncio

import httpx

import dsf_ai_service.app as appmod


def test_current_release_routes_are_truthful_and_retired_routes_are_absent(
    monkeypatch,
) -> None:
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", False)
    monkeypatch.setattr(appmod, "_init_complete", False)
    monkeypatch.setattr(appmod, "_init_error", None)
    monkeypatch.setattr(appmod, "_boot_halted", None)
    monkeypatch.setattr(appmod, "_guala", None)

    mounted = {
        (method, route.path)
        for route in appmod.app.routes
        for method in (getattr(route, "methods", None) or ())
    }
    assert ("POST", "/api/v1/gualaloom") not in mounted
    assert ("GET", "/v7/state") not in mounted
    assert ("POST", "/sleep_for_deploy") not in mounted
    assert ("POST", "/internal/deployment/quiesce") in mounted
    assert ("GET", "/health") in mounted
    assert ("GET", "/ready") in mounted
    assert ("GET", "/api/v1/gualaloom/observation") in mounted

    async def scenario() -> None:
        transport = httpx.ASGITransport(
            app=appmod.app,
            raise_app_exceptions=False,
        )
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            retired_converse = await client.post(
                "/api/v1/gualaloom",
                json={"text": "not an admitted physical input"},
            )
            retired_v7 = await client.get("/v7/state")
            retired_deploy = await client.post("/sleep_for_deploy")
            health = await client.get("/health")
            ready = await client.get("/ready")
            observation = await client.get(
                "/api/v1/gualaloom/observation"
            )

        assert retired_converse.status_code == 404
        assert retired_v7.status_code == 404
        assert retired_deploy.status_code == 404
        assert health.status_code == 200
        assert health.json()["status"] == "initializing"
        assert health.json()["ready"] is False
        assert ready.status_code == 200
        assert ready.json()["ready"] is True
        assert ready.json()["guala_ready"] is False
        assert ready.json()["state"] == "warming"
        assert observation.status_code == 200
        assert observation.json() == {
            "schema": "guala.observation_snapshot.v5",
            "status": "unavailable",
            "reason": "embedded_substrate_unavailable",
        }

    asyncio.run(scenario())
