# Auditory direct full-field topology preflight falsification — 2026-07-27

## Outcome

The frozen direct-full-field change-mask topology is falsified as a
speaker-independent auditory recurrence relation.

None of the three held-out hearings was admitted by its correct trained
THING branch. All three remained unknown. The result does not authorize a
production hearing claim or production wiring.

L0–L4, the existing production path, and persistence were unchanged.

## Tested architecture

- three spoken words: `down`, `go`, and `left`
- 16 source-disjoint training speakers and one source-disjoint held-out
  speaker per word
- 51 globally source-disjoint physical audio captures
- unchanged canonical L0–L4
- direct `AuditoryReceptorFullFieldEvent` input from both ears
- all 64 ear/channel/component positions on the common source grid
- complete ordered D/M/R/U/C/P/B tuple witnesses
- ordered 64-bit masks recording which positions changed between frames
- zero-change durations excluded from identity
- word labels excluded from the adapter and withheld from held-out
  evaluation until after comparison
- bounded at 800 frames, 799 masks, 128 KiB per encoded topology, 48 trained
  topology identities, and a 16 MiB report

This was intentionally a reduced relation. Full field magnitudes and change
durations remained authenticated witnesses but did not determine topology
identity.

## Frozen result

| Measurement | Result |
|---|---:|
| Physical captures | 51 |
| Source-disjoint speakers | 51 |
| Unique training topologies | 48/48 |
| Correct held-out admissions | 0/3 |
| Competitor admissions | 0/6 |
| Unknown held-out hearings | 3/3 |
| Full gate passed | false |
| Claim allowed | false |

Each word accumulated 16 distinct training topologies. Each held-out topology
was different from every trained topology, including all 16 examples of its
correct word.

## Frozen evidence

- report:
  `/tmp/auditory_direct_full_field_topology_preflight.json`
- report SHA-256:
  `1a2721301a1c67cbba9040a753cae596336f15c045f067423d107bc36f4db7e6`
- embedded authority receipt:
  `19725dc3615227432892d2c21c7c5d26342a0b23d62aa3d60eb00e305e6fc7e8`
- authority recomputation: passed
- archive SHA-256:
  `49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0`
- plan SHA-256:
  `3ea2d10462d4aca14956c287ffe9d75fea26495a447548159c8cb94cd48d984a`
- corpus manifest SHA-256:
  `64e4835379990d7d703c6300633c3d12794c12dcf7e4cd781aa729af5ff37740`
- direct adapter SHA-256:
  `e778c8e4ed3a7c5ee3d8c0f4f3e3ab806f1ca7e30f37607a7e4fd1a37aa31528`
- probe SHA-256:
  `e2df8d1145cce90c16d582e7d910693e97545b40582a21353eac7ddde72bb5e1`
- adapter static tests: 4 passed
- process exit: 1, the frozen falsification exit

## Exact interpretation

The result falsifies exact ordered change-mask equality for these unseen
speakers. It does not falsify the full D/M/R/U/C/P/B field, because the tested
identity deliberately discarded field magnitudes and change durations.

The preflight therefore gives no authority to implement its relation, extend
it with after-the-fact tolerance, wire it into Guala, or describe hearing as
solved. Any next relation must be specified and frozen independently before
its held-out oracle is exposed.
