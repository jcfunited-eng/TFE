#!/usr/bin/env python3
"""
Run UF snapshot refresh and then run L5 policy learning pipeline.

This wrapper is the production entrypoint for admin refresh jobs so policy
learning is automatically executed after refresh without manual one-off steps.
"""

from __future__ import annotations

import argparse
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

from l5_policy_learning_pipeline import run_l5_policy_learning
from rebuild_uf_snapshot import (
    REFRESH_MODE_FULL,
    REFRESH_MODE_TARGETED,
    rebuild_snapshot,
)

DEFAULT_ORACLE_TARGET_RETURN_LIFT = 4.0
DEFAULT_ORACLE_SHORT_CYCLE_RUNS = 1
DEFAULT_ORACLE_TIMEOUT_SECONDS = 3600
DEFAULT_ORACLE_POLL_SECONDS = 1.0
EXPECTED_EPOCH_LIBRARY_SCHEMA = "v1"
DEFAULT_ORACLE_TRIGGER_POLICY = "scheduled_or_explicit"
DEFAULT_RESUME_MAX_AGE_SECONDS = 6 * 60 * 60
RESUME_STAGE_POST_L5_PRE_ORACLE = "post_l5_pre_oracle"
QUOTE_CACHE_FOLLOWUP_LANE = "post_publication_followup"


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
    except Exception:
        # Do not interrupt refresh execution on history-write issues.
        pass


def _resume_checkpoint_dir() -> Path:
    raw = str(os.environ.get("TFE_REFRESH_RESUME_CHECKPOINT_DIR", "")).strip()
    if raw:
        return Path(raw)
    return Path("backups/runtime/refresh_resume")


def _resume_checkpoint_path(mode: str) -> Path:
    mode_key = "targeted" if mode == REFRESH_MODE_TARGETED else "full"
    return _resume_checkpoint_dir() / f"{mode_key}.json"


def _checkpoint_mode_key(mode: str) -> str:
    return "targeted" if mode == REFRESH_MODE_TARGETED else "full"


def _resume_checkpoint_s3_uri(mode: str) -> str:
    raw = str(os.environ.get("TFE_REFRESH_RESUME_S3_URI", "")).strip()
    if not raw:
        return ""
    # Normalize malformed placeholder variants seen in env propagation.
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
        completed = subprocess.run(
            args,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if completed.returncode == 0:
        return True, ""
    stderr = str(completed.stderr or "").strip()
    stdout = str(completed.stdout or "").strip()
    tail = stderr or stdout or "unknown aws cli failure"
    return False, tail


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
        print(f"[REFRESH+L5] Resume checkpoint downloaded from S3: {s3_uri} -> {checkpoint_path}")
        return
    fallback_ok, fallback_err = _download_from_s3_boto3(s3_uri=s3_uri, local_path=checkpoint_path)
    if fallback_ok:
        reason = "aws cli missing" if _aws_cli_missing(err) else "aws cli cp failed"
        print(
            f"[REFRESH+L5] Resume checkpoint downloaded from S3 via boto3 ({reason}): "
            f"{s3_uri} -> {checkpoint_path}"
        )
    else:
        print(
            f"[REFRESH+L5] Resume checkpoint S3 download skipped: uri={s3_uri} "
            f"aws_cli_reason={err}; boto3_reason={fallback_err}"
        )


def _upload_resume_checkpoint_to_s3(*, mode: str, checkpoint_path: Path) -> None:
    s3_uri = _resume_checkpoint_s3_uri(mode)
    if not s3_uri:
        return
    ok, err = _run_aws_cli(["aws", "s3", "cp", str(checkpoint_path), s3_uri, "--only-show-errors"])
    if ok:
        print(f"[REFRESH+L5] Resume checkpoint uploaded to S3: {checkpoint_path} -> {s3_uri}")
        return
    fallback_ok, fallback_err = _upload_to_s3_boto3(local_path=checkpoint_path, s3_uri=s3_uri)
    if fallback_ok:
        reason = "aws cli missing" if _aws_cli_missing(err) else "aws cli cp failed"
        print(
            f"[REFRESH+L5] Resume checkpoint uploaded to S3 via boto3 ({reason}): "
            f"{checkpoint_path} -> {s3_uri}"
        )
    else:
        print(
            f"[REFRESH+L5] Resume checkpoint S3 upload skipped: path={checkpoint_path} uri={s3_uri} "
            f"aws_cli_reason={err}; boto3_reason={fallback_err}"
        )


def _clear_resume_checkpoint_s3(*, mode: str, archive_name: str) -> None:
    s3_uri = _resume_checkpoint_s3_uri(mode)
    if not s3_uri:
        return
    prefix, _, _name = s3_uri.rpartition("/")
    if not prefix:
        print(f"[REFRESH+L5] Resume checkpoint S3 cleanup skipped: unsupported uri={s3_uri}")
        return
    archive_uri = f"{prefix}/{archive_name}"
    ok_copy, err_copy = _run_aws_cli(["aws", "s3", "cp", s3_uri, archive_uri, "--only-show-errors"])
    if ok_copy:
        print(f"[REFRESH+L5] Resume checkpoint archived in S3: {archive_uri}")
    else:
        fallback_copy_ok, fallback_copy_err = _copy_s3_boto3(src_s3_uri=s3_uri, dst_s3_uri=archive_uri)
        if fallback_copy_ok:
            reason = "aws cli missing" if _aws_cli_missing(err_copy) else "aws cli cp failed"
            print(f"[REFRESH+L5] Resume checkpoint archived in S3 via boto3 ({reason}): {archive_uri}")
        else:
            print(
                f"[REFRESH+L5] Resume checkpoint S3 archive skipped: uri={s3_uri} "
                f"aws_cli_reason={err_copy}; boto3_reason={fallback_copy_err}"
            )
    ok_rm, err_rm = _run_aws_cli(["aws", "s3", "rm", s3_uri, "--only-show-errors"])
    if ok_rm:
        print(f"[REFRESH+L5] Resume checkpoint removed from S3: {s3_uri}")
    else:
        fallback_rm_ok, fallback_rm_err = _delete_s3_boto3(s3_uri=s3_uri)
        if fallback_rm_ok:
            reason = "aws cli missing" if _aws_cli_missing(err_rm) else "aws cli rm failed"
            print(f"[REFRESH+L5] Resume checkpoint removed from S3 via boto3 ({reason}): {s3_uri}")
        else:
            print(
                f"[REFRESH+L5] Resume checkpoint S3 remove skipped: uri={s3_uri} "
                f"aws_cli_reason={err_rm}; boto3_reason={fallback_rm_err}"
            )


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
        print(f"[REFRESH+L5] Ignoring unreadable resume checkpoint {checkpoint_path}: {type(exc).__name__}: {exc}")
        return None

    if not isinstance(payload, dict):
        print(f"[REFRESH+L5] Ignoring malformed resume checkpoint {checkpoint_path}: payload is not an object.")
        return None

    stage = str(payload.get("stage", "")).strip()
    if stage != RESUME_STAGE_POST_L5_PRE_ORACLE:
        print(
            f"[REFRESH+L5] Ignoring resume checkpoint {checkpoint_path}: "
            f"unsupported stage={stage or 'missing'}."
        )
        return None

    checkpoint_mode = str(payload.get("mode", "")).strip()
    if checkpoint_mode != mode:
        print(
            f"[REFRESH+L5] Ignoring resume checkpoint {checkpoint_path}: "
            f"mode mismatch checkpoint={checkpoint_mode or 'missing'} requested={mode}."
        )
        return None

    refresh_report = payload.get("refresh_report")
    quote_cache_refresh_report = payload.get("quote_cache_refresh_report")
    l5_learning_report = payload.get("l5_learning_report")
    if not isinstance(refresh_report, dict) or not isinstance(quote_cache_refresh_report, dict) or not isinstance(l5_learning_report, dict):
        print(
            f"[REFRESH+L5] Ignoring resume checkpoint {checkpoint_path}: "
            "required report payloads are missing or invalid."
        )
        return None

    max_age_seconds = _read_env_int(
        "TFE_REFRESH_RESUME_MAX_AGE_SECONDS",
        default_value=DEFAULT_RESUME_MAX_AGE_SECONDS,
        minimum=60,
    )
    written_at_utc = _parse_iso_utc(str(payload.get("written_at_utc", "")))
    if written_at_utc is not None:
        age_seconds = (datetime.now(timezone.utc) - written_at_utc).total_seconds()
        if age_seconds > float(max_age_seconds):
            print(
                f"[REFRESH+L5] Ignoring stale resume checkpoint {checkpoint_path}: "
                f"age_seconds={age_seconds:.1f} max_age_seconds={max_age_seconds}."
            )
            return None

    payload["_checkpoint_path"] = str(checkpoint_path)
    return payload


def _write_resume_checkpoint(
    *,
    mode: str,
    report: dict[str, Any],
    quote_cache_refresh_report: dict[str, Any],
    l5_learning_report: dict[str, Any],
) -> Path:
    checkpoint_path = _resume_checkpoint_path(mode)
    checkpoint_payload = {
        "stage": RESUME_STAGE_POST_L5_PRE_ORACLE,
        "mode": mode,
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
        "trigger_source": _normalize_trigger_source(),
        "refresh_report": report,
        "quote_cache_refresh_report": quote_cache_refresh_report,
        "l5_learning_report": l5_learning_report,
    }
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps(checkpoint_payload, indent=2), encoding="utf-8")
    print(f"[REFRESH+L5] Resume checkpoint written: {checkpoint_path}")
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
        print(f"[REFRESH+L5] Resume checkpoint archived: {archive_path} reason={reason}")
        _clear_resume_checkpoint_s3(mode=mode, archive_name=archive_name)
        return
    except Exception:
        pass

    try:
        checkpoint_path.unlink(missing_ok=True)
        print(f"[REFRESH+L5] Resume checkpoint cleared: {checkpoint_path} reason={reason}")
        _clear_resume_checkpoint_s3(mode=mode, archive_name=archive_name)
    except Exception:
        # Checkpoint cleanup should never fail the refresh run.
        return


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh UF snapshot and run L5 policy learning.")
    parser.add_argument(
        "--refresh-mode",
        choices=[REFRESH_MODE_FULL, REFRESH_MODE_TARGETED],
        default=REFRESH_MODE_FULL,
    )
    parser.add_argument(
        "--targeted-refresh",
        action="store_true",
        help="Shortcut for --refresh-mode targeted_pfsc.",
    )
    parser.add_argument(
        "--force-refresh-universe",
        action="store_true",
        help="Refresh universe caches from Massive before rebuild.",
    )
    parser.add_argument(
        "--years-history",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--skip-l5-learning",
        action="store_true",
        help="Run refresh only and skip policy learning pipeline.",
    )
    parser.add_argument(
        "--run-l5-on-targeted",
        action="store_true",
        help="Also run L5 learning after targeted refresh mode.",
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        action="store_true",
        help="Resume from the latest post-L5 checkpoint when available.",
    )
    parser.add_argument(
        "--quote-cache-followup-only",
        action="store_true",
        help="Run only the detached quote-cache follow-up lane.",
    )
    return parser.parse_args()


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
    print(
        f"[REFRESH+L5] {phase_label} starting. cwd={cwd}; cmd={_format_command(cmd)}",
        flush=True,
    )
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=1,
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
                    print(f"[REFRESH+L5][{phase_label}][{stream_name}] {line}", flush=True)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    stdout_thread = threading.Thread(
        target=_pump_stream,
        args=(process.stdout, "stdout", stdout_lines, stdout_tail),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_pump_stream,
        args=(process.stderr, "stderr", stderr_lines, stderr_tail),
        daemon=True,
    )
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
                    f"[REFRESH+L5] {phase_label} still running. "
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
    print(
        f"[REFRESH+L5] {phase_label} completed. "
        f"exit_code={return_code}; elapsed_seconds={elapsed_seconds:.1f}",
        flush=True,
    )
    return {
        "returncode": return_code,
        "stdout": stdout_text,
        "stderr": stderr_text,
        "stdout_tail": stdout_tail_text,
        "stderr_tail": stderr_tail_text,
        "elapsed_seconds": elapsed_seconds,
    }


def _run_quote_cache_refresh() -> dict[str, Any]:
    enabled_raw = str(os.environ.get("TFE_REFRESH_REBUILD_QUOTE_CACHE", "1")).strip().lower()
    if enabled_raw in {"0", "false", "no", "off"}:
        return {
            "status": "skipped",
            "reason": "disabled_by_env",
        }

    workers = _read_env_int("TFE_QUOTE_CACHE_WORKERS", default_value=12, minimum=1)
    timeout_sec = _read_env_int("TFE_QUOTE_CACHE_TIMEOUT_SEC", default_value=35, minimum=5)
    min_non_meta_fields = _read_env_int("TFE_QUOTE_CACHE_MIN_NON_META_FIELDS", default_value=20, minimum=1)
    save_every = _read_env_int("TFE_QUOTE_CACHE_SAVE_EVERY", default_value=200, minimum=1)
    skip_finviz_refresh = str(os.environ.get("TFE_REFRESH_SKIP_FINVIZ_REFRESH", "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    cmd = [
        sys.executable or "python3",
        "-u",
        "web/scripts/build_screener_quote_cache.py",
        "--workers",
        str(workers),
        "--timeout-sec",
        str(timeout_sec),
        "--save-every",
        str(save_every),
        "--min-non-meta-fields",
        str(min_non_meta_fields),
    ]
    if skip_finviz_refresh:
        cmd.append("--skip-finviz-refresh")

    completed = _run_logged_subprocess(
        phase_label="quote_cache_refresh",
        cmd=cmd,
        cwd=str(Path.cwd()),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RuntimeError(
            "Quote cache refresh failed. "
            f"exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}"
        )

    summary: dict[str, Any] = {
        "status": "ok",
        "workers": workers,
        "timeout_sec": timeout_sec,
        "min_non_meta_fields": min_non_meta_fields,
        "skip_finviz_refresh": skip_finviz_refresh,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }

    run_profile_overrides_raw = str(os.environ.get("TFE_REFRESH_BUILD_PROFILE_OVERRIDES", "1")).strip().lower()
    if run_profile_overrides_raw in {"0", "false", "no", "off"}:
        summary["profile_overrides"] = {"status": "skipped", "reason": "disabled_by_env"}
        return summary

    profile_workers = _read_env_int("TFE_PROFILE_OVERRIDE_WORKERS", default_value=8, minimum=1)
    profile_timeout_sec = _read_env_int("TFE_PROFILE_OVERRIDE_TIMEOUT_SEC", default_value=45, minimum=5)
    profile_save_every = _read_env_int("TFE_PROFILE_OVERRIDE_SAVE_EVERY", default_value=200, minimum=1)
    profile_limit = _read_env_int("TFE_PROFILE_OVERRIDE_LIMIT", default_value=0, minimum=0)
    profile_cmd = [
        sys.executable or "python3",
        "-u",
        "web/scripts/build_screener_profile_overrides.py",
        "--workers",
        str(profile_workers),
        "--timeout-sec",
        str(profile_timeout_sec),
        "--save-every",
        str(profile_save_every),
        "--limit",
        str(profile_limit),
    ]

    profile_completed = _run_logged_subprocess(
        phase_label="profile_overrides_refresh",
        cmd=profile_cmd,
        cwd=str(Path.cwd()),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    profile_stdout_tail = str(profile_completed.get("stdout_tail") or "").strip()
    profile_stderr_tail = str(profile_completed.get("stderr_tail") or "").strip()
    if int(profile_completed.get("returncode") or 0) != 0:
        raise RuntimeError(
            "Profile override refresh failed. "
            f"exit_code={profile_completed.get('returncode')}; stdout_tail={profile_stdout_tail or 'n/a'}; stderr_tail={profile_stderr_tail or 'n/a'}"
        )

    summary["profile_overrides"] = {
        "status": "ok",
        "workers": profile_workers,
        "timeout_sec": profile_timeout_sec,
        "limit": profile_limit,
        "stdout_tail": profile_stdout_tail,
        "stderr_tail": profile_stderr_tail,
    }
    return summary


def _quote_cache_refresh_detail_payload(payload: dict[str, Any]) -> dict[str, Any]:
    profile_overrides = payload.get("profile_overrides")
    return {
        "quote_cache_refresh": payload.get("status"),
        "quote_cache_profile_overrides": profile_overrides.get("status")
        if isinstance(profile_overrides, dict)
        else None,
        "quote_cache_lane": payload.get("lane"),
        "quote_cache_followup_pid": payload.get("followup_pid"),
    }


def _should_defer_quote_cache_refresh(mode: str) -> bool:
    return mode == REFRESH_MODE_FULL


def _deferred_quote_cache_refresh_report() -> dict[str, Any]:
    return {
        "status": "deferred",
        "lane": QUOTE_CACHE_FOLLOWUP_LANE,
        "reason": "full_universe_publish_should_not_wait_on_quote_cache_refresh",
    }


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
    cmd = [
        sys.executable or "python3",
        "-u",
        str(script_path),
        "--refresh-mode",
        mode,
        "--quote-cache-followup-only",
    ]

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["TFE_REFRESH_QUOTE_CACHE_FOLLOWUP"] = "1"

    try:
        child = subprocess.Popen(
            cmd,
            cwd=str(Path.cwd()),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=_stream_fileno(sys.stdout, 1),
            stderr=_stream_fileno(sys.stderr, 2),
            start_new_session=True,
        )
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        print(f"[REFRESH+L5] Quote cache follow-up launch failed. error={error_text}", flush=True)
        _append_history_event(
            {
                "phase": "quote_cache_refresh_followup_launch_failed",
                "status": "error",
                "lane": QUOTE_CACHE_FOLLOWUP_LANE,
                "error": error_text,
            }
        )
        return {
            "status": "launch_failed",
            "lane": QUOTE_CACHE_FOLLOWUP_LANE,
            "reason": "detached_followup_launch_failed",
            "error": error_text,
        }

    print(
        "[REFRESH+L5] Quote cache follow-up launched. "
        f"pid={child.pid}; lane={QUOTE_CACHE_FOLLOWUP_LANE}",
        flush=True,
    )
    _append_history_event(
        {
            "phase": "quote_cache_refresh_followup_launch",
            "status": "launched",
            "lane": QUOTE_CACHE_FOLLOWUP_LANE,
            "pid": child.pid,
        }
    )
    return {
        "status": "launched",
        "lane": QUOTE_CACHE_FOLLOWUP_LANE,
        "reason": "detached_followup_launched_after_publication",
        "followup_pid": child.pid,
    }


def _run_runtime_postgres_sync(
    report: dict[str, Any],
    mode: str,
    optimizer_summary: dict[str, Any] | None,
    optimizer_short_cycle_status: str,
    epoch_schema: str | None,
    epoch_status: str | None,
) -> dict[str, Any]:
    script_path = Path("web/scripts/sync_runtime_postgres.mjs")
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Runtime sync script is missing: {script_path}")

    env = dict(os.environ)
    env.setdefault("TFE_REFRESH_REQUESTED_MODE", mode)
    env.setdefault("TFE_REFRESH_COMPLETED_AT", datetime.now(timezone.utc).isoformat())
    env.setdefault("TFE_REFRESH_STARTED_AT", str(os.environ.get("TFE_REFRESH_STARTED_AT", "")).strip() or datetime.now(timezone.utc).isoformat())

    if optimizer_summary:
        env["TFE_OPTIMIZER_SHORT_CYCLE"] = str(optimizer_short_cycle_status or "run")
        env["TFE_OPTIMIZER_CYCLE_REQUESTED_RUNS"] = str(optimizer_summary.get("requested_additional_runs") or "")
        env["TFE_OPTIMIZER_CYCLE_COMPLETED_RUNS"] = str(optimizer_summary.get("actual_additional_runs") or "")
        env["TFE_OPTIMIZER_SESSION_ID"] = str(optimizer_summary.get("session_id") or "")
        optimizer_target = _float_or_none(optimizer_summary.get("success_target_return_lift_pct")) or DEFAULT_ORACLE_TARGET_RETURN_LIFT
        env["TFE_OPTIMIZER_TARGET_RETURN_LIFT_PCT"] = str(optimizer_target)
        optimizer_end = optimizer_summary.get("end")
        optimizer_best_score = _float_or_none(optimizer_end.get("best_score")) if isinstance(optimizer_end, dict) else None
        env["TFE_OPTIMIZER_BEST_SCORE"] = "" if optimizer_best_score is None else str(optimizer_best_score)
        env["TFE_OPTIMIZER_TARGET_MET"] = "true" if _is_target_met(optimizer_summary) else "false"
    else:
        env["TFE_OPTIMIZER_SHORT_CYCLE"] = str(optimizer_short_cycle_status or "not_run")
        env["TFE_OPTIMIZER_CYCLE_REQUESTED_RUNS"] = ""
        env["TFE_OPTIMIZER_CYCLE_COMPLETED_RUNS"] = ""
        env["TFE_OPTIMIZER_SESSION_ID"] = ""
        env["TFE_OPTIMIZER_TARGET_RETURN_LIFT_PCT"] = ""
        env["TFE_OPTIMIZER_BEST_SCORE"] = ""
        env["TFE_OPTIMIZER_TARGET_MET"] = ""

    env["TFE_EPOCH_LIBRARY_CONFIDENCE_SCHEMA"] = str(epoch_schema or "")
    env["TFE_EPOCH_LIBRARY_STATUS"] = str(epoch_status or "")

    cmd = ["node", str(script_path)]
    completed = _run_logged_subprocess(
        phase_label="runtime_postgres_sync",
        cmd=cmd,
        cwd=str(Path.cwd()),
        env=env,
    )
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RuntimeError(
            "Runtime Postgres sync failed. "
            f"exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}"
        )

    payload = _extract_json_payload(str(completed.get("stdout") or ""))
    payload.setdefault("refresh_report_status", report.get("status"))
    return payload


def _run_validation_gate() -> dict[str, Any]:
    script_path = Path("web/scripts/run_validation_gate_v1.mjs")
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Validation gate script is missing: {script_path}")

    cmd = ["node", str(script_path)]
    completed = _run_logged_subprocess(
        phase_label="validation_gate",
        cmd=cmd,
        cwd=str(Path.cwd()),
        env=dict(os.environ),
    )
    stdout_tail = str(completed.get("stdout_tail") or "").strip()
    stderr_tail = str(completed.get("stderr_tail") or "").strip()
    if int(completed.get("returncode") or 0) != 0:
        raise RuntimeError(
            "Validation gate failed. "
            f"exit_code={completed.get('returncode')}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}"
        )

    payload = _extract_json_payload(str(completed.get("stdout") or ""))
    status = str(payload.get("status", "")).strip().lower()
    if status != "pass":
        raise RuntimeError(f"Validation gate returned non-pass status: {status or 'missing'}")
    return payload


def _extract_json_payload(stdout_text: str) -> dict[str, Any]:
    raw = stdout_text.strip()
    if not raw:
        raise RuntimeError("Oracle optimizer short-cycle returned empty stdout.")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    first = raw.find("{")
    last = raw.rfind("}")
    if first < 0 or last < first:
        raise RuntimeError("Oracle optimizer short-cycle did not output JSON payload.")

    try:
        parsed = json.loads(raw[first : last + 1])
    except Exception as exc:
        raise RuntimeError(f"Failed to parse oracle optimizer JSON payload: {type(exc).__name__}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Oracle optimizer payload is not a JSON object.")
    return parsed


def _run_oracle_optimizer_short_cycle(*, mode: str) -> dict[str, Any]:
    oracle_program_path = Path("tools/oracle_program/oracle_program.py")
    if not oracle_program_path.exists() or not oracle_program_path.is_file():
        raise FileNotFoundError(f"Oracle optimizer program is missing: {oracle_program_path}")

    runs = _read_env_int(
        "TFE_REFRESH_ORACLE_SHORT_CYCLE_RUNS",
        default_value=DEFAULT_ORACLE_SHORT_CYCLE_RUNS,
        minimum=1,
    )
    timeout_seconds = _read_env_int(
        "TFE_REFRESH_ORACLE_TIMEOUT_SECONDS",
        default_value=DEFAULT_ORACLE_TIMEOUT_SECONDS,
        minimum=60,
    )
    poll_seconds = _read_env_float(
        "TFE_REFRESH_ORACLE_POLL_SECONDS",
        default_value=DEFAULT_ORACLE_POLL_SECONDS,
        minimum=0.2,
    )
    no_progress_timeout_override = str(os.environ.get("TFE_REFRESH_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS", "")).strip()
    if no_progress_timeout_override:
        no_progress_timeout_seconds = _read_env_int(
            "TFE_REFRESH_ORACLE_NO_PROGRESS_TIMEOUT_SECONDS",
            default_value=120,
            minimum=30,
        )
    else:
        # Full refresh can spend longer before completing first optimizer run; keep targeted stricter.
        no_progress_timeout_seconds = 120 if mode == REFRESH_MODE_TARGETED else 900

    cmd = [
        sys.executable or "python3",
        str(oracle_program_path),
        "short-cycle",
        "--runs",
        str(runs),
        "--poll-seconds",
        str(poll_seconds),
        "--timeout-seconds",
        str(timeout_seconds),
        "--no-progress-timeout-seconds",
        str(no_progress_timeout_seconds),
    ]
    hard_timeout_seconds = timeout_seconds + 120
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(Path.cwd()),
            text=True,
            capture_output=True,
            check=False,
            timeout=hard_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_tail = "\n".join(str(exc.stdout or "").splitlines()[-12:]).strip()
        stderr_tail = "\n".join(str(exc.stderr or "").splitlines()[-12:]).strip()
        raise RuntimeError(
            "Oracle optimizer short-cycle timed out. "
            f"timeout_seconds={hard_timeout_seconds}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}"
        ) from exc
    if completed.returncode != 0:
        stderr_tail = "\n".join(completed.stderr.splitlines()[-12:]).strip()
        stdout_tail = "\n".join(completed.stdout.splitlines()[-12:]).strip()
        raise RuntimeError(
            "Oracle optimizer short-cycle failed. "
            f"exit_code={completed.returncode}; stdout_tail={stdout_tail or 'n/a'}; stderr_tail={stderr_tail or 'n/a'}"
        )

    summary = _extract_json_payload(completed.stdout)
    summary.setdefault("requested_runs_effective", runs)
    summary.setdefault("timeout_seconds_effective", timeout_seconds)
    summary.setdefault("poll_seconds_effective", poll_seconds)
    summary.setdefault("no_progress_timeout_seconds_effective", no_progress_timeout_seconds)
    summary.setdefault("refresh_mode_effective", mode)
    return summary


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _is_target_met(summary: dict[str, Any]) -> bool:
    target_met = summary.get("target_met_for_prepare_promote")
    if isinstance(target_met, bool):
        return target_met

    target = _float_or_none(summary.get("success_target_return_lift_pct"))
    end = summary.get("end")
    best = _float_or_none(end.get("best_score")) if isinstance(end, dict) else None
    if target is None:
        target = DEFAULT_ORACLE_TARGET_RETURN_LIFT
    if best is None:
        return False
    return bool(best >= target)


def _epoch_schema(summary: dict[str, Any]) -> str | None:
    schema = summary.get("epoch_library_confidence_schema")
    if isinstance(schema, str) and schema.strip():
        return schema.strip()

    end = summary.get("end")
    if isinstance(end, dict):
        nested = end.get("latest_epoch_library_confidence_schema")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return None


def _safe_int(value: Any, default_value: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default_value


def _should_skip_oracle_short_cycle(mode: str, report: dict[str, Any]) -> bool:
    if mode != REFRESH_MODE_TARGETED:
        return False

    status = str(report.get("status", "")).strip().lower()
    if status == "no_rows_written":
        return True

    if _safe_int(report.get("rows_written"), default_value=0) <= 0:
        return True

    targeted_selector = report.get("targeted_selector")
    if isinstance(targeted_selector, dict):
        if _safe_int(targeted_selector.get("selected_union"), default_value=0) <= 0:
            return True

    return False


def _is_truthy(raw: str) -> bool:
    normalized = str(raw).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _normalize_trigger_source() -> str:
    raw = str(os.environ.get("TFE_REFRESH_TRIGGER_SOURCE", "program")).strip().lower()
    if raw in {"manual", "scheduled", "program"}:
        return raw
    if raw:
        return raw
    return "program"


def _resolve_oracle_execution_plan(mode: str, report: dict[str, Any]) -> dict[str, Any]:
    if _should_skip_oracle_short_cycle(mode=mode, report=report):
        return {
            "should_run": False,
            "status": "skipped_targeted_no_rows",
            "reason": "targeted_refresh_no_rows_written",
            "trigger_source": _normalize_trigger_source(),
            "policy": "targeted_no_rows_skip_rule",
            "explicit_allow": False,
        }

    trigger_source = _normalize_trigger_source()
    policy_raw = str(os.environ.get("TFE_REFRESH_ORACLE_TRIGGER_POLICY", DEFAULT_ORACLE_TRIGGER_POLICY)).strip().lower()
    policy = policy_raw or DEFAULT_ORACLE_TRIGGER_POLICY
    explicit_allow = _is_truthy(os.environ.get("TFE_REFRESH_ORACLE_ALLOW_SHORT_CYCLE", "0"))

    if policy == "always":
        should_run = True
        reason = "policy_always"
    elif policy == "scheduled_only":
        should_run = trigger_source == "scheduled"
        reason = "scheduled_required"
    elif policy == "explicit_only":
        should_run = explicit_allow
        reason = "explicit_allow_required"
    else:
        # Default and fallback policy: only scheduled runs or explicit opt-in.
        policy = DEFAULT_ORACLE_TRIGGER_POLICY
        should_run = trigger_source == "scheduled" or explicit_allow
        reason = "scheduled_or_explicit"

    status = "run" if should_run else "skipped_by_trigger_policy"
    return {
        "should_run": should_run,
        "status": status,
        "reason": reason,
        "trigger_source": trigger_source,
        "policy": policy,
        "explicit_allow": explicit_allow,
    }


def _resolve_latest_anomaly_policy_path() -> Path | None:
    env_path = str(os.environ.get("TFE_POLICY_ANOMALY_POLICY", "")).strip()
    if env_path:
        p = Path(env_path)
        if p.exists() and p.is_file():
            return p

    candidates = sorted(
        Path("backups").glob("pscf-policy-anomaly-watch-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for candidate in candidates:
        # Exclude report artifacts; we need policy artifacts with cells.
        if "-report-" in candidate.name:
            continue
        return candidate

    return None


def _ensure_learning_env() -> None:
    resolved = _resolve_latest_anomaly_policy_path()
    if resolved is not None:
        os.environ["TFE_POLICY_ANOMALY_POLICY"] = str(resolved)


def _run_post_rebuild_phase(
    *,
    phase_name: str,
    runner: Any,
    detail_builder: Any | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    _append_history_event(
        {
            "phase": f"{phase_name}_start",
            "status": "running",
        }
    )
    print(f"[REFRESH+L5] Post-rebuild phase start: {phase_name}", flush=True)
    try:
        result = runner()
    except Exception as exc:
        elapsed_seconds = time.monotonic() - started_at
        error_text = f"{type(exc).__name__}: {exc}"
        print(
            f"[REFRESH+L5] Post-rebuild phase failed: {phase_name}; "
            f"elapsed_seconds={elapsed_seconds:.1f}; error={error_text}",
            flush=True,
        )
        _append_history_event(
            {
                "phase": f"{phase_name}_failed",
                "status": "error",
                "elapsed_seconds": elapsed_seconds,
                "error": error_text,
            }
        )
        raise

    if not isinstance(result, dict):
        raise RuntimeError(f"Post-rebuild phase {phase_name} returned non-dict result.")

    elapsed_seconds = time.monotonic() - started_at
    detail_payload = detail_builder(result) if callable(detail_builder) else {}
    if not isinstance(detail_payload, dict):
        detail_payload = {}
    phase_status = str(result.get("status") or "ok")
    print(
        f"[REFRESH+L5] Post-rebuild phase complete: {phase_name}; "
        f"elapsed_seconds={elapsed_seconds:.1f}; status={phase_status}",
        flush=True,
    )
    _append_history_event(
        {
            "phase": f"{phase_name}_complete",
            "status": phase_status,
            "elapsed_seconds": elapsed_seconds,
            **detail_payload,
        }
    )
    return result


def _run_post_rebuild_pipeline(
    *,
    report: dict[str, Any],
    mode: str,
    optimizer_summary: dict[str, Any] | None,
    optimizer_short_cycle_status: str,
    epoch_schema: str | None,
    epoch_status: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime_sync_report = _run_post_rebuild_phase(
        phase_name="runtime_postgres_sync",
        runner=lambda: _run_runtime_postgres_sync(
            report=report,
            mode=mode,
            optimizer_summary=optimizer_summary,
            optimizer_short_cycle_status=optimizer_short_cycle_status,
            epoch_schema=epoch_schema,
            epoch_status=epoch_status,
        ),
        detail_builder=lambda payload: {
            "runtime_postgres_sync": payload.get("status"),
            "runtime_postgres_sync_run_id": payload.get("run_id"),
        },
    )
    validation_report = _run_post_rebuild_phase(
        phase_name="validation_gate",
        runner=_run_validation_gate,
        detail_builder=lambda payload: {
            "validation_gate_status": payload.get("status"),
            "validation_gate_report_run_id": payload.get("run_id"),
        },
    )
    return runtime_sync_report, validation_report


def main() -> int:
    args = _parse_args()

    mode = str(args.refresh_mode)
    if bool(args.targeted_refresh):
        mode = REFRESH_MODE_TARGETED

    if bool(args.quote_cache_followup_only):
        quote_cache_refresh_report = _run_post_rebuild_phase(
            phase_name="quote_cache_refresh_followup",
            runner=_run_quote_cache_refresh,
            detail_builder=_quote_cache_refresh_detail_payload,
        )
        print("[REFRESH+L5] Quote cache refresh follow-up report:")
        print(json.dumps(quote_cache_refresh_report, indent=2))
        return 0

    resume_enabled = bool(args.resume_from_checkpoint) or _is_truthy(os.environ.get("TFE_REFRESH_RESUME_FROM_CHECKPOINT", "1"))
    resume_payload = _load_resume_checkpoint(mode=mode, enabled=resume_enabled)
    resumed_from_checkpoint = resume_payload is not None
    l5_report: dict[str, Any] | None = None

    if resumed_from_checkpoint:
        report = dict(resume_payload.get("refresh_report") or {})
        quote_cache_refresh_report = dict(resume_payload.get("quote_cache_refresh_report") or {})
        l5_report = dict(resume_payload.get("l5_learning_report") or {})
        checkpoint_path = str(resume_payload.get("_checkpoint_path") or _resume_checkpoint_path(mode))
        print(
            "[REFRESH+L5] Resume checkpoint loaded. "
            f"path={checkpoint_path}; stage={resume_payload.get('stage')}; mode={mode}"
        )
        print("[REFRESH+L5] Refresh report (from checkpoint):")
        print(json.dumps(report, indent=2))
        print("[REFRESH+L5] Quote cache refresh report (from checkpoint):")
        print(json.dumps(quote_cache_refresh_report, indent=2))
    else:
        report = rebuild_snapshot(
            refresh_mode=mode,
            force_refresh_universe=bool(args.force_refresh_universe),
            years_history=int(args.years_history),
        )

        print("[REFRESH+L5] Refresh report:")
        print(json.dumps(report, indent=2))

        if _should_defer_quote_cache_refresh(mode):
            quote_cache_refresh_report = _deferred_quote_cache_refresh_report()
            print(
                "[REFRESH+L5] Quote cache refresh deferred. "
                f"lane={QUOTE_CACHE_FOLLOWUP_LANE}; reason={quote_cache_refresh_report.get('reason')}",
                flush=True,
            )
            _append_history_event(
                {
                    "phase": "quote_cache_refresh_deferred",
                    "status": "deferred",
                    "lane": QUOTE_CACHE_FOLLOWUP_LANE,
                    "reason": quote_cache_refresh_report.get("reason"),
                }
            )
        else:
            quote_cache_refresh_report = _run_post_rebuild_phase(
                phase_name="quote_cache_refresh",
                runner=_run_quote_cache_refresh,
                detail_builder=_quote_cache_refresh_detail_payload,
            )
        print("[REFRESH+L5] Quote cache refresh report:")
        print(json.dumps(quote_cache_refresh_report, indent=2))

    if bool(args.skip_l5_learning):
        runtime_sync_report, validation_report = _run_post_rebuild_pipeline(
            report=report,
            mode=mode,
            optimizer_summary=None,
            optimizer_short_cycle_status="skipped_by_skip_l5_learning",
            epoch_schema=None,
            epoch_status=None,
        )
        quote_cache_refresh_report = _launch_quote_cache_refresh_followup(
            mode=mode,
            quote_cache_refresh_report=quote_cache_refresh_report,
        )
        print("[REFRESH+L5] L5 learning skipped by flag.")
        _append_history_event(
            {
                "phase": "complete",
                "status": "ok",
                "refresh_mode": mode,
                "refresh_report_status": report.get("status"),
                "rows_written": report.get("rows_written"),
                "elapsed_seconds": report.get("elapsed_seconds"),
                "l5_learning": "skipped",
                "quote_cache_refresh": quote_cache_refresh_report.get("status"),
                "quote_cache_profile_overrides": (
                    quote_cache_refresh_report.get("profile_overrides") or {}
                ).get("status"),
                "runtime_postgres_sync": runtime_sync_report.get("status"),
                "runtime_postgres_sync_run_id": runtime_sync_report.get("run_id"),
                "validation_gate_status": validation_report.get("status"),
                "validation_gate_report_run_id": validation_report.get("run_id"),
                "resume_checkpoint_used": resumed_from_checkpoint,
            }
        )
        _clear_resume_checkpoint(mode=mode, reason="completed_with_skip_l5_learning")
        return 0

    should_run_l5 = mode == REFRESH_MODE_FULL or bool(args.run_l5_on_targeted)
    if not should_run_l5:
        runtime_sync_report, validation_report = _run_post_rebuild_pipeline(
            report=report,
            mode=mode,
            optimizer_summary=None,
            optimizer_short_cycle_status="skipped_targeted_no_l5",
            epoch_schema=None,
            epoch_status=None,
        )
        quote_cache_refresh_report = _launch_quote_cache_refresh_followup(
            mode=mode,
            quote_cache_refresh_report=quote_cache_refresh_report,
        )
        print("[REFRESH+L5] L5 learning not run for targeted mode unless --run-l5-on-targeted is set.")
        _append_history_event(
            {
                "phase": "complete",
                "status": "ok",
                "refresh_mode": mode,
                "refresh_report_status": report.get("status"),
                "rows_written": report.get("rows_written"),
                "elapsed_seconds": report.get("elapsed_seconds"),
                "l5_learning": "not_run_for_targeted_mode",
                "quote_cache_refresh": quote_cache_refresh_report.get("status"),
                "quote_cache_profile_overrides": (
                    quote_cache_refresh_report.get("profile_overrides") or {}
                ).get("status"),
                "runtime_postgres_sync": runtime_sync_report.get("status"),
                "runtime_postgres_sync_run_id": runtime_sync_report.get("run_id"),
                "validation_gate_status": validation_report.get("status"),
                "validation_gate_report_run_id": validation_report.get("run_id"),
                "resume_checkpoint_used": resumed_from_checkpoint,
            }
        )
        _clear_resume_checkpoint(mode=mode, reason="completed_without_l5_learning")
        return 0

    if resumed_from_checkpoint:
        print("[REFRESH+L5] L5 learning report (from checkpoint):")
        print(json.dumps(l5_report or {}, indent=2))
    else:
        _ensure_learning_env()
        result = run_l5_policy_learning(trigger=f"refresh:{mode}")
        l5_report = dict(result.report) if isinstance(result.report, dict) else {}

        print("[REFRESH+L5] L5 learning report:")
        print(json.dumps(l5_report, indent=2))
        _write_resume_checkpoint(
            mode=mode,
            report=report,
            quote_cache_refresh_report=quote_cache_refresh_report,
            l5_learning_report=l5_report,
        )

    optimizer_summary: dict[str, Any] | None = None
    optimizer_target: float | None = None
    optimizer_best_score: float | None = None
    optimizer_target_met: bool | None = None
    epoch_schema: str | None = None
    epoch_status: str | None = None
    oracle_short_cycle_status = "not_run"
    oracle_short_cycle_reason = "l5_path_not_reached"
    oracle_plan = _resolve_oracle_execution_plan(mode=mode, report=report)

    oracle_short_cycle_status = str(oracle_plan.get("status") or oracle_short_cycle_status)
    oracle_short_cycle_reason = str(oracle_plan.get("reason") or "unspecified")

    if bool(oracle_plan.get("should_run")):
        optimizer_summary = _run_oracle_optimizer_short_cycle(mode=mode)
        optimizer_target = _float_or_none(optimizer_summary.get("success_target_return_lift_pct")) or DEFAULT_ORACLE_TARGET_RETURN_LIFT
        optimizer_end = optimizer_summary.get("end")
        optimizer_best_score = _float_or_none(optimizer_end.get("best_score")) if isinstance(optimizer_end, dict) else None
        optimizer_target_met = _is_target_met(optimizer_summary)
        epoch_schema = _epoch_schema(optimizer_summary)
        epoch_status = "ok" if epoch_schema == EXPECTED_EPOCH_LIBRARY_SCHEMA else "missing_or_invalid"

        if not optimizer_target_met:
            raise RuntimeError(
                "Oracle optimizer target gate failed after refresh. "
                f"required_return_lift={optimizer_target}; observed_best={optimizer_best_score}"
            )

        if epoch_status != "ok":
            raise RuntimeError(
                "Epoch library schema gate failed after refresh. "
                f"expected={EXPECTED_EPOCH_LIBRARY_SCHEMA}; observed={epoch_schema or 'missing'}"
            )
    else:
        print(
            "[REFRESH+L5] Oracle optimizer short-cycle skipped. "
            f"status={oracle_short_cycle_status}; reason={oracle_short_cycle_reason}; "
            f"policy={oracle_plan.get('policy')}; trigger_source={oracle_plan.get('trigger_source')}; "
            f"explicit_allow={oracle_plan.get('explicit_allow')}"
        )

    runtime_sync_report, validation_report = _run_post_rebuild_pipeline(
        report=report,
        mode=mode,
        optimizer_summary=optimizer_summary,
        optimizer_short_cycle_status=oracle_short_cycle_status,
        epoch_schema=epoch_schema,
        epoch_status=epoch_status,
    )
    quote_cache_refresh_report = _launch_quote_cache_refresh_followup(
        mode=mode,
        quote_cache_refresh_report=quote_cache_refresh_report,
    )

    _append_history_event(
        {
            "phase": "complete",
            "status": "ok",
            "refresh_mode": mode,
            "refresh_report_status": report.get("status"),
            "rows_written": report.get("rows_written"),
            "elapsed_seconds": report.get("elapsed_seconds"),
            "l5_learning": "run",
            "l5_cells_total": (l5_report or {}).get("cells_total"),
            "l5_coverage_rate": (l5_report or {}).get("coverage_rate"),
            "l5_fallback_rate": (l5_report or {}).get("fallback_rate"),
            "quote_cache_refresh": quote_cache_refresh_report.get("status"),
            "quote_cache_profile_overrides": (quote_cache_refresh_report.get("profile_overrides") or {}).get("status"),
            "resume_checkpoint_used": resumed_from_checkpoint,
            "optimizer_short_cycle": oracle_short_cycle_status,
            "optimizer_cycle_requested_runs": optimizer_summary.get("requested_additional_runs") if optimizer_summary else None,
            "optimizer_cycle_completed_runs": optimizer_summary.get("actual_additional_runs") if optimizer_summary else None,
            "optimizer_session_id": optimizer_summary.get("session_id") if optimizer_summary else None,
            "optimizer_target_return_lift_pct": optimizer_target,
            "optimizer_best_score": optimizer_best_score,
            "optimizer_target_met": optimizer_target_met,
            "optimizer_short_cycle_reason": oracle_short_cycle_reason,
            "optimizer_short_cycle_policy": oracle_plan.get("policy"),
            "optimizer_short_cycle_trigger_source": oracle_plan.get("trigger_source"),
            "optimizer_short_cycle_explicit_allow": oracle_plan.get("explicit_allow"),
            "epoch_library_confidence_schema": epoch_schema,
            "epoch_library_status": epoch_status,
            "runtime_postgres_sync": runtime_sync_report.get("status"),
            "runtime_postgres_sync_run_id": runtime_sync_report.get("run_id"),
            "validation_gate_status": validation_report.get("status"),
            "validation_gate_report_run_id": validation_report.get("run_id"),
        }
    )

    _clear_resume_checkpoint(mode=mode, reason="completed_successfully")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        _append_history_event(
            {
                "phase": "complete",
                "status": "error",
                "error": str(error),
            }
        )
        raise
