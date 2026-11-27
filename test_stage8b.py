# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage 8B registration tests (stdlib only): exact binomial bounds, grading rules, forecasts,
the C8R rule, and agreement between AMENDMENT-8B-STAGE8B.md, grade8b.py and stage8b.py.
Run: python -m unittest -v test_stage8b"""
import ast
import os
import unittest

import grade8b

HERE = os.path.dirname(os.path.abspath(__file__))


def fires_with(finite=0.0, long_memory=0.0, recursive=0.6, **over):
    rates = {k: finite for k in grade8b.FINITE}
    rates.update({k: long_memory for k in grade8b.LONG})
    rates.update({k: recursive for k in grade8b.RECURSIVE})
    rates.update(over)
    return {k: int(round(rates[k] * grade8b.WORLDS[k])) for k in grade8b.ALL}


class TestBounds(unittest.TestCase):
    def test_zero_and_all(self):
        lo, hi = grade8b.cp_bounds(0, 100)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 1 - 0.025 ** (1 / 100), places=9)
        lo, hi = grade8b.cp_bounds(100, 100)
        self.assertEqual(hi, 1.0)
        self.assertAlmostEqual(lo, 0.025 ** (1 / 100), places=9)

    def test_known_interval(self):
        lo, hi = grade8b.cp_bounds(3, 50)          # about 0.0125 to 0.1655
        self.assertTrue(0.0115 < lo < 0.0135, lo)
        self.assertTrue(0.1635 < hi < 0.1675, hi)

    def test_upper_rule_edges(self):
        self.assertLess(grade8b.cp_bounds(4, 100)[1], 0.10)      # about 0.0993
        self.assertGreater(grade8b.cp_bounds(5, 100)[1], 0.10)   # about 0.1128
        self.assertLess(grade8b.cp_bounds(20, 400)[1], 0.10)     # about 0.076
        self.assertGreater(grade8b.cp_bounds(40, 400)[0], 0.05)  # about 0.072

    def test_cdf(self):
        self.assertAlmostEqual(grade8b.binom_cdf(1, 2, 0.5), 0.75, places=12)
        self.assertEqual(grade8b.binom_cdf(-1, 5, 0.3), 0.0)
        self.assertEqual(grade8b.binom_cdf(5, 5, 0.3), 1.0)


class TestGrade(unittest.TestCase):
    def test_hierarchy(self):
        g = grade8b.grade(fires_with(long_memory=0.2, recursive=0.5))
        self.assertEqual(g["verdict"], "CALIBRATED_HIERARCHY_SIGNATURE")

    def test_f2_at_limit_passes(self):
        f = fires_with(F2_pooled_individuals=0.05)
        self.assertEqual(f["F2_pooled_individuals"], 20)
        self.assertEqual(grade8b.grade(f)["verdict"], "CALIBRATED_HIERARCHY_SIGNATURE")

    def test_long_memory(self):
        g = grade8b.grade(fires_with(L3_fgn_h09=0.3))
        self.assertEqual(g["verdict"], "CALIBRATED_LONG_MEMORY_SIGNATURE")
        self.assertAlmostEqual(g["max_long_memory_rate"], 0.3)

    def test_not_specific(self):
        g = grade8b.grade(fires_with(F2_pooled_individuals=0.10))
        self.assertEqual(g["verdict"], "NOT_SPECIFIC")

    def test_unresolved(self):
        g = grade8b.grade(fires_with(F6_high_order_markov=0.05))
        self.assertFalse(g["false_alarm_ok"])
        self.assertEqual(g["verdict"], "UNRESOLVED")

    def test_insensitive(self):
        g = grade8b.grade(fires_with(R5_pooled_recursive_birds=0.3))
        self.assertEqual(g["verdict"], "SPECIFIC_BUT_INSENSITIVE")

    def test_missing_kind(self):
        f = fires_with()
        del f["L2_fgn_h07"]
        with self.assertRaises(KeyError):
            grade8b.grade(f)


class TestForecasts(unittest.TestCase):
    def test_brier_hand_traced(self):
        c8 = fires_with(long_memory=0.5)
        c8r = fires_with(R1_lin_tegmark_k5_d12=0.5)
        v = grade8b.grade(c8)["verdict"]
        self.assertEqual(v, "CALIBRATED_LONG_MEMORY_SIGNATURE")
        out = grade8b.forecast_outcomes(c8, c8r, v)
        self.assertEqual([out[q] for q, _, _ in grade8b.FORECASTS],
                         [True, True, True, True, True, True, False, True])
        self.assertAlmostEqual(grade8b.brier(out), 0.196875, places=9)


class TestC8R(unittest.TestCase):
    def test_rule(self):
        f = grade8b.c8r
        self.assertTrue(f("powerlaw", {"exponential": -100.0, "powerlaw": -110.0, "composite": -106.0}))
        self.assertFalse(f("powerlaw", {"exponential": -100.0, "powerlaw": -109.9, "composite": -106.0}))
        self.assertFalse(f("composite", {"exponential": -100.0, "powerlaw": -120.0, "composite": -125.0}))
        self.assertFalse(f(None, {}))
        self.assertFalse(f("powerlaw", {"powerlaw": -10.0}))


class TestRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "AMENDMENT-8B-STAGE8B.md"), encoding="utf-8") as fh:
            cls.text = fh.read()
        with open(os.path.join(HERE, "stage8b.py"), encoding="utf-8") as fh:
            cls.src = fh.read()

    def test_constants_in_amendment(self):
        self.assertEqual(grade8b.SEED, 20261128)
        self.assertEqual(sum(grade8b.WORLDS.values()), 1100)
        for s in ("Seed 20261128", "1,100 worlds", "AICc(exponential) - AICc(power law) >= 10",
                  "above 0.05", "at most 0.10", "at least 0.40", "0.30 or more"):
            self.assertIn(s, self.text)

    def test_forecast_rows(self):
        for q, stmt, p in grade8b.FORECASTS:
            self.assertIn("| %s | %s | %.2f |" % (q, stmt, p), self.text)

    def test_kinds_and_worlds_listed(self):
        for k in grade8b.ALL:
            self.assertIn("`%s`" % k, self.text)
        for g in grade8b.GRADES:
            self.assertIn(g, self.text)
        for k, n in grade8b.WORLDS.items():
            self.assertRegex(self.text, r"\| `%s` \| [^|]+ \| %d \|" % (k, n))

    def test_world_order_in_code(self):
        tree = ast.parse(self.src)
        keys = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "WORLD_FNS" for t in node.targets):
                keys = [k.value for k in node.value.keys]
        self.assertEqual(keys, grade8b.ALL)


if __name__ == "__main__":
    unittest.main()
