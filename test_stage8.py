# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage 8 registration tests (stdlib only): grading rules, forecasts, blind real-data readout,
and agreement between AMENDMENT-8-STAGE8.md, grade8.py and stage8.py.
Run: python -m unittest -v test_stage8"""
import ast
import os
import unittest

import grade8

HERE = os.path.dirname(os.path.abspath(__file__))


def rates_with(finite=0.0, recursive=0.6, long_memory=0.0, **over):
    r = {k: finite for k in grade8.FINITE}
    r.update({k: recursive for k in grade8.RECURSIVE})
    r["L1_heavy_tailed_bouts"] = long_memory
    r.update(over)
    return r


class TestGrade(unittest.TestCase):
    def test_not_specific(self):
        r = rates_with(F2_pooled_individuals=0.2)
        self.assertEqual(grade8.grade(r)["verdict"], "NOT_SPECIFIC")

    def test_hierarchy_signature(self):
        r = rates_with(finite=0.04, long_memory=0.1)
        r.update({"R1_lin_tegmark_k5_d12": 0.5, "R2_lin_tegmark_k8_d12": 0.5,
                  "R3_lin_tegmark_k5_d8_q3": 0.5, "R4_recursive_bouts": 0.0,
                  "R5_pooled_recursive_birds": 0.0})
        g = grade8.grade(r)
        self.assertEqual(g["verdict"], "CALIBRATED_HIERARCHY_SIGNATURE")
        self.assertEqual(g["median_detection"], 0.5)

    def test_long_memory_signature(self):
        r = rates_with(finite=0.04, long_memory=0.3)
        self.assertEqual(grade8.grade(r)["verdict"], "CALIBRATED_LONG_MEMORY_SIGNATURE")

    def test_insensitive(self):
        r = rates_with(recursive=0.2)
        self.assertEqual(grade8.grade(r)["verdict"], "SPECIFIC_BUT_INSENSITIVE")

    def test_mixed(self):
        r = rates_with(F6_high_order_markov=0.1)
        self.assertEqual(grade8.grade(r)["verdict"], "MIXED")

    def test_missing_kind(self):
        r = rates_with()
        del r["R4_recursive_bouts"]
        with self.assertRaises(KeyError):
            grade8.grade(r)


class TestForecasts(unittest.TestCase):
    def test_brier_hand_traced(self):
        r = rates_with(long_memory=0.4)
        v = grade8.grade(r)["verdict"]
        self.assertEqual(v, "CALIBRATED_LONG_MEMORY_SIGNATURE")
        out = grade8.forecast_outcomes(r, v)
        self.assertEqual([out[q] for q, _, _ in grade8.FORECASTS],
                         [True, True, True, True, True, True, True, False])
        self.assertAlmostEqual(grade8.brier(out), 0.220625, places=9)


class TestReadout(unittest.TestCase):
    def test_branches(self):
        f = grade8.real_data_readout
        self.assertEqual(f(None, [])["verdict"], "NOT_MEASURED")
        self.assertEqual(f("composite", ["powerlaw"])["verdict"], "C8_ABSENT")
        self.assertEqual(f("powerlaw", [])["verdict"], "C8_PRESENT_NO_SURROGATES")
        five = ["composite"] * 95 + ["powerlaw"] * 5
        six = ["composite"] * 94 + ["powerlaw"] * 6
        self.assertEqual(f("powerlaw", five)["verdict"], "C8_EXCEEDS_FINITE_STATE")
        self.assertEqual(f("powerlaw", six)["verdict"], "C8_PRESENT_IN_SURROGATES")
        self.assertEqual(f("powerlaw", six)["surrogate_fires"], 6)


class TestRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "AMENDMENT-8-STAGE8.md"), encoding="utf-8") as fh:
            cls.text = fh.read()
        with open(os.path.join(HERE, "stage8.py"), encoding="utf-8") as fh:
            cls.src = fh.read()

    def test_constants_in_amendment(self):
        self.assertEqual(grade8.SEED, 20261127)
        self.assertEqual(grade8.WORLDS, 50)
        for s in ("seed 20261127", "50 worlds", "0.05", "0.20", "0.50", "0.30", "0.999"):
            self.assertIn(s, self.text)

    def test_forecast_rows(self):
        for q, stmt, p in grade8.FORECASTS:
            self.assertIn("| %s | %s | %.2f |" % (q, stmt, p), self.text)

    def test_kinds_listed(self):
        for k in grade8.ALL:
            self.assertIn("`%s`" % k, self.text)
        for g in grade8.GRADES:
            self.assertIn(g, self.text)

    def test_world_order_in_code(self):
        tree = ast.parse(self.src)
        keys = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "WORLD_FNS" for t in node.targets):
                keys = [k.value for k in node.value.keys]
        self.assertEqual(keys, grade8.ALL)


if __name__ == "__main__":
    unittest.main()
