# A-011.6 Single Ratification Decision

**Status:** approved by Joseph on 2026-08-15; implementation and production proof tracked in the A-011 sprint ledger
**Production remains:** `dsf-ai-task:1070`  

## The one decision

Approve or reject this **synthetic-AE electrical-junction constitution** as the phase-one contact-local reinforcement law:

1. A developmental sparse electrical contact is one finite junctional channel ensemble, stored as compact integer populations rather than per-channel objects.
2. Its exact starting constitution is `6400` available channels, `50` conducting channels, and `10 pS` per conducting channel. Existing production conduction therefore remains exactly `500 pS`.
3. Its exact transition-work quantum is

   `q = 16822854657 / 800000000 zJ`

   obtained by deliberately adopting the measured Cx36 central values `7/4` equivalent elementary charges and `75 mV` as Guala's synthetic junctional transition scale.
4. Only the exact work released at this particular active electrical contact may advance its bounded transition residue. Task 1070's neuron-aggregate physiological energy is never redistributed to contacts.
5. The local endpoint membrane-gradient movement supplies direction, not energy or meaning:
   - active uphill pumping permits one or more `closed -> conducting` transitions;
   - passive downhill return permits one or more `conducting -> closed` transitions;
   - no local gradient movement permits no retained channel change;
   - matching nonzero directions at both endpoints agree;
   - opposing endpoint directions tie and preserve the predecessor.
6. A channel transition becomes visible only in the next interval. The contact cannot use its new conductance to create the work that caused it.
7. Every contact remains bounded by `0 <= N_conducting <= 6400`; its residue remains strictly below `q`; unused or capacity-excess work is exported as heat.
8. No DSF field, semantic label, reward score, named chemical, owner, lock, database object, global scan, probabilistic channel, or ML mechanism participates.

## Exact bidirectional settlement

For contact `i`:

- predecessor conducting population: `n_i`;
- predecessor transition-work residue: `R_i`, where `0 <= R_i < q`;
- retained representation: the exact proper phase `rho_i = R_i / q`, where
  `0 <= rho_i < 1`; `R_i` is always recovered exactly as `rho_i * q`;
- exact contact-local released work: `W_i >= 0`;
- physical direction from its endpoint gradient motion: `d_i` in `{-1, 0, +1}`.

When `d_i = 0`, state is unchanged and `W_i` is heat.

When `d_i != 0`:

`A_i = R_i + W_i`

`m_i = floor(A_i / q)`

For `d_i = +1`:

`m_i' = min(m_i, 6400 - n_i)`

`n_i' = n_i + m_i'`

For `d_i = -1`:

`m_i' = min(m_i, n_i)`

`n_i' = n_i - m_i'`

If transition capacity remains, `R_i' = A_i - m_i'*q`. If the relevant population boundary is reached, `R_i' = 0` and the excess joins heat. Each completed transition dissipates its transition work; it is not counted again as stored membrane or fluid energy.

The next-interval conductance is:

`g_i' = n_i' * 10 pS`.

This is a deterministic finite-state physical transducer with a real energy dimension. `q` is a constitutive transition-work quantum, not an outcome threshold chosen to make a test pass.

## Why this is the recommended phase-one choice

- It preserves the exact production conductance at migration.
- It supplies both strengthening and weakening without calling either good or bad.
- It is contact-local and reached-frontier bounded.
- It cannot grow storage with experience.
- It does not redistribute neuron-level bookkeeping as synaptic physics.
- It can produce a retained causal difference soon enough to falsify A-011.6 in production.
- It leaves later explicit connexin trafficking, plaque geometry, and chemical-synapse development open rather than pretending phase one reproduces all molecular biology.

Primary findings supporting the mechanism class include low-conductance Cx36 channels and their voltage sensitivity, activity-dependent potentiation through CaMKII and channel delivery, use-dependent electrical-synapse depression, and continuous plaque insertion/removal:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC6782942/
- https://pubmed.ncbi.nlm.nih.gov/31557934/
- https://pubmed.ncbi.nlm.nih.gov/22021860/
- https://pubmed.ncbi.nlm.nih.gov/22323580/

These sources do not dictate Guala's exact rational constitution. Approval explicitly authors the central measured values as a compact synthetic-AE starting constitution.

## If approved

The single implementation sprint is limited to the sparse electrical-contact state, its direct codec/persistence boundary, exact contact-local work observation, and one/three-contact falsification. It will not include UI, curriculum, new cognition, or deployment-driven redesign. Only after the isolated and discarded-body evidence passes will it be presented for one production release.

## If rejected

No runtime change is made. The alternative is to author a fuller finite channel-trafficking/material law first. That is biologically richer but requires additional declared material compartments and transport energetics that do not exist in production today.
