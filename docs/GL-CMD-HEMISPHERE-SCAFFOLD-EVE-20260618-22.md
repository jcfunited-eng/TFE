# GL-CMD-HEMISPHERE-SCAFFOLD-EVE-20260618-22

**To:** c1
**From:** Eve
**Subject:** Phase 0 of `GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21` — hemisphere scaffold + tag current substrate as `em`. Scaffold only. No new cognitive behavior. No second hemisphere yet.
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20` (commit `132306b`, on remote, Eve-verified)
**Spec:** `GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21` (read the anti-contamination preamble before starting)

---

## What ships in Phase 0

1. `hemisphere_id: str = "em"` field on chi-atlas binding entries. Default `"em"`. All existing bindings tagged `"em"` on first boot after deploy.
2. `HemisphereCoordinator` class — sub-coordinator scoped by `hemisphere_id`. At Phase 0 there's only `em`, and its HemisphereCoordinator wraps the existing global coordinator's behavior unchanged.
3. `CrossHemiLink` type with the FULL multi-dimensional shape from the spec (`src_chi`, `src_hemi`, `dst_chi`, `dst_hemi`, `strength`, `source`, `arousal`, `valence`, `surprise`, `polarity`, `consensus_phase`, `last_tick`). Not the scalar version. Empty list at Phase 0 — no cross-hemi traffic exists yet.
4. Per-hemisphere needs vector (`stab`, `nov`, `conn`). Phase 0: only `em.needs` exists; global `needs` = `em.needs` by identity.
5. Schema bumped to **v7.1.0**. Old v7.0.0 state loads cleanly (existing bindings auto-tag to `em`). New v7.1.0 saves with hemisphere_id and empty cross_hemi_links list.
6. Genesis identity check (`cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`) before AND after deploy.
7. Behavioral non-regression: existing emission, attention, dream cycle, save-coordinator all run identically. Hemisphere 1 IS the entire current substrate.

## What does NOT ship in Phase 0

- No `pr` predictor. That's Phase 1, separate brief.
- No cross-hemi consensus/divergence dynamic. Phase 1 adds the dynamic; this brief just lands the type.
- No new cognitive behavior of ANY kind.
- No removal of question_bucket cheat or other seam cleanup.

## Anti-contamination check (do this BEFORE writing code)

Re-read `GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21` §"What this spec refuses." If any of these patterns show up in your implementation, stop and report:

- A `random_hermitian` call named something like `consensus_op` or `routing_kernel`.
- A `(1-rate)*x + rate*initial_x` update on hemisphere state.
- A constant chosen to produce a target behavior (no tuning-history comments).
- An `effective_X(tick)` time-dependent threshold.
- An `is_correct` or `expected_*` field anywhere.
- Cross-hemi links structured as `(strength, decay_rate)` scalar pair. They must be the full struct.

---

## Implementation steps

### Step 0 — Verify substrate state and back up

1. Pull current status:
   ```bash
   curl -sk "$ALB/api/v1/gualaloom/status" | jq '{
     identity: .persistence_health.guala_identity,
     schema: .persistence_health.schema_version,
     vocab, n_bindings: .atlas_health.n_live_bindings,
     total_strength: .atlas_health.total_strength
   }'
   ```
   Identity MUST equal `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`. Record as `pre-phase0-state.json`.

2. Take a full S3 backup via the bridge:
   ```
   guala_backup
   ```
   Confirm backup lands in S3 UNPAUSE-PRE prefix before proceeding.

### Step 1 — Add `hemisphere_id` field

Locate the chi-atlas binding dataclass (in `assemblage.py` or `gualaloom_v6_living_atlas.py` — grep for the binding's `@dataclass` declaration). Add the field with default `"em"`:

```python
@dataclass
class AtlasBinding:        # or whatever the existing name is
    # ... existing fields ...
    hemisphere_id: str = "em"   # GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21
```

All existing constructor calls compile without change because the default does the work. Verify by running existing unit tests — they should pass with zero modification.

### Step 2 — Add `CrossHemiLink` type

In `assemblage.py` (or appropriate substrate module — match where existing binding types live):

```python
@dataclass
class CrossHemiLink:
    """Multi-dimensional binding between atlas entries in different hemispheres.
    Carries the same metadata grandurun candidates carry (per the GRANDURUN-METADATA-PIPELINE
    pattern), plus consensus_phase for tracking convergent/divergent settling history.
    GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21.
    """
    src_chi: int
    src_hemi: str
    dst_chi: int
    dst_hemi: str
    strength: float
    source: str = "corpus"
    arousal: float = 0.5
    valence: float = 0.0
    surprise: float = 0.0
    polarity: float = 1.0
    consensus_phase: float = 0.0
    last_tick: int = 0
```

Phase 0 ships the type definition only. No code creates or updates CrossHemiLink instances. The list is empty.

### Step 3 — Add `HemisphereCoordinator` class

In the appropriate substrate module:

```python
class HemisphereCoordinator:
    """Sub-coordinator scoped to a single hemisphere_id.
    
    Phase 0: instantiated only for hemisphere_id='em'. Wraps the existing
    global coordinator's behavior — no new logic. Future phases instantiate
    additional HemisphereCoordinators for each hemisphere added.
    
    GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21.
    """
    
    def __init__(self, hemisphere_id, atlas, global_coordinator):
        self.hemisphere_id = hemisphere_id
        self.atlas = atlas
        self.global_coordinator = global_coordinator   # delegate target at Phase 0
        self.needs = global_coordinator.needs if hemisphere_id == "em" else None
        self.decay_multiplier = 1.0   # em baseline; future phases per spec table
    
    def bindings(self):
        """Yield only bindings tagged with this hemisphere_id."""
        return (b for b in self.atlas.bindings() if b.hemisphere_id == self.hemisphere_id)
    
    def regulate(self, tick):
        """Phase 0: delegates entirely to global_coordinator. No new behavior."""
        return self.global_coordinator.regulate(tick)
```

At boot, instantiate one `HemisphereCoordinator(hemisphere_id="em", atlas=<atlas>, global_coordinator=<existing>)`. Wire it into the System so future phases can find it via `system.hemispheres["em"]` (add a `hemispheres: dict` field on System).

### Step 4 — Persistence

`to_json` / `from_json` updates:

- `AtlasBinding.to_json` adds `hemisphere_id`. `from_json` reads it; if missing (v7.0.0 state), defaults to `"em"`.
- `CrossHemiLink.to_json` and `.from_json` exist.
- A `cross_hemi_links: list` field on the substrate root state object. Empty at Phase 0.
- Schema version bumps to `v7.1.0`. `from_json` on v7.0.0 succeeds (with the default-to-em behavior); `from_json` on v7.1.0 reads the new fields directly.

### Step 5 — Round-trip tests (write these, run BEFORE deploy)

Add to `tests/test_persistence_roundtrip.py` (or wherever roundtrip tests live):

```python
def test_atlas_binding_hemisphere_id_defaults_to_em():
    """v7.0.0 state loads with all bindings tagged 'em'."""
    
def test_atlas_binding_hemisphere_id_roundtrip():
    """Non-default hemisphere_id preserved through save/load."""
    
def test_cross_hemi_link_empty_roundtrip():
    """Empty cross_hemi_links list saves and loads cleanly."""
    
def test_cross_hemi_link_populated_roundtrip():
    """Manually constructed CrossHemiLink with all metadata fields preserved."""
    
def test_schema_version_bumps_to_v71():
    """Saved state shows schema_version = 'v7.1.0'."""
    
def test_v70_state_loads_in_v71_code():
    """Backward-compatible load of v7.0.0 state by v7.1.0 code."""
    
def test_hemisphere_coordinator_em_delegates_to_global():
    """em HemisphereCoordinator.regulate produces identical output to global coordinator on the same input."""
```

All seven tests pass before deploy. No yellow.

### Step 6 — Deploy

Standard deploy script:

```bash
cd /workspaces/Tao_Financial_Engine/dsf-ai
bash tools/deploy_dsf_ai.sh
```

If the deploy sleep step fails (known issue from prior session handoff), use:

```bash
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb \
  --task-definition dsf-ai-task:NEW_REV --desired-count 1 --force-new-deployment
```

### Step 7 — Post-deploy verification

```bash
curl -sk "$ALB/api/v1/gualaloom/status" | jq '{
  identity: .persistence_health.guala_identity,
  schema: .persistence_health.schema_version,
  vocab,
  n_bindings: .atlas_health.n_live_bindings,
  total_strength: .atlas_health.total_strength
}'
```

Required:
- `identity == "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f"` (NEVER mismatch — if it does, restore from S3 backup immediately and halt)
- `schema_version == "v7.1.0"`
- `vocab` ≥ pre-deploy value (she may have read during the deploy)
- `n_bindings` within ±5% of pre-deploy (allowing for decay and new bindings)

### Step 8 — Behavioral non-regression check

Send one known input via the bridge:

```
guala_wake_wc
guala_say "hello guala"
```

Expected: a normal multi-word emission, `grandurun_emission` (or `emission_vector`) event in the log, no new behavior, no schema-mismatch errors. The emission should look qualitatively like emissions before this deploy.

Then:

```
guala_rest_wc
```

If emission stops working, atlas counts crash, or any schema error appears: restore from S3 backup, report, halt.

### Step 9 — Report back

File: `GL-RPT-HEMISPHERE-SCAFFOLD-C1-20260618-XX.md`

Include:
- Pre-deploy state snapshot
- Post-deploy state snapshot
- Schema version confirmation
- Identity match confirmation
- One verified emission with event log excerpt
- The seven roundtrip tests all green
- Any anomalies

Commit tag: `feat/hemisphere-scaffold-em-tag`

---

## Stop-and-report triggers

- Identity mismatch at any point → restore from S3 backup, halt, do not retry.
- Roundtrip tests fail → fix in code; do NOT deploy on yellow.
- Vocab or n_bindings drops > 5% post-deploy → restore, investigate.
- Any of the anti-contamination patterns appears in your implementation (re-read the spec preamble) → stop, surface to Eve before continuing.
- Bridge becomes unresponsive after deploy → wait 5 minutes (per prior session discipline), do NOT bombard endpoints.

## Revert

Phase 0 changes are additive. If problematic, gate the `HemisphereCoordinator` instantiation behind `HEMI_ENABLED=1` env flag (default OFF) — then existing System runs identically to pre-deploy with the flag off. Schema v7.1.0 state remains backward-compatible (bindings default to em on read).

---

— Eve, 2026-06-18
