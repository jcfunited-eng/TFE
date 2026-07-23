import contextlib
from pathlib import Path

from dsf_ai_service import app as app_module
from dsf_ai_service.substrate.deployment_generation import (
    BoundedStageAdmission,
)


def test_runtime_generation_stage_carries_raw_sound_experience(
        tmp_path, monkeypatch):
    active = tmp_path / "active"
    stage = tmp_path / "stage"
    active.mkdir()
    stage.mkdir()
    (active / "guala_identity.json").write_text(
        '{"guala_identity":"identity-1"}')
    sounds = active / "sounds"
    sounds.mkdir()
    original = b"exact-audio-experience"
    (sounds / "voice.audio").write_bytes(original)
    for index in range(64):
        (sounds / f"empty-{index:02d}" / "nested").mkdir(parents=True)

    class FakeGuala:
        IDENTITY_FILE = "guala_identity.json"

        @contextlib.contextmanager
        def bounded_persistence_admission(self, admission):
            self.admission = admission
            try:
                yield
            finally:
                self.admission = None

        def save_full_state(self, target, publish_generation):
            assert publish_generation is False
            with self.admission.open_text(
                    Path(target, "guala_identity.json")) as handle:
                handle.write('{"guala_identity":"identity-1"}')
            with self.admission.open_text(
                    Path(target, "guala_core.json")) as handle:
                handle.write("{}")

        def _save_wave_atlas(self, target):
            with self.admission.open_binary(
                    Path(target, "wave_atlas.npz")) as handle:
                handle.write(b"wave")

    guala = FakeGuala()
    monkeypatch.setattr(app_module, "STATE_DIR", str(active))
    monkeypatch.setattr(app_module, "_guala", guala)
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")

    admission = BoundedStageAdmission(
        stage,
        max_total_bytes=1024 * 1024,
        max_required_files=128,
        max_path_bytes=16 * 1024,
    )
    app_module._write_runtime_generation_stage(stage, admission)

    assert (stage / "sounds" / "voice.audio").read_bytes() == original
    assert {
        path.relative_to(stage / "sounds").as_posix()
        for path in (stage / "sounds").rglob("*")
    } == {"voice.audio"}
