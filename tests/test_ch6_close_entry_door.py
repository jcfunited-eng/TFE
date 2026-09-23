"""CH6 at-close entry door (Joe 2026-09-23) — the pure read of the day so
far, on the engine's own three conditions. Values are real: AAPL from the
store and the market snapshot on 2026-09-23, and the day's gainers that
the dry run screened (MTC +20.1% on 2.6x, QMCO +11.1% on 2.1x — both
refused for volume, correctly).

Run: python3 -m pytest tests/test_ch6_close_entry_door.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.ch6_fast_harvest import (  # noqa: E402
    EVENT_GAIN, VOL_MULT, PRICE_FLOOR, close_entry_door, ENTRY_AT_CLOSE,
)


def test_constants_are_the_engines_own():
    assert EVENT_GAIN == 8.0
    assert VOL_MULT == 3.0
    assert PRICE_FLOOR == 5.0
    assert ENTRY_AT_CLOSE is True


def test_spike_on_heavy_volume_opens_the_door():
    # +10% over the prior close on 4x the trailing mean
    gain = close_entry_door(px=11.0, vol_today=4_000_000, prev_close=10.0, vol_mean20=1_000_000)
    assert gain is not None and abs(gain - 10.0) < 1e-9


def test_exactly_on_both_lines_opens():
    gain = close_entry_door(px=10.8, vol_today=3_000_000, prev_close=10.0, vol_mean20=1_000_000)
    assert gain is not None and abs(gain - 8.0) < 1e-9


def test_mtc_refused_for_volume():
    # dry run 2026-09-23: MTC +20.1% but only 2.6x the trailing mean
    assert close_entry_door(px=12.01, vol_today=77_383, prev_close=10.0, vol_mean20=29_310) is None


def test_qmco_refused_for_volume():
    assert close_entry_door(px=11.11, vol_today=2_171_696, prev_close=10.0, vol_mean20=1_022_091) is None


def test_aapl_quiet_day_refused_for_gain():
    # AAPL 2026-09-23 ~14:10 ET: 337.35 vs prior close 339.75, 15.4M so far vs ~52M mean
    assert close_entry_door(px=337.3501, vol_today=15_354_395, prev_close=339.75, vol_mean20=52_000_000) is None


def test_price_floor():
    assert close_entry_door(px=4.99, vol_today=9e6, prev_close=4.0, vol_mean20=1e6) is None


def test_unusable_inputs_never_open():
    assert close_entry_door(px=None, vol_today=1, prev_close=1, vol_mean20=1) is None
    assert close_entry_door(px="abc", vol_today=1, prev_close=1, vol_mean20=1) is None
    assert close_entry_door(px=11.0, vol_today=4e6, prev_close=0.0, vol_mean20=1e6) is None
    assert close_entry_door(px=11.0, vol_today=4e6, prev_close=10.0, vol_mean20=0.0) is None
    assert close_entry_door(px=float("nan"), vol_today=4e6, prev_close=10.0, vol_mean20=1e6) is None


def test_strings_from_a_feed_parse():
    gain = close_entry_door(px="11.0", vol_today="4000000", prev_close="10", vol_mean20="1000000")
    assert gain is not None and abs(gain - 10.0) < 1e-9
