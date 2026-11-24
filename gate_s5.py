"""Refuse to run stage 5 unless AMENDMENT-5-STAGE5-VIREO.md is public first.

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.
"""
import sys
import time
import urllib.request

URL = ("https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/"
       "main/AMENDMENT-5-STAGE5-VIREO.md")
MARK = "registered BEFORE any Cassin's vireo annotation was downloaded"


def main(tries=8, wait=600):
    for i in range(tries):
        try:
            text = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8", "replace")
            if MARK in text:
                print(f"amendment live (try {i + 1})", flush=True)
                return 0
            print(f"try {i + 1}: marker missing", flush=True)
        except Exception as exc:  # 404 before the commit lands
            print(f"try {i + 1}: {exc}", flush=True)
        if i + 1 < tries:
            time.sleep(wait)
    print("AMENDMENT NOT LIVE: refusing to run", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
