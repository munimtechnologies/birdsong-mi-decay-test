# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name. MV2, Munim, Inc., mv2@munimtech.com
"""Stage 6B dependencies and registration gate.

1. Fetch the registered code of munimtechnologies/birdsong-mi-decay-test that stage 6B runs on
   (mi_decay.py, bf_stage4.py, speech_stage6.py) and check each file's git blob SHA-1.
2. Check that AMENDMENT-6B-STAGE6B-SPEECH-SIZE.md, stage6b.py and test_stage6b.py on GitHub (main)
   equal this job's own copies, so nothing runs before its registration is public. Tries 3 times,
   10 minutes apart.
Exit 1 on any failure: no analysis runs on other code or before registration.
"""
import hashlib
import os
import sys
import time
import urllib.request

REPO = "munimtechnologies/birdsong-mi-decay-test"
DEPS = {"mi_decay.py": "83d578e3d03d130ac31f5cb4da5b3eb9bb077659",
        "bf_stage4.py": "0a58a89e4f7b7c4ceb327d12b71ac0dd65f8ae4e",
        "speech_stage6.py": "ce357898083f01fca01ad1788628e79b296241f9"}
REGISTERED = ("AMENDMENT-6B-STAGE6B-SPEECH-SIZE.md", "stage6b.py", "test_stage6b.py")
UA = {"User-Agent": "mv2-research-job/1.0"}


def blob_sha(data):
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def get(url, headers=UA):
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120).read()


def fetch_pinned(name, sha):
    tries = [(f"https://api.github.com/repos/{REPO}/git/blobs/{sha}",
              dict(UA, Accept="application/vnd.github.raw")),
             (f"https://raw.githubusercontent.com/{REPO}/main/{name}", UA)]
    for url, headers in tries:
        try:
            data = get(url, headers)
        except Exception as exc:  # noqa: BLE001
            print(f"{name}: {url} failed: {exc}", flush=True)
            continue
        got = blob_sha(data)
        if got == sha:
            return data
        print(f"{name}: {url} gave blob {got}, want {sha}", flush=True)
    return None


def norm(b):
    return b.replace(b"\r\n", b"\n")


def registration_ok(here):
    for name in REGISTERED:
        with open(os.path.join(here, name), "rb") as fh:
            mine = norm(fh.read())
        try:
            theirs = norm(get(f"https://raw.githubusercontent.com/{REPO}/main/{name}"))
        except Exception as exc:  # noqa: BLE001
            print(f"registration {name}: fetch failed: {exc}", flush=True)
            return False
        same = hashlib.sha256(mine).hexdigest() == hashlib.sha256(theirs).hexdigest()
        print(f"registration {name}: {'same' if same else 'DIFFERENT'} "
              f"sha256 {hashlib.sha256(mine).hexdigest()}", flush=True)
        if not same:
            return False
    return True


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    for name, sha in DEPS.items():
        data = fetch_pinned(name, sha)
        if data is None:
            print(f"BLOB MISMATCH or download failure for {name}", flush=True)
            return 1
        written = False
        for folder in (here, "/data/core"):
            try:
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, name), "wb") as fh:
                    fh.write(data)
                print(f"{name} blob {sha} sha256 {hashlib.sha256(data).hexdigest()} -> {folder}",
                      flush=True)
                written = True
                break
            except OSError as exc:
                print(f"cannot write {folder}: {exc}", flush=True)
        if not written:
            return 1
    for attempt in range(3):
        if registration_ok(here):
            print("REGISTRATION GATE OK", flush=True)
            return 0
        if attempt < 2:
            time.sleep(600)
    print("REGISTRATION GATE FAILED: the job's files differ from GitHub main", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
