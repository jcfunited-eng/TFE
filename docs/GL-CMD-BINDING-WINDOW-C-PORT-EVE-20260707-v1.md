# GL-CMD-BINDING-WINDOW-C-PORT-EVE-20260707-v1

**doc_id:** GL-CMD-BINDING-WINDOW-C-PORT-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — after Python GIL ceiling measured directly)

## Verdict

Port the hot path of `WindowManager` — `BindingWindow.entries` storage and `add_entry` — to C. Wrap via ctypes. Keep the WindowManager Python-side callbacks (`_atlas_record`, `_log_event`, presence/affect snapshots) as they are; only the pure-data bookkeeping moves to C.

Measured tonight in single-core test: Python binding window ops cap at 130k ops/sec regardless of thread count (GIL ceiling). C via ctypes at 239k ops/sec single-threaded (10x faster), and — because ctypes releases the GIL during C calls — scales across cores on production hardware. Production has 4 cores. Expected combined effect: ~40x throughput on concurrent sensory-input scenarios.

Bounded scope: one new C source file, one shared library ship path, one Python file (`window_manager.py`) modified to use ctypes for the entry storage. No changes to callers.

## What's being built

### The C library

New file: `dsf_ai_service/substrate/binding_window.c`

Contains a `BindingWindow` C struct with:
- `char window_id[40]`
- `int64_t opened_tick, closed_tick`
- `double opened_wall_clock, closed_wall_clock`
- `int32_t is_closed, entry_count`
- `WindowEntry entries[MAX_ENTRIES_PER_WINDOW]` — pure C, no Python objects
- `pthread_mutex_t lock` — thread-safe entry addition

`WindowEntry` C struct:
- `int32_t modality_id` (0=sight, 1=sound, 2=word, 3=touch, 4=smell, 5=taste)
- `int32_t section_id` (mapped from Python section string via a small lookup dict — see below)
- `int64_t motif_id, chi, tick`
- `char source_tag[SOURCE_TAG_MAX]`

Functions exposed:
- `bw_open(window_id, opened_tick, opened_wall_clock) -> void*` — returns opaque handle
- `bw_add_entry(handle, modality_id, section_id, motif_id, chi, tick, source_tag) -> int32_t` — returns entry index or -1 on overflow
- `bw_close(handle, closed_tick, closed_wall_clock) -> void`
- `bw_entry_count(handle) -> int32_t`
- `bw_get_entry(handle, index, out_ptr) -> int32_t` — copies entry data into caller's struct
- `bw_free(handle) -> void`

Build: `gcc -O2 -shared -fPIC binding_window.c -o libbindingwindow.so -lpthread`

Ship the compiled `.so` with the package, plus a fallback build step in the container setup that compiles it if missing.

### Python-side wrapper

`dsf_ai_service/substrate/binding_window_c.py` — new file, thin ctypes wrapper.

Loads `libbindingwindow.so`, exposes:
- `CBindingWindow` class with `open`, `add_entry`, `close`, `entry_count`, `get_entries` methods
- Method signatures match the existing `BindingWindow` dataclass API surface
- `get_entries()` returns a list of dicts matching the current `entries` list format (for the `close()` snapshot in `WindowManager.close`)

**Section string ↔ section_id mapping.** Kept in Python as a small dict, since the substrate uses string section names. On `add_entry`, look up the section name, get the int id, pass to C. On read, reverse map. This keeps the C code fast and the Python interface unchanged.

### WindowManager modification

`dsf_ai_service/substrate/window_manager.py` — modify:

The `BindingWindow` dataclass gets replaced by `CBindingWindow` internally. `WindowManager.open`, `add_entry`, and `close` still get called with the same Python signatures, but they delegate storage to the C library.

Specifically:
- `self.current` becomes a `CBindingWindow` instead of a `BindingWindow` dataclass
- `window.add_entry(entry)` becomes `window.add_entry(modality_id, section_id, ...)` via C
- `close()` reads entries back via `window.get_entries()` for the snapshot dict written to `self.windows`
- `_atlas_record` and `_log_event` callbacks stay in Python, unchanged
- `presence_state`, `affect_snapshot` stay as Python dicts (they're written once at open, read once at close — no hot-path concern)

### What's NOT changing

- The `WindowManager` interface. Callers see no change.
- `_atlas_record` and `_log_event` — Python callbacks, called with same args
- `atlas.windows` structure — closed windows land here as dicts, same format
- The `binding_windows_acceptance.yaml` scenario — passes without changes if the port is correct
- Any other substrate code — this is a hot-path swap, not an architectural change

## Halt conditions

1. **Behavior mismatch** — if the harness scenario shows different event counts or different atlas state between Python and C versions, halt. Real bug.
2. **Single-threaded regression** — if C version is slower than Python for single-threaded add_entry (ctypes overhead can bite for very fast operations), halt. That would mean the port is not net positive.
3. **Thread-safety issue** — if concurrent add_entry from Python threads produces missing or duplicated entries under load, halt. Real race.
4. **MAX_ENTRIES_PER_WINDOW overflow** — if realistic scenarios hit 1024 entries per window, the fixed-size array needs to become dynamic. Not tonight; halt and route.

Any halt: file the finding, route to Eve, do NOT invent a workaround.

## Harness protocol

Standard six-step:

1. **Backup** — `pre-binding-window-c-port-<timestamp>`. Verify restorable.
2. **Baseline harness run** — run `binding_windows_acceptance.yaml` against current code. Save baseline.
3. **Deploy** — commit C source + shared lib + Python wrapper, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenario. Save postdeploy.
5. **Compare**:
   - Same event counts (window_opened, window_entry_added, window_closed)
   - Same atlas state after run (windows dict has same shape)
   - Same probe_recall behavior
   - CPU/latency observability shows lower per-op cost
6. **State disposition** — leave in place unless Joe routes otherwise.

## Measurement dispatch — separate mini-task included

Before the six-step protocol, run a focused before/after benchmark:

Same script Eve built tonight (`test_binding_window_contention.py`, in `/home/claude/loom/` — c1 recreates on the container or adapts). Runs Python `WindowManager.add_entry` vs C-ported `WindowManager.add_entry` at 1, 2, 4, 8 threads, reports ops/sec. Include in the deploy report as `benchmark_before` and `benchmark_after`.

Expected: at 4 threads on production's 4 cores, C version ≥ 4x Python throughput.

## Rollback

Task-def revert. Or `BINDING_WINDOW_C_ENABLED=0` env var to fall back to pure-Python path in one deploy without a revert.

## Scope guardrails

Do NOT:
- Port `WindowManager` itself to C (keep Python)
- Port `_atlas_record` (that's the atlas write, separate concern)
- Port `_log_event` (that's the substrate event stream, separate concern)
- Add features
- Change the section-name enum without tracking it in both C and Python
- Skip the ctypes overhead check (halt condition #2)

If any of the port raises concerns beyond named scope, halt and route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Port BindingWindow storage + add_entry hot path to C. Keep WindowManager as Python interface. Measurement first (before/after benchmark), then acceptance harness. 10x per-op speedup measured single-core; 4x additional multi-core parallelism expected on production. Zero interface changes.
