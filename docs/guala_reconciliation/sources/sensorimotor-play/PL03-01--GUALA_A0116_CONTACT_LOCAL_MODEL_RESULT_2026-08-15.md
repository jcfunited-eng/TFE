# A-011.6 Contact-Local Electrical Plasticity Model Result

**Status:** isolated mathematical falsification; no runtime edit, deployment, or production claim  
**Candidate:** `GUALA_A0116_CONTACT_LOCAL_ELECTRICAL_PLASTICITY_CANDIDATE_2026-08-15.md`  
**Production remains:** `dsf-ai-task:1070`  

## Exact boundary result

The proposed finite contact state is sufficient to conserve local work and alter later conductance without a counter, score, semantic label, global scan, or per-channel software object.

The existing task-1070 physiological-energy settlement is **not** sufficient to drive that state lawfully. It first sums association and body contact activity at one neuron, then debits one neuron-local recovery reservoir. It does not preserve which exact contact received which share of the delivered work. Distributing that aggregate back to contacts after settlement would invent contact history.

Therefore the runtime must not reuse the aggregate `ContactModulatedGateEnergySettlement` as contact-local plastic authority. A reached contact may use only its own exact before/after physical work while the existing same-place fluid trajectory acts as a local permissive condition. The fluid condition is not a reward and does not supply a second copy of the contact's work.

## Exact channel constitution candidate

The current developmental electrical-contact conductance is exactly 500 pS. A Cx36-informed synthetic-AE constitution can preserve it exactly:

- single-channel conductance `g_unit = 10 pS`;
- predecessor open population `N_open = 50`;
- finite total population `N_total = 6400`;
- therefore `g = N_open * g_unit = 500 pS`.

The 10 pS unit is within the experimentally observed approximately 10–15 pS Cx36 range. The measured open fraction `0.0078` is approximately `1/128`; applying `1/128` to 6400 channels yields 50 open channels. This is a compact numerical state, not 6400 allocated objects.

The Cx36 measurements also report a half-inactivation voltage of approximately 75 mV and an equivalent gating charge of approximately `7/4` elementary charges. Using Guala's already-authoritative exact elementary-charge conversion,

`epsilon = 801088317 / 5000000000 zJ / (elementary_charge * mV)`,

the corresponding synthetic conformational-energy candidate is

`E_transition = (7/4) * 75 * epsilon`

`             = 16822854657 / 800000000 zJ`

`             = 21.02856832125 zJ`.

This is not inferred truth about Guala. It is the exact rational constitution obtained by deliberately adopting the published central Cx36 values for this synthetic electrical contact. That adoption requires architecture approval before code.

Primary evidence:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC6782942/
- https://pubmed.ncbi.nlm.nih.gov/23420660/

## One-contact conservation model

For one reached contact, let:

- `q = E_transition > 0`;
- `N` be its finite total channel population;
- `n` be its predecessor open population, `0 <= n <= N`;
- `R` be retained sub-transition work, `0 <= R < q`;
- `W` be exact work available from this contact's own settled physical transition;
- `eligible` mean that this exact active contact is incident to the exact locally modulated endpoint in the same causal interval.

If the contact is not eligible, its channel state and residue remain unchanged and `W` is exported through the ordinary thermal path.

If it is eligible:

`A = R + W`

`m = min(floor(A / q), N - n)`

`n' = n + m`

When `n' < N`:

`R' = A - m*q`

`H = 0`

When capacity is reached:

`R' = 0`

`H = A - m*q`

In both cases:

`R + W = (n' - n)*q + R' + H`.

Successor conductance is not used until the next interval:

`g_next = n' * g_unit`.

The model therefore cannot use its own new conductance to manufacture the work that caused it.

## Three-contact locality model

For three reached contacts `a`, `b`, and `c`, settlement applies the one-contact law independently to each contact's own `(n_i, R_i, W_i, eligible_i)`. There is no shared plastic accumulator.

The exact aggregate conservation identity follows only after the three independent settlements:

`sum(R_i + W_i) = sum((n_i' - n_i)*q + R_i' + H_i)`.

Consequences:

- activity at `a` cannot change `b` or `c`;
- simultaneous activity at `a` and `b` cannot multiply their available work;
- an unmodulated `c` retains identical channel state even if it conducts;
- contact ordering cannot change the result because no contact consumes another contact's work;
- work is proportional to reached active contacts, never all organism contacts.

## What the model proves

- Finite integer channel state can preserve the existing 500 pS conductance exactly.
- One additional open channel changes the next-interval conductance from 500 pS to 510 pS, a retained 2% local change.
- State is bounded by `N_total`; it cannot grow with organism age.
- A single rational residue is bounded by one transition quantum.
- Three contacts remain independent and exactly conservative.
- No DSF field changes or participates in this local downstream mechanism.

## What the model does not yet prove

- It does not ratify Cx36 central measurements as Guala's synthetic constitution.
- It does not yet calculate task-1070 contact-local `W` values because the live observer reports carrier transfer but not the full two-endpoint before/after membrane-and-gradient work at each contact.
- It does not supply a lawful structural decay/channel-removal path. Absence of modulation alone cannot be treated as an instruction to decrement a channel.
- It does not prove later action changes, reciprocal positive engagement, joy, laughter, or A-011.6 completion.

## Smallest next implementation after approval

Only `sparse_electrical_contact.rs` and its direct persistence callers should change first:

1. introduce a fresh contact constitution/state codec rather than reinterpret `GLSEC01` or `GLSEC02`;
2. retain `N_open` and bounded `R` per sparse contact;
3. compute effective conductance from predecessor `N_open`;
4. expose exact contact-local before/after work and settle the model above only when the already-authenticated local physiological condition reaches that same contact;
5. read legacy contact-plastic bytes for task-1070 compatibility but discard them as non-authoritative false physics;
6. prove one-contact, three-contact, cold-restore, and reached-frontier resource behavior before any organism integration.

No runtime implementation is authorized by this model document.
