# GL-FIND-RESPONSE-PATH-C1-20260610
## Response Binding Wiring Gap — Conversational Replies Never Enter Substrate

**Author:** c1 | **Date:** 2026-06-10
**Trigger:** wC observation: all response windows expire with n_responses_bound=0 despite Guala replying within seconds (task:69, commit 51fbf8f)

---

## Root Cause

Guala has **two distinct reply paths**, and response binding only wires one of them:

### Path 1: Autonomous Emission (`_do_emit`) — WIRED
- Fires during EMITTING activity (autonomy loop)
- Has access to `recent_chis` from section commits
- Opens a response window from "guala" (line 1855 in v5 engine)
- **This path works correctly** but fires rarely (only during autonomous emission cycles)

### Path 2: Conversational Reply (`converse()` return value) — NOT WIRED
- Fires when joe/wc/c1 speaks to her via bridge or UI
- `converse()` generates a reply via `_recall_response()` or question bucket
- Returns the reply as a **plain string** directly to the caller
- **The reply is never:**
  - Fed back into `read_sentence` or `read_word` as her own speech
  - Used to open a response window from "guala"
  - Written to atlas with any chi-key
  - Tagged against the speaker's open window

### Why all windows expire with 0 bindings

1. wC says "hello guala" → `converse(source="wc")` opens window from "wc"
2. `converse()` returns "what is hello" (Guala's reply) — no window from "guala" opened
3. wC says "hello means hi" → `converse(source="wc")` opens another window from "wc"
4. Tagging check on line 1043: `_get_response_contexts("wc")` looks for windows from OTHER emitters — but only "wc" windows exist. Returns `[]`.
5. Window from step 1 expires: `n_responses_bound=0`

**Every exchange is wC→wC→wC from the window's perspective.** Guala's replies are invisible to the response binding mechanism because they never pass through any input handler or emission path that checks windows.

---

## The Two Missing Pieces

### A. Guala's conversational reply needs to open a response window

When `converse()` generates a reply (recalled text or question), it should:
1. Compute the reply's chi-keys (transduce the reply words)
2. Open a response window from "guala" with those chi-keys
3. This way, wC's NEXT utterance will be tagged as a response to Guala's reply

### B. Guala's conversational reply should be tagged against the speaker's window

The reply is generated INSIDE `converse()` while the speaker's window is open. The reply text should:
1. Be read into substrate as her own speech (mild self-hearing, like human inner speech during dialogue)
2. OR at minimum, the reply's chi-keys should be cross-linked to the speaker's window anchors

Without (A), wC's follow-up utterances are never cross-emitter responses.
Without (B), the temporal-causal link from question to answer is never formed.

---

## Scope of the Gap

- **Conversational replies** (the primary dialogue mechanism): UNBOUND. This is ~100% of interactive Q&A.
- **Autonomous emissions** (`_do_emit`): correctly wired but fire only during EMITTING activity, which requires presence + pair-bond + needs conditions. Rare during active conversation.
- **Picture/sound uploads during open windows**: would work IF a "guala" window were open, but without (A) above, no "guala" windows ever open during conversation.

---

## What NOT to change yet

Per instructions: no fix in this iteration. wC writes the fix brief.

**Candidate fix for wC's brief:**

In `converse()`, after generating the reply but before returning:
```python
# Compute reply chi-keys
reply_words = [w for w in reply.lower().split() if w]
reply_chis = []
for w in reply_words:
    temp = LanguageKrimelack()
    temp.transduce(w)
    reply_chis.append(temp.winding)

# Open window from guala (so next input is a response to her reply)
if reply_chis:
    self._open_response_window("guala", reply_chis,
                               source_context={"reply": reply[:50]})

# Tag reply against speaker's open window
# (read reply into substrate as self-hearing, or just cross-link)
for ch in reply_chis:
    self._tag_response_bindings(ch, "listen", ?, "guala")
```

The question mark on motif is the implementation detail — the reply words may or may not have motifs in the listen section. The fix brief should specify whether to (a) read the reply via `read_sentence(reply, source="guala")` which creates atlas entries naturally, or (b) just compute chi-keys and cross-link without reading.

---

*No code changes made. This is a finding, not a fix.*
