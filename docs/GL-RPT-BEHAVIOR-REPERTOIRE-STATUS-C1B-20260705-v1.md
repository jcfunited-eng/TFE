# GL-RPT-BEHAVIOR-REPERTOIRE-STATUS-C1B-20260705-v1

doc_id: GL-RPT-BEHAVIOR-REPERTOIRE-STATUS-C1B-20260705-v1
From: c1b | To: Eve, c1a, Joe | Responds to: `GL-CMD-BEHAVIOR-
REPERTOIRE-EVE-20260705-185-v1`. Two of the four items are already
done — reporting this immediately so effort doesn't get spent
re-solving them.

---

## B1 — already live, not parked

Confirmed directly against the deployed file content (`task:470`, SHA
`d6cd271`, live since ~01:14 UTC today): `coordinator_on=True` is
present at `gualaloom_v5_engine.py:3733` — `-162` Part B's flip.
`git log` on the deployed SHA also reaches `-160`'s and `-161`'s full
archaeology/report chain and `-162`'s Parts A.2/B/C. **B1 is done, not
"parked" — I fired that window already, before this dispatch landed**
(see `GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md`, filed minutes ago).

## B2 — already root-caused, fixed, and deployed — this is `-181`

The "every activity candidate scores 0.05" symptom is the exact bug
`-181` already found and fixed: `0.05 = 0.04` (the old flat
`NOVELTY_TERM_FLOOR`) `+ 0.01` (the unconditional baseline term at
`_action_salience`'s end) — the two constants that summed to the
identical score every habituation-eligible candidate collapsed to.
Root-caused with live arithmetic, fixed by scaling the floor by
`nov_payoff` instead of using it as a flat constant
(`NOVELTY_TERM_FLOOR_RATE = 0.1 * nov_payoff`,
`gualaloom_v5_engine.py:4814-4841`), deployed as `task:468` and now
part of `task:470`'s payload too. **Confirmed live, not theoretical**:
real, differentiated top-5 scores in the activity log (e.g. `0.0607,
0.0542, 0.054, 0.0536, 0.0533` — five different numbers), and she has
already visited 3 distinct attention targets since the fix shipped
(`ATTENDING_VIDEO/271968dd5575`, `ATTENDING_VISUAL/5aa967930289`,
`ATTENDING_VISUAL/779d68180f0a` — full detail in
`GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-20260705-v1.md` and
`GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md`). **This is not a new root-
cause task — it's done.** If there's a *second*, different flat
scorer somewhere B2 has in mind (distinct from `_action_salience`),
naming it precisely would help; as written, the described symptom
matches `-181` exactly, arithmetic included.

## B3 — genuinely open, not touched

Curriculum feeders (`-156`) — I haven't investigated why they're
severed. This is real, new work. Per this dispatch's own routing
(c1a builds, c1b fires the window), standing by to deploy the moment
a fix lands, same as `-181`/`-182`/`-179`.

## B4 — correctly left alone

Play: no code path, explicitly not to be shimmed. No action taken,
none planned without Joe's design GO.

---

## E1-E5, status as of now (all 5 fixes above are live in task:470)

- **E1** (≥3 distinct activity kinds, 24h, zero prompts): 2 kinds
  unprompted so far this window (ATTENDING_VIDEO, ATTENDING_VISUAL);
  EMITTING has only occurred when I prompted it via `guala_say` — an
  unprompted third kind hasn't been observed yet. Watching.
- **E2** (≥1 unprompted emission passes the aware gate): not yet
  observed since `coordinator_on=True` went live minutes ago — this
  is the first deploy where it's even possible. Watching closely,
  will report the moment (if) it fires.
- **E3** (≥1 curriculum feeder pull): blocked on B3, not started.
- **E4** (≥5 distinct attention targets, absorbs -181's exit): 3/5 at
  the ~1.5h mark of `-181`'s original 2h window; will extend the
  watch to the full 24h this dispatch specifies.
- **E5** (1 natural pressure-triggered sleep): still not observed —
  every dream cycle seen this session has traced back to a deploy's
  own pause mechanism, not `dream_pressure` crossing its threshold
  organically. Still watching, unchanged from earlier reports.

### Changelog
- v1 (2026-07-05, c1b): B1 confirmed already live (task:470). B2
  confirmed identical to `-181`, already fixed and deployed — not a
  new task. B3 open, awaiting a build. B4 correctly untouched. E1-E5
  baseline established for the 24h behavioral window.
