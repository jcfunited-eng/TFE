from __future__ import annotations

import asyncio
import hashlib
import subprocess
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

import dsf_ai_service.app as appmod
import dsf_ai_service.substrate_runner as substrate_runner


_FAILURE_REPETITIONS = 12


class _Upload:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def read(self, size: int) -> bytes:
        return self.payload[:size]


class _RejectingVideoMap(dict):
    def __setitem__(self, key, value) -> None:
        del key, value
        raise RuntimeError("injected video-map admission failure")


def _guala(*, videos=None, event_log=None):
    return SimpleNamespace(
        lock=threading.RLock(),
        _videos={} if videos is None else videos,
        tick=31,
        _asset_key=lambda item_id: hashlib.sha256(
            str(item_id).encode("utf-8")
        ).hexdigest(),
        _log_substrate_event=(
            (lambda _kind, **_detail: None)
            if event_log is None
            else event_log
        ),
    )


def _configure_decoder(
    monkeypatch,
    tmp_path: Path,
    *,
    engine,
) -> tuple[Path, Path]:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    state = tmp_path / "state"
    state.mkdir()

    async def run_inline(function, *args):
        return function(*args)

    def bounded_ffmpeg(command, **_kwargs):
        template = command[command.index("-frames:v") + 2]
        Image.new("L", (160, 120), color=127).save(
            template.replace("%05d", "00001")
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.setattr(appmod, "STATE_DIR", str(state))
    monkeypatch.setattr(appmod, "_physical_byte_authority", None)
    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_gl_init", lambda: None)
    monkeypatch.setattr(appmod, "_guala", engine)
    monkeypatch.setattr(appmod, "_run_lifecycle_executor", run_inline)
    monkeypatch.setattr(subprocess, "run", bounded_ffmpeg)
    monkeypatch.setattr(
        substrate_runner,
        "_webm_to_wav_bytes",
        lambda _payload, **_kwargs: None,
    )
    return scratch, state


def _temporary_census(scratch: Path) -> tuple[str, ...]:
    return tuple(sorted(
        path.name
        for path in scratch.iterdir()
        if path.is_dir() and path.name.startswith("guala_vid_")
    ))


def _durable_item_census(state: Path) -> tuple[str, ...]:
    video_root = state / "assets" / "videos"
    if not video_root.exists():
        return ()
    return tuple(sorted(path.name for path in video_root.iterdir()))


def test_repeated_frame_save_failures_restore_temp_census(
    monkeypatch,
    tmp_path: Path,
) -> None:
    scratch, state = _configure_decoder(
        monkeypatch,
        tmp_path,
        engine=_guala(),
    )
    baseline = _temporary_census(scratch)

    def fail_frame_save(*_args, **_kwargs):
        raise RuntimeError("injected frame save failure")

    monkeypatch.setattr(appmod.np, "save", fail_frame_save)
    for occurrence in range(_FAILURE_REPETITIONS):
        with pytest.raises(
            RuntimeError,
            match="injected frame save failure",
        ):
            asyncio.run(
                appmod.gualaloom_upload_video(
                    _Upload(f"video-{occurrence}".encode("utf-8"))
                )
            )
        assert _temporary_census(scratch) == baseline
        assert _durable_item_census(state) == ()


def test_repeated_video_map_admission_failures_restore_temp_census(
    monkeypatch,
    tmp_path: Path,
) -> None:
    scratch, state = _configure_decoder(
        monkeypatch,
        tmp_path,
        engine=_guala(videos=_RejectingVideoMap()),
    )
    baseline = _temporary_census(scratch)

    for occurrence in range(_FAILURE_REPETITIONS):
        with pytest.raises(
            RuntimeError,
            match="injected video-map admission failure",
        ):
            asyncio.run(
                appmod.gualaloom_upload_video(
                    _Upload(f"video-{occurrence}".encode("utf-8"))
                )
            )
        assert _temporary_census(scratch) == baseline
        assert _durable_item_census(state) == ()


def test_success_reclaims_temp_and_retains_committed_media(
    monkeypatch,
    tmp_path: Path,
) -> None:
    engine = _guala()
    scratch, state = _configure_decoder(
        monkeypatch,
        tmp_path,
        engine=engine,
    )
    baseline = _temporary_census(scratch)

    for occurrence in range(4):
        result = asyncio.run(
            appmod.gualaloom_upload_video(
                _Upload(f"success-{occurrence}".encode("utf-8"))
            )
        )
        video = engine._videos[result["item_id"]]
        assert Path(video.frame_dir).is_dir()
        assert tuple(Path(video.frame_dir).iterdir())
        assert _temporary_census(scratch) == baseline

    assert len(_durable_item_census(state)) == 4


def test_post_map_exception_does_not_delete_committed_media(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fail_event_log(_kind, **_detail):
        raise RuntimeError("injected post-map event failure")

    engine = _guala(event_log=fail_event_log)
    scratch, state = _configure_decoder(
        monkeypatch,
        tmp_path,
        engine=engine,
    )
    baseline = _temporary_census(scratch)

    with pytest.raises(
        RuntimeError,
        match="injected post-map event failure",
    ):
        asyncio.run(
            appmod.gualaloom_upload_video(_Upload(b"committed-video"))
        )

    assert _temporary_census(scratch) == baseline
    assert len(engine._videos) == 1
    committed = next(iter(engine._videos.values()))
    assert Path(committed.frame_dir).is_dir()
    assert len(_durable_item_census(state)) == 1
