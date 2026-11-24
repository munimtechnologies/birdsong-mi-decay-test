"""Tests for mi_stage2.py (Apache-2.0, MV2, Munim, Inc.; made with AI agents).
Pure-logic tests need numpy only; the end-to-end test needs scipy and mi_decay.py."""
import json
import math
import os
import tempfile
import unittest

import numpy as np

import mi_stage2 as m


def _have_core():
    try:
        import scipy  # noqa: F401
        m._core()
        return True
    except Exception:
        return False


A1, A2, B = (1, 2, 3), (1, 2, 4), (7, 8, 9)


class TestPure(unittest.TestCase):
    def test_encode(self):
        birds = [("a", [["x", "y"], ["y"]]), ("b", [["z"], []])]
        coded, labels = m.encode(birds)
        self.assertEqual(coded, [("a", [(0, 1), (1,)]), ("b", [(2,)])])
        self.assertEqual(labels, ["x", "y", "z"])

    def test_join_and_sequences(self):
        j = m.join_songs([(0, 1), (1,)])
        self.assertEqual(j.tolist(), [0, 1, 1])
        self.assertEqual(j.dtype, np.int64)
        self.assertEqual(len(m.join_songs([])), 0)
        seqs = m.bird_sequences([("a", []), ("b", [(1, 2)])])
        self.assertEqual(len(seqs), 1)
        self.assertEqual(seqs[0].tolist(), [1, 2])

    def test_coverage(self):
        c = m.coverage([np.arange(5), np.arange(30)])
        self.assertEqual(c["1"], {"birds": 2, "pairs": 33})
        self.assertEqual(c["10"], {"birds": 1, "pairs": 20})
        self.assertEqual(c["100"], {"birds": 0, "pairs": 0})

    def test_repeat_rate(self):
        self.assertAlmostEqual(m.repeat_rate([(1,), (1,), (2,), (2,)]), 2 / 3)
        self.assertTrue(math.isnan(m.repeat_rate([(1,)])))
        self.assertAlmostEqual(m.repeat_rate([0, 0, 1]), 0.5)

    def test_permute_keeps_songs(self):
        rng = np.random.default_rng(0)
        songs = [(1,), (2,), (3,), (2,)]
        self.assertEqual(sorted(m.permute_songs(rng, songs)), sorted(songs))

    def test_surrogate_exact(self):
        rng = np.random.default_rng(1)
        out = m.surrogate_songs(rng, [(1,), (1,), (1,)])
        self.assertEqual(out, [(1,), (1,), (1,)])
        out = m.surrogate_songs(rng, [(1,), (2,), (1,), (2,)])
        self.assertEqual(len(out), 4)
        self.assertTrue(all(out[i] != out[i - 1] for i in range(1, 4)))
        self.assertTrue(set(out) <= {(1,), (2,)})
        out = m.surrogate_songs(rng, [(1,), (2,), (3,)], rate=1.0)
        self.assertEqual(len(out), 3)
        self.assertEqual(len(set(out)), 1)
        self.assertEqual(m.surrogate_songs(rng, []), [])

    def test_edit_distance(self):
        self.assertEqual(m.edit_distance(("a", "b", "c"), ("a", "c")), 1)
        self.assertAlmostEqual(m.norm_dist(("a", "b", "c"), ("a", "c")), 1 / 3)
        self.assertEqual(m.norm_dist((), ()), 0.0)
        self.assertEqual(m.edit_distance(A1, (4, 5, 6)), 3)

    def test_song_types(self):
        self.assertEqual(m.song_types([A1, A2, B, A1]), [0, 0, 1, 0])

    def test_surrogate_typed(self):
        rng = np.random.default_rng(2)
        for _ in range(20):
            out = m.surrogate_typed(rng, [A1, B, A2, B])
            self.assertEqual(len(out), 4)
            self.assertTrue(set(out) <= {A1, A2, B})
            isA = [s in (A1, A2) for s in out]
            self.assertTrue(all(isA[i] != isA[i - 1] for i in range(1, 4)))
        self.assertEqual(m.surrogate_typed(rng, []), [])

    def test_grade_t2(self):
        gaps = [float(x) for x in range(100)]
        g = m.grade_t2(95.0, [False] * 100, gaps)
        self.assertEqual(g["grade"], "EXCEEDS_FINITE_STATE")
        self.assertAlmostEqual(g["gap_p95"], 94.05)
        self.assertAlmostEqual(g["p_upper"], 6 / 101)
        self.assertEqual(m.grade_t2(50.0, [True] * 100, gaps)["grade"], "FINITE_STATE_SUFFICES")
        self.assertEqual(m.grade_t2(50.0, [False] * 100, gaps)["grade"], "UNRESOLVED")
        g = m.grade_t2(None, [True] * 100, gaps)
        self.assertEqual(g["grade"], "UNRESOLVED")
        self.assertIsNone(g["real_gap"])
        few = [float(x) for x in range(10)] + [None] * 85 + [float("nan")] * 5
        g = m.grade_t2(1000.0, [True] * 100, few)
        self.assertEqual(g["grade"], "UNRESOLVED")
        self.assertEqual(g["n_finite_gap"], 10)

    def test_summarize_empty(self):
        s = m.summarize_null(1.0, [], [])
        self.assertIsNone(s["fire_rate"])
        self.assertIsNone(s["gap_p95"])
        self.assertIsNone(s["p_upper"])

    def test_selfcheck_verdict(self):
        s = {"F0": {"t2c_exceeds": 0.0625, "t2c_type_exceeds": 0.0},
             "F1": {"t2c_exceeds": 0.5, "t2c_type_exceeds": 0.125},
             "F2": {"t2c_exceeds": 0.9, "t2c_type_exceeds": 0.8}}
        v = m.selfcheck_verdict(s)
        self.assertFalse(v["t2c_calibrated"])
        self.assertTrue(v["t2c_type_calibrated"])
        self.assertEqual(v["stage2_primary"], "T2c_type")
        self.assertEqual(v["power_t2c"], 0.9)
        s["F1"]["t2c_exceeds"] = 0.0
        self.assertEqual(m.selfcheck_verdict(s)["stage2_primary"], "T2c")
        s["F1"]["t2c_exceeds"] = 0.1875
        s["F1"]["t2c_type_exceeds"] = 0.1875
        self.assertIsNone(m.selfcheck_verdict(s)["stage2_primary"])

    def test_finch_world(self):
        rng = np.random.default_rng(1)
        birds = m.finch_world(rng, n_ind=20)
        self.assertEqual(len(birds), 20)
        for _, songs in birds:
            self.assertGreaterEqual(len(songs), 1)
            for s in songs:
                self.assertTrue(6 <= len(s) <= 12)
                self.assertTrue(all(0 <= x < 114 for x in s))
        cyc = m.finch_world(rng, order="cycle", n_ind=20)
        for _, songs in cyc:
            r = m.repeat_rate(songs)
            self.assertTrue(math.isnan(r) or r == 0.0)

    def test_jsonable(self):
        o = {"a": np.float64(np.nan), "b": np.int64(3), "c": np.array([1.0, np.inf]),
             "d": np.bool_(True), "e": (1, "x")}
        self.assertEqual(m.jsonable(o), {"a": None, "b": 3, "c": [1.0, None],
                                         "d": True, "e": [1, "x"]})
        json.dumps(m.jsonable(o))

    def test_load_levels(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "birds.json")
        with open(p, "w") as fh:
            json.dump({"levels": {"2": [{"bird": "b1", "songs": [["a", "b"], ["a"]]}]}}, fh)
        self.assertEqual(m.load_levels(p), {"2": [("b1", [["a", "b"], ["a"]])]})


@unittest.skipUnless(_have_core(), "needs scipy and mi_decay.py")
class TestEndToEnd(unittest.TestCase):
    def test_run_level_small(self):
        rng = np.random.default_rng(3)
        birds = m.finch_world(rng, n_ind=30)
        r = m.run_level(birds, rng, n_perm=2, n_surr=3, tag="test")
        for k in ("describe", "T2a", "T2b", "T2c", "T2c_type"):
            self.assertIn(k, r)
        self.assertEqual(r["T2b"]["n"], 2)
        self.assertEqual(r["T2c"]["grade"], "UNRESOLVED")
        self.assertEqual(r["describe"]["n_birds"], 30)
        json.dumps(m.jsonable(r))


if __name__ == "__main__":
    unittest.main()
