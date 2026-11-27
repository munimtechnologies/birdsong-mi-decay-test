# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Checks that READING-STAGE8.md matches results/stage8/stage8.json and the registered rules in
grade8.py (stdlib only).

Run: python -m unittest -v test_reading_stage8
"""
import json
import os
import re
import unittest

import grade8

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "stage8")


def _load(name):
    with open(os.path.join(RES, name), encoding="utf-8") as f:
        return json.load(f)


def _reading():
    with open(os.path.join(HERE, "READING-STAGE8.md"), encoding="utf-8") as f:
        return f.read()


class TestReadingStage8(unittest.TestCase):
    def setUp(self):
        self.r = _load("stage8.json")
        self.s = self.r["summary"]
        self.text = _reading()

    def test_registered_grade_recomputes(self):
        rates = {k: self.s[k]["c8_rate"] for k in grade8.ALL}
        g = grade8.grade(rates)
        self.assertEqual(g["verdict"], "MIXED")
        self.assertEqual(g["verdict"], self.r["grade_primary"]["verdict"])
        self.assertAlmostEqual(g["max_false_alarm"], 0.06)
        self.assertAlmostEqual(g["median_detection"], 0.54)
        self.assertEqual(g["long_memory_rate"], 0.0)
        self.assertIn("## Headline: MIXED", self.text)
        strong = {k: self.s[k]["c8_strong_rate"] for k in grade8.ALL}
        self.assertEqual(grade8.grade(strong)["verdict"], "SPECIFIC_BUT_INSENSITIVE")
        self.assertEqual(self.r["grade_secondary_strong"]["verdict"], "SPECIFIC_BUT_INSENSITIVE")

    def test_table_rows(self):
        for k in grade8.ALL:
            row = self.s[k]
            self.assertEqual(row["worlds"], 50)
            line = "| %s | " % k
            self.assertIn(line, self.text, k)
            tail = "| %d | %.2f | %d |" % (row["c8_fires"], row["c8_rate"],
                                          row["composite_strong_fires"])
            seg = self.text.split(line, 1)[1].split("\n", 1)[0]
            self.assertTrue(seg.endswith(tail), "%s: %r" % (k, seg))

    def test_pooled_counts(self):
        fin = sum(self.s[k]["c8_fires"] for k in grade8.FINITE)
        rec = sum(self.s[k]["c8_fires"] for k in grade8.RECURSIVE)
        self.assertEqual(fin, 5)
        self.assertEqual(rec, 133)
        self.assertIn("**5 of 350**", self.text)
        self.assertIn("**133 of 250**", self.text)
        comp_fin = sum(self.s[k]["composite_strong_fires"] for k in grade8.FINITE)
        comp_rec = sum(self.s[k]["composite_strong_fires"] for k in grade8.RECURSIVE)
        self.assertEqual(comp_fin, 146)
        self.assertEqual(comp_rec, 39)
        self.assertEqual(self.s["L1_heavy_tailed_bouts"]["composite_strong_fires"], 50)
        self.assertIn("146 of 350 finite-state worlds", self.text)
        self.assertIn("39 of 250 recursive worlds", self.text)
        self.assertEqual(self.s["F2_pooled_individuals"]["c8_fires"], 3)
        self.assertEqual(self.s["R1_lin_tegmark_k5_d12"]["c8_fires"], 31)
        self.assertEqual(sum(self.s[k]["c8_strong_fires"] for k in grade8.ALL), 0)

    def test_forecasts_and_brier(self):
        rates = {k: self.s[k]["c8_rate"] for k in grade8.ALL}
        out = grade8.forecast_outcomes(rates, "MIXED")
        self.assertEqual(out, self.r["forecast_outcomes"])
        b = grade8.brier(out)
        self.assertEqual("%.4f" % b, "0.2831")
        self.assertEqual("%.4f" % self.r["brier"], "0.2831")
        self.assertIn("**0.2831**", self.text)
        for q, _, p in grade8.FORECASTS:
            m = re.search(r"\| %s \| [^|]+ \| ([0-9.]+) \| (true|false)" % q, self.text)
            self.assertIsNotNone(m, q)
            self.assertAlmostEqual(float(m.group(1)), p)
            self.assertEqual(m.group(2) == "true", out[q], q)

    def test_gate(self):
        g = _load("gate8.json")
        self.assertTrue(all(line.endswith(" same") for line in g["gate"]))
        self.assertIn(g["mi_decay_sha256"], self.text)

    def test_strong_ceiling(self):
        p = os.path.join(RES, "stage8_worlds.json")
        if not os.path.exists(p):
            self.skipTest("stage8_worlds.json not present")
        with open(p, encoding="utf-8") as f:
            rows = json.load(f)
        self.assertEqual(len(rows), 650)
        wpl = [r["w"]["powerlaw"] for r in rows
               if isinstance(r.get("w"), dict) and isinstance(r["w"].get("powerlaw"), float)]
        self.assertTrue(wpl)
        self.assertLess(max(wpl), 0.91)
        f2 = sorted(round(r["w"]["powerlaw"], 4) for r in rows if isinstance(r, dict)
                    and r.get("kind") == "F2_pooled_individuals" and r.get("best") == "powerlaw")
        self.assertEqual(f2, [0.8676, 0.8987, 0.8997])


if __name__ == "__main__":
    unittest.main()
