# Auditory bilateral recurrence stop result — 2026-07-27

## Outcome

The first required recurrence condition is falsified. The proposed post-L4
`AuditoryBilateralCrossReceptorResonanceTrajectory` exact-edge relation is not
justified for implementation or production.

No kernel, VTVR, runtime, persistence, or deployment file was changed.

## Tested architecture

- 64 globally source-disjoint speech experiences
- eight commands
- five reference and three held-out speakers per command
- physically distinct left and right propagation
- unchanged canonical L0–L4
- 32 cumulative-phase receptor vertices
- complete 496-edge bilateral certified gamma-squared graph
- all 64 pressure/phase L4 support receipts retained per experience
- scalar graph meet excluded from the relation
- command labels withheld until the complete 64-by-64 matrix existed

The tested relation was reciprocal canonical L6 over exact corresponding
certified edge facts. It used no tolerance, score, alignment, transcript, ML,
q identity, Krim reduction, or label.

## Stop requirement

Before any post-L4 operator could be justified, at least one nonidentity
same-command pair had to show selective recurrence. The requirement failed.

| Measurement | Result |
|---|---:|
| Same-command locked pairs | 0/224 |
| Cross-command locked pairs | 0/1,792 |
| Held-out passes | 0/24 |
| Nonidentity pairs | 2,016 |
| Nonidentity pairs sharing any exact edge fact | 0/2,016 |
| Maximum shared exact edge facts | 0/496 |

The result is not merely an over-strict final whole-cochlea gate. Every pair
of different experiences had zero exactly corresponding certified edge facts.

## Reproduction

```text
taskset -c 0-3 python -m \
  tools.probe_auditory_bilateral_cross_receptor_resonance_trajectory \
  --archive /tmp/mini_speech_commands.zip \
  --output /tmp/guala_bilateral_cross_receptor_trajectory_v1_rerun.json \
  --summary
```

- corpus SHA-256:
  `49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0`
- report:
  `/tmp/guala_bilateral_cross_receptor_trajectory_v1_rerun.json`
- report SHA-256:
  `01701421e74ca4ec2dbfbf88a7b395a2e514aad4fef8f74673cc541bf03cf3e1`
- embedded report authority:
  `14145e40790959fce41254a3668660928262a63bc6ec10c7b2143b451abc5674`
- probe SHA-256:
  `f5507f2fd63a1edaf445c609af33ad4b1416d44948e53c91e4ae3cad5202e0e6`
- authority recomputation: passed
- independent rerun: byte-identical to the prior report

## Exact interpretation

This falsifies exact certified-edge equality as a speaker-independent
recurrence relation. It does not prove that bilateral resonance physics lacks
useful information under every possible lawful relation.

The complete D/M/R/U/C/P/B fields were preserved as authenticated support but
did not enter the tested edge-fact relation. That disclosed reduction means
the result cannot authorize discarding the fields, nor can it authorize
inventing a new quotient.

The independent raw-to-L4 audit is consistent with this stop result: neither
its exact whole-trajectory relation nor its local structural alphabet
established selective held-out recurrence at raw PCM. Therefore there is no
evidence-backed raw recurrence disappearance boundary and no justified
hearing-scoped kernel change.

## Required decision

Do not implement, wire, persist, deploy, or describe the proposed post-L4
cross-receptor operator as a hearing repair. A different mechanism requires a
new explicit architectural hypothesis and its own pre-implementation
falsification contract; this audit supplies no authority to choose one.
