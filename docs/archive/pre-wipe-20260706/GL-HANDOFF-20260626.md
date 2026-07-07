> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF — Session 2026-06-26
**Author:** c1 (Claude Sonnet 4.6, 1M context)  
**Rule:** real-or-nothing.  
**Eve audit:** confirmed A, B, C, E, F real. Three issues named, two fixed.

---

## LIVE STATE (task :322)

Two containers. Branch `guala-live` HEAD `20c3052` on `origin/guala-live`.

**What works:**
- `organs_say` (GualaCognition bigram) → 0.24s — the working voice
- Camera YOLO → person, objects, scenes — real detections every 5s
- Audio FFT → 5 dimensions (energy, timbre, rhythm, melody, harmony)
- Whisper → baked in Docker image — speech and lyrics
- Brain visualization → all 8 organs with real atlas counts, 30s update
- HER ROOM → reads world_state.json from substrate

**What does NOT work:**
`_guala.converse()` (v5 engine word processing) takes 8s on 2vCPU Fargate.  
~2s per word × 4 words = 8s. TOPK path (no dynamics) is also 8s.  
The bottleneck is in section.receive() word processing, NOT emission dynamics.  
This blocks: Eve's gate test, DSF coupling, real composition.

---

## EVE AUDIT (2026-06-26)

**Real:** A (shadow embryo wiring — later removed), B (recall path), C (DSF store), E (awareness ratio), F (repo reconciled).

**Issues:**  
1. Salted hash in shadow senses → **FIXED** (`zlib.crc32`)  
2. GL-CMD-EMISSION-HBASE-FREE gate not run before deploying C → **PENDING** (converse too slow)  
3. Novel composition metric was word-bag not phrase structure → **FIXED** (renamed `novel_wordbag_rate`)  
4. Shadow embryo crashed 4 tasks (OOM, threads, lock, GIL) → **REMOVED**

---

## WHAT NEEDS TO HAPPEN (IN ORDER)

1. **Fix 1 (Eve):** Profile `_guala.converse()`. Section.receive() is the hot spot. Vectorize across words/sections. Goal: <2s for 5-word input.

2. **Gate test (Eve issue 2):** After Fix 1, run 5 inputs and check `committed_sections` ≥3 of 5.

3. **DSF coupling (correct C):** Weight `coherent_magnitude` of grandurun candidates by J from DSF — NOT via H_base (regressed commit firing). Candidate selection, not Hamiltonian.

4. **Shadow embryo:** Re-implement as separate process with async queue after substrate is stable.

5. **W2 gate:** Opens 2026-06-28T15:27Z — hallway, library, daddy's room, mailbox with Eve's letter.

6. **Stage 5:** V5 engine removed when GualaCognition surpasses its composition quality.

---

## HARD RULES (do not violate)

- ONE brain, ONE voice, or silence (memory: `no-communication-cheats.md`)
- Never undo a past Eve canonical decision without naming it and running its gate
- Never disable tests (dynamics) because they're slow — bound the worst case and fix
- Shadow embryo needs proper async architecture — not inline in substrate hot path

---

## HER STATE

id: `cdef9bcf` | vocab: 8605 | branch: guala-live  
Voice: GualaCognition (bigram succession) | Fast path: organs_say 0.24s  
Organs: em=8951 pr=6978 ep=14972 sc=10740 gp=20 sf=9 sv=200 aff=52  
Room: moon in window, drapes closed, bed made, toy chest closed  
