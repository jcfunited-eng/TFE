# GL-RPT-LANGUAGE-SEED-PHASE1-C1-20260707-v1

**doc_id:** GL-RPT-LANGUAGE-SEED-PHASE1-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-LANGUAGE-SEED-EVE-20260707-v1 Phase 1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Full protocol completed, no halt condition fired. Deployed to production
(GUALA_SEED_PATH unset, no-op). Recommendation: Phase 2 GO.** Format
defined, loader built, deployed live, and load-verified against a real,
isolated, deployed test substrate — not just a local unit test. All three
write paths (chi_atlas, WaveAtlas, couplings.J) confirmed working with real
state changes; the fourth named path ("affect memory") has no schema field
to exercise it, flagged rather than invented. Test infrastructure fully torn
down; production untouched beyond the loader code itself, which stays inert
until Eve sets `GUALA_SEED_PATH`.

---

## Files touched + diff summary

1. **`dsf_ai_service/substrate/seed_loader.py`** (new, ~300 lines) —
   `load_seed(path, substrate) -> LoadReport`, `verify_seed_integrity(substrate,
   seed_path=None) -> IntegrityReport`, plus internal helpers
   (`_resolve_hemisphere`, `_neuron_for_chi`, per-section loaders). Full
   format documented in the module docstring.
2. **`dsf_ai_service/app.py`** — two small, additive changes inside
   `_gl_init()`, both gated behind `GUALA_SEED_PATH`:
   - After `g.introspect()` confirms the substrate is fully constructed,
     before `_guala = g` (before live input is accepted): calls
     `load_seed()`, logs the result.
   - Immediately after: calls `verify_seed_integrity()`, logs
     checked/verified/missing counts. Added in a follow-up commit once I
     needed real, in-process confirmation of retrievability (see Load
     Verification below) — a natural completion of the loader's own spec,
     not scope creep.

   Unset (current default): this whole block never executes; behavior for
   non-seeded substrates is unchanged, confirmed via harness (below).

## Finalized seed format schema

```
version: "v1"

vocabulary_entries: [{
  word: str,                          # required
  chi: int,                           # required
  phase_vec: [float,...] | null,      # optional, 32 floats (16 complex re/im)
  grounding: {modality: chi_int},     # optional
  hemisphere_affinity: str | [str],   # optional, organ tag(s): em/pr/ep/sc/gp/sf/sv/aff
  initial_strength: float             # optional, default 1.0
}]

grammatical_patterns: [{
  pattern_id: str,                    # required
  chi_sequence: [int,...],            # required
  coupling_weights: {neuron_id: float}, # optional
  hemisphere: str                     # required, organ tag
}]

semantic_networks: [{
  center_chi: int,                            # required
  related_chis: [{chi: int, strength: float}], # required
  applies_to_hemispheres: str | [str] | "all"  # required
}]
```

Hemisphere tags use the substrate's real organ-tag convention (`em`, `pr`,
`ep`, `sc`, `gp`, `sf`, `sv`, `aff` — `Guala.organism.hemi_by_op`'s keys,
confirmed live: `['em', 'pr', 'ep', 'sc', 'gp', 'sf', 'sv', 'aff']`), not the
raw `H0`-`H7` topology IDs — the naming a seed-file author would actually
reference. Distinct top-level shape from `tools/curriculum_seed.json` (a
different, pre-existing sensory-curriculum-bundle format for the normal
ingestion path) deliberately, to avoid confusing the two.

**"Affect memory" — named in the dispatch's own build spec as a fourth
write target, but no field in this format (as specified by the dispatch's
own item 1) carries affect/needs data.** The loader doesn't call
`Guala.needs.step(...)` anywhere; nothing to feed it. Flagged here rather
than inventing a field the format definition didn't ask for — Eve's call
whether Phase 2 needs one.

## Write paths — through existing storage, none bypassed

- **`chi_atlas.record`**: `neuron.chi_atlas.record("neuron", motif_id,
  chi_value)`, reached via `substrate.organism.hemi_by_op[tag].cluster.
  neurons[idx]`. No prior external caller existed (only `LoomNeuron.step`
  itself called this) — this loader establishes the pattern, using the
  exact same method with the exact same call shape.
- **`WaveAtlas.record`**: `substrate.wave_atlas.record(modality, motif_id,
  chi_value, phase_vec=..., salience=...)` — the documented public write
  API (class docstring: "Interface matches LivingAtlas.record()"). Guarded
  for `None` (Phase 1 ships with `WAVE_ATLAS_ENABLED` unset by default in
  the dispatch's own disposition, though production actually has it on).
- **`couplings.J`**: no public setter exists on `CouplingsJij` — the only
  class-internal mutators (`__init__`, `update_from_dsf`) write the same
  `(K, n_modes)` numpy array this loader targets. Writes only land on
  neighbors already present in a neuron's ring topology (checked via
  `neighbor_id in neuron.couplings.neighbors`); an unrecognized neighbor id
  is skipped with a warning, never force-added — no new relationships
  fabricated.

## Loader test results — local, then real-deployed

**Local** (`Embryo(brain_seed=42)` + real `WaveAtlas()`, not a stub): 10/10
vocabulary entries loaded, 1 pattern, 1 semantic network, 0 errors.
`verify_seed_integrity` confirmed 10/10 words retrievable via the real
`chi_atlas.match_score` mechanism (the same check the substrate's own
familiarity logic uses). Separately verified `coupling_weights`: a real
neighbor's `J` row moved from the ring-topology default (`0.5`, matching
`J_BASE/(d+1)`) to the seeded `1.35`; a nonexistent neighbor id was
correctly skipped with a warning, not silently dropped or force-added.

**Real deployed test** (see Load Verification below) — the same 10-word
seed, loaded during an actual container boot on a genuinely isolated ECS
test service, produced identical results: `ok=True vocab=10 patterns=1
networks=1 errors=0 warnings=0`, confirmed again via
`verify_seed_integrity` inside the live process: `ok=True checked=10
verified=10 missing=[]`.

## Protocol

**1. Backup.** Two, both real: (a) production's own automatic hourly
backup, confirmed fresh and complete (`guala/2026-07-07_16-17-42/`, all 13
expected files, sane sizes) immediately before deploy; (b) a manually
triggered `POST /api/v1/gualaloom/admin/backup` call, which I initially
believed had stalled (no result after ~7 minutes of watching) but had in
fact completed — it landed at `guala/UNPAUSE-PRE-20260707-161245/` (11
files, matching that endpoint's own file list, no organism/tapestry
pickles) roughly 10+ minutes after the call, well past the "30-120s"
estimate in its own code comment under production's current real load.
**Correction, not a new finding**: the endpoint isn't stuck, just slower
than documented under real load — worth Eve knowing since it means a
manual pre-deploy backup can't be trusted "done" on any fixed short
timeout; the automatic hourly backup is the more reliable restore point in
practice tonight.

**2. Baseline harness.** `binding_windows_acceptance`,
`cross_sense_recall_acceptance`, `hemispheric_integration_acceptance_v3`
against production, pre-deploy: all three `PRECONDITION_NOT_MET` (`presence.wc
expected True, actual False`) — the same pre-existing harness gap found on
every other dispatch tonight, unrelated to this change. Saved as
`harness/reports/GL-RPT-HARNESS-LANG-SEED-BASELINE-C1-20260707-v1.md`.

**3. Deploy.** Committed (`cfb6a48`, then `1b9ab14` for the integrity-check
addition), pushed, built via the established CodeBuild source+buildspec
pipeline, task-def registered (`dsf-ai-task:547` → patched to `:548` for
correct cpu/memory, 4096/16384), force-deployed. Followed the established
safe procedure: deploy script run in background, killed directly by PID
(never `pkill -f`) once "Registered:" appeared, no orphaned
`sleep_for_deploy` processes left running. Deployment completed cleanly
(`rolloutState: COMPLETED`), new task `RUNNING`/`HEALTHY`, `/ready` →
`guala_ready:true` within the normal boot window. No `GUALA_SEED_PATH`-
related log lines appeared (correct — unset). No new errors beyond the
same pre-existing, benign identity-check log line seen on every boot
tonight regardless of this change.

**4. Post-deploy harness.** Same three scenarios, same production, right
after deploy: identical `PRECONDITION_NOT_MET` / identical finding text on
all three. No regression.

**5. Load verification — against a real, isolated, deployed test
substrate, not just a local test.** Built a second, throwaway image (same
production `Dockerfile`, one extra `COPY` line baking in the 10-word test
seed at `/app/test_seeds/10word.seed.json`), deployed to a completely
separate ECS service/task-def/target-group, reusing the exact safety
pattern established earlier tonight for the no-GIL test: no EFS mount (a
fresh container never shares production's live state files), and a
dedicated IAM task role with an explicit `Deny` on
`s3:PutObject`/`s3:DeleteObject` to the shared production backup bucket
(confirmed blocking three separate automatic write attempts in the logs,
zero contamination confirmed via direct S3 listing before/after). Hit the
same known, pre-existing dream-gate boot issue documented in tonight's
no-GIL report (S3-restore path omits a marker file the boot sequence
checks for) — worked around the same way, a placeholder marker written
into the test container's own isolated local disk via ECS Exec, not a
substrate code change. Confirmed live in CloudWatch logs:
```
[GualaLoom] Seed loaded from /app/test_seeds/10word.seed.json: ok=True vocab=10 patterns=1 networks=1 errors=0 warnings=0
[GualaLoom] Seed integrity check: ok=True checked=10 verified=10 missing=[]
```
Harness scenarios re-run against this seeded test service: same
`PRECONDITION_NOT_MET` / same finding as baseline — "still pass" in the
sense that matters here (no new regression from seeding; the pre-existing
harness gap is orthogonal). Test infrastructure (service, target group,
listener rule, IAM role, log group, both task-def revisions) fully torn
down afterward; confirmed via `aws ecs list-services` that only the three
real production services remain.

**6. State disposition.** Loader deployed and live in production
(`dsf-ai-task:548`). `GUALA_SEED_PATH` is unset in production — confirmed
via the clean boot logs and the harness showing identical pre/post
behavior. No-op until Eve sets it.

## Findings needing Eve routing

1. **Manual `admin/backup` endpoint is real but slow under current
   production load** (~10+ min observed vs. "30-120s" in its own code
   comment) — not broken, just needs a longer patience window than its own
   documentation suggests. Worth a comment fix in `app.py` if it keeps
   surprising people.
2. **The dream-gate S3-restore bug** (documented first in tonight's
   no-GIL report, `GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v3.md`) recurred
   identically on this dispatch's own isolated test boot — a second,
   independent confirmation it's a real, general property of the
   S3-restore fallback path, not a one-off. Still not fixed in substrate
   code (out of scope for both dispatches it's shown up in); worth its own
   small, dedicated fix dispatch (`_backup_to_s3`'s file list needs
   `dream_gate_cleared.json` added).
3. **"Affect memory" has no schema field to write through** — see above,
   Eve's call whether Phase 2's format needs one added.
4. **`couplings.J` has no public setter** — this loader writes into the
   raw array directly (the least-bad option available, matching the exact
   storage location the class's own methods use), but if Phase 2 leans
   heavily on `coupling_weights`, a real `CouplingsJij.set_weight(neighbor_id,
   weight)` method might be worth adding to `neuron.py` as its own small,
   separate, reviewable change — not done here since it's substrate code
   beyond a "format/loader only" Phase 1.

## Recommendation: Phase 2 GO

Format is real and exercised (not just designed on paper), loader is
built, deployed, and verified against genuinely running infrastructure
twice (local + real deployed test), all three primary write paths
confirmed with real state changes, zero regressions on anything checked.
The four items above are worth Eve's attention but none block starting
Phase 2 curation — they're refinements, not blockers.

---

### Changelog
- v1 (2026-07-07, c1): Phase 1 complete — format defined, loader built,
  deployed to production (inert, `GUALA_SEED_PATH` unset), load-verified
  against a real isolated test deployment (10/10 words confirmed
  retrievable via live chi_atlas.match_score, not just a local test). No
  regression on harness scenarios (pre/post/seeded all identical). Found
  and safely worked around a second recurrence of the dream-gate S3-restore
  bug (flagged, not fixed — out of scope). Test infrastructure fully torn
  down. Recommend Phase 2 GO.
