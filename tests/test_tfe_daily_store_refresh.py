import datetime as dt
import io
import json

import pandas as pd
import pytest

from tools.ch4_store_refresh import assemble, completed_sessions, publish_atomic


def fixture():
    days = [dt.date(2026, 9, d) for d in (1, 2, 3, 4)]
    frame = pd.DataFrame([(pd.Timestamp(days[i]), 'A', 10., 100.) for i in (0, 2)],
                         columns=['Date', 'Symbol', 'Close', 'Volume'])
    def fetch(day, key):
        return [{'T': 'A', 'c': 30. if day == str(days[3]) else 10., 'v': 100.}]
    return frame, days, fetch


def test_repairs_interior_gap_and_keeps_large_structural_move():
    frame, days, fetch = fixture()
    result, receipt = assemble(frame, {'A'}, days, 'test', fetch=fetch)
    assert result.Close.tolist() == [10., 10., 10., 30.]
    assert result.Date.dt.date.tolist() == days
    assert receipt['added_rows'] == 2


def test_failed_fetch_cannot_be_called_current():
    frame, days, _ = fixture()
    original = frame.copy()
    def fetch(day, key):
        raise RuntimeError('provider unavailable')
    with pytest.raises(RuntimeError, match='provider unavailable'):
        assemble(frame, {'A'}, days, 'test', fetch=fetch)
    pd.testing.assert_frame_equal(frame, original)


def test_empty_completed_session_is_a_failure():
    frame, days, _ = fixture()
    with pytest.raises(RuntimeError, match='no provider bars'):
        assemble(frame, {'A'}, days, 'test', fetch=lambda *_: [])


def test_revised_overlap_refuses_instead_of_deleting_history():
    frame, days, _ = fixture()
    def fetch(day, key):
        return [{'T': 'A', 'c': 5., 'v': 100.}]
    with pytest.raises(RuntimeError, match='revised historical overlap'):
        assemble(frame, {'A'}, days, 'test', fetch=fetch)


def test_budget_refuses_before_network_calls():
    frame, days, _ = fixture()
    def fetch(*_):
        pytest.fail('budget must be checked before any network call')
    with pytest.raises(RuntimeError, match='resource budget'):
        assemble(frame, {'A'}, days, 'test', fetch=fetch, max_fetch_days=1)


def test_atomic_publication_failure_preserves_old_store(tmp_path, monkeypatch):
    frame, _, _ = fixture()
    target = tmp_path / 'store.parquet'
    target.write_bytes(b'original bytes')
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(pd.DataFrame, 'to_parquet', fail)
    with pytest.raises(OSError, match='disk full'):
        publish_atomic(frame, target)
    assert target.read_bytes() == b'original bytes'
    assert list(tmp_path.iterdir()) == [target]


def test_successful_atomic_publication_roundtrip(tmp_path):
    frame, _, _ = fixture()
    target = tmp_path / 'store.parquet'
    publish_atomic(frame, target)
    assert frame.to_dict('records') == pd.read_parquet(target).to_dict('records')


@pytest.mark.parametrize('day,utc_close', [('2026-07-02', 17), ('2026-11-27', 18)])
def test_calendar_early_close_and_daylight_saving(monkeypatch, day, utc_close):
    monkeypatch.setenv('APCA_API_KEY_ID', 'test')
    monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
    def response(*args, **kwargs):
        return io.BytesIO(json.dumps([{'date': day, 'close': '13:00'}]).encode())
    monkeypatch.setattr('urllib.request.urlopen', response)
    date = dt.date.fromisoformat(day)
    before = dt.datetime.combine(date, dt.time(utc_close - 1, 59), dt.timezone.utc)
    after = dt.datetime.combine(date, dt.time(utc_close, 1), dt.timezone.utc)
    assert completed_sessions(date, before) == []
    assert completed_sessions(date, after) == [date]
