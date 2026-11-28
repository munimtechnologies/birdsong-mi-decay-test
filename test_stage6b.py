# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Unit tests of stage6b.py (numpy and stdlib; the loader test also needs the pinned
speech_stage6.py that get_deps6b.py fetches, and is skipped without it).
Run: python -m unittest -v test_stage6b
"""
import io
import os
import tempfile
import unittest
import zipfile

import numpy as np

import stage6b as s6b

LONG = '''File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 1.2
tiers? <exists>
size = 2
item []:
    item [1]:
        class = "IntervalTier"
        name = "words"
        xmin = 0
        xmax = 1.2
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.3
            text = ""
        intervals [2]:
            xmin = 0.3
            xmax = 1.2
            text = "CAT"
    item [2]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 1.2
        intervals: size = 5
        intervals [1]:
            xmin = 0
            xmax = 0.3
            text = "sil"
        intervals [2]:
            xmin = 0.3
            xmax = 0.5
            text = "%s"
        intervals [3]:
            xmin = 0.5
            xmax = 0.8
            text = "%s"
        intervals [4]:
            xmin = 0.8
            xmax = 1.0
            text = "%s"
        intervals [5]:
            xmin = 1.0
            xmax = 1.2
            text = "sp"
'''


def _cdays():
    # 3 speakers x 2 chapters, chapter i of speaker s has (s + 1) * (i + 1) utterances of 10 phones
    out = []
    for s in range(3):
        for c in range(2):
            out.append((str(10 + s), str(100 + c), [tuple(range(10))] * ((s + 1) * (c + 1))))
    return out


class TestPure(unittest.TestCase):
    def test_sample_chapters(self):
        cd = _cdays()
        total = sum(len(u) for _, _, us in cd for u in us)
        for target in (1, 25, 60, 10 ** 9):
            rng = np.random.default_rng([1, target])
            sub, tot = s6b.sample_chapters(cd, target, rng)
            self.assertEqual(tot, sum(len(u) for _, _, us in sub for u in us))
            self.assertGreaterEqual(tot, min(target, total))
            keys = [(a, b) for a, b, _ in sub]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertEqual(keys, [k for k in [(a, b) for a, b, _ in cd] if k in keys])
            # minimal: dropping the last chapter drawn would go below the target
            if target <= total:
                self.assertLess(tot - min(sum(len(u) for u in us) for _, _, us in sub), target + 60)
        sub, tot = s6b.sample_chapters(cd, 10 ** 9, np.random.default_rng(0))
        self.assertEqual(len(sub), len(cd))
        self.assertEqual(tot, total)

    def test_sample_reproducible(self):
        cd = _cdays()
        a = s6b.sample_chapters(cd, 50, np.random.default_rng([5, 1, 0, 0]))
        b = s6b.sample_chapters(cd, 50, np.random.default_rng([5, 1, 0, 0]))
        self.assertEqual(a, b)

    def test_group_cdays(self):
        rows = [("20", "5", 2, (1, 2)), ("3", "7", 1, (3,)), ("20", "5", 0, (4,)),
                ("3", "7", 0, ()), ("20", "11", 0, (5,))]
        cd = s6b.group_cdays(rows)
        self.assertEqual([(a, b) for a, b, _ in cd], [("3", "7"), ("20", "5"), ("20", "11")])
        self.assertEqual(cd[0][2], [(3,)])
        self.assertEqual(cd[1][2], [(4,), (1, 2)])

    def test_gate(self):
        rd = {"files": 1000, "bad": 5, "n_labels": 39}
        desc = {"speakers": 251, "phones": 3000000}
        self.assertEqual(s6b.gate6b(True, rd, desc), [])
        self.assertEqual(len(s6b.gate6b(False, rd, desc)), 1)
        self.assertEqual(len(s6b.gate6b(True, dict(rd, bad=11), desc)), 1)
        self.assertEqual(len(s6b.gate6b(True, rd, dict(desc, speakers=199))), 1)
        self.assertEqual(len(s6b.gate6b(True, rd, dict(desc, phones=2499999))), 1)
        self.assertEqual(len(s6b.gate6b(True, dict(rd, n_labels=29), desc)), 1)
        self.assertEqual(len(s6b.gate6b(True, dict(rd, files=0), desc)), 1)

    def test_headline(self):
        h = s6b.headline6b
        c = {200000: 0, 500000: 0, 1000000: 0, 2000000: 0}
        self.assertEqual(h(False, c, None, None), "LOADER_STOP")
        self.assertEqual(h(True, {}, None, None), "UNRESOLVED_MISSING_OUTPUT")
        self.assertEqual(h(True, dict(c, **{}), False, False), "NEVER_FIRES")
        self.assertEqual(h(True, c, False, None), "NEVER_FIRES_TO_TRAIN_CLEAN_100")
        self.assertEqual(h(True, c, True, None), "FIRES_ABOVE_BIRD_SIZE")
        self.assertEqual(h(True, c, False, True), "FIRES_ABOVE_BIRD_SIZE")
        c2 = dict(c)
        c2[1000000] = 3
        self.assertEqual(h(True, c2, False, False), "FIRES_ABOVE_BIRD_SIZE")
        self.assertEqual(s6b.smallest_firing(c2, True, True), "1000000")
        c2[500000] = 2
        self.assertEqual(s6b.smallest_firing(c2, False, False), "1000000")
        self.assertEqual(s6b.smallest_firing(c, True, False), "all of train-clean-100")
        self.assertIsNone(s6b.smallest_firing(c, False, None))
        c3 = dict(c)
        c3[200000] = 1
        self.assertEqual(h(True, c3, False, False), "NEVER_FIRES")
        c3[200000] = 2
        self.assertEqual(h(True, c3, True, True), "MIXED")
        c3[200000] = 3
        self.assertEqual(h(True, c3, False, False), "FIRES_AT_BIRD_SIZE")

    def test_counts_forecasts_brier(self):
        rows = []
        for n in s6b.SIZES:
            for r in range(5):
                rows.append({"size": n, "draw": r, "fire_strong": (n >= 1000000 and r < 3),
                             "gap": (-3.0 if n == 200000 else 1.0 + r)})
        c = s6b.fire_counts(rows)
        self.assertEqual(c, {200000: 0, 500000: 0, 1000000: 3, 2000000: 3})
        self.assertAlmostEqual(s6b.mean_gap(rows, 200000), -3.0)
        self.assertAlmostEqual(s6b.mean_gap(rows, 2000000), 3.0)
        head = s6b.headline6b(True, c, True, None)
        self.assertEqual(head, "FIRES_ABOVE_BIRD_SIZE")
        out = s6b.forecast_outcomes(c, True, None, head, "UNRESOLVED", rows)
        self.assertEqual(out, {"Q1": True, "Q2": True, "Q3": True, "Q4": None, "Q5": True,
                               "Q6": False, "Q7": False, "Q8": True})
        exp = ((0.85 - 1) ** 2 + (0.35 - 1) ** 2 + (0.50 - 1) ** 2 + (0.55 - 1) ** 2
               + (0.30 - 0) ** 2 + (0.30 - 0) ** 2 + (0.80 - 1) ** 2) / 7
        self.assertAlmostEqual(s6b.brier(out), exp)
        self.assertIsNone(s6b.brier({}))
        self.assertEqual(s6b.fire_counts([])[200000], None)


class TestLoader(unittest.TestCase):
    def test_read_subset(self):
        try:
            s6 = s6b._s6()
        except ImportError:
            self.skipTest("speech_stage6.py not fetched")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("LibriSpeech/train-clean-100/19/198/19-198-0001.TextGrid",
                       LONG % ("K", "AE1", "T"))
            z.writestr("LibriSpeech/train-clean-100/19/198/19-198-0000.TextGrid",
                       LONG % ("D", "AO1", "G"))
            z.writestr("LibriSpeech/train-clean-100/103/1240/103-1240-0000.TextGrid",
                       LONG % ("K", "AO1", "T"))
            z.writestr("LibriSpeech/train-clean-100/103/1240/103-1240-0001.TextGrid",
                       LONG.replace('name = "phones"', 'name = "other"') % ("K", "AE1", "T"))
            z.writestr("LibriSpeech/dev-clean/84/121/84-121-0000.TextGrid",
                       LONG % ("S", "IY1", "Z"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.zip")
            with open(p, "wb") as fh:
                fh.write(buf.getvalue())
            cd, info = s6b.read_subset(p, "train-clean-100", s6)
        self.assertEqual(info["files"], 4)
        self.assertEqual(info["bad"], 1)
        self.assertEqual(info["labels"], ["AE", "AO", "D", "G", "K", "T"])
        self.assertEqual(info["n_labels"], 6)
        self.assertEqual([(a, b) for a, b, _ in cd], [("19", "198"), ("103", "1240")])
        # 19-198-0000 (D AO G) comes before 19-198-0001 (K AE T) in number order
        code = {}
        dag, kat = cd[0][2]
        self.assertEqual(len(dag), 3)
        self.assertEqual(len(set(dag) & set(kat)), 0)
        kot = cd[1][2][0]
        self.assertEqual(kot[0], kat[0])   # K
        self.assertEqual(kot[1], dag[1])   # AO
        self.assertEqual(kot[2], kat[2])   # T
        self.assertEqual(code, {})


if __name__ == "__main__":
    unittest.main()
