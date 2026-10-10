# Guala Permanent Fix and Anti-Resurrection Register

Status: active production-development authority.

Purpose: keep one cumulative list of accepted fixes and require every later
candidate to prove that it does not restore the rejected mechanism. Sprint
ledgers retain the detailed evidence; this register is the cross-sprint gate.

## Required check for every candidate

Before commit and again after live cutover, record for every applicable row:

1. the exact source symbol or production surface checked;
2. whether the rejected mechanism is absent or unreachable;
3. the focused proof or live observation used;
4. the candidate commit and, after deployment, the task definition.

A row may not be called preserved from a source comment, ledger claim, or test
fixture alone. If it cannot be checked, the candidate remains open.

## Current accepted fixes

| ID | Accepted correction | Mechanism that must not return | Required regression check | Current evidence |
|---|---|---|---|---|
| F-001 | One resident organism restores only from authenticated `CURRENT`; identity survives cutover. | Ghost successor organisms, alternate restore authority, or observer-owned cognition. | Confirm one running writer, one `CURRENT` lineage, and unchanged organism identity after cutover. | Production task 1280 reports identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`; detailed custody evidence remains in the A-009/A-011 ledgers. |
| F-002 | Unattended native life advances without an external request. | Request-driven or observer-driven cognition. | Observe ticks advance while request logs contain only health/read traffic; observers remain read-only. | Live unattended advancement was measured before and after task 1280. |
| F-003 | Electrical settlement is per connected physical pathway. | One global minimizing fraction allowing disconnected pathways to suppress each other. | Inspect the mounted solver boundary and retain the disconnected-path falsifier. | Accepted correction `662f9cce`; A-006 ledger. |
| F-004 | Coincidence-based layer-11 to motor/articulatory fan-out is deleted and the contaminated pool was removed one way. | Authoring every simultaneous ordering/motor pair; restart restoration of the approximately 97,000 removed contacts. | Check authorship requires the retained directed causal chain; restore census must keep contaminated-pool count zero. | Live cleanup cut over in the task-1248 lineage; successor task 1280 retained the corrected body. |
| F-005 | Contact settlement uses the mounted event frontier and the old unconditional full-contact sweep is deleted. | Production reachability of the old whole-fabric sweep or a second scheduler authority. | Inspect the production call graph and observe due/sleeping census from the sole resident frontier. | Task-1248 lineage and later releases; detailed scheduler evidence in A-006. |
| F-006 | Passive membrane return is a local neuron transition; the pump serves only the causal frontier. | Pump-as-rest, pumping every touched neuron, or outside-energy creation. | Preserve positive/negative return, zero-crossing, carrier conservation, and untouched-neuron falsifiers. | Deployed in `cd9ffa93`; A-006 ledger. |
| F-007 | Persistence encoding/copying is outside the ordinary cognitive settlement critical section. | Whole-body seal or cloud copy pausing every physical interval. | Per-interval timing must show custody outside settlement and one bounded custodian. | Task-1248 lineage and later releases; A-006 runtime evidence. |
| F-008 | Observers are read-only and have no authority to admit, discard, choose, pause, or mutate cognition. | Observer labels, polling windows, or proof caches controlling organism transitions. | Review every changed observation callsite for immutable access only; live ticks must not depend on observer availability. | A-009/A-011 observer corrections and live continuity evidence. |
| F-009 | Native motor output is the neuron's exact local membrane whole-carrier discharge; contact transfer is preparation evidence only. | Relabeling incoming or net inter-neuron contact flow as efferent motor discharge. | Preserve positive/zero/negative/no-preparation falsifiers and inspect the runtime action payload source. | Commit `40a0222c`, focused proof passed, live task 1280. |
| F-010 | Root-yaw proprioception uses compact disjoint layer-6/layer-8 anatomy; malformed historical root paths are retired one way. | Recursive Cantor projection into a 93,824,443 pF regulation cell, restoration of its contacts, or a second root route beside the corrected route. | Prove V32 retirement is one-way; after one real root movement require exactly receptor -> compact integration -> compact regulation -> paired motor, with the malformed regulation isolated. | Commit `c8f84bd1`, live task 1281. V32 left malformed lineage `...02ecfd` isolated and mounted compact regulation `...000ecf` at 37,393 pF between layer-6 `...002ae9` and paired motor `...00009b`. |

## Current open correction

| ID | Correction in progress | Regression scope |
|---|---|---|
| O-001 | The corrected root route is live. A copied authenticated body now produces the motor's own seven-carrier terminal discharge; live world application, returned consequences, and continued unattended life remain to be cut over and witnessed. | Every candidate must preserve F-001 through F-010. A lesson is not claimed landed until the native motor discharges, the world applies it, all applicable consequences return to the same identity, and unattended life continues. |

### O-001 current causal boundary — 2026-08-28

- Corrected in the local candidate: signed contact evidence now follows the
  electrical anatomy's physical endpoint order rather than canonical bond
  identity order. The copied live body proves regulation-to-motor arrival.
- Corrected in the local candidate: the explicitly mounted terminal is a
  distinct local carrier path. Incoming contact current may only leave
  retained positive membrane displacement; the terminal then moves the
  motor's own carriers outward, never past zero, only under exact stored-work
  descent, and deposits released work in the cohort thermal reservoir.
- Copied-body evidence: restored production lineage `...00009b` held seven
  separated charges and, on its next reached interval, emitted exactly seven
  local carriers through its positive root-yaw terminal. No contact current
  was relabelled and no observer or action command participated.
- Rejected during development: using the passive-return event as the terminal
  discharge. Its exact crossing on this motor was 20,143 intervals away, so
  that candidate was removed rather than mislabeled as a useful action path.
- Next acceptance: the live world must apply that native discharge, then move,
  return every applicable consequence to identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, and unattended ticks must continue.

## Release 1281 cumulative preservation check

| Prior fix | Source and live result |
|---|---|
| F-001 one organism | Task 1281 is the sole writer and reports the same identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1` from one raw `CURRENT` lineage. |
| F-002 unattended life | Tick advanced unattended from 207797 through at least 208070 while public reads remained non-authoritative. |
| F-003 connected-path settlement | No solver or DSF equation changed; live contact-frontier settlement continued on the mounted connected-path law. |
| F-004 fan-out cleanup | Live layer-pair census contains no layer-11/layer-12 contacts; the contaminated ordering-to-motor pool did not return. |
| F-005 event frontier | Live event census remained mounted (`due_now_contacts`, `future_contacts`, and exact selected frontier); no full-sweep authority was restored. |
| F-006 passive return | No return/pump law changed; live census continued to publish separate return events and causal seeds. |
| F-007 custody outside cognition | Live transition stopwatch kept ordinary `seal_ms=0`; the candidate introduced no custody path. |
| F-008 read-only observers | Public contract reports `cognition_authority=false` and `read_advances_organism=false`; reads did not stop unattended advancement. |
| F-009 membrane-owned motor output | The runtime payload source and all four falsifiers are unchanged from `40a0222c`; the new root route prepares the existing motor but no output is claimed before local discharge. |
| F-010 compact root anatomy | V32 removed every contact incident to malformed regulation `...02ecfd`. A real one-millidegree world movement mounted exactly `layer-5 ...00090e -> layer-6 ...002ae9 -> layer-8 ...000ecf (37,393 pF) -> layer-12 ...00009b`; no parallel malformed route exists. |

## Historical reconciliation backlog

The delivery ledger and item ledgers contain older claimed fixes. They are not
silently promoted here. Each older claim will be added only when its current
source reachability and, where relevant, live production evidence have been
rechecked. This prevents a stale historical `complete` label from becoming
architecture authority.
