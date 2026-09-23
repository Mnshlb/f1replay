"""F1 Race Replay — race view — full-bleed track map, timing tower, telemetry rail."""
import traceback
from collections import deque

import numpy as np
import arcade

from f1replay import config
from f1replay.config import (
    INITIAL_TIME_SPEED, SPEED_STEPS, SKIP_SECONDS, CAR_RADIUS,
)
from f1replay.ui.helpers import fmt_hms, fmt_laptime
from f1replay.core.track_geometry import TrackTransform
from f1replay.panels.weather import draw_weather_panel
from f1replay.panels.leaderboard import draw_leaderboard
from f1replay.panels.race_control import draw_race_control_panel
from f1replay.panels.driver_radio import draw_rc_popup
from f1replay.panels.stats import draw_stats_panel
from f1replay.ui.picking import pick_driver_anywhere
from f1replay.ui.design import (
    filled_rrect, outline_rrect, tag, icon_btn,
    draw_brand, console_footer, spaced,
    BG, PANEL, CARD_HI, HAIRLINE, HAIRLINE_HI,
    AMBER, PURPLE, GREEN, RED, CYAN, MONO, INK,
    TEXT, TEXT_DIM, TEXT_FAINT, WHITE,
    TRACK_ASPHALT, TRACK_EDGE,
    F_H1, F_H2, F_LABEL, F_MICRO, PAD, R,
)

# Fixed layout heights (px)
_TOP_H   = 58
_TRANS_H = 56
_FOOT_H  = 22
_M       = 10
_GAP     = 8


def _rail_widths(w):
    l_w = max(188, min(245, int(w * 0.16)))
    r_w = max(265, min(330, int(w * 0.225)))
    return l_w, r_w


class RaceView(arcade.View):
    def __init__(self, data):
        """`data` is a ReplayData, built off-thread by ReplayLoader."""
        super().__init__()

        self.session      = data.session
        self.num_to_abbr  = data.num_to_abbr
        self.abbr_to_num  = data.abbr_to_num
        self.cx_world     = data.cx_world
        self.cy_world     = data.cy_world
        self.driver_data  = data.driver_data
        self.t_min        = data.t_min
        self.t_max        = data.t_max
        self.drivers      = data.drivers
        self.car_colors   = data.car_colors
        self.weather      = data.weather
        self.laps         = data.laps
        self.race_control = data.race_control
        self.stream       = data.stream
        # Venues with no editorial entry still name themselves from the schedule.
        self.meta         = data.meta
        self.event        = data.event

        self.transform   = TrackTransform()
        self.center_loop = []
        self.outer_loop  = []
        self.inner_loop  = []

        self.t0           = float(self.t_min)
        self.replay_time  = 0.0
        self.current_time = self.t0

        self.time_speed = INITIAL_TIME_SPEED
        self.paused     = False

        self.hover_driver = None
        self.pin_a        = None   # primary pinned driver (amber)
        self.pin_b        = None   # comparison driver (cyan)

        self.leaderboard_hitboxes = []

        self._scrubber_box   = None
        self._scrubbing      = False

        self._back_box       = None
        self._exit_box       = None
        self._play_btn       = None
        self._restart_btn    = None
        self._skip_back_btn  = None
        self._skip_fwd_btn   = None
        self._spd_down_btn   = None
        self._spd_up_btn     = None

        self._pit_world   = data.pit_world
        self._trails      = {code: deque(maxlen=22) for code in self.drivers}
        self._last_t      = self.current_time
        self._draw_failed = set()   # regions already reported by _guard

    def on_show_view(self):
        arcade.set_background_color(BG)
        self._rebuild_geometry()

    # ── layout ────────────────────────────────────────────────────────────────

    def _main_y1(self):
        return _FOOT_H + _TRANS_H + _M

    def _map_bounds(self, w, h):
        l_w, r_w = _rail_widths(w)
        my1 = self._main_y1()
        my2 = h - _TOP_H - _M
        lx2 = _M + l_w
        rx1 = w - _M - r_w
        return lx2 + _GAP + 6, my1 + 6, rx1 - _GAP - 6, my2 - 6

    def _rebuild_geometry(self):
        w, h = self.window.width, self.window.height
        if len(self.cx_world) < 2:
            # ReplayData rejects this before a view is built; guarded anyway
            # because resize calls straight back in here.
            self.center_loop = self.outer_loop = self.inner_loop = []
            return
        mx1, my1, mx2, my2 = self._map_bounds(w, h)
        self.transform.fit_to_rect(self.cx_world, self.cy_world, mx1, my1, mx2, my2)
        center_pts = [self.transform.to_screen(x, y)
                      for x, y in zip(self.cx_world, self.cy_world)]
        outer_pts, inner_pts = TrackTransform.build_screen_edges(center_pts)
        self.center_loop = center_pts + [center_pts[0]]
        self.outer_loop  = outer_pts + [outer_pts[0]]
        self.inner_loop  = inner_pts + [inner_pts[0]]

    def _driver_screen_pos(self, code):
        data = self.driver_data.get(code)
        if not data:
            return None
        t_arr = data["t"]
        if self.current_time < t_arr[0] or self.current_time > t_arr[-1]:
            return None
        x = np.interp(self.current_time, t_arr, data["x"])
        y = np.interp(self.current_time, t_arr, data["y"])
        return self.transform.to_screen(x, y)

    # ── draw ─────────────────────────────────────────────────────────────────

    def _guard(self, name, draw_fn, box=None):
        """Draw one region; a failure marks that region instead of killing the
        replay. The traceback is printed once per region so it stays debuggable.
        """
        try:
            draw_fn()
        except Exception:
            if name not in self._draw_failed:
                self._draw_failed.add(name)
                traceback.print_exc()
            if box:
                x1, y1, x2, y2 = box
                filled_rrect(x1, y1, x2, y2, R, PANEL)
                outline_rrect(x1, y1, x2, y2, R, RED)
                arcade.draw_text(f"{name} UNAVAILABLE",
                                 (x1 + x2) // 2, (y1 + y2) // 2, RED, F_MICRO,
                                 anchor_x="center", anchor_y="center", font_name=MONO)

    def on_draw(self):
        self.clear()
        w, h = self.window.width, self.window.height

        l_w, r_w  = _rail_widths(w)
        my1       = self._main_y1()
        my2       = h - _TOP_H - _M
        lx1, lx2  = _M, _M + l_w
        rx1, rx2  = w - _M - r_w, w - _M

        self._guard("TRACK", lambda: self._draw_track(lx2 + _GAP, my1, rx1 - _GAP, my2))
        self._guard("TIMING", lambda: self._draw_tower(lx1, my1, lx2, my2),
                    (lx1, my1, lx2, my2))
        self._guard("TELEMETRY", lambda: self._draw_right_rail(rx1, my1, rx2, my2),
                    (rx1, my1, rx2, my2))
        self._guard("HEADER", lambda: self._draw_top_bar(w, h))
        self._guard("TRANSPORT",
                    lambda: self._draw_transport(_M, _FOOT_H, w - _M, _FOOT_H + _TRANS_H))
        console_footer(
            w,
            "SPACE pause · ←→ ±10s · SHIFT+←→ lap · ↑↓ speed · R restart · ESC back · click pins driver A, next pins B",
            _FOOT_H,
        )

    # ── top bar ──────────────────────────────────────────────────────────────

    def _draw_top_bar(self, w, h):
        arcade.draw_lrbt_rectangle_filled(0, w, h - _TOP_H, h, PANEL)
        arcade.draw_line(0, h - _TOP_H, w, h - _TOP_H, HAIRLINE, 1)
        bar_cy = h - _TOP_H // 2

        bx = draw_brand(16, bar_cy)
        arcade.draw_line(bx + 10, bar_cy - 15, bx + 10, bar_cy + 15, HAIRLINE, 1)

        # Event block
        ev_x = bx + 26
        rnd  = config.ROUND
        arcade.draw_text(config.EVENT_NAME.upper(),
                         ev_x, bar_cy + 7, TEXT, F_H2, bold=True,
                         anchor_x="left", anchor_y="center")
        sub = f"{config.YEAR} · RACE" + (f" · ROUND {rnd}" if rnd else "")
        arcade.draw_text(sub, ev_x, bar_cy - 9, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        # Lap counter (centre)
        ref = self.laps.ref_driver
        lap_num = self.laps.info_at_time(ref, self.current_time).get("lap") if ref else None
        total_laps = None
        if ref:
            wins = self.laps.windows_by_driver.get(ref)
            if wins:
                total_laps = wins[-1][0]
        cx = w // 2
        arcade.draw_text("LAP", cx - 40, bar_cy, TEXT_FAINT, F_MICRO,
                         anchor_x="right", anchor_y="center", font_name=MONO)
        lap_str = f"{lap_num if lap_num is not None else '–'}"
        if total_laps:
            lap_str += f" / {total_laps}"
        arcade.draw_text(lap_str, cx - 30, bar_cy + 1, TEXT, F_H1,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        # Track status tag next to the lap counter
        status = self.race_control.active_status(self.current_time)
        if status:
            sc_col = {"SC": AMBER, "VSC": AMBER, "RED": RED}.get(status, AMBER)
            tag(cx + 110, bar_cy, status, INK, bg=sc_col, fs=F_MICRO)

        # Fastest lap so far (purple — timing screen convention). Deliberately
        # not the race's eventual best: showing that from lap one spoils it.
        fl_code, fl_seconds = self.laps.fastest_at(self.current_time)
        fl_x = w - 130
        arcade.draw_text(spaced("FASTEST"), fl_x, bar_cy + 9, TEXT_FAINT, F_MICRO,
                         anchor_x="right", anchor_y="center")
        if fl_code:
            arcade.draw_text(f"{fl_code} {fmt_laptime(fl_seconds)}",
                             fl_x, bar_cy - 8, PURPLE, F_LABEL,
                             anchor_x="right", anchor_y="center", font_name=MONO)
        else:
            arcade.draw_text("—", fl_x, bar_cy - 8, TEXT_FAINT, F_LABEL,
                             anchor_x="right", anchor_y="center", font_name=MONO)

        # Back + exit
        self._back_box = icon_btn(w - 88, bar_cy, 34, 30, "←")
        self._exit_box = icon_btn(w - 46, bar_cy, 34, 30, "✕")

        # Status strip under the bar: green when clear, amber/red on incidents
        strip_col = GREEN
        if status in ("SC", "VSC"):
            strip_col = AMBER
        elif status == "RED":
            strip_col = RED
        arcade.draw_lrbt_rectangle_filled(0, w, h - _TOP_H - 3, h - _TOP_H, strip_col)

    # ── track map (full-bleed, no panel box) ─────────────────────────────────

    def _draw_track(self, x1, y1, x2, y2):
        # Caption — circuit identity, bottom-left of the map space
        ev      = self.event
        circuit = (self.meta.get("circuit") or (ev.location if ev else "")).upper()
        loc     = (self.meta.get("loc")     or (ev.country  if ev else "")).upper()
        if circuit:
            arcade.draw_text(circuit, x1 + 6, y1 + 22, TEXT_FAINT, F_LABEL,
                             anchor_x="left", anchor_y="center", font_name=MONO)
        if loc:
            arcade.draw_text(loc, x1 + 6, y1 + 8, TEXT_FAINT, F_MICRO,
                             anchor_x="left", anchor_y="center", font_name=MONO)

        if len(self.center_loop) > 1:
            # Asphalt ribbon + hairline edges
            arcade.draw_line_strip(self.center_loop, TRACK_ASPHALT, 14)
            arcade.draw_line_strip(self.outer_loop, TRACK_EDGE, 1)
            arcade.draw_line_strip(self.inner_loop, TRACK_EDGE, 1)

            # Start/finish: amber tick perpendicular to the racing line
            (p0x, p0y), (p1x, p1y) = self.center_loop[0], self.center_loop[1]
            dx, dy = p1x - p0x, p1y - p0y
            ln = max((dx * dx + dy * dy) ** 0.5, 1e-6)
            nx, ny = -dy / ln, dx / ln
            arcade.draw_line(p0x - nx * 11, p0y - ny * 11,
                             p0x + nx * 11, p0y + ny * 11, AMBER, 3)

        # Pit entry marker
        if self._pit_world:
            mpx, mpy = self.transform.to_screen(*self._pit_world)
            tag(mpx, mpy, "PIT", GREEN)

        # Ghost trails (fade towards background)
        for code in self.drivers:
            trail = list(self._trails[code])
            n = len(trail)
            if n < 2:
                continue
            base = self.car_colors.get(code, (180, 180, 185))
            for i, (twx, twy) in enumerate(trail[:-1]):
                frac = (i + 1) / n
                r = int(BG[0] + (base[0] - BG[0]) * frac * 0.7)
                g = int(BG[1] + (base[1] - BG[1]) * frac * 0.7)
                b = int(BG[2] + (base[2] - BG[2]) * frac * 0.7)
                radius = max(1, int(CAR_RADIUS * 0.5 * frac))
                tsx, tsy = self.transform.to_screen(twx, twy)
                arcade.draw_circle_filled(tsx, tsy, radius, (r, g, b))

        # Cars
        for code in self.drivers:
            pos = self._driver_screen_pos(code)
            if pos is None:
                continue
            sx, sy = pos
            color  = self.car_colors.get(code, (180, 180, 185))

            pin_col  = AMBER if code == self.pin_a else (CYAN if code == self.pin_b else None)
            is_hover = self.hover_driver == code

            arcade.draw_circle_filled(sx, sy, CAR_RADIUS - 1, color)

            if pin_col is not None:
                arcade.draw_circle_outline(sx, sy, CAR_RADIUS + 3, pin_col, 2)
            elif is_hover:
                arcade.draw_circle_outline(sx, sy, CAR_RADIUS + 3, WHITE, 2)
            else:
                arcade.draw_circle_outline(sx, sy, CAR_RADIUS - 1, BG, 1)

            if pin_col is not None or is_hover:
                lbl_col = pin_col if pin_col is not None else WHITE
                arcade.draw_text(code, sx + 12, sy + 10, lbl_col, F_LABEL,
                                 anchor_x="left", anchor_y="center", font_name=MONO)
            else:
                arcade.draw_text(code, sx + 10, sy + 9, TEXT_DIM, F_MICRO,
                                 anchor_x="left", anchor_y="center", font_name=MONO)

    # ── rails ────────────────────────────────────────────────────────────────

    def _draw_tower(self, x1, y1, x2, y2):
        hitboxes, _ = draw_leaderboard(
            self.stream, self.laps, self.drivers, self.current_time,
            self.car_colors, self.pin_a, self.pin_b, self.hover_driver,
            x1, y1, x2, y2,
        )
        self.leaderboard_hitboxes = hitboxes

    def _card_drivers(self):
        """Resolve what each telemetry card shows.

        Hover previews into the first empty slot; pinned drivers hold theirs.
        Returns ((code_a, state_a), (code_b, state_b)).
        """
        hov = self.hover_driver
        a = (self.pin_a, "PINNED") if self.pin_a else (None, None)
        b = (self.pin_b, "PINNED") if self.pin_b else (None, None)
        if hov and hov not in (self.pin_a, self.pin_b):
            if self.pin_a is None:
                a = (hov, "PREVIEW")
            elif self.pin_b is None:
                b = (hov, "PREVIEW")
        return a, b

    def _gap_info(self, code):
        """(position, gap_to_leader_seconds | None) from the timing stream."""
        for pos, c, gap in self.stream.order_at_time(self.current_time, self.drivers):
            if c != code:
                continue
            if pos == 1:
                return pos, 0.0
            if gap:
                try:
                    return pos, float(gap.lstrip("+"))
                except ValueError:
                    return pos, None
            return pos, None
        return None, None

    def _draw_delta_strip(self, code_a, code_b, x1, y1, x2, y2):
        filled_rrect(x1, y1, x2, y2, R, PANEL)
        outline_rrect(x1, y1, x2, y2, R, HAIRLINE)
        cy = (y1 + y2) // 2

        pos_a, gap_a = self._gap_info(code_a)
        pos_b, gap_b = self._gap_info(code_b)

        lbl_a = f"{code_a}" + (f" P{pos_a}" if pos_a else "")
        lbl_b = f"{code_b}" + (f" P{pos_b}" if pos_b else "")
        arcade.draw_text(lbl_a, x1 + PAD, cy, AMBER, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        arcade.draw_text(lbl_b, x2 - PAD, cy, CYAN, F_MICRO,
                         anchor_x="right", anchor_y="center", font_name=MONO)

        if gap_a is not None and gap_b is not None:
            delta = f"Δ {abs(gap_b - gap_a):.3f}s"
        else:
            delta = "Δ —"
        arcade.draw_text(delta, (x1 + x2) // 2, cy, TEXT, F_LABEL,
                         anchor_x="center", anchor_y="center", font_name=MONO)

    def _draw_right_rail(self, x1, y1, x2, y2):
        avail   = y2 - y1
        tele_h  = max(168, min(205, int(avail * 0.26)))
        delta_h = 24
        cond_h  = 104

        (code_a, state_a), (code_b, state_b) = self._card_drivers()

        # Card A (amber)
        a_y1 = y2 - tele_h
        draw_stats_panel(self.driver_data, self.laps, self.current_time,
                         code_a, "A", state_a, x1, a_y1, x2, y2)
        draw_rc_popup(self.race_control,
                      self.abbr_to_num.get(code_a, ""),
                      code_a, AMBER, self.current_time, x1, a_y1, x2, y2)

        # Delta strip — only meaningful with two drivers up
        d_y2 = a_y1 - _GAP
        d_y1 = d_y2 - delta_h
        if code_a and code_b:
            self._draw_delta_strip(code_a, code_b, x1, d_y1, x2, d_y2)
        else:
            filled_rrect(x1, d_y1, x2, d_y2, R, PANEL)
            outline_rrect(x1, d_y1, x2, d_y2, R, HAIRLINE)
            arcade.draw_text("Δ INTERVAL", (x1 + x2) // 2, (d_y1 + d_y2) // 2,
                             TEXT_FAINT, F_MICRO,
                             anchor_x="center", anchor_y="center", font_name=MONO)

        # Card B (cyan)
        b_y2 = d_y1 - _GAP
        b_y1 = b_y2 - tele_h
        draw_stats_panel(self.driver_data, self.laps, self.current_time,
                         code_b, "B", state_b, x1, b_y1, x2, b_y2)
        draw_rc_popup(self.race_control,
                      self.abbr_to_num.get(code_b, ""),
                      code_b, CYAN, self.current_time, x1, b_y1, x2, b_y2)

        c_y2 = b_y1 - _GAP
        c_y1 = c_y2 - cond_h
        draw_weather_panel(self.weather, self.current_time, x1, c_y1, x2, c_y2)

        rc_y2 = c_y1 - _GAP
        if rc_y2 - y1 >= 50:
            draw_race_control_panel(self.race_control, self.current_time,
                                    x1, y1, x2, rc_y2)

    # ── transport bar ─────────────────────────────────────────────────────────

    def _draw_transport(self, x1, y1, x2, y2):
        filled_rrect(x1, y1, x2, y2, R, PANEL)
        outline_rrect(x1, y1, x2, y2, R, HAIRLINE)

        cy = (y1 + y2) // 2
        bx = x1 + PAD

        self._restart_btn   = icon_btn(bx + 13, cy, 26, 26, "⟲"); bx += 32
        self._skip_back_btn = icon_btn(bx + 23, cy, 46, 26, "« LAP",
                                       fs=F_MICRO); bx += 52
        # Play/pause — the one amber button on screen
        pp_sym = "▶" if self.paused else "❚❚"
        self._play_btn = icon_btn(bx + 18, cy, 36, 32, pp_sym,
                                  bg=AMBER, fg=INK, border=AMBER); bx += 42
        self._skip_fwd_btn = icon_btn(bx + 23, cy, 46, 26, "LAP »",
                                      fs=F_MICRO); bx += 52

        max_replay = float(self.t_max) - float(self.t0)

        arcade.draw_text(fmt_hms(self.replay_time), bx + 10, cy, TEXT, F_LABEL,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        scrub_x1 = bx + 76
        scrub_x2 = x2 - 226
        self._scrubber_box = (scrub_x1, y1, scrub_x2, y2)

        progress = max(0.0, min(1.0, self.replay_time / max_replay if max_replay > 0 else 0.0))
        handle_x = int(scrub_x1 + progress * (scrub_x2 - scrub_x1))

        # Rail + progress
        arcade.draw_lrbt_rectangle_filled(scrub_x1, scrub_x2, cy - 2, cy + 2, CARD_HI)
        if handle_x > scrub_x1:
            arcade.draw_lrbt_rectangle_filled(scrub_x1, handle_x, cy - 2, cy + 2, AMBER)

        # Lap ticks every 10 laps
        ref = self.laps.ref_driver
        if ref and max_replay > 0:
            for (lap_no, start_s, *_rest) in self.laps.windows_by_driver.get(ref, []):
                if lap_no % 10 == 0:
                    tx = scrub_x1 + (start_s - self.t0) / max_replay * (scrub_x2 - scrub_x1)
                    if scrub_x1 <= tx <= scrub_x2:
                        arcade.draw_line(tx, cy - 5, tx, cy + 5, HAIRLINE_HI, 1)
                        arcade.draw_text(str(lap_no), tx, cy - 12, TEXT_FAINT, F_MICRO,
                                         anchor_x="center", anchor_y="center",
                                         font_name=MONO)

        # Handle: square console knob
        arcade.draw_lrbt_rectangle_filled(handle_x - 4, handle_x + 4, cy - 8, cy + 8, AMBER)
        arcade.draw_lrbt_rectangle_outline(handle_x - 4, handle_x + 4, cy - 8, cy + 8, INK, 1)

        # Current lap tag above the handle
        if ref:
            lap = self.laps.info_at_time(ref, self.current_time).get("lap")
            if lap is not None:
                tag(handle_x, cy + 17, f"L{lap}", INK, bg=AMBER)

        arcade.draw_text(fmt_hms(max_replay), scrub_x2 + 12, cy, TEXT_FAINT, F_LABEL,
                         anchor_x="left", anchor_y="center", font_name=MONO)

        # Speed stepper — standard ladder 0.25× … 20×
        spd_cx = x2 - 76
        self._spd_down_btn = icon_btn(spd_cx - 48, cy, 24, 24, "−")
        arcade.draw_text(f"{self.time_speed:g}×", spd_cx, cy + 5, AMBER, F_H2,
                         anchor_x="center", anchor_y="center", font_name=MONO)
        arcade.draw_text("SPEED", spd_cx, cy - 11, TEXT_FAINT, F_MICRO,
                         anchor_x="center", anchor_y="center", font_name=MONO)
        self._spd_up_btn = icon_btn(spd_cx + 48, cy, 24, 24, "+")

    # ── update / input ────────────────────────────────────────────────────────

    def _step_speed(self, direction):
        """Move playback speed one notch along the standard ladder."""
        s = self.time_speed
        if direction > 0:
            for v in SPEED_STEPS:
                if v > s + 1e-9:
                    self.time_speed = v
                    return
            self.time_speed = SPEED_STEPS[-1]
        else:
            for v in reversed(SPEED_STEPS):
                if v < s - 1e-9:
                    self.time_speed = v
                    return
            self.time_speed = SPEED_STEPS[0]

    def _seek(self, t_target):
        max_replay = float(self.t_max) - float(self.t0)
        self.replay_time  = max(0.0, min(max_replay, t_target - self.t0))
        self.current_time = self.t0 + self.replay_time
        self._clear_trails()

    def _skip_time(self, direction):
        self._seek(self.current_time + direction * SKIP_SECONDS)

    def _skip_lap(self, direction):
        """Jump to the next/previous lap start of the reference driver."""
        ref    = self.laps.ref_driver
        starts = [w[1] for w in self.laps.windows_by_driver.get(ref, [])] if ref else []
        if not starts:
            self._skip_time(direction)
            return
        t = self.current_time
        if direction > 0:
            target = next((s for s in starts if s > t + 0.5), self.t_max)
        else:
            # 1.5 s grace so a double-press steps back a full lap, not to the
            # start of the current one twice
            prev = [s for s in starts if s < t - 1.5]
            target = prev[-1] if prev else self.t0
        self._seek(target)

    def _sample_trails(self):
        """Append current world positions to each driver's trail deque."""
        for code in self.drivers:
            data = self.driver_data.get(code)
            if not data:
                continue
            t = data["t"]
            if t[0] <= self.current_time <= t[-1]:
                wx = float(np.interp(self.current_time, t, data["x"]))
                wy = float(np.interp(self.current_time, t, data["y"]))
                self._trails[code].append((wx, wy))

    def _clear_trails(self):
        self._trails = {code: deque(maxlen=22) for code in self.drivers}

    def on_update(self, delta_time):
        if self.paused:
            return
        self.replay_time += delta_time * self.time_speed
        max_replay = float(self.t_max) - float(self.t0)
        self.replay_time  = max(0.0, min(max_replay, self.replay_time))
        self.current_time = self.t0 + self.replay_time
        dt_abs = abs(self.current_time - self._last_t)
        if dt_abs > 2.0:
            self._clear_trails()
        self._last_t = self.current_time
        self._sample_trails()

    def on_key_press(self, symbol, modifiers):
        shift = bool(modifiers & arcade.key.MOD_SHIFT)
        if symbol == arcade.key.SPACE:
            self.paused = not self.paused
        elif symbol == arcade.key.R:
            self._seek(self.t0)
        elif symbol == arcade.key.LEFT:
            self._skip_lap(-1) if shift else self._skip_time(-1)
        elif symbol == arcade.key.RIGHT:
            self._skip_lap(+1) if shift else self._skip_time(+1)
        elif symbol == arcade.key.UP:
            self._step_speed(+1)
        elif symbol == arcade.key.DOWN:
            self._step_speed(-1)
        elif symbol == arcade.key.ESCAPE:
            from f1replay.ui.selection import SelectionView
            self.window.show_view(SelectionView())
            return True   # consume so pyglet's default ESC-close never fires

    def on_mouse_motion(self, x, y, dx, dy):
        if self._scrubbing and self._scrubber_box:
            sx1, _, sx2, _ = self._scrubber_box
            progress          = max(0.0, min(1.0, (x - sx1) / max(1, sx2 - sx1)))
            max_replay        = float(self.t_max) - float(self.t0)
            self.replay_time  = progress * max_replay
            self.current_time = self.t0 + self.replay_time
            return

        self.hover_driver = pick_driver_anywhere(
            self.drivers, self.driver_data, self.current_time,
            self.transform, self.leaderboard_hitboxes, x, y,
        )

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        if self._back_box:
            bx1, by1, bx2, by2 = self._back_box
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                from f1replay.ui.selection import SelectionView
                self.window.show_view(SelectionView())
                return

        if self._exit_box:
            ex1, ey1, ex2, ey2 = self._exit_box
            if ex1 <= x <= ex2 and ey1 <= y <= ey2:
                self.window.close()
                return

        for box, action in [
            (self._restart_btn,   lambda: self._seek(self.t0)),
            (self._skip_back_btn, lambda: self._skip_lap(-1)),
            (self._play_btn,      lambda: setattr(self, "paused", not self.paused)),
            (self._skip_fwd_btn,  lambda: self._skip_lap(+1)),
            (self._spd_down_btn,  lambda: self._step_speed(-1)),
            (self._spd_up_btn,    lambda: self._step_speed(+1)),
        ]:
            if box:
                bx1, by1, bx2, by2 = box
                if bx1 <= x <= bx2 and by1 <= y <= by2:
                    action()
                    return

        if self._scrubber_box:
            sx1, sy1, sx2, sy2 = self._scrubber_box
            if sx1 <= x <= sx2 and sy1 <= y <= sy2:
                self._scrubbing = True
                progress          = max(0.0, min(1.0, (x - sx1) / max(1, sx2 - sx1)))
                max_replay        = float(self.t_max) - float(self.t0)
                self.replay_time  = progress * max_replay
                self.current_time = self.t0 + self.replay_time
                return

        code = pick_driver_anywhere(
            self.drivers, self.driver_data, self.current_time,
            self.transform, self.leaderboard_hitboxes, x, y,
        )
        if code is None:
            # Click on empty space clears both pins
            self.pin_a = None
            self.pin_b = None
        elif code == self.pin_a:
            # Unpin A; promote B so slot A is always filled first
            self.pin_a = self.pin_b
            self.pin_b = None
        elif code == self.pin_b:
            self.pin_b = None
        elif self.pin_a is None:
            self.pin_a = code
        elif self.pin_b is None:
            self.pin_b = code
        else:
            # Both slots full — replace the comparison driver
            self.pin_b = code

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self._scrubbing = False
            self._clear_trails()

    def on_resize(self, width, height):
        self._rebuild_geometry()


class RaceWindow(arcade.Window):
    def __init__(self, event=None):
        from f1replay.ui.selection import (
            SEL_W, SEL_H, SelectionView, LoadingView, apply_event,
        )
        super().__init__(SEL_W, SEL_H, config.SCREEN_TITLE, resizable=True)
        arcade.set_background_color(BG)
        if event is None:
            self.show_view(SelectionView())
            return
        # Launched as `f1replay <race> <year>` — skip the select screen. ESC
        # from the replay still drops back into it.
        apply_event(event)
        self.set_caption(config.SCREEN_TITLE)
        self.show_view(LoadingView())

    def on_resize(self, width, height):
        super().on_resize(width, height)
        if isinstance(self.current_view, RaceView):
            self.current_view._rebuild_geometry()
