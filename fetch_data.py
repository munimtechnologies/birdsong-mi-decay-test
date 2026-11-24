# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Download the public house-finch release (Youngblood 2024; Zenodo concept record 10689807,
version v1.0.1-zenodo = record 10786105, CC BY 4.0), check its size and md5, and extract only the
R data files the registered stages need. Nothing is opened or printed beyond names, sizes and hashes.
Usage: python fetch_data.py <data_dir> <out_dir>"""
import hashlib
import json
import os
import sys
import urllib.request
import zipfile

URLS = [
    "https://zenodo.org/api/records/10786105/files/masonyoungblood/linguistic_efficiency-v1.0.1-zenodo.zip/content",
    "https://zenodo.org/api/records/10786105/files/masonyoungblood%2Flinguistic_efficiency-v1.0.1-zenodo.zip/content",
]
MD5 = "e5770657a37ebe3d7d0a40461d40ce75"
SIZE = 95781849
WANT = ("docs/data_models/processed_data.RData", "docs/data_models/mi_data.RData",
        "docs/data_models/mi_models.RData", "docs/data_models/mi_models_bout_level.RData",
        "docs/data_models/mi_simulated.RData")


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(zpath):
    last = None
    for url in URLS:
        try:
            tmp = zpath + ".part"
            with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as fh:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
            os.replace(tmp, zpath)
            return url
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError("download failed: %s" % last)


def main(data_dir, out_dir):
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    zpath = os.path.join(data_dir, "linguistic_efficiency-v1.0.1-zenodo.zip")
    url = "cached"
    if not (os.path.exists(zpath) and os.path.getsize(zpath) == SIZE and file_md5(zpath) == MD5):
        url = download(zpath)
    size, md5 = os.path.getsize(zpath), file_md5(zpath)
    if size != SIZE or md5 != MD5:
        print("zip check FAILED: size %d md5 %s" % (size, md5), flush=True)
        return 1
    extracted = {}
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            for want in WANT:
                if info.filename.endswith(want):
                    target = os.path.join(data_dir, os.path.basename(want))
                    with zf.open(info) as src, open(target, "wb") as dst:
                        while True:
                            chunk = src.read(1 << 20)
                            if not chunk:
                                break
                            dst.write(chunk)
                    extracted[os.path.basename(want)] = {
                        "zip_member": info.filename, "bytes": os.path.getsize(target),
                        "sha256": file_sha256(target)}
    report = {"zip_url": url, "zip_bytes": size, "zip_md5": md5, "licence": "CC BY 4.0 (Zenodo record)",
              "extracted": extracted, "missing": [w for w in WANT if os.path.basename(w) not in extracted]}
    for path in (os.path.join(data_dir, "fetch.json"), os.path.join(out_dir, "fetch.json")):
        with open(path, "w") as fh:
            json.dump(report, fh, indent=1)
    print(json.dumps(report, indent=1), flush=True)
    return 0 if not report["missing"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
