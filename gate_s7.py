"""Refuse to run stage 7 unless AMENDMENT-7-STAGE7-STARLING.md AND the exact stage-7 code are
public in the repository first (registration before data).

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.

The marker is matched with every run of whitespace (line breaks included) collapsed to one space
(lesson of 2026-11-26: markdown wraps lines). The code check compares the local starling_stage7.py
with the public one after normalising line endings and trailing spaces.
"""
import os
import sys
import time
import urllib.request

RAW = "https://raw.githubusercontent.com/munimtechnologies/birdsong-mi-decay-test/main/"
AMENDMENT = "AMENDMENT-7-STAGE7-STARLING.md"
CODE = ("starling_stage7.py",)
MARK = "registered BEFORE any starling audio was downloaded by this study"


def squash(text):
    return " ".join(text.split())


def has_mark(text, mark=MARK):
    return squash(mark) in squash(text)


def norm_code(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def same_code(local_text, public_text):
    return norm_code(local_text) == norm_code(public_text)


def fetch(name):
    return urllib.request.urlopen(RAW + name, timeout=60).read().decode("utf-8", "replace")


def check_once(here):
    if not has_mark(fetch(AMENDMENT)):
        return "marker missing"
    for name in CODE:
        with open(os.path.join(here, name), encoding="utf-8") as fh:
            local = fh.read()
        if not same_code(local, fetch(name)):
            return f"{name} differs from the public copy"
    return ""


def main(tries=8, wait=600):
    here = os.path.dirname(os.path.abspath(__file__))
    for i in range(tries):
        try:
            why = check_once(here)
            if not why:
                print(f"amendment and code live (try {i + 1})", flush=True)
                return 0
            print(f"try {i + 1}: {why}", flush=True)
        except Exception as exc:  # 404 before the commit lands
            print(f"try {i + 1}: {exc}", flush=True)
        if i + 1 < tries:
            time.sleep(wait)
    print("AMENDMENT OR CODE NOT LIVE: refusing to run", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
