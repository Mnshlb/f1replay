import bisect

import numpy as np
import pandas as pd


class WeatherIndex:
    def __init__(self, session):
        self._df = None
        try:
            w = getattr(session, "weather_data", None)
            if w is None or w.empty:
                return
            w = w.copy()
            if "Time" not in w.columns:
                return
            w["t_s"] = w["Time"].apply(lambda td: float(td.total_seconds()) if td is not None else np.nan)
            w = w.dropna(subset=["t_s"]).sort_values("t_s")
            self._df = w
        except Exception:
            self._df = None

    def at_time(self, t_s: float):
        if self._df is None or self._df.empty:
            return None
        tt = self._df["t_s"].to_numpy(dtype=float)
        idx = np.searchsorted(tt, t_s, side="right") - 1
        if idx < 0:
            idx = 0
        row = self._df.iloc[int(idx)]

        def get(col, default=None):
            return row[col] if col in self._df.columns else default

        return {
            "AirTemp": get("AirTemp"),
            "TrackTemp": get("TrackTemp"),
            "Humidity": get("Humidity"),
            "Pressure": get("Pressure"),
            "WindSpeed": get("WindSpeed"),
            "WindDirection": get("WindDirection"),
            "Rainfall": get("Rainfall"),
        }


def _truthy(v):
    """Bool of a pandas cell, treating NA/NaN as False."""
    try:
        if v is None or not pd.notnull(v):
            return False
    except (TypeError, ValueError):
        return bool(v)
    return bool(v)


class LapIndex:
    def __init__(self, session, drivers):
        self.windows_by_driver = {}
        self.ref_driver = None
        # Purple-lap progression: the times a new fastest lap was set, and what
        # it was. Kept so the header can show the fastest lap *so far* rather
        # than spoiling the race's eventual best from lap one.
        self._fl_at = []
        self._fl_time = []
        self._fl_code = []

        laps = session.laps
        if laps is None or laps.empty:
            return

        candidates = []
        for code in drivers:
            try:
                dlaps = laps.pick_drivers(code).sort_values("LapNumber")
            except Exception:
                continue
            if dlaps is None or dlaps.empty:
                continue

            windows = []
            for _, r in dlaps.iterrows():
                lap_no = r.get("LapNumber", None)
                start = r.get("LapStartTime", None)
                # End from "Time" (when the lap was completed), not
                # LapStartTime + LapTime: a lap interrupted by a red flag has
                # LapTime = NaT, which made end_s NaN. Every comparison against
                # NaN is False, so those laps became invisible holes and the
                # header reported the final lap during the stoppage.
                end = r.get("Time", None)
                if lap_no is None or start is None or end is None:
                    continue

                try:
                    lap_no = int(lap_no)
                    start_s = float(start.total_seconds())
                    end_s = float(end.total_seconds())
                except Exception:
                    continue
                if not (end_s > start_s):
                    continue

                compound = r.get("Compound", None)
                tyre_life = r.get("TyreLife", None)
                stint = r.get("Stint", None)

                windows.append((lap_no, start_s, end_s, compound, tyre_life, stint))

                # Fastest-lap candidate. Uses the real LapTime (end_s - start_s
                # is the wall-clock span, which a red flag inflates) and skips
                # laps the stewards deleted.
                #
                # Deliberately NOT filtered on IsAccurate: that flag is False
                # for the first several laps of every race (standing start,
                # safety car, yellows), which left the header showing "—" for
                # the first 6-10 minutes of race time. In/out laps are always
                # slower than a flying lap so they can never win, and dropping
                # the filter still reproduces FastF1's own pick_fastest() on
                # every cached race.
                lt = r.get("LapTime", None)
                if lt is None or not pd.notnull(lt):
                    continue
                if _truthy(r.get("Deleted", False)):
                    continue
                lap_seconds = float(lt.total_seconds())
                if lap_seconds > 0:
                    candidates.append((end_s, lap_seconds, code))

            if windows:
                self.windows_by_driver[code] = windows

        self._build_fastest_lap_timeline(candidates)

        self._ref_lap_ends = []
        self.ref_driver = None
        try:
            results = session.results.sort_values("Position")
            self.ref_driver = results.iloc[0]["Abbreviation"]
        except Exception:
            self.ref_driver = drivers[0] if drivers else None

        ref_windows = self.windows_by_driver.get(self.ref_driver) or []
        self._ref_lap_ends = sorted(w[2] for w in ref_windows)

    def _build_fastest_lap_timeline(self, candidates):
        """Keep only the laps that actually improved on the best at the time."""
        candidates.sort(key=lambda c: c[0])   # by completion time
        best = None
        for done_at, lap_seconds, code in candidates:
            if best is None or lap_seconds < best:
                best = lap_seconds
                self._fl_at.append(done_at)
                self._fl_time.append(lap_seconds)
                self._fl_code.append(code)

    def _lap_boundary(self, t_s: float):
        """Snap to the end of the most recently completed reference lap.

        Without this the purple time updates the instant any car crosses the
        line, so the whole field strobes through it one after another — lap 3
        at Monaco 2022 alone produced 16 changes, 24 of the race's 62 landing
        under 5 s apart. Snapping settles it to one update per lap, in step
        with the LAP counter.
        """
        ends = self._ref_lap_ends
        if not ends or t_s >= ends[-1]:
            # Before the first lap completes, or after the last one, report
            # the true value — otherwise a fastest lap set on the final lap
            # would never be shown.
            return t_s
        i = bisect.bisect_right(ends, t_s) - 1
        return ends[i] if i >= 0 else t_s

    def fastest_at(self, t_s: float):
        """(code, lap_seconds) of the fastest lap as of the last completed lap."""
        if not self._fl_at:
            return None, None
        i = bisect.bisect_right(self._fl_at, self._lap_boundary(t_s)) - 1
        if i < 0:
            return None, None
        return self._fl_code[i], self._fl_time[i]

    def info_at_time(self, code: str, t_s: float):
        windows = self.windows_by_driver.get(code)
        if not windows:
            return {"lap": None, "compound": None, "tyre_life": None, "stint": None}

        for (lap_no, a, b, compound, tyre_life, stint) in windows:
            if a <= t_s < b:
                return {"lap": lap_no, "compound": compound, "tyre_life": tyre_life, "stint": stint}

        if t_s < windows[0][1]:
            lap_no, _, _, compound, tyre_life, stint = windows[0]
            return {"lap": lap_no, "compound": compound, "tyre_life": tyre_life, "stint": stint}

        # Past the end, or inside a hole: a red-flag stoppage leaves a gap in
        # the windows, and falling through to the final lap made the header
        # read "LAP 64 / 64" (with lap-64 tyre data) while the cars sat in the
        # pit lane on lap 29. Report the most recent lap that had started.
        started = [w for w in windows if w[1] <= t_s]
        lap_no, _, _, compound, tyre_life, stint = started[-1] if started else windows[-1]
        return {"lap": lap_no, "compound": compound, "tyre_life": tyre_life, "stint": stint}


def _rc_time_offset(session):
    """
    Return the absolute datetime that corresponds to SessionTime=0.

    race_control_messages["Time"] is an absolute Timestamp while telemetry
    uses SessionTime (Timedelta from session start).  session.t0_date is the
    authoritative source; laps LapStartDate/LapStartTime is the fallback.
    """
    try:
        # t0_date is a property that RAISES when telemetry was not loaded, so
        # getattr's default never fires — it has to be caught, or the laps
        # fallback below is unreachable.
        t0 = session.t0_date
        if t0 is not None:
            return t0
    except Exception:
        pass
    try:
        # Fallback: derive from lap absolute start date and relative start time
        laps = getattr(session, "laps", None)
        if laps is None or laps.empty:
            return None
        valid = laps.dropna(subset=["LapStartDate", "LapStartTime"])
        if valid.empty:
            return None
        row = valid.iloc[0]
        return row["LapStartDate"] - row["LapStartTime"]
    except Exception:
        return None


def _status_after(message, current):
    """Track status once `message` has been read, given the current status.

    Order matters — "VIRTUAL SAFETY CAR DEPLOYED" contains "SAFETY CAR
    DEPLOYED", so the virtual cases are tested first. Anything unrecognised
    leaves the status alone, which is what keeps "SAFETY CAR IN THIS LAP"
    (the car is still out, coming in at the end of the lap) from clearing SC.
    """
    m = message.upper()
    chequered = "CHEQUERED" in m
    if chequered:
        return None
    # "RED FLAG" is a substring of "CHEQUERED FLAG", which is why the old rule
    # left every race — red-flagged or not — showing RED once it finished.
    # Tested explicitly so this survives any reordering of these branches.
    if "RED FLAG" in m and not chequered:
        return "RED"
    # Clears everything, red flags included. The old rule only cleared SC/VSC,
    # so a red-flagged race stayed red for the rest of the replay.
    if "TRACK CLEAR" in m:
        return None
    if "VIRTUAL SAFETY CAR DEPLOYED" in m:
        return "VSC"
    if "VIRTUAL SAFETY CAR ENDING" in m:
        return None
    if "SAFETY CAR DEPLOYED" in m:
        return "SC"
    if "SAFETY CAR WILL ENTER PITS" in m or "SAFETY CAR RETURNING" in m:
        return None
    # Resuming a suspended race, or starting one, behind the safety car.
    if "RACE WILL RESUME" in m or "BEHIND SAFETY CAR" in m \
            or "BEHIND THE SAFETY CAR" in m:
        return "SC"
    return current


class RaceControlIndex:
    """Parses session.race_control_messages into time-ordered entries."""

    def __init__(self, session):
        self._msgs = []
        self._status_times = []
        self._status_values = []
        try:
            df = getattr(session, "race_control_messages", None)
            if df is None or (hasattr(df, "empty") and df.empty):
                return
            df = df.copy()

            # Detect whether Time is relative (Timedelta) or absolute (Timestamp)
            sample = df["Time"].dropna().iloc[0] if not df["Time"].dropna().empty else None
            if sample is None:
                return

            if hasattr(sample, "total_seconds"):
                # Already a Timedelta — e.g. pd.Timedelta
                df["t_s"] = df["Time"].apply(
                    lambda td: float(td.total_seconds()) if pd.notnull(td) else np.nan
                )
            else:
                # Absolute Timestamp — convert via session-start offset
                offset = _rc_time_offset(session)
                if offset is None:
                    return
                df["t_s"] = df["Time"].apply(
                    lambda ts: float((ts - offset).total_seconds()) if pd.notnull(ts) else np.nan
                )

            df = df.dropna(subset=["t_s"]).sort_values("t_s").reset_index(drop=True)
            for _, row in df.iterrows():
                msg = str(row.get("Message", "") or "").strip()
                if not msg:
                    continue
                self._msgs.append({
                    "t_s":           float(row["t_s"]),
                    "message":       msg,
                    "category":      str(row.get("Category", "") or "").strip(),
                    "flag":          str(row.get("Flag", "") or "").strip(),
                    "racing_number": str(row.get("RacingNumber", "") or "").strip(),
                })
        except Exception:
            self._msgs = []
        self._build_status_timeline()

    @property
    def has_data(self):
        return bool(self._msgs)

    def messages_up_to(self, t_s: float, max_count: int = 30):
        """Return up to max_count messages at or before t_s, most recent first."""
        result = [m for m in self._msgs if m["t_s"] <= t_s]
        return list(reversed(result[-max_count:]))

    def messages_for_driver(self, racing_number: str, t_s: float, max_count: int = 15):
        """Return messages for a specific car number at or before t_s, most recent first."""
        if not racing_number:
            return []
        result = [m for m in self._msgs
                  if m["t_s"] <= t_s and m["racing_number"] == racing_number]
        return list(reversed(result[-max_count:]))

    def _build_status_timeline(self):
        """Collapse the message stream into status-change points, once."""
        status = None
        for msg in self._msgs:
            new = _status_after(msg["message"], status)
            if new != status:
                status = new
                self._status_times.append(msg["t_s"])
                self._status_values.append(status)

    @property
    def status_timeline(self):
        """[(t_s, status)] — every track-status change, for inspection/tests."""
        return list(zip(self._status_times, self._status_values))

    def active_status(self, t_s: float):
        """Return 'SC', 'VSC', 'RED', or None — the track status at t_s."""
        if not self._status_times:
            return None
        i = bisect.bisect_right(self._status_times, t_s) - 1
        return self._status_values[i] if i >= 0 else None


class StreamIndex:
    def __init__(self, stream_data, drivers, num_to_abbr):
        self.by_driver = {}

        if stream_data is None or getattr(stream_data, "empty", True):
            return

        df = stream_data.copy()

        if "Time" in df.columns:
            try:
                df["t_s"] = df["Time"].apply(lambda td: float(td.total_seconds()) if td is not None else np.nan)
            except Exception:
                return
        else:
            try:
                df = df.reset_index()
                time_col = "Time" if "Time" in df.columns else "index"
                df["t_s"] = df[time_col].apply(lambda td: float(td.total_seconds()) if td is not None else np.nan)
            except Exception:
                return

        driver_col = None
        for c in ("Driver", "DriverNumber", "RacingNumber"):
            if c in df.columns:
                driver_col = c
                break
        if driver_col is None:
            return

        pos_col = None
        for c in ("Position", "Pos", "position"):
            if c in df.columns:
                pos_col = c
                break
        if pos_col is None:
            return

        gap_col = "GapToLeader" if "GapToLeader" in df.columns else None

        df = df.dropna(subset=["t_s", driver_col, pos_col]).copy()

        def to_abbr(v):
            s = str(v).strip()
            if s.isdigit() and s in num_to_abbr:
                return num_to_abbr[s]
            return s

        df["DriverKey"] = df[driver_col].apply(to_abbr)

        allowed = set(drivers)
        df = df[df["DriverKey"].isin(allowed)].copy()

        def _coerce_int(x):
            try:
                return int(float(x))
            except Exception:
                return None

        df["Pos_i"] = df[pos_col].apply(_coerce_int)
        df = df.dropna(subset=["Pos_i"]).copy()

        keep = ["t_s", "DriverKey", "Pos_i"]
        if gap_col:
            keep.append(gap_col)
        df = df[keep].sort_values("t_s")

        for d in df["DriverKey"].unique().tolist():
            sub = df[df["DriverKey"] == d]
            t = sub["t_s"].to_numpy(dtype=float)
            pos = sub["Pos_i"].to_numpy(dtype=int)
            gap = sub[gap_col].astype(str).to_numpy() if gap_col else None
            self.by_driver[d] = {"t": t, "pos": pos, "gap": gap}

    def order_at_time(self, t_seconds: float, drivers):
        items = []
        for code in drivers:
            series = self.by_driver.get(code)
            if not series:
                continue

            tt = series["t"]
            if tt.size == 0:
                continue

            idx = np.searchsorted(tt, t_seconds, side="right") - 1
            if idx < 0:
                continue

            pos = int(series["pos"][idx])
            gap = None
            if series["gap"] is not None:
                g = series["gap"][idx]
                if isinstance(g, str) and g.strip() and g.strip().lower() != "nan":
                    gap = g.strip()

            items.append((pos, code, gap))

        items.sort(key=lambda x: x[0])
        return items