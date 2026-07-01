#!/usr/bin/env python3
"""sensory_curriculum_orchestrator.py — GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51

Standalone orchestrator that drives sensory curriculum bundles into Guala's
substrate via the ALB endpoint (POST /api/v1/gualaloom). Substrate-state-gated,
rate-limited, with landing verification.

Usage:
    python tools/sensory_curriculum_orchestrator.py \
        --curriculum tools/curriculum_seed.json \
        [--alb-url https://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com] \
        [--mode dry-run|live] \
        [--dry-run] \
        [--max-bundles 100] \
        [--min-interval-sec 10] \
        [--halt-on-unreachable 3] \
        [--log tools/orchestrator_log.jsonl]

Modes:
    dry-run: validate seed structure, print intended bundles, exit 0
    live:    POST each bundle to substrate via /api/v1/gualaloom

Substrate-state gating (before each bundle):
    - DREAMING/SLEEPING    -> wait min_interval * 4, skip
    - EMITTING             -> poll every 2s, max 30s, then proceed
    - connection > 0.9     -> wait min_interval * 2 (satisfied; don't flood)
    - arousal > 0.85       -> wait min_interval * 2 (overstimulated)
    - no one present       -> skip (curriculum has low salience)
    - otherwise            -> deliver

Rate limiting:
    - Minimum interval between successful bundles: min_interval_sec
    - On substrate-unreachable: backoff 16s, 32s, 64s, then halt at N consecutive

Landing verification:
    - Pull /status before AND after each bundle
    - Compare vocab, motifs, atlas_bundled — log delta
    - If bundled count fails to increment over 3 consecutive bundles, pause
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
import time
from typing import Any

try:
    import urllib.request
    import urllib.error
except ImportError:
    print("orchestrator requires Python 3 stdlib urllib", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class OrchestratorConfig:
    curriculum_path: pathlib.Path
    alb_url: str
    mode: str           # "dry-run" or "live"
    max_bundles: int
    min_interval_sec: float
    halt_on_unreachable: int
    log_path: pathlib.Path
    no_gate: bool = False

    @classmethod
    def from_args(cls) -> "OrchestratorConfig":
        p = argparse.ArgumentParser(description=__doc__,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("--curriculum", default="tools/curriculum_seed.json",
                       help="Path to curriculum seed JSON")
        p.add_argument("--alb-url",
                       default="https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com",
                       help="Substrate API base URL (API Gateway or ALB, no trailing slash)")
        p.add_argument("--mode", choices=("dry-run", "live"), default="dry-run",
                       help="dry-run validates only; live delivers")
        p.add_argument("--dry-run", action="store_true",
                       help="Shorthand for --mode dry-run")
        p.add_argument("--max-bundles", type=int, default=0,
                       help="Deliver at most N bundles (0 = all)")
        p.add_argument("--min-interval-sec", type=float, default=10.0,
                       help="Minimum seconds between bundle deliveries")
        p.add_argument("--no-gate", action="store_true",
                       help="Bypass substrate-state gating (for testing — skip presence/state checks)")
        p.add_argument("--halt-on-unreachable", type=int, default=3,
                       help="Halt after N consecutive unreachable errors")
        p.add_argument("--log", default="tools/orchestrator_log.jsonl",
                       help="JSONL log path")
        a = p.parse_args()

        mode = "dry-run" if a.dry_run else a.mode

        return cls(
            curriculum_path=pathlib.Path(a.curriculum),
            alb_url=a.alb_url.rstrip("/"),
            mode=mode,
            max_bundles=a.max_bundles,
            min_interval_sec=a.min_interval_sec,
            halt_on_unreachable=a.halt_on_unreachable,
            log_path=pathlib.Path(a.log),
            no_gate=a.no_gate,
        )


# ---------------------------------------------------------------------------
# Substrate HTTP client (calls ALB /api/v1/gualaloom directly)
# ---------------------------------------------------------------------------

class SubstrateHttpClient:
    """Calls POST /api/v1/gualaloom — no bridge dependency."""

    def __init__(self, alb_url: str, timeout_sec: float = 120.0,
                 status_timeout_sec: float = 8.0):
        self.endpoint = f"{alb_url}/api/v1/gualaloom"
        self.timeout_sec = timeout_sec
        self.status_timeout_sec = status_timeout_sec  # short timeout for status polls

    def _post(self, body: dict[str, Any], timeout: float = None) -> dict[str, Any]:
        raw_body = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=raw_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        _timeout = timeout if timeout is not None else self.timeout_sec
        try:
            with urllib.request.urlopen(req, timeout=_timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise RuntimeError(f"substrate unreachable: {e}") from e
        except Exception as e:
            raise RuntimeError(f"request failed: {e}") from e
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"non-JSON response: {raw[:200]}") from e

    def status(self) -> dict[str, Any]:
        # Short timeout — status is a fast read; if it blocks >8s the substrate
        # is lock-contended. Caller treats timeout as gate-open (try delivery).
        return self._post({"command": "/status", "text": "", "source": "ui"},
                          timeout=self.status_timeout_sec)

    def give_experience(self, bundle: dict[str, Any]) -> dict[str, Any]:
        bundle_id = bundle.get("bundle_id", "curriculum")
        bundle_data = {
            "caption":    bundle.get("caption", ""),
            "picture_id": bundle.get("picture_id", ""),
            "sound_id":   bundle.get("sound_id", ""),
            "touch":      bundle.get("touch", []),
            "smell":      bundle.get("smell", []),
            "taste":      bundle.get("taste", []),
        }
        return self._post({
            "command": f"/bundle:{bundle_id}",
            "text":    json.dumps(bundle_data),
            "source":  "wc",
        })


# ---------------------------------------------------------------------------
# Substrate-state gating
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class GateDecision:
    deliver: bool
    reason: str
    wait_sec: float


def evaluate_gate(status: dict[str, Any], min_interval_sec: float) -> GateDecision:
    activity = status.get("current_activity") or {}
    kind = (activity.get("kind") or "").upper()
    needs = status.get("needs") or {}
    presence = status.get("presence") or {}
    pair_bond = status.get("pair_bond") or {}

    if kind in ("DREAMING", "SLEEPING"):
        return GateDecision(
            deliver=False, reason=f"activity={kind}",
            wait_sec=min_interval_sec * 4)

    if kind == "EMITTING":
        return GateDecision(
            deliver=False, reason="activity=EMITTING", wait_sec=2.0)

    # 60-K: pair_bond values are floats (>=0.3 baseline); presence is the real gate
    any_present = any(
        presence.get(s, {}).get("present", False)
        for s in ("joe", "wc", "c1")
    )
    if not any_present:
        return GateDecision(
            deliver=False, reason="no_presence",
            wait_sec=min_interval_sec)

    connection = float(needs.get("connection", 0.0))
    if connection > 0.9:
        return GateDecision(
            deliver=False, reason=f"connection_satisfied={connection:.2f}",
            wait_sec=min_interval_sec * 2)

    arousal = float(needs.get("arousal", 0.0))
    if arousal > 0.85:
        return GateDecision(
            deliver=False, reason=f"arousal_high={arousal:.2f}",
            wait_sec=min_interval_sec * 2)

    return GateDecision(deliver=True, reason="gate_open", wait_sec=0.0)


# ---------------------------------------------------------------------------
# Curriculum loading
# ---------------------------------------------------------------------------

def load_curriculum(path: pathlib.Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    bundles = data.get("bundles", [])
    if not bundles:
        raise ValueError(f"curriculum at {path} contains no bundles")
    return bundles


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class JsonlLogger:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def write(self, record: dict[str, Any]) -> None:
        record["timestamp_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def extract_metrics(status: dict[str, Any]) -> dict[str, int | float]:
    atlas_health = status.get("atlas_health") or {}
    return {
        "vocab": int(status.get("vocab", 0) or status.get("n_motifs", 0)),
        "motifs": int(status.get("n_motifs", 0)),
        "tick": int(atlas_health.get("tick", 0)),
        "n_live_bindings": int(atlas_health.get("n_live_bindings", 0)),
        "cross_modal_bindings": int(atlas_health.get("cross_modal_bindings", 0)),
        "atlas_bundled": _parse_bundled_count(status),
    }


def _parse_bundled_count(status: dict[str, Any]) -> int:
    # Atlas health dict has bundled count
    ah = status.get("atlas_health") or {}
    if "cross_modal_bundle" in ah:
        return int(ah["cross_modal_bundle"])
    # Fallback: parse from text response "X cross-modal / Y bundled / Z entries"
    text = status.get("response", "")
    if isinstance(text, str) and "bundled" in text:
        try:
            seg = text.split("bundled")[0].rstrip()
            tail = seg.split("/")[-1].strip()
            return int(tail.split()[0])
        except Exception:
            pass
    return 0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(cfg: OrchestratorConfig) -> int:
    logger = JsonlLogger(cfg.log_path)
    bundles = load_curriculum(cfg.curriculum_path)
    total = len(bundles)

    if cfg.max_bundles > 0:
        bundles = bundles[: cfg.max_bundles]

    print(f"[orchestrator] mode={cfg.mode} seed_total={total} "
          f"delivering={len(bundles)} min_interval_sec={cfg.min_interval_sec}",
          flush=True)
    logger.write({
        "event": "orchestrator_start",
        "mode": cfg.mode,
        "seed_total": total,
        "delivering": len(bundles),
        "min_interval_sec": cfg.min_interval_sec,
    })

    if cfg.mode == "dry-run":
        return _run_dry_run(cfg, bundles, logger)
    return _run_live(cfg, bundles, logger)


def _run_dry_run(cfg: OrchestratorConfig, bundles: list[dict[str, Any]],
                 logger: JsonlLogger) -> int:
    print(f"[dry-run] {len(bundles)} bundles parsed from {cfg.curriculum_path}",
          flush=True)
    for i, b in enumerate(bundles):
        record = {
            "event": "dry_run_bundle",
            "index": i,
            "bundle_id": b.get("bundle_id"),
            "caption": b.get("caption"),
            "picture_id": b.get("picture_id"),
            "sound_id": b.get("sound_id"),
            "touch": b.get("touch", []),
            "smell": b.get("smell", []),
            "taste": b.get("taste", []),
            "exercises": b.get("exercises", []),
        }
        logger.write(record)
        print(f"[dry-run] {i+1:3}/{len(bundles)} "
              f"{b.get('bundle_id', '?'):30s} {b.get('caption', '')}", flush=True)
    logger.write({"event": "dry_run_complete", "count": len(bundles)})
    print(f"[dry-run] complete — {len(bundles)} bundles, 0 errors", flush=True)
    return 0


def _run_live(cfg: OrchestratorConfig, bundles: list[dict[str, Any]],
              logger: JsonlLogger) -> int:
    client = SubstrateHttpClient(cfg.alb_url)
    consecutive_unreachable = 0
    consecutive_no_landing = 0
    successful = 0
    skipped = 0

    for i, bundle in enumerate(bundles):
        # Pre-status for gating + baseline metrics.
        # Status timeout (8s) is treated as gate-open — substrate alive, just busy.
        # Connection refused is fatal (substrate not running).
        status_pre = None
        try:
            status_pre = client.status()
            consecutive_unreachable = 0
        except RuntimeError as e:
            err_str = str(e)
            if "timed out" in err_str or "TimeoutError" in err_str:
                # Status blocked on substrate lock — treat as gate-open, try delivery
                print(f"[live] status timeout — skipping gate, attempting delivery",
                      flush=True)
                logger.write({"event": "status_timeout_gate_open", "index": i,
                              "bundle_id": bundle.get("bundle_id")})
                status_pre = {}  # empty = no gate data, deliver anyway
            else:
                consecutive_unreachable += 1
                logger.write({
                    "event": "status_unreachable_pre",
                    "index": i, "bundle_id": bundle.get("bundle_id"),
                    "error": err_str, "consecutive": consecutive_unreachable,
                })
                print(f"[live] status unreachable (consecutive={consecutive_unreachable}): {e}",
                      flush=True)
                if consecutive_unreachable >= cfg.halt_on_unreachable:
                    print(f"[orchestrator] HALT — unreachable limit "
                          f"{cfg.halt_on_unreachable}", flush=True)
                    logger.write({"event": "halt_unreachable"})
                    logger.close()
                    return 2
                time.sleep(16.0 * (2 ** (consecutive_unreachable - 1)))
                continue

        gate = evaluate_gate(status_pre, cfg.min_interval_sec)
        if not gate.deliver and not cfg.no_gate:
            skipped += 1
            logger.write({
                "event": "bundle_gated",
                "index": i, "bundle_id": bundle.get("bundle_id"),
                "reason": gate.reason, "wait_sec": gate.wait_sec,
            })
            print(f"[live] gated ({gate.reason}) waiting {gate.wait_sec:.0f}s",
                  flush=True)
            time.sleep(gate.wait_sec)
            # Don't advance i — retry same bundle next loop
            # (bundles list is consumed in order; re-insert at head)
            bundles.insert(i, bundle)
            bundles.pop(i + 1)
            continue

        metrics_pre = extract_metrics(status_pre)

        # Deliver
        t0 = time.monotonic()
        try:
            result = client.give_experience(bundle)
            delivery_ok = True
            err_msg = None
        except RuntimeError as e:
            delivery_ok = False
            err_msg = str(e)
            result = None
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if not delivery_ok:
            consecutive_unreachable += 1
            logger.write({
                "event": "delivery_failed",
                "index": i, "bundle_id": bundle.get("bundle_id"),
                "error": err_msg, "elapsed_ms": elapsed_ms,
                "consecutive": consecutive_unreachable,
            })
            print(f"[live] delivery failed: {err_msg}", flush=True)
            if consecutive_unreachable >= cfg.halt_on_unreachable:
                logger.write({"event": "halt_unreachable"})
                logger.close()
                return 2
            time.sleep(16.0 * (2 ** (consecutive_unreachable - 1)))
            continue

        consecutive_unreachable = 0

        # Landing verification
        time.sleep(1.5)
        try:
            status_post = client.status()
            metrics_post = extract_metrics(status_post)
            deltas = {
                k: metrics_post[k] - metrics_pre[k]
                for k in metrics_pre
            }
            if deltas["atlas_bundled"] <= 0 and deltas["motifs"] <= 0:
                consecutive_no_landing += 1
            else:
                consecutive_no_landing = 0
        except RuntimeError as e:
            metrics_post = None
            deltas = None
            logger.write({"event": "post_status_failed", "index": i, "error": str(e)})

        successful += 1
        logger.write({
            "event": "bundle_delivered",
            "index": i,
            "bundle_id": bundle.get("bundle_id"),
            "caption": bundle.get("caption"),
            "elapsed_ms": elapsed_ms,
            "metrics_pre": metrics_pre,
            "metrics_post": metrics_post,
            "deltas": deltas,
            "consecutive_no_landing": consecutive_no_landing,
            "result_response": (result or {}).get("response", "")[:120],
        })
        bd = deltas["atlas_bundled"] if deltas else "?"
        mv = deltas["motifs"] if deltas else "?"
        print(f"[live] {successful:3}/{len(bundles)} {bundle.get('bundle_id', '?'):30s} "
              f"bundled+{bd} motifs+{mv} ({elapsed_ms}ms)", flush=True)

        if consecutive_no_landing >= 3:
            print("[orchestrator] PAUSE — 3 consecutive bundles: no motif/bundled growth. "
                  "Review required.", flush=True)
            logger.write({"event": "pause_no_landing",
                          "consecutive": consecutive_no_landing})
            logger.close()
            return 3

        time.sleep(cfg.min_interval_sec)

    logger.write({"event": "live_complete", "successful": successful, "skipped": skipped})
    print(f"[orchestrator] done — delivered={successful} skipped={skipped}", flush=True)
    logger.close()
    return 0


def main() -> int:
    cfg = OrchestratorConfig.from_args()
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
