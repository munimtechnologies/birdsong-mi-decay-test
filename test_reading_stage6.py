# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Checks that READING-STAGE6.md matches results/stage6/*.json and the registered headline rule
of AMENDMENT-6-STAGE6-SPEECH.md (stdlib only).

Run: python -m unittest -v test_reading_stage6
"""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results", "stage6")
UNITS = ("dev-clean/chapter", "test-clean/chapter", "dev-clean/utterance", "test-clean/utterance")


def _load(name):
    with open(os.path.join(RES, name), encoding="utf-8") as f:
        return json.load(f)


def _reading():
    with open(os.path.join(HERE, "READING-STAGE6.md"), encoding="utf-8") as f:
        return f.read()


def registered_headline(grade):
    """AMENDMENT-6 headline table, from the chapter-level T6c grades."""
    if not grade["selfcheck"]["calibrated"]:
        return "UNRESOLVED_UNCALIBRATED"
    g = (grade["grades"]["dev-clean/chapter"], grade["grades"]["test-clean/chapter"])
    if "FINITE_STATE_SUFFICES" in g:
        return "POSITIVE_CONTROL_FAILS"
    if g == ("EXCEEDS_FINITE_STATE", "EXCEEDS_FINITE_STATE"):
        return "POSITIVE_CONTROL_PASSES"
    return "SPLIT_OR_UNRESOLVED"


class TestReadingStage6(unittest.TestCase):
    def setUp(self):
        self.g = _load("grade6.json")
        self.s = _load("stage6_summary.json")
        self.sc = _load("selfcheck6.json")
        self.text = _reading()

    def test_headline(self):
        h = registered_headline(self.g)
        self.assertEqual(h, "SPLIT_OR_UNRESOLVED")
        self.assertEqual(h, self.g["headline"])
        self.assertEqual(h, self.s["headline"])
        self.assertIn("## Headline: SPLIT_OR_UNRESOLVED", self.text)

    def test_selfcheck(self):
        v = self.sc["verdict"]
        self.assertEqual(v, self.g["selfcheck"])
        self.assertEqual(len(self.sc["rows"]), 8)
        exceeds = [r["world"] for r in self.sc["rows"] if r["t6c"] == "EXCEEDS_FINITE_STATE"]
        self.assertEqual(exceeds, [5])
        self.assertEqual(v["false_exceeds"], 1)
        self.assertLessEqual(v["false_exceeds_rate"], 0.125)
        self.assertTrue(v["calibrated"])
        self.assertFalse(any(r["t6a_fire"] for r in self.sc["rows"]))
        for r in self.sc["rows"]:
            self.assertEqual(sum(r["k_counts"].values()), 40)
        self.assertIn("**1 of 8**", self.text)
        self.assertIn("world 5, p %.4f" % self.sc["rows"][5]["t6c_p"], self.text)

    def test_unit_table(self):
        for u in UNITS:
            row = self.s["units"][u]
            t6c = self.g["T6c"][u]
            self.assertEqual(row["T6c"]["grade"], self.g["grades"][u])
            self.assertAlmostEqual(row["gap_exp_minus_composite"], t6c["real_gap"], places=12)
            self.assertAlmostEqual(row["T6c"]["gap_p95"], t6c["gap_p95"], places=12)
            self.assertAlmostEqual(row["T6c"]["p_upper"], t6c["p_upper"], places=12)
            a = row["aicc"]
            self.assertAlmostEqual(a["exponential"] - a["composite"],
                                   row["gap_exp_minus_composite"], places=9)
            self.assertEqual(min(a, key=a.get), "exponential")
            self.assertEqual(row["best"], "exponential")
            self.assertFalse(row["t6a_fire"])
            self.assertLess(row["w"]["composite"], 0.999)
            subset, unit = u.split("/")
            line = "| %s | %s | %d | %s | %.2f | %.1f | %d/%d | %.2f | %.4f | %s |" % (
                subset, unit, row["n_points"], row["best"], row["gap_exp_minus_composite"],
                100 * row["w"]["composite"], int(round(row["T6c"]["fire_rate"] * row["T6c"]["n"])),
                row["T6c"]["n"], row["T6c"]["gap_p95"], row["T6c"]["p_upper"], row["T6c"]["grade"])
            self.assertIn(line, self.text, u)
        top = max(100 * self.s["units"][u]["w"]["composite"] for u in UNITS)
        self.assertIn("at most %.1f%% of the AICc weight" % top, self.text)

    def test_t6b(self):
        for u, label in (("dev-clean/chapter", "dev-clean"), ("test-clean/chapter", "test-clean")):
            b = self.g["T6b"][u]
            self.assertEqual(b["fire_rate"], 0.0)
            self.assertEqual(b["n"], 100)
            self.assertIn("%.4f (%s)" % (b["p_upper"], label), self.text)

    def test_describe(self):
        d = self.s["describe"]
        lr = _load("load_report6.json")
        self.assertTrue(lr["loader_ok"])
        self.assertEqual(lr["gate_failures"], [])
        self.assertTrue(lr["zenodo"]["md5_ok"])
        self.assertIn(lr["zenodo"]["md5"], self.text)
        for sub in ("dev-clean", "test-clean"):
            for k in ("speakers", "utterances", "phones"):
                self.assertEqual(d[sub][k], lr["subsets"][sub]["describe"][k])
        self.assertIn("40 speakers, 2,703 utterances, 193,644 phones", self.text)
        self.assertIn("40 speakers, 2,620 utterances,\n189,327 phones", self.text)

    def test_chosen_k(self):
        ks = list(self.s["chosen_k"]["dev-clean"].values()) + \
            list(self.s["chosen_k"]["test-clean"].values())
        self.assertEqual(len(ks), 80)
        ks.sort()
        self.assertEqual((ks[39] + ks[40]) / 2.0, 2.0)
        self.assertEqual(ks.count(1), 2)
        self.assertEqual(ks.count(2), 76)
        self.assertEqual(ks.count(3), 2)
        self.assertTrue(all(k == 2 for k in self.s["chosen_k"]["dev-clean"].values()))
        self.assertIn("Median k over the 80 speakers is **2**", self.text)

    def test_curve_and_chart(self):
        m = self.s["mi_dev_clean_chapter"]["values"]
        ch = self.s["chart_mi_by_distance"]
        self.assertEqual(len(ch["distances"]), len(ch["speech_dev_clean_chapters"]))
        self.assertEqual(len(ch["distances"]), len(ch["finch_real_song_stage4"]))
        for d, v in zip(ch["distances"], ch["speech_dev_clean_chapters"]):
            self.assertAlmostEqual(round(m[str(d)], 5), v, places=9, msg=str(d))
        for d, s in ((1, "0.5535"), (3, "0.0539"), (5, "0.0074"), (8, "0.0011")):
            self.assertEqual("%.4f" % m[str(d)], s)
            self.assertIn(s, self.text)
        self.assertEqual("%.5f" % m["10"], "0.00009")
        self.assertIn("0.00009 at 10", self.text)
        lo = self.s["mi_dev_clean_chapter"]["tail_11_to_100_min"]
        hi = self.s["mi_dev_clean_chapter"]["tail_11_to_100_max"]
        self.assertIn("between %.5f and %.5f" % (lo, hi), self.text)
        self.assertIn("0.5719\nat distance 10 and 0.0124 at 100", self.text)

    def test_forecasts_and_brier(self):
        out = {}
        for k, v in self.g.items():
            if k[:1] == "P" and k[1:2].isdigit() and "_" in k:
                out[k.split("_", 1)[0]] = v
        self.assertEqual(sorted(out), ["P%d" % i for i in range(1, 10)])
        fc = self.s["forecasts"]
        b = 0.0
        for f in fc:
            self.assertEqual(f["outcome"], out[f["id"]], f["id"])
            b += (f["p"] - (1.0 if f["outcome"] else 0.0)) ** 2
            line = "| %s | %s | %.2f | %s |" % (f["id"], f["statement"], f["p"],
                                               "true" if f["outcome"] else "false")
            self.assertIn(line, self.text, f["id"])
        b /= len(fc)
        self.assertEqual("%.4f" % b, "0.3653")
        self.assertAlmostEqual(self.s["brier"], b, places=12)
        self.assertIn("Brier score **0.3653**", self.text)

    def test_finch_reference(self):
        self.assertEqual(self.s["finch_stage4_reference"]["real_gap_exp_minus_composite"], 138.84)
        self.assertIn("138.84", self.text)
        self.assertIn("215,740 syllables", self.text)


if __name__ == "__main__":
    unittest.main()
