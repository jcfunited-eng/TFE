"""
sensory_catalog.py — SQLite-backed sensory distribution catalog.

GL-CMD-112 Phase A, per GL-SPC-SENSORY-CATALOG-EVE-20260621-111 §6.2.

Stores per-word per-modality Gaussian distributions (mean, std per channel).
Lives on EFS alongside substrate state for persistence across deploys.
"""

import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple

# Canonical channel sets (must match F1 SensoryTransducer)
from dsf_ai_service.substrate.sensory_transducer import (
    TOUCH_CHANNELS, SMELL_CHANNELS, TASTE_CHANNELS,
)

MODALITY_CHANNELS_MAP = {
    "touch": TOUCH_CHANNELS,
    "smell": SMELL_CHANNELS,
    "taste": TASTE_CHANNELS,
}

STATE_DIR = os.environ.get("STATE_DIR", "/mnt/efs/guala")
CATALOG_DIR = os.path.join(STATE_DIR, "catalog")
CATALOG_DB_PATH = os.path.join(CATALOG_DIR, "sensory_catalog.sqlite3")


class SensoryCatalog:
    """SQLite-backed sensory distribution storage.

    Schema: one row per (word, modality) with:
      - applicable: bool (False = word has no sensory grounding for this modality)
      - mean_json: JSON dict of channel_name → float mean
      - std_json: JSON dict of channel_name → float std
      - source: str (how this entry was generated, e.g., "llm_batch", "substrate")
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or CATALOG_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sensory_entries (
                word TEXT NOT NULL,
                modality TEXT NOT NULL,
                applicable INTEGER NOT NULL DEFAULT 1,
                mean_json TEXT,
                std_json TEXT,
                source TEXT DEFAULT 'llm_batch',
                PRIMARY KEY (word, modality)
            )
        """)
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def has(self, word: str, modality: str) -> bool:
        """Return True if catalog has ANY entry for (word, modality)."""
        row = self._conn.execute(
            "SELECT 1 FROM sensory_entries WHERE word=? AND modality=?",
            (word, modality)
        ).fetchone()
        return row is not None

    def is_applicable(self, word: str, modality: str) -> bool:
        """Return True if word has applicable sensory grounding for modality."""
        row = self._conn.execute(
            "SELECT applicable FROM sensory_entries WHERE word=? AND modality=?",
            (word, modality)
        ).fetchone()
        if row is None:
            return False
        return bool(row[0])

    def get_distribution(self, word: str, modality: str) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
        """Return (mean_dict, std_dict) for a word+modality, or None if not found/not applicable."""
        row = self._conn.execute(
            "SELECT applicable, mean_json, std_json FROM sensory_entries WHERE word=? AND modality=?",
            (word, modality)
        ).fetchone()
        if row is None or not row[0] or not row[1]:
            return None
        mean = json.loads(row[1])
        std = json.loads(row[2]) if row[2] else {k: 0.1 for k in mean}
        return mean, std

    def set_entry(self, word: str, modality: str, *,
                  applicable: bool = True,
                  mean: Optional[Dict[str, float]] = None,
                  std: Optional[Dict[str, float]] = None,
                  source: str = "llm_batch"):
        """Insert or replace a catalog entry."""
        mean_json = json.dumps(mean) if mean else None
        std_json = json.dumps(std) if std else None
        self._conn.execute("""
            INSERT OR REPLACE INTO sensory_entries (word, modality, applicable, mean_json, std_json, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (word, modality, int(applicable), mean_json, std_json, source))
        self._conn.commit()

    def list_unknown(self, words: List[str]) -> List[str]:
        """Return words that have NO entry in catalog for ANY modality."""
        unknown = []
        for w in words:
            row = self._conn.execute(
                "SELECT 1 FROM sensory_entries WHERE word=? LIMIT 1", (w,)
            ).fetchone()
            if row is None:
                unknown.append(w)
        return unknown

    def count(self) -> int:
        """Total entries in catalog."""
        row = self._conn.execute("SELECT COUNT(*) FROM sensory_entries").fetchone()
        return row[0] if row else 0

    def all_words(self) -> List[str]:
        """Return all distinct words in catalog."""
        rows = self._conn.execute(
            "SELECT DISTINCT word FROM sensory_entries"
        ).fetchall()
        return [r[0] for r in rows]
