"""
test_v7_awareness_real_path.py — functional tests for
GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711.

Background: _emit_from_invariants (dsf_ai_service/v4/gualaloom_v5_engine.py)
has long accepted a v7_session parameter and gated an "aware_active" prior-
boosting mechanism (_get_emission_priors / _build_context_priors) on
v7_session.aware_recently_fired() -- but self._v7_session is only ever
assigned by the isolated /v7/* endpoint handlers (substrate_runner.py:
_ensure_v7_link), never by the real conversation path (_converse_body /
_converse_phased). So in production, v7_session was always None at every
real call site and this gate was permanently dead.

This fix replaces that dependency with a real, grounded signal computed
directly against the organism's OWN state: self.sections["intro"] is a
real production section that already receives real per-word commits
during real read_sentence() (Section.receive(), ~line 1408) -- completely
independent of the isolated, simulated V7Session (substrate/v7_engine.py).
_introspection_active_this_turn() / _introspection_recent_words() read
that real, already-populated data directly. No new parallel process, no
synthetic session, v7_session itself no longer read anywhere in the gate.

These tests drive the REAL Guala() engine through its REAL public
entry points (read_sentence / converse / _emit_from_invariants) -- no
mocking of the mechanism under test itself, matching the established
convention in tests/test_emission_wall_budget_retime.py and
tests/test_read_sentence_lock_granularity_concurrency.py.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("EMISSION_MODE", "grandurun")

import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def test_real_conversation_populates_real_introspection_signal():
    """A real read_sentence() call must produce real entries in
    self.sections["intro"].commits (the organism's own real introspection
    history), and _introspection_active_this_turn()/_get_emission_priors()
    must reflect that real data -- with v7_session never passed/used."""
    print("Test: real conversation populates real introspection signal "
          "(no v7_session involved)...")
    g = Guala()
    assert not hasattr(g, "_v7_session"), (
        "fresh engine should never have _v7_session set -- it is only "
        "ever assigned by the isolated /v7/* endpoint handlers")

    assert g._introspection_active_this_turn() is False, (
        "before any real turn, _last_converse_tick is unset -- the gate "
        "must fail safe to False, not error or default True")
    assert g._get_emission_priors(None) == {}, (
        "cold start (no prior turn, no cache) must return empty priors")

    # Drive a REAL turn through the REAL public entry point.
    g._last_converse_tick = g.tick
    tick_before = g.tick
    g.read_sentence("the real chimneyword story about a chimneyword",
                     source="joe")
    tick_after = g.tick
    assert tick_after > tick_before, "read_sentence must advance real tick"

    intro_commits_this_turn = [
        c for c in g.sections["intro"].commits if c.get("tick", 0) > tick_before]
    assert intro_commits_this_turn, (
        "expected the organism's real 'intro' section to commit at least "
        "once for this sentence (Section.receive(), fam_listen > 0.3) -- "
        "if this fails the test fixture itself needs a richer sentence, "
        "not the gate under test")

    assert g._introspection_active_this_turn() is True, (
        "real intro commits happened after _last_converse_tick but the "
        "gate did not detect them")

    recent = g._introspection_recent_words()
    real_words = {c["word"].lower() for c in intro_commits_this_turn if c.get("word")}
    assert recent, "recent introspection words must be non-empty"
    assert recent & real_words, (
        f"_introspection_recent_words() {recent} shares nothing with the "
        f"words that actually committed to intro this turn {real_words} -- "
        "signal is not grounded in real data")

    priors = g._get_emission_priors(None)  # v7_session=None: never touched
    assert priors, "aware_active=True must produce non-empty real priors"
    for w in priors:
        assert w in real_words or w in recent, (
            f"prior key {w!r} is not traceable to any real intro commit "
            "-- would be fabricated content")
        assert priors[w] == g.INTRO_RECENCY_BOOST, (
            f"prior weight for {w!r} should be exactly INTRO_RECENCY_BOOST "
            f"on first fire, got {priors[w]}")
    print(f"  OK: real intro commits {sorted(real_words)}, "
          f"real priors {priors}")


def test_v7_session_argument_is_never_read_for_the_gate():
    """Passing a real, non-None (but otherwise unused) object as
    v7_session must not change aware_active or the priors at all --
    proves the gate is 100% computed from self's own state."""
    print("Test: v7_session argument no longer influences the gate...")
    g = Guala()
    g._last_converse_tick = g.tick
    g.read_sentence("the real chimneyword story about a chimneyword",
                     source="joe")

    priors_without = g._get_emission_priors(None)
    priors_with_junk = g._get_emission_priors(object())  # not a V7Session at all
    assert priors_without == priors_with_junk, (
        "priors changed depending on the v7_session argument -- the gate "
        "must be computed purely from self's own real state")
    print("  OK: identical priors regardless of v7_session argument")


def test_cold_start_before_any_conversation_returns_empty_priors():
    print("Test: brand-new engine (never converse()'d) is cold, not "
          "vacuously 'aware'...")
    g = Guala()
    assert g._introspection_active_this_turn() is False
    assert g._get_emission_priors(None) == {}
    print("  OK")


def test_aware_blocked_attenuates_cached_priors_not_live_v7_data():
    """After a real 'aware' turn produces + caches priors, a later point
    in time where intro has NOT committed anything new must attenuate the
    cached priors (0.5x) rather than returning fresh ones or crashing."""
    print("Test: aware-blocked turn attenuates cached real priors...")
    g = Guala()
    g._last_converse_tick = g.tick
    g.read_sentence("the real chimneyword story about a chimneyword",
                     source="joe")
    assert g._introspection_active_this_turn() is True
    fresh_priors = g._get_emission_priors(None)
    assert fresh_priors

    # Advance the turn boundary to now, WITHOUT any new intro commit --
    # i.e. simulate "no introspection happened since the last turn began".
    g._last_converse_tick = g.tick
    assert g._introspection_active_this_turn() is False, (
        "moving the turn boundary past the last real intro commit should "
        "deactivate the gate")

    attenuated = g._get_emission_priors(None)
    assert attenuated, "should fall back to attenuated cache, not empty"
    for w, v in fresh_priors.items():
        expected = 1.0 + (v - 1.0) * g.AWARE_BLOCKED_ATTENUATION
        assert abs(attenuated[w] - expected) < 1e-9, (
            f"{w!r}: expected attenuated {expected}, got {attenuated[w]}")
    print(f"  OK: fresh={fresh_priors} -> attenuated={attenuated}")


def _chi_for(word):
    from dsf_ai_service.v4.gualaloom_v5_engine import LanguageKrimelack
    k = LanguageKrimelack()
    k.transduce(word)
    return k.winding


def test_live_emission_dynamics_path_applies_real_aware_bias():
    """The LIVE production emission path (EMISSION_DYNAMICS=1) must now
    genuinely apply the real introspection-derived bias to candidates --
    not just the non-default scalar _emit_grandurun path. Same Stage-1
    stubbing convention as test_emission_wall_budget_retime.py: only
    candidate SOURCING is stubbed; the real Stage-2 settling loop and the
    real bias-application code under test run unmodified."""
    print("Test: live _emit_dynamics path applies real aware-derived bias "
          "to candidates (shapes what actually gets said)...")
    old_env = {k: os.environ.get(k) for k in
               ("EMISSION_MODE", "EMISSION_DYNAMICS", "EMISSION_DYNAMICS_TICKS")}
    os.environ["EMISSION_MODE"] = "grandurun"
    os.environ["EMISSION_DYNAMICS"] = "1"
    os.environ["EMISSION_DYNAMICS_TICKS"] = "20"
    orig_select = engine_mod._grandurun_select_candidates
    try:
        g = Guala()
        g._brain_emission_candidates = lambda input_words: [({}, {}, 1.0)]

        # Real turn: genuine intro commits via real read_sentence.
        g._last_converse_tick = g.tick
        g.read_sentence("the real chimneyword story about a chimneyword",
                         source="joe")
        assert g._introspection_active_this_turn() is True
        aware_word = next(iter(g._introspection_recent_words()))

        # Stage 1 stub: a weak candidate that MATCHES the real aware
        # signal vs. a strong candidate that does not -- if the aware
        # bias genuinely applies, the weak-but-aware candidate should win.
        def stub_stage1(*_a, **_kw):
            return [
                {"chi": _chi_for(aware_word), "section": "subject",
                 "motif": f"subject:{aware_word}", "word": aware_word,
                 "strength": 0.2, "coherent_magnitude": 0.2, "source": "corpus",
                 "arousal": 0.5, "valence": 0.3, "polarity": 1.0,
                 "sensory_refs": [], "origin": "grandurun"},
                {"chi": _chi_for("unrelatedword"), "section": "verb",
                 "motif": "verb:unrelatedword", "word": "unrelatedword",
                 "strength": 0.9, "coherent_magnitude": 0.9, "source": "corpus",
                 "arousal": 0.5, "valence": 0.3, "polarity": 1.0,
                 "sensory_refs": [], "origin": "grandurun"},
            ]
        engine_mod._grandurun_select_candidates = stub_stage1

        reply = g._emit_from_invariants([], [], mode_override="grandurun")

        ev = {}
        for evt in g._substrate_events:
            if getattr(evt, "kind", None) == "emission_dynamics":
                ev = evt.detail
        assert ev.get("aware_priors_applied") is True, (
            "emission_dynamics event did not report aware_priors_applied "
            f"-- got event={ev}")
        assert ev.get("n_aware_priors", 0) > 0

        print(f"  reply={reply!r} aware_word={aware_word!r} "
              f"n_aware_priors={ev.get('n_aware_priors')}")
        assert reply is not None and aware_word in reply.split(), (
            f"expected the aware-boosted low-magnitude candidate "
            f"{aware_word!r} to win over the higher-magnitude "
            f"'unrelatedword' candidate -- bias did not shape the reply "
            f"(reply={reply!r})")
        print("  OK: real introspection signal genuinely shaped the live "
              "emission path's output")
    finally:
        engine_mod._grandurun_select_candidates = orig_select
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


if __name__ == "__main__":
    tests = [
        test_real_conversation_populates_real_introspection_signal,
        test_v7_session_argument_is_never_read_for_the_gate,
        test_cold_start_before_any_conversation_returns_empty_priors,
        test_aware_blocked_attenuates_cached_priors_not_live_v7_data,
        test_live_emission_dynamics_path_applies_real_aware_bias,
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
