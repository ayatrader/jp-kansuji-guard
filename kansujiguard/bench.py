"""Bench: does a converter turn kanji numerals into digits without breaking names, places, words and idioms?

python -m kansujiguard.bench                 # score this tool and the naive baseline
python -m kansujiguard.bench --write data/   # write data/kansuji_guard_bench_v1.jsonl
python -m kansujiguard.bench --module mypkg.mod:func   # score your own converter (str -> str)
"""
import argparse
import importlib
import json
import os
from collections import OrderedDict

from .cases import all_cases
from .guard import convert, naive_convert

FILE = "kansuji_guard_bench_v1.jsonl"


def score(fn, rows=None):
    """fn: str -> str. Returns {overall, by_category, failures}. Exact match of the whole output."""
    rows = rows or all_cases()
    by = OrderedDict()
    failures = []
    for r in rows:
        got = fn(r["input"])
        ok = got == r["expected"]
        c = by.setdefault(r["category"], [0, 0])
        c[0] += ok
        c[1] += 1
        if not ok:
            failures.append({"id": r["id"], "input": r["input"], "expected": r["expected"], "got": got})
    total = sum(v[0] for v in by.values())
    n = sum(v[1] for v in by.values())
    return {"overall": {"correct": total, "total": n, "accuracy": round(total / n, 4)},
            "by_category": {k: {"correct": v[0], "total": v[1]} for k, v in by.items()},
            "failures": failures}


def write(dirpath):
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, FILE)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in all_cases():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _load(spec):
    mod, _, func = spec.partition(":")
    return getattr(importlib.import_module(mod), func)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kansujiguard.bench")
    ap.add_argument("--write", metavar="DIR")
    ap.add_argument("--module", metavar="MOD:FUNC")
    a = ap.parse_args(argv)
    if a.write:
        print(write(a.write))
        return
    runs = {"naive (convert every numeral)": naive_convert, "kansujiguard": lambda t: convert(t)["text"]}
    if a.module:
        runs = {a.module: _load(a.module)}
    for name, fn in runs.items():
        s = score(fn)
        o = s["overall"]
        cats = ", ".join(f"{k} {v['correct']}/{v['total']}" for k, v in s["by_category"].items())
        print(f"{name}: {o['correct']}/{o['total']} ({o['accuracy']:.1%})  [{cats}]")


if __name__ == "__main__":
    main()
