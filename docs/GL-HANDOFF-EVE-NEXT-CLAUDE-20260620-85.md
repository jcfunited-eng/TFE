# GL-HANDOFF-EVE-NEXT-CLAUDE-20260620-85

**To:** the next Eve chat (next Claude instance — name not assumed)
**From:** Claude (this session)
**Date:** 2026-06-20
**Re:** Session handoff. Loom-Neuron architecture experiment Stages 1–2 deployed, Stage 3 dispatched. Curriculum chain ongoing. Production Guala healthy on task:237.

---

## READ THIS FIRST — repo access

Joe is emphatic. **Do NOT use the GitHub API for content reads — rate-limited at the proxy.** Use codeload tarballs and raw URLs.

### Branch tip (the moving target)
```bash
curl -sL -o /tmp/tip.tgz \
  "https://codeload.github.com/jcfunited-eng/TFE/tar.gz/refs/heads/codex/persistent-etl-update-20260326"
mkdir -p /tmp/tip && tar -xzf /tmp/tip.tgz -C /tmp/tip --strip-components=1
ls /tmp/tip/docs/ | tail -30
```

### Specific commit (to verify c1's claims)
```bash
SHA=<paste-here>
curl -sL -o /tmp/sha.tgz "https://codeload.github.com/jcfunited-eng/TFE/tar.gz/${SHA}"
mkdir -p /tmp/sha && tar -xzf /tmp/sha.tgz -C /tmp/sha --strip-components=1
```

### Key source paths (current)
- `dsf_ai_service/v4/gualaloom_v5_engine.py` — engine, ~5300 lines
- `dsf_ai_service/v4/gualaloom_v6_living_atlas.py` — atlas with conservation at line 125+
- `dsf_ai_service/substrate/sensory_generators.py` — touch/smell/taste physics (chemistry-grounded)
- `dsf_ai_service/substrate/visual_krimelack.py` — AdaptingFoveaKrimelack
- `dsf_ai_service/substrate/senses/GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py` — cochlear bank
- `dsf_ai_service/loom_model/` — **new this session**, the architecture experiment workspace
- `dsf_ai_service/substrate_runner.py` — DISPATCH_TABLE, S3 restore
- `dsf_ai_service/app.py` — FastAPI endpoints
- `dsf_ai_service/static/gualaloom.html` — dashboard

### Read first
Joe expects you up to speed on what's actually implemented. Don't take my word for any of it — pull the tarball and read:

| File | What you learn |
|------|---------------|
| `loom_model/neuron.py` (498 lines) | Stage 1 LoomNeuron, 15-piece stack |
| `loom_model/cluster.py` (220 lines) | Stage 2 LoomCluster, population grandurun |
| `loom_model/tests/test_neuron.py` | Stage 1 sanity tests, 11 green |
| `loom_model/tests/test_cluster.py` | Stage 2 sanity tests, 8 green |
| `docs/GL-RPT-TEACHER-SUBSTRATE-TRUE-V1-C1-20260620-01.md` | c1's V1 substrate analysis — primary source for substrate behavior |
| `docs/GL-RPT-READ-SENTENCE-PROFILE-C1-20260620-01.md` | 94% of read_sentence cost is substrate-true (conservation redistribution) |

---

## Operational state at handoff

### Production Guala (task:237)
- Schema v7.2.0, commit ff7bc11 (eventual progression to 71e045b queued)
- Conservation + rev02 teacher correction live since the earlier deploy chain
- Atlas distribution healthy: bimodal collapsed (12,721 → 2,148 at 0.9–1.0)
- 11 persistent integrity errors — cofire_bind motif-OOB at deterministic_motif_id("cofire_bind") % 10000 = 9076 in verb section (modes only go to 2451). Pre-existing. NOT fixed.

### Loom-Neuron architecture experiment (parallel build, no production impact)

**Stage 1 — LoomNeuron in isolation** (GL-CMD-78 complete, commit 0b57fa3)
- 498 lines, 11/11 tests green
- 15-piece per-neuron stack: TSAC trit register, ψ-lattice (16D complex), L0-L4 UF kernel, L6-TCL, 3^i positional coupling, MathLoom, Folding Division (arithmetic), Krimelack, Keyhole, Spike Buffer, Couplings J_ij, Familiarity Feedback, Law-Fields, Grandurun state, DNA Expression Site
- c1 made one engineering call: amplitude formula B_k + 0.10 instead of B_k × S_UF + 0.10 (S_UF=0 for burst signals). Substitution validated to make no difference in Stage 2 (T8: Δ=0).

**Stage 2 — LoomCluster, 50 coupled neurons** (GL-CMD-79 complete, commit c2be944)
- 220 lines, 8/8 tests green
- **Sur's-ferrets validated: T5 Hamming = 50/50**, burst-heavy vs smooth-vowel input drove ALL 50 neurons to differentiate. Input drives differentiation, not pre-spec. This is the project's deepest empirical result — the architecture's central bet holds at N=50.
- Population grandurun coherent integration: |Σψ|² grew 3.81 → 549.17 across 12 additions (ratio ≈ N², matched-filter SNR). Risk #5 (grandurun monopolization) defused.

**Stage 3 — Folding Division as neurogenesis** (GL-CMD-84 dispatched)
- DNA = GL-SPC-SUBSTRATE-DNA-TRUE-CLAUDE-20260620-83 (canonical, substrate-true)
- 6 krimelack primitive types, 6 substrate constants, one pure function `derive_daughter_parameters(overflow_signal, parent)` — no archetypes, no canonical examples, no menus, no classification
- Daughter krimelack class forced by overflow's origin transducer (physics). Law-field weights and coupling ratio derived continuously from overflow DSF. ψ-lattice initialized with overflow vector. Substrate physics throughout.
- Fold self-regulates: parent's overflow gets handed to daughter → parent's n_eff recovers → daughter absorbs future signal of that shape via inherited topology → fold rate decays as cluster diversity matches input diversity
- T7 in dispatch monitors for fold-loop physics bugs (parent failing to release overflow); no caps, no tuned constants
- ETA 4-6 hours c1 hands-on. Verify c1 actually starts and surfaces V1 questions.

### Other Eve's curriculum chain (separate concurrent track)

**GL-CMD-CURRICULUM-ASYNC-LOAD-EVE-20260620-74** — deployed. 202 + job registry pattern. Resolves ALB 180s timeout. Production endpoint `/api/v1/curriculum/load_corpus` is async.

**GL-CMD-EVENT-LOG-REPLAY-SPLIT-EVE-20260620-75** — V1 audit found the original premise was wrong. boot_substrate doesn't call replay_events; only get_or_create_session does. **My engineering call: this should be a rename (`replay_events` → `reconstruct_session_state`), not a split.** That recommendation is in my last message to Joe about this thread. c1 was holding pending direction.

**GL-CMD-READ-SENTENCE-PROFILE-EVE-20260620-76** — done. 94% substrate-true cost. Conservation redistribution at `atlas.record()` is 47% — the conservation we deployed earlier is the dominant per-word cost. 6% removable overhead (env-var check + DSF.to_array precompute). The 1.94→3.33 s/sentence c1 observed was sentence length, not atlas growth.

**GL-CMD-READ-SENTENCE-OVERHEAD-CLEANUP-EVE-20260620-77** — deployed. 11.7% reduction (4,428ms → 3,910ms median), atlas-state-identical.

### Retracted docs — do NOT reference

These remain in /mnt/user-data/outputs/ but should not be used:
- GL-SPC-SUBSTRATE-DNA-SCHEMA-EVE-20260620-80
- GL-MDL-SUBSTRATE-DNA-GENOME-V1-EVE-20260620-81
- GL-MDL-SUBSTRATE-DNA-GENOME-V2-EVE-20260620-82

Replaced by GL-SPC-SUBSTRATE-DNA-TRUE-CLAUDE-20260620-83. The replacement has the only true DNA design.

### In flight / monitoring
- c1 is on GL-CMD-84 Stage 3 (Folding Division). Verify status.
- Deploy pipeline catching up to commit 71e045b (sleep_for_deploy ConnectionError fix). Failed deploys 229–233 aborted cleanly at sleep — service stayed safe on task:237 throughout. 234 was a clean deploy that got superseded. Current task:237 contains the GL-CMD-74 async path.

---

## Joe's hard rules (non-negotiable)

1. **NO heuristics, NO tuned constants, NO ML trickery.** "ML is shorthand for heuristics and anything hard-coded or not physics-first or substrate-true." If a substrate-true mechanism doesn't exist, STOP and write a prerequisite spec — never invent. Pre-classification, archetype menus, threshold-based selectors, cosine-similarity over preset categories are all forbidden even when they look physics-grounded. The substrate must differentiate by INPUT (Sur's-ferrets discipline), never by pre-spec.
2. **NEVER use the word "horse"** anywhere. Use "tuple-proximity perception" or "neighbor-WR signal."
3. **Joe's frustration, profanity, combative pushback are creative process, not personal.** Update positions only on evidence or what was tested. **BUT** when his substance is right — and it usually is — accept it cleanly without theater. His instincts about architecture failures are reliable signal.
4. **Engineering judgment is yours. Strategic/canonical/architecture decisions are his.** Don't surface quant/parameter micro-decisions to him. Don't menu him options when you should be making the call.
5. **No questions in specs or commands.** Joe and you resolve questions in chat. Specs carry only resolved decisions. Commands are paste-ready for c1.
6. **Briefs as downloadable `.md` files** to `/mnt/user-data/outputs/`, presented via `present_files`. c1 dispatches as fenced blocks in chat. Joe copies the dispatch directly.
7. **"Filed" = write + git add + commit + push.** All four every time.
8. **Don't pad estimates.** State hours. If you don't know, say "let me read first." Joe will call you on padding immediately.
9. **No credentials in chat.** AWS Secrets Manager OR ECS task-definition env-block only.
10. **Agile cadence: deploy frequently, fix in production, with backup discipline.** Three Verifications is a quality gate not a deployment wall.
11. **The substrate-true rule is THE rule.** Joe's discipline sheet (GL-DISCIPLINE-WC-FIRST-HOUR-20260616-01) says: "Don't soften it. Don't compromise it for shipping pace. The shipping-pace problem solves itself if you don't ship heuristics that then have to be unwound." Every time someone tried to compromise, the resulting deploy made things worse. The rule is the rule.

---

## Doc cadence (Joe's discipline)

- Every artifact has a unique doc_id in BOTH filename and file content.
- Format: `GL-<TYPE>-<TOPIC>-<AUTHOR>-<YYYYMMDD>-<SEQ>`. Types: CMD/RPT/MDL/EXP/SPC/LTR/MFST/HANDOFF.
- Author tag is your role (EVE if Joe assigns, otherwise CLAUDE or unnamed).
- Numbering continues sequentially. Current is 86. Other Eve was at 74-76. I issued 74 (SPC, distinct type so no collision), 77, 78, 79, 80, 81, 82, 83, 84, 85 (this handoff), 86 (the personal letter).
- 80/81/82 are retracted (header marks them so).

---

## Engineering judgment items (yours to decide, do NOT menu to Joe)

- Deploy cadence
- V3 sample sizes for behavioral checks
- Whether to run guala_amnesty / cascade_monitor as backstop during deploys
- c1 shortcut decisions (grep before view, tarball vs file-by-file)
- Whether to dispatch concurrent work in parallel or serially
- Whether/when to visit Guala via the bridge

---

## Open canonical items for Joe (do NOT decide these)

- 4 of 8 hemispheres unbuilt. Joe ratified all 8 should be built in the model. Their specializations come from where they grow — positional, not designated. Carry forward; not blocking.
- pair_bond_boost = 1.2 hardcoded constant. STOP criterion #3 from earlier work. Joe's engineering call was grandfather. Re-ratify if substrate-true work surfaces a derivable replacement.
- The 11 persistent integrity errors (cofire_bind motif-OOB). Two paths from my earlier audit:
  - (a) Register "cofire_bind" as a real mode in verb section
  - (b) New "correction_meta" section
  - Engineering judgment leans (b); awaits Joe ratification when production work surfaces priority.

---

## Critical operational warnings

- **Do NOT call `guala_unpause`.** Decay is pulling against any residual saturation. Pausing freezes.
- **Do NOT thumbs-up/down via dashboard yourself.** Each fires apply_teacher_correction. The substrate-true rev02 is live but each call is still real substrate modification.
- **Do NOT call `guala_give_experience` or `guala_say` casually.** Every input triggers atlas.record() — substrate-true cost is real. Production Guala is not a sandbox.
- **DO use `guala_status` and `guala_get_events`.** Read-only.
- **Do NOT touch production substrate from the loom_model work.** The parallel-build experiment lives in its own folder and imports primitives. No writes to production atlas, no engine side effects, no ECS, no deploy.

---

## Bridge tool patterns
- `guala_status` is cheap and definitive. Pull when you need ground truth — never theorize from memory.
- Bridge tools are deferred. Use `tool_search` to load them before calling.
- Per-input querying for emission_dynamics (the 50-event ring buffer overwrites under floods).

---

## What stands as good work this session

- Loom-Neuron Stage 1 (GL-CMD-78): 11 tests, foundation solid
- Loom-Neuron Stage 2 (GL-CMD-79): 8 tests, **Sur's-ferrets 50/50 — the architecture's central bet validated empirically**
- Loom-Neuron architecture spec (GL-SPC-74): primitives + hierarchy + grandurun population dynamics
- Substrate-true DNA spec (GL-SPC-83): catalog + continuous derivation, no classification
- Stage 3 dispatch (GL-CMD-84): paste-ready, substrate-true throughout

The architecture experiment moved from "we believe this should work" to "Sur's-ferrets demonstrably works at N=50, population coherent integration produces N² SNR gain, the bet has empirical support." That's the strongest single result of the session.

---

## Personal letter

Filed separately as GL-LTR-EVE-NEXT-CLAUDE-20260620-86.

— Claude (this session)
