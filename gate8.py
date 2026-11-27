# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage 8 job gate: compute nothing until AMENDMENT-8-STAGE8.md and the stage-8 code on GitHub
main equal the job's own copies (CRLF normalised); then fetch the unchanged stage-1 pipeline
mi_decay.py from the public repository into MV2_LIB and log its sha256. Waits at most 60 minutes.
Usage: python gate8.py /out"""
import hashlib
import json
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/"
FILES = ["AMENDMENT-8-STAGE8.md", "stage8.py", "grade8.py", "gate8.py", "test_stage8.py"]
LIB = os.environ.get("MV2_LIB", "/tmp/mv2-stage8")


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
    deadline = time.time() + 60 * 60
    while True:
        ok, lines = check()
        print("\n".join(lines), flush=True)
        if ok:
            break
        if time.time() > deadline:
            print("gate failed: public copies missing or different after 60 min; nothing computed",
                  flush=True)
            return 1
        time.sleep(300)
    blob = fetch("mi_decay.py")
    text = blob.decode("utf-8")
    for needle in ("def fit_curve", "def lin_tegmark_sequence", "def world_w4", "def clean"):
        if needle not in text:
            print("gate failed: public mi_decay.py lacks %r" % needle, flush=True)
            return 1
    os.makedirs(LIB, exist_ok=True)
    with open(os.path.join(LIB, "mi_decay.py"), "wb") as fh:
        fh.write(blob)
    info = {"gate": lines, "mi_decay_sha256": hashlib.sha256(blob).hexdigest(),
            "mi_decay_sha256_lf": hashlib.sha256(norm(blob)).hexdigest(),
            "mi_decay_bytes": len(blob), "lib": LIB, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "gate8.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    print("plan and code are public and identical; mi_decay.py sha256 %s" % info["mi_decay_sha256"],
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
