"""Refuse to run the stage-2 self-check unless AMENDMENT-0-STAGE2.md is public first.

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.

Fix of 2026-11-26: the marker is searched with all runs of whitespace (including line breaks)
collapsed to one space, because the public amendment wraps the marker phrase across two lines.
Version 1 of this gate compared the raw text and refused to run although the amendment was live.
"""
import sys
import time
import urllib.request

URL = ("https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/"
       "main/AMENDMENT-0-STAGE2.md")
MARK = "BEFORE any stage-1 result came back"


def squash(text):
    return " ".join(text.split())


def has_mark(text, mark=MARK):
    return squash(mark) in squash(text)


def main(tries=8, wait=600):
    for i in range(tries):
        try:
            text = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8", "replace")
            if has_mark(text):
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
