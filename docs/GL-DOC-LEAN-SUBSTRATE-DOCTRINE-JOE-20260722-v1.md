# GL-DOC-LEAN-SUBSTRATE-DOCTRINE-JOE-20260722-v1

**Status:** RATIFIED by Joe, 2026-07-22 (verbal, this session). Standing project goal.
**Applies to:** the entire Guala project — substrate, services, storage, logs, deploys.

## The doctrine

The project must demonstrate a **fully lean, efficient, structurally sound architecture**:

1. **No runaway data.** Every store — in RAM, on EFS, in S3, in logs — has an explicit bound or an explicit decay law. Unbounded growth anywhere is a defect, regardless of whether it is "working."
2. **No unnecessary data.** Nothing is stored that the substrate's mechanisms do not actually consume. Diagnostic/telemetry data gets a retention limit. Dead stores, leftover copies, and debris are removed, not accumulated.
3. **Decay must actually decay.** Where a mechanism claims decay (working atlas, wave atlas, familiarity, dream-cycle trims), decay must be live-verified, not assumed. A decay law that never fires is a bound that doesn't exist.
4. **Leanness is part of the proof.** The demo story is deterministic structure versus data-hoarding ML. A substrate that learns in bounded space IS the pitch. Efficiency is not housekeeping — it is the thesis.

## Standing rules derived from prior rulings (now unified here)

- RAM-resident load-everything stores: condemned (Joe, 2026-07-16). Disk-resident lazy access is the mandate.
- Lifetime/append-forever ledgers: retired (2026-07-20). Fail closed on unbounded retention.
- Emission/causal provenance: bounded (Sol's branch, 2026-07-21).
- Every ship record must state the storage bound of anything new it persists. "Bounded by X, decays by Y" or it doesn't ship.
- Spec tension resolved: ArcLoom's "compress into quiescence, never delete" is honored **only within a bounded quiescent store**. Where compression and leanness conflict, leanness wins — bounded stores with pruning are the project's ruling, by Joe's authority.

## Known offenders at ratification (from GL-RPT-COMPLETE-PROJECT-AUDIT-C1-20260722-v1)

| Offender | Status |
|---|---|
| Dream-cycle RAM growth (+300–1240MB/cycle, grows with life) | root-caused 07-17, still unfixed; top lean-doctrine violation |
| CloudWatch logs: /ecs/dsf-ai ~49GB, /ecs/gualaloom-bridge ~7GB, codebuild ~13GB, never-expire + /health spam flooding | retention policies applied 2026-07-22 (30d, Guala groups); /health log spam still generated at source |
| generations/ crash-loop snapshot accumulation | pruning partial (age-guard only) |
| Organism worker: 193k+ dropped items | throughput waste, filed 07-19, unaddressed |
| WAL checkpoint streaming compaction | written+tested, uncommitted; live runs old non-streaming body |
| docs/binding_atlas_patched.py and similar leftover copies | debris, remove when convenient |
| Dead organ-brain polling (90s thread against removed container) | wasted cycles + fallback noise |

## Enforcement

- The three runaway alarms (guala-cpu / guala-memory / guala-efs-storage) stay armed permanently.
- Any audit finding of a new unbounded store is a defect report, not an observation.
