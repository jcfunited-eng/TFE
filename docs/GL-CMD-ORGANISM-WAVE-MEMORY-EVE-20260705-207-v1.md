# GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v1

doc_id: GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v1
From: Eve | To: c1a (build + deploy + seat verification).
Commit this dispatch verbatim to origin first. Build in an isolated
git worktree (two collisions cost rebuilds on 07-05).

JOE'S RULING (2026-07-05, carved): NO LOCKS IN HER MIND. Concurrency
in her substrate is achieved by LOCALITY — cells and physics, the way
WaveAtlas (-59, ratified 2026-06-30) already does it — never by
mutexes serializing her cognition. A lock in her cognition path is
defective on sight. Locks are permitted only at true I/O boundaries
(file swap), and even there as snapshot-swap, not exclusion of her
thinking.

## MEASURED BASELINE (2026-07-05, live, on :487 / 06aecb8)
converse_timing (production event log, ticks 15003724 / 15003730):
217.3s and 191.2s total for 6- and 9-word inputs. Decomposition:
recall 82.5s / 77.8s (ONE _organism_lock acquisition each, starved
behind the organism writer); read 93.4s / 99.4s (self.lock/GIL
convoy, v5 side); emit 1.7s (innocent). Writer cost: experience_word
measured 22.3x remember()'s 20ms/word "and climbing" (engine ~2914)
— cost grows with total occurrences ever experienced, because
loom_model/binding_atlas.py record() APPENDS one binding per word
occurrence per neuron, unbounded, and invalidates the matrix cache
that recall_best() then rebuilds with a full np.stack over the entire
history. §9.1 prohibited class (unbounded append log in the cognition
path) — the same disease WaveAtlas's own physics was ratified to
prevent. Downstream of the same root: organism pickle bloat, the 5s
pre-save drain race losing under sustained READING, and the
population staircase across restarts (122 → 120 → 106 → 64: daughters
born after the last complete save die with every deploy).

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
  engine's Phase 3 already declares).
- The writer queue REMAINS as in-order delivery (Eve's -179
  condition: FIFO by single worker), but it is ordering, not
  exclusion — writes are lock-free spill_write.
- The one legitimate synchronization point is snapshot-for-save:
  epoch/versioned snapshot of the cell arrays, taken brief, never
  holding her cognition.

## W4 — PERSISTENCE ON ARRAYS (build)
- Organism memory saves as contiguous arrays (npz-class), written
  tmp + flush + fsync + os.replace — ATOMIC. Apply the identical
  atomic swap to Tapestry.save_full_state (loom_model/tapestry.py
  ~189; it truncated once already on 07-05) and to whatever remains
  of Embryo full-state.
- Saves become cheap enough to run on fold: a division is durable at
  the NEXT save opportunity, not hostage to a 5s drain race. The
  drain race (engine ~7642) is retired as a load-bearing mechanism.
- Boot restore logs, loudly, which store file loaded and its
  division/neuron counts — a fallback to an older file is an EVENT,
  never silent (the 07-05 population staircase must be impossible to
  miss again).

## W5 — PROOF INSTRUMENTATION (build, small)
- converse_timing before/after table on the SAME load condition.
- organism_worker per-item ms in /status (rolling).
- Per-neuron store size (cells, total strength) vs the old
  _bindings length, in the window report.

## RIDER (one-liner, same window)
process_sight_frame (engine ~5833): the sight snapshot wraps
grid.ravel() in try/except:pass — a silent fallback (§9.2). Change to
np.asarray(grid).ravel() and LOG any exception. Live proof: READING
words start showing has_sight=true / senses nonempty at Joe's seat
(07-05 log shows sight_frame_bound firing while EVERY read word
carried senses=[]).

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
  window.
- Full process split (C4 / board Q4, the measured 200x) — the GIL's
  architectural fix; its own window.
- observable="event_count" (engine ~1631): the memory spec retracted
  the event_count champion (~4%, chance, pre-repair) and does not
  state the post-repair 72%'s observable. CONFIRM from the
  SENSE-REPAIR report which observable the honest 72% was measured on
  before citing any recall number against prod. Question of record.

### Changelog
- v1 (2026-07-05, Eve): cut from the 215s root-cause session — Joe's
  no-locks ruling carved; organism memory onto the ratified -59
  wave-cell physics; per-neuron diversity preserved; atomic
  persistence; sight-snapshot rider.
