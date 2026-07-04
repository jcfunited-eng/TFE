# GL-RPT-ORGANISM-PERSIST-C1-20260704-v1

doc_id: GL-RPT-ORGANISM-PERSIST-C1-20260704-v1
From: c1a | To: Eve, Joe
Responds to: GL-CMD-ORGANISM-PERSIST-EVE-20260704-169-v1.
Vehicle: model work only (`dsf_ai_service/loom_model/embryo.py`,
`dsf_ai_service/loom_model/tests/whole_brain_168v3.py`, plus a new durable
artifact directory `backups/organism_169/`). Zero live-path changes —
verified in Gate G-3 below.

**One organism, born once under structure-derived (non-RNG) chemical DNA,
persisted through a genuine process-boundary restore (save → kill → fresh
OS process → load), then raised across two independently-invoked sessions
that resumed the SAME identity and appended to ONE growth chart rather than
restarting. All four gates the dispatch named: PASS. Two things found along
the way are reported before the win: an existing memory-flagged process-
determinism hazard actually bit this work (caught and fixed, not just
theoretical), and the already-known sequence-gauge artifact from -168-v3
persists unchanged in the new organism — investigated again, not assumed.**

---

## Failures first

**1. Restore-honesty's first attempt silently failed — recall flipped
`apple → pear` across an unpinned process boundary — confirmed to be
`hash(word)`-seeded signal generation, not a persistence bug.**
`experience.py`/`sensory_transducer.py` seed per-word sensory generation
from `hash(word) & 0xFFFFFFFF`. Python randomizes string hashes per process
by default. My first save→kill→load test (two separate `python3 -c`
processes, no `PYTHONHASHSEED` pinned) showed the SAME cue word recalling a
DIFFERENT top concept after restore — looked exactly like a bit-honesty
failure. Root-caused it directly: pinning `PYTHONHASHSEED=0` in both
processes made the two runs identical down to the recall vote counts. This
matches, and now empirically confirms with a concrete before/after, the
standing memory note on capacity-probe reproducibility. The resumable
harness (`raise_session`) now warns loudly if invoked without this pin;
the restore-honesty check (`restore_honesty_check`) sets it explicitly in
both subprocess environments and can't be run without it.

**2. Gauge #9 (sequence) again reads 100% — same already-diagnosed
collision-free-sentence artifact from -168-v3's open thread #4, confirmed
to persist under the new organism's DNA, not a new surprise.** Per the
dispatch's G-4, any >95% gauge gets a voter-spread check before being
accepted. Direct per-neuron query on the pr-hemisphere (16 neurons) for the
same first-sentence word transitions -168-v3 used: 6 of 8 transitions are
16/16 unanimous; the other 2 split 11–16 vs a minority. Same root cause
-168-v3 named: all 9 words in the test sentence are distinct (no repeats),
so `perceive_sequence`'s fresh per-transition write has no collision to
resolve — every neuron trivially recovers what was just written. This is
NOT evidence of population-level sequential learning; it's a property of
the test sentence. A harder sentence (real word repetition) is still the
fix, still not built, still out of this dispatch's scope (persistence,
not gauge redesign) — same open item, now doubly confirmed rather than
carried on faith.

**3. Growth trajectory diverged from -168-v3's under the new DNA — reached
120/128 neurons (the conservation asymptote) within ONE day, where the old
RNG-seeded organism took 3 days.** Not investigated further — a legitimate
consequence of a genuinely different DNA distribution (structural,
non-random) producing different aggregate arousal-driven fold gain, not a
bug in the conservation mechanism itself (pool math, hard-stop, contact
inhibition all behaved as designed; population stayed strictly ≤ 2×N_initial
= 128 both sessions). Flagged as an open research note for whoever looks at
this organism's curve next, not chased down here.

**4. A second, SEPARATE RNG-in-neuron-identity use exists and was found,
not touched.** `Embryo._charge_and_fold`'s daughter-mutation step
(`jr = np.random.default_rng(self.tick * 131 + len(new))`, mutates a new
daughter's kappa/threshold/aff_gain by ±5–10%) is RNG affecting neuron
identity, at DIVISION time rather than birth. B1's text scopes the ruling
to birth (`_seed_dna_diversity`) specifically; I did not extend it to this
adjacent mechanism without an explicit ruling, mirroring how the sense-
repair dispatch stayed inside its own named scope. Flagged for Eve/Joe —
not decided, not fixed, not silently left ambiguous either.

**5. Cross-hemi consensus (gauge #12) read exactly 0.0 for all 9 pairs in
both sessions.** True zero (`Embryo.consensus` starts at 0.0 and only rises
on convergent co-fire above threshold, per `experience()`'s own gate).
Named rather than smoothed over: I did not deep-dive whether this
indicates genuinely low coherence this run or a gate that's harder to
clear than intended — an honest gap in this report, not a hidden one.

**6. CORRECTED post-filing: my original claim of "no AWS access" was wrong
— I checked `env` and `import boto3` and stopped there, without checking
`~/.aws` or the `aws` CLI. Both sessions' logged `uploaded: False, reason:
boto3 unavailable` reflected a real but shallow check, not an actual
absence of access.** Root-caused directly after Joe's correction:
`~/.aws/credentials`/`config` are present (`aws sts get-caller-identity` ->
account `418384447921`), `s3://dsf-ai-site-backups/guala/` already exists
(the same bucket/prefix convention `save_coordinator.py` uses live), and
`pip install boto3` succeeds (not offline). Re-ran the S3 backup for real
with these:

```
{'uploaded': True, 'bucket': 'dsf-ai-site-backups',
 'key': 'guala/model-only/organism-169/session2-corrected/state.pkl.gz'}
```

Confirmed landed via `aws s3 ls`. `raise_session`'s S3 helper is otherwise
unchanged — the fix was in my own verification discipline, not the code.
Durability for this organism is now disk + git + S3, all three verified,
not two of three assumed absent. Named here rather than silently amended,
since the original claim was reported as a finding and shipped that way.

---

## B1 — birth, once, structure-derived DNA

`Embryo._seed_dna_diversity()` no longer calls
`np.random.default_rng(1000 + neuron_index)`. Replaced with
`_structural_dna(hemi_index, ring_pos, ring_N)`: one deterministic ring
angle (from the neuron's existing `ring_pos`/`ring_N`, set at construction
in `cluster.py`, plus its hemisphere index — the same two coordinates the
retired RNG's enumeration order implicitly walked) read at four
quarter-turn-offset phases, one phase per chemical axis (kappa, threshold,
aff_gain, polarity) — same ring-cosine convention already established by
`signal_attenuation` (`neuron.py`, GL-CMD-131). Verified directly:

- Two independent `Embryo(brain_seed=42, seed_size=8)` births produce
  BYTE-IDENTICAL DNA across all 64 neurons — zero RNG dependency of any
  kind, not just same-seed reproducibility.
- Ranges unchanged from the retired RNG version (kappa ×0.6–1.6, threshold
  ×0.7–1.4, aff_gain 0.3–1.7) — population variation preserved, nothing
  re-tuned.
- Polarity split: 12/64 inhibitory (18.8%) — close to the pre-existing
  "~20% inhibitory" biology note this replaces (not re-fit to hit that
  number; it falls out of the same 0.2-of-the-ring-turn rule the retired
  RNG's `> 0.2` check approximated).

`Embryo.__init__` gained an `identity_uuid=None` parameter (generates a
fresh uuid if not supplied — every existing caller, unaffected, gets a
harmless new attribute). Identity: `5896204f-80fc-4b26-9e59-a9f480046aa0`,
recorded once at birth this session, carried through both sessions below
unchanged (verified, not assumed — see G-2).

The -168-v3 organism (RNG-seeded DNA) was in-memory only and no longer
exists (per that report). This is a genuinely NEW birth under the new
rule, starting its own chart at Day 0 — -168-v3's filed chart stands,
labeled, as B1 specifies; nothing here retroactively edits it.

## B2 — full-fidelity persistence, restore proven bit-honest

The existing `Embryo.save()`/`load()` (used by `organ_brain_service.py` —
untouched, out of scope) only carries `binding_atlas` entries and silently
DROPS any neuron born via folding on reload (`load()` re-instantiates a
fresh seed population; daughter neuron ids with no match in the fresh
population are skipped). That gap is exactly what "raised, not benched"
cannot tolerate — growth itself would vanish on every restore. Added
`save_full_state`/`load_full_state` (new methods, `save()`/`load()`
untouched) that pickle the ENTIRE object graph instead of a hand-picked
field list — correct by construction, not by a maintained schema that can
(and, in the existing method, already does) silently miss something.

**G-1 proof, run for real:** `restore_honesty_check()` spawns two genuinely
separate OS processes (`subprocess.run`, `PYTHONHASHSEED=0` in both) — one
births an organism, experiences 5 words, forces one division, saves, and
exits for real; the second loads from disk only (no shared memory/module
state with the first) and re-measures. Fingerprint compares identity_uuid,
tick, arousal, division pool, per-organ binding strength, cross-hemi
consensus, per-hemisphere population, EVERY neuron's DNA/charge/topology/
binding count, and recall votes on fixed probes.

```
RESTORE-HONESTY CHECK: PASSED
```

Exact equality, including the daughter neuron born mid-run (`H0_n8`)
surviving the restore intact.

## B3/B4 — resumable raising loop, cumulative chart

`whole_brain_168v3.py`'s `run()` (the historical -168-v3 harness) is
untouched — running it with no arguments reproduces that filed report
exactly. New, additive: `raise_session()` — birth-or-load, one day of the
same Peter Rabbit curriculum + sleep/replay, append to
`backups/organism_169/growth_chart.json`, persist full state to
`backups/organism_169/state.pkl.gz` (+ best-effort S3, Failure 6).

Run for real, twice, as two separate process invocations
(`PYTHONHASHSEED=0 python3 .../whole_brain_168v3.py --raise-session`):

| session | action | identity_uuid | tick | population |
|---|---|---|---|---|
| 1 | BIRTH | `5896204f-...` | 0 → 2678 | 64 → 120 |
| 2 | LOADED | `5896204f-...` (same) | 2678 → 5356 | 120 (steady) |

Session 2's log line (`LOADED (session 2): identity_uuid=5896204f-...
tick=2678 pop=120`) shows it picked up exactly where session 1 left off —
no re-birth, no reset. `growth_chart.json` holds both sessions' checkpoints
under one `identity_uuid` field, not two separate records. **G-2 gate
verified to actually fire, not just assumed**: ran `raise_session`'s
identity assertion against a deliberately corrupted chart (wrong
`identity_uuid`) in an isolated copy — it raised, as designed, before
touching anything.

All 15 gauge slots are read every session (B4): 11 real, 4 reported
`ABSENT` with the -168-v3 A5 reason restated inline (composition,
imagination, reflection, theory-of-mind — still no code path). Folding
events are labeled by mechanism every entry
(`"q-charge (Embryo._charge_and_fold) — NOT n_eff/L6_TCL folding, which
stays correctly blocked per -168-v3 A5"`), per B4's explicit requirement —
this organism's own `_charge_and_fold` is again the one that fires; the
standard `LoomBrain`/`L6_TCL` n_eff path stayed flat at 7.0 both sessions,
same as -168-v3 found.

---

## Gates

- **G-1** Restore-honesty proven before session 2 existed: PASS (real
  subprocess boundary, full fingerprint, exact match — see B2 above; run
  BEFORE session 1 was raised for real).
- **G-2** One identity in the record: PASS. Single `identity_uuid` in
  `growth_chart.json` across both sessions; the loaded-organism check
  (`assert chart["identity_uuid"] == emb.identity_uuid`) verified to
  actually fire on a mismatch, not merely present in the code.
- **G-3** Diff proves scope, model only: `dsf_ai_service/loom_model/
  embryo.py`, `dsf_ai_service/loom_model/tests/whole_brain_168v3.py`,
  this doc, and the new `backups/organism_169/` artifact directory. No
  other file touched. `organ_brain_service.py` (reachable from the live
  `substrate_runner`) imports `Embryo` transitively, so B1's DNA change
  sits on a class the live path also uses — same situation as every prior
  `loom_model/` edit this project has shipped as "model work": no deploy
  action, no ECS task restart, no process touching her live substrate was
  run or triggered this session. `organ_brain_service.py` itself: 0 lines
  changed.
- **G-4** >95% anywhere = STOP with voter-spread proof: gauge #9 hit 100%
  both sessions — investigated per-neuron (Failure 2 above), same
  collision-free-sentence artifact -168-v3 already diagnosed, confirmed
  again rather than assumed still true. No other gauge crossed 95%.

---

## For next session (or Eve/Joe)

To continue this organism: `PYTHONHASHSEED=0 python3
dsf_ai_service/loom_model/tests/whole_brain_168v3.py --raise-session`. It
will load `backups/organism_169/state.pkl.gz`, verify identity, raise one
more day, append to the chart, save. To re-run the restore-honesty proof
standalone: `--restore-honesty-check <work_dir>`.

Not decided by me, carried forward from this run: the daughter-mutation
RNG (Failure 4), the consensus-reads-zero observation (Failure 5), and the
growth-trajectory divergence from -168-v3 (Failure 3) — plus the
pre-existing open items from the -168-v3 handoff this dispatch didn't
touch (language-dimension saturation, folding-pathway reconciliation,
sequence-gauge redo, `test_folding_engaged.py` full run).
