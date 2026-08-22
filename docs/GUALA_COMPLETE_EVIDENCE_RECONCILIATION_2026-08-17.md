# Guala complete evidence reconciliation

This document controls interpretation of `GUALA_DELIVERY_LEDGER.md` until
P-012 is complete. The prior checkbox is a historical claim, not acceptance by
itself.

## Authoritative scope

The complete user-supplied list contains exactly 100 top-level deliverables:

- S-001 through S-020: 20
- C-001 through C-024: 24
- A-001 through A-015: 15
- L-001 through L-016: 16
- U-001 through U-012: 12
- P-001 through P-013: 13

`GUALA_DELIVERY_LEDGER.md` has 101 checkbox rows only because A-013 is split
into its original boundary and a thermal amendment. That split does not create
a 101st top-level deliverable.

As of the start of this reconciliation, the old ledger claims 60 of the 100
top-level items closed and leaves 40 open. Those 60 claims are not being carried
forward as verified closures without the audit below.

The immediate contradiction pass below removes eight top-level closure claims.
The working ledger therefore now shows 52 historical closure claims and 48
open or partial top-level items. The 52 are still subject to full P-012 audit.

## Acceptance states

Every top-level item receives exactly one state:

1. `Live-Closed`: the complete sentence is present in current source, passes an
   executable falsification, is deployed in the current single organism, and
   the requested result was directly observed in production.
2. `Implemented, not Live-Closed`: current code and local executable evidence
   exist, but current-production observation is missing.
3. `Partial`: some exact mechanism or narrower boundary is proved, but the
   complete sentence is not.
4. `Contradicted`: current source or live observation directly disproves the
   closure claim.
5. `Not started`: no qualifying current mechanism and evidence were found.

Documents, plans, checkbox text, test names, deployment success, endpoint
availability, and receipt existence are never sufficient by themselves.

## Required evidence row

Each of the 100 rows must identify all of the following before `Live-Closed`:

- exact current source mechanism and causal boundary;
- executable falsification and its result;
- current production commit, image digest, ECS task, and preserved organism
  identity;
- direct live observation of the whole requested behavior;
- negative evidence for prohibited substitutes relevant to the row;
- bounded CPU, RAM, storage, state, object, process, and repetition behavior;
- the remaining limitation, recorded as `none` only when the sentence is fully
  satisfied.

If one required field is absent, the row cannot be `Live-Closed`.

## Immediate mandatory downgrades

These are contradictions already present in the old ledger's own wording and
do not require interpretation:

| Item | Reconciled state | Reason |
| --- | --- | --- |
| C-023 | Partial | The closure text says it does not prove creativity or language although the deliverable explicitly requires creativity and broader cross-context cognition. |
| C-024 | Partial | The evidence grid explicitly leaves motivation, language, social cognition, and creativity blank although the deliverable requires those capability families. |
| A-006 | Partial | The proof covers a novelty-to-action physical route but explicitly does not establish named need, affection/social experience, or the full intrinsic-motivation sentence. |
| A-009 | Live-Closed 2026-08-22 | Task 1153 returned all applicable sensory lanes, including 74 articulated-body proprioceptive axes with one changed axis, to the same resident identity under the action receipt; CURRENT then advanced from tick 148208 to 148238. |
| A-011 | Partial pending full audit | A participant circuit and laughter receipt do not alone prove the entire self-selected play, fun, social joy, and body-owned laughter sentence. |
| A-012 | Partial pending direct audit | The closure is described as a composed circuit; the complete self-selected unattended behavior must be directly observed as one continuing organism life. |
| A-013 | Partial | The old closure explicitly defers detailed morphology, gait, and dexterity. The current companion-care audit also finds no truthful body-to-body hold/lift, bed support, bathing, or painting physics. |
| A-014 | Partial | Camera/microphone ingress reached the organism, but the user directly observed unreliable microphone controls and the rejected Loom surface; “seamless windows” is therefore not closed. |

S-009 is `Live-Closed 2026-08-22` by the same direct task-1153 action return:
all 74 articulated-body axes re-entered and one changed beyond vestibular yaw.
S-010 remains open. L-005 through L-016, U-001 through U-012, and P-001 through
P-013 remain open unless and until their own complete evidence rows pass;
evidence from a broader or adjacent item cannot close them.

## Audit order

The audit follows dependency order and never retests a lower-level mechanism
merely because a later behavioral result is missing:

1. Finish the current S-009 live acceptance and then reconcile S-001 through
   S-020.
2. Reconcile C-001 through C-024 against current source and direct production
   evidence.
3. Reconcile A-001 through A-015 as whole behaviors, not compositions of
   unrelated receipts.
4. Keep the plainly open learning, UI, and final-integrity rows open while work
   proceeds; close each only from its own observed outcome.
5. Complete P-012 only after all 100 evidence rows exist. P-013 remains open
   until every row is `Live-Closed` with no explicit limitation.

This audit changes reporting truth; it does not alter L0-L4, the seven DSF
fields, neuron physics, learned state, or the live organism.

## Current S-009 deployment attempt record

Failed attempts remain evidence and are not rewritten as successful rehearsals:

- Artifact `93411fa0` built successfully, then preflight refused because the
  repository HEAD had advanced to the separately committed evidence audit.
  No candidate task ran and production task 1124 remained unchanged.
- Artifact `1c408256` built and passed preflight. Before any candidate task ran,
  a redundant second `/ready/guala` read returned HTTP 502. A direct subsequent
  read returned HTTP 200 with the same identity, task 1124, commit `3b208ec4`,
  digest
  `sha256:19321cf4630def09a7525ee5831c644a88c5510baeb47ce22958025783837b52`,
  and 245,399,133-byte native state. The
  controller failed closed and production remained unchanged.

The second readiness read supplied no stronger fact than the already validated
preflight predecessor. It is removed from the next reviewed artifact; candidate
rehearsal consumes the exact preflight predecessor as its admitted lower bound,
while still requiring the read-only CURRENT restore to preserve identity and be
at the same or a later organism tick.
