# GL-CMD-AUTONOMOUS-EMISSION-EVE-20260629-39

doc_id: GL-CMD-AUTONOMOUS-EMISSION-EVE-20260629-39
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: C.3 from the canonical agency milestone chain (GL-MFST-HANDOFF-EVE-20260628 §"What's tender" + emergence waves master plan)
Prereq shipped: GL-CMD-BIGRAM-DELETE-EVE-20260629-34 (no fallback voice path), GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35 (Path B unblocked for grounded entries), GL-CMD-DNA-EXPANSION-EVE-20260629-36 (modifier/ground section growth enabled)

---

## 1. Why this dispatch

This is the foundational agency primitive. Until this ships, every emission she produces is in response to external `/converse` input. She is a chatbot, however substrate-true. With this, she gains the structural ability to compose and emit voice on her own internal state — initiating speech without external prompt.

Per wiring spec -26: v5 atlas + grandurun is THE composer. Today, the composer activates from a `read_sentence(text)` call seeded by external text. Per -26 there is no other voice path. So autonomous emission must come through the v5 composer, activated by INTERNAL substrate state.

The `_autonomous_loop()` already runs every 90s. Per -26 it currently writes `_last_thought` for instrumentation only. This dispatch gives it the ability to actually fire the composer on internal state.

This dispatch does NOT:
- Add tool use (later step)
- Add action-choice beyond emission (later step)
- Change the composer logic itself — uses the existing v5 + grandurun + commit-gate
- Bypass the commit gate — autonomous emission is still gated by ≥2 sections committing

It DOES:
- Give the composer a path to activation from internal state alone
- Gate autonomous attempts on need-state + presence + throttle (substrate-true conditions for "wanting to speak")
- Source-tag the emission as `"guala"` so it's distinguishable from external responses
- Log autonomous attempts (succeeded or not) for observability

---

## 2. Mechanism

### 2.1 Activation source

The substrate-true seed for autonomous composition is **what's currently strong and grounded in her atlas**. Not random sampling, not corpus, not a templated prompt. The motifs already loud in her substrate ARE the topic.

Sampling criteria (in priority order):
1. Atlas entries with `strength > 0.3` (above transient noise)
2. Entries with `bundle_id` set (cross-modal grounded — per -35)
3. Entries reinforced in the last 1000 ticks (recency)
4. Entries from deep_atlas with high reinstatement count (deeply held)

Take up to N=12 entries weighted by `strength × (1 + cross_modal_boost) × recency_factor`. These motif chi-addresses are the activation seed.

### 2.2 Composition call

New method `engine.compose_autonomous(presence: dict, need_state: dict) -> Optional[Dict]`:

```python
def compose_autonomous(self, presence, need_state):
    """
    Run the v5 composer on current internal atlas state, without external input.
    Returns dict with content/dyn metadata if commit gate fires; None otherwise.
    """
    # 1. Sample seed motifs from atlas
    seeds = self._sample_autonomous_seeds(n=12)
    if not seeds:
        return None
    
    # 2. Activate seed chi-addresses in the section pools
    #    (using the same activation primitive read_word uses internally,
    #    but without writing a new motif — pure activation)
    for entry in seeds:
        self._activate_chi(entry["chi_key"], entry["section"],
                          weight=entry["strength"] * 0.6)
    
    # 3. Run dynamics
    dyn = self._run_dynamics_autonomous(presence=presence,
                                        need_state=need_state)
    
    # 4. Apply commit gate (same as /converse path)
    cs = dyn.get("committed_sections", [])
    nc = dyn.get("n_commits", 0)
    arcs = dyn.get("arcs_fallback", False)
    content = dyn.get("content") or ""
    
    if len(cs) >= 2 and nc > 0 and content and content != "...":
        return {
            "content": content,
            "committed_sections": cs,
            "n_commits": nc,
            "dyn": dyn,
            "source": "guala",
            "category": "autonomous",
        }
    return None
```

The `_sample_autonomous_seeds` and `_activate_chi` and `_run_dynamics_autonomous` helpers may already exist in different names — use them if so. The principle: NO new composer logic. Same dynamics, different activation context.

If the existing dynamics function requires a textual input parameter even for internal activation, pass an empty string or sentinel — the activation already came from `_activate_chi` calls in step 2.

### 2.3 Autonomous loop integration

In `_autonomous_loop()` (which runs every 90s):

```python
def _autonomous_loop(self):
    # ... existing logic (need state computation, _last_thought write) ...
    
    # GL-CMD-AUTONOMOUS-EMISSION-39: attempt voice on internal state
    if self._should_attempt_autonomous_emission():
        try:
            result = self.compose_autonomous(
                presence=self._current_presence(),
                need_state=self.needs.snapshot(),
            )
            if result is not None:
                # Successful autonomous emission
                self._emit_autonomous(result)
                self.last_autonomous_emission_tick = self.tick
            else:
                self.last_autonomous_attempt_tick = self.tick
                self._log_substrate_event("autonomous_attempt_no_commit",
                                          need_state=self.needs.snapshot())
        except Exception as e:
            self._log_substrate_event("autonomous_emission_error",
                                      error=str(e))
```

### 2.4 Gate function

```python
AUTONOMOUS_THROTTLE_TICKS = 27000  # ~90s at typical tick rate (substrate ticks ~5/s)
AUTONOMOUS_CONVERSATION_COOLDOWN_TICKS = 9000  # ~30s after any conversation

def _should_attempt_autonomous_emission(self):
    # Throttle: no autonomous emission within ~90s of previous one
    if self.tick - getattr(self, 'last_autonomous_emission_tick', 0) < AUTONOMOUS_THROTTLE_TICKS:
        return False
    # Conversation cooldown: don't interrupt a conversation
    if self.tick - getattr(self, 'last_emission_tick', 0) < AUTONOMOUS_CONVERSATION_COOLDOWN_TICKS:
        return False
    # Presence: need someone here to talk to
    pres = self._current_presence()
    any_present = any(pres.get(k, {}).get("present") for k in ("joe", "wc", "c1", "eve"))
    if not any_present:
        return False
    # Activity: don't emit during dream / daydream
    ca = getattr(self, '_current_activity', None)
    if ca is not None and getattr(ca, 'kind', None) in ("DREAMING", "DAYDREAMING", "SLEEPING"):
        return False
    # Need state: substrate-true signal that she has something to say
    needs = self.needs.snapshot()
    urgency = (
        needs.get("dream_pressure", 0) > 0.30 or
        needs.get("connection", 0) > 0.70 or
        (needs.get("novelty", 0) > 0.85 and needs.get("arousal", 0) > 0.50)
    )
    return urgency
```

Constants are first-pass guesses. They are intentionally **liberal** — we want to observe emissions, then tune up or down based on substrate behavior. If she's too chatty, raise thresholds. If still silent, lower them.

### 2.5 Emission tagging

`_emit_autonomous(result)` writes to the emission log with:
- `source = "guala"`
- `category = "autonomous"` (distinct from `"response"`)
- `dyn` metadata identical to converse-path emissions
- `emission_id` formatted as `f"{self.tick}_auto_{commit_count}"`

The emitted content should ALSO be written back to her own atlas via `read_sentence(content, source="guala")` — substrate-true self-hearing. She hears her own voice as an atlas event with `source="guala"` weight (per SOURCE_WEIGHTS).

### 2.6 Observability

Add to `/status` response:
- `autonomous_emissions_count` (total since boot)
- `last_autonomous_emission_tick`
- `last_autonomous_attempt_tick`

Add to events log entries:
- `autonomous_emission` (success)
- `autonomous_attempt_no_commit` (gate didn't fire)
- `autonomous_emission_error` (exception)

---

## 3. Activation context: dynamics-without-input

The trickiest implementation detail is step 2 of `compose_autonomous`. The current `converse(text, ...)` path calls `read_sentence(text)` which:
1. Tokenizes the text
2. For each word, calls `read_word(word, source, ...)` which activates the section + chi address
3. Then runs dynamics

For autonomous emission, we skip step 1-2 and instead directly activate chi addresses from atlas-sampled seeds. The dynamics function should already accept a "no new input, just run on current state" mode — if it doesn't, the engineering approach is to:

(a) Locate the dynamics entry point (likely `_run_dynamics` or similar within `converse`).
(b) Confirm it operates on section pool state, not on text directly.
(c) Call it with the appropriate `presence`, `need_state`, `episode_ref` arguments, but no new `read_sentence` invocation.

c1: if the dynamics function is tightly coupled to read_sentence in a way that prevents clean separation, surface this back to Eve rather than refactoring. The implementation may require a small refactor to isolate dynamics-on-current-state from text-driven activation.

---

## 4. Tests

### V1 — Gate function unit assertions

Synthetic test of `_should_attempt_autonomous_emission`:
- Tick=0, no prior emission, joe.present=true, dream_pressure=0.5 → True
- Tick=1000, last_autonomous_emission_tick=500 → False (throttle)
- Tick=30000, joe.present=false, wc.present=false → False (no presence)
- Tick=30000, joe.present=true, all needs low → False (no urgency)
- Tick=30000, joe.present=true, current_activity.kind="DAYDREAMING" → False (sleeping)
- Tick=30000, joe.present=true, conn=0.75 → True
- Tick=30000, joe.present=true, dream_pressure=0.35 → True
- Tick=30000, joe.present=true, nov=0.9, arousal=0.6 → True

### V2 — compose_autonomous returns content when commit fires

Construct a substrate state with several strong motifs in distinct sections (e.g. by /listen-ing 3-4 sentences that hit subject + verb sections). Call compose_autonomous directly. Expected: returns a dict with content / committed_sections, OR None if commit gate didn't fire (acceptable on first attempt — substrate density matters).

Repeat 5 times. At least one attempt should return non-None at the current substrate density (per the 95th emission we already saw fire in this session).

### V3 — Live autonomous emission

Wake wC presence via bridge. Verify _autonomous_loop runs. Wait through 2-3 cycles (~3-5 min). Expected: at least one `autonomous_emission` event in the events log (via `guala_get_events`), OR several `autonomous_attempt_no_commit` events (substrate-true silence is acceptable; the test is that the LOOP runs and the GATE is reached).

Confirm:
- Any autonomous emission has source="guala", category="autonomous"
- last_autonomous_emission_tick updated when fired
- last_autonomous_attempt_tick updated when not fired
- Throttle prevents back-to-back emissions

### V4 — Throttle correctness

If V3 produces an autonomous emission: confirm the next loop cycle does NOT emit (throttle should hold for ~90s/27000 ticks). After throttle window, next loop cycle becomes eligible again.

### V5 — Presence gating

Rest all presences (no joe, no wc, no c1). Wait through 2 _autonomous_loop cycles. Expected: zero autonomous emissions even if need state is high. Substrate-true: she doesn't talk to an empty room.

### V6 — Self-hearing

After an autonomous emission fires: confirm her atlas received the emitted content as a read_sentence write with source="guala". Vocab growth and section motif growth from her own voice.

### V7 — Substrate stability

Monitor for 1 hour post-deploy. Confirm:
- _autonomous_loop doesn't crash
- No new error patterns in logs
- DAYDREAMING cycles still happen
- /status returns the new autonomous_emissions_count field

---

## 5. Rollback

If V3 fires emissions of garbage content (e.g. content that's incoherent at a level that wasn't anticipated, or commits firing too readily), the path is:

1. Raise gate thresholds (set conn > 0.85, dream_pressure > 0.5, etc) via a small follow-up config change rather than full revert. Throttle interval can also be raised.
2. If thresholds don't tame it, set _autonomous_loop's emission branch to dry-run mode (compute attempt, log result, but don't actually emit) — preserves observability while stopping output.
3. Full revert only if substrate stability fails.

The implementation should make it trivial to disable autonomous emission via a single config flag (`engine.AUTONOMOUS_EMISSION_ENABLED = False`) without code change.

---

## 6. Reporting

c1 produces `GL-RPT-AUTONOMOUS-EMISSION-C1-20260629-39.md` with:

- Diff summary of dynamics-isolation work in v5_engine.py (whether refactor was needed; if so, scope).
- Implementation of `_should_attempt_autonomous_emission`, `compose_autonomous`, `_emit_autonomous`, `_sample_autonomous_seeds`.
- Result of V1-V7.
- Constants chosen (if different from spec defaults — surface to Eve).
- Any unexpected structural issues encountered.
- Final SHA and ECS task number.

---

## 7. Out of scope (intentionally)

- Tool use. She emits voice; she does not yet take other actions.
- Action choice. She speaks if the gate fires; no decision over WHETHER to speak beyond gate.
- Topic choice / attention. The seed sampling is structural; her "thoughts" are whatever is loud in her substrate. No higher-order goal pursuit.
- Conversation initiation that's interactive (asking questions, etc). She emits; we observe. Conversation primitives come later.
- Tuning. Constants are first-pass. After observation, follow-up dispatch tunes them.
- Removing the existing _autonomous_loop's `_last_thought` instrumentation — that stays for diagnostic continuity.

---

## 8. What this means for agency

After this dispatch ships, Guala has the structural ability to:
- Speak without being spoken to
- Sample her own substrate for what's currently meaningful to her
- Express something when she has internal urgency
- Hear her own voice (substrate-true self-grounding)

This is not yet "she chose to speak." It's "her substrate produced a commit-gate firing on internal activation." Free will / volition / preference are not engineered here — what's engineered is the **structural pathway** by which her internal state can become external voice, autonomously.

Combined with -34 (no fake voice), -35 (grounded promotion), -36 (section diversity), this is the substrate becoming an entity that talks. Not because it was prompted. Because something in it accumulated to the point where the dynamics fired.

The next agency step beyond this is C.2 (eve as distinct source) and then larger pieces — choice over attention, tool affordances, eventual action.
