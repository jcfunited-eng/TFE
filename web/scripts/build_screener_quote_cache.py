#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from build_screener_quote_cache_impl import DEFAULT_FAILURES, DEFAULT_OUTPUT, main as impl_main
from publication_identity import stamp_active_snapshot_and_quote_artifacts


FORCE_REFRESH_FLAG = "--force-refresh"
FORCED_WORKER_COUNT = "4"
ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = ROOT / "web" / "scripts" / "seed_screener_quote_cache_from_runtime.mjs"
LEGACY_DISABLED_SCRAPER_ARGS = {
    "--skip-finviz-refresh",
}
LEGACY_DISABLED_SCRAPER_ARG_PREFIXES = (
    "--finviz-",
)


def _resolve_paths(argv: list[str]) -> tuple[Path, Path]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--failures-output", default=str(DEFAULT_FAILURES))
    args, _ = parser.parse_known_args(argv[1:])
    return Path(args.output).resolve(), Path(args.failures_output).resolve()


def _normalize_refresh_mode(raw_value: str) -> str:
    value = str(raw_value or "").strip().lower()
    if value in {"snapshot", "targeted_pfsc", "targeted"}:
        return "snapshot"
    if value in {"universe_snapshot", "full_universe", "full"}:
        return "universe_snapshot"
    return value


def _read_bool_env(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _read_positive_int_env(name: str, default: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    if value <= 0:
        return default
    return value


def _requested_mode() -> str:
    return _normalize_refresh_mode(os.environ.get("TFE_REFRESH_REQUESTED_MODE", ""))


def _should_seed_from_runtime(mode: str) -> bool:
    if mode not in {"snapshot", "universe_snapshot"}:
        return False
    return _read_bool_env("TFE_QUOTE_CACHE_SEED_FROM_RUNTIME", True)


def _should_force_refresh(argv: list[str], mode: str) -> bool:
    if FORCE_REFRESH_FLAG in argv[1:]:
        return True
    env_default = mode != "snapshot"
    return _read_bool_env("TFE_QUOTE_CACHE_FORCE_REFRESH", env_default)


def _apply_force_refresh(argv: list[str], enabled: bool) -> list[str]:
    filtered = [argv[0], *[arg for arg in argv[1:] if arg != FORCE_REFRESH_FLAG]]
    if not enabled:
        return filtered
    return [filtered[0], FORCE_REFRESH_FLAG, *filtered[1:]]


def _strip_legacy_disabled_scraper_args(argv: list[str]) -> list[str]:
    normalized = [argv[0]]
    skip_next = False

    for arg in argv[1:]:
        if skip_next:
            skip_next = False
            continue

        if arg in LEGACY_DISABLED_SCRAPER_ARGS:
            continue

        matched_prefix = next(
            (prefix for prefix in LEGACY_DISABLED_SCRAPER_ARG_PREFIXES if arg.startswith(prefix)),
            None,
        )
        if matched_prefix:
            if "=" not in arg:
                skip_next = True
            continue

        normalized.append(arg)

    return normalized


def _normalize_worker_args(argv: list[str]) -> list[str]:
    normalized = [argv[0]]
    skip_next = False
    for arg in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg == "--workers":
            skip_next = True
            continue
        if arg.startswith("--workers="):
            continue
        normalized.append(arg)
    normalized.extend(["--workers", FORCED_WORKER_COUNT])
    return normalized


def _print_prefixed_lines(prefix: str, text: str) -> None:
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        if line:
            print(f"{prefix}{line}")


def _seed_quote_cache_from_runtime(output_path: Path) -> bool:
    if not SEED_SCRIPT.exists():
        print(f"runtime_quote_cache_seed_warning=seed_script_missing:{SEED_SCRIPT}")
        print("runtime_quote_cache_seed_fallback=true")
        return False

    timeout_sec = _read_positive_int_env("TFE_QUOTE_CACHE_SEED_TIMEOUT_SEC", 180)
    min_rows = str(os.environ.get("TFE_QUOTE_CACHE_SEED_MIN_ROWS", "")).strip()
    cmd = ["node", str(SEED_SCRIPT), "--output", str(output_path)]
    if min_rows:
        cmd.extend(["--min-rows", min_rows])

    print("runtime_quote_cache_seed_enabled=true")
    print(f"runtime_quote_cache_seed_cmd={' '.join(cmd)}")
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_sec,
            env=dict(os.environ),
        )
    except subprocess.TimeoutExpired:
        print(f"runtime_quote_cache_seed_warning=seed_timeout_after_{timeout_sec}s")
        print("runtime_quote_cache_seed_fallback=true")
        return False

    _print_prefixed_lines("runtime_quote_cache_seed_stdout=", completed.stdout)
    _print_prefixed_lines("runtime_quote_cache_seed_stderr=", completed.stderr)

    if completed.returncode != 0:
        stdout_tail = "\n".join(str(completed.stdout or "").splitlines()[-20:]).strip()
        stderr_tail = "\n".join(str(completed.stderr or "").splitlines()[-20:]).strip()
        print(
            "runtime_quote_cache_seed_warning="
            f"seed_failed_exit_{completed.returncode};"
            f"stdout_tail={stdout_tail or 'n/a'};"
            f"stderr_tail={stderr_tail or 'n/a'}"
        )
        print("runtime_quote_cache_seed_fallback=true")
        return False

    print("runtime_quote_cache_seed_fallback=false")
    return True


def main() -> int:
    output_path, failures_path = _resolve_paths(sys.argv)
    requested_mode = _requested_mode()
    seed_from_runtime = _should_seed_from_runtime(requested_mode)
    force_refresh = _should_force_refresh(sys.argv, requested_mode)

    print(f"requested_mode={requested_mode or 'unknown'}")
    print(f"runtime_quote_cache_seed={seed_from_runtime}")
    print(f"force_refresh={force_refresh}")
    print(f"forced_worker_count={FORCED_WORKER_COUNT}")

    if seed_from_runtime:
        seed_ok = _seed_quote_cache_from_runtime(output_path)
        if not seed_ok:
            force_refresh = True
            print("force_refresh_escalated_due_to_seed_failure=true")

    normalized_argv = _strip_legacy_disabled_scraper_args(sys.argv)
    normalized_argv = _apply_force_refresh(normalized_argv, force_refresh)
    normalized_argv = _normalize_worker_args(normalized_argv)
    sys.argv = normalized_argv

    rc = int(impl_main() or 0)
    if rc != 0:
        return rc
    stamp_active_snapshot_and_quote_artifacts(
        output_path=output_path,
        failures_path=failures_path,
        require_aligned=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
