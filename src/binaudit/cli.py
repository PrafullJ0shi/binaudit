"""Command line interface: binaudit summary | compare | report | lookup | sample."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .io import AuditFileError, load_catalogue, lookup, read_csv, to_csv
from .report import comparison_line, markdown_report, summary_table
from .sample import make_sample
from .stats import bins, compare, phases, summarise


def _add_boot(p: argparse.ArgumentParser) -> None:
    p.add_argument("--draws", type=int, default=2000, help="bootstrap draws (default 2000)")
    p.add_argument("--seed", type=int, default=7, help="random seed (default 7)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="binaudit", description="Bin audits for hostels and wards.")
    p.add_argument("--version", action="version", version=f"binaudit {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summary", help="contamination rate per site, bin and phase")
    s.add_argument("csv", type=Path)
    s.add_argument("--json", action="store_true", help="print JSON instead of a table")
    _add_boot(s)

    c = sub.add_parser("compare", help="before/after difference for every bin")
    c.add_argument("csv", type=Path)
    c.add_argument("--before", help="phase label (default: first phase in the file)")
    c.add_argument("--after", help="phase label (default: last phase in the file)")
    c.add_argument("--json", action="store_true")
    _add_boot(c)

    r = sub.add_parser("report", help="Markdown report")
    r.add_argument("csv", type=Path)
    r.add_argument("-o", "--output", type=Path, help="write to a file instead of stdout")
    _add_boot(r)

    lk = sub.add_parser("lookup", help="find the right stream for an item")
    lk.add_argument("item", nargs="+")

    sm = sub.add_parser("sample", help="write the labelled synthetic sample CSV")
    sm.add_argument("-o", "--output", type=Path, help="write to a file instead of stdout")
    sm.add_argument("--seed", type=int, default=2026)
    return p


def _write(text: str, path: Path | None) -> None:
    if path is None:
        sys.stdout.write(text)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "summary":
            sums = summarise(read_csv(args.csv), B=args.draws, seed=args.seed)
            if args.json:
                print(json.dumps([asdict(s) for s in sums], indent=1))
            else:
                print(summary_table(sums))
        elif args.cmd == "compare":
            rows = read_csv(args.csv)
            ph = phases(rows)
            before, after = args.before or ph[0], args.after or ph[-1]
            if before == after:
                print("Need two different phases to compare.", file=sys.stderr)
                return 2
            out = []
            for site, bin_stream in bins(rows):
                cmp = compare(rows, site, bin_stream, before, after, B=args.draws, seed=args.seed)
                if cmp:
                    out.append(cmp)
            if args.json:
                print(json.dumps([asdict(c) for c in out], indent=1))
            else:
                for cmp in out:
                    print(comparison_line(cmp))
        elif args.cmd == "report":
            _write(markdown_report(read_csv(args.csv), B=args.draws, seed=args.seed), args.output)
        elif args.cmd == "lookup":
            hits = lookup(" ".join(args.item), load_catalogue())
            if not hits:
                print("No match in the catalogue.", file=sys.stderr)
                return 1
            for h in hits:
                note = f"  {h['note']}" if h.get("note") else ""
                print(f"{h['name']}: {h['stream']}{note}")
        elif args.cmd == "sample":
            _write(to_csv(make_sample(args.seed)), args.output)
    except (AuditFileError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
