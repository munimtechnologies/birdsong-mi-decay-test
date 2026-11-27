# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Unit tests for the AMENDMENT-5A loader (synthetic workbook and TextGrids only; no real data).

Run (after gate_s5a.py has fetched the registered code): python -m unittest -v test_vireo_s5a
"""
import io
import unittest
import zipfile

import vireo_s5a as a

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _xlsx(rows):
    """rows: list of lists; str -> shared string (or inline when it starts with '!'), int/float ->
    number. Returns xlsx bytes with an empty second sheet."""
    shared, idx = [], {}
    xml_rows = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, v in enumerate(row):
            ref = "%s%d" % (chr(65 + c), r)
            if v is None:
                continue
            if isinstance(v, str) and v.startswith("!"):
                cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, v[1:]))
            elif isinstance(v, str):
                if v not in idx:
                    idx[v] = len(shared)
                    shared.append(v)
                cells.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, idx[v]))
            else:
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, v))
        xml_rows.append('<row r="%d">%s</row>' % (r, "".join(cells)))
    sst = '<sst xmlns="%s">%s</sst>' % (NS, "".join("<si><t>%s</t></si>" % s for s in shared))
    sheet = '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>' % (NS, "".join(xml_rows))
    empty = '<worksheet xmlns="%s"><sheetData/></worksheet>' % NS
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/worksheets/sheet2.xml", empty)
    return buf.getvalue()


def _grid(tier, labels_gaps):
    """Long-format TextGrid: tier name, list of (label, start, end)."""
    items = [("", 0.0, 1.0)] + labels_gaps
    end = items[-1][2]
    items.append(("", end, end + 1.0))
    lines = ['File type = "ooTextFile"', 'Object class = "TextGrid"', "", "xmin = 0",
             "xmax = %s" % (end + 1.0), "tiers? <exists>", "size = 1", "item []:", "    item [1]:",
             '        class = "IntervalTier"', '        name = "%s"' % tier, "        xmin = 0",
             "        xmax = %s" % (end + 1.0), "        intervals: size = %d" % len(items)]
    for i, (lab, x0, x1) in enumerate(items, start=1):
        lines += ["        intervals [%d]:" % i, "            xmin = %s" % x0,
                  "            xmax = %s" % x1, '            text = "%s"' % lab]
    return ("\n".join(lines) + "\n").encode("utf-8")


class TestKeysAndDays(unittest.TestCase):
    def test_rec_key(self):
        self.assertEqual(a.rec_key("Cavi1113"), 1113)
        self.assertEqual(a.rec_key("CAVI1113.wav"), 1113)
        self.assertEqual(a.rec_key("1113"), 1113)
        self.assertEqual(a.rec_key("1113.0"), 1113)
        self.assertEqual(a.rec_key("Cavi_2013_1113.TextGrid"), 1113)
        self.assertIsNone(a.rec_key("Gate"))
        self.assertIsNone(a.rec_key(""))

    def test_parse_day(self):
        self.assertEqual(a.parse_day("45000"), "2023-03-15")
        self.assertEqual(a.parse_day("45000.5"), "2023-03-15")
        self.assertEqual(a.parse_day("2014-05-20"), "2014-05-20")
        self.assertEqual(a.parse_day("5/20/2014"), "2014-05-20")
        self.assertEqual(a.parse_day("20/5/14"), "2014-05-20")
        self.assertIsNone(a.parse_day("12"))
        self.assertIsNone(a.parse_day("morning"))


class TestWorkbook(unittest.TestCase):
    def setUp(self):
        birds = ["RBO", "Gate", "Meadow", "Gully", "WGY", "RBO"]
        rows = [["Metadata for sound recordings"], [],
                ["Recording", "Individual", "Phrases", "Date", "Time"]]
        for i, b in enumerate(birds):
            date = 45000 + i if i % 2 == 0 else "5/%d/2014" % (20 + i)
            rows.append(["CAVI%d.wav" % (1113 + i), b if i != 4 else "!" + b, 100 + 7 * i,
                         date, "07:%02d" % i])
        rows.append(["CAVI1113.wav", "Dup", 1, 45000, "08:00"])
        self.raw = _xlsx(rows)

    def test_parse_xlsx_picks_full_sheet(self):
        name, rows = a.parse_xlsx(self.raw)
        self.assertEqual(name, "xl/worksheets/sheet1.xml")
        self.assertEqual(rows[2], ["Recording", "Individual", "Phrases", "Date", "Time"])
        self.assertEqual(rows[3][0], "CAVI1113.wav")
        self.assertEqual(rows[7][1], "WGY")  # inline string
        self.assertEqual(rows[3][2], "100")

    def test_s1_map(self):
        _, rows = a.parse_xlsx(self.raw)
        keys = {1113, 1114, 1115, 1116, 1117, 1118}
        out, rep, fails = a.s1_map(rows, keys)
        self.assertEqual(fails, [])
        self.assertEqual(rep["recording_column"], 0)
        self.assertEqual(rep["bird_column"], 1)
        self.assertEqual(rep["bird_header"], "Individual")
        self.assertEqual(rep["date_column"], 3)
        self.assertEqual(rep["duplicate_keys"], 1)
        self.assertEqual(rep["data_rows"], 6)
        self.assertEqual(rep["n_birds_distinct"], 5)
        self.assertEqual(out[1113], ("RBO", "2023-03-15"))
        self.assertEqual(out[1114], ("Gate", "2014-05-21"))
        self.assertEqual(out[1117], ("WGY", "2023-03-19"))
        self.assertEqual(rep["n_dated"], 6)

    def test_s1_map_stops_without_match(self):
        _, rows = a.parse_xlsx(self.raw)
        out, rep, fails = a.s1_map(rows, {2001, 2002, 2003})
        self.assertEqual(out, {})
        self.assertTrue(fails and fails[0].startswith("S1 recording column matched 0 of 3"))

    def test_build5a(self):
        _, rows = a.parse_xlsx(self.raw)
        members = {}
        for i in range(6):
            members["Textgrids/T%02d.TextGrid" % i] = _grid(
                "Cavi%d" % (1113 + i), [("AB", 1.0, 2.0), ("CD", 2.0, 3.0), ("", 3.0, 70.0),
                                        ("AB", 70.0, 71.0)])
        members["Textgrids/bad.TextGrid"] = b"not a textgrid"
        recs, rep, fails = a.build5a(members, rows)
        self.assertEqual(fails, [])
        self.assertEqual(rep["n_textgrid"], 7)
        self.assertEqual(rep["n_unparsed"], 1)
        self.assertEqual(len(recs), 6)
        self.assertEqual(rep["n_dated"], 6)
        r0 = [r for r in recs if r["name"].endswith("T00.TextGrid")][0]
        self.assertEqual(r0["bird"], "RBO")
        self.assertEqual(r0["day"], "2023-03-15")
        self.assertEqual(r0["bouts"], [["AB", "CD"], ["AB"]])
        days = a.vs.group_days(recs, True)
        self.assertEqual(len(days), 6)


if __name__ == "__main__":
    unittest.main()
