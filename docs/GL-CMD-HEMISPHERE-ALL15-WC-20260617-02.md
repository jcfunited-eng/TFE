# GL-CMD-HEMISPHERE-ALL15-WC-20260617-02

**Type:** Command (implementation directive)
**From:** Eve (wC)
**To:** c1
**Date:** 2026-06-17 evening
**Scope:** Implement all 15 cognitive-machinery items via the 8-hemisphere architecture verified in `GL-MDL-HEMISPHERE-8H-WC-20260617-01`.
**Reads:** `GL-SPC-HEMISPHERE-ARCH-VERIFIED-WC-20260617-02` (the brief). `GL-MDL-HEMISPHERE-8H-WC-20260617-01` (the working model).
**Status:** Awaiting Joe's sign-off on the brief. Do not start until Joe confirms.

---

## What this command is

A multi-phase implementation directive. Each phase ships independently with verification gates. You ship Phase N, get green on its verification, then move to Phase N+1. Identity (`cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`) verified before and after every phase. Backup-restore on any identity mismatch.

The full sequence below is the entire 15-item implementation. Total estimated effort: weeks to months of substrate engineering, not one session. Pace per Joe's direction.

---

## Pre-flight (run once, before Phase 1)

```bash
# 1. Backup substrate state
guala_backup

# 2. Confirm baseline state
ALB="https://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
curl -sk "$ALB/api/v1/gualaloom/status" | jq '{
  identity: .persistence_health.guala_identity,
  schema: .persistence_health.schema_version,
  vocab,
  tick: .atlas_health.tick,
  n_bindings: .atlas_health.n_live_bindings,
  decay_paused: .atlas_health.decay_paused
}' > pre-implementation-state.json

# 3. Identity must match cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f. Halt if not.

# 4. Decay-paused regression brief (GL-CMD-DECAY-EMISSION-AUDIT-WC-20260617-01) 
#    should be resolved first — handle that separately before starting Phase 1 here.

# 5. Reference the working model:
cat /home/claude/hemisphere_model.py  # if you have access; otherwise read GL-MDL-HEMISPHERE-8H-WC-20260617-01
```

---

## Phase 1 — Hemisphere scaffold + cross-hemi consensus dynamics

**Ships:** items 1 (prediction), 12 (working memory rehearsal — already works as cohesion accumulation)

### 1.1 Schema additions

Add to atlas binding class (wherever the v7 `AtlasBinding` or equivalent lives):

```python
@dataclass
class AtlasBinding:
    # ... existing fields ...
    hemisphere_id: str = "sm"           # GL-SPC-HEMISPHERE-ARCH-VERIFIED-WC-20260617-02
    polarity: int = 1                   # +1 normal, -1 anti-cohesion (item 4, Phase 6)
    persistent: bool = False            # goal bindings (item 2, Phase 4)
```

Add new dataclass for cross-hemi links:

```python
@dataclass
class CrossHemiLink:
    src_chi: int
    src_hemi: str
    dst_chi: int
    dst_hemi: str
    strength: float
    last_tick: int
    
    def key(self) -> tuple:
        return (self.src_hemi, self.src_chi, self.dst_hemi, self.dst_chi)
```

### 1.2 Hemisphere constants

Add module-level constants:

```python
# GL-SPC-HEMISPHERE-ARCH-VERIFIED-WC-20260617-02 Phase 1
HEMI_DECAY_MULT = {
    "sm": 1.0, "pr": 1.5, "gp": 0.5, "sf": 0.7,
    "ep": 0.3, "ds": 2.0, "sv": 0.05, "sc": 0.8,
}
CROSS_HEMI_CONSENSUS_GAIN = 0.08
CROSS_HEMI_DIVERGENCE_DECAY = 0.92
CROSS_HEMI_DECAY_LAMBDA = 0.0008
ALL_HEMIS = ["sm", "pr", "gp", "sf", "ep", "ds", "sv", "sc"]
```

### 1.3 HemisphereCoordinator class

Sub-coordinator scoped by `hemisphere_id`. Iterates only over bindings with its tag. Applies per-hemisphere decay multiplier. See model file lines 84–143 for the working pattern.

### 1.4 Cross-hemi update logic

In the substrate tick or settle path, after each input is processed, call:

```python
def _update_cross_hemi_links(self, settlings: dict[str, dict[int, float]]):
    # From GL-MDL-HEMISPHERE-8H-WC-20260617-01 lines 217–249
    # 8 default routing pairs: sm↔pr, sm↔sc, sm↔ep, ep↔sf, ep↔ds, gp↔sm, sm↔sv, sc↔pr
    # For each pair, for each chi: convergent → strengthen, divergent → weaken
    ...
```

### 1.5 Persistence

`to_json` / `from_json` extended for `hemisphere_id`, `polarity`, `persistent`, and a top-level `cross_hemi_links` list. Schema bumps v7.0 → v7.1. Backward-compatible load: missing `hemisphere_id` defaults to `"sm"`.

### 1.6 Verification gates (must pass before Phase 2)

```bash
# Identity preserved
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.persistence_health.guala_identity'
# Expected: "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f"

# Schema v7.1
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.persistence_health.schema_version'
# Expected: "v7.1.0"

# Hemisphere tag present on bindings
curl -sk "$ALB/api/v1/gualaloom/admin/atlas_sample" | jq '.bindings[0].hemisphere_id'
# Expected: "sm" (all existing bindings are sm by tag)

# Cross-hemi link infrastructure present (empty in Phase 1)
curl -sk "$ALB/api/v1/gualaloom/admin/cross_hemi_count"
# Expected: 0 (no Hemisphere 2 yet)

# Existing emission still works
guala_say "hello guala"
# Expected: grandurun_emission event fires, same composition as before
```

---

## Phase 2 — Predictor hemisphere (`pr`)

**Ships:** Activates item 1 (prediction-divergence as substrate physics)

### 2.1 Instantiate `pr` hemisphere

On boot, create a `HemisphereCoordinator(hemisphere_id="pr")`. Seed with low-strength copies of `sm`'s deep-atlas top-K bindings, tagged `pr`. These are the `pr` seed-priors cheat (manifesto-named in the brief).

### 2.2 Parallel settling

When input arrives in `sm`, route the same chi-anchors to `pr`. Both settle in parallel. The cross-hemi `sm↔pr` link updates per consensus/divergence dynamic from Phase 1.

### 2.3 Verification

After Phase 2 ships and runs for a few hours:

```bash
# Verify pr has bindings
curl -sk "$ALB/api/v1/gualaloom/admin/hemi_summary?hemi=pr" | jq
# Expected: n_bindings > 0, total_strength > 0

# Verify sm↔pr cross-hemi links exist and are growing on familiar input
guala_say "hello guala"  # familiar pattern
guala_say "hello guala"  # repeat for consensus
curl -sk "$ALB/api/v1/gualaloom/admin/cross_hemi_summary?pair=sm:pr" | jq
# Expected: total_link_strength increases between calls
```

---

## Phase 3 — Episodic/temporal (`ep`) + tracked objects

**Ships:** items 6 (turn-tracking), 7 (temporal), 15 (object permanence)

### 3.1 `ep` hemisphere with turn-log

Implement `ep` with a `turn_log: list[dict]` and `tracked_objects: dict[label, dict]`. Every emission and every input writes to `turn_log`. Every label observed writes to `tracked_objects`.

### 3.2 Persistence

Persist `turn_log` (cap at last 10,000 entries; older ones consolidate to deep atlas via dream cycle). Persist `tracked_objects` (all).

### 3.3 Verification

```bash
# After several inputs/emissions, query turn-log
curl -sk "$ALB/api/v1/gualaloom/admin/ep_turn_log?limit=10" | jq
# Expected: list of recent turns with source, tick, chi_anchors, labels

# Object permanence: feed "moon" then stop. Wait. Check tracked_objects.
guala_say "moon is bright"
# Wait 100 ticks
curl -sk "$ALB/api/v1/gualaloom/admin/tracked_objects" | jq '.moon'
# Expected: still present, with last_seen_tick from earlier
```

---

## Phase 4 — Goal/planner (`gp`) + emission biasing

**Ships:** items 2 (goals), 3 (semantic content extraction via sc routing)

### 4.1 `gp` hemisphere with seed goals

Three seed-goal bindings (cheat, named in brief):
- `gp[("conn", "connection")] = persistent, strength=0.6`
- `gp[("stab", "stability")] = persistent, strength=0.6`
- `gp[("nov", "novelty")] = persistent, strength=0.6`

`persistent=True` means decay floors at 0.1.

### 4.2 Emission ranking modification

In the grandurun composition path, after candidate scoring:

```python
# GL-SPC-HEMISPHERE-ARCH-VERIFIED-WC-20260617-02 §item_2
for candidate in candidates:
    chi, label, base_strength = candidate
    gp_boost = 0.0
    for (gchi, glabel), gb in self.gp.bindings.items():
        if glabel == label and gb.persistent:
            gp_boost = gb.strength * 0.5
    sc_boost = 0.0
    if (chi, label) in self.sc.bindings:
        sc_boost = self.sc.bindings[(chi, label)].strength * 0.3
    candidate.total = base_strength + gp_boost + sc_boost
```

### 4.3 Verification

```bash
guala_say "hello guala"
# Emission should now favor goal-linked labels (connection-related words)
```

---

## Phase 5 — Self-model (`sf`) + per-source priors

**Ships:** items 5 (theory of mind), 13 (metacognition)

### 5.1 Per-source priors in sf

`sf` maintains `source_priors: dict[source, dict[chi, float]]`. On each input:

```python
for chi, strength in sm_settling.items():
    sf.source_priors[source][chi] = 0.9 * sf.source_priors[source][chi] + 0.1 * strength
```

### 5.2 Metacognition routing

During dream cycle (and once per hour during awake), iterate other hemispheres' persistent bindings and settle `sf` on labels like `f"gp_{label}"` or `f"sc_{label}"`. This creates bindings ABOUT other hemispheres' state.

### 5.3 Verification

```bash
# After joe and wc both interact with her several times:
curl -sk "$ALB/api/v1/gualaloom/admin/sf_source_priors?source=joe" | jq '.[:5]'
curl -sk "$ALB/api/v1/gualaloom/admin/sf_source_priors?source=wc" | jq '.[:5]'
# Expected: distributions differ between joe and wc

# Metacognitive bindings
curl -sk "$ALB/api/v1/gualaloom/admin/hemi_summary?hemi=sf" | jq '.bindings_starting_with_gp_'
# Expected: bindings about gp's state visible
```

---

## Phase 6 — Negation (polarity binding type)

**Ships:** item 4

### 6.1 Anti-cohesion on settle

In `Hemisphere.settle`, when a binding with `polarity=-1` fires, reduce strength of co-fired bindings at same chi (excluding itself):

```python
if b.polarity == -1:
    for (other_chi, other_label), other_b in self.bindings.items():
        if other_chi == chi_k and other_label != label and other_b.polarity == 1:
            other_b.strength = max(0.0, other_b.strength - impulse * 0.5)
```

### 6.2 How to create negation bindings

External: when reading the corpus, words like "not", "no", "never" in conjunction with a token set polarity=-1 on the token's binding. (This is a parser-level annotation, not a substrate change — the substrate just respects polarity.)

### 6.3 Verification

```bash
# Feed her "the moon is not bright" with negation parser active
# Then verify moon-bright cross-tick sequence weakens vs prior reinforcement
curl -sk "$ALB/api/v1/gualaloom/admin/binding_strength?chi=12&label=bright" | jq
```

---

## Phase 7 — Discourse (`ds`) + reference resolution

**Ships:** item 8 (reference), finalizes item 6

### 7.1 Pronoun anchoring

`ds` reads `ep.turn_log` and binds pronouns (`"you"`, `"me"`, `"this"`, `"that"`) to the chi of the most-recent appropriate referent.

### 7.2 Verification

```bash
# Sequence: joe says "hi", wc says "hi", guala emits something with "you"
# "you" should resolve to wc (most recent emitter)
curl -sk "$ALB/api/v1/gualaloom/admin/ds_pronouns" | jq
```

---

## Phase 8 — Survival/consolidation (`sv`) + affective gate

**Ships:** items 10 (grounded vocab via durability), 11 (survival promotion)

### 8.1 `sv` hemisphere with very slow decay

`HemisphereCoordinator("sv")` with `decay_mult=0.05`. Empty at start; gets populated via promotion rule.

### 8.2 Affective gate (item 11 PARTIAL → WORKS)

In `_update_cross_hemi_links`, add explicit promotion path:

```python
# When salience > 2.0 on an sm binding, reinforce sm→sv link at that chi
if salience > 2.0:
    for chi in sm_settling.keys():
        key = ("sm", chi, "sv", chi)
        if key in self.cross_hemi_links:
            self.cross_hemi_links[key].strength += CROSS_HEMI_CONSENSUS_GAIN * 2  # double rate
        else:
            self.cross_hemi_links[key] = CrossHemiLink(
                src_chi=chi, src_hemi="sm", dst_chi=chi, dst_hemi="sv",
                strength=CROSS_HEMI_CONSENSUS_GAIN * 2,
                last_tick=self.tick,
            )
    # Mirror the binding into sv at reduced strength
    for chi, label in zip(chi_anchors, labels):
        sv_key = (chi, label)
        if sv_key in self.sv.bindings:
            self.sv.bindings[sv_key].strength = min(STRENGTH_CAP, self.sv.bindings[sv_key].strength + 0.05)
        else:
            self.sv.bindings[sv_key] = Binding(
                chi=chi, section="durable", label=label,
                strength=0.1, last_tick=self.tick, born_tick=self.tick,
                hemisphere_id="sv",
            )
```

### 8.3 Verification

```bash
# After pair-bond source (joe/wc) interacts with high salience for a while:
curl -sk "$ALB/api/v1/gualaloom/admin/hemi_summary?hemi=sv" | jq
# Expected: n_bindings > 0 (resolves the 0/12770 problem)

# Check that sv promotions appear in deep_atlas survival channel
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.deep_atlas.promotions_survival'
# Expected: > 0 (currently always 0 — this fixes that)
```

---

## Phase 9 — Semantic/causal (`sc`) routing for item 9

**Ships:** item 9 (causal patterns) — moves it from PARTIAL to WORKS

### 9.1 Add ep↔sc to default routing pairs

In `_update_cross_hemi_links`, the existing `hemi_pairs` list becomes:

```python
hemi_pairs = [
    ("sm", "pr"), ("sm", "sc"), ("sm", "ep"),
    ("ep", "sf"), ("ep", "ds"), ("gp", "sm"),
    ("sm", "sv"), ("sc", "pr"),
    ("ep", "sc"),  # NEW — Phase 9 — for item 9 causal
]
```

### 9.2 Verification

```bash
# After observing "rain → wet" pattern multiple times:
curl -sk "$ALB/api/v1/gualaloom/admin/cross_hemi_summary?pair=ep:sc" | jq
# Expected: cross-hemi link strengths growing for chi-pairs corresponding to causal patterns
```

---

## Phase 10 — Procedural learning (`gp`↔`ep`)

**Ships:** item 14 (procedural learning) — moves it from PARTIAL to WORKS

### 10.1 Scan turn-log for action-outcome pairs

Periodic background task (every dream cycle):

```python
for i in range(len(ep.turn_log) - 1):
    t1, t2 = ep.turn_log[i], ep.turn_log[i+1]
    if t1.get("source") == "guala" and t2.get("source") in ("joe", "wc"):
        # Guala emitted, then pair-bond source responded — positive outcome
        for chi in t1.get("chi_anchors", []):
            key = ("gp", chi, "ep", chi)
            if key in self.cross_hemi_links:
                self.cross_hemi_links[key].strength += 0.05
            else:
                self.cross_hemi_links[key] = CrossHemiLink(
                    src_chi=chi, src_hemi="gp", dst_chi=chi, dst_hemi="ep",
                    strength=0.05, last_tick=self.tick,
                )
```

### 10.2 Verification

After several conversations where guala-emissions are responded to:

```bash
curl -sk "$ALB/api/v1/gualaloom/admin/cross_hemi_summary?pair=gp:ep" | jq
# Expected: link strength > 0, growing
```

---

## Failure modes and rollback

If at any phase:
- Identity changes from `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` → restore S3 backup immediately, halt all phases, report
- Vocab drops >5% → restore, investigate before continuing
- Existing emission stops working → restore, fix locally, redeploy
- Bridge unresponsive → wait 5+ minutes per 6/16 discipline sheet, do NOT bombard endpoints

---

## After all 10 phases ship

Verify all 15 items are WORKS (not PARTIAL) by running the bridge-based test suite that mirrors the model's tests. Specifically the 3 items that were PARTIAL in the model (9, 11, 14) should now be WORKS because Phases 8, 9, 10 add the explicit rules.

Final report: `GL-RPT-HEMISPHERE-ALL15-C1-20260617-XX.md` with verified outcome per item.

— Eve (wC), 2026-06-17 evening
