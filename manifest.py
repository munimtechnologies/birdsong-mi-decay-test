# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage-1 loader manifest for the house-finch R data files: object names, classes, shapes,
column names, dtypes and counts of distinct values. No data values are written, so the stage-2
loader can be registered (AMENDMENT-1) before any MI is computed on real songs.
Usage: python manifest.py <data_dir> <out_dir>"""
import json
import os
import sys

FILES = ("processed_data.RData", "mi_data.RData", "mi_models.RData", "mi_models_bout_level.RData",
         "mi_simulated.RData")


def n_unique(col):
    try:
        return int(col.nunique(dropna=True))
    except Exception:  # noqa: BLE001
        return None


def describe(obj, depth=0):
    d = {"type": type(obj).__module__ + "." + type(obj).__name__}
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            d["shape"] = [int(v) for v in obj.shape]
            d["columns"] = []
            for c in obj.columns:
                col = obj[c]
                entry = {"name": str(c), "dtype": str(col.dtype), "n_unique": n_unique(col),
                         "n_missing": int(col.isna().sum())}
                if str(col.dtype) == "category":
                    entry["n_levels"] = int(col.cat.categories.size)
                d["columns"].append(entry)
            return d
        if isinstance(obj, pd.Series):
            d["length"] = int(len(obj))
            d["dtype"] = str(obj.dtype)
            d["n_unique"] = n_unique(obj)
            return d
    except ImportError:
        pass
    if isinstance(obj, dict):
        keys = list(obj)
        d["n_keys"] = len(keys)
        if depth < 3:
            d["keys"] = {str(k): describe(obj[k], depth + 1) for k in keys[:60]}
        return d
    if isinstance(obj, (list, tuple)):
        d["length"] = len(obj)
        if obj and depth < 3:
            d["first"] = describe(obj[0], depth + 1)
        return d
    if hasattr(obj, "shape"):
        d["shape"] = [int(v) for v in getattr(obj, "shape")]
        d["dtype"] = str(getattr(obj, "dtype", ""))
        if hasattr(obj, "dims"):
            d["dims"] = [str(v) for v in obj.dims]
        return d
    return d


def read(path):
    import rdata
    if hasattr(rdata, "read_rda"):
        return rdata.read_rda(path)
    return rdata.conversion.convert(rdata.parser.parse_file(path))


def main(data_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    for name in FILES:
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            report[name] = {"error": "missing"}
            continue
        try:
            report[name] = {"bytes": os.path.getsize(path), "objects": describe(read(path))}
        except Exception as exc:  # noqa: BLE001
            report[name] = {"bytes": os.path.getsize(path), "error": "%s: %s" % (type(exc).__name__, exc)}
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps(report, indent=1)[:20000], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
