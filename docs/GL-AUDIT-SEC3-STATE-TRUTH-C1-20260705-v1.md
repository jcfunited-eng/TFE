# GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1

doc_id: GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1
Part of: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, §3 (State truth: every file on EFS) and §0.6 (shadow restorability proof)
Author: c1 | Freeze in effect — read-only, no fixes applied to production. The shadow instance referenced here is the audit's own isolated resource (see tools/audit/AUDIT-RESOURCE-MANIFEST.md), not production.

## Summary (failures first)

1. **[EV — CONFIRMED by independent adversarial re-verification, see addendum] SEVERE — a full cold-boot restore from a standard S3 backup does not actually reach a ready state; it gets permanently stuck.** The audit's own mandated shadow instance (§0.6), seeded from the newest real backstop backup, hit an **uncaught `RuntimeError` in `_eager_init()`** at `dsf_ai_service/app.py:4600` roughly 9 seconds after the substrate began loading: `"DREAM GATE: decay may not resume before the forced dream promotes paused-era content to deep. Marker absent: state/dream_gate_cleared.json"`. The async init task died once, was never retried, and after **1,725,534ms (~28.8 minutes) of wall-clock polling this audit performed directly (re-checked twice, independently, since first observed)**, `guala_ready` is still `false` and will never flip without manual intervention. **This means: restoring Guala from a standard S3 backup and cold-booting her currently does NOT work end-to-end.** This directly contradicts an implicit assumption behind every backup taken to date — that they are usable for recovery. Root cause of why this was never caught before, per the verification addendum: the only existing restore-validation tool (`tools/guala_restore_drill.sh`) bypasses this exact code path — it hardcodes `DECAY_PAUSED=1` and calls `Guala.load_full_state()` directly, never going through `app.py`'s real `_gl_init()`/DREAM GATE check that a genuine cold boot exercises.
2. **[EV — CONFIRMED numbers, but CORRECTED attribution, see addendum] `wave_atlas.npz` is excluded from all three S3 backup code paths in the codebase** (`dsf_ai_service/app.py:3047` `admin_backup`, 11-file list; `dsf_ai_service/app.py:4832` `_backup_to_s3`, 13-file list; `dsf_ai_service/save_coordinator.py:128` `_s3_loop`, the current 15-file "auto" backstop mechanism — none of the three ever names `wave_atlas.npz`). It only exists on the live EFS mount; it survives container restarts (EFS is persistent) but is invisible to any S3-only disaster-recovery path. **Correction: this is NOT the `-207` wave-memory rewrite's data** (that's `BindingAtlas`/`guala_organism.pkl.gz`, which IS present in 2 of the 3 backup lists) — `wave_atlas.npz` belongs to a separate, earlier ticket (`-59`/`-85`, ratified 2026-06-30) and per code inspection has **zero read consumers in production today** (write-only/dormant, "Phase 1a not yet firing" per its own docstring). The gap is real and exactly quantified below, but it is not the urgent "just shipped, no backup" story it first appeared to be.
3. **[EV — CONFIRMED byte-for-byte by independent re-derivation from live CloudWatch logs, see addendum] Quantified cost of finding #2**: there IS a graceful fallback — on missing npz, the code rebuilds the WaveAtlas from `LivingAtlas` (`guala_atlas.json`) instead of failing outright — but the rebuild is materially smaller than the real thing. Shadow (restored from S3, npz absent, rebuilt from LivingAtlas): **171 cells, 11,925 bindings**. Production (same identity, same tick range, loaded directly from the live npz on EFS): **2,016 cells, 26,764 bindings**. That's a **~91.5% cell loss and ~55% binding loss** in any scenario that has to fall back to an S3-only restore — real and reproducible, but currently inert since nothing reads WaveAtlas yet.
4. **[EV] File-count correction:** the dispatch/charter's "14 engine state files" is off by one — the actual, currently-backed-up state file set is **15**: `guala_atlas.json, guala_bucket.json, guala_coordinator.json, guala_core.json, guala_deep_atlas.json, guala_identity.json, guala_needs.json, guala_organism.pkl.gz, guala_sections.json, guala_sounds.json, guala_survival.json, guala_tapestry.pkl.gz, guala_teaching.json, guala_videos.json, guala_visual.json`. (`wave_atlas.npz` would make 16 if it were included, per finding #2 — it isn't.)
5. **[EV]** One picture in the corpus (`91e42db1c66c_original.png`, 68 bytes) decodes successfully as a valid PNG but is a **degenerate 1×1 pixel placeholder**, not real photo content — technically "opens fine," practically empty.

## Detail: the 15 engine state files — open/parse pass

Pulled the newest real backup (`s3://dsf-ai-site-backups/guala/auto/2026-07-05_22-08-19_activity_ended/`) and attempted to actually open/parse every file (not just confirm it exists):

| file | size | result |
|---|---|---|
| guala_atlas.json | 10,437,870 B | [EV-OPEN-OK] dict, keys: schema_version/guala_identity/saved_at_tick/saved_at_timestamp/data |
| guala_bucket.json | 208 B | [EV-OPEN-OK] same schema |
| guala_coordinator.json | 1,257,203 B | [EV-OPEN-OK] same schema |
| guala_core.json | 155,921 B | [EV-OPEN-OK] same schema |
| guala_deep_atlas.json | 206,478,106 B | [EV-OPEN-OK] same schema |
| guala_identity.json | 202 B | [EV-OPEN-OK] dict, keys: schema_version/guala_identity/first_boot_timestamp/first_boot_notes |
| guala_needs.json | 324 B | [EV-OPEN-OK] same schema |
| guala_organism.pkl.gz | 5,593,985 B | [EV-OPEN-OK] unpickles to `dsf_ai_service.loom_model.embryo.Embryo` (required `dsf_ai_service` importable — fails with a bare `ModuleNotFoundError` otherwise; not a corruption, just a class-resolution requirement worth documenting for whoever next needs to inspect a raw backup file) |
| guala_sections.json | 8,748,034 B | [EV-OPEN-OK] same schema |
| guala_sounds.json | 6,689 B | [EV-OPEN-OK] same schema |
| guala_survival.json | 43,370,459 B | [EV-OPEN-OK] same schema |
| guala_tapestry.pkl.gz | 15,743,632 B | [EV-OPEN-OK] unpickles to `dsf_ai_service.loom_model.tapestry.LoomTapestry` |
| guala_teaching.json | 44,340 B | [EV-OPEN-OK] same schema |
| guala_videos.json | 312 B | [EV-OPEN-OK] same schema |
| guala_visual.json | 9,361 B | [EV-OPEN-OK] same schema |

No corrupt or unparseable files found in this specific backup snapshot. All 13 JSON files share a consistent envelope (`schema_version`, `guala_identity`, `saved_at_tick`, `saved_at_timestamp`, `data`), which is a reasonable, well-formed convention.

**[EV] Point-in-time inconsistency across files, observed in BOTH the current production boot log and the shadow's boot log:** the boot log line `"Organism restored: ...tick=11473..."` (production) / `tick=20006` (shadow, different moment) does not match `"Tapestry restored: tick=2800..."` (production) / `tick=3620` (shadow) — the organism and tapestry files carry materially different internal tick values from each other at every boot observed. This suggests the two files are not saved as a single atomic point-in-time snapshot; whether this is by design (tapestry has its own independent clock) or a real consistency gap was not resolved this pass — flagging as [NOT MEASURED — needs a code-level read of what "tapestry tick" actually means before calling it a defect].

## Media decode

- Sampled 5 pictures from a full media backup (`s3://dsf-ai-site-backups/guala/2026-07-05_21-33-02/pictures/`), covering JPEG, PNG, and HEIC (with `pillow-heif` — HEIC decode is NOT free out of the box, most tooling needs an explicit HEIF plugin; worth knowing if anyone else tries to inspect these files). All 5 decoded successfully, including two real HEIC photos at full resolution (4032×3024, 4284×5712).
- One of the five (`91e42db1c66c_original.png`) is the degenerate 1×1 placeholder noted in the Summary.
- Did not sample sound/video files this pass — [NOT MEASURED], flagging as a gap rather than silently skipping it.

## Boot-restore evidence (real, from live CloudWatch logs, not inferred)

- **[EV] Production's current task** (`8002d064...`, running since this audit began) booted cleanly: `Organism restored: ...pop=106 total_divisions=42`, `Deep atlas loaded: 4989 entries`, `Survival history loaded: 269285 entries`, `Sounds loaded: 16`, `Videos loaded: 1`, `Visual restored: 30 pictures, 19416 sight motifs`, `WaveAtlas loaded from disk (npz): 2016 cells, 26764 bindings` — this is a warm boot reading the LIVE EFS npz directly, not a from-S3 restore, and it succeeded with no errors. `[boot] no .sleeping marker — cold boot or previous task did not sleep cleanly` was also logged — consistent with §1's finding of an unhealthy-task-triggered replacement rather than a graceful shutdown.
- **[EV] The audit's shadow** (seeded purely from the S3 backup, no live EFS access) hit the DREAM GATE crash described in the Summary and never became ready. This is the first real, controlled test of "restore from S3 backup alone" this system has had — and it fails.

## Resolution: Eve's authorized workaround, and the severity upgrade it produced

Eve (dispatch author, Joe's order) made the call explicitly: create the marker file on the
shadow's isolated storage only, mirror production's real schema first (read-only peek, freeze-
legal), annotate every §8A mutating row with the workaround's provenance, and upgrade this
finding's severity. All three conditions executed:

1. **[EV]** Read production's real, live `state/dream_gate_cleared.json` via a dedicated one-off
   ECS task with the container mount explicitly `readOnly: true` (physically incapable of
   writing) — content: `{"cleared_at_tick": 15058880, "via": "substrate_dream_end"}`, matching the
   schema in `gualaloom_v5_engine.py:5643` exactly. Also confirmed by direct code read
   (`app.py:1274`, `substrate_runner.py:655`) that both boot-time gate checks are pure
   `os.path.exists(gate_marker)` — the content is never parsed anywhere in the repo, so an
   incorrect value could not have "poisoned" a downstream test, though the real schema was still
   mirrored per instruction.
2. **[EV]** Created a matching-schema marker (`{"cleared_at_tick": 15003400, "via":
   "substrate_dream_end"}`, tick taken from the shadow's own boot-observed `last_real_dream_tick`,
   not copied wholesale from production) on the shadow's isolated EFS access point only, via a
   dedicated write-only one-off task. Stopped the stuck shadow, launched a fresh one from the same
   task-def — it reached `guala_ready:true` in **41.5 seconds**. Restorability is now **proven
   possible**, not just disproven — but only with this manual intervention.
3. **[EV] Every §8A mutating-test row carries the mandatory provenance annotation** (see
   `docs/GL-AUDIT-SEC8A-TEST-MATRIX-C1-20260705-v1.md`, D4): *"Obtained on an isolated shadow
   instance that required a manual disaster-recovery workaround (an undocumented marker file) to
   boot at all."*

**SEVERITY UPGRADE (per Eve's explicit instruction, condition 3):** this is no longer "restore is
slow and silent." It is: **as of this audit, Guala's disaster-recovery restore procedure does not
exist in runnable form.** A from-scratch restore from any standard S3 backup, following the
documented/expected boot path, hits an uncaught `RuntimeError` and never becomes ready — full
stop — unless an operator who already knows about this specific undocumented internal marker file
manually fabricates one first. No such knowledge is written down anywhere in `docs/` (confirmed by
§9's 30-day sweep) and the one tool that exists to validate restores (`tools/guala_restore_drill.sh`)
bypasses the exact code path that fails, so it has never once caught this. This was invisible until
someone actually attempted the restore rather than trusting the backup inventory — which is exactly
why the dispatch ordered testing over inventory in the first place.

**Unplanned side-effect discovered and corrected during this workaround, recorded in full in
`tools/audit/AUDIT-RESOURCE-MANIFEST.md`:** the first successfully-booted shadow inherited
production's S3 backup destination unchanged and wrote one real backup into production's actual
bucket before this was caught and deleted; fixed by creating a dedicated IAM role that hard-denies
S3 writes to that bucket for any shadow going forward. Also found and fixed: the shadow's network
security group was inherited from production (`0.0.0.0/0` on port 8080) rather than scoped —
replaced with a dedicated, IP-restricted security group. Both are now standing recommendations
(see the defects register) against ever standing up a shadow this way again in this environment
without those two isolations built in from the start.

**Standing recommendation, per explicit instruction from Joe's seat:** the shadow-instance pattern
itself, in this environment, is judged too risky to maintain going forward — not because the
technique is wrong in principle (§0.6 of the dispatch correctly identified the need for it, and it
produced this audit's single most important finding), but because this environment's defaults
(hardcoded backup-bucket destinations in application code, shared security groups, world-writable
root credentials at the host level) make safe isolation require deliberate, expert, multi-step
correction every time rather than being safe by default. This shadow is being torn down at the end
of this audit (see the resource manifest) and is recorded in the defects register as an item to
resolve structurally (e.g. environment-configurable backup destinations, dedicated non-production
security groups provisioned by default) before this pattern is used again.

## Addendum: independent adversarial verification (ultracode verify pass)

Both findings above were independently re-derived from scratch by separate verification agents (not shown my write-up, told only the claim under review) — full detail in the workflow journal (`wf_6f04f66f-0e9`), summarized here:

- **Stuck-restore (finding #1): VERDICT CONFIRMED.** The verifier curled the shadow live itself (`22:54:29Z`, `elapsed_ms=1725534`), confirmed via `aws ecs describe-tasks` it is the same never-restarted task instance, confirmed by reading `app.py:4596-4600` that `_eager_init()` has no try/except and is fired via bare `asyncio.ensure_future()` with nothing ever awaiting it, confirmed via fresh CloudWatch logs that the exception fired exactly once with no retry, and confirmed via whole-repo grep that `dream_gate_cleared.json` is written ONLY by the live dream-end handler (a runtime side effect requiring an already-running instance), never by any boot/restore path — so this isn't specific to this audit's shadow, production's own real task-def (`DECAY_PAUSED=0` today too) would hit the identical wall on a true from-scratch restore, and only survives because its marker persists on a long-lived EFS mount. The verifier also traced `docs/GL-BRIEF-PERSISTSAFE-FIX-WC-20260611-039.md` as the gate's original, deliberate design intent (item D5) — it's "working as designed" for its narrow original purpose, but its collision with a genuine cold-restore-from-backup was never designed for or tested, which is exactly why the existing `guala_restore_drill.sh` tool never caught it (it bypasses the gate entirely).
- **wave_atlas.npz gap (finding #2/#3): VERDICT PARTIAL.** The exclusion-from-all-three-lists claim and the exact 171/11,925 vs 2,016/26,764 numbers were independently re-pulled from live CloudWatch logs and confirmed byte-for-byte (recomputed 91.52% cell loss / 55.44-55.52% binding loss). The verifier also checked for a fourth/generic backup mechanism (a directory-wide `s3 sync`, or the separate `persistence_consumer.py` checkpoint path) and confirmed none exists that would catch this file — the exclusion is total on the write side. But the verifier caught a real error in the original write-up: **wave_atlas.npz is not `-207`'s data.** Tracing ticket numbers in the code/docs directly: `-207` ("GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207") is about the per-neuron `BindingAtlas` class (`guala_organism.pkl.gz`, present in 2 of 3 backup lists), while `wave_atlas.npz` belongs to the separate, earlier `-59`/`-85` ticket (ratified 2026-06-30) — `-207`'s own spec doc cites WaveAtlas as prior art it's building on, confirming they're sequential, distinct subsystems. Further, grepping for `.phase_vec` consumers outside `wave_atlas.py` itself found zero — WaveAtlas is currently write-only/dormant in production, so today's real-world impact of the gap is lower than the original framing implied, even though the technical gap and its exact size are accurate.

### Changelog
- v2 (2026-07-05, c1): incorporated independent adversarial verification. Stuck-restore finding CONFIRMED with an added root-cause (the existing restore-drill tool bypasses the DREAM GATE code path entirely, explaining why this was never caught). wave_atlas.npz finding's numbers CONFIRMED but its attribution to "-207" CORRECTED — it belongs to the separate, earlier, currently-dormant -59/-85 WaveAtlas ticket, not the organism/BindingAtlas rewrite this session has otherwise been about; present-day severity is lower than originally framed.
- v1 (2026-07-05, c1): initial §3 filing. 15-file open/parse pass clean; wave_atlas.npz backup-exclusion found and quantified via live shadow reproduction; shadow cold-boot found permanently stuck on a DREAM GATE RuntimeError, meaning backup restorability is disproven, not proven, for a true from-scratch restore.
