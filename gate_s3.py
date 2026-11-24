"""Refuse to run stage 3 unless both stage-3 amendments are public first and the code-choices
amendment on GitHub is identical (line endings aside) to this job's copy.

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.
"""
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/"
A2 = ("AMENDMENT-2-STAGE3-CHIMP.md", "Registered before any of the data below was downloaded")
A3 = "AMENDMENT-3-STAGE3-CODE.md"


def norm(b):
    return b.replace(b"\r\n", b"\n").strip()


def check():
    a2 = urllib.request.urlopen(RAW + A2[0], timeout=60).read().decode("utf-8", "replace")
    if A2[1] not in a2:
        return "AMENDMENT-2 marker missing"
    remote = urllib.request.urlopen(RAW + A3, timeout=60).read()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, A3), "rb") as fh:
        local = fh.read()
    if norm(remote) != norm(local):
        return "AMENDMENT-3 on GitHub differs from the job's copy"
    return None


def main(tries=8, wait=600):
    for i in range(tries):
        try:
            problem = check()
            if problem is None:
                print(f"amendments live and identical (try {i + 1})", flush=True)
                return 0
            print(f"try {i + 1}: {problem}", flush=True)
        except Exception as exc:  # 404 before the commit lands
            print(f"try {i + 1}: {exc}", flush=True)
        if i + 1 < tries:
            time.sleep(wait)
    print("AMENDMENTS NOT LIVE: refusing to run", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
