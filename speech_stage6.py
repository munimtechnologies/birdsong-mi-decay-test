# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name. MV2, Munim, Inc., mv2@munimtech.com
"""birdsong-mi-decay-test, stage 6 (AMENDMENT-6-STAGE6-SPEECH.md): a HUMAN-SPEECH CONTROL for the
MI-decay hierarchy diagnostic. Human language is hierarchical by any account. Does the composite
(exponential + power-law) MI-decay verdict on read English phone sequences exceed what per-speaker
FINITE-MEMORY (k-gram) models produce when they are given the same design (speakers, chapters,
utterances, sample size)? If it does not, a 'finite state suffices' verdict on birds or chimps
means 'not detectable by this diagnostic', not 'absent'.

Data: LibriSpeech Alignments (Lugosch 2019, Zenodo record 2619474, CC BY 4.0): Montreal Forced
Aligner TextGrids, one per LibriSpeech utterance. Subsets dev-clean (primary, 40 speakers) and
test-clean (replicate, 40 speakers). Phones from the phone tier in time order; stress digits
removed (AH0 -> AH); silence and spoken-noise intervals dropped.

Design mapping onto the registered stage-4 code (bf_stage4.py, pinned by git blob):
  speaker -> bird, chapter -> day, utterance -> bout.
  T6a = T4a composite verdict on chapter sequences (utterances concatenated in order).
  T6b = T4b utterance order permuted within chapter.
  T6c = T4c per-speaker k-gram (k = 1..8 by held-out likelihood) surrogates, graded by
        bf_stage4.grade_null (EXCEEDS_FINITE_STATE / FINITE_STATE_SUFFICES / UNRESOLVED).
  T6u = the same T6a/T6c on single utterances as sequences (Sainburg et al.'s speech unit).
  Self-check: in-class worlds = surrogates of the fitted dev-clean k-grams treated as data.
Only numpy and the standard library are imported at module level (the analysis imports the
pinned bf_stage4 and mi_decay, which need scipy, when it runs).
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.request
import zipfile

import numpy as np

ZENODO_API = "https://zenodo.org/api/records/2619474"
ZIP_NAME = "librispeech_alignments.zip"
ZIP_FALLBACK_URL = "https://zenodo.org/records/2619474/files/librispeech_alignments.zip?download=1"
ALL_SUBSETS = ("dev-clean", "dev-other", "test-clean", "test-other", "train-clean-100",
               "train-clean-360", "train-other-500")
SUBSETS = ("dev-clean", "test-clean")
PRIMARY = "dev-clean"
SILENCE = frozenset(["", "sil", "sp", "spn", "<eps>", "<unk>", "<sil>", "sil0", "noise"])
PHONE_TIERS = ("phones", "phone", "phonemes", "phoneme")
BASE_RE = re.compile(r"^(\d+)-(\d+)-(\d+)\.textgrid$", re.IGNORECASE)
UA = {"User-Agent": "mv2-research-job/1.0"}
CORE_FALLBACK = "/data/core"

# registered loader gate
MIN_SPEAKERS = 35
MIN_UTTS = 2000
MIN_PHONES = 100000
MAX_BAD_FRAC = 0.01
MIN_LABELS, MAX_LABELS = 30, 50

# registered effort
N_PERM = 100
N_SURR = 100
N_SURR_UTT = 100
SC_WORLDS = 8
SC_SURR = 40
MAX_FALSE = 0.125


# ------------------------------------------------------------------ TextGrid parsing (pure)

def decode_bytes(b):
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace")
    if b[:3] == b"\xef\xbb\xbf":
        return b[3:].decode("utf-8", "replace")
    return b.decode("utf-8", "replace")


def _unq(s):
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1].replace('""', '"')
    return s


_ITEM_RE = re.compile(r"item\s*\[\s*\d+\s*\]\s*:")
_NAME_RE = re.compile(r'name\s*=\s*"((?:[^"]|"")*)"')
_CLASS_RE = re.compile(r'class\s*=\s*"((?:[^"]|"")*)"')
_IV_RE = re.compile(r'intervals\s*\[\s*\d+\s*\]\s*:\s*xmin\s*=\s*(\S+)\s*xmax\s*=\s*(\S+)\s*'
                    r'text\s*=\s*"((?:[^"]|"")*)"')
_TOK_RE = re.compile(r'"(?:[^"]|"")*"|[^\s"]+')


def _parse_long(text):
    tiers = {}
    for part in _ITEM_RE.split(text)[1:]:
        m = _NAME_RE.search(part)
        if not m:
            continue
        c = _CLASS_RE.search(part)
        if c and c.group(1) != "IntervalTier":
            continue
        tiers[m.group(1).replace('""', '"')] = [
            (float(a), float(b), t.replace('""', '"')) for a, b, t in _IV_RE.findall(part)]
    return tiers


def _parse_short(text):
    tok = _TOK_RE.findall(text)
    try:
        i = tok.index("<exists>") + 1
        n_tiers = int(tok[i])
    except (ValueError, IndexError):
        return {}
    i += 1
    tiers = {}
    try:
        for _ in range(n_tiers):
            cls, name = _unq(tok[i]), _unq(tok[i + 1])
            n = int(tok[i + 4])
            i += 5
            if cls == "IntervalTier":
                ivs = []
                for _ in range(n):
                    ivs.append((float(tok[i]), float(tok[i + 1]), _unq(tok[i + 2])))
                    i += 3
                tiers[name] = ivs
            else:
                i += 2 * n
    except (ValueError, IndexError):
        return tiers
    return tiers


def parse_textgrid(text):
    """-> {tier name: [(xmin, xmax, label), ...]} for the interval tiers (long or short format)."""
    if _ITEM_RE.search(text):
        return _parse_long(text)
    return _parse_short(text)


def normalize_phone(label):
    """'AH0' -> 'AH'; silence / spoken noise -> None."""
    s = (label or "").strip()
    if s.lower() in SILENCE:
        return None
    s = s.rstrip("0123456789").upper()
    return s or None


def phone_tier(tiers):
    """The phone tier: named 'phones' (or phone/phonemes/phoneme), else MFA's multi-speaker
    form '<speaker> - phones'."""
    for name in tiers:
        if name.strip().lower() in PHONE_TIERS:
            return name
    for name in tiers:
        n = name.strip().lower()
        if any(n.endswith("- " + t) or n.endswith("-" + t) for t in PHONE_TIERS):
            return name
    return None


def utt_phones(text):
    """Phones of one TextGrid in onset order, or None if it has no phone tier."""
    tiers = parse_textgrid(text)
    name = phone_tier(tiers)
    if name is None:
        return None
    ivs = sorted(tiers[name], key=lambda x: (x[0], x[1]))
    out = []
    for _, _, lab in ivs:
        p = normalize_phone(lab)
        if p is not None:
            out.append(p)
    return out


def parse_member_name(name):
    """'.../dev-clean/1272/128104/1272-128104-0003.TextGrid' -> ('dev-clean', '1272', '128104', 3)
    or None (no subset folder in the path, not a TextGrid, or a macOS resource file)."""
    n = name.replace("\\", "/")
    parts = n.split("/")
    base = parts[-1]
    if "__MACOSX" in n or base.startswith("._"):
        return None
    m = BASE_RE.match(base)
    if not m:
        return None
    subset = None
    for p in parts[:-1]:
        if p.lower() in ALL_SUBSETS:
            subset = p.lower()
    if subset is None:
        return None
    return subset, m.group(1), m.group(2), int(m.group(3))


def build_cdays(entries):
    """entries: [(speaker, chapter, utt_no, [phone labels])] of one subset ->
    (cdays, n_symbols, symbol list). cdays = [(speaker, chapter, [utterance tuples])] sorted by
    speaker then chapter, utterances in utt_no order, empty utterances dropped. Phones get ONE
    shared code across speakers (a phone means the same for every speaker), codes in sorted
    label order."""
    labels = sorted({p for _, _, _, ph in entries for p in ph})
    code = {p: i for i, p in enumerate(labels)}
    groups = {}
    for spk, chap, no, ph in entries:
        if ph:
            groups.setdefault((spk, chap), []).append((no, tuple(code[p] for p in ph)))
    cdays = []
    for key in sorted(groups, key=lambda k: (int(k[0]), int(k[1]))):
        utts = [u for _, u in sorted(groups[key], key=lambda x: x[0])]
        cdays.append((key[0], key[1], utts))
    return cdays, len(labels), labels


def utterance_days(cdays):
    """Every utterance becomes its own 'day' (one bout), so the stage-4 code works on single
    utterances as sequences; speakers (and so the k-gram models) are unchanged."""
    out = []
    for spk, chap, utts in cdays:
        for i, u in enumerate(utts):
            out.append((spk, f"{chap}#{i}", [u]))
    return out


def describe6(cdays):
    spk = sorted({s for s, _, _ in cdays}, key=int)
    utts = [u for _, _, us in cdays for u in us]
    lens = [len(u) for u in utts]
    return {"speakers": len(spk), "chapters": len(cdays), "utterances": len(utts),
            "phones": int(sum(lens)),
            "mean_utt_len": (float(np.mean(lens)) if lens else None),
            "utts_longer_than_100": int(sum(1 for x in lens if x > 100)),
            "mean_chapter_len": (float(np.mean([sum(len(u) for u in us) for _, _, us in cdays]))
                                 if cdays else None)}


def loader_gate6(md5_ok, per_subset):
    """per_subset: {subset: {"files": n, "bad": n, "describe": {...}, "n_labels": n}}."""
    fails = []
    if not md5_ok:
        fails.append("zip md5 does not match Zenodo's checksum")
    for s in SUBSETS:
        r = per_subset.get(s)
        if r is None or r["files"] == 0:
            fails.append(f"{s}: no TextGrid files found under a '{s}' folder")
            continue
        if r["bad"] > MAX_BAD_FRAC * r["files"]:
            fails.append(f"{s}: {r['bad']} of {r['files']} files without a phone tier")
        d = r["describe"]
        if d["speakers"] < MIN_SPEAKERS:
            fails.append(f"{s}: speakers {d['speakers']} < {MIN_SPEAKERS}")
        if d["utterances"] < MIN_UTTS:
            fails.append(f"{s}: utterances {d['utterances']} < {MIN_UTTS}")
        if d["phones"] < MIN_PHONES:
            fails.append(f"{s}: phones {d['phones']} < {MIN_PHONES}")
        if not MIN_LABELS <= r["n_labels"] <= MAX_LABELS:
            fails.append(f"{s}: {r['n_labels']} phone labels, outside {MIN_LABELS}-{MAX_LABELS}")
    return fails


# ------------------------------------------------------------------ grading (pure)

def selfcheck_verdict6(grades):
    """grades: T6c grades of the in-class worlds."""
    n = len(grades)
    false = sum(1 for g in grades if g == "EXCEEDS_FINITE_STATE")
    rate = false / n if n else None
    return {"worlds": n, "false_exceeds": false, "false_exceeds_rate": rate,
            "suffices_rate": (sum(1 for g in grades if g == "FINITE_STATE_SUFFICES") / n
                              if n else None),
            "calibrated": bool(n > 0 and rate <= MAX_FALSE)}


def headline6(calibrated, dev_grade, test_grade):
    """Registered headline from the chapter-level T6c grades of dev-clean and test-clean."""
    if not calibrated:
        return "UNRESOLVED_UNCALIBRATED"
    if "FINITE_STATE_SUFFICES" in (dev_grade, test_grade):
        return "POSITIVE_CONTROL_FAILS"
    if dev_grade == "EXCEEDS_FINITE_STATE" and test_grade == "EXCEEDS_FINITE_STATE":
        return "POSITIVE_CONTROL_PASSES"
    return "SPLIT_OR_UNRESOLVED"


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [jsonable(v) for v in o.tolist()]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    return o


# ------------------------------------------------------------------ network and zip

def zenodo_file_info():
    meta = json.loads(urllib.request.urlopen(urllib.request.Request(ZENODO_API, headers=UA),
                                             timeout=120).read().decode("utf-8"))
    lic = (meta.get("metadata") or {}).get("license")
    lic = lic.get("id") if isinstance(lic, dict) else lic
    for f in meta.get("files", []):
        name = f.get("key") or f.get("filename")
        if name == ZIP_NAME:
            links = f.get("links") or {}
            url = links.get("self") or links.get("download") or ZIP_FALLBACK_URL
            md5 = (f.get("checksum") or "").replace("md5:", "")
            return {"url": url, "md5": md5, "size": f.get("size") or f.get("filesize"),
                    "license": lic, "record_version": (meta.get("metadata") or {}).get("version")}
    raise RuntimeError("zip not listed in the Zenodo record")


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(url, path, tries=3):
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as resp, open(path + ".part", "wb") as fh:
                while True:
                    b = resp.read(1 << 20)
                    if not b:
                        break
                    fh.write(b)
            os.replace(path + ".part", path)
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  download try {t + 1} failed: {exc}", flush=True)
            time.sleep(30)
    raise RuntimeError(f"download failed: {last}")


def fetch_zip(data_dir):
    info = zenodo_file_info()
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, ZIP_NAME)
    if not (os.path.exists(path) and file_md5(path) == info["md5"]):
        t0 = time.time()
        download(info["url"], path)
        if file_md5(path) != info["md5"]:
            download(ZIP_FALLBACK_URL, path)
        print(f"zip downloaded ({time.time() - t0:.0f}s)", flush=True)
    got = file_md5(path)
    info["md5_got"] = got
    info["md5_ok"] = got == info["md5"]
    info["bytes"] = os.path.getsize(path)
    return path, info


def read_subsets(zip_path):
    """-> ({subset: [(spk, chap, utt_no, phones)]}, {subset: {'files', 'bad'}}, manifest)."""
    z = zipfile.ZipFile(zip_path)
    names = z.namelist()
    entries = {s: [] for s in SUBSETS}
    counts = {s: {"files": 0, "bad": 0} for s in SUBSETS}
    tier_names, labels_raw, subset_files = {}, {}, {}
    for n in names:
        p = parse_member_name(n)
        if p is None:
            continue
        subset_files[p[0]] = subset_files.get(p[0], 0) + 1
        if p[0] not in SUBSETS:
            continue
        counts[p[0]]["files"] += 1
        text = decode_bytes(z.read(n))
        tiers = parse_textgrid(text)
        for tn in tiers:
            tier_names[tn] = tier_names.get(tn, 0) + 1
        ph = utt_phones(text)
        if ph is None:
            counts[p[0]]["bad"] += 1
            continue
        tn = phone_tier(tiers)
        for _, _, lab in tiers[tn]:
            labels_raw[lab.strip()] = labels_raw.get(lab.strip(), 0) + 1
        entries[p[0]].append((p[1], p[2], p[3], ph))
    manifest = {"n_members": len(names), "first_members": sorted(names)[:12],
                "textgrids_per_subset": subset_files, "tier_names": tier_names,
                "raw_phone_labels": dict(sorted(labels_raw.items()))}
    return entries, counts, manifest


# ------------------------------------------------------------------ analysis

def _stage4():
    try:
        import bf_stage4  # noqa: F401
    except ImportError:
        if os.path.isdir(CORE_FALLBACK) and CORE_FALLBACK not in sys.path:
            sys.path.insert(0, CORE_FALLBACK)
        import bf_stage4  # noqa: F401
    return sys.modules["bf_stage4"]


def run_load(data_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    zip_path, info = fetch_zip(data_dir)
    entries, counts, manifest = read_subsets(zip_path)
    per, data = {}, {}
    for s in SUBSETS:
        cdays, n_sym, labels = build_cdays(entries[s])
        data[s] = cdays
        per[s] = {"files": counts[s]["files"], "bad": counts[s]["bad"],
                  "describe": describe6(cdays), "n_labels": n_sym, "labels": labels}
    fails = loader_gate6(info["md5_ok"], per)
    report = {"zenodo": info, "subsets": per, "manifest": manifest, "gate_failures": fails,
              "loader_ok": not fails}
    with open(os.path.join(out_dir, "load_report6.json"), "w") as fh:
        json.dump(jsonable(report), fh, indent=1)
    print("LOADER", "OK" if not fails else f"STOP {fails}", flush=True)
    return (data if not fails else None), report


def _summ(res):
    """Keep what the reading needs (the real curve and fits, null summaries, chosen k)."""
    return {"T6a": res["T4a"], "T6b": res["T4b"], "T6c": res["T4c"],
            "k": {s: v["k"] for s, v in res["kgram"].items()},
            "kgram": res["kgram"], "seconds": res["seconds"]}


def run_stage6(data_dir, out_dir, seed, n_perm, n_surr, n_surr_utt, sc_worlds, sc_surr):
    data, report = run_load(data_dir, out_dir)
    if data is None:
        return None
    bf = _stage4()
    results = {"seed": seed, "n_perm": n_perm, "n_surr": n_surr, "n_surr_utt": n_surr_utt,
               "describe": {s: report["subsets"][s]["describe"] for s in SUBSETS}}
    # self-check first: in-class worlds from the k-grams fitted to dev-clean
    rng = np.random.default_rng([seed, 0])
    models, info, caps = bf.fit_models(data[PRIMARY])
    sc_rows = []
    for w in range(sc_worlds):
        wr = np.random.default_rng([seed, 9, w])
        pseudo = bf.kgram_surrogate(wr, data[PRIMARY], models, caps)
        r = bf.analyse(pseudo, wr, 0, sc_surr, tag=f"SC#{w}")
        sc_rows.append({"world": w, "t6a_fire": r["T4a"]["fire_strong"], "real_gap": r["T4a"]["gap"],
                        "t6c": r["T4c"]["grade"], "t6c_p": r["T4c"]["p_upper"],
                        "t6c_fire_rate": r["T4c"]["fire_rate"],
                        "k": [v["k"] for v in r["kgram"].values()]})
    sc = {"rows": sc_rows, "verdict": selfcheck_verdict6([x["t6c"] for x in sc_rows]),
          "fitted_k_dev": {s: v["k"] for s, v in info.items()}}
    with open(os.path.join(out_dir, "selfcheck6.json"), "w") as fh:
        json.dump(jsonable(sc), fh, indent=1)
    print("SELFCHECK6", json.dumps(jsonable(sc["verdict"])), flush=True)
    for i, s in enumerate(SUBSETS):
        rng = np.random.default_rng([seed, 1, i])
        results[f"{s}/chapter"] = _summ(bf.analyse(data[s], rng, n_perm, n_surr, tag=f"{s}/ch"))
        with open(os.path.join(out_dir, "stage6_results.json"), "w") as fh:
            json.dump(jsonable(results), fh, indent=1)
    for i, s in enumerate(SUBSETS):
        rng = np.random.default_rng([seed, 2, i])
        results[f"{s}/utterance"] = _summ(bf.analyse(utterance_days(data[s]), rng, 0, n_surr_utt,
                                                     tag=f"{s}/utt"))
        with open(os.path.join(out_dir, "stage6_results.json"), "w") as fh:
            json.dump(jsonable(results), fh, indent=1)
    return results


def grade6(out_dir):
    def load(name):
        p = os.path.join(out_dir, name)
        if not os.path.exists(p):
            return None
        with open(p) as fh:
            return json.load(fh)
    lr, sc, st = load("load_report6.json"), load("selfcheck6.json"), load("stage6_results.json")
    g = {}
    if lr is None or not lr.get("loader_ok"):
        g["headline"] = "LOADER_STOP"
    elif sc is None or st is None or any(f"{s}/chapter" not in st for s in SUBSETS):
        g["headline"] = "UNRESOLVED_MISSING_OUTPUT"
    else:
        cal = bool(sc["verdict"]["calibrated"])
        dev, test = st[f"{PRIMARY}/chapter"], st["test-clean/chapter"]
        g["headline"] = headline6(cal, dev["T6c"]["grade"], test["T6c"]["grade"])
        ks = [k for s in SUBSETS for k in st[f"{s}/chapter"]["k"].values()]
        g.update({
            "selfcheck": sc["verdict"],
            "P1_dev_T6a_fires": bool(dev["T6a"]["fire_strong"]),
            "P2_test_T6a_fires": bool(test["T6a"]["fire_strong"]),
            "P3_selfcheck_calibrated": cal,
            "P4_dev_chapter_exceeds": dev["T6c"]["grade"] == "EXCEEDS_FINITE_STATE",
            "P5_passes": g["headline"] == "POSITIVE_CONTROL_PASSES",
            "P6_fails": g["headline"] == "POSITIVE_CONTROL_FAILS",
            "P7_dev_T6b_p_le_05": (dev["T6b"]["p_upper"] is not None
                                   and dev["T6b"]["p_upper"] <= 0.05),
            "P8_dev_utterance_exceeds": (st.get(f"{PRIMARY}/utterance", {}).get("T6c", {})
                                         .get("grade") == "EXCEEDS_FINITE_STATE"),
            "P9_median_k_ge3": (float(np.median(ks)) >= 3) if ks else False,
            "grades": {key: st[key]["T6c"]["grade"] for key in st
                       if isinstance(st[key], dict) and "T6c" in st[key]},
            "T6c": {key: {kk: st[key]["T6c"].get(kk) for kk in
                          ("real_gap", "gap_p95", "fire_rate", "p_upper", "n_finite_gap")}
                    for key in st if isinstance(st[key], dict) and "T6c" in st[key]},
            "T6b": {key: {kk: st[key]["T6b"].get(kk) for kk in ("fire_rate", "p_upper", "n")}
                    for key in st if isinstance(st[key], dict) and "T6b" in st[key]}})
    with open(os.path.join(out_dir, "grade6.json"), "w") as fh:
        json.dump(jsonable(g), fh, indent=1)
    print("GRADE6", g["headline"], flush=True)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("stage6")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--seed", type=int, default=20261124)
    r.add_argument("--perm", type=int, default=N_PERM)
    r.add_argument("--surr", type=int, default=N_SURR)
    r.add_argument("--surr-utt", type=int, default=N_SURR_UTT)
    r.add_argument("--sc-worlds", type=int, default=SC_WORLDS)
    r.add_argument("--sc-surr", type=int, default=SC_SURR)
    gp = sub.add_parser("grade")
    gp.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "stage6":
        run_stage6(a.data_dir, a.out_dir, a.seed, a.perm, a.surr, a.surr_utt, a.sc_worlds,
                   a.sc_surr)
    else:
        grade6(a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
