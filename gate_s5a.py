# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Gate for AMENDMENT-5A: refuse to run until the amendment and vireo_s5a.py are public with the
same content as the copies in this job, then fetch the registered stage-5 code from the public
repository (sha256 logged) and run its get_deps (pinned blobs of mi_decay.py and bf_stage4.py).

Usage: python gate_s5a.py /out
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/"
UA = {"User-Agent": "mv2-research-job/1.0"}
MARK = "BEFORE any cell of S1 Table of Hedley (2016) was read by us"
SAME = ("AMENDMENT-5A-VIREO-LOADER.md", "vireo_s5a.py", "test_vireo_s5a.py", "gate_s5a.py")
FETCH = ("vireo_stage5.py", "test_vireo_stage5.py", "get_deps.py")
HERE = os.path.dirname(os.path.abspath(__file__))
CORE = "/data/core5a"


def _get(url):
    req = urllib.request.Request(url + "?t=%d" % int(time.time()), headers=UA)
    return urllib.request.urlopen(req, timeout=60).read()


def _norm_md5(data):
    return hashlib.md5(data.replace(b"\r\n", b"\n")).hexdigest()


def wait_public(tries=8, wait=600):
    log = []
    for i in range(tries):
        ok, log = True, []
        for name in SAME:
            with open(os.path.join(HERE, name), "rb") as fh:
                local = _norm_md5(fh.read())
            try:
                data = _get(RAW + name)
            except Exception as exc:  # noqa: BLE001  (404 before the commit lands)
                log.append("%s: %s" % (name, exc))
                ok = False
                continue
            remote = _norm_md5(data)
            if name.endswith(".md") and MARK.encode() not in data:
                log.append("%s: marker missing" % name)
                ok = False
            log.append("%s local %s remote %s %s" % (name, local, remote,
                                                      "same" if local == remote else "DIFFERENT"))
            ok = ok and local == remote
        print("try %d: %s" % (i + 1, "; ".join(log)), flush=True)
        if ok:
            return True, log
        if i + 1 < tries:
            time.sleep(wait)
    return False, log


def fetch_registered():
    got = {}
    for name in FETCH:
        data = _get(RAW + name)
        if name == "vireo_stage5.py" and b"api.figshare.com/v2/articles/3081814" not in data:
            raise RuntimeError("vireo_stage5.py does not look like the registered stage-5 code")
        written = None
        for folder in (HERE, CORE):
            try:
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, name), "wb") as fh:
                    fh.write(data)
                written = folder
                break
            except OSError as exc:
                print("cannot write %s: %s" % (folder, exc), flush=True)
        if written is None:
            raise RuntimeError("no writable folder for %s" % name)
        got[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                     "folder": written}
        print("%s -> %s (sha256 %s)" % (name, written, got[name]["sha256"]), flush=True)
    return got


def main(argv):
    out = argv[1] if len(argv) > 1 else "/out"
    os.makedirs(out, exist_ok=True)
    ok, log = wait_public()
    rec = {"gate": log, "public_ok": ok, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if not ok:
        rec["stop"] = "AMENDMENT 5A NOT LIVE OR DIFFERENT: refusing to run"
        with open(os.path.join(out, "gate5a.json"), "w") as fh:
            json.dump(rec, fh, indent=1)
        print(rec["stop"], flush=True)
        return 1
    rec["registered"] = fetch_registered()
    folder = rec["registered"]["get_deps.py"]["folder"]
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import get_deps  # registered: fetches pinned blobs next to itself, else /data/core
    rc = get_deps.main()
    rec["get_deps_exit"] = rc
    with open(os.path.join(out, "gate5a.json"), "w") as fh:
        json.dump(rec, fh, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
