"""Season calendars — real event schedules, resolved from FastF1.

The app used to carry one hardcoded 24-race list and pass the race *name* to
FastF1 for every season. FastF1 fuzzy-matches names, so asking for "Miami" in
2019 silently returned Monza — wrong race, no error. Seasons are now read from
the real schedule and loaded by round number, which is exact.
"""
import datetime

import fastf1 as ff1

from f1replay import FIRST_YEAR, LAST_YEAR

YEARS = list(range(LAST_YEAR, FIRST_YEAR - 1, -1))

# Circuit assets — outlines in ui/circuits.py, editorial facts in
# ui/selection.py:_RACE_META — are keyed by these short names. Location is the
# stable identifier for a venue, but the schedule spells a few differently
# across seasons, so alias them here. Venues with no assets resolve to None
# and the UI degrades to schedule data alone.
_LOCATION_TO_CIRCUIT = {
    "Sakhir":            "Bahrain",
    "Jeddah":            "Saudi Arabia",
    "Melbourne":         "Australia",
    "Suzuka":            "Japan",
    "Shanghai":          "China",
    "Miami":             "Miami",
    "Miami Gardens":     "Miami",
    "Imola":             "Emilia Romagna",
    "Monaco":            "Monaco",
    "Monte Carlo":       "Monaco",
    "Montréal":          "Canada",
    "Barcelona":         "Spain",
    "Spielberg":         "Austria",
    "Silverstone":       "Great Britain",
    "Budapest":          "Hungary",
    "Spa-Francorchamps": "Belgium",
    "Zandvoort":         "Netherlands",
    "Monza":             "Italy",
    "Baku":              "Azerbaijan",
    "Marina Bay":        "Singapore",
    "Singapore":         "Singapore",
    "Austin":            "United States",
    "Mexico City":       "Mexico",
    "São Paulo":         "Brazil",
    "Las Vegas":         "Las Vegas",
    "Lusail":            "Qatar",
    "Yas Island":        "Abu Dhabi",
    "Yas Marina":        "Abu Dhabi",   # renamed for 2026
    # No outline or editorial data (never on the modern calendar the assets
    # were generated from): Le Castellet, Hockenheim, Nürburgring, Mugello,
    # Portimão, Sochi, Istanbul.
}

# Country names differ between seasons for the same flag.
_COUNTRY_ALIAS = {
    "United Kingdom":       "Great Britain",
    "United Arab Emirates": "Abu Dhabi",
}


class Event:
    """One Grand Prix weekend, as the schedule actually lists it."""

    __slots__ = ("year", "round", "name", "short", "country",
                 "location", "date", "circuit_key")

    def __init__(self, year, round_, name, country, location, date):
        self.year        = year
        self.round       = round_
        self.name        = name
        # "Austrian Grand Prix" → "AUSTRIAN"; keeps list rows narrow and is
        # honest about one-offs ("70TH ANNIVERSARY", "STYRIAN").
        self.short       = name.replace(" Grand Prix", "").strip()
        self.country     = _COUNTRY_ALIAS.get(country, country)
        self.location    = location
        self.date        = date
        self.circuit_key = _LOCATION_TO_CIRCUIT.get(location)

    def __repr__(self):
        return f"<Event {self.year} R{self.round} {self.name}>"


# year -> (events, error_message). Failures are cached too, so a draw loop
# calling season() every frame never re-hammers a dead network.
_CACHE = {}


def _fetch(year):
    try:
        # Schedule requests are HTTP too, so the cache has to be enabled before
        # them — not just before session.load() — or they land in FastF1's
        # default location and ignore --cache entirely.
        from f1replay.core.data_loader import enable_cache
        enable_cache()
        sched = ff1.get_event_schedule(year)
    except Exception as exc:
        return [], f"SCHEDULE UNAVAILABLE — {type(exc).__name__}"

    events = []
    try:
        sched = sched[sched["RoundNumber"] > 0].sort_values("RoundNumber")
        # Drop rounds that have not been run: the schedule for the current
        # season lists the whole year, and a race that has not happened has no
        # telemetry to replay.
        now = datetime.datetime.now()
        sched = sched[sched["EventDate"] <= now]
        for _, r in sched.iterrows():
            date = r["EventDate"]
            events.append(Event(
                year, int(r["RoundNumber"]), str(r["EventName"]),
                str(r["Country"]), str(r["Location"]),
                date.strftime("%d %b %Y") if date is not None else "",
            ))
    except Exception as exc:
        return [], f"SCHEDULE UNREADABLE — {type(exc).__name__}"

    if not events:
        return [], "NO RACES RUN YET THIS SEASON"
    return events, None


def season(year):
    """Events for a season, in round order. Empty list if unavailable."""
    if year not in _CACHE:
        _CACHE[year] = _fetch(year)
    return _CACHE[year][0]


def season_error(year):
    """Why season(year) is empty, or None if it loaded."""
    if year not in _CACHE:
        _CACHE[year] = _fetch(year)
    return _CACHE[year][1]


def find(year, round_):
    """The event at a given round, or None."""
    for ev in season(year):
        if ev.round == round_:
            return ev
    return None


def resolve(year, text):
    """Best event match for a user-typed race name, or None.

    Matches — in order — round number, exact short name, exact event name,
    then a unique substring of either. Deliberately refuses ambiguous input
    rather than guessing, which is the bug this module exists to fix.
    """
    events = season(year)
    if not events:
        return None

    q = str(text).strip().lower()
    if not q:
        return None

    if q.isdigit():
        return find(year, int(q))

    for ev in events:
        if q == ev.short.lower() or q == ev.name.lower():
            return ev

    hits = [ev for ev in events
            if q in ev.short.lower() or q in ev.name.lower()
            or q in ev.location.lower() or q in ev.country.lower()]
    return hits[0] if len(hits) == 1 else None
