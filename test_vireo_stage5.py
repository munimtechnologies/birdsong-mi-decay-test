# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Tests for vireo_stage5.py. Pure-logic tests need numpy and bf_stage4.py only; the end-to-end
test needs scipy and the registered stage-1 core (mi_decay.py) and is skipped without them."""
import io
import json
import unittest
import zipfile

import numpy as np

import vireo_stage5 as m


def _have_core():
    try:
        import scipy  # noqa: F401
        m.s4._core()
        return True
    except Exception:  # noqa: BLE001
        return False


LONG = '''File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 3
tiers? <exists>
size = 2
item []:
    item [1]:
        class = "IntervalTier"
        name = "phrases"
        xmin = 0
        xmax = 3
        intervals: size = 3
        intervals [1]:
            xmin = 0
            xmax = 1
            text = ""
        intervals [2]:
            xmin = 1
            xmax = 2
            text = "A""B"
        intervals [3]:
            xmin = 2
            xmax = 3
            text = ""
    item [2]:
        class = "TextTier"
        name = "notes"
        xmin = 0
        xmax = 3
        points: size = 1
        points [1]:
            number = 1.5
            mark = "x1"
'''

SHORT = ('File type = "ooTextFile"\nObject class = "TextGrid"\n\n0\n3\n<exists>\n2\n'
         '"IntervalTier"\n"phrases"\n0\n3\n3\n0\n1\n""\n1\n2\n"A""B"\n2\n3\n""\n'
         '"TextTier"\n"notes"\n0\n3\n1\n1.5\n"x1"\n')


def short_grid(intervals, first_class="IntervalTier"):
    end = intervals[-1][1]
    parts = ['File type = "ooTextFile"', 'Object class = "TextGrid"', '', '0', repr(float(end)),
             '<exists>', '1', '"%s"' % first_class, '"phrases"', '0', repr(float(end)),
             str(len(intervals))]
    for a, b, lab in intervals:
        if first_class == "IntervalTier":
            parts += [repr(float(a)), repr(float(b)), '"%s"' % lab]
        else:
            parts += [repr(float(a)), '"%s"' % lab]
    return "\n".join(parts) + "\n"


IV = [(0, 1, ""), (1, 2, "AA"), (2, 3, ""), (3, 70, ""), (70, 71, "BB"), (71, 72, " "),
      (72, 73, "CC"), (73, 74, "")]
IV2 = [(0, 1, ""), (1, 2, "AA"), (2, 62, ""), (62, 63, "BB"), (63, 64, "")]


class TestTextGrid(unittest.TestCase):
    def test_long_and_short_formats(self):
        a = m.parse_textgrid(LONG)
        b = m.parse_textgrid(SHORT)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 2)
        self.assertEqual(a[0]["class"], "IntervalTier")
        self.assertEqual(a[0]["name"], "phrases")
        self.assertEqual(a[0]["items"], [(0.0, 1.0, ""), (1.0, 2.0, 'A"B'), (2.0, 3.0, "")])
        self.assertEqual(a[1]["items"], [(1.5, 1.5, "x1")])
        self.assertEqual(m.recording_bouts(a), [['A"B']])

    def test_not_a_textgrid(self):
        with self.assertRaises(ValueError):
            m.parse_textgrid("garbage")
        with self.assertRaises(ValueError):
            m.parse_textgrid('File type = "ooTextFile"\nObject class = "Pitch"\n')
        with self.assertRaises(ValueError):
            m.parse_textgrid(SHORT[:60])

    def test_decode(self):
        self.assertEqual(m.decode(SHORT.encode("utf-16")), (SHORT, "utf-16"))
        self.assertEqual(m.decode(SHORT.encode("utf-8")), (SHORT, "utf-8"))
        self.assertEqual(m.decode(b"\xef\xbb\xbf" + SHORT.encode("utf-8"))[1], "utf-8-sig")
        self.assertEqual(m.decode(SHORT.encode("utf-16-le")), (SHORT, "utf-16-le"))
        self.assertEqual(m.decode(b"\xe9abc")[1], "latin-1")

    def test_recording_bouts(self):
        self.assertEqual(m.recording_bouts(m.parse_textgrid(short_grid(IV))),
                         [["AA"], ["BB", "CC"]])
        self.assertEqual(m.recording_bouts(m.parse_textgrid(short_grid(IV2))), [["AA", "BB"]])
        self.assertIsNone(m.recording_bouts(m.parse_textgrid(short_grid(IV[:2]))))
        pts = m.parse_textgrid(short_grid(IV, first_class="TextTier"))
        self.assertIsNone(m.recording_bouts(pts))
        self.assertIsNone(m.recording_bouts([]))

    def test_bird_and_day(self):
        self.assertEqual(m.bird_of("Textgrids/AGBk/2013-05-01_06-12-33-00.TextGrid"), "AGBk")
        self.assertEqual(m.bird_of("Textgrids/AGBk/2013/x.TextGrid"), "AGBk")
        self.assertEqual(m.bird_of("Textgrids/AGBk/2013-05-01/x.TextGrid"), "AGBk")
        self.assertEqual(m.bird_of("AGBk_20130501.TextGrid"), "AGBk")
        self.assertIsNone(m.bird_of("Textgrids/2013-05-01.TextGrid"))
        self.assertEqual(m.day_of("Textgrids/AGBk/2013-05-01_06-12-33-00.TextGrid"), "2013-05-01")
        self.assertEqual(m.day_of("AGBk_20140612_x.TextGrid"), "2014-06-12")
        self.assertEqual(m.day_of("Textgrids/AGBk/2013_05_02/x.TextGrid"), "2013-05-02")
        self.assertIsNone(m.day_of("AGBk_x.TextGrid"))
        self.assertIsNone(m.day_of("AGBk/0501/x.TextGrid"))
        self.assertIsNone(m.day_of(""))


class TestLoader(unittest.TestCase):
    def test_read_zip(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as z:
            z.writestr("c.TextGrid", SHORT)
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w") as z:
            z.writestr("Textgrids/AGBk/a.TextGrid", SHORT)
            z.writestr("__MACOSX/Textgrids/AGBk/._a.TextGrid", b"\x00\x05")
            z.writestr("Textgrids/._b.TextGrid", b"\x00\x05")
            z.writestr("Textgrids/README.txt", "hello")
            z.writestr("Textgrids/Meadow.zip", inner.getvalue())
        got = m.read_zip(outer.getvalue())
        self.assertEqual(sorted(got), ["Textgrids/AGBk/a.TextGrid", "Textgrids/Meadow/c.TextGrid"])
        self.assertEqual(got["Textgrids/Meadow/c.TextGrid"], SHORT.encode("utf-8"))

    def test_build_group_retain_encode(self):
        members = {
            "Textgrids/AGBk/2013-05-01_06-00-00-00.TextGrid": short_grid(IV).encode("utf-8"),
            "Textgrids/AGBk/2013-05-01_07-00-00-00.TextGrid": short_grid(IV2).encode("utf-16"),
            "Textgrids/Meadow/2014-06-02_05-00-00-00.TextGrid": short_grid(IV2).encode("utf-8"),
            "Textgrids/Meadow/notes.TextGrid": b"garbage",
            "Textgrids/?/2014-06-02_05-00-00-00.TextGrid": short_grid(IV2).encode("utf-8"),
            "Textgrids/Meadow/2014-06-03_05-00-00-00.TextGrid": short_grid(IV[:2]).encode("utf-8"),
        }
        recs, rep = m.build(members)
        self.assertEqual(rep["n_textgrid"], 6)
        self.assertEqual(rep["n_unparsed"], 1)
        self.assertEqual(rep["n_no_tier0"], 1)
        self.assertEqual(rep["n_question_bird"], 1)
        self.assertEqual(rep["n_dated"], 3)
        self.assertEqual(rep["encodings"]["utf-16"], 1)
        self.assertEqual(rep["tier0_names"], {"phrases": 4})
        self.assertEqual([(r["bird"], r["day"]) for r in recs],
                         [("AGBk", "2013-05-01"), ("AGBk", "2013-05-01"), ("Meadow", "2014-06-02")])
        days = m.group_days(recs, True)
        self.assertEqual(days, [("AGBk", "2013-05-01", [["AA"], ["BB", "CC"], ["AA", "BB"]]),
                                ("Meadow", "2014-06-02", [["AA", "BB"]])])
        by_rec = m.group_days(recs, False)
        self.assertEqual(len(by_rec), 3)
        self.assertEqual(by_rec[0][2], [["AA"], ["BB", "CC"]])
        undated = [dict(recs[0], day=None)] + recs[1:]
        self.assertEqual(len(m.group_days(undated, True)), 2)
        self.assertEqual(m.group_days(undated, True)[0][2], [["AA", "BB"]])
        kept, report = m.retain_birds(days, min_bouts=2, min_phrases=3)
        self.assertEqual([x[0] for x in kept], ["AGBk"])
        self.assertEqual(report, {"AGBk": {"bouts": 3, "phrases": 5, "kept": True},
                                  "Meadow": {"bouts": 1, "phrases": 2, "kept": False}})
        cdays, n = m.encode_shared([("AGBk", "d", [["AA"], ["BB", "CC"]]), ("Meadow", "d", [["BB"]])])
        self.assertEqual(cdays, [("AGBk", "d", [(0,), (1, 2)]), ("Meadow", "d", [(1,)])])
        self.assertEqual(n, 3)

    def test_loader_gate(self):
        rep = {"n_textgrid": 200, "n_unparsed": 5, "n_no_tier0": 5}
        desc = {"n_syllables": 40000, "birds": {f"b{i}": {} for i in range(14)}}
        self.assertEqual(m.loader_gate(True, rep, desc), [])
        self.assertEqual(len(m.loader_gate(False, rep, desc)), 1)
        self.assertEqual(len(m.loader_gate(True, dict(rep, n_textgrid=100), desc)), 1)
        self.assertEqual(m.loader_gate(True, dict(rep, n_unparsed=15), desc), [])
        self.assertEqual(len(m.loader_gate(True, dict(rep, n_unparsed=16), desc)), 1)
        few = {"n_syllables": 40000, "birds": {f"b{i}": {} for i in range(9)}}
        many = {"n_syllables": 40000, "birds": {f"b{i}": {} for i in range(21)}}
        self.assertEqual(len(m.loader_gate(True, rep, few)), 1)
        self.assertEqual(len(m.loader_gate(True, rep, many)), 1)
        self.assertEqual(len(m.loader_gate(True, rep, dict(desc, n_syllables=29999))), 1)
        self.assertEqual(len(m.loader_gate(True, {"n_textgrid": 0, "n_unparsed": 0,
                                                  "n_no_tier0": 0}, desc)), 2)


class TestSynthetic(unittest.TestCase):
    def test_worlds(self):
        for kind in m.KINDS:
            rng = np.random.default_rng(0)
            days = m.synth_vireo(rng, kind, n_birds=2, n_days=2, bouts_per_day=3)
            self.assertEqual(len(days), 4)
            for _, _, bouts in days:
                self.assertGreaterEqual(len(bouts), 1)
                for bt in bouts:
                    self.assertGreaterEqual(len(bt), 1)
                    self.assertTrue(all(0 <= w < m.N_POP for w in bt))
                    if kind == "S4":
                        self.assertEqual(len(bt), 128)

    def test_chain_uses_overrides(self):
        rng = np.random.default_rng(2)
        c = m.ChainVireo(rng, n=10, p_over=1.0)
        self.assertEqual(len(c.over), 100)
        c0 = m.ChainVireo(rng, n=10, p_over=0.0)
        self.assertEqual(len(c0.over), 0)
        b = c0.bout(rng, cap=50)
        self.assertTrue(1 <= len(b) <= 50)
        self.assertTrue(set(b) <= set(int(s) for s in c0.syms))


class TestGrading(unittest.TestCase):
    ST = {"T4a": {"fire_strong": True}, "T4b": {"fire_rate": 0.6, "p_upper": 0.3},
          "T4c": {"grade": "FINITE_STATE_SUFFICES"},
          "kgram": {"a": {"k": 1}, "b": {"k": 2}, "c": {"k": 2}, "d": {"k": 4}}}
    SC = {"verdict": {"t4c_calibrated": True, "power_S4_within_bout_hierarchy": 0.5}}

    def test_predictions(self):
        g = m.predictions(self.ST, self.SC, {"loader_ok": True})
        self.assertEqual(g["grade"], "FINITE_STATE_SUFFICES")
        for key in ("V1_T5a_fires", "V2_k_le2_in_75pct", "V3_selfcheck_calibrated",
                    "V4_T5b_majority", "V5_finite_state_suffices", "V6_S4_power_ge_half",
                    "V7_loader_ok"):
            self.assertTrue(g[key], key)
        self.assertEqual(g["k_per_bird"], {"a": 1, "b": 2, "c": 2, "d": 4})
        st = dict(self.ST, kgram={"a": {"k": 3}, "b": {"k": 2}})
        self.assertFalse(m.predictions(st, self.SC, {"loader_ok": True})["V2_k_le2_in_75pct"])
        sc = {"verdict": {"t4c_calibrated": False, "power_S4_within_bout_hierarchy": 0.2}}
        g = m.predictions(self.ST, sc, {"loader_ok": True})
        self.assertEqual(g["grade"], "UNRESOLVED_UNCALIBRATED")
        self.assertFalse(g["V5_finite_state_suffices"])
        self.assertFalse(g["V6_S4_power_ge_half"])

    def test_stop_and_missing(self):
        g = m.predictions(None, None, {"loader_ok": False})
        self.assertEqual(g["grade"], "LOADER_STOP")
        self.assertFalse(g["V7_loader_ok"])
        self.assertEqual(m.predictions(None, None, None)["grade"], "LOADER_STOP")
        self.assertEqual(m.predictions(self.ST, None, {"loader_ok": True})["grade"],
                         "UNRESOLVED_MISSING_OUTPUT")
        json.dumps(m.s4.jsonable(g))


@unittest.skipUnless(_have_core(), "needs scipy and mi_decay.py")
class TestEndToEnd(unittest.TestCase):
    def test_analyse_small(self):
        rng = np.random.default_rng(3)
        cdays = m.synth_vireo(rng, "S0", n_birds=2, n_days=2, bouts_per_day=3)
        r = m.s4.analyse(cdays, rng, n_perm=2, n_surr=3, tag="test")
        for k in ("T4a", "T4b", "T4c", "kgram"):
            self.assertIn(k, r)
        self.assertEqual(r["T4c"]["grade"], "UNRESOLVED")
        json.dumps(m.s4.jsonable(r))


if __name__ == "__main__":
    unittest.main()
