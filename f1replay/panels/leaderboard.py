"""F1 Race Replay — timing tower — broadcast-style position column."""
import arcade
from f1replay.ui.design import (
    panel, section, filled_rrect, compound_color, compound_letter,
    CARD, CARD_HI, AMBER, CYAN, MONO,
    TEXT, TEXT_DIM, TEXT_FAINT,
    F_LABEL, F_MICRO, PAD,
)


def draw_leaderboard(stream_index, lap_index, drivers, current_time,
                     car_colors, pin_a, pin_b, hover_driver,
                     x1, y1, x2, y2):
    """Timing tower. Returns (hitboxes, None) for call-site compatibility."""
    panel(x1, y1, x2, y2)
    hitboxes = []

    px = x1 + PAD
    py = section(px, y2 - PAD + 2, x2 - PAD, "TIMING", right="GAP")

    if not stream_index.by_driver:
        arcade.draw_text("NO TIMING FEED", px, py - 8, TEXT_FAINT, F_MICRO)
        return hitboxes, None

    items = stream_index.order_at_time(current_time, drivers)
    if not items:
        arcade.draw_text("AWAITING POSITIONS", px, py - 8, TEXT_FAINT, F_MICRO)
        return hitboxes, None

    row_guard = y1 + 8
    avail = py - row_guard
    row_h = max(17, min(26, avail // max(1, len(items)) - 1))

    for (pos, code, gap) in items:
        if py - row_h < row_guard:
            break

        rx1, rx2 = x1 + 4, x2 - 4
        ry1, ry2 = py - row_h, py
        hitboxes.append((rx1, ry1, rx2, ry2, code))

        pin_col = AMBER if code == pin_a else (CYAN if code == pin_b else None)
        is_hover = (hover_driver == code)

        if pin_col is not None:
            filled_rrect(rx1, ry1, rx2, ry2, 2, CARD_HI)
            arcade.draw_lrbt_rectangle_filled(rx1, rx1 + 2, ry1 + 1, ry2 - 1, pin_col)
        elif is_hover:
            filled_rrect(rx1, ry1, rx2, ry2, 2, CARD)

        row_cy = (ry1 + ry2) // 2

        # Position
        pos_col = AMBER if pos == 1 else (TEXT if pos <= 3 else TEXT_DIM)
        arcade.draw_text(f"{pos:>2}", px, row_cy, pos_col, F_LABEL,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        # Team colour bar
        team_col = car_colors.get(code, (90, 95, 106))
        arcade.draw_lrbt_rectangle_filled(px + 22, px + 25,
                                          row_cy - row_h // 2 + 3,
                                          row_cy + row_h // 2 - 3, team_col)

        # Driver code
        arcade.draw_text(code, px + 32, row_cy,
                         pin_col if pin_col is not None else TEXT, F_LABEL,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        # Tyre compound letter (colored, no badge)
        lap_info = lap_index.info_at_time(code, current_time)
        comp = lap_info.get("compound")
        if comp and str(comp).strip().upper() not in ("", "NAN", "NONE"):
            arcade.draw_text(compound_letter(comp), x2 - PAD - 52, row_cy,
                             compound_color(comp), F_MICRO,
                             anchor_x="center", anchor_y="center", font_name=MONO)

        # Gap to leader
        if pos == 1:
            arcade.draw_text("LEADER", x2 - PAD, row_cy, AMBER, F_MICRO,
                             anchor_x="right", anchor_y="center", font_name=MONO)
        elif gap:
            arcade.draw_text(f"+{gap}", x2 - PAD, row_cy, TEXT_DIM, F_MICRO,
                             anchor_x="right", anchor_y="center", font_name=MONO)

        py -= row_h + 1

    return hitboxes, None
