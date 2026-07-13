"""Cancellation contracts for app-owned mutating executor work."""

import asyncio
import io
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod
from dsf_ai_service.substrate import v7_engine


@pytest.fixture
def isolated_lifecycle(monkeypatch):
    lifecycle = appmod._DeploymentLifecycle()
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    token = appmod._lifecycle_mutation_depth.set(0)
    try:
        yield lifecycle
    finally:
        appmod._lifecycle_mutation_depth.reset(token)


def test_lifecycle_executor_waits_for_worker_after_request_cancellation(
        isolated_lifecycle):
    started = threading.Event()
    release = threading.Event()

    def writer():
        started.set()
        assert release.wait(3.0)
        return "written"

    async def scenario():
        task = asyncio.create_task(appmod._run_lifecycle_executor(writer))
        assert await asyncio.to_thread(started.wait, 1.0)
        assert isolated_lifecycle.snapshot()["active_mutations"] == 1

        task.cancel()
        await asyncio.sleep(0.05)
        assert not task.done()
        assert isolated_lifecycle.snapshot()["active_mutations"] == 1

        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert isolated_lifecycle.snapshot()["active_mutations"] == 0

    asyncio.run(scenario())


def test_picture_upload_cancellation_owns_atomic_efs_write(
        isolated_lifecycle, monkeypatch, tmp_path):
    started = threading.Event()
    release = threading.Event()
    real_fsync = appmod.os.fsync

    def blocking_fsync(fd):
        started.set()
        assert release.wait(3.0)
        real_fsync(fd)

    picture_bytes = io.BytesIO()
    Image.new("RGB", (4, 4), color=(12, 34, 56)).save(
        picture_bytes, format="PNG")
    fake_guala = SimpleNamespace(
        tick=17,
        _pictures={},
        _log_substrate_event=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(appmod, "_guala", fake_guala)
    monkeypatch.setattr(appmod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(appmod.os, "fsync", blocking_fsync)

    async def scenario():
        upload = UploadFile(
            filename="memory.png", file=io.BytesIO(picture_bytes.getvalue()))
        task = asyncio.create_task(appmod.gualaloom_upload_picture(upload))
        assert await asyncio.to_thread(started.wait, 1.0)

        task.cancel()
        await asyncio.sleep(0.05)
        assert not task.done()
        assert isolated_lifecycle.snapshot()["active_mutations"] == 1
        assert fake_guala._pictures == {}

        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert isolated_lifecycle.snapshot()["active_mutations"] == 0

    asyncio.run(scenario())

    originals = list((tmp_path / "pictures").glob("*_original.png"))
    assert len(originals) == 1
    assert originals[0].read_bytes() == picture_bytes.getvalue()
    assert len(fake_guala._pictures) == 1
    assert not list((tmp_path / "pictures").glob("*.tmp"))


def test_v7_converse_cancellation_waits_through_required_save(
        isolated_lifecycle, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    saved = []

    class Session:
        def converse(self, text):
            started.set()
            assert release.wait(3.0)
            return {"response_tokens": [], "text": text}

    session = Session()
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace())
    monkeypatch.setattr(
        v7_engine, "get_or_create_session",
        lambda _session_id, engine=None: session)
    monkeypatch.setattr(v7_engine, "save_session", saved.append)

    async def scenario():
        request = appmod.V7ConverseRequest(text="remember this", session_id="s1")
        task = asyncio.create_task(appmod.v7_converse(request))
        assert await asyncio.to_thread(started.wait, 1.0)

        task.cancel()
        await asyncio.sleep(0.05)
        assert not task.done()
        assert saved == []
        assert isolated_lifecycle.snapshot()["active_mutations"] == 1

        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert saved == [session]
        assert isolated_lifecycle.snapshot()["active_mutations"] == 0

    asyncio.run(scenario())
