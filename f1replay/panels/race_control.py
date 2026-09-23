"""F1 Race Replay — race control feed — official FIA messages, console style."""
import arcade
from f1replay.ui.design import (
    panel, section, tag,
    AMBER, GREEN, RED, CYAN, YELLOW, BLUE, MONO,
    TEXT, TEXT_DIM, TEXT_FAINT,
    F_MICRO, PAD,
)


def _classify(cat: str, flag: str, msg: str):
    """Return (tag_label, color) for a message."""
    m = msg.upper()
    f = flag.upper() if flag else ""

    if "VIRTUAL SAFETY CAR" in m:
        return "VSC", AMBER
    if "SAFETY CAR" in m:
        return "SC", AMBER
    if "RED FLAG" in m or f == "RED":
        return "RED", RED
    if "CHEQUERED" in m:
        return "FIN", TEXT
    if "DRS ENABLED" in m:
        return "DRS", CYAN
    if "DRS DISABLED" in m:
        return "DRS", TEXT_FAINT
    if "TRACK CLEAR" in m or f == "GREEN" or f == "CLEAR":
        return "CLR", GREEN
    if "YELLOW" in m or f in ("YELLOW", "DOUBLE YELLOW"):
        return "YEL", YELLOW
    if "BLUE" in f:
        return "BLU", BLUE
    if "INCIDENT" in m or "NOTED" in m or "PENALTY" in m or "INVESTIGATION" in m:
        return "INC", TEXT_DIM
    return "MSG", TEXT_FAINT


def _time_label(t_s: float) -> str:
    mins = int(t_s // 60)
    secs = int(t_s % 60)
    return f"{mins:02d}:{secs:02d}"


def draw_race_control_panel(rc_index, current_time, x1, y1, x2, y2):
    panel(x1, y1, x2, y2)

    px = x1 + PAD
    py = section(px, y2 - PAD + 2, x2 - PAD, "RACE CONTROL")

    msgs = rc_index.messages_up_to(current_time, max_count=40)
    if not msgs:
        arcade.draw_text("NO MESSAGES", (x1 + x2) // 2, (y1 + py) // 2,
                         TEXT_FAINT, F_MICRO,
                         anchor_x="center", anchor_y="center")
        return

    row_h     = 20
    time_w    = 34
    tag_w     = 30
    msg_x     = px + time_w + 6 + tag_w + 8
    max_msg_w = x2 - PAD - msg_x
    # Menlo advance ≈ 0.60 em; pyglet sizes are points at 96 dpi (×4/3),
    # so one char ≈ font_size × 0.80 px. Budget exactly so text stays inside.
    max_chars = max(8, int(max_msg_w / (F_MICRO * 0.80)) - 1)

    for entry in msgs:
        if py - row_h < y1 + 8:
            break

        lbl, col = _classify(entry["category"], entry["flag"], entry["message"])

        # Dark tinted row for safety car / red flag events
        if lbl in ("SC", "VSC"):
            arcade.draw_lrbt_rectangle_filled(x1 + 3, x2 - 3,
                                              py - row_h + 1, py + 1, (46, 36, 16))
        elif lbl == "RED":
            arcade.draw_lrbt_rectangle_filled(x1 + 3, x2 - 3,
                                              py - row_h + 1, py + 1, (50, 18, 20))

        row_mid = py - row_h // 2

        arcade.draw_text(_time_label(entry["t_s"]), px, row_mid,
                         TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        tag(px + time_w + 6 + tag_w // 2, row_mid, lbl, col)

        msg = entry["message"].upper()
        display = msg if len(msg) <= max_chars else msg[:max_chars - 1] + "…"
        arcade.draw_text(display, msg_x, row_mid,
                         col if lbl in ("SC", "VSC", "RED") else TEXT_DIM,
                         F_MICRO, anchor_x="left", anchor_y="center",
                         font_name=MONO)

        py -= row_h
