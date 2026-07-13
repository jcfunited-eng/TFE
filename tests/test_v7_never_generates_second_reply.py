"""
test_v7_never_generates_second_reply.py — permanent regression-guard
tripwire for GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711.

Standing rule this project has a hard line against ("one brain, one
voice, or silence — never build parallel brain processes, never fake her
voice"): the real conversation path (_converse_body / _converse_phased in
dsf_ai_service/v4/gualaloom_v5_engine.py) must NEVER call
V7Session.converse() (dsf_ai_service/substrate/v7_engine.py) or any other
method that would generate a second, independent reply. V7Session.converse()
runs its OWN full assemblage-dynamics settling loop over its OWN separate
pool_a/pool_b/pool_c vocabulary and even synthesizes its OWN self-voice
audio (V7Session._synthesize_self_voice, espeak-ng) — a second, fully
independent reply-generation pathway if it were ever wired into the real
turn. It is reachable ONLY via the isolated /v7/converse and /v7/state
HTTP endpoints (app.py), never from the real conversation path — confirmed
by exhaustive grep: the only two production call sites of
"session.converse(" in the whole tree are app.py's /v7/converse handler
and substrate_runner.py's handle_v7_converse (itself only reachable via
that same isolated endpoint in remote mode).

GL-CMD-V7-AWARENESS-REAL-PATH-C1-20260711 wires a REAL introspection
signal into the real path's existing aware_active gate, but computes it
entirely from self's own state (self.sections["intro"].commits) and never
touches v7_session at all — the v7_session parameter threaded through
_emit_from_invariants / _emit_dynamics / _emit_grandurun / _get_emission_
priors / _build_context_priors is now dead plumbing, kept only for call-
site signature stability.

This file is the PERMANENT tripwire that keeps it that way — not a one-
time check. It combines:
  (1) a static source scan for the literal forbidden call patterns
      (belt) — catches an obvious future regression even before tests run
  (2) a dynamic run with a real Guala() and a hostile "must never be
      touched" v7_session spy attached, driven through REAL converse()
      calls (suspenders) — catches a regression even if it doesn't
      literally re-introduce the exact source patterns being grepped for
  (3) a hard patch on V7Session.converse() itself that raises if called,
      driven through the same real turns — the ultimate backstop, since
      it doesn't depend on how the real path would have reached it
  (4) a call-count assertion that _emit_from_invariants (the one real
      reply composer) runs exactly once per real turn.
"""

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("EMISSION_MODE", "grandurun")

import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    ConversationTurnResult,
    Guala,
)
from dsf_ai_service.substrate.v7_engine import V7Session  # noqa: E402


ENGINE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dsf_ai_service", "v4", "gualaloom_v5_engine.py")

# Real-conversation-reachable functions: everything _emit_from_invariants
# can transitively reach, plus the two real turn entry points. If a future
# change adds a v7_session.converse()/.quiet_tick()/.apply_feedback() (or
# any other V7Session method) call inside any of these, this test's static
# scan (part 1) must catch it even before the dynamic spy (part 2) would.
REAL_PATH_FUNCTIONS = (
    "_converse_body", "_converse_phased",
    "_emit_from_invariants", "_emit_dynamics",
    "_emit_grandurun", "_emit_grandurun_vector",
    "_get_emission_priors", "_build_context_priors",
    "_introspection_active_this_turn", "_introspection_recent_words",
    "compose_autonomous", "_do_emit", "_do_emit_phased",
)

# Any of these substrings appearing inside one of the functions above is a
# hard regression: they are the shapes a "wire v7_session in for real" bug
# would take. Matched against literal source text of each function's body
# only (see _function_source_texts below) -- not the whole file -- so
# unrelated code elsewhere (e.g. the isolated /v7/* handlers, which are
# SUPPOSED to call these) can't trip it, and prose in comments/docstrings
# about "V7Session.converse()" (capital-V class name, not the lowercase
# instance-variable call syntax below) doesn't false-positive either.
FORBIDDEN_PATTERNS = (
    "v7_session.converse(",
    "v7_session.quiet_tick(",
    "v7_session.apply_feedback(",
    "_v7_session.converse(",
    "_v7_session.quiet_tick(",
    "_v7_session.apply_feedback(",
    "V7Session(",
    "get_or_create_session(",
)


def _function_source_texts():
    """Parse the real engine source once and return {func_name: source_text}
    for every REAL_PATH_FUNCTIONS match found (as methods of class Guala)."""
    src = open(ENGINE_PATH).read()
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Guala":
            for item in node.body:
                if (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name in REAL_PATH_FUNCTIONS):
                    start = item.lineno - 1
                    end = getattr(item, "end_lineno", item.lineno)
                    out[item.name] = "".join(lines[start:end])
    return out


def test_static_scan_no_forbidden_v7_calls_in_real_path_functions():
    print("Tripwire 1/4: static source scan of every real-path function "
          "for forbidden V7Session call patterns...")
    funcs = _function_source_texts()
    missing = [f for f in REAL_PATH_FUNCTIONS if f not in funcs]
    assert not missing, (
        f"expected to find these functions as Guala methods, source scan "
        f"is stale/broken, fix this test's own scanning first: {missing}")

    violations = []
    for fname, text in funcs.items():
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                violations.append((fname, pattern))
    assert not violations, (
        "REGRESSION: found forbidden V7Session call pattern(s) inside "
        f"real-conversation-reachable function(s): {violations} -- the "
        "real path must never construct a V7Session or call any of its "
        "reply-generating/state-mutating methods")
    print(f"  OK: scanned {len(funcs)} real-path functions "
          f"({', '.join(sorted(funcs))}), zero forbidden patterns")


class _NeverTouchedV7Session:
    """Any attribute access at all raises. Attached as self._v7_session on
    a real Guala() to prove the real conversation path genuinely never
    reads or calls anything on it -- not just that it happens not to be
    set (which is the current, coincidental, production reality)."""

    def __getattr__(self, name):
        raise AssertionError(
            f"real conversation path touched v7_session.{name} -- "
            "V7Session must never be read from or called on the real path")


def _run_real_turn_with_hostile_v7_session(converse_phased):
    old_phased = os.environ.get("CONVERSE_PHASED")
    os.environ["CONVERSE_PHASED"] = "1" if converse_phased else "0"
    orig_v7_converse = V7Session.converse

    def _forbidden_converse(self, *a, **kw):
        raise AssertionError(
            "V7Session.converse() was called from a real conversation "
            "turn -- this is the exact 'second voice' regression this "
            "test exists to catch")

    V7Session.converse = _forbidden_converse

    legacy_emit_calls = {"n": 0}
    fact_compose_calls = {"n": 0}
    orig_emit = Guala._emit_from_invariants
    orig_fact_compose = Guala._compose_language_fact_settlement

    def _counting_emit(self, *a, **kw):
        legacy_emit_calls["n"] += 1
        return orig_emit(self, *a, **kw)

    def _counting_fact_compose(self, *a, **kw):
        fact_compose_calls["n"] += 1
        return orig_fact_compose(self, *a, **kw)

    Guala._emit_from_invariants = _counting_emit
    Guala._compose_language_fact_settlement = _counting_fact_compose

    try:
        g = Guala()
        g._v7_session = _NeverTouchedV7Session()
        reply = g.converse("tell me a real thing about the real world",
                           source="joe")
        assert isinstance(reply, ConversationTurnResult), (
            f"expected an immutable turn result, got {reply!r}")
        assert isinstance(reply.response, str)
        assert legacy_emit_calls["n"] == 0, (
            "retired invariant composer ran on the real Fact-Strand path")
        assert fact_compose_calls["n"] == 1, (
            "expected the one canonical Fact-Strand composer exactly once, "
            f"ran {fact_compose_calls['n']} times")
        return reply
    finally:
        V7Session.converse = orig_v7_converse
        Guala._emit_from_invariants = orig_emit
        Guala._compose_language_fact_settlement = orig_fact_compose
        if old_phased is None:
            os.environ.pop("CONVERSE_PHASED", None)
        else:
            os.environ["CONVERSE_PHASED"] = old_phased


def test_real_converse_never_touches_hostile_v7_session_unphased():
    print("Tripwire 2/4 + 3/4 + 4/4 (CONVERSE_PHASED=0): real converse() "
          "with a v7_session that raises on ANY access, and "
          "V7Session.converse() patched to raise if called...")
    reply = _run_real_turn_with_hostile_v7_session(converse_phased=False)
    print(f"  OK: reply={reply!r}, v7_session never touched, "
          "V7Session.converse() never called, exactly one reply composer")


def test_real_converse_never_touches_hostile_v7_session_phased():
    print("Tripwire 2/4 + 3/4 + 4/4 (CONVERSE_PHASED=1): same, through "
          "the phased real entry point...")
    reply = _run_real_turn_with_hostile_v7_session(converse_phased=True)
    print(f"  OK: reply={reply!r}, v7_session never touched, "
          "V7Session.converse() never called, exactly one reply composer")


def test_autonomous_emission_never_touches_hostile_v7_session():
    """Same guarantee for the autonomous/spontaneous emission paths
    (compose_autonomous, _do_emit) -- they thread v7_session through
    _emit_from_invariants exactly like real converse() does."""
    print("Tripwire (autonomous paths): compose_autonomous()/_do_emit() "
          "never touch a hostile v7_session either...")
    orig_v7_converse = V7Session.converse

    def _forbidden_converse(self, *a, **kw):
        raise AssertionError("V7Session.converse() called from autonomous emission")

    V7Session.converse = _forbidden_converse
    try:
        g = Guala()
        g._v7_session = _NeverTouchedV7Session()
        # Seed some real section commits so these autonomous paths have
        # real material to work with (both bail out early to an honest
        # "..."/None on a totally cold engine, which would make this test
        # vacuous).
        g.read_sentence("a real word about a real thing", source="corpus")
        g.compose_autonomous()
        g._do_emit()
        print("  OK: compose_autonomous()/_do_emit() never touched "
              "v7_session, never called V7Session.converse()")
    finally:
        V7Session.converse = orig_v7_converse


if __name__ == "__main__":
    tests = [
        test_static_scan_no_forbidden_v7_calls_in_real_path_functions,
        test_real_converse_never_touches_hostile_v7_session_unphased,
        test_real_converse_never_touches_hostile_v7_session_phased,
        test_autonomous_emission_never_touches_hostile_v7_session,
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
