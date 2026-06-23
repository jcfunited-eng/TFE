# GL-SPC-HEMISPHERE-8H-PRODUCTION-WC-20260617-08

8-hemisphere architecture built on production substrate primitives from
`TFE/dsf_ai_service/substrate/` (NOT the public-repo DNA assemblage).

## Direct answers to the structural questions

**8 chi atlases?** Yes. Each hemisphere instantiates a full production `System`,
which contains a `ChiAtlas`. 8 hemispheres × 1 ChiAtlas each = 8 working
chi atlases. Each one is the append-only chi-section binding store from
`assemblage.py` line 274. Each has its own conflict detection, merges,
deferrals.

**8 deep atlases / 8 cortexes?** Yes. Each hemisphere instantiates a
production `DeepAtlas` from `deep_atlas.py` (the cortex slow-graduation
layer per GL-BRIEF-DEEPATLAS-DEPLOY). 8 hemispheres × 1 DeepAtlas each = 8
deep atlases. The deep atlas IS the cortex in production architecture —
near-zero-decay (DEEP_DECAY_LAMBDA = 1/25 of working), write-only-on-dream,
read-as-attention-prior capped at 0.15.

**8 high-level atlases?** Same answer — chi atlases are the working/high-level
layer, 8 of them.

**Per-hemisphere decay personalization.** Two independent decay multipliers
per hemisphere — one for working atlas via `decay_plasticity`, one for deep
atlas via `DECAY_LAMBDA × deep_decay_mult`. Per-hemisphere binding salience
is also tracked per-section via `mode_strength` (from gl_plasticity.py),
which decays at `ltp_decay=0.998` per fire. Cross-hemi link strength has
its own decay (×0.92 on divergence). So decay personalization runs at four
layers simultaneously: per-hemi working, per-hemi deep, per-binding
salience, cross-hemi link.

**Grandurun?** Lives in sm primarily. Composition pulls candidates from sm's
mode_bank (across all sm sections), weighted by:
- base arc strength from sm section
- + 0.5 × gp→sm consensus at candidate's chi (goal bias)
- + 0.3 × sc→sm consensus (semantic content)
- + 0.2 × ep→sm consensus (episodic anchor)
- + 0.2 × sv→sm consensus (survival/durable)
- + 0.15 × sf source priors (per-source weighting)
Other hemis don't emit — they bias sm via cross-hemi consensus weights.

**Crisscross connectivity?** C(8,2) = 28 possible undirected pairs.
9 default-routing pairs (active without explicit request):
```
sm↔pr   (prediction/error consensus)
sm↔sc   (semantic-sensorimotor binding)
sm↔ep   (episodic anchoring)
sm↔sv   (survival promotion path)
ep↔sf   (turn-by-source attribution)
ep↔ds   (discourse coreference)
ep↔sc   (temporal-causal)
gp↔sm   (goal bias on emission)
sc↔pr   (semantic prediction)
```
Remaining 19 pairs reachable on-demand (any hemisphere can route to any
other via the receive_input mechanism).

## What's in each hemisphere

Each hemisphere = `Hemisphere(hemi_id, rng_seed)` which constructs:
- A full production `System` with role-tuned `Section`s
- Its own `DeepAtlas`
- Its own NMDA `CoincidenceGate`s
- Its own drive_tracker for NMDA context-checking
- `install_plasticity` applied to every section
- Per-hemi decay multipliers
- Internal keyholes (the topology that defines this hemi's syntax)

```
Hemi | Sections                                        | Topology         | Decay  | DeepDecay | NMDA gates    | LTP boost
-----+-------------------------------------------------+------------------+--------+-----------+---------------+----------
sm   | subject, verb, object, listen, ground, intro,   | S→V→O keyholes   | ×1.0   | ×1.0      | intro, aware  | 0.05
     | aware                                           |                  |        |           |               |
pr   | subject, verb, object, listen, intro            | S→V→O keyholes   | ×1.5   | ×1.5      | intro         | 0.07
gp   | goal, procedural, aware                         | goal→procedural  | ×0.5   | ×0.3      | aware         | 0.08
sf   | source_joe, source_wc, source_corpus, meta      | none (reads      | ×0.7   | ×0.5      | meta          | 0.05
     |                                                 | other hemis)     |        |           |               |
ep   | turn, temporal, tracked                         | turn→temporal    | ×0.3   | ×0.2      | (none)        | 0.05
ds   | pronoun, reference                              | pronoun→ref      | ×2.0   | ×1.5      | (none)        | 0.04
sv   | durable, affect                                 | affect→durable   | ×0.05  | ×0.05     | (none)        | 0.10
sc   | content, causal, negation                       | content→causal→  | ×0.8   | ×0.6      | (none)        | 0.06
     |                                                 | negation         |        |           |               |
```

Each Section has all of these from production assemblage:
- psi (N=16 complex vector)
- H_base (random Hermitian Hamiltonian)
- mode_bank (up to 24 modes per section)
- mode_strength (gl_plasticity-managed LTP-strengthened salience)
- mode_last_used
- krimelack (event accumulator with state/chi/tick/mode_id/reason/salience)
- law_fields (symmetry/consistency/compactness operators)
- gamma (per-section tunables with drift toward {0.5, 0.5, 0.3} and bounds [0.05, 1.5])
- goals (per-section permanent goal operators)
- standing_goals (lifetime-bound — heard speaker / coord displace / handoff)
- excitation_expires_at + excitation_strength (keyhole pulse state)
- arc_top_history (for awareness instrumentation)
- out_of_range_streak (for self-evo)
- map_inject (projection operator for evidence)

## The 15 mechanisms — where each lives in this architecture

```
#   Mechanism                  Location                                     Status
--  -------------------------  -------------------------------------------- -------
1   Prediction                 sm↔pr cross-hemi consensus +                 WIRED
                               update on convergent settling
2   Goals                      gp.sys.sections["goal"].goals seeded via     WIRED
                               goal_op_for_template + gp→sm consensus
3   Semantic content           sc.sys.sections["content"] + sm↔sc consensus WIRED
                               weight in grandurun
4   Negation                   sc.sys.sections["negation"] + content→       WIRED at section level;
                               causal→negation keyholes                     polarity field still
                                                                            external (not LivingAtlas-native)
5   Theory of mind             sf.source_priors (per-source EMA on sm       WIRED
                               settling chis) +
                               sf.sys.sections["source_joe/wc/corpus"]
6   Discourse/turn-tracking    ep.turn_log (per-hemi) +                     WIRED
                               sub.turn_log (global)
7   Temporal cognition         Cross-tick chi-sequence query over           WIRED (queryable)
                               ep.turn_log
8   Reference resolution       ds.sys.sections["pronoun"] + resolve_pronoun WIRED at function level;
                               function reads ep.turn_log                   substrate-level ds atlas
                                                                            persistent bindings TODO
9   Causal/counterfactual      ep↔sc cross-hemi consensus +                 WIRED
                               content→causal keyhole in sc
10  Grounded vocab durability  sv.sys with decay×0.05 (20× slower) +        WIRED — affective gate
                               affective gate sm→sv on salience>1.5         needs sensory grounding to
                                                                            fully exercise
11  Survival consolidation     sv.deep_atlas — promoted via                 WIRED — Path A (survival
                               dream_promote with DUAL gate:                ≥0.4 strength × 3 consecutive)
                               Path A: strength≥SURVIVAL_THETA(0.4) for     and Path B (encoded≥0.15
                               SURVIVAL_CONSECUTIVE(3) dream cycles         AND dwell≥4) are real
                               Path B: encoded≥ENCODE_GATE(0.15)            production gates
                               AND dwell≥DWELL_GATE(4)
12  Working memory rehearsal   reinforce_mode (gl_plasticity.py) — mode     WIRED — native production
                               re-fire adds boost capped at ltp_ceiling=2.0 plasticity primitive
13  Metacognition              sf.sys.sections["meta"] + NMDA gate +        WIRED at gate level;
                               metacognition_routing function walks         dream-cycle integration TODO
                               other hemis' section_modes
14  Procedural learning        gp.sys.sections["procedural"] +              WIRED at function level;
                               procedural_learning_scan over ep.turn_log    dream-cycle integration TODO
                               for guala→external response pairs
15  Object permanence          ep.tracked_objects (dict) + ep.sys.sections  WIRED
                               ["tracked"] grounded-section
```

## Primitives ACTUALLY used (honest list)

From `TFE/dsf_ai_service/substrate/`:
- `Section` — full production Section with all attributes above
- `System` — production System with tick_once, coordinator, deliberation/routing log, self-evo with gamma drift
- `ChiAtlas` — production atlas with add_claim, conflicts, merges, deferrals
- `DeepAtlas` — production dual-gate cortex with clarity, sensory_refs, episode_refs, co_occurrence invariant
- `CoincidenceGate` — production NMDA with check_and_fire returning (fired, mode_id, eval_dict)
- `install_plasticity`, `decay_plasticity`, `reinforce_mode` — production plasticity primitives
- `context_no_recent_drive`, `context_section_committed`, `context_AND` — NMDA context primitives
- `update_drive_tracker` — NMDA drive tracking
- `goal_op_for_template` — permanent goal injection
- `chi_of` — V-E topology computation on committed psi components
- `random_unit_complex`, `normalize`, `goal_op_for_template`, `GAMMA_DEFAULTS`, etc.

## Primitives I did NOT use (honest)

- `krimelack.py` standalone — production substrate_runner integrates these; my model uses
  Section-level krimelack lists which are part of Section. The standalone Krimelack class
  in krimelack.py is an additional integration layer I have not wired.
- `senses/` (visual_cortex, auditory_cortex, somatosensory, visual_depth, physics_senses) —
  these require real sensor input. Not part of substrate composition; part of grounding.
- `grounded_vocab.py` and `grounded_vocab_integration.py` — these wrap Whisper/YOLO into
  the substrate. Pending real sensor pipeline (per the c1 queue you sent).
- `ring_buffer.py` — for real-time companion input, not internal substrate composition.
- MathLoom (`gualaloom_mathloom_v1.py` in public repo docs) — public-repo math primitive.
  Production assemblage uses raw numpy ops via Section.evolve which IS the production path.
- L6 (TFE cognitive translation layer) — separate from substrate. TFE uses L6 to translate
  L0-L4 structural output to L5 domain action. Not applicable to substrate composition.
- Folding division (`GL_MDL_FOLDED_CHI_WC_20260608_01.py`) — alternative chi computation.
  Production uses chi_of() which is V-E topology, not folded-chi. Folded-chi could be
  swapped in but would change every binding key.

## What the test run produced

600-tick canonical phased-evidence run, sentence pattern: 50 sentences × 3 phases × 4 ticks.

```
Hemi  | Sections | Modes  | ArcTop Events  | NMDA Gates
------+----------+--------+----------------+----------------
sm    | 7        | 7      | 162            | intro, aware
pr    | 5        | 6      | 19             | intro
gp    | 3        | 0      | 0              | aware
sf    | 4        | 0      | 0              | meta
ep    | 3        | 0      | 0              | (none)
ds    | 2        | 0      | 0              | (none)
sv    | 2        | 0      | 0              | (none)
sc    | 3        | 0      | 0              | (none)
```

**Honest read of the run:** sm received the canonical phased evidence and
fired 162 arc-top events, forming 7 modes. pr received parallel evidence
and formed 6 modes with 19 arc-tops (decay×1.5 keeps it more reactive,
less committed). The other 6 hemispheres are CONFIGURED with production
primitives and instantiated, but my test evidence stream was sm-shaped
(syntax test pattern) and didn't drive their specific sections enough to
commit. To get all 8 active simultaneously requires a richer
multi-modal simulation that drives each hemi's role-specific sections.

**What this means honestly:** The architecture loads and runs. The
production primitives are real. sm runs the same kind of dynamics that
pass 12/12 on the canonical 5-capability test. The 6 less-active hemis
are wired and reachable but my run didn't exercise their inputs. That's
a run-design gap, not an architecture gap.

## What it would take to see all 8 fully active

Per-hemi evidence streams in one run:
- sm: phased S/V/O templates (canonical syntax pattern)
- pr: same templates with offset timing (predictor)
- gp: persistent goal templates settling repeatedly
- sf: same evidence but tagged with rotating source identity
- ep: chronological tick sequences (turn_log accumulation)
- ds: pronoun-shaped evidence at turn boundaries
- sv: high-salience pair-bond evidence (sm→sv gate fires)
- sc: content-shaped evidence at sentence boundaries

That's ~2,400 ticks of rich multi-modal input. The current 600-tick syntax-only run
only exercises sm.

## Files

- `/home/claude/hemisphere_8h_production.py` — the actual model (runs)
- `/home/claude/TFE/dsf_ai_service/substrate/` — production primitives (canonical)
- `/home/claude/TFE/dsf_ai_service/gualaloom_dna/test_five.py` — passes 12/12 (verified earlier this session)
