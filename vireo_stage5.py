# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 5 (AMENDMENT-5-STAGE5-VIREO.md): does the composite
(exponential + power-law) MI-decay verdict that Sainburg et al. (2019, Nat Commun 10:3636) read as
hierarchy in Cassin's vireo song exceed what a per-bird FINITE-MEMORY syntax model produces when it
is given the same design (birds, days, bouts, sample size)?

Data: Hedley (2016, PLoS ONE 11:e0150822), figshare 3081814 v1 (CC BY 4.0), Textgrids.zip: Praat
TextGrids of phrase-type labels from 14 wild males. The zip's md5 is checked against figshare's
own API at run time. Loader rules follow Sainburg et al.'s public code (prep_CAVI_CATH): tier 0,
first and last interval dropped, bouts split at silent intervals longer than 60 s, bouts of one
bird and day joined in time order.

Tests (registered): T5a composite verdict on the real pooled curve; T5b the same after permuting
bout order within days; T5c per-bird k-gram (k 1..8 by 5-fold held-out log-likelihood) with
independent bouts. In the JSON outputs these keep the stage-4 names T4a, T4b and T4c because the
analysis is the registered stage-4 code (bf_stage4.py, pinned by git blob). A vireo-shaped
self-check (S0, S1, S3, S4) runs in the same job before any grade counts.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

import numpy as np

DEPS_FALLBACK = "/data/core"


def _s4():
    try:
        import bf_stage4  # noqa: F401
    except ImportError:
        if os.path.isdir(DEPS_FALLBACK) and DEPS_FALLBACK not in sys.path:
            sys.path.insert(0, DEPS_FALLBACK)
        import bf_stage4  # noqa: F401
    return sys.modules["bf_stage4"]


s4 = _s4()

ARTICLE_API = "https://api.figshare.com/v2/articles/3081814"
ZIP_NAME = "Textgrids.zip"
README_NAME = "Textgrids ReadMe.txt"
UA = {"User-Agent": "mv2-research-job/1.0"}

ISI_THRESH = 60.0
MIN_GRIDS = 150
BIRDS_MIN, BIRDS_MAX = 10, 20
MIN_PHRASES = 30000
MIN_BIRD_BOUTS = 5
MIN_BIRD_PHRASES = 300
MIN_TIER_OK = 0.90
MIN_DATED = 0.90
N_PERM = 100
N_SURR = 100
N_POP = 126

# ------------------------------------------------------------------ TextGrid parsing (pure)

TOKEN_RE = re.compile(r'"((?:[^"]|"")*)"|\[\s*\d*\s*\]|(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)')
DATE_RE = re.compile(r"(?<!\d)(19\d\d|20\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])")


def decode(b):
    """Bytes of a TextGrid -> (text, encoding name)."""
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace"), "utf-16"
    if b[:3] == b"\xef\xbb\xbf":
        return b[3:].decode("utf-8", "replace"), "utf-8-sig"
    if b"\x00" in b[:200]:
        return b.decode("utf-16-le", "replace"), "utf-16-le"
    try:
        return b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return b.decode("latin-1"), "latin-1"


def tokens(text):
    """Praat text-file tokens: ('s', string) and ('n', number); bracketed indices such as
    'item [1]:' are skipped, so the long and the short TextGrid formats give the same stream."""
    out = []
    for m in TOKEN_RE.finditer(text):
        if m.group(1) is not None:
            out.append(("s", m.group(1).replace('""', '"')))
        elif m.group(2) is not None:
            out.append(("n", float(m.group(2))))
    return out


def parse_textgrid(text):
    """-> list of tiers {'class', 'name', 'items'}; interval items are (xmin, xmax, text), point
    items (time, time, mark). Raises ValueError on anything that is not a text TextGrid."""
    t = tokens(text)
    pos = [0]

    def take(kind):
        i = pos[0]
        if i >= len(t) or t[i][0] != kind:
            raise ValueError(f"token {i}: expected {kind}")
        pos[0] = i + 1
        return t[i][1]

    if take("s") != "ooTextFile":
        raise ValueError("not ooTextFile")
    if take("s") != "TextGrid":
        raise ValueError("not a TextGrid")
    take("n")
    take("n")
    tiers = []
    for _ in range(int(take("n"))):
        cls = take("s")
        name = take("s")
        take("n")
        take("n")
        items = []
        for _ in range(int(take("n"))):
            if cls == "IntervalTier":
                a = take("n")
                b = take("n")
                items.append((a, b, take("s")))
            else:
                a = take("n")
                items.append((a, a, take("s")))
        tiers.append({"class": cls, "name": name, "items": items})
    return tiers


def recording_bouts(tiers, isi=ISI_THRESH):
    """Sainburg et al.'s rule: tier 0 must be an interval tier with >= 3 intervals; its first and
    last intervals are dropped; a blank interval longer than `isi` seconds ends a bout; bouts are
    the non-blank labels (stripped). None if tier 0 is unusable."""
    if not tiers or tiers[0]["class"] != "IntervalTier" or len(tiers[0]["items"]) < 3:
        return None
    bouts, cur = [], []
    for a, b, lab in tiers[0]["items"][1:-1]:
        lab = lab.strip()
        if lab:
            cur.append(lab)
        elif (b - a) > isi:
            if cur:
                bouts.append(cur)
            cur = []
    if cur:
        bouts.append(cur)
    return bouts


def _skip_dir(p):
    return p.lower() in ("textgrids", "textgrid") or p.isdigit() or DATE_RE.search(p) is not None


def bird_of(path):
    """Bird id: the deepest folder that is not 'TextGrids', a number or a date; for a file at the
    top level, the leading letters-and-digits of the file name. None if neither exists."""
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    dirs = [p for p in parts[:-1] if not _skip_dir(p)]
    if dirs:
        return dirs[-1]
    m = re.match(r"([A-Za-z][A-Za-z0-9]*)", parts[-1]) if parts else None
    return m.group(1) if m else None


def day_of(path):
    """'YYYY-MM-DD' from the file name, else from the folders; None if no date is found."""
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if not parts:
        return None
    for p in [parts[-1]] + parts[:-1][::-1]:
        m = DATE_RE.search(p)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def is_grid(name):
    base = name.replace("\\", "/").split("/")[-1]
    return base.lower().endswith(".textgrid") and not base.startswith("._") and "__MACOSX" not in name


def read_zip(raw, prefix="", depth=0):
    """{path: bytes} of every TextGrid in the zip (and in zips inside it, one level deep; an inner
    'X.zip' becomes the folder 'X/'). macOS '._' and __MACOSX entries are skipped."""
    out = {}
    z = zipfile.ZipFile(io.BytesIO(raw))
    for n in z.namelist():
        if "__MACOSX" in n:
            continue
        base = n.replace("\\", "/").split("/")[-1]
        if base.startswith("._"):
            continue
        if is_grid(n):
            out[prefix + n] = z.read(n)
        elif base.lower().endswith(".zip") and depth < 1:
            out.update(read_zip(z.read(n), prefix + n[:-4] + "/", depth + 1))
    return out


def build(members):
    """{path: bytes} -> (records sorted by path, report). A record is one recording:
    {'name', 'bird', 'day', 'bouts'}."""
    rep = {"n_textgrid": 0, "n_unparsed": 0, "n_no_tier0": 0, "n_no_bird": 0,
           "n_question_bird": 0, "n_dated": 0, "encodings": {}, "tier0_names": {},
           "unparsed_examples": []}
    recs = []
    for name in sorted(members):
        rep["n_textgrid"] += 1
        text, enc = decode(members[name])
        rep["encodings"][enc] = rep["encodings"].get(enc, 0) + 1
        try:
            tiers = parse_textgrid(text)
        except ValueError as exc:
            rep["n_unparsed"] += 1
            if len(rep["unparsed_examples"]) < 5:
                rep["unparsed_examples"].append([name, str(exc)])
            continue
        bouts = recording_bouts(tiers)
        if bouts is None:
            rep["n_no_tier0"] += 1
            continue
        t0 = tiers[0]["name"]
        rep["tier0_names"][t0] = rep["tier0_names"].get(t0, 0) + 1
        bird = bird_of(name)
        if not bird:
            rep["n_no_bird"] += 1
            continue
        if bird == "?":
            rep["n_question_bird"] += 1
            continue
        day = day_of(name)
        if day:
            rep["n_dated"] += 1
        recs.append({"name": name, "bird": bird, "day": day, "bouts": bouts})
    return recs, rep


def group_days(recs, use_dates):
    """Day sequences: bouts of one bird and day joined in path (time) order; with use_dates False
    every recording is its own group (Hedley's unit). Undated recordings are left out when
    use_dates is True."""
    groups = {}
    for r in sorted(recs, key=lambda x: x["name"]):
        if use_dates and r["day"] is None:
            continue
        key = (r["bird"], r["day"] if use_dates else r["name"])
        groups.setdefault(key, []).extend(list(b) for b in r["bouts"])
    return [(b, d, groups[(b, d)]) for (b, d) in sorted(groups)]


def retain_birds(days, min_bouts=MIN_BIRD_BOUTS, min_phrases=MIN_BIRD_PHRASES):
    tot = {}
    for b, _, bouts in days:
        t = tot.setdefault(b, [0, 0])
        t[0] += len(bouts)
        t[1] += sum(len(x) for x in bouts)
    keep = {b for b, (nb, nph) in tot.items() if nb >= min_bouts and nph >= min_phrases}
    report = {b: {"bouts": v[0], "phrases": v[1], "kept": b in keep} for b, v in sorted(tot.items())}
    return [x for x in days if x[0] in keep], report


def encode_shared(days):
    """Labels -> ints. Vireo phrase types are population-wide two-letter codes (Hedley 2016), so
    one symbol per label, shared across birds, as in Sainburg et al."""
    index, out = {}, []
    for bird, day, bouts in days:
        cb = []
        for b in bouts:
            arr = tuple(index.setdefault(lab, len(index)) for lab in b)
            if arr:
                cb.append(arr)
        out.append((bird, day, cb))
    return out, len(index)


def loader_gate(md5_ok, rep, desc):
    fails = []
    if not md5_ok:
        fails.append("md5 mismatch")
    n = rep["n_textgrid"]
    if n < MIN_GRIDS:
        fails.append(f"textgrids {n} < {MIN_GRIDS}")
    ok = n - rep["n_unparsed"] - rep["n_no_tier0"]
    if n == 0 or ok < MIN_TIER_OK * n:
        fails.append(f"usable tier 0 in {ok} of {n}")
    nb = len(desc["birds"])
    if not BIRDS_MIN <= nb <= BIRDS_MAX:
        fails.append(f"birds kept {nb} not in [{BIRDS_MIN}, {BIRDS_MAX}]")
    if desc["n_syllables"] < MIN_PHRASES:
        fails.append(f"phrases {desc['n_syllables']} < {MIN_PHRASES}")
    return fails


# ------------------------------------------------------------------ vireo-shaped synthetic worlds

class ChainVireo:
    """S0 in-class: first-order sparse chain over n of the 126 population types (0.7/0.2/0.1 on
    three next types), with a second-order override (its own three next types) on a share p_over
    of (previous, current) pairs: 'between first and second order' as Hedley found."""

    def __init__(self, rng, n=50, p_over=0.2, p_end=0.005):
        self.syms = rng.choice(N_POP, size=n, replace=False)
        self.n, self.p_end = n, p_end
        self.first = s4._rows3(rng, n + 1, n)
        mask = rng.random((n, n)) < p_over
        self.over = {(int(x), int(y)): rng.choice(n, size=3, replace=False)
                     for x, y in zip(*np.nonzero(mask))}

    def bout(self, rng, cap=3000):
        x, y, out = -1, self.n, []
        while len(out) < cap:
            if out and rng.random() < self.p_end:
                break
            row = self.over.get((x, y))
            if row is None:
                row = self.first[y]
            w = s4._pick3(rng, row)
            out.append(int(self.syms[w]))
            x, y = y, w
        return out


class HMMVireo:
    """S1 finite-state outside the k-gram class: 10 hidden states with sparse first-order
    transitions, each emitting uniformly one of its own 5 of the bird's 50 types (overlaps allowed)."""

    def __init__(self, rng, n=50, n_states=10, per_state=5, p_end=0.005):
        self.syms = rng.choice(N_POP, size=n, replace=False)
        self.rows = s4._rows3(rng, n_states, n_states)
        self.emit = [rng.choice(n, size=per_state, replace=False) for _ in range(n_states)]
        self.n_states, self.p_end = n_states, p_end

    def bout(self, rng, cap=3000):
        s, out = int(rng.integers(self.n_states)), []
        while len(out) < cap:
            if out and rng.random() < self.p_end:
                break
            e = self.emit[s]
            out.append(int(self.syms[int(e[int(rng.integers(len(e)))])]))
            s = s4._pick3(rng, self.rows[s])
        return out


class TypedVireo:
    """S3 cross-bout persistence (finite-state): 3 bout types, each its own ChainVireo over 17
    types; the type persists from bout to bout with probability 0.8."""

    def __init__(self, rng, n_types=3, n=17, persist=0.8):
        self.types = [ChainVireo(rng, n=n, p_end=0.01) for _ in range(n_types)]
        self.persist, self.t = persist, 0

    def new_day(self, rng):
        self.t = int(rng.integers(len(self.types)))

    def bout(self, rng, cap=3000):
        if rng.random() >= self.persist:
            k = len(self.types)
            self.t = int((self.t + 1 + rng.integers(k - 1)) % k)
        return self.types[self.t].bout(rng, cap)


class TreeVireo:
    """S4 positive control: every bout is a Lin-Tegmark recursive sequence (5 types, 2 children,
    depth 7 = 128 phrases)."""

    def __init__(self, rng, n=5, depth=7):
        self.tree = s4.TreeBird(rng, n=n, depth=depth)
        self.syms = rng.choice(N_POP, size=n, replace=False)

    def bout(self, rng, cap=3000):
        return [int(self.syms[w]) for w in self.tree.bout(rng, cap)]


VWORLDS = {"S0": ChainVireo, "S1": HMMVireo, "S3": TypedVireo, "S4": TreeVireo}
KINDS = ("S0", "S1", "S3", "S4")


def synth_vireo(rng, kind, n_birds=14, n_days=4, bouts_per_day=4):
    """Vireo-shaped design: 14 birds x 4 days x 4 bouts; symbols shared across birds."""
    out = []
    for b in range(n_birds):
        bird = VWORLDS[kind](rng)
        for d in range(n_days):
            if hasattr(bird, "new_day"):
                bird.new_day(rng)
            bouts = []
            for _ in range(bouts_per_day):
                bt = bird.bout(rng)
                if bt:
                    bouts.append(tuple(int(w) for w in bt))
            out.append((f"v{b}", f"d{d}", bouts))
    return out


# ------------------------------------------------------------------ grading (pure)

def predictions(st, sc, lr):
    g = {"selfcheck": sc["verdict"] if sc else None,
         "V7_loader_ok": bool(lr and lr.get("loader_ok"))}
    if not g["V7_loader_ok"]:
        g["grade"] = "LOADER_STOP"
        return g
    if st is None or sc is None:
        g["grade"] = "UNRESOLVED_MISSING_OUTPUT"
        return g
    cal = bool(sc["verdict"]["t4c_calibrated"])
    ks = [v["k"] for v in st["kgram"].values()]
    rate = st["T4b"].get("fire_rate")
    g.update({"grade": s4.final_grade(st["T4c"]["grade"], st["T4b"].get("p_upper"), cal),
              "V1_T5a_fires": bool(st["T4a"]["fire_strong"]),
              "V2_k_le2_in_75pct": bool(ks) and sum(1 for k in ks if k <= 2) >= 0.75 * len(ks),
              "V3_selfcheck_calibrated": cal,
              "V4_T5b_majority": rate is not None and rate >= 0.5,
              "V6_S4_power_ge_half": sc["verdict"]["power_S4_within_bout_hierarchy"] >= 0.5,
              "k_per_bird": {b: v["k"] for b, v in st["kgram"].items()},
              "T5b": st["T4b"], "T5c": st["T4c"]})
    g["V5_finite_state_suffices"] = g["grade"] == "FINITE_STATE_SUFFICES"
    return g


def _load(out_dir, name):
    p = os.path.join(out_dir, name)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def grade5(out_dir):
    g = predictions(_load(out_dir, "stage5_results.json"), _load(out_dir, "selfcheck5.json"),
                    _load(out_dir, "load_report5.json"))
    with open(os.path.join(out_dir, "grade5.json"), "w") as fh:
        json.dump(s4.jsonable(g), fh, indent=1)
    print("GRADE5", g["grade"], flush=True)
    return g


# ------------------------------------------------------------------ jobs

def selfcheck5(seed, n_worlds, n_perm, n_surr, out_dir, skip_if_stop=False):
    if skip_if_stop:
        lr = _load(out_dir, "load_report5.json")
        if not lr or not lr.get("loader_ok"):
            print("SELFCHECK5 skipped: loader stop", flush=True)
            return None
    rows = []
    for wi, kind in enumerate(KINDS):
        for w in range(n_worlds):
            rng = np.random.default_rng([seed, 5, wi, w])
            cdays = synth_vireo(rng, kind)
            r = s4.analyse(cdays, rng, n_perm, n_surr, tag=f"{kind}#{w}")
            rows.append({"world": kind, "i": w, "t4a_fire": r["T4a"]["fire_strong"],
                         "real_gap": r["T4a"]["gap"], "t4b_p": r["T4b"]["p_upper"],
                         "t4b_fire_rate": r["T4b"]["fire_rate"], "t4c": r["T4c"]["grade"],
                         "t4c_p": r["T4c"]["p_upper"], "t4c_fire_rate": r["T4c"]["fire_rate"],
                         "k": [v["k"] for v in r["kgram"].values()],
                         "final": s4.final_grade(r["T4c"]["grade"], r["T4b"]["p_upper"], True)})
    summary = {}
    for kind in KINDS:
        rs = [x for x in rows if x["world"] == kind]
        n = max(1, len(rs))
        summary[kind] = {"worlds": len(rs),
                         "t4a_fire_rate": sum(x["t4a_fire"] for x in rs) / n,
                         "t4c_exceeds": sum(x["t4c"] == "EXCEEDS_FINITE_STATE" for x in rs) / n,
                         "t4c_suffices": sum(x["t4c"] == "FINITE_STATE_SUFFICES" for x in rs) / n,
                         "cross_bout_order": sum(x["final"] == "CROSS_BOUT_ORDER" for x in rs) / n}
    out = {"seed": seed, "n_worlds": n_worlds, "n_perm": n_perm, "n_surr": n_surr,
           "summary": summary, "verdict": s4.selfcheck_verdict(summary)}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "selfcheck5.json"), "w") as fh:
        json.dump(s4.jsonable(out), fh, indent=1)
    with open(os.path.join(out_dir, "selfcheck5_worlds.json"), "w") as fh:
        json.dump(s4.jsonable(rows), fh, indent=1)
    print("SELFCHECK5", json.dumps(s4.jsonable(out["verdict"])), flush=True)
    return out


def _get(url, timeout, tries=3):
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  try {t + 1} failed: {exc}", flush=True)
            time.sleep(20)
    raise RuntimeError(f"download failed: {last}")


def fetch(data_dir):
    meta = json.loads(_get(ARTICLE_API, 120).decode("utf-8"))
    files = {f.get("name"): f for f in meta.get("files", [])}
    info = {"license": (meta.get("license") or {}).get("name"), "version": meta.get("version"),
            "files": sorted(files)}
    zf = files.get(ZIP_NAME)
    if zf is None:
        raise RuntimeError(f"{ZIP_NAME} not listed by figshare")
    want = zf.get("computed_md5") or zf.get("supplied_md5")
    root = os.path.join(data_dir, "vireo")
    os.makedirs(root, exist_ok=True)
    cache = os.path.join(root, ZIP_NAME)
    raw = None
    if os.path.exists(cache):
        with open(cache, "rb") as fh:
            raw = fh.read()
        if hashlib.md5(raw).hexdigest() != want:
            raw = None
    if raw is None:
        raw = _get(zf["download_url"], 600)
        if hashlib.md5(raw).hexdigest() == want:
            with open(cache, "wb") as fh:
                fh.write(raw)
    md5 = hashlib.md5(raw).hexdigest()
    readme = None
    rf = files.get(README_NAME)
    if rf is not None:
        try:
            readme = _get(rf["download_url"], 120).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            readme = f"(not fetched: {exc})"
    info.update({"zip_bytes": len(raw), "zip_md5": md5, "figshare_md5": want, "md5_ok": md5 == want})
    return raw, readme, info


def run_stage5(data_dir, out_dir, seed, n_perm, n_surr):
    os.makedirs(out_dir, exist_ok=True)
    raw, readme, info = fetch(data_dir)
    if readme is not None:
        with open(os.path.join(out_dir, "vireo_readme.txt"), "w", encoding="utf-8") as fh:
            fh.write(readme)
    members = read_zip(raw)
    recs, rep = build(members)
    use_dates = bool(recs) and rep["n_dated"] >= MIN_DATED * len(recs)
    days = group_days(recs, use_dates)
    days, birds_report = retain_birds(days)
    cdays, n_sym = encode_shared(days)
    desc = s4.describe(cdays)
    fails = loader_gate(info["md5_ok"], rep, desc)
    report = {"fetch": info, "parse": rep, "n_records": len(recs),
              "grouping": "bird-day" if use_dates else "recording", "birds": birds_report,
              "describe": desc, "n_symbols": n_sym, "gate_failures": fails, "loader_ok": not fails}
    with open(os.path.join(out_dir, "load_report5.json"), "w") as fh:
        json.dump(s4.jsonable(report), fh, indent=1)
    if fails:
        print("LOADER STOP", fails, flush=True)
        return None
    rng = np.random.default_rng(seed)
    res = s4.analyse(cdays, rng, n_perm, n_surr, tag="CAVI")
    res["describe"] = desc
    res["grouping"] = report["grouping"]
    with open(os.path.join(out_dir, "stage5_results.json"), "w") as fh:
        json.dump(s4.jsonable(res), fh, indent=1)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selfcheck")
    s.add_argument("--out-dir", required=True)
    s.add_argument("--worlds", type=int, default=12)
    s.add_argument("--perm", type=int, default=20)
    s.add_argument("--surr", type=int, default=40)
    s.add_argument("--seed", type=int, default=20261124)
    s.add_argument("--skip-if-loader-stop", action="store_true")
    r = sub.add_parser("stage5")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--perm", type=int, default=N_PERM)
    r.add_argument("--surr", type=int, default=N_SURR)
    r.add_argument("--seed", type=int, default=20261124)
    gp = sub.add_parser("grade")
    gp.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "selfcheck":
        selfcheck5(a.seed, a.worlds, a.perm, a.surr, a.out_dir, a.skip_if_loader_stop)
    elif a.cmd == "stage5":
        run_stage5(a.data_dir, a.out_dir, a.seed, a.perm, a.surr)
    else:
        grade5(a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
