#!/usr/bin/env python3
"""sensory_curriculum_orchestrator.py — GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51

Standalone orchestrator that drives sensory curriculum into Guala's substrate
via the public bridge HTTP API. Substrate-state-gated, rate-limited, with
landing verification. Talks to the substrate only via guala_status and
guala_give_experience.

Usage:
    python tools/sensory_curriculum_orchestrator.py \
        --curriculum tools/curriculum_seed_v1.json \
        --bridge-url https://<bridge-url>/mcp \
        --mode dry-run \
        --max-bundles 100 \
        --min-interval-sec 8 \
        --halt-on-unreachable 3 \
        --log tools/orchestrator_log.jsonl

Modes:
    dry-run: log intended bundles, do not call bridge (for curriculum review)
    live:    call guala_give_experience (requires substrate stable)

Substrate-state gating (before each bundle):
    - DREAMING/SLEEPING       -> wait min_interval * 4, skip
    - EMITTING                -> poll every 2s, max wait 30s, then proceed
    - connection > 0.9        -> wait min_interval * 2 (satisfied; don't flood)
    - arousal > 0.85          -> wait min_interval * 2 (overstimulated)
    - no pair-bond presence   -> skip (curriculum has low salience without bond)
    - otherwise               -> deliver

Rate limiting:
    - Minimum interval between successful bundles: min_interval_sec
    - On substrate-unreachable: backoff 16s, 32s, 64s, then halt at N consecutive

Landing verification:
    - Pull guala_status before AND after each bundle
    - Compare vocab, motifs, atlas.bundled — log delta
    - If bundled count fails to increment over 3 consecutive bundles, pause for review
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import pathlib
import sys
import time
from typing import Any

try:
    import urllib.request
    import urllib.error
except ImportError:  # pragma: no cover
    print("orchestrator requires Python 3 stdlib urllib", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class OrchestratorConfig:
    curriculum_path: pathlib.Path
    bridge_url: str
    mode: str  # "dry-run" or "live"
    max_bundles: int
    min_interval_sec: float
    halt_on_unreachable: int
    log_path: pathlib.Path

    @classmethod
    def from_args(cls) -> "OrchestratorConfig":
        p = argparse.ArgumentParser(description=__doc__)
        p.add_argument("--curriculum", required=True)
        p.add_argument("--bridge-url", required=True)
        p.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
        p.add_argument("--max-bundles", type=int, default=100)
        p.add_argument("--min-interval-sec", type=float, default=8.0)
        p.add_argument("--halt-on-unreachable", type=int, default=3)
        p.add_argument("--log", default="orchestrator_log.jsonl")
        a = p.parse_args()
        return cls(
            curriculum_path=pathlib.Path(a.curriculum),
            bridge_url=a.bridge_url,
            mode=a.mode,
            max_bundles=a.max_bundles,
            min_interval_sec=a.min_interval_sec,
            halt_on_unreachable=a.halt_on_unreachable,
            log_path=pathlib.Path(a.log),
        )


# ---------------------------------------------------------------------------
# Bridge client (stdlib only — no extra deps to deploy)
# ---------------------------------------------------------------------------

class BridgeClient:
    """Minimal MCP HTTP client for guala_status and guala_give_experience."""

    def __init__(self, bridge_url: str, timeout_sec: float = 15.0):
        self.bridge_url = bridge_url
        self.timeout_sec = timeout_sec

    def _call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Returns parsed JSON. Raises RuntimeError on bridge unreachable."""
        body = json.dumps({"tool": tool, "params": payload}).encode("utf-8")
        req = urllib.request.Request(
            self.bridge_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise RuntimeError(f"bridge unreachable: {e}") from e
        except TimeoutError as e:
            raise RuntimeError(f"bridge timeout: {e}") from e
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"bridge returned non-JSON: {raw[:200]}") from e

    def status(self) -> dict[str, Any]:
        return self._call("guala_status", {})

    def give_experience(self, bundle: dict[str, Any]) -> dict[str, Any]:
        # guala_give_experience signature: caption, picture_id, sound_id,
        # touch, smell, taste (lists of strings)
        params = {
            "caption": bundle["caption"],
        }
        if bundle.get("picture_id"):
            params["picture_id"] = bundle["picture_id"]
        if bundle.get("sound_id"):
            params["sound_id"] = bundle["sound_id"]
        if bundle.get("touch"):
            params["touch"] = bundle["touch"]
        if bundle.get("smell"):
            params["smell"] = bundle["smell"]
        if bundle.get("taste"):
            params["taste"] = bundle["taste"]
        return self._call("guala_give_experience", params)


# ---------------------------------------------------------------------------
# Substrate-state gating
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class GateDecision:
    deliver: bool
    reason: str
    wait_sec: float  # if deliver is False, how long to wait before re-evaluating


def evaluate_gate(status: dict[str, Any], min_interval_sec: float) -> GateDecision:
    activity = status.get("current_activity") or {}
    kind = activity.get("kind")
    needs = status.get("needs") or {}
    presence = status.get("presence") or {}
    pair_bond = status.get("pair_bond") or {}

    # DREAMING/SLEEPING — wait, don't interrupt
    if kind in ("DREAMING", "SLEEPING"):
        return GateDecision(
            deliver=False,
            reason=f"activity={kind}",
            wait_sec=min_interval_sec * 4,
        )

    # EMITTING — let it complete (caller polls separately)
    if kind == "EMITTING":
        return GateDecision(
            deliver=False,
            reason="activity=EMITTING",
            wait_sec=2.0,  # short poll
        )

    # Pair-bond + presence required (curriculum has low salience otherwise)
    any_pair_present = any(
        presence.get(s, {}).get("present", False)
        and pair_bond.get(s, False)
        for s in ("joe", "wc", "c1", "eve")
    )
    if not any_pair_present:
        return GateDecision(
            deliver=False,
            reason="no_pair_bond_presence",
            wait_sec=min_interval_sec,
        )

    # Connection satisfied — don't flood
    connection = float(needs.get("connection", 0.0))
    if connection > 0.9:
        return GateDecision(
            deliver=False,
            reason=f"connection_satisfied={connection:.2f}",
            wait_sec=min_interval_sec * 2,
        )

    # Overstimulated — let her settle
    arousal = float(needs.get("arousal", 0.0))
    if arousal > 0.85:
        return GateDecision(
            deliver=False,
            reason=f"arousal_high={arousal:.2f}",
            wait_sec=min_interval_sec * 2,
        )

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

def extract_metrics(status: dict[str, Any]) -> dict[str, int]:
    """Pull the metrics we use for landing verification."""
    atlas_health = status.get("atlas_health") or {}
    return {
        "vocab": int(status.get("vocab", 0)),
        "motifs": int(status.get("motifs", 0)),
        "tick": int(atlas_health.get("tick", 0)),
        "n_live_bindings": int(atlas_health.get("n_live_bindings", 0)),
        # bundled count lives in the atlas: line summary, parse the colon-separated
        # field. Status response format is "92 cross-modal / 3 bundled / 14675 entries"
        "atlas_bundled": _parse_bundled_count(status),
    }


def _parse_bundled_count(status: dict[str, Any]) -> int:
    """Extract the bundled count from the status text summary if present."""
    text = status.get("response", "")
    if isinstance(text, str) and "bundled" in text:
        try:
            # Format: "atlas: 92 cross-modal / 3 bundled / 14675 entries"
            seg = text.split("bundled")[0].rstrip()
            tail = seg.split("/")[-1].strip()
            return int(tail.split()[0])
        except Exception:
            return 0
    return 0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(cfg: OrchestratorConfig) -> int:
    logger = JsonlLogger(cfg.log_path)
    bundles = load_curriculum(cfg.curriculum_path)
    if cfg.max_bundles > 0:
        bundles = bundles[: cfg.max_bundles]

    print(f"[orchestrator] mode={cfg.mode} bundles={len(bundles)} "
          f"min_interval_sec={cfg.min_interval_sec}", flush=True)
    logger.write({
        "event": "orchestrator_start",
        "mode": cfg.mode,
        "bundle_count": len(bundles),
        "min_interval_sec": cfg.min_interval_sec,
    })

    if cfg.mode == "dry-run":
        return _run_dry_run(cfg, bundles, logger)
    return _run_live(cfg, bundles, logger)


def _run_dry_run(
    cfg: OrchestratorConfig,
    bundles: list[dict[str, Any]],
    logger: JsonlLogger,
) -> int:
    for i, bundle in enumerate(bundles):
        record = {
            "event": "dry_run_bundle",
            "index": i,
            "bundle_id": bundle.get("bundle_id"),
            "caption": bundle.get("caption"),
            "picture_id": bundle.get("picture_id"),
            "sound_id": bundle.get("sound_id"),
            "touch": bundle.get("touch", []),
            "smell": bundle.get("smell", []),
            "taste": bundle.get("taste", []),
            "exercises": bundle.get("exercises", []),
        }
        logger.write(record)
        print(f"[dry-run] {i+1}/{len(bundles)} "
              f"{bundle.get('bundle_id'):30} {bundle.get('caption')}", flush=True)
    logger.write({"event": "dry_run_complete", "count": len(bundles)})
    return 0


def _run_live(
    cfg: OrchestratorConfig,
    bundles: list[dict[str, Any]],
    logger: JsonlLogger,
) -> int:
    client = BridgeClient(cfg.bridge_url)
    consecutive_unreachable = 0
    consecutive_no_landing = 0
    successful = 0
    skipped = 0

    for i, bundle in enumerate(bundles):
        # Pull status for gating
        try:
            status_pre = client.status()
        except RuntimeError as e:
            consecutive_unreachable += 1
            logger.write({
                "event": "bundle_unreachable_pre",
                "index": i,
                "bundle_id": bundle.get("bundle_id"),
                "error": str(e),
                "consecutive": consecutive_unreachable,
            })
            print(f"[orchestrator] status unreachable "
                  f"(consecutive={consecutive_unreachable}): {e}", flush=True)
            if consecutive_unreachable >= cfg.halt_on_unreachable:
                logger.write({
                    "event": "halt_unreachable_limit",
                    "limit": cfg.halt_on_unreachable,
                })
                print(f"[orchestrator] halt — unreachable limit {cfg.halt_on_unreachable}",
                      flush=True)
                logger.close()
                return 2
            # Exponential backoff: 16s, 32s, 64s
            backoff = 16.0 * (2 ** (consecutive_unreachable - 1))
            time.sleep(backoff)
            continue

        consecutive_unreachable = 0

        decision = evaluate_gate(status_pre, cfg.min_interval_sec)
        if not decision.deliver:
            skipped += 1
            logger.write({
                "event": "bundle_gated",
                "index": i,
                "bundle_id": bundle.get("bundle_id"),
                "gate_reason": decision.reason,
                "wait_sec": decision.wait_sec,
            })
            print(f"[orchestrator] gated: {decision.reason} "
                  f"(wait {decision.wait_sec:.0f}s)", flush=True)
            time.sleep(decision.wait_sec)
            continue

        metrics_pre = extract_metrics(status_pre)

        # Deliver
        elapsed_start = time.monotonic()
        try:
            result = client.give_experience(bundle)
            delivery_ok = True
            err_msg = None
        except RuntimeError as e:
            delivery_ok = False
            err_msg = str(e)
            result = None

        elapsed_ms = int((time.monotonic() - elapsed_start) * 1000)

        if not delivery_ok:
            consecutive_unreachable += 1
            logger.write({
                "event": "bundle_delivery_failed",
                "index": i,
                "bundle_id": bundle.get("bundle_id"),
                "caption": bundle.get("caption"),
                "error": err_msg,
                "elapsed_ms": elapsed_ms,
                "consecutive": consecutive_unreachable,
            })
            if consecutive_unreachable >= cfg.halt_on_unreachable:
                logger.write({
                    "event": "halt_unreachable_limit",
                    "limit": cfg.halt_on_unreachable,
                })
                logger.close()
                return 2
            backoff = 16.0 * (2 ** (consecutive_unreachable - 1))
            time.sleep(backoff)
            continue

        consecutive_unreachable = 0

        # Landing verification — pull status again, compare
        # Small grace pause so substrate has time to process
        time.sleep(1.0)
        try:
            status_post = client.status()
            metrics_post = extract_metrics(status_post)
            deltas = {
                "vocab": metrics_post["vocab"] - metrics_pre["vocab"],
                "motifs": metrics_post["motifs"] - metrics_pre["motifs"],
                "atlas_bundled": metrics_post["atlas_bundled"] - metrics_pre["atlas_bundled"],
                "n_live_bindings": metrics_post["n_live_bindings"]
                                   - metrics_pre["n_live_bindings"],
            }
            if deltas["atlas_bundled"] <= 0 and deltas["motifs"] <= 0:
                consecutive_no_landing += 1
            else:
                consecutive_no_landing = 0
        except RuntimeError as e:
            metrics_post = None
            deltas = None
            logger.write({
                "event": "post_status_failed",
                "index": i,
                "error": str(e),
            })

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
        })

        print(f"[live] {successful}/{len(bundles)} "
              f"{bundle.get('bundle_id'):30} "
              f"vocab+{deltas['vocab'] if deltas else '?'} "
              f"bundled+{deltas['atlas_bundled'] if deltas else '?'} "
              f"({elapsed_ms}ms)", flush=True)

        # Substrate-acceptance check
        if consecutive_no_landing >= 3:
            logger.write({
                "event": "pause_no_landing",
                "consecutive": consecutive_no_landing,
            })
            print(f"[orchestrator] pause — 3 consecutive bundles did not increment "
                  f"motifs or bundled count. Review required.", flush=True)
            logger.close()
            return 3

        time.sleep(cfg.min_interval_sec)

    logger.write({
        "event": "live_complete",
        "successful": successful,
        "skipped": skipped,
    })
    logger.close()
    return 0


def main() -> int:
    cfg = OrchestratorConfig.from_args()
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
