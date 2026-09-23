"""F1 Race Replay — command line — replay a Grand Prix straight from the terminal."""
import argparse
import os
import sys

from f1replay import __version__, config, FIRST_YEAR, LAST_YEAR


def _parser():
    p = argparse.ArgumentParser(
        prog="f1replay",
        description="Replay a Formula 1 race from real telemetry.",
        epilog=(
            "examples:\n"
            "  f1replay                      open the session-select screen\n"
            "  f1replay austria              this season's Austrian Grand Prix\n"
            "  f1replay austria 2019         the 2019 Austrian Grand Prix\n"
            "  f1replay monaco 2022 -s 5     Monaco 2022 at 5x speed\n"
            "  f1replay --round 11 2025      by round number\n"
            "  f1replay --list 2019          show that season's calendar\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("race", nargs="?",
                   help="race name, e.g. austria, monaco, 'united states'")
    p.add_argument("year", nargs="?", type=int,
                   help=f"season, {FIRST_YEAR}-{LAST_YEAR} (default: latest)")
    p.add_argument("-r", "--round", type=int,
                   help="select by round number instead of name")
    p.add_argument("-l", "--list", nargs="?", const=-1, type=int, metavar="YEAR",
                   help="list a season's races and exit")
    p.add_argument("-s", "--speed", type=float,
                   help=f"initial playback speed {config.SPEED_STEPS}")
    p.add_argument("--session", default="R", metavar="CODE",
                   help="session to replay: R race, Q qualifying, S sprint "
                        "(default: R)")
    p.add_argument("--cache", metavar="PATH",
                   help="telemetry cache directory (default: %(default)s)",
                   default=config.CACHE_DIR)
    p.add_argument("-V", "--version", action="version",
                   version=f"f1replay {__version__}")
    return p


def _print_season(year):
    from f1replay.core.calendar import season, season_error
    events = season(year)
    if not events:
        print(f"f1replay: {season_error(year) or 'no events'}", file=sys.stderr)
        return 1
    print(f"{year} Formula 1 season — {len(events)} races")
    for ev in events:
        venue = f"{ev.location}, {ev.country}"
        print(f"  {ev.round:>2}  {ev.short:<22} {venue:<32} {ev.date}")
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)

    config.CACHE_DIR = os.path.abspath(os.path.expanduser(args.cache))
    config.SESSION = args.session.upper()

    if args.list is not None:
        return _print_season(args.list if args.list != -1 else LAST_YEAR)

    from f1replay.core.calendar import YEARS, season, find, resolve

    year = args.year or YEARS[0]
    if year not in YEARS:
        print(f"f1replay: no data for {year}; try {YEARS[-1]}-{YEARS[0]}",
              file=sys.stderr)
        return 2

    event = None
    if args.round is not None:
        event = find(year, args.round)
        if event is None:
            print(f"f1replay: {year} has no round {args.round}", file=sys.stderr)
            return 2
    elif args.race:
        event = resolve(year, args.race)
        if event is None:
            # resolve() refuses ambiguous input rather than guessing, which is
            # the whole point — say so, and show what was actually available.
            print(f"f1replay: no unique match for {args.race!r} in {year}",
                  file=sys.stderr)
            _print_season(year)
            return 2

    if args.speed is not None:
        config.INITIAL_TIME_SPEED = args.speed

    from f1replay.app import run
    return run(event)


if __name__ == "__main__":
    sys.exit(main())
