# GL-SPC-MODE-GROWTH-AND-SUCCESSOR-KEYING-DESIGN-20260714-v2

**doc_id:** GL-SPC-MODE-GROWTH-AND-SUCCESSOR-KEYING-DESIGN-20260714-v2
**Date:** 2026-07-14 UTC
**Status:** `proposed_pending_ratification` — design only. No code written, nothing deployed. Implementation is a separate, later dispatch once this design is reviewed.
**Governing spec:** `docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md`.
**Adjacent design:** `docs/GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1.md` (the coexperienced-scene recall subsystem this one shares a blast surface with; also `proposed_pending_ratification`).
**Owner requirements this answers (verbatim, not softened):**
1. *"Live experience must grow new modes when the full field is structurally distinct."*
2. *"A mode cannot permanently own only one successor. Transitions must be distinguished by the complete prior state, memory, chemistry, and causal experience — not by mode identity alone."*
**Scope:** the mode-growth/recognition decision in `expression_modes.py` and the successor-keying invariant in `expression_learning.py` (with its honest recall-side blast surface in `recall_reentry.py`). It does not change field physics, evidence preparation, the commit conjunction's authorities, or the closed-experience seal.

---

## 1. Plain-language outcome

Tonight a real multi-word sentence was driven through the real GLEW conversation engine (`dsf_ai_service/glew_runtime/glew_runtime` path: recognition → commit → learn). With only the two bootstrapped modes in the bank (the `"a"`/`"b"` genesis pair) plus one already-seeded successor, essentially every well-formed novel scalar was **recognized as one of those two existing, unrelated modes** instead of being treated as new — and because the recognized mode already owned a learned successor, the learn step hit `expression_learning.py`'s hard invariant *"prior committed mode already has a learned successor"* and failed. The flag was rolled back to off after this finding.

Two independent things are wrong, and they need two independent fixes:

- **Requirement 1 (recognition/growth).** The recognition rule is a winner-take-all interval dominance over the vector `[mode-1 probability, … , mode-n probability, orthogonal-residual probability]`. A novel full field that happens to *share most of its energy* with an existing mode is **recognized as that mode by design** — its orthogonal innovation only "wins" (and grows a new mode) when that innovation dominates everything else. This is not a broken or unreachable growth path; it is the intended semantics, and it is the wrong semantics for live experience. The fix makes **certified orthogonal-residual energy against the whole existing basis** — a value the boundary *already computes* — the growth/recognition arbiter: an input with genuine energy outside *every* existing mode grows and stays novel-silent; recognition-as-an-existing-mode is reserved for inputs the field certifies to lie within the existing span.

- **Requirement 2 (successor keying).** A learned successor is keyed **by the committed mode's receipt alone**. One mode → at most one successor, forever. The fix keys a successor by `(mode receipt, transition-context digest)`, where the digest is a **real composite of receipts that already exist and are already sealed** on the per-turn `CommittedModeRelation` and the `LearnedBindingState` — so the same recognized mode can learn genuinely distinct successors arising from genuinely distinct prior state / memory / chemistry / causal experience, while an *identical* experience twice still collides (correctly).

The two fixes compose: Requirement 1 stops misrecognition when the field is genuinely distinct; Requirement 2 handles the legitimate case where two turns genuinely recognize the *same* mode from *different* context. Neither invents new physics; both reuse quantities the substrate already computes and seals.

---

## 2. The decision, up front

- **Requirement 1 — chosen:** replace the "recognize if this mode's probability strictly dominates the residual and every other mode" branch with a **certified-residual arbiter**. At rank ≥ 2, with a unique dominating mode, recognition-as-that-mode is granted **only if the input's orthogonal residual against the full basis is certified NOT strictly positive** (certified zero / within-span to enclosure). If the residual is **certified strictly positive** (genuine energy outside every existing mode), the turn **grows a new mode and returns `NOVEL_SILENCE`**, regardless of which mode's activation was larger. An **indeterminate** residual refines through the *existing* precision-doubling loop before deciding; exhaustion yields `AMBIGUOUS_SILENCE` (honest silence), never a forced match. Uses only `residual_energy_ball`, `_certified_positive`, `_certified_zero`, and the loop already present — no threshold, no tolerance, no new physics, dimension-independent (identical at rank 2 and rank n).
- **Requirement 1 — rejected:** a numeric "structural-distinctness floor" constant on the residual probability. Rejected because `expression_modes.py`'s whole contract forbids any tolerance/threshold/midpoint obtaining decision authority (module docstring; `evaluate_expression_mode_boundary` docstring). The certified-positive/certified-zero predicate is threshold-free and already the module's growth primitive.
- **Requirement 2 — chosen:** a `TransitionContext` receipt composed from already-sealed fields; successor uniqueness keyed on `(mode_receipt_sha256, transition_context_digest_sha256)`. The recall-time *match* uses the **reproducible sub-digest** (the receipts a deterministic scene re-run reproduces); the non-reproducible receipts (recognition, closed-experience seal, commit, memory snapshot) are recorded as a sealed **provenance strand** on the binding and drive the learn-time duplicate guard.
- **Requirement 2 — rejected:** keying on a fresh, invented per-transition nonce/counter. Rejected because the owner's requirement is explicit that identity comes from *real* prior state / memory / chemistry / causal experience — all of which are already receipted — not from a fabricated tag.

---

## 3. Verified findings (read from code + one empirical run; cited, not recalled)

### 3.1 The recognition rule is a winner-take-all dominance over `[modes…, residual]`, and recognizing an existing mode while growing the innovation is *intended*

At rank ≥ 2 the boundary forms the certified probability vector and computes the unique-dominance `winners` set over `all_bounds = (*probability_bounds, residual_bounds)` — the mode activations **plus the orthogonal residual as a co-equal last candidate** (`expression_modes.py:896–940`; decision rule string `"one_lower_bound_strictly_exceeds_every_other_upper_bound"`, `expression_modes.py:624`). The decision (`expression_modes.py:993–1024`):

- `len(winners) == 1` and `unique < bank.rank` → **`RECOGNIZED`** (winner is an existing mode);
- `len(winners) == 1` and `unique == bank.rank` → **`NOVEL_SILENCE`** (the residual won);
- and **on either branch** a new mode is appended when `_certified_positive(residual_energy_ball)` and there is room (`expression_modes.py:996–1007`).

So growth **is** reachable at rank ≥ 2 — the "growth only ever fires during bootstrap/rank < 2" hypothesis is **false**. What is true is that *recognition status* (which drives commit and successor keying) is decided purely by which probability-vector candidate uniquely dominates. An input mostly aligned with an existing mode, carrying only a small orthogonal innovation, is **recognized as that mode**, and its innovation is grown as a *separate* mode the recognition ignores.

**Empirical confirmation (ran locally, 3 passed):** the sibling `modes.py` — same dominance contract, same statuses — is exercised by `tests/glew_runtime/test_certified_mode_boundary.py`. `test_tiny_positive_innovation_grows_without_a_threshold_after_old_mode_wins` (`:353–370`) feeds `[1_000_000, 0, 1]` (energy ≈10¹² along mode 0, orthogonal innovation energy 1) and asserts `status is RECOGNIZED`, `recognized_mode_index == 0`, `residual.exact_energy == 1`, **and** `post_growth_bank.rank == 3`, `mutation_applied`. `test_residual_dominant_external_experience_grows_silently_after_decision` (`:288–310`) feeds a mostly-orthogonal input and asserts `NOVEL_SILENCE`. `test_exact_repeat_recognizes_existing_mode_without_growth` (`:274–285`) asserts an exact repeat (`residual.exact_energy == 0`) is `RECOGNIZED` with no growth. `expression_modes.py` mirrors this exactly (`:993–1024`).

**Therefore the live failure is hypothesis A: a structurally sound, *intended* dominance decision in which the field genuinely judges the novel scalars as dominating an existing mode**, because a single-scalar six-lane scene shares the overwhelming majority of its energy with the existing modes. It is **not** a distinct bug in the growth trigger.

### 3.2 "Only two modes ever grew" ⇒ the live inputs' residual was never certified strictly positive

Growth-append at rank ≥ 2 is gated on `_certified_positive(residual_energy_ball)` (`expression_modes.py:996–999`), i.e. the residual's certified **lower** bound > 0 (`expression_modes.py:74–75`). The live bank stayed at two modes. Deduction: on every live turn the input's orthogonal residual against the two-mode basis was **not certified strictly positive** — its certified enclosure straddled zero — so no mode grew **and** an existing mode's activation dominated the (near-zero) residual → forced `RECOGNIZED`. The live single-scalar fields are near-collinear with the existing 2-D span to within certified enclosure. (This is consistent with, not contradicted by, an ambient field that is *large*: §3.3.)

### 3.3 The ambient field is high-dimensional, so near-collinearity is a property of the scenes, not of the space

Field dimension is `FIBER_DIMENSION × len(ordered_port_fibers)` (`field.py:420,452`), `FIBER_DIMENSION = 19` (`field.py:59–80`), over six lanes (language + five senses: sound/smell/taste/touch/sight — `story_chemistry.py:104–108`, `PRODUCTION_SENSOR_CALIBRATION_UNRATIFIED_v1.py:190`) ⇒ a **114-dimensional** ambient field. Two modes span a 2-D subspace; a genuinely distinct input *should* have large orthogonal residual. That the live residual is sub-certified-positive (§3.2) means the six-lane single-scalar scenes are near-collinear — they share sensory/chemistry structure and differ only in the language lane's balanced-ternary trits. So Requirement 1's *premise* ("genuinely, structurally distinct from every existing mode") does not automatically hold for these inputs at the field level; some live inputs are within-span and are the domain of Requirement 2, not Requirement 1 (see §7).

### 3.4 The commit boundary independently re-checks the same dominance — so a committed turn genuinely dominated an existing mode

`commit._verify_expression_recognition` re-derives dominance from the sealed recognition receipt: `winner_lower > residual_upper` and `winner_lower > every other mode upper`, else `ReceiptError("recognized expression mode lacks unique interval dominance")` (`commit.py:1187–1201`). It requires `rank ≥ 2` (`:1163–1164`) and `RECOGNIZED` (`:1169–1170`), and keys the committed mode on `recognition.pre_growth_bank.modes[winner]` (`commit.py:1228–1230`; engine at `clean_conversation_engine.py:985–990`). So the live commit really did select an existing pre-growth mode by dominance — the misrecognition propagates verbatim into the committed `selected_mode`.

### 3.5 A learned successor is keyed by the committed mode's receipt alone

In `learn_committed_binding_transaction` the stable binding is built with `mode_receipt_sha256 = prior_relation.selected_mode_receipt_sha256` and the uniqueness guard removes any existing binding with that same mode receipt, raising *"prior committed mode already has a learned successor"* if one existed (`expression_learning.py:1156–1187`). `LearnedBindingState.verify` re-imposes it: `len(set(stable_modes)) != len(stable_modes) → "learned mode has more than one successor"` (`:750–757`). Recall resolves the successor **by mode only**: `StableModeMotifBank.resolve_unique(mode_receipt_sha256, …)` requires exactly one motif for that mode (`recall_reentry.py:355–376`), used at recall settle (`recall_reentry.py:854–862`) and at initial-event build (`expression_learning.py:786–796, 922`). The stored `StableModeMotifBinding` carries no context beyond `mode_receipt` / `motif_receipt` / `source_fact_strand_receipt` (`recall_reentry.py:229–253`, bank payload `:272–317`). **The key is mode identity alone; no prior state, memory, chemistry, or causal receipt participates.**

### 3.6 The full context is *already sealed* — no new state need be tracked

The per-turn `CommittedModeRelation` already carries, sealed and receipt-verified (`expression_learning.py:469–482`, `derive_committed_mode_relation :556–617`, `committed_relation_receipt_payload :411–466`):

| Owner's context axis | Already-sealed receipt (exact field) |
|---|---|
| prior state | `prior_relation.authority_receipt_sha256` (the `CommittedModeRelation` the transition departs from) + the actuator's `CommittedMotifEvent.source_state_receipt_sha256` (chain position) |
| memory at that moment | `state.output_bank.bank_receipt_sha256` + `state.stable_bank.bank_receipt_sha256` (the `LearnedBindingState` banks at call time, `expression_learning.py:681–682`) |
| chemistry / sensory state | `current_relation.closed_experience_receipt_sha256` (the six-lane `SealedClosedExperience.closed_experience.authority_receipt_sha256`, which folds the deterministically-evolved `StoryChemistryRuntime` state, the causal-window bridge, and every sensory + language evidence record) + `current_relation.sensory_evidence_receipt_sha256s` (`_sensory_receipts(sealed)`, `expression_learning.py:149–158`) |
| causal experience of the turn | `current_relation.expression_receipt_sha256` (the full-field `ClosedExperienceFieldExpression`) + `current_relation.recognition_receipt_sha256` + `current_relation.commit_receipt_sha256` |

Every field above is a real sha256 of a payload already in the mounted `ReceiptRegistry`. A composite key is a **canonical digest over these existing receipts** — no fabricated tag, no new tracked state.

### 3.7 The engine already documents this exact collision as its reason for never auto-closing

`clean_conversation_engine._learn_and_persist` (`:998–1040`) states in-code that `learn_committed_binding_transaction(expression_close=True)` *"raises `ReceiptError("prior committed mode already has a learned successor")` whenever the turn's scene mode already anchors a successor — which is exactly the case for every recall-trigger turn (you trigger recall by RE-experiencing a known anchor scene)."* This is the same wall from the emission side, and it is why the single-successor invariant blocks both learning **and** expression-close on recurring anchors.

---

## 4. Requirement 1 design — certified-residual growth/recognition arbiter

**Intent (owner):** when the full field is genuinely, structurally distinct from *every* existing mode, grow a new mode rather than falsely recognizing an existing one.

**Mechanism.** The value that answers "distinct from *every* existing mode, independent of how many exist" is already computed: the input's **orthogonal residual against the full basis**, `residual_energy_ball` / `certified_residual_probability` (`expression_modes.py:876–895`). It is `‖present − proj_span(all modes)(present)‖²`, so it is by construction "energy outside every existing mode" and is dimension-independent. The current defect is that this value is only consulted as a *co-equal dominance candidate*, so a large in-span alignment beats it; it is never used as the **arbiter** of whether the input deserves recognition-as-existing at all.

**Changed decision (rank ≥ 2, replacing `expression_modes.py:993–1024`):**

1. Compute `winners` and the unique dominating candidate exactly as today.
2. Consult the **certified residual** first:
   - **`_certified_zero(residual_energy_ball)`** → the input lies within the existing span to certified enclosure. If a unique existing mode dominates, return **`RECOGNIZED`** for it (grows nothing — residual is zero). This preserves exact-repeat recognition (the `matching_mode_index` path already forces residual to exact zero, `expression_modes.py:876–895`) and legitimate within-span recognition.
   - **`_certified_positive(residual_energy_ball)`** → the input has genuine energy outside every existing mode. **Grow** the input as a new mode (existing `_append_expression_mode`, gated on room `bank.rank < bank.max_rank`) and return **`NOVEL_SILENCE`** — *regardless of whether some existing mode's activation was numerically larger*. This is the semantic change the owner requires: distinctness is judged by certified out-of-span energy, not by winner-take-all.
   - **indeterminate** (neither certified positive nor certified zero at the working precision) → **do not decide**: fall into the *existing* precision-doubling loop (`expression_modes.py:1042–1045`) and re-evaluate. On mounted-maximum exhaustion with an indeterminate residual → **`AMBIGUOUS_SILENCE`** (`expression_modes.py:1081–1096`) — honest silence, never a forced match.
3. If no unique dominator exists (`len(winners) != 1`), behaviour is unchanged (refine → `AMBIGUOUS_SILENCE`).

**Why this is correct and threshold-free.** `_certified_zero` / `_certified_positive` are the module's own exact-interval primitives; the arbiter introduces no constant, midpoint, or tolerance. It is identical at rank 2 and rank n (the residual is against *all* modes). It reuses the growth-append and precision-loop already present. It changes exactly one thing: recognition-as-existing now requires the field to *certify* the input is within the existing span, and genuine out-of-span energy now grows-and-stays-silent instead of being absorbed.

**Interaction with §3.2/§3.3 (important, not hidden).** For the live near-collinear scalars whose residual is *not* certified positive even after refinement, this fix leaves them `RECOGNIZED` (they are, in the field's exact judgment, the same mode). Requirement 1 alone therefore does **not** by itself stop the live collision for genuinely within-span inputs — those are the domain of Requirement 2 (a recognized mode learning a distinct successor per distinct context). Requirement 1 stops the collision for every input that carries genuine out-of-span energy (grow → no commit-as-old → no successor collision); Requirement 2 stops it for the within-span remainder. The owner named both as non-negotiable precisely because both regimes occur.

**New/changed signatures (expression_modes.py):**

```python
# ExpressionRecognitionStatus: unchanged set (RECOGNIZED / NOVEL_SILENCE /
# AMBIGUOUS_SILENCE / BOOTSTRAP_SILENCE / UNKNOWN). No new status is required:
# a structurally-distinct input reuses the existing NOVEL_SILENCE ("novel
# experience remains silent") + growth path.

def evaluate_expression_mode_boundary(  # signature UNCHANGED
    *, topology, bank, input_expression, receipt_registry, hermitian_evaluators=None,
) -> ExpressionModeBoundaryResult: ...
#   internal rank>=2 branch changed per steps 1-3 above; the returned
#   ExpressionModeBoundaryResult dataclass, its receipt payload/schema, and the
#   decision-rule string are UNCHANGED, so every downstream verify() is
#   byte-compatible.
```

No dataclass, receipt schema, or public signature changes — only the branch selection inside the loop. This keeps `ExpressionModeBoundaryResult.verify` and `commit._verify_expression_recognition` byte-identical.

---

## 5. Requirement 2 design — successor keyed by full, sealed context

**Intent (owner):** a mode may own multiple successors; each transition's identity/eligibility is the full prior-state/memory/chemistry/causal context, not the mode index.

### 5.1 The composite key

Introduce a sealed `TransitionContext` (new receipt in `recall_reentry.py`, alongside `StableModeMotifBinding`), whose payload folds the §3.6 receipts. It has **two named sub-digests** because recall can only reproduce some of them:

```python
TRANSITION_CONTEXT_SCHEMA = "glew.recall.transition_context.v1"

def transition_context_receipt_payload(
    *,
    profile_binding_sha256: str,
    mode_receipt_sha256: str,
    # --- reproducible sub-key (a deterministic scene re-run reproduces these) ---
    prior_relation_receipt_sha256: str,          # prior_relation.authority_receipt_sha256 (prior state / chain departure)
    input_expression_receipt_sha256: str,        # current_relation.expression_receipt_sha256 (bank-independent, deterministic)
    sensory_evidence_receipt_sha256s: tuple[str, ...],  # current_relation.sensory_evidence_receipt_sha256s (six-lane, reproduce bit-for-bit)
    # --- provenance strand (sealed, audited, NOT part of the recall match) -----
    closed_experience_receipt_sha256: str,       # current_relation.closed_experience_receipt_sha256 (chemistry+causal+sensory seal)
    recognition_receipt_sha256: str,             # current_relation.recognition_receipt_sha256 (bank-dependent -> not reproducible)
    commit_receipt_sha256: str,                  # current_relation.commit_receipt_sha256 (fresh at recall -> not reproducible)
    memory_output_bank_receipt_sha256: str,      # state.output_bank.bank_receipt_sha256 (memory at that moment)
    memory_stable_bank_receipt_sha256: str,      # state.stable_bank.bank_receipt_sha256 (memory at that moment)
) -> bytes: ...
#   returns canonical JSON with two nested objects:
#     "reproducible_match": {prior_relation, input_expression, sensory_evidence}
#     "provenance": {closed_experience, recognition, commit, memory_output_bank, memory_stable_bank}
#   and the top-level digest = receipt_sha256(payload).
#   The reproducible-match sub-digest = receipt_sha256(canonical(reproducible_match)),
#   stored explicitly so recall can recompute and compare it without the provenance.
```

Every argument is an existing, mounted receipt (§3.6). Nothing is fabricated or newly tracked.

**Why the split is real, not a dodge.** A deterministic scene re-run (the `coexperienced_scene_recall_executor` of the adjacent v1 design) reproduces `input_expression_receipt_sha256` (built from scene descriptors + text + chemistry, **bank-independent**, `clean_conversation_engine.py:761–769`) and `sensory_evidence_receipt_sha256s` (the v1 design's core premise, its §3.2) bit-for-bit, and it knows `prior_relation` from the walked chain. It **cannot** reproduce `recognition_receipt_sha256` (folds `pre_growth_bank.receipt_sha256`, which grows monotonically), `closed_experience_receipt_sha256` (folds recognition), or `commit_receipt_sha256` (self-recall mints a *fresh* commit each time — asserted distinct in v1 §11 T1). So those, and the mutable-memory snapshot, are recorded as sealed **provenance** and used for the learn-time duplicate guard, while recall matches on the reproducible sub-digest. Because at any reproducible chain position the memory snapshot and recognition are themselves deterministic functions of (prior relation, scene), the reproducible sub-digest is a faithful, collision-safe proxy for "same full context" — the provenance strand is the audit trail, not an independent discriminator.

### 5.2 Changed binding, bank, uniqueness, resolution

```python
@dataclass(frozen=True, slots=True)
class StableModeMotifBinding:          # recall_reentry.py:229 — ADD one field
    binding_id: str
    profile_binding_sha256: str
    mode_receipt_sha256: str
    motif_receipt_sha256: str
    source_fact_strand_receipt_sha256: str
    transition_context_receipt_sha256: str        # NEW: the §5.1 sealed context
    transition_context_match_sha256: str          # NEW: the reproducible sub-digest
    binding_receipt_sha256: str
    # payload()/verify() extend to bind both new digests; bank payload
    # (recall_reentry.py:272-317) adds them to each entry's serialized object.

class StableModeMotifBank:              # recall_reentry.py:320
    # _by_mode stays (grouping by mode), but a mode may now map to MANY bindings.
    def resolve_for_transition(          # REPLACES resolve_unique(mode)
        self, *, mode_receipt_sha256: str, transition_context_match_sha256: str,
        receipt_registry: ReceiptRegistry,
    ) -> StableModeMotifBinding:
        # verify bank + every candidate; select the one binding whose
        # transition_context_match_sha256 equals the caller's; ReceiptError on
        # zero matches ("no stable motif binding for this mode under this
        # transition context") or >1 ("conflicting stable motif bindings for one
        # transition context" -- a true-duplicate defect).
        ...
```

```python
def learn_committed_binding_transaction(...):   # expression_learning.py:1016 — signature UNCHANGED
    # After deriving current_relation, build the TransitionContext from
    # prior_relation + current_relation + state.output_bank/stable_bank (all
    # already in `working`). Replace the mode-only guard (:1179-1187) with:
    #
    #   duplicate = [b for b in state.stable_bank.bindings
    #                if b.mode_receipt_sha256 == prior_relation.selected_mode_receipt_sha256
    #                and b.transition_context_match_sha256 == new_context_match]
    #   if duplicate:
    #       raise ReceiptError("prior committed mode already learned this exact "
    #                          "transition context")   # TRUE duplicate only
    #   stable_values = list(state.stable_bank.bindings) + [new_binding]   # keep siblings
    #
    # binding_id already includes motif_digest (:1156-1159) so distinct
    # contexts -> distinct motifs -> distinct binding_ids (no id collision).
```

```python
class LearnedBindingState:               # expression_learning.py:677 — verify() change only
    # Replace the mode-uniqueness check (:750-757) with (mode, match)-uniqueness:
    #   keys = [(b.mode_receipt_sha256, b.transition_context_match_sha256)
    #           for b in self.stable_bank.bindings]
    #   if len(set(keys)) != len(keys):
    #       raise ReceiptError("learned mode/transition-context pair is not unique")
    # The output-motif and content-motif coverage checks (:762-775) are
    # unchanged (distinct experiences already produce distinct motifs).
```

Recall settle (`recall_reentry.py:854`) and initial-event build (`expression_learning.py:786–796, 922`) switch from `resolve_unique(mode)` to `resolve_for_transition(mode, match_digest)`, computing `match_digest` from the current transition's reproducible receipts (the re-run's `input_expression_receipt_sha256` + `sensory_evidence_receipt_sha256s` + the chain's `prior_relation` receipt). The checkpoint restore (`_restore_stable_bank`, `expression_learning.py:1431–1467`) reads the two new fields.

### 5.3 The true-duplicate guard is preserved

Two learns with the *same* mode and the *same* reproducible context (same prior relation, same scene, same senses) produce the same `transition_context_match_sha256` → the guard raises. Two learns with genuinely different prior state / chemistry / causal experience produce different match digests → both succeed. This is exactly the owner's requirement, with a real, non-fabricated key.

---

## 6. Composition — how the two fixes interact per turn

1. `_build_turn_expression` (unchanged) → `evaluate_expression_mode_boundary`. **Req 1** changes the rank ≥ 2 branch: genuine out-of-span energy → grow + `NOVEL_SILENCE`; certified within-span → `RECOGNIZED`; indeterminate → refine → `AMBIGUOUS_SILENCE`.
2. On `NOVEL_SILENCE` (Req 1 growth): no commit, no learn, no collision; the new mode is now in the bank, so a later exact re-experience recognizes *its own* mode.
3. On `RECOGNIZED` (within-span, or exact repeat): commit proceeds (`commit.py` unchanged — dominance re-check still holds because a within-span input's residual upper ≈ 0). Learn builds the `TransitionContext` and, via **Req 2**, appends a successor keyed by `(mode, context-match)` — *adding* to any sibling successors the mode already owns instead of colliding.
4. Recall (adjacent v1 design) re-runs the scene, recomputes the reproducible `match` digest, and `resolve_for_transition` fires the successor for *this* context.

The live crash is removed on both regimes: out-of-span novelty never commits-as-old (Req 1); within-span recurrence learns a sibling successor instead of colliding (Req 2).

---

## 7. Blast radius and risk — stated honestly

**Requirement 1 is narrow but a genuine semantic change.**
- **Contained:** no dataclass/schema/signature change; `ExpressionModeBoundaryResult`, its receipt, the decision-rule string, and every downstream `verify()` are byte-identical. `commit._verify_expression_recognition` (`commit.py:1187–1201`) still passes for `RECOGNIZED` (within-span residual upper ≈ 0 ⇒ dominance trivially holds) and never sees the newly-grown mode (recognition still indexes `pre_growth_bank`). The bootstrap path (rank < 2, `expression_modes.py:943–992`) is untouched, preserving the bootstrap-to-rank-2 requirement `commit.py:1163–1164` and every module depending on it.
- **Real risk:** the recognition/commit *rate* changes. Inputs that today `RECOGNIZED`-and-committed while carrying certified out-of-span energy will now `NOVEL_SILENCE`-and-grow, i.e. **learning of a genuinely-novel scalar shifts from its first experience to its first exact re-experience** (first sight grows the mode silently; the repeat recognizes it and commits/learns). This is consistent with the module's own `NOVEL_SILENCE` semantics ("novel experience remains silent") but is a behavioural shift a ratifier must accept. Any existing test asserting "mostly-aligned input RECOGNIZES + commits" flips and must be updated to the new arbiter (the `modes.py` sibling's `test_tiny_positive_innovation…` is the canonical example of the *old* intent; `expression_modes.py`'s analogue tests must be re-pinned). **Recall is safe:** recall re-runs are exact reconstructions → exact-DAG match → residual exact zero → `RECOGNIZED`, unaffected by the arbiter.

**Requirement 2 has the larger, tested blast surface — do not understate it.**
- It changes `recall_reentry.py` (`StableModeMotifBinding`, the bank payload/canonical order, `resolve_unique` → `resolve_for_transition`, and `RecallTransitionSettlement.verify`'s `:854` resolution) — a file with existing passing conformance (`tests/glew_runtime/test_recall_self_sense_reentry.py`, `test_remembered_expression_output.py`). Every stable-bank receipt payload changes shape, so **every checkpoint written before this change is schema-incompatible** on restore; a migration or a fresh genesis is required (the store already re-mounts the mode bank at rank 0 on restart — v1 §9 — so a genesis reseed via `seed_first_production_successor.py` is the clean path, but that seeder itself must be updated to the new binding shape).
- It couples to the **adjacent, also-unratified** coexperienced-scene recall design (`GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1.md`): `resolve_for_transition` needs the recall executor to hand it the re-run's reproducible receipts. If that design changes, this coupling moves with it. The two should be ratified and built together.
- The **transition chain currently flattens source-state to genesis** (`_make_initial_event` builds `source_state` from `initial_relation` only, `expression_learning.py:926–956`), so multi-successor resolution by chain position is not free: threading a genuine per-transition `source_state` through the actuator walk (`RememberedExpressionActuator`, `output.py`) is part of this work, not a trivial add. Named here so it is costed, not discovered mid-build.
- **Physics untouched:** no change to `field.py`, `closed_experience.py`, `expressions.py`, `story_chemistry.py`, `story_native_replay.py`, `story_global_uf_basin.py`, `commit.py`'s conjunction, or the closed-experience seal. Requirement 2 is a memory/keying change, not a physics change.

**Combined residual:** if either fix is wrong, the failure is a hard `ReceiptError` at a `verify()` (recognition, commit, or settlement), i.e. typed silence, never a silent wrong emission — the substrate's fail-closed discipline holds throughout.

---

## 8. Test plan (Requirement 4) — genuine, non-monkeypatched, learn/novel/restart proof

All tests drive real objects end-to-end (real mount, real recognition/commit/learn, real checkpoint round-trip); none monkeypatches recognition, commit, or recall, and none asserts `False` in place of a required result. Reuses this session's existing patterns and helpers.

- **G1 — Requirement 1 arbiter, direct (extends `tests/glew_runtime/test_certified_mode_boundary.py` / a new `test_expression_mode_growth_arbiter.py`).** Build a rank-2 bank. (a) Feed an input with certified-**positive** orthogonal residual but a *larger* in-span alignment (the analogue of `[1_000_000,0,1]`): assert the **new** outcome `status is NOVEL_SILENCE`, `post_growth_bank.rank == 3`, `winner_mode_index is None` — i.e. distinctness now grows instead of recognizing. (b) Feed an exact repeat: assert `RECOGNIZED`, no growth (residual certified zero). (c) Feed an input whose residual is indeterminate at base precision but certifies at higher precision: assert the loop refines and the terminal status matches the certified sign, never a base-precision forced match.

- **G2 — Requirement 2 multi-successor learn (extends `tests/glew_runtime/test_expression_learning.py`).** From a real `LearnedBindingState`, learn two successors for the **same** committed mode arising from two genuinely different `CommittedCoexperience` contexts (different `closed_experience`/`expression`/`prior_relation`): assert both succeed, `stable_bank` holds two bindings for that mode with distinct `transition_context_match_sha256`, and `LearnedBindingState.verify` passes. Then replay the **identical** context a third time: assert it raises *"already learned this exact transition context"* (true-duplicate guard intact).

- **G3 — repeated utterance still recognizes + recalls (extends `tests/glew_runtime/test_clean_conversation_engine.py` and `test_multi_scalar_turn_scheduler.py`).** Cold-start a real engine (bootstrap), drive a turn that commits+learns, then replay the same `(task_id, text)`: assert it recognizes its own mode and, given an expression-close, recalls the learned scalar via `resolve_for_transition` (fresh self-recall commit receipt distinct from learn-time, per v1 §11 T1).

- **G4 — genuinely novel utterance grows, does not collide (same fixture as G3).** Drive a novel scalar carrying certified out-of-span energy against a mode that already owns a successor: assert `NOVEL_SILENCE` + growth (Req 1), **no** commit-as-old, **no** *"prior committed mode already has a learned successor"*. Drive a within-span recurrence of a successor-owning mode from a new context: assert a sibling successor is learned (Req 2), not a collision.

- **G5 — cold-restart holds (extends `tests/glew_runtime/test_production_runtime_bootstrap.py`, mirroring `test_restore_round_trip_matches_persisted_learned_state`).** After G3/G4 (multi-successor stable bank + grown-and-relived modes), persist via the engine's own `_persist_checkpoint`, cold-restart off disk through `bootstrap_production_clean_conversation_engine`, and assert: the restored `LearnedBindingState` (with multi-successor `stable_bank` and both new binding fields) round-trips byte-for-byte; a repeated utterance (G3) still recognizes+recalls against the restored state; and a novel utterance (G4) still grows without collision. Record the known v1 §9 bound (mode bank re-mounts at rank 0 on restart, so cross-restart recall of not-yet-relived scenes is honest silence until re-lived) as the guarded, expected limitation — not a failure.

---

## 9. Summary for the ratifier

- **Finding (Requirement 1):** the live misrecognition is **hypothesis A — a structurally sound, *intended* winner-take-all dominance** over `[modes…, residual]`; a novel scalar that shares most of its energy with an existing mode is recognized as that mode by design (`expression_modes.py:993–1024`; confirmed empirically by `test_certified_mode_boundary.py:353–370`, 3 passed). It is **not** an unreachable-growth bug (growth *is* reachable at rank ≥ 2, `:996–1007`). "Only two modes grew" ⇒ the live residual was never certified strictly positive (`:996–999`) — the six-lane single-scalar scenes are near-collinear inside a 114-D field (`field.py:59–80,420`).
- **Fix (Requirement 1):** make the **certified orthogonal residual** the arbiter — grow + `NOVEL_SILENCE` on certified-positive out-of-span energy, `RECOGNIZED` only on certified within-span, refine the existing precision loop when indeterminate. Threshold-free, dimension-independent, no schema change.
- **Fix (Requirement 2):** key successors by `(mode_receipt_sha256, transition_context_digest)`, the digest a real composite of **already-sealed** receipts — prior state (`prior_relation.authority_receipt_sha256` + chain `source_state`), memory (`state.output_bank`/`stable_bank` bank receipts), chemistry/sensory (`current_relation.closed_experience_receipt_sha256` + `sensory_evidence_receipt_sha256s`), causal (`current_relation.expression_receipt_sha256` + `recognition_` + `commit_receipt_sha256`) — split into a reproducible recall-match sub-digest and a sealed provenance strand. Same mode → many distinct successors; identical experience twice still collides.
- **Blast radius:** Req 1 is contained to one branch but shifts learning of novel scalars to their re-experience and re-pins `expression_modes.py` recognition tests. Req 2 touches tested `recall_reentry.py` (binding/bank/resolve/settlement-verify + checkpoint schema, forcing a genesis reseed), threads a real per-transition source-state, and is coupled to the adjacent unratified recall design — build them together. No physics file is touched by either.
- **Status:** `proposed_pending_ratification` — implementation is a later, separate dispatch.
