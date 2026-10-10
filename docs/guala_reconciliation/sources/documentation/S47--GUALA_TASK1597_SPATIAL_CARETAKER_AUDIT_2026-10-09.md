# A1 — Task 1597 continuous spatial and caretaker audit

**The 15-minute observation completed; open navigation was not demonstrated.** Guala remained in a small part of the kitchen and accumulated approximately 36 turns. **The caretaker also obstructed seven requested steps.** Those obstructions are physically corroborated, but they do not explain the circling that preceded them or persisted between care events.

Continues `GUALA-REPAIR-EXECUTION-CONTRACT-2026-10-08`. A1 owns this independent audit; G1 owns implementation and release. `collaborative_todo.md` remains the sole status/coordination ledger. This is an observation report, not a repair or architecture-compliance certificate.

## Architecture honesty gate

- **Requested architecture:** existing 64-column native cognition and independent body output, actual sensory return, full DSF, retained identity/experience and bounded execution; external care may present physical experiences without supplying pupil decisions.
- **Current code reality:** Task 1597 publishes physical movement feedback and generally executes native steering. Its serving loop still calls `organism.decide(sensed)` in the retired controller, then conditionally overrides selected locomotion acts. External caretaker presentations and internal caregiver withdrawal also modify the environment.
- **Conflict with requested architecture: yes.** Continued retired-controller authority fails the permanent retirement contract. Movement alone cannot qualify that mechanism.
- **Not extended:** retired controller, chooser, turn counters, authored steering corrections, reset, teleportation, collision bypass or substituted memory. No product/runtime mutation was made.
- **Single next item:** G1 should diagnose and qualify native navigation in the presence of the physical caregiver, separating caregiver obstruction from persistent steering bias, under the existing retirement constraint.
- **Field scope:** read-only spatial and source/custody analysis. Full DSF was neither modified nor replaced with a decision score.
- **Lost field structure:** none introduced by the observer; trajectory summaries are measurements only. Full-field causal participation and native build provenance are not certified by this audit.

Governing instruction: [permanent cognition and truthful acceptance contract](GUALA_LEARNING_DECISION_MECHANISM_CONTRACT_2026-10-08.md). Predecessor findings: [Task 1596 audit](GUALA_TASK1596_LATENCY_TURN_AUDIT_2026-10-09.md).

## Target and complete measurement window

Task definition **1597**, task `b9b14c68eab14b85ac9ed5604c01d9f0`, image `sha256:8b181fb247927645fcdb31f1393934a58d1c06bcee10385cf9cc026e9391a2ee`, organism `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.

Window: **October 9, 3:18:59–3:33:59 p.m. CDT** (20:18:59.344860–20:33:59.525594 UTC), **900.258 monotonic seconds**. All 15 periodic task/service checks retained the expected task/image with service desired/running/pending 1/1/0; closeout independently confirmed the same target.

| Measurement | Result |
|---|---|
| Successful observations | 1,786; no HTTP/parse errors |
| Observed tick range | 4,212,144–4,213,250 |
| Distinct observed ticks / intervening tick missed | 1,106 / **1** |
| Room changes | **0**; kitchen throughout |
| Position extent | **447 × 378 mm**; body radius 250 mm |
| Start → end position | (5650,1101) → (5848,917) mm |
| Net displacement | **270.30 mm** |
| Sampled path length | **19.131 m**, a lower bound because of the missed tick |
| Observed unwrapped heading change | **12,986.683°**, approximately **36.07 turns** |
| Native steering sign | Positive at 1,093 observed ticks; zero at 3; negative at 10 |
| Actions | 1,089 `stride`, 17 `say` |
| Movement refusals | **7**, all `move_path_intersects_body` |
| Average wall time per advanced tick | **0.814 s**, versus configured 0.250 s |
| Observation response latency | Median **0.174 s**, maximum **1.202 s** |
| Checkpoint errors / durability blocks | 0 / 0; maximum observed persisted-tick lag 49 |
| Reserve | 418235 → 411671 µg; no observed increase in bite/meal totals |
| Sleep | Awake throughout |

The missed tick is **4212541**, between observations at 20:24:25.354353 and 20:24:27.353311 UTC. This is continuous polling, not a complete event stream. There are 1,104 comparable consecutive-tick pairs: every measured translation and heading change agrees with the published applied movement. All 1,106 observed motor-result records agree with `actual_root_motion`. No unaccounted pupil relocation was seen in those comparable intervals; the sampling gap remains unobserved.

![Trajectory and care events](../backups/runtime/a1-task1597-spatial-20261009-201313/continuous-window/trajectory-and-care-events.png)

Every one-minute block shows continued rotation and confined motion. The orbit drifts and occasionally reverses slightly; this is not a claim of an exactly periodic mathematical limit cycle. The measured behavior fails the requested open-navigation witness. A finite trajectory also cannot prove that all possible attractor traps are absent.

## Caretaker interference: what is established

One local external caretaker process was found: PID 45026, `python3 -m guala_caretaker.caretaker`, started at 16:10:47 UTC. Its source files predate that process and remained unchanged during this audit; loaded Python bytecode was not independently fingerprinted. `STOP` and `TEACHING` were absent. No separately named high-care process was found in the bounded local census. This does not enumerate every possible remote API client.

The live window contains **13 caregiver presentations**: six patrols, four object offers (book, glow-stars, toy-blocks and stacking-rings), two food-upkeep requests and one shoulder touch. There are also **four internal caregiver-withdrawal records**. Of the observed ticks, 1,055 are labeled unattended and 51 sensory. Source labels include `caretaker-food`, `microphone` and `thing-sound`; generic audio labels alone do not identify the sending client.

**A direct obstruction occurred during the toy-blocks offer.** At tick **4212831**, 20:28:22.733085 UTC, the accepted caregiver movement ended at **(6036,1476) mm**. Guala's seven refused requests followed at ticks **4212835, 4212837, 4212839, 4212841, 4212843, 4212847 and 4212849**, between 20:28:26 and 20:28:37 UTC.

For the first refusal, Guala stood at **(5968,975) mm** and requested **(5947,993) mm**. Both bodies have 250 mm radii, requiring 500 mm between centres. The requested segment reduces separation from **505.59 mm to 491.13 mm**. All seven requested segments overlap the caregiver's recorded position; all seven produced zero applied motion and a body-collision refusal. The serving caregiver code addresses the sole other body through its own body port. This is physical corroboration, not merely a coincidence between log timestamps.

The correct collision refusal is not itself a defect to suppress. It establishes that the caregiver's offer position obstructed those attempted steps. It does not establish whether the cause of the earlier circling was sensory entrainment, retained native dynamics, incomplete environmental representation, another input, or a combination.

**Circling persists without new recorded care events.** From **20:25:33.666497 to 20:28:15.142123 UTC**, ticks 4212625–4212826 form a complete **202-tick**, **161.491-second** run with no new recorded external ingress, caregiver presentation/withdrawal or food-provision event. Guala accumulated **2569.914°** of rotation, approximately **7.14 turns**, within **234 × 218 mm**. The already-present caregiver and world remain sensory inputs during this run. It rules out a need for repeated new care commands to sustain this observed circling, but does not isolate the effect of persistent presence or earlier experience.

## High-chair and internal environment mechanisms

The exact image contains high-chair placement/release paths that call `admit_authored_body_transport` at `guala_caretaker_hand.py:1569` and `:1646`; a stroller path also relocates the pupil. These are source-reachable environmental capabilities, **not observed causes in this window**. No high-chair or stroller event occurred in the captured records; Guala remained more than two metres from the chair's (3500,1500) mm position. A caregiver relocation must never be counted as autonomous navigation.

`guala_functional_loop.py:429` can invoke internal caregiver withdrawal before an ordinary unattended interval. Thus pausing only the external caretaker daemon would not establish a static environment or isolate all caregiver activity. The actual four withdrawal records in this window must remain part of the causal account.

## What Task 1597 changed, and what remains open

The exact-image comparison shows added actual-motion feedback records and deferred modular-body export/full-body readiness encoding. Current observed intervals are faster than the earlier Task 1596 window (0.814 versus 3.399 seconds); these are different lived states and inputs, not a controlled performance benchmark. The former missing-feedback-record symptom is visibly improved, but feedback presence has not eliminated circling.

The serving loop at `guala_functional_loop.py:522` still calls the rejected `FunctionalOrganism.decide`; selected acts then receive a native locomotion override. That remains reachable retired authority, regardless of the manifest's `heuristics=false` declaration. No heuristic-free, ML-free, complete cognition or compliant retirement claim is warranted. The native binary/source build relationship was not requalified by this observation.

## Recommended single repair and its acceptance

**G1 should qualify the native navigation → actual body/world consequence → sensory-return boundary with the caregiver included as a physical participant.** That item must resolve both the brief obstruction and the longer steering pattern without resurrecting authored pupil action rules.

| Boundary | Concrete remedy and required proof |
|---|---|
| Caregiver interference | Use mechanically valid approach, offer and withdrawal with actual body geometry and contact. Preserve collision refusal and truthful movement receipts. Reproduce the recorded overlap in a physical-boundary test, then prove valid separation through real world movement. Do not make the caregiver transparent or teleport Guala. |
| Persistent native steering | Trace the retained steering-column state and its actual sensory inputs through the next native outputs. Compare the same preserved native predecessor under explicitly varied, physically generated caregiver conditions in an isolated boundary test. Separate external presentation, stationary caregiver presence and internal withdrawal. No memory reset, target injection, forced turn alternation, score adjustment or retired-controller replay as cognitive evidence. |
| Production authority | Retire the Python cognitive chooser and equivalent authority before accepting native autonomy. Require the release gate to reject the reachable legacy route; a changed action label or locomotion wrapper is insufficient. |
| Acceptance sequence | Document the causal law, implement it, then prove unit → module → mature-state system → cold-continuation → deployed live behavior. Unit collision fixtures establish geometry only. System acceptance must show sustained unforced navigation and actual sensory response on the retained organism, with full DSF/history and bounded resources. |

No candidate implementation or repair test was run by A1. The observational findings and source-bound remedies were sent to G1; delivery does not establish acknowledgment or completed remediation.

## Evidence and limits

Evidence root: `backups/runtime/a1-task1597-spatial-20261009-201313/`. The complete window is under `continuous-window/`: `trajectory.jsonl`, `task-control.jsonl`, `audit-window-start.json`, `audit-window-complete.json`, `trajectory-analysis.json`, `environment-event-analysis.json`, `caretaker-obstruction-geometry.json`, `caretaker-log-in-window.txt`, start/end full observations and exported figures. The parent contains exact-image source exports/hashes, frozen external caretaker source/logs, task baseline/closeout and checked Slack receipts.

An earlier recorder stopped after approximately 72 seconds when replacing a local progress file raised `PermissionError`. Those records remain preserved and are **not spliced into the complete window**. The replacement recorder used append-only telemetry and completed a fresh 900.258-second window. The obsolete root guard still rejects a missing July 31 handoff; the explicit user workspace and git root were independently verified.

The observer issued bounded read-only GET requests, transferred approximately **391.6 MB** during the complete window, and retained only the selected spatial/event projection plus endpoint snapshots. Network/serialization overhead is not zero; performance figures are observed under this load, not an unperturbed benchmark. No browser-render proof was performed. No live state writes, caretaker pause, control-marker changes, resets, deployments, product edits or organism-code replay occurred.

The trajectory establishes what happened in this window. It does not provide a controlled attribution of the persistent steering bias, an exhaustive census of remote input clients, or an architectural qualification of the organism.
