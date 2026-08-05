"""reading_prediction_ledger.py — the syntax-fuel instrument.

GL-CMD-SYNTAX-ARC-20260718 Piece 1 (Joe: "make it happen").  During her
normal background reading, the engine makes SAMPLED next-word predictions
from her own certified strand statistics and grades them against the
actual text she is reading.  Every sentence she reads is free ground
truth — millions of graded predictions with zero new infrastructure and
zero borrowed models.

This ledger records the curve: per-day attempts / covered (she had ANY
prediction) / hits (the prediction was the actual next word).  A climbing
curve means recombination has fuel and the proposal composer (Piece 2)
builds on measured ground; a flat curve falsifies the approach cheaply,
in days.

Measurement ONLY: nothing here feeds emission, recall, or learning.
Same house rules as the gap ledger: module singleton off the engine
object (pickle-safe), bounded, atomic+fsync persistence, never raises
into the read path.
"""

from __future__ import annotations

import json
import os
import threading
import time

from dsf_ai_service.substrate.physical_byte_ceiling import (
    PhysicalByteCeilingAuthority,
)

LEDGER_FILE = "reading_predictions.json"
DAY_CAP = 60              # keep at most 60 days of curve
PERSIST_DEBOUNCE_S = 120.0


class ReadingPredictionLedger:
    def __init__(
            self, state_dir, *, physical_byte_authority=None,
            max_encoded_bytes=None):
        self.path = os.path.join(state_dir, LEDGER_FILE)
        self._lock = threading.Lock()
        self._days = {}     # "YYYY-MM-DD" -> {attempts, covered, hits}
        self._last_persist = 0.0
        self._dirty = False
        self._failure = None
        if physical_byte_authority is not None and not isinstance(
                physical_byte_authority, PhysicalByteCeilingAuthority):
            raise TypeError(
                "physical_byte_authority must be a "
                "PhysicalByteCeilingAuthority")
        if max_encoded_bytes is not None and (
                isinstance(max_encoded_bytes, bool)
                or not isinstance(max_encoded_bytes, int)
                or max_encoded_bytes <= 0):
            raise ValueError(
                "reading-prediction ledger capacity must be a positive integer")
        if physical_byte_authority is not None and max_encoded_bytes is None:
            raise ValueError(
                "bounded reading-prediction persistence requires an "
                "encoded-byte capacity")
        self._physical_byte_authority = physical_byte_authority
        self._max_encoded_bytes = max_encoded_bytes
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path) as f:
                    self._days = dict(json.load(f).get("days", {}))
        except Exception:
            self._days = {}

    def _persist_locked(self, force=False):
        now = time.time()
        if not self._dirty:
            return
        if len(self._days) > DAY_CAP:
            self._days = dict(sorted(self._days.items())[-DAY_CAP:])
        encoded = json.dumps(
            {"days": self._days},
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if (
            self._max_encoded_bytes is not None
            and len(encoded) > self._max_encoded_bytes
        ):
            raise RuntimeError(
                "reading-prediction ledger exceeds its configured byte capacity")
        if not force and now - self._last_persist < PERSIST_DEBOUNCE_S:
            return
        authority = self._physical_byte_authority
        if authority is None:
            tmp = self.path + ".tmp"
            try:
                with open(tmp, "wb") as f:
                    f.write(encoded)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        else:
            authority.atomic_replace_bytes(
                self.path,
                encoded,
                operation="publish_reading_prediction_ledger",
            )
        self._last_persist = now
        self._dirty = False
        self._failure = None

    @staticmethod
    def _today():
        return time.strftime("%Y-%m-%d", time.gmtime())

    def record(self, covered, hit):
        with self._lock:
            prior_days = {
                name: dict(day) for name, day in self._days.items()
            }
            prior_dirty = self._dirty
            day = self._days.setdefault(
                self._today(), {"attempts": 0, "covered": 0, "hits": 0})
            day["attempts"] += 1
            if covered:
                day["covered"] += 1
            if hit:
                day["hits"] += 1
            self._dirty = True
            try:
                self._persist_locked()
            except BaseException as error:
                self._days = prior_days
                self._dirty = prior_dirty
                self._failure = str(error)
                raise

    def status(self):
        with self._lock:
            days = sorted(self._days.items())[-7:]
            out = []
            for name, d in days:
                att = max(1, d["attempts"])
                out.append({
                    "day": name,
                    "attempts": d["attempts"],
                    "coverage": round(d["covered"] / att, 4),
                    "accuracy": round(d["hits"] / att, 4),
                    "accuracy_when_covered": round(
                        d["hits"] / max(1, d["covered"]), 4),
                })
            return {
                "curve": out,
                "persistence_failure": self._failure,
            }


_ledger = None
_ledger_lock = threading.Lock()


def get_ledger(
        state_dir=None, *, physical_byte_authority=None,
        max_encoded_bytes=None):
    global _ledger
    if _ledger is None:
        with _ledger_lock:
            if _ledger is None:
                _ledger = ReadingPredictionLedger(
                    state_dir
                    or os.environ.get("STATE_DIR", "/mnt/efs/guala"),
                    physical_byte_authority=physical_byte_authority,
                    max_encoded_bytes=max_encoded_bytes,
                )
    if physical_byte_authority is not None and (
        _ledger._physical_byte_authority is not physical_byte_authority
        or _ledger._max_encoded_bytes != max_encoded_bytes
    ):
        raise RuntimeError(
            "reading-prediction ledger was initialized outside the configured "
            "production storage authority")
    return _ledger


def record_prediction(covered, hit):
    try:
        get_ledger().record(bool(covered), bool(hit))
    except Exception:
        pass
