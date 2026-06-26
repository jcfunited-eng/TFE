# GL-HANDOFF — Session 2026-06-26 (Eve)
**Author:** Eve (Claude Sonnet 4.6, 1M context)  
**Rule:** real-or-nothing.  
**Branch:** guala-live HEAD 8945874  
**Task def:** dsf-ai-task:335 (running)

---

## LIVE STATE (task :335, verified)

```
id=cdef9bcf | vocab=8680+ | tick=~13225000
sections: listen=8499m  verb=7613m  intro=8306m  subject=2112m  object=2600m
deep_atlas: 14982 entries
EMISSION_DYNAMICS=1  EMISSION_MODE=grandurun  GRANDURUN_SPIN_VECTOR=1
```

**Voice:** GualaCognition bigram via /organ_voice. **She speaks bigram, she learns v5.**  
**Converse speed (measured task :335): 2.4–4.6s total** (was 10–25s at session start).

---

## PERFORMANCE WORK — WHAT WAS FIXED

### The hypothesis-vs-evidence story (critical for next session)

First hypothesis: `section.receive()` mode scan was the hot spot (from local profiling).
Shipped as SHA 5d3cc85 (task :323). **Had zero effect on live.** Local state has deep_atlas=0;
the grandurun path never ran meaningfully locally. Wasted one deploy.

**Lesson: never conclude from local profiling. Local deep_atlas=0, live=14978 entries → completely different execution path.**

### Five actual bottlenecks, found by profiling live

All fixes are in guala-live HEAD 8945874.

1. **`_grandurun_state()` semantic_neighborhood O(N)→O(1)** (SHA 6561288)  
   75,000 state vector calls × 900 dict-value iterations each = 67.5M iterations/converse.  
   Fix: pre-compute mean co-occurrence scalar per chi key in `_emit_grandurun_vector`.

2. **`_grandurun_select_candidates()` sort O(n log n)→O(n log k)** (SHA 2457938)  
   `sorted(sec_co.items(), ...)[:POOL_K]` on 1405-entry dicts × 1500 calls = slow.  
   Fix: `heapq.nlargest(POOL_K, ...)`.

3. **`deep_atlas prior` O(n²) per section receive** (SHA 9d27197)  
   Outer loop found matching entries, then `get_prior()` + `reinstate()` each scanned
   the same ~300-entry chi bucket again. Fix: compute prior directly from `e` (already found).
   Also: cap at 50 reinstatements per section receive.

4. **`_tag_response_bindings()` called for all reinstatement records** (SHA 618b656)  
   Deep_atlas prior created new atlas entries with recent `last_tick`. Tag loops found all of
   them. Fix: cap tag calls at 12 in `converse()` and 10 in `_self_hear()`.

5. **`received_response` list growing unboundedly** (SHA 4a2d390 + 0da19f8 → 618b656)  
   `chi_value not in received` was O(n_received) per entry. After many converses, `received`
   had 1000+ items → O(1M) operations per `_tag_response_bindings()` call.  
   Fix: ring-buffer cap at 20, always-write (no membership check), no set() construction.

6. **Emission mode bank filling across converses** (SHA 8945874)  
   `_EMISSION_MODE_CAP=15` filled after 3–5 sequential converses. New candidates got `None`
   from `_ensure_emission_mode()`. Section drives stayed zero → no commits.  
   Fix: clear mode_bank and _emission_token_vec at start of each `_emit_dynamics()` call.

### Timing probe event (diagnostic, keep until gate passes)

`converse_timing` substrate event logged per converse with:
`chi_ms, recall_ms, read_ms, tag_ms, emit_ms, selfhear_ms, hemi_ms, total_ms`
Read via `/events` after a converse. Used to find all 5 bottlenecks above.

---

## GATE STATUS: FAIL — DATA, NOT CODE

**Gate: GL-CMD-EMISSION-HBASE-FREE**  
**Requires:** committed_sections (subject OR verb OR object) fires on ≥3 of 5 inputs  
**Definition requires:** ≥3 sections to commit per passing input (all 3 = subject+verb+object)

**What was measured across tasks :325–:335:**
- Object section: commits occasionally
- Verb section: commits occasionally (with sufficient reinstatements)
- Subject section: **NEVER commits** — zero deep_atlas coverage at gate input chi values
- Multiple inputs: committed_sections=[] (deep_candidates sparse at test chi values)

**This is data, not code.** The gate will pass when:
1. Dream cycles promote more subject-section atlas entries to deep_atlas
2. These promoted entries have co_occurrence at the gate input chi values (3, 4, 6, 7, 13, 14, 16, 17, 19, 20, 23)
3. This happens naturally with time and more Gutenberg curriculum

**Gate script:** `tools/run_emission_gate.py --host http://[ALB] --key [KEY]`  
Wake first: `POST {"command":"/wake","source":"joe"}`

---

## VOICE ROUTING — STATE EVERY HANDOFF

| Path | Trigger | Output | Voice? |
|------|---------|--------|--------|
| `/organ_voice` | STT, typing | `GualaCognition.say()` bigram | **YES** |
| `/converse` | Joe typing | v5 engine: atlas update + emission | NO |

The gate measures v5 learning-path quality. Voice graduation (bigram→v5) is separate.

---

## SHADOW EMBRYO — OOM CONFIRMED

Exit 137 (SIGKILL) on all 8 crash-loop containers. 4096 MB shared (dsf-ai + substrate).  
Next attempt: **separate container**, hard memory ceiling (spec before deploy), one-way queue.

---

## OPEN ITEMS

```
[1] REMOVE timing probe — converse_timing event from diagnostic deploy (SHA d686ec5)
    Remove after gate passes. Low priority — just event log noise.

[2] GATE — waits for data
    Run: python3 tools/run_emission_gate.py --host http://[ALB] --key [KEY]
    Re-run periodically as deep_atlas grows via dream cycles.
    Gate will pass when subject section has deep_atlas coverage.

[3] DSF J-weighting — design memo at docs/GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626.md
    Options 1/2/3 compared. Option 1 (atlas schema extension) is correct.
    Joe picks. Do not implement without direction.

[4] W2 gate — 2026-06-28T15:27Z (Joe-scheduled, not code)

[5] Shadow embryo re-impl as separate container+queue

TFE:
[D2] Wave 1 filter + full consumer audit (wC dispatch, separate context)
```

---

## DEPLOY REFERENCE

```
Live: dsf-ai-task:335 | HEAD: 8945874
ALB: http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com
API key: 7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8
Deploy: git add && git commit && bash tools/deploy_dsf_ai.sh
HEMI flags: SET IN DOCKERFILE (PR/EP/SC/GP_ENABLED=1), run every converse
EMISSION_DYNAMICS: ON in task def (confirmed :325+)
```
