#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bundle_hash(repo_root: Path, rel_paths: Sequence[str]) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    missing: List[str] = []

    for rel in rel_paths:
        p = (repo_root / rel).resolve()
        if not p.exists() or not p.is_file():
            missing.append(rel)
            continue
        files.append(
            {
                "path": str(p),
                "relative_path": str(Path(rel)),
                "sha256": _sha256_file(p),
                "size_bytes": int(p.stat().st_size),
            }
        )

    files.sort(key=lambda x: str(x["relative_path"]))
    digest = _canonical_json_hash(files)
    return {
        "sha256": digest,
        "files": files,
        "missing_files": missing,
    }


def _parse_csv_list(raw: str) -> List[str]:
    out: List[str] = []
    for token in str(raw).split(","):
        t = token.strip()
        if len(t) <= 0:
            continue
        out.append(t)
    if len(out) <= 0:
        raise ValueError("empty_file_list")
    return out


def _extract_market_data_version(input_manifest: Dict[str, Any]) -> Dict[str, Any]:
    entries = input_manifest.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    snapshot_entry: Optional[Dict[str, Any]] = None
    for row in entries:
        if not isinstance(row, dict):
            continue
        if str(row.get("logical_name", "")).strip() == "snapshot":
            snapshot_entry = row
            break

    if snapshot_entry is None:
        return {
            "value": None,
            "status": "missing",
            "reason": "input_manifest_missing_snapshot_entry",
            "source": None,
        }

    sha = str(snapshot_entry.get("sha256", "")).strip()
    if len(sha) <= 0:
        return {
            "value": None,
            "status": "missing",
            "reason": "snapshot_entry_missing_sha256",
            "source": snapshot_entry,
        }

    return {
        "value": f"snapshot_sha256:{sha}",
        "status": "derived",
        "reason": "derived_from_input_manifest_snapshot_sha256",
        "source": snapshot_entry,
    }


def _extract_lookback_window_rules(export_script: Path) -> Dict[str, Any]:
    if not export_script.exists() or not export_script.is_file():
        return {
            "value": None,
            "status": "missing",
            "reason": f"export_script_not_found:{export_script}",
            "source": None,
        }

    text = export_script.read_text(encoding="utf-8")

    years = re.search(r"--years-history\"\s*,\s*type=int\s*,\s*default=(\d+)", text)
    learning = re.search(r"--learning-bars\"\s*,\s*type=int\s*,\s*default=(\d+)", text)
    min_bars = re.search(r"--min-bars\"\s*,\s*type=int\s*,\s*default=(\d+)", text)
    horizons = re.search(r"--horizons\"\s*,\s*type=int\s*,\s*nargs=\"\+\"\s*,\s*default=\[([^\]]+)\]", text)

    if years is None or learning is None or min_bars is None or horizons is None:
        return {
            "value": None,
            "status": "missing",
            "reason": "failed_to_parse_export_defaults",
            "source": str(export_script),
        }

    horizon_tokens = [t.strip() for t in horizons.group(1).split(",") if t.strip()]
    horizon_clean = ",".join(horizon_tokens)
    value = (
        f"years_history={years.group(1)};"
        f"learning_bars={learning.group(1)};"
        f"min_bars={min_bars.group(1)};"
        f"horizons={horizon_clean}"
    )
    return {
        "value": value,
        "status": "derived",
        "reason": "derived_from_rowtrace_export_argparse_defaults",
        "source": str(export_script),
    }


def _extract_horizons_from_rules(rules_value: Optional[str]) -> List[int]:
    if rules_value is None:
        return []
    m = re.search(r"horizons=([0-9,]+)", str(rules_value))
    if m is None:
        return []
    out: List[int] = []
    for tok in m.group(1).split(","):
        t = tok.strip()
        if len(t) <= 0:
            continue
        out.append(int(t))
    return out


def _extract_feature_config_hash(temporal_manifest: Dict[str, Any]) -> Dict[str, Any]:
    inputs = temporal_manifest.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
    design = temporal_manifest.get("design_contract", {})
    if not isinstance(design, dict):
        design = {}

    feature_config = {
        "horizons": inputs.get("horizons"),
        "state_fields": inputs.get("state_fields"),
        "lookback": inputs.get("lookback"),
        "rolling_windows": inputs.get("rolling_windows"),
        "use_hardening_behavior": inputs.get("use_hardening_behavior"),
        "design_contract": design,
    }

    return {
        "value": f"sha256:{_canonical_json_hash(feature_config)}",
        "status": "derived",
        "reason": "derived_from_temporal_policy_dataset_manifest_inputs_and_design_contract",
        "source": feature_config,
    }


def _extract_raw_data_range(
    rowtrace_manifest: Dict[str, Any],
    temporal_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    rowtrace_ds = rowtrace_manifest.get("dataset_manifest", {})
    if not isinstance(rowtrace_ds, dict):
        rowtrace_ds = {}

    temporal_health = temporal_manifest.get("data_health", {})
    if not isinstance(temporal_health, dict):
        temporal_health = {}

    refs: List[Dict[str, Any]] = []

    if rowtrace_ds:
        refs.append(
            {
                "source": "rowtrace_merged_historical_manifest.dataset_manifest",
                "ts_min_iso_utc": rowtrace_ds.get("ts_min_iso_utc"),
                "ts_max_iso_utc": rowtrace_ds.get("ts_max_iso_utc"),
                "ts_min_ms": rowtrace_ds.get("ts_min_ms"),
                "ts_max_ms": rowtrace_ds.get("ts_max_ms"),
            }
        )

    if temporal_health:
        refs.append(
            {
                "source": "temporal_policy_dataset_manifest.data_health",
                "ts_min_iso_utc": temporal_health.get("ts_min_iso_utc"),
                "ts_max_iso_utc": temporal_health.get("ts_max_iso_utc"),
                "ts_min_ms": temporal_health.get("ts_min_ms"),
                "ts_max_ms": temporal_health.get("ts_max_ms"),
            }
        )

    mins: List[Tuple[int, str]] = []
    maxs: List[Tuple[int, str]] = []
    for ref in refs:
        min_ms = ref.get("ts_min_ms")
        max_ms = ref.get("ts_max_ms")
        if isinstance(min_ms, int):
            mins.append((min_ms, str(ref.get("ts_min_iso_utc"))))
        if isinstance(max_ms, int):
            maxs.append((max_ms, str(ref.get("ts_max_iso_utc"))))

    if len(mins) <= 0 or len(maxs) <= 0:
        return {
            "status": "missing",
            "reason": "no_reference_date_range_found",
            "sources": refs,
            "value": None,
        }

    min_row = sorted(mins, key=lambda t: t[0])[0]
    max_row = sorted(maxs, key=lambda t: t[0])[-1]

    return {
        "status": "derived",
        "reason": "derived_from_current_rowtrace_and_temporal_dataset_manifests",
        "sources": refs,
        "value": {
            "start_ts_ms": int(min_row[0]),
            "end_ts_ms": int(max_row[0]),
            "start_ts_iso_utc": str(min_row[1]),
            "end_ts_iso_utc": str(max_row[1]),
        },
    }


def _extract_code_version(repo_root: Path, deploy_pointer_path: Path) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "code_commit_hash": None,
            "status": "missing",
            "reason": f"git_rev_parse_failed:{exc.__class__.__name__}",
            "source_zip_sha256": None,
            "source": None,
        }

    if proc.returncode == 0:
        head = proc.stdout.strip()
        if len(head) > 0:
            return {
                "code_commit_hash": head,
                "status": "exact",
                "reason": "git_head",
                "source_zip_sha256": None,
                "source": "git",
            }

    pointer = ""
    if deploy_pointer_path.exists() and deploy_pointer_path.is_file():
        pointer = deploy_pointer_path.read_text(encoding="utf-8").strip()

    deploy_dir: Optional[Path] = None
    if len(pointer) > 0:
        deploy_dir = (repo_root / pointer).resolve()
    if deploy_dir is None or not deploy_dir.exists() or not deploy_dir.is_dir():
        return {
            "code_commit_hash": None,
            "status": "missing",
            "reason": "git_unavailable_and_deploy_pointer_invalid",
            "source_zip_sha256": None,
            "source": pointer if len(pointer) > 0 else None,
        }

    source_sha_path = deploy_dir / "source-zip-sha.txt"
    if not source_sha_path.exists() or not source_sha_path.is_file():
        return {
            "code_commit_hash": None,
            "status": "missing",
            "reason": "git_unavailable_and_source_zip_sha_missing",
            "source_zip_sha256": None,
            "source": str(source_sha_path),
        }

    line = source_sha_path.read_text(encoding="utf-8").strip().splitlines()
    first = line[0].strip() if len(line) > 0 else ""
    sha = first.split()[0] if len(first) > 0 else ""
    if len(sha) != 64:
        return {
            "code_commit_hash": None,
            "status": "missing",
            "reason": "source_zip_sha_invalid",
            "source_zip_sha256": None,
            "source": str(source_sha_path),
        }

    return {
        "code_commit_hash": None,
        "status": "derived",
        "reason": "git_unavailable_using_deploy_source_zip_sha256",
        "source_zip_sha256": sha,
        "source": str(source_sha_path),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Freeze fresh research baseline manifest for contiguous temporal regeneration and TMA research."
        )
    )
    p.add_argument("--repo-root", default="/workspaces/Tao_Financial_Engine")
    p.add_argument(
        "--input-manifest",
        default="backups/lab/recommendation_lab/current_inputs/input-manifest.json",
    )
    p.add_argument(
        "--rowtrace-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "real_world_cleaned_universe_l5_row_trace_merged_historical_manifest_latest.json"
        ),
    )
    p.add_argument(
        "--temporal-dataset-manifest",
        default="backups/lab/recommendation_lab/current_inputs/temporal_policy_dataset_manifest_latest.json",
    )
    p.add_argument(
        "--deploy-pointer",
        default="backups/CURRENT_DEPLOY_EVIDENCE_POINTER.txt",
    )
    p.add_argument(
        "--export-script",
        default="real_world_cleaned_universe_l5_row_trace_export.py",
    )
    p.add_argument(
        "--kernel-files",
        default=(
            "uf_core/layer0.py,uf_core/layer1.py,uf_core/layer2.py,"
            "uf_core/layer3.py,uf_core/layer4.py,uf_core/uf_structural_engine.py"
        ),
    )
    p.add_argument(
        "--adapter-files",
        default=(
            "real_world_cleaned_universe_l5_row_trace_export.py,"
            "tfe_market_data_factory.py,tfe_market_data_service.py,"
            "unified_market_data_service.py,massive_universe_cache.py,policy_horizon_overrides.json"
        ),
    )
    p.add_argument(
        "--out-manifest",
        default=(
            "backups/lab/recommendation_lab/current_inputs/"
            "fresh_research_baseline_manifest_latest.json"
        ),
    )
    p.add_argument("--report-out", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(str(args.repo_root)).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise FileNotFoundError(f"repo_root_not_found:{repo_root}")

    input_manifest_path = (repo_root / str(args.input_manifest)).resolve()
    rowtrace_manifest_path = (repo_root / str(args.rowtrace_manifest)).resolve()
    temporal_manifest_path = (repo_root / str(args.temporal_dataset_manifest)).resolve()
    deploy_pointer_path = (repo_root / str(args.deploy_pointer)).resolve()
    export_script_path = (repo_root / str(args.export_script)).resolve()

    out_manifest = (repo_root / str(args.out_manifest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else out_manifest.with_name(f"fresh_research_baseline_manifest_{_utc_stamp()}.json")
    )

    required = [input_manifest_path, rowtrace_manifest_path, temporal_manifest_path]
    missing_required = [str(p) for p in required if not p.exists() or not p.is_file()]
    if len(missing_required) > 0:
        raise FileNotFoundError(f"required_manifest_missing:{','.join(missing_required)}")

    input_manifest = _read_json(input_manifest_path)
    rowtrace_manifest = _read_json(rowtrace_manifest_path)
    temporal_manifest = _read_json(temporal_manifest_path)

    market_data_version = _extract_market_data_version(input_manifest)
    lookback_rules = _extract_lookback_window_rules(export_script_path)
    feature_config_hash = _extract_feature_config_hash(temporal_manifest)
    raw_data_range = _extract_raw_data_range(rowtrace_manifest, temporal_manifest)
    code_version = _extract_code_version(repo_root=repo_root, deploy_pointer_path=deploy_pointer_path)

    kernel_files = _parse_csv_list(str(args.kernel_files))
    adapter_files = _parse_csv_list(str(args.adapter_files))

    kernel_bundle = _bundle_hash(repo_root=repo_root, rel_paths=kernel_files)
    adapter_bundle = _bundle_hash(repo_root=repo_root, rel_paths=adapter_files)

    kernel_version = {
        "value": f"kernel_bundle_sha256:{kernel_bundle['sha256']}",
        "status": "derived",
        "reason": "derived_from_canonical_kernel_file_bundle",
        "source": {
            "files": kernel_bundle["files"],
            "missing_files": kernel_bundle["missing_files"],
        },
    }

    adapter_config_hash = {
        "value": f"adapter_bundle_sha256:{adapter_bundle['sha256']}",
        "status": "derived",
        "reason": "derived_from_adapter_and_generation_config_file_bundle",
        "source": {
            "files": adapter_bundle["files"],
            "missing_files": adapter_bundle["missing_files"],
        },
    }

    horizons = _extract_horizons_from_rules(lookback_rules.get("value"))

    baseline = {
        "market_data_version": market_data_version,
        "kernel_version": kernel_version,
        "adapter_config_hash": adapter_config_hash,
        "lookback_window_rules": lookback_rules,
        "code_commit_hash": {
            "value": code_version.get("code_commit_hash"),
            "status": code_version.get("status"),
            "reason": code_version.get("reason"),
            "source": code_version.get("source"),
            "source_zip_sha256": code_version.get("source_zip_sha256"),
        },
        "feature_config_hash": feature_config_hash,
        "raw_data_date_range": raw_data_range,
        "horizons": {
            "value": horizons,
            "status": "derived" if len(horizons) > 0 else "missing",
            "reason": (
                "derived_from_lookback_window_rules"
                if len(horizons) > 0
                else "horizons_missing_in_lookback_window_rules"
            ),
        },
    }

    missing_fields: List[str] = []
    for key in [
        "market_data_version",
        "kernel_version",
        "adapter_config_hash",
        "lookback_window_rules",
        "code_commit_hash",
        "feature_config_hash",
        "raw_data_date_range",
        "horizons",
    ]:
        status = str(baseline[key].get("status", "missing"))
        value = baseline[key].get("value")
        if status == "missing" or value is None:
            missing_fields.append(key)

    status = "pass" if len(missing_fields) == 0 else "partial"

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "freeze_research_baseline_manifest",
        "status": status,
        "inputs": {
            "input_manifest": str(input_manifest_path),
            "rowtrace_manifest": str(rowtrace_manifest_path),
            "temporal_dataset_manifest": str(temporal_manifest_path),
            "deploy_pointer": str(deploy_pointer_path),
            "export_script": str(export_script_path),
            "kernel_files": kernel_files,
            "adapter_files": adapter_files,
        },
        "baseline": baseline,
        "missing_fields": missing_fields,
        "decision_rule": (
            "Use this manifest as the canonical Track B research freeze. "
            "If code_commit_hash is missing, source_zip_sha256 is the reproducibility fallback."
        ),
        "outputs": {
            "manifest_latest": str(out_manifest),
            "manifest_timestamped": str(report_out),
        },
    }

    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    out_manifest.write_text(payload, encoding="utf-8")
    report_out.write_text(payload, encoding="utf-8")

    print(str(report_out))
    print(str(out_manifest))
    print(
        json.dumps(
            {
                "status": status,
                "missing_fields": missing_fields,
            },
            indent=2,
        )
    )

    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
