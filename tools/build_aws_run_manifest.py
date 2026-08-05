#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_horizons(raw: str) -> List[int]:
    out: List[int] = []
    for token in str(raw).split(","):
        tok = token.strip()
        if not tok:
            continue
        out.append(int(tok))
    if len(out) <= 0:
        raise ValueError("empty_horizons")
    return out


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_json_object:{path}")
    return payload


def _metadata_get(path: str, token: Optional[str], timeout: float = 1.5) -> Optional[str]:
    url = f"http://169.254.169.254/latest/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    if token:
        req.add_header("X-aws-ec2-metadata-token", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return None


def _metadata_token(timeout: float = 1.5) -> Optional[str]:
    url = "http://169.254.169.254/latest/api/token"
    req = urllib.request.Request(url, method="PUT")
    req.add_header("X-aws-ec2-metadata-token-ttl-seconds", "21600")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return None


def _aws_instance_identity() -> Dict[str, Any]:
    token = _metadata_token()
    doc_raw = _metadata_get("dynamic/instance-identity/document", token)
    if doc_raw is None:
        return {
            "instance_id": None,
            "instance_type": None,
            "region": None,
            "availability_zone": None,
        }
    try:
        doc = json.loads(doc_raw)
    except Exception:
        return {
            "instance_id": None,
            "instance_type": None,
            "region": None,
            "availability_zone": None,
        }

    if not isinstance(doc, dict):
        return {
            "instance_id": None,
            "instance_type": None,
            "region": None,
            "availability_zone": None,
        }

    return {
        "instance_id": doc.get("instanceId"),
        "instance_type": doc.get("instanceType"),
        "region": doc.get("region"),
        "availability_zone": doc.get("availabilityZone"),
    }


def _memory_gb() -> Optional[float]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith("MemTotal:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            kb = float(parts[1])
        except Exception:
            return None
        return round(kb / (1024.0 * 1024.0), 3)
    return None


def _mounted_device(mount_path: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["findmnt", "-n", "-o", "SOURCE", "--target", str(mount_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    src = str(proc.stdout or "").strip()
    return src if src else None


def _filesystem_type(mount_path: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["findmnt", "-n", "-o", "FSTYPE", "--target", str(mount_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    fstype = str(proc.stdout or "").strip()
    return fstype if fstype else None


def _attached_volumes(instance_id: Optional[str], region: Optional[str]) -> Dict[str, Any]:
    if not instance_id or not region:
        return {
            "selected": {
                "volume_id": None,
                "volume_type": None,
                "size_gb": None,
            },
            "all": [],
            "source": "metadata_missing",
        }

    if shutil.which("aws") is None:
        return {
            "selected": {
                "volume_id": None,
                "volume_type": None,
                "size_gb": None,
            },
            "all": [],
            "source": "aws_cli_missing",
        }

    try:
        proc = subprocess.run(
            [
                "aws",
                "ec2",
                "describe-volumes",
                "--region",
                str(region),
                "--filters",
                f"Name=attachment.instance-id,Values={instance_id}",
                "--output",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return {
            "selected": {
                "volume_id": None,
                "volume_type": None,
                "size_gb": None,
            },
            "all": [],
            "source": "aws_cli_exec_failed",
        }

    if proc.returncode != 0:
        return {
            "selected": {
                "volume_id": None,
                "volume_type": None,
                "size_gb": None,
            },
            "all": [],
            "source": "aws_cli_describe_volumes_failed",
            "stderr": str(proc.stderr or "")[-5000:],
        }

    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return {
            "selected": {
                "volume_id": None,
                "volume_type": None,
                "size_gb": None,
            },
            "all": [],
            "source": "aws_cli_json_parse_failed",
        }

    volumes = payload.get("Volumes") if isinstance(payload, dict) else None
    if not isinstance(volumes, list):
        volumes = []

    flat: List[Dict[str, Any]] = []
    for vol in volumes:
        if not isinstance(vol, dict):
            continue
        attachments = vol.get("Attachments") if isinstance(vol.get("Attachments"), list) else []
        attachment = attachments[0] if attachments else {}
        flat.append(
            {
                "volume_id": vol.get("VolumeId"),
                "volume_type": vol.get("VolumeType"),
                "size_gb": vol.get("Size"),
                "device": attachment.get("Device") if isinstance(attachment, dict) else None,
                "delete_on_termination": attachment.get("DeleteOnTermination") if isinstance(attachment, dict) else None,
            }
        )

    non_root = [v for v in flat if v.get("delete_on_termination") is False]
    if non_root:
        selected = sorted(non_root, key=lambda v: (int(v.get("size_gb") or 0), str(v.get("volume_id") or "")), reverse=True)[0]
        source = "aws_cli_non_root_volume"
    elif flat:
        selected = sorted(flat, key=lambda v: (int(v.get("size_gb") or 0), str(v.get("volume_id") or "")), reverse=True)[0]
        source = "aws_cli_largest_attached_volume"
    else:
        selected = {
            "volume_id": None,
            "volume_type": None,
            "size_gb": None,
        }
        source = "aws_cli_no_volumes"

    return {
        "selected": {
            "volume_id": selected.get("volume_id"),
            "volume_type": selected.get("volume_type"),
            "size_gb": selected.get("size_gb"),
        },
        "all": flat,
        "source": source,
    }


def _git_commit(repo_root: Path) -> Optional[str]:
    if shutil.which("git") is None:
        return None
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    commit = str(proc.stdout or "").strip()
    return commit if commit else None


def _fallback_code_bundle_hash(repo_root: Path) -> Optional[str]:
    key_paths = [
        repo_root / "tools" / "eval_temporal_walkforward.py",
        repo_root / "tools" / "build_temporal_policy_dataset.py",
        repo_root / "tools" / "regenerate_fresh_temporal_rowtrace_from_raw.py",
        repo_root / "real_world_cleaned_universe_l5_row_trace_export.py",
        repo_root / "l5_policy_learning_pipeline.py",
    ]
    existing = [p for p in key_paths if p.exists() and p.is_file()]
    if len(existing) <= 0:
        return None

    payload = []
    for p in existing:
        payload.append({
            "path": str(p),
            "sha256": _file_sha256(p),
            "size_bytes": int(p.stat().st_size),
        })
    return _canonical_hash(payload)


def _artifact_info(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "path": str(path),
            "exists": False,
            "sha256": None,
            "size_bytes": None,
        }
    return {
        "path": str(path),
        "exists": True,
        "sha256": _file_sha256(path),
        "size_bytes": int(path.stat().st_size),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build one AWS run manifest with provenance, infrastructure metadata, and dataset hashes "
            "for a full temporal cycle."
        )
    )
    p.add_argument("--repo-root", default="/data/tfe/repo")
    p.add_argument("--data-mount", default="/data/tfe")
    p.add_argument("--run-root", default="")
    p.add_argument("--run-timestamp", default="")
    p.add_argument("--horizons", default="5,20,60")
    p.add_argument(
        "--rowtrace-manifest",
        default="/data/tfe/data/current_inputs/fresh_temporal_rowtrace_manifest_latest.json",
    )
    p.add_argument(
        "--temporal-manifest",
        default="/data/tfe/data/current_inputs/temporal_policy_dataset_manifest_latest.json",
    )
    p.add_argument(
        "--audit-report",
        default="/data/tfe/data/current_inputs/temporal_dataset_audit_latest.json",
    )
    p.add_argument(
        "--eval-report",
        default="/data/tfe/data/current_inputs/temporal_walkforward_eval_latest.json",
    )
    p.add_argument(
        "--stage-loss-report",
        default="/data/tfe/data/current_inputs/temporal_stage_loss_latest.json",
    )
    p.add_argument(
        "--bootstrap-manifest",
        default="/data/tfe/logs/bootstrap_manifest_latest.json",
    )
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default="/data/tfe/data/current_inputs/aws_run_manifest_latest.json",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(str(args.repo_root)).resolve()
    data_mount = Path(str(args.data_mount)).resolve()
    run_root = Path(str(args.run_root)).resolve() if str(args.run_root).strip() else None

    rowtrace_manifest_path = Path(str(args.rowtrace_manifest)).resolve()
    temporal_manifest_path = Path(str(args.temporal_manifest)).resolve()
    audit_report_path = Path(str(args.audit_report)).resolve()
    eval_report_path = Path(str(args.eval_report)).resolve()
    stage_loss_report_path = Path(str(args.stage_loss_report)).resolve()
    bootstrap_manifest_path = Path(str(args.bootstrap_manifest)).resolve()

    report_latest = Path(str(args.report_latest)).resolve()
    report_out = (
        Path(str(args.report_out)).resolve()
        if str(args.report_out).strip()
        else report_latest.with_name(f"aws_run_manifest_{_utc_stamp()}.json")
    )

    horizons = _parse_horizons(str(args.horizons))

    rowtrace_manifest = _load_json(rowtrace_manifest_path) if rowtrace_manifest_path.exists() else {}
    temporal_manifest = _load_json(temporal_manifest_path) if temporal_manifest_path.exists() else {}

    rowtrace_csv = Path(
        str(
            (rowtrace_manifest.get("outputs") or {}).get(
                "fresh_temporal_rowtrace_csv",
                "/data/tfe/data/current_inputs/fresh_temporal_rowtrace_latest.csv",
            )
        )
    ).resolve()
    temporal_csv = Path(
        str(
            (temporal_manifest.get("outputs") or {}).get(
                "dataset_csv",
                "/data/tfe/data/current_inputs/temporal_policy_dataset_latest.csv",
            )
        )
    ).resolve()

    feature_payload = {
        "inputs": temporal_manifest.get("inputs", {}),
        "feature_schema": temporal_manifest.get("feature_schema", {}),
    }
    feature_config_hash = _canonical_hash(feature_payload)

    instance = _aws_instance_identity()
    memory_gb = _memory_gb()
    mounted_device = _mounted_device(data_mount)
    fs_type = _filesystem_type(data_mount)
    volumes = _attached_volumes(instance.get("instance_id"), instance.get("region"))

    commit_hash = _git_commit(repo_root)
    code_bundle_hash = _fallback_code_bundle_hash(repo_root)

    bootstrap_hash = _file_sha256(bootstrap_manifest_path) if bootstrap_manifest_path.exists() else None
    bootstrap_script_path = repo_root / "tools" / "aws_bootstrap.sh"
    bootstrap_script_hash = _file_sha256(bootstrap_script_path) if bootstrap_script_path.exists() else None

    run_timestamp = str(args.run_timestamp).strip()
    if not run_timestamp:
        if run_root is not None:
            run_timestamp = run_root.name
        else:
            run_timestamp = _utc_stamp()

    report: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "aws_temporal_full_cycle_manifest",
        "run_timestamp": run_timestamp,
        "run_root": str(run_root) if run_root is not None else None,
        "horizon_list": [int(h) for h in horizons],
        "provenance": {
            "market_data_version": (rowtrace_manifest.get("frozen_provenance") or {}).get("market_data_version"),
            "kernel_version": (rowtrace_manifest.get("frozen_provenance") or {}).get("kernel_version"),
            "adapter_config_hash": (rowtrace_manifest.get("frozen_provenance") or {}).get("adapter_config_hash"),
            "lookback_window_rules": (rowtrace_manifest.get("frozen_provenance") or {}).get("lookback_window_rules"),
            "feature_config_hash": feature_config_hash,
        },
        "infrastructure": {
            "instance_type": instance.get("instance_type"),
            "instance_id": instance.get("instance_id"),
            "region": instance.get("region"),
            "availability_zone": instance.get("availability_zone"),
            "ram_gb": memory_gb,
            "data_mount": str(data_mount),
            "mounted_device": mounted_device,
            "filesystem_type": fs_type,
            "ebs_volume": volumes.get("selected", {}),
            "ebs_discovery_source": volumes.get("source"),
            "attached_volumes": volumes.get("all", []),
        },
        "bootstrap": {
            "bootstrap_manifest_path": str(bootstrap_manifest_path),
            "bootstrap_hash": bootstrap_hash,
            "bootstrap_script_path": str(bootstrap_script_path),
            "bootstrap_script_hash": bootstrap_script_hash,
        },
        "code_bundle": {
            "repo_root": str(repo_root),
            "commit_hash": commit_hash,
            "code_bundle_hash": code_bundle_hash,
        },
        "datasets": {
            "rowtrace_manifest": _artifact_info(rowtrace_manifest_path),
            "rowtrace_csv": _artifact_info(rowtrace_csv),
            "temporal_manifest": _artifact_info(temporal_manifest_path),
            "temporal_dataset_csv": _artifact_info(temporal_csv),
            "audit_report": _artifact_info(audit_report_path),
            "eval_report": _artifact_info(eval_report_path),
            "stage_loss_report": _artifact_info(stage_loss_report_path),
        },
    }

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2)
    report_out.write_text(text, encoding="utf-8")
    report_latest.write_text(text, encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "analysis": report["analysis"],
                "run_timestamp": report["run_timestamp"],
                "instance_type": report["infrastructure"].get("instance_type"),
                "ram_gb": report["infrastructure"].get("ram_gb"),
                "ebs_volume": report["infrastructure"].get("ebs_volume"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
