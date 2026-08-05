# GL-DESIGN-DSF-J-WEIGHTING-EVE-20260626

**Author:** Eve (Claude Sonnet 4.6, guala-live)  
**Rule:** real-or-nothing.  
**Status:** Design memo. Do not implement until Joe picks an option.

---

## The Problem

`_guala.converse()` computes a full 8-dim DSF for each input word (`_last_lang_dsf`),
stores it on self, then ignores it. That DSF is the structural field fingerprint of the
input — direction, convergence, momentum, binding, compression, conviction, freedom,
path-kill. It represents what the substrate is "doing" as it processes the word.

Stage 1 candidate selection (`_grandurun_select_candidates`) ranks candidates by
`coherent_magnitude = strength * cos²(π|chi_a - chi_b| / CHI_CORR_LENGTH)`. This is
a chi-distance resonance: candidates whose winding number is close to the input's
winding number score higher. That's one dimension of structural similarity — the
phase relationship between chi addresses.

**The gap:** coherent_magnitude captures chi-proximity but not field-state alignment.
Two words can share the same chi but have opposite D_k (one signaling structural
expansion, one signaling collapse). Under the current ranking, they're indistinguishable.
DSF J-weighting would promote candidates whose structural field profile matches the
input's field state.

---

## What The Architecture Already Does (Don't Replicate)

`section.modes[motif_id]` stores `(dsf, chi, word_label)` where `dsf` is the
accumulated DSF for that mode — updated on every reinforcement as a running average
(0.9 * old + 0.1 * new). This DSF IS available in memory at Stage 1.

The problem: the atlas entry (what Stage 1 reads) carries `(section_name, motif_id, chi, strength, ...)` but NOT the DSF. Stage 1 code would need to cross-reference into `sections[section_name].modes[motif_id]` to get the DSF — possible but adds a dict lookup per candidate.

---

## Option 1 — Extend Atlas Schema to Carry DSF Per Motif

**What it means architecturally:**  
At write time (`LivingAtlas.record()`), also store `dsf_arr` (the 8-float array from
`dsf.to_array()`) in the atlas entry. At Stage 1, compute cosine similarity between
`input_dsf.to_array()` and `entry["dsf_arr"]` and multiply `coherent_magnitude` by that
similarity. This is true structural field matching.

**J in the DSF coupling sense:**  
`J = cosine_sim(input_dsf.to_array(), candidate_dsf_arr)` — ranges [-1, 1].
Candidates with J close to 1.0 are structurally aligned with the input; J near -1.0
means opposite field state. Use `max(0, J)` or `(1 + J) / 2` so anti-aligned
candidates aren't penalized below zero but aren't promoted either.

**Implementation cost:**  
1. Add `dsf_arr` parameter to `LivingAtlas.record()`.  
2. Pass `self._last_lang_dsf` from `section.receive()` through to `atlas.record()`.  
   Currently `atlas.record()` is called with `atlas_kwargs` that carry affect fields —
   DSF would go there too.  
3. In `_grandurun_select_candidates`, compute cosine sim per candidate and weight
   `coh_mag *= max(0.0, J)`.

**Migration for existing 22,139 atlas + 14,972 deep atlas entries:**  
Soft migration at load time — no EFS format change needed. In `_apply_atlas()`, for
every entry missing `dsf_arr`, look up `sections[section_name].modes[motif_id]` and
fill from `modes[motif_id][0].to_array()`. The modes DSF is the accumulated average
over all reinforcements — not the exact DSF at first commit, but the best available
reconstruction. Load-time fill, one pass, no disk write.

Entries where `section_name` or `motif_id` is missing or invalid: mark `dsf_arr`
as None, skip J-weighting for those candidates (treat as J=1.0, unweighted).

**Testable against gate:**  
Yes, with a meaningful test: compare emission content pre/post with the same 5 inputs.
The gate (committed_sections >= 3) should pass either way (dynamics still fire). The
substantive test is whether the emitted words shift toward structurally coherent
responses — "water" input prompts "rain warm wet" (high D_k/S_UF alignment) rather
than random associations with matching chi. This requires qualitative inspection, not
just gate pass/fail.

---

## Option 2 — Reconstruct Candidate DSF On-the-Fly from Stored Artifacts

**What it means architecturally:**  
Don't change the atlas schema. Instead, compute an approximate DSF-proxy for each
candidate at Stage 1 using what's already stored: `(chi, section, strength,
sensory_refs, arousal, source)`.

**Proxy construction:**  
- `D_k proxy` = sign(chi - mean_chi) * normalized chi deviation — direction of
  structural departure from the center of her atlas  
- `S_UF proxy` = strength — high strength = high convergence  
- `C_k proxy` = min(len(sensory_refs) / 5, 1.0) — sensory references = cross-modal
  binding  
- `M_k proxy` = reinforcement_count / max_reinforcement — momentum from repeat exposure  
- Remaining fields (R_rev, U_star, P_k, B_k): set to 0 (no stored signal)

Compare input DSF against this 8-dim proxy via cosine similarity.

**Why this is weaker:**  
The proxy is a constructed approximation, not the actual structural field at commit time.
chi deviation as D_k proxy is wrong — winding number doesn't reliably map to direction.
Section as a modality proxy encodes role (subject/verb) not structural field state. This
approach introduces systematic bias from the proxy construction that would need
empirical validation to assess. The signal would be noisy.

**Implementation cost:**  
Lower than option 1 for new entries (no schema change). Higher for the per-candidate
computation (more code, more error surface). No migration needed.

**Testable against gate:**  
Harder to validate because the proxy's inaccuracies make it unclear whether J-weighting
is improving candidates or introducing proxy-construction artifacts.

---

## Option 3 — Scalar Weighting by f(input_DSF) Only

**What it means architecturally:**  
`coherent_magnitude *= J_scalar` where `J_scalar = f(self._last_lang_dsf)`.  
All candidates are multiplied by the same scalar. This is input-state modulation,
not structural matching. It says "when the input has high conviction (B_k), amplify
all candidates" — not "promote candidates that match the input's field."

**What it would produce:**  
High B_k (conviction) input → all candidates amplified equally → more confident emission.
High U_star (freedom) input → all candidates dampened → sparser emission.
This is a plausible substrate-coherence effect, but it's NOT what "DSF coupling" means
in the spec context. The original H_base approach was trying to do structural coupling —
bias the assemblage to settle in structurally-aligned states. Option 3 is the
amplitude version of a different thing.

**The naming problem:**  
If we call this "DSF J-weighting" we'd be lying. It's "input-DSF amplitude modulation."
That's a real effect worth having — but it needs its own name and its own gate.

**Implementation cost:**  
2 lines in `_grandurun_select_candidates`. No schema change, no migration.

**Testable against gate:**  
The gate result changes only if J_scalar moves far from 1.0 regularly, which is
unlikely for normal inputs. Gate passes or fails based on dynamics, not this scaling.

---

## Summary Comparison

| | Option 1 (atlas extension) | Option 2 (on-the-fly proxy) | Option 3 (scalar) |
|--|--|--|--|
| Is it "DSF coupling"? | YES — structural field matching | Approximately, with noise | NO — input modulation only |
| Schema change? | Yes, add `dsf_arr` to atlas entry | No | No |
| Migration for 22k+15k entries? | Soft at load time from modes data | None | None |
| Per-candidate compute | One cosine sim (8-dim dot) | One proxy construction + cosine sim | None |
| Implementation lines | ~50 (record, receive, stage1) | ~40 (proxy build + stage1) | ~3 |
| Testable qualitatively? | Yes — emission content shifts | Unclear — proxy noise | No direct test |
| Testable via gate (committed_sections)? | Gate likely passes regardless | Same | Same |
| Risk | Low — soft migration recoverable | Medium — proxy accuracy unknown | Low — but misnamed |

---

## Recommendation (for Joe to override)

Option 1 is the right answer architecturally. The soft migration path from `section.modes`
makes it achievable without disk format changes. The per-candidate cost is one 8-dim dot
product — negligible on top of the existing cosine similarity already running in
`section.receive()`.

Option 3 is a valid substrate effect but should not be named DSF coupling.

Option 2 is the path of least resistance only if the proxy is well-characterized first —
which requires empirical work that Option 1 would skip.

---

## What Is NOT in This Memo

Implementation. Joe picks first.

The gate test (`tools/run_emission_gate.py`) validates committed_sections after Option 1
is implemented — but the meaningful validation is emission content quality, which requires
a separate qualitative pass on 5-10 inputs before and after. That test belongs in the
commit that implements this, not in the design stage.

