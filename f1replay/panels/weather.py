"""F1 Race Replay — conditions card — compact weather/track data grid."""
import numpy as np
import arcade
from f1replay.ui.design import (
    panel, section, tag,
    AMBER, GREEN, RED, BLUE, MONO,
    TEXT, TEXT_DIM, TEXT_FAINT,
    F_LABEL, F_MICRO, PAD,
)


def _ok(v):
    return v is not None and not (isinstance(v, float) and np.isnan(float(v)))


def _temp_color(t):
    if t is None:
        return TEXT_DIM
    if t < 15:
        return BLUE
    if t < 35:
        return TEXT
    return RED


def draw_weather_panel(weather_index, current_time, x1, y1, x2, y2):
    panel(x1, y1, x2, y2)
    px = x1 + PAD
    py = section(px, y2 - PAD + 2, x2 - PAD, "CONDITIONS")

    w = weather_index.at_time(current_time)
    if not w:
        arcade.draw_text("NO WEATHER FEED", px, py - 8, TEXT_FAINT, F_MICRO)
        return

    air   = float(w["AirTemp"])       if _ok(w["AirTemp"])       else None
    trk   = float(w["TrackTemp"])     if _ok(w["TrackTemp"])     else None
    hum   = float(w["Humidity"])      if _ok(w["Humidity"])      else None
    wspd  = float(w["WindSpeed"])     if _ok(w["WindSpeed"])     else None
    wdir  = float(w["WindDirection"]) if _ok(w["WindDirection"]) else None

    raining = False
    if _ok(w["Rainfall"]):
        rain = w["Rainfall"]
        try:
            raining = bool(rain) if isinstance(rain, (bool, np.bool_)) else float(rain) >= 0.5
        except Exception:
            raining = False

    # Wet/dry state tag, top-right of the grid
    tag(x2 - PAD - 18, py - 8,
        "WET" if raining else "DRY",
        BLUE if raining else GREEN)

    dir_name = ""
    if wdir is not None:
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        dir_name = dirs[int((wdir + 22.5) % 360 // 45)]

    cells = [
        ("AIR",   f"{air:.0f}°C" if air  is not None else "–",  _temp_color(air)),
        ("TRACK", f"{trk:.0f}°C" if trk  is not None else "–",  AMBER if (trk or 0) >= 40 else _temp_color(trk)),
        ("WIND",  f"{wspd:.1f} {dir_name}" if wspd is not None else "–", TEXT),
        ("HUM",   f"{hum:.0f}%" if hum  is not None else "–",   TEXT),
    ]

    # 2 × 2 grid
    col_w  = (x2 - x1 - PAD * 2) // 2
    row_h  = 30
    top_y  = py - 12
    for i, (lbl, val, vc) in enumerate(cells):
        cx = px + (i % 2) * col_w
        cy = top_y - (i // 2) * row_h
        arcade.draw_text(lbl, cx, cy, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        arcade.draw_text(val, cx, cy - 13, vc, F_LABEL,
                         anchor_x="left", anchor_y="center", font_name=MONO)
