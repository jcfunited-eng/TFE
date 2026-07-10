# benchmarks/

Clean-room benchmark infrastructure. Measurement only -- nothing here is
imported by production code, nothing here talks to the live process
(local or deployed), nothing here touches AWS/EFS/S3 or the network.
Safe to run anywhere, anytime, repeatedly, alone.

## gil_scaling_bench.py

Re-measures the two GIL-escape hypotheses tested 2026-07-07
(`docs/GL-RPT-BINDING-WINDOW-C-PORT-BUILD-C1-20260707-v1.md`,
`docs/GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1.md`,
`docs/GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v1/v2/v3.md`) without either
prior confound: no comparison against live production traffic, and no
dependence on a shared box's ambient load being invisible. See the
module docstring in `gil_scaling_bench.py` for the full design rationale
-- short version: it drives the REAL hot-path functions
(`WindowManager.add_entry`, `LivingAtlas.record`,
`tools.wave_spillover.spill_write`, and the already-built-but-unwired C
ports) against a synthetic, seeded workload, standalone, in its own
process.

### Run it

```
python3 benchmarks/gil_scaling_bench.py run --label <tag>
```

Useful flags: `--threads 1,2,4,8` (default), `--repeats 3` (default,
median reported), `--pin-cores N` (pin to N logical CPUs via
`os.sched_setaffinity`), `--quick` (tiny smoke-test sizes, verifies the
harness itself runs end-to-end in a few seconds). Full default run takes
well under a minute. Results print to stdout and are written as JSON to
`benchmarks/results/<timestamp>_<label>_<git_sha>.json`.

### Compare two runs

```
python3 benchmarks/gil_scaling_bench.py compare A.json B.json
```

### Getting a trustworthy answer once the self.lock fix lands

1. A pre-fix, GIL-enabled sanity check is committed at
   `benchmarks/results/*_prelockfix-gil311-sanitycheck_*.json` (Python
   3.11, this repo's default interpreter). It reproduces the historical
   signature cleanly and confounder-free: the C ports collapse under
   thread count (e.g. the lock-free `bw_entry_count` diagnostic alone
   goes from ~992k ops/sec at 1 thread to ~50k ops/sec at 8 threads, with
   zero contention on any shared state) -- consistent with the original
   finding that the bottleneck is the ctypes GIL-crossing handshake
   itself, not any mutex or algorithm, and not (as this harness proves by
   construction) contamination from live traffic or `self.lock`.
2. Once the `self.lock` fix in `gualaloom_v5_engine.py` lands, re-run the
   identical command with a new `--label` (e.g. `postlockfix-gil`). This
   script needs no changes for that step -- it never imported that lock in
   the first place, so a delta here isolates whatever the fix actually
   changed about the underlying interpreter/hardware picture, not about
   this measurement's own validity.
3. For the free-threaded-Python hypothesis: install a real free-threaded
   interpreter (`uv python install 3.14t`; every dependency this script
   touches -- numpy plus the stdlib -- is confirmed `cp314t`-clean per
   `docs/GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v2.md`) and run this exact
   script under it, same command, e.g. `--label postlockfix-nogil314t`.
   No code changes needed. Compare the **Python-only** N-thread/1-thread
   scaling ratio (the `py Nx-scale` column / the H2 headline) between the
   GIL and no-GIL runs -- that number has no ctypes involvement at all, so
   it is the clean test of whether free-threading actually helps this
   substrate's real hot paths, undistorted by the ctypes-crossing cost
   that sank the C-port approach (H1).
4. Use `compare` to print both hypotheses' headline numbers side by side
   for any two runs.
