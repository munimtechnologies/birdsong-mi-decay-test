# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Refuse to run the house-finch stage-2 test unless AMENDMENT-1-FINCH-LOADER.md is public first
and identical (line endings aside) to this job's copy, and AMENDMENT-0 is public too."""
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/"
A0 = ("AMENDMENT-0-STAGE2.md", "BEFORE any stage-1 result came back")
A1 = "AMENDMENT-1-FINCH-LOADER.md"


def norm(b):
    return b.replace(b"\r\n", b"\n").strip()


def check():
    a0 = urllib.request.urlopen(RAW + A0[0], timeout=60).read().decode("utf-8", "replace")
    if A0[1] not in a0:
        return "AMENDMENT-0 marker missing"
    remote = urllib.request.urlopen(RAW + A1, timeout=60).read()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, A1), "rb") as fh:
        local = fh.read()
    if norm(remote) != norm(local):
        return "AMENDMENT-1 on GitHub differs from the job's copy"
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
