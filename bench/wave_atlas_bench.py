"""wave_atlas_bench.py — Phase 1 (measurement-only) benchmark: Python
tools.wave_spillover.spill_write vs. the C port in wave_atlas_bench.c,
under real multi-threaded contention.

Per GL dispatch: standalone benchmark harness only. Does NOT wire the C
port into production (dsf_ai_service/v4/wave_atlas.py, tools/wave_spillover.py
are untouched by this file).

Two pieces:
  1. A ctypes wrapper (`WaveAtlasC`) around bench/libwaveatlasbench.so.
     The native WaveAtlasC* handle is kept fully opaque (ctypes.c_void_p),
     never mirrored as a ctypes.Structure -- it embeds pthread_mutex_t[256],
     whose layout is platform/libc-specific. Mirroring that in Python risks
     silent memory corruption on a layout mismatch (same reasoning as
     dsf_ai_service/substrate/binding_window_c.py's CBindingWindow). Every
     field access goes through a real C accessor function instead.
  2. A benchmark harness (adapted from docs/test_binding_window_contention.py's
     pattern -- barrier-started threads, wall-clock timing, ops/sec -- but the
     call shape here is different: spill_write takes a chi_target + a 16-dim
     complex phase vector + a strength-bearing binding, not a fixed tuple of
     scalar fields).

Baseline fidelity note (per dispatch spec): production's real WaveAtlas
(dsf_ai_service/v4/wave_atlas.py) is explicitly documented "lock-free" and
does NOT wrap spill_write in any lock today. The Python baseline below calls
the real tools.wave_spillover.spill_write directly against a plain dict of
cells with NO added lock -- this is not a bug in this benchmark, it is a
faithful reproduction of what production actually does (GIL-serialized
bytecode, races and all). Do not "fix" it here.
"""
from __future__ import annotations

import ctypes
import os
import random
import sys
import threading
import time
from typing import Callable, Optional

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
_TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from wave_spillover import spill_write  # noqa: E402  (Cell not needed directly -- dict values are Cell instances spill_write creates itself)
from wave_constants import N_CELLS  # noqa: E402

_SO_NAME = "libwaveatlasbench.so"
PHASE_FLOATS = 32   # 16 complex numbers, re/im interleaved
HOP_LIMIT = 512      # matches wave_spillover.py's _hop_limit default


# ─── ctypes wrapper ─────────────────────────────────────────────────────────

_lib = None
_lib_load_error: Optional[str] = None


def _load_lib():
    global _lib, _lib_load_error
    if _lib is not None or _lib_load_error is not None:
        return
    so_path = os.path.join(_HERE, _SO_NAME)
    try:
        lib = ctypes.CDLL(so_path)
        lib.wa_open.restype = ctypes.c_void_p
        lib.wa_open.argtypes = []

        lib.wa_spill_write.restype = ctypes.c_int64
        lib.wa_spill_write.argtypes = [
            ctypes.c_void_p,               # WaveAtlasC*
            ctypes.c_int64,                # chi_target
            ctypes.POINTER(ctypes.c_float),  # phase_vec_in_or_null (32 floats)
            ctypes.c_int32,                # has_phase_vec_in
            ctypes.c_int64,                # motif_id
            ctypes.c_double,               # strength
            ctypes.c_int32,                # hop_limit
        ]

        lib.wa_get_cell_snapshot.restype = ctypes.c_int32
        lib.wa_get_cell_snapshot.argtypes = [
            ctypes.c_void_p, ctypes.c_int64,
            ctypes.POINTER(ctypes.c_double),  # out_aggregate_strength
            ctypes.POINTER(ctypes.c_int32),   # out_is_saturated
            ctypes.POINTER(ctypes.c_int32),   # out_binding_count
            ctypes.POINTER(ctypes.c_float),   # out_phase_vec_32
            ctypes.POINTER(ctypes.c_int32),   # out_has_phase_vec
        ]

        lib.wa_get_cell_binding_motif_ids.restype = ctypes.c_int32
        lib.wa_get_cell_binding_motif_ids.argtypes = [
            ctypes.c_void_p, ctypes.c_int64,
            ctypes.POINTER(ctypes.c_int64), ctypes.c_int32,
        ]

        lib.wa_free.restype = None
        lib.wa_free.argtypes = [ctypes.c_void_p]

        _lib = lib
    except OSError as e:
        _lib_load_error = str(e)


_load_lib()


def c_backend_available() -> bool:
    return _lib is not None


class WaveAtlasC:
    """Drop-in-ish wrapper around the native WaveAtlasC*. The handle is a
    plain ctypes.c_void_p -- opaque on purpose (see module docstring)."""

    def __init__(self):
        if _lib is None:
            raise RuntimeError(f"{_SO_NAME} not loaded: {_lib_load_error}")
        self._handle = _lib.wa_open()
        if not self._handle:
            raise MemoryError("wa_open returned NULL (native allocation failed)")
        self._freed = False

    def spill_write(self, chi_target: int, phase_vec_floats, motif_id: int,
                     strength: float, hop_limit: int = HOP_LIMIT) -> int:
        """phase_vec_floats: a ctypes (c_float*32) array, a sequence of 32
        floats, or None for a phase-less write."""
        if phase_vec_floats is None:
            has_phase = 0
            phase_ptr = None
        else:
            if not isinstance(phase_vec_floats, ctypes.Array):
                floats = list(phase_vec_floats)
                assert len(floats) == PHASE_FLOATS
                phase_vec_floats = (ctypes.c_float * PHASE_FLOATS)(*floats)
            has_phase = 1
            phase_ptr = phase_vec_floats
        return _lib.wa_spill_write(
            self._handle, int(chi_target), phase_ptr, has_phase,
            int(motif_id), float(strength), int(hop_limit),
        )

    def get_cell_snapshot(self, idx: int) -> Optional[dict]:
        agg = ctypes.c_double()
        sat = ctypes.c_int32()
        bcount = ctypes.c_int32()
        phase = (ctypes.c_float * PHASE_FLOATS)()
        has_phase = ctypes.c_int32()
        ok = _lib.wa_get_cell_snapshot(
            self._handle, int(idx), ctypes.byref(agg), ctypes.byref(sat),
            ctypes.byref(bcount), phase, ctypes.byref(has_phase),
        )
        if not ok:
            return None
        return {
            "aggregate_strength": agg.value,
            "is_saturated": bool(sat.value),
            "binding_count": bcount.value,
            "has_phase_vec": bool(has_phase.value),
            "phase_vec": list(phase) if has_phase.value else None,
        }

    def get_cell_binding_motif_ids(self, idx: int, max_count: int = 4096) -> list:
        arr = (ctypes.c_int64 * max_count)()
        n = _lib.wa_get_cell_binding_motif_ids(self._handle, int(idx), arr, max_count)
        return list(arr[:n])

    def free(self) -> None:
        if not self._freed and self._handle:
            _lib.wa_free(self._handle)
            self._handle = None
            self._freed = True

    def __del__(self):
        try:
            self.free()
        except Exception:
            pass


# ─── quick sanity smoke test (not the Phase-2 verification harness -- just
#     enough to catch a crash / NaN / non-unit-norm before trusting timings) ──

def _smoke_test():
    a = WaveAtlasC()
    rng = random.Random(1)
    for i in range(50):
        floats = [rng.uniform(-1.0, 1.0) for _ in range(PHASE_FLOATS)]
        a.spill_write(chi_target=1000 + (i % 5), phase_vec_floats=floats,
                       motif_id=i, strength=rng.uniform(0.1, 2.0))
    snap = a.get_cell_snapshot(1000)
    assert snap is not None
    import math
    assert not math.isnan(snap["aggregate_strength"])
    if snap["has_phase_vec"]:
        nrm = sum(v * v for v in snap["phase_vec"]) ** 0.5
        assert abs(nrm - 1.0) < 1e-3, f"phase_vec not unit norm: {nrm}"
    a.free()


# ─── chi_target distributions ───────────────────────────────────────────────

HOT_CENTER = N_CELLS // 2
HOT_RADIUS = 2000


def gen_chi_uniform(rng: random.Random, n: int) -> list:
    return [rng.randint(0, N_CELLS - 1) for _ in range(n)]


def gen_chi_clumpy(rng: random.Random, n: int) -> list:
    """80% drawn from a narrow hot window (fixed center +/- 2000), 20%
    uniform across the full range -- creates real contention on the same
    handful of buckets across threads, unlike uniform which spreads thin."""
    lo = max(0, HOT_CENTER - HOT_RADIUS)
    hi = min(N_CELLS - 1, HOT_CENTER + HOT_RADIUS)
    out = []
    for _ in range(n):
        if rng.random() < 0.8:
            out.append(rng.randint(lo, hi))
        else:
            out.append(rng.randint(0, N_CELLS - 1))
    return out


DISTRIBUTIONS: dict = {
    "uniform": gen_chi_uniform,
    "clumpy": gen_chi_clumpy,
}


# ─── write payload pre-generation (kept OUT of the timed region so both
#     implementations are compared on pure spill_write cost, not RNG /
#     data-marshalling overhead) ────────────────────────────────────────────

def prepare_writes(n_threads: int, ops_per_thread: int, distribution: str,
                    seed: int) -> list:
    """Returns a list (len n_threads) of lists (len ops_per_thread) of dicts:
    {chi, floats, complex_arr, c_floats, motif_id, strength}.

    strength: random.uniform(0.1, 2.0) per write (documented choice -- varied
    strengths exercise saturation timing more realistically than a fixed 1.0).
    motif_id: thread_id * 1_000_000 + i, unique per write as specified.
    """
    gen_chi = DISTRIBUTIONS[distribution]
    rng = random.Random(seed)
    thread_data = []
    for t in range(n_threads):
        chi_targets = gen_chi(rng, ops_per_thread)
        writes = []
        for i in range(ops_per_thread):
            floats = [rng.uniform(-1.0, 1.0) for _ in range(PHASE_FLOATS)]
            complex_arr = np.array(
                [complex(floats[2 * k], floats[2 * k + 1]) for k in range(16)],
                dtype=np.complex128,
            )
            c_floats = (ctypes.c_float * PHASE_FLOATS)(*floats)
            motif_id = t * 1_000_000 + i
            strength = rng.uniform(0.1, 2.0)
            writes.append({
                "chi": chi_targets[i],
                "complex_arr": complex_arr,
                "c_floats": c_floats,
                "motif_id": motif_id,
                "strength": strength,
            })
        thread_data.append(writes)
    return thread_data


# ─── run one (impl, distribution, n_threads) combo ─────────────────────────

def run_python_baseline(thread_data: list, n_threads: int) -> float:
    """Real tools.wave_spillover.spill_write against a shared plain dict,
    NO added lock -- matches production's lock-free design (see module
    docstring)."""
    cells: dict = {}
    barrier = threading.Barrier(n_threads)

    def worker(writes):
        barrier.wait()
        for w in writes:
            binding = {"motif_id": w["motif_id"], "strength": w["strength"]}
            spill_write(cells, w["chi"], w["complex_arr"], binding)

    threads = [threading.Thread(target=worker, args=(thread_data[t],))
               for t in range(n_threads)]
    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    return time.perf_counter() - t0


def run_c_port(thread_data: list, n_threads: int) -> float:
    atlas = WaveAtlasC()
    barrier = threading.Barrier(n_threads)

    def worker(writes):
        barrier.wait()
        for w in writes:
            atlas.spill_write(w["chi"], w["c_floats"], w["motif_id"], w["strength"])

    threads = [threading.Thread(target=worker, args=(thread_data[t],))
               for t in range(n_threads)]
    t0 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    elapsed = time.perf_counter() - t0
    atlas.free()
    return elapsed


# ─── main sweep: 2 distributions x 2 impls x 4 thread counts = 16 runs ──────

THREAD_COUNTS = [1, 2, 4, 8]
OPS_PER_THREAD = 1000


def run_sweep():
    results = []  # (impl, distribution, n_threads, elapsed_s, ops_per_sec)
    for distribution in DISTRIBUTIONS:
        for n_threads in THREAD_COUNTS:
            # Same seed per (distribution, n_threads) so both implementations
            # see the same generated writes -- an apples-to-apples workload,
            # even though the two atlases are independent objects/dicts.
            seed = hash((distribution, n_threads)) & 0xFFFFFFFF
            thread_data = prepare_writes(n_threads, OPS_PER_THREAD, distribution, seed)

            py_elapsed = run_python_baseline(thread_data, n_threads)
            total_ops = n_threads * OPS_PER_THREAD
            py_rate = total_ops / py_elapsed
            results.append(("python", distribution, n_threads, py_elapsed, py_rate))

            c_elapsed = run_c_port(thread_data, n_threads)
            c_rate = total_ops / c_elapsed
            results.append(("c", distribution, n_threads, c_elapsed, c_rate))

    return results


def print_report(results: list):
    cpu_count = os.cpu_count() or 1
    print("=" * 88)
    print("WaveAtlas spill_write: Python baseline vs. C port (Phase 1, measurement-only)")
    print(f"CPU cores available: {cpu_count}")
    print(f"ops per thread: {OPS_PER_THREAD}, thread counts: {THREAD_COUNTS}")
    print("=" * 88)

    for distribution in DISTRIBUTIONS:
        print(f"\n--- distribution: {distribution} ---")
        print(f"{'threads':>8} {'impl':>8} {'elapsed_s':>12} {'total_ops':>10} {'ops/sec':>14}")
        for impl in ("python", "c"):
            for n_threads in THREAD_COUNTS:
                for r in results:
                    if r[0] == impl and r[1] == distribution and r[2] == n_threads:
                        _, _, nt, elapsed, rate = r
                        total_ops = nt * OPS_PER_THREAD
                        print(f"{nt:>8} {impl:>8} {elapsed:>12.4f} {total_ops:>10} {rate:>14,.0f}")

        print(f"\n  speedup (C ops/sec ÷ Python ops/sec) at each thread count:")
        for n_threads in THREAD_COUNTS:
            py_rate = next(r[4] for r in results if r[0] == "python" and r[1] == distribution and r[2] == n_threads)
            c_rate = next(r[4] for r in results if r[0] == "c" and r[1] == distribution and r[2] == n_threads)
            print(f"    {n_threads} threads: {c_rate / py_rate:6.2f}x")

    print()
    print("=" * 88)
    print("Rate (ops/sec) is the honest measurement. Higher rate at higher thread")
    print("counts = actually parallelizing (GIL released during C calls).")
    print("=" * 88)


if __name__ == "__main__":
    print("Running smoke test...")
    _smoke_test()
    print("Smoke test passed.\n")

    results = run_sweep()
    print_report(results)
