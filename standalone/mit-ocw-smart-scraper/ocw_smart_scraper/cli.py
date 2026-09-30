"""Command-line interface for the OCW Smart Scraper."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from .backtest import BacktestRunner
from .config import RuntimeConfig, load_config
from .pipeline import ScraperPipeline
from .self_test import SelfTestRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MIT OCW Smart Scraper v2.0")
    parser.add_argument("search_url", nargs="?", help="MIT OCW search URL to crawl")
    parser.add_argument("--config", type=Path, help="Path to config.yaml")
    parser.add_argument("--limit", type=int, help="Limit the number of courses processed")
    parser.add_argument("--no-selenium", action="store_true", help="Disable Selenium discovery fallback")
    parser.add_argument("--backtest", action="store_true", help="Run the curated backtest harness")
    parser.add_argument("--self-test", action="store_true", help="Run environment diagnostics")
    parser.add_argument("--from-zip", action="append", default=[], help="Build master PDFs from offline OCW download bundles")
    parser.add_argument("--course", action="append", default=[], metavar="URL", help="Archive a specific course page (repeatable), skipping search discovery")
    parser.add_argument("-o", "--override", action="append", default=[], help="Override configuration key=value")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(config_path=args.config, overrides=args.override)

    if args.backtest:
        runner = BacktestRunner(config=config)
        return 0 if runner.run() else 1

    if args.self_test:
        runner = SelfTestRunner(config=config)
        return 0 if runner.run(verbose=args.verbose) else 1

    if args.from_zip:
        pipeline = ScraperPipeline(config=config, verbose=args.verbose)
        overall_success = True
        for bundle in args.from_zip:
            archive = pipeline.process_course_zip(Path(bundle))
            overall_success = overall_success and bool(archive)
        return 0 if overall_success else 1

    if args.course:
        pipeline = ScraperPipeline(config=config, verbose=args.verbose)
        try:
            result = pipeline.run_courses(args.course)
        except ValueError as exc:
            parser.error(str(exc))
        logging.info("Processed %d of %d courses", len(result.processed_courses), len(args.course))
        return 0 if result.success else 1

    if not args.search_url:
        parser.error("search_url is required unless --course, --from-zip, --backtest or --self-test is supplied")

    pipeline = ScraperPipeline(config=config, verbose=args.verbose)

    result = pipeline.run(args.search_url, limit=args.limit, use_selenium=not args.no_selenium)
    if not result.success:
        logging.error("No courses were successfully processed.")
        return 1

    logging.info("Processed %d courses", len(result.processed_courses))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
