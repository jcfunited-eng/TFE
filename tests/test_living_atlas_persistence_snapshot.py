import json
import os

from dsf_ai_service.v4.gualaloom_v6_living_atlas import LivingAtlas
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def test_persistence_snapshot_is_detached_from_later_field_mutation() -> None:
    atlas = LivingAtlas()
    atlas.record(
        "em",
        7,
        40,
        tick=11,
        structural_fact={
            "schema": "explicit_full_field.v1",
            "D_k": [1, 0, -1],
        },
        causal_experience_id="a" * 64,
        causal_intake_receipt_sha256="b" * 64,
    )

    snapshot = atlas.persistence_snapshot()
    captured = snapshot["entries"]["40"][0]

    live = atlas.entries[40][0]
    live["last_tick"] = 19
    live["structural_fact"]["D_k"][0] = -1
    live["causal_experience_refs"][0]["causal_experience_id"] = "c" * 64

    assert snapshot["tick"] == 11
    assert captured["last_tick"] == 11
    assert captured["structural_fact"]["D_k"] == [1, 0, -1]
    assert captured["causal_experience_refs"] == [
        {
            "causal_experience_id": "a" * 64,
            "causal_intake_receipt_sha256": "b" * 64,
        }
    ]


def test_full_save_generation_keeps_the_captured_atlas_tick(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_REQUIRE_SEALED_STATE", "0")

    writer = Guala()
    restored = None
    try:
        writer.atlas.record("em", 3, 17, tick=writer.tick)
        original_atomic_write = writer._atomic_write
        mutation_applied = False

        def mutate_after_snapshot(path, payload):
            nonlocal mutation_applied
            if (
                not mutation_applied
                and os.path.basename(path) == "guala_core.json"
            ):
                mutation_applied = True
                writer.atlas.entries[17][0]["last_tick"] = writer.tick + 1
            return original_atomic_write(path, payload)

        writer._atomic_write = mutate_after_snapshot
        writer.save_full_state(str(tmp_path))

        with (tmp_path / "guala_core.json").open() as handle:
            core = json.load(handle)["data"]
        with (tmp_path / "guala_atlas.json").open() as handle:
            atlas = json.load(handle)["data"]

        assert mutation_applied is True
        assert writer.atlas.entries[17][0]["last_tick"] == writer.tick + 1
        assert atlas["entries"]["17"][0]["last_tick"] == core["tick"]

        restored = Guala()
        restored.load_full_state(
            str(tmp_path),
            require_exact_binary=True,
        )
        assert restored._load_successful, restored._load_errors
    finally:
        writer.strict_shutdown(timeout=30.0)
        if restored is not None:
            restored.strict_shutdown(timeout=30.0)
