# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Fetch the registered code this job runs, pinned by git blob SHA-1, into one folder:
mi_decay.py (stage-1 core), mi_stage2.py (AMENDMENT-0 stage-2 tests), fetch_data.py (download
and md5 check of the authors' release). Tries raw main first, then the blob API by SHA.
Usage: python get_files.py <folder>"""
import base64
import hashlib
import json
import os
import sys
import urllib.request

REPO = "munimtechnologies/birdsong-mi-decay-test"
FILES = {
    "mi_decay.py": "83d578e3d03d130ac31f5cb4da5b3eb9bb077659",
    "mi_stage2.py": "a962139cf96146ab246adbbea64c64cb4522cf1c",
    "fetch_data.py": "c682679f0f25d32f48a93891429eb4752173e274",
}


def blob_sha(data):
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def fetch(name, sha):
    raw = "https://raw.githubusercontent.com/%s/main/%s" % (REPO, name)
    try:
        data = urllib.request.urlopen(raw, timeout=120).read()
        if blob_sha(data) == sha:
            return data
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
