from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

STRUCTURAL_RECENCY_SCHEMA_VERSION = "v1"
TRACKED_SIGN_FIELDS: Tuple[str, ...] = (
    "D",
    "M",
    "R_rev",
    "U_star",
    "C",
    "P",
    "B",
    "S_UF",
    "R_UF",
)
MERGED_HISTORICAL_ROW_TRACE_PATH = Path(
    "backups/lab/recommendation_lab/current_inputs/real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
)
ACTIVE_SNAPSHOT_PATH = Path("uf_snapshot.json")
ACTIVE_SNAPSHOT_BACKUP_PATH = Path("uf_snapshot_old_backup.json")


@dataclass(frozen=True)
class StructuralState:
    regime: str
    pattern_key: str
    values: Dict[str, float]


@dataclass(frozen=True)
class StructuralRecencySeed:
    symbol: str
    source: str
    source_timestamp_utc: Optional[str]
    source_timestamp_ms: Optional[int]
    state: StructuralState
    steps_since_regime_change: int
    steps_since_pattern_change: int
    steps_since_sign_flip_by_field: Dict[str, int]


_TRACE_SEED_CACHE: Optional[Dict[str, StructuralRecencySeed]] = None
_ACTIVE_RECENCY_SEED_CACHE: Optional[Dict[str, StructuralRecencySeed]] = None
_BOOTSTRAP_SEED_CACHE: Optional[Dict[str, StructuralRecencySeed]] = None
_TRACE_CASEFOLD_INDEX: Optional[Dict[str, List[str]]] = None
_ACTIVE_CASEFOLD_INDEX: Optional[Dict[str, List[str]]] = None
_BOOTSTRAP_CASEFOLD_INDEX: Optional[Dict[str, List[str]]] = None


def _clean_symbol(value: Any) -> str:
    return str(value or "").strip()


def _symbol_casefold(value: Any) -> str:
    return _clean_symbol(value).casefold()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _sign(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def _timestamp_to_iso_utc(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    if len(text) <= 0:
        return None
    if text.endswith("Z"):
        return text
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _timestamp_to_epoch_ms(value: Any) -> Optional[int]:
    iso = _timestamp_to_iso_utc(value)
    if iso is None:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None
    return int(dt.timestamp() * 1000.0)


def _pattern_key(regime: str, d: float, p: float, r_rev: float, b: float) -> str:
    return f"reg={regime}|D={int(round(d))}|P={int(round(p))}|Rrev={int(round(r_rev))}|Bsgn={_sign(float(b))}"


def _history_metadata_from_bar_timestamps(bar_timestamps: Iterable[Any]) -> Dict[str, Any]:
    epoch_values: List[int] = []
    latest_bar_timestamp_utc: Optional[str] = None
    for raw in bar_timestamps:
        iso = _timestamp_to_iso_utc(raw)
        epoch_ms = _timestamp_to_epoch_ms(raw)
        if iso is None or epoch_ms is None:
            continue
        latest_bar_timestamp_utc = iso
        epoch_values.append(epoch_ms)

    history_available_steps = max(0, len(epoch_values) - 1)
    if len(epoch_values) >= 2:
        ts_gap_days_from_prev = float((epoch_values[-1] - epoch_values[-2]) / (1000.0 * 60.0 * 60.0 * 24.0))
    else:
        ts_gap_days_from_prev = 0.0

    return {
        "history_available_steps": int(history_available_steps),
        "ts_gap_days_from_prev": float(ts_gap_days_from_prev),
        "latest_bar_timestamp_utc": latest_bar_timestamp_utc,
    }


def history_metadata_from_bars(bars: Iterable[Any]) -> Dict[str, Any]:
    return _history_metadata_from_bar_timestamps(getattr(bar, "timestamp", None) for bar in bars)


def _decision_vector_value(current_state: Dict[str, Any], index: int, default: float = 0.0) -> float:
    dv = current_state.get("decision_vector")
    if isinstance(dv, (list, tuple)) and len(dv) > index:
        return _to_float(dv[index], default)
    return float(default)


def _state_from_live_state(current_state: Dict[str, Any]) -> StructuralState:
    regime = str(current_state.get("regime", "UNKNOWN") or "UNKNOWN").strip() or "UNKNOWN"
    values = {
        "D": _to_float(current_state.get("D_k"), _decision_vector_value(current_state, 0, 0.0)),
        "M": _to_float(current_state.get("M_k"), _decision_vector_value(current_state, 1, 0.0)),
        "R_rev": _to_float(current_state.get("R_rev_k"), _decision_vector_value(current_state, 2, 0.0)),
        "U_star": _to_float(current_state.get("U_star_k"), _decision_vector_value(current_state, 3, 0.0)),
        "C": _to_float(current_state.get("C_k"), 0.0),
        "P": _to_float(current_state.get("P_k"), _decision_vector_value(current_state, 4, 0.0)),
        "B": _to_float(current_state.get("B_k"), _decision_vector_value(current_state, 5, 0.0)),
        "S_UF": _to_float(current_state.get("S_UF"), 0.0),
        "R_UF": _to_float(current_state.get("R_UF"), 0.0),
    }
    return StructuralState(
        regime=regime,
        pattern_key=_pattern_key(regime, values["D"], values["P"], values["R_rev"], values["B"]),
        values=values,
    )


def _state_from_trace_row(row: Dict[str, Any]) -> StructuralState:
    regime = str(row.get("regime", "UNKNOWN") or "UNKNOWN").strip() or "UNKNOWN"
    values = {
        "D": _to_float(row.get("D"), 0.0),
        "M": _to_float(row.get("M"), 0.0),
        "R_rev": _to_float(row.get("R_rev"), 0.0),
        "U_star": _to_float(row.get("U_star"), 0.0),
        "C": _to_float(row.get("C_k"), _to_float(row.get("C"), 0.0)),
        "P": _to_float(row.get("P"), 0.0),
        "B": _to_float(row.get("B"), 0.0),
        "S_UF": _to_float(row.get("S_UF"), 0.0),
        "R_UF": _to_float(row.get("R_UF"), 0.0),
    }
    pattern_key = str(row.get("pattern_key", "") or "").strip()
    if len(pattern_key) <= 0:
        pattern_key = _pattern_key(regime, values["D"], values["P"], values["R_rev"], values["B"])
    return StructuralState(regime=regime, pattern_key=pattern_key, values=values)


def _state_from_snapshot_row(row: Dict[str, Any]) -> StructuralState:
    return _state_from_live_state(row)


def _states_equal(a: StructuralState, b: StructuralState) -> bool:
    if a.regime != b.regime or a.pattern_key != b.pattern_key:
        return False
    for field in TRACKED_SIGN_FIELDS:
        if float(a.values.get(field, 0.0)) != float(b.values.get(field, 0.0)):
            return False
    return True


def _initial_sign_flip_counts() -> Dict[str, int]:
    return {field: -1 for field in TRACKED_SIGN_FIELDS}


def _advance_seed(
    symbol: str,
    source: str,
    source_timestamp_utc: Optional[str],
    source_timestamp_ms: Optional[int],
    prior_seed: Optional[StructuralRecencySeed],
    current_state: StructuralState,
) -> StructuralRecencySeed:
    if prior_seed is None:
        return StructuralRecencySeed(
            symbol=symbol,
            source=source,
            source_timestamp_utc=source_timestamp_utc,
            source_timestamp_ms=source_timestamp_ms,
            state=current_state,
            steps_since_regime_change=0,
            steps_since_pattern_change=0,
            steps_since_sign_flip_by_field=_initial_sign_flip_counts(),
        )

    next_regime_steps = (
        int(prior_seed.steps_since_regime_change + 1)
        if current_state.regime == prior_seed.state.regime
        else 0
    )
    next_pattern_steps = (
        int(prior_seed.steps_since_pattern_change + 1)
        if current_state.pattern_key == prior_seed.state.pattern_key
        else 0
    )

    next_sign_counts: Dict[str, int] = {}
    for field in TRACKED_SIGN_FIELDS:
        prior_value = float(prior_seed.state.values.get(field, 0.0))
        current_value = float(current_state.values.get(field, 0.0))
        if _sign(current_value) != _sign(prior_value):
            next_sign_counts[field] = 0
            continue
        prior_steps = int(prior_seed.steps_since_sign_flip_by_field.get(field, -1))
        next_sign_counts[field] = -1 if prior_steps < 0 else int(prior_steps + 1)

    return StructuralRecencySeed(
        symbol=symbol,
        source=source,
        source_timestamp_utc=source_timestamp_utc,
        source_timestamp_ms=source_timestamp_ms,
        state=current_state,
        steps_since_regime_change=next_regime_steps,
        steps_since_pattern_change=next_pattern_steps,
        steps_since_sign_flip_by_field=next_sign_counts,
    )


def _load_json_payload(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _build_casefold_index(seed_map: Dict[str, StructuralRecencySeed]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for symbol in seed_map.keys():
        folded = _symbol_casefold(symbol)
        bucket = index.setdefault(folded, [])
        bucket.append(symbol)
    for bucket in index.values():
        bucket.sort()
    return index


def _seed_from_recency_snapshot_payload(payload: Dict[str, Any], source_label: str) -> Dict[str, StructuralRecencySeed]:
    generated_at_utc = _timestamp_to_iso_utc(payload.get("generated_at_utc"))
    generated_at_ms = _timestamp_to_epoch_ms(generated_at_utc)
    out: Dict[str, StructuralRecencySeed] = {}
    for row in payload.get("rows", []) or []:
        if not isinstance(row, dict):
            continue
        symbol = _clean_symbol(row.get("ticker"))
        if len(symbol) <= 0:
            continue
        schema_version = str(row.get("structural_recency_schema_version", "") or "").strip()
        if schema_version != STRUCTURAL_RECENCY_SCHEMA_VERSION:
            continue
        out[symbol] = StructuralRecencySeed(
            symbol=symbol,
            source=source_label,
            source_timestamp_utc=generated_at_utc,
            source_timestamp_ms=generated_at_ms,
            state=_state_from_snapshot_row(row),
            steps_since_regime_change=_to_int(row.get("steps_since_regime_change"), 0),
            steps_since_pattern_change=_to_int(row.get("steps_since_pattern_change"), 0),
            steps_since_sign_flip_by_field={
                field: _to_int(row.get(f"{field}_steps_since_sign_flip"), -1)
                for field in TRACKED_SIGN_FIELDS
            },
        )
    return out


def _load_active_snapshot_recency_seed_map() -> Dict[str, StructuralRecencySeed]:
    global _ACTIVE_RECENCY_SEED_CACHE, _ACTIVE_CASEFOLD_INDEX
    if _ACTIVE_RECENCY_SEED_CACHE is not None:
        return _ACTIVE_RECENCY_SEED_CACHE

    payload = _load_json_payload(ACTIVE_SNAPSHOT_PATH)
    if payload is None:
        _ACTIVE_RECENCY_SEED_CACHE = {}
        _ACTIVE_CASEFOLD_INDEX = {}
        return _ACTIVE_RECENCY_SEED_CACHE

    _ACTIVE_RECENCY_SEED_CACHE = _seed_from_recency_snapshot_payload(payload, "active_snapshot_with_recency")
    _ACTIVE_CASEFOLD_INDEX = _build_casefold_index(_ACTIVE_RECENCY_SEED_CACHE)
    return _ACTIVE_RECENCY_SEED_CACHE


def _load_trace_seed_map() -> Dict[str, StructuralRecencySeed]:
    global _TRACE_SEED_CACHE, _TRACE_CASEFOLD_INDEX
    if _TRACE_SEED_CACHE is not None:
        return _TRACE_SEED_CACHE

    by_symbol_ts: Dict[str, Dict[str, StructuralState]] = {}
    if not MERGED_HISTORICAL_ROW_TRACE_PATH.exists():
        _TRACE_SEED_CACHE = {}
        _TRACE_CASEFOLD_INDEX = {}
        return _TRACE_SEED_CACHE

    with MERGED_HISTORICAL_ROW_TRACE_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symbol = _clean_symbol(row.get("symbol"))
            ts_utc = _timestamp_to_iso_utc(row.get("decision_timestamp"))
            if len(symbol) <= 0 or ts_utc is None:
                continue
            state = _state_from_trace_row(row)
            symbol_rows = by_symbol_ts.setdefault(symbol, {})
            existing = symbol_rows.get(ts_utc)
            if existing is None:
                symbol_rows[ts_utc] = state
                continue
            if not _states_equal(existing, state):
                raise RuntimeError(
                    "structural_recency_trace_conflict:"
                    f"symbol={symbol}:decision_timestamp={ts_utc}"
                )

    seed_map: Dict[str, StructuralRecencySeed] = {}
    for symbol, ts_map in by_symbol_ts.items():
        prior: Optional[StructuralRecencySeed] = None
        for ts_utc in sorted(ts_map.keys()):
            prior = _advance_seed(
                symbol=symbol,
                source="merged_historical_row_trace",
                source_timestamp_utc=ts_utc,
                source_timestamp_ms=_timestamp_to_epoch_ms(ts_utc),
                prior_seed=prior,
                current_state=ts_map[ts_utc],
            )
        if prior is not None:
            seed_map[symbol] = prior

    _TRACE_SEED_CACHE = seed_map
    _TRACE_CASEFOLD_INDEX = _build_casefold_index(_TRACE_SEED_CACHE)
    return _TRACE_SEED_CACHE


def _bootstrap_snapshot_payloads() -> List[Tuple[str, Dict[str, Any]]]:
    payloads: List[Tuple[str, Dict[str, Any]]] = []
    for label, path in (
        ("snapshot_old_backup", ACTIVE_SNAPSHOT_BACKUP_PATH),
        ("active_snapshot", ACTIVE_SNAPSHOT_PATH),
    ):
        payload = _load_json_payload(path)
        if payload is None:
            continue
        payloads.append((label, payload))

    payloads.sort(
        key=lambda item: (
            _timestamp_to_epoch_ms(item[1].get("generated_at_utc")) or -1,
            item[0],
        )
    )
    return payloads


def _overlay_bootstrap_snapshot(
    seed_map: Dict[str, StructuralRecencySeed],
    source_label: str,
    payload: Dict[str, Any],
) -> None:
    generated_at_utc = _timestamp_to_iso_utc(payload.get("generated_at_utc"))
    generated_at_ms = _timestamp_to_epoch_ms(generated_at_utc)
    rows = payload.get("rows", []) or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = _clean_symbol(row.get("ticker"))
        if len(symbol) <= 0:
            continue
        current_state = _state_from_snapshot_row(row)
        prior_seed = seed_map.get(symbol)
        if prior_seed is not None and generated_at_ms is not None and prior_seed.source_timestamp_ms is not None:
            if generated_at_ms <= int(prior_seed.source_timestamp_ms):
                continue
        seed_map[symbol] = _advance_seed(
            symbol=symbol,
            source=source_label,
            source_timestamp_utc=generated_at_utc,
            source_timestamp_ms=generated_at_ms,
            prior_seed=prior_seed,
            current_state=current_state,
        )


def _load_bootstrap_seed_map() -> Dict[str, StructuralRecencySeed]:
    global _BOOTSTRAP_SEED_CACHE, _BOOTSTRAP_CASEFOLD_INDEX
    if _BOOTSTRAP_SEED_CACHE is not None:
        return _BOOTSTRAP_SEED_CACHE

    seed_map = dict(_load_trace_seed_map())
    for source_label, payload in _bootstrap_snapshot_payloads():
        _overlay_bootstrap_snapshot(seed_map, source_label, payload)

    _BOOTSTRAP_SEED_CACHE = seed_map
    _BOOTSTRAP_CASEFOLD_INDEX = _build_casefold_index(_BOOTSTRAP_SEED_CACHE)
    return _BOOTSTRAP_SEED_CACHE


def _resolve_seed_with_casefold(
    seed_map: Dict[str, StructuralRecencySeed],
    casefold_index: Dict[str, List[str]],
    symbol: str,
) -> Optional[StructuralRecencySeed]:
    direct = seed_map.get(symbol)
    if direct is not None:
        return direct
    folded = _symbol_casefold(symbol)
    matches = casefold_index.get(folded, [])
    if len(matches) == 1:
        return seed_map.get(matches[0])
    return None


def _resolve_prior_seed(symbol: str) -> Optional[StructuralRecencySeed]:
    clean_symbol = _clean_symbol(symbol)

    active_map = _load_active_snapshot_recency_seed_map()
    active_index = _ACTIVE_CASEFOLD_INDEX or {}
    active_seed = _resolve_seed_with_casefold(active_map, active_index, clean_symbol)
    if active_seed is not None:
        return active_seed

    bootstrap_map = _load_bootstrap_seed_map()
    bootstrap_index = _BOOTSTRAP_CASEFOLD_INDEX or {}
    return _resolve_seed_with_casefold(bootstrap_map, bootstrap_index, clean_symbol)


def build_structural_recency_payload(
    symbol: str,
    current_state: Dict[str, Any],
    history_available_steps: int,
    ts_gap_days_from_prev: float,
) -> Dict[str, Any]:
    clean_symbol = _clean_symbol(symbol)
    live_state = _state_from_live_state(current_state)
    prior_seed = _resolve_prior_seed(clean_symbol)
    current_seed = _advance_seed(
        symbol=clean_symbol,
        source="current_snapshot_build",
        source_timestamp_utc=None,
        source_timestamp_ms=None,
        prior_seed=prior_seed,
        current_state=live_state,
    )

    payload = {
        "structural_recency_schema_version": STRUCTURAL_RECENCY_SCHEMA_VERSION,
        "history_available_steps": int(max(0, history_available_steps)),
        "ts_gap_days_from_prev": float(ts_gap_days_from_prev),
        "steps_since_regime_change": int(current_seed.steps_since_regime_change),
        "steps_since_pattern_change": int(current_seed.steps_since_pattern_change),
        "steps_since_reversal_sign_flip": int(current_seed.steps_since_sign_flip_by_field.get("R_rev", -1)),
    }

    for field in TRACKED_SIGN_FIELDS:
        payload[f"{field}_steps_since_sign_flip"] = int(current_seed.steps_since_sign_flip_by_field.get(field, -1))

    return payload
