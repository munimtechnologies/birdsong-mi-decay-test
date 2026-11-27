# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Check that the numbers in READING-STAGE1.md are the ones in results/stage1/ (stdlib only).
Run: python -m unittest -v test_reading_stage1"""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "stage1")

SCEN = ["W0_plain_markov", "W1_two_timescale_markov", "W2_pooled_individuals",
        "W3_bout_song_types", "W4_house_finch_design", "W5_recursive_hierarchy"]


def load(name):
    with open(os.path.join(RES, name), encoding="utf-8") as fh:
        return json.load(fh)


class TestReadingStage1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "READING-STAGE1.md"), encoding="utf-8") as fh:
            cls.text = fh.read()
        cls.cal = load("calibration.json")
        cls.worlds = load("calibration_worlds.json")

    def has(self, s):
        self.assertIn(s, self.text)

    def test_grade(self):
        self.assertEqual(self.cal["grade_primary"]["verdict"], "UNCALIBRATED_MULTI_TIMESCALE")
        self.assertFalse(self.cal["grade_primary"]["positive_control_ok"])
        self.assertEqual(self.cal["grade_secondary_lowest_aicc"]["verdict"],
                         "UNCALIBRATED_MULTI_TIMESCALE")
        self.has("## Grade: UNCALIBRATED_MULTI_TIMESCALE (positive control failed)")

    def test_table_rows(self):
        s = self.cal["summary"]
        for i, key in enumerate(SCEN):
            r = s[key]
            self.assertEqual(r["worlds"], 50)
            row_tail = "| %d of 50 | %d of 50 | %.2f |" % (
                r["fires_strong"], r["fires_best"], r["median_d_aicc_exp_minus_comp"])
            self.has("| W%d |" % i)
            self.has(row_tail)

    def test_per_world_matches_summary(self):
        for key in SCEN:
            ws = [w for w in self.worlds if w["scenario"] == key]
            self.assertEqual(len(ws), 50)
            self.assertEqual(sum(1 for w in ws if w["fire_strong"]),
                             self.cal["summary"][key]["fires_strong"])
            self.assertEqual(sum(1 for w in ws if w["best"] == "composite"),
                             self.cal["summary"][key]["fires_best"])

    def test_exploratory_best_counts(self):
        fs = [w for w in self.worlds if w["scenario"] != "W5_recursive_hierarchy"]
        w5 = [w for w in self.worlds if w["scenario"] == "W5_recursive_hierarchy"]
        self.assertEqual(len(fs), 250)

        def counts(ws):
            return tuple(sum(1 for w in ws if w["best"] == b)
                         for b in ("powerlaw", "composite", "exponential"))
        self.has("| W0-W4 (250 finite-state worlds) | %d | %d | %d |" % counts(fs))
        self.has("| W5 recursive hierarchy (50) | %d | %d | %d |" % counts(w5))
        self.assertEqual(counts(fs)[0], 0)

    def test_brier(self):
        s = self.cal["summary"]
        rate = {k: s[k]["fire_rate_strong"] for k in SCEN}
        outcomes = [
            (rate["W0_plain_markov"] <= 0.10, 0.70),
            (rate["W1_two_timescale_markov"] >= 0.30, 0.60),
            (rate["W2_pooled_individuals"] >= 0.30, 0.80),
            (rate["W3_bout_song_types"] >= 0.30, 0.70),
            (rate["W4_house_finch_design"] >= 0.30, 0.55),
            (rate["W5_recursive_hierarchy"] >= 0.80, 0.75),
            (self.cal["grade_primary"]["verdict"] in (
                "UNCALIBRATED_MULTI_TIMESCALE", "UNCALIBRATED_EVEN_PLAIN_MARKOV"), 0.80),
        ]
        brier = sum((float(o) - p) ** 2 for o, p in outcomes) / len(outcomes)
        self.has("Brier score %.3f" % brier)
        self.assertEqual([o for o, _ in outcomes],
                         [True, False, True, True, False, False, True])


if __name__ == "__main__":
    unittest.main()
