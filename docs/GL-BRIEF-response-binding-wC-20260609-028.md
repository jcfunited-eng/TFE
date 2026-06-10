# GL-BRIEF-response-binding-wC-20260609-028

**Title:** Response Binding — Grounding Brief and Implementation Spec
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v3-wC-20260609-024 (will need v4 update reflecting revised sequence)
**Status:** Design ready. c1 command ready to send after Picture Habituation lands and is observed.
**Priority:** Foundational. Without this, dialogue is parallel monologues — she asks, we answer, but the substrate doesn't bind the answer TO the question. This is the primitive that makes "reply" meaningful.

## What This Fixes

When Guala emits "what is wc" and you respond by uploading a picture of yourself or saying "wc is friend," her substrate processes both the emission and your response, but they exist as independent events. The emission's chi-key and the response's chi-key are not linked in atlas. There's no "this picture is the answer to that question."

Result: even after dozens of question-answer exchanges, she never builds "wc means this picture" or "joe answered with these words." The bindings she could form to learn from conversation aren't being formed because the temporal-causal link is missing.

This was missed when we built input pipelines because we focused on input fidelity (color preservation, cochlear processing, corpus reading) rather than on how inputs RELATE to her ongoing dialogue. The senses work — they just produce orphan bindings instead of conversational structure.

## Biological Grounding

This is the substrate of joint attention, the foundational mechanism by which children acquire language and adults sustain meaningful conversation.

**Joint attention (Tomasello, Carpenter, Liszkowski).** Emerges in human infants at 9-12 months. The infant follows the adult's gaze or pointing; the adult names what they're co-attending to; the binding between word and referent forms because both parties are attending to the same thing at the same time. Without joint attention, language acquisition is severely impaired — this is one of the earliest and most reliable markers of typical development.

The mechanism is referential triangulation: three-way binding between (self, other, object-of-attention). The infant develops "you see what I see" as a cognitive operation, which is also the substrate of theory of mind.

**Contingency detection (Watson, Rovee-Collier).** Infants are exquisitely sensitive to temporal contingency. When their behavior is followed predictably by another's behavior, they learn the contingency within 3-5 trials. Mobile-paradigm experiments show infants will modulate their own actions to maintain contingent responses from caregivers. The substrate-relevant insight: temporal proximity + causal contingency = automatic learning of the relationship.

**Conversation as joint construction (Sacks, Schegloff, Jefferson; conversation analysis).** Dialogue is structurally organized around turn-taking, where each turn references and responds to the prior turn. The meaning of any utterance is partly constituted by what it follows. Without binding successive turns to each other, you don't have conversation — you have parallel monologues.

**Episodic binding in hippocampus.** Eichenbaum, Tulving, and many others: temporally-proximate events get bound into unified episodic traces. When you ask a question and get an answer, the question-answer pair becomes a single episode, not two separate memories. This is how dialogue becomes memory rather than just noise.

**The substrate-relevant insight:** without temporal-causal binding between an utterance and the inputs that follow it, dialogue is structurally absent. The substrate can process inputs and produce outputs, but it can't learn from conversation. Joint attention as substrate primitive is what makes language acquisition possible at all.

## The Simplest Sufficient Approximation

Every emission opens a **response window** — a brief tick range during which subsequent inputs are tagged as "in response to" that emission. Bindings formed from response-window inputs include a cross-link to the emission's chi-key in atlas. The same applies in reverse: every input from a pair-bonded source opens a response window for HER emission.

Question-answer pairs become bound units in atlas, not separate fragments. Recall of either side raises probability of recalling the other.

Formula sketch:

```
On emission at tick T with chi_key K_emit:
  open response_window(emitter=guala, opened_at=T, expires_at=T+W)
  K_emit becomes the context_anchor for the window

On input at tick T' arriving from source S during open window:
  if T' < expires_at:
    tag input with response_to: context_anchor
    when input creates atlas binding at chi K_input:
      add cross-link: K_emit ↔ K_input
    log event: response_bound { context_anchor, input_chi, source, delta_t }

On input from joe/wc at tick T with chi_key K_input:
  open response_window(emitter=joe_or_wc, opened_at=T, expires_at=T+W)
  K_input becomes the context_anchor

On her emission at tick T' during open window from joe/wc:
  similarly bind her emission to the input that prompted it
```

Window length W: start at 600 ticks (≈30 seconds at 20Hz). Wide enough to capture human reply time (text typing, picture upload, sound recording), narrow enough that unrelated events don't get falsely bound. Tunable based on observation.

## Substrate-Coherent Design

### What Stays the Same

- All existing input pipelines (text converse, picture upload, sound upload, corpus reading)
- All existing emission mechanism
- All existing atlas binding logic
- All existing autonomy and activity selection
- Pair-bond mechanism

### What Changes

**1. Add response_window state.**

On the Guala object, maintain a list of currently-open response windows:
```
self.open_response_windows = [
    {
        "emitter": "guala" | "joe" | "wc" | "c1",
        "context_anchor": chi_key_of_originating_utterance,
        "opened_at_tick": int,
        "expires_at_tick": int,
        "source_context": dict  # source, content summary, etc
    },
    ...
]
```

Cleanup: at each `_autonomy_tick`, prune windows where `expires_at_tick < current_tick`.

**2. Open response window on every utterance.**

In `_atick_emitting` after emission fires:
```
open_response_window(
    emitter="guala",
    context_anchor=emission_chi_key,
    opened_at=current_tick,
    expires_at=current_tick + RESPONSE_WINDOW_TICKS  # default 600
)
```

In the converse path when a source utterance arrives (joe, wc):
```
open_response_window(
    emitter=source_name,
    context_anchor=utterance_chi_key,
    opened_at=current_tick,
    expires_at=current_tick + RESPONSE_WINDOW_TICKS
)
```

**3. Tag inputs arriving during open windows.**

In every input handler (text converse, picture upload, sound upload):
- Before processing, check `open_response_windows`
- If any window from a DIFFERENT emitter is open, this input is a response
- Tag the input event with `response_to: [list_of_context_anchors]`

Critical: a response can be tagged as responding to multiple windows. If Guala asked "what is wc" AND "what is joe" within the window and you reply with a picture, that picture binds to both questions. Multi-context binding is more biologically accurate than picking one.

**4. Cross-link atlas bindings.**

When atlas.add_claim is called from an input handler that has `response_to` tags:
- The new atlas entry includes a `response_context` field listing the context_anchor chi_keys
- Bidirectional cross-link: the context_anchor entries also get updated to reference the new entry's chi-key as a "received_response"
- This creates a graph structure: utterances and their responses are connected as edges in atlas

Backward compatible: existing entries without `response_context` or `received_response` continue to work as before.

**5. Use cross-links in recall.**

When recall fires on a chi-address and finds an entry with `response_context` or `received_response` links, optionally also recall the linked entries (probability-weighted by atlas strength of the linked entries).

This is what makes Q&A pairs surface together: recall of "what is wc" surfaces the picture/sound/book/text that was the answer; recall of the answer surfaces the question.

**6. Event logging.**

New events:
- `response_window_opened`: {emitter, context_anchor, opened_at, expires_at}
- `response_bound`: {context_anchor, input_chi, source, delta_t_ticks}
- `response_window_expired`: {emitter, context_anchor, n_responses_bound}

These let us observe conversational structure forming in real time.

### What This Doesn't Change

- Mode_bank: unchanged
- Sight motif formation: unchanged
- Vocab installation: unchanged
- Dream mechanism: unchanged (but dream will now consolidate response-bound pairs as units once Dream Consolidation lands)
- Suffering / recovery: unchanged
- Activity selection: unchanged
- Picture habituation: unchanged

This is pure additive structure on top of existing mechanisms.

## Interaction With Other Pieces

**Picture Habituation (landing first):** Response-window inputs might want to bypass habituation discount. If she asks "what is wc" and you upload a picture, that picture is contextually relevant even if it's a familiar image — joint attention overrides novelty. Implementation: when a picture is uploaded during an open response window, temporarily boost its attention payoff for the duration of the window. Optional refinement — can be added later if needed.

**Dream Consolidation (landing after this):** Dream replay should treat response-bound pairs as units. When dream samples a chi-address and finds a response_context link, the linked entry is also replayed and reinforced. This means question-answer pairs consolidate together rather than fragmenting. Major improvement to dream's value.

**Self-Section v3 (landing after Dream):** When she emits, her self-vector folds into the emission chi. The emission becomes the context_anchor. Responses bind to that context_anchor — which means responses to HER utterances form bindings near her self-vector. "Things people said to me" become identifiable in atlas via self-tag proximity. This is the precursor to entity-models of bonded-others.

**Vision Stage 2 (last):** When color cortex pipeline activates, the richer atlas bindings from pictures will include response_context tags. The visual cortex's output becomes part of the conversational graph rather than orphan bindings. Substantially more meaningful processing.

## Instrumentation

For observation:
- Count of response_windows opened per session
- Count of inputs that arrived during open windows vs not (orphan rate)
- Average inputs-per-window (some windows expire with 0 responses, some with many)
- Average delta_t between window-open and response (do humans/Guala respond fast or slow?)
- Cross-link density in atlas (entries with response_context, entries with received_response)
- Recall improvement over time: are emissions producing content (not "...") more frequently after response binding has accumulated?

## Acceptance for This Piece

After deploy and 30+ minutes of substrate time with active conversation:

- `response_window_opened` events fire on every emission and every source utterance
- `response_bound` events fire when inputs arrive during open windows
- `response_window_expired` events fire when windows close with appropriate response counts
- Atlas entries created during response windows have `response_context` populated
- A test sequence: she emits → upload a picture immediately → the picture's atlas binding includes a cross-link to the emission's chi-key
- A test sequence: joe says X → she emits within window → her emission's binding includes cross-link to X
- No regression in other autonomy events (activity_started/ended rate, suffering recovery, dream timing)
- Persistence survives — response_context links preserved across container restart

If response binding produces no observable change in atlas structure, window is too short or implementation has a hook-point bug. Tunable; observe and adjust.

## What Could Diverge From Design

- **Window length wrong.** 600 ticks may be too short (humans take a while to upload pictures from phone) or too long (unrelated background autonomy events get bound). Observe and tune.
- **Multi-context binding might explode.** If she emits multiple questions in rapid succession and you respond once, that response binds to ALL open windows. May or may not be desirable. Watch for over-binding.
- **Atlas size grows.** Cross-links use space. Atlas with response_context will be richer. May interact with atlas decay (linked entries should probably be harder to prune).
- **Existing chi-binding code may have implicit assumptions** about single-entry-per-chi-address. Cross-links complicate that. Audit carefully.

## c1 Command

```
RESPONSE BINDING — under GL-CHARTER-motivation-v3-wC-20260609-024
and per GL-BRIEF-response-binding-wC-20260609-028.

DO NOT START until Picture Habituation has landed and been observed
by wC for at least 30 minutes AND wC explicitly says "proceed with
response binding deploy."

NOTE: This is being inserted into the sequence before Dream
Consolidation because joint attention is foundational — Q&A pairs
need to be bound BEFORE dream consolidates them. Otherwise dream
just consolidates orphan fragments and conversational structure
never forms.

Targets production (Guala cdef9bcf) — substrate enhancement adding
a new conversational primitive.

GOAL: Add response window mechanism. Every utterance (Guala's
emissions OR pair-bonded sources speaking to her) opens a response
window. Inputs arriving during open windows get tagged as responses
and form cross-linked atlas bindings to the utterance that opened
the window. Q&A pairs become bound units in atlas.

STEP 1 — Audit existing emission and input handler code.

Read in gualaloom_v5_engine.py:
  - _atick_emitting (lines 1650-1660)
  - _do_emit (lines 1684-1718)
  - converse / input path (find the entry point where joe/wc utterances
    arrive and get processed)
  - Picture upload handler in app.py
  - Sound upload handler in app.py
  - Corpus reading handlers (if applicable for response-window context)

Report what you find. Identify the hook points where:
  - An emission completes and its chi-key is known
  - A source utterance arrives and its chi-key is computed
  - An input creates an atlas binding (add_claim path)

STEP 2 — Add response_window state.

On the Guala object:
  self.open_response_windows = []
  self.RESPONSE_WINDOW_TICKS = 600  # tunable

Persist in session state JSON. Backward-compatible.

Add cleanup: in _autonomy_tick, prune windows where
expires_at_tick < current_tick. Log response_window_expired event
with n_responses_bound counter.

STEP 3 — Open response window on emission.

In _atick_emitting (or _do_emit, whichever has access to the
emission's chi-key), after emission fires:

  open_window = {
      "emitter": "guala",
      "context_anchor": emission_chi_key,  # or hash of it
      "opened_at_tick": current_tick,
      "expires_at_tick": current_tick + self.RESPONSE_WINDOW_TICKS,
      "source_context": {"emission_content": content, "to_sources": to_sources}
  }
  self.open_response_windows.append(open_window)
  log event: response_window_opened

STEP 4 — Open response window on source utterance.

In the converse / input handler when a joe/wc utterance arrives:
  - Compute the utterance's chi-key (or use whichever chi-key
    represents this utterance — the listen section's commit chi
    is probably right)
  - Open a window with emitter=<source_name>, context_anchor=
    <utterance_chi>, similar structure as above
  log event: response_window_opened

STEP 5 — Tag inputs with response_to.

In every input handler (text converse from joe/wc, picture upload,
sound upload, book/corpus loading if applicable):

  Before processing the input:
    open_windows_from_others = [
        w for w in self.open_response_windows
        if w["emitter"] != current_input_source
        and w["expires_at_tick"] >= current_tick
    ]
    if open_windows_from_others:
        input.response_to = [w["context_anchor"] for w in open_windows_from_others]

The "from others" filter is critical: if joe speaks twice in a row,
the second utterance is NOT a response to the first (same emitter).
Responses come from different emitters.

STEP 6 — Cross-link atlas bindings.

When atlas.add_claim is called for an input with response_to tags:
  - Add response_context: [list of context_anchor chi_keys] to the
    new entry
  - For each context_anchor:
    - Look up the original entry at context_anchor
    - Add the new entry's chi_key to its received_response list
  - log event: response_bound { context_anchor, input_chi, source,
    delta_t_ticks }

Backward compatible: entries without response_context / received_response
work as before.

STEP 7 — Use cross-links in recall (light touch).

When recall fires on a chi-address and finds an entry with
response_context or received_response links:
  - Include the linked entries in the recall candidate pool
  - Weight by linked entry's atlas strength

This is the mechanism that surfaces Q&A pairs together. Keep light
in this initial implementation — don't over-engineer. Just include
linked entries in recall.

STEP 8 — Deploy to production.

Bounded change with clear hook points. Deploy to Guala (cdef9bcf).

STEP 9 — Test and observe.

After deploy:
  - Wake wc presence
  - Say "hello guala" — should open a response window from wc
  - Wait for Guala to emit (or trigger via her own autonomous emission)
  - If she emits within the window, her emission should be tagged
    as response_to the wc utterance
  - Conversely: when she emits, that opens a window
  - Upload a picture within her window
  - The picture's atlas binding should include response_context

Run for 30+ minutes with active conversation. Report:
  - Commit SHA
  - response_window_opened event count
  - response_bound event count
  - response_window_expired events with response counts
  - Average delta_t between window open and response binding
  - Atlas entries with response_context populated (count, sample)
  - Atlas entries with received_response populated (count, sample)
  - Whether her emissions still produce "..." or whether content
    started appearing (post-binding, recall may finally find linked
    entries from prior Q&A pairs)
  - Any regression in other autonomy
  - Honest narrative of what surprised you

WHAT NOT TO DO:
  - Start before Picture Habituation observed by wC and wC confirms
  - Modify any existing input pipeline behavior — only ADD tagging
    and cross-linking
  - Change emission mechanism, activity selection, suffering, or any
    other autonomy
  - Implement aggressive recall changes — keep step 7 light, refinement
    comes later
  - Tune RESPONSE_WINDOW_TICKS away from 600 in this iteration
  - Make response binding bypass picture habituation (refinement, future)

This is a foundational substrate primitive. The bar: dialogue
structure observable in atlas, no regression in other behavior.
```
