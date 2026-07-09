"""
GL-CMD-EMISSION-SHADOW-EVE-20260709: unit tests for
_brain_emission_candidates' extended RECALL_BACKEND=shadow dispatch
(design only -- this dispatch is NOT enabled by default and NOT
deployed; see the accompanying report for what real data would still
need to be gathered before any cutover).

Mirrors dsf_ai_service/loom_model/tests/test_brain_dual_path.py's own
style for recall_fast's three-way dispatch: stub-based dispatcher tests
(fast, deterministic, exercise the real dispatch code) plus one
integration-level test against a real Guala() boot proving the single
most important property -- shadow mode returns EXACTLY what legacy mode
returns and never mutates neuron state, i.e. zero production impact
when RECALL_BACKEND=shadow vs RECALL_BACKEND=legacy (default).
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    """Same convention as test_debug_stdp_state.py's helper."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


# ─────────────────────────────────────────────────────────────────────
# Dispatcher-level tests (stubbed backends, mirrors test_brain_dual_path.py)
# ─────────────────────────────────────────────────────────────────────

def test_default_backend_calls_legacy_only():
    os.environ.pop("RECALL_BACKEND", None)
    g = _fresh_guala()
    try:
        calls = {"legacy": 0, "membrane": 0}
        g._brain_emission_candidates_legacy = lambda w: (calls.__setitem__("legacy", calls["legacy"] + 1) or [("LEGACY", {}, 1.0)])
        g._brain_emission_candidates_membrane = lambda w: (calls.__setitem__("membrane", calls["membrane"] + 1) or [(0, 1.0, "MEMBRANE")])
        result = g._brain_emission_candidates(["dog"])
        assert calls == {"legacy": 1, "membrane": 0}
        assert result == [("LEGACY", {}, 1.0)]
        print("test_default_backend_calls_legacy_only: PASS")
    finally:
        g.shutdown()


def test_stdp_backend_calls_membrane_only():
    """Regression guard: the pre-existing RECALL_BACKEND=stdp branch
    (item 8, before this extension) must be completely unchanged."""
    os.environ["RECALL_BACKEND"] = "stdp"
    g = _fresh_guala()
    try:
        calls = {"legacy": 0, "membrane": 0}
        g._brain_emission_candidates_legacy = lambda w: (calls.__setitem__("legacy", calls["legacy"] + 1) or [("LEGACY", {}, 1.0)])
        g._brain_emission_candidates_membrane = lambda w: (calls.__setitem__("membrane", calls["membrane"] + 1) or [(0, 1.0, "MEMBRANE")])
        result = g._brain_emission_candidates(["dog"])
        assert calls == {"legacy": 0, "membrane": 1}
        assert result == [(0, 1.0, "MEMBRANE")]
        print("test_stdp_backend_calls_membrane_only: PASS")
    finally:
        os.environ.pop("RECALL_BACKEND", None)
        g.shutdown()


def test_shadow_backend_runs_both_returns_legacy_exactly():
    os.environ["RECALL_BACKEND"] = "shadow"
    g = _fresh_guala()
    try:
        calls = {"legacy": 0, "membrane": 0, "log": 0}
        g._brain_emission_candidates_legacy = lambda w: (calls.__setitem__("legacy", calls["legacy"] + 1) or [("LEGACY", {}, 1.0)])
        g._brain_emission_candidates_membrane = lambda w: (calls.__setitem__("membrane", calls["membrane"] + 1) or [(0, 1.0, "MEMBRANE")])
        g._log_emission_shadow_comparison = lambda l, m, w: calls.__setitem__("log", calls["log"] + 1)
        result = g._brain_emission_candidates(["dog"])
        assert calls == {"legacy": 1, "membrane": 1, "log": 1}
        assert result == [("LEGACY", {}, 1.0)], "shadow mode must return the LEGACY result unchanged"
        print("test_shadow_backend_runs_both_returns_legacy_exactly: PASS")
    finally:
        os.environ.pop("RECALL_BACKEND", None)
        g.shutdown()


def test_shadow_membrane_exception_non_fatal_returns_legacy():
    os.environ["RECALL_BACKEND"] = "shadow"
    g = _fresh_guala()
    try:
        g._brain_emission_candidates_legacy = lambda w: [("LEGACY", {}, 1.0)]
        def _boom(w):
            raise RuntimeError("membrane broke")
        g._brain_emission_candidates_membrane = _boom
        result = g._brain_emission_candidates(["dog"])
        assert result == [("LEGACY", {}, 1.0)]
        print("test_shadow_membrane_exception_non_fatal_returns_legacy: PASS")
    finally:
        os.environ.pop("RECALL_BACKEND", None)
        g.shutdown()


def test_shadow_log_exception_non_fatal_returns_legacy():
    """The comparison LOGGING itself failing must also not touch the
    returned value -- same non-fatal contract, one level deeper."""
    os.environ["RECALL_BACKEND"] = "shadow"
    g = _fresh_guala()
    try:
        g._brain_emission_candidates_legacy = lambda w: [("LEGACY", {}, 1.0)]
        g._brain_emission_candidates_membrane = lambda w: [(0, 1.0, "MEMBRANE")]
        def _boom(l, m, w):
            raise RuntimeError("log broke")
        g._log_emission_shadow_comparison = _boom
        result = g._brain_emission_candidates(["dog"])
        assert result == [("LEGACY", {}, 1.0)]
        print("test_shadow_log_exception_non_fatal_returns_legacy: PASS")
    finally:
        os.environ.pop("RECALL_BACKEND", None)
        g.shutdown()


# ─────────────────────────────────────────────────────────────────────
# Comparison-metric unit tests (_emission_legacy_top_words /
# _emission_membrane_top_words / _log_emission_shadow_comparison)
# ─────────────────────────────────────────────────────────────────────

def test_legacy_top_words_resolves_real_section_mode():
    """Exercises the REAL section/mode resolution against a real
    (hand-seeded) Section object -- not mocked -- so this proves the
    resolution logic itself, not just that a mock was called."""
    g = _fresh_guala()
    try:
        sec = g.sections["subject"]
        sec.modes.append((None, None, "dog"))
        mode_idx = len(sec.modes) - 1
        co = {"subject": {str(mode_idx): 0.8}}
        de = {"co_occurrence": co, "clarity": 0.8, "origin": "brain"}
        candidates = [(de, co, 0.8)]
        top = g._emission_legacy_top_words(candidates, k=5)
        assert top == [("dog", 0.8)], top
        print("test_legacy_top_words_resolves_real_section_mode: PASS")
    finally:
        g.shutdown()


def test_membrane_top_words_grounded_filter():
    g = _fresh_guala()
    try:
        sec = g.sections["subject"]
        sec.modes.append((None, None, "dog"))
        g._word_to_emission_sections["dog"] = [("subject", len(sec.modes) - 1, "dog")]
        candidates = [(1, 0.9, "dog"), (2, 0.7, "zzznever")]
        raw = g._emission_membrane_top_words(candidates, k=5, grounded_only=False)
        grounded = g._emission_membrane_top_words(candidates, k=5, grounded_only=True)
        assert raw == [("dog", 0.9), ("zzznever", 0.7)], raw
        assert grounded == [("dog", 0.9)], grounded
        print("test_membrane_top_words_grounded_filter: PASS")
    finally:
        g.shutdown()


def test_top1_agree_both_empty_is_agreement():
    g = _fresh_guala()
    try:
        logged = {}
        orig = g._log_substrate_event
        def _capture(kind, **detail):
            if kind == "emission_shadow":
                logged.update(detail)
            return orig(kind, **detail)
        g._log_substrate_event = _capture
        g._log_emission_shadow_comparison([], [], ["dog"])
        assert logged["top1_agree"] is True
        assert logged["top5_jaccard"] == 1.0
        print("test_top1_agree_both_empty_is_agreement: PASS")
    finally:
        g.shutdown()


def test_top1_agree_one_sided_empty_is_disagreement():
    """One backend would speak, the other stays silent -- must count as
    disagreement, not be silently skipped, per the halt condition's
    own intent."""
    g = _fresh_guala()
    try:
        sec = g.sections["subject"]
        sec.modes.append((None, None, "dog"))
        mode_idx = len(sec.modes) - 1
        co = {"subject": {str(mode_idx): 0.8}}
        de = {"co_occurrence": co, "clarity": 0.8, "origin": "brain"}
        legacy_candidates = [(de, co, 0.8)]

        logged = {}
        orig = g._log_substrate_event
        def _capture(kind, **detail):
            if kind == "emission_shadow":
                logged.update(detail)
            return orig(kind, **detail)
        g._log_substrate_event = _capture

        g._log_emission_shadow_comparison(legacy_candidates, [], ["dog"])
        assert logged["top1_agree"] is False, logged
        print("test_top1_agree_one_sided_empty_is_disagreement: PASS")
    finally:
        g.shutdown()


def test_top1_agree_matching_words():
    g = _fresh_guala()
    try:
        sec = g.sections["subject"]
        sec.modes.append((None, None, "dog"))
        mode_idx = len(sec.modes) - 1
        g._word_to_emission_sections["dog"] = [("subject", mode_idx, "dog")]
        co = {"subject": {str(mode_idx): 0.8}}
        de = {"co_occurrence": co, "clarity": 0.8, "origin": "brain"}
        legacy_candidates = [(de, co, 0.8)]
        membrane_candidates = [(0, 1.2, "dog")]

        logged = {}
        orig = g._log_substrate_event
        def _capture(kind, **detail):
            if kind == "emission_shadow":
                logged.update(detail)
            return orig(kind, **detail)
        g._log_substrate_event = _capture

        g._log_emission_shadow_comparison(legacy_candidates, membrane_candidates, ["dog"])
        assert logged["top1_agree"] is True, logged
        assert logged["top5_jaccard"] == 1.0, logged
        print("test_top1_agree_matching_words: PASS")
    finally:
        g.shutdown()


# ─────────────────────────────────────────────────────────────────────
# Integration-level test: real Guala(), proves zero production impact
# ─────────────────────────────────────────────────────────────────────

def test_shadow_vs_legacy_bit_for_bit_identical_and_non_mutating():
    """THE critical property: on the SAME real Guala instance and SAME
    (deterministic, stubbed-legacy) candidate content, RECALL_BACKEND
    ="legacy" and RECALL_BACKEND="shadow" must return an IDENTICAL
    value, and running the real (unstubbed) membrane path alongside it
    must not perturb any neuron's membrane_potential -- shadow mode
    reads membrane state, it must never write it."""
    g = _fresh_guala(event_driven=True)
    try:
        sec = g.sections["subject"]
        sec.modes.append((None, None, "dog"))
        mode_idx = len(sec.modes) - 1
        co = {"subject": {str(mode_idx): 0.8}}
        de = {"co_occurrence": co, "clarity": 0.8, "origin": "brain"}
        fixed_legacy_result = [(de, co, 0.8)]
        g._brain_emission_candidates_legacy = lambda w: fixed_legacy_result
        # _brain_emission_candidates_membrane is left as the REAL
        # implementation (unstubbed) -- this is the real production
        # code actually running during the shadow call below.

        potentials_before = [n.membrane_potential for n in g._all_neurons()]

        os.environ.pop("RECALL_BACKEND", None)
        result_legacy = g._brain_emission_candidates(["hello"])

        os.environ["RECALL_BACKEND"] = "shadow"
        n_events_before = len(g._substrate_events)
        result_shadow = g._brain_emission_candidates(["hello"])
        n_events_after = len(g._substrate_events)

        potentials_after = [n.membrane_potential for n in g._all_neurons()]

        assert result_legacy == result_shadow == fixed_legacy_result, \
            (result_legacy, result_shadow)
        assert potentials_before == potentials_after, \
            "membrane state must be unperturbed by shadow's read-only membrane pass"
        assert any(e.kind == "emission_shadow" for e in g._substrate_events), \
            "shadow mode must have logged a comparison event"
        assert n_events_after > n_events_before
        print("test_shadow_vs_legacy_bit_for_bit_identical_and_non_mutating: PASS")
    finally:
        os.environ.pop("RECALL_BACKEND", None)
        g.shutdown()


def test_legacy_mode_never_invokes_shadow_comparison():
    """Converse: with RECALL_BACKEND unset/legacy (production default),
    no "emission_shadow" event should EVER be logged -- proves legacy
    callers take the old code path with zero new machinery involved,
    not just that the return value happens to match."""
    os.environ.pop("RECALL_BACKEND", None)
    g = _fresh_guala()
    try:
        g._brain_emission_candidates_legacy = lambda w: []
        g._brain_emission_candidates(["hello"])
        assert not any(e.kind == "emission_shadow" for e in g._substrate_events)
        print("test_legacy_mode_never_invokes_shadow_comparison: PASS")
    finally:
        g.shutdown()


if __name__ == "__main__":
    test_default_backend_calls_legacy_only()
    test_stdp_backend_calls_membrane_only()
    test_shadow_backend_runs_both_returns_legacy_exactly()
    test_shadow_membrane_exception_non_fatal_returns_legacy()
    test_shadow_log_exception_non_fatal_returns_legacy()
    test_legacy_top_words_resolves_real_section_mode()
    test_membrane_top_words_grounded_filter()
    test_top1_agree_both_empty_is_agreement()
    test_top1_agree_one_sided_empty_is_disagreement()
    test_top1_agree_matching_words()
    test_shadow_vs_legacy_bit_for_bit_identical_and_non_mutating()
    test_legacy_mode_never_invokes_shadow_comparison()
    print("ALL PASS: test_emission_shadow")
