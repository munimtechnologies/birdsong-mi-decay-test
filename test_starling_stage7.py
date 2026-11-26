"""Tests for stage 7 (starling). Pure parts need numpy only; the audio and labelling tests run
only where vocalseg/librosa/scipy and umap/scikit-learn are installed (the job installs them and
checks the imports before this test runs). Apache-2.0, MV2, Munim, Inc. Made with AI agents."""
import datetime as dt
import importlib.util
import unittest

import numpy as np

import starling_stage7 as s7


def _has(*mods):
    try:
        return all(importlib.util.find_spec(m) is not None for m in mods)
    except Exception:  # noqa: BLE001
        return False


def _bf_ok():
    try:
        s7._bf()
        return True
    except Exception:  # noqa: BLE001
        return False


HAVE_BF = _bf_ok()
HAVE_SEG = _has("vocalseg", "librosa", "scipy")
HAVE_LAB = _has("umap", "sklearn")


def fake_final_grade(t4c, p, cal):
    if not cal:
        return "UNRESOLVED_UNCALIBRATED"
    if t4c == "FINITE_STATE_SUFFICES":
        return t4c
    if t4c == "EXCEEDS_FINITE_STATE" and p is not None:
        return "CROSS_BOUT_ORDER" if p <= 0.05 else "WITHIN_BOUT_EXCESS"
    return "UNRESOLVED"


class TestPure(unittest.TestCase):
    def test_parse_wav_name(self):
        self.assertEqual(s7.parse_wav_name("b1125/wavs/2018-03-03_07-02-26-180000.wav"),
                         ("b1125", dt.datetime(2018, 3, 3, 7, 2, 26, 180000)))
        self.assertEqual(s7.parse_wav_name("B338/wavs/2008-04-16_23-10-00-000000.wav"),
                         ("B338", dt.datetime(2008, 4, 16, 23, 10, 0, 0)))
        self.assertIsNone(s7.parse_wav_name("b1125/csv/2018-03-03_07-02-26-180000.csv"))
        self.assertIsNone(s7.parse_wav_name("__MACOSX/b1125/wavs/._2018-03-03_07-02-26-180000.wav"))
        self.assertIsNone(s7.parse_wav_name("b1125/wavs/2018-13-03_07-02-26-180000.wav"))

    def test_to_float(self):
        np.testing.assert_allclose(s7.to_float(np.array([0, 16384, -32768], dtype=np.int16)),
                                   [0.0, 0.5, -1.0])
        np.testing.assert_allclose(s7.to_float(np.array([[16384, 0], [0, 0]], dtype=np.int16)),
                                   [0.5, 0.0])
        np.testing.assert_allclose(s7.to_float(np.array([128, 0, 255], dtype=np.uint8)),
                                   [0.0, -1.0, 127.0 / 128.0])
        np.testing.assert_allclose(s7.to_float(np.array([0.25], dtype=np.float32)), [0.25])
        self.assertEqual(s7.to_float(np.array([1], dtype=np.int16)).dtype, np.float32)

    def test_chunk_bounds(self):
        self.assertEqual(s7.chunk_bounds(45, 1), [(0, 45)])
        self.assertEqual(s7.chunk_bounds(100, 1), [(0, 30), (30, 60), (60, 90), (90, 100)])
        self.assertEqual(s7.chunk_bounds(905, 10), [(0, 300), (300, 600), (600, 905)])

    def test_patch_vector(self):
        np.testing.assert_allclose(s7.patch_vector(np.ones((32, 10))), np.ones(1024))
        np.testing.assert_allclose(s7.patch_vector(np.zeros((32, 10))), np.zeros(1024))
        np.testing.assert_allclose(s7.patch_vector(np.ones((32, 1))), np.ones(1024))
        P = np.ones((32, 2))
        P[:, 1] = 1e-8
        v = s7.patch_vector(P)
        self.assertEqual(len(v), 1024)
        self.assertAlmostEqual(float(v[0]), 1.0, places=6)
        self.assertAlmostEqual(float(v[31]), 0.0, places=6)
        self.assertTrue(np.all((v >= 0) & (v <= 1)))

    def test_frame_span(self):
        self.assertEqual(s7.frame_span(0.0, 0.15, 1000, 3, 100), (0, 50))
        self.assertEqual(s7.frame_span(0.0, 0.15, 1000, 3, 40), (0, 40))
        self.assertEqual(s7.frame_span(10.0, 11.0, 1000, 3, 5), (4, 5))

    def test_build_bird_days(self):
        want = [("b", "d0", [(1, 2, 3), (4, 5)]), ("b", "d1", [(6,)])]
        self.assertEqual(s7.build_bird_days("b", [0, 1, 2, 20, 21, 86405], [1, 2, 3, 4, 5, 6]),
                         want)
        t = [21, 0, 86405, 2, 20, 1]
        lab = [5, 1, 6, 3, 4, 2]
        self.assertEqual(s7.build_bird_days("b", t, np.array(lab)), want)
        self.assertEqual(s7.build_bird_days("b", [0, 10, 20], [1, 2, 3]),
                         [("b", "d0", [(1, 2, 3)])])

    def test_design_of(self):
        cdays = [("a", "d0", [(1,), (2,)]), ("a", "d1", []), ("b", "d0", [(1,)] * 300)]
        self.assertEqual(s7.design_of(cdays), [("a", "d0", 2), ("b", "d0", 100)])
        many = [("c", "d%d" % i, [(1,)] * n) for i, n in enumerate([5, 1, 8, 2, 7, 3, 6, 4])]
        self.assertEqual(s7.design_of(many),
                         [("c", "d0", 5), ("c", "d2", 8), ("c", "d4", 7), ("c", "d5", 3),
                          ("c", "d6", 6), ("c", "d7", 4)])
        self.assertEqual(s7.design_of(many, cap=5, max_days=2), [("c", "d2", 5), ("c", "d4", 5)])

    def test_loader_gate7(self):
        per = {b: {"md5_ok": True, "n_wav": 100, "n_read": 95} for b in s7.BIRDS}
        desc = {"birds": {b: {"days": 2, "bouts": 20} for b in s7.BIRDS}, "n_syllables": 20000}
        self.assertEqual(s7.loader_gate7(per, desc), [])
        per2 = dict(per)
        per2[s7.BIRDS[0]] = {"md5_ok": True, "n_wav": 100, "n_read": 80}
        fails = s7.loader_gate7(per2, desc)
        self.assertEqual(len(fails), 1)
        self.assertIn(s7.BIRDS[0], fails[0])
        per3 = {b: v for b, v in per.items() if b != s7.BIRDS[1]}
        self.assertTrue(any(s7.BIRDS[1] in f for f in s7.loader_gate7(per3, desc)))
        desc2 = {"birds": desc["birds"], "n_syllables": 50}
        self.assertTrue(any("syllables" in f for f in s7.loader_gate7(per, desc2)))

    def test_labels_ok(self):
        good = {b: {"hdb_clusters": 6} for b in s7.BIRDS}
        self.assertTrue(s7.labels_ok(good))
        bad = dict(good)
        bad[s7.BIRDS[2]] = {"hdb_clusters": 3}
        self.assertFalse(s7.labels_ok(bad))

    def test_brier(self):
        self.assertAlmostEqual(s7.brier({"a": 0.8, "b": 0.4}, {"a": True, "b": False}), 0.1)

    def test_grade_from(self):
        prim = {"T4a": {"fire_strong": True, "gap": 10.0, "best": "composite"},
                "T4b": {"fire_rate": 0.9, "p_upper": 0.3},
                "T4c": {"grade": "FINITE_STATE_SUFFICES", "p_upper": 0.4},
                "kgram": {"b1": {"k": 3}, "b2": {"k": 4}, "b3": {"k": 3}, "b4": {"k": 1}}}
        km = {"T4a": {"fire_strong": True, "gap": 12.0, "best": "composite"},
              "T4b": {"fire_rate": 0.9, "p_upper": 0.3},
              "T4c": {"grade": "EXCEEDS_FINITE_STATE", "p_upper": 0.01},
              "kgram": {"b1": {"k": 2}}}
        sc = {"verdict": {"t4c_calibrated": True, "power_S4_within_bout_hierarchy": 1.0,
                          "exceeds_S3_cross_bout": 0.5}}
        lr = {"loader_ok": True, "primary_labels_ok": True}
        st = {"primary": prim, "kmeans": km}
        g = s7.grade_from(lr, sc, st, fake_final_grade)
        self.assertEqual(g["grade"], "FINITE_STATE_SUFFICES")
        self.assertEqual(g["grade_kmeans"], "WITHIN_BOUT_EXCESS")
        o = g["outcomes"]
        self.assertEqual([o[k] for k in sorted(o)],
                         [True, True, True, True, True, False, True, True])
        self.assertAlmostEqual(g["brier"], 0.158125)
        g2 = s7.grade_from({"loader_ok": True, "primary_labels_ok": False}, sc, st,
                           fake_final_grade)
        self.assertEqual(g2["grade"], "UNRESOLVED_LABELS")
        self.assertFalse(g2["outcomes"]["C5_finite_state_suffices"])
        self.assertFalse(g2["outcomes"]["C6_arms_agree"])
        self.assertEqual(s7.grade_from(None, sc, st, fake_final_grade)["grade"], "LOADER_STOP")
        self.assertEqual(s7.grade_from(lr, sc, None, fake_final_grade)["grade"],
                         "UNRESOLVED_MISSING_OUTPUT")
        sc2 = {"verdict": dict(sc["verdict"], t4c_calibrated=False)}
        self.assertEqual(s7.grade_from(lr, sc2, st, fake_final_grade)["grade"],
                         "UNRESOLVED_UNCALIBRATED")


@unittest.skipUnless(HAVE_BF, "bf_stage4.py not importable here")
class TestWithStage4(unittest.TestCase):
    def test_synth_design_matches_design(self):
        design = [("a", "d0", 5), ("a", "d1", 3), ("b", "d0", 4)]
        for kind in s7.KINDS:
            rng = np.random.default_rng(1)
            out = s7.synth_design(rng, kind, design)
            self.assertEqual([(b, d, len(x)) for b, d, x in out], design)
            self.assertTrue(all(0 <= w < 18 for x in out[:2] for bt in x[2] for w in bt))
            self.assertTrue(all(18 <= w < 36 for bt in out[2][2] for w in bt))

    def test_encode_and_grade_rule(self):
        bf = s7._bf()
        days = s7.build_bird_days("b1", [0, 1, 30, 31], [-1, 2, 2, -1])
        cdays, n = bf.encode_days(days)
        self.assertEqual(n, 2)
        self.assertEqual(cdays, [("b1", "d0", [(0, 1), (1, 0)])])
        self.assertEqual(bf.final_grade("FINITE_STATE_SUFFICES", 0.5, True),
                         fake_final_grade("FINITE_STATE_SUFFICES", 0.5, True))
        self.assertEqual(bf.final_grade("EXCEEDS_FINITE_STATE", 0.01, True), "CROSS_BOUT_ORDER")


@unittest.skipUnless(HAVE_SEG, "vocalseg/librosa/scipy not installed")
class TestAudio(unittest.TestCase):
    def test_segment_three_tones(self):
        rate = 44100
        rng = np.random.default_rng(3)
        y = 1e-7 * rng.standard_normal(int(2.1 * rate))
        t = np.arange(int(0.3 * rate)) / rate
        for k in range(3):
            a = int((0.3 + 0.6 * k) * rate)
            y[a:a + len(t)] += 0.5 * np.sin(2 * np.pi * 3000.0 * t)
        yf, ons, offs, n_chunks = s7.segment_wave(y.astype(np.float32), rate)
        self.assertEqual(n_chunks, 1)
        self.assertEqual(len(ons), 3)
        self.assertTrue(np.all(np.abs(ons - np.array([0.3, 0.9, 1.5])) < 0.03))
        self.assertTrue(np.all(np.abs(offs - np.array([0.6, 1.2, 1.8])) < 0.03))
        f = s7.syllable_features(yf, rate, ons, offs)
        self.assertEqual(f.shape, (3, 1024))
        self.assertTrue(np.all(np.isfinite(f)) and f.min() >= 0.0 and f.max() <= 1.0)


@unittest.skipUnless(HAVE_LAB, "umap/scikit-learn not installed")
class TestLabels(unittest.TestCase):
    def test_label_bird_blobs(self):
        rng = np.random.default_rng(5)
        centers = rng.random((3, 1024))
        X = np.vstack([c + 0.01 * rng.standard_normal((100, 1024)) for c in centers])
        hdb, km, info = s7.label_bird(X.astype(np.float32), seed=1)
        self.assertEqual(len(hdb), 300)
        self.assertEqual(len(km), 300)
        self.assertGreaterEqual(info["hdb_clusters"], 2)
        self.assertEqual(info["kmeans_k"], 30)
        self.assertEqual(info["pca_dim"], 50)


if __name__ == "__main__":
    unittest.main()
