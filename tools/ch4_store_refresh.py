"""Refresh TFE daily bars without deleting histories or hiding fetch failures.

Completed sessions come from the broker calendar. Missing dates are repaired
inside the history as well as at its tail. Changed overlap prices require
history reconciliation; provider volume corrections are upserted verbatim.
Publication is atomic and serialized. Older history and per-ticker gaps are
not certified merely because the latest overlap agrees.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'quarantine_12k_universe_ext.parquet'
LIVE = ROOT / 'ch4_live_store.parquet'
ROSTER = ROOT / 'artifacts/ch4_uf/ch4_field_cohorts.json'
COLUMNS = ['Date', 'Symbol', 'Close', 'Volume']


def fetch_day(day, key):
    query = urllib.parse.urlencode({'adjusted': 'true', 'apiKey': key})
    url = f'https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{day}?{query}'
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
    except Exception as error:
        raise RuntimeError(f'provider fetch failed for {day}: {type(error).__name__}') from None
    if payload.get('status') != 'OK' or not isinstance(payload.get('results'), list):
        raise RuntimeError(f'provider did not confirm a complete response for {day}')
    return payload['results']


def completed_sessions(start, now):
    key = os.environ.get('ALPACA_API_KEY') or os.environ.get('APCA_API_KEY_ID')
    secret = (os.environ.get('ALPACA_API_SECRET_KEY') or os.environ.get('ALPACA_SECRET_KEY')
              or os.environ.get('APCA_API_SECRET_KEY'))
    if not key or not secret:
        raise RuntimeError('Alpaca credentials required for the completed-session calendar')
    eastern = ZoneInfo('America/New_York')
    query = urllib.parse.urlencode({'start': str(start), 'end': str(now.astimezone(eastern).date())})
    request = urllib.request.Request('https://paper-api.alpaca.markets/v2/calendar?' + query,
        headers={'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            calendar = json.load(response)
    except Exception as error:
        raise RuntimeError(f'calendar fetch failed: {type(error).__name__}') from None
    if not isinstance(calendar, list) or not calendar:
        raise RuntimeError('calendar response missing')
    sessions = []
    for row in calendar:
        day = dt.date.fromisoformat(row['date'])
        close = dt.datetime.combine(day, dt.time.fromisoformat(row['close']), eastern)
        if close <= now:
            sessions.append(day)
    if len(sessions) != len(set(sessions)):
        raise RuntimeError('duplicate calendar sessions')
    return sorted(sessions)


def validate_frame(frame):
    if not set(COLUMNS) <= set(frame):
        raise ValueError('daily store is missing required columns')
    out = frame[COLUMNS].copy()
    out['Date'] = pd.to_datetime(out.Date)
    if out.empty or out.Date.isna().any() or out.Symbol.isna().any():
        raise ValueError('empty store or missing dates/symbols')
    if (out.Date != out.Date.dt.normalize()).any():
        raise ValueError('daily store dates must be midnight date labels')
    if out.duplicated(['Date', 'Symbol']).any():
        raise ValueError('duplicate stored bars')
    for column, positive in [('Close', True), ('Volume', False)]:
        values = pd.to_numeric(out[column], errors='raise').astype(float)
        if not values.map(math.isfinite).all() or (values <= 0 if positive else values < 0).any():
            raise ValueError(f'invalid stored {column}')
        out[column] = values
    return out


def assemble(frame, roster, sessions, key, *, fetch=fetch_day, max_fetch_days=10):
    """Return a complete proposed replacement, or raise without publishing."""
    frame = validate_frame(frame)
    days = set(frame.Date.dt.date)
    sessions = sorted(set(sessions))
    if not sessions:
        raise ValueError('no completed sessions')
    if not days <= set(sessions):
        raise ValueError('store dates are outside the supplied completed-session calendar')
    missing = [d for d in sessions if min(days) <= d and d not in days]
    overlap_day = max(days)
    requests = sorted(set(missing + [overlap_day]))
    if len(requests) > max_fetch_days:
        raise RuntimeError(f'refresh requires {len(requests)} provider days; resource budget is {max_fetch_days}')
    responses = {}
    for day in requests:
        records = fetch(day.isoformat(), key)
        if not records:
            raise RuntimeError(f'no provider bars for completed session {day}')
        by_symbol = {}
        for row in records:
            symbol = row['T']
            if symbol not in roster:
                continue
            if symbol in by_symbol:
                raise ValueError(f'duplicate provider bar: {symbol} {day}')
            close, volume = float(row['c']), float(row['v'])
            if not math.isfinite(close) or close <= 0 or not math.isfinite(volume) or volume < 0:
                raise ValueError(f'invalid provider bar: {symbol} {day}')
            by_symbol[symbol] = (close, volume)
        if not by_symbol:
            raise RuntimeError(f'no roster coverage for completed session {day}')
        responses[day] = by_symbol
    overlap_mask = frame.Date.dt.date == overlap_day
    overlap = frame[overlap_mask].set_index('Symbol')
    revised_volumes = {}
    for symbol, (close, volume) in responses[overlap_day].items():
        if symbol in overlap.index:
            old = overlap.loc[symbol]
            if close != float(old.Close):
                raise RuntimeError(f'provider revised historical overlap price for {symbol} {overlap_day}; history reconciliation required')
            if volume != float(old.Volume):
                revised_volumes[symbol] = volume
    appended_symbols = {s for day in missing for s in responses[day]}
    uncovered = (appended_symbols & set(frame.Symbol)) - (set(overlap.index) & set(responses[overlap_day]))
    if uncovered:
        raise RuntimeError('no verified adjustment overlap for: ' + ','.join(sorted(uncovered)))
    # Raw provider corrections, not inferred factors or rounded quantities.
    if revised_volumes:
        mask = overlap_mask & frame.Symbol.isin(revised_volumes)
        frame.loc[mask, 'Volume'] = frame.loc[mask, 'Symbol'].map(revised_volumes)
    rows = [(pd.Timestamp(day), symbol, close, volume) for day in missing
            for symbol, (close, volume) in responses[day].items()]
    receipt = {'fetched_days': len(requests), 'added_rows': len(rows),
               'revised_overlap_rows': len(revised_volumes),
               'repaired_sessions': [str(d) for d in missing],
               'latest_session': str(sessions[-1])}
    if not rows:
        return frame, receipt
    out = pd.concat([frame, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
    return out.sort_values(['Symbol', 'Date']).reset_index(drop=True), receipt


def publish_atomic(frame, target):
    target = Path(target)
    descriptor, name = tempfile.mkstemp(prefix=target.name + '.', suffix='.tmp', dir=target.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        frame.to_parquet(temporary, index=False)
        with temporary.open('rb') as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-fetch-days', type=int, default=10,
                        help='network resource ceiling; never truncates a refresh')
    args = parser.parse_args()
    if args.max_fetch_days <= 0:
        raise ValueError('max-fetch-days must be positive')
    key = os.environ.get('MASSIVE_API_KEY') or os.environ.get('POLYGON_API_KEY')
    if not key:
        raise RuntimeError('Massive API key missing')
    with (ROOT / 'artifacts/vtvr_observer/.daily_store_refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = LIVE if LIVE.exists() else BASE
        frame = validate_frame(pd.read_parquet(source, columns=COLUMNS))
        roster = {s for group in json.loads(ROSTER.read_text())['roster'] for s in group}
        sessions = completed_sessions(frame.Date.min().date(), dt.datetime.now(dt.timezone.utc))
        proposed, receipt = assemble(frame, roster, sessions, key, max_fetch_days=args.max_fetch_days)
        if receipt['added_rows'] or receipt['revised_overlap_rows'] or source != LIVE:
            publish_atomic(proposed, LIVE)
        print(json.dumps({'status': 'complete', **receipt}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
