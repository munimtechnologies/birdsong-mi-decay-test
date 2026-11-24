# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Tests for chimp_mi.py (numpy only; tests that need scipy are skipped without it)."""
import itertools
import math
import unittest

import numpy as np

import chimp_mi as cm

try:
    import scipy  # noqa: F401
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


class Estimator(unittest.TestCase):
    def test_psi_table(self):
        t = cm.psi_table(4)
        self.assertEqual(len(t), 5)
        self.assertAlmostEqual(t[1], -0.5772156649, places=9)
        self.assertAlmostEqual(t[2], 0.4227843351, places=9)
        self.assertAlmostEqual(t[3], 0.9227843351, places=9)
        self.assertEqual(t[0], 0.0)

    def test_entropy_two_by_two(self):
        # log2(4) - (2*psi(2) + 2*psi(2)) / 4 = 2 - psi(2)
        self.assertAlmostEqual(cm.est_entropy(np.array([2, 2]), cm.psi_table(5)), 1.5772156649, places=9)

    def test_condense(self):
        self.assertEqual(cm.condense([1, 1, 2, 2, 2, 1, 3, 3]).tolist(), [1, 2, 1, 3])
        self.assertEqual(cm.condense([]).tolist(), [])

    def test_alternating_profile(self):
        s = np.array([0, 1] * 50)
        prof = cm.mi_profile(s, np.random.default_rng(0), nperm=20, dmax=3)
        # d = 1: a has 50 zeros and 49 ones, joint cells (0,1) x50 and (1,0) x49, so MI = H(a)
        expect = cm.est_entropy(np.array([50, 49]), cm.psi_table(101))
        self.assertAlmostEqual(prof["mi"][0], expect, places=12)
        self.assertLess(prof["perm_mean"][0], prof["mi"][0])
        self.assertTrue(np.all(prof["perm_se"] >= 0))
        self.assertTrue(np.all(np.isfinite(prof["perm_q95"])))

    def test_missing_pairs_dropped(self):
        s = np.array([0, 1, -1, 0, 1, 0, 1, 0, 1, 0])
        prof = cm.mi_profile(s, np.random.default_rng(1), nperm=5, dmax=2)
        self.assertTrue(np.isfinite(prof["mi"][0]))


class Cuts(unittest.TestCase):
    def test_paper_cut(self):
        prof = {"mi": np.array([1.0, 1, 1, 1]), "perm_mean": np.array([0.0, 0, 2, 0]),
                "perm_se": np.zeros(4), "perm_q95": np.zeros(4)}
        self.assertEqual(cm.paper_cut(prof), (3, 2))
        prof2 = {"mi": np.array([1.0, 1]), "perm_mean": np.zeros(2), "perm_se": np.zeros(2),
                 "perm_q95": np.zeros(2)}
        self.assertEqual(cm.paper_cut(prof2), (2, 2))

    def test_a2_cut_and_range(self):
        prof = {"mi": np.array([3.0, 3, 1, 3]), "perm_q95": np.array([2.0, 2, 2, 2])}
        self.assertEqual(cm.a2_cut(prof), 2)
        prof = {"mi": np.array([1.0, 1, 0, 1, 0]), "perm_mean": np.zeros(5)}
        self.assertEqual(cm.positive_range(prof), 4)

    def test_aicc(self):
        self.assertAlmostEqual(cm.aicc(10, 3, 1.0), 10 * math.log(0.1) + 10.0, places=9)
        self.assertTrue(math.isnan(cm.aicc(5, 4, 1.0)))


class Generators(unittest.TestCase):
    def test_mle_transition(self):
        P = cm.mle_transition([0, 1, 0, 1, 1], 2)
        np.testing.assert_allclose(P, [[0.0, 1.0], [0.5, 0.5]])
        P = cm.mle_transition([0, 0, 1], 2)
        np.testing.assert_allclose(P, [[0.5, 0.5], [2 / 3, 1 / 3]])

    def test_forward_loglik_brute_force(self):
        pi = np.array([0.6, 0.4])
        A = np.array([[0.7, 0.3], [0.2, 0.8]])
        B = np.array([[0.9, 0.1], [0.3, 0.7]])
        obs = np.array([0, 1, 1])
        total = 0.0
        for path in itertools.product(range(2), repeat=3):
            p = pi[path[0]] * B[path[0], obs[0]]
            for t in range(1, 3):
                p *= A[path[t - 1], path[t]] * B[path[t], obs[t]]
            total += p
        ll, gamma, xi = cm.forward_backward(pi[None], A[None], B[None], obs)
        self.assertAlmostEqual(float(ll[0]), math.log(total), places=12)
        np.testing.assert_allclose(gamma.sum(axis=2), 1.0)
        self.assertAlmostEqual(float(xi.sum()), 2.0, places=12)

    def test_em_does_not_decrease(self):
        rng = np.random.default_rng(1)
        obs = rng.integers(0, 3, size=50)
        pi = rng.dirichlet(np.ones(2), size=2)
        A = rng.dirichlet(np.ones(2), size=(2, 2))
        B = rng.dirichlet(np.ones(3), size=(2, 2))
        ll0, pi, A, B = cm.em_step(pi, A, B, obs, 3)
        ll1 = cm.forward_backward(pi, A, B, obs)[0]
        self.assertTrue(np.all(ll1 >= ll0 - 1e-6))

    def test_hmm_fit_and_simulate(self):
        rng = np.random.default_rng(2)
        obs = np.array([0, 0, 1, 2, 2, 1, 0, 0, 1, 2] * 10)
        r = cm.hmm_fit(obs, 3, 2, rng, n_starts=2, max_iter=20)
        self.assertEqual(r["n_params"], 1 + 2 + 4)
        self.assertTrue(np.isfinite(r["bic"]))
        sim = cm.hmm_simulate(rng, r["A"], r["B"], 200)
        self.assertEqual(len(sim), 200)
        self.assertTrue(sim.min() >= 0 and sim.max() <= 2)

    def test_stationary(self):
        np.testing.assert_allclose(cm.stationary(np.array([[0.9, 0.1], [0.5, 0.5]])), [5 / 6, 1 / 6])

    def test_lin_tegmark_length(self):
        s = cm.lin_tegmark_n(np.random.default_rng(3), 5, 300)
        self.assertEqual(len(s), 300)
        self.assertTrue(s.min() >= 0 and s.max() <= 4)

    def test_encode(self):
        codes, cats = cm.encode(["b", "a", "NA", "b"])
        self.assertEqual(cats, ["a", "b"])
        self.assertEqual(codes.tolist(), [1, 0, -1, 1])


class Grading(unittest.TestCase):
    def test_verdict(self):
        self.assertEqual(cm.verdict(0.5, 0.0, 8), "CONTROL_FAILED")
        self.assertEqual(cm.verdict(0.9, 0.4, 0), "SIGNATURE_UNSAFE_AGAINST_HMM")
        self.assertEqual(cm.verdict(0.9, 0.05, 4), "HIERARCHY_SIGNATURE_SURVIVES_HMM")
        self.assertEqual(cm.verdict(0.9, 0.05, 3), "MIXED")
        self.assertEqual(cm.verdict(0.9, 0.2, 8), "MIXED")

    def test_c3(self):
        self.assertAlmostEqual(cm.c3_p(1.0, [0.5, 2.0, None, 1.0]), 0.6)
        self.assertEqual(cm.c3_p(None, [1.0]), 1.0)


@unittest.skipUnless(HAVE_SCIPY, "needs scipy")
class Fits(unittest.TestCase):
    def test_power_law_wins_on_power_law(self):
        d = np.arange(1, 31, dtype=float)
        y = 0.2 * d ** -0.8 * (1 + 0.02 * (-1) ** d)
        for v in cm.VARIANTS:
            f = cm.fit_curve(d, y, v)
            self.assertTrue(f["pl_win"], (v, f["aicc"]))

    def test_composite_nests_exponential(self):
        d = np.arange(1, 31, dtype=float)
        y = 0.5 * np.exp(-0.3 * d) * (1 + 0.02 * (-1) ** d)
        f = cm.fit_curve(d, y, "paper")
        a = f["aicc"]
        pen_c = 2 * 5 + 2 * 5 * 6 / (30 - 6)
        pen_e = 2 * 3 + 2 * 3 * 4 / (30 - 4)
        self.assertLessEqual(a["composite"] - pen_c, a["exponential"] - pen_e + 1e-9)
        self.assertNotEqual(f["best"], "powerlaw")

    def test_profile_smoke(self):
        rng = np.random.default_rng(4)
        P = cm.balanced_matrix(rng, 6)
        s = cm.simulate_chain(rng, P, 400, 0)
        out = cm.analyse_profile(cm.mi_profile(s, rng, nperm=50, dmax=20), keep_curve=True)
        self.assertTrue(1 <= out["index_max"] <= 20)
        self.assertIn("pl_win", out["paper"])
        self.assertIn("pl_win", out["a2"])
        self.assertEqual(len(out["curve"]["mi"]), 20)

    def test_their_upper(self):
        self.assertAlmostEqual(cm.their_upper(10.0), 17.0848, places=3)

    def test_grade_smoke(self):
        def fake(pl, margin, idx):
            r = {"pl_win": pl, "best": "powerlaw" if pl else "exponential", "margin": margin, "n_points": 5}
            return {"index_max": idx, "range_pos": idx, "paper": dict(r), "a2": dict(r)}
        slot = {"real": fake(True, 3.0, 20), "N1": [fake(False, -1.0, 5)] * 4,
                "N2": [fake(True, 1.0, 8), fake(False, -2.0, 4)] * 2, "P": [fake(True, 5.0, 30)] * 4}
        g = cm.grade({("fanle", "full"): slot, ("fanle", "condensed"): slot}, 4, {})
        rate = g["paper"]["median_pl_win_rate"]
        self.assertEqual((rate["N1"], rate["N2"], rate["P"]), (0.0, 0.5, 1.0))
        self.assertEqual(g["primary_verdict"], "SIGNATURE_UNSAFE_AGAINST_HMM")
        row = g["per_individual_version"]["fanle/full"]
        self.assertAlmostEqual(row["paper"]["C3_p"], 0.2)
        self.assertEqual(row["C4_share_N2"], 0.0)
        self.assertTrue(row["C4_real_exceeds"])
        self.assertEqual(row["C4b_share_N1_self"], 0.0)
        self.assertEqual(g["ledger"]["chimp-mi-plwin-vs-hmm"], {"worlds": 8, "hits": 4})


if __name__ == "__main__":
    unittest.main()
