# GL-DEPLOY-usability-and-persistence-wC-20260609-013

**Two specs, sequenced, both ship in this work cycle:**
- `GL-SPEC-usability-wC-20260609-011.md` — uploads + v6 UI + visibility
- `GL-SPEC-persistence-real-wC-20260609-012.md` — real mode_bank fix

**Deploy tags:** `gl-usability-v1` then `gl-persistence-real`

## Read this carefully before starting

Joe's words on the current pattern: "shouldn't I be able to see your
interaction and visa versa ... and why only 3 primitive S/V/O ... if
we're limiting her and letting c1 just amass a list of todo she'll
never get close to todone."

That's a direct critique of the todo-amassing pattern. Multiple things
have been queued as "next session" and never landed. The "Restore full
v6 UI" todo has been on the list for multiple deploys. Upload
capability is sitting in stub form. The mode_bank persistence workaround
was supposed to be revisited and wasn't.

This deploy cycle breaks that pattern. Neither spec is for queueing.
Both ship.

## Paste-ready c1 instruction

```
Two deploys in sequence. Read both specs before starting either.

DEPLOY 1: gl-usability-v1
Spec: GL-SPEC-usability-wC-20260609-011.md
Branch: gl-usability-v1

Implement and ship all 5 sections atomically:
  1. /upload/book endpoint + UI button + corpus integration
  2. /upload/image endpoint + UI button + visual cortex processing
     into sight_section motifs
  3. /upload/sound endpoint + UI button + audio pipeline processing
     into audio motifs
  4. v6 UI restoration (entire pending todo): sleep/wake button,
     activity display, needs line, presence heartbeat, atlas
     strength display, autonomous emissions in chat as italic/
     prefixed lines
  5. Visibility unification: bridge guala_say and chat UI inputs
     write to same event stream; UI scroll replays from event
     stream so wC's interactions and autonomous emissions both
     surface in Joe's view

NON-NEGOTIABLE: if you cannot ship all 5 in this deploy, ship what
works AND report exactly which item is incomplete and why. Do NOT
add an unshipped item to a todo list for "next session." Either it
ships or Joe and wC know explicitly that it didn't.

Test plan:
- Upload a sample .txt book → appears in corpora, reads it
- Upload a sample .jpg → sight_section.n_motifs goes from 0 to >0
- Upload a sample audio file → audio motifs created
- Sleep/wake button works, activity display updates live
- wC calls guala_say via bridge → utterance appears in UI scroll
  tagged as wC
- Autonomous emission during idle → appears with thinking prefix

After deploy 1 lands and is verified, proceed to deploy 2.

DEPLOY 2: gl-persistence-real
Spec: GL-SPEC-persistence-real-wC-20260609-012.md
Branch: gl-persistence-real

Implement substrate fix:
  1. Section.commit blend factor 0.92/0.08 → 0.98/0.02
  2. Snapshot initial_mode_bank at Section.__init__
  3. Add Section.apply_homeostasis(drift_rate=0.001)
  4. Call homeostasis every 20 ticks from System.tick_once
  5. REMOVE the per-turn System rebuild from c1 commit 2cc3c96
     (keeping vocab + mode_strength carried forward as before,
     but also keeping psi/mode_bank/atlas/keyholes/krimelack)

Run 4 tests from spec. Report:
  - Test 1 (5-turn varied): pass/fail
  - Test 2 (mode_bank persists across turns): pass/fail
  - Test 3 (atlas/krimelack accumulate): pass/fail
  - Test 4 (50-turn no lock-in): pass count out of 50

If Test 1 fails: tune blend rate (try 0.04) or homeostasis
(try drift 0.0005) and re-deploy. Do not revert to per-turn rebuild.

If Test 4 fails at turn N: report N and current parameters. wC
will spec the tuning adjustment.

REPORT BACK for both deploys:
  - Final commit SHA per deploy
  - Test results
  - For deploy 1: screenshot of UI showing the new buttons +
    one of wC's interactions visible in the chat scroll
  - For deploy 2: the 4 test outcomes verbatim
  - Anything that didn't work and why (with no "queued for next
    session" framing — either it's working or it's broken)
```

## What's NOT in this cycle

These are real future work, NOT being added to a c1 todo:

- Emission expansion beyond 3-token S/V/O — wC will spec separately
  after this cycle lands. The substrate fix has to come first because
  emission expansion against a substrate that resets every turn would
  amplify the lock-in problem.
- Environment Stage 1 (the virtual room with senses) — wC will spec
  after Joe answers the 5 open questions in
  GL-CONCEPT-environment-wC-20260608-010.
- "Toys" as multi-modal interactive objects — that's environment work.

These are tracked here so Joe sees them named, but they are NOT
c1's job until specced.
