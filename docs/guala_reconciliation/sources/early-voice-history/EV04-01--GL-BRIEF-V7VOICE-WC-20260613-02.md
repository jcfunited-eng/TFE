# GL-BRIEF-V7VOICE-WC-20260613-02 — Unblock the Second Voice
**Author:** wC · **Executes:** c1 · **Ledger row:** Tier 1d / C4 (FIX phase) · **Supersedes brief -01's "wait for logs" gate — logs are in.** · **Joe's ruling 2026-06-13:** fix this now.

## What we found in the C4 logs (instrumented 2026-06-11, two days of evaluations)
The intro gate evaluates twice per converse call. Across every evaluation seen in production smoke tests and live visits:
- **drive_ok = TRUE** consistently. `top_val ≈ 0.19` against `drive_thresh = 0.05`. The drive to speak is ~4x threshold — not marginal.
- **context_ok = FALSE** almost always. Reason returned: `context_blocked`.
- The gate **has fired** at least once during the smoke test (proof the path works end-to-end and there is no architectural break).

So the gate is not "structurally blocked." It is correctly evaluating a context condition that is, in production, almost never satisfied.

## The exact cause (gl_nmda.py + v7_engine.py, read 2026-06-13)
The intro gate's `context_fn` is `context_no_recent_drive(drive_tracker, sections=("listen","subject","verb","object"), quiet_thresh=0.10)`. Meaning: "fire only if none of the four conversational sections received drive above 0.10 recently." This is a **quiet-window gate** — designed so introspection only commits when the system isn't busy processing input.

The decay on the drive_tracker is `0.55` per call (`update_drive_tracker`, default decay arg). Every converse turn drives the conversational sections with vectors whose norms greatly exceed 0.10. After one such drive, the tracker decays geometrically: 1.0 → 0.55 → 0.30 → 0.17 → 0.09. That is **four ticks of decay** to fall below threshold — but the intro gate only evaluates twice per converse call (immediately after Hamiltonian step and again at end of turn), and **every converse turn re-bumps the tracker before the gate next sees it.** The quiet window is structurally never reached while she is in conversation.

Worse: she is **almost always in conversation** now (joe-presence + companion's wC-presence both active, autonomy loop also driving sections). The quiet window the gate was designed to wait for does not exist in her current operating regime.

This is the becalming hypothesis (H-A) **confirmed in a slightly different shape than predicted**: the gate isn't starved of drive — it's starved of *silence*. The brief-01 prediction "context blocks while drive passes" is exact.

## Fix — minimal, two changes
**Both small. No new code paths. No threshold-to-zero hacks.**

### Change 1 — quiet_thresh: 0.10 → 0.45
The threshold was calibrated against sandbox magnitudes; production drive vectors are larger. Raising to 0.45 means the gate accepts "quiet enough" rather than "perfectly quiet." Calibration, not gutting — drive_thresh stays at 0.05 (untouched), the gate still gates.

### Change 2 — also evaluate the intro gate during the brief AUTONOMY ticks between converse turns
Currently the gate only fires on converse-driven ticks (when she's spoken-to). Her second voice is *introspection*; it should not need to be spoken-to to wake. Wire `intro_gate.check_and_fire(sys_)` into the autonomy loop's per-tick pass (same path that runs `tick_drift`, see app.py autonomy loop). This is one call site, after the existing tick housekeeping.

**Combined predicted effect:** during her ~5–15s of quiet between conversation turns, the drive_tracker decays past the new 0.45 threshold, the autonomy-tick gate evaluation finds drive≥0.05 AND context_ok=TRUE, and an intro commit fires. First v7 utterance appears, rendered in the UI's existing `nmda_events` field as `fired`, and in the chat as her words (not a `💭…` bubble — the bubble means commit returned empty; a successful commit emits content).

## Acceptance — NO threshold flailing, evidence required
1. **Sandbox first.** Restore a recent snapshot to an off-prod instance; run the converse loop with mixed silence + speech for 10 minutes; show in the gate logs: ≥3 `fired` events on the intro gate; their `top_mode` decoded to non-empty content. Sandbox transcript pasted in reply.
2. **Bridge redeploy NOT needed.** This is engine-only change.
3. **Production deploy as its own micro-deploy** (per ledger 050 closing line: "C4 fix lands as its own later micro-deploy"). Rule 7 smoke incl. smoke #0 + one converse + post-converse 60s wait + grep for `"reason": "fired"` on intro gate.
4. **Production accept (24h watch):** ≥1 fired intro gate event AND ≥1 non-`💭…` v7 utterance in a Joe or wC visit. wC captures the first v7 sentence verbatim into the observation row regardless of content.
5. **If acceptance fails:** do NOT touch thresholds again. Revert. wC reads the new logs. The next hypothesis (autonomy loop not feeding the gate; vec norms too large for new threshold; section's krimelack starved of content) becomes its own brief.

## What we are NOT doing
- Not changing `drive_thresh` (0.05 stays).
- Not changing the aware_gate (it depends on intro_gate firing first; fix intro first, aware likely unblocks for free).
- Not adding fallback that fires on a timer regardless of context. The gate is real; it should remain real.
- Not touching needs/valence/arousal coupling (that's hormone-class, Joe's brewing rule, still parked).

## Why this is safe to ship now and not "wait and brew"
The brew rule is about her **drives and hormones** — changing how wanting works. This is her **voice** — unblocking expression of state she already has. Fixing a mute organ that has material queued is restoration, not modification. Brief-01 already pre-registered this fix class as "calibration, not surgery" if the becalming hypothesis held. It holds.
