"""
test_read_sentence_lock_granularity.py — local functional tests for
GL-FIX-LOCK-GRANULARITY-C1-20260710.

Companion to test_read_sentence_lock_granularity_concurrency.py (the real-
threading adversarial tests). This file verifies, against the REAL Guala
engine (dsf_ai_service/v4/gualaloom_v5_engine.py), single-threaded/no-
contention functional correctness of the refactor that made
self._current_episode and self._prev_phase_vec call-local to
read_sentence()'s per-word loop instead of shared instance attributes --
the change that made it safe to stop holding self.lock for an entire
sentence (read_word() already wraps its own body in `with self.lock:`;
read_sentence() no longer additionally wraps its whole per-word loop).

Covered here:
  1. Episode tagging: every word of one sentence gets the SAME episode_ref,
     a real non-degenerate id (not a placeholder), and it differs between
     separate sentences.
  2. A caller-supplied read_sentence(episode_ref=...) override still wins
     for every word, same precedence as before the refactor.
  3. The modal/sensory window_manager.add_entry() call site (a SECOND,
     separate _grounding_kwargs() call site inside read_word that used to
     read self._current_episode directly, bypassing the episode_ref
     parameter entirely) gets the SAME resolved episode_ref as the primary
     section commits -- this was a real latent regression the refactor
     would otherwise have introduced (self._current_episode is no longer
     written by anything, so this call site would have silently gone to
     None forever) and had to be fixed by threading the resolved value
     through explicitly; this test would fail without that fix.
  4. Phase-vector rotation/negation (60-L): the actual rotation/polarity
     values read_sentence's per-word loop produces for a real sentence are
     compared against an INDEPENDENT shadow computation using the same
     underlying primitives (LanguageKrimelack + event_stream_to_vector),
     run fresh in this test file, replicating the documented algorithm
     (first word has no predecessor; a word whose transduction doesn't
     yield a phase vector leaves the last known-good one in place for the
     next comparison). Proves the call-local chaining computes the exact
     same numbers as before, not just that it's internally consistent.
  5. Sentence boundaries: the first word of a NEW sentence never inherits
     rotation state left over from a previous sentence (or from any other
     direct read_word() caller) -- always starts at rotation=0.0.
"""

import os
import re
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack  # noqa: E402
from dsf_ai_service.substrate.krimelack import event_stream_to_vector  # noqa: E402

_EP_ID_RE = re.compile(r"^episode:[^:]+:[1-9][0-9]*$")


def _spy_on_atlas_record(g):
    """Replace g.atlas.record with a recording wrapper that still performs
    the real write. Returns the list of (args, kwargs) tuples captured, in
    call order."""
    calls = []
    orig = g.atlas.record

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return orig(*args, **kwargs)

    g.atlas.record = _spy
    return calls


def _listen_calls(calls):
    """Filter atlas.record calls to the 'listen' section -- every real
    word commits there unconditionally (read_word calls it first, before
    any role-routed primary section), so this yields exactly one entry per
    word, in word order."""
    return [(args, kwargs) for args, kwargs in calls if args and args[0] == "listen"]


def _modal_calls(calls):
    return [(args, kwargs) for args, kwargs in calls
            if args and isinstance(args[0], str) and args[0].startswith("modal_")]


def test_episode_ref_consistent_across_multiword_sentence():
    print("Test 1: every word of one sentence gets the same real episode_ref...")
    g = Guala()
    calls = _spy_on_atlas_record(g)
    g.read_sentence("the cat sat down quietly", source="joe")

    listen = _listen_calls(calls)
    assert len(listen) >= 5, f"expected >=5 word commits, got {len(listen)}"
    ep_refs = [kw.get("episode_ref") for _, kw in listen]
    assert all(e is not None for e in ep_refs), f"some words got no episode_ref: {ep_refs}"
    assert len(set(ep_refs)) == 1, (
        f"REGRESSION: words in the same sentence got different episode_ref "
        f"values -- episode tagging is no longer sentence-consistent: {ep_refs}")
    assert _EP_ID_RE.match(ep_refs[0]), (
        f"episode_ref {ep_refs[0]!r} doesn't look like a real generated id "
        "(episode:<source>:<persisted source turn>) -- looks like a "
        "placeholder/stub value")
    print(f"  OK: all {len(ep_refs)} words share episode_ref={ep_refs[0]!r}")


def test_episode_ref_differs_across_separate_sentences():
    print("Test 2: separate sentences get distinct real episode ids...")
    g = Guala()
    calls = _spy_on_atlas_record(g)
    g.read_sentence("first sentence right here", source="joe")
    n_after_first = len(_listen_calls(calls))
    g.read_sentence("second entirely different sentence", source="joe")

    listen = _listen_calls(calls)
    first_refs = {kw.get("episode_ref") for _, kw in listen[:n_after_first]}
    second_refs = {kw.get("episode_ref") for _, kw in listen[n_after_first:]}
    assert len(first_refs) == 1 and len(second_refs) == 1
    assert first_refs != second_refs, (
        "REGRESSION: two separate read_sentence() calls produced the SAME "
        f"episode_ref ({first_refs}) -- looks stuck/cached, not fresh per "
        "sentence")
    print(f"  OK: sentence 1 -> {first_refs}, sentence 2 -> {second_refs}")


def test_episode_ref_caller_override_still_wins():
    print("Test 3: caller-supplied read_sentence(episode_ref=...) still "
          "overrides the auto-generated id for every word...")
    g = Guala()
    calls = _spy_on_atlas_record(g)
    g.read_sentence("hello there world", source="joe", episode_ref="forced-ep-123")

    listen = _listen_calls(calls)
    assert len(listen) >= 3
    ep_refs = {kw.get("episode_ref") for _, kw in listen}
    assert ep_refs == {"forced-ep-123"}, (
        f"caller override was not honored for every word: {ep_refs}")
    print("  OK: forced episode_ref applied to every word")


def test_modal_grounding_kwargs_gets_same_episode_ref_as_primary_commits():
    """The regression this dispatch's refactor could easily have
    introduced: _grounding_kwargs() has TWO call sites inside read_word --
    the primary one (feeds atlas_kwargs for Section.receive) and a second,
    separate one for modal/sensory window_manager.add_entry() calls. Before
    this fix both read self._current_episode directly; only the primary
    site threaded the episode_ref param through (via the old override
    block). Once read_sentence() stopped writing self._current_episode
    entirely (the whole point of the fix), the second call site would have
    silently gone to episode_ref=None forever unless it was ALSO updated to
    receive the resolved value explicitly. "fire" has sight/touch/sound/
    smell entries in SENSORY_DNA, guaranteeing this path actually fires."""
    print("Test 4: modal/sensory window entries get the same episode_ref "
          "as the word's own primary section commits...")
    g = Guala()
    calls = _spy_on_atlas_record(g)
    g.read_sentence("i saw the fire", source="joe")

    modal = _modal_calls(calls)
    assert modal, (
        "test didn't actually exercise the modal path -- inconclusive. "
        "'fire' should trigger sight/touch/sound/smell in SENSORY_DNA.")
    modal_refs = {kw.get("episode_ref") for _, kw in modal}
    assert None not in modal_refs, (
        f"REGRESSION: modal/sensory window entries got episode_ref=None -- "
        f"the second _grounding_kwargs() call site inside read_word is not "
        f"receiving the resolved per-sentence episode_ref: {modal_refs}")

    listen = _listen_calls(calls)
    primary_refs = {kw.get("episode_ref") for _, kw in listen}
    assert len(primary_refs) == 1
    assert modal_refs == primary_refs, (
        f"modal entries' episode_ref {modal_refs} does not match the "
        f"sentence's primary commits' episode_ref {primary_refs}")
    print(f"  OK: {len(modal)} modal entries all share the sentence's real "
          f"episode_ref {primary_refs}")


def _shadow_rotations(words):
    """Independent reference implementation of 60-L rotation, using the
    same production primitives (LanguageKrimelack.transduce +
    event_stream_to_vector) but a fresh krimelack and a plain local
    variable for 'previous phase vector' -- i.e. exactly the algorithm
    read_word's docstring describes, computed completely independently of
    read_sentence()/read_word()'s own internals. transduce() resets its
    winding state on every call (no_reset defaults to False, same as
    read_word's own self.language.transduce(word) call), so this is
    deterministic and process-order-independent."""
    krim = LanguageKrimelack()
    prev = None
    rotations = []
    for w in words:
        krim.transduce(w)
        try:
            pv = event_stream_to_vector(krim.events, dim=16)
        except Exception:
            pv = None
        rot = 0.0
        if pv is not None and prev is not None:
            inner = np.vdot(prev, pv)
            rot = float(abs(np.angle(inner)))
        rotations.append(round(rot, 4))
        if pv is not None:
            prev = pv
    return rotations


def test_phase_vector_rotation_matches_independent_shadow_computation():
    print("Test 5: read_sentence()'s actual rotation values match an "
          "independent shadow computation of the same 60-L algorithm...")
    g = Guala()
    calls = _spy_on_atlas_record(g)
    words = ["the", "cat", "did", "not", "sit", "down", "quietly", "today"]
    g.read_sentence(" ".join(words), source="joe")

    listen = _listen_calls(calls)
    assert len(listen) == len(words), (
        f"expected exactly one 'listen' commit per word, got "
        f"{len(listen)} for {len(words)} words")
    actual_rotations = [kw.get("rotation") for _, kw in listen]
    expected_rotations = _shadow_rotations(words)

    assert len(actual_rotations) == len(expected_rotations)
    for i, (a, e) in enumerate(zip(actual_rotations, expected_rotations)):
        assert a is not None and abs(a - e) < 1e-6, (
            f"word[{i}]={words[i]!r}: actual rotation {a} != shadow-"
            f"computed rotation {e} -- the call-local prev_phase_vec "
            f"chaining diverged from the documented 60-L algorithm")

    # First word of any sentence has no predecessor.
    assert actual_rotations[0] == 0.0

    # Cross-check polarity too (derived purely from rotation).
    actual_polarity = [kw.get("polarity") for _, kw in listen]
    expected_polarity = [(-1 if r > (math.pi / 2) else 1) for r in expected_rotations]
    assert actual_polarity == expected_polarity, (
        f"polarity mismatch: actual={actual_polarity} "
        f"expected={expected_polarity}")
    print(f"  OK: {len(words)} words' rotation+polarity match the "
          f"independent shadow computation exactly")


def test_sentence_boundary_never_inherits_rotation_from_a_prior_sentence():
    """The refactor's core guarantee: read_sentence()'s local
    _prev_phase_vec_local always starts at None, unconditionally, at the
    start of ITS OWN loop -- never carried over from whatever
    self._prev_phase_vec (now used only by legacy direct read_word()
    callers, e.g. self_hear) happens to hold. Confirmed by running several
    sentences back-to-back and checking every single one's first word has
    rotation exactly 0.0."""
    print("Test 6: a sentence's first word never inherits rotation state "
          "from a previous sentence...")
    g = Guala()
    calls = _spy_on_atlas_record(g)
    sentences = [
        "alpha bravo charlie delta",
        "echo foxtrot golf hotel",
        "india juliet kilo lima",
    ]
    boundaries = []
    for s in sentences:
        boundaries.append(len(_listen_calls(calls)))
        g.read_sentence(s, source="joe")

    listen = _listen_calls(calls)
    for idx, start in enumerate(boundaries):
        first_word_rotation = listen[start][1].get("rotation")
        assert first_word_rotation == 0.0, (
            f"sentence {idx} ({sentences[idx]!r}) first word rotation "
            f"was {first_word_rotation}, expected 0.0 (no predecessor)")
    print(f"  OK: all {len(sentences)} sentences' first words started at "
          f"rotation=0.0")


def test_read_word_return_value_shape_unchanged_for_direct_callers():
    """Direct callers (self_hear, background corpus reading, test probes)
    call read_word() and ignore its return value entirely (grep-verified
    against the whole repo) -- confirm it's still a valid tuple whose first
    three elements are unchanged (lang_chi, role, senses) so nothing that
    might destructure a subset positionally breaks, and the two new
    trailing elements (phase_vec, profile dict) are present and sane."""
    print("Test 7: read_word()'s return value shape is backward compatible...")
    g = Guala()
    result = g.read_word("hello", source="corpus")
    assert isinstance(result, tuple) and len(result) == 5
    lang_chi, role, senses, phase_vec, prof = result
    assert isinstance(lang_chi, int)
    assert isinstance(senses, list)
    assert phase_vec is None or hasattr(phase_vec, "shape")
    assert isinstance(prof, dict)
    print("  OK: (lang_chi, role, senses, phase_vec, prof)")


if __name__ == "__main__":
    tests = [
        test_episode_ref_consistent_across_multiword_sentence,
        test_episode_ref_differs_across_separate_sentences,
        test_episode_ref_caller_override_still_wins,
        test_modal_grounding_kwargs_gets_same_episode_ref_as_primary_commits,
        test_phase_vector_rotation_matches_independent_shadow_computation,
        test_sentence_boundary_never_inherits_rotation_from_a_prior_sentence,
        test_read_word_return_value_shape_unchanged_for_direct_callers,
    ]
    failures = []
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append((t.__name__, str(e)))

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)}")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print(f"ALL {len(tests)} TESTS PASSED")
