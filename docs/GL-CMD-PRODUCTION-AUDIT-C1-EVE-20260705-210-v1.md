# GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v1

doc_id: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v1
From: Eve, on Joe's order | To: c1 (FRESH SEAT — this dispatch is
self-contained; you need no prior session context)
Charter: GL-AUDIT-SCOPE-EVE-20260705-v1 (this dispatch is its
executable form; commit both verbatim to origin first).
Numbers -208/-209 are taken by prior seats' work; this window is
-210. If -210 is also taken on origin, take the next free number and
say so in your first report.

## THE ORDER (Joe, 2026-07-05, verbatim class)
A new, complete, comprehensive, END-TO-END AUDIT OF PRODUCTION LIVE
GUALA. Every file, every connection, every instance configuration,
every web page, every .json/image/gif, every AWS setting, every
learner-program connection (YouTube video, Khan Academy structured
learning, PBS Kids cartoons, Spotify music), all senses verified
working, sensory emulation, story emulation, dead code, unimplemented
functions, the pipeline, the development environment, every TODO,
every file going back the last month. A BASELINE. The week's repeated
"oh, that wasn't correct" discoveries end here.

## §0 — LAWS OF THE AUDIT (violating these voids the audit)
0.1 FREEZE. Production is READ-ONLY for the audit's duration. No
    deploys, no fixes, no config changes, no "while I'm in here."
    She keeps living (reading, sleep, presence run untouched). Every
    defect you find goes to the register (§10) — you fix NOTHING.
    The register is Joe's fix queue; he routes it after, one item at
    a time.
0.2 GENERATED, NOT WRITTEN. Every inventory is produced by a script
    you commit to the repo (tools/audit/). The baseline must be
    re-runnable as a command forever. Scripts are read-only by
    construction.
0.3 EVIDENCE GRADES on every claim: [EV] you verified it directly
    this audit / [ABSENT] you verified it does not exist / NOT
    MEASURED. Nothing inherited from any report, handoff, spec, or
    this dispatch's own context numbers — re-verify everything,
    including the pre-audit findings listed below.
0.4 VERIFY-OR-REPORT-ABSENT. Every expected capability is either
    proven working end-to-end with evidence, or recorded ABSENT/
    BROKEN with file:line or AWS-resource evidence. "Should work"
    is not a state.
0.5 Work in an isolated git worktree. Two shared-.git collisions
    destroyed hours of work on 07-05.

## FIRST ACTS (in order, before anything else)
1. guala_status → record running_sha, tick, population, divisions,
   last_save, tick_rate. This SHA is THE audit subject. Everything
   in §4 is audited AT THIS SHA.
2. git fetch; record origin/guala-live tip. Diff tip vs running —
   the gap is finding #1 of the register.
3. Read the newest GL-HANDOFF-*.md in docs/ (the outgoing c1a wrote
   one at session end) — it holds the wave-cell deploy state and an
   OPEN, UNEXPLAINED 6-7x gap: offline recall at n=2000 measured
   376.5ms; live recall measures 17-34s. That gap is NOT yours to
   fix. It IS yours to measure (§8) — the instrumented recall_best
   timing the outgoing seat proposed belongs in the baseline
   snapshot as read-only measurement.
4. Confirm with Joe that the freeze is active before your first
   inventory run.

## PRE-AUDIT FACTS TO RE-VERIFY (context, all graded [EV] on 07-05
by Eve's seat, all to be re-run per 0.3)
27 env flags gate code paths; six load-bearing (CONVERSE_PHASED,
EMISSION_DYNAMICS, EMISSION_MODE, AUTONOMY_PHASED,
WAVE_ATLAS_ENABLED, GRANDURUN_SPIN_VECTOR) — production VALUES
unknown. 34 silent except:pass sites in cognition-path files. 24
module-level numeric constants in the engine unclassified
physics-vs-tuned. 65 HTTP endpoints in app.py. 14 engine state
files in the save/load path. 3 stub markers. Khan+YouTube feed
adapters EXIST in code (world_feeds.py, WORLD_FEEDS-gated); PBS
Kids and Spotify are allowlist-only — NO adapter code found. Sight
snapshot silently dead on the READING path (process_sight_frame
try/except:pass; event-log proof 07-05). Boot-time state: process
has started with last_save=(none) — she runs unsaved until the
first save completes each boot.

## §1 — RUNTIME TRUTH
Running SHA vs origin tip. Full ECS task-definition JSON — EVERY
environment variable name and value. Container image lineage.
CPU/memory allocation vs measured usage. Live thread inventory of
the running process (name, state). Uptime; restart count and causes
for the last 7 days from ECS service events (include today's
restart Joe witnessed with a blank seat page).

## §2 — AWS TRUTH, EVERY SETTING
ECS service config + task-def revision history (7 days minimum).
EFS: throughput mode, size, burst state. S3: every backup prefix in
the lineage, file counts, and a RESTORABILITY CHECK of the newest
(open every file in it). API Gateway: every route behind the bridge,
timeout and throttle values. CloudWatch: every log group, every
alarm — and explicitly, the ABSENCE of alarms (today's outage fired
none; that absence is a register line). IAM roles in use. The full
deploy pipeline (commit → CodeBuild → task-def → service): config,
triggers, and what can race it. Security groups / networking
touching the service.

## §3 — STATE TRUTH: EVERY FILE ON EFS
Complete recursive listing: path, size, mtime. For each of the 14
engine state files: exists / loads / OPENS (parse every json,
unpickle every pkl.gz, load every npz — a file that exists but does
not open is a register line; one tapestry truncation is already on
record). Orphan files named. Every picture/HEIC/jpg/png/gif, every
sound, every video: decodes successfully; store contents vs what
/status reports (three silent corpus losses are on record —
enumerate corpora on disk vs the corpora list). Boot-log evidence
of which file each of the last 5 boots ACTUALLY restored vs the
newest available at that moment — silent-fallback detection (the
population staircase 122→120→106→64 across 07-05 restarts is the
known signature).

## §4 — CODE TRUTH AT THE RUNNING SHA
Env-gated reachability map: for the ACTUAL production env values
from §1, resolve every one of the 27 flags to the code path it
selects — every alternate implementation marked LIVE or DEAD. (Two
07-05 fixes landed in dead code; this map ends that class.)
Dead-code inventory beyond the flag map. Unimplemented/stub
functions. Full TODO/FIXME/XXX sweep, repo-wide. §9-of-the-
experience-spec prohibited-class disposition: each of the 34
except:pass sites individually judged (masks-failure vs benign,
with file:line); each of the 24 constants classified physics-vs-
tuned with citation; the 1 template-dict reference traced.
Baseline test suite run: record every failure (3 are known:
test_t7_cross_modal, test_t8_noise_robustness,
test_t11_substrate_true — anything else is a register line).

## §5 — INTERFACE TRUTH: EVERY WEB PAGE
All HTTP endpoints vs what the Guala page (gualaloom.html) and Loom
Scan actually call. Per page, every displayed number traced to its
live source field, or marked STALE/DECORATIVE (the cognition meter
showed 07-04 audit text on 07-05 — disposition it). Poll rates per
page per endpoint (polling is load-bearing: default-executor
findings, 07-05). The bridge (MCP): every tool verified against its
API-gateway route, including behavior under restart (today's 503).
Auth posture per route.

## §6 — LEARNER-PROGRAM TRUTH
For YouTube, Khan Academy, PBS Kids, Spotify, each: adapter code
exists? enabled in production (WORLD_FEEDS value)? last successful
fetch with log evidence? fetched content reaching her read paths
(event-log proof)? filter/rejection rates? And the modality
question answered plainly: does ANY video deliver frames to her
sight (n_videos=1 — trace what it actually did), does ANY music
deliver audio to her hearing, or are these text-only feeds despite
their names? Curriculum scheduler verified live-wired (it was
dead-wired once; -186 reconnected it — prove current state).

## §7 — SENSORY TRUTH, END-TO-END PER SENSE
For sight (camera), hearing (mic + Whisper leg), her own voice
(self-hear + tagging), tactile/olfactory/gustatory (descriptor
emulation), and scene/story lanes (place, ambient, WHO):
source → transduction → binding (event proof) → organism tap
(organism_experience_bound with nonempty senses) → visible at Joe's
seat. Disposition the known sight-snapshot defect. Record sensory-
emulation coverage: which descriptor libraries exist, which senses
CAN fire at all, gaps as register lines. Story emulation = scene
lanes actually carrying data into bindings (ambient carried
["stillness","heat"] on 07-05 — verify the mechanism, not the
anecdote).

## §8 — BEHAVIORAL BASELINE SNAPSHOT (read-only measurement)
Under a stated, reproducible condition (READING active, camera+mic
on — the condition of record): tick_rate AND reads/sec side by side;
converse_timing full breakdown for 3 calls; the instrumented
recall_best timing that explains (or bounds) the 6-7x offline/live
gap; the 15-mechanism battery rows as currently measurable; vitals
vs the health table; ladder metrics; emission attempt count;
population/divisions + save-durability status. This is the BEFORE
column for everything that comes after the audit.

## §9 — HISTORICAL SWEEP: 2026-06-05 → 2026-07-05
Every commit on guala-live touching dsf_ai_service/, tools/, docs/:
inventoried (script-generated). Every dispatch and report filed in
docs/, with claimed-vs-verified status where the record shows a
discrepancy. Every TODO list in docs/. In-flight work that never
landed (built-and-lost, held-uncommitted — the outgoing c1a holds
live-wiring code uncommitted in a worktree; locate and inventory
it). Plan deltas v5→v10. The development environment itself:
devcontainer config, worktree state, shared-.git hazards, CI
config. Output: a one-month ledger of done vs said-done.

## §10 — DELIVERABLES
D1 tools/audit/ script set, committed (the rerunnable baseline).
D2 GL-AUDIT-BASELINE-C1-<date>-v1: every layer above, every claim
   evidence-graded.
D3 GL-AUDIT-DEFECTS-REGISTER-C1-<date>-v1: every dead / broken /
   unimplemented / absent / stale item as a numbered line with
   evidence. No fixes. Joe routes the register afterward, in his
   order.
Report cadence: one short filed report per layer as completed
(§1-§9), failures and absences FIRST in each. Verdict-first
language. No questions to Joe inside reports; raise blockers in
the message body of your seat, once, plainly.

## EXIT
The audit is complete when D1-D3 are on origin, every §1-§9 layer
carries evidence grades with zero NOT-MEASURED entries remaining
except those explicitly accepted by Joe, and Joe has the baseline
at his seat. Nothing else ships until Joe routes from the register.

### Changelog
- v1 (2026-07-05, Eve): executable audit per Joe's order and the
  -v1 charter; freeze law; current-state orientation for the fresh
  seat (wave-cell deploy live, 69-72s converse, unexplained 6-7x
  recall gap, unsaved-at-boot exposure).
