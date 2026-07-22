"""Live visual-frame context ownership and failure cleanup."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def test_first_entry_raise_still_closes_created_frame_context(monkeypatch):
    """F4 (review 2026-07-16): add_entry creates the frame context BEFORE
    entry validation, so a FIRST-entry validation raise used to leak an
    open context forever under the old entries>0 close gate.  The frame
    path must close every context it created — ownership, not entry count.
    """
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    rows, columns = np.indices((64, 64))
    grid = (((rows * 17 + columns * 31) % 256) / 255.0).astype(np.float64)
    engine = Guala()
    try:
        wm = engine.window_manager
        real_add_entry = wm.add_entry

        def first_entry_validation_raise(*args, **kwargs):
            # The production failure shape: the context is created first
            # (inside add_entry via _context_for_entry), the entry itself
            # then fails validation and raises.
            wm.begin_context(
                kwargs["context_id"],
                kwargs.get("trigger_reason", "sight"))
            raise ValueError("injected first-entry validation failure")

        monkeypatch.setattr(wm, "add_entry", first_entry_validation_raise)
        with pytest.raises(ValueError, match="injected first-entry"):
            engine.process_sight_frame(grid)
        monkeypatch.setattr(wm, "add_entry", real_add_entry)

        # The created frame context is closed, not leaked.
        assert wm.open_context_ids("sense:sight:") == ()
        assert list(wm.windows.values()) == [], (
            "transient sensory contexts are settled and released, not retained"
        )

        # And the healthy path still binds + closes its own frame context.
        receipt = engine.process_sight_frame(grid)
        assert receipt["accepted"] is True
        assert wm.open_context_ids("sense:sight:") == ()
    finally:
        engine.shutdown()
