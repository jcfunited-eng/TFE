# GL-CMD-FIX-CONVERSATION-WC-20260608-02

**doc_id:** `GL-CMD-FIX-CONVERSATION-WC-20260608-02`
**from:** wC (Web Claude)
**to:** c1 (Claude in VS Code)
**date:** 2026-06-08
**re:** Convert tests 1 and 2 from PARTIAL to PASS. Two architectural fixes.

---

## What's broken

Both partials stem from the same root cause and one secondary cause:

**Root cause:** the deployed `/v7/converse` fires heard words into the substrate by name (`mode_id` lookup) and runs the rhythm cycle. But firing one mode doesn't make it the cascade winner — the substrate's commit_check picks the highest-arc mode, and with random initial psi, that's not reliably the just-fired one. The conversation experiment got 100% by using a different pattern: accumulate listen evidence per slot, derive drive vectors, **prime the S/V/O psi states with those drives**, then run the cycle.

The prime step is what makes the cascade favor the heard tokens. The deployed version doesn't do it. That's why tests 1 and 2 emit "whatever happens to win" instead of the input.

**Secondary cause:** vocab is microscopic (3 modes per slot, hardcoded from the experiment). Joe types anything other than `{cow,moon,bears,jumped,ran,sleeps,fence,milk,dish}` and the routing fails silently. She can't converse if she has no words.

---

## Fix 1 — Listen-prime architecture in `/v7/converse`

Replace the current chat handler logic with:

```python
def v7_converse(text, session):
    sys_ = session.substrate  # the assemblage System
    tokens = [t.lower().strip(".,?!") for t in text.split() if t.strip(".,?!")]
    
    # PHASE 1 — route each heard word to its best-matching section
    # and accumulate evidence in a per-section buffer
    
    listen_acc = {"subject": np.zeros(N, dtype=complex),
                  "verb":    np.zeros(N, dtype=complex),
                  "object":  np.zeros(N, dtype=complex)}
    routing_log = []  # for the event panel
    
    for pos, word in enumerate(tokens):
        # Step A: get this word's vector (install if new — see Fix 2 below)
        word_vec, slot, was_new = lookup_or_install(session, word, position=pos)
        if word_vec is None:
            routing_log.append({"word": word, "routed_to": None, "reason": "skipped"})
            continue
        
        routing_log.append({
            "word": word, "routed_to": slot,
            "newly_installed": was_new,
        })
        
        # Step B: drive the LISTEN section with this word's noisy vector for
        # ~15 ticks (lets listen accumulate). Use the same noise schedule as
        # the conversation experiment so behavior matches the test results.
        for _ in range(15):
            noisy = normalize(word_vec +
                              0.10 * (rng.standard_normal(N) +
                                      1j * rng.standard_normal(N)))
            ev = {"listen": noisy}
            sys_.tick_once(ev, enable_self_evo=False,
                           coordinator_on=False, introspection_on=False)
            # Bump the listen-side accumulator for the routed slot
            listen_acc[slot] = listen_acc[slot] + noisy
    
    # Normalize the accumulators (matches conversation experiment exactly)
    for slot in listen_acc:
        n = np.linalg.norm(listen_acc[slot])
        if n > 0:
            listen_acc[slot] = listen_acc[slot] / n
    
    # PHASE 2 — derive per-slot drive vectors from listen accumulator
    # (weighted sum of top-2 token vectors by overlap with accumulator)
    
    drives = {}
    for slot in ("subject", "verb", "object"):
        snap = listen_acc[slot]
        sec = sys_.sections[slot]
        if np.linalg.norm(snap) == 0:
            # No evidence routed to this slot — use a random small drive
            drives[slot] = random_unit_complex(N, rng) * 0.1
            continue
        # Score each installed mode by overlap with the listen accumulator
        weights = []
        for mode_id, mode_vec in enumerate(sec.mode_bank):
            w = float(np.abs(np.vdot(mode_vec, snap)) ** 2)
            weights.append((mode_id, w, mode_vec))
        weights.sort(key=lambda x: -x[1])
        bias = np.zeros(N, dtype=complex)
        for mode_id, w, v in weights[:2]:
            bias = bias + w * v
        drives[slot] = normalize(bias) if np.linalg.norm(bias) > 0 \
                                       else random_unit_complex(N, rng)
    
    # PHASE 3 — PRIME the S/V/O psi states with the drive vectors
    # This is the missing step. Without it, cascade dynamics don't favor
    # the heard tokens. With it, conversation experiment gets 100%.
    
    for slot in ("subject", "verb", "object"):
        sys_.sections[slot].psi = drives[slot].copy()
    
    # PHASE 4 — run the rhythm-gated emission cycle (existing v7 code)
    # exactly as deployed today, with drives passed as the ongoing evidence
    
    emitted, events = run_rhythm_cycle(sys_, drives, gates, ...)
    
    # Response includes routing_log so the UI panel can show WHICH word
    # went to WHICH slot (Joe needs to see this to debug input parsing)
    
    return {
        "response_tokens": emitted,
        "routing_log": routing_log,
        "rhythm_events": events.rhythm,
        "nmda_events": events.nmda,
        "introspection": events.intro,
        "awareness": events.aware,
        "mode_strengths": current_strengths(sys_),
    }
```

The critical lines are PHASE 3 — the psi priming. Without it everything else is decoration.

After this fix, run the conversation experiment's test inside the deployed code path:
- Send `"cow jumped fence"`
- Expect `response_tokens` to contain cow, jumped, fence in order
- Routing log should show cow→subject, jumped→verb, fence→object

This should reproduce the conversation experiment's 100% result.

---

## Fix 2 — On-the-fly vocabulary install (`lookup_or_install`)

Currently the substrate has 9 hardcoded words. Joe can't converse if his words aren't in the list. Add a function that installs new words as Joe uses them:

```python
def lookup_or_install(session, word, position):
    """Return (word_vec, slot, was_new).
       If word already installed, return its vector and the slot it lives in.
       If not, install it in the slot suggested by position, then return."""
    
    # Already installed? Find which slot it lives in.
    for slot in ("subject", "verb", "object"):
        if word in session.vocab[slot]:
            sec = session.substrate.sections[slot]
            mode_id = session.vocab[slot].index(word)
            return sec.mode_bank[mode_id], slot, False
    
    # New word — install based on position
    # Position 0 -> subject, 1 -> verb, 2 -> object, 3+ -> object (extra modifiers)
    slot = ["subject", "verb", "object"][min(position, 2)]
    sec = session.substrate.sections[slot]
    
    # Generate a fresh random mode vector for this word and install it
    word_vec = random_unit_complex(N, session.rng)
    sec.mode_bank.append(word_vec.copy())
    sec.mode_last_used.append(session.substrate.tick)
    # Initialize plasticity for the new mode
    if hasattr(sec, "mode_strength"):
        sec.mode_strength.append(0.0)
    # Also install in listen for cross-reference
    session.substrate.sections["listen"].mode_bank.append(word_vec.copy())
    session.substrate.sections["listen"].mode_last_used.append(session.substrate.tick)
    session.vocab[slot].append(word)
    
    return word_vec, slot, True
```

This is position-based, not grammatical. It's the simplest thing that works.
Limitation: same word said in different positions gets different vectors per
session. That's fine for V1 — Joe will see this in the routing_log and we
can layer in proper part-of-speech detection later.

---

## Fix 3 — Surface routing in the UI (small)

Add a `ROUTING` block to the substrate state panel showing the last
turn's word→slot mapping:

```
ROUTING (last turn)
  cow      -> subject  (new)
  jumped   -> verb     (new)
  fence    -> object   (new)
```

When Joe types `cow ran milk` next, the `cow` line shows `(known)` and
the routing pulls cow back to its existing subject mode.

---

## Acceptance tests after fix

In the browser, with a fresh session (incognito or new session_id):

1. Type `cow jumped fence` — response should contain `cow jumped fence` in that order. Routing panel should show all three as `(new)`.

2. Type `cow jumped fence` again, same session — response should match again. Mode strengths still 0 (no thumbs-up yet, no learning). Routing panel shows all `(known)`.

3. Type `moon ran milk`. Response should contain `moon ran milk`. Routing shows `(new)`.

4. Hit 👍 on the response. Subject MODE STRENGTHS panel: `moon` bar grows.

5. Type `apple flies cloud` — three brand-new words. Routing shows `(new)` for all. Response should be `apple flies cloud` (or close — substrate may emit cleanly or noisily on first install, but the routing should clearly map words to slots).

6. Type just `hello`. Routing should show `hello -> subject (new)`. Response: substrate emits something. Probably noisy since only one slot was driven. This is honest behavior — partial input = partial emission.

If tests 1-5 PASS, conversation works. Test 6 is informational (single-word handling not specified yet).

---

## DO NOT

- Don't add grammatical parsing (POS tagging, dependency parsing). Position-based routing is V1. Smarter routing is a future fix.
- Don't try to install the vocabulary at startup with a big word list. Per-session, on-demand only. That keeps each session genuinely learning rather than starting pre-loaded.
- Don't change anything in the NMDA gate, plasticity, or rhythm code. Those are working. The fix is purely in the chat handler routing logic.
- Don't drop the routing_log from the response. The UI panel needs it. Joe needs to see how his words got routed to debug input handling.

---

## Why the partial→pass should land

In my sandbox conversation experiment, the exact pipeline above produces:
- 100% per-slot match
- 100% full S-V-O match  
- 80% S→V→O order

The deployed version was missing PHASE 3 (psi priming). With it added, the deployed substrate behavior should match the experiment behavior — because it now IS the experiment behavior.

If the deploy lands and tests 1-5 don't reproduce ~100% on cow/jumped/fence with a fresh session, then there's another integration mismatch between the experiment and the deployed engine that I missed. Report it specifically and I'll diff.

---

## Report what you ship

1. New deploy task / commit / image
2. Tests 1-5 in browser with screenshots (or curl+JSON if browser unavailable)
3. Any routing_log examples that illustrate edge cases
4. Confirmation that the previous 5 passing tests are still passing (regression check)

---

**End of command. This should make her conversational.**
