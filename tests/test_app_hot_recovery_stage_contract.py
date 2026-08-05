from pathlib import Path
from types import SimpleNamespace

import pytest

import dsf_ai_service.app as app_module


IDENTITY = "exact-hot-stage-test-ae"
HOT_FILES = (
    "guala_core.json",
    "owner_state/anonymous_passive_window.json",
)


class _RecordingLiveStore:
    baseline = SimpleNamespace(identity=IDENTITY)
    hot_files = HOT_FILES

    def __init__(self, generation_directory: Path) -> None:
        self.generation_directory = generation_directory
        self.committed = None

    def commit_hot_state(self, *, tick, files):
        self.committed = (tick, dict(files))
        return SimpleNamespace(
            generation_uuid="8f7de8e4-06e9-45dc-b971-bd942c7f2d90",
            identity=IDENTITY,
            tick=tick,
            manifest_sha256="a" * 64,
            directory=self.generation_directory,
        )


def _private_stages(state_root: Path) -> dict[str, Path]:
    stages = {}
    for relative in HOT_FILES:
        path = state_root / f"{relative}.tmp"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative.encode("utf-8"))
        stages[relative] = path
    return stages


def test_authoritative_hot_publish_accepts_exact_nested_private_stages(
    monkeypatch,
    tmp_path,
) -> None:
    state_root = tmp_path / "active"
    state_root.mkdir()
    stages = _private_stages(state_root)
    store = _RecordingLiveStore(tmp_path / "generation")
    monkeypatch.setattr(app_module, "STATE_DIR", str(state_root))
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(app_module, "_live_recovery_store", store)
    monkeypatch.setattr(app_module, "_loaded_generation", None)

    app_module._publish_authoritative_hot_generation(
        save_tick=19,
        identity=IDENTITY,
        manifest_files=HOT_FILES,
        files=stages,
    )

    assert store.committed == (
        19,
        {
            relative: str(path.absolute())
            for relative, path in stages.items()
        },
    )
    assert app_module._loaded_generation.generation_uuid == (
        "8f7de8e4-06e9-45dc-b971-bd942c7f2d90"
    )


def test_authoritative_hot_publish_rejects_nested_stage_symlink(
    monkeypatch,
    tmp_path,
) -> None:
    state_root = tmp_path / "active"
    state_root.mkdir()
    stages = _private_stages(state_root)
    external = tmp_path / "external"
    external.write_bytes(b"not-private")
    nested = stages["owner_state/anonymous_passive_window.json"]
    nested.unlink()
    nested.symlink_to(external)
    store = _RecordingLiveStore(tmp_path / "generation")
    monkeypatch.setattr(app_module, "STATE_DIR", str(state_root))
    monkeypatch.setattr(app_module, "_REQUIRE_SEALED_STATE", True)
    monkeypatch.setattr(app_module, "_live_recovery_store", store)

    with pytest.raises(RuntimeError, match="exact private engine stage"):
        app_module._publish_authoritative_hot_generation(
            save_tick=19,
            identity=IDENTITY,
            manifest_files=HOT_FILES,
            files=stages,
        )

    assert store.committed is None
