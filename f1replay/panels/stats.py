"""F1 Race Replay — telemetry cards — twin A/B driver comparison readouts."""
import numpy as np
import arcade
from f1replay.ui.helpers import is_num
from f1replay.ui.design import (
    panel, section, divider, filled_rrect, outline_rrect,
    compound_color, compound_letter, speed_color,
    AMBER, CYAN, GREEN, RED, MONO,
    CARD, CARD_HI, HAIRLINE,
    TEXT, TEXT_DIM, TEXT_FAINT, WHITE,
    F_GIANT, F_H1, F_LABEL, F_MICRO, PAD,
)

CARD_ACCENT = {"A": AMBER, "B": CYAN}


def _tel_at(driver_data, code, t):
    data = driver_data.get(code)
    if not data:
        return {}
    # Channels keep their own time base ("tc"); position uses "t".
    tt = data.get("tc")
    if tt is None or tt.size == 0 or t < tt[0] or t > tt[-1]:
        return {}
    out = {}
    if data.get("speed")    is not None:
        out["speed"]    = float(np.interp(t, tt, data["speed"]))
    if data.get("gear")     is not None:
        out["gear"]     = int(round(float(np.interp(t, tt, data["gear"]))))
    if data.get("throttle") is not None:
        out["throttle"] = float(np.interp(t, tt, data["throttle"]))
    if data.get("brake")    is not None:
        out["brake"]    = 1 if float(np.interp(t, tt, data["brake"])) >= 0.5 else 0
    return out


def draw_stats_panel(driver_data, lap_index, current_time,
                     driver_code, card_id, state, x1, y1, x2, y2):
    """One telemetry card.

    card_id: 'A' | 'B' — fixed slot identity (A amber, B cyan).
    state:   'PINNED' | 'PREVIEW' | None.
    """
    accent = CARD_ACCENT.get(card_id, AMBER)
    panel(x1, y1, x2, y2, accent=accent if driver_code else None)

    px = x1 + PAD
    state_col = accent if state == "PINNED" else WHITE
    py = section(px, y2 - PAD + 2, x2 - PAD, f"TELEMETRY {card_id}",
                 right=state or "", right_color=state_col)

    # ── Empty state ───────────────────────────────────────────────────────────
    if driver_code is None:
        mid_y = (y1 + py) // 2
        arcade.draw_text("—", (x1 + x2) // 2, mid_y + 10, TEXT_FAINT, F_H1,
                         anchor_x="center", anchor_y="center", font_name=MONO)
        hint = ("HOVER TO PREVIEW · CLICK TO PIN" if card_id == "A"
                else "PIN A SECOND DRIVER TO COMPARE")
        arcade.draw_text(hint, (x1 + x2) // 2, mid_y - 12,
                         TEXT_FAINT, F_MICRO, anchor_x="center", anchor_y="center")
        return

    tel = _tel_at(driver_data, driver_code, current_time)
    lap = lap_index.info_at_time(driver_code, current_time)

    # ── Driver code + lap ─────────────────────────────────────────────────────
    arcade.draw_text(driver_code, px, py + 2, accent, F_H1, bold=True,
                     anchor_x="left", anchor_y="top", font_name=MONO)
    lap_no = lap.get("lap")
    if lap_no is not None:
        arcade.draw_text(f"LAP {lap_no}", x2 - PAD, py - 2, TEXT_DIM, F_LABEL,
                         anchor_x="right", anchor_y="top", font_name=MONO)
    py -= 26

    # ── Speed (hero number) + gear box ───────────────────────────────────────
    speed = tel.get("speed")
    gear  = tel.get("gear")

    if is_num(speed):
        sc = speed_color(speed)
        arcade.draw_text(f"{int(speed):>3}", px, py, sc, F_GIANT,
                         anchor_x="left", anchor_y="top", font_name=MONO)
        arcade.draw_text("KM/H", px + 96, py - 30, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="top", font_name=MONO)
    else:
        arcade.draw_text("---", px, py, TEXT_FAINT, F_GIANT,
                         anchor_x="left", anchor_y="top", font_name=MONO)

    # Gear box, right-aligned
    gx2 = x2 - PAD
    gx1 = gx2 - 40
    gy2 = py
    gy1 = gy2 - 40
    filled_rrect(gx1, gy1, gx2, gy2, 3, CARD)
    outline_rrect(gx1, gy1, gx2, gy2, 3, HAIRLINE)
    arcade.draw_text(str(gear) if is_num(gear) else "–",
                     (gx1 + gx2) // 2, (gy1 + gy2) // 2 + 4,
                     TEXT, F_H1, anchor_x="center", anchor_y="center",
                     font_name=MONO)
    arcade.draw_text("GEAR", (gx1 + gx2) // 2, gy1 + 7, TEXT_FAINT, F_MICRO,
                     anchor_x="center", anchor_y="center", font_name=MONO)
    py -= 50

    if py < y1 + 14:
        return
    divider(px, py, x2 - PAD)
    py -= 11

    # ── Throttle bar ──────────────────────────────────────────────────────────
    thr = tel.get("throttle")
    if thr is not None and py > y1 + 18:
        arcade.draw_text("THR", px, py, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        bx1, bx2 = px + 30, x2 - PAD - 36
        arcade.draw_lrbt_rectangle_filled(bx1, bx2, py - 3, py + 3, CARD_HI)
        fill = int((bx2 - bx1) * max(0.0, min(1.0, thr / 100)))
        if fill > 0:
            arcade.draw_lrbt_rectangle_filled(bx1, bx1 + fill, py - 3, py + 3, GREEN)
        arcade.draw_text(f"{thr:>3.0f}%", x2 - PAD, py, TEXT_DIM, F_MICRO,
                         anchor_x="right", anchor_y="center", font_name=MONO)
        py -= 15

    # ── Brake bar (binary) ────────────────────────────────────────────────────
    brk = tel.get("brake")
    if brk is not None and py > y1 + 18:
        arcade.draw_text("BRK", px, py, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        bx1, bx2 = px + 30, x2 - PAD - 36
        arcade.draw_lrbt_rectangle_filled(bx1, bx2, py - 3, py + 3, CARD_HI)
        if brk:
            arcade.draw_lrbt_rectangle_filled(bx1, bx2, py - 3, py + 3, RED)
        arcade.draw_text("ON" if brk else "OFF", x2 - PAD, py,
                         RED if brk else TEXT_FAINT, F_MICRO,
                         anchor_x="right", anchor_y="center", font_name=MONO)
        py -= 16

    # ── Tyre row ──────────────────────────────────────────────────────────────
    comp      = lap.get("compound")
    tyre_life = lap.get("tyre_life")
    if comp and str(comp).strip().upper() not in ("", "NAN", "NONE") and py > y1 + 12:
        cc = compound_color(comp)
        arcade.draw_text("TYRE", px, py, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        arcade.draw_text(f"{compound_letter(comp)} · {str(comp).upper()}",
                         px + 38, py, cc, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        if is_num(tyre_life):
            arcade.draw_text(f"{int(tyre_life)} LAPS", x2 - PAD, py,
                             TEXT_DIM, F_MICRO,
                             anchor_x="right", anchor_y="center", font_name=MONO)
