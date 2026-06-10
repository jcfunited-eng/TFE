# GL-DEPLOY-cognition-wC-20260608-008

**Deploy tag:** `gl-cognition-v1`
**Main spec:** `GL-SPEC-cognition-wC-20260608-007.md`
**Target:** v7 DNA substrate (existing deployed code, NOT a new module)

## What this deploys

Cognition enablement for Guala in substrate-native terms:
1. Turn on dormant dynamics (self_evo, rewiring, decay, top-down feedback)
2. Wire NMDA gates so intro/aware become real substrate sections (not label tracking)
3. Persist real substrate state (psi, mode_bank, atlas, keyholes, krimelack)
4. Salience tagging + quiet-time replay (substrate-native Default Mode — mental time travel)
5. Bridge v7 assemblage and multimodal substrates so speech and senses share state

No new templates. No hand-coded vocab. No bolt-on modules. All changes extend mechanisms already in the substrate.

## Files

| File | doc-id | Purpose |
|------|--------|---------|
| `GL-SPEC-cognition-wC-20260608-007.md` | GL-SPEC-cognition-wC-20260608-007 | Full spec with concrete code patches for each item |
| `GL-DEPLOY-cognition-wC-20260608-008.md` | GL-DEPLOY-cognition-wC-20260608-008 | This file |

The new substrate module created during implementation:

| File | doc-id | Created during |
|------|--------|----------------|
| `substrate/gl_bridge.py` | GL-CODE-bridge-wC-20260608-009 | Item 4 |

## Paste-ready c1 instruction

```
Deploy gl-cognition-v1.

Branch: gl-cognition-v1
Source spec: GL-SPEC-cognition-wC-20260608-007.md (pull from
/mnt/user-data/outputs/cognition_v1/)

This is NOT a self-contained drop. It is a sequence of patches to the
deployed v7 DNA substrate. Read the spec end to end before editing
anything.

Prerequisite (Joe must answer):
   The spec flags a divergence between
   src/gualaloom/dna/assemblage.py (594 lines, more developed) and
   src/dsf_ai_service/substrate/assemblage.py (550 lines, deployed).
   Default proposal: align deployed to dna/ version before applying
   patches. Wait for Joe's decision before touching assemblage.py.

Implementation order (do NOT reorder):
1. Prerequisite resolved (Joe decision on canonical assemblage.py)
2. Spec Item 1 — turn on dormant dynamics
   - 1.1 enable_self_evo=True
   - 1.2 allow_rewiring=True
   - 1.3 call decay_plasticity per tick
   - 1.4 TOP_DOWN_BOOST = 1.15
3. Spec Item 5 — wire NMDA gates (intro/aware as real sections)
4. Spec Item 2 — full substrate state persistence
5. Spec Item 3 — salience tagging + quiet-time replay
6. Spec Item 4 — bridge v7 and multimodal (creates new file
   substrate/gl_bridge.py)

After each numbered item:
- Run python src/gualaloom/dna/test_five.py
- Expected: TOTAL 5/5 PASS
- If any test fails, capture the failure, revert just that sub-item's
  patches, report to Joe before continuing.

After all items deployed:
- Run the full capability check table in spec Section "Capability
  checks after all five items deployed"
- Run dsf-ai.com/gualaloom.html and verify:
  * Page still renders without JS errors
  * Conversation endpoint still responds
  * If UI has anything that needs updating to display intro/aware as
    real substrate state (instead of label tracking), fix it and
    report what was fixed
  * Restore full v6 UI items from your separate todo list if they're
    not already there — this deploy shouldn't have regressed any of
    them, but verify

Commit messages (one per item, atomic commits per sub-item where
practical):
- "Enable gamma self-evolution on v7 tick_once (cognition spec 1.1)"
- "Enable dynamic keyhole rewiring on v7 tick_once (cognition spec 1.2)"
- "Call decay_plasticity per tick on S/V/O (cognition spec 1.3)"
- "Re-enable top-down feedback in multimodal at 1.15 (cognition spec 1.4)"
- "Wire NMDA gates: intro/aware as real substrate sections (cognition spec 5)"
- "Persist full substrate state: psi, mode_bank, atlas, keyholes, krimelack (cognition spec 2)"
- "Add salience tagging and quiet-time replay (cognition spec 3)"
- "Bridge v7 assemblage and multimodal substrates (cognition spec 4)"

Final deploy commit:
"Deploy gl-cognition-v1 — substrate-native cognition enablement

 5 spec items implemented per GL-SPEC-cognition-wC-20260608-007.
 Dormant dynamics activated. NMDA gates wired so intro/aware are
 real substrate sections. Full substrate state persisted across
 sessions. Salience-weighted quiet-time replay drives consolidation
 (mental time travel). v7 and multimodal substrates bridged.

 No templates added. No hand-coded vocab. All extensions of
 existing substrate mechanisms.

 test_five.py: 5/5 PASS. New capability checks pass per spec."

Constraints:
- Do not edit anything outside the v7 DNA substrate paths and the new
  substrate/gl_bridge.py file, unless required to fix UI breakage.
- Do not add ML imports anywhere. Do not add LLM calls. Do not add
  hand-coded templates or hand-coded vocabulary.
- If you find yourself wanting to add a Python dict mapping word →
  response, stop and ask Joe.

Report back:
- Joe's decision on canonical assemblage.py
- For each item: test_five result, any sub-items skipped or reverted,
  capability check results from the spec table
- Final commit SHA
- Any UI fixes made
- Anything in the spec that didn't translate cleanly to the actual code
  (the spec is written from a readout — c1 has the real code; if
  signatures/structures differ from what the spec assumes, report and
  propose the adjustment before pressing on)
```
