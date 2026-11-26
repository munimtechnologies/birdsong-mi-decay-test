# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Check that the numbers in READING-BF4.md are the ones in results/stage4/ (stdlib only).
Run: python -m unittest -v test_reading_bf4"""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "stage4")


def load(name):
    with open(os.path.join(RES, name), encoding="utf-8") as fh:
        return json.load(fh)


class TestReadingBF4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "READING-BF4.md"), encoding="utf-8") as fh:
            cls.text = fh.read()
        cls.grade = load("grade4.json")
        cls.stage = load("stage4_results.json")
        cls.self = load("selfcheck4.json")

    def has(self, s):
        self.assertIn(s, self.text)

    def test_grade(self):
        self.assertEqual(self.grade["grade"], "FINITE_STATE_SUFFICES")
        self.assertEqual(self.stage["T4c"]["grade"], "FINITE_STATE_SUFFICES")
        self.has("## Grade: FINITE_STATE_SUFFICES")

    def test_t4_numbers(self):
        t4c, t4b = self.grade["T4c"], self.grade["T4b"]
        self.has("%.2f" % t4c["real_gap"])
        self.has("%.2f" % t4c["gap_p95"])
        self.has("%.4f" % t4c["p_upper"])
        self.has("%.2f" % t4b["gap_p95"])
        self.has("%.4f" % t4b["p_upper"])
        self.assertEqual(t4c["n"], 100)
        self.assertEqual(round(t4c["fire_rate"] * t4c["n"]), 100)
        self.assertEqual(round(t4b["fire_rate"] * t4b["n"]), 100)
        self.assertAlmostEqual(t4c["p_upper"], 48 / 101, places=12)

    def test_aicc(self):
        a = self.stage["T4a"]["fit"]["aicc"]
        for k in ("exponential", "powerlaw", "composite"):
            self.has("%.2f" % a[k])
        self.assertEqual(self.stage["T4a"]["best"], "composite")

    def test_data_counts(self):
        d = self.stage["describe"]
        self.has("{:,}".format(d["n_syllables"]))
        self.has("{:,}".format(d["n_bouts"]))
        for bird, b in d["birds"].items():
            k = self.stage["kgram"][bird]["k"]
            self.has("| %s | %d | %d | %s | %d | %d |" % (
                bird, b["days"], b["bouts"], "{:,}".format(b["syllables"]), b["symbols"], k))

    def test_selfcheck_counts(self):
        s = self.self["summary"]
        rows = {"S0": (0, 0), "S1": (11, 1), "S3": (12, 12), "S4": (1, 12)}
        for kind, (t4a, t4c) in rows.items():
            n = s[kind]["worlds"]
            self.assertEqual(round(s[kind]["t4a_fire_rate"] * n), t4a)
            self.assertEqual(round(s[kind]["t4c_exceeds"] * n), t4c)
        self.assertTrue(self.self["verdict"]["t4c_calibrated"])

    def test_brier(self):
        priors = {"B1_T4a_fires": 0.80, "B2_k_ge3_in_3of4": 0.70,
                  "B3_selfcheck_calibrated": 0.65, "B4_T4b_majority": 0.60,
                  "B5_finite_state_suffices": 0.40, "B6_S4_power_ge_half": 0.50,
                  "B7_S3_exceeds_ge_half": 0.75}
        brier = sum((float(self.grade[k]) - p) ** 2 for k, p in priors.items()) / len(priors)
        self.has("Brier score %.3f" % brier)


if __name__ == "__main__":
    unittest.main()
