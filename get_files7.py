# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Fetch the registered code stage 7 reuses, pinned by git blob SHA-1, into one folder:
mi_decay.py (stage-1 core: MI curve, fits, firing rule) and bf_stage4.py (stage-4 k-gram
finite-memory null, permutation test, grading rules and synthetic self-check worlds).
Tries raw main first, then the blob API by SHA. Usage: python get_files7.py <folder>"""
import base64
import hashlib
import json
import os
import sys
import urllib.request

REPO = "munimtechnologies/birdsong-mi-decay-test"
FILES = {
    "mi_decay.py": "83d578e3d03d130ac31f5cb4da5b3eb9bb077659",
    "bf_stage4.py": "0a58a89e4f7b7c4ceb327d12b71ac0dd65f8ae4e",
}


def blob_sha(data):
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def fetch(name, sha):
    raw = "https://raw.githubusercontent.com/%s/main/%s" % (REPO, name)
    try:
        data = urllib.request.urlopen(raw, timeout=120).read()
        if blob_sha(data) == sha:
            return data
        print("raw %s: blob differs, trying the pinned blob" % name, flush=True)
    except Exception as exc:  # noqa: BLE001
        print("raw %s: %s" % (name, exc), flush=True)
    api = "https://api.github.com/repos/%s/git/blobs/%s" % (REPO, sha)
    req = urllib.request.Request(api, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "mv2-birdsong-mi-decay-test"})
    body = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
    data = base64.b64decode(body["content"])
    if blob_sha(data) != sha:
        raise RuntimeError("blob mismatch for %s" % name)
    return data


def main(folder):
    os.makedirs(folder, exist_ok=True)
    for name, sha in FILES.items():
        data = fetch(name, sha)
        with open(os.path.join(folder, name), "wb") as fh:
            fh.write(data)
        print("%s blob %s -> %s" % (name, sha, folder), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
