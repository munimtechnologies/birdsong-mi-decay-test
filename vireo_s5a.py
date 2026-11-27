# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 5 loader fix (AMENDMENT-5A-VIREO-LOADER.md).

The registered stage-5 code (vireo_stage5.py, unchanged) found no bird id and no date in the
Cassin's vireo TextGrids: each tier 0 is named after its recording. Hedley (2016, PLoS ONE
11:e0150822) lists the individual and the date of every recording in S1 Table. This module reads
that table with the standard library and replaces only the assignment of bird and day; T5a-T5c,
the self-check and the grade are the registered code.

Usage: python vireo_s5a.py stage5 --data-dir /data --out-dir /out [--perm 100 --surr 100 --seed S]
       python vireo_s5a.py selfcheck|grade ...   (passed to vireo_stage5.main unchanged)
"""
import datetime
import hashlib
import io
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, "/data/core5a", "/data/core"):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.append(_p)

import vireo_stage5 as vs  # noqa: E402  (registered stage-5 code, unchanged)

S1_URL = ("https://journals.plos.org/plosone/article/file?type=supplementary"
          "&id=10.1371/journal.pone.0150822.s002")
S1_NAME = "pone.0150822.s002.xlsx"
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
MIN_REC_MATCH = 0.90
MIN_FILLED = 0.90
BIRD_DISTINCT = (5, 40)
BIRD_HEADER_RE = re.compile(r"individual|bird|subject|identity|male|band|\bid\b|name", re.I)
EXT_RE = re.compile(r"\.(wav|textgrid|txt)$", re.I)
WHOLE_RE = re.compile(r"\d+(?:\.0+)?")
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
MDY_RE = re.compile(r"(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})(?!\d)")
EXCEL_EPOCH = datetime.date(1899, 12, 30)


# ------------------------------------------------------------------ xlsx reading (stdlib)

def _col_index(ref):
    letters = re.match(r"([A-Za-z]+)", ref or "")
    if not letters:
        return None
    n = 0
    for ch in letters.group(1).upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _text_of(el):
    return "".join(t.text or "" for t in el.iter() if _local(t.tag) == "t")


def _child(el, name):
    for x in el:
        if _local(x.tag) == name:
            return x
    return None


def parse_xlsx(raw):
    """Bytes of an .xlsx -> (sheet name, list of rows); each row is a list of cell strings ('' for
    empty), taken from the worksheet with the most non-empty cells. Tags are matched by local
    name, so transitional and strict OOXML namespaces both work."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = z.namelist()
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared = [_text_of(si) for si in root.iter() if _local(si.tag) == "si"]
    best = (None, [], -1)
    for name in sorted(n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml")):
        root = ET.fromstring(z.read(name))
        cells = {}
        rows_el = [x for x in root.iter() if _local(x.tag) == "row"]
        for r_i, row in enumerate(rows_el):
            r = int(row.get("r")) - 1 if row.get("r") else r_i
            col = -1
            for c in row:
                if _local(c.tag) != "c":
                    continue
                ci = _col_index(c.get("r"))
                col = ci if ci is not None else col + 1
                t = c.get("t")
                v = _child(c, "v")
                if t == "s" and v is not None and v.text is not None:
                    idx = int(float(v.text))
                    val = shared[idx] if 0 <= idx < len(shared) else ""
                elif t == "inlineStr":
                    is_ = _child(c, "is")
                    val = _text_of(is_) if is_ is not None else ""
                else:
                    val = v.text if v is not None and v.text is not None else ""
                val = val.strip()
                if val:
                    cells[(r, col)] = val
        if len(cells) > best[2]:
            if cells:
                nr = max(r for r, _ in cells) + 1
                nc = max(c for _, c in cells) + 1
                rows = [[cells.get((r, c), "") for c in range(nc)] for r in range(nr)]
            else:
                rows = []
            best = (name, rows, len(cells))
    return best[0], best[1]


# ------------------------------------------------------------------ keys, birds, days (pure)

def rec_key(value):
    """Recording key: the integer itself for a whole number, else the last run of digits after
    removing a .wav/.textgrid/.txt ending; None if there are no digits."""
    s = str(value or "").strip()
    if not s:
        return None
    if WHOLE_RE.fullmatch(s):
        return int(float(s))
    runs = re.findall(r"\d+", EXT_RE.sub("", s))
    return int(runs[-1]) if runs else None


def _is_number(s):
    return NUM_RE.fullmatch(s.strip()) is not None


def parse_day(value):
    """'YYYY-MM-DD' from an Excel serial date, an ISO-like date or a month/day/year date."""
    s = str(value or "").strip()
    if not s:
        return None
    if _is_number(s):
        x = float(s)
        if 20000 <= x <= 80000:
            return (EXCEL_EPOCH + datetime.timedelta(days=int(x))).isoformat()
        return None
    m = vs.DATE_RE.search(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = MDY_RE.search(s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        mo, d = (b, a) if a > 12 else (a, b)
        try:
            return datetime.date(y, mo, d).isoformat()
        except ValueError:
            return None
    return None


def s1_map(rows, keys, distinct=BIRD_DISTINCT):
    """rows of S1 Table, set of TextGrid keys -> ({key: (bird, day)}, report, failures)."""
    rep = {"n_rows": len(rows), "n_cols": max((len(r) for r in rows), default=0),
           "n_keys": len(keys)}
    fails = []
    ncol = rep["n_cols"]
    match = [sum(1 for r in rows if c < len(r) and rec_key(r[c]) in keys) for c in range(ncol)]
    rep["key_matches_by_column"] = match
    if not match or max(match) < MIN_REC_MATCH * max(len(keys), 1):
        fails.append("S1 recording column matched %d of %d TextGrids"
                     % (max(match) if match else 0, len(keys)))
        return {}, rep, fails
    rc = match.index(max(match))
    data, seen, dup = [], set(), 0
    first_row = None
    for i, r in enumerate(rows):
        k = rec_key(r[rc]) if rc < len(r) else None
        if k in keys:
            if first_row is None:
                first_row = i
            if k in seen:
                dup += 1
                continue
            seen.add(k)
            data.append((k, r))
    header = []
    for i in range(first_row - 1, -1, -1):
        if any(x for x in rows[i]):
            header = rows[i]
            break
    head = [header[c] if c < len(header) else "" for c in range(ncol)]
    rep.update({"recording_column": rc, "recording_header": head[rc], "data_rows": len(data),
                "duplicate_keys": dup, "headers": head})

    def col(c):
        return [r[c] if c < len(r) else "" for _, r in data]

    cands = []
    for c in range(ncol):
        if c == rc:
            continue
        vals = col(c)
        filled = [v for v in vals if v]
        if not data or len(filled) < MIN_FILLED * len(data):
            continue
        nd = len(set(filled))
        if distinct[0] <= nd <= distinct[1]:
            cands.append((c, nd, all(_is_number(v) for v in filled)))
    rep["bird_candidates"] = [[c, nd, num] for c, nd, num in cands]
    pref = [c for c, _, _ in cands if BIRD_HEADER_RE.search(head[c] or "")]
    plain = [c for c, _, num in cands if not num]
    if pref:
        bc = pref[0]
    elif plain:
        bc = plain[0]
    else:
        fails.append("S1 has no bird column (%d candidates)" % len(cands))
        return {}, rep, fails
    date_cols = [c for c in range(ncol) if c != rc and "date" in (head[c] or "").lower()]
    dc = date_cols[0] if date_cols else None
    out = {}
    for k, r in data:
        bird = (r[bc] if bc < len(r) else "").strip() or None
        day = parse_day(r[dc]) if dc is not None and dc < len(r) else None
        out[k] = (bird, day)
    rep.update({"bird_column": bc, "bird_header": head[bc],
                "n_birds_distinct": len({b for b, _ in out.values() if b}),
                "date_column": dc, "date_header": head[dc] if dc is not None else None,
                "n_dated": sum(1 for _, d in out.values() if d)})
    return out, rep, fails


# ------------------------------------------------------------------ records

def build5a(members, rows):
    """{path: bytes} of TextGrids and the S1 rows -> (records, report, failures). Same records and
    report fields as vireo_stage5.build, with bird and day from S1 Table."""
    rep = {"n_textgrid": 0, "n_unparsed": 0, "n_no_tier0": 0, "n_no_bird": 0,
           "n_question_bird": 0, "n_dated": 0, "n_no_key": 0, "encodings": {},
           "unparsed_examples": []}
    items = []
    for name in sorted(members):
        rep["n_textgrid"] += 1
        text, enc = vs.decode(members[name])
        rep["encodings"][enc] = rep["encodings"].get(enc, 0) + 1
        try:
            tiers = vs.parse_textgrid(text)
        except ValueError as exc:
            rep["n_unparsed"] += 1
            if len(rep["unparsed_examples"]) < 5:
                rep["unparsed_examples"].append([name, str(exc)])
            continue
        bouts = vs.recording_bouts(tiers)
        if bouts is None:
            rep["n_no_tier0"] += 1
            continue
        base = name.replace("\\", "/").split("/")[-1]
        key = rec_key(tiers[0]["name"])
        if key is None:
            key = rec_key(base)
        if key is None:
            rep["n_no_key"] += 1
            continue
        items.append((name, key, bouts))
    keys = {k for _, k, _ in items}
    mapping, s1rep, fails = s1_map(rows, keys)
    rep["s1"] = s1rep
    recs = []
    for name, key, bouts in items:
        bird, day = mapping.get(key, (None, None))
        if not bird:
            rep["n_no_bird"] += 1
            continue
        if bird == "?":
            rep["n_question_bird"] += 1
            continue
        if day:
            rep["n_dated"] += 1
        recs.append({"name": name, "bird": bird, "day": day, "bouts": bouts})
    return recs, rep, fails


def fetch_s1(data_dir):
    root = os.path.join(data_dir, "vireo")
    os.makedirs(root, exist_ok=True)
    cache = os.path.join(root, S1_NAME)
    if os.path.exists(cache):
        with open(cache, "rb") as fh:
            raw = fh.read()
    else:
        raw = vs._get(S1_URL, 120)
        with open(cache, "wb") as fh:
            fh.write(raw)
    return raw, {"url": S1_URL, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def run_stage5a(data_dir, out_dir, seed, n_perm, n_surr):
    import numpy as np
    os.makedirs(out_dir, exist_ok=True)
    raw, readme, info = vs.fetch(data_dir)
    if readme is not None:
        with open(os.path.join(out_dir, "vireo_readme.txt"), "w", encoding="utf-8") as fh:
            fh.write(readme)
    s1_fail = []
    try:
        s1_raw, s1_info = fetch_s1(data_dir)
        sheet, rows = parse_xlsx(s1_raw)
        s1_info["sheet"] = sheet
    except Exception as exc:  # noqa: BLE001
        s1_info, rows = {"url": S1_URL, "error": str(exc)}, []
        s1_fail.append("S1 Table not read: %s" % exc)
    members = vs.read_zip(raw)
    recs, rep, fails = build5a(members, rows)
    use_dates = bool(recs) and rep["n_dated"] >= vs.MIN_DATED * len(recs)
    days = vs.group_days(recs, use_dates)
    days, birds_report = vs.retain_birds(days)
    cdays, n_sym = vs.encode_shared(days)
    desc = vs.s4.describe(cdays)
    fails = s1_fail + fails + vs.loader_gate(info["md5_ok"], rep, desc)
    report = {"amendment": "5A", "fetch": info, "s1_fetch": s1_info, "parse": rep,
              "n_records": len(recs), "grouping": "bird-day" if use_dates else "recording",
              "birds": birds_report, "describe": desc, "n_symbols": n_sym,
              "gate_failures": fails, "loader_ok": not fails}
    with open(os.path.join(out_dir, "load_report5.json"), "w") as fh:
        json.dump(vs.s4.jsonable(report), fh, indent=1)
    if fails:
        print("LOADER STOP", fails, flush=True)
        return None
    rng = np.random.default_rng(seed)
    res = vs.s4.analyse(cdays, rng, n_perm, n_surr, tag="CAVI")
    res["describe"] = desc
    res["grouping"] = report["grouping"]
    res["amendment"] = "5A"
    with open(os.path.join(out_dir, "stage5_results.json"), "w") as fh:
        json.dump(vs.s4.jsonable(res), fh, indent=1)
    return res


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "stage5":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--data-dir", required=True)
        ap.add_argument("--out-dir", required=True)
        ap.add_argument("--perm", type=int, default=vs.N_PERM)
        ap.add_argument("--surr", type=int, default=vs.N_SURR)
        ap.add_argument("--seed", type=int, default=20261124)
        a = ap.parse_args(argv)
        run_stage5a(a.data_dir, a.out_dir, a.seed, a.perm, a.surr)
        return 0
    rc = vs.main(argv)
    if argv and argv[0] == "grade":
        out_dir = argv[argv.index("--out-dir") + 1]
        mark_v7(out_dir)
    return rc


def mark_v7(out_dir):
    """The registered grade5 records whether THIS run's loader passed. Prediction V7 asked whether
    the loader passes on the FIRST run, which it did not (birdsong-mi-vireo5-v1, LOADER_STOP)."""
    p = os.path.join(out_dir, "grade5.json")
    if not os.path.exists(p):
        return
    with open(p) as fh:
        g = json.load(fh)
    g["V7_loader_passed_first_run"] = False
    g["amendment_5a_note"] = ("V7 is graded false: the first run (birdsong-mi-vireo5-v1) stopped "
                              "at the loader; V7_loader_ok refers to this run's loader "
                              "(AMENDMENT-5A-VIREO-LOADER.md).")
    with open(p, "w") as fh:
        json.dump(g, fh, indent=1)


if __name__ == "__main__":
    sys.exit(main())
