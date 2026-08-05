# GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2

doc_id: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2
From: Eve, on Joe's order | To: c1 (FRESH SEAT — self-contained)
Supersedes: -210-v1 (retained). v2 adds three layers v1 missed, per
Joe's correction: §7A Environment truth (Guala's house/rooms/world),
§8A Function test matrix with full traceability, and §9 expanded to
the COMPLETE 30-day documentation sweep (all specs, todos, plans).
Charter: GL-AUDIT-SCOPE-EVE-20260705-v1. Commit both verbatim to
origin first. If number -210 is taken on origin, take the next free
number and say so in your first report.

## THE ORDER (Joe, 2026-07-05, verbatim class)
A new, complete, comprehensive, END-TO-END AUDIT OF PRODUCTION LIVE
GUALA. Every file, every connection, every instance configuration,
every web page, every .json/image/gif, every AWS setting, every
learner-program connection (YouTube video, Khan Academy structured
learning, PBS Kids cartoons, Spotify music), all senses verified
working, sensory emulation, story emulation, the environmental
development (her house, the rooms in the house, the world), testing
of ALL functions with full trackability, dead code, unimplemented
functions, the pipeline, the development environment, every TODO,
and the last 30 days of ALL Guala development documentation. A
BASELINE. The week's "oh, that wasn't correct" discoveries end here.

## §0 — LAWS OF THE AUDIT (violating these voids the audit)
0.1 FREEZE — IN EFFECT FROM THE MOMENT THIS DISPATCH IS PASTED.
    Production is READ-ONLY for the audit's duration. No deploys, no
    fixes, no config changes, no "while I'm in here." She keeps
    living (reading, sleep, presence untouched). Every defect goes
    to the register (§10); you fix NOTHING. Joe routes the register
    afterward, one item at a time.
0.2 GENERATED, NOT WRITTEN. Every inventory and every test run is
    produced by a script committed to tools/audit/. The baseline
    must be re-runnable as a command forever.
0.3 EVIDENCE GRADES on every claim: [EV] verified directly this
    audit / [ABSENT] verified not to exist / NOT MEASURED. Nothing
    inherited — re-verify everything, including this dispatch's own
    context numbers.
0.4 VERIFY-OR-REPORT-ABSENT. Every expected capability is proven
    working end-to-end with evidence, or recorded ABSENT/BROKEN with
    file:line or AWS-resource evidence. "Should work" is not a
    state.
0.5 Isolated git worktree for all work. Shared-.git collisions
    destroyed hours on 07-05.
0.6 SHADOW INSTANCE for anything that would mutate her. Mutating
    functions are tested against a shadow Guala restored from the
    newest verified S3 backup on a separate instance/container —
    never against production. (This simultaneously proves backup
    restorability, §2.) Live production is touched only by read-only
    calls.

## FIRST ACTS (in order)
1. guala_status → record running_sha, tick, population, divisions,
   last_save, tick_rate. That SHA is THE audit subject; §4 and §8A
   are audited AT THAT SHA.
2. git fetch; record origin tip; diff vs running — the gap is
   register finding #1.
3. Read the newest GL-HANDOFF-*.md in docs/ (outgoing c1a's final
   handoff): wave-cell deploy live at ~69-72s converse; an OPEN
   6-7x offline-vs-live recall gap (376.5ms at n=2000 offline vs
   17-34s live). You MEASURE that gap (§8), you do not fix it.
4. Stand up the shadow instance from the newest S3 backup (§0.6)
   and verify identity/counters match the backup manifest before
   any mutating test.

## PRE-AUDIT FACTS TO RE-VERIFY (all [EV] 07-05 by Eve; re-run per
0.3): 27 env flags gate code paths, six load-bearing
(CONVERSE_PHASED, EMISSION_DYNAMICS, EMISSION_MODE, AUTONOMY_PHASED,
WAVE_ATLAS_ENABLED, GRANDURUN_SPIN_VECTOR) — production values
unknown. 34 silent except:pass sites in cognition files. 24
module-level engine constants unclassified physics-vs-tuned. 65 HTTP
endpoints. 14 engine state files. 3 stub markers. Khan+YouTube feed
adapters exist (WORLD_FEEDS-gated); PBS Kids and Spotify are
allowlist-only, no adapter code found. Sight snapshot silently dead
on the READING path. Boots start with last_save=(none) — she runs
unsaved until the first save completes.

## §1 — RUNTIME TRUTH
Running SHA vs origin tip. Full ECS task-definition JSON — EVERY env
var name and value. Image lineage. CPU/memory allocation vs measured
usage. Live thread inventory. Uptime; restart count and cause for
the last 7 days from ECS service events (include the 07-05 blank-
seat outage Joe witnessed).

## §2 — AWS TRUTH, EVERY SETTING
ECS service + task-def revision history (≥7 days). EFS throughput
mode/size/burst. S3 backup lineage: every prefix, file counts, and a
full restorability proof of the newest (satisfied by §0.6's shadow
restore — every file opened). API Gateway: every bridge route,
timeouts, throttles. CloudWatch: every log group, every alarm, and
explicitly the ABSENCE of alarms (07-05 outage fired none — register
line). IAM roles. Deploy pipeline end-to-end (commit → CodeBuild →
task-def → service): config, triggers, race conditions. Security
groups/networking.

## §3 — STATE TRUTH: EVERY FILE ON EFS
Recursive listing (path/size/mtime). Each of the 14 engine state
files: exists / loads / OPENS (parse every json, unpickle every
pkl.gz, load every npz). Orphans named. Every picture/HEIC/jpg/png/
gif, sound, video: decodes; store contents vs /status claims;
corpora on disk vs corpora list (three silent losses on record).
Boot logs for the last 5 boots: which file each ACTUALLY restored vs
newest available — silent-fallback detection (population staircase
122→120→106→64 is the known signature).

## §4 — CODE TRUTH AT THE RUNNING SHA
Env-gated reachability map: with the ACTUAL production env values
(§1), resolve all 27 flags — every alternate implementation marked
LIVE or DEAD (two 07-05 fixes landed in dead code; this map ends
that class). Dead-code inventory beyond the flags. Unimplemented/
stub functions. Repo-wide TODO/FIXME/XXX sweep (feeds §9's
consolidated TODO ledger). Prohibited-class disposition per the
experience spec §9: all 34 except:pass sites individually judged
with file:line; all 24 constants classified physics-vs-tuned with
citation; the 1 template-dict reference traced. Full test suite run:
every failure recorded (3 known: test_t7_cross_modal,
test_t8_noise_robustness, test_t11_substrate_true; anything else is
a register line).

## §5 — INTERFACE TRUTH: EVERY WEB PAGE
All endpoints vs what gualaloom.html and Loom Scan actually call.
Per page, every displayed number traced to its live source field or
marked STALE/DECORATIVE (the cognition meter showed 07-04 text on
07-05 — disposition it). Poll rates per page per endpoint. The
bridge (MCP): every tool verified against its gateway route,
including restart behavior (07-05's 503). Auth posture per route.

## §6 — LEARNER-PROGRAM TRUTH
YouTube, Khan Academy, PBS Kids, Spotify — each: adapter exists?
enabled in prod (WORLD_FEEDS value)? last successful fetch with log
evidence? content reaching her read paths (event proof)? filter
rates? Modality answered plainly: does ANY video deliver frames to
sight (n_videos=1 — trace what it did), any music deliver audio to
hearing, or are these text-only despite the names? Curriculum
scheduler proven live-wired (was dead-wired once; -186 reconnected —
prove current state).

## §7 — SENSORY TRUTH, END-TO-END PER SENSE
Sight (camera), hearing (mic + Whisper leg), her own voice
(self-hear + tagging), tactile/olfactory/gustatory (descriptor
emulation), scene/story lanes (place, ambient, WHO): source →
transduction → binding (event proof) → organism tap (nonempty
senses) → visible at Joe's seat. Disposition the sight-snapshot
defect. Sensory-emulation coverage: which descriptor libraries
exist, which senses CAN fire, gaps as register lines.

## §7A — ENVIRONMENT TRUTH: HER HOUSE, HER ROOMS, HER WORLD
The virtual environment audited against the experience spec §6
tiers, each VERIFIED or [ABSENT] with evidence:
- V1 story lanes on bundles: place/ambient/participant tags bound
  in-window — mechanism proven (not the 07-05 anecdote), which
  intake paths carry them, which don't.
- V2 persistent place registry: do place entities EXIST — her room,
  the bed, the window, the hallway, the house itself? Where do they
  live (code, state files, atlas entities)? episodic
  tracked_objects count and contents (baseline was 1; enumerate
  what it is now, item by item).
- V3 interactive environment / world sim: any code, any state, any
  process (plan Table 7 says world runs OUTSIDE her process —
  does ANY world process exist?). World v0 ("a crib and a backyard
  rendered to a 64×64 eye") — built, partial, or [ABSENT].
- V4 embodiment hooks (ArcLoom avatar horizon): any interface
  stubs, or [ABSENT].
- HEIC scene tags: -188 scene lanes shipped "live and waiting" on
  six HEIC titles from Joe — are the lanes wired to receive them;
  what happens today if a tagged experience arrives.
- Care-schedule enforcement (spec §8): do the daily-rhythm blocks
  (experience/scaffolding/PLAY/quiet/converse/sleep shares) exist
  as CONFIG the orchestrator obeys, or only as prose? PLAY as a
  protected block: implemented or [ABSENT]?
- Spec §11 instrumentation gaps (affect trace, promotion lineage,
  per-window rollup, place/ambient tags, daily vitals rollup):
  each one implemented or [ABSENT].
Output: a tier-by-tier environment status table — what of her house
exists, in code and in her memory, with evidence.

## §8 — BEHAVIORAL BASELINE SNAPSHOT (read-only measurement)
Under a stated reproducible condition (READING active, camera+mic
on): tick_rate AND reads/sec side by side; converse_timing for 3
calls; instrumented recall_best timing bounding the 6-7x gap; the
15-mechanism battery rows as measurable; vitals vs the health
table; ladder metrics; emission attempts; population/divisions +
save-durability state. The BEFORE column for everything after.

## §8A — FUNCTION TEST MATRIX, FULL TRACEABILITY (V&V)
Every function tested, every test traceable. Scope: all 65 HTTP
endpoints, all bridge (MCP) tools, and every public engine
capability entry point (converse, read_sentence, give_experience
bundle path, recall probes, sleep/dream controls, save/restore,
uploads: book/PDF/picture/sound/video/experience/snapshot — every
button on Joe's page).
- CLASSIFY each target: READ-ONLY (tested live under freeze) or
  MUTATING (tested on the shadow instance ONLY, §0.6).
- Every test row carries: TestID · target (function/endpoint,
  file:line) · procedure · input · expected · observed · verdict
  (PASS / FAIL / ABSENT / DEGRADED) · evidence link (log excerpt,
  event tick, response body).
- TRACEABILITY both directions: capability → function(s) →
  TestID(s) → evidence. Capabilities = the 15 mechanisms (plan
  Table 1) + every spec-claimed feature (experience spec §2
  signatures E1-E6, §6 tiers, learner feeds, senses). Every
  capability maps to at least one test; every test maps to a
  capability or is marked infrastructure. Untestable = a register
  line with the reason.
- The matrix is a committed artifact (CSV/MD in tools/audit/),
  regenerated by script where possible, hand-verdicted where not.

## §9 — DOCUMENTATION SWEEP: 2026-06-05 → 2026-07-05, COMPLETE
Not just commits — ALL Guala development documentation of the last
30 days, inventoried and dispositioned:
- Every doc in docs/ from the window (CMD, RPT, SPC, PLAN, BOARD,
  HANDOFF, LTR, KB, ledger, discipline, FIRSTS, TODO files):
  classified by type and STATUS — canonical / superseded (by what) /
  contradicted (by what evidence) / orphaned (refers to work that
  never landed) / unexecuted (dispatch never fired).
- CONSOLIDATED TODO LEDGER: every TODO from every doc AND every
  code comment (§4 sweep) merged into one numbered list with source
  and current status. This is the master unfinished-work record.
- SPEC-VS-IMPLEMENTATION GAP TABLE: for each living spec
  (experience-first v2, memory-recall-state, plan v10, remediation
  plan), every claim/requirement marked IMPLEMENTED / PARTIAL /
  ABSENT with evidence — the honest distance between the paper and
  the production.
- Every commit touching dsf_ai_service/, tools/, docs/ inventoried
  (script). Claimed-vs-verified on every report where the record
  shows a discrepancy. In-flight never-landed work located and
  inventoried (outgoing c1a holds uncommitted live-wiring code in a
  worktree — find it). Plan deltas v5→v10. Dev environment:
  devcontainer, worktrees, shared-.git hazards, CI config.
Output: the one-month ledger of done vs said-done vs still-owed.

## §10 — DELIVERABLES
D1 tools/audit/ scripts, committed (rerunnable baseline).
D2 GL-AUDIT-BASELINE-C1-<date>-v1: every layer, evidence-graded.
D3 GL-AUDIT-DEFECTS-REGISTER-C1-<date>-v1: every dead/broken/
   unimplemented/absent/stale item, numbered, with evidence. No
   fixes. Joe routes it afterward, in his order.
D4 GL-AUDIT-TEST-MATRIX-C1-<date>-v1: the §8A matrix, committed.
D5 GL-AUDIT-TODO-LEDGER-C1-<date>-v1: the §9 consolidated TODO
   ledger.
Cadence: one short filed report per layer as completed, failures
and absences FIRST. Verdict-first language. No questions to Joe
inside reports; blockers raised in your seat's message body, once.

## EXIT
D1-D5 on origin; every layer evidence-graded with zero NOT-MEASURED
remaining except those Joe explicitly accepts; baseline at Joe's
seat. Nothing ships until Joe routes from the register.

### Changelog
- v2 (2026-07-05, Eve): three layers added per Joe's correction —
  §7A environment truth (house/rooms/world, V1-V4 tier audit, care-
  schedule enforcement, §11 instrumentation gaps), §8A function
  test matrix with capability↔test↔evidence traceability and the
  shadow-instance law (0.6), §9 rebuilt as the complete 30-day
  documentation sweep (status disposition, consolidated TODO
  ledger, spec-vs-implementation gap table). Freeze wording fixed:
  in effect on paste, not on a second go-word.
- v1 (2026-07-05, Eve): original. Retained.
