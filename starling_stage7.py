# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 7 (AMENDMENT-7-STAGE7-STARLING.md): does the composite
(exponential + power-law) MI-decay verdict that Sainburg, Theilman, Thielk and Gentner (2019,
Nat Commun 10:3636) read as hierarchy in European starling song exceed what a per-bird
FINITE-MEMORY syntax model produces when it is given the same design (birds, days, bouts)?

Data: "An acoustically isolated European starling song library" (Arneodo, Sainburg, Jeanne and
Gentner; Zenodo record 3237218, CC BY 4.0), the recordings behind the 2019 paper. The released
library has audio only (no syllable labels), so this stage segments and labels it itself:
  * birds: the four smallest archives among the ten birds recorded with one system in 2017-2018
    (b1125, b1160, b1077, b1066), chosen by file size before any audio was opened;
  * segmentation: Sainburg's own vocalseg package (github.com/timsainb/vocalization-segmentation,
    MIT, pinned commit) with the parameters of his public starling notebook (avgn_paper,
    notebooks/01.1-syllabic-segmentation/starling-syllable-segmentation.ipynb), after the same
    500-15000 Hz Butterworth bandpass; files longer than 45 s are segmented in 30 s pieces;
  * features: per syllable a 32-band mel spectrogram (500-15000 Hz, 10 ms window, 3 ms hop) in dB
    relative to the syllable's peak, floored at -80 dB, resampled to 32 time steps;
  * labels, per bird: PRIMARY = PCA(50) -> UMAP(2-D) -> HDBSCAN (noise label kept as a symbol, as
    in Sainburg's sequence code); ROBUSTNESS = k-means (k = 30) on the same PCA(50) features;
  * bouts: a bird's syllables in time order, split where one onset follows the previous by more
    than 10 s (Sainburg's isi_thresh = 10) and at calendar-day changes; day sequence = that
    day's bouts joined in time order (as in stage 4).
Tests T7a/T7b/T7c are the stage-4 tests T4a/T4b/T4c, imported unchanged from bf_stage4.py
(pinned by git blob): the composite verdict on the real curve, the same after permuting bout
order within each bird-day, and per-bird k-gram (k = 1..8 by 5-fold held-out likelihood)
surrogates. The self-check runs the stage-4 synthetic worlds (S0, S1, S3, S4) in the REAL
starling design (same birds and bouts per day, on each bird's 6 days with the most bouts, at
most 100 bouts per bird-day, to bound the run time).
"""
import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import urllib.request
import zipfile

import numpy as np

RECORD_API = "https://zenodo.org/api/records/3237218"
FILE_URL = "https://zenodo.org/api/records/3237218/files/{key}/content"
BIRDS = ("b1125", "b1160", "b1077", "b1066")
MD5 = {"b1125.zip": "dafeef92db5249a565bc8db999b1124a",
       "b1160.zip": "c696f077cb20e281c3f3429234657b44",
       "b1077.zip": "d240e78eff0dd85623005eac26523081",
       "b1066.zip": "581ace7f2147b2cd3388a5a987c609aa"}
UA = {"User-Agent": "mv2-research-job/1.0"}
WAV_RE = re.compile(r"^(?:.*/)?([A-Za-z0-9]+)/wavs/(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})"
                    r"-(\d{6})\.wav$")
EPOCH = dt.datetime(2000, 1, 1)

SEG = {"n_fft": 1024, "hop_length_ms": 1, "win_length_ms": 5, "ref_level_db": 20, "pre": 0.97,
       "min_level_db": -100, "min_level_db_floor": -60, "db_delta": 5, "silence_threshold": 0.01,
       "min_silence_for_spec": 0.1, "max_vocal_for_spec": 2.0, "min_syllable_length_s": 0.15}
BUTTER = (500, 15000)
CHUNK_S = 30.0
MAX_WHOLE_S = 45.0

N_MELS = 32
N_T = 32
HOP_FEAT_S = 0.003
WIN_FEAT_S = 0.010
FMIN = 500.0
FMAX = 15000.0
DB_FLOOR = 80.0

PCA_DIM = 50
UMAP_NEIGHBORS = 15
UMAP_MIN_DIST = 0.1
HDB_MIN_FRAC = 0.01
HDB_MIN_ABS = 25
KMEANS_K = 30
MIN_LABEL_N = 200

ISI_SPLIT_S = 10.0
ARMS = ("primary", "kmeans")
KINDS = ("S0", "S1", "S3", "S4")
SC_MAX_BOUTS = 100
SC_MAX_DAYS = 6
SEED = 20261126

MIN_SYLLABLES = 10000
MIN_DAYS = 2
MIN_BOUTS = 20
MIN_READ_FRAC = 0.9
MIN_CLUSTERS = 5

PRIORS = {"C1_T7a_fires": 0.85, "C2_k_ge3_in_3of4": 0.60, "C3_selfcheck_calibrated": 0.65,
          "C4_T7b_majority": 0.60, "C5_finite_state_suffices": 0.40,
          "C6_arms_agree": 0.60, "C7_S4_power_ge_half": 0.80, "C8_S3_exceeds_ge_half": 0.80}
CORE_DIRS = ("/data/core7",)


def _bf():
    """The pinned stage-4 module (and through it the stage-1 core mi_decay)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (here,) + CORE_DIRS:
        if os.path.exists(os.path.join(d, "bf_stage4.py")) and d not in sys.path:
            sys.path.insert(0, d)
    import bf_stage4
    return bf_stage4


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


def dump(path, obj):
    with open(path, "w") as fh:
        json.dump(jsonable(obj), fh, indent=1)


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


# ------------------------------------------------------------------ pure helpers

def parse_wav_name(name):
    """'<bird>/wavs/YYYY-MM-DD_HH-MM-SS-ffffff.wav' -> (bird, datetime) or None."""
    if "__MACOSX" in name or name.replace("\\", "/").split("/")[-1].startswith("._"):
        return None
    m = WAV_RE.match(name.replace("\\", "/"))
    if not m:
        return None
    y, mo, d, h, mi, s, us = (int(v) for v in m.groups()[1:])
    try:
        return m.group(1), dt.datetime(y, mo, d, h, mi, s, us)
    except ValueError:
        return None


def to_float(data):
    """wav samples -> float32 mono in [-1, 1] (first channel if several)."""
    a = np.asarray(data)
    if a.ndim == 2:
        a = a[:, 0]
    if a.dtype == np.uint8:
        return (a.astype(np.float32) - 128.0) / 128.0
    if np.issubdtype(a.dtype, np.integer):
        return a.astype(np.float32) / float(2 ** (8 * a.dtype.itemsize - 1))
    return a.astype(np.float32)


def chunk_bounds(n, rate, chunk_s=CHUNK_S, max_whole_s=MAX_WHOLE_S):
    """Whole file if at most max_whole_s long, else consecutive chunk_s pieces (a last piece
    shorter than 1 s is merged into the one before)."""
    if n <= int(max_whole_s * rate):
        return [(0, n)]
    step = int(chunk_s * rate)
    out = [(s, min(s + step, n)) for s in range(0, n, step)]
    if len(out) > 1 and out[-1][1] - out[-1][0] < int(rate):
        out[-2] = (out[-2][0], out[-1][1])
        out.pop()
    return out


def patch_vector(P, n_t=N_T, floor_db=DB_FLOOR):
    """mel power patch (bands x frames) -> flat vector: dB re the patch peak, floored at
    -floor_db, scaled to [0, 1], linearly resampled to n_t time steps."""
    P = np.asarray(P, dtype=np.float64)
    n_bands = P.shape[0]
    top = float(P.max()) if P.size else 0.0
    if not top > 0.0:
        return np.zeros(n_bands * n_t, dtype=np.float32)
    db = 10.0 * np.log10(np.maximum(P, top * 1e-12) / top)
    norm = (np.clip(db, -floor_db, 0.0) + floor_db) / floor_db
    m = norm.shape[1]
    if m == 1:
        out = np.repeat(norm, n_t, axis=1)
    else:
        src = np.linspace(0.0, 1.0, m)
        dst = np.linspace(0.0, 1.0, n_t)
        out = np.vstack([np.interp(dst, src, row) for row in norm])
    return out.reshape(-1).astype(np.float32)


def frame_span(on, off, rate, hop, n_frames):
    """Frames [a, b) of a centred STFT covering onset..offset (at least one frame)."""
    a = int(math.floor(on * rate / hop))
    b = int(math.ceil(off * rate / hop))
    a = max(0, min(a, n_frames - 1))
    b = max(a + 1, min(b, n_frames))
    return a, b


def build_bird_days(bird, t_on, labels, isi=ISI_SPLIT_S):
    """Syllables (absolute onset seconds since 2000-01-01, labels) -> [(bird, day, bouts)]:
    time order; a new bout when an onset follows the previous onset by more than isi seconds
    or falls on a new calendar day."""
    t_on = np.asarray(t_on, dtype=float)
    order = np.argsort(t_on, kind="stable")
    days = {}
    prev_t = prev_day = None
    cur = None
    for i in order:
        t = float(t_on[i])
        d = int(t // 86400.0)
        if cur is None or d != prev_day or t - prev_t > isi:
            cur = []
            days.setdefault(d, []).append(cur)
        cur.append(int(labels[i]))
        prev_t, prev_day = t, d
    return [(bird, "d%d" % d, [tuple(b) for b in days[d]]) for d in sorted(days)]


def design_of(cdays, cap=SC_MAX_BOUTS, max_days=SC_MAX_DAYS):
    """[(bird, day, n_bouts)] of the real data for the self-check: each bird's max_days days
    with the most bouts (ties: earlier in the list), kept in their original order, bouts per
    bird-day capped at cap."""
    rows = [(i, b, d, len(bouts)) for i, (b, d, bouts) in enumerate(cdays) if bouts]
    keep = set()
    for bird in sorted({r[1] for r in rows}):
        mine = sorted([r for r in rows if r[1] == bird], key=lambda r: (-r[3], r[0]))
        keep.update(r[0] for r in mine[:max_days])
    return [(b, d, min(n, cap)) for i, b, d, n in rows if i in keep]


def loader_gate7(per_bird, desc):
    fails = []
    for b in BIRDS:
        r = per_bird.get(b)
        if r is None or not r.get("md5_ok"):
            fails.append("%s: archive missing or md5 mismatch" % b)
            continue
        if not r.get("n_wav") or r.get("n_read", 0) < MIN_READ_FRAC * r["n_wav"]:
            fails.append("%s: read %s of %s wav files" % (b, r.get("n_read"), r.get("n_wav")))
        d = desc["birds"].get(b)
        if d is None or d["days"] < MIN_DAYS or d["bouts"] < MIN_BOUTS:
            fails.append("%s too small: %s" % (b, d))
    if desc.get("n_syllables", 0) < MIN_SYLLABLES:
        fails.append("syllables %s < %d" % (desc.get("n_syllables"), MIN_SYLLABLES))
    return fails


def labels_ok(label_info):
    return all(label_info.get(b, {}).get("hdb_clusters", 0) >= MIN_CLUSTERS for b in BIRDS)


def brier(priors, outcomes):
    keys = [k for k in priors if outcomes.get(k) is not None]
    if not keys:
        return None
    return float(np.mean([(priors[k] - float(bool(outcomes[k]))) ** 2 for k in keys]))


def predictions(prim, km, sc_verdict, grade_prim, grade_km):
    cal = bool(sc_verdict["t4c_calibrated"])
    out = {"C1_T7a_fires": bool(prim["T4a"]["fire_strong"]),
           "C2_k_ge3_in_3of4": sum(1 for v in prim["kgram"].values() if v["k"] >= 3) >= 3,
           "C3_selfcheck_calibrated": cal,
           "C4_T7b_majority": (prim["T4b"]["fire_rate"] is not None
                               and prim["T4b"]["fire_rate"] >= 0.5),
           "C5_finite_state_suffices": grade_prim == "FINITE_STATE_SUFFICES",
           "C6_arms_agree": grade_prim == grade_km,
           "C7_S4_power_ge_half": sc_verdict["power_S4_within_bout_hierarchy"] >= 0.5,
           "C8_S3_exceeds_ge_half": sc_verdict["exceeds_S3_cross_bout"] >= 0.5}
    return out


# ------------------------------------------------------------------ audio parts (heavy deps)

def segment_wave(y, rate):
    """Bandpass then Sainburg's dynamic-threshold segmentation; onsets/offsets in seconds."""
    from vocalseg.dynamic_thresholding import dynamic_threshold_segmentation
    from vocalseg.utils import butter_bandpass_filter
    yf = butter_bandpass_filter(y, BUTTER[0], BUTTER[1], rate)
    ons, offs = [], []
    bounds = chunk_bounds(len(yf), rate)
    for a, b in bounds:
        res = dynamic_threshold_segmentation(yf[a:b], rate, **SEG)
        if res is None:
            continue
        for on, off in zip(np.ravel(res["onsets"]), np.ravel(res["offsets"])):
            ons.append(a / rate + float(on))
            offs.append(a / rate + float(off))
    return yf, np.asarray(ons, dtype=float), np.asarray(offs, dtype=float), len(bounds)


def syllable_features(yf, rate, ons, offs):
    import librosa
    hop = max(1, int(round(HOP_FEAT_S * rate)))
    win = max(2, int(round(WIN_FEAT_S * rate)))
    n_fft = 512
    while n_fft < win:
        n_fft *= 2
    S = librosa.feature.melspectrogram(y=np.asarray(yf, dtype=np.float32), sr=rate, n_fft=n_fft,
                                       hop_length=hop, win_length=win, n_mels=N_MELS, fmin=FMIN,
                                       fmax=min(FMAX, rate / 2.0), power=2.0)
    feats = np.zeros((len(ons), N_MELS * N_T), dtype=np.float32)
    for i, (on, off) in enumerate(zip(ons, offs)):
        a, b = frame_span(on, off, rate, hop, S.shape[1])
        feats[i] = patch_vector(S[:, a:b])
    return feats


def process_zip(zpath, bird, log_every=25):
    from scipy.io import wavfile
    z = zipfile.ZipFile(zpath)
    members = sorted(n for n in z.namelist()
                     if parse_wav_name(n) is not None and parse_wav_name(n)[0] == bird)
    rec = {"n_wav": len(members), "n_read": 0, "n_unreadable": 0, "n_seg_error": 0,
           "n_no_syllable": 0, "n_chunked": 0, "rates": {}, "seconds_audio": 0.0, "errors": []}
    widx, t_on, t_off, feats = [], [], [], []
    t0 = time.time()
    for wi, name in enumerate(members):
        start = (parse_wav_name(name)[1] - EPOCH).total_seconds()
        try:
            rate, data = wavfile.read(io.BytesIO(z.read(name)))
            y = to_float(data)
            del data
        except Exception as exc:  # noqa: BLE001
            rec["n_unreadable"] += 1
            if len(rec["errors"]) < 5:
                rec["errors"].append("%s: %s" % (name, exc))
            continue
        rec["n_read"] += 1
        rec["rates"][str(rate)] = rec["rates"].get(str(rate), 0) + 1
        rec["seconds_audio"] += len(y) / float(rate)
        try:
            yf, ons, offs, n_chunks = segment_wave(y, rate)
            if n_chunks > 1:
                rec["n_chunked"] += 1
            if len(ons) == 0:
                rec["n_no_syllable"] += 1
                continue
            f = syllable_features(yf, rate, ons, offs)
        except Exception as exc:  # noqa: BLE001
            rec["n_seg_error"] += 1
            if len(rec["errors"]) < 5:
                rec["errors"].append("%s: %s" % (name, exc))
            continue
        widx.extend([wi] * len(ons))
        t_on.extend((start + ons).tolist())
        t_off.extend((start + offs).tolist())
        feats.append(f)
        if (wi + 1) % log_every == 0:
            print("  %s: %d/%d files, %d syllables (%.0f s)" % (bird, wi + 1, len(members),
                                                                 len(t_on), time.time() - t0),
                  flush=True)
    F = np.concatenate(feats) if feats else np.zeros((0, N_MELS * N_T), dtype=np.float32)
    rec["n_syllables"] = int(len(t_on))
    arrs = {"feats": F.astype(np.float16), "t_on": np.asarray(t_on, dtype=np.float64),
            "t_off": np.asarray(t_off, dtype=np.float64),
            "wav_idx": np.asarray(widx, dtype=np.int32), "members": np.asarray(members)}
    return arrs, rec


def label_bird(X, seed=SEED):
    """PRIMARY: PCA(50) -> UMAP 2-D -> HDBSCAN; ROBUSTNESS: k-means(30) on PCA(50)."""
    import umap
    from sklearn.cluster import HDBSCAN, KMeans
    from sklearn.decomposition import PCA
    X = np.asarray(X, dtype=np.float32)
    n = len(X)
    dim = int(min(PCA_DIM, X.shape[1], n - 1))
    Z = PCA(n_components=dim, random_state=seed).fit_transform(X)
    emb = umap.UMAP(n_components=2, n_neighbors=UMAP_NEIGHBORS, min_dist=UMAP_MIN_DIST,
                    random_state=seed).fit_transform(Z)
    mcs = max(HDB_MIN_ABS, int(HDB_MIN_FRAC * n))
    hdb = np.asarray(HDBSCAN(min_cluster_size=mcs, min_samples=1).fit_predict(emb), dtype=np.int64)
    k = int(min(KMEANS_K, n))
    km = np.asarray(KMeans(n_clusters=k, n_init=4, random_state=seed).fit_predict(Z),
                    dtype=np.int64)
    info = {"n": n, "pca_dim": dim, "hdb_min_cluster_size": mcs,
            "hdb_clusters": int(len(set(hdb.tolist()) - {-1})),
            "hdb_noise_frac": float(np.mean(hdb == -1)), "kmeans_k": k}
    return hdb, km, info


# ------------------------------------------------------------------ download

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ensure_zip(path, url, want, tries=3):
    if os.path.exists(path) and md5_file(path) == want:
        return True, os.path.getsize(path)
    for t in range(tries):
        try:
            h, n = hashlib.md5(), 0
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r, open(path + ".part", "wb") as fh:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    h.update(b)
                    fh.write(b)
                    n += len(b)
            if h.hexdigest() == want:
                os.replace(path + ".part", path)
                return True, n
            print("  md5 mismatch on try %d" % (t + 1), flush=True)
        except Exception as exc:  # noqa: BLE001
            print("  try %d failed: %s" % (t + 1, exc), flush=True)
        time.sleep(30)
    if os.path.exists(path + ".part"):
        os.remove(path + ".part")
    return False, 0


def api_checksums():
    meta = json.loads(urllib.request.urlopen(urllib.request.Request(RECORD_API, headers=UA),
                                             timeout=120).read().decode("utf-8"))
    out = {}
    for f in meta.get("files", []):
        out[f.get("key")] = str(f.get("checksum", "")).replace("md5:", "")
    return {"license": str((meta.get("metadata") or {}).get("license")),
            "md5_match": {k: out.get(k) == v for k, v in MD5.items()}}


# ------------------------------------------------------------------ steps

def root_of(data_dir):
    return os.path.join(data_dir, "starling")


def run_load(data_dir, out_dir, seed):
    """Download, segment, featurise and label the four birds; write the design and a load
    report. No mutual information is computed here."""
    bf = _bf()
    root = root_of(data_dir)
    os.makedirs(root, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    try:
        api = api_checksums()
    except Exception as exc:  # noqa: BLE001
        api = {"error": str(exc)}
    per_bird, label_info, days = {}, {}, {"primary": [], "kmeans": []}
    for bird in BIRDS:
        key = bird + ".zip"
        cache = os.path.join(root, "feat7_%s.npz" % bird)
        rec_path = os.path.join(root, "feat7_%s.json" % bird)
        if os.path.exists(cache) and os.path.exists(rec_path):
            rec = load_json(rec_path)
        else:
            zpath = os.path.join(root, key)
            t0 = time.time()
            ok, nbytes = ensure_zip(zpath, FILE_URL.format(key=key), MD5[key])
            print("%s: download ok=%s %d bytes (%.0f s)" % (key, ok, nbytes, time.time() - t0),
                  flush=True)
            if not ok:
                per_bird[bird] = {"md5_ok": False}
                continue
            t0 = time.time()
            arrs, rec = process_zip(zpath, bird)
            rec.update({"md5_ok": True, "zip_bytes": nbytes, "seconds": time.time() - t0})
            np.savez_compressed(cache, **arrs)
            dump(rec_path, rec)
            os.remove(zpath)
            print("%s: %d syllables from %d files (%.0f s)" % (bird, rec["n_syllables"],
                                                               rec["n_read"], rec["seconds"]),
                  flush=True)
        per_bird[bird] = rec
        z = np.load(cache)
        t_on = z["t_on"]
        if len(t_on) < MIN_LABEL_N:
            label_info[bird] = {"n": int(len(t_on)), "skipped": True}
            continue
        t0 = time.time()
        hdb, km, info = label_bird(z["feats"].astype(np.float32), seed)
        info["seconds"] = time.time() - t0
        label_info[bird] = info
        print("%s labels: %s" % (bird, json.dumps(jsonable(info))), flush=True)
        days["primary"].extend(build_bird_days(bird, t_on, hdb))
        days["kmeans"].extend(build_bird_days(bird, t_on, km))
    cp, n_sym = bf.encode_days(days["primary"])
    desc = bf.describe(cp)
    fails = loader_gate7(per_bird, desc)
    report = {"api": api, "per_bird": per_bird, "labels": label_info, "describe": desc,
              "describe_kmeans": bf.describe(bf.encode_days(days["kmeans"])[0]),
              "n_symbols_primary": n_sym, "gate_failures": fails, "loader_ok": not fails,
              "primary_labels_ok": labels_ok(label_info), "design": design_of(cp)}
    dump(os.path.join(out_dir, "load_report7.json"), report)
    dump(os.path.join(root, "days7.json"), days)
    if fails:
        print("LOADER STOP", fails, flush=True)
    return report


def load_days(data_dir):
    raw = load_json(os.path.join(root_of(data_dir), "days7.json"))
    return {arm: [(b, d, [tuple(x) for x in bouts]) for b, d, bouts in raw[arm]] for arm in ARMS}


def synth_design(rng, kind, design, width=18):
    """Stage-4 synthetic birds sung into the real design (birds, days, bouts per day)."""
    bf = _bf()
    birds = sorted({b for b, _, _ in design})
    gens = {b: bf.WORLD_KINDS[kind](rng) for b in birds}
    off = {b: i * width for i, b in enumerate(birds)}
    out = []
    for b, d, nb in design:
        g = gens[b]
        if hasattr(g, "new_day"):
            g.new_day(rng)
        bouts, tries = [], 0
        while len(bouts) < nb and tries < 50 * nb + 50:
            tries += 1
            bt = g.bout(rng)
            if bt:
                bouts.append(tuple(int(w) + off[b] for w in bt))
        out.append((b, d, bouts))
    return out


def run_selfcheck(data_dir, out_dir, seed, n_worlds, n_perm, n_surr):
    bf = _bf()
    lr = load_json(os.path.join(out_dir, "load_report7.json"))
    if not lr or not lr.get("loader_ok"):
        print("SKIP self-check: loader did not pass", flush=True)
        return None
    design = [tuple(x) for x in lr["design"]]
    rows = []
    for wi, kind in enumerate(KINDS):
        for w in range(n_worlds):
            rng = np.random.default_rng([seed, wi, w])
            cdays = synth_design(rng, kind, design)
            r = bf.analyse(cdays, rng, n_perm, n_surr, tag="%s#%d" % (kind, w))
            rows.append({"world": kind, "i": w, "t4a_fire": r["T4a"]["fire_strong"],
                         "real_gap": r["T4a"]["gap"], "t4b_p": r["T4b"]["p_upper"],
                         "t4b_fire_rate": r["T4b"]["fire_rate"], "t4c": r["T4c"]["grade"],
                         "t4c_p": r["T4c"]["p_upper"], "t4c_fire_rate": r["T4c"]["fire_rate"],
                         "k": [v["k"] for v in r["kgram"].values()],
                         "final": bf.final_grade(r["T4c"]["grade"], r["T4b"]["p_upper"], True)})
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
           "design_bouts": int(sum(x[2] for x in design)), "summary": summary,
           "verdict": bf.selfcheck_verdict(summary)}
    dump(os.path.join(out_dir, "selfcheck7.json"), out)
    dump(os.path.join(out_dir, "selfcheck7_worlds.json"), rows)
    print("SELFCHECK7", json.dumps(jsonable(out["verdict"])), flush=True)
    return out


def run_stage7(data_dir, out_dir, seed, n_perm, n_surr):
    bf = _bf()
    lr = load_json(os.path.join(out_dir, "load_report7.json"))
    if not lr or not lr.get("loader_ok"):
        print("SKIP stage 7: loader did not pass", flush=True)
        return None
    days = load_days(data_dir)
    res = {}
    for ai, arm in enumerate(ARMS):
        cdays, n_sym = bf.encode_days(days[arm])
        rng = np.random.default_rng([seed, 7, ai])
        r = bf.analyse(cdays, rng, n_perm, n_surr, tag=arm)
        r["describe"] = bf.describe(cdays)
        r["n_symbols"] = n_sym
        res[arm] = r
    dump(os.path.join(out_dir, "stage7_results.json"), res)
    return res


def grade_from(lr, sc, st, final_grade):
    """Pure grading (final_grade = bf_stage4.final_grade)."""
    g = {"selfcheck": sc["verdict"] if sc else None, "priors": PRIORS}
    if lr is None or not lr.get("loader_ok"):
        g["grade"] = "LOADER_STOP"
        return g
    if st is None or sc is None:
        g["grade"] = "UNRESOLVED_MISSING_OUTPUT"
        return g
    cal = bool(sc["verdict"]["t4c_calibrated"])
    prim, km = st["primary"], st["kmeans"]
    g_km = final_grade(km["T4c"]["grade"], km["T4b"]["p_upper"], cal)
    if lr.get("primary_labels_ok"):
        g_prim = final_grade(prim["T4c"]["grade"], prim["T4b"]["p_upper"], cal)
    else:
        g_prim = "UNRESOLVED_LABELS"
    outcomes = predictions(prim, km, sc["verdict"], g_prim, g_km)
    g.update({"grade": g_prim, "grade_kmeans": g_km, "outcomes": outcomes,
              "brier": brier(PRIORS, outcomes),
              "T7a_primary": {"fire_strong": prim["T4a"]["fire_strong"], "gap": prim["T4a"]["gap"],
                              "best": prim["T4a"]["best"]},
              "T7b_primary": prim["T4b"], "T7c_primary": prim["T4c"],
              "T7a_kmeans": {"fire_strong": km["T4a"]["fire_strong"], "gap": km["T4a"]["gap"],
                             "best": km["T4a"]["best"]},
              "T7b_kmeans": km["T4b"], "T7c_kmeans": km["T4c"],
              "k_primary": {b: v["k"] for b, v in prim["kgram"].items()},
              "k_kmeans": {b: v["k"] for b, v in km["kgram"].items()}})
    return g


def run_grade(out_dir):
    bf = _bf()
    g = grade_from(load_json(os.path.join(out_dir, "load_report7.json")),
                   load_json(os.path.join(out_dir, "selfcheck7.json")),
                   load_json(os.path.join(out_dir, "stage7_results.json")), bf.final_grade)
    dump(os.path.join(out_dir, "grade7.json"), g)
    print("GRADE7", g["grade"], g.get("grade_kmeans"), g.get("brier"), flush=True)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("load")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--seed", type=int, default=SEED)
    s = sub.add_parser("selfcheck")
    s.add_argument("--data-dir", required=True)
    s.add_argument("--out-dir", required=True)
    s.add_argument("--worlds", type=int, default=12)
    s.add_argument("--perm", type=int, default=20)
    s.add_argument("--surr", type=int, default=40)
    s.add_argument("--seed", type=int, default=SEED)
    r = sub.add_parser("stage7")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--perm", type=int, default=100)
    r.add_argument("--surr", type=int, default=100)
    r.add_argument("--seed", type=int, default=SEED)
    gp = sub.add_parser("grade")
    gp.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "load":
        run_load(a.data_dir, a.out_dir, a.seed)
    elif a.cmd == "selfcheck":
        run_selfcheck(a.data_dir, a.out_dir, a.seed, a.worlds, a.perm, a.surr)
    elif a.cmd == "stage7":
        run_stage7(a.data_dir, a.out_dir, a.seed, a.perm, a.surr)
    else:
        run_grade(a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
