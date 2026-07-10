#!/usr/bin/env python3
"""gil_scaling_bench.py -- clean-room benchmark harness for the two GIL-escape
hypotheses tested on this substrate the week of 2026-07-06:

  H1 (fine-grained C port): does moving a single hot-path operation
     (BindingWindow.add_entry, WaveAtlas spill_write) into C via ctypes,
     one call per operation, let concurrent Python threads scale across
     cores? Prior measurement: 0.07x-0.14x at 4 threads (WORSE than
     1-thread), against a required >=2-3.5x GO bar. See
     docs/GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1.md and
     docs/GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1.md.

  H2 (free-threaded Python 3.14t): does running the SAME pure-Python hot
     path under a GIL-disabled interpreter let it scale across cores
     without any C port at all? Prior measurement: explicitly confounded
     -- compared a freshly-booted no-GIL test container against LIVE
     PRODUCTION TRAFFIC as the "loaded" baseline, and production's own
     "fresh" baseline swung 3x (9,298ms vs a previously-cited 178ms)
     between two measurements taken minutes apart. See
     docs/GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v3.md, section
     "Contention measurement -- mixed, confounded, genuinely
     inconclusive on the core hypothesis".

WHY THIS HARNESS IS DIFFERENT
------------------------------
Both prior results are suspect for the same underlying reason (confirmed
2026-07-10): dsf_ai_service/v4/gualaloom_v5_engine.py holds a process-wide
lock (`self.lock`) for an entire sentence at a time, contended by
camera/mic frame handling and autosave -- a real, severe, UNRELATED bug
that was live during both tests. H2's method (compare against live
production) bakes that confound directly into the "loaded" number. H1's
method (a shared, ambiently-loaded 20-core dev box, never checked for
other tenants) is vulnerable to the same class of contamination even
though it never talked to production directly.

This harness:
  - NEVER imports gualaloom_v5_engine.py, NEVER constructs a Guala /
    GualaLoomV5Engine instance, NEVER touches self.lock.
  - NEVER makes a network call, NEVER touches AWS/EFS/S3, NEVER talks to
    the live process (local or deployed).
  - Builds its own representative organism/atlas state: the REAL
    WindowManager (dsf_ai_service/substrate/window_manager.py) wired to a
    REAL LivingAtlas (dsf_ai_service/v4/gualaloom_v6_living_atlas.py --
    a standalone, pure-Python/stdlib class with zero engine dependency),
    and the REAL tools/wave_spillover.spill_write against a plain dict of
    Cells, called exactly the way production's WaveAtlas calls it.
  - Drives a fixed, seeded synthetic workload through these actual
    hot-path functions, alone, in its own process, so nothing else
    contends for the GIL or CPU during the measurement it reports.
  - Runs a preflight load-average / CPU-affinity check and prints it
    with the results, rather than silently trusting the box is idle.
  - Does not modify dsf_ai_service/substrate/window_manager.py,
    dsf_ai_service/substrate/binding_window.c,
    dsf_ai_service/substrate/binding_window_c.py, tools/wave_spillover.py,
    dsf_ai_service/v4/gualaloom_v6_living_atlas.py, or bench/*. It only
    imports and calls them.

WHAT IT MEASURES
-----------------
For each of two suites (binding_window, wave_atlas), at a configurable
sweep of thread counts (default 1, 2, 4, 8 -- production targets 4
physical cores; the full sweep gives the scaling curve), median-of-N
repeats:
  - Python-only ops/sec, calling the REAL hot-path function directly.
  - C-via-ctypes ops/sec, calling the already-built, never-wired C ports.
  - C/Python ratio at each thread count (H1's metric -- the historical
    GO bar was >=2-3.5x at 4 threads, NO-GO below 1.5x).
  - N-thread/1-thread scaling ratio for the PYTHON-ONLY path (H2's
    metric -- this is the number to compare before/after switching
    interpreters; it has no ctypes involvement at all, so it isolates
    H2 from H1's ctypes-crossing confound).
  - binding_window suite only: an extra lock-free-C-noop diagnostic
    (bw_entry_count, no mutex) reproducing the original root-cause
    isolation -- if this collapses on the same curve as the real add,
    the bottleneck is the ctypes GIL-crossing handshake itself, not the
    mutex or the algorithm (this was the prior finding; worth
    reconfirming cleanly).

HOW TO USE THIS TO GET A TRUSTWORTHY ANSWER
---------------------------------------------
1. `python3 benchmarks/gil_scaling_bench.py run --label <tag>`
   Run this now (a pre-lock-fix, GIL-enabled sanity check is already
   committed under benchmarks/results/).
2. Once the self.lock fix lands live, re-run the identical command with
   a new --label (e.g. "postlockfix-gil"). This harness needed no
   changes for that -- it never touched the lock, so this step is purely
   about re-establishing the baseline is what changed, not the harness.
3. For H2: install a real free-threaded interpreter (`uv python install
   3.14t`, confirmed viable per docs/GL-RPT-NOGIL-PYTHON-TEST-C1-
   20260707-v2.md for every dependency this script touches -- numpy,
   the stdlib) and run this EXACT script under it, same command, label
   e.g. "postlockfix-nogil314t". No code changes needed -- the
   Python-only code path here has no C-extension dependency beyond numpy
   (used only by the wave_atlas suite).
4. `python3 benchmarks/gil_scaling_bench.py compare A.json B.json`
   prints a side-by-side diff of both hypotheses' headline numbers
   between any two runs (e.g. prelockfix-gil vs postlockfix-nogil314t).

Run it alone. Close other heavy processes first if you can -- the
preflight check reports load average and CPU count so you can judge how
clean the environment was, but it cannot force the box to be idle.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Path setup: make repo-root packages (dsf_ai_service), tools/, and bench/
# importable regardless of cwd. Mirrors bench/wave_atlas_bench.py's own
# pattern -- this file lives at <repo_root>/benchmarks/.
# --------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
for _p in (_REPO_ROOT, os.path.join(_REPO_ROOT, "tools"), os.path.join(_REPO_ROOT, "bench")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Real, unmodified production/benchmark modules -- import only, no edits.
from dsf_ai_service.substrate.window_manager import WindowManager  # noqa: E402
from dsf_ai_service.substrate import binding_window_c as _bwc  # noqa: E402
from dsf_ai_service.v4.gualaloom_v6_living_atlas import LivingAtlas  # noqa: E402
from wave_constants import N_CELLS  # noqa: E402
import wave_atlas_bench as _wab  # noqa: E402  (bench/wave_atlas_bench.py)

RESULTS_DIR = os.path.join(_HERE, "results")


# ==========================================================================
# Environment / isolation reporting
# ==========================================================================

def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=_REPO_ROOT,
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _gil_status() -> str:
    fn = getattr(sys, "_is_gil_enabled", None)
    if fn is None:
        return "gil-only-build (interpreter predates PEP 703 toggle, always GIL-enabled)"
    return "GIL-DISABLED (free-threaded)" if not fn() else "GIL-enabled (free-threaded build, but GIL active)"


def collect_env_info() -> dict:
    affinity = None
    if hasattr(os, "sched_getaffinity"):
        try:
            affinity = sorted(os.sched_getaffinity(0))
        except Exception:
            affinity = None
    loadavg = None
    if hasattr(os, "getloadavg"):
        try:
            loadavg = os.getloadavg()
        except Exception:
            loadavg = None
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "gil_status": _gil_status(),
        "cpu_count_logical": os.cpu_count(),
        "sched_affinity": affinity,
        "loadavg_1_5_15": loadavg,
    }


def preflight_report(env: dict) -> list:
    """Returns a list of warning strings (empty if the box looks idle
    enough to trust). Never blocks the run -- this is disclosure, not
    a gate; the box is a shared dev container, not a lab bench."""
    warnings = []
    cpu = env.get("cpu_count_logical") or 1
    loadavg = env.get("loadavg_1_5_15")
    if loadavg:
        load1 = loadavg[0]
        if load1 > 0.5 * cpu:
            warnings.append(
                f"1-min load average ({load1:.2f}) exceeds half of logical "
                f"CPU count ({cpu}) -- this box has other ambient work "
                f"running right now. Numbers below may be contaminated by "
                f"that, exactly the class of confound this harness exists "
                f"to avoid. Consider re-running when idle, or use "
                f"--pin-cores to at least bound the blast radius."
            )
    if env.get("sched_affinity") and len(env["sched_affinity"]) != cpu:
        warnings.append(
            f"CPU affinity is pinned to {len(env['sched_affinity'])} of "
            f"{cpu} logical CPUs -- intentional if --pin-cores was used, "
            f"otherwise investigate."
        )
    return warnings


def maybe_pin_cores(n) -> None:
    if n is None:
        return
    if not hasattr(os, "sched_setaffinity"):
        print(f"WARNING: --pin-cores {n} requested but os.sched_setaffinity "
              f"is unavailable on this platform; ignoring.", file=sys.stderr)
        return
    cpu = os.cpu_count() or 1
    n = max(1, min(n, cpu))
    os.sched_setaffinity(0, set(range(n)))
    print(f"[pinned to {n} of {cpu} logical CPUs: {sorted(os.sched_getaffinity(0))}]")


# ==========================================================================
# Generic threaded-run helper
# ==========================================================================

def timed_threaded_run(worker_fn, n_threads: int, per_thread_args: list) -> float:
    """Runs worker_fn(args) in n_threads threads, all released together by
    a Barrier (so thread-start skew doesn't leak into the timing), returns
    wall-clock seconds for the whole run (all threads joined)."""
    barrier = threading.Barrier(n_threads)

    def _wrapped(args):
        barrier.wait()
        worker_fn(args)

    threads = [threading.Thread(target=_wrapped, args=(per_thread_args[t],))
               for t in range(n_threads)]
    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    return time.perf_counter() - t0


def repeat_median(fn, repeats: int) -> tuple:
    """Runs fn() `repeats` times, returns (median_seconds, [all_seconds])."""
    samples = [fn() for _ in range(repeats)]
    return statistics.median(samples), samples


# ==========================================================================
# Suite A: binding_window (WindowManager.add_entry / CBindingWindow.add_entry)
# ==========================================================================

_MODALITIES = ["sight", "sound", "word", "touch", "smell", "taste"]
_SECTION_FOR_MODALITY = {
    "sight": "sight", "sound": "audio_low", "word": "word",
    "touch": "modal_touch", "smell": "smell", "taste": "taste",
}


def _gen_binding_workload(rng: random.Random, n_threads: int, ops_per_thread: int) -> list:
    """Representative synthetic sensory/word stream -- deterministic given
    seed, pre-generated OUTSIDE the timed region (matches
    bench/wave_atlas_bench.py's own documented discipline: compare
    implementations on pure hot-path cost, not RNG cost)."""
    out = []
    for _t in range(n_threads):
        thread_ops = []
        for _i in range(ops_per_thread):
            m = rng.choice(_MODALITIES)
            thread_ops.append({
                "modality": m,
                "section": _SECTION_FOR_MODALITY[m],
                "motif_id": rng.randint(0, 50_000),
                "chi": rng.randint(0, N_CELLS - 1),
                "source_tag": "bench",
            })
        out.append(thread_ops)
    return out


def run_python_binding(thread_data: list, n_threads: int) -> float:
    """Drives the REAL WindowManager.add_entry -> REAL LivingAtlas.record,
    exactly as dsf_ai_service/v4/gualaloom_v5_engine.py wires it (minus
    the engine's own reverse-index/write-counter bookkeeping in
    _atlas_record, which is engine-specific, not part of the
    window/atlas-write hot path this suite targets).

    Deliberately NOT wrapped in any extra lock -- the real WindowManager
    class has no internal lock of its own (production's serialization
    today comes entirely from the engine's coarse self.lock, which this
    harness does not use). This is a faithful, honest reproduction of
    what "the hot path, freed of the coarse sentence-lock" looks like.
    """
    atlas = LivingAtlas()
    tick_counter = iter(range(1, 10_000_000))
    wm = WindowManager(
        atlas_record_fn=atlas.record,
        log_event_fn=lambda *a, **k: None,
        get_tick_fn=lambda: next(tick_counter),
        atlas_windows=atlas.windows,
    )
    wm.open(trigger_reason="bench")

    def worker(ops):
        for op in ops:
            wm.add_entry(op["modality"], op["section"], op["motif_id"],
                         op["chi"], source_tag=op["source_tag"])

    return timed_threaded_run(worker, n_threads, thread_data)


def run_c_binding(thread_data: list, n_threads: int) -> float:
    """Drives the REAL, already-built (never wired into window_manager.py)
    CBindingWindow.add_entry via ctypes -- same call shape the 2026-07-07
    halt report measured."""
    if not _bwc.c_backend_available():
        raise RuntimeError("libbindingwindow.so not built/loadable")
    cw = _bwc.CBindingWindow("bench_window", opened_tick=0, opened_wall_clock=time.time(),
                              trigger_reason="bench")

    def worker(ops):
        for op in ops:
            cw.add_entry(op["modality"], op["section"], op["motif_id"],
                         op["chi"], tick=0, source_tag=op["source_tag"])

    elapsed = timed_threaded_run(worker, n_threads, thread_data)
    cw.free()
    return elapsed


def run_c_binding_nolock_diagnostic(n_threads: int, ops_per_thread: int) -> float:
    """Root-cause isolation control, reproduced from the original halt
    report: calls bw_entry_count (a real, LOCK-FREE, zero-work C read) the
    same number of times under the same thread sweep. If this collapses on
    the same curve as the real bw_add_entry call, the bottleneck is the
    ctypes GIL-release/reacquire handshake itself, not the mutex or the
    algorithm -- confirmed via binding_window.c's own source (bw_entry_count
    takes no lock)."""
    if not _bwc.c_backend_available():
        raise RuntimeError("libbindingwindow.so not built/loadable")
    cw = _bwc.CBindingWindow("bench_nolock", opened_tick=0, opened_wall_clock=time.time(),
                              trigger_reason="bench")
    handle = cw._handle  # read-only use of the real loaded lib handle
    lib = _bwc._lib

    def worker(_ops):
        for _ in range(ops_per_thread):
            lib.bw_entry_count(handle)

    elapsed = timed_threaded_run(worker, n_threads, [None] * n_threads)
    cw.free()
    return elapsed


# ==========================================================================
# Suite B: wave_atlas (tools.wave_spillover.spill_write / WaveAtlasC)
# ==========================================================================
# Reuses bench/wave_atlas_bench.py's own workload generator and distribution
# functions directly (gen_chi_uniform / gen_chi_clumpy / prepare_writes) so
# the write shape is identical to the original Phase-1 measurement -- this
# suite only supplies its own sweep/repeat driver.

def run_python_wave(thread_data: list, n_threads: int) -> float:
    return _wab.run_python_baseline(thread_data, n_threads)


def run_c_wave(thread_data: list, n_threads: int) -> float:
    return _wab.run_c_port(thread_data, n_threads)


# ==========================================================================
# Sweep orchestration
# ==========================================================================

def run_binding_suite(thread_counts: list, ops_per_thread: int, repeats: int,
                       seed: int, include_nolock_diagnostic: bool) -> dict:
    rng = random.Random(seed)
    results = {"python": {}, "c": {}, "c_nolock_diagnostic": {}}
    for n in thread_counts:
        thread_data = _gen_binding_workload(rng, n, ops_per_thread)
        total_ops = n * ops_per_thread

        med, raw = repeat_median(lambda: run_python_binding(thread_data, n), repeats)
        results["python"][n] = {"elapsed_s_median": med, "elapsed_s_all": raw,
                                 "ops": total_ops, "ops_per_sec": total_ops / med}

        if _bwc.c_backend_available():
            med, raw = repeat_median(lambda: run_c_binding(thread_data, n), repeats)
            results["c"][n] = {"elapsed_s_median": med, "elapsed_s_all": raw,
                                "ops": total_ops, "ops_per_sec": total_ops / med}

            if include_nolock_diagnostic:
                med, raw = repeat_median(
                    lambda: run_c_binding_nolock_diagnostic(n, ops_per_thread), repeats)
                results["c_nolock_diagnostic"][n] = {
                    "elapsed_s_median": med, "elapsed_s_all": raw,
                    "ops": total_ops, "ops_per_sec": total_ops / med}
    return results


def run_wave_suite(thread_counts: list, ops_per_thread: int, repeats: int,
                    seed: int, distributions: list) -> dict:
    results = {dist: {"python": {}, "c": {}} for dist in distributions}
    for dist in distributions:
        for n in thread_counts:
            dseed = (seed + hash((dist, n))) & 0xFFFFFFFF
            thread_data = _wab.prepare_writes(n, ops_per_thread, dist, dseed)
            total_ops = n * ops_per_thread

            med, raw = repeat_median(lambda: run_python_wave(thread_data, n), repeats)
            results[dist]["python"][n] = {"elapsed_s_median": med, "elapsed_s_all": raw,
                                           "ops": total_ops, "ops_per_sec": total_ops / med}

            if _wab.c_backend_available():
                med, raw = repeat_median(lambda: run_c_wave(thread_data, n), repeats)
                results[dist]["c"][n] = {"elapsed_s_median": med, "elapsed_s_all": raw,
                                          "ops": total_ops, "ops_per_sec": total_ops / med}
    return results


# ==========================================================================
# Reporting
# ==========================================================================

def _fmt_rate(x: float) -> str:
    return f"{x:,.0f}"


def print_binding_table(results: dict, thread_counts: list) -> None:
    print("\n--- Suite A: binding_window (WindowManager/LivingAtlas real hot path) ---")
    print(f"{'threads':>8} {'python ops/s':>14} {'c ops/s':>14} {'C/Py':>8} "
          f"{'py Nx-scale':>12} {'c Nx-scale':>11} {'c-nolock ops/s':>16}")
    py1 = results["python"].get(thread_counts[0], {}).get("ops_per_sec")
    c1 = results["c"].get(thread_counts[0], {}).get("ops_per_sec")
    for n in thread_counts:
        py = results["python"].get(n, {}).get("ops_per_sec")
        c = results["c"].get(n, {}).get("ops_per_sec")
        nl = results["c_nolock_diagnostic"].get(n, {}).get("ops_per_sec")
        ratio = f"{c / py:.2f}x" if (py and c) else "n/a"
        py_scale = f"{py / py1:.2f}x" if (py and py1) else "n/a"
        c_scale = f"{c / c1:.2f}x" if (c and c1) else "n/a"
        print(f"{n:>8} {_fmt_rate(py) if py else 'n/a':>14} "
              f"{_fmt_rate(c) if c else 'n/a':>14} {ratio:>8} "
              f"{py_scale:>12} {c_scale:>11} "
              f"{_fmt_rate(nl) if nl else 'n/a':>16}")


def print_wave_table(results: dict, thread_counts: list) -> None:
    print("\n--- Suite B: wave_atlas (tools.wave_spillover.spill_write real hot path) ---")
    for dist, d in results.items():
        print(f"\n  distribution: {dist}")
        print(f"  {'threads':>8} {'python ops/s':>14} {'c ops/s':>14} {'C/Py':>8} "
              f"{'py Nx-scale':>12} {'c Nx-scale':>11}")
        py1 = d["python"].get(thread_counts[0], {}).get("ops_per_sec")
        c1 = d["c"].get(thread_counts[0], {}).get("ops_per_sec")
        for n in thread_counts:
            py = d["python"].get(n, {}).get("ops_per_sec")
            c = d["c"].get(n, {}).get("ops_per_sec")
            ratio = f"{c / py:.2f}x" if (py and c) else "n/a"
            py_scale = f"{py / py1:.2f}x" if (py and py1) else "n/a"
            c_scale = f"{c / c1:.2f}x" if (c and c1) else "n/a"
            print(f"  {n:>8} {_fmt_rate(py) if py else 'n/a':>14} "
                  f"{_fmt_rate(c) if c else 'n/a':>14} {ratio:>8} "
                  f"{py_scale:>12} {c_scale:>11}")


def print_headline(env: dict, warnings: list, binding: dict, wave: dict,
                    thread_counts: list) -> None:
    print("=" * 92)
    print("gil_scaling_bench -- clean-room GIL-escape measurement (no live production involved)")
    print("=" * 92)
    print(f"git_sha={env['git_sha']}  python={env['python_implementation']} "
          f"{platform.python_version()}  gil_status={env['gil_status']}")
    print(f"cpu_count_logical={env['cpu_count_logical']}  "
          f"sched_affinity={env['sched_affinity']}  loadavg={env['loadavg_1_5_15']}")
    for w in warnings:
        print(f"WARNING: {w}")

    four = 4 if 4 in thread_counts else thread_counts[-1]
    one = thread_counts[0]
    print(f"\nHEADLINE (thread count {four} vs {one}):")

    c4 = binding["c"].get(four, {}).get("ops_per_sec")
    py4 = binding["python"].get(four, {}).get("ops_per_sec")
    py1 = binding["python"].get(one, {}).get("ops_per_sec")
    if c4 and py4:
        print(f"  H1 (binding_window C-port): C/Python ratio at {four} threads = "
              f"{c4 / py4:.3f}x  (historical GO bar: >=2-3.5x; NO-GO: <1.5x; "
              f"prior measurement: 0.14x at 4 threads)")
    if py4 and py1:
        print(f"  H2 (binding_window free-threading potential): Python-only "
              f"{four}-thread/{one}-thread scaling = {py4 / py1:.3f}x  "
              f"(ideal free-threaded ~= {four / one:.1f}x; GIL-bound python "
              f"today should sit well below that)")

    uni = wave.get("uniform", {})
    c4w = uni.get("c", {}).get(four, {}).get("ops_per_sec")
    py4w = uni.get("python", {}).get(four, {}).get("ops_per_sec")
    py1w = uni.get("python", {}).get(one, {}).get("ops_per_sec")
    if c4w and py4w:
        print(f"  H1 (wave_atlas C-port, uniform): C/Python ratio at {four} threads = "
              f"{c4w / py4w:.3f}x  (historical GO bar: >=3.5x; "
              f"prior measurement: 0.071x)")
    if py4w and py1w:
        print(f"  H2 (wave_atlas free-threading potential): Python-only "
              f"{four}-thread/{one}-thread scaling = {py4w / py1w:.3f}x")


# ==========================================================================
# CLI
# ==========================================================================

def cmd_run(args: argparse.Namespace) -> None:
    maybe_pin_cores(args.pin_cores)
    env = collect_env_info()
    warnings = preflight_report(env)

    thread_counts = [int(x) for x in args.threads.split(",")]
    cpu = env["cpu_count_logical"] or 1
    over = [n for n in thread_counts if n > cpu]
    if over:
        warnings.append(f"Requested thread counts {over} exceed logical CPU count "
                         f"({cpu}) -- oversubscription will show as artificially poor "
                         f"scaling, not a GIL/C-boundary finding.")

    ops_window = 20 if args.quick else args.ops_per_thread_window
    ops_wave = 100 if args.quick else args.ops_per_thread_wave
    repeats = 1 if args.quick else args.repeats

    suites = set(args.suites.split(","))
    binding_results = None
    wave_results = None

    if "binding_window" in suites:
        binding_results = run_binding_suite(
            thread_counts, ops_window, repeats, seed=args.seed,
            include_nolock_diagnostic=not args.quick)
    if "wave_atlas" in suites:
        wave_results = run_wave_suite(
            thread_counts, ops_wave, repeats, seed=args.seed,
            distributions=list(_wab.DISTRIBUTIONS.keys()))

    if binding_results and wave_results:
        print_headline(env, warnings, binding_results, wave_results, thread_counts)
    else:
        print("=" * 92)
        print("gil_scaling_bench -- partial run (one suite skipped)")
        print(f"git_sha={env['git_sha']}  gil_status={env['gil_status']}")
        for w in warnings:
            print(f"WARNING: {w}")
    if binding_results:
        print_binding_table(binding_results, thread_counts)
    if wave_results:
        print_wave_table(wave_results, thread_counts)

    payload = {
        "env": env,
        "warnings": warnings,
        "config": {
            "thread_counts": thread_counts, "ops_per_thread_window": ops_window,
            "ops_per_thread_wave": ops_wave, "repeats": repeats, "seed": args.seed,
            "label": args.label, "quick": args.quick,
        },
        "binding_window": binding_results,
        "wave_atlas": wave_results,
    }
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = args.label or ("quick" if args.quick else "run")
    out_path = Path(RESULTS_DIR) / f"{ts}_{label}_{env['git_sha']}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n[results written to {out_path}]")


def _headline_pair(data, four: int, one: int):
    if not data:
        return None, None
    c4 = data.get("c", {}).get(str(four), data.get("c", {}).get(four, {})).get("ops_per_sec")
    py4 = data.get("python", {}).get(str(four), data.get("python", {}).get(four, {})).get("ops_per_sec")
    py1 = data.get("python", {}).get(str(one), data.get("python", {}).get(one, {})).get("ops_per_sec")
    h1 = (c4 / py4) if (c4 and py4) else None
    h2 = (py4 / py1) if (py4 and py1) else None
    return h1, h2


def cmd_compare(args: argparse.Namespace) -> None:
    a = json.loads(Path(args.file_a).read_text())
    b = json.loads(Path(args.file_b).read_text())
    for tag, r, fname in (("A", a, args.file_a), ("B", b, args.file_b)):
        env = r["env"]
        print(f"[{tag}] {fname}")
        print(f"     label={r['config'].get('label')}  git_sha={env['git_sha']}  "
              f"python={env['python_implementation']} {env.get('python_version', '').splitlines()[0]}  "
              f"gil_status={env['gil_status']}")

    tcs_a = a["config"]["thread_counts"]
    tcs_b = b["config"]["thread_counts"]
    four = 4 if (4 in tcs_a and 4 in tcs_b) else min(tcs_a[-1], tcs_b[-1])
    one = 1 if (1 in tcs_a and 1 in tcs_b) else min(tcs_a[0], tcs_b[0])

    print(f"\nHEADLINE COMPARISON (thread count {four} vs {one}):")
    for suite_name, get in (
        ("binding_window", lambda r: r.get("binding_window")),
        ("wave_atlas.uniform", lambda r: (r.get("wave_atlas") or {}).get("uniform")),
        ("wave_atlas.clumpy", lambda r: (r.get("wave_atlas") or {}).get("clumpy")),
    ):
        h1_a, h2_a = _headline_pair(get(a), four, one)
        h1_b, h2_b = _headline_pair(get(b), four, one)
        print(f"\n  {suite_name}:")
        if h1_a is not None or h1_b is not None:
            print(f"    H1 C/Python ratio @ {four}t:  A={h1_a and f'{h1_a:.3f}x'}  "
                  f"B={h1_b and f'{h1_b:.3f}x'}")
        if h2_a is not None or h2_b is not None:
            print(f"    H2 Python {four}t/{one}t scaling: A={h2_a and f'{h2_a:.3f}x'}  "
                  f"B={h2_b and f'{h2_b:.3f}x'}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run the benchmark sweep")
    run_p.add_argument("--threads", default="1,2,4,8",
                        help="comma-separated thread counts to sweep (default 1,2,4,8)")
    run_p.add_argument("--repeats", type=int, default=3,
                        help="repeats per (impl, config); median is reported (default 3)")
    run_p.add_argument("--ops-per-thread-window", type=int, default=200)
    run_p.add_argument("--ops-per-thread-wave", type=int, default=1000)
    run_p.add_argument("--seed", type=int, default=1234)
    run_p.add_argument("--pin-cores", type=int, default=None,
                        help="pin this process to the first N logical CPUs via "
                             "os.sched_setaffinity (Linux only)")
    run_p.add_argument("--suites", default="binding_window,wave_atlas")
    run_p.add_argument("--label", default=None,
                        help="tag stored in the JSON output and its filename, e.g. "
                             "'prelockfix-gil' or 'postlockfix-nogil314t'")
    run_p.add_argument("--quick", action="store_true",
                        help="tiny smoke-test sizes, 1 repeat, no diagnostics -- "
                             "verifies the harness runs end-to-end in seconds")
    run_p.set_defaults(func=cmd_run)

    cmp_p = sub.add_parser("compare", help="diff two JSON result files")
    cmp_p.add_argument("file_a")
    cmp_p.add_argument("file_b")
    cmp_p.set_defaults(func=cmd_compare)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
