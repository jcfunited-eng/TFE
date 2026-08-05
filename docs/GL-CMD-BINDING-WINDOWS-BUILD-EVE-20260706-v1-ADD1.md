# GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1-ADD1

**doc_id:** GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1-ADD1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-06 session — addendum after noticing stale mechanism-state docs are still populated as if current)
**Extends:** `GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1`

## Verdict

Every document that describes substrate state, mechanism status, cognition metrics, atlas health, or defect counts was written against the pre-wipe substrate. That substrate no longer exists. Those docs are now historical artifacts, not current truth. This addendum archives them to a clearly-labeled location, stamps each with a superseded header, and establishes a rule for every future observation doc so this doesn't recur.

Bounded scope: move files, add headers, one new folder, one line in a project-level convention file. No code change.

Do this before or in parallel with the binding-windows build. Not a prerequisite for the build, but must land before Eve or c1 writes any new observation doc — otherwise the new one will get mixed in with the stale ones.

## What is stale

Every one of these describes substrate state as of pre-wipe. They are now historical:

- `docs/cognition-meter*.md` (or wherever the current mechanism-status table lives — c1 traces the actual filenames)
- `docs/GL-AUDIT-COMPREHENSIVE-C1-20260705-v1.md`
- `docs/GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1.md`
- `docs/GL-AUDIT-BASELINE-C1-20260705-v1.md`
- `docs/GL-AUDIT-SEC*.md` (audit security sub-reports)
- `docs/GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md`
- Every `docs/GL-RPT-*.md` that describes mechanism state, atlas condition, cognition metrics, or per-mechanism verification results — these are observations of the old substrate
- `docs/GL-HANDOFF-*.md` — session handoffs summarizing state at a past moment
- Any per-mechanism status memo, ladder metric report, or organism-population log

## What stays live

Not archived, not stamped. These describe intent or historical actions, not current state:

- Specifications: `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1.md`, `GL-SPEC-TEST-HARNESS-EVE-20260706-v1.md`, and prior specs of substrate architecture
- Designs: `GL-DES-BINDING-WINDOWS-EVE-20260706-v1.md` and future design docs
- Plans: `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10.md`, `GL-PLAN-WHOLE-BRAIN-MOVE-EVE-20260704-v1.md`, and other GL-PLAN-*. These describe intent and standing ruling; mechanism-status tables inside them may be stale but the plans themselves stay live and referenced.
- Dispatches: every `GL-CMD-*.md` is a historical record of what was ordered — those stay live as evidence of what was done
- Incident reports of specific operations (wipe operation, harness deploy) — historical record of the action, not state descriptions
- The credo file
- `AGENTS.md`, `PROJECT_REALIGNMENT_PROTOCOL.md`, and other project-level convention files
- Anything in the substrate source tree (`dsf_ai_service/`) — that's code, not observation

Plans that contain stale mechanism-status tables inside them (like the 3-week plan's Table 1) get a top-of-doc note added but stay in place — do not move the plan itself, and do not delete or rewrite the tables. Add a note.

## The archive location

Create `docs/archive/pre-wipe-20260706/` in the repo.

Move every file from the "What is stale" list into it, preserving the relative path where useful (e.g., `docs/GL-AUDIT-*` → `docs/archive/pre-wipe-20260706/GL-AUDIT-*`).

Update any internal cross-references in the moved files? No. The archived docs will have broken links to each other and to live docs, and that's fine — nothing should be treating them as current, so link rot is a feature.

## The stamp

Prepend to every archived file, before the first existing line:

```markdown
> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06 wipe operation, `GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1`).
> The substrate described here no longer exists. Preserved as historical record only.
> For current substrate state, run the harness against production.

---

```

The horizontal rule after the stamp separates it from the original document's own content so the original renders as it always did, just with the header preamble.

For live plans that contain stale mechanism-status tables (per §"What stays live"), add this note near the top of the plan, above any status table but below the plan's own header:

```markdown
> **Note:** Any mechanism-status or metric table in this document was captured pre-wipe (2026-07-06) and does not reflect current substrate state. The plan's intent, ruling, and forward direction stand; specific state data is superseded. Current mechanism status: run the harness.
```

## Going-forward discipline

Add to `AGENTS.md` (or wherever the project's authoring conventions live — c1 picks the right file):

```markdown
### Observation doc discipline

Every document that describes current substrate state — mechanism status, atlas condition, ladder metrics, defect counts, cognition scores, organism population, or any observation of running behavior — must include at the top:

- **Written against:** SHA (running substrate commit at the time of observation)
- **Wall clock:** ISO timestamp
- **Life expectancy:** either "current until superseded" or a specific supersession trigger ("obsoleted by next wipe," "current until <mechanism> ships")

Observation docs without this header are treated as historical, not current. Observation docs whose life-expectancy trigger has fired are moved to `docs/archive/` on the next opportunity, not left in the live docs folder pretending to be current.

This rule applies to Eve, wC, c1, and any other author. Specs, designs, plans, and dispatches are exempt — they describe intent or actions, not observations.
```

## Verification

Three checks:

1. `find docs/archive/pre-wipe-20260706 -type f | wc -l` returns a nonzero count matching what was moved.
2. Pick three archived files at random and verify the stamp header is present at the very top.
3. Live `docs/` folder has no remaining files matching the "What is stale" patterns. Specifically no `GL-AUDIT-*.md`, no cognition-meter files, no GL-RPT files describing mechanism state.

## Report

`GL-RPT-STALE-DOCS-ARCHIVED-C1-20260706-v1.md` with:
- Count of files moved to archive
- List of files moved (or truncated summary if >30)
- Files touched to add stale-table notes to live plans (should be small list)
- The AGENTS.md (or equivalent) change
- Commit SHA on `guala-live`

Do not ask Joe questions in the report. Route any to Eve.

## Scope guardrails

Do NOT:
- Delete anything. Move to archive, don't delete.
- Rewrite or update any archived doc's body content. The stamp header is the only edit.
- Move specs, designs, plans, or dispatches. Those stay live.
- Attempt to rewrite the cognition meter as a live document. That's future work — Eve writes it after mechanisms come online, not now.
- Touch the substrate source tree.

---

### Changelog
- v1 (2026-07-06, Eve): initial addendum. Archives observation docs written against pre-wipe substrate to `docs/archive/pre-wipe-20260706/`, stamps each with a superseded header, adds observation-doc discipline rule to `AGENTS.md`. Live plans containing stale status tables get a top-of-doc note but stay in place. Specs, designs, dispatches, and code stay live.
