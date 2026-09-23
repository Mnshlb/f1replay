"""Everything a replay needs, assembled off the UI thread.

RaceView used to do all of this inside __init__, on the GL thread, which froze
the window for ~7 s on a warm cache and up to a minute on a cold one — the
loading screen painted once and then stopped pumping events, so the OS marked
the app unresponsive. The work is pure data (FastF1, pandas, numpy; no GL), so
it runs on a worker thread and the view is built from the result.
"""
import threading

import numpy as np

from f1replay import config
from f1replay.core.data_loader import (
    load_session, build_centerline,
    load_driver_telemetry_and_colors, load_live_timing_stream,
)
from f1replay.core.indexers import WeatherIndex, LapIndex, StreamIndex, RaceControlIndex

# Ordered stages, for the loading screen's progress bar.
STAGES = ["SESSION", "CIRCUIT", "TELEMETRY", "TIMING", "RACE CONTROL"]


class ReplayDataError(Exception):
    """A session loaded but cannot be replayed."""


class ReplayData:
    """Session, telemetry and time indexes for one race."""

    def __init__(self, progress=None):
        step = progress or (lambda _stage: None)

        step("SESSION")
        self.session = load_session()
        self.num_to_abbr = self._driver_numbers(self.session)
        self.abbr_to_num = {v: k for k, v in self.num_to_abbr.items()}

        step("CIRCUIT")
        self.cx_world, self.cy_world = build_centerline(self.session)
        if len(self.cx_world) < 2:
            raise ReplayDataError("NO TRACK GEOMETRY FOR THIS SESSION")

        step("TELEMETRY")
        (
            self.driver_data,
            self.t_min,
            self.t_max,
            self.drivers,
            self.car_colors,
        ) = load_driver_telemetry_and_colors(self.session)
        # Better to say so on the loading screen than to open an empty replay.
        if not self.drivers:
            raise ReplayDataError("NO TELEMETRY FOR THIS SESSION")
        if not (self.t_max > self.t_min):
            raise ReplayDataError("SESSION HAS NO REPLAYABLE DURATION")

        step("TIMING")
        self.weather = WeatherIndex(self.session)
        self.laps    = LapIndex(self.session, self.drivers)
        self.stream  = StreamIndex(
            load_live_timing_stream(self.session),
            self.drivers, self.num_to_abbr,
        )

        step("RACE CONTROL")
        self.race_control = RaceControlIndex(self.session)

        # Editorial facts live in the UI layer; imported late to avoid a cycle.
        from f1replay.ui.selection import _RACE_META
        from f1replay.core.calendar import find
        self.meta      = _RACE_META.get(config.CIRCUIT_KEY, {})
        self.event     = find(config.YEAR, config.ROUND)
        self.pit_world = self._pit_entry()

    @staticmethod
    def _driver_numbers(session):
        out = {}
        try:
            res = session.results
            if res is not None and not res.empty:
                for _, r in res.iterrows():
                    num  = str(r.get("DriverNumber", "")).strip()
                    abbr = str(r.get("Abbreviation", "")).strip()
                    if num and abbr:
                        out[num] = abbr
        except Exception:
            return {}
        return out

    def _pit_entry(self):
        """(world_x, world_y) of the pit-lane entry, or None."""
        try:
            laps = self.session.laps
            pit_laps = laps[laps["PitInTime"].notna()]
            if pit_laps.empty:
                return None
            for _, row in pit_laps.iterrows():
                data = self.driver_data.get(str(row.get("Driver", "")).strip())
                if not data:
                    continue
                t_pit = float(row["PitInTime"].total_seconds())
                if t_pit < data["t"][0] or t_pit > data["t"][-1]:
                    continue
                return (float(np.interp(t_pit, data["t"], data["x"])),
                        float(np.interp(t_pit, data["t"], data["y"])))
        except Exception:
            pass
        return None


class ReplayLoader:
    """Builds ReplayData on a background thread.

    Poll `done` from on_update; then either `data` or `error` is set.
    """

    def __init__(self):
        self.data      = None
        self.error     = None
        self.stage     = STAGES[0]
        self.cancelled = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            data = ReplayData(progress=self._set_stage)
        except ReplayDataError as exc:
            self.error = str(exc)          # already a readable message
            return
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            return
        self.data = data

    def _set_stage(self, stage):
        self.stage = stage

    @property
    def done(self):
        return self.data is not None or self.error is not None

    @property
    def progress(self):
        """0..1 across the named stages."""
        try:
            return (STAGES.index(self.stage) + 1) / (len(STAGES) + 1)
        except ValueError:
            return 0.0
