# GL-SPC-REPRODUCIBLE-EXPERIENCE-IDENTITY-DESIGN-20260714-v3

**doc_id:** GL-SPC-REPRODUCIBLE-EXPERIENCE-IDENTITY-DESIGN-20260714-v3
**Date:** 2026-07-14 UTC
**Status:** `proposed_pending_ratification` — design only. No code written, nothing deployed. Production is safe (`GLEW_CONVERSATION_ENGINE_ENABLED=0`); the engine is not live, so this is pure design before any further implementation.
**Governing spec:** `docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md`.
**Adjacent designs (share this blast surface; both already implemented in commit `3ff6745`):**
- `docs/GL-SPC-MODE-GROWTH-AND-SUCCESSOR-KEYING-DESIGN-20260714-v2.md` (certified-residual growth arbiter + transition-context successor keying — **now live in the code this doc reads**).
- `docs/GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1.md` (the six-lane coexperienced-scene deterministic-replay recall subsystem this design's step 6 reasons against).

**Reviewer finding this answers (verbatim, not softened):**
> "Production creates a new request identity for every utterance, then uses that identity to manufacture the scene's sensory conditions." Recommendation: *"replace request-ID-generated 'experience' with a reproducible experience identity derived from the actual sensed field, chemistry, and causal state, and carry that same identity through recall resolution. The request UUID may remain bookkeeping but must have no physical authority."*

**Scope:** the sensory-content derivation in `clean_conversation_engine._scene_descriptors` and its three call sites. It does **not** change field physics, evidence preparation, recognition, the commit conjunction, the successor-keying invariant, or the recall subsystem. It removes one thing: the request transport id's authority over physical sensory content.

---

## 1. Plain-language outcome

Every real conversational turn today mints a fresh random request id — `app.py:2618`, `task_id = f"cv_{tick}_{uuid4().hex[:8]}"` — unique for every utterance, even byte-identical text typed twice. That id flows unchanged through the scheduler into the engine's scene builder, and `_scene_descriptors` (`clean_conversation_engine.py:355`) uses `hashlib.sha256(task_id.encode()).digest()` as the seed for the scene's **real sensory content**: the sight fill-value, the visual saccade seed, and the auditory born-tick (`clean_conversation_engine.py:392,396–398`). So the same real words, typed twice, are handed two completely different manufactured "sensory" scenes. Their full-field expressions are numerically different, and recognition — which operates on the numeric field, not on any id — can therefore never see the two utterances as the same recurring pattern. This is not a defect in recognition or growth; it is a defect in the *input* those correct mechanisms receive.

**The correct reframing (confirmed against the code, §3, not assumed):** this is **not** "two different real utterances must recognize as the same experience." Two different moments in time, with no shared real sensory grounding, genuinely *are* distinct experiences, and forcing them to be identical would itself be a fabrication. The real defect is narrower and exactly locatable: **when no real camera/mic is attached to a turn (which is every turn today — the live translators exist but are not wired to live input), the five sensory lanes should report a *fixed, reproducible, honest* "nothing real sensed" reading, not a randomly-varying one that manufactures fake sensory diversity where none exists.** `_scene_descriptors` invents per-request random variation in precisely the place a constant belongs.

The fix removes the request id's *physical authority* over sensory content while leaving its *bookkeeping* role (polling, logging, and the receipt-identity naming that correctly distinguishes distinct moments) entirely intact. It is confined to one function's body plus a signature change threaded through three call sites. It touches no physics, no recognition rule, no receipt schema.

---

## 2. The decision, up front

- **Chosen:** make `_scene_descriptors`'s per-instant descriptor **values** (`visual_fill_value`, `visual_seed`, `auditory_born_tick`) a **fixed canonical constant sequence indexed by instant position only**, with no dependence on `task_id`. Drop `task_id` from the function signature entirely so the "the transport id has no physical authority" invariant is enforced structurally (you cannot pass it), not by convention. Update the three call sites (`_build_turn_expression`, `_build_genesis_scene`, `_rebuild_scene`) to call `_scene_descriptors(count=valid_count)`. This makes the numeric sensory field content identical for every turn of a given length, so recognition can identify a recurring language pattern across distinct moments.
- **Rejected — deriving sensory content from the text/word content.** Explicitly and repeatedly prohibited by this session's own established rule ("no sensory value is ever derived from the text content itself" — the module's own docstring, `clean_conversation_engine.py:382`). Fixing the request-id defect must not violate the text-content prohibition.
- **Rejected — genuinely *absent* sight/sound (passing `visual_fragment_receipt=None` / `auditory_fragment_receipt=None`).** This is the boundary owner's real, already-defined "no capture this instant" path (`six_sense_boundary_owner.py:214–234`) and is the most *semantically* honest "nothing sensed." It is **rejected for this fix** because it is not viable on the engine's evolution path: an absent sight/sound port produces a 3-port evolved frame, and `build_story_frozen_kernel_inputs` hard-requires every frame to cover *all five* manifest ports (`story_chemistry.py:1710–1720`; confirmed by `six_sense_boundary_owner.py:131–143`) — a 3-port frame fails closed. Making full absence viable would require reworking the evolve/bridge path, which is out of scope and higher-risk. The fixed-canonical-percept path keeps all five ports present with the exact same structure as today, changing only the *values*.
- **Rejected — a per-request nonce/counter for the sensory seed.** That is the current defect with a different name. Identity must come from a reproducible constant, not a fresh tag.

---

## 3. Verified findings (read from the real code; cited, not recalled)

### 3.1 The request id is minted fresh-random per turn, and it is genuinely load-bearing bookkeeping

The live embedded converse route mints `task_id = f"cv_{tick}_{uuid4().hex[:8]}"` (`app.py:2618`; siblings at `:2557` for the listen path, `:3702` for the feedback path). The **bookkeeping role is real and must not be eliminated**: the same string is immediately the key of the in-memory task registry `_converse_tasks[task_id] = {…}` (`app.py:2619`) and the value returned to the client as its `poll_url` (`app.py:2641`), consumed by the polling endpoint `GET /api/v1/gualaloom/task/{task_id}` (`app.py:3722–3723`). Two concurrent turns *must* have distinct ids or their poll results collide. So the fix **separates two roles the id currently conflates** — it does not remove the id:

| Role | Where | Must the id stay unique per request? | Touched by this fix? |
|---|---|---|---|
| **Bookkeeping / transport** | `_converse_tasks` key, `poll_url`, logging | **Yes** — polling correctness depends on it | No |
| **Receipt-identity naming** | `scene_id`, `event_id`, `source_epoch`, `grid_id`, `identity` in `_build_turn_expression` (`clean_conversation_engine.py:748,766,776–777,795`) | Yes, so distinct moments get distinct receipts (correct, §5) | No |
| **Sensory-content authority** | `_scene_descriptors`'s SHA-256 seed | **No — this is the defect** | **Yes — removed** |

### 3.2 The task id reaches `_scene_descriptors` unchanged, per real scalar

`_run_glew_converse_turn` passes the raw request id into `_glew_scheduler.run_turn(task_id=task_id, …)` (`app.py:416–419`). The scheduler derives one per-scalar id `default_scalar_task_id(task_id, index) = f"{task_id}-scalar-{index:04d}"` (`multi_scalar_turn_scheduler.py:174–184,361–364`) — still carrying the random UUID, still unique per real request — and builds each `CleanConversationTurn(task_id=scalar_task_id, …)` (`multi_scalar_turn_scheduler.py:381–395`). `_build_turn_expression` then calls `_scene_descriptors(turn.task_id, count=valid_count)` (`clean_conversation_engine.py:745`).

### 3.3 `_scene_descriptors` derives real physical percepts from the SHA-256 of that id — the exact defect

`_scene_descriptors` (`clean_conversation_engine.py:355–403`) computes `digest = hashlib.sha256(task_id.encode("utf-8")).digest()` (`:392`) and, per instant, `byte = digest[index]` (`:395`), then:
- `fill_value = 0.15 + (byte / 255.0) * 0.7` (`:396`) — the brightness of the emulated 16×16 camera frame (`real_experience_learning_pipeline._real_visual_fragment_receipt`, `:365–383`);
- `visual_seed = 10_000 + (index * 257) + byte` (`:397`) — the saccade/fovea RNG seed;
- `born_tick = index * 100 + byte` (`:398`) — the auditory fragment's birth tick (`_real_auditory_fragment_receipt`, `:393–414`).

All three physical values are seeded by `byte`, which is seeded by the random `task_id`. **These are the real physical percepts fed into the field.** Two turns with identical text but different `task_id` get different `byte` sequences, hence different sight/sound percepts, hence numerically different fields.

**One field of `_scene_descriptors` is already correct and must be left alone:** the touch/smell/taste values, `_SOMATIC_ROTATION[index % len(_SOMATIC_ROTATION)]` (`:399`; table at `:266–272`), are indexed by **instant position only** — already `task_id`-independent. Only sight/sound (`fill_value`, `visual_seed`, `born_tick`) carry the defect.

### 3.4 Recognition operates on the numeric field, not on any receipt id — so removing the seed's authority is sufficient to fix recognition

`_run_locked` feeds the built expression to `evaluate_expression_mode_boundary(input_expression=expression, …)` (`clean_conversation_engine.py:845–854`). Inside, the input becomes a numeric vector via `present = field(input_expression)` (`expression_modes.py:878`), where `field()` = `evaluate_closed_experience_in_arb(expression, …)` and the `receipt_sha256` is used **only as a memo key** (`expression_modes.py:836–848`). Recognition's whole decision — orthogonal residual against the basis, Gram activation energies, certified-positive/zero predicates — is arithmetic over that numeric vector (`expression_modes.py:850–909`).

Crucially, the numeric field is **source-driven with a trivial evolution operator**: `_build_expression` builds each step with `hamiltonian=()`, `local_rates=()`, and `source = source_coefficients_for_injection(event.injection, …)` (`real_experience_learning_pipeline.py:690–728`). The `authority_id = f"{identity}:field:{index:08d}"` and every other `task_id`-derived naming string enter only the **receipt payloads** (`:695–711`), never the numeric evolution. Therefore the numeric field content is a function of exactly: the injection coefficients (from the sensory descriptors + the language scalar + the chemistry runtime), the topology dimension, and the zero initial state — **none of which depends on `task_id` once the descriptors do not.** Fixing `_scene_descriptors` makes `field(input_expression)` identical for two same-text turns, so recognition (numeric) recognizes them as the same mode. This is the direct, sufficient repair of the reviewer's stated harm.

### 3.5 Genesis and the seeder already use fixed, non-request ids — the defect is confined to the live conversational entry point

`_build_genesis_scene` is invoked with `root_scene_id = f"{engine_id}-genesis-root"` and `bootstrap_scene_id = f"{engine_id}-genesis-bootstrap"` (`production_runtime_bootstrap.py:459–462,536–586`; genesis texts `"a"`/`"b"`, `:220–221`) — **deterministic, `engine_id`-derived, never a request UUID.** The one-time seeder re-derives that same deterministic genesis and learns its single successor over the `"b"` genesis scene, all off `calibration.ENGINE_ID` (`seed_first_production_successor.py:236–260`) — again no request id. So genesis and the seeder are already *reproducible*; they are **not** the site of the defect. The defect is solely the live `run_clean_conversation` entry point, where the descriptor seed is the random request UUID.

**But note (real interaction, not a free pass):** because `_build_genesis_scene` also calls `_scene_descriptors` (`:480`), the fix *does* change genesis scene content — genesis `"a"` and `"b"` currently get two *different* sensory scenes (SHA of two different fixed ids); after the fix they get the *same* fixed sensory scene and differ only in their language lane. That is the intended, honest end state, but it has a real consequence analysed in §6 and §7 (the two bootstrap modes must still certify as an independent basis using the language lane alone) and forces a genesis reseed (§7).

### 3.6 The boundary owner already defines what "nothing sensed" means for each sense — the fix reuses that semantics, it does not invent one

`observe_six_sense_boundary` (`six_sense_boundary_owner.py:208–249`) already distinguishes three honest cases:
- **Sight/sound absent:** `visual_fragment_receipt=None` / `auditory_fragment_receipt=None` is "no real capture this instant — a legitimate absence, not an error; that port is simply left out" (`:228–234`).
- **Sight/sound present:** a real fragment was supplied and must translate or fail closed.
- **Touch/smell/taste quiet:** a `None` descriptor is "no active event," which `somatic_boundary.py` turns into a **real zero-flux natural-decay observation** — not missing evidence (`:236–239`; proven by `test_somatic_boundary.py::test_repeated_zero_flux_observations_prove_real_relaxation_toward_rest`).

So a real "absent/quiet" observation type already exists. The reason this fix does **not** route sight/sound through the `None` path (and instead supplies a *fixed canonical* fragment) is the all-five-port frame requirement of §2's third rejected option — a hard, code-confirmed constraint (`story_chemistry.py:1710–1720`). The fix's fixed-canonical percept is the honest reproducible stand-in that keeps all five ports present; the truly-absent path is named as the eventual target once the evolve/bridge path can carry sub-five-port frames (a separate, larger change).

---

## 4. The fix — concrete, minimal, named

### 4.1 The one function that changes

`clean_conversation_engine._scene_descriptors` (`:355–403`). New signature and body:

```python
def _scene_descriptors(*, count: int = _SCENE_INSTANT_COUNT) -> tuple[InstantDescriptor, ...]:
    """`count` real, deterministic instant descriptors representing the fixed,
    reproducible "no real camera/mic attached this turn" sensory reading.

    Derived from the instant POSITION only -- never from the turn's transport
    id (removed: the request UUID must have no physical authority) and never
    from the turn's text content (the standing prohibition). The same canonical
    scene is produced for every turn of a given length, so recognition can see
    a recurring language pattern across distinct moments; distinct MOMENTS are
    still distinguished, correctly, by their receipt identity (see design §5),
    not by manufactured sensory noise.
    """
    if not isinstance(count, int) or count < 2:
        raise ReceiptError("scene descriptor count must be a real integer of at least two ...")
    descriptors = []
    for index in range(count):
        fill_value = _CANONICAL_ABSENT_FILL_VALUE                 # e.g. 0.15, a fixed uniform frame
        visual_seed = _CANONICAL_ABSENT_VISUAL_SEED_BASE + index * 257
        born_tick = index * 100
        touch, smell, taste = _SOMATIC_ROTATION[index % len(_SOMATIC_ROTATION)]   # UNCHANGED
        descriptors.append(InstantDescriptor(fill_value, visual_seed, born_tick, touch, smell, taste))
    return tuple(descriptors)
```

The mechanical essence is a **one-line deletion** (`digest = hashlib.sha256(task_id…)`) and replacing `byte = digest[index]` with the fixed constant `byte = 0` folded into the existing formulas — the descriptor formulas, the `InstantDescriptor` shape, and the somatic rotation are otherwise byte-identical. Per-instant variation is preserved through `index` (visual_seed and born_tick still differ per instant, so intra-scene "change" — which frozen L0–L4 evaluates — is unaffected); only the cross-request random variation is removed. The `count` parameter is retained exactly as-is: it still equals the scalar's own valid-trit-place count (tonight's earlier, correct, orthogonal fix), so scenes still have the right length per scalar.

### 4.2 The three call sites (signature-thread only)

- `clean_conversation_engine._build_turn_expression:745` → `_scene_descriptors(count=valid_count)` (drop `turn.task_id`).
- `production_runtime_bootstrap._build_genesis_scene:480` → `_scene_descriptors(count=valid_count)`.
- `coexperienced_scene_recall_executor._rebuild_scene:389` → `_scene_descriptors(count=valid_count)`.

Every other use of `turn.task_id` / `scene_id` / `episode.scene_task_id` in those three functions (the `scene_id=`, `event_id=`, `source_epoch=`, `grid_id=`, `identity=` naming strings) is **left unchanged** — that is the bookkeeping/receipt-identity role the reviewer explicitly permits, and it is correct that distinct moments carry distinct receipts (§5). The test helper `test_clean_conversation_engine._build_scene:197–236` and its `_scene_descriptors(task_id, …)` call (`:211`) update the same way.

### 4.3 What "canonical absent" value to pick

Any fixed, reproducible constant is correct; the honest choice is the least-suggestive one — a uniform/neutral fill value and a fixed base seed, held in two named module constants (`_CANONICAL_ABSENT_FILL_VALUE`, `_CANONICAL_ABSENT_VISUAL_SEED_BASE`) so the "this is the placeholder standing in for absent real capture" intent is legible and greppable. (A strictly-more-honest variant — a near-silent auditory fragment via `sound_boundary`'s already-real "captured and near-silent" path, `sound_boundary.py:28`, and touch/smell/taste switched to the `None` natural-decay reading — is a small adjacent purity improvement, named here but not required for this fix, since those lanes are already `task_id`-independent and thus not part of the defect.)

---

## 5. Distinct moments stay distinct — and that is correct, not a residual bug

A subtle, important point the ratifier must see stated plainly: after this fix, two same-text live turns produce an **identical numeric field** (so recognition matches — the fix's goal) but **different receipt hashes**, because the receipt-identity strings (`event_id`, `source_epoch`, `identity`, …) still carry the two different request ids. Those id-carrying strings flow into `input_expression_receipt_sha256` and `sensory_evidence_receipt_sha256s`, which are exactly the two receipts the successor-keying **reproducible match sub-digest** folds (`recall_reentry._reproducible_match_object:238–262`, part of commit `3ff6745`). So the two turns have **different transition-context match digests** → they learn **distinct sibling successors** of the (same) recognized mode, rather than colliding.

This is **correct** per the reframing, and per commit `3ff6745`'s own design intent:
- **Recognition** (numeric) answers "which recurring pattern is this?" — now correctly "the same mode" for the same words. This is the harm the reviewer reported ("can never be recognized as the same experience"), and it is fixed.
- **Transition-context keying** (receipt, id-bearing) answers "is this the same *moment/experience*?" — correctly "no, a new moment," so a distinct successor is learned. Two genuinely different moments in time *are* different experiences (the reframing); keying them separately is faithful, not a fabrication.

The "identical experience twice **collides**" guarantee in the mode-growth design (§5.3 of the v2 doc) refers to the **recall re-run** replaying the *same archived id*, which correctly reproduces the same match digest — not to two distinct live utterances. There is therefore **no residual defect** here and **no further change required**: the id-bearing receipt naming should *remain*. Removing it would be over-reaching past the reviewer's instruction (id "may remain bookkeeping") and would destabilise the recall subsystem, which depends on reproducing those exact receipts from the archived id (§6).

---

## 6. Recall-side reconstruction is confirmed UNAFFECTED (and slightly more robust)

`coexperienced_scene_recall_executor._rebuild_scene` reconstructs an archived scene from `episode.scene_task_id` and `episode.scene_language_text` (`:383–439`), calling `_scene_descriptors(task_id, count)` (`:389`) and reusing the archived id for all naming (`event_id=f"{task_id}-language"`, `identity=episode.scene_task_id`, `:408,437`). Two independent reasons this is safe under the fix:

1. **Sensory content:** recall recomputes descriptors for a scene it is *replaying*. Before the fix, descriptors were `SHA(archived_task_id)` — reproducible only because recall reused the exact archived id. After the fix, descriptors are a function of `count` alone, and `count` is derived from `episode.scene_language_text` (`:387–388`). So recall reproduces the **same** descriptors it will have at learn time — in fact **more** robustly, because reproduction no longer depends on threading the exact id string into a hash; it depends only on the archived text's length, which recall already holds.
2. **Receipt identity:** the id-bearing naming strings are reproduced bit-for-bit because recall reuses `episode.scene_task_id` verbatim (unchanged by this fix). So the reconstructed `sensory_evidence_receipt_sha256s` still equal the learned binding's — the settlement's mandatory equality (`recall_reentry.py:686`, the executor's own step-7 tripwire) still holds by construction.

The recall executor's `_scene_descriptors(task_id, …)` call simply becomes `_scene_descriptors(count=…)`; the local `task_id = episode.scene_task_id` variable stays (it still names the reconstructed receipts). **No recall-side problem is introduced, and none pre-exists here.** This directly satisfies the reviewer's "carry that same identity through recall resolution": recall's identity is the archived scene's own reproducible (text + fixed-sensory + chemistry) content, and the fix strengthens, not weakens, that reproducibility.

---

## 7. The honest hard question — does a fixed sensory scene make growth degenerate? (step 7)

After the fix, **every text-only turn shares the exact same sensory field**; the *only* per-turn-varying signal in the numeric field is the language lane. This is honest (it is genuinely the one real varying signal that exists until camera/mic are wired), but it must be checked against the certified-residual arbiter now live in `expression_modes.py` (commit `3ff6745`), because a fixed sensory scene is **not automatically safe** — it concentrates *all* structural distinctness into one lane. Reasoned through the real mechanism:

**7.1 Growth is not structurally degenerate.** Growth fires when `_certified_positive(residual)` — the input's orthogonal residual against the whole basis is certified strictly positive (`expression_modes.py`, arbiter branch `:1021`). The field is exact-rational arithmetic (python-flint) over exact balanced-ternary language injections, so **genuinely distinct language content produces an exactly linearly-independent language field vector**, hence an exactly-positive residual energy, certifiable at sufficient precision through the arbiter's **existing precision-doubling loop**. The language fiber is 19-dimensional (per the v2 design §3.3); two bootstrap modes span a 2-D slice of it, so a third distinct scalar is generically outside their span. Growth is therefore reachable, not structurally blocked, under fixed sensory.

**7.2 But the working-precision behaviour is a real, must-test open question.** The v2 design (§3.2/§3.3) observed live that residuals *straddled zero* at working precision even *with* the old random sensory — i.e. the sensory noise was not, in practice, supplying certifiable orthogonal energy. Removing it concentrates the whole decision on the language lane. Two outcomes, both non-catastrophic:
- **(a) language certifies positive** at working precision (possibly after refinement): a genuinely novel scalar **grows** its own mode; repeats **recognize**; sibling successors (§5) handle recurrences. Clean, desired.
- **(b) language straddles zero** at available precision: the arbiter refines, and on exhaustion returns `AMBIGUOUS_SILENCE` (honest silence) or `RECOGNIZED` against the nearest mode, whereupon transition-context keying (§5) learns a sibling successor. The bank may not grow past its bootstrap rank, and "growth per distinct word" is effectively deferred — a **degraded but non-crashing, non-fabricating** state.

**7.3 The fix is a strict improvement over the pre-fix baseline in every case.** Pre-fix (v2 §3.2): random sensory, residuals straddled zero, bank stayed at rank 2, and under the *old* winner-take-all rule turns were force-`RECOGNIZED` and **crashed** on the one-successor cap. Post-fix + the live `3ff6745` arbiter/Req-2: the crash is gone (multi-successor keying), same-text recognition is now *possible* (was impossible under random sensory), and growth is either clean (7.2a) or gracefully deferred (7.2b). The fix never makes growth *worse* than the random-sensory baseline; it makes the growth signal **cleaner** (purely the honest language signal).

**7.4 The one genuinely new risk this fix introduces — and it lands at genesis, not live.** Under fixed sensory, genesis `"a"` and `"b"` differ **only** in their language lane (§3.5). Bootstrap must still grow the mode bank rank 0→2, i.e. certify `"b"` as an independent second basis mode against `"a"` **using the language lane alone**. With the old code they *also* differed in random sensory, which could have been the energy that made them certifiably independent. So the honest worst case is: **if the language lane alone cannot certify an independent basis at working precision, genesis bootstrap itself could fail to produce two independent modes.** Given exact arithmetic (7.1) the language vectors *are* exactly independent, so this should certify with refinement — but it is the single load-bearing empirical assumption and **must be proven by test G0 before this fix is ratified**, not assumed. If G0 fails, the finding is deeper than this fix: it says the sensory lanes were silently carrying the distinctness the system relies on, and the real unblock is wiring genuine camera/mic signal (a separate, already-tracked, larger gap) rather than any change here — a conclusion this design surfaces honestly rather than papering over.

---

## 8. Blast radius and risk — stated honestly

- **Code contained to one function body + a signature threaded through three call sites and one test helper.** No physics file, no recognition rule, no commit conjunction, no receipt schema, no `expression_modes.py`, no `recall_reentry.py`, no `expression_learning.py`. `InstantDescriptor`, the somatic rotation, `_evolve_real_causal_window`, `_build_expression`, `_seal`, and every receipt payload shape are untouched. If wrong, revert is a one-function diff.
- **Genesis reseed required (schema-real, but not a live-data event today).** The fix changes the genesis scenes' sensory content, hence the bootstrap mode-bank vectors, hence every downstream receipt derived from them. Any checkpoint/archive persisted under the old `_scene_descriptors` is content-incompatible and must be regenerated by a fresh genesis (`bootstrap_genesis_learned_binding_state`) + reseed (`seed_first_production_successor`). Because production is `GLEW_CONVERSATION_ENGINE_ENABLED=0` and nothing is live or persisted, this is a build-time reseed, not a migration of live state. The v2/v1 designs already call for a genesis reseed for their own schema change, so this rides the same reseed — **sequence this fix into the same reseed as `3ff6745`'s deployment**, not as a separate one.
- **Compatibility with the just-landed `3ff6745` (mode-growth arbiter + successor keying) — confirmed compatible, and complementary.** `3ff6745`'s two fixes assume the *recognition input* is well-formed; they cannot help if the input carries manufactured per-request sensory noise. This fix repairs exactly that input. Read together: this fix makes same-text turns recognize as the same mode (numeric); `3ff6745`'s Req-2 keying then correctly stores each distinct *moment* as a sibling successor; `3ff6745`'s Req-1 arbiter decides growth-vs-recognition from the now-honest (language-only) residual. The one coupling to verify is §7's G0 (genesis bootstrap still certifies two independent modes under fixed sensory) — that is the sequencing gate.
- **Recall subsystem (v1 design) — unaffected and slightly hardened** (§6). Its settlement equality still holds by construction; reproduction no longer depends on threading the id into a sensory hash.
- **Fail-closed discipline preserved throughout.** If anything downstream is wrong, it surfaces as a typed `ReceiptError` at a `verify()`/preparation/settlement boundary — typed silence, never a silent wrong emission.

---

## 9. Test plan (step 8) — genuine, non-monkeypatched, real-entry-point proof

Every test drives real objects end-to-end (real mount, real recognition/commit/learn, real reconstruction). None monkeypatches recognition, commit, or recall; none uses a single literal `task_id` twice to *simulate* a replay — that literal-id shortcut is precisely the blind spot this whole finding exposed (`test_clean_conversation_engine._build_scene` took a `task_id`, so every "same scene twice" test reused one string, a condition live traffic never produces).

- **G0 — genesis bootstrap certifies two independent modes under fixed sensory (the ratification gate, §7.4).** Cold-start `bootstrap_genesis_learned_binding_state` with the fixed-sensory `_scene_descriptors`; assert the mode bank grows rank 0→2 (both `"a"` and `"b"` become distinct certified modes) and the seeder's first successor learns. If this fails, the fix is not ratifiable as-is and §7.4's deeper finding stands.
- **G1 — identical text, two REAL distinct request ids, identical *sensory evidence* (the headline test).** Build two turns through the real production entry path with two **different** ids minted the way `app.py` mints them (the real `f"cv_{tick}_{uuid4().hex[:8]}"` pattern — *not* a test-chosen fixed string), same text. Assert: (a) their numeric `field(input_expression)` vectors are **identical** and recognition selects the **same** mode with **certified-zero residual** between them; (b) their reconstructed **sensory** evidence *content* is identical even though their sensory evidence *receipt hashes* differ (the id-bearing naming, correctly, §5); (c) each learns a **distinct sibling successor** (distinct transition-context match digest), and neither raises the one-successor collision.
- **G2 — genuinely different text still differs honestly.** Two turns, different real ids, **different** text. Assert the numeric field differs **only** through the language lane (the fixed sensory descriptors are byte-identical between them), and the arbiter's outcome (grow vs recognize) is driven purely by the certified language residual — record which of §7.2 (a)/(b) actually occurs at working precision, as the empirical answer to the degenerate-growth question.
- **G3 — recall reconstructs bit-for-bit (unaffected, §6).** Learn a scene; archive it; run the recall executor; assert reconstructed descriptors, sensory evidence receipts, and the settlement's `sensory_evidence` equality all hold — and that mutating the archived text (hence `count`) is the only thing that changes the reconstructed sensory scene, proving `task_id` no longer has sensory authority even on the recall path.
- **G4 — the transport id retains zero physical authority, directly.** Assert that `_scene_descriptors` no longer accepts a `task_id` argument (signature test), and that two engines fed the same text under different ids produce identical grown mode-bank vectors (numeric), differing only in receipt identity — the machine-checkable statement of "the request UUID has no physical authority."

---

## 10. Summary for the ratifier

- **Reframing — confirmed** (§1, §3): the defect is not "different utterances must recognize as the same." It is that `_scene_descriptors` manufactures **random per-request** sensory content (`clean_conversation_engine.py:392,396–398`, seeded by the `uuid4` request id, `app.py:2618`) where, with no camera/mic wired, a **fixed reproducible "nothing real sensed" reading** belongs. Recognition operates on the numeric field, which the random seed corrupts (§3.4).
- **Fix — chosen** (§4): drop `task_id` from `_scene_descriptors` and make the sight/sound descriptor values a fixed canonical constant sequence indexed by instant position only; leave the already-`task_id`-independent somatic rotation, the receipt-identity naming, and `count` untouched. A one-function change threaded through three call sites; no physics, no recognition, no schema, no recall change. (Genuinely-absent sight/sound rejected only because the bridge hard-requires all-five-port frames, `story_chemistry.py:1710–1720`.)
- **Recall — confirmed safe** (§6): the recall executor reuses the archived id verbatim for naming and now reproduces sensory content from `count`/text alone — *more* robust, not broken. Settlement equality holds by construction.
- **Degenerate-growth question — answered honestly** (§7): a fixed sensory scene is not automatically safe; it concentrates all distinctness in the language lane. Under exact arithmetic growth is not structurally degenerate, and the fix is a strict improvement over the crashing random-sensory baseline in every case — but the load-bearing empirical assumption (language lane alone certifies an independent basis, at genesis and for novel scalars) **must be proven by test G0/G2 before ratification**; if it fails, the honest conclusion is that real camera/mic signal — not any change here — is the true unblock.
- **Sequencing:** ride the same genesis reseed as commit `3ff6745`; complementary to it, not conflicting.
- **Status:** `proposed_pending_ratification` — implementation is a later, separate dispatch.
