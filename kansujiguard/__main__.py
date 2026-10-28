"""CLI: python -m kansujiguard input.txt [--json]  (reads stdin when no file is given)."""
import argparse
import json
import sys

from .guard import convert


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kansujiguard", description="Convert kanji numerals in Japanese text without breaking names and idioms")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--json", action="store_true", help="print changes, kept spans and flags as JSON")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    r = convert(text)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        sys.stdout.write(r["text"])
        for f in r["flags"]:
            print(f"# check {f['text']}: {f['reason']}", file=sys.stderr)


if __name__ == "__main__":
    main()
