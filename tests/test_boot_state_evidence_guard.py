"""Retired verbatim WAL artifacts have no boot authority."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import WAL_DIRNAME  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def test_retired_wal_segments_do_not_block_structural_genesis(tmp_path):
    state = str(tmp_path)
    wal = os.path.join(state, WAL_DIRNAME)
    os.makedirs(wal)
    legacy_segment = os.path.join(wal, "seg-00000002-00000000.jsonl")
    with open(legacy_segment, "w") as handle:
        handle.write("legacy verbatim data")

    guala = Guala()
    guala.load_full_state(state)

    assert guala._load_successful
    assert os.path.exists(os.path.join(state, "guala_identity.json"))
    assert os.path.exists(legacy_segment)
    assert guala.window_manager.closed_window_count() == 0


def test_empty_retired_wal_dir_allows_genesis(tmp_path):
    state = str(tmp_path)
    os.makedirs(os.path.join(state, WAL_DIRNAME))

    guala = Guala()
    guala.load_full_state(state)
    assert guala._load_successful
    assert os.path.exists(os.path.join(state, "guala_identity.json"))
