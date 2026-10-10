"""Native effector component evidence, not autonomous feeding or speech.

Run with the explicitly rebuilt candidate guala_core extension loaded. Drives
are declared mechanical fixtures; no test claims that a neuron produced them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import guala_core
import pytest


def interval(body, drives=(), duration=1_000):
    return guala_core.exact_articulated_body_interval(body, drives, duration)


def test_neutral_body_and_existing_width_consumer():
    from dsf_ai_service.glew_runtime.native_resident_organism import native_articulated_body_state_width

    body = guala_core.exact_neutral_articulated_body_state()
    assert isinstance(body, bytes)
    assert len(body) == native_articulated_body_state_width() == 680
    assert body[:10] == b"GLBODY01\x00\x08"
    assert interval(body) == (body, [], 0)
    anatomy = guala_core.exact_articulated_body_axis_contract()
    assert len(anatomy) == 45
    assert [row[0] for row in anatomy] == list(range(45))
    assert len({row[1] for row in anatomy}) == 45
    assert all(low <= neutral <= high for _, _, _, low, neutral, high in anatomy)
    assert anatomy[18][1:3] == ("glottal_aperture", "square_millimetre")


def test_jaw_impulse_transports_every_consequence_field():
    before = guala_core.exact_neutral_articulated_body_state()
    after, rows, reached = interval(before, ((14, 1, 2_048),))
    # One impulse admits 2048*32 activation. The first 1-ms tissue response is
    # ceil(2048/32)=64 micrometres. No semantic biting action is inferred.
    assert rows == [("jaw_opening", "micrometre", 0, 64, 64, 0, 2_048, 0, 64, 0)]
    assert reached == 1 and len(after) == len(before)
    passive, passive_rows, passive_reached = interval(after, (), 250_000)
    assert passive_reached == 0
    assert all(row[5:8] == (0, 0, 0) and row[9] == 0 for row in passive_rows)
    for _ in range(8):
        passive, _, count = interval(passive, (), 250_000)
        assert count == 0
    assert passive == before


def test_opposed_drive_and_stop_load_remain_distinct():
    before = guala_core.exact_neutral_articulated_body_state()
    after, rows, count = interval(before, ((14, 0, 500), (14, 1, 500)))
    assert after == before and count == 2
    assert rows == [("jaw_opening", "micrometre", 0, 0, 0, 500, 500, 500, 0, 0)]
    after, rows, count = interval(before, ((14, 0, 500),))
    # Jaw neutral equals its lower stop: closing further is reacted load.
    assert after == before and count == 1
    assert rows == [("jaw_opening", "micrometre", 0, 0, 0, 500, 0, 0, 0, 500)]


def test_partitioned_time_and_second_process_cold_successor():
    before = guala_core.exact_neutral_articulated_body_state()
    drives = ((14, 1, 2_048), (23, 0, 4_096), (37, 1, 80))
    whole, _, _ = interval(before, drives, 250_000)
    first, _, _ = interval(before, drives, 64_000)
    split, _, _ = interval(first, (), 186_000)
    assert whole == split
    expected = interval(first, ((18, 1, 8),), 186_000)
    native_path = str(Path(guala_core.__file__).resolve(strict=True))
    script = """
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location('guala_core', os.environ['GUALA_TEST_BODY_NATIVE_PATH'])
core = importlib.util.module_from_spec(spec)
sys.modules['guala_core'] = core
spec.loader.exec_module(core)
request = json.load(sys.stdin)
body, rows, reached = core.exact_articulated_body_interval(
    bytes.fromhex(request['body']), ((18, 1, 8),), 186000)
json.dump([body.hex(), rows, reached], sys.stdout)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps({"body": first.hex()}), text=True, capture_output=True,
        env=dict(os.environ, GUALA_TEST_BODY_NATIVE_PATH=native_path),
        timeout=30, check=True,
    )
    cold_body, cold_rows, cold_reached = json.loads(result.stdout)
    assert bytes.fromhex(cold_body) == expected[0]
    assert [tuple(row) for row in cold_rows] == expected[1]
    assert cold_reached == expected[2]


@pytest.mark.parametrize("drives", [
    ((True, 1, 1),), ((14, False, 1),), ((14, 1, True),),
    ((14, 1, 1.0),), ((14, 1, "1"),), ((14, 1, 0),),
    ((45, 1, 1),), ((14, 2, 1),), ((14, 1, -1),),
    ((14, 1, 1 << 128),), ((14, 1, 1), (14, 1, 2)),
    ((14, 1),), tuple((14, 1, 1) for _ in range(91)),
])
def test_bad_drives_refuse_without_changing_predecessor(drives):
    before = guala_core.exact_neutral_articulated_body_state()
    with pytest.raises((TypeError, ValueError, OverflowError)):
        interval(before, drives)
    assert interval(before) == (before, [], 0)


@pytest.mark.parametrize("duration", [True, 1.0, "1000", 0, -1, 999, 250_001, 251_000])
def test_interval_requires_exact_bounded_clock(duration):
    with pytest.raises((TypeError, ValueError, OverflowError)):
        interval(guala_core.exact_neutral_articulated_body_state(), (), duration)


def test_ordinary_continuation_never_migrates_or_resets_bad_body():
    before = guala_core.exact_neutral_articulated_body_state()
    cases = [before[:-1], before + b"\0", b"GLFUNC01" + before[8:],
             before[:9] + b"\x07" + before[10:]]
    corrupt_axis = bytearray(before)
    corrupt_axis[10:14] = (2**31 - 1).to_bytes(4, "big")
    cases.append(bytes(corrupt_axis))
    for body in cases:
        with pytest.raises(ValueError):
            interval(body)
    assert interval(before) == (before, [], 0)
