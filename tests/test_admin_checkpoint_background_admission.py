from __future__ import annotations

import asyncio

import httpx

import dsf_ai_service.app as appmod


async def _wait_for_background_completion() -> None:
    tasks = tuple(appmod._mutating_background_tasks)
    if tasks:
        await asyncio.gather(*tasks)
    await asyncio.sleep(0)


def test_blocked_checkpoint_refuses_99_overlaps_and_releases_for_retry(
    monkeypatch,
) -> None:
    async def scenario() -> None:
        lifecycle = appmod._DeploymentLifecycle()
        admission = appmod._AdministrativeCheckpointAdmission()
        tasks = set()
        started = asyncio.Event()
        release = asyncio.Event()
        execution = {
            "active": 0,
            "maximum": 0,
            "calls": 0,
            "fail": False,
        }

        async def controlled_executor(_function, *_arguments):
            execution["calls"] += 1
            execution["active"] += 1
            execution["maximum"] = max(
                execution["maximum"],
                execution["active"],
            )
            started.set()
            try:
                await release.wait()
                if execution["fail"]:
                    raise RuntimeError(
                        "injected checkpoint transaction failure")
                return {"checkpoint": "complete"}
            finally:
                execution["active"] -= 1

        monkeypatch.setattr(
            appmod,
            "_deployment_lifecycle",
            lifecycle,
        )
        monkeypatch.setattr(
            appmod,
            "_administrative_checkpoint_admission",
            admission,
        )
        monkeypatch.setattr(
            appmod,
            "_mutating_background_tasks",
            tasks,
        )
        monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
        monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")
        monkeypatch.setattr(
            appmod,
            "_GUALALOOM_API_KEY",
            "authenticated-checkpoint-test-key",
        )
        monkeypatch.setattr(appmod, "_gl_init", lambda: None)
        monkeypatch.setattr(appmod, "_guala", object())
        monkeypatch.setattr(
            appmod,
            "_run_lifecycle_executor",
            controlled_executor,
        )

        transport = httpx.ASGITransport(
            app=appmod.app,
            raise_app_exceptions=False,
        )
        headers = {
            "X-API-Key": "authenticated-checkpoint-test-key",
        }
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            responses = await asyncio.gather(*(
                client.post(
                    "/api/v1/gualaloom/admin/backup",
                    headers=headers,
                )
                for _ in range(100)
            ))
            await asyncio.wait_for(started.wait(), timeout=1.0)

            accepted = [
                response for response in responses
                if response.status_code == 202
            ]
            refused = [
                response for response in responses
                if response.status_code == 409
            ]
            assert len(accepted) == 1
            assert len(refused) == 99
            assert all(
                response.json()["detail"] == (
                    "an authenticated administrative checkpoint is "
                    "already in progress"
                )
                for response in refused
            )
            assert all(
                response.headers["retry-after"] == "5"
                for response in refused
            )
            assert execution["maximum"] == 1
            assert execution["calls"] == 1
            assert admission.snapshot() == {
                "active": True,
                "active_count": 1,
            }
            assert len(tasks) == 1
            assert lifecycle.snapshot()["active_mutations"] == 1

            release.set()
            await _wait_for_background_completion()

            assert admission.snapshot() == {
                "active": False,
                "active_count": 0,
            }
            assert tasks == set()
            assert lifecycle.snapshot()["active_mutations"] == 0

            execution["fail"] = True
            failed_retry = await client.post(
                "/api/v1/gualaloom/admin/backup",
                headers=headers,
            )
            assert failed_retry.status_code == 202
            await _wait_for_background_completion()
            assert execution["calls"] == 2
            assert execution["maximum"] == 1
            assert admission.snapshot()["active_count"] == 0
            assert tasks == set()
            assert lifecycle.snapshot()["active_mutations"] == 0

            execution["fail"] = False
            successful_retry = await client.post(
                "/api/v1/gualaloom/admin/backup",
                headers=headers,
            )
            assert successful_retry.status_code == 202
            await _wait_for_background_completion()
            assert execution["calls"] == 3
            assert execution["maximum"] == 1
            assert admission.snapshot()["active_count"] == 0
            assert tasks == set()
            assert lifecycle.snapshot()["active_mutations"] == 0

    asyncio.run(scenario())


def test_scheduling_failure_releases_checkpoint_admission(
    monkeypatch,
) -> None:
    admission = appmod._AdministrativeCheckpointAdmission()
    monkeypatch.setattr(
        appmod,
        "_administrative_checkpoint_admission",
        admission,
    )
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(appmod, "_gl_init", lambda: None)
    monkeypatch.setattr(appmod, "_guala", object())

    def fail_schedule(*_args, **_kwargs):
        raise RuntimeError("injected scheduler failure")

    monkeypatch.setattr(
        appmod,
        "_schedule_mutating_background",
        fail_schedule,
    )

    async def scenario() -> None:
        try:
            await appmod.admin_backup()
        except RuntimeError as error:
            assert str(error) == "injected scheduler failure"
        else:
            raise AssertionError("scheduling failure was swallowed")

    asyncio.run(scenario())
    assert admission.snapshot() == {
        "active": False,
        "active_count": 0,
    }
