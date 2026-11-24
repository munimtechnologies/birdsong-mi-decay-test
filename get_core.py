"""Fetch the registered stage-1 core (mi_decay.py) and check its git blob SHA-1.

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.
Writes mi_decay.py next to this file; if that folder is read-only, to /data/core.
"""
import hashlib
import os
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/mi_decay.py"
BLOB = "83d578e3d03d130ac31f5cb4da5b3eb9bb077659"


def blob_sha(data):
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def main():
    data = urllib.request.urlopen(URL, timeout=120).read()
    got = blob_sha(data)
    if got != BLOB:
        print(f"BLOB MISMATCH {got} != {BLOB}", flush=True)
        return 1
    here = os.path.dirname(os.path.abspath(__file__))
    for folder in (here, "/data/core"):
        try:
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "mi_decay.py"), "wb") as fh:
                fh.write(data)
            print(f"mi_decay.py blob {got} -> {folder}", flush=True)
            return 0
        except OSError as exc:
            print(f"cannot write {folder}: {exc}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
