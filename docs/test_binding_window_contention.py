"""Real contention test: many threads calling add_entry on the same
binding window simultaneously.

Setup A: Python WindowManager.add_entry (matches actual substrate code).
Setup B: C bw_add_entry via ctypes (releases GIL).

Both must add N entries total across N_THREADS threads. Measure wall-
clock time. The GIL contention scenario in production is exactly this
shape: many senses arriving in parallel, each needing to add to the
current window.
"""
import ctypes
import os
import time
import threading
import sys
from dataclasses import dataclass, field
from typing import Optional


# Simulate the production WindowManager add_entry hot path in pure Python
@dataclass
class PyWindowEntry:
    modality: str
    section: str
    motif_id: int
    chi: int
    tick: int
    source_tag: str = ""
    provenance: dict = field(default_factory=dict)


@dataclass
class PyBindingWindow:
    window_id: str
    opened_tick: int
    opened_wall_clock: float
    entries: list = field(default_factory=list)
    closed_tick: Optional[int] = None
    closed: bool = False

    def add_entry(self, entry: PyWindowEntry) -> int:
        # Matches production WindowManager: append + return index
        self.entries.append(entry)
        return len(self.entries) - 1


class PyWindowManager:
    """Simulates production WindowManager.add_entry hot path.
    Real production has a threading.Lock — including it here for fidelity.
    """

    def __init__(self):
        self.window = None
        self.lock = threading.Lock()  # matches production
        self._log_events = []  # matches log_event_fn calls

    def open(self, window_id, tick, wall_clock):
        with self.lock:
            self.window = PyBindingWindow(
                window_id=window_id,
                opened_tick=tick,
                opened_wall_clock=wall_clock,
            )
            self._log_events.append(("window_opened", window_id, tick))

    def add_entry(self, modality, section, motif_id, chi, tick, source_tag=""):
        # Approximates production WindowManager.add_entry sequence:
        # lock, validate, create entry, append, log event, unlock.
        with self.lock:
            if self.window is None or self.window.closed:
                return -1
            entry = PyWindowEntry(
                modality=modality, section=section, motif_id=motif_id,
                chi=chi, tick=tick, source_tag=source_tag,
            )
            idx = self.window.add_entry(entry)
            self._log_events.append(("window_entry_added", self.window.window_id, idx))
            return idx


# C implementation via ctypes
lib = ctypes.CDLL('/home/claude/loom/libbindingwindow.so')
lib.bw_open.restype = ctypes.c_void_p
lib.bw_open.argtypes = [ctypes.c_char_p, ctypes.c_int64, ctypes.c_double]
lib.bw_add_entry.restype = ctypes.c_int32
lib.bw_add_entry.argtypes = [
    ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32,
    ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_char_p,
]
lib.bw_entry_count.restype = ctypes.c_int32
lib.bw_entry_count.argtypes = [ctypes.c_void_p]
lib.bw_free.argtypes = [ctypes.c_void_p]


class CWindowManager:
    def __init__(self):
        self.window = None

    def open(self, window_id, tick, wall_clock):
        wid_bytes = window_id.encode('utf-8')
        self.window = lib.bw_open(wid_bytes, tick, wall_clock)

    def add_entry(self, modality_id, section_id, motif_id, chi, tick, source_tag=b""):
        # Direct ctypes call — GIL released during the C code
        return lib.bw_add_entry(
            self.window, modality_id, section_id, motif_id, chi, tick, source_tag
        )

    def close(self):
        if self.window:
            lib.bw_free(self.window)
            self.window = None


def run_threaded_adds(wm_factory, is_c, n_threads, entries_per_thread):
    """Create a fresh WindowManager, open a window, spawn n_threads each
    adding entries_per_thread entries. Measure wall-clock time."""
    wm = wm_factory()
    wm.open("test_window_" + str(id(wm)), 100, time.time())

    barrier = threading.Barrier(n_threads)

    def worker(thread_id):
        barrier.wait()
        if is_c:
            for i in range(entries_per_thread):
                wm.add_entry(0, 0, thread_id * 1000 + i, i, i, b"src")
        else:
            for i in range(entries_per_thread):
                wm.add_entry("sight", "sight", thread_id * 1000 + i, i, i, "src")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if is_c:
        wm.close()
    return elapsed_ms


def test_scaling(name, wm_factory, is_c, entries_per_thread):
    print(f"\n{name}:")
    for n_threads in [1, 2, 4, 8]:
        elapsed = run_threaded_adds(wm_factory, is_c, n_threads, entries_per_thread)
        total_ops = n_threads * entries_per_thread
        rate = total_ops / (elapsed / 1000)
        print(f"  {n_threads} threads × {entries_per_thread:>6} adds: "
              f"{elapsed:8.2f} ms  ({total_ops:>7} total ops, "
              f"{rate:>10,.0f} ops/sec)")


if __name__ == "__main__":
    cpu_count = os.cpu_count() or 1
    print("=" * 78)
    print(f"Binding window add_entry: Python WindowManager vs C via ctypes")
    print(f"CPU cores available: {cpu_count}")
    print("=" * 78)

    # NOTE: MAX_ENTRIES_PER_WINDOW = 1024 in the C code, so cap threads*entries
    # at 1024 to stay under the array bound.
    entries_per_thread = 100  # 8 threads × 100 = 800 < 1024

    test_scaling("Python WindowManager (baseline)",
                 lambda: PyWindowManager(), False, entries_per_thread)

    test_scaling("C binding window via ctypes",
                 lambda: CWindowManager(), True, entries_per_thread)

    print()
    print("=" * 78)
    print("Rate (ops/sec) is the honest measurement.")
    print("Higher rate at higher thread counts = actually parallelizing.")
    print("=" * 78)
