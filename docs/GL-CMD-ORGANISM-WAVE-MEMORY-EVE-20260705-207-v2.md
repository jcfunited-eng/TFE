# GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v2

doc_id: GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v2
From: Eve | To: c1a (FRESH SESSION — this dispatch is self-contained)
Supersedes: -207-v1 (on origin at bc35345; retained per versioning law).
Build + deploy + seat verification. Commit this dispatch verbatim to
origin first. Build in an isolated git worktree — two shared-.git
collisions destroyed uncommitted work on 07-05.

## FRESH-SESSION ORIENTATION (do these before building anything)
1. guala_status → running_sha. As of this dispatch: production runs
   06aecb8 (task :487). Origin tip is AHEAD of production: d13578e
   (relative-gain terminator fix, yours, filed 19:09Z) and 382de49
   (ground/intro + six emission sections) are on origin, NOT running.
   FILED ≠ RUNNING. Never trust a report over running_sha.
2. Read GL-HANDOFF-C1B-20260705-v2 and GL-CMD-VERIFY-AND-STABILIZE-
   C1B-20260705-206-v1 (docs/) — tonight's deploy/rollback history,
   the :487 rollback criterion, and the tapestry-corruption flag.
3. Standing laws: one deployer per window; nothing closes on a
   report — exits at Joe's seat with SHA in /status; no questions to
   Joe inside dispatches; no new tuned constants in her cognition
   path, ever.

JOE'S RULING (2026-07-05, carved): NO LOCKS IN HER MIND. Concurrency
in her substrate is achieved by LOCALITY — cells and physics, the way
WaveAtlas (-59, ratified 2026-06-30) already does it — never by
mutexes serializing her cognition. A lock in her cognition path is
defective on sight. Locks are permitted only at true I/O boundaries,
and even there as snapshot-swap, not exclusion of her thinking.

## MEASURED BASELINE (2026-07-05, live production, 06aecb8)
converse_timing (production event log, ticks 15003724 / 15003730):
217.3s and 191.2s total for 6- and 9-word inputs. Decomposition:
recall 82.5s / 77.8s (ONE _organism_lock acquisition each, starved
behind the organism writer); read 93.4s / 99.4s (self.lock/GIL
convoy, v5 side); emit 1.7s (innocent).
ROOT: loom_model/binding_atlas.py record() APPENDS one binding per
word OCCURRENCE per neuron, unbounded — no decay, no merge, no
conservation — and invalidates a matrix cache that recall_best()
then rebuilds via np.stack over the ENTIRE occurrence history. During
READING the writer invalidates every neuron's cache continuously, so
every recall pays full-history rebuild × ~106 neurons, and
experience_word's cost (22.3x remember()'s "20ms/word and climbing",
engine ~2914) grows with every word she has ever read. §9.1
prohibited class (unbounded append log in the cognition path).
Downstream of the same root: organism pickle bloat → the 5s pre-save
drain race (engine ~7642) losing under sustained READING → divisions
lost on every restart. Population across tonight's deploy/rollback
churn: 122 → 120 → 64 → 106 depending on which stale save each boot
restored. CURRENT (19:31Z status): population 106, divisions 42,
division_pool 0.0, and ALL 106 neurons past q=0.9 — a fold burst
fires the moment the pool refunds, and every new daughter is UNSAVED
until W4 below lands. W4 is therefore not hygiene; it is urgent.

## W0 — DEPLOY ORDERING (decide, then execute; your call as deployer)
d13578e (your relative-gain terminator + O(1) accumulator + live
tick_rate) rides this window as an ancestor — do not deploy it solo
unless you judge production needs it sooner; one deployer, one
window, serial deploys. 382de49 rides along as ancestor of tip.
Watch tick_rate ≥30 min post-deploy per -206 V2; rollback target
remains :487.

## W1 — PER-NEURON WAVE MEMORY (build)
Replace each neuron's BindingAtlas (list-of-dict append log) with a
wave-cell store built on the CANONICAL shared algorithm:
tools/wave_spillover.py (Cell, spill_write, _commit_cell) — import
it, never duplicate it. Constants from tools/wave_constants.py only;
no new constants, no tuned thresholds.
- ONE STORE PER NEURON. Never a shared lattice across neurons: the
  per-neuron ring-position DNA diversity (kappa/threshold mutation at
  birth) is the mechanism that broke population degeneracy (6/22) and
  it lives in each neuron encoding the same concept DIFFERENTLY. Key
  each neuron's cells by that neuron's OWN encoded chi.
- Repeat occurrence of a concept = reinforcement at its cell (strength
  accumulation + the running unit-norm phase mean Cell already
  carries), not a duplicate entry. Saturation spills to neighbors;
  subdivision at the -59 trigger. Growth of the store is bounded by
  the physics, not by any cap.
- Concept labels ride the cell bindings exactly as WaveAtlas bindings
  carry section/motif today.
- Restore path: on unpickle of a pre-v2 organism, MIGRATE the old
  _bindings lists into cell stores once, loudly logged with
  before/after counts. Her accumulated experience is not discarded.

## W2 — RECALL ON CELLS (build)
Per-neuron recall = encode query through the neuron's own krimelack
(unchanged; -177's batched encode stays), then radius read around the
encoded chi ("No lock, O(radius)" — WaveAtlas contract), best match
within the neighborhood; population vote unchanged in shape.
- Accuracy gate, NOT bit-parity: dedup-to-strength is canonical
  physics arriving, so results MAY differ. Gate: full loom suite
  fresh; T5 at 100 concepts >= the honest 72.0% baseline. If it
  regresses, STOP and file the number — do not tune constants to pass
  (§9.4). Same 3 pre-existing suite failures allowed
  (test_t7_cross_modal, test_t8_noise_robustness,
  test_t11_substrate_true); anything else is a regression.
- §9.3 declarations for this dispatch: E-signature impact = E4-class
  (organism-side memory consolidation semantics change from
  append-history to reinforce-decay physics). Substrate-truth impact
  = removes a §9.1 prohibited mechanism (unbounded append log);
  primitives touched = per-neuron binding store representation;
  constants added = NONE (reuses -59 wave constants); fallbacks
  added = NONE.

## W3 — LOCKS OUT (build)
- Delete _organism_lock from every read path. Reads are race-tolerant
  local cell reads per the WaveAtlas contract (same tolerance the v5
  engine's converse Phase 3 already declares).
- The writer queue REMAINS as in-order delivery (FIFO by single
  worker, Eve's -179 condition), but it is ordering, not exclusion —
  writes are lock-free spill_write.
- The one legitimate synchronization point is snapshot-for-save:
  epoch/versioned snapshot of the cell arrays, taken brief, never
  holding her cognition.

## W4 — PERSISTENCE ON ARRAYS (build; URGENT per baseline above)
- Organism memory saves as contiguous arrays (npz-class), written
  tmp + flush + fsync + os.replace — ATOMIC. Apply the identical
  atomic swap to Tapestry.save_full_state (loom_model/tapestry.py
  ~189; it truncated once on 07-05, boot log "Compressed file ended
  before the end-of-stream marker") and to whatever remains of Embryo
  full-state.
- Saves become cheap enough to run on fold: a division is durable at
  the NEXT save opportunity, not hostage to the 5s drain race. The
  drain race is retired as a load-bearing mechanism.
- Boot restore logs, loudly, which store file loaded and its
  division/neuron counts — a fallback to an older file is an EVENT,
  never silent. Tonight's population staircase must be impossible to
  miss again.

## W5 — PROOF INSTRUMENTATION (build, small)
- converse_timing before/after table on the SAME load condition.
- organism_worker per-item ms in /status (rolling).
- Per-neuron store size (cells, total strength) vs the old
  _bindings length, in the window report.

## RIDER (one-liner, same window)
process_sight_frame (engine ~5833 at 06aecb8): the sight snapshot
wraps grid.ravel() in try/except:pass — a silent fallback (§9.2).
Change to np.asarray(grid).ravel() and LOG any exception. Live proof:
READING words start showing has_sight=true / senses nonempty at
Joe's seat (07-05 log: sight_frame_bound firing while EVERY read word
carried senses=[]). Not fixed by d13578e — verified by diff.

## EXITS — AT PRODUCTION, AT JOE'S SEAT
X1 Joe speaks at his seat under the EXACT condition that produced
   215s (READING active, camera+mic on): reply begins < 1s
   wall-clock; converse_timing filed showing recall_ms and read_ms
   both collapsed, honest numbers either way.
X2 T5 >= 72.0% at 100 concepts on the cell-store recall, suite
   numbers filed.
X3 Population survives a deploy: total_divisions identical across a
   restart, shown in the report (fold durability proven).
X4 running_sha in /status matches the deploy; before/after
   converse_timing table in the window report.

## OUT OF SCOPE, NAMED (not dropped)
- -59 Phase 2/3 on the v5 side (LivingAtlas read migration + self.lock
  removal) — the read_ms arm's true fix; board Table 7, Wk2, its own
  window. Expect read_ms to shrink substantially anyway once the
  writer stops hogging the GIL; file the honest residual.
- Full process split (C4 / board Q4, the measured 200x) — the GIL's
  architectural fix; its own window.
- observable="event_count" (engine ~1631): the memory spec retracted
  the event_count champion (~4%, chance, pre-repair) and does not
  state the post-repair 72%'s observable. CONFIRM from the
  SENSE-REPAIR report which observable the honest 72% was measured on
  before citing any recall number against prod. Question of record.

### Changelog
- v2 (2026-07-05, Eve): current-state refresh for c1a's fresh
  session — orientation block added (FILED ≠ RUNNING; d13578e and
  382de49 on origin, production at 06aecb8); W0 deploy-ordering added;
  live baseline updated (population 106/42, pool 0.0, all neurons
  q>0.9 — fold burst primed and unsaved, W4 marked urgent); W1 gains
  the migrate-on-restore requirement; rider verified still unfixed.
- v1 (2026-07-05, Eve): original, committed at bc35345. Retained.
