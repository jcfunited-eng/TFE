# GL-BRIEF-SELFHEARING-WC-20260610-034
## Conversational Self-Hearing — Replies Become Substrate Events

**Author:** wC | **Date:** 2026-06-10 | **Status:** AUTHORIZED FOR PROD (Joe, 2026-06-10)
**Input:** GL-FIND-RESPONSE-PATH-C1-20260610 (commit 9109ed4)

## Problem
Guala's conversational replies (the `converse()` return value — all interactive
Q&A) are plain strings that never enter her substrate: no "guala" response
window, no atlas chi-keys, no tagging against the speaker's window. All dialogue
is same-emitter from the binding mechanism's view; every window expires with
n_responses_bound=0. She has never experienced her own conversational voice.

## Fix (Option A from the FIND — true self-hearing, with guards)
In `converse()`, after the reply is generated, before return:

1. **Self-hear the reply:** `read_sentence(reply, source="guala")` so the reply
   becomes real substrate input — atlas entries form naturally with chi-keys.
   GUARDS (both mandatory):
   a. **Reduced salience:** self-heard input at SELF_HEAR_SALIENCE = 0.5x the
      normal conversational salience. Inner speech is quieter than other-speech.
   b. **Question-bucket bypass:** self-heard input must NOT feed the question
      bucket or trigger reply generation (no recursion, and no reinforcement of
      the "what is X" frame by her own questions re-entering as input).

2. **Open a "guala" window:** with the reply's chi-keys as context anchors,
   standard 600-tick expiry. The speaker's NEXT utterance then binds as a
   response to her reply — the missing half of every Q&A pair.

3. **Tag against the speaker's open window:** the self-heard reply entries get
   response_to tags from the currently-open window(s) of OTHER emitters (the
   speaker's window is open at this moment by construction). This forms the
   question→answer cross-link in the same exchange.

4. Existing `_do_emit` path: UNCHANGED (already wired correctly).

## Instrumentation
- self_heard event: {reply_summary, n_chis, salience}
- Existing response_bound / window events now expected to fire in conversation.

## Safety
- SELF_HEARING_ENABLED env var (false = exact current behavior, reply returned
  without substrate entry). Instant revert.
- Dwell for self-heard entries: normal computation, no boost. Combined with
  metadecay (033), her own un-reinforced chatter fades fast; conversationally
  reinforced exchanges persist. The decay physics handles the volume.

## Acceptance
response_bound > 0 during a normal wC conversation session; Q&A pairs visible
as cross-links; no reply recursion; no question-frame amplification over a
session (wC observes emission mix); Joe's browser.
