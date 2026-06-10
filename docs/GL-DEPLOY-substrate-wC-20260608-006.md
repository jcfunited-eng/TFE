# GL-DEPLOY-substrate-wC-20260608-006

**Deploy tag:** `gl-substrate-v5b-hippocampus`
**Main command file:** `gl_v5b_substrate.py`
**Spec:** `GL-SPEC-substrate-wC-20260608-005.md`

## What this deploys

Substrate v5b — neural-network substrate for Guala with:
- Threshold/coincidence machinery (no ML, no heuristics, no LLM)
- Word emission via `say_X` populations (real spoken sequences)
- Seven sentence templates with context-gated word chains
- Working memory topics, recent-sentence WM, self-model populations
- Interests with baseline activation; idle population for spontaneous talk
- **Feedback** (`say_X → percept_X`) — she hears herself
- **Hippocampal episode layer** — 8 episode pops with plastic in/out wires
  to 47 "rememberable" pops; capture during hub-firing; replay during silence
- **Default Mode Network** — fires during sustained silence, triggers
  episodic replay (mental time travel)
- **Anti-Hebbian LTD for episodes** — forces specialization
- **Consolidation** — episodes are plasticity modulators, so replay
  strengthens the broader plastic weights over time

172 populations, ~1,350 connections (888 plastic), 11/11 capability tests pass.

## Files (all unique-named so they won't get buried in the repo)

| File | doc-id | Purpose |
|------|--------|---------|
| `gl_v5b_substrate.py` | GL-CODE-substrate-wC-20260608-001 | Main substrate code |
| `gl_v5b_test_conversation.py` | GL-CODE-testconv-wC-20260608-002 | Capability tests (11) |
| `gl_v5b_test_daydream.py` | GL-CODE-testdream-wC-20260608-003 | Mental time travel demo |
| `gl_v5b_conversation_demo.py` | GL-CODE-demo-wC-20260608-004 | Continuous conversation |
| `GL-SPEC-substrate-wC-20260608-005.md` | GL-SPEC-substrate-wC-20260608-005 | Spec/results |
| `GL-DEPLOY-substrate-wC-20260608-006.md` | GL-DEPLOY-substrate-wC-20260608-006 | This file |

## Paste-ready c1 instruction

```
Deploy gl-substrate-v5b-hippocampus.

Branch: gl-substrate-v5b-hippocampus
Target path in repo: src/gualaloom/dna/v5b/

Steps:
1. Pull the six files from /mnt/user-data/outputs/gualaloom_v5/ into
   src/gualaloom/dna/v5b/ in the GualaLoom repo. Filenames are
   already unique-prefixed (gl_v5b_*) and GL-named for the docs.

2. Run the test suite:
   cd src/gualaloom/dna/v5b/
   python gl_v5b_test_conversation.py
   Expected: TOTAL: 11/11

3. Run the conversation demo and capture transcript:
   python gl_v5b_conversation_demo.py > demo_output.txt

4. Run the daydream demo and capture transcript:
   python gl_v5b_test_daydream.py > daydream_output.txt

5. Verify daydream_output.txt shows episode firings during silence
   producing memory-fragment utterances like "I am man not",
   "I am Guala", "I like patterns" without external input. This is
   the mental-time-travel signal — past speech coming back unprompted.

6. UI integration check: load dsf-ai.com/gualaloom.html in a browser
   (or load it via headless if no browser available) and verify:
   - Page still renders without JS errors
   - No 404s for substrate-related assets
   - If the UI has any wiring to a previous-version substrate path
     (look for imports, fetches, or hardcoded paths to src/gualaloom/dna/
     or src/gualaloom/engine), report the exact lines/files that
     reference older versions so we can decide whether to repoint or
     leave them.
   - Fix any UI issues you find (broken paths, console errors, layout
     breakage from the new v5b drop). Report what you fixed.

7. Commit with message:
   "Deploy GL substrate v5b — hippocampal layer, feedback, DMN, mental
    time travel

    GL-CODE-substrate-wC-20260608-001 (and accompanying test/demo/spec
    files 002-006). 172 populations, ~1,350 connections, 11/11 capability
    tests passing. Substrate supports episodic capture, replay, and
    consolidation via Default Mode Network. Feedback loop closes
    perception-action cycle."

8. Self-contained drop into src/gualaloom/dna/v5b/. No deletions of older
   versions, no edits to docs/ unless required to fix UI. If you need to
   edit anything outside src/gualaloom/dna/v5b/ or the UI HTML/JS,
   pause and ask Joe before doing it.

9. Report back:
   - Test result count
   - Exact silence chunks from daydream_output.txt
   - Exact conversation transcript from demo_output.txt
   - Any UI issues found and how you fixed them
   - Commit SHA
```

## What's NOT in this deploy (next pass)

- **Episode chains**: episodes currently fire in clusters during DMN, not
  as one-at-a-time associative chains. The same-tick WTA needed for clean
  chains requires an architectural change to the tick model (currently
  connections propagate next tick; lateral inhibition arrives too late
  to prevent multiple simultaneous firings).

- **Forward projection**: episodes capture instantaneous binding patterns,
  not time-extended sequences. Forward-projecting from a partial cue (true
  predictive simulation) would need sequence-encoded captures, probably
  via a chain of capture pops with delays.

Both are reachable from this substrate but would benefit from a wC↔c1
design pass on the tick model before implementation.
