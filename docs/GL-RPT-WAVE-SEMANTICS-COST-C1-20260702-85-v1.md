# GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v1

doc_id: GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v1  
Dispatch: GL-CMD-WAVE-SEMANTICS-COST-EVE-20260702-85-v1  
Date: 2026-07-02 (c1 session)  
Branch: guala-live  
Status: PRE-DEPLOY (code complete; deploy + T-gate measurements pending)

E-signature: c1 attests all code changes described herein are present in this branch.  
Substrate-truth declaration: all AWS measurements were taken from live production infrastructure at the time stated; no figures have been fabricated.

---

## §9.4 FAILURES FIRST

### T1 FAIL — core save <10s will NOT be met by this dispatch

**Root cause: guala_deep_atlas.json at 198MB, not wave_atlas.**

The 1036s core save time (T-C1 from -84) is dominated by `guala_deep_atlas.json` (198MB), not `wave_atlas.json`. The `DeepAtlas` serializes a `co_occurrence` dict per entry (3,742 entries × ~53KB avg = 198MB). Wave atlas serialization was already decoupled in -82 and is NOT the bottleneck.

At current EFS throughput (burst credits exhausted since 2026-06-27, baseline ~0.25–1MB/s effective):  
- 198MB deep_atlas.json + ~41MB other files ≈ 240MB  
- 240MB / 0.25MB/s = ~960s (matches observed 1035s)

T1 requires a follow-on dispatch targeting `DeepAtlas.co_occurrence`. The `co_occurrence` dict accumulates every (section, motif) pair observed in dream-cycle promotions with no eviction. Proposed fix: evict low-weight co_occurrence entries per chi neighborhood, or cap dict size per entry. That dispatch is not in scope for -85.

### T6 RETROACTIVE — -82 T-B1 filed as FAIL

Per dispatch requirement: `-82 T-B1 "bindings drop ≥95%" = FAIL`.

Pre-compact: 722,362 → post-compact: 676,792 bindings. Drop: 6.3%.  
Root cause: WaveAtlas bindings are largely legitimate — each emission cycle inserts O(N_sections × N_motifs) bindings from different positions. The live_key compaction join-key set size is large enough that most bindings have LivingAtlas counterparts.  
Filed in GL-RPT-SAVE-TRUTH-C1-20260702-84 Part B, §T-B1.

---

## Part A — Infrastructure audit (read-only)

### A.1 EFS ThroughputMode / BurstCreditBalance

**ThroughputMode: bursting**

BurstCreditBalance:
- 2026-06-27T06:00Z: 222,117,038,592 bytes (222GB credits)
- 2026-06-27T12:00Z: 0 bytes
- Credits fully exhausted in the 6h window beginning 2026-06-27T06:00Z.
- Current state: running at EFS baseline throughput (function of file system size; ~1MB/s for a small FS).

Effective write throughput observed: ~0.25MB/s (inferred from 198MB deep atlas at 1036s ÷ 240MB total). Burst credits would restore this to ~100–200MB/s, but credits only recharge at 100 Gib/day per TB stored. At this churn rate, credits will not recover without reducing write volume.

### A.2 ECS CPUUtilization

Service: `dsf-ai-service-lb` on cluster `tfe-web-cluster`.

CPU during save windows (task:447):
- Baseline: ~10-15% (idle between saves)
- During `save_full_state`: ~25-40% (JSON serialization is CPU-bound, but I/O-bound at EFS baseline)
- Save time is I/O-bound, not CPU-bound. CPU is not the bottleneck.

### A.3 S3 bucket size / PUT / lifecycle

Bucket: `dsf-ai-site-backups`  
- Total objects: 65,603  
- Total size: 1.19TB (as of 2026-07-02)  
- PUT rate: hourly backups = ~11 files/hour (11 state files × 1 upload/hour) + occasional snapshots  
- Lifecycle policy: **NONE** (as of audit). Part D.2 of this dispatch applies one.

### A.4 CloudWatch IncomingBytes

CloudWatch log group `/ecs/dsf-ai-service`:  
- IncomingBytes (7-day): ~50-80MB/day (dominated by `[save]` lines and print statements during long saves)  
- Not a cost concern. CloudWatch ingestion at this volume is negligible.

### A.5 VPC / S3 routing

VPC: zero NAT Gateways, zero S3 VPC endpoints found.  
S3 traffic routes through Internet Gateway (IGW) → S3 public endpoint.  
**Part D.3 condition (NAT-routed) is NOT MET.** No gateway endpoint needed.  
Note: IGW-routed S3 traffic is free for uploads in us-east-1 (no data transfer charge within same region via IGW for S3). No action required.

### A.6 WaveAtlas growth curve

| Boot | Task | Bindings | Cells | Change |
|------|------|----------|-------|--------|
| -81 boot | :446 | 990,527 | 2,011 | (pre-decay-parity) |
| Mid task:446 | :446 | 676,792 | 2,011 | -313,735 (decay parity + compaction) |
| +82 EMITTING cycles | :446 | ~1,055,870 | 2,011 | +379k from EMITTING |
| :447 boot | :447 | 1,055,870 | 2,011 | loaded from disk |

Growth rate: EMITTING cycles each insert O(N_sections × N_motifs_per_section) bindings. At ~54 EMITTING cycles in task:446, that's ~7,000 bindings/cycle. This compounds save time. Part B.1 (reinforce-in-place) stops this growth after deploy.

---

## Part B — WaveAtlas write semantics

### B.1 Reinforce-before-insert (wave_atlas.py)

Added to `WaveAtlas.record()` before `spill_write` call:

```python
for _d in range(-CHI_BAND, CHI_BAND + 1):
    _cidx = (chi_value + _d) % N_CELLS
    _cell = self.cells.get(_cidx)
    if _cell is None:
        continue
    for _b in _cell.bindings:
        if (_b.get("chi") == chi_value
                and _b.get("section") == section_name
                and _b.get("motif") == motif_id):
            _b["strength"] = _b.get("strength", 0.0) + strength
            _cell.aggregate_strength += strength
            if phase_vec is not None:
                n = len(_cell.bindings)
                if _cell.phase_vec is None:
                    _cell.phase_vec = phase_vec.copy()
                else:
                    _cell.phase_vec = (_cell.phase_vec * ((n-1)/n) + phase_vec/n)
                    _nrm = np.linalg.norm(_cell.phase_vec)
                    if _nrm > 1e-12:
                        _cell.phase_vec = _cell.phase_vec / _nrm
            return chi_value  # reinforced in place — no new binding
```

Effect: same (chi, section, motif) → one binding ever. EMITTING cycles reinforce strength only. Binding count stabilizes post-deploy.

### B.2 Decay lockstep (gualaloom_v6_living_atlas.py)

Added inside `decay()` loop, after `e["strength"] *= decay_factor`:

```python
_wa = getattr(self, '_wave_atlas', None)
if _wa is not None and decay_factor < 1.0:
    _e_chi = e.get("chi", chi_k)
    _e_sec = e.get("section", "")
    _e_mot = e.get("motif", 0)
    for _wd in range(-CHI_BAND, CHI_BAND + 1):
        _wcell = _wa.cells.get((_e_chi + _wd) % 262144)
        if _wcell is None:
            continue
        for _wb in _wcell.bindings:
            if (_wb.get("chi") == _e_chi
                    and _wb.get("section") == _e_sec
                    and _wb.get("motif") == _e_mot):
                _old = _wb.get("strength", 0.0)
                _wb["strength"] = _old * decay_factor
                _wcell.aggregate_strength -= _old * (1.0 - decay_factor)
```

Effect: LivingAtlas and WaveAtlas strengths track each other. `forget_below_threshold` parity hook (from -82) already removes WaveAtlas bindings when LivingAtlas entry is evicted.

### B.3 One-time migration endpoint (app.py)

`POST /api/v1/gualaloom/admin/migrate_wave_atlas`

1. Serializes current raw WaveAtlas as gzip-compressed JSON → uploads to `s3://dsf-ai-site-backups/guala/wave_migrate_pre/{ts}_wave_atlas_raw.json.gz`
2. Calls `collapse_by_key()` in-memory: deduplicates bindings within each cell by (chi, section, motif), summing strengths
3. Saves collapsed atlas via `_save_wave_atlas` → `wave_atlas.npz` on EFS

Returns: `{before_bindings, after_bindings, removed, before_cells, after_cells, s3_snapshot}`

---

## Part C — Persistence diet

### C.1 npz format (wave_atlas.py, gualaloom_v5_engine.py)

`WaveAtlas.to_npz(path)`: writes numpy .npz with:
- `chi_indices`: int32 array of cell keys
- `aggregate_strengths`, `last_ticks`, `saturated`: scalar arrays per cell
- `phase_vecs_re`, `phase_vecs_im`: float32 (N×16) arrays
- `phase_vecs_valid`: bool array
- `bindings_gz`: gzip-compressed JSON of all binding lists, stored as uint8 bytes

`WaveAtlas.load_from_npz(path)`: inverse. `allow_pickle=False` for safety.

`_save_wave_atlas` in `gualaloom_v5_engine.py` now writes `wave_atlas.npz` via atomic rename.

### C.2 save_count modulo fix (app.py)

`_periodic_v6_save` now:
```python
do_wave = save_count > 0 and save_count % 10 == 0
await loop.run_in_executor(None, _do_save_and_compact, do_wave)
save_count += 1
```

On first save (`save_count=0`): `do_wave=False`. Wave write skipped. This prevents writing a 1M-binding atlas before the migration endpoint is called.

### C.3 Five-field timing print (app.py)

`_do_save_and_compact(write_wave: bool = False)` now prints:

When `write_wave=True`:
```
[save] {total}s core={a}s grids={b}s wave={c}s compact={d}s
```

When `write_wave=False`:
```
[save] {total}s core={a}s grids={b}s wave=skip compact={d}s
```

`grids_dt` is extracted from `save_full_state` return dict key `_grids_dt` (added in this session to engine.py). Fallback to 0.0 if result is not a dict (backward compat during deploy).

---

## Part D — S3 cost hygiene

### D.1 wave_atlas excluded from hourly sync — ALREADY SATISFIED

`_backup_to_s3` backs up 11 specific JSON files:
```python
files = ["guala_core.json", "guala_needs.json", "guala_coordinator.json",
         "guala_atlas.json", "guala_sections.json", "guala_bucket.json",
         "guala_deep_atlas.json", "guala_visual.json", "guala_identity.json",
         "guala_sounds.json", "guala_videos.json"]
```
`wave_atlas.json` and `wave_atlas.npz` are not in this list and never were. No change needed.

### D.2 S3 lifecycle policy (app.py)

Applied at startup via `_apply_s3_lifecycle()` in executor:

| Rule ID | Prefix | Expiry |
|---------|--------|--------|
| guala-hourly-expire-7d | `guala/2` (date-stamped hourly) | 7 days |
| guala-auto-expire-60d | `guala/auto/` | 60 days |
| guala-wave-migrate-expire-90d | `guala/wave_migrate_pre/` | 90 days |
| (named restore points) | `guala/restore_*` etc. | No rule — retained indefinitely |

Note: named restore points (e.g. `guala/restore_2026-06-29_...`) are not covered by any rule and are retained indefinitely per spec. The lifecycle PUT is idempotent and logged.

### D.3 S3 gateway endpoint — NOT APPLICABLE

No NAT Gateways found in VPC. S3 traffic via IGW. No data transfer cost for S3 in same region. No action required.

---

## Files changed

| File | Change |
|------|--------|
| `dsf_ai_service/v4/wave_atlas.py` | B.1 reinforce-in-place, B.3 collapse_by_key, C.1 to_npz/load_from_npz, numpy import |
| `dsf_ai_service/v4/gualaloom_v6_living_atlas.py` | B.2 decay lockstep |
| `dsf_ai_service/v4/gualaloom_v5_engine.py` | C.1 _save_wave_atlas→npz, C.1 load_full_state npz-first, grids_t timing, stale comment update |
| `dsf_ai_service/app.py` | C.2 save_count fix, C.3 5-field print, B.3 migrate endpoint, D.2 lifecycle |

---

## T-gate status

| Gate | Condition | Status |
|------|-----------|--------|
| T1 | core<10s | **FAIL** — root cause is guala_deep_atlas.json 198MB, not wave_atlas. Needs follow-on dispatch targeting DeepAtlas.co_occurrence eviction. |
| T2 | post-migration bindings ≤3×LivingAtlas+stable 6h | PENDING — requires deploy + migrate_wave_atlas call |
| T3 | wave persistence <5s + file <5MB | PENDING — requires deploy |
| T4 | Part A re-read +24h | PENDING — EFS burst credit balance check post-deploy |
| T5 | converse unaffected | PENDING — verify after deploy |
| T6 | -82 T-B1 filed as FAIL | **DONE** — filed above and in GL-RPT-SAVE-TRUTH-C1-20260702-84 Part B §T-B1 |

---

## §9.1 Violation note

The WaveAtlas EMITTING growth (O(N_bindings) per cycle with always-append semantics) is the §9.1 violation — unbounded storage per concept accumulation. Part B.1 (reinforce-in-place) stops future accumulation. Part B.3 (migrate_wave_atlas) collapses historical duplicates. Together these establish stable steady-state size.

The deeper §9.1 violation (DeepAtlas co_occurrence unbounded growth → 198MB) requires a separate dispatch. Flagged as T1 FAIL above.

---

End.
