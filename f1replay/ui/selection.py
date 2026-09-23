"""F1 Race Replay — session select — round list left, editorial race hero right."""
import arcade
from f1replay import config
from f1replay.core.calendar import YEARS, season, season_error, resolve
from f1replay.ui.design import (
    panel, section, filled_rrect, outline_rrect, tag, divider, meter,
    draw_brand, console_footer, draw_circuit, spaced,
    BG, PANEL, CARD, CARD_HI, HAIRLINE, HAIRLINE_HI,
    AMBER, AMBER_DARK, RED, MONO, INK,
    TEXT, TEXT_DIM, TEXT_FAINT,
    F_GIANT, F_TITLE, F_H1, F_H2, F_LABEL, F_MICRO,
    PAD, R, RACE_DOT,
)

SEL_W, SEL_H = 1400, 900

_TOP_H  = 58
_CTRL_H = 44
_FOOT_H = 22
_M      = 12
_GAP    = 10

# 3 horizontal stripe colors for each country's flag (bottom → top)
_FLAG_STRIPES = {
    "Austria":        ((185, 18, 38), (235, 240, 250), (185, 18, 38)),
    "Bahrain":        ((215, 20, 40), (245, 245, 245), (215, 20, 40)),
    "Saudi Arabia":   ((0, 115, 45),  (0, 115, 45),    (0, 115, 45)),
    "Australia":      ((0, 40, 160),  (215, 20, 40),   (245, 245, 245)),
    "Japan":          ((245,245,245), (215, 20, 40),   (245, 245, 245)),
    "China":          ((200, 20, 40), (200, 20, 40),   (200, 20, 40)),
    "Miami":          ((0, 40, 160),  (245, 245, 245), (215, 20, 40)),
    "Emilia Romagna": ((0, 140, 70),  (245, 245, 245), (215, 20, 40)),
    "Monaco":         ((215, 20, 40), (215, 20, 40),   (245, 245, 245)),
    "Canada":         ((215, 20, 40), (245, 245, 245), (215, 20, 40)),
    "Spain":          ((215, 20, 40), (215, 165, 0),   (215, 20, 40)),
    "Great Britain":  ((0, 40, 160),  (215, 20, 40),   (245, 245, 245)),
    "Hungary":        ((0, 140, 70),  (245, 245, 245), (215, 20, 40)),
    "Belgium":        ((215, 20, 40), (215, 165, 0),   (20, 20, 20)),
    "Netherlands":    ((0, 40, 160),  (245, 245, 245), (215, 20, 40)),
    "Italy":          ((0, 140, 70),  (245, 245, 245), (215, 20, 40)),
    "Azerbaijan":     ((0, 130, 70),  (215, 20, 40),   (0, 90, 180)),
    "Singapore":      ((215, 20, 40), (245, 245, 245), (215, 20, 40)),
    "United States":  ((0, 40, 160),  (215, 20, 40),   (245, 245, 245)),
    "Mexico":         ((0, 130, 50),  (245, 245, 245), (215, 20, 40)),
    "Brazil":         ((0, 150, 58),  (215, 165, 0),   (0, 150, 58)),
    "Las Vegas":      ((0, 40, 160),  (215, 20, 40),   (245, 245, 245)),
    "Qatar":          ((130, 20, 30), (245, 245, 245), (130, 20, 30)),
    "Abu Dhabi":      ((0, 100, 50),  (245, 245, 245), (20, 20, 20)),
    # Venues off the modern calendar, reachable now that seasons are real.
    "France":         ((215, 20, 40), (245, 245, 245), (0, 40, 160)),
    "Germany":        ((215, 165, 0), (215, 20, 40),   (20, 20, 20)),
    "Russia":         ((215, 20, 40), (0, 57, 166),    (245, 245, 245)),
    "Turkey":         ((215, 20, 40), (215, 20, 40),   (215, 20, 40)),
    "Portugal":       ((215, 20, 40), (0, 102, 51),    (0, 102, 51)),
}


def _draw_flag(circuit_key, country, cx, cy, w=18, h=12):
    """Mini 3-stripe flag, by circuit then by country."""
    x1, x2 = int(cx - w / 2), int(cx + w / 2)
    y1, y2 = int(cy - h / 2), int(cy + h / 2)
    stripes = _FLAG_STRIPES.get(circuit_key) or _FLAG_STRIPES.get(country)
    if stripes:
        sh = (y2 - y1) // 3
        for i, col in enumerate(stripes):
            arcade.draw_lrbt_rectangle_filled(
                x1, x2, y1 + i * sh,
                y1 + (i + 1) * sh if i < 2 else y2, col)
        arcade.draw_lrbt_rectangle_outline(x1, x2, y1, y2, HAIRLINE_HI, 1)
    else:
        dot_col = RACE_DOT.get(circuit_key) or RACE_DOT.get(country, (80, 90, 110))
        arcade.draw_circle_filled(cx, cy, h // 2, dot_col)


# Editorial facts per circuit, keyed by Event.circuit_key. Season-dependent
# values (round number, date) are NOT read from here — they come from the real
# schedule via core.calendar, because they differ every year. The "round" and
# "date" entries below are vestigial 2025 values; only the circuit-constant
# fields (laps, dist, record, traits, desc) are used.
_RACE_META = {
    "Bahrain": {
        "round": 1, "circuit": "Bahrain International Circuit", "loc": "Sakhir, Bahrain",
        "laps": 57, "dist": "308.238 km", "record": "1:31.447 · Leclerc (2019)",
        "date": "16 Mar 2025", "diff": "Medium", "ot": "High",
        "tyre": "High", "fuel": "Medium",
        "desc": ("The floodlit Bahrain International Circuit hosts the season opener. "
                 "Long straights and heavy braking zones demand precise tyre management across its desert setting."),
    },
    "Saudi Arabia": {
        "round": 2, "circuit": "Jeddah Corniche Circuit", "loc": "Jeddah, Saudi Arabia",
        "laps": 50, "dist": "308.450 km", "record": "1:30.734 · Verstappen (2021)",
        "date": "22 Mar 2025", "diff": "High", "ot": "Medium",
        "tyre": "Medium", "fuel": "High",
        "desc": ("One of the fastest street circuits on the calendar. Over 27 corners with "
                 "minimal run-off and walls everywhere demand absolute commitment and bravery."),
    },
    "Australia": {
        "round": 3, "circuit": "Albert Park Circuit", "loc": "Melbourne, Australia",
        "laps": 58, "dist": "307.574 km", "record": "1:19.813 · Hamilton (2019)",
        "date": "30 Mar 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "Low", "fuel": "Low",
        "desc": ("Set around the picturesque Albert Park lake, Melbourne's circuit blends "
                 "fast flowing sections with tight chicanes. A superb season-opening spectacle."),
    },
    "Japan": {
        "round": 4, "circuit": "Suzuka International Racing Course", "loc": "Suzuka, Japan",
        "laps": 53, "dist": "307.471 km", "record": "1:30.983 · Räikkönen (2005)",
        "date": "6 Apr 2025", "diff": "High", "ot": "Low",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("The iconic figure-of-eight Suzuka layout is widely regarded as the greatest "
                 "circuit on the calendar. Requires perfection through Spoon, 130R and the Esses."),
    },
    "China": {
        "round": 5, "circuit": "Shanghai International Circuit", "loc": "Shanghai, China",
        "laps": 56, "dist": "305.066 km", "record": "1:32.238 · Räikkönen (2004)",
        "date": "20 Apr 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("Shanghai's sweeping back straight and the iconic Turn 1-2 complex define the "
                 "Chinese GP. Overtaking is possible but requires strategy and bravery."),
    },
    "Miami": {
        "round": 6, "circuit": "Miami International Autodrome", "loc": "Miami Gardens, USA",
        "laps": 57, "dist": "308.326 km", "record": "1:29.708 · Verstappen (2023)",
        "date": "4 May 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "High", "fuel": "Medium",
        "desc": ("The Miami circuit winds around Hard Rock Stadium in a made-for-TV spectacle. "
                 "Its unique marina section and multiple DRS zones create exciting racing."),
    },
    "Emilia Romagna": {
        "round": 7, "circuit": "Autodromo Enzo e Dino Ferrari", "loc": "Imola, Italy",
        "laps": 63, "dist": "309.049 km", "record": "1:15.484 · Hamilton (2020)",
        "date": "18 May 2025", "diff": "High", "ot": "Low",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("Historic Imola is tight, technical and unforgiving. The narrow layout punishes "
                 "mistakes heavily and makes overtaking rare, placing emphasis on qualifying."),
    },
    "Monaco": {
        "round": 8, "circuit": "Circuit de Monaco", "loc": "Monte Carlo, Monaco",
        "laps": 78, "dist": "260.286 km", "record": "1:12.909 · Räikkönen (2018)",
        "date": "25 May 2025", "diff": "High", "ot": "Low",
        "tyre": "Low", "fuel": "Low",
        "desc": ("The crown jewel of Formula 1. Monaco's narrow streets, barriers and "
                 "barriers make it the ultimate test of precision and nerve at every lap."),
    },
    "Canada": {
        "round": 9, "circuit": "Circuit Gilles Villeneuve", "loc": "Montreal, Canada",
        "laps": 70, "dist": "305.270 km", "record": "1:13.078 · Bottas (2019)",
        "date": "15 Jun 2025", "diff": "Medium", "ot": "High",
        "tyre": "Medium", "fuel": "High",
        "desc": ("The Circuit Gilles Villeneuve on Île Notre-Dame is a power circuit. The "
                 "infamous Wall of Champions and long straights make for dramatic wheel-to-wheel racing."),
    },
    "Spain": {
        "round": 10, "circuit": "Circuit de Barcelona-Catalunya", "loc": "Barcelona, Spain",
        "laps": 66, "dist": "307.104 km", "record": "1:16.330 · Verstappen (2023)",
        "date": "22 Jun 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "High", "fuel": "Medium",
        "desc": ("Barcelona's smooth and technical circuit has hosted F1 testing for decades. "
                 "It rewards aerodynamic efficiency and tyre management across all compound types."),
    },
    "Austria": {
        "round": 11, "circuit": "Red Bull Ring", "loc": "Spielberg, Austria",
        "laps": 71, "dist": "306.452 km", "record": "1:05.619 · Sainz (2020)",
        "date": "29 Jun 2025", "diff": "Medium", "ot": "High",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("Set in the heart of Styria, the Red Bull Ring is a high-speed circuit "
                 "known for dramatic elevation changes and overtaking opportunities. "
                 "A true test of precision and power."),
    },
    "Great Britain": {
        "round": 12, "circuit": "Silverstone Circuit", "loc": "Silverstone, England",
        "laps": 52, "dist": "306.198 km", "record": "1:27.097 · Hamilton (2020)",
        "date": "6 Jul 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "High", "fuel": "Low",
        "desc": ("The home of Formula 1. Silverstone's iconic high-speed corners — Copse, "
                 "Maggotts, Becketts — demand ultimate car balance and driver commitment."),
    },
    "Hungary": {
        "round": 13, "circuit": "Hungaroring", "loc": "Budapest, Hungary",
        "laps": 70, "dist": "306.630 km", "record": "1:16.627 · Hamilton (2020)",
        "date": "20 Jul 2025", "diff": "High", "ot": "Low",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("The twisty Hungaroring is often compared to Monaco without the walls. "
                 "Its low-speed, high-downforce layout makes overtaking very difficult."),
    },
    "Belgium": {
        "round": 14, "circuit": "Circuit de Spa-Francorchamps", "loc": "Stavelot, Belgium",
        "laps": 44, "dist": "308.052 km", "record": "1:46.286 · Bottas (2018)",
        "date": "27 Jul 2025", "diff": "High", "ot": "High",
        "tyre": "High", "fuel": "High",
        "desc": ("Spa-Francorchamps is one of the greatest circuits ever built. Eau Rouge, "
                 "Raidillon and Pouhon reward bravery, while unpredictable Ardennes weather adds drama."),
    },
    "Netherlands": {
        "round": 15, "circuit": "Circuit Zandvoort", "loc": "Zandvoort, Netherlands",
        "laps": 72, "dist": "306.587 km", "record": "1:11.097 · Verstappen (2021)",
        "date": "31 Aug 2025", "diff": "High", "ot": "Low",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("Zandvoort returned to the calendar in 2021 with Verstappen mania sweeping the "
                 "nation. Its banked corners and narrow layout are unique in modern Formula 1."),
    },
    "Italy": {
        "round": 16, "circuit": "Autodromo Nazionale Monza", "loc": "Monza, Italy",
        "laps": 53, "dist": "306.720 km", "record": "1:21.046 · Barrichello (2004)",
        "date": "7 Sep 2025", "diff": "Low", "ot": "High",
        "tyre": "Low", "fuel": "Low",
        "desc": ("The Temple of Speed. Monza is the fastest circuit on the calendar, "
                 "featuring iconic tifosi passion, slipstream battles and breathtaking top speeds."),
    },
    "Azerbaijan": {
        "round": 17, "circuit": "Baku City Circuit", "loc": "Baku, Azerbaijan",
        "laps": 51, "dist": "306.049 km", "record": "1:43.009 · Leclerc (2023)",
        "date": "21 Sep 2025", "diff": "High", "ot": "High",
        "tyre": "Low", "fuel": "High",
        "desc": ("Baku's street circuit combines a long 2.2 km straight with a tight, "
                 "narrow old city section. Safety Cars are frequent and nothing is predictable."),
    },
    "Singapore": {
        "round": 18, "circuit": "Marina Bay Street Circuit", "loc": "Singapore",
        "laps": 62, "dist": "306.143 km", "record": "1:35.867 · Leclerc (2023)",
        "date": "5 Oct 2025", "diff": "High", "ot": "Low",
        "tyre": "Medium", "fuel": "High",
        "desc": ("The Singapore night race is Formula 1's most physically demanding event. "
                 "Humidity, heat and zero run-off combine for an unforgiving street circuit challenge."),
    },
    "United States": {
        "round": 19, "circuit": "Circuit of the Americas", "loc": "Austin, Texas, USA",
        "laps": 56, "dist": "308.405 km", "record": "1:36.169 · Hamilton (2019)",
        "date": "19 Oct 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "High", "fuel": "Medium",
        "desc": ("COTA's flowing layout across the Texas hills features 20 varied corners. "
                 "The uphill Turn 1 is an iconic overtaking opportunity heading into the first complex."),
    },
    "Mexico": {
        "round": 20, "circuit": "Autodromo Hermanos Rodriguez", "loc": "Mexico City, Mexico",
        "laps": 71, "dist": "305.354 km", "record": "1:17.774 · Bottas (2021)",
        "date": "26 Oct 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "Low", "fuel": "Low",
        "desc": ("At 2,285 metres altitude the thin air of Mexico City reduces aerodynamic "
                 "grip and engine power. The stadium section through the baseball venue is unique."),
    },
    "Brazil": {
        "round": 21, "circuit": "Autodromo Jose Carlos Pace", "loc": "São Paulo, Brazil",
        "laps": 71, "dist": "305.879 km", "record": "1:10.540 · Verstappen (2023)",
        "date": "9 Nov 2025", "diff": "Medium", "ot": "High",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("Interlagos is a legendary circuit with passionate Brazilian fans. "
                 "Unpredictable weather, an anti-clockwise layout and Senna S create unforgettable races."),
    },
    "Las Vegas": {
        "round": 22, "circuit": "Las Vegas Street Circuit", "loc": "Las Vegas, Nevada, USA",
        "laps": 50, "dist": "309.958 km", "record": "1:35.490 · Verstappen (2023)",
        "date": "22 Nov 2025", "diff": "Medium", "ot": "High",
        "tyre": "Low", "fuel": "High",
        "desc": ("F1 races down the Vegas Strip in a dazzling night spectacle. "
                 "The 1.9 km Koval straight is the longest on the calendar, producing wheel-to-wheel drama."),
    },
    "Qatar": {
        "round": 23, "circuit": "Lusail International Circuit", "loc": "Lusail, Qatar",
        "laps": 57, "dist": "306.660 km", "record": "1:24.319 · Verstappen (2023)",
        "date": "30 Nov 2025", "diff": "High", "ot": "Medium",
        "tyre": "High", "fuel": "Medium",
        "desc": ("The floodlit Lusail circuit is one of the most physically demanding on the "
                 "calendar. High-speed sweeping corners load the neck and expose tyre degradation."),
    },
    "Abu Dhabi": {
        "round": 24, "circuit": "Yas Marina Circuit", "loc": "Abu Dhabi, UAE",
        "laps": 58, "dist": "306.183 km", "record": "1:26.103 · Verstappen (2021)",
        "date": "7 Dec 2025", "diff": "Medium", "ot": "Medium",
        "tyre": "Medium", "fuel": "Medium",
        "desc": ("The season finale at Yas Marina blends slow technical sections with "
                 "fast sweeping corners. A stunning twilight setting under the Yas Hotel bridge."),
    },
}

_LEVEL = {"Low": 1, "Medium": 2, "High": 3}


def apply_event(event):
    """Point config at a race. Shared by the select screen and the CLI so both
    reach RaceView through exactly one path."""
    config.YEAR         = event.year
    config.ROUND        = event.round
    config.EVENT_NAME   = event.name
    config.CIRCUIT_KEY  = event.circuit_key or ""
    config.SCREEN_TITLE = f"F1 Race Replay — {event.short} {event.year}"


class SelectionView(arcade.View):
    def __init__(self):
        super().__init__()
        self.selected_year  = YEARS[0]
        self.selected_round = None      # resolved lazily on first draw
        self.search_text    = ""
        self._year_boxes    = []
        self._race_boxes    = []
        self._start_box     = None
        self._mouse         = (-1, -1)

    def _hovered(self, x1, y1, x2, y2):
        mx, my = self._mouse
        return x1 <= mx <= x2 and y1 <= my <= y2

    # ── season state ──────────────────────────────────────────────────────────

    def _selected_event(self):
        """The highlighted event, resolving a default on first use."""
        events = season(self.selected_year)
        if not events:
            return None
        if self.selected_round is not None:
            for ev in events:
                if ev.round == self.selected_round:
                    return ev
        ev = resolve(self.selected_year, "Austria") or events[0]
        self.selected_round = ev.round
        return ev

    def _set_year(self, year):
        """Switch season, staying at the same circuit where it still exists."""
        if year == self.selected_year:
            return
        current = self._selected_event()
        key = current.circuit_key if current else None
        self.selected_year = year
        events = season(year)
        if not events:
            self.selected_round = None
            return
        match = next((e for e in events if key and e.circuit_key == key),
                     events[0])
        self.selected_round = match.round

    def _visible_events(self):
        """Season events narrowed by the search box."""
        events = season(self.selected_year)
        q = self.search_text.lower().strip()
        if not q:
            return events
        return [e for e in events
                if q in e.short.lower() or q in e.name.lower()
                or q in e.location.lower() or q in e.country.lower()]

    def on_show_view(self):
        arcade.set_background_color(BG)

    # ── draw ──────────────────────────────────────────────────────────────────

    def on_draw(self):
        self.clear()
        w, h = self.window.width, self.window.height

        self._year_boxes = []
        self._race_boxes = []

        ctrl_y2 = h - _TOP_H - _GAP
        ctrl_y1 = ctrl_y2 - _CTRL_H
        body_y2 = ctrl_y1 - _GAP
        body_y1 = _FOOT_H + _M

        list_w = max(330, int(w * 0.32))
        lx1, lx2 = _M, _M + list_w
        rx1, rx2 = lx2 + _GAP, w - _M

        self._draw_top_bar(w, h)
        self._draw_control_row(_M, ctrl_y1, w - _M, ctrl_y2)
        self._draw_race_list(lx1, body_y1, lx2, body_y2)
        self._draw_hero(rx1, body_y1, rx2, body_y2)
        console_footer(w, "type to search · ENTER start · ESC clear", _FOOT_H)

    def _draw_top_bar(self, w, h):
        arcade.draw_lrbt_rectangle_filled(0, w, h - _TOP_H, h, PANEL)
        arcade.draw_line(0, h - _TOP_H, w, h - _TOP_H, HAIRLINE, 1)
        bar_cy = h - _TOP_H // 2
        draw_brand(16, bar_cy)
        arcade.draw_text(spaced("SELECT GRAND PRIX"), w - 16, bar_cy,
                         TEXT_FAINT, F_LABEL,
                         anchor_x="right", anchor_y="center")

    def _draw_control_row(self, x1, y1, x2, y2):
        cy = (y1 + y2) // 2

        # Year chips
        cx = x1
        for year in YEARS:
            bw, bh = 62, 30
            bx1, bx2 = cx, cx + bw
            by1, by2 = cy - bh // 2, cy + bh // 2
            self._year_boxes.append((bx1, by1, bx2, by2, year))
            selected = (year == self.selected_year)
            hov = self._hovered(bx1, by1, bx2, by2)
            if selected:
                filled_rrect(bx1, by1, bx2, by2, R, AMBER)
                arcade.draw_text(str(year), (bx1 + bx2) // 2, cy + 1, INK,
                                 F_LABEL, bold=True,
                                 anchor_x="center", anchor_y="center", font_name=MONO)
            else:
                filled_rrect(bx1, by1, bx2, by2, R, CARD_HI if hov else CARD)
                outline_rrect(bx1, by1, bx2, by2, R,
                              HAIRLINE_HI if hov else HAIRLINE)
                arcade.draw_text(str(year), (bx1 + bx2) // 2, cy + 1,
                                 TEXT if hov else TEXT_DIM, F_LABEL,
                                 anchor_x="center", anchor_y="center", font_name=MONO)
            cx += bw + 6

        # Search box, right side
        sb_w = min(280, x2 - cx - 20)
        sb_x1, sb_x2 = x2 - sb_w, x2
        sb_y1, sb_y2 = cy - 15, cy + 15
        filled_rrect(sb_x1, sb_y1, sb_x2, sb_y2, R, CARD)
        outline_rrect(sb_x1, sb_y1, sb_x2, sb_y2, R,
                      AMBER if self.search_text else HAIRLINE)
        q = self.search_text if self.search_text else "SEARCH…"
        arcade.draw_text(q, sb_x1 + 10, cy,
                         TEXT if self.search_text else TEXT_FAINT,
                         F_LABEL, anchor_x="left", anchor_y="center",
                         font_name=MONO)

    def _draw_race_list(self, x1, y1, x2, y2):
        panel(x1, y1, x2, y2)
        px = x1 + PAD
        events = season(self.selected_year)
        py = section(px, y2 - PAD + 2, x2 - PAD, "ROUNDS",
                     right=f"{len(events)} RACES" if events else "")

        err = season_error(self.selected_year)
        if err:
            arcade.draw_text(err, (x1 + x2) // 2, (y1 + py) // 2,
                             TEXT_FAINT, F_MICRO,
                             anchor_x="center", anchor_y="center", font_name=MONO)
            return

        visible = self._visible_events()
        if not visible:
            arcade.draw_text("NO MATCH", (x1 + x2) // 2, (y1 + py) // 2,
                             TEXT_FAINT, F_MICRO,
                             anchor_x="center", anchor_y="center")
            return

        current   = self._selected_event()
        row_guard = y1 + 8
        avail = py - row_guard
        row_h = max(22, min(32, avail // len(visible) - 1))

        for ev in visible:
            if py - row_h < row_guard:
                break
            rx1, rx2 = x1 + 4, x2 - 4
            ry1, ry2 = py - row_h, py
            self._race_boxes.append((rx1, ry1, rx2, ry2, ev.round))

            selected = (current is not None and ev.round == current.round)
            hov = self._hovered(rx1, ry1, rx2, ry2)
            if selected:
                filled_rrect(rx1, ry1, rx2, ry2, 2, CARD_HI)
                arcade.draw_lrbt_rectangle_filled(rx1, rx1 + 2, ry1 + 2, ry2 - 2, AMBER)
            elif hov:
                filled_rrect(rx1, ry1, rx2, ry2, 2, CARD)

            row_cy = (ry1 + ry2) // 2
            arcade.draw_text(f"{ev.round:02d}", px, row_cy,
                             AMBER if selected else TEXT_FAINT, F_MICRO,
                             anchor_x="left", anchor_y="center", font_name=MONO)
            _draw_flag(ev.circuit_key, ev.country, px + 38, row_cy)
            arcade.draw_text(ev.short.upper(), px + 58, row_cy,
                             TEXT if (selected or hov) else TEXT_DIM, F_LABEL,
                             anchor_x="left", anchor_y="center")
            if selected:
                arcade.draw_text("▸", rx2 - 10, row_cy, AMBER, F_LABEL,
                                 anchor_x="right", anchor_y="center")
            py -= row_h + 1

    def _draw_hero(self, x1, y1, x2, y2):
        panel(x1, y1, x2, y2)
        px = x1 + PAD + 6
        pw = x2 - x1 - (PAD + 6) * 2
        py = y2 - PAD - 4

        event = self._selected_event()
        if event is None:
            arcade.draw_text("NO SEASON DATA", (x1 + x2) // 2, (y1 + y2) // 2,
                             TEXT_FAINT, F_H2,
                             anchor_x="center", anchor_y="center", font_name=MONO)
            self._start_box = None
            return
        meta = _RACE_META.get(event.circuit_key)

        # Header: round tag + year
        tag(px + 36, py - 8, f"ROUND {event.round:02d}", INK, bg=AMBER)
        arcade.draw_text(str(self.selected_year), x2 - PAD - 6, py - 14,
                         TEXT_FAINT, F_TITLE,
                         anchor_x="right", anchor_y="center", font_name=MONO)
        py -= 34

        # Title block
        arcade.draw_text(event.short.upper(), px, py, TEXT,
                         F_GIANT, bold=True, anchor_x="left", anchor_y="top")
        py -= F_GIANT + 14
        arcade.draw_text(spaced("GRAND PRIX"), px, py, AMBER, F_H2,
                         anchor_x="left", anchor_y="top")
        py -= 24

        circ = meta["circuit"] if meta else event.location
        loc  = meta["loc"]     if meta else event.country
        arcade.draw_text(f"{circ}  ·  {loc}".upper(), px, py, TEXT_FAINT, F_MICRO,
                         anchor_x="left", anchor_y="top", font_name=MONO)
        py -= 24

        # Circuit outline — the hero graphic
        btn_h    = 48
        traits_h = 56
        desc_h   = 56
        stats_h  = 46
        map_y1   = y1 + PAD + btn_h + 12 + traits_h + desc_h + stats_h
        map_y2   = py - 4
        if map_y2 - map_y1 > 60:
            found = draw_circuit(event.circuit_key,
                                 px + 20, map_y1 + 8, px + pw - 20, map_y2 - 8,
                                 color=AMBER_DARK, thickness=3)
            if not found:
                arcade.draw_text("CIRCUIT DATA UNAVAILABLE",
                                 px + pw // 2, (map_y1 + map_y2) // 2,
                                 TEXT_FAINT, F_MICRO,
                                 anchor_x="center", anchor_y="center")
        py = map_y1 - 2

        # Stats row — DATE is the real one for this season; the rest are
        # circuit constants that only exist for venues with editorial data.
        divider(px, py, px + pw)
        py -= 14
        stats = [("DATE",       event.date or "–"),
                 ("LAPS",       str(meta["laps"]) if meta else "–"),
                 ("DISTANCE",   meta["dist"]      if meta else "–"),
                 ("LAP RECORD", meta["record"]    if meta else "–")]
        col_w = pw // 4
        for i, (lbl, val) in enumerate(stats):
            cx = px + i * col_w
            arcade.draw_text(lbl, cx, py, TEXT_FAINT, F_MICRO,
                             anchor_x="left", anchor_y="top", font_name=MONO)
            arcade.draw_text(val, cx, py - 14, TEXT, F_MICRO,
                             anchor_x="left", anchor_y="top", font_name=MONO)
        py -= stats_h - 6

        if meta:
            # Description
            divider(px, py, px + pw)
            py -= 14
            words, line, lines = meta["desc"].split(), "", []
            for wd in words:
                if len(line) + len(wd) + 1 > 74:
                    lines.append(line); line = wd
                else:
                    line = (line + " " + wd).strip()
            if line:
                lines.append(line)
            for ln in lines[:3]:
                arcade.draw_text(ln, px, py, TEXT_DIM, F_LABEL,
                                 anchor_x="left", anchor_y="top")
                py -= 14
            py -= 10

            # Trait meters
            traits = [("DIFFICULTY", meta["diff"]), ("OVERTAKING", meta["ot"]),
                      ("TYRE WEAR",  meta["tyre"]), ("FUEL USE", meta["fuel"])]
            for i, (lbl, lv) in enumerate(traits):
                cx = px + i * (pw // 4)
                arcade.draw_text(lbl, cx, py, TEXT_FAINT, F_MICRO,
                                 anchor_x="left", anchor_y="top", font_name=MONO)
                meter(cx, py - 24, _LEVEL.get(lv, 1))
                arcade.draw_text(lv.upper(), cx + 64, py - 24, TEXT_DIM, F_MICRO,
                                 anchor_x="left", anchor_y="bottom", font_name=MONO)

        # START button
        btn_y1 = y1 + PAD; btn_y2 = btn_y1 + btn_h
        btn_x1 = px - 2;   btn_x2 = px + pw + 2
        hov = self._hovered(btn_x1, btn_y1, btn_x2, btn_y2)
        filled_rrect(btn_x1, btn_y1, btn_x2, btn_y2, R,
                     (255, 192, 70) if hov else AMBER)
        self._start_box = (btn_x1, btn_y1, btn_x2, btn_y2)
        arcade.draw_text("START REPLAY  ▸",
                         (btn_x1 + btn_x2) // 2, (btn_y1 + btn_y2) // 2 + 1,
                         INK, F_H2, bold=True,
                         anchor_x="center", anchor_y="center", font_name=MONO)

    # ── interaction ───────────────────────────────────────────────────────────

    def on_mouse_motion(self, x, y, dx, dy):
        self._mouse = (x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        for x1, y1, x2, y2, val in self._year_boxes:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._set_year(val)
                return
        for x1, y1, x2, y2, val in self._race_boxes:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.selected_round = val
                return
        if self._start_box:
            x1, y1, x2, y2 = self._start_box
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._launch()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ENTER:
            self._launch()
        elif symbol == arcade.key.BACKSPACE:
            self.search_text = self.search_text[:-1]
        elif symbol == arcade.key.ESCAPE:
            self.search_text = ""
            return True   # consume so pyglet's default ESC-close never fires
        elif 32 <= symbol <= 126:
            ch = chr(symbol)
            if not (modifiers & arcade.key.MOD_SHIFT):
                ch = ch.lower()
            self.search_text += ch

    def on_resize(self, width, height):
        pass  # layout recomputes from window size on every on_draw

    def _launch(self):
        event = self._selected_event()
        if event is None:
            return
        apply_event(event)
        self.window.set_caption(config.SCREEN_TITLE)
        self.window.show_view(LoadingView())


# The loading screen is near-static, and every frame it draws competes with the
# worker thread for the GIL. Throttling it back measurably shortens the load.
_LOAD_DRAW_RATE = 1 / 20
_NORMAL_DRAW_RATE = 1 / 60


class LoadingView(arcade.View):
    """Live progress while ReplayLoader works on a background thread."""

    def __init__(self):
        super().__init__()
        self._loader  = None
        self._elapsed = 0.0

    def on_show_view(self):
        arcade.set_background_color(BG)
        self.window.set_draw_rate(_LOAD_DRAW_RATE)
        from f1replay.core.replay_data import ReplayLoader
        self._loader = ReplayLoader()

    def on_hide_view(self):
        self.window.set_draw_rate(_NORMAL_DRAW_RATE)

    def on_draw(self):
        self.clear()
        w, h = self.window.width, self.window.height
        cx, cy = w // 2, h // 2

        draw_circuit(config.CIRCUIT_KEY,
                     cx - 180, cy - 20, cx + 180, cy + 220,
                     color=HAIRLINE_HI, thickness=2)

        failed = self._loader is not None and self._loader.error
        arcade.draw_text(spaced("LOAD FAILED" if failed else "LOADING TELEMETRY"),
                         cx, cy - 36, RED if failed else AMBER, F_LABEL,
                         anchor_x="center", anchor_y="center")
        arcade.draw_text(f"{config.EVENT_NAME.upper()} · {config.YEAR}",
                         cx, cy - 60, TEXT, F_H1, bold=True,
                         anchor_x="center", anchor_y="center")

        if failed:
            arcade.draw_text(self._loader.error[:96], cx, cy - 88, TEXT_DIM, F_MICRO,
                             anchor_x="center", anchor_y="center", font_name=MONO)
            arcade.draw_text("ESC TO GO BACK", cx, cy - 108, TEXT_FAINT, F_MICRO,
                             anchor_x="center", anchor_y="center", font_name=MONO)
            return

        # Stage bar — proof the window is alive, and where the time is going.
        bar_w = 320
        bx1, bx2 = cx - bar_w // 2, cx + bar_w // 2
        by = cy - 92
        arcade.draw_lrbt_rectangle_filled(bx1, bx2, by - 2, by + 2, CARD_HI)
        prog = self._loader.progress if self._loader else 0.0
        if prog > 0:
            arcade.draw_lrbt_rectangle_filled(bx1, bx1 + int(bar_w * prog),
                                              by - 2, by + 2, AMBER)
        # A scanning tick keeps moving through the long telemetry stage.
        scan = (self._elapsed * 0.6) % 1.0
        sx = bx1 + int(bar_w * scan)
        arcade.draw_lrbt_rectangle_filled(sx - 1, sx + 1, by - 5, by + 5, AMBER_DARK)

        stage = self._loader.stage if self._loader else ""
        arcade.draw_text(stage, bx1, by - 18, TEXT_DIM, F_MICRO,
                         anchor_x="left", anchor_y="center", font_name=MONO)
        arcade.draw_text(f"{self._elapsed:.0f}S", bx2, by - 18, TEXT_FAINT, F_MICRO,
                         anchor_x="right", anchor_y="center", font_name=MONO)
        arcade.draw_text("FIRST RUN MAY TAKE A MINUTE WHILE SESSION DATA IS CACHED",
                         cx, by - 38, TEXT_FAINT, F_MICRO,
                         anchor_x="center", anchor_y="center", font_name=MONO)

    def on_update(self, dt):
        self._elapsed += dt
        if self._loader is None or self._loader.cancelled or not self._loader.done:
            return
        if self._loader.data is not None:
            from f1replay.ui.window import RaceView
            self.window.show_view(RaceView(self._loader.data))

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            if self._loader:
                self._loader.cancelled = True
            self.window.show_view(SelectionView())
            return True   # consume so pyglet's default ESC-close never fires
