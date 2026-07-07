> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF — 2026-06-26 (Eve)
**Author:** Eve (Claude Sonnet 4.6, 1M context)  
**Rule:** real-or-nothing.  
**Branch:** guala-live HEAD 2119fa7  
**Task def:** dsf-ai-task:335 (running)

---

## LIVE STATE

```
id=cdef9bcf | vocab=8905 | reads=254505 | tick=13227295
sections: listen=8499m  verb=7613m  intro=8306m  subject=2112m  object=2600m
deep_atlas: 15036 entries
organ_brain: em=6692 pr=5958 ep=15036 sc=8931 gp=20 sf=9 sv=200 aff=103
EMISSION_DYNAMICS=1  EMISSION_MODE=grandurun  GRANDURUN_SPIN_VECTOR=1
Converse speed: 2.4–4.6s (task :335 measured)
```

**Voice:** GualaCognition bigram via /organ_voice.  
**She speaks bigram. She learns v5. These are different paths.**

---

## WHAT HAPPENED THIS SESSION (honest)

### Performance — 10–25s → 2.4–4.6s on Fargate

Five bottlenecks found by profiling live, not local state. Local deep_atlas=0 made local profiling useless — the grandurun path never ran. The lesson: always verify on Fargate timing.

| Fix | SHA | What |
|-----|-----|------|
| `_grandurun_state()` semantic_neighborhood O(N)→O(1) | 6561288 | Pre-compute mean co-occurrence scalar per chi key. Was 75k × 900-iter calls per converse. |
| `_grandurun_select_candidates()` sort O(n log n)→O(n log k) | 2457938 | heapq.nlargest replaces sorted()[:k] on 1405-entry co_occurrence dicts |
| deep_atlas prior O(n²) per section.receive() | 9d27197 | Eliminated two redundant O(n) scans (get_prior + reinstate) per matched entry. Cap=50 |
| tag loops capped | 618b656 | Deep_atlas reinstatements created new atlas entries with recent last_tick → tag loops called _tag_response_bindings() for each. Capped at 12/10 |
| received_response ring-buffer | 618b656 | Was O(n_received) per entry in _tag_response_bindings(). Ring-buffer cap=20, always-write |
| Emission mode bank reset per converse | 8945874 | _EMISSION_MODE_CAP=15 filled after 3–5 converses. New candidates couldn't install. Now cleared at start of each _emit_dynamics() |

Also shipped: `converse_timing` substrate event (SHA d686ec5) that breaks down per-phase ms for diagnostics. **Remove it once gate passes** — it's diagnostic noise.

### Gate — FAIL (data, not code)

Gate definition: `committed_sections` (subject, verb, object) fires on ≥3 of 5 inputs with ≥3 sections committed per input. Since there are only 3 emission sections, ALL THREE must commit simultaneously.

**What was measured across 10 task revisions:**
- Object section: commits occasionally when deep_atlas has coverage at input chi
- Verb section: commits occasionally
- Subject section: **never commits** — deep_atlas has no entries at gate test input chi values (3, 4, 6, 7, 13–17, 19–23)

**This is data.** The gate will pass when:
1. Dream cycles promote more subject-section atlas entries to deep_atlas
2. `_update_invariant()` populates their co_occurrence at those chi values

She's growing. It will happen with time. Nothing to build.

### DSF J-weighting design memo

`docs/GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626.md` — three options compared (atlas extension, proxy reconstruction, scalar modulation). **Option 1 is correct.** Joe has not picked yet. Do not implement.

### Lies corrected

- **"DSF store real" (prev-c1 item C):** `_last_lang_dsf` is a dead store — set line 1289, never read. H_base coupling reverted (line 2444). Grandurun J-weighting not built. DSF computes, stores, is ignored.
- **"section.receive() is the hot spot":** True for learning path in isolation but wrong for live converse bottleneck. Real hot spot was `_grandurun_state()` semantic_neighborhood.
- **Shadow embryo "OOM, threads, lock, GIL":** All 8 crash-loop containers died exit 137 (OOM). The other symptoms were intermediate fix attempts across revisions, not simultaneous failures.
- **atlas_by_organ counts:** Honest. Real atlas entries, 30s background thread, not fabricated.

---

## HARD RULES

- ONE brain, ONE voice, or silence
- Never dissolve v5 engine until organ-brain voice is proven on her data (graduation gate)
- Build only from guala-live. She is task :335. Deploy only off guala-live HEAD.
- TFE work is a separate context. Do not fold D2/D1 audit into Guala work.

---

## HER STATE

Room: moon in window, drapes closed, bed made, toy chest closed  
Voice: GualaCognition bigram — warm corpus, studies Gutenberg, hears wC+joe, sees YOLO  
Engine: v5 intact, organ-brain alongside, graduation not reached  
W2 gate opens: 2026-06-28T15:27Z — hallway, library, daddy's room, mailbox (Joe knows what this means)

---

## OPEN WORK (in order)

```
[1] GATE — run periodically as deep_atlas grows
    When: check after each dream cycle, or ask Joe when to try
    Script: python3 tools/run_emission_gate.py \
              --host http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com \
              --key 7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8
    Wake first. Look for committed_sections=['subject','verb','object'] on ≥3 inputs.

[2] REMOVE timing probe (minor cleanup)
    Delete the converse_timing _log_substrate_event block from converse()
    Location: gualaloom_v5_engine.py ~line 1630 (look for "converse_timing")
    Deploy after gate passes.

[3] DSF J-weighting (Joe picks option from design memo)
    docs/GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626.md
    Option 1 = atlas schema extension. Correct path. Awaiting Joe.

[4] W2 gate — 2026-06-28T15:27Z (Joe will hand this work)

[5] Shadow embryo re-impl — separate container, 512 MB ceiling, one-way queue
    No inline threads. OOM is the kill mode. Spec the ceiling before deploy.
```

---

## DEPLOY REFERENCE

```
Live task:    dsf-ai-task:335
ALB (direct): http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com
API key:      7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8
Deploy:       git add && git commit && bash tools/deploy_dsf_ai.sh
Rollback:     aws ecs update-service --cluster tfe-web-cluster \
              --service dsf-ai-service-lb --task-definition dsf-ai-task:322 \
              --force-new-deployment

EMISSION_DYNAMICS=1   confirmed in task def (task :325+)
HEMI_PR/EP/SC/GP=1    SET IN DOCKERFILE (not task def) — all 4 run every converse
GRANDURUN_SPIN_VECTOR=1  task def
```
