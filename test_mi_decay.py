# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Unit tests for mi_decay.py (numpy only; the curve-fit test runs only where scipy is installed)."""
import math
import unittest

import numpy as np

import mi_decay as M

try:
    import scipy  # noqa: F401
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False

GAMMA = 0.5772156649015329


class TestEstimator(unittest.TestCase):
    def test_digamma_known_values(self):
        v = M.digamma([1.0, 0.5, 10.0, 3.0, 5.0])
        self.assertAlmostEqual(v[0], -GAMMA, places=9)
        self.assertAlmostEqual(v[1], -1.9635100260214235, places=9)
        self.assertAlmostEqual(v[2], 2.251752589066721, places=9)
        self.assertAlmostEqual(v[3], 1.5 - GAMMA, places=9)
        self.assertAlmostEqual(v[4], 1 + 1 / 2 + 1 / 3 + 1 / 4 - GAMMA, places=9)

    def test_entropy_estimator_formula(self):
        # counts 3 and 5: log2(8) - (3 psi(3) + 5 psi(5)) / 8
        exp = 3.0 - (3 * (1.5 - GAMMA) + 5 * (1 + 1 / 2 + 1 / 3 + 1 / 4 - GAMMA)) / 8
        self.assertAlmostEqual(M.est_entropy_counts([3, 5, 0]), exp, places=9)
        self.assertAlmostEqual(exp, 1.7126323316, places=8)
        self.assertTrue(math.isnan(M.est_entropy_counts([0, 0])))

    def test_mi_at_alternating(self):
        s = [np.array([0, 1, 0, 1, 0, 1], dtype=np.int64)]
        # d=1: a=[1,0,1,0,1], b=[0,1,0,1,0]; marginal and joint count multisets are all {2,3}
        h = M.est_entropy_counts([2, 3])
        self.assertAlmostEqual(M.mi_at(s, 1, 2), h, places=12)
        self.assertTrue(math.isnan(M.mi_at(s, 6, 2)))

    def test_shuffle_baseline_cancels_bias(self):
        rng = np.random.default_rng(1)
        mi, base = M.mi_curve([np.zeros(10, dtype=np.int64)], rng, distances=np.arange(1, 6))
        # a constant sequence: MI estimate equals the estimator's bias, identical after shuffling
        self.assertTrue(np.all(mi - base == 0.0))
        self.assertAlmostEqual(mi[0], math.log2(9) - float(M.digamma([9.0])[0]), places=9)


class TestFitHelpers(unittest.TestCase):
    def test_aicc(self):
        self.assertAlmostEqual(M.aicc(10, 3, 10.0), 10.0, places=12)
        self.assertTrue(math.isnan(M.aicc(5, 4, 1.0)))

    def test_rel_probs(self):
        w = M.rel_probs({"exponential": 10.0, "powerlaw": 12.0, "composite": 0.0})
        self.assertAlmostEqual(sum(w.values()), 1.0, places=12)
        self.assertGreater(w["composite"], 0.99)
        self.assertEqual(M.rel_probs({"exponential": float("nan")}), {})

    def test_too_few_points_never_fires(self):
        sig = np.full(100, -1.0)
        sig[:5] = 0.1
        out = M.fit_curve(M.DISTANCES, sig)
        self.assertEqual(out["n_points"], 5)
        self.assertFalse(out["fire_best"])
        self.assertFalse(out["fire_strong"])

    def test_model_values(self):
        x = np.array([1.0, 2.0])
        self.assertTrue(np.allclose(M.model_values("powerlaw", [2.0, -1.0, 0.5], x), [2.5, 1.5]))
        self.assertTrue(np.allclose(M.model_values("exponential", [1.0, 0.0, 1.0], x), [2.0, 2.0]))
        self.assertTrue(np.allclose(M.model_values("composite", [1.0, 0.0, 2.0, -1.0, 0.0], x),
                                    [3.0, 2.0]))

    @unittest.skipUnless(HAVE_SCIPY, "scipy not installed")
    def test_fit_finds_composite(self):
        x = M.DISTANCES.astype(float)
        rng = np.random.default_rng(3)
        y = (0.3 * np.exp(-0.3 * x) + 0.05 * x ** -0.7) * np.exp(0.01 * rng.standard_normal(len(x)))
        out = M.fit_curve(M.DISTANCES, y)
        self.assertEqual(out["n_points"], 100)
        self.assertEqual(out["best"], "composite")
        self.assertTrue(out["fire_strong"])


class TestGenerators(unittest.TestCase):
    def test_sparse_rows_and_groups(self):
        rng = np.random.default_rng(0)
        P = M.random_sparse_rows(rng, 6)
        self.assertTrue(np.allclose(P.sum(axis=1), 1.0))
        self.assertTrue(np.all((P > 0).sum(axis=1) == 3))
        G = M.group_chain(rng, 3, 4, 0.9)
        self.assertEqual(G.shape, (12, 12))
        self.assertTrue(np.allclose(G.sum(axis=1), 1.0))
        self.assertAlmostEqual(G[0, 4:].sum(), 0.1, places=12)
        self.assertTrue(M.strongly_connected(G))

    def test_strongly_connected(self):
        self.assertTrue(M.strongly_connected(np.array([[0, 1], [1, 0]])))
        self.assertFalse(M.strongly_connected(np.array([[1, 1], [0, 1]])))

    def test_simulate_deterministic_cycle(self):
        P = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
        s = M.simulate_chain(np.random.default_rng(5), P, 7, start=0)
        self.assertEqual(s.tolist(), [0, 1, 2, 0, 1, 2, 0])

    def test_lin_tegmark_length(self):
        rng = np.random.default_rng(2)
        Mx = M.balanced_matrix(rng, 5)
        s = M.lin_tegmark_sequence(rng, Mx, 6)
        self.assertEqual(len(s), 64)
        self.assertTrue(s.min() >= 0 and s.max() < 5)

    def test_lin_tegmark_deterministic_children(self):
        Mx = np.array([[0.0, 1.0], [1.0, 0.0]])
        s = M.lin_tegmark_sequence(np.random.default_rng(4), Mx, 3)
        # every symbol's two children are the other symbol: lengths 2, 4, 8, constant per level
        self.assertEqual(len(s), 8)
        self.assertEqual(len(set(s.tolist())), 1)

    def test_worlds_shapes(self):
        rng = np.random.default_rng(7)
        w4 = M.world_w4(rng, n_ind=20)
        self.assertEqual(len(w4), 20)
        self.assertTrue(all(len(s) >= 6 for s in w4))
        self.assertTrue(all(s.max() < 114 for s in w4))
        w3 = M.world_w3(rng, n_days=2, n_bouts=4)
        self.assertEqual(len(w3), 2)
        self.assertTrue(all(s.max() < 18 for s in w3))

    def test_verdict(self):
        base = {k: 0.0 for k, _ in M.SCENARIOS}
        base["W5_recursive_hierarchy"] = 0.9
        self.assertEqual(M.verdict(base)["verdict"], "CALIBRATED")
        self.assertTrue(M.verdict(base)["positive_control_ok"])
        r = dict(base, W2_pooled_individuals=0.5)
        self.assertEqual(M.verdict(r)["verdict"], "UNCALIBRATED_MULTI_TIMESCALE")
        r = dict(base, W0_plain_markov=0.3)
        self.assertEqual(M.verdict(r)["verdict"], "UNCALIBRATED_EVEN_PLAIN_MARKOV")
        r = dict(base, W3_bout_song_types=0.2)
        self.assertEqual(M.verdict(r)["verdict"], "MIXED")


if __name__ == "__main__":
    unittest.main()
