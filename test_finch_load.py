# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Tests for the AMENDMENT-1 house-finch loader (numpy only, no real data)."""
import json
import math
import os
import shutil
import tempfile
import unittest

import numpy as np

import finch_load as fl

EULER = 0.5772156649015329


def row(ind, song, c2, c3=None, c4=None):
    return {"individual": ind, "song": song, "c2": c2,
            "c3": c2 if c3 is None else c3, "c4": c2 if c4 is None else c4}


class TestEstimator(unittest.TestCase):
    def test_digamma(self):
        self.assertAlmostEqual(float(fl.digamma(1.0)[0]), -EULER, places=9)
        self.assertAlmostEqual(float(fl.digamma(10.0)[0]), 2.2517525890667211, places=9)

    def test_ent_nat(self):
        self.assertAlmostEqual(fl.ent_nat([2, 2]), math.log(4) - (1 - EULER), places=9)
        self.assertTrue(math.isnan(fl.ent_nat([])))

    def test_mi_small(self):
        self.assertAlmostEqual(fl.mi_nat([[0, 1, 0, 1]], 1), fl.ent_nat([2, 1]), places=12)

    def test_pairs_stay_within_birds(self):
        self.assertAlmostEqual(fl.mi_nat([[0, 0], [1, 1]], 1), fl.ent_nat([1, 1]), places=12)
        self.assertAlmostEqual(fl.mi_nat([[0, 1], [0]], 1), fl.ent_nat([1]), places=12)
        self.assertTrue(math.isnan(fl.mi_nat([[0]], 1)))


class TestBuild(unittest.TestCase):
    def test_file_order_and_runs(self):
        rows = [row("A", "s1", "x"), row("A", "s1", "y"), row("B", "t1", "x"),
                row("A", "s2", "z")]
        levels, stats = fl.build_levels(rows)
        self.assertEqual(levels["2"][0], {"bird": "A", "songs": [["x", "y"], ["z"]]})
        self.assertEqual(levels["2"][1], {"bird": "B", "songs": [["x"]]})
        self.assertEqual(stats["n_birds"], 2)
        self.assertEqual(stats["n_songs"], 3)
        self.assertEqual(stats["n_song_values_split"], 0)
        self.assertEqual(stats["levels"]["2"]["n_symbols"], 3)

    def test_split_song_and_na(self):
        rows = [row("A", "s1", "x"), row("A", "s2", "NA"), row("A", "s1", "y")]
        levels, stats = fl.build_levels(rows)
        self.assertEqual(stats["n_songs"], 3)
        self.assertEqual(stats["n_song_values_split"], 1)
        self.assertEqual(stats["levels"]["2"]["n_na"], 1)
        probs = fl.problems(stats)
        self.assertIn("song values split into non-adjacent runs", probs)
        self.assertIn("NA labels at deep split 2", probs)
        self.assertIn("birds 1 vs paper 331", probs)


class TestC0(unittest.TestCase):
    def setUp(self):
        rows = [row("A", "s1", "x", "p", "u"), row("A", "s1", "y", "q", "u"),
                row("A", "s2", "z", "p", "v"), row("B", "t1", "x", "q", "v"),
                row("B", "t1", "x", "p", "u"), row("B", "t2", "y", "q", "u")]
        self.levels, _ = fl.build_levels(rows)
        self.theirs = {}
        for g, lv in ((1, "2"), (2, "3"), (3, "4")):
            seqs = fl.int_sequences(self.levels[lv])
            self.theirs[g] = {d: fl.mi_nat(seqs, d) for d in (1, 2, 3)}

    def test_pass(self):
        res = fl.c0_check(self.levels, self.theirs, max_d=3)
        self.assertTrue(res["pass"])
        self.assertEqual(res["n_their_curves"], 3)

    def test_fail_on_mismatch(self):
        self.theirs[1][1] += 1e-3
        self.assertFalse(fl.c0_check(self.levels, self.theirs, max_d=3)["pass"])

    def test_fail_on_missing_curve(self):
        del self.theirs[3]
        self.assertFalse(fl.c0_check(self.levels, self.theirs, max_d=3)["pass"])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data = os.path.join(self.tmp, "data")
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.data)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_rows(self, rows):
        with open(os.path.join(self.data, "finch_rows.tsv"), "w", encoding="utf-8") as fh:
            fh.write("row\tindividual\tsong\tc2\tc3\tc4\n")
            for i, r in enumerate(rows, 1):
                fh.write("%d\t%s\t%s\t%s\t%s\t%s\n" % (i, r["individual"], r["song"],
                                                       r["c2"], r["c3"], r["c4"]))

    def test_stop_writes_report(self):
        self.write_rows([row("A", "s1", "x"), row("A", "s1", "y")])
        self.assertEqual(fl.main(self.data, self.out), 1)
        with open(os.path.join(self.out, "load_report.json")) as fh:
            rep = json.load(fh)
        self.assertFalse(rep["ok"])
        self.assertFalse(os.path.exists(os.path.join(self.data, "finch_levels.json")))

    def test_missing_export(self):
        self.assertEqual(fl.main(self.data, self.out), 1)

    def test_happy_path(self):
        rng = np.random.default_rng(1)
        rows = []
        for b in range(331):
            n_songs = 9 if b < 76 else 8
            for s in range(n_songs):
                for _ in range(3):
                    rows.append(row("bird%d" % b, "b%d_s%d" % (b, s),
                                    str(int(rng.integers(10))), str(int(rng.integers(12))),
                                    str(int(rng.integers(15)))))
        self.write_rows(rows)
        levels, stats = fl.build_levels(rows)
        self.assertEqual(stats["n_songs"], 2724)
        for g, lv in ((1, "2"), (2, "3"), (3, "4")):
            seqs = fl.int_sequences(levels[lv])
            with open(os.path.join(self.data, "their_mi_%d.tsv" % g), "w") as fh:
                fh.write("dist\tmi_raw\tmi_base\n")
                for d in range(1, 120):
                    v = fl.mi_nat(seqs, d)
                    fh.write("%d\t%s\t0\n" % (d, repr(v) if math.isfinite(v) else "NA"))
        self.assertEqual(fl.main(self.data, self.out), 0)
        with open(os.path.join(self.data, "finch_levels.json")) as fh:
            lv = json.load(fh)["levels"]
        self.assertEqual(sorted(lv), ["2", "3", "4"])
        self.assertEqual(len(lv["2"]), 331)
        with open(os.path.join(self.out, "load_report.json")) as fh:
            rep = json.load(fh)
        self.assertTrue(rep["ok"])
        self.assertTrue(rep["C0"]["pass"])


if __name__ == "__main__":
    unittest.main()
