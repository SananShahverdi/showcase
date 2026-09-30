"""Command line: run one mission with a readable event log, or reproduce the results.

    python -m asp1 mission --policy "When 1σ > 20 km" --years 1
    python -m asp1 experiments [--quick]
"""

import argparse

from . import experiments, mission


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m asp1", description="ASP-1 deep-space autonomy simulator")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("mission", help="simulate one mission and print its event log")
    run.add_argument("--policy", default="When 1σ > 20 km", choices=list(mission.POLICIES))
    run.add_argument("--years", type=float, default=1.0)
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--quiet", action="store_true", help="print only the summary")
    study = commands.add_parser("experiments", help="reproduce every result in the README")
    study.add_argument("--quick", action="store_true")
    study.add_argument("--workers", type=int, default=8)
    study.add_argument("--plot-only", action="store_true", help="redraw docs/navigation.png only")
    args = parser.parse_args()

    if args.command == "experiments":
        if args.plot_only:
            experiments.plot_only(args.workers)
        else:
            experiments.main(quick=args.quick, workers=args.workers)
        return
    report = mission.Mission(mission.MissionConfig(years=args.years, seed=args.seed), args.policy).run()
    if not args.quiet:
        for event in report.events:
            details = ", ".join(f"{k}={v}" for k, v in event.items() if k not in ("day", "event"))
            print(f"day {event['day']:7.2f}  {event['event']:<9} {details}")
    print()
    for key, value in report.summary().items():
        print(f"{key:>26}: {value:.2f}" if isinstance(value, float) else f"{key:>26}: {value}")


if __name__ == "__main__":
    main()
