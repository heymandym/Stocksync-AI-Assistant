"""Command-line entry point: python -m stocksync run --input FILE.xlsx"""

from __future__ import annotations

import argparse
import sys

from .pipeline import DEFAULT_MODEL, DEFAULT_THRESHOLD, run_pipeline
from .reconcile import BELOW, INVALID, OK, REVIEW


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stocksync", description="Inventory reconciliation workflow (synthetic data).")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Validate, calculate and write outputs for one workbook.")
    run.add_argument("--input", required=True, help="Path to the .xlsx workbook.")
    run.add_argument("--out", default="outputs", help="Output directory (default: outputs/).")
    run.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                     help=f"Accuracy threshold between 0 and 1 (default: {DEFAULT_THRESHOLD}).")
    run.add_argument("--llm", action="store_true", help="Add an AI narrative summary (needs ANTHROPIC_API_KEY).")
    run.add_argument("--model", default=DEFAULT_MODEL, help=f"Model for --llm (default: {DEFAULT_MODEL}).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_pipeline(args.input, args.out, threshold=args.threshold, use_llm=args.llm, model=args.model)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    counts = result.results["Status"].value_counts()
    print(f"Rows: {len(result.results)}")
    print(f"  OK: {counts.get(OK, 0)}  Below threshold: {counts.get(BELOW, 0)}  "
          f"Review required: {counts.get(REVIEW, 0)}  Invalid input: {counts.get(INVALID, 0)}")
    print(f"Validation issues: {len(result.issues)}")
    for label, path in result.files.items():
        print(f"Wrote {label}: {path}")
    return 0
