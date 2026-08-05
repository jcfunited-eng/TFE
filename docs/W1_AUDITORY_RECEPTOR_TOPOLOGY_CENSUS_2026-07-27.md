# W1 Auditory Receptor Topology Census — 2026-07-27

## Architecture honesty gate

- Requested architecture: continuous substrate-true hearing through explicit
  physical receptor state and the unchanged full D/M/R/U/C/P/B L0–L4 field.
- Current code reality: the canonical provider exposes 16 independent
  fourth-order ERB gammatone channels, 10 ms complex RMS, cumulative carrier
  phase, and direct phase advance.
- Conflict with the requested architecture: yes. The provider contains no
  deterministic inner-hair-cell adaptation and no cross-band
  formant-trajectory relation.
- Mechanisms not extended: the failed L5 matchers, chi/psi identity,
  transcript labels, scalar scores, reduced field vectors, and production
  hearing code.
- Single item executed: an isolated 16/32/64/128-channel receptor and exact
  L0–L4 information-survival census.
- Field evaluation: the complete explicit D_k, M_k, R_rev_k, U_star_k, C_k,
  P_k, and B_k trajectories on every pressure and phase component.
- Reduced structure lost: none.

## Exact result

The channel-count hypothesis is falsified. Increasing the same independent
ERB topology from 16 to 128 channels never made the correct L4 basin strictly
dominant for all three held-out speakers.

| Channels | Held-out `down` | Held-out `go` | Held-out `left` | Full reversal |
|---:|---|---|---|---|
| 16 | 111 vs wrong max 112 | 111 vs 113 | 108 vs 110 | No |
| 32 | 232 vs 235 | 220 vs 218 | 213 vs 221 | No |
| 64 | 459 vs 466 | 445 vs 458 | 438 vs 448 | No |
| 128 | 923 vs 936 | 899 vs 902 | 885 vs 901 | No |

The predeclared reversal rule required all three source-disjoint held-out
speakers to have strictly more exact complete L4 run-envelope lanes in the
physically grounded basin than every wrong basin. No tolerance or fitted
threshold was used.

## What survived

At every tested topology:

- all 18 physical receptor trajectories were distinct;
- all 18 cross-band order trajectories were distinct;
- all 18 full explicit L4 trajectories were distinct.

Therefore the cochlear field is not erasing the recordings into identical
states. Speaker and articulation information reaches both the receptors and
L4. The failure is the absence of a lawful learned invariant or relation that
turns those distinct experiences into stable causal structure across
speakers.

## Bounded cost

| Channels | Receptor state | Transduction / audio time | Exact L0–L4 / audio time |
|---:|---:|---:|---:|
| 16 | 1,664 bytes | 0.298 | 0.579 |
| 32 | 3,328 bytes | 0.303 | 1.141 |
| 64 | 6,656 bytes | 0.335 | 2.377 |
| 128 | 13,312 bytes | 0.376 | 4.708 |

Physical transduction remained bounded and faster than real time through 128
channels. Exact L0–L4 did not: 32 channels already crossed the one-core
real-time boundary in this isolated execution. More channels add cost without
repairing the causal error.

## Decision

Do not enlarge the canonical channel count. The next recommended isolated
item is an explicit deterministic cross-band formant-trajectory relation,
because cross-band order trajectories are already physically distinct and
currently have no receiving operator. Inner-hair-cell adaptation should be
tested separately afterward so the two physical causes are not conflated.

No canonical or live production code was changed.

## Authorities

- Census report:
  `/tmp/w1_auditory_receptor_topology_census.json`
- Report authority:
  `762e6d207bc2e22a4f498c8339e1239b72391dd6822358f920e1a8737c63ab6c`
- Probe:
  `tools/probe_auditory_receptor_topology_census.py`
- Probe SHA-256:
  `18127ed1ceec9b982e19ba2cd5fc210cc1ce556bf97628cd8db92480e9ce3472`
- Focused verification: 11 tests passed.
