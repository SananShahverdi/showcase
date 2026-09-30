"""Command-line report: python -m quant_research_lab.cli <dataset-id | path/to/prices.csv>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quant_research_lab.algorithms.data import DataError
from quant_research_lab.services.lab_service import BUNDLED, LabService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help=f"Bundled dataset ({', '.join(BUNDLED)}) or a CSV path")
    parser.add_argument("-o", "--output", type=Path, help="Write the Markdown report to this file")
    args = parser.parse_args(argv)

    lab = LabService()
    dataset_id = args.dataset
    if dataset_id not in BUNDLED:
        path = Path(args.dataset)
        try:
            dataset_id = lab.upload(path.stem, path.read_text(encoding="utf-8")).id
        except (OSError, DataError) as exc:
            print(f"Cannot use {path}: {exc}", file=sys.stderr)
            return 1
    report = lab.report(dataset_id)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
