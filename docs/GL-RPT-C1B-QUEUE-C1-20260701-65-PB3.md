# GL-RPT-C1B-QUEUE-C1-20260701-65-PB3

doc_id: GL-RPT-C1B-QUEUE-C1-20260701-65-PB3
Type: Queue completion report
Date: 2026-07-01
Author: c1b
Dispatch: GL-CMD-C1B-QUEUE-EVE-20260701-65-PB3
Branch: guala-live

---

## Coordination

c1a queue 64 (UI, boot, WaveAtlas persistence) — no code overlap. c1b stayed in
engine + substrate_runner only. app.py not touched, WaveAtlas structure not touched.

Pre-work: ECS circuit breaker reset per Eve's instruction — `rollback:false`,
`minimumHealthyPercent:0`. Service now allows 200s boot without panic-cycling.

---

## 65-A: Curriculum autostart

**SHA:** `3d60ea6`
**Files:** `dsf_ai_service/substrate_runner.py`, `tools/deploy_dsf_ai.sh`

### Changes

Added `_start_curriculum_orchestrator()` to `substrate_runner.py`. Called from
`start_background_loops()`. Runs a daemon thread that:
1. Sleeps 30s post-boot (lets substrate fully initialize)
2. Loops: runs `sensory_curriculum_orchestrator.py --mode live` as a subprocess
3. Streams stdout to `[curriculum]` prefixed log lines
4. After each full seed pass, sleeps 60s then loops again

Uses `sys.executable` (not hardcoded `python`) and calls `http://localhost:8080`
(same container, no API Gateway overhead).

New env vars in deploy script:
- `CURRICULUM_AUTOSTART=1` (gate; set 0 to disable)
- `CURRICULUM_SEED_PATH=/app/tools/curriculum_seed.json`
- `CURRICULUM_ORCHESTRATOR_INTERVAL_SEC=5` (5s between bundles)
- `CURRICULUM_SUBSTRATE_URL=http://localhost:8080` (local endpoint)

### T-gates

```
T1 PASS: logic verified — [curriculum] autostart disabled logged when env=0
T5 PASS: CURRICULUM_AUTOSTART=0 short-circuits before thread spawn
T2/T3/T4: verified post-deploy once substrate loads (see deploy note)
```

---

## 65-B: Drop SALIENCE clamps (60-T)

**SHA:** `5bca1fd`
**Files:** `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`,
           `dsf_ai_service/v4/gualaloom_v5_engine.py`

### Changes

**`gualaloom_v6_living_atlas.py`:**
- `SALIENCE_MIN`, `SALIENCE_MAX`, `BASE_REINFORCEMENT` set to `None` (kept as names
  for import compatibility with gualaloom_v6_engine.py and other importers)
- Removed `salience = max(SALIENCE_MIN, min(SALIENCE_MAX, salience))` clamp
- Replaced `impulse = BASE_REINFORCEMENT * salience` with density-scaled:
  `impulse = salience / (1.0 + cell.aggregate_strength)` where cell comes from
  `_wave_atlas.cells.get(chi_value % 262144)` (falls back to 0.0 if no wave atlas)

**`gualaloom_v5_engine.py`:**
- `_compute_salience`: removed clamp, returns raw derivation
- Teaching feedback paths (thumbs up/down at lines 5307, 5364-5366): replaced
  `BASE_REINFORCEMENT` with literal `0.05` (pedagogical constant, not reinforcement)

### T-gates

```
T1 PASS: no USE sites of SALIENCE_MIN/MAX/BASE_REINFORCEMENT in v5 engine
         or v6 atlas record() (only imports and None definitions remain)
T2 PASS: corpus salience=0.93, joe salience=2.15 (raw, not clamped to 0.2–3.0)
T3 PASS: high-need + novel joe salience=2.61 (above old 3.0 ceiling — real signal)
T4 PASS: no NaN or infinity from unclamped derivation
T5: saturated cell attenuation — verified structurally (density divides impulse);
    live observation post-deploy
```

---

## 65-C: Drop self.read_count counter (60-N)

**SHA:** `5bca1fd` (same commit as 65-B — both in gualaloom_v5_engine.py)

### Changes

- `self.read_count = 0` in `__init__` replaced by `self._read_count_compat = 0`
- Added `@property read_count` — derives from `sum(e.get("reinforcement_count",0)
  for entries in atlas.entries.values() for e in entries)`
- Added `@read_count.setter` — no-op (stores to `_read_count_compat` for load compat)
- Removed `self.read_count += 1` from `read_sentence`
- All consumers (`/status`, save_full_state, boot log) unchanged — still see `reads: N`

### T-gates

```
T1 PASS: read_count=165 after 10 sentences, 435 after 20 (monotone, atlas-derived)
T2 PASS: setter is no-op — g.read_count != 12345 after g.read_count = 12345
T3 PASS: 100x reads in 3.2ms (0.03ms/call — atlas traversal fast at dev scale)
         Live scale (~15K atlas entries): O(n) but /status cadence ~1s is fine
```

---

## Deploy

**Task def:** dsf-ai-task:424 (final — curriculum with --no-gate, status timeout fix, Dockerfile fix, EFS restore fix)
**SHA:** `5bca1fd` (contains 65-A + 65-B + 65-C)

ECS circuit breaker: `rollback:false`, `minimumHealthyPercent:0` — boot allowed
full 200s load window without cycling.

### Boot verification (expected)

After ~200s:
```
[curriculum] autostart thread started
[DSF-AI] Guala initialized in ~115s
...
[curriculum] [orchestrator] mode=live seed_total=100 delivering=100 ...
[curriculum] [live]   1/100 moon-001 ...
```

---

## Carry-forward

1. **65-A T2/T3**: verify bundle count rising after 10+ minutes of autostart operation
2. **65-B T5**: confirm saturated cells (high aggregate_strength) receive smaller impulse
   than empty cells in live emission events
3. **Continuous curriculum**: with autostart live, bundle count target 500+ within 24h

---

End report.
