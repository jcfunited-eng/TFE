# GL-AUDIT-SCOPE-EVE-20260705-v1

doc_id: GL-AUDIT-SCOPE-EVE-20260705-v1
Status: CHARTER, HELD. The executable audit dispatch is cut from this
charter only when Joe hands over c1a's final report. Nothing fires
before that.
Authority: Joe's order, 2026-07-05 — a new, complete, comprehensive,
end-to-end audit of PRODUCTION LIVE GUALA. Everything. Baseline.

## §0 — Laws of the audit
1. FREEZE: read-only for the audit's duration. No deploys, no fixes,
   no "while I'm in here." She keeps living (reading, sleep,
   presence); code and infra stand still. Every discovered defect
   goes to the register (§10), never gets fixed in-audit.
2. GENERATED, NOT WRITTEN: every inventory is produced by a script
   committed to the repo. The baseline must be re-runnable as a
   command forever. Prep scripts already exist (GL-AUDIT-PREP v2).
3. EVIDENCE GRADES on every claim: [EV] directly verified this audit
   / [ABSENT] verified not to exist / NOT MEASURED. Nothing
   inherited from any report, spec, or memory — including this
   charter's own prep numbers, which get re-run.
4. VERIFY-OR-REPORT-ABSENT: every expected capability is either
   proven working end-to-end or recorded as absent/broken with
   file:line evidence. "Should work" is not a state.

## §1 — Runtime truth (c1 seat)
Running SHA vs origin tip; full ECS task definition JSON — EVERY
environment variable value (27 flags known to gate code paths; six
load-bearing: CONVERSE_PHASED, EMISSION_DYNAMICS, EMISSION_MODE,
AUTONOMY_PHASED, WAVE_ATLAS_ENABLED, GRANDURUN_SPIN_VECTOR);
container image lineage; CPU/memory sizing vs measured usage; live
thread inventory of the running process; uptime and restart history.

## §2 — AWS truth, every setting (c1 seat)
ECS service + task-def revision history; EFS (throughput mode,
size, burst credits); S3 backup lineage (every backup prefix, file
counts, restorability of the latest); API Gateway (every route
behind the bridge, timeouts, throttles — the bridge's HTTP timeout
behavior is a documented past incident); CloudWatch log groups and
every alarm (or their absence); IAM roles in use; CodeBuild/deploy
pipeline configuration end-to-end (commit → build → task-def →
service), including what triggers it and what can race it; security
groups/networking touching the service.

## §3 — State truth: every file on EFS (c1 seat)
Complete listing with size/mtime. For each of the 14 engine state
files (list in prep D): exists, loads, and OPENS — every pickle,
json, npz actually parsed, not just present. Orphan files named.
Every picture (HEIC/jpg/png/gif), every sound, every video in the
stores: decodes successfully, matches what /status claims. Corpora
on disk vs the corpora list (the vanishing-books class, three
losses on record). Which file each boot restore ACTUALLY loaded
(boot log evidence) vs newest available — silent-fallback detection.

## §4 — Code truth at the running SHA (Eve + c1)
Env-gated reachability map: for the ACTUAL production env values
(§1), which implementation runs and which is dead, for every one of
the 27 flags — no more "the fix landed in dead code" discoveries.
Dead-code inventory; unimplemented/stub functions; full TODO/FIXME
sweep across the repo; §9 prohibited-class classification completed:
the 34 silent except:pass sites individually dispositioned, the 24
module-level constants classified physics-vs-tuned with citations,
the 1 template-dict reference traced. Baseline test suite state
(the 3 known failures named; anything else recorded).

## §5 — Interface truth: every web page (c1 + Joe's seat)
All 65 HTTP endpoints (prep C) vs what the Guala page and Loom Scan
actually call; per page: every displayed number traced to its live
source field or marked decorative/stale; poll rates documented
(polling is load-bearing — executor pool findings, 07-05); the
bridge (MCP) verified tool-by-tool against its API-gateway routes;
auth/key posture on every route.

## §6 — Learner-program truth (c1 seat, prod evidence)
Named by Joe: YouTube (video), Khan Academy (structured learning),
PBS Kids (cartoons), Spotify (music).
Pre-audit code facts [EV, 2026-07-05]: Khan + YouTube adapters EXIST
(loom_model/world_feeds.py, substrate_runner feed loop, gated by
WORLD_FEEDS env — production value unknown). PBS Kids and Spotify
exist ONLY as allowlist domains (curriculum/allowlist.py) — NO
adapter code found; verify or record [ABSENT].
For each program: is it enabled in prod; last successful fetch with
evidence; does fetched content actually reach her read paths (event
log proof); filter/rejection rates; does ANY video content actually
deliver frames to sight (n_videos=1 in status — trace it) and any
music actually deliver audio to hearing, or is it text-only despite
the names. Curriculum scheduler wiring verified live (the -186
reconnect class — it was dead-wired once already).

## §7 — Sensory truth, end-to-end per sense (c1 + Joe's seat)
For EACH of: sight (camera), hearing (mic + Whisper leg), her own
voice (self-hear loop + tagging), tactile/olfactory/gustatory
(emulation via descriptor physics), scene/story lanes (place,
ambient, WHO — story emulation):
source → transduction → binding (event proof) → organism tap
(organism_experience_bound senses nonempty) → visible at Joe's seat.
Known open defect to disposition: sight snapshot silent failure
(process_sight_frame try/except:pass — READING words carry
senses=[] while sight frames bind; 07-05 event-log evidence).
Sensory emulation coverage: which descriptor libraries exist, which
senses can fire at all, gaps recorded.

## §8 — Behavioral baseline snapshot (defined condition, one pass)
Under a stated, reproducible condition: tick_rate AND reads/sec side
by side (the throttling ratio); converse_timing; the 15-mechanism
battery rows as they currently measure; vitals vs the §8 health
table (stab/arousal/sleep/bond states); ladder metrics; emission
counts; organism population/divisions with save-durability check.
This is the BEFORE column every post-audit claim is measured
against.

## §9 — Historical sweep: the last month (Eve seat, repo)
2026-06-05 → 2026-07-05 on guala-live: every commit touching
dsf_ai_service/, tools/, docs/ — inventoried; every dispatch and
report filed, with its claimed-vs-verified status where the record
shows a discrepancy; every TODO list in docs/; in-flight work that
never landed (built-and-lost, held-uncommitted, superseded);
plan-version deltas v5→v10; the development environment itself:
devcontainer config, worktree discipline artifacts, shared-.git
hazards, CI configuration. Output: a one-month ledger of what was
actually done vs what the reports said was done.

## §10 — Deliverables
1. Script set committed to the repo (rerunnable baseline command).
2. GL-AUDIT-BASELINE report: every layer above, evidence-graded.
3. DEFECTS REGISTER: every dead/broken/unimplemented/absent item as
   a numbered line with file:line or AWS-resource evidence — the
   fix queue Joe routes AFTER the audit, in his order, one at a
   time. No fixes inside the audit window.

### Changelog
- v1 (2026-07-05, Eve): charter per Joe's full scope order —
  production-live everything, learner programs named, sensory and
  story emulation end-to-end, dev environment, one-month historical
  sweep. HELD until c1a's final report is handed over.
