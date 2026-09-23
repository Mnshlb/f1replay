"""F1 Race Replay — driver event strip — flashes over the telemetry card for ~15 s
when race control issues a message directed at the active driver."""
import arcade
from f1replay.ui.design import (
    filled_rrect, outline_rrect,
    AMBER, RED, YELLOW, BLUE, MONO,
    PANEL, TEXT, TEXT_DIM,
    F_MICRO,
)

_POPUP_H    = 24
_POPUP_LIFE = 15.0   # seconds the strip stays visible


def _classify(msg: str, flag: str):
    """Return (short_label, accent_color) for a driver-specific RC message."""
    m = msg.upper()
    f = flag.upper() if flag else ""

    if "BLUE FLAG" in m or f == "BLUE":
        return "BLUE FLAG", BLUE
    if "BLACK FLAG" in m:
        return "BLACK FLAG", TEXT
    if "BLACK AND WHITE FLAG" in m:
        return "B/W WARNING", TEXT_DIM
    if "DISQUALIFIED" in m or "DSQ" in m:
        return "DISQUALIFIED", RED
    if "DRIVE THROUGH" in m:
        return "DRIVE-THROUGH", RED
    if "STOP AND GO" in m:
        return "STOP & GO", RED
    if "TIME PENALTY" in m:
        import re
        hit = re.search(r'(\d+)\s*SECOND', msg, re.IGNORECASE)
        sec = hit.group(1) if hit else "?"
        return f"{sec}S PENALTY", AMBER
    if "REPRIMAND" in m:
        return "REPRIMAND", TEXT_DIM
    if "TRACK LIMITS" in m:
        return "TRACK LIMITS", YELLOW
    if "LAP TIME DELETED" in m or "DELETED" in m:
        return "LAP DELETED", YELLOW
    if "INVESTIGATION" in m or "NOTED" in m:
        return "INVESTIGATION", AMBER
    if "INCIDENT" in m:
        return "INCIDENT", AMBER
    if "WARNING" in m:
        return "WARNING", YELLOW
    short = msg if len(msg) <= 26 else msg[:25] + "…"
    return short.upper(), TEXT_DIM


def draw_rc_popup(rc_index, racing_number, driver_code, label_color,
                  current_time, x1, y1, x2, y2):
    """Thin alert strip across the top of the telemetry card bounds."""
    if not racing_number:
        return

    msgs = rc_index.messages_for_driver(racing_number, current_time, max_count=1)
    if not msgs:
        return

    latest = msgs[0]
    age = current_time - latest["t_s"]
    if age < 0 or age > _POPUP_LIFE:
        return

    short, accent = _classify(latest["message"], latest["flag"])

    px1, px2 = x1 + 4, x2 - 4
    py2 = y2 - 2
    py1 = py2 - _POPUP_H

    filled_rrect(px1, py1, px2, py2, 2, PANEL)
    outline_rrect(px1, py1, px2, py2, 2, accent, 1)
    arcade.draw_lrbt_rectangle_filled(px1 + 1, px1 + 3, py1 + 3, py2 - 3, accent)

    mid_y = (py1 + py2) // 2

    if driver_code:
        arcade.draw_text(driver_code, px1 + 10, mid_y, accent, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)

    arcade.draw_text(short, px1 + 42, mid_y, TEXT, F_MICRO,
                     anchor_x="left", anchor_y="center", font_name=MONO)

    # Countdown bar along the bottom edge
    bar_w = int((1.0 - age / _POPUP_LIFE) * (px2 - px1 - 6))
    if bar_w > 0:
        arcade.draw_lrbt_rectangle_filled(px1 + 3, px1 + 3 + bar_w,
                                          py1 + 1, py1 + 3, accent)
