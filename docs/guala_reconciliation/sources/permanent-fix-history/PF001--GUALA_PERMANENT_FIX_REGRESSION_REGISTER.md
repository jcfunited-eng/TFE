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

## Current candidate

| ID | Correction in progress | Regression scope |
|---|---|---|
| C-001 | Give the two root-yaw directional endings compact, disjoint layer-6 and layer-8 projection slots instead of recursively Cantor-projecting them into a 93,824,443 pF regulation membrane; retire every contact incident to the malformed historical paths at the V32 one-way boundary. | Source-complete. Must preserve F-001 through F-009. It changes only root-yaw anatomical address derivation and cold contact retirement; no DSF field, observer, action label, event law, or motor-output law changes. Focused proofs: `body_terminal_integration_places_follow_the_existing_sensory_geography`, `moved_root_terminal_mounts_only_its_paired_sensorimotor_reflex`, and `v32_retires_misprojected_root_yaw_paths_once` all pass. Live cutover evidence remains pending. |

## Candidate C-001 preservation check

| Prior fix | Result before commit |
|---|---|
| F-001 one organism | Preserved: V32 is a one-way rewrite of the same resident state; no new organism owner or restore path. |
| F-002 unattended life | Preserved: no loop, request, or observer code changed. |
| F-003 connected-path settlement | Preserved: no solver or DSF equation changed. |
| F-004 fan-out cleanup | Preserved: the shared retirement helper keeps V31's exact contaminated-pool removal and the existing motor authorship law. |
| F-005 event frontier | Preserved: no event selection or scheduling code changed; retired-path frontier entries are removed with their retired bonds. |
| F-006 passive return | Preserved: no membrane return, pump, carrier, energy, work, or heat law changed. |
| F-007 custody outside cognition | Preserved: no runtime, custodian, seal cadence, or cloud path changed. |
| F-008 read-only observers | Preserved: no observation surface changed. |
| F-009 membrane-owned motor output | Preserved by the paired-reflex proof: preparation remains an exact contact transfer and output remains exact positive local membrane discharge. |

## Historical reconciliation backlog

The delivery ledger and item ledgers contain older claimed fixes. They are not
silently promoted here. Each older claim will be added only when its current
source reachability and, where relevant, live production evidence have been
rechecked. This prevents a stale historical `complete` label from becoming
architecture authority.
