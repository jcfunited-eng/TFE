"""farm.py — the lesson-falsification farm. Charter: shared ledger
2026-09-12 (farm charter v1 + Sol's concurrency amendment, binding).

WHAT IT IS: a cage that runs DECLARED lesson trials one at a time
against disposable copies of a saved practice body, measures each
trial's peak memory, and files every result — failures included.
It selects nothing, grades nothing, merges nothing back: grading is
whatever pre-declared structural fact the trial's own probe reports,
and a "winner" is only ever believed after replication on a fresh
copy (procedural rule, enforced by the ledger, not this code).

BATCH CONTRACT: a batch file guala_farm/batches/<name>.json must be
COMMITTED to git before it runs (declared-before-launch, enforced),
and holds: {"batch": name, "declared_claim": one falsifiable sentence,
"trials": [{"lesson_id", "command"}...]} — each command is a complete
shell command (Sol's probe contract; this harness never edits speech
files or invents probe parameters). Results land in
guala_farm/results/<batch>/<lesson_id>.json with exit code, wall
seconds, peak RSS KiB, and the probe's own output receipt.

CEILINGS (charter): sequential only (concurrency 1 until the first
measured single-copy peak is filed and a higher bound is recorded in
the ledger); max 16 trials per batch; max 4 batches per invocation;
nice 15; STOP file halts between trials; no retry of any trial.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BATCHES = os.path.join(HERE, "batches")
RESULTS = os.path.join(HERE, "results")
STOP = os.path.join(HERE, "STOP")
LOG = os.path.join(HERE, "farm.log")
MAX_TRIALS = 16
MAX_BATCHES = 4


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as fh:
        fh.write(line + "\n")


def committed(path: str) -> bool:
    """Declared-before-launch: the batch file must be in git HEAD."""
    rel = os.path.relpath(path, os.path.dirname(HERE))
    r = subprocess.run(["git", "-C", os.path.dirname(HERE), "cat-file", "-e",
                        f"HEAD:{rel}"], capture_output=True)
    return r.returncode == 0


def run_trial(batch: str, trial: dict) -> dict:
    lesson = trial["lesson_id"]
    out_dir = os.path.join(RESULTS, batch)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{lesson}.json")
    if os.path.exists(out_path):
        log(f"{batch}/{lesson}: already run — never retried, skipping")
        return json.load(open(out_path))
    t0 = time.time()
    proc = subprocess.run(
        ["nice", "-n", "15", "bash", "-c", trial["command"]],
        capture_output=True, text=True, timeout=3600)
    wall = time.time() - t0
    peak_kib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    rec = {
        "batch": batch, "lesson_id": lesson,
        "exit": proc.returncode, "wall_s": round(wall, 1),
        "peak_rss_kib_cumulative_max": peak_kib,
        "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-1000:],
        "command_sha256": hashlib.sha256(trial["command"].encode()).hexdigest(),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    json.dump(rec, open(out_path, "w"), indent=1)
    log(f"{batch}/{lesson}: exit {proc.returncode} in {wall:.0f}s "
        f"peak-so-far {peak_kib//1024} MiB")
    return rec


def main() -> None:
    names = sys.argv[1:]
    if not names:
        print("usage: farm.py <batch-name> [...]  (batches/<name>.json, committed)")
        return
    if len(names) > MAX_BATCHES:
        log(f"refused: {len(names)} batches exceeds ceiling {MAX_BATCHES}")
        return
    for name in names:
        path = os.path.join(BATCHES, f"{name}.json")
        if not os.path.exists(path):
            log(f"refused: {path} missing")
            return
        if not committed(path):
            log(f"refused: batch '{name}' is not committed — declare it "
                "in git (and the ledger) before launch")
            return
        batch = json.load(open(path))
        trials = batch.get("trials") or []
        if len(trials) > MAX_TRIALS:
            log(f"refused: {len(trials)} trials exceeds ceiling {MAX_TRIALS}")
            return
        log(f"batch {name}: {len(trials)} trials — claim: "
            f"{batch.get('declared_claim','(none)')[:120]}")
        for trial in trials:
            if os.path.exists(STOP):
                log("STOP file present — halting between trials")
                return
            run_trial(name, trial)
        log(f"batch {name} complete; all results filed under results/{name}/")


if __name__ == "__main__":
    main()
