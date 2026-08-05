"""Physical persistence proof retained after scripted cognition retirement."""

from __future__ import annotations

import os

import numpy as np
import pytest


@pytest.fixture()
def engine(tmp_path):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    value = Guala()
    value.load_full_state(str(tmp_path / "genesis"))
    try:
        yield value
    finally:
        value.shutdown()


def test_save_completes_when_picture_original_missing(engine, tmp_path):
    """A missing display artifact cannot block physical visual-state save."""
    from dsf_ai_service.v4.gualaloom_v5_engine import PictureItem

    state_dir = str(tmp_path / "state")
    picture = PictureItem(
        item_id="pmiss",
        title="lost original",
        intensity_grid=np.zeros((4, 4)),
    )
    picture.original_path = str(tmp_path / "gone.jpg")
    with engine.lock:
        engine._pictures["pmiss"] = picture

    engine.save_full_state(state_dir)

    retained = engine._pictures["pmiss"]
    assert retained.original_path == ""
    assert np.array_equal(retained.intensity_grid, picture.intensity_grid)
    grid_dir = os.path.join(state_dir, "assets", "pictures")
    assert os.path.isdir(grid_dir)
    assert os.listdir(grid_dir)

    engine.save_full_state(state_dir)
