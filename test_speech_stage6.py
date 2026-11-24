# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Unit tests of the pure parts of speech_stage6.py (numpy and stdlib only).
Run: python -m unittest -v test_speech_stage6
"""
import unittest

import speech_stage6 as s6

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
            text = "K"
        intervals [3]:
            xmin = 0.5
            xmax = 0.8
            text = "AE1"
        intervals [4]:
            xmin = 0.8
            xmax = 1.0
            text = "T"
        intervals [5]:
            xmin = 1.0
            xmax = 1.2
            text = "sp"
'''

SHORT = '''File type = "ooTextFile"
Object class = "TextGrid"

0
1.0
<exists>
2
"IntervalTier"
"words"
0
1.0
1
0
1.0
"DOG"
"IntervalTier"
"phones"
0
1.0
4
0.6
1.0
"G"
0
0.2
"D"
0.2
0.6
"AO1"
1.0
1.0
"spn"
'''


class TestParse(unittest.TestCase):
    def test_long(self):
        t = s6.parse_textgrid(LONG)
        self.assertEqual(sorted(t), ["phones", "words"])
        self.assertEqual(len(t["phones"]), 5)
        self.assertEqual(t["phones"][2], (0.5, 0.8, "AE1"))
        self.assertEqual(t["words"][1][2], "CAT")
        self.assertEqual(s6.utt_phones(LONG), ["K", "AE", "T"])

    def test_short(self):
        t = s6.parse_textgrid(SHORT)
        self.assertEqual(sorted(t), ["phones", "words"])
        self.assertEqual(t["words"], [(0.0, 1.0, "DOG")])
        self.assertEqual(len(t["phones"]), 4)
        # sorted by onset, stress removed, spoken noise dropped
        self.assertEqual(s6.utt_phones(SHORT), ["D", "AO", "G"])

    def test_no_phone_tier(self):
        txt = LONG.replace('name = "phones"', 'name = "other"')
        self.assertIsNone(s6.utt_phones(txt))

    def test_speaker_tier_name(self):
        txt = LONG.replace('name = "phones"', 'name = "1272 - phones"')
        self.assertEqual(s6.utt_phones(txt), ["K", "AE", "T"])

    def test_normalize(self):
        self.assertEqual(s6.normalize_phone("AH0"), "AH")
        self.assertEqual(s6.normalize_phone(" er1 "), "ER")
        self.assertIsNone(s6.normalize_phone("SIL"))
        self.assertIsNone(s6.normalize_phone(""))
        self.assertIsNone(s6.normalize_phone("spn"))

    def test_decode(self):
        self.assertEqual(s6.decode_bytes("ab".encode("utf-16")), "ab")
        self.assertEqual(s6.decode_bytes(b"\xef\xbb\xbfab"), "ab")
        self.assertEqual(s6.decode_bytes(b"ab"), "ab")


class TestNames(unittest.TestCase):
    def test_member(self):
        self.assertEqual(
            s6.parse_member_name("librispeech_alignments/dev-clean/1272/128104/1272-128104-0003.TextGrid"),
            ("dev-clean", "1272", "128104", 3))
        self.assertEqual(s6.parse_member_name("x\\test-clean\\61-70968-0000.textgrid"),
                         ("test-clean", "61", "70968", 0))
        self.assertIsNone(s6.parse_member_name("dev-clean/1272/128104/"))
        self.assertIsNone(s6.parse_member_name("1272-128104-0003.TextGrid"))
        self.assertIsNone(s6.parse_member_name("__MACOSX/dev-clean/._1272-128104-0003.TextGrid"))
        self.assertIsNone(s6.parse_member_name("dev-clean/1272-128104-0003.txt"))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.entries = [("84", "121123", 1, ["B", "A"]),
                        ("84", "121123", 0, ["A", "C"]),
                        ("7", "5", 0, ["C"]),
                        ("84", "99", 0, []),
                        ("84", "121550", 2, ["A"])]

    def test_build(self):
        cdays, n, labels = s6.build_cdays(self.entries)
        self.assertEqual(labels, ["A", "B", "C"])
        self.assertEqual(n, 3)
        # speakers in numeric order (7 before 84), chapters numeric, utterances by number,
        # the chapter with only an empty utterance is gone
        self.assertEqual(cdays, [("7", "5", [(2,)]),
                                 ("84", "121123", [(0, 2), (1, 0)]),
                                 ("84", "121550", [(0,)])])

    def test_utterance_days(self):
        cdays, _, _ = s6.build_cdays(self.entries)
        u = s6.utterance_days(cdays)
        self.assertEqual(u, [("7", "5#0", [(2,)]), ("84", "121123#0", [(0, 2)]),
                             ("84", "121123#1", [(1, 0)]), ("84", "121550#0", [(0,)])])

    def test_describe(self):
        cdays, _, _ = s6.build_cdays(self.entries)
        d = s6.describe6(cdays)
        self.assertEqual((d["speakers"], d["chapters"], d["utterances"], d["phones"]), (2, 3, 4, 6))
        self.assertAlmostEqual(d["mean_utt_len"], 1.5)
        self.assertAlmostEqual(d["mean_chapter_len"], 2.0)
        self.assertEqual(d["utts_longer_than_100"], 0)


def _ok_subset():
    return {"files": 2700, "bad": 5, "n_labels": 39,
            "describe": {"speakers": 40, "utterances": 2690, "phones": 200000}}


class TestGates(unittest.TestCase):
    def test_gate_pass(self):
        self.assertEqual(s6.loader_gate6(True, {"dev-clean": _ok_subset(),
                                                "test-clean": _ok_subset()}), [])

    def test_gate_fail(self):
        bad = _ok_subset()
        bad["bad"] = 28            # > 1% of 2700
        bad["n_labels"] = 70       # stress not removed, say
        f = s6.loader_gate6(False, {"dev-clean": bad})
        self.assertEqual(len(f), 4)  # md5, bad files, labels, test-clean missing
        self.assertTrue(f[0].startswith("zip md5"))
        self.assertTrue(any("test-clean: no TextGrid" in x for x in f))

    def test_selfcheck(self):
        v = s6.selfcheck_verdict6(["FINITE_STATE_SUFFICES"] * 7 + ["EXCEEDS_FINITE_STATE"])
        self.assertTrue(v["calibrated"])
        self.assertEqual(v["false_exceeds"], 1)
        self.assertAlmostEqual(v["suffices_rate"], 0.875)
        v = s6.selfcheck_verdict6(["UNRESOLVED"] * 6 + ["EXCEEDS_FINITE_STATE"] * 2)
        self.assertFalse(v["calibrated"])
        self.assertFalse(s6.selfcheck_verdict6([])["calibrated"])

    def test_headline(self):
        E, S, U = "EXCEEDS_FINITE_STATE", "FINITE_STATE_SUFFICES", "UNRESOLVED"
        self.assertEqual(s6.headline6(False, E, E), "UNRESOLVED_UNCALIBRATED")
        self.assertEqual(s6.headline6(True, E, E), "POSITIVE_CONTROL_PASSES")
        self.assertEqual(s6.headline6(True, E, S), "POSITIVE_CONTROL_FAILS")
        self.assertEqual(s6.headline6(True, S, U), "POSITIVE_CONTROL_FAILS")
        self.assertEqual(s6.headline6(True, E, U), "SPLIT_OR_UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
