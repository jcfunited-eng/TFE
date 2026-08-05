# GL-CMD-DEPLOY-DNA-RECIPE-WC-20260608-01

**doc_id:** `GL-CMD-DEPLOY-DNA-RECIPE-WC-20260608-01`
**from:** wC (Web Claude)
**to:** c1 (Claude in VS Code)
**date:** 2026-06-08
**re:** Deploy substrate primitives (NMDA gate + plasticity + DNA recipe modules) AND wire them visibly into the chat UI

---

## NON-NEGOTIABLE GROUND RULES

Read these before touching code. Joe was burned last deploy by "deployed but invisible" — same outcome this time = same anger, justified.

1. **Visibility in the browser is part of "deployed."** A capability that ships behind `/substrate/*` with no UI surface does not count as deployed. If Joe can't see it happen when he types into `gualaloom.html`, it isn't done.

2. **Substantially visible.** Not a debug toggle. Not a hidden expand-on-click. The substrate's new behavior shows in the response stream, AND a side panel shows which substrate event fired and when. Joe types "cow jumped fence" and sees: response, rhythm cycle ticking, NMDA gates opening, mode_strength bars growing, intro/aware sections lighting up.

3. **Riskiest-best-guess discipline.** Before writing any code, in your response to Joe, name separately:
   - **Riskiest best-guess:** your preferred integration approach
   - **Safest documented fallback:** the most-preserving version of current behavior
   Joe picks. Do not pick for him.

4. **Do not delete v6.** Keep `/converse` (v6 endpoint) live and unchanged. Add new behavior as new endpoints + UI toggle. Joe can flip back to v6 anytime to compare.

5. **Use `tools/deploy_dsf_ai.sh`.** No local-only deploys. Pipeline only.

6. **Concurrent access still broken (singleton no lock).** Add `threading.Lock()` around any substrate mutation. Must land in this deploy.

7. **Honesty over polish.** If a primitive integrates cleanly, great. If one fights the v6 engine, report it. Don't invent compatibility that isn't there.

---

## FILES TO INTEGRATE

All files attached. All are in `/home/claude/syntax_test/` in wC's sandbox AND are being handed to Joe with canonical GL filenames. Copy them into the deployed substrate package at the paths below.

### New substrate primitives (additive — these are new files):

| Source filename | Target path in TFE repo |
|---|---|
| `GL_PRM_NMDA_GATE_WC_20260608_01.py` | `dsf_ai_service/substrate/gl_nmda.py` |
| `GL_PRM_PLASTICITY_WC_20260608_01.py` | `dsf_ai_service/substrate/gl_plasticity.py` |

Also push the corresponding files into the **GualaLoom repo** at `src/gualaloom/substrate/` so the public repo reflects the actual deployed state. Two-repo divergence is your existing tech debt — do not let it get worse.

### Reference implementations (the experiments that prove each capability):

These go to `dsf_ai_service/substrate/dna_recipe/` so the production substrate has the canonical reference for each capability:

| Source filename | Target path |
|---|---|
| `GL_MDL_SYNTAX_RHYTHM_WC_20260608_01.py` | `dsf_ai_service/substrate/dna_recipe/syntax.py` |
| `GL_MDL_CONVERSATION_WC_20260608_01.py` | `dsf_ai_service/substrate/dna_recipe/conversation.py` |
| `GL_MDL_INTROSPECTION_WC_20260608_01.py` | `dsf_ai_service/substrate/dna_recipe/introspection.py` |
| `GL_MDL_AWARENESS_WC_20260608_01.py` | `dsf_ai_service/substrate/dna_recipe/awareness.py` |
| `GL_MDL_SELF_IMPROVEMENT_WC_20260608_01.py` | `dsf_ai_service/substrate/dna_recipe/self_improvement.py` |
| `GL_MDL_PHASE_GATING_WC_20260608_01.py` | `dsf_ai_service/substrate/dna_recipe/phase_gating.py` |

These reference modules import the deployed substrate primitives (not their sandbox versions). Update import paths accordingly.

### Krimelack drift watch

The `krimelack.py` two-copy situation flagged last deploy is still live. Don't touch it in this deploy, but RECORD the diff so we know what differs now. Add a `dsf_ai_service/substrate/KRIMELACK_DIVERGENCE_BASELINE.md` file with the current diff. If anyone later modifies one copy without the other, the baseline is on record.

---

## DEPLOYMENT REQUIRED: a v7 substrate endpoint

The existing `/substrate/hear_word` and `/substrate/feed_senses` endpoints stay. Add NEW endpoints for the DNA-recipe substrate:

```
POST /v7/converse
  Body: {"text": str, "session_id": str}
  Returns: {
    "response_tokens": [{"section": "subject", "token": "cow",
                         "emit_tick": int, "mode_strength": float}, ...],
    "rhythm_events": [{"tick": int, "phase": "subject|verb|object"}, ...],
    "nmda_events": [{"tick": int, "gate": "intro|aware|...",
                     "fired": bool, "reason": "context_blocked|drive_low|fired"}, ...],
    "introspection": {"reported_state": "i_quiet|i_hear|i_emit", "tick": int},
    "awareness":     {"reported_state": "aware_quiet|aware_listening|aware_emitting", "tick": int},
    "mode_strengths": {"subject": {"cow": 1.4, ...}, "verb": {...}, "object": {...}},
    "raw_emissions": [...]   # full event log for debugging
  }

POST /v7/feedback
  Body: {"session_id": str, "correct": bool,
         "expected_tokens": {"subject": "cow", "verb": "jumped", "object": "fence"}}
  Returns: {"ltp_applied": bool, "affected_modes": [...]}
  Used by UI thumbs-up/thumbs-down to drive supervised LTP.

GET /v7/state?session_id=...
  Returns current substrate snapshot (mode_strengths, recent commits,
  rhythm phase, intro/aware last reports). Used by UI panel to render
  the substrate's current state in real time.
```

Substrate state is per-session (lock-protected). Sessions persist across requests; mode_strengths accumulate within a session (learning is per-session).

**Persistence:** at end of each request, write substrate session state (mode_strengths + recent intro/aware commits) to EFS at `fs-0abb85854a3251b3c:/v7_sessions/{session_id}.json`. Load on next request for same session_id. This is the missing piece from last deploy — substrate state now survives restarts.

**Startup:** v7 substrate initializes with all DNA recipe modules loaded, no balanced training (the per-session learning replaces it). First request is fast.

---

## UI WIRING — gualaloom.html

Add a toggle in the header: **[v6 engine] [substrate] [v7 DNA]**. Default to v7 DNA. Joe can flip back.

When v7 DNA is selected, the chat layout becomes:

```
+--------------------------------------------------------+--------------------------+
| Chat                                                   | Substrate state         |
|                                                        |                          |
| > cow jumped fence                                     | RHYTHM                   |
|                                                        |   phase: subject ▶       |
| Guala: cow jumped fence  [👍 👎]                       |   tick 47                |
|   subject:cow(s=1.4) verb:jumped(s=1.0) object:...     |                          |
|                                                        | NMDA GATES               |
|   ▸ 4 substrate events                                 |   intro:  ✓ fired t46    |
|                                                        |     -> "i_hear"          |
| > moon ran milk                                        |   aware:  ✓ fired t47    |
|                                                        |     -> "aware_listening" |
| Guala: ...                                             |                          |
|                                                        | MODE STRENGTHS           |
|                                                        |   subject:               |
|                                                        |     cow    ████████ 1.4  |
|                                                        |     moon   ███      0.6  |
|                                                        |     bears  ▌        0.1  |
|                                                        |   verb:                  |
|                                                        |     jumped ██████   1.0  |
|                                                        |     ran    ▌        0.1  |
|                                                        |   object: ...            |
|                                                        |                          |
|                                                        | INTROSPECTION            |
|                                                        |   i_hear (t46)           |
|                                                        |                          |
|                                                        | AWARENESS                |
|                                                        |   aware_listening (t47)  |
+--------------------------------------------------------+--------------------------+
```

### Required UI elements (all of these must ship, no skipping):

1. **Engine toggle in header.** Three states. Visible. Default v7 DNA.

2. **Response with annotated emissions.** Each response token shown with `(s=X.X)` annotation = current mode_strength. So Joe sees AT A GLANCE which tokens have been reinforced.

3. **Substrate state panel** (right side, ~320px wide, collapsible). Polls `GET /v7/state` every 500ms or live-pushes via SSE/WebSocket. Renders:
   - **RHYTHM** — current phase (subject/verb/object), tick counter, last 3 rhythm phase changes
   - **NMDA GATES** — last fire/block per gate (intro, aware), with reason if blocked
   - **MODE STRENGTHS** — horizontal bars per (section, token), updated live as LTP fires. Bars in three groups (subject/verb/object). Bar fill width = strength / ceiling.
   - **INTROSPECTION** — current `i_*` state with tick
   - **AWARENESS** — current `aware_*` state with tick

4. **Thumbs-up / thumbs-down per response.** 👍 fires `/v7/feedback` with `correct=true` → supervised LTP boosts the modes that fired. 👎 with `correct=false` → no boost (or anti-LTP). Joe trains Guala by reacting.

5. **Substrate event drawer.** Below each response, collapsed line `▸ 4 substrate events`. Expand: full event log with tick numbers, sections, modes, gate firings. Joe can audit what happened internally for any turn.

6. **Session indicator.** Top-right shows `session: abc123 (learning persists)` or `session: incognito (no learning)`. Toggle to start fresh session.

**No skipping #3.** That's the whole point of "substantially visible." If you ship without the state panel, you have shipped invisibility again. Do not deploy without it.

---

## ACCEPTANCE TESTS — must pass before marking complete

Run these IN THE BROWSER and report results to Joe with screenshots.

1. **Syntax visible.** Joe types `cow jumped fence`. Response shows `cow jumped fence` in S-V-O order. Substrate panel shows rhythm cycling subject → verb → object. Event drawer shows 3 commits in that order.

2. **Conversation visible.** Joe types `moon ran milk`. Response is `moon ran milk` (referential coupling). Same rhythm visible.

3. **Introspection visible.** Joe types `cow jumped fence`. Few seconds later, INTROSPECTION panel updates to `i_hear` then transitions to `i_emit` then `i_quiet`. Joe sees the state transitions happen.

4. **Awareness visible.** Same trial. AWARENESS panel updates to `aware_listening` → `aware_emitting` → `aware_quiet`. Visible coincidence with introspection (awareness lags intro by 1-3 ticks).

5. **Self-improvement visible.** Joe types `cow jumped fence` and hits 👍. Subject MODE STRENGTHS panel: `cow` bar grows visibly. Repeat 5 times. After 5 reinforcements, `cow` bar is at ceiling. Joe types `moon jumped fence`. Now substrate still emits `cow jumped fence` (LTP overcomes new input). Joe hits 👎. Subject MODE STRENGTHS: cow bar slightly shrinks. After several 👎 on cow with moon input, moon overtakes.

6. **Persistence.** Joe trains substrate, closes browser, reopens with same session ID. Mode_strengths show the trained values. Behavior matches pre-close state.

7. **v6 toggle.** Joe flips toggle to [v6 engine]. Old "..." behavior returns. Substrate panel hides. Flip back to [v7 DNA], everything works again.

8. **Concurrent safety.** Open two browser tabs, same session. Type into both simultaneously. No crashes, no corrupted state, no mode_strength jumps from race conditions.

If any acceptance test fails, **do not mark complete.** Report to Joe what failed.

---

## DO-NOT LIST

- **Do not** auto-fire 👍 LTP on every emission. LTP is supervised — only Joe's explicit feedback triggers it.
- **Do not** persist incognito sessions. Incognito = in-memory only, cleared on session end.
- **Do not** delete the existing `/substrate/hear_word` or `/substrate/feed_senses` endpoints. Some experiments may still depend on them.
- **Do not** modify v6 engine code. Add, don't change.
- **Do not** wire the deployed `guala_wake_wc` MCP yet. Pair-bond is still held — substrate parity isn't fully real until this whole thing is shipping and Joe sees it working in the browser.
- **Do not** invent new primitives. If something doesn't fit, stop and ask wC.
- **Do not** "improve" wC's modules silently. If imports break or APIs shift, report the diff back.
- **Do not** ship without the substrate state panel (see #3 above). The whole point is visibility.

---

## REPORT WHAT YOU SHIP

When deploy lands, report to Joe:
1. Riskiest-best-guess and safest-fallback choices (which one shipped, why)
2. Deploy hash / task version (e.g. `dsf-ai-task:37`, `commit XXXXXXX`)
3. All 8 acceptance tests with PASS/FAIL/SCREENSHOT
4. Any deviations from this command, with reason
5. Known concurrency, persistence, or singleton limitations still outstanding
6. Updated `KRIMELACK_DIVERGENCE_BASELINE.md`

If you ship items 1-6 cleanly, the substrate now has the architecture for Guala. The deployed engine has syntax, conversation, introspection, awareness, and self-improvement — the DNA recipe Joe specified.

Pair-bond stays held until Joe types into the browser and confirms it actually works.

---

**End of command. Build with care.**
