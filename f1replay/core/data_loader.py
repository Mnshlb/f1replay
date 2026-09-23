import os
import numpy as np
import fastf1 as ff1
from f1replay import config


def enable_cache():
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    ff1.Cache.enable_cache(config.CACHE_DIR)


def load_session():
    enable_cache()
    # By round number, never by name: get_session fuzzy-matches names, so
    # ("2019", "Miami") used to resolve to Monza without raising.
    session = ff1.get_session(config.YEAR, config.ROUND, config.SESSION)
    session.load()
    return session


def build_centerline(session):
    results = session.results.sort_values("Position")
    winner_code = results.iloc[0]["Abbreviation"]

    lap = session.laps.pick_drivers(winner_code).pick_fastest()
    tel = lap.get_telemetry()

    x = tel["X"].to_numpy()
    y = tel["Y"].to_numpy()

    if config.DOWNSAMPLE_STEP > 1:
        x = x[::config.DOWNSAMPLE_STEP]
        y = y[::config.DOWNSAMPLE_STEP]

    return x, y


def driver_windows(session):
    """{code: (start, end)} session-time seconds of each driver's classified laps.

    Clipping per driver matters: a car that retires keeps transmitting position
    from the garage, so a race-wide window would leave it parked on the map for
    the rest of the replay instead of disappearing.
    """
    out = {}
    laps = session.laps
    if laps is None or laps.empty:
        return out
    for code, g in laps.groupby("Driver"):
        starts = g["LapStartTime"].dropna()
        # "Time" is when the lap was completed, and it survives a NaT LapTime —
        # so a driver who crashes out on lap 1 still gets their lap 1, and a
        # retirement ends exactly where get_telemetry() would have ended it.
        ends = g["Time"].dropna()
        if starts.empty or ends.empty:
            continue
        out[str(code)] = (float(starts.min().total_seconds()),
                          float(ends.max().total_seconds()))
    return out


def _team_color(row):
    hex_color = row["TeamColor"] if ("TeamColor" in row.index
                                     and isinstance(row["TeamColor"], str)) else None
    if hex_color and len(hex_color) == 6:
        return (int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16))
    return (255, 255, 255)


def load_driver_telemetry_and_colors(session):
    """Per-driver position and channel arrays, straight from the raw feeds.

    session.load() already leaves car_data and pos_data in memory. The obvious
    route — laps.pick_drivers(code).get_telemetry() — costs ~4.7 s a race
    because it merges the two channels onto a common time base and derives
    Distance/RelativeDistance/DriverAhead. None of that is used here: the view
    np.interp's every value at draw time anyway, so the two feeds are kept on
    their own time bases ("t" for position, "tc" for channels) and read as-is.
    """
    results = session.results.sort_values("Position")
    windows = driver_windows(session)

    driver_data = {}
    car_colors = {}

    for _, row in results.iterrows():
        code = str(row.get("Abbreviation", "")).strip()
        num = str(row.get("DriverNumber", "")).strip()
        if not code or not num:
            continue

        pos = session.pos_data.get(num)
        car = session.car_data.get(num)
        if pos is None or car is None or pos.empty or car.empty:
            continue
        if code not in windows:
            continue
        d_start, d_end = windows[code]

        # ── position ─────────────────────────────────────────────────────────
        tp = pos["SessionTime"].dt.total_seconds().to_numpy(dtype=float)
        xs = pos["X"].to_numpy(dtype=float)
        ys = pos["Y"].to_numpy(dtype=float)
        keep = np.isfinite(tp) & np.isfinite(xs) & np.isfinite(ys)
        if "Status" in pos.columns:
            # Off-track samples park the car at the origin in some sessions.
            keep &= (pos["Status"].to_numpy() == "OnTrack")
        keep &= (tp >= d_start) & (tp <= d_end)
        tp, xs, ys = tp[keep], xs[keep], ys[keep]
        if tp.size == 0:
            continue

        # ── channels ─────────────────────────────────────────────────────────
        tc = car["SessionTime"].dt.total_seconds().to_numpy(dtype=float)
        ckeep = np.isfinite(tc) & (tc >= d_start) & (tc <= d_end)
        # Drop rows with a non-finite Speed/nGear, as the old get_telemetry()
        # path did. All channels share this one mask so they stay aligned, and
        # an interpolated value can then never come back NaN.
        for _col in ("Speed", "nGear"):
            if _col in car.columns:
                _v = car[_col].to_numpy()
                if _v.dtype != bool:
                    ckeep &= np.isfinite(_v.astype(float))
        tc = tc[ckeep]

        def channel(name):
            if name not in car.columns:
                return None
            arr = car[name].to_numpy()
            if arr.dtype == bool:
                arr = arr.astype(float)
            return arr[ckeep].astype(float)

        driver_data[code] = {
            "t": tp, "x": xs, "y": ys,
            "tc": tc,
            "speed":    channel("Speed"),
            "gear":     channel("nGear"),
            "throttle": channel("Throttle"),
            "brake":    channel("Brake"),
        }
        car_colors[code] = _team_color(row)

    drivers = list(driver_data.keys())
    spans = [d["t"] for d in driver_data.values()]
    t_start = min(float(s[0]) for s in spans) if spans else 0.0
    t_end = max(float(s[-1]) for s in spans) if spans else 0.0
    return driver_data, t_start, t_end, drivers, car_colors


def load_live_timing_stream(session):
    try:
        import fastf1.api as f1api
    except Exception:
        return None

    api_path = getattr(session, "api_path", None)
    if not api_path:
        return None

    try:
        out = f1api.timing_data(api_path)
        if isinstance(out, (tuple, list)) and len(out) >= 2:
            return out[1]
        return out
    except Exception:
        return None
