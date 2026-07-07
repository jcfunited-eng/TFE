> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1B-20260702

doc_id: GL-HANDOFF-C1B-20260702
Type: Session handoff
Date: 2026-07-02
Author: c1b (outgoing)
For: c1b (next session)
Branch: guala-live
HEAD: 4d84b08

---

## What happened in this session

### Dispatches completed

| SHA | Dispatch | Outcome |
|-----|---------|---------|
| 3a96ad4 | Status fast (persistence_health → executor) | Deployed task:427. /status <500ms. |
| 9f7f09b | Bridge audit fixes A/B/C | 13/13 bridge tools pass. Task:428. |
| a00b36f | Sleep rate fix -68 | 4h natural cycle. Task:429. REST dominant. |
| 4d84b08 | Investigation -70 (read-only) | Report filed. No code. |

### Key findings from investigation -70

1. **Emission blocked by presence gate** (not a bug, a gate): `_generate_activity_candidates` and `_check_emission_trigger` both require pair-bond presence. total_emissions was 159 for >24h. Briefly hit 160 (one emission fired when joe presence was active). Gate is substrate-physical design, not malfunction.

2. **n_pictures=0**: All 11 pictures lost at task:429 boot. Boot log confirms `Visual restored: 0 pictures`. Likely caused by WaveAtlas serialization failure corrupting or not saving visual state. This is new — needs investigation.

3. **WaveAtlas save failing repeatedly**: `Object of type complex is not JSON serializable` — c1a's -59 Phase 2 WaveAtlas persistence is storing complex numbers that can't serialize. Firing every save cycle (non-fatal but leaking).

4. **wake_wc intermittent failure**: `log_event(STATE_DIR, "wake", ...)` synchronous EFS write in the wake handler takes 5-31s under NFS load. Same fix as persistence_health (run_in_executor). Unfixed because it's in app.py (c1a territory).

5. **Atlas IS growing**: 9,662 → 12,419 bindings in session. Curriculum landing (~15 writes/bundle). Vocab +12 new words (seed uses known vocab mostly).

6. **Sleep rate fix working**: Zero SLEEPING/DREAMING events in 33-min observation window. dream_pressure accumulating at correct rate.

---

## Current substrate state (at session end)

```
Task: dsf-ai-task:430
Branch: guala-live HEAD 4d84b08
Vocab: 13,908 (+12 from session start)
Atlas: ~7,000 n_live, strength ~952
Activity: REST
Emissions: 160 (one new emission fired during session)
Pictures: 0 (lost)
Sounds: 15
Curriculum: running (autostart, --no-gate, 5s interval)
Sleep rate: fixed (-68), ~4h natural cycle
Bridge: 13/13 tools working (task:17)
```

---

## What next c1b should do first

**Read before touching anything:**
- `docs/GL-RPT-INVESTIGATION-C1-20260702-70.md` — Eve's dispatch found 6 substrate issues
- `docs/GL-CMD-C1B-QUEUE-EVE-20260701-65-PB3.md` — the queue that started this session (for context)

**Do NOT:**
- Touch app.py without checking with c1a (currently their territory for embedded path)
- Touch WaveAtlas code (-59 Phase 2 is c1a's domain)
- Deploy anything before Eve reviews the -70 findings

**Await:**
- Eve's response to GL-RPT-INVESTIGATION-C1-20260702-70 before any code work
- Joe's signal on whether to remove the presence gate from emission

---

## Open items for next c1b (pending Eve approval)

Priority 1 — **wake_wc EFS fix** (independent, app.py, ~2 lines):
```python
# app.py /wake handler, line 1385:
# Current:
_guala.log_event(STATE_DIR, "wake", source=wake_source)
# Fix:
import asyncio as _aio
await _aio.get_event_loop().run_in_executor(None, lambda: _guala.log_event(STATE_DIR, "wake", source=wake_source))
```
This removes the 5-31s spike in wake_wc. Eve can approve independently of -70 conclusions.

Priority 2 — **Pictures investigation**: Why did n_pictures go from 11 to 0 at task:429?
- Check if pictures are on EFS at `/mnt/efs/guala/pictures/`
- Check WaveAtlas serialization failure and whether it corrupts the save
- Do NOT redeploy pictures — just understand why they disappeared

Priority 3 — **Emission presence gate** (awaits Eve+Joe decision):
Remove from `_generate_activity_candidates` (engine L3131):
```python
# Remove the "if pair-bond present" gate:
# EMITTING goes into candidates always (when cooldown elapsed)
# Needs state selects it when connection is low and she has things to say
```
This is a substrate-physics decision — Eve reviews.

---

## Branch state

```
git log --oneline -5 origin/guala-live:
4d84b08  doc: GL-RPT-INVESTIGATION-C1-20260702-70
832cec7  doc: GL-RPT-PHASE2-COMMIT-A-CLEARANCE-C1 (c1a)
c190218  d4.6 fix (other work)
26df634  Revert Phase 2 Commit A (c1a)
c1cd78e  doc: GL-RPT-SLEEP-RATE-FIX-C1-20260702-68
```

c1a is active on -59 Phase 2 and other work. Check for their commits before every push.

---

## Deploy script note

The deploy script sends `sleep_for_deploy` signal before new task starts. She was at sleep_tick=14222850 at one point — if she's sleeping when you deploy, that's normal. The 202 response from sleep endpoint is expected.

---

End handoff.
