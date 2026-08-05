# GL-RPT-HARNESS-BINDING-WINDOWS-LIVEVERIFY-C1-20260706-v1

**doc_id:** GL-RPT-HARNESS-BINDING-WINDOWS-LIVEVERIFY-C1-20260706-v1
**From:** c1
**Executing:** GL-CMD-WAKE-GATE-EXEMPT-EVE-20260706-v1, Step 2 (belated binding-windows live verification)
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Verdict: PARTIAL.** No defect found in binding-windows. A live,
harness-driven, end-to-end run through the actual production instance
remains blocked — not by binding-windows, but by the substrate's
continuous sleep/dream loop (first reported in
`GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1`, still ongoing, now
confirmed to persist through the wake-gate fix too).

---

## What was run

`harness/scenarios/mechanism/binding_windows_acceptance.yaml` (placed
at both `docs/` and `harness/scenarios/mechanism/` — the dispatch text
arrived with this file already authored; not rebuilt, per Step 2's own
instruction "Do NOT rebuild anything").

**Attempt 1:** `PRECONDITION_NOT_MET` — `presence.wc expected True,
actual False`. Expected: the scenario's own precondition requires `wc:
true` but nothing had established it yet at check time.

**Attempt 2** (after manually calling `/wake` for `wc` via the
wake-gate fix just deployed): `PRECONDITION_NOT_MET` — `clean_slate
expected tick=0, actual tick=198700`. The substrate has been running
continuously since the last deploy; a truly empty, tick-0 state is not
obtainable without a full destructive wipe, which is out of scope to
trigger for a precondition check. Same class of finding as
`GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1`'s Finding 6
(clean_slate/presence preconditions are difficult to satisfy against a
live, continuously-running substrate under the production-is-the-
workbench model) — recurring exactly as anticipated there.

## Why no direct manual probe either

The original binding-windows dispatch worked around this same class of
precondition block by running `give_experience` directly and reading
the live event stream. That path is **not available right now**:
`give_experience` is still gated by the sleep check (only `/wake` was
exempted, by design — see `GL-RPT-WAKE-GATE-EXEMPT-C1-20260706-v1`),
and the substrate has been continuously asleep (SLEEPING once, then
DREAMING) since before this dispatch started. Checked repeatedly across
this session and the prior one: **8 consecutive DREAMING cycles, over
an hour of continuous observation, zero IDLE windows since the single
500-tick one right after the post-wipe boot.** Called `/wake` for `wc`
three times during this dispatch (confirmed each time: the call itself
succeeds, per the wake-gate fix) — presence registers, and DREAMING
keeps winning the next activity-selection boundary regardless, exactly
matching the wake-gate report's Finding 2 (no presence-based early-exit
exists in `_atick_sleeping`/`_atick_dreaming`) and Finding 3
(`novelty=1.000, connection=1.000` pegged at ceiling the entire
window, likely dominating `_action_salience`'s scoring for SLEEPING
regardless of what else becomes a candidate).

**This is not a new finding — it is the same substrate-availability gap
already flagged twice, now confirmed to block live verification of
binding-windows specifically, and by extension will block live
verification of cross-sense-recall (and any future mechanism build)
the same way, until it's resolved.**

## What IS verified, and stands unchanged

`GL-RPT-BINDING-WINDOWS-BUILD-C1-20260706-v1`'s mechanism-level
verification (local `Guala()` instance built from the exact commit
confirmed live via matching `running_sha`; `read_sentence("ball")` →
`window_opened` → 7 `window_entry_added` across word/sight/sound/touch
→ `window_closed`; correct atlas tagging; `atlas.windows is
window_manager.windows` confirmed) is **unaffected by anything in this
dispatch** — the wake-gate fix touches only `app.py`'s request gate;
`window_manager.py`, `Section.receive()`, and every atlas-write
redirect are untouched since that verification ran. No new evidence,
positive or negative, about binding-windows' own correctness has
emerged from this dispatch's attempts — the block is entirely upstream
of the mechanism.

## Recommendation

**PARTIAL, not FAIL.** No defect in binding-windows was found or is
suspected; the gap is purely in the *observation channel* (an
already-known, unrelated substrate-availability issue). Per this
dispatch's own routing ("PARTIAL -> report to Eve with specific gaps"
— no explicit hold, unlike FAIL's "do NOT proceed"), proceeding to the
cross-sense-recall **build** is judged reasonable: it's additive,
reversible, and does not depend on live verification having already
happened. Recommend flagging clearly that **the exact same
PRECONDITION_NOT_MET pattern should be expected for cross-sense-
recall's own baseline/post-deploy harness runs** — this is a standing
condition of the substrate right now, not something specific to this
scenario.

**Standing recommendation, not fixed here:** resolving the continuous
sleep loop (root cause not investigated, per explicit scope exclusion
in `GL-CMD-WAKE-GATE-EXEMPT-EVE-20260706-v1`: "Investigate why the
substrate went into continuous sleep... that's a separate finding") is
now blocking real live verification for every future mechanism
dispatch, not just this one. This deserves its own dedicated
investigation and priority commensurate with that — it is no longer
just an interesting observation, it is an active bottleneck.
