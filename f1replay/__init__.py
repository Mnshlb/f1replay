"""F1 Race Replay — replay any Formula 1 race from real telemetry."""
import datetime

__version__ = "1.1.0"

# Seasons FastF1 serves full timing + telemetry for. Kept here, free of heavy
# imports, so the CLI can print help and validate arguments without paying for
# `import fastf1`.
#
# The upper bound tracks the calendar rather than being pinned, so a new season
# appears on its own without a release. Each season's races come from the real
# schedule (core.calendar), so new rounds within a season need no change either.
FIRST_YEAR = 2019
LAST_YEAR = datetime.date.today().year
