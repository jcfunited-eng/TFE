#!/usr/bin/env python3
"""bench_organism_core.py -- UN-CONFOUNDED organism hot-path benchmark.

GL native-core track, 2026-07-16. The C-port test of ~2 weeks ago ran under
the since-removed coarse global lock; this harness measures the REAL,
post-lock-narrowing cost of the organism worker's hot path, standalone
(no engine, no service, no AWS), so the numbers are attributable to the
substrate math itself and become the baseline any native (Rust) port must
beat.

What it measures, on a REAL production-shaped organism
(Embryo(brain_seed=42, seed_size=8, observable="event_count") -- the exact
constructor gualaloom_v5_engine.py:2958 uses, 64 neurons / 8 hemispheres --
warmed by driving N synthetic words through the real experience_word path,
the same way the live organism worker feeds it):

  1. organism.experience_word per-call cost -- language-only words and
     multi-modal (real-shaped visual ~100 samples + auditory ~300 samples,
     matching process_sight_frame's _flat[::step][:100] and
     process_sound_frame's 200Hz downsample) measured separately, because
     the cascade cost differs structurally (language-only composite is
     zeros(1) -> sig_res 0 -> em-only fold; multi-modal cascades through
     DEFAULT_PAIRS).
  2. neuron.step per-call -- word input and array input, plus the
     64-neuron full-population sweep cost (the wave-summary sensory-push
     shape).
  3. SpikeBus delivery throughput -- pre-filled drain and sustained
     concurrent-injection, plus raw receive_spike cost without the bus.
  4. GIL exposure: the same word stream driven by 1 thread vs 4
     concurrent feeder threads (each on its OWN pickle-restored organism
     copy, so there is no shared-object lock contention -- any failure to
     scale is interpreter serialization, not application locking).
  5. cProfile of experience_word (top cumulative), to answer "is the time
     interpretable Python math or dict-shuffling?"

Usage:
  python3 tools/bench_organism_core.py                 # full run
  python3 tools/bench_organism_core.py --quick         # small sizes
  python3 tools/bench_organism_core.py --warmup 1000   # deeper lifetime

PYTHONHASHSEED is forced to 0 (re-exec) for reproducibility -- salted
hash() seeding is a documented source of run-to-run wobble in this
codebase (gualaloom capacity-probe finding).
"""

import argparse
import cProfile
import io
import math
import os
import pickle
import pstats
import statistics
import sys
import threading
import time

# --- reproducibility: force PYTHONHASHSEED=0 before numpy/substrate load ---
if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np  # noqa: E402

from dsf_ai_service.loom_model.embryo import Embryo  # noqa: E402
from dsf_ai_service.substrate.spike_bus import PendingSpike, SpikeBus  # noqa: E402
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (  # noqa: E402
    ROLE_DNA, SENSORY_DNA,
)

# ---------------------------------------------------------------------------
# Word stream + signal shapes (production-shaped)
# ---------------------------------------------------------------------------

_FILLER = (
    "the and was her she with that said little into when them from garden "
    "door key robin wall spring wind moor magic children secret every "
    "morning again looked thought found under trees green grass roses "
    "walked whispered slowly quietly opened locked hidden inside outside "
    "remember believe wonder curious strange lovely bright"
).split()


def build_word_stream(n, rng):
    """Deterministic mixed stream: SENSORY_DNA words (DNA hits), ROLE_DNA
    words, and filler English -- the shape of a real read/teach session."""
    vocab = sorted(set(list(SENSORY_DNA.keys()) + list(ROLE_DNA.keys()) + _FILLER))
    idx = rng.integers(0, len(vocab), size=n)
    return [vocab[i] for i in idx]


def make_signal(word, multimodal, rng):
    """Production signal shape (gualaloom_v5_engine._organism_signal_with_
    senses): language always; visual/auditory only when a real frame is in
    the binding window. visual = flattened grayscale grid subsample (100
    floats in [0,1]); auditory = 200Hz downsampled mono audio in [-1,1]."""
    sig = {"language": word}
    if multimodal:
        sig["visual"] = rng.random(100)
        sig["auditory"] = rng.uniform(-1.0, 1.0, 300)
    return sig


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _ms(x):
    return x * 1000.0


def summarize(samples_s):
    """samples in seconds -> dict of ms stats."""
    if not samples_s:
        return {"n": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    xs = sorted(samples_s)
    n = len(xs)
    return {
        "n": n,
        "mean": _ms(statistics.fmean(xs)),
        "p50": _ms(xs[n // 2]),
        "p95": _ms(xs[min(n - 1, int(n * 0.95))]),
        "max": _ms(xs[-1]),
    }


def fmt_row(label, st, extra=""):
    return (f"| {label:<44} | {st['n']:>5} | {st['mean']:>9.2f} | "
            f"{st['p50']:>9.2f} | {st['p95']:>9.2f} | {st['max']:>9.2f} |{extra}")


TABLE_HEADER = (
    "| measurement                                  |     n |  mean ms  |"
    "   p50 ms  |   p95 ms  |   max ms  |\n"
    "|----------------------------------------------|-------|-----------|"
    "-----------|-----------|-----------|"
)


# ---------------------------------------------------------------------------
# 1. Build the production-shaped organism
# ---------------------------------------------------------------------------

def drive_words(org, words, mm_flags, rng, collect=False):
    """Drive words through the REAL path (experience_word). Returns
    (lang_samples, mm_samples) per-call seconds if collect else None."""
    lang, mm = [], []
    for w, is_mm in zip(words, mm_flags):
        sig = make_signal(w, is_mm, rng)
        t0 = time.perf_counter()
        org.experience_word(w, sig)
        dt = time.perf_counter() - t0
        if collect:
            (mm if is_mm else lang).append(dt)
        # drain fold telemetry like the engine does (cheap, keeps buffer bounded)
        org.pop_fold_events()
    return lang, mm


def build_organism(n_warmup, mm_frac, rng):
    org = Embryo(brain_seed=42, seed_size=8, observable="event_count")
    words = build_word_stream(n_warmup, rng)
    mm_flags = rng.random(n_warmup) < mm_frac
    t0 = time.perf_counter()
    lang, mm = drive_words(org, words, mm_flags, rng, collect=True)
    wall = time.perf_counter() - t0
    return org, words, {"lang": lang, "mm": mm, "wall": wall}


# ---------------------------------------------------------------------------
# 2. neuron.step micro-benchmarks
# ---------------------------------------------------------------------------

def bench_neuron_step(org, n_calls, rng):
    em = org.hemi_by_op["em"]
    neuron = em.cluster.neurons[0]
    tick = org.tick

    word_samples = []
    for i in range(n_calls):
        w = "water" if i % 2 == 0 else "garden"
        t0 = time.perf_counter()
        neuron.step(w, tick + i, None)
        word_samples.append(time.perf_counter() - t0)

    arr = list(rng.uniform(-1.0, 1.0, 52))  # wave-summary band-signal size
    arr_samples = []
    for i in range(n_calls):
        t0 = time.perf_counter()
        neuron.step(arr, tick + n_calls + i, None)
        arr_samples.append(time.perf_counter() - t0)

    # full-population sweep: all 64 neurons once (wave-push shape)
    sweep_samples = []
    all_neurons = [n for h in org.brain.hemispheres for n in h.cluster.neurons]
    for i in range(max(3, n_calls // 40)):
        t0 = time.perf_counter()
        for n_obj in all_neurons:
            n_obj.step(arr, tick + 2 * n_calls + i, None)
        sweep_samples.append(time.perf_counter() - t0)

    return word_samples, arr_samples, sweep_samples, len(all_neurons)


def bench_neuron_step_threads(org_pickles, n_threads, n_calls):
    """Each thread steps neuron 0 of a DIFFERENT restored organism copy --
    zero shared application state, pure GIL exposure."""
    orgs = [pickle.loads(p) for p in org_pickles[:n_threads]]
    neurons = [o.hemi_by_op["em"].cluster.neurons[0] for o in orgs]
    barrier = threading.Barrier(n_threads)
    walls = [0.0] * n_threads

    def run(k):
        n_obj = neurons[k]
        barrier.wait()
        t0 = time.perf_counter()
        for i in range(n_calls):
            n_obj.step("water", i, None)
        walls[k] = time.perf_counter() - t0

    threads = [threading.Thread(target=run, args=(k,)) for k in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_calls = n_threads * n_calls
    return total_calls / max(walls)  # aggregate steps/s over the slowest lane


# ---------------------------------------------------------------------------
# 3. Spike delivery
# ---------------------------------------------------------------------------

_SUB_THRESHOLD_W = 0.001  # 64 neurons x hundreds of spikes stays << threshold


def bench_spike_drain(org, n_spikes):
    """Pre-fill the bus queue, then start it and measure drain wall time."""
    registry = {n.neuron_id: n
                for h in org.brain.hemispheres for n in h.cluster.neurons}
    ids = list(registry.keys())
    bus = SpikeBus(registry)
    for i in range(n_spikes):
        bus.inject(ids[i % len(ids)], "_bench", _SUB_THRESHOLD_W, 0.0)
    t0 = time.perf_counter()
    bus.start()
    while bus.delivered_count + bus.dropped_count < n_spikes:
        if time.perf_counter() - t0 > 120.0:
            break
        time.sleep(0.001)
    wall = time.perf_counter() - t0
    bus.stop()
    delivered = bus.delivered_count
    return delivered, wall, delivered / wall if wall > 0 else 0.0


def bench_spike_concurrent(org, n_spikes, n_injectors):
    """Sustained: injectors racing the delivery thread (production shape --
    fires inject while the bus drains)."""
    registry = {n.neuron_id: n
                for h in org.brain.hemispheres for n in h.cluster.neurons}
    ids = list(registry.keys())
    bus = SpikeBus(registry)
    bus.start()
    per = n_spikes // n_injectors
    barrier = threading.Barrier(n_injectors + 1)

    def inject(k):
        barrier.wait()
        for i in range(per):
            bus.inject(ids[(k * per + i) % len(ids)], "_bench",
                       _SUB_THRESHOLD_W, 0.0)

    threads = [threading.Thread(target=inject, args=(k,))
               for k in range(n_injectors)]
    for t in threads:
        t.start()
    barrier.wait()
    t0 = time.perf_counter()
    total = per * n_injectors
    while bus.delivered_count + bus.dropped_count < total:
        if time.perf_counter() - t0 > 120.0:
            break
        time.sleep(0.001)
    wall = time.perf_counter() - t0
    for t in threads:
        t.join()
    bus.stop()
    return bus.delivered_count, wall, bus.delivered_count / wall if wall > 0 else 0.0


def bench_receive_spike_direct(org, n_calls):
    """receive_spike cost without the bus (isolates neuron-side cost from
    queue/thread overhead)."""
    neuron = org.hemi_by_op["pr"].cluster.neurons[1]
    spike = PendingSpike(arrival_time=0.0, target_neuron_id=neuron.neuron_id,
                         source_neuron_id="_bench", weight=_SUB_THRESHOLD_W)
    t0 = time.perf_counter()
    for _ in range(n_calls):
        neuron.receive_spike(spike)
    wall = time.perf_counter() - t0
    return n_calls / wall if wall > 0 else 0.0, _ms(wall / n_calls)


# ---------------------------------------------------------------------------
# 4. Feeder-thread scaling (GIL exposure) on experience_word
# ---------------------------------------------------------------------------

def bench_feeder_threads(org_pickles, words, mm_flags, n_threads, seed):
    """n_threads, each with its OWN organism copy and the SAME word list.
    Returns (aggregate words/s, per-call mean ms)."""
    orgs = [pickle.loads(p) for p in org_pickles[:n_threads]]
    barrier = threading.Barrier(n_threads)
    walls = [0.0] * n_threads

    def run(k):
        rng = np.random.default_rng(seed + k)
        barrier.wait()
        t0 = time.perf_counter()
        drive_words(orgs[k], words, mm_flags, rng)
        walls[k] = time.perf_counter() - t0

    threads = [threading.Thread(target=run, args=(k,)) for k in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = max(walls)
    total_words = n_threads * len(words)
    return total_words / wall, _ms(wall * n_threads / total_words)


# ---------------------------------------------------------------------------
# 5. Profile
# ---------------------------------------------------------------------------

def profile_experience_word(org, n_words, mm_frac, rng, top=15):
    words = build_word_stream(n_words, rng)
    mm_flags = rng.random(n_words) < mm_frac
    pr = cProfile.Profile()
    pr.enable()
    drive_words(org, words, mm_flags, rng)
    pr.disable()
    buf = io.StringIO()
    stats = pstats.Stats(pr, stream=buf)
    stats.sort_stats("cumulative").print_stats(top)
    cum = buf.getvalue()
    buf2 = io.StringIO()
    stats2 = pstats.Stats(pr, stream=buf2)
    stats2.sort_stats("tottime").print_stats(top)
    return cum, buf2.getvalue()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--warmup", type=int, default=300,
                    help="words driven to build the production-shaped organism")
    ap.add_argument("--measure", type=int, default=60,
                    help="words measured after warmup")
    ap.add_argument("--mm-frac", type=float, default=0.25,
                    help="fraction of words carrying real visual+auditory frames")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--spikes", type=int, default=20000)
    ap.add_argument("--neuron-calls", type=int, default=200)
    ap.add_argument("--thread-words", type=int, default=30,
                    help="words per feeder thread in the scaling test")
    ap.add_argument("--profile-words", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-profile", action="store_true")
    ap.add_argument("--native", action="store_true",
                    help="swap in the guala_core (Rust) kernels via "
                         "dsf_ai_service.substrate.native_core.install() "
                         "before building/measuring (build-time fallback: "
                         "refuses if the wheel is not installed)")
    args = ap.parse_args()

    if args.native:
        from dsf_ai_service.substrate import native_core
        if not native_core.install():
            print("ERROR: --native requested but guala_core wheel is not "
                  "installed (pip install native/guala_core/dist/*.whl)")
            sys.exit(2)

    if args.quick:
        args.warmup = min(args.warmup, 80)
        args.measure = min(args.measure, 20)
        args.spikes = min(args.spikes, 4000)
        args.neuron_calls = min(args.neuron_calls, 60)
        args.thread_words = min(args.thread_words, 8)
        args.profile_words = min(args.profile_words, 12)

    rng = np.random.default_rng(args.seed)
    mode = "NATIVE (guala_core Rust kernels)" if args.native else "pure Python"
    print(f"# bench_organism_core -- mode={mode}, "
          f"PYTHONHASHSEED={os.environ['PYTHONHASHSEED']}, "
          f"python {sys.version.split()[0]}, numpy {np.__version__}, "
          f"nproc={os.cpu_count()}")
    print(f"# warmup={args.warmup} words, mm_frac={args.mm_frac}, seed={args.seed}")

    if args.native:
        # FFI overhead at real call granularity: one boundary crossing with a
        # minimal payload, vs the same 1-sample feed in pure Python.
        import guala_core as _gc
        from dsf_ai_service.substrate import native_core as _nc
        n_ffi = 100_000
        t0 = time.perf_counter()
        for _ in range(n_ffi):
            _gc.krim_feed(0.0, 0.0, 0, 0, 2.0, 80.0, 0.04, math.pi / 3, [0.5])
        ffi_us = (time.perf_counter() - t0) / n_ffi * 1e6
        _k = __import__("dsf_ai_service.v4.gualaloom_v4_krimelack_dna",
                        fromlist=["Krimelack"])
        kp = _k.Krimelack(omega_0=2.0, kappa=80.0, dt=0.04,
                          threshold=math.pi / 3)
        py_feed = _nc._originals["v4_feed"]
        t0 = time.perf_counter()
        for _ in range(n_ffi):
            py_feed(kp, [0.5])
        py_us = (time.perf_counter() - t0) / n_ffi * 1e6
        print(f"# FFI overhead: krim_feed(1 sample) = {ffi_us:.2f} us/crossing "
              f"(pure-Python same call: {py_us:.2f} us) -- natural batch "
              f"level is one signal per crossing (word: 4*len chars; "
              f"audio: ~300; visual: ~100 samples)")

    # -- build ---------------------------------------------------------------
    t0 = time.perf_counter()
    org, _, warm = build_organism(args.warmup, args.mm_frac, rng)
    n_neurons = org.brain.total_neurons()
    print(f"# organism built: {n_neurons} neurons / "
          f"{len(org.brain.hemispheres)} hemispheres, tick={org.tick}, "
          f"divisions={getattr(org, '_total_divisions', 0)}, "
          f"build wall={time.perf_counter() - t0:.1f}s")

    # lifetime scaling: first 50 vs last 50 warmup calls (all kinds pooled)
    pooled = warm["lang"] + warm["mm"]
    half = len(pooled) // 2

    # -- measured experience_word --------------------------------------------
    words_m = build_word_stream(args.measure, rng)
    mm_flags_m = rng.random(args.measure) < args.mm_frac
    lang_s, mm_s = drive_words(org, words_m, mm_flags_m, rng, collect=True)

    # -- neuron.step ----------------------------------------------------------
    w_s, a_s, sweep_s, n_all = bench_neuron_step(org, args.neuron_calls, rng)

    # -- spike bus ------------------------------------------------------------
    d_count, d_wall, d_rate = bench_spike_drain(org, args.spikes)
    c_count, c_wall, c_rate = bench_spike_concurrent(org, args.spikes, args.threads)
    rs_rate, rs_ms = bench_receive_spike_direct(org, max(2000, args.spikes // 4))

    # -- thread scaling --------------------------------------------------------
    org_pickle = pickle.dumps(org)
    org_pickles = [org_pickle] * max(args.threads, 1)
    tw = build_word_stream(args.thread_words, rng)
    tw_mm = rng.random(args.thread_words) < args.mm_frac
    thr1_rate, thr1_ms = bench_feeder_threads(org_pickles, tw, tw_mm, 1, args.seed)
    thrN_rate, thrN_ms = bench_feeder_threads(org_pickles, tw, tw_mm,
                                              args.threads, args.seed + 100)
    step1 = bench_neuron_step_threads(org_pickles, 1, args.neuron_calls)
    stepN = bench_neuron_step_threads(org_pickles, args.threads, args.neuron_calls)

    # -- report ----------------------------------------------------------------
    print()
    label = ("NATIVE guala_core kernels" if args.native
             else "pure Python, post-lock-narrowing")
    print(f"## BASELINE TABLE ({label}, standalone)")
    print(TABLE_HEADER)
    print(fmt_row("experience_word (language-only)", summarize(lang_s)))
    print(fmt_row("experience_word (multi-modal)", summarize(mm_s)))
    print(fmt_row(f"warmup first-half pooled (n={half})", summarize(pooled[:half])))
    print(fmt_row(f"warmup second-half pooled", summarize(pooled[half:])))
    print(fmt_row("neuron.step (word input)", summarize(w_s)))
    print(fmt_row("neuron.step (array input, 52 samples)", summarize(a_s)))
    print(fmt_row(f"population sweep ({n_all} neuron.steps)", summarize(sweep_s)))
    print()
    print("## THROUGHPUT / CONCURRENCY")
    print(f"spike drain (pre-filled {args.spikes}):        "
          f"{d_rate:>10.0f} spikes/s  (delivered {d_count} in {d_wall:.2f}s)")
    print(f"spike sustained ({args.threads} injector threads): "
          f"{c_rate:>10.0f} spikes/s  (delivered {c_count} in {c_wall:.2f}s)")
    print(f"receive_spike direct (no bus):        "
          f"{rs_rate:>10.0f} calls/s   ({rs_ms:.4f} ms/call)")
    print()
    print(f"experience_word feeders x1:  {thr1_rate:>8.2f} words/s "
          f"(mean {thr1_ms:.1f} ms/word)")
    print(f"experience_word feeders x{args.threads}:  {thrN_rate:>8.2f} words/s "
          f"(mean {thrN_ms:.1f} ms/word)")
    print(f"  -> scaling factor {thrN_rate / thr1_rate:.2f}x of ideal "
          f"{args.threads}.0x ({100 * thrN_rate / thr1_rate / args.threads:.0f}% "
          f"parallel efficiency)")
    print(f"neuron.step x1 thread:  {step1:>10.0f} steps/s")
    print(f"neuron.step x{args.threads} threads: {stepN:>10.0f} steps/s "
          f"aggregate -> scaling {stepN / step1:.2f}x of ideal {args.threads}.0x")

    # -- profile ----------------------------------------------------------------
    if not args.no_profile:
        print()
        print(f"## PROFILE: experience_word x{args.profile_words} "
              f"(mm_frac={args.mm_frac}) -- top by CUMULATIVE time")
        cum, tot = profile_experience_word(org, args.profile_words,
                                           args.mm_frac, rng)
        print(cum)
        print("## PROFILE -- top by TOTTIME (self time)")
        print(tot)


if __name__ == "__main__":
    main()
