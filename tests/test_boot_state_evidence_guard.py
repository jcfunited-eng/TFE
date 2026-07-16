"""Genesis must never proceed over leftover window-WAL segments.

Review item 7 (2026-07-16): the boot decision tree checked only the flat
STATE_FILES, so a state dir holding real window memory (guala_windows_wal/
segments) but no flat files — a half-wiped or half-restored dir — would sail
into genesis, mint a new identity, and interleave new WAL generations with
the orphaned experience.  WAL segments are state evidence: without an
identity they are a NAMED loud halt, same as flat files.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import WAL_DIRNAME  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    Guala,
    GualaBootStateIntegrityHalt,
)


def test_wal_segments_without_identity_halt_boot(tmp_path):
    state = str(tmp_path)
    wal = os.path.join(state, WAL_DIRNAME)
    os.makedirs(wal)
    with open(os.path.join(wal, "seg-00000002-00000000.jsonl"), "w") as fh:
        fh.write("")

    guala = Guala()
    with pytest.raises(GualaBootStateIntegrityHalt, match="segments"):
        guala.load_full_state(state)
    # And no identity was minted over the orphaned memory.
    assert not os.path.exists(os.path.join(state, "guala_identity.json"))


def test_empty_wal_dir_still_allows_genesis(tmp_path):
    state = str(tmp_path)
    os.makedirs(os.path.join(state, WAL_DIRNAME))  # dir exists, no segments

    guala = Guala()
    guala.load_full_state(state)
    assert guala._load_successful
    assert os.path.exists(os.path.join(state, "guala_identity.json"))
