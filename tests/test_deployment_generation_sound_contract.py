from pathlib import Path
from types import SimpleNamespace

from dsf_ai_service import app as app_module


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

    def save_full_state(target, publish_generation):
        assert publish_generation is False
        Path(target, "guala_core.json").write_text("{}")

    def save_wave_atlas(target):
        Path(target, "wave_atlas.npz").write_bytes(b"wave")

    guala = SimpleNamespace(
        IDENTITY_FILE="guala_identity.json",
        save_full_state=save_full_state,
        _save_wave_atlas=save_wave_atlas,
    )
    monkeypatch.setattr(app_module, "STATE_DIR", str(active))
    monkeypatch.setattr(app_module, "_guala", guala)
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")

    app_module._write_runtime_generation_stage(stage)

    assert (stage / "sounds" / "voice.audio").read_bytes() == original
