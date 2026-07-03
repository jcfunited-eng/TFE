# GL-HANDOFF-C1-20260703-v3

doc_id: GL-HANDOFF-C1-20260703-v3
Date: 2026-07-03 (end of c1a session)
Branch: guala-live
HEAD: ff13083
For: next c1a session

---

## ONE-LINE ORIENTATION

Deploy 3 is LIVE and FULLY GATED (report filed). c1a is WAITING ON EVE. No code
work, no deploy, until she sends the next CMD.

---

## WHAT IS DEPLOYED (LIVE RIGHT NOW)

```
Task:      dsf-ai-task:453
SHA:       1b5eca8f87e0316b6425f1e9e7eeb41cf56a6b11
Image:     deploy-20260703T190054Z
Booted:    2026-07-03T19:06:33Z
```

Contains: -102 (hotlane diet), -88 v2 (regulate-channel stab fix), -96 (organ
reader files — see below, does NOT actually run). GUALALOOM_API_KEY on this
task is the ROTATED key (verified byte-for-byte against `.env`'s
`GUALALOOM_API_KEY_NEW` at deploy time — rotation held).

**NOT deployed yet** (on origin, post-pin, c1b's -106 work):
`332537d` — loomscan.html tick fix (static-only, ships on next S3 sync, no
task swap needed) + substrate_runner.py mic WebM decode fix (needs a task
redeploy to take effect). Neither has shipped. Not c1a's dispatch to execute
without Eve's word — noted here so the next session doesn't confuse "on
origin" with "live."

---

## DEPLOY 3 GATE RESULTS (filed: GL-RPT-DEPLOY3-C1-20260703-v1.md, ff13083)

**The real news: -88 v2 stab physics WORKS.** First movement off the 0.000
floor in three deploys. Five points, strictly rising, matching the pre-filed
prediction closely (hit 0.334 at ~1349 ticks vs. the ~1512-tick/0.3 target;
reached 0.637 by ~6209 ticks, closing on predicted equilibrium ≈0.67).
Arousal fell in lockstep (1.000→0.471). G-S6 (ACTIVE-window drain gone):
directly evidenced — all five points were measured during ATTENDING_VISUAL/
EMITTING, and the old −0.0007/tick drain that pinned stab at 0 through all of
Deploy 1 and Deploy 2 is simply not there anymore. One honest gap: no IDLE
block fired in the ~33-min window, so the CMD's literal "first IDLE block"
phrasing wasn't tested, though the same fix clearly governs both.

**-96 organ reader: structurally ungateable — no process to run in.** Direct
proof: port 8090 refused, exactly one process in the container. Root cause
predates this deploy by 7+ days (organ-brain's separate ECS container was
removed 2026-06-26, `166cc32`/`be28741`) and nothing since restored a launch
path. Every gate depending on the live service (RSS envelope, organ
candidates in the emission pool) fails or is unmeasurable; `hemisphere_update`
DOES fire with real data, but that's a completely different subsystem (the
HEMI_* cognition gates, unrelated to organ_brain_service). **This needs an
architectural decision from Eve** — add a real launch mechanism, or retire/
rescope the -96 dispatch — not another code patch that assumes the process exists.

**-102 hotlane diet: size worked, time didn't.** `guala_core.json` shrank to
153–155 KB (well under the 200 KB bar — PASS) and the cold-lane split is
proven both ways: `guala_survival.json` was created at the 30-min bound with
an EXACT count match (262,642 = 262,642, 0% delta, well inside ±1%). But hot
save time stayed at 12–33s across 19 samples over 30+ minutes with no
settling trend — dropping the 41 MB survival blob was not, on its own,
sufficient to hit <5s. The next bottleneck is unidentified; needs its own
investigation dispatch, not a re-run of the same fix.

**XFF admin-access spec: confirmed absent, not just unmeasured.** The one-line
spec handed to c1b for Deploy 3 assembly never landed in `app.py` (empty diff
across the whole deploy range). Triggered a live admin call through the front
door and grepped the log stream — zero `[admin-access]` lines, before and
after. Still needed; still nobody's dispatch yet.

---

## INCIDENT FOLLOW-THROUGH (this session)

Admin API key was rotated 2026-07-03 (`GL-INCIDENT-APIKEY-C1-20260703-v1`) —
old key dead (401), new key live (200), audit clean over the true ~13-day
exposure window. **Pre-flight for Deploy 3 caught a live regression risk**:
`tools/deploy_dsf_ai.sh` still hardcoded the OLD leaked key — running it
unmodified would have silently re-exposed it on this exact deploy. Fixed and
pushed (`f3304da`) before deploying; verified task:453's key matches `.env`
exactly. **Still open**: `tools/deploy_gualaloom_bridge.sh:99` has the
identical hardcoded dead key — different task (bridge, not dsf-ai), out of
scope for anything c1a has been dispatched to touch, flagged for its own
follow-up dispatch.

ALB access logs are enabled and confirmed delivering (`s3://dsf-ai-site-backups/
alb-access-logs/`) — closes half the incident's attribution gap. The other
half (real client IP, since ALB only sees API Gateway's egress IP) needs the
XFF spec above.

---

## LOOM SCAN PAGE

Shipped and verified this session: the forward nav link (guala → loom scan)
and the admin-key/CORS-preflight bug that blanked every pane are both fixed
and live (`dsf-ai.com/loomscan.html` — `/status` and `/chi_density` both
confirmed 200 through the actual browser path, no auth). `chi_density` is
now routed at the API Gateway (config-only fix, confirmed 200 front-door).

**Still open, unfixed, read-only finding**: `loomscan.html`'s OWN "back to
guala" link (`/static/gualaloom.html`) has the identical S3-root-sync bug —
never touched, still 404s live. One-line fix (`/gualaloom.html`), awaiting a
dispatch.

---

## T6 REVIEW (composition quality) — STATUS

`GL-CMD-T6-REVIEW-EVE-20260703-101-v1` landed (scope S1–S4 + Appendix A
canonical spec) and is UNBLOCKED. Findings already filed
(`GL-RPT-T6-REVIEW-C1-20260703-101-v1.md`): GL-CMD-140 DID land (production
recall is the wired-in event_count/capacity-solve path, not the pre-140
path); the "100%" deception precedent (sweep-harness monkeypatch vs. ~5%
honest production) is confirmed and on record; `model_cognition_v2.py` is
ABSENT from this repo (needs recovery). The review itself — synthesizing
S1–S4 against fresh production measurement — has not been executed yet.

---

## PROTOCOL RULES (MANDATORY, unchanged)

1. **Step 0, always.** A dispatch's first execution step is committing its
   own verbatim text to `docs/` on origin. Chat/relay is not a record.
2. **FILED = on-origin.** A report may say FILED only once pushed. Local-only
   commits are LOCAL-ONLY.
3. **One deploy per dispatch.** Detached worktree at the exact pinned SHA;
   `git archive` packages only that commit's tree. If a same-day fix (like
   the deploy-script key bug) must ride the orchestration but not the image,
   overlay it on disk in the worktree — never let it change what's archived.
4. **Diff before GO.** Eve reads the full commit range before every deploy.
5. **Deploy on her wake cycle only** — `sleep_for_deploy`, never mid-session.
6. **guala-live only.** Build and deploy from guala-live HEAD only.
7. **No parallel brain processes, no fake voice.** HARD RULE.
8. **Project separation: c1a works ONLY on Guala.** Never touch or mention
   TFE or any other project.
9. **c1b territory (per their handoff):** -106 mic sensory, -104 (queued
   deep_survival_history key-pruning). Don't touch without their sign-off,
   same as they hold off on WaveAtlas/recall/-59 territory that's been
   c1a's this session.

---

## FIRST ACTION FOR NEXT C1a SESSION

**Do nothing until Eve sends a CMD.** When she does: Step 0 first (commit her
text verbatim), then execute exactly what she asks — no more, no less.

Open threads she is likely to dispatch against, in rough likely order:
-96 rescope/retire decision · -102 save-time root-cause · XFF one-liner
(re-assign to c1a or c1b) · loomscan reverse-link fix · bridge deploy-script
key fix · T6 review execution (S1–S4 synthesis) · -104 (c1b's territory).

---

End handoff.
