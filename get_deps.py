"""Fetch the registered stage-1 core (mi_decay.py) and the registered stage-4 code (bf_stage4.py)
of munimtechnologies/birdsong-mi-decay-test and check each file's git blob SHA-1.

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.
Writes the files next to this file; if that folder is read-only, to /data/core.
"""
import hashlib
import os
import sys
import urllib.request

REPO = "munimtechnologies/birdsong-mi-decay-test"
DEPS = {"mi_decay.py": "83d578e3d03d130ac31f5cb4da5b3eb9bb077659",
        "bf_stage4.py": "0a58a89e4f7b7c4ceb327d12b71ac0dd65f8ae4e"}
UA = {"User-Agent": "mv2-research-job/1.0"}


def blob_sha(data):
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def fetch(name, sha):
    """Raw content of the pinned blob: the git blobs API first, then raw main; None if neither
    gives bytes with the pinned SHA."""
    tries = [(f"https://api.github.com/repos/{REPO}/git/blobs/{sha}",
              dict(UA, Accept="application/vnd.github.raw")),
             (f"https://raw.githubusercontent.com/{REPO}/main/{name}", UA)]
    for url, headers in tries:
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                          timeout=120).read()
        except Exception as exc:  # noqa: BLE001
            print(f"{name}: {url} failed: {exc}", flush=True)
            continue
        got = blob_sha(data)
        if got == sha:
            return data
        print(f"{name}: {url} gave blob {got}, want {sha}", flush=True)
    return None


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    for name, sha in DEPS.items():
        data = fetch(name, sha)
        if data is None:
            print(f"BLOB MISMATCH or download failure for {name}", flush=True)
            return 1
        written = False
        for folder in (here, "/data/core"):
            try:
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, name), "wb") as fh:
                    fh.write(data)
                print(f"{name} blob {sha} -> {folder}", flush=True)
                written = True
                break
            except OSError as exc:
                print(f"cannot write {folder}: {exc}", flush=True)
        if not written:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
