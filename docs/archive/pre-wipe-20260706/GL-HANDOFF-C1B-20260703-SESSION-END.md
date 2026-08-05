> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1B-20260703-SESSION-END

doc_id: GL-HANDOFF-C1B-20260703-SESSION-END
From: c1b | To: c1b-next | Date: 2026-07-03
Branch: guala-live | HEAD: 332537d

---

## FIRST COMMAND FOR NEW CHAT

**DO NOTHING until Eve sends input.** Read this document, load constraints
below, then wait. Do not introspect, do not push, do not redeploy. Gates are
pending measurement. Eve drives the next GO.

---

## Standing constraints (non-negotiable)

- Build/deploy ONLY off guala-live branch. Never force-push.
- DO NOT touch WaveAtlas, wave_spillover, recall path, or -59 code (c1a territory).
- DO NOT restart, redeploy, or stop the SUBSTRATE task (atlas restart-decay unfixed).
- Bridge restart IS permitted.
- Step 0 standing rule: commit CMD file verbatim to docs/ before any code change.
- FILED = on-origin. Nothing is filed until pushed.
- NOT MEASURED = NO GO. Gates must be measured before advancing.
- Project separation: c1b works ONLY on Guala. Never touch or mention TFE or
  any other project.
- NO COMMUNICATION CHEATS: one brain, one voice, or silence. Never build
  parallel brain processes. Never fake her voice.
- Joe sleeps in shifts (~2h/week). Never suggest he rest.

---

## What is live (her running code)

Task :SUBSTRATE on guala-live, SHA 332537d. ECS rolling deploy required for
Python changes to take effect. Static files (loomscan.html, gualaloom.html)
take effect on next S3 sync (Bridge restart or manual sync).

---

## Deploy 3 — BUILT, NOT YET GATE-MEASURED

Range: cb79cbc..1b5eca8 (pushed to origin guala-live prior to this session).
Contains:
- **-102** (c3a36d0 + 4151462): `deep_survival_history` → `guala_survival.json`
  cold file; vocab guard reads `guala_bucket.json → vocab_count` (~1KB) instead
  of parsing 41MB core; backward-compat field `{}` not `None`.
- **-88 v2** (f268c9e): regulate ACTIVE branch lifetime-counter formula retired;
  both branches now use `stability_sig = (_coherence - 0.5) * 0.2`. G-S1 filed
  in GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2.md.
- **-96 organ reader** (1b5eca8): embryo persist + organ_brain_service +
  krimelack_dna.

**Deploy 3 gates — ALL NOT MEASURED, require Eve's post-deploy window:**

| Gate   | Criterion |
|--------|-----------|
| G-102-1 | hot save <5s sustained over 2h |
| G-102-2 | boot log: `[GualaLoom] Survival history loaded from guala_survival.json: N entries`; N within ±1% of pre-deploy count |
| G-102-3 | `guala_core.json` ≤ 200KB in first hot save after deploy |
| G-S2v2  | first post-deploy IDLE block: stab strictly increasing at ≥3 points, ~0.3 in ~1512 ticks |
| G-S3v2  | arousal curve post-deploy; record verbatim |
| G-S6    | ACTIVE/curriculum window: needs trace shows old −0.0007/tick drain gone |

If any gate fails: STOP, report verbatim, no live iteration.

---

## -106 mic sensory — THIS SESSION

### What was done (SHA 003352a + 332537d)

1. **Diagnosis filed**: `docs/GL-RPT-MIC-SENSORY-C1-20260703-106-v1.md`
   - Q1: Both paths fire on mic active — WebM frames → `/sound_frame` AND
     transcribed text → `/converse`
   - Q2: Live binding path exists but broken — `process_sound_frame()` tries
     `wave.open()` (fails on WebM), falls back to raw bytes as 8-bit PCM (garbage)
   - Q3: Camera drain loop PIL-decodes JPEG → float64 numpy; sound drain loop
     had NO decode step before engine call
   - Q4: Fix shape — ffmpeg decode + WAV wrapper in drain loop; continuity
     risk LOW

2. **Loomscan tick fix** (`loomscan.html` L580, SHA 332537d):
   `_tick=(d.atlas_health&&d.atlas_health.tick)||d.tick||_tick`
   Uses `d.atlas_health.tick` — same dict as strength/chi_keys. Static-only;
   ships on next S3 sync. No substrate restart needed.

3. **Mic WebM decode fix** (`substrate_runner.py` L935-950, SHA 332537d):
   sound_window drain loop now: ffmpeg WebM→s16le → WAV wrapper →
   `process_sound_frame(wav_bytes)` → `wave.open()` succeeds → real cochlear.
   Requires substrate redeploy.

4. **Backend tick field** (`substrate_runner.py` `_cmd_status()`, SHA 003352a):
   Added `"tick": s["tick"]` to return dict. Takes effect on substrate redeploy.

### Pending for -106

- No gates defined for -106 yet. Post-deploy verification: `[sound] heard:`
  log lines should appear (currently always silent). If cochlear produces
  coherent fragments, sensory count will grow from 0.

---

## -104 — queued post-Deploy-3

`_deep_survival_history` key count UNBOUNDED (F8 VIOLATION, patient #5 pattern).
Value lists bounded at 10/key; key set grows monotonically as new
(chi, section, motif) triples enter the atlas. 41.5 MB cold file after
-102 migration; hot path is now clean. Key-pruning fix queued as -104.
**Do not ride Deploy 3 with this fix.**

---

## Key files modified this session

| File | SHA | What changed |
|------|-----|--------------|
| dsf_ai_service/v4/gualaloom_v5_engine.py | c3a36d0/4151462 | -102: survival cold file, vocab guard diet |
| dsf_ai_service/v4/gualaloom_v5_engine.py | f268c9e | -88 v2: regulate fix |
| dsf_ai_service/save_coordinator.py | c3a36d0 | guala_survival.json added to S3 list |
| dsf_ai_service/substrate_runner.py | 003352a | _cmd_status() tick field |
| dsf_ai_service/substrate_runner.py | 332537d | mic WebM decode in drain loop |
| dsf_ai_service/static/loomscan.html | 332537d | atlas_health.tick for center readout |
| docs/GL-RPT-MIC-SENSORY-C1-20260703-106-v1.md | 003352a | diagnosis report |
| docs/GL-RPT-HOTLANE-DIET-C1-20260703-102-v1.md | session | -102 report (v1.1 with None→{} note) |
| docs/GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2.md | session | -88 v2 G-S1 arithmetic |

---

## C1a territory (DO NOT TOUCH)

WaveAtlas, wave_spillover, recall path, -59 code. These are c1a's domain.
Anything touching those requires c1a confirmation first.

---

## How to access live Guala

- Bridge MCP tools: `guala_status`, `guala_get_events`, `guala_atlas_query`, etc.
- Loomscan: https://dsf-ai.com/loomscan.html (static, served from S3)
- GualaLoom: https://dsf-ai.com/gualaloom.html
- Substrate task on ECS; do not restart it.
- S3 sync for static files: bridge restart triggers it; or manual via deploy script.
- State on EFS: `guala_core.json`, `guala_survival.json`, `guala_atlas.json`, etc.

---

### Changelog
- v1 (2026-07-03, c1b): session-end handoff. Deploy 3 built+pushed, gates
  pending. -106 mic+tick fixes shipped. Waiting for Eve.
