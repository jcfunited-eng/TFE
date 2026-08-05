#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

FIELDS: Tuple[str, ...] = (
    "market_data_version",
    "kernel_version",
    "adapter_config_hash",
    "lookback_window_rules",
)

EXACT_KEYS: Dict[str, Set[str]] = {
    "market_data_version": {"market_data_version", "source_market_data_version"},
    "kernel_version": {"kernel_version"},
    "adapter_config_hash": {"adapter_config_hash", "adapter_runtime_config_hash"},
    "lookback_window_rules": {"lookback_window_rules"},
}

INFERRED_KEYS: Dict[str, Set[str]] = {
    "market_data_version": {"market_data_provider", "provider", "data_source", "market_data_source"},
    "kernel_version": {"kernel", "kernel_name", "uf_kernel", "kernel_build"},
    "adapter_config_hash": {"adapter_hash", "config_hash", "policy_sha256", "sha256"},
    "lookback_window_rules": {
        "lookback",
        "lookback_days",
        "lookback_window",
        "years_history",
        "learning_bars",
        "min_bars",
        "horizons",
    },
}

PASS1_ROOTS: Tuple[str, ...] = (
    "backups/lab/recommendation_lab/current_inputs/real_world_cleaned_universe_l5_row_trace_merged_historical_manifest_latest.json",
    "backups/lab/recommendation_lab/current_inputs/temporal_policy_dataset_manifest_latest.json",
    "backups/lab/recommendation_lab/current_inputs/rowtrace_backfill_merge_manifest_latest.json",
    "backups/lab/recommendation_lab/current_inputs/rowtrace_backfill_from_snapshots_manifest_latest.json",
    "backups/lab/recommendation_lab/current_inputs/input-manifest.json",
    "backups/lab/recommendation_lab/current_inputs/pscf_policy_runtime.json",
    "recommendation_policy_promotion_contract.json",
)

PASS2_FALLBACK: Tuple[str, ...] = (
    "backups/lab/recommendation_lab/current_inputs/rowtrace_backfill_regenerated_raw_manifest_latest.json",
    "backups/lab/recommendation_lab/current_inputs/rowtrace_backfill_plan_latest.json",
    "backups/lab/recommendation_lab/current_inputs/temporal_dataset_audit_latest.json",
    "backups/lab/recommendation_lab/current_inputs/temporal_walkforward_eval_latest.json",
    "tools/regenerate_historical_rowtrace_from_raw.py",
    "real_world_cleaned_universe_l5_row_trace_export.py",
)

PASS2_REFERENCE_BASENAMES: Set[str] = {
    "rowtrace_backfill_plan_latest.json",
    "rowtrace_backfill_regenerated_raw_manifest_latest.json",
    "temporal_dataset_audit_latest.json",
    "temporal_walkforward_eval_latest.json",
    "temporal_timestamp_gap_report_latest.json",
}

DEFAULT_MAX_FILE_BYTES = 12 * 1024 * 1024


@dataclass(frozen=True)
class Candidate:
    field: str
    value: str
    confidence: str
    source_path: str
    source_locator: str
    pass_name: str
    lineage_roots: Tuple[str, ...]


@dataclass(frozen=True)
class ScanRecord:
    path: str
    pass_name: str
    role: str
    status: str
    size_bytes: Optional[int]
    reason: Optional[str]
    lineage_roots: Tuple[str, ...]


class JsonCache:
    def __init__(self, max_file_bytes: int):
        self.max_file_bytes = int(max_file_bytes)
        self._cache: Dict[str, Tuple[Optional[Any], str, Optional[int], Optional[str]]] = {}

    def read_json(self, path: Path) -> Tuple[Optional[Any], str, Optional[int], Optional[str]]:
        key = str(path.resolve())
        if key in self._cache:
            return self._cache[key]

        if not path.exists() or not path.is_file():
            out = (None, "skip", None, "missing_file")
            self._cache[key] = out
            return out

        size = path.stat().st_size
        if size > self.max_file_bytes:
            out = (None, "skip", int(size), f"file_too_large>{self.max_file_bytes}")
            self._cache[key] = out
            return out

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            out = (None, "skip", int(size), f"read_error:{exc.__class__.__name__}")
            self._cache[key] = out
            return out

        try:
            payload = json.loads(text)
        except Exception as exc:
            out = (None, "skip", int(size), f"json_parse_error:{exc.__class__.__name__}")
            self._cache[key] = out
            return out

        out = (payload, "scanned", int(size), None)
        self._cache[key] = out
        return out


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _norm_key(key: str) -> str:
    return str(key).strip().lower()


def _canonical_scalar(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        txt = value.strip()
        return txt if len(txt) > 0 else None
    return None


def _iter_json_nodes(obj: Any, path: str = "$") -> Iterable[Tuple[str, str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            k = str(key)
            child = f"{path}.{k}"
            yield k, child, value
            yield from _iter_json_nodes(value, child)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            child = f"{path}[{idx}]"
            yield from _iter_json_nodes(value, child)


def _resolve_candidate_path(raw: str, *, base_file: Path, repo_root: Path) -> Optional[Path]:
    txt = str(raw).strip()
    if len(txt) <= 0:
        return None
    if "\n" in txt or "\r" in txt:
        return None
    if txt.startswith("http://") or txt.startswith("https://"):
        return None

    path_obj: Path
    if txt.startswith("/"):
        path_obj = Path(txt)
    elif txt.startswith("./"):
        rel = txt[2:]
        cand_repo = (repo_root / rel).resolve()
        cand_base = (base_file.parent / txt).resolve()
        path_obj = cand_repo if cand_repo.exists() else cand_base
    else:
        path_obj = (base_file.parent / txt).resolve()

    try:
        resolved = path_obj.resolve()
    except Exception:
        return None

    if not resolved.exists() or not resolved.is_file():
        return None

    try:
        resolved.relative_to(repo_root)
    except Exception:
        return None

    return resolved


def _is_manifest_like(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() == ".json" and ("manifest" in name or "contract" in name)


def _extract_manifest_references(payload: Any, *, base_file: Path, repo_root: Path) -> List[Path]:
    refs: List[Path] = []
    seen: Set[str] = set()

    for _key, _node_path, value in _iter_json_nodes(payload):
        if not isinstance(value, str):
            continue
        if ".json" not in value.lower():
            continue

        ref = _resolve_candidate_path(value, base_file=base_file, repo_root=repo_root)
        if ref is None:
            continue
        if not _is_manifest_like(ref):
            continue

        key = str(ref)
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref)

    refs.sort(key=lambda p: str(p))
    return refs


def _extract_json_path_references(payload: Any, *, base_file: Path, repo_root: Path) -> List[Path]:
    refs: List[Path] = []
    seen: Set[str] = set()

    for _key, _node_path, value in _iter_json_nodes(payload):
        if not isinstance(value, str):
            continue
        if ".json" not in value.lower():
            continue

        ref = _resolve_candidate_path(value, base_file=base_file, repo_root=repo_root)
        if ref is None:
            continue

        key = str(ref)
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref)

    refs.sort(key=lambda p: str(p))
    return refs


def _extract_compound_lookback_rule(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None

    parts: List[str] = []
    for key in ("years_history", "learning_bars", "min_bars", "horizons"):
        if key not in value:
            continue
        raw = value.get(key)
        if isinstance(raw, list):
            joined = ",".join(str(x) for x in raw)
            if len(joined) > 0:
                parts.append(f"{key}={joined}")
        else:
            scalar = _canonical_scalar(raw)
            if scalar is not None:
                parts.append(f"{key}={scalar}")

    if len(parts) <= 0:
        return None
    return ";".join(parts)


def _extract_candidates_from_json(
    *,
    payload: Any,
    source_path: Path,
    pass_name: str,
    lineage_roots: Sequence[str],
    include_inferred: bool,
    exact_eligible: bool,
) -> List[Candidate]:
    out: List[Candidate] = []

    for key, node_path, value in _iter_json_nodes(payload):
        key_norm = _norm_key(key)
        scalar = _canonical_scalar(value)

        for field in FIELDS:
            if key_norm in EXACT_KEYS[field] and scalar is not None:
                confidence = "exact" if exact_eligible else "inferred"
                out.append(
                    Candidate(
                        field=field,
                        value=scalar,
                        confidence=confidence,
                        source_path=str(source_path),
                        source_locator=node_path,
                        pass_name=pass_name,
                        lineage_roots=tuple(sorted(set(lineage_roots))),
                    )
                )
            elif include_inferred and key_norm in INFERRED_KEYS[field] and scalar is not None:
                out.append(
                    Candidate(
                        field=field,
                        value=scalar,
                        confidence="inferred",
                        source_path=str(source_path),
                        source_locator=node_path,
                        pass_name=pass_name,
                        lineage_roots=tuple(sorted(set(lineage_roots))),
                    )
                )

        if include_inferred:
            compound = _extract_compound_lookback_rule(value)
            if compound is not None:
                out.append(
                    Candidate(
                        field="lookback_window_rules",
                        value=compound,
                        confidence="inferred",
                        source_path=str(source_path),
                        source_locator=f"{node_path} (compound_lookback_rule)",
                        pass_name=pass_name,
                        lineage_roots=tuple(sorted(set(lineage_roots))),
                    )
                )

    deduped: List[Candidate] = []
    seen: Set[Tuple[str, str, str, str, str, str]] = set()
    for c in out:
        sig = (c.field, c.value, c.confidence, c.source_path, c.source_locator, c.pass_name)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(c)

    return deduped


def _extract_candidates_from_text(
    *,
    text: str,
    source_path: Path,
    pass_name: str,
    lineage_roots: Sequence[str],
) -> List[Candidate]:
    out: List[Candidate] = []

    patterns: Dict[str, List[Tuple[str, str]]] = {
        "market_data_version": [
            ("exact", r"\bmarket[_-]?data[_-]?version\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
            ("exact", r"\bsource[_-]?market[_-]?data[_-]?version\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
        ],
        "kernel_version": [
            ("exact", r"\bkernel[_-]?version\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
        ],
        "adapter_config_hash": [
            ("exact", r"\badapter[_-]?config[_-]?hash\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
            ("exact", r"\badapter[_-]?runtime[_-]?config[_-]?hash\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
            ("inferred", r"\bpolicy[_-]?sha256\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
        ],
        "lookback_window_rules": [
            ("exact", r"\blookback[_-]?window[_-]?rules\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
            ("inferred", r"\blookback\b\s*[:=]\s*[\"']?([^\"'\n\r]+)"),
        ],
    }

    for field, pat_list in patterns.items():
        for confidence, pattern in pat_list:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                val = match.group(1).strip()
                if len(val) <= 0:
                    continue
                out.append(
                    Candidate(
                        field=field,
                        value=val,
                        confidence=confidence,
                        source_path=str(source_path),
                        source_locator=f"regex:{pattern}",
                        pass_name=pass_name,
                        lineage_roots=tuple(sorted(set(lineage_roots))),
                    )
                )

    years = re.search(r"--years-history\",\s*type=int,\s*default=(\d+)", text)
    learning = re.search(r"--learning-bars\",\s*type=int,\s*default=(\d+)", text)
    min_bars = re.search(r"--min-bars\",\s*type=int,\s*default=(\d+)", text)
    horizons = re.search(r"--horizons\",\s*default=\"([0-9,]+)\"", text)

    parts: List[str] = []
    if years is not None:
        parts.append(f"years_history={years.group(1)}")
    if learning is not None:
        parts.append(f"learning_bars={learning.group(1)}")
    if min_bars is not None:
        parts.append(f"min_bars={min_bars.group(1)}")
    if horizons is not None:
        parts.append(f"horizons={horizons.group(1)}")

    if len(parts) > 0:
        out.append(
            Candidate(
                field="lookback_window_rules",
                value=";".join(parts),
                confidence="inferred",
                source_path=str(source_path),
                source_locator="regex:argparse_defaults",
                pass_name=pass_name,
                lineage_roots=tuple(sorted(set(lineage_roots))),
            )
        )

    deduped: List[Candidate] = []
    seen: Set[Tuple[str, str, str, str, str, str]] = set()
    for c in out:
        sig = (c.field, c.value, c.confidence, c.source_path, c.source_locator, c.pass_name)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(c)

    return deduped


def _resolve_field(field: str, candidates: Sequence[Candidate], include_inferred: bool) -> Dict[str, Any]:
    scoped = [c for c in candidates if c.field == field and len(c.value.strip()) > 0]

    exact = [c for c in scoped if c.confidence == "exact"]
    inferred = [c for c in scoped if c.confidence == "inferred"]

    exact_values = sorted(set(c.value for c in exact))
    inferred_values = sorted(set(c.value for c in inferred))

    status = "missing"
    confidence = "missing"
    candidate_value: Optional[str] = None

    if len(exact_values) == 1:
        status = "resolved"
        confidence = "exact"
        candidate_value = exact_values[0]
    elif len(exact_values) > 1:
        status = "ambiguous"
        confidence = "missing"
    elif include_inferred and len(inferred_values) == 1:
        status = "inferred_only"
        confidence = "inferred"
        candidate_value = inferred_values[0]
    elif include_inferred and len(inferred_values) > 1:
        status = "ambiguous"
        confidence = "missing"

    selected_sources: List[Dict[str, Any]] = []
    selected_lineage_roots: List[str] = []
    pool: Sequence[Candidate] = []
    if candidate_value is not None and confidence == "exact":
        pool = exact
    elif candidate_value is not None and confidence == "inferred":
        pool = inferred

    if len(pool) > 0 and candidate_value is not None:
        roots: Set[str] = set()
        for c in pool:
            if c.value != candidate_value:
                continue
            selected_sources.append(
                {
                    "path": c.source_path,
                    "locator": c.source_locator,
                    "confidence": c.confidence,
                    "pass": c.pass_name,
                    "lineage_roots": list(c.lineage_roots),
                }
            )
            roots.update(c.lineage_roots)
        selected_lineage_roots = sorted(roots)

    conflicts: List[Dict[str, Any]] = []
    if len(exact_values) > 1:
        for value in exact_values:
            conflicts.append(
                {
                    "value": value,
                    "confidence": "exact",
                    "sources": [
                        {
                            "path": c.source_path,
                            "locator": c.source_locator,
                            "pass": c.pass_name,
                            "lineage_roots": list(c.lineage_roots),
                        }
                        for c in exact
                        if c.value == value
                    ],
                }
            )
    elif len(exact_values) == 0 and include_inferred and len(inferred_values) > 1:
        for value in inferred_values:
            conflicts.append(
                {
                    "value": value,
                    "confidence": "inferred",
                    "sources": [
                        {
                            "path": c.source_path,
                            "locator": c.source_locator,
                            "pass": c.pass_name,
                            "lineage_roots": list(c.lineage_roots),
                        }
                        for c in inferred
                        if c.value == value
                    ],
                }
            )

    return {
        "field": field,
        "status": status,
        "candidate_value": candidate_value,
        "confidence": confidence,
        "exact_values": exact_values,
        "inferred_values": inferred_values,
        "selected_sources": selected_sources,
        "selected_lineage_roots": selected_lineage_roots,
        "ambiguity": status == "ambiguous",
        "conflicts": conflicts,
    }


def _build_pass1_lineage(
    *,
    repo_root: Path,
    root_files: Sequence[Path],
    cache: JsonCache,
) -> Tuple[Dict[str, Set[str]], Dict[str, List[str]], List[ScanRecord]]:
    lineage_roots_by_file: Dict[str, Set[str]] = {}
    refs_cache: Dict[str, List[str]] = {}
    scan_records: List[ScanRecord] = []

    def load_refs(path: Path, pass_name: str, role: str, lineage_roots: Sequence[str]) -> List[Path]:
        payload, status, size, reason = cache.read_json(path)
        scan_records.append(
            ScanRecord(
                path=str(path),
                pass_name=pass_name,
                role=role,
                status=status,
                size_bytes=size,
                reason=reason,
                lineage_roots=tuple(sorted(set(lineage_roots))),
            )
        )
        if payload is None:
            return []
        return _extract_manifest_references(payload, base_file=path, repo_root=repo_root)

    for root in root_files:
        root_key = str(root)
        lineage_roots_by_file.setdefault(root_key, set()).add(root_key)

        stack: List[Path] = [root]
        visited: Set[str] = set()
        while len(stack) > 0:
            cur = stack.pop()
            cur_key = str(cur)
            if cur_key in visited:
                continue
            visited.add(cur_key)

            lineage_roots_by_file.setdefault(cur_key, set()).add(root_key)

            if cur_key not in refs_cache:
                refs = load_refs(cur, pass_name="pass1", role="lineage_manifest", lineage_roots=[root_key])
                refs_cache[cur_key] = [str(x) for x in refs]
            else:
                refs = [Path(x) for x in refs_cache[cur_key]]

            for ref in refs:
                ref_key = str(ref)
                lineage_roots_by_file.setdefault(ref_key, set()).add(root_key)
                if ref_key not in visited:
                    stack.append(ref)

    return lineage_roots_by_file, refs_cache, scan_records


def _resolve_paths(repo_root: Path, rel_paths: Sequence[str]) -> List[Path]:
    out: List[Path] = []
    seen: Set[str] = set()
    for rel in rel_paths:
        p = (repo_root / rel).resolve()
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.exists() and p.is_file():
            out.append(p)
    out.sort(key=lambda x: str(x))
    return out


def _load_text_if_small(path: Path, max_file_bytes: int) -> Tuple[Optional[str], str, Optional[int], Optional[str]]:
    if not path.exists() or not path.is_file():
        return None, "skip", None, "missing_file"

    size = path.stat().st_size
    if size > int(max_file_bytes):
        return None, "skip", int(size), f"file_too_large>{max_file_bytes}"

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return None, "skip", int(size), f"read_error:{exc.__class__.__name__}"

    return text, "scanned", int(size), None


def _build_pass2_files(
    *,
    repo_root: Path,
    pass1_roots: Sequence[Path],
    cache: JsonCache,
) -> List[Path]:
    files: List[Path] = []
    seen: Set[str] = set()

    for p in _resolve_paths(repo_root, PASS2_FALLBACK):
        key = str(p)
        if key not in seen:
            seen.add(key)
            files.append(p)

    for root in pass1_roots:
        payload, status, _size, _reason = cache.read_json(root)
        if status != "scanned" or payload is None:
            continue
        for ref in _extract_json_path_references(payload, base_file=root, repo_root=repo_root):
            if ref.name not in PASS2_REFERENCE_BASENAMES:
                continue
            key = str(ref)
            if key in seen:
                continue
            seen.add(key)
            files.append(ref)

    files.sort(key=lambda x: str(x))
    return files


def _field_resolution(
    *,
    candidates: Sequence[Candidate],
    include_inferred: bool,
) -> Dict[str, Dict[str, Any]]:
    return {field: _resolve_field(field, candidates, include_inferred=include_inferred) for field in FIELDS}


def _lineage_intersection(field_results: Dict[str, Dict[str, Any]]) -> List[str]:
    sets: List[Set[str]] = []
    for field in FIELDS:
        row = field_results[field]
        if row.get("confidence") != "exact":
            return []
        roots = set(str(x) for x in row.get("selected_lineage_roots", []))
        if len(roots) <= 0:
            return []
        sets.append(roots)

    if len(sets) <= 0:
        return []

    intersection = set(sets[0])
    for s in sets[1:]:
        intersection.intersection_update(s)
    return sorted(intersection)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Discover locked provenance tuple using bounded artifact lineage trace. "
            "Fail-stop on ambiguity, missing, or inferred-only outcomes."
        )
    )
    p.add_argument("--repo-root", default="/workspaces/Tao_Financial_Engine")
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "provenance_candidate_report_latest.json"
        ),
    )
    p.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(str(args.repo_root)).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise FileNotFoundError(f"repo_root_not_found:{repo_root}")

    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"provenance_candidate_report_{_utc_stamp()}.json")
    )

    max_file_bytes = int(args.max_file_bytes)
    cache = JsonCache(max_file_bytes=max_file_bytes)

    pass1_root_files = _resolve_paths(repo_root, PASS1_ROOTS)

    lineage_roots_by_file, refs_cache, pass1_scan_log = _build_pass1_lineage(
        repo_root=repo_root,
        root_files=pass1_root_files,
        cache=cache,
    )

    pass1_files = sorted(Path(p) for p in lineage_roots_by_file.keys())

    pass1_candidates: List[Candidate] = []
    for path in pass1_files:
        payload, status, _size, _reason = cache.read_json(path)
        if status != "scanned" or payload is None:
            continue
        roots = sorted(lineage_roots_by_file.get(str(path), set()))
        pass1_candidates.extend(
            _extract_candidates_from_json(
                payload=payload,
                source_path=path,
                pass_name="pass1",
                lineage_roots=roots,
                include_inferred=False,
                exact_eligible=True,
            )
        )

    pass1_field_results = _field_resolution(candidates=pass1_candidates, include_inferred=False)
    pass1_ambiguity = [f for f in FIELDS if bool(pass1_field_results[f].get("ambiguity", False))]
    pass1_missing = [f for f in FIELDS if str(pass1_field_results[f].get("confidence")) != "exact"]
    pass1_common_roots = _lineage_intersection(pass1_field_results)
    pass1_lineage_consistent = len(pass1_common_roots) > 0

    pass1_canary_safe = len(pass1_ambiguity) == 0 and len(pass1_missing) == 0 and pass1_lineage_consistent

    pass2_scan_log: List[ScanRecord] = []
    pass2_candidates: List[Candidate] = []
    pass2_files: List[Path] = []

    final_candidates: List[Candidate]
    final_field_results: Dict[str, Dict[str, Any]]
    lineage_consistent = pass1_lineage_consistent
    shared_lineage_roots = pass1_common_roots

    if pass1_canary_safe:
        final_candidates = list(pass1_candidates)
        final_field_results = dict(pass1_field_results)
        canary_safe = True
        discovery_pass = "pass1_exact_only"
    else:
        pass2_files = _build_pass2_files(repo_root=repo_root, pass1_roots=pass1_root_files, cache=cache)

        for path in pass2_files:
            lineage_roots = sorted(lineage_roots_by_file.get(str(path), set()))
            exact_eligible = str(path) in lineage_roots_by_file

            if path.suffix.lower() == ".json":
                payload, status, size, reason = cache.read_json(path)
                pass2_scan_log.append(
                    ScanRecord(
                        path=str(path),
                        pass_name="pass2",
                        role="fallback_json",
                        status=status,
                        size_bytes=size,
                        reason=reason,
                        lineage_roots=tuple(lineage_roots),
                    )
                )
                if status == "scanned" and payload is not None:
                    pass2_candidates.extend(
                        _extract_candidates_from_json(
                            payload=payload,
                            source_path=path,
                            pass_name="pass2",
                            lineage_roots=lineage_roots,
                            include_inferred=True,
                            exact_eligible=exact_eligible,
                        )
                    )
                continue

            text, status, size, reason = _load_text_if_small(path, max_file_bytes=max_file_bytes)
            pass2_scan_log.append(
                ScanRecord(
                    path=str(path),
                    pass_name="pass2",
                    role="fallback_text",
                    status=status,
                    size_bytes=size,
                    reason=reason,
                    lineage_roots=tuple(lineage_roots),
                )
            )
            if status == "scanned" and text is not None:
                pass2_candidates.extend(
                    _extract_candidates_from_text(
                        text=text,
                        source_path=path,
                        pass_name="pass2",
                        lineage_roots=lineage_roots,
                    )
                )

        final_candidates = [*pass1_candidates, *pass2_candidates]
        final_field_results = _field_resolution(candidates=final_candidates, include_inferred=True)
        canary_safe = False
        discovery_pass = "pass1_plus_targeted_pass2"

    ambiguity_fields = [f for f in FIELDS if bool(final_field_results[f].get("ambiguity", False))]
    inferred_fields = [
        f
        for f in FIELDS
        if str(final_field_results[f].get("confidence")) == "inferred"
    ]
    missing_fields = [
        f
        for f in FIELDS
        if str(final_field_results[f].get("confidence")) == "missing"
    ]
    exact_fields = [
        f
        for f in FIELDS
        if str(final_field_results[f].get("confidence")) == "exact"
    ]

    if canary_safe:
        blocking_fields: List[str] = []
        reason_for_not_canary_safe: Optional[str] = None
        stop_required = False
        recommendation_status = "canary-safe"
    else:
        blocking_fields = sorted(set([*ambiguity_fields, *inferred_fields, *missing_fields]))
        if len(ambiguity_fields) > 0:
            reason_for_not_canary_safe = "ambiguity_detected"
        elif len(missing_fields) > 0:
            reason_for_not_canary_safe = "missing_provenance_fields"
        elif len(inferred_fields) > 0:
            reason_for_not_canary_safe = "inferred_only_provenance_fields"
        elif not lineage_consistent:
            reason_for_not_canary_safe = "lineage_inconsistency"
        else:
            reason_for_not_canary_safe = "pass1_exact_lineage_resolution_not_achieved"
        stop_required = True
        recommendation_status = "not-canary-safe"

    conflict_list: List[Dict[str, Any]] = []
    for field in FIELDS:
        for conflict in final_field_results[field].get("conflicts", []):
            row = dict(conflict)
            row["field"] = field
            conflict_list.append(row)

    canary_command_if_safe: Optional[str] = None
    if canary_safe:
        canary_command_if_safe = (
            "python3 tools/regenerate_historical_rowtrace_from_raw.py --execute "
            "--approval-note \"<approved>\" "
            f"--market-data-version \"{final_field_results['market_data_version']['candidate_value']}\" "
            f"--kernel-version \"{final_field_results['kernel_version']['candidate_value']}\" "
            f"--adapter-config-hash \"{final_field_results['adapter_config_hash']['candidate_value']}\" "
            f"--lookback-window-rules \"{final_field_results['lookback_window_rules']['candidate_value']}\" "
            "--years-history 5 --learning-bars 252 --min-bars 120 --horizons 5,20,60"
        )

    scanned_file_list = [
        {
            "path": r.path,
            "pass": r.pass_name,
            "role": r.role,
            "status": r.status,
            "size_bytes": r.size_bytes,
            "reason": r.reason,
            "lineage_roots": list(r.lineage_roots),
        }
        for r in [*pass1_scan_log, *pass2_scan_log]
    ]

    lineage_root_files = [str(p) for p in pass1_root_files]
    pass1_lineage_files = [str(p) for p in pass1_files]
    pass2_files_list = [str(p) for p in pass2_files]

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "discover_locked_provenance",
        "control_rule": "bounded_artifact_lineage_trace_with_targeted_fallback",
        "inputs": {
            "repo_root": str(repo_root),
            "max_file_bytes": max_file_bytes,
            "pass1_roots_requested": list(PASS1_ROOTS),
            "pass2_fallback_requested": list(PASS2_FALLBACK),
            "pass2_reference_basenames": sorted(PASS2_REFERENCE_BASENAMES),
        },
        "lineage_root_files": lineage_root_files,
        "lineage_files_pass1": pass1_lineage_files,
        "lineage_manifest_references": refs_cache,
        "pass2_files": pass2_files_list,
        "scanned_file_list": scanned_file_list,
        "field_results": final_field_results,
        "conflict_list": conflict_list,
        "exact_fields": exact_fields,
        "inferred_fields": inferred_fields,
        "ambiguity_fields": ambiguity_fields,
        "missing_fields": missing_fields,
        "blocking_fields": blocking_fields,
        "reason_for_not_canary_safe": reason_for_not_canary_safe,
        "shared_lineage_roots_if_exact": shared_lineage_roots,
        "recommendation": {
            "status": recommendation_status,
            "canary_safe": canary_safe,
            "stop_required": stop_required,
            "discovery_pass": discovery_pass,
            "strict_fail_stop_rules": {
                "ambiguity": "stop_required=true",
                "missing": "stop_required=true",
                "inferred_only": "stop_required=true",
            },
        },
        "canary_command_if_safe": canary_command_if_safe,
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    report_out.write_text(payload, encoding="utf-8")
    report_latest.write_text(payload, encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "status": recommendation_status,
                "canary_safe": canary_safe,
                "stop_required": stop_required,
                "blocking_fields": blocking_fields,
                "reason_for_not_canary_safe": reason_for_not_canary_safe,
            },
            indent=2,
        )
    )

    return 0 if canary_safe else 2


if __name__ == "__main__":
    raise SystemExit(main())
