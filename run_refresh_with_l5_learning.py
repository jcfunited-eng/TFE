#!/usr/bin/env python3
"""
CP-2: Run UF snapshot refresh, apply deterministic canonical baseline filter,
then publish to runtime Postgres and run the validation gate.

All ML, policy learning, oracle optimizer, and policy cell logic has been
removed. L5 decision generation is exclusively driven by
`tfe_l5_baseline.apply_canonical_filter(df)` (deterministic structural
physics). The DSF V3 basin math in `runtime_decision_provenance.mjs` handles
all per-row decision computation downstream.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tfe_l5_baseline import apply_canonical_filter
from rebuild_uf_snapshot import (
    REFRESH_MODE_FULL,
    REFRESH_MODE_TARGETED,
    rebuild_snapshot,
)

QUOTE_CACHE_FOLLOWUP_LANE = "post_publication_followup"
PHASE_LEDGER_SCRIPT = Path("web/scripts/update_refresh_phase_ledger.mjs")
PHASE_HEARTBEAT_SECONDS = 30
DEFAULT_RESUME_MAX_AGE_SECONDS = 6 * 60 * 60
RESUME_STAGE_POST_BASELINE_FILTER = "post_baseline_filter"


class RefreshPhaseError(RuntimeError):
    def __init__(self, failure_code: str, failure_detail: str):
        super().__init__(failure_detail)
        self.failure_code = str(failure_code or "").strip() or "REFRESH_PHASE_FAILED"
        self.failure_detail = str(failure_detail or "").strip() or "Unknown refresh phase failure."


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _history_path() -> Path | None:
    raw = str(os.environ.get("TFE_REFRESH_HISTORY_PATH", "")).strip()
    if not raw:
        return None
    return Path(raw)


def _history_base_event() -> dict[str, object]:
    return {
        "event": "refresh_update",
        "run_id": str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip() or None,
        "mode": str(os.environ.get("TFE_REFRESH_REQUESTED_MODE", "")).strip() or None,
        "trigger_source": str(os.environ.get("TFE_REFRESH_TRIGGER_SOURCE", "")).strip() or None,
        "requested_by": str(os.environ.get("TFE_REFRESH_REQUESTED_BY", "")).strip() or None,
    }


def _append_history_event(payload: dict[str, object]) -> None:
    history_path = _history_path()
    if history_path is None:
        return
    entry = {
        **_history_base_event(),
        **payload,
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry))
            fp.write("\n")
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        print(f"[REFRESH+CP2] History write failed. path={history_path}; error={error_text}", flush=True)
        raise RefreshPhaseError("REFRESH_HISTORY_WRITE_FAILED", error_text) from exc


def _read_env_int(name: str, default_value: int, minimum: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default_value
    try:
        value = int(raw)
    except Exception:
        return default_value
    if value < minimum:
        return minimum
    return value


def _read_env_float(name: str, default_value: float, minimum: float) -> float:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default_value
    try:
        value = float(raw)
    except Exception:
        return default_value
    if value < minimum:
        return minimum
    return value


def _is_truthy(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_trigger_source() -> str:
    raw = str(os.environ.get("TFE_REFRESH_TRIGGER_SOURCE", "program")).strip().lower()
    if raw in {"manual", "scheduled", "program"}:
        return raw
    if raw:
        return raw
    return "program"


def _parse_iso_utc(raw: str) -> datetime | None:
    text = str(raw).strip()
    if not text:
        return None
    normalized = text
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# S3 resume checkpoint helpers
# ---------------------------------------------------------------------------

def _resume_checkpoint_dir() -> Path:
    raw = str(os.environ.get("TFE_REFRESH_RESUME_CHECKPOINT_DIR", "")).strip()
    if raw:
        return Path(raw)
    return Path("backups/runtime/refresh_resume")


def _checkpoint_mode_key(mode: str) -> str:
    return "targeted" if mode == REFRESH_MODE_TARGETED else "full"


def _resume_checkpoint_path(mode: str) -> Path:
    return _resume_checkpoint_dir() / f"{_checkpoint_mode_key(mode)}.json"


def _resume_checkpoint_s3_uri(mode: str) -> str:
    raw = str(os.environ.get("TFE_REFRESH_RESUME_S3_URI", "")).strip()
    if not raw:
        return ""
    raw = raw.replace("{mode.json}", "{mode}.json")
    if "{mode}.json" in raw:
        return raw.replace("{mode}.json", f"{_checkpoint_mode_key(mode)}.json")
    if "{mode}" in raw:
        return raw.replace("{mode}", _checkpoint_mode_key(mode))
    if raw.endswith("/"):
        return f"{raw}{_checkpoint_mode_key(mode)}.json"
    if raw.endswith(".json"):
        return raw
    return f"{raw}/{_checkpoint_mode_key(mode)}.json"


def _run_aws_cli(args: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(args, text=True, capture_output=True, check=False, timeout=60)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if completed.returncode == 0:
        return True, ""
    stderr = str(completed.stderr or "").strip()
    stdout = str(completed.stdout or "").strip()
    return False, stderr or stdout or "unknown aws cli failure"


def _aws_cli_missing(err: str) -> bool:
    text = str(err or "").lower()
    return ("filenotfounderror" in text and "aws" in text) or ("no such file or directory" in text and "aws" in text)


def _parse_s3_uri(s3_uri: str) -> tuple[str, str] | None:
    uri = str(s3_uri or "").strip()
    if not uri.startswith("s3://"):
        return None
    remainder = uri[5:]
    bucket, sep, key = remainder.partition("/")
    if not bucket or not sep or not key:
        return None
    return bucket, key


def _boto3_s3_client() -> tuple[Any | None, str]:
    try:
        import boto3  # type: ignore
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    try:
        return boto3.client("s3"), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _download_from_s3_boto3(*, s3_uri: str, local_path: Path) -> tuple[bool, str]:
    parsed = _parse_s3_uri(s3_uri)
    if parsed is None:
        return False, f"unsupported uri={s3_uri}"
    client, err = _boto3_s3_client()
    if client is None:
        return False, err
    bucket, key = parsed
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, key, str(local_path))
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _upload_to_s3_boto3(*, local_path: Path, s3_uri: str) -> tuple[bool, str]:
    parsed = _parse_s3_uri(s3_uri)
    if parsed is None:
        return False, f"unsupported uri={s3_uri}"
    client, err = _boto3_s3_client()
    if client is None:
        return False, err
    bucket, key = parsed
    try:
        client.upload_file(str(local_path), bucket, key)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _copy_s3_boto3(*, src_s3_uri: str, dst_s3_uri: str) -> tuple[bool, str]:
    src = _parse_s3_uri(src_s3_uri)
    dst = _parse_s3_uri(dst_s3_uri)
    if src is None or dst is None:
        return False, f"unsupported copy uri src={src_s3_uri} dst={dst_s3_uri}"
    client, err = _boto3_s3_client()
    if client is None:
        return False, err
    src_bucket, src_key = src
    dst_bucket, dst_key = dst
    try:
        client.copy({"Bucket": src_bucket, "Key": src_key}, dst_bucket, dst_key)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _delete_s3_boto3(*, s3_uri: str) -> tuple[bool, str]:
    parsed = _parse_s3_uri(s3_uri)
    if parsed is None:
        return False, f"unsupported uri={s3_uri}"
    client, err = _boto3_s3_client()
    if client is None:
        return False, err
    bucket, key = parsed
    try:
        client.delete_object(Bucket=bucket, Key=key)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _download_resume_checkpoint_from_s3(*, mode: str, checkpoint_path: Path) -> None:
    s3_uri = _resume_checkpoint_s3_uri(mode)
    if not s3_uri:
        return
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    ok, err = _run_aws_cli(["aws", "s3", "cp", s3_uri, str(checkpoint_path), "--only-show-errors"])
    if ok:
        print(f"[REFRESH+CP2] Resume checkpoint downloaded from S3: {s3_uri} -> {checkpoint_path}")
        return
    fallback_ok, fallback_err = _download_from_s3_boto3(s3_uri=s3_uri, local_path=checkpoint_path)
    if fallback_ok:
        reason = "aws cli missing" if _aws_cli_missing(err) else "aws cli cp failed"
        print(f"[REFRESH+CP2] Resume checkpoint downloaded from S3 via boto3 ({reason}): {s3_uri} -> {checkpoint_path}")
    else:
        print(f"[REFRESH+CP2] Resume checkpoint S3 download skipped: uri={s3_uri} aws_cli_reason={err}; boto3_reason={fallback_err}")


def _upload_resume_checkpoint_to_s3(*, mode: str, checkpoint_path: Path) -> None:
    s3_uri = _resume_checkpoint_s3_uri(mode)
    if not s3_uri:
        return
    ok, err = _run_aws_cli(["aws", "s3", "cp", str(checkpoint_path), s3_uri, "--only-show-errors"])
    if ok:
        print(f"[REFRESH+CP2] Resume checkpoint uploaded to S3: {checkpoint_path} -> {s3_uri}")
        return
    fallback_ok, fallback_err = _upload_to_s3_boto3(local_path=checkpoint_path, s3_uri=s3_uri)
    if fallback_ok:
        reason = "aws cli missing" if _aws_cli_missing(err) else "aws cli cp failed"
        print(f"[REFRESH+CP2] Resume checkpoint uploaded to S3 via boto3 ({reason}): {checkpoint_path} -> {s3_uri}")
    else:
        print(f"[REFRESH+CP2] Resume checkpoint S3 upload skipped: path={checkpoint_path} uri={s3_uri} aws_cli_reason={err}; boto3_reason={fallback_err}")


def _clear_resume_checkpoint_s3(*, mode: str, archive_name: str) -> None:
    s3_uri = _resume_checkpoint_s3_uri(mode)
    if not s3_uri:
        return
    prefix, _, _name = s3_uri.rpartition("/")
    if not prefix:
        print(f"[REFRESH+CP2] Resume checkpoint S3 cleanup skipped: unsupported uri={s3_uri}")
        return
    archive_uri = f"{prefix}/{archive_name}"
    ok_copy, err_copy = _run_aws_cli(["aws", "s3", "cp", s3_uri, archive_uri, "--only-show-errors"])
    if ok_copy:
        print(f"[REFRESH+CP2] Resume checkpoint archived in S3: {archive_uri}")
    else:
        fallback_copy_ok, fallback_copy_err = _copy_s3_boto3(src_s3_uri=s3_uri, dst_s3_uri=archive_uri)
        if fallback_copy_ok:
            reason = "aws cli missing" if _aws_cli_missing(err_copy) else "aws cli cp failed"
            print(f"[REFRESH+CP2] Resume checkpoint archived in S3 via boto3 ({reason}): {archive_uri}")
        else:
            print(f"[REFRESH+CP2] Resume checkpoint S3 archive skipped: uri={s3_uri} aws_cli_reason={err_copy}; boto3_reason={fallback_copy_err}")
    ok_rm, err_rm = _run_aws_cli(["aws", "s3", "rm", s3_uri, "--only-show-errors"])
    if ok_rm:
        print(f"[REFRESH+CP2] Resume checkpoint removed from S3: {s3_uri}")
    else:
        fallback_rm_ok, fallback_rm_err = _delete_s3_boto3(s3_uri=s3_uri)
        if fallback_rm_ok:
            reason = "aws cli missing" if _aws_cli_missing(err_rm) else "aws cli rm failed"
            print(f"[REFRESH+CP2] Resume checkpoint removed from S3 via boto3 ({reason}): {s3_uri}")
        else:
            print(f"[REFRESH+CP2] Resume checkpoint S3 remove skipped: uri={s3_uri} aws_cli_reason={err_rm}; boto3_reason={fallback_rm_err}")


def _load_resume_checkpoint(*, mode: str, enabled: bool) -> dict[str, Any] | None:
    if not enabled:
        return None
    checkpoint_path = _resume_checkpoint_path(mode)
    if not checkpoint_path.exists() or not checkpoint_path.is_file():
        _download_resume_checkpoint_from_s3(mode=mode, checkpoint_path=checkpoint_path)
    if not checkpoint_path.exists() or not checkpoint_path.is_file():
        return None
    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[REFRESH+CP2] Ignoring unreadable resume checkpoint {checkpoint_path}: {type(exc).__name__}: {exc}")
        return None
    if not isinstance(payload, dict):
        print(f"[REFRESH+CP2] Ignoring malformed resume checkpoint {checkpoint_path}: payload is not an object.")
        return None
    stage = str(payload.get("stage", "")).strip()
    if stage != RESUME_STAGE_POST_BASELINE_FILTER:
        print(f"[REFRESH+CP2] Ignoring resume checkpoint {checkpoint_path}: unsupported stage={stage or 'missing'}.")
        return None
    checkpoint_mode = str(payload.get("mode", "")).strip()
    if checkpoint_mode != mode:
        print(f"[REFRESH+CP2] Ignoring resume checkpoint {checkpoint_path}: mode mismatch checkpoint={checkpoint_mode or 'missing'} requested={mode}.")
        return None
    refresh_report = payload.get("refresh_report")
    quote_cache_refresh_report = payload.get("quote_cache_refresh_report")
    baseline_filter_report = payload.get("baseline_filter_report")
    if not isinstance(refresh_report, dict) or not isinstance(quote_cache_refresh_report, dict) or not isinstance(baseline_filter_report, dict):
        print(f"[REFRESH+CP2] Ignoring resume checkpoint {checkpoint_path}: required report payloads are missing or invalid.")
        return None
    max_age_seconds = _read_env_int("TFE_REFRESH_RESUME_MAX_AGE_SECONDS", default_value=DEFAULT_RESUME_MAX_AGE_SECONDS, minimum=60)
    written_at_utc = _parse_iso_utc(str(payload.get("written_at_utc", "")))
    if written_at_utc is not None:
        age_seconds = (datetime.now(timezone.utc) - written_at_utc).total_seconds()
        if age_seconds > float(max_age_seconds):
            print(f"[REFRESH+CP2] Ignoring stale resume checkpoint {checkpoint_path}: age_seconds={age_seconds:.1f} max_age_seconds={max_age_seconds}.")
            return None
    payload["_checkpoint_path"] = str(checkpoint_path)
    return payload


def _write_resume_checkpoint(
    *,
    mode: str,
    report: dict[str, Any],
    quote_cache_refresh_report: dict[str, Any],
    baseline_filter_report: dict[str, Any],
) -> Path:
    checkpoint_path = _resume_checkpoint_path(mode)
    checkpoint_payload = {
        "stage": RESUME_STAGE_POST_BASELINE_FILTER,
        "mode": mode,
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
        "trigger_source": _normalize_trigger_source(),
        "refresh_report": report,
        "quote_cache_refresh_report": quote_cache_refresh_report,
        "baseline_filter_report": baseline_filter_report,
    }
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps(checkpoint_payload, indent=2), encoding="utf-8")
    print(f"[REFRESH+CP2] Resume checkpoint written: {checkpoint_path}")
    _upload_resume_checkpoint_to_s3(mode=mode, checkpoint_path=checkpoint_path)
    return checkpoint_path


def _clear_resume_checkpoint(*, mode: str, reason: str) -> None:
    checkpoint_path = _resume_checkpoint_path(mode)
    if not checkpoint_path.exists() or not checkpoint_path.is_file():
        return
    archive_name = f"{checkpoint_path.stem}.consumed.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    archive_path = checkpoint_path.with_name(archive_name)
    try:
        checkpoint_path.rename(archive_path)
        print(f"[REFRESH+CP2] Resume checkpoint archived: {archive_path} reason={reason}")
        _clear_resume_checkpoint_s3(mode=mode, archive_name=archive_name)
        return
    except Exception:
        pass
    try:
        checkpoint_path.unlink(missing_ok=True)
        print(f"[REFRESH+CP2] Resume checkpoint cleared: {checkpoint_path} reason={reason}")
        _clear_resume_checkpoint_s3(mode=mode, archive_name=archive_name)
    except Exception:
        return


# ---------------------------------------------------------------------------
# Phase ledger
# ---------------------------------------------------------------------------

def _phase_ledger_required() -> bool:
    return bool(str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip())


def _normalize_phase_failure_code(phase_name: str, suffix: str = "FAILED") -> str:
    raw = f"{phase_name}_{suffix}".upper()
    normalized: list[str] = []
    last_was_sep = False
    for ch in raw:
        if ch.isalnum():
            normalized.append(ch)
            last_was_sep = False
            continue
        if not last_was_sep:
            normalized.append("_")
            last_was_sep = True
    return "".join(normalized).strip("_") or "REFRESH_PHASE_FAILED"


def _extract_phase_failure(phase_name: str, error: Exception) -> tuple[str, str]:
    if isinstance(error, RefreshPhaseError):
        return error.failure_code, error.failure_detail
    return _normalize_phase_failure_code(phase_name), f"{type(error).__name__}: {error}"


def _write_phase_ledger_state(
    *,
    phase_name: str,
    process_status: str,
    input_contract: dict[str, Any] | None = None,
    output_contract: dict[str, Any] | None = None,
    started_at_iso: str | None = None,
    completed_at_iso: str | None = None,
    failure_code: str | None = None,
    failure_detail: str | None = None,
    last_heartbeat_at_iso: str | None = None,
) -> None:
    if not _phase_ledger_required():
        return
    if not PHASE_LEDGER_SCRIPT.exists() or not PHASE_LEDGER_SCRIPT.is_file():
        raise RefreshPhaseError(
            "REFRESH_PHASE_LEDGER_SCRIPT_MISSING",
            f"Refresh phase ledger script is missing: {PHASE_LEDGER_SCRIPT}",
        )
    payload = {
        "run_id": str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip(),
        "phase_name": phase_name,
        "process_status": process_status,
        "input_contract": input_contract,
        "output_contract": output_contract,
        "started_at": started_at_iso,
        "completed_at": completed_at_iso,
        "failure_code": failure_code,
        "failure_detail": failure_detail,
        "last_heartbeat_at": last_heartbeat_at_iso,
    }
    completed = subprocess.run(
        ["node", str(PHASE_LEDGER_SCRIPT)],
        cwd=str(Path.cwd()),
        env=dict(os.environ),
        text=True,
        input=json.dumps(payload),
        capture_output=True,
        check=False,
        timeout=60,
    )
    if completed.returncode == 0:
        return
    stdout_tail = "\n".join(str(completed.stdout or "").splitlines()[-20:]).strip()
    stderr_tail = "\n".join(str(completed.stderr or "").splitlines()[-20:]).strip()
    raise RefreshPhaseError(
        _normalize_phase_failure_code(phase_name, "LEDGER_WRITE_FAILED"),
        "Refresh phase ledger update failed. "
        f"exit_code={completed.returncode}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}",
    )


def _phase_input_contract(mode: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "refresh_mode": mode,
        "run_id": str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip() or None,
        "requested_mode": str(os.environ.get("TFE_REFRESH_REQUESTED_MODE", "")).strip() or None,
        "trigger_source": str(os.environ.get("TFE_REFRESH_TRIGGER_SOURCE", "")).strip() or None,
        "requested_by": str(os.environ.get("TFE_REFRESH_REQUESTED_BY", "")).strip() or None,
    }
    if isinstance(details, dict):
        payload.update(details)
    return payload


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------

def _format_command(cmd: list[str]) -> str:
    return " ".join(str(part) for part in cmd)


def _run_logged_subprocess(
    *,
    phase_label: str,
    cmd: list[str],
    cwd: str,
    env: dict[str, str] | None = None,
    heartbeat_seconds: int = 60,
) -> dict[str, Any]:
    started_at = time.monotonic()
    print(f"[REFRESH+CP2] {phase_label} starting. cwd={cwd}; cmd={_format_command(cmd)}", flush=True)
    try:
        process = subprocess.Popen(
            cmd, cwd=cwd, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, bufsize=1,
        )
    except Exception as exc:
        raise RuntimeError(f"{phase_label} failed to start: {type(exc).__name__}: {exc}") from exc

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_tail: deque[str] = deque(maxlen=40)
    stderr_tail: deque[str] = deque(maxlen=40)
    activity_lock = threading.Lock()
    last_activity_seconds = time.monotonic()

    def _pump_stream(stream: Any, stream_name: str, sink: list[str], tail: deque[str]) -> None:
        nonlocal last_activity_seconds
        if stream is None:
            return
        try:
            for raw_line in iter(stream.readline, ""):
                sink.append(raw_line)
                line = raw_line.rstrip("\n")
                tail.append(line)
                with activity_lock:
                    last_activity_seconds = time.monotonic()
                if line.strip():
                    print(f"[REFRESH+CP2][{phase_label}][{stream_name}] {line}", flush=True)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    stdout_thread = threading.Thread(target=_pump_stream, args=(process.stdout, "stdout", stdout_lines, stdout_tail), daemon=True)
    stderr_thread = threading.Thread(target=_pump_stream, args=(process.stderr, "stderr", stderr_lines, stderr_tail), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    last_heartbeat_seconds = started_at
    while True:
        try:
            return_code = process.wait(timeout=5)
            break
        except subprocess.TimeoutExpired:
            now_seconds = time.monotonic()
            if now_seconds - last_heartbeat_seconds >= float(max(heartbeat_seconds, 5)):
                with activity_lock:
                    idle_seconds = now_seconds - last_activity_seconds
                elapsed_seconds = now_seconds - started_at
                print(
                    f"[REFRESH+CP2] {phase_label} still running. "
                    f"elapsed_seconds={elapsed_seconds:.1f}; idle_output_seconds={idle_seconds:.1f}; pid={process.pid}",
                    flush=True,
                )
                last_heartbeat_seconds = now_seconds

    stdout_thread.join(timeout=10)
    stderr_thread.join(timeout=10)

    elapsed_seconds = time.monotonic() - started_at
    stdout_text = "".join(stdout_lines)
    stderr_text = "".join(stderr_lines)
    stdout_tail_text = "\n".join(stdout_tail).strip()
    stderr_tail_text = "\n".join(stderr_tail).strip()
    print(f"[REFRESH+CP2] {phase_label} completed. exit_code={return_code}; elapsed_seconds={elapsed_seconds:.1f}", flush=True)
    return {
        "returncode": return_code,
        "stdout": stdout_text,
        "stderr": stderr_text,
        "stdout_tail": stdout_tail_text,
        "stderr_tail": stderr_tail_text,
        "elapsed_seconds": elapsed_seconds,
    }


# ---------------------------------------------------------------------------
# Quote cache refresh
# ---------------------------------------------------------------------------

def _quote_cache_refresh_input_contract() -> dict[str, Any]:
    return _phase_input_contract(
        str(os.environ.get("TFE_REFRESH_REQUESTED_MODE", "")).strip() or "unknown",
        {
            "workers": _read_env_int("TFE_QUOTE_CACHE_WORKERS", default_value=4, minimum=1),
            "timeout_sec": _read_env_int("TFE_QUOTE_CACHE_TIMEOUT_SEC", default_value=35, minimum=5),
            "min_non_meta_fields": _read_env_int("TFE_QUOTE_CACHE_MIN_NON_META_FIELDS", default_value=20, minimum=1),
            "save_every": _read_env_int("TFE_QUOTE_CACHE_SAVE_EVERY", default_value=200, minimum=1),
        },
    )


def _profile_overrides_input_contract() -> dict[str, Any]:
    return _phase_input_contract(
        str(os.environ.get("TFE_REFRESH_REQUESTED_MODE", "")).strip() or "unknown",
        {
            "workers": _read_env_int("TFE_PROFILE_OVERRIDE_WORKERS", default_value=8, minimum=1),
            "timeout_sec": _read_env_int("TFE_PROFILE_OVERRIDE_TIMEOUT_SEC", default_value=45, minimum=5),
            "save_every": _read_env_int("TFE_PROFILE_OVERRIDE_SAVE_EVERY", default_value=200, minimum=1),
            "limit": _read_env_int("TFE_PROFILE_OVERRIDE_LIMIT", default_value=0, minimum=0),
        },
    )


def _run_profile_overrides_refresh() -> dict[str, Any]:
    run_raw = str(os.environ.get("TFE_REFRESH_BUILD_PROFILE_OVERRIDES", "1")).strip().lower()
    if run_raw in {"0", "false", "no", "off"}:
        return {"status": "skipped", "reason": "disabled_by_env"}
    workers = _read_env_int("TFE_PROFILE_OVERRIDE_WORKERS", default_value=8, minimum=1)
    timeout_sec = _read_env_int("TFE_PROFILE_OVERRIDE_TIMEOUT_SEC", default_value=45, minimum=5)
    save_every = _read_env_int("TFE_PROFILE_OVERRIDE_SAVE_EVERY", default_value=200, minimum=1)
    limit = _read_env_int("TFE_PROFILE_OVERRIDE_LIMIT", default_value=0, minimum=0)
    cmd = [
        sys.executable or "python3", "-u",
        "web/scripts/build_screener_profile_overrides.py",
        "--workers", str(workers),
        "--timeout-sec", str(timeout_sec),
        "--save-every", str(save_every),
        "--limit", str(limit),
    ]
    completed = _run_logged_subprocess(
        phase_label="profile_overrides_refresh", cmd=cmd,
        cwd=str(Path.cwd()), env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RefreshPhaseError(
            "PROFILE_OVERRIDES_REFRESH_FAILED",
            f"Profile override refresh failed. exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}",
        )
    return {"status": "ok", "workers": workers, "timeout_sec": timeout_sec, "limit": limit, "stdout_tail": stdout_tail, "stderr_tail": stderr_tail}


def _run_quote_cache_refresh() -> dict[str, Any]:
    enabled_raw = str(os.environ.get("TFE_REFRESH_REBUILD_QUOTE_CACHE", "1")).strip().lower()
    if enabled_raw in {"0", "false", "no", "off"}:
        return {"status": "skipped", "reason": "disabled_by_env"}
    workers = _read_env_int("TFE_QUOTE_CACHE_WORKERS", default_value=4, minimum=1)
    timeout_sec = _read_env_int("TFE_QUOTE_CACHE_TIMEOUT_SEC", default_value=35, minimum=5)
    min_non_meta_fields = _read_env_int("TFE_QUOTE_CACHE_MIN_NON_META_FIELDS", default_value=20, minimum=1)
    save_every = _read_env_int("TFE_QUOTE_CACHE_SAVE_EVERY", default_value=200, minimum=1)
    cmd = [
        sys.executable or "python3", "-u",
        "web/scripts/build_screener_quote_cache.py",
        "--workers", str(workers),
        "--timeout-sec", str(timeout_sec),
        "--save-every", str(save_every),
        "--min-non-meta-fields", str(min_non_meta_fields),
    ]
    completed = _run_logged_subprocess(
        phase_label="quote_cache_refresh", cmd=cmd,
        cwd=str(Path.cwd()), env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RefreshPhaseError(
            "QUOTE_CACHE_REFRESH_FAILED",
            f"Quote cache refresh failed. exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}",
        )
    summary: dict[str, Any] = {"status": "ok", "workers": workers, "timeout_sec": timeout_sec, "min_non_meta_fields": min_non_meta_fields, "stdout_tail": stdout_tail, "stderr_tail": stderr_tail}
    summary["profile_overrides"] = _run_post_rebuild_phase(
        phase_name="profile_overrides_refresh",
        runner=_run_profile_overrides_refresh,
        detail_builder=lambda payload: {"profile_overrides_refresh": payload.get("status")},
        input_contract=_profile_overrides_input_contract(),
    )
    return summary


def _quote_cache_refresh_detail_payload(payload: dict[str, Any]) -> dict[str, Any]:
    profile_overrides = payload.get("profile_overrides")
    return {
        "quote_cache_refresh": payload.get("status"),
        "quote_cache_profile_overrides": profile_overrides.get("status") if isinstance(profile_overrides, dict) else None,
        "quote_cache_lane": payload.get("lane"),
        "quote_cache_followup_pid": payload.get("followup_pid"),
    }


def _should_defer_quote_cache_refresh(mode: str) -> bool:
    return mode in {REFRESH_MODE_FULL, REFRESH_MODE_TARGETED}


def _deferred_quote_cache_refresh_report(mode: str) -> dict[str, Any]:
    reason = "full_universe_publish_should_not_wait_on_quote_cache_refresh"
    if mode == REFRESH_MODE_TARGETED:
        reason = "snapshot_publish_should_not_wait_on_quote_cache_refresh"
    return {"status": "deferred", "lane": QUOTE_CACHE_FOLLOWUP_LANE, "publication_blocking": False, "reason": reason}


def _quote_cache_refresh_is_deferred(report: dict[str, Any]) -> bool:
    return (
        isinstance(report, dict)
        and str(report.get("status") or "").strip().lower() == "deferred"
        and str(report.get("lane") or "").strip() == QUOTE_CACHE_FOLLOWUP_LANE
    )


def _stream_fileno(stream: Any, fallback: int) -> int:
    try:
        return int(stream.fileno())
    except Exception:
        return fallback


def _launch_quote_cache_refresh_followup(*, mode: str, quote_cache_refresh_report: dict[str, Any]) -> dict[str, Any]:
    if not _quote_cache_refresh_is_deferred(quote_cache_refresh_report):
        return quote_cache_refresh_report
    script_path = Path(__file__).resolve()
    cmd = [sys.executable or "python3", "-u", str(script_path), "--refresh-mode", mode, "--quote-cache-followup-only"]
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["TFE_REFRESH_QUOTE_CACHE_FOLLOWUP"] = "1"
    try:
        child = subprocess.Popen(
            cmd, cwd=str(Path.cwd()), env=env,
            stdin=subprocess.DEVNULL,
            stdout=_stream_fileno(sys.stdout, 1),
            stderr=_stream_fileno(sys.stderr, 2),
            start_new_session=True,
        )
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        print(f"[REFRESH+CP2] Quote cache follow-up launch failed. error={error_text}", flush=True)
        _append_history_event({"phase": "quote_cache_refresh_followup_launch_failed", "status": "error", "lane": QUOTE_CACHE_FOLLOWUP_LANE, "error": error_text})
        return {"status": "launch_failed", "lane": QUOTE_CACHE_FOLLOWUP_LANE, "reason": "detached_followup_launch_failed", "error": error_text}
    print(f"[REFRESH+CP2] Quote cache follow-up launched. pid={child.pid}; lane={QUOTE_CACHE_FOLLOWUP_LANE}", flush=True)
    _append_history_event({"phase": "quote_cache_refresh_followup_launch", "status": "launched", "lane": QUOTE_CACHE_FOLLOWUP_LANE, "pid": child.pid})
    return {"status": "launched", "lane": QUOTE_CACHE_FOLLOWUP_LANE, "reason": "detached_followup_launched_after_publication", "followup_pid": child.pid}


# ---------------------------------------------------------------------------
# CP-2: Canonical baseline filter
# ---------------------------------------------------------------------------

def _run_l5_canonical_filter() -> dict[str, Any]:
    """Load uf_snapshot.json, apply deterministic canonical filter, return summary.

    No ML. No policy cells. No heuristics. Pure structural physics via
    tfe_l5_baseline.apply_canonical_filter(df).
    """
    snapshot_path = Path("uf_snapshot.json")
    if not snapshot_path.exists() or not snapshot_path.is_file():
        raise RefreshPhaseError(
            "L5_CANONICAL_FILTER_SNAPSHOT_MISSING",
            f"Snapshot file not found: {snapshot_path}",
        )
    try:
        raw = snapshot_path.read_text(encoding="utf-8")
        payload = json.loads(raw.replace("NaN", "null").replace("-Infinity", "null").replace("Infinity", "null"))
    except Exception as exc:
        raise RefreshPhaseError(
            "L5_CANONICAL_FILTER_SNAPSHOT_UNREADABLE",
            f"Could not read snapshot: {type(exc).__name__}: {exc}",
        ) from exc

    if isinstance(payload, dict):
        rows = payload.get("rows") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    if not rows:
        print("[REFRESH+CP2] Canonical filter: no snapshot rows found.", flush=True)
        return {
            "status": "ok",
            "total_rows": 0,
            "filtered_rows": 0,
            "filter_rate": 0.0,
            "policy_source": "tfe_l5_baseline.apply_canonical_filter",
            "policy_mode": "deterministic_structural_physics",
            "reason": "no_snapshot_rows",
        }

    try:
        df = pd.DataFrame(rows)
    except Exception as exc:
        raise RefreshPhaseError(
            "L5_CANONICAL_FILTER_DATAFRAME_FAILED",
            f"Could not build DataFrame from snapshot: {type(exc).__name__}: {exc}",
        ) from exc

    total_rows = len(df)

    try:
        filtered_df = apply_canonical_filter(df)
    except ValueError as exc:
        raise RefreshPhaseError(
            "L5_CANONICAL_FILTER_MISSING_COLUMNS",
            f"Canonical filter missing required columns: {exc}",
        ) from exc
    except Exception as exc:
        raise RefreshPhaseError(
            "L5_CANONICAL_FILTER_FAILED",
            f"Canonical filter execution failed: {type(exc).__name__}: {exc}",
        ) from exc

    filtered_rows = len(filtered_df)
    filter_rate = filtered_rows / total_rows if total_rows > 0 else 0.0

    print(
        f"[REFRESH+CP2] Canonical filter applied. "
        f"total_rows={total_rows}; filtered_rows={filtered_rows}; filter_rate={filter_rate:.4f}",
        flush=True,
    )

    return {
        "status": "ok",
        "total_rows": total_rows,
        "filtered_rows": filtered_rows,
        "filter_rate": filter_rate,
        "policy_source": "tfe_l5_baseline.apply_canonical_filter",
        "policy_mode": "deterministic_structural_physics",
    }


# ---------------------------------------------------------------------------
# Snapshot publication stamping
# ---------------------------------------------------------------------------

def _stamp_snapshot_publication_id_if_needed(snapshot_path: Path) -> str | None:
    try:
        raw = snapshot_path.read_text(encoding="utf-8")
        payload: dict[str, Any] = json.loads(
            raw.replace("NaN", "null").replace("-Infinity", "null").replace("Infinity", "null")
        )
    except Exception as exc:
        print(f"[REFRESH+CP2] Snapshot stamp: could not read snapshot; {exc}", flush=True)
        return None
    existing_id = str(payload.get("publication_id") or "").strip()
    if existing_id:
        print(f"[REFRESH+CP2] Snapshot stamp: publication_id already present={existing_id}", flush=True)
        return existing_id
    generated_at_utc: str | None = str(payload.get("generated_at_utc") or "").strip() or None
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    base: dict[str, Any] = {"generated_at_utc": generated_at_utc, "rows": rows}
    digest = hashlib.sha256(
        json.dumps(base, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    publication_id = f"snapshot_pub_v1_{digest[:24]}"
    payload["publication_id"] = publication_id
    try:
        tmp_path = snapshot_path.with_suffix(".tmp_stamp")
        tmp_path.write_text(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(snapshot_path)
    except Exception as exc:
        print(f"[REFRESH+CP2] Snapshot stamp: could not write publication_id; {exc}", flush=True)
        return None
    print(f"[REFRESH+CP2] Snapshot stamp: derived and wrote publication_id={publication_id}", flush=True)
    return publication_id


# ---------------------------------------------------------------------------
# Runtime Postgres sync
# ---------------------------------------------------------------------------

def _runtime_postgres_sync_input_contract(*, report: dict[str, Any], mode: str, quote_cache_refresh_report: dict[str, Any]) -> dict[str, Any]:
    return _phase_input_contract(
        mode,
        {
            "refresh_report_status": report.get("status"),
            "rows_written": report.get("rows_written"),
            "quote_cache_refresh_status": quote_cache_refresh_report.get("status"),
            "quote_cache_refresh_lane": quote_cache_refresh_report.get("lane"),
            "quote_cache_publication_blocking": quote_cache_refresh_report.get("publication_blocking"),
            "policy_mode": "deterministic_structural_physics",
            "cp_profile": "CP-2",
        },
    )


def _run_runtime_postgres_sync(
    report: dict[str, Any],
    mode: str,
    quote_cache_refresh_report: dict[str, Any],
) -> dict[str, Any]:
    script_path = Path("web/scripts/sync_runtime_postgres.mjs")
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Runtime sync script is missing: {script_path}")

    _stamp_snapshot_publication_id_if_needed(Path("uf_snapshot.json"))

    env = dict(os.environ)
    env.setdefault("TFE_REFRESH_REQUESTED_MODE", mode)
    env.setdefault("TFE_REFRESH_COMPLETED_AT", datetime.now(timezone.utc).isoformat())
    env.setdefault("TFE_REFRESH_STARTED_AT", str(os.environ.get("TFE_REFRESH_STARTED_AT", "")).strip() or datetime.now(timezone.utc).isoformat())
    env["TFE_ALLOW_DEFERRED_QUOTE_CACHE_FALLBACK"] = (
        "1" if _quote_cache_refresh_is_deferred(quote_cache_refresh_report) else "0"
    )
    # CP-2: Oracle optimizer is not used. Set all optimizer env vars to empty so
    # the sync script records null in runtime_refresh_runs optimizer columns.
    env["TFE_OPTIMIZER_SHORT_CYCLE"] = "not_run_cp2"
    env["TFE_OPTIMIZER_CYCLE_REQUESTED_RUNS"] = ""
    env["TFE_OPTIMIZER_CYCLE_COMPLETED_RUNS"] = ""
    env["TFE_OPTIMIZER_SESSION_ID"] = ""
    env["TFE_OPTIMIZER_TARGET_RETURN_LIFT_PCT"] = ""
    env["TFE_OPTIMIZER_BEST_SCORE"] = ""
    env["TFE_OPTIMIZER_TARGET_MET"] = ""
    env["TFE_EPOCH_LIBRARY_CONFIDENCE_SCHEMA"] = ""
    env["TFE_EPOCH_LIBRARY_STATUS"] = ""

    cmd = ["node", str(script_path)]
    completed = _run_logged_subprocess(phase_label="runtime_postgres_sync", cmd=cmd, cwd=str(Path.cwd()), env=env)
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RefreshPhaseError(
            "RUNTIME_POSTGRES_SYNC_FAILED",
            f"Runtime Postgres sync failed. exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}",
        )
    payload = _extract_json_payload(str(completed.get("stdout") or ""))
    payload.setdefault("refresh_report_status", report.get("status"))
    return payload


# ---------------------------------------------------------------------------
# Validation gate
# ---------------------------------------------------------------------------

def _validation_gate_input_contract() -> dict[str, Any]:
    return _phase_input_contract(
        str(os.environ.get("TFE_REFRESH_REQUESTED_MODE", "")).strip() or "unknown",
        {
            "refresh_run_id": str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip() or None,
            "refresh_started_at": str(os.environ.get("TFE_REFRESH_STARTED_AT", "")).strip() or None,
            "refresh_completed_at": str(os.environ.get("TFE_REFRESH_COMPLETED_AT", "")).strip() or None,
        },
    )


def _run_validation_gate() -> dict[str, Any]:
    script_path = Path("web/scripts/run_validation_gate_v1.mjs")
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Validation gate script is missing: {script_path}")
    cmd = ["node", str(script_path)]
    completed = _run_logged_subprocess(phase_label="validation_gate", cmd=cmd, cwd=str(Path.cwd()), env=dict(os.environ))
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RefreshPhaseError(
            "VALIDATION_GATE_FAILED",
            f"Validation gate failed. exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}",
        )
    payload = _extract_json_payload(str(completed.get("stdout") or ""))
    status = str(payload.get("status", "")).strip().lower()
    if status != "pass":
        raise RefreshPhaseError("VALIDATION_GATE_NON_PASS", f"Validation gate returned non-pass status: {status or 'missing'}")
    return payload


def _extract_json_payload(stdout_text: str) -> dict[str, Any]:
    raw = stdout_text.strip()
    if not raw:
        raise RuntimeError("Subprocess returned empty stdout.")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    first = raw.find("{")
    last = raw.rfind("}")
    if first < 0 or last < first:
        raise RuntimeError("Subprocess did not output a JSON payload.")
    try:
        parsed = json.loads(raw[first: last + 1])
    except Exception as exc:
        raise RuntimeError(f"Failed to parse subprocess JSON payload: {type(exc).__name__}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Subprocess payload is not a JSON object.")
    return parsed


# ---------------------------------------------------------------------------
# Post-rebuild pipeline
# ---------------------------------------------------------------------------

def _run_post_rebuild_phase(
    *,
    phase_name: str,
    runner: Any,
    detail_builder: Any | None = None,
    input_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    started_at_iso = datetime.now(timezone.utc).isoformat()
    heartbeat_stop = threading.Event()
    heartbeat_error: list[Exception] = []

    def _heartbeat_loop() -> None:
        while not heartbeat_stop.wait(PHASE_HEARTBEAT_SECONDS):
            try:
                _write_phase_ledger_state(
                    phase_name=phase_name, process_status="running",
                    input_contract=input_contract, started_at_iso=started_at_iso,
                    last_heartbeat_at_iso=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as exc:
                heartbeat_error.append(exc)
                print(f"[REFRESH+CP2] Phase heartbeat failed: {phase_name}; error={type(exc).__name__}: {exc}", flush=True)
                heartbeat_stop.set()
                return

    _write_phase_ledger_state(
        phase_name=phase_name, process_status="running",
        input_contract=input_contract, started_at_iso=started_at_iso,
        last_heartbeat_at_iso=started_at_iso,
    )
    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    _append_history_event({"phase": f"{phase_name}_start", "status": "running"})
    print(f"[REFRESH+CP2] Post-rebuild phase start: {phase_name}", flush=True)

    try:
        result = runner()
    except Exception as exc:
        elapsed_seconds = time.monotonic() - started_at
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=5)
        failure_code, failure_detail = _extract_phase_failure(phase_name, exc)
        completed_at_iso = datetime.now(timezone.utc).isoformat()
        _write_phase_ledger_state(
            phase_name=phase_name, process_status="failed",
            input_contract=input_contract,
            output_contract={"status": "error", "failure_code": failure_code, "failure_detail": failure_detail},
            started_at_iso=started_at_iso, completed_at_iso=completed_at_iso,
            failure_code=failure_code, failure_detail=failure_detail,
            last_heartbeat_at_iso=completed_at_iso,
        )
        print(f"[REFRESH+CP2] Post-rebuild phase failed: {phase_name}; elapsed_seconds={elapsed_seconds:.1f}; error={failure_detail}", flush=True)
        _append_history_event({"phase": f"{phase_name}_failed", "status": "error", "elapsed_seconds": elapsed_seconds, "error": failure_detail, "failure_code": failure_code})
        raise

    heartbeat_stop.set()
    heartbeat_thread.join(timeout=5)
    if heartbeat_error:
        print(f"[REFRESH+CP2] Post-rebuild phase heartbeat warning (non-fatal): {phase_name}; heartbeat_error={heartbeat_error[0]}", flush=True)
    if not isinstance(result, dict):
        failure = RefreshPhaseError(
            _normalize_phase_failure_code(phase_name, "INVALID_OUTPUT"),
            f"Post-rebuild phase {phase_name} returned non-dict result.",
        )
        failure_code, failure_detail = _extract_phase_failure(phase_name, failure)
        completed_at_iso = datetime.now(timezone.utc).isoformat()
        _write_phase_ledger_state(
            phase_name=phase_name, process_status="failed",
            input_contract=input_contract,
            output_contract={"status": "error", "failure_code": failure_code, "failure_detail": failure_detail},
            started_at_iso=started_at_iso, completed_at_iso=completed_at_iso,
            failure_code=failure_code, failure_detail=failure_detail,
            last_heartbeat_at_iso=completed_at_iso,
        )
        raise failure

    elapsed_seconds = time.monotonic() - started_at
    detail_payload = detail_builder(result) if callable(detail_builder) else {}
    if not isinstance(detail_payload, dict):
        detail_payload = {}
    phase_status = str(result.get("status") or "ok")
    completed_at_iso = datetime.now(timezone.utc).isoformat()
    try:
        _write_phase_ledger_state(
            phase_name=phase_name, process_status="completed",
            input_contract=input_contract, output_contract=result,
            started_at_iso=started_at_iso, completed_at_iso=completed_at_iso,
            last_heartbeat_at_iso=completed_at_iso,
        )
    except Exception as _ledger_exc:
        _persist_code = _normalize_phase_failure_code(phase_name, "LEDGER_PERSIST_FAILED")
        _persist_detail = f"Phase completion ledger write failed for '{phase_name}': {type(_ledger_exc).__name__}: {_ledger_exc}"
        print(f"[REFRESH+CP2] FATAL: {_persist_code}: {_persist_detail}", flush=True)
        _failed_at_iso = datetime.now(timezone.utc).isoformat()
        try:
            _write_phase_ledger_state(
                phase_name=phase_name, process_status="failed",
                input_contract=input_contract,
                output_contract={"status": "error", "failure_code": _persist_code, "failure_detail": _persist_detail},
                started_at_iso=started_at_iso, completed_at_iso=_failed_at_iso,
                failure_code=_persist_code, failure_detail=_persist_detail,
                last_heartbeat_at_iso=_failed_at_iso,
            )
        except Exception as _settle_exc:
            print(f"[REFRESH+CP2] FATAL: Phase failure settlement also failed for '{phase_name}': {type(_settle_exc).__name__}: {_settle_exc}", flush=True)
        raise RefreshPhaseError(_persist_code, _persist_detail) from _ledger_exc

    print(f"[REFRESH+CP2] Post-rebuild phase complete: {phase_name}; elapsed_seconds={elapsed_seconds:.1f}; status={phase_status}", flush=True)
    _append_history_event({"phase": f"{phase_name}_complete", "status": phase_status, "elapsed_seconds": elapsed_seconds, **detail_payload})
    return result


def _run_post_rebuild_pipeline(
    *,
    report: dict[str, Any],
    mode: str,
    quote_cache_refresh_report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime_sync_report = _run_post_rebuild_phase(
        phase_name="runtime_postgres_sync",
        runner=lambda: _run_runtime_postgres_sync(
            report=report,
            mode=mode,
            quote_cache_refresh_report=quote_cache_refresh_report,
        ),
        detail_builder=lambda payload: {
            "runtime_postgres_sync": payload.get("status"),
            "runtime_postgres_sync_run_id": payload.get("run_id"),
        },
        input_contract=_runtime_postgres_sync_input_contract(
            report=report,
            mode=mode,
            quote_cache_refresh_report=quote_cache_refresh_report,
        ),
    )
    validation_report = _run_post_rebuild_phase(
        phase_name="validation_gate",
        runner=_run_validation_gate,
        detail_builder=lambda payload: {
            "validation_gate_status": payload.get("status"),
            "validation_gate_report_run_id": payload.get("run_id"),
        },
        input_contract=_validation_gate_input_contract(),
    )
    return runtime_sync_report, validation_report


def _load_followup_refresh_report() -> dict[str, Any]:
    report_path = Path("uf_snapshot_rebuild_report.json")
    if not report_path.exists() or not report_path.is_file():
        return {"status": "unknown", "rows_written": None, "reason": "followup_refresh_report_missing"}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unknown", "rows_written": None, "reason": f"followup_refresh_report_unreadable:{type(exc).__name__}"}
    if not isinstance(payload, dict):
        return {"status": "unknown", "rows_written": None, "reason": "followup_refresh_report_not_object"}
    return payload


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CP-2: Refresh UF snapshot, apply canonical baseline filter, publish to runtime Postgres."
    )
    parser.add_argument("--refresh-mode", choices=[REFRESH_MODE_FULL, REFRESH_MODE_TARGETED], default=REFRESH_MODE_FULL)
    parser.add_argument("--targeted-refresh", action="store_true", help="Shortcut for --refresh-mode targeted_pfsc.")
    parser.add_argument("--force-refresh-universe", action="store_true", help="Refresh universe caches from Massive before rebuild.")
    parser.add_argument("--years-history", type=int, default=5)
    parser.add_argument("--resume-from-checkpoint", action="store_true", help="Resume from the latest post-baseline-filter checkpoint when available.")
    parser.add_argument("--quote-cache-followup-only", action="store_true", help="Run only the detached quote-cache follow-up lane.")
    # CP-2: L5 learning is permanently removed. Accept --skip-l5-learning as a
    # no-op so the admin console (which still passes this flag for legacy
    # compatibility) does not trigger an argparse error (exit_code=2).
    parser.add_argument("--skip-l5-learning", action="store_true", help="No-op. L5 learning is not used in CP-2.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = _parse_args()

    mode = str(args.refresh_mode)
    if bool(args.targeted_refresh):
        mode = REFRESH_MODE_TARGETED

    if bool(args.quote_cache_followup_only):
        # Run quote cache refresh — this phase writes to the ledger under the
        # follow-up lane, which is fine because it is a new phase name.
        quote_cache_refresh_report = _run_post_rebuild_phase(
            phase_name="quote_cache_refresh",
            runner=_run_quote_cache_refresh,
            detail_builder=_quote_cache_refresh_detail_payload,
            input_contract=_quote_cache_refresh_input_contract(),
        )
        print("[REFRESH+CP2] Quote cache refresh follow-up report:")
        print(json.dumps(quote_cache_refresh_report, indent=2))
        # Run the follow-up postgres sync DIRECTLY (no phase-ledger writes) so
        # that a transient deadlock or other failure does not overwrite the
        # completed/pass state that the main run already wrote for
        # runtime_postgres_sync and validation_gate.
        followup_report = _load_followup_refresh_report()
        try:
            runtime_sync_report = _run_runtime_postgres_sync(
                report=followup_report,
                mode=mode,
                quote_cache_refresh_report=quote_cache_refresh_report,
            )
            print("[REFRESH+CP2] Quote cache follow-up runtime sync report:")
            print(json.dumps(runtime_sync_report, indent=2))
        except Exception as exc:
            print(f"[REFRESH+CP2] Quote cache follow-up runtime sync failed (non-fatal, main run already succeeded): {exc}", flush=True)
        try:
            validation_report = _run_validation_gate()
            print("[REFRESH+CP2] Quote cache follow-up validation report:")
            print(json.dumps(validation_report, indent=2))
        except Exception as exc:
            print(f"[REFRESH+CP2] Quote cache follow-up validation failed (non-fatal): {exc}", flush=True)
        return 0

    resume_enabled = bool(args.resume_from_checkpoint) or _is_truthy(os.environ.get("TFE_REFRESH_RESUME_FROM_CHECKPOINT", "1"))
    resume_payload = _load_resume_checkpoint(mode=mode, enabled=resume_enabled)
    resumed_from_checkpoint = resume_payload is not None
    baseline_filter_report: dict[str, Any] | None = None

    if resumed_from_checkpoint:
        report = dict(resume_payload.get("refresh_report") or {})
        quote_cache_refresh_report = dict(resume_payload.get("quote_cache_refresh_report") or {})
        baseline_filter_report = dict(resume_payload.get("baseline_filter_report") or {})
        checkpoint_path = str(resume_payload.get("_checkpoint_path") or _resume_checkpoint_path(mode))
        print(f"[REFRESH+CP2] Resume checkpoint loaded. path={checkpoint_path}; stage={resume_payload.get('stage')}; mode={mode}")
        print("[REFRESH+CP2] Refresh report (from checkpoint):")
        print(json.dumps(report, indent=2))
        print("[REFRESH+CP2] Baseline filter report (from checkpoint):")
        print(json.dumps(baseline_filter_report, indent=2))
    else:
        report = _run_post_rebuild_phase(
            phase_name="snapshot_rebuild",
            runner=lambda: rebuild_snapshot(
                refresh_mode=mode,
                force_refresh_universe=bool(args.force_refresh_universe),
                years_history=int(args.years_history),
            ),
            detail_builder=lambda payload: {
                "snapshot_rebuild_status": payload.get("status"),
                "rows_written": payload.get("rows_written"),
            },
            input_contract=_phase_input_contract(
                mode,
                {"force_refresh_universe": bool(args.force_refresh_universe), "years_history": int(args.years_history)},
            ),
        )
        print("[REFRESH+CP2] Refresh report:")
        print(json.dumps(report, indent=2))

        if _should_defer_quote_cache_refresh(mode):
            quote_cache_refresh_report = _deferred_quote_cache_refresh_report(mode)
            deferred_at_iso = datetime.now(timezone.utc).isoformat()
            _write_phase_ledger_state(
                phase_name="quote_cache_refresh", process_status="deferred",
                input_contract=_quote_cache_refresh_input_contract(),
                output_contract=quote_cache_refresh_report,
                started_at_iso=deferred_at_iso, last_heartbeat_at_iso=deferred_at_iso,
            )
            print(f"[REFRESH+CP2] Quote cache refresh deferred. lane={QUOTE_CACHE_FOLLOWUP_LANE}; reason={quote_cache_refresh_report.get('reason')}", flush=True)
            _append_history_event({"phase": "quote_cache_refresh_deferred", "status": "deferred", "lane": QUOTE_CACHE_FOLLOWUP_LANE, "reason": quote_cache_refresh_report.get("reason")})
        else:
            quote_cache_refresh_report = _run_post_rebuild_phase(
                phase_name="quote_cache_refresh",
                runner=_run_quote_cache_refresh,
                detail_builder=_quote_cache_refresh_detail_payload,
                input_contract=_quote_cache_refresh_input_contract(),
            )
        print("[REFRESH+CP2] Quote cache refresh report:")
        print(json.dumps(quote_cache_refresh_report, indent=2))

        baseline_filter_report = _run_post_rebuild_phase(
            phase_name="l5_baseline_filter",
            runner=_run_l5_canonical_filter,
            detail_builder=lambda payload: {
                "baseline_filter_status": payload.get("status"),
                "baseline_filter_total_rows": payload.get("total_rows"),
                "baseline_filter_filtered_rows": payload.get("filtered_rows"),
                "baseline_filter_rate": payload.get("filter_rate"),
            },
            input_contract=_phase_input_contract(mode, {"policy_mode": "deterministic_structural_physics", "cp_profile": "CP-2"}),
        )
        print("[REFRESH+CP2] Baseline filter report:")
        print(json.dumps(baseline_filter_report, indent=2))

        _write_resume_checkpoint(
            mode=mode,
            report=report,
            quote_cache_refresh_report=quote_cache_refresh_report,
            baseline_filter_report=baseline_filter_report,
        )

    runtime_sync_report, validation_report = _run_post_rebuild_pipeline(
        report=report,
        mode=mode,
        quote_cache_refresh_report=quote_cache_refresh_report,
    )
    quote_cache_refresh_report = _launch_quote_cache_refresh_followup(
        mode=mode,
        quote_cache_refresh_report=quote_cache_refresh_report,
    )

    _append_history_event({
        "phase": "complete",
        "status": "ok",
        "refresh_mode": mode,
        "refresh_report_status": report.get("status"),
        "rows_written": report.get("rows_written"),
        "elapsed_seconds": report.get("elapsed_seconds"),
        "cp_profile": "CP-2",
        "policy_mode": "deterministic_structural_physics",
        "baseline_filter_status": (baseline_filter_report or {}).get("status"),
        "baseline_filter_total_rows": (baseline_filter_report or {}).get("total_rows"),
        "baseline_filter_filtered_rows": (baseline_filter_report or {}).get("filtered_rows"),
        "quote_cache_refresh": quote_cache_refresh_report.get("status"),
        "quote_cache_profile_overrides": (quote_cache_refresh_report.get("profile_overrides") or {}).get("status"),
        "runtime_postgres_sync": runtime_sync_report.get("status"),
        "runtime_postgres_sync_run_id": runtime_sync_report.get("run_id"),
        "validation_gate_status": validation_report.get("status"),
        "validation_gate_report_run_id": validation_report.get("run_id"),
        "resume_checkpoint_used": resumed_from_checkpoint,
    })

    # CP-2: Regenerate quality audit JSON after every successful refresh so the
    # Admin UI never shows stale or zombie PSCF content.  This runs as a
    # best-effort step — failures are logged but do not abort the pipeline.
    try:
        import importlib.util as _ilu, pathlib as _pl
        _audit_src = _pl.Path(__file__).resolve().parent / "tools" / "cp2_quality_audit.py"
        _spec = _ilu.spec_from_file_location("cp2_quality_audit", _audit_src)
        _mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
        _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        _mod.run_audit()
        print("[REFRESH+CP2] Quality audit JSON regenerated.", flush=True)
    except Exception as _qa_exc:
        print(f"[REFRESH+CP2] Quality audit step failed (non-fatal): {_qa_exc}", flush=True)

    # CP-2: Fill financial data gaps for Accumulate tickers after every
    # successful refresh.  This runs as a best-effort step — failures are
    # logged but do not abort the pipeline.  Respects Polygon rate limits
    # (1.5 s between tickers) so a full 150-ticker pass takes ~4 minutes.
    try:
        import importlib.util as _ilu2, pathlib as _pl2
        _backfill_src = _pl2.Path(__file__).resolve().parent / "tools" / "backfill_accumulate_fundamentals.py"
        _spec2 = _ilu2.spec_from_file_location("backfill_accumulate_fundamentals", _backfill_src)
        _mod2 = _ilu2.module_from_spec(_spec2)  # type: ignore[arg-type]
        _spec2.loader.exec_module(_mod2)  # type: ignore[union-attr]
        _mod2.run()
        print("[REFRESH+CP2] Fundamentals gap-fill complete.", flush=True)
    except Exception as _bf_exc:
        print(f"[REFRESH+CP2] Fundamentals gap-fill failed (non-fatal): {_bf_exc}", flush=True)

    _clear_resume_checkpoint(mode=mode, reason="completed_successfully")

    # Auto-fire PEE-1 after every successful refresh.
    # PEE-1 checks auto_tfe_enabled internally — if OFF, it logs signals only.
    try:
        import subprocess as _sp, pathlib as _pl3
        _pee1_script = _pl3.Path(__file__).resolve().parent / "web" / "scripts" / "execution" / "pee1_runner.mjs"
        _node_bin = __import__("os").environ.get("TFE_NODE_BIN", "node")
        _env = {**__import__("os").environ, "PGSSLMODE": "require"}
        _pee1 = _sp.Popen([_node_bin, str(_pee1_script)], env=_env, stdin=_sp.DEVNULL, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, start_new_session=True)
        print(f"[REFRESH+PEE1] Execution engine launched (pid={_pee1.pid}).", flush=True)
    except Exception as _pee1_exc:
        print(f"[REFRESH+PEE1] Failed to launch execution engine (non-fatal): {_pee1_exc}", flush=True)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        _append_history_event({"phase": "complete", "status": "error", "error": str(error)})
        raise
