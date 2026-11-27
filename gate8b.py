# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage 8B job gate: compute nothing until AMENDMENT-8B-STAGE8B.md and the stage-8B code on
GitHub main equal the job's own copies (CRLF normalised); then fetch the unchanged stage-1
pipeline mi_decay.py and the stage-8 worlds (stage8.py, grade8.py) from the public repository
into MV2_LIB and log their sha256. Waits at most 80 minutes.
Usage: python gate8b.py /out"""
import hashlib
import json
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/"
FILES = ["AMENDMENT-8B-STAGE8B.md", "stage8b.py", "grade8b.py", "gate8b.py", "test_stage8b.py"]
LIB_FILES = {"mi_decay.py": ("def fit_curve", "def group_chain", "def world_w2", "def clean"),
             "stage8.py": ("def world_f6", "def world_r1", "def world_r5"),
             "grade8.py": ("def real_data_readout",)}
LIB = os.environ.get("MV2_LIB", "/tmp/mv2-stage8b")


def norm(blob):
    return blob.replace(b"\r\n", b"\n")


def fetch(name):
    with urllib.request.urlopen(RAW + name + "?t=%d" % int(time.time()), timeout=60) as r:
        return r.read()


def check():
    ok, lines = True, []
    for name in FILES:
        with open(name, "rb") as fh:
            lm = hashlib.md5(norm(fh.read())).hexdigest()
        try:
            rm = hashlib.md5(norm(fetch(name))).hexdigest()
        except Exception as exc:  # noqa: BLE001
            lines.append("%s local %s remote fetch failed: %s" % (name, lm, exc))
            ok = False
            continue
        lines.append("%s local %s remote %s %s" % (name, lm, rm, "same" if lm == rm else "DIFFERENT"))
        ok = ok and lm == rm
    return ok, lines


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    deadline = time.time() + 80 * 60
    while True:
        ok, lines = check()
        print("\n".join(lines), flush=True)
        if ok:
            break
        if time.time() > deadline:
            print("gate failed: public copies missing or different after 80 min; nothing computed",
                  flush=True)
            return 1
        time.sleep(300)
    os.makedirs(LIB, exist_ok=True)
    info = {"gate": lines, "lib": LIB, "lib_sha256": {}, "lib_sha256_lf": {},
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for name, needles in LIB_FILES.items():
        blob = fetch(name)
        text = blob.decode("utf-8")
        for needle in needles:
            if needle not in text:
                print("gate failed: public %s lacks %r" % (name, needle), flush=True)
                return 1
        with open(os.path.join(LIB, name), "wb") as fh:
            fh.write(blob)
        info["lib_sha256"][name] = hashlib.sha256(blob).hexdigest()
        info["lib_sha256_lf"][name] = hashlib.sha256(norm(blob)).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "gate8b.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    print("plan and code are public and identical; library sha256 %s" % json.dumps(info["lib_sha256"]),
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
