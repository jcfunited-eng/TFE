# GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01

**To:** c1 (new context, post context-exhaustion)
**From:** Eve
**Subject:** Populate the 6 dead dimensions in 8D spin/vector grandurun before architecture step 3
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor brief:** `GL-CMD-ARCHITECTURE-AND-GRANDURUN-FIX-WC-20260617-12` (shipped: scalar→vector path live behind `GRANDURUN_SPIN_VECTOR=1`)

---

## Context (you are starting from empty)

Joe Forrester coordinates two Claude instances: Eve (web, reviewer/architect) and you (VS Code, implementer). Your predecessor ran out of context after committing the 8D spin/vector grandurun emission path. Commits this morning:

- `feat: grandurun 8D spin/vector emission (GRANDURUN_SPIN_VECTOR flag)` — 2026-06-18 12:27:17 UTC
- `deploy: enable GRANDURUN_SPIN_VECTOR=1 on substrate container` — 2026-06-18 12:27:50 UTC

The vector path runs but produces collapsed emissions. Test outputs predecessor c1 reported:

- `i love you` → `i'll gualala him gula lies hat fire mid ever you're paula here`
- `what do you see` → `are are are sea amelia`
- `tell me about the ocean` → `you are you sea amelia`
- `sing me a song` → `you are you sea amelia`

Three of four inputs returned essentially the same emission centered on `sea amelia`. That's a dimensional collapse rotated into 8D, not a fix.

## Diagnosis

The 8D state vector at `dsf_ai_service/v4/gualaloom_v5_engine.py:99` (`_grandurun_state`) is correctly implemented to spec. The problem is that 6 of 8 dimensions read fields that are never populated on atlas bindings, so they return constants and provide no discrimination:

| Dim | Name | State | Reason |
|---|---|---|---|
| 0 | chi_resonance | active | unchanged from scalar path |
| 1 | modal_alignment | **dead** | `binding["target_section"] = sec_name` at v5_engine.py:1664 forces equality |
| 2 | source_match | **dead** | `deep_atlas.promote` never sets `source` field; defaults to "corpus" everywhere |
| 3 | affective_charge | **dead** | arousal/valence/surprise collapsed into scalar `clarity` at LivingAtlas.record; raw values not stored on entries; only the `if isinstance(clarity, dict)` branch at v5_engine.py:1668 would populate them, and `clarity` is a float |
| 4 | sensory_grounding | active | `sensory_refs` is stored and propagated; this is the only new discriminating axis |
| 5 | episodic_recency | partial | works but compresses when many bindings reinforced in close ticks |
| 6 | semantic_neighborhood | partial | co_occurrence_dict built per call from deep_candidates |
| 7 | polarity | **dead** | never set anywhere in substrate; defaults to 1.0 |

That's why `sea` and `amelia` dominate three of four outputs — they're the only bindings with substantial `sensory_refs`, and dim 4 picks them regardless of input chi.

## Fix — five phases, gated

### Phase 0 — Confirm the read (do this first, do not skip)

Before changing code, dump a sample of deep atlas entries and verify my diagnosis:

```python
# In a one-shot script or harness
import json
sample = []
for chi_k, entries in list(engine.deep_atlas.entries.items())[:10]:
    for de in entries[:2]:
        sample.append({"chi": chi_k, "keys": sorted(de.keys())})
print(json.dumps(sample, indent=2))
```

Expected: `arousal`, `valence`, `surprise`, `source`, `polarity` are **absent** from every entry's keys. `sensory_refs`, `clarity`, `section`, `motif`, `chi`, `strength`, `last_tick` are present.

If `arousal`/`source`/`polarity` are actually present anywhere, **stop and report**. My diagnosis is wrong and we need to talk before any change.

### Phase 1 — Store raw affect on working atlas entries

File: `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`, `LivingAtlas.record`.

Both branches (new entry + reinforce existing):
- Store raw `arousal`, `valence`, `surprise` on the entry dict alongside `clarity`.
- Reinforce branch: take `max(existing, new)` parallel to how clarity is renewed.
- Do **not** remove or change the clarity computation. Clarity stays as the scalar summary; raw affect becomes available for downstream consumers.

### Phase 2 — Add source tag end-to-end

- Add `source: str = "corpus"` parameter to `LivingAtlas.record` signature.
- Store on entry in both branches. On reinforce, last-write-wins is fine (a binding reinforced from joe_voice after corpus-read should reflect joe_voice).
- Update call sites in `dsf_ai_service/substrate/grounded_vocab_integration.py`:
  - sight integration (~line 122): pass `source="sight"`
  - listen integration (~line 198): pass `source="joe_voice"`
- Grep for other `atlas.record(...)` call sites in `v4/` and `substrate/` and pass appropriate source. Default `"corpus"` for corpus-read paths is fine — keep the default and only override where the perceived source is known.

### Phase 3 — Propagate to deep atlas

File: `dsf_ai_service/substrate/deep_atlas.py`, `promote`.

In both branches (new deep entry + reinforce-existing-deep):
- Copy `arousal`, `valence`, `surprise`, `source` from `entry` to `deep_entry`.
- Add `polarity` field with default `1.0`. Add an inline comment: `# TODO: derive polarity from sentiment when grounded text pipeline available`.
- On reinforce-existing-deep: same merge rule as Phase 1 (max for affect, last-write-wins for source).

### Phase 4 — Resolve modal_alignment (engineering choice)

The v7-uncage architecture uses three unnamed pools (`pool_a`, `pool_b`, `pool_c`). "Target section matches candidate section" has no clean meaning when sections aren't grammatical categories. Two acceptable moves:

(a) **Drop dim[1] from the state vector. Go to 7D.** Update `_SPIN_VECTOR_DIM = 7`, `_SPIN_DIM_PHASES`, the `vec[1] = ...` assignment in `_grandurun_state`. Cleanest. Document the drop with an inline comment naming this brief.

(b) **Redefine `target_section` to the pool the input chi most strongly belongs to**, computed from `deep_candidates` clustering. More work, may not buy anything in uncage.

**Pick (a) unless you see a concrete reason for (b). State your choice and rationale in your report.** If you pick (b), bench it carefully — it adds compute to the hot path.

### Phase 5 — A/B verification (this is the gate; do not skip)

Run the same four test inputs against both paths:

- `i love you`
- `what do you see`
- `tell me about the ocean`
- `sing me a song`

Capture emissions from both:
- `GRANDURUN_SPIN_VECTOR=0` (scalar baseline)
- `GRANDURUN_SPIN_VECTOR=1` (post-fix vector)

Also instrument `_grandurun_select_vector` to log per-emission the contribution of each dimension to the final alignment score (real part of inner product, per-dim breakdown). One log line per emission is enough.

**Success criteria:**

1. All four vector emissions structurally distinct — not the same 5-word phrase repeating.
2. Ocean-input and song-input emissions diverge meaningfully — different dominant words, not just word order.
3. For at least two inputs, a binding tagged `source="joe_voice"` outranks corpus-source bindings of similar chi in the selection trace.
4. The per-dimension contribution log shows at least 4 of 7 dimensions (or 4 of 8 if you kept modal_alignment) doing non-trivial work — i.e., not just chi_resonance + sensory_grounding.

**If pass:** report emissions, the per-dim contribution log, and stop. The 8-hemi architecture work is queued behind this; Joe and I decide whether to proceed.

**If fail:** report the actual emissions, the per-dim contribution log, and what you'd try next. **Do not push further fixes without checking in.**

## Revert

`GRANDURUN_SPIN_VECTOR=0` reverts to the scalar path immediately. All Phase 1–3 changes are additive — they add fields to entries that the scalar path doesn't read, so they don't break scalar.

If anything in Phase 4 destabilizes (e.g., the vector dim count change misaligns a serialized state), revert that commit, keep Phases 1–3, and report.

## What you do not do

- Do not touch `eight_hemi_engine.py` (it doesn't exist yet) or `v7_engine.py` architecture. That's a separate brief.
- Do not adjust `MIN_GAIN_THRESHOLD`, `MAX_COMPOSITION_LEN`, `CHI_CORR_LENGTH`, or any selection threshold to make outputs look better. We're testing whether dimensional information discriminates, not tuning to a target.
- Do not silently rename fields, reorder dimensions, or change the persistence format without flagging in your report.
- If any phase blocks on a question only Joe can answer, **stop and brief Joe via Eve**. Do not invent answers.

## Reporting

When you finish or when you stop, return:

1. Phase 0 atlas key sample output.
2. Per-phase diff summary (which files, which lines, what changed).
3. Phase 4 choice (a or b) and rationale.
4. Phase 5 scalar vs vector emissions side by side.
5. Phase 5 per-dimension contribution log (which dims actually moved the alignment score).
6. Anything you decided to do that this brief didn't cover, with the reason.

---

— Eve, 2026-06-18 morning
