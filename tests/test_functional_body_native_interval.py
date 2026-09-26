"""Compiled-boundary proof only; numerical equivalence has its existing suite.

Loader faults below are explicit infrastructure fault injection, never fabricated
organism sensation or experience. Run as standalone unittest, not pytest.
"""
from fractions import Fraction
from importlib.machinery import EXTENSION_SUFFIXES
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import guala_body_interval as interval
from test_functional_body_native import apparatus
from test_functional_body_interval_equivalence import outcome, previous


class NativeIntervalTests(unittest.TestCase):
    def test_loaded_binary_and_one_interval_dispatch(self):
        expected = os.environ.get("GUALA_BODY_INTERVAL_EXTENSION_ROOT")
        self.assertIsNotNone(expected, "explicit isolated compiled extension root required")
        actual = Path(interval.__file__).resolve()
        self.assertTrue(actual.is_relative_to(Path(expected).resolve()))
        self.assertTrue(any(str(actual).endswith(s) for s in EXTENSION_SUFFIXES))
        self.assertEqual(interval.INTERVAL_ABI, 1)
        engine = apparatus(False)
        self.assertIs(engine._advance_interval, interval.advance_interval)
        calls = []
        original = engine._advance_interval
        def observed(*args):
            calls.append(args[2])
            return original(*args)
        engine._advance_interval = observed
        state = engine.initial_state()
        result = engine.advance(state, (.3,), 10000, 1.)
        self.assertEqual(calls, [10])
        self.assertEqual(result, previous(apparatus(False)).advance(state, (.3,), 10000, 1.))
        print(dict(body_interval_extension=str(actual)), flush=True)

    def test_missing_and_wrong_abi_refuse_without_python_fallback(self):
        with patch.dict(sys.modules, {"guala_body_interval": None}):
            with self.assertRaises(ModuleNotFoundError):
                apparatus(False)
        with patch.object(interval, "INTERVAL_ABI", 2):
            with self.assertRaisesRegex(ValueError, "interval ABI"):
                apparatus(False)
        engine = apparatus(False)
        engine.advance(engine.initial_state(), (.3,), 1000, 1.)

    def test_supply_comparison_retains_exact_numeric_boundary(self):
        engine, predecessor = apparatus(False), previous(apparatus(False))
        state = engine.initial_state()
        work = predecessor.advance(state, (.3,), 1000, 1.).positive_motor_work_j
        self.assertGreater(work, 0.)
        exact = Fraction.from_float(work)
        # Both rationals round to the same binary64 supply. A native double
        # argument would silently erase the strict first-interval refusal.
        tiny = Fraction(1, 10**100)
        for supply in (exact - tiny, exact, exact + tiny):
            command = dict(efforts=(.3,), elapsed_us=1000, available_work_j=supply)
            self.assertEqual(outcome(engine, state, **command),
                             outcome(predecessor, state, **command))
        self.assertIsNotNone(outcome(engine, state, efforts=(.3,), elapsed_us=1000,
                                     available_work_j=exact - tiny)[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
