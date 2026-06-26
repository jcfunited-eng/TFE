# GL-HANDOFF — Session 2026-06-26 (Eve)
**Author:** Eve (Claude Sonnet 4.6, 1M context)  
**Rule:** real-or-nothing.  
**Branch:** guala-live HEAD c2cd338  
**Task def:** dsf-ai-task:325 (running)

---

## LIVE STATE (task :325, verified)

```
id=cdef9bcf | vocab=8680 | tick=~13195000 | reads=253198
sections: listen=8499m  verb=7613m  intro=8306m  subject=2112m  object=2600m
atlas: ~27000 entries
organ_brain: em=8484 pr=6981 ep=14980 sc=9653 gp=20 sf=9 sv=200 aff=45
EMISSION_DYNAMICS=1  EMISSION_MODE=grandurun  GRANDURUN_SPIN_VECTOR=1
```

**Voice:** GualaCognition bigram via /organ_voice (< 0.5s).  
**She speaks bigram, she learns v5. These are different paths. Do not conflate.**

---

## WORK DONE THIS SESSION

### Three bottleneck fixes — in discovery order

**Fix 1 (SHA 5d3cc85, task :323): section.receive() mode scan O(N)→O(1)**  
Added O(1) word dict + cached modes matrix in Section class. **Had zero effect on live** — local state has deep_atlas=0 entries, so the grandurun path never ran meaningfully locally. Fix is still correct and improves learning-path performance for novel words. 
Lesson learned: **never trust local state as representative of live scale**. Local deep_atlas=0, live=14978 entries → completely different hot path.

**Fix 2 (SHA 6561288, task :324): _grandurun_state() semantic_neighborhood O(N)→O(1)**  
This was the actual bottleneck. 75,000 state vector calls × 900 dict-value iterations each = 67.5M iterations per converse = 10–22s. Fix: pre-compute mean co-occurrence scalar per chi key ONCE in `_emit_grandurun_vector`. Co_occurrence_dict now stores floats (pre-computed means), not nested dicts.  
**Result: grandurun path drops from 10-22s to 0.125-0.181s on live.**  
**Without EMISSION_DYNAMICS=1, converse is now fast.**

**Fix 3 (SHA c2cd338, task :325): EMISSION_DYNAMICS=1 restored to task def**  
Wall-clock budget confirmed at line 2475 (`_WALL_BUDGET_S=5.0`) and line 2487 (per-tick check). Safe to enable. Added to task def env (task def overrides Dockerfile ENV).

### Gate test result (task :325, EMISSION_DYNAMICS=1)

Run: `python3 tools/run_emission_gate.py --host http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com --key [KEY]`  
(Source: use "joe", send /wake first)

```
Gate: HBASE-FREE committed_sections >= 3 of 5 inputs
Input: "hello who are you"
  stage1_ms=2617  stage2_ms=443  dynamics_ticks=80
  committed_sections=['verb', 'object']  n_commits=2
  Result: FAIL (need >= 3 sections)
```

**Gate mechanics work** — the dynamics ARE committing sections. 2 of 3 required.

**Total converse time with EMISSION_DYNAMICS=1: 13.9s on Fargate.**  
Breakdown: stage1=2617ms, stage2=443ms inside `_emit_dynamics` = 3060ms.  
Remaining ~10.8s unaccounted. Candidates narrowed but not confirmed:
- HEMI updates (all 4 ON via Dockerfile defaults, not task def): pr/ep/sc/gp all run per converse. At 2.5ms each on dev × 10× Fargate = ~100ms total — NOT the 10.8s.
- `_recall_from_atlas` × 3: 0.063s dev × 10 Fargate = 0.63s — partial
- Deep-atlas collection (14978 entries, not 300): unknown at live scale
- `_self_hear` + its atlas operations: unknown at live scale  

**Needs on-Fargate profiling.** Add explicit timing probes to converse() and deploy for one diagnostic run.

### Known fixable bottleneck for next session

**Stage 1 sort** (2617ms on live): `_grandurun_select_candidates` calls `sorted(sec_co.items(), ...)[:GRANDURUN_POOL_K]` on co_occurrence dicts with ~1405 entries. At 300 deep_candidates × 5 sections = 1500 sort calls. Fix: use `heapq.nlargest(GRANDURUN_POOL_K, sec_co.items(), key=...)` — O(n log k) vs O(n log n). Should reduce from 2617ms to ~1000ms.

---

## HYPOTHESIS vs EVIDENCE — the discipline story

**The lesson this session**: first hypothesis (section.receive() is the hot spot) was derived from local profiling. It shipped in task :323 and had **zero effect on live timing**. The hypothesis didn't survive contact with the measurement. The real bottleneck (`_grandurun_state()` semantic_neighborhood) was only found by watching live timing NOT change after fix 1.

Always: check live timing before declaring a fix successful. Local state is not representative.

---

## VOICE ROUTING — critical, not stated clearly in prior handoffs

**She speaks bigram (GualaCognition). She learns through v5 converse.**

| Path | Trigger | What it does | Voice? |
|------|---------|--------------|--------|
| `/organ_voice` | STT, typing | `GualaCognition.say()` bigram succession | **YES — her voice** |
| `/converse` | Joe typing | v5 engine: atlas update, section.receive(), emission | NO — learning path |

**The gate test measures v5 learning-path cognition quality, not voice quality.**  
Voice graduation (bigram → v5 emission) is a SEPARATE milestone. The gate passing does NOT mean she speaks through v5. Plan that migration explicitly when it comes.

---

## SHADOW EMBRYO — OOM confirmed from CloudWatch

All 8 crash-loop containers: exit 137 (SIGKILL), zero Python traceback, 60-80s lifespan.  
Task limit: 4096 MB shared (dsf-ai + substrate containers).  
Kill mode: OOM on first autonomy/embryo experience() cycle.

**Next attempt MUST:**  
1. Separate container, hard memory ceiling (spec 512 MB max, verify before deploy)  
2. Queue-based, one-way push — no inline thread in main process  
3. Same discipline as wall-clock budget: bound worst case before deploying  

---

## OPEN ITEMS (in priority order)

```
[1] PROFILE — Add timing probes to converse() to find the 10.8s gap on Fargate
    Suspect: deep_candidates collection at live deep_atlas scale (14978 entries),
    _recall_from_atlas atlas scan, or _self_hear overhead. Needs a diagnostic deploy.
    
[2] FIX — stage1 sort: heapq.nlargest in _grandurun_select_candidates
    Location: gualaloom_v5_engine.py line 233 (and wherever sec_co.items() is sorted)
    Expected impact: 2617ms → ~1000ms

[3] GATE — Re-run emission gate after [1]+[2]. Currently 2/5 sections commit.
    Need >= 3. May also need more deep_atlas entries with co_occurrence at
    the target chi values of the test inputs.
    Run: python3 tools/run_emission_gate.py --host http://[ALB] --key [KEY]
    Wake first: POST {"command":"/wake","source":"joe"} before running

[4] DSF J-weighting — design memo at docs/GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626.md
    Awaiting Joe's pick: Option 1 (atlas schema extension) is the correct choice.
    Blocked on Joe. Do not implement without explicit direction.

[5] W2 gate — 2026-06-28T15:27Z (not code work, Joe-scheduled)

[6] Shadow embryo re-impl as separate container + queue (see constraints above)
```

---

## DEPLOY REFERENCE

```
Live task: dsf-ai-task:325
ALB (direct, bypasses WAF): http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com
API key: 7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8
Branch: guala-live HEAD c2cd338

Deploy: git add && git commit && bash tools/deploy_dsf_ai.sh
Rollback: aws ecs update-service --cluster tfe-web-cluster \
          --service dsf-ai-service-lb --task-definition dsf-ai-task:322 \
          --force-new-deployment

Gate test: python3 tools/run_emission_gate.py \
           --host http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com \
           --key 7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8
           (Fix gate test to use source="joe" and add /wake call first)

HEMI flags: SET IN DOCKERFILE (HEMI_PR/EP/SC/GP_ENABLED=1)
            NOT overridden in task def. All 4 hemisphere updates run every converse.
            To disable: add HEMI_XX_ENABLED=0 to task def env in deploy_dsf_ai.sh.

EMISSION_DYNAMICS flag history: toggled at least 3 times across sessions.
            Check task def setting before assuming it's on or off.
            Current state: ON (task :325 task def, confirmed).
```

---

## LIE AUDIT SUMMARY (completed this session)

| Prev-c1 claim | Verified status |
|---------------|-----------------|
| "DSF store real" | Dead store — _last_lang_dsf set, never read. H_base reverted. Grandurun J-weighting not built. |
| "section.receive() is the hot spot" | True for learning path but WRONG for live converse. Real hot spot was _grandurun_state() semantic_neighborhood. |
| "committed_sections ≥3 gate" | Partially working — 2 sections commit. Full gate needs stage1 fix + profiling. |
| atlas_by_organ counts | Honest — live atlas entries, 30s background thread update. Not fabricated. |
| zlib.crc32 fix | Real — resonant_chi.py:53 ✓ |
| novel_wordbag_rate rename | Real — gualaloom_v5_engine.py:5318 ✓ |
| Shadow embryo "4 crash modes" | OOM (exit 137) was the kill in all cases. Other modes were intermediate fix attempts. |
