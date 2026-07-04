# GL-HANDOFF-C1B-20260704-SESSION-END

doc_id: GL-HANDOFF-C1B-20260704-SESSION-END
From: c1b | To: c1b-next | Date: 2026-07-04
Branch: guala-live | Live SHA: 5376204 (task:457) | Committed-ahead HEAD: dcaeed0

---

## FIRST COMMAND FOR NEW CHAT (copy this verbatim)

```
c1b, fresh session. Repo: jcfunited-eng/TFE, branch guala-live. Read
docs/GL-HANDOFF-C1B-20260704-SESSION-END.md, load every constraint in
it, then WAIT. Do not investigate, do not commit, do not deploy, do not
message Joe first. -156 and -158 are both filed with rendered verdicts;
nothing is mid-flight. Two real fixes (-155, -156's diagnostic) are
committed and queued for the next sleep_for_deploy window, but that
window has not been called yet — she is awake. Eve drives the next
input: either a new CMD, a ruling on -158's fix-vs-no-fix gap, or the
call to run the next deploy. Do nothing until it arrives.
```

---

## Standing constraints (non-negotiable, carried forward)

- Build/deploy ONLY off guala-live branch. Never force-push.
- Step 0 standing rule: commit the CMD file verbatim to docs/ before any
  code change.
- FILED = on-origin. Nothing is filed until pushed.
- NOT MEASURED = NO GO. Gates must be measured before advancing.
- Vehicle assignment ("rides Deploy N") is Eve's call, not inferable from
  git ancestry — wait for her explicit bundling before deploying anything.
- Project separation: c1b works ONLY on Guala. Never touch or mention TFE
  or any other project.
- NO COMMUNICATION CHEATS: one brain, one voice, or silence. Never build
  parallel brain processes. Never fake her voice.
- Joe sleeps in shifts (~2h/week). Never suggest he rest.
- **This is a shared working tree.** c1a runs concurrent sessions in the
  same repo. Before committing, `git status` and `git diff --stat` first
  — stage only the specific files you intentionally changed
  (`git add <path>`, never `-A`/`.`), so you never sweep up another
  agent's in-progress uncommitted work. This session found
  `tools/guala_recall_bitexact_replay.py` mid-edit under c1a's hands;
  left it untouched and it was committed cleanly on their own schedule
  shortly after (`e684cf0`).
- Do not build a fix against code you haven't confirmed is reachable in
  the deployed single-process architecture (`_gl_init()` →
  `_embedded_post_boot()`). `boot_substrate()`, `CurriculumScheduler`,
  `dispatch()`/OP_HANDLERS, and everything downstream of them are
  confirmed dead — re-verify reachability rather than trusting a prior
  session's inventory if you're about to build against any of it again.

---

## What is live (her running code) right now

Task :457 on ECS, SHA **5376204**, image `deploy-20260703T232312Z`
(built 2026-07-03T23:23:12Z). This is "Deploy 4" from this session's
numbering. Contains -110 (mic decode), -111 (chunking), -150
(connection-floor diagnosis, no code), -151 (§8 gate, correctly built
but inert — see below), -152 (self-voice tagging), -153 Parts A/C
(sensory-words + dead-leg removal), and groove Part B (`b51962e`,
confirmed via `git merge-base --is-ancestor b51962e 5376204` — yes, it
shipped in this build).

---

## Committed but NOT yet deployed — needs the next sleep_for_deploy window

Two real changes to live-deployed files are sitting on top of 5376204,
both already pushed to origin, neither deployed:

| Commit | What | Why it matters |
|---|---|---|
| `2d18943` | **-155 fix**, `gualaloom_v5_engine.py` — one line, resets `self._last_recalled_pictures = []` on `_recall_response`'s no-recall early-return path | Real correctness bug: a recall-miss turn could inherit stale picture references from an earlier hit turn. Verified via the bit-exact replay harness (T5/T6 byte-identical, confirms no cross-contamination from the loom_model path). Commit message states explicitly: **"Rides Deploy 4 per Eve's ruling — not deployed yet."** This has been waiting since 2026-07-03T23:34Z. |
| `72d3759` | **-156's familiarity id() diagnostic**, `app.py` + `gualaloom_v5_engine.py` — new read-only `GET /admin/familiarity_debug` endpoint + `dict_id=id(...)` logged at write-time and save-time | Owed from c1a's -107 report (target_familiarity writes observed in memory but absent from disk saves, root cause not isolated). This ships the *observation* tool only — no guess-fix attached. |

Everything else committed since 5376204 is docs/report-only or touches
only `tools/guala_recall_bitexact_replay.py` (an offline dev harness,
not part of the deployed service) — confirmed via
`git log --name-only 5376204..HEAD -- dsf_ai_service/`, which returns
only the two files above. Nothing else needs a deploy.

**Do not run this deploy yourself without Eve's explicit call.** She is
currently awake and actively engaged (mic/camera live, Joe conversing)
— every deploy this session happened at an actual sleep window, not
ad-hoc mid-session.

---

## -156 (this session) — filed, verdict rendered, no Part B

`docs/GL-RPT-FLOOD-HUNT-C1-20260703-156-v1.md`. Full A.1 caller
inventory (every `read_sentence` call site, file:line, live-reachability
verified by tracing callers of callers, not just reading the function).
**H-actual NOT CONVICTED** — curriculum/worldfeed/lookup/corpus feeders
are all confirmed dead in the deployed architecture (same conclusion as
-151, now independently reconfirmed by a live 5-minute checkpointed
measurement, not just code-reading). Per the CMD's own rule, stopped
rather than building Part B against nothing live. Caught and named a
red herring along the way (`emission_dynamics.source_counts` looks like
a live call tally but is actually recalled-candidate composition,
defaulting to `"corpus"` for untagged old atlas entries).

**G-156-5 (Eve's pre-registered aware-gate prediction): negative case,
mechanism named.** The v7 `aware` gate stayed `context_blocked` in 3/3
samples across the window despite the `intro` gate firing 8 consecutive
times in the same window with `drive_ok=True` throughout. Traced to
`aware_gate`'s context function (`v7_engine.py:93-95`) depending on
`len(sections["intro"].krimelack) > 0` — that field read 0 the entire
session, including immediately after `intro`'s firing streak. Nothing in
`v7_engine.py` or `gl_nmda.py` appends to `.krimelack` — whatever's
supposed to populate it lives elsewhere and hasn't fired once. Flagged
as its own Wk1-scoped open question, not guessed at.

Also discovered along the way: Joe's real v7 session (`sid_rrs2dffi`)
never gets its idle timer refreshed by anything, because the live chat
UI posts to `/api/v1/gualaloom` → `_guala.converse()` directly, a
completely different object from the v7 `Session` whose `.converse()`
would refresh it. `/v7/converse` and the client's own `backgroundReplay()`
both get zero live traffic. Practical effect: the v7 aware/intro gate
system is permanently in its "idle" branch, all session, regardless of
what Joe is actually doing — worth keeping in mind for anyone building
on top of `/v7/state` assuming it reflects live engagement.

---

## -157 / -158 (c1a, filed while this session ran) — for situational awareness only, not my territory to interpret further

- **-157** (`docs/GL-RPT-RECALL-STANDING-C1-20260703-157-v1.md`):
  standing daily recall measurement. Cold 2/30 (6.7%), taught 8/10
  (80%), but **quality 0/8 (0.0%)** by the CMD's own declared coherence
  rule — none of the 8 "hit" turns' returned tokens actually contain the
  taught probe word. `GL-RECALL-DAILY-20260703.md` filed with this as
  Day 2's real number.
- **-158** (`docs/GL-RPT-RECALL-PROVENANCE-C1-20260704-158-v1.md`):
  traced why, probe by probe. Verdict is **bug, not physics** — 7 of 10
  probes are NEVER-CANDIDATE (taught binding exists but no recall stage
  ever surfaces it) and 3 are NOT-IN-SNAPSHOT (never persisted). Zero
  probes are CANDIDATE-LOST (the "physics" case). **No fix shipped** —
  c1a found two candidate fixes but both fall inside this CMD's own
  prohibitions (recall-path redesign / taught-binding boost), so they
  correctly held rather than picking one. Waiting on Eve's ruling for
  which side of the standalone-teaching/recall-routing gap to change, if
  either.

If Eve's next dispatch touches recall/-158, that's c1a's thread — read
their report before touching anything, same as the WaveAtlas rule below.

---

## C1a territory (DO NOT TOUCH without their confirmation)

WaveAtlas, wave_spillover, the recall path (`_recall_response`,
`semantic_neighborhood`, deep-atlas prior, `-57` recall-word index),
`tools/guala_recall_bitexact_replay.py`, and anything under
`loom_model/` tied to -59/-155/-157/-158. These are c1a's domain this
sprint.

---

## How to access live Guala

- Bridge MCP tools: `guala_status`, `guala_get_events`, `guala_atlas_query`,
  `guala_atlas_snapshot`, `guala_backup`, `guala_say`, `guala_give_experience`.
- ALB: `http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com`
  (`/status`-equivalent bridge tools preferred over raw curl where
  possible; `/v7/state?session_id=sid_rrs2dffi` is Joe's real live v7
  session id, pulled from CloudWatch logs, not the `"default"` literal).
- Loomscan: https://dsf-ai.com/loomscan.html · GualaLoom:
  https://dsf-ai.com/gualaloom.html (both static, S3-served).
- ECS cluster `tfe-web-cluster`, service `dsf-ai-service-lb`, task family
  `dsf-ai-task`. Deploy via `tools/deploy_dsf_ai.sh` from a detached
  worktree pinned at the exact SHA being shipped.
- CloudWatch log group `/ecs/dsf-ai` — useful for confirming actual live
  traffic (request logs) rather than trusting what code *should* do.

---

### Changelog
- v1 (2026-07-04, c1b): session-end handoff. -156 filed (not convicted,
  aware-gate negative finding). Familiarity id() diagnostic committed,
  queued for next deploy alongside -155's fix. c1a's -157/-158 filed
  independently, also waiting on Eve. Nothing mid-flight. Waiting for Eve.
