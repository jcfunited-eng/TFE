#!/usr/bin/env python3
"""Bounded synthetic component stress runner; NOT a canonical-DSF witness.

The periodic stimuli below are authored test inputs, not kernel outputs, sleep,
dreaming, sensory experience, or a diurnal clock. The native full-field operator
is presently unavailable, so this command must refuse on its first transition.
Do not clear the field or switch to a different binary to manufacture success.

Historical 50,000-cycle telemetry from the rejected operator remains in Git.
Completion, if a future independently accepted operator permits it, establishes
only finite execution and the explicitly measured checkpoint checks below.
It does not establish plastic equilibrium, memory competence or conservation.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate


def synthetic_stimulus(cycle: int, checkpoint_interval: int) -> dict:
    """Preserve the old fixture's inputs without calling them canonical or sleep."""
    if cycle % checkpoint_interval >= (checkpoint_interval * 4) // 5:
        return {"field": None, "sensory": [0] * 64,
                "somatic": [int((cycle + i) % 7 == 0) for i in range(32)],
                "step": {}}
    phase = 2.0 * math.pi * (cycle % 2000) / 2000.0
    reversal = 0.5 if cycle % 4000 == 1999 else -0.3
    field = [0.6 * math.sin(phase), 0.4 * math.cos(phase), reversal,
             0.2 + 0.1 * math.sin(phase * 2.0),
             0.7 + 0.15 * math.cos(phase * 1.5),
             0.8 if cycle % 1000 > 700 else 0.3, 0.5]
    return {"field": (field, 0.90 if reversal < 0 else 0.0),
            "sensory": [int(math.sin(cycle * 0.1 + i) > 0.3) for i in range(64)],
            "somatic": [0] * 32,
            "step": {"observed_r_mm": 800.0 + 300.0 * math.sin(cycle * 0.05),
                     "observed_theta_mdeg": int(30_000 * math.cos(cycle * 0.05)),
                     "barrier_stress": 0.0}}


def _step(sub, stimulus):
    if stimulus["field"] is None:
        sub.clear_continuous_joint_field()
    else:
        field, stability = stimulus["field"]
        sub.consume_continuous_joint_field(field, s_uf=stability)
    return sub.step(stimulus["sensory"], stimulus["somatic"], **stimulus["step"])


def run_burn_in(total_cycles: int = 50_000, checkpoint_interval: int = 10_000) -> dict:
    if not 1 <= total_cycles <= 50_000 or not 2 <= checkpoint_interval <= 10_000:
        raise ValueError("cycles must be 1..50000 and checkpoint interval 2..10000")
    sub = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.05, activation_threshold=0.15, columns=64)
    started = time.perf_counter()
    report = {"status": "running", "evidence_scope": "synthetic_component_stress",
              "completed_cycles": 0, "checkpoint_roundtrips": 0,
              "same_process_next_step_checks": 0, "canonical_uf_used": False,
              "sleep_consolidation_tested": False, "fresh_process_restart_tested": False,
              "physical_equilibrium_proven": False, "memory_competence_proven": False,
              "full_field_closure_proven": False, "cumulative_yields": 0,
              "cumulative_model_strain": 0.0}
    restored = None
    try:
        for cycle in range(total_cycles):
            stimulus = synthetic_stimulus(cycle, checkpoint_interval)
            result = _step(sub, stimulus)
            if not math.isfinite(result[1]) or not all(
                    math.isfinite(x) for x in sub.get_motor_efferent()):
                raise RuntimeError("nonfinite component output")
            if restored is not None:
                cold_result = _step(restored, stimulus)
                if (cold_result != result or
                        restored.export_sparse_bytes(version=4) != sub.export_sparse_bytes(version=4)):
                    raise RuntimeError("same-process restored next-step state mismatch")
                report["same_process_next_step_checks"] += 1
                restored = None
            report["completed_cycles"] += 1
            report["cumulative_yields"] += result[0]
            report["cumulative_model_strain"] += result[1]
            if (cycle + 1) % checkpoint_interval == 0:
                checkpoint = sub.export_sparse_bytes(version=4)
                restored = ModularColumnSubstrate(columns=64)
                restored.import_sparse_bytes(checkpoint)
                if restored.export_sparse_bytes(version=4) != checkpoint:
                    raise RuntimeError("same-process checkpoint roundtrip mismatch")
                report["checkpoint_roundtrips"] += 1
        report["status"] = "completed_component_cycles"
        report["final_active_contacts"] = sub.active_synapses()
        # A last-boundary restore has not executed a successor; do not count one.
        report["final_checkpoint_next_step_unchecked"] = restored is not None
    except NotImplementedError as exc:
        report["status"] = "blocked_unmounted_operator"
        report["error"] = str(exc)
        raise
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        report["elapsed_seconds"] = time.perf_counter() - started
        print(json.dumps(report, sort_keys=True, allow_nan=False), flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=50_000)
    parser.add_argument("--checkpoint-interval", type=int, default=10_000)
    args = parser.parse_args()
    try:
        run_burn_in(args.cycles, args.checkpoint_interval)
    except NotImplementedError:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
