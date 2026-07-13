"""Live typed conversation must bind its actual camera event before speech."""

import base64
import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _camera_frame_b64() -> str:
    rows, columns = np.indices((64, 64))
    pixels = ((rows * 17 + columns * 31) % 256).astype(np.uint8)
    image = Image.fromarray(pixels, mode="L").convert("RGB")
    payload = io.BytesIO()
    image.save(payload, format="JPEG", quality=90)
    return base64.b64encode(payload.getvalue()).decode("ascii")


def test_observed_turn_teaches_and_releases_exact_multiword_continuation(
        monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    monkeypatch.setattr(appmod, "_guala", engine)
    frame = _camera_frame_b64()

    try:
        learned = appmod._run_embedded_observed_conversation(
            task_id="live-teach",
            text="60x growth in one year",
            source="joe",
            sight_b64=frame,
        )
        emitted = appmod._run_embedded_observed_conversation(
            task_id="live-query",
            text="60x growth",
            source="joe",
            sight_b64=frame,
        )

        assert learned.response == ""
        assert emitted.response == "in one year"
        assert emitted.response_source == "fact_strand_commit"
        assert emitted.committed_sections == (
            "language_fact", "language_fact", "language_fact")

        snapshot = engine.window_manager.snapshot()
        assert snapshot["open_contexts"] == {}
        observed = [
            window for window in snapshot["windows"].values()
            if (window.get("context_detail") or {}).get(
                "experience_origin") == "observed"
        ]
        assert len(observed) == 2
        for window in observed:
            assert {entry["modality"] for entry in window["entries"]} >= {
                "sight", "word"}
            sight_entries = [
                entry for entry in window["entries"]
                if entry["modality"] == "sight"
            ]
            assert len(sight_entries) == 3
            receipts = [
                entry["provenance"]["structural_fact"]
                for entry in sight_entries
            ]
            assert all(receipt["schema"] ==
                       "guala.native_sight_fragment.v1"
                       for receipt in receipts)
            assert all(receipt["dsf"]["status"] == "unknown"
                       for receipt in receipts)
            event_records = [
                event
                for receipt in receipts
                for event in receipt["events"]
            ]
            assert event_records
            assert all(set(event) == {"t", "dw", "s"}
                       for event in event_records)

        restarted = Guala()
        try:
            restarted.window_manager.restore(snapshot)
            restarted._rebuild_language_fact_memory_from_windows()
            rebuilt = restarted._compose_language_fact_settlement(
                ("60x", "growth"))
            assert restarted._committed_emission_response(rebuilt) == (
                "in one year", "fact_strand_commit")
        finally:
            restarted.shutdown()

        completed_exchange = next(
            window for window in observed
            if any(entry["source_tag"] == "guala:self"
                   for entry in window["entries"])
        )
        assert [
            entry["provenance"]["detail"]["language_form"]
            for entry in completed_exchange["entries"]
            if entry["modality"] == "word"
        ] == ["60x", "growth", "in", "one", "year"]

        learned_window = next(
            window for window in observed
            if not any(entry["source_tag"] == "guala:self"
                       for entry in window["entries"])
        )
        learned_window_id = learned_window["window_id"]
        for stored_window in snapshot["windows"].values():
            stored_receipt = next(
                entry["provenance"]["structural_fact"]
                for entry in stored_window["entries"]
                if entry["modality"] == "sight" and
                entry["provenance"]["structural_fact"]["events"]
            )
            stored_receipt["events"][0]["s"] += 0.01
        engine.window_manager.restore(snapshot)

        rejected = appmod._run_embedded_observed_conversation(
            task_id="live-tamper-check",
            text="60x growth",
            source="joe",
            sight_b64=frame,
        )
        assert rejected.response == ""
        assert rejected.response_source == "silence_no_commit"

        label_only = engine.window_manager.snapshot()
        stored_window = label_only["windows"][learned_window_id]
        sight_entry = next(
            entry for entry in stored_window["entries"]
            if entry["modality"] == "sight"
        )
        sight_entry["provenance"]["structural_fact"] = None
        engine.window_manager.restore(label_only)
        with pytest.raises(ValueError, match="lacks certified native sight"):
            engine._remember_closed_language_window(learned_window_id)
    finally:
        engine.shutdown()
