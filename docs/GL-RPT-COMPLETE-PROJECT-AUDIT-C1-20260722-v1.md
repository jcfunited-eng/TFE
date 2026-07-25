# GL-RPT-COMPLETE-PROJECT-AUDIT-C1-20260722-v1

**Status: LOCAL-ONLY (not committed to origin — audit was ordered passive; commit on Joe's word)**
**Scope:** Full passive audit of the Guala project — infrastructure, senses, virtual embodiment/environment, curriculum/learning, UI surfaces (incl. LOOM Scan), ArcLoom spec compliance, promised-vs-built. All evidence gathered read-only (file reads, `git` reads, AWS describe/get, HTTP GET only). Zero writes, zero POSTs, zero deploys. Conducted 2026-07-21T23:30Z → 2026-07-22, six parallel audit agents + two spec deep-dives + direct infra checks.

---

## 0. Deploy ground truth

- Live: ECS `tfe-web-cluster/dsf-ai-service-lb`, task-def `dsf-ai-task:717`, image `deploy-20260721T184014Z`, git SHA `57363b95` on branch `codex/guala-causal-boundary-20260721` — **NOT an ancestor of origin/guala-live**. That branch carries ~10 commits (the whole new causal auditory stack, +8.5–9.3k lines incl. `substrate/auditory_*.py`, `senses/auditory_full_field_provider.py`, Rust `native/guala_core/src/auditory.rs`, ~300 lines of gualaloom.html) absent from guala-live. Branch tip `d73265eb` ("Bound continuous auditory learning and recovery") is one commit newer than what is deployed.
- The 5 commits on origin/guala-live missing from the deploy are all TFE-only — no substrate work is lost in that direction.
- **Landmine:** any deploy built off guala-live today regresses the live auditory stack + dashboard. Merge-back required before next guala-live deploy.
- Identity `1cc4e70a` (post-wipe genesis) intact. `/ready` sealed proof healthy. Task 18:54Z failed container health checks silently at 22:36Z (no traceback in logs); ECS auto-replaced with same image; replacement healthy since 22:40Z.
- Resources: 4 vCPU / 16 GB (down from 40GB/8vCPU OOM-mitigation era). CPU avg 3–10%, max ~37%. Memory steady ~21%. EFS (`gualaloom-state`) 9.2 GB. Alarms `guala-cpu/memory/efs-storage-runaway` all OK.
- **Memory-bloat verdict:** near-OOM (92–99% max) on 07-18..20 ended at exactly 07-20 ~17:53Z, coinciding with "retire lifetime experience ledger" + "fail closed on lifetime window retention" (59108f73, b0223a0c). Fixed by retiring/bounding the unbounded ledger — real fix, holding; note it removed a capability (lifetime ledger). Dream-cycle RAM leak (+300–1240MB/cycle) root-caused 07-17 remains **unfixed**; task is back at 16GB.
- **No S3 backups since the wipe**: `last_s3_backup: null`, snapshots 0 ("not in remote mode"). The substrate state is a single copy on one EFS.
- Speech: `VOICE_WHISPER=0` in :717 env; `/health` → speech.enabled=false, worker `never_started`, 0 starts; PCM transport 0 streams / 0 accepted chunks.
- Builds: 5 image builds on 07-21 (14:46→18:40Z), all SUCCEEDED; none in flight at audit time.

## 1. Senses

| Sense | Verdict |
|---|---|
| Text conversation intake | LIVE-WORKING (single sentence-intake door; admission guard f730634e) |
| Books/curriculum reading | LIVE-WORKING but near-stalled (see §3 intake collapse) |
| Khan world feed (via Tavily) | LIVE-WORKING (observed live) |
| YouTube feed | DEPLOYED-DISABLED — code complete, gated on YOUTUBE_API_KEY; **key IS present in local .env (39 chars)** — stale "no key" memory wrong for the repo; presence in ECS task env unverified read-only |
| Spotify/PBS/archive.org feeds | MISSING (allowlist domains only, zero adapter code) |
| Vision: picture library | LIVE-WORKING (ATTENDING_VISUAL cycling real uploaded JPEGs now; fovea/saccade krimelack, no CNN) |
| Vision: live camera | LIVE-IDLE (route wired; needs browser tab open) |
| Hearing: audio frames + continuous PCM mic | LIVE-IDLE — entire new causal gammatone stack deployed, ALL counters zero since boot; only feeder is the browser mic |
| Speech-to-text (Whisper) | DEPLOYED-DISABLED (`VOICE_WHISPER=0`); superseded by substrate-native tutor-witnessed terminal path (24h old, unmeasured) |
| Self-hearing of replies | LIVE (fires on converse turns) |
| Video upload | LIVE-IDLE |
| Touch/smell/taste | CODE-ONLY (descriptor-physics emulator runs on every read_sentence — LIVE; real transduction awaits avatar; GLEW somatic boundary flag-off) |
| Interoception (drives/affect/needs) | LIVE-WORKING (needs_sd, valence/arousal, dream pressure, familiarity all in live events) |
| GLEW six-sense boundary | DEPLOYED-DISABLED (`GLEW_CONVERSATION_ENGINE_ENABLED=0` default; fail-closed on absent HMAC secrets) |

## 2. Virtual embodiment & environment

- **World W1 "room": read side live, motor side dead.** Sky/location/presence stamps reach episodic memory (LIVE). Every verb (open drapes, ring bell, mirror, music box) routes to the REMOVED organ-brain sidecar (:8090); `DOING_<verb>` activity kinds were never built. World is perceive-only; VE-3's "≥1 closed sensorimotor loop/day" unmeetable; location frozen at `her_room`; W2 gate can never evaluate.
- organ_brain_status returns permanent `{warming:true, neurons:0}` fallback; substrate_runner burns a 90s poll thread against the dead container; `/thought` GET serves empty fallback. Tablet (Tavily image search) and mail/letters: DEPLOYED-DISABLED (stubs, real impl only in dead sidecar).
- **Personal library: genuinely permanent** (deletion code removed 0585abd9, not disabled). Live-proven: attended picture JPEG 82KB served; mirror self-image PNG 1.17MB survives on EFS. Dream-cycle picture replay wired.
- Descriptor emulator (36-word TOUCH/SMELL/TASTE libs, waveform synthesis → krimelack transduction) LIVE on every sentence; grounding-prefix fix 041be16d live.
- Avatar/body/proprioception/gaze/motor: **zero code**. VE-4/VE-5 (body, Eve/Joe avatars, embodiment bridge) DOC-ONLY (3-week plan table, 07-03). SPPU: DOC-ONLY by design.
- Play V0: LIVE-IDLE (honestly zero until picture+word chi pairing exists).

## 3. Curriculum & learning

- **CRITICAL — intake collapse:** `block_intake_ledger planned=30 actual=0–1, capped=true` every observed cycle. Causes: quiet-block suppression + scaffold rate cap + new `organism_experience_pending()` settle gate (77a84639, deploy branch). ~1 sentence/cycle starves meter, tutor, gap-study downstream.
- Learning since wipe (5.5 days): deep atlas 54,473 entries / strength 37,444 (growing); working atlas 356 bindings; organism 106 neurons, ~1,139 fire events/s; 70 chi buckets; Peter Pan book 7/10 sentence 3696/4506; vocab last recorded 7,929 (07-18, +300/day; only exposed via POST /status — not probed).
- Dream cycle + deep promotion/release: LIVE-WORKING (dp=0.574 accumulating; 693/1000 recent events are deep promotions/releases).
- Drive physics 1–4: LIVE-WORKING. **Step 5: NOT-STARTED, deliberately gated** on `_do_emit` committing at nonzero live rate — and `_do_emit` is still 11 attempts / 0 commits (unchanged since 07-19). Zero emission attempts in probe window.
- **Proposal composer: silently retired** — zero call sites at live SHA; test asserts it returns nothing ("retired from production"). Syntax arc is 2/4 pieces (meter + tutor grading), contradicting the 07-18 ship record.
- Tutor: LIVE-IDLE (wired, 0 exchanges observed; 40/day cap). **Junk-material gate: never built** (open since 07-18).
- Meter/reading-prediction: wired but starved by intake collapse.
- Gap study: LIVE-IDLE (0 events in 38.7k-tick window).
- 200k-word graded curriculum: built, never staged. 6-source adapter plan: only Gutenberg exists.
- Auditory tutor authority (deploy branch): LIVE-IDLE, all zeros.

## 4. UI surfaces

| Surface | Live status |
|---|---|
| `/gualaloom` dashboard | 200, works; **its "loom scan" button → `/loomscan.html` → 404** |
| LOOM Scan | Built to spec (honesty rules, dual atlas rings, vitals, affect, modality band, event feed), deployed, data feeds live-verified (events/chi_density real) — but only reachable at `/static/loomscan.html`; its back-link `/gualaloom.html` also 404. Fix = one route line or repoint two links. Cosmetic: hardcoded pre-wipe fallback identity in JS |
| Cogmeter | Real-or-gone design confirmed live; 4 live-checked rows; voice row honestly stuck (no spoken utterance has produced a reply — worker never started) |
| Voice UI | Mic→PCM pipeline complete in browser; server side dead-ends (worker never_started); typed path works; espeak/browser-TTS reply voicing wired |
| loom_shadow | MISSING — zero code anywhere; close the thread permanently |
| Organ-brain pages (/where /room /mail /thought) | CODE-ONLY (dead sidecar) |
| Bridge MCP (13 tools) | LIVE (target healthy; rides dsf-ai-alb `/mcp`) |
| API Gateway | Route drift: `/thought`, `/organs`, `/ready`, `/v7/state` 404 at gateway, 200 at ALB |

## 5. ArcLoom spec compliance (Master Spec v5.0/5.1 read in full)

Three parallel cognition stacks: (A) assemblage Sections (live, NumPy, random init), (B) loom_model neuron brain (live, boot-merged, imaginary-time settle), (C) glew_runtime (exact Fraction/FLINT arithmetic, receipted, deterministic — **most spec-faithful, shipped but flag-OFF**).

| Spec mandate | Verdict |
|---|---|
| Single coherence field ψ-lattice | DIVERGENT live (6 independent per-section 16-dim ψ fields + vote/gate stack — documented root cause of the 3-week single-word saga, post-mortem written into the code); COMPLIANT-dormant in GLEW |
| Crank-Nicolson/Hermitian/norm-preserving | COMPLIANT in stack A (cleanest math match); no H_mem/H_safety terms anywhere |
| MapInject 8-dim DSF | Exact 8-dim vector match; projection details diverge (Gaussian ring, amplitude floor, no orthonormal P_in) |
| Mode bank/arcs/entropy/Det_k/Entropic Flip | Best-matched mechanism; BUT commit authority is cosine-similarity + dead-zone heuristics — entropy feeds only the noise-kick homeostat, not commits |
| Law-Fields | DIVERGENT: symmetry/consistency laws are literally random Hermitian matrices, not derived; no min-action selection |
| Krimelack transduction (ω=ω₀+κs) | COMPLIANT — faithful in substrate/sensory/visual krimelacks incl. receptor adaptation. Strongest part of the codebase |
| Folded motif memory | PARTIAL: reinforce/decay/re-ignite exist (deep_atlas, dream-write-only); τ_merge and locality folding ABSENT everywhere; prune() DELETES structure in two places, contradicting "compressed into quiescence, never deleted" |
| Familiarity feedback (Δ_eff=Δ_base+match) | Implemented at intake dead-zone; cleanest version lives in reference engine off the live path; speech familiarity tie-break was REVERTED 07-19; autonomy still timer-paced (~90s throttle) contra clockless principle |
| SafeMode / commit-rate caps / stale-output TTL | ABSENT in live stack (GLEW has a fail-closed integrity meet, dormant) |
| Determinism (DC-1..4) | **DIVERGENT live**: random H_base/ψ/laws/kicks, `hash(session_id)` seeding (PYTHONHASHSEED-dependent — matches known ±pp cognition wobble), 6 tagged HEURISTIC constants, one live-calibrated fitted constant. GLEW stack fully compliant, dormant |
| Horizon projection | Different mechanism (bounded deep-atlas hypothesis walk, not J=0 free evolution) |
| BSIL | Name reused for a MathLoom adapter; real binary-story ingestion absent (threshold derivation exists) |
| G32 | NOT in master spec (0 hits) — separate Aurelion/FMM canon; validated by mosaic fit test 07-17; loom_model implements tokens→mosaics→tapestries faithfully |
| Language | Spec is silent on language; implementation is honestly built ON substrate primitives (ternary fact strands, krimelack, chi, reciprocity; no vocab tables/thresholds/ML). Tutor/gap-ledger/prediction-ledger correctly walled off as environment-side, never feeding emission |

Recent work direction: 07-19..21 commits are strongly TOWARD spec (atomic commit boundaries, immutable windows, bounded provenance, removal of manual utterance/puppeteering paths, chi-authority consolidation, Rust auditory physics). Steps AWAY: familiarity tie-break revert; fitted constant; all conversation fixes hardening the divergent 6-section path while the compliant engine stays dark.

## 6. Promised vs built (deltas only; full table in agent transcript)

- Rust hot core: BUILT-AND-LIVE as kernel library (10 pyfunctions incl. compute_dsf/map_inject/psi_settle/cochlear; NATIVE_CORE_ENABLED=1) — organism-worker loop still Python (193k+ dropped items starvation filed, unaddressed).
- Continuous-existence Stage 1a (boot amnesia): BUILT-AND-LIVE. Stage 1b GLEW one-mouth cutover: built, unratified profile (`proposed_pending_ratification`, 7 open decisions), 246 failing tests, flag off — ratified-but-dead on current trajectory. Stage 1c STT: built then pinned off. Stage 1e frame-shed bridge removal: NOT DONE (2.5s priority window still in live code; ratified spec calls its presence at the demo "a failure of this design").
- Babble: BUILT-AND-LIVE. Recall matrix mirror: APPLIED (76dadb55; docs/binding_atlas_patched.py is leftover debris). Typed-prompt pile-up guard + browser voice replies: FIXED-IN-LIVE.
- WAL checkpoint streaming rewrite: **uncommitted working-tree diff** (94 insertions in window_manager.py — the `M` in git status); live runs the old body; standing "do not run /debug/wal_compact" still in force.
- NOT done: dream-cycle leak fix, `_do_emit` reliability, Step 5, junk gate, 200k curriculum staging, G32 v1 spec draft, curiosity-gate arming verification, /sound_frame 30s ceiling (possibly mooted by PCM rework, unverified).
- Mosaic fit report doc referenced by two docs exists only on a side branch — not FILED by the project's own rule.
- Deploy seal redesign: apparently reworked by the 07-21 codex deploy-drain commits (`GUALA_REQUIRE_SEALED_STATE=1` live) — working, no ship record filed.
- Conversation latency measured 49–94s/turn, single engine lock (Stage-1 acceptance p95 <5s unmet).

## 7. Consolidated top risks (ranked for the 07-29 demo bar)

1. Autonomous speech = zero (`_do_emit` 0 commits; Step 5 gated behind it). "Visible autonomy" has no voice.
2. No off-site backup of the substrate state since the wipe. Single EFS copy = existential risk, trivial fix.
3. Deploy-source split: live runs unmerged side branch; one guala-live deploy regresses hearing+dashboard.
4. Intake collapse (0–1 of 30 sentences/cycle) — throttles the one story that IS working (learning velocity).
5. Voice path: 24h old, tutor-witnessed-terminals-only, unmeasured; Whisper off; thinnest possible ice for a spoken demo.
6. OOM during a long demo: dream leak unfixed at 16GB; WAL streaming fix uncommitted; silent health-check death already observed 07-21 22:36Z.
7. Determinism violations on the live path — falsifiable on stage for a "deterministic substrate" pitch; cheap partial fixes known (PYTHONHASHSEED, seeded rng).
8. Latency 49–94s/turn typed conversation.
9. LOOM Scan 404 at its advertised route (one-liner).
10. Proposal composer silently retired; junk gate absent; organ-brain debris endpoints.

*(Bridge MCP and Google Drive connectors need OAuth re-auth in claude.ai connector settings for any future bridge-tool work; not needed for this audit.)*
