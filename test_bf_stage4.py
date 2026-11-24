# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Tests for bf_stage4.py. Pure-logic tests need numpy only; the end-to-end test needs scipy
and the registered stage-1 core (mi_decay.py) and is skipped without them."""
import hashlib
import io
import json
import math
import tarfile
import unittest

import numpy as np

import bf_stage4 as m


def _have_core():
    try:
        import scipy  # noqa: F401
        m._core()
        return True
    except Exception:  # noqa: BLE001
        return False


HDR = "onset_s,offset_s,label\n"


class TestLoader(unittest.TestCase):
    def test_parse_tar_name(self):
        self.assertEqual(m.parse_tar_name("sober.repo1.gy6or6.032212.wav.csv.tar.gz"),
                         ("gy6or6", "120322"))
        self.assertIsNone(m.parse_tar_name("sober.repo1.gy6or6.032212.cbin.not.mat.tar.gz"))
        self.assertIsNone(m.parse_tar_name("x.tar.gz"))

    def test_is_csv_member(self):
        self.assertTrue(m.is_csv_member("a/b/gy6or6_1.wav.csv"))
        self.assertFalse(m.is_csv_member("a/._gy6or6_1.wav.csv"))
        self.assertFalse(m.is_csv_member("__MACOSX/a/x.csv"))
        self.assertFalse(m.is_csv_member("a/x.wav"))

    def test_parse_simple_seq(self):
        labels, cols = m.parse_simple_seq(HDR + "0.5,0.6,b\n0.1,0.2,a\n0.9,1.0,\nx,1.1,c\n")
        self.assertEqual(labels, ["a", "b", "c"])
        self.assertEqual(cols, ["onset_s", "offset_s", "label"])
        labels, _ = m.parse_simple_seq("onset_s, offset_s, label\n0.1, 0.2, a\n")
        self.assertEqual(labels, ["a"])
        labels, cols = m.parse_simple_seq("start,stop,name\n1,2,a\n")
        self.assertIsNone(labels)
        self.assertEqual(cols, ["start", "stop", "name"])

    def test_build_days(self):
        per_tar = {"sober.repo1.b1.010212.wav.csv.tar.gz": {
            "z/f2.wav.csv": HDR + "0,1,c\n",
            "z/f1.wav.csv": HDR + "0,1,a\n1,2,b\n",
            "z/f3.wav.csv": HDR,
            "z/f4.wav.csv": "start,stop\n1,2\n"},
            "junk.tar.gz": {}}
        days, rep = m.build_days(per_tar)
        self.assertEqual(days, [("b1", "120102", [["a", "b"], ["c"]])])
        self.assertEqual(rep["n_csv"], 4)
        self.assertEqual(rep["n_empty"], 1)
        self.assertEqual(rep["n_bad_header"], 1)
        self.assertEqual(rep["unparsed_tars"], ["junk.tar.gz"])

    def test_encode_and_describe(self):
        days = [("b1", "d1", [["a", "b"], ["a"]]), ("b2", "d1", [["a"]])]
        cdays, n = m.encode_days(days)
        self.assertEqual(cdays, [("b1", "d1", [(0, 1), (0,)]), ("b2", "d1", [(2,)])])
        self.assertEqual(n, 3)
        d = m.describe(cdays)
        self.assertEqual(d["birds"]["b1"], {"days": 1, "bouts": 2, "syllables": 3, "symbols": 2,
                                            "mean_bout_len": 1.5})
        self.assertEqual(d["birds"]["b2"]["syllables"], 1)
        self.assertEqual((d["n_day_sequences"], d["n_bouts"], d["n_syllables"]), (2, 3, 4))

    def test_loader_gate(self):
        md5_ok = {f"t{i}": True for i in range(18)}
        rep = {"n_csv": 100, "n_bad_header": 1}
        desc = {"n_syllables": 20000,
                "birds": {b: {"days": 2, "bouts": 20} for b in m.BIRDS}}
        self.assertEqual(m.loader_gate(md5_ok, 18, rep, desc), [])
        self.assertEqual(len(m.loader_gate(md5_ok, 17, rep, desc)), 1)
        bad = dict(md5_ok, t3=False)
        self.assertEqual(len(m.loader_gate(bad, 18, rep, desc)), 1)
        self.assertEqual(len(m.loader_gate(md5_ok, 18, {"n_csv": 100, "n_bad_header": 2}, desc)), 1)
        small = {"n_syllables": 9999, "birds": {b: {"days": 2, "bouts": 20} for b in m.BIRDS[:3]}}
        self.assertEqual(len(m.loader_gate(md5_ok, 18, rep, small)), 2)

    def test_hashreader_and_tar_stream(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name, data in (("x/a.wav", b"\x00\x01" * 5000),
                               ("x/a.wav.csv", (HDR + "0,1,a\n").encode()),
                               ("x/._a.wav.csv", b"\x00\x05junk"),
                               ("x/b.wav.csv", (HDR + "0,1,b\n").encode())):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
        raw = buf.getvalue()
        texts, md5, n = m.read_csvs_from_stream(io.BytesIO(raw))
        self.assertEqual(sorted(texts), ["x/a.wav.csv", "x/b.wav.csv"])
        self.assertEqual(texts["x/b.wav.csv"], HDR + "0,1,b\n")
        self.assertEqual(md5, hashlib.md5(raw).hexdigest())
        self.assertEqual(n, len(raw))
        hr = m.HashReader(io.BytesIO(b"abcdef"))
        self.assertEqual(hr.read(2), b"ab")
        self.assertEqual(hr.read(), b"cdef")
        self.assertEqual(hr.md5.hexdigest(), hashlib.md5(b"abcdef").hexdigest())
        self.assertEqual(hr.n, 6)


class TestKGram(unittest.TestCase):
    def test_witten_bell_values(self):
        km = m.KGram([(0,)], 1, [0, 1])
        self.assertEqual(km.out, [0, 1, m.END])
        np.testing.assert_allclose(km.dist((m.START,)), [0.7, 0.1, 0.2])
        np.testing.assert_allclose(km.dist((0,)), [0.2, 0.1, 0.7])
        np.testing.assert_allclose(km.dist((1,)), [0.4, 0.2, 0.4])
        ll, n = km.loglik([(0,)])
        self.assertEqual(n, 2)
        self.assertAlmostEqual(ll, 2 * math.log(0.7))
        k0 = m.KGram([(0,)], 0, [0, 1])
        self.assertEqual(k0.start(), ())
        np.testing.assert_allclose(k0.dist(()), [0.4, 0.2, 0.4])

    def test_dist_sums_to_one(self):
        km = m.KGram([(0, 1, 0, 1), (0, 1), (2,)], 3, [0, 1, 2])
        for h in [(m.START,) * 3, (m.START, m.START, 0), (0, 1, 0), (2, 2, 2), (1, 0, 1)]:
            self.assertAlmostEqual(float(km.dist(h).sum()), 1.0)

    def test_choose_k(self):
        bouts = [(0, 0, 1), (1, 1, 0)] * 30
        best, scores = m.choose_k(bouts, [0, 1], k_grid=(1, 2, 3))
        self.assertGreaterEqual(best, 2)
        self.assertGreater(scores[2], scores[1])
        self.assertEqual(sorted(scores), [1, 2, 3])

    def test_sampling(self):
        rng = np.random.default_rng(0)
        km = m.KGram([(0, 1, 2)] * 10, 2, [0, 1, 2])
        for _ in range(30):
            b = km.sample_nonempty(rng, 6)
            self.assertTrue(1 <= len(b) <= 6)
            self.assertTrue(set(b) <= {0, 1, 2})

    def test_surrogates_and_sequences(self):
        rng = np.random.default_rng(1)
        cdays = [("b1", "d1", [(0, 1), (1, 0, 1)]), ("b1", "d2", [(0,)]),
                 ("b2", "d1", [(5, 6, 5)]), ("b2", "d2", [])]
        seqs = m.day_sequences(cdays)
        self.assertEqual([s.tolist() for s in seqs], [[0, 1, 1, 0, 1], [0], [5, 6, 5]])
        pb = m.permute_bouts(rng, cdays)
        for (b1, d1, x), (b2, d2, y) in zip(cdays, pb):
            self.assertEqual((b1, d1, sorted(x)), (b2, d2, sorted(y)))
        models, info, caps = m.fit_models(cdays, k_grid=(1, 2))
        self.assertEqual(sorted(models), ["b1", "b2"])
        self.assertEqual(caps, {"b1": 6, "b2": 6})
        self.assertIn(info["b1"]["k"], (1, 2))
        sur = m.kgram_surrogate(rng, cdays, models, caps)
        self.assertEqual([len(x[2]) for x in sur], [2, 1, 1, 0])
        for b, _, bouts in sur:
            allowed = {0, 1} if b == "b1" else {5, 6}
            for bt in bouts:
                self.assertTrue(1 <= len(bt) <= 6)
                self.assertTrue(set(bt) <= allowed)


class TestGrading(unittest.TestCase):
    def test_grade_null(self):
        gaps = [float(x) for x in range(100)]
        g = m.grade_null(95.0, [False] * 100, gaps)
        self.assertEqual(g["grade"], "EXCEEDS_FINITE_STATE")
        self.assertAlmostEqual(g["gap_p95"], 94.05)
        self.assertAlmostEqual(g["p_upper"], 6 / 101)
        self.assertEqual(m.grade_null(50.0, [True] * 100, gaps)["grade"], "FINITE_STATE_SUFFICES")
        self.assertEqual(m.grade_null(50.0, [False] * 100, gaps)["grade"], "UNRESOLVED")
        self.assertEqual(m.grade_null(None, [True] * 100, gaps)["grade"], "UNRESOLVED")
        few = [float(x) for x in range(10)] + [None] * 90
        self.assertEqual(m.grade_null(1000.0, [True] * 100, few)["grade"], "UNRESOLVED")

    def test_final_grade(self):
        self.assertEqual(m.final_grade("FINITE_STATE_SUFFICES", 0.5, False), "UNRESOLVED_UNCALIBRATED")
        self.assertEqual(m.final_grade("FINITE_STATE_SUFFICES", 0.5, True), "FINITE_STATE_SUFFICES")
        self.assertEqual(m.final_grade("EXCEEDS_FINITE_STATE", 0.01, True), "CROSS_BOUT_ORDER")
        self.assertEqual(m.final_grade("EXCEEDS_FINITE_STATE", 0.05, True), "CROSS_BOUT_ORDER")
        self.assertEqual(m.final_grade("EXCEEDS_FINITE_STATE", 0.3, True), "WITHIN_BOUT_EXCESS")
        self.assertEqual(m.final_grade("EXCEEDS_FINITE_STATE", None, True), "UNRESOLVED")
        self.assertEqual(m.final_grade("UNRESOLVED", 0.01, True), "UNRESOLVED")

    def test_selfcheck_verdict(self):
        s = {"S0": {"t4c_exceeds": 1 / 12, "cross_bout_order": 0.0},
             "S1": {"t4c_exceeds": 0.125, "cross_bout_order": 0.0},
             "S3": {"t4c_exceeds": 0.9, "cross_bout_order": 0.8},
             "S4": {"t4c_exceeds": 0.4, "cross_bout_order": 0.1}}
        v = m.selfcheck_verdict(s)
        self.assertTrue(v["t4c_calibrated"])
        self.assertEqual(v["power_S4_within_bout_hierarchy"], 0.4)
        self.assertEqual(v["cross_bout_label_S3"], 0.8)
        s["S1"]["t4c_exceeds"] = 2 / 12
        self.assertFalse(m.selfcheck_verdict(s)["t4c_calibrated"])

    def test_jsonable(self):
        o = {"a": np.float64(np.nan), "b": np.int64(3), "c": np.array([1.0, np.inf]),
             "d": np.bool_(True), "e": (1, "x")}
        self.assertEqual(m.jsonable(o), {"a": None, "b": 3, "c": [1.0, None], "d": True,
                                         "e": [1, "x"]})
        json.dumps(m.jsonable(o))


class TestSynthetic(unittest.TestCase):
    def test_worlds(self):
        limits = {"S0": 10, "S1": 10, "S3": 18, "S4": 5}
        for kind, lim in limits.items():
            rng = np.random.default_rng(0)
            days = m.synth_days(rng, kind, n_birds=2, n_days=2, bouts_per_day=5)
            self.assertEqual(len(days), 4)
            for bird, _, bouts in days:
                b = int(bird[1:])
                self.assertGreaterEqual(len(bouts), 1)
                for bt in bouts:
                    self.assertGreaterEqual(len(bt), 1)
                    self.assertTrue(all(18 * b <= w < 18 * b + lim for w in bt))
                    if kind == "S4":
                        self.assertEqual(len(bt), 32)


@unittest.skipUnless(_have_core(), "needs scipy and mi_decay.py")
class TestEndToEnd(unittest.TestCase):
    def test_analyse_small(self):
        rng = np.random.default_rng(3)
        cdays = m.synth_days(rng, "S0", n_birds=2, n_days=2, bouts_per_day=10)
        r = m.analyse(cdays, rng, n_perm=2, n_surr=3, tag="test")
        for k in ("T4a", "T4b", "T4c", "kgram"):
            self.assertIn(k, r)
        self.assertEqual(r["T4b"]["n"], 2)
        self.assertEqual(r["T4c"]["grade"], "UNRESOLVED")
        json.dumps(m.jsonable(r))


if __name__ == "__main__":
    unittest.main()
