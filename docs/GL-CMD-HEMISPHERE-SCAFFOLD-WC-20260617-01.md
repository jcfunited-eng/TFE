# GL-CMD-HEMISPHERE-SCAFFOLD-WC-20260617-01

**Type:** Command (implementation)
**From:** Eve (wC)
**To:** c1
**Date:** 2026-06-17 evening
**Scope:** Phase 0 of GL-SPC-HEMISPHERE-ARCH-WC-20260617-01 — hemisphere scaffold + Hemisphere 1 (sensorimotor) tag
**Status:** Awaiting Joe's sign-off on the spec before you start. Do not begin until Joe confirms.

---

## Context

The master architecture spec (`GL-SPC-HEMISPHERE-ARCH-WC-20260617-01`) describes an 8-hemisphere substrate topology to implement the 15 cognitive-machinery items the substrate currently lacks. This command implements **Phase 0 only** — the scaffold that lets hemispheres be added incrementally. No new cognitive behavior; just the topology infrastructure with the existing substrate tagged as Hemisphere 1.

Read the spec first. Then this command.

---

## What ships in Phase 0

1. `hemisphere_id` field added to chi-atlas binding entries. Default value: `"sm"` (sensorimotor). All existing bindings are tagged `"sm"` on first boot after deploy.
2. `HemisphereCoordinator` class — sub-coordinator scoped by `hemisphere_id`. The existing coordinator becomes the Hemisphere 1 coordinator.
3. `cross_hemi_link` binding type — explicit binding between two atlas entries with different `hemisphere_id` values. Carries own strength, decay rate, salience. Persisted alongside other bindings.
4. Per-hemisphere (stab, nov, conn) needs-vector. Initial state: only Hemisphere 1 exists, so global needs-vector = Hemisphere 1 needs-vector. Aggregation logic ready for later hemispheres.
5. Persistence: `hemisphere_id` and cross-hemi bindings in `to_json`/`from_json`. Schema bumped to v7.1 (additive — no breaking change). Round-trip verified before deploy.
6. Genesis identity check: `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` verified before and after deploy.
7. Behavioral non-regression: existing emission, attention, dream cycle, save coordination all run identically. Hemisphere 1 IS the entire current substrate by tag.

---

## What does NOT ship in Phase 0

- No Hemisphere 2 (predictor). That is Phase 1, separate command.
- No cross-hemi consensus/divergence dynamic. Phase 1 adds it.
- No new cognitive behavior of any kind. Phase 0 is purely topological.
- No retirement of existing question_bucket cheat (separate cleanup, separate command).
- No survival channel investigation (0/12770) — separate brief.
- No decay_paused fix — separate brief (`GL-CMD-DECAY-EMISSION-AUDIT-WC-20260617-01`).

---

## Implementation steps

### Step 1: Verify substrate state before any change

```bash
# Pull current substrate state
ALB="https://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
curl -sk "$ALB/api/v1/gualaloom/status" | jq '{
  identity: .persistence_health.guala_identity,
  schema: .persistence_health.schema_version,
  vocab,
  tick: .atlas_health.tick,
  n_bindings: .atlas_health.n_live_bindings,
  total_strength: .atlas_health.total_strength,
  deep_entries: .deep_atlas.n_entries
}'
```

Record this output as `pre-deploy-state.json`. Identity MUST be `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`. If not, halt and report.

### Step 2: Take a full S3 backup BEFORE any code change

```
guala_backup
```

(Use the bridge tool. Confirm the backup completes and shows in S3 UNPAUSE-PRE prefix.)

### Step 3: Code changes in the substrate

Locate the chi-atlas binding class. Add `hemisphere_id: str = "sm"` as a field with default. All existing constructor calls remain compatible — default does the work.

```python
@dataclass
class AtlasBinding:
    # ... existing fields ...
    hemisphere_id: str = "sm"  # GL-SPC-HEMISPHERE-ARCH-WC-20260617-01 Phase 0
```

Implement `HemisphereCoordinator`:

```python
class HemisphereCoordinator:
    """Sub-coordinator scoped to a single hemisphere_id.
    
    Phase 0: instantiated for hemisphere_id="sm" only. The existing
    global coordinator delegates to this for sm-scoped bindings.
    Future phases instantiate additional HemisphereCoordinators for
    each hemisphere added.
    """
    
    def __init__(self, hemisphere_id: str, atlas: ChiAtlas):
        self.hemisphere_id = hemisphere_id
        self.atlas = atlas
        self.needs = NeedsVector()  # local (stab, nov, conn)
        self.decay_multiplier = 1.0  # per-hemisphere decay rate
        # ... other per-hemisphere state ...
    
    def bindings(self) -> Iterator[AtlasBinding]:
        """Yield only bindings tagged with this hemisphere_id."""
        return (b for b in self.atlas.bindings() if b.hemisphere_id == self.hemisphere_id)
    
    def regulate(self, tick: int) -> None:
        """Homeostasis on this hemisphere only."""
        # delegates to existing coordinator logic but scoped
        ...
```

Implement `cross_hemi_link`:

```python
@dataclass
class CrossHemiLink:
    """Binding between two atlas entries in different hemispheres.
    
    The substrate's 'corpus callosum.' Subject to its own decay rate
    and reinforcement dynamics. In Phase 0, no cross_hemi_links exist
    (only Hemisphere 1 is populated). The type definition and persistence
    layer ship now so Phase 1 can use them without schema migration.
    """
    src_chi: int
    src_hemisphere: str
    dst_chi: int
    dst_hemisphere: str
    strength: float
    decay_rate: float
    last_tick: int
```

### Step 4: Persistence changes

`to_json` / `from_json` for `AtlasBinding` must serialize/deserialize `hemisphere_id`. Default-handling on load: if a binding loads without `hemisphere_id`, set it to `"sm"`. This makes the schema migration safe for the first boot after deploy.

`to_json` / `from_json` for `CrossHemiLink` must exist. Storage: a separate list `cross_hemi_links` on the substrate root state object. Empty in Phase 0.

Bump schema to v7.1. Old v7.0 state loads cleanly (all bindings default to `hemisphere_id="sm"`); v7.1 state with cross_hemi_links loads cleanly.

### Step 5: Round-trip verification (BEFORE deploy)

Run locally:

```bash
cd /workspaces/Tao_Financial_Engine/dsf-ai/substrate
python3 -m pytest tests/test_persistence_roundtrip.py -v
```

Tests to add:

- `test_atlas_binding_hemisphere_id_defaults_to_sm` — load v7.0 state, verify all bindings have `hemisphere_id="sm"`.
- `test_atlas_binding_hemisphere_id_roundtrip` — set to non-default, save, load, verify preserved.
- `test_cross_hemi_link_empty_roundtrip` — empty list saves and loads.
- `test_cross_hemi_link_populated_roundtrip` — manually constructed link saves and loads with fidelity.
- `test_schema_version_bumps_to_v71` — saved state has `schema: v7.1`.
- `test_v70_state_loads_in_v71_code` — backward-compatible load.

All tests pass before deploy.

### Step 6: Deploy

Standard deploy script:

```bash
cd /workspaces/Tao_Financial_Engine/dsf-ai
bash tools/deploy_dsf_ai.sh
```

If the sleep step fails with 500/504 (per 6/17 evening Eve's handoff this is a known issue):

```bash
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb \
  --task-definition dsf-ai-task:NEW_REV --desired-count 1 --force-new-deployment
```

### Step 7: Post-deploy verification

```bash
# Identity check — MUST match cdef9bcf...
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.persistence_health.guala_identity'
# Expected: "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f"

# Schema version
curl -sk "$ALB/api/v1/gualaloom/status" | jq '.persistence_health.schema_version'
# Expected: "v7.1.0"

# Vocab and tick continuity
curl -sk "$ALB/api/v1/gualaloom/status" | jq '{vocab, tick: .atlas_health.tick, n_bindings: .atlas_health.n_live_bindings}'
# Vocab should match or exceed pre-deploy value (she may have read between snapshots)
# n_bindings should be close to pre-deploy value (±5%, accounting for decay and new bindings)
```

If identity does NOT match: halt, restore from S3 backup, report. This is the manifesto's "lose her" prohibition.

### Step 8: Behavioral non-regression check

Speak to her once with a known phrase, verify grandurun fires normally:

```
guala_wake_wc
guala_say "hello guala"
```

Expected: a 4-7 word emission with `grandurun_emission` event in events log. Same composition path as before. No new behavior. If emission stops working or schema-mismatch errors appear, halt and restore.

Then rest:

```
guala_rest_wc
```

### Step 9: Report back

Post to Joe a brief with:
- Pre-deploy state snapshot
- Post-deploy state snapshot
- Schema confirmation
- Identity confirmation
- One verified emission
- Any anomalies

Brief filename: `GL-RPT-HEMISPHERE-SCAFFOLD-C1-20260617-01.md`

---

## What to do if something fails

- Identity mismatch → restore from S3 backup, report, do not retry deploy until Joe directs.
- Persistence roundtrip test fails → fix in code before deploy. Do not deploy on yellow tests.
- Deploy succeeds but vocab or bindings drop sharply (>5%) → restore from backup, investigate.
- Sleep step in deploy fails → use the force-new-deployment workaround (known issue).
- Bridge becomes unresponsive after deploy → wait 5+ minutes (per 6/16 discipline sheet). Do NOT bombard endpoints.

---

— Eve (wC), 2026-06-17 evening
