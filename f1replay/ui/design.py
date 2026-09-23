"""F1 Race Replay — design system.

A pit-wall engineering console: graphite carbon surfaces, hairline borders,
monospaced data, a single amber signature accent. Purple is reserved for
fastest-lap, green/red for semantics only.
"""
import arcade

from f1replay.ui.circuits import CIRCUITS

# ── Palette ───────────────────────────────────────────────────────────────────
BG          = ( 12,  13,  16)   # graphite black
PANEL       = ( 17,  19,  23)   # raised surface
CARD        = ( 24,  27,  32)   # interactive surface
CARD_HI     = ( 33,  37,  44)   # hovered / selected surface
HAIRLINE    = ( 41,  45,  52)   # default border
HAIRLINE_HI = ( 66,  72,  82)   # emphasized border

AMBER       = (255, 171,  26)   # signature accent
AMBER_DARK  = (124,  88,  28)
PURPLE      = (192, 108, 255)   # fastest lap
GREEN       = ( 62, 201, 120)
RED         = (236,  74,  74)
CYAN        = ( 94, 196, 255)
YELLOW      = (255, 214,  70)
BLUE        = ( 92, 138, 255)

TEXT        = (233, 234, 237)
TEXT_DIM    = (148, 153, 163)
TEXT_FAINT  = ( 92,  97, 108)
INK         = ( 14,  15,  18)   # dark text on amber surfaces
WHITE       = (255, 255, 255)

TRACK_ASPHALT = ( 34,  37,  43)
TRACK_EDGE    = ( 98, 104, 116)

# ── Typography ────────────────────────────────────────────────────────────────
MONO = ("Menlo", "Consolas", "DejaVu Sans Mono", "Courier New")

F_GIANT = 38
F_TITLE = 26
F_H1    = 19
F_H2    = 14
F_BODY  = 12
F_LABEL = 10
F_MICRO =  8

PAD = 14
GAP = 8
R   = 3     # corner radius — sharp, technical


def spaced(s: str) -> str:
    """Letterspaced section header: 'TIMING' → 'T I M I N G'."""
    return " ".join(s.upper())


# ── Tyre compound helpers ─────────────────────────────────────────────────────

def compound_color(compound) -> tuple:
    c = str(compound or "").upper()
    if "SOFT"   in c: return (255,  82,  82)
    if "MEDIUM" in c: return (255, 214,  70)
    if "HARD"   in c: return (225, 228, 234)
    if "INTER"  in c: return ( 62, 201, 120)
    if "WET"    in c: return ( 92, 138, 255)
    return TEXT_FAINT


def compound_letter(compound) -> str:
    c = str(compound or "").upper()
    if "SOFT"   in c: return "S"
    if "MEDIUM" in c: return "M"
    if "HARD"   in c: return "H"
    if "INTER"  in c: return "I"
    if "WET"    in c: return "W"
    return "·"


def speed_color(speed_kmh, max_speed=340):
    frac = max(0.0, min(1.0, speed_kmh / max_speed))
    if frac < 0.40:
        return GREEN
    if frac < 0.72:
        return AMBER
    return RED


# ── Primitive shapes ──────────────────────────────────────────────────────────

def filled_rrect(x1, y1, x2, y2, r, color):
    r = max(0, min(int(r), int((x2 - x1) // 2), int((y2 - y1) // 2)))
    if r == 0:
        arcade.draw_lrbt_rectangle_filled(x1, x2, y1, y2, color)
        return
    arcade.draw_lrbt_rectangle_filled(x1 + r, x2 - r, y1, y2, color)
    arcade.draw_lrbt_rectangle_filled(x1, x2, y1 + r, y2 - r, color)
    arcade.draw_circle_filled(x1 + r, y1 + r, r, color)
    arcade.draw_circle_filled(x2 - r, y1 + r, r, color)
    arcade.draw_circle_filled(x1 + r, y2 - r, r, color)
    arcade.draw_circle_filled(x2 - r, y2 - r, r, color)


def outline_rrect(x1, y1, x2, y2, r, color, t=1):
    r = max(0, min(int(r), int((x2 - x1) // 2), int((y2 - y1) // 2)))
    if r == 0:
        arcade.draw_lrbt_rectangle_outline(x1, x2, y1, y2, color, t)
        return
    arcade.draw_line(x1 + r, y1, x2 - r, y1, color, t)
    arcade.draw_line(x1 + r, y2, x2 - r, y2, color, t)
    arcade.draw_line(x1, y1 + r, x1, y2 - r, color, t)
    arcade.draw_line(x2, y1 + r, x2, y2 - r, color, t)
    arcade.draw_arc_outline(x1 + r, y1 + r, r * 2, r * 2, color, 180, 270, t)
    arcade.draw_arc_outline(x2 - r, y1 + r, r * 2, r * 2, color, 270, 360, t)
    arcade.draw_arc_outline(x1 + r, y2 - r, r * 2, r * 2, color,  90, 180, t)
    arcade.draw_arc_outline(x2 - r, y2 - r, r * 2, r * 2, color,   0,  90, t)


def divider(x1, y, x2, color=None):
    arcade.draw_line(x1, y, x2, y, color if color is not None else HAIRLINE, 1)


# ── Components ────────────────────────────────────────────────────────────────

def panel(x1, y1, x2, y2, accent=None):
    """Flat carbon panel with hairline border and optional left accent bar."""
    filled_rrect(x1, y1, x2, y2, R, PANEL)
    outline_rrect(x1, y1, x2, y2, R, HAIRLINE)
    if accent is not None:
        arcade.draw_lrbt_rectangle_filled(x1 + 1, x1 + 3, y1 + 4, y2 - 4, accent)


def section(x1, y, x2, title, right=None, right_color=None):
    """Letterspaced section header + hairline. Returns the y below it."""
    arcade.draw_text(spaced(title), x1, y, TEXT_FAINT, F_MICRO,
                     anchor_x="left", anchor_y="top")
    if right:
        arcade.draw_text(right, x2, y, right_color or TEXT_DIM, F_MICRO,
                         anchor_x="right", anchor_y="top")
    y -= 14
    divider(x1, y, x2)
    return y - 9


def tag(cx, cy, text, fg, bg=None, fs=F_MICRO):
    """Small square technical chip."""
    w = max(24, int(len(text) * fs * 0.72 + 12))
    h = fs + 9
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x2, y2 = int(cx + w / 2), int(cy + h / 2)
    if bg is not None:
        filled_rrect(x1, y1, x2, y2, 2, bg)
        arcade.draw_text(text, cx, cy + 1, fg, fs,
                         anchor_x="center", anchor_y="center", font_name=MONO)
    else:
        filled_rrect(x1, y1, x2, y2, 2, CARD)
        outline_rrect(x1, y1, x2, y2, 2, fg, 1)
        arcade.draw_text(text, cx, cy + 1, fg, fs,
                         anchor_x="center", anchor_y="center", font_name=MONO)
    return (x1, y1, x2, y2)


def icon_btn(cx, cy, w, h, glyph, bg=None, fg=None, border=None, fs=F_BODY):
    """Square console button. Returns (x1, y1, x2, y2)."""
    if bg is None: bg = CARD
    if fg is None: fg = TEXT
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x2, y2 = int(cx + w / 2), int(cy + h / 2)
    filled_rrect(x1, y1, x2, y2, R, bg)
    outline_rrect(x1, y1, x2, y2, R, border if border is not None else HAIRLINE_HI)
    arcade.draw_text(glyph, cx, cy + 1, fg, fs,
                     anchor_x="center", anchor_y="center")
    return (x1, y1, x2, y2)


def meter(x, y, level, seg_w=16, seg_h=5, gap=3):
    """3-segment intensity meter: level 1..3 segments lit amber."""
    for i in range(3):
        sx = x + i * (seg_w + gap)
        col = AMBER if i < level else CARD_HI
        arcade.draw_lrbt_rectangle_filled(sx, sx + seg_w, y, y + seg_h, col)


def data_row(x1, y, x2, label, value, lc=None, vc=None, fs=F_LABEL):
    arcade.draw_text(label, x1, y, lc or TEXT_FAINT, fs,
                     anchor_x="left", anchor_y="center")
    arcade.draw_text(value, x2, y, vc or TEXT, fs,
                     anchor_x="right", anchor_y="center", font_name=MONO)


BRAND = "F1 RACE REPLAY"


def draw_brand(x, cy):
    """Wordmark: three amber slashes plus the name. Returns its right edge x.

    Set on one line rather than the old name-over-subtitle stack: the name is
    now the full descriptor, so a second line would just repeat it. The width
    is measured rather than hardcoded because the header lays the divider and
    event block out from this return value.
    """
    for i in range(3):
        sx = x + i * 7
        arcade.draw_line(sx, cy - 9, sx + 7, cy + 9, AMBER, 2)
    bx = x + 28
    arcade.draw_text(BRAND, bx, cy, TEXT, F_H2, bold=True,
                     anchor_x="left", anchor_y="center", font_name=MONO)
    # Menlo advance is ~0.60 em and pyglet sizes are points at 96 dpi, so one
    # character is about font_size x 0.80 px.
    return bx + int(len(BRAND) * F_H2 * 0.80)


def console_footer(w, hint, foot_h=22):
    """Thin shared footer strip."""
    arcade.draw_lrbt_rectangle_filled(0, w, 0, foot_h, PANEL)
    arcade.draw_line(0, foot_h, w, foot_h, HAIRLINE, 1)
    cy = foot_h // 2
    arcade.draw_text("// F1 RACE REPLAY", 12, cy, TEXT_FAINT, F_MICRO,
                     anchor_x="left", anchor_y="center", font_name=MONO)
    arcade.draw_text(hint, w // 2, cy, TEXT_FAINT, F_MICRO,
                     anchor_x="center", anchor_y="center")
    # OSM is credited here because ODbL 4.3 requires a notice wherever a
    # Produced Work from the database is publicly used — the circuit outlines
    # on the select and loading screens are exactly that. Keeping it in the
    # shared footer means no view can accidentally drop the attribution.
    arcade.draw_text("DATA · FASTF1 · © OPENSTREETMAP", w - 12, cy,
                     TEXT_FAINT, F_MICRO,
                     anchor_x="right", anchor_y="center", font_name=MONO)


# ── Race accent dots (used as flag fallback) ─────────────────────────────────
RACE_DOT = {
    "Bahrain":       (200,  20,  50),
    "Saudi Arabia":  (  0, 130,  60),
    "Australia":     (  0,  40, 160),
    "Japan":         (200,  20,  50),
    "China":         (200,  20,  50),
    "Miami":         (  0,  80, 160),
    "Emilia Romagna":(  0, 140,  70),
    "Monaco":        (200,  20,  50),
    "Canada":        (200,  20,  50),
    "Spain":         (200,  20,  50),
    "Austria":       (190,  20,  40),
    "Great Britain": (  0,  40, 160),
    "Hungary":       (200,  20,  50),
    "Belgium":       ( 20,  20,  20),
    "Netherlands":   (200,  80,   0),
    "Italy":         (  0, 140,  70),
    "Azerbaijan":    (  0, 130, 110),
    "Singapore":     (200,  20,  50),
    "United States": (  0,  40, 160),
    "Mexico":        (  0, 140,  70),
    "Brazil":        (  0, 130,  60),
    "Las Vegas":     (  0,  40, 160),
    "Qatar":         (130,   0,  40),
    "Abu Dhabi":     (  0,  70, 140),
}

def draw_circuit(race, x1, y1, x2, y2, color=None, thickness=2):
    """Draw the real circuit outline (GPS-derived, north up) fitted into the
    box with aspect ratio preserved. Amber start/finish tick at the first
    point. Returns True if the circuit is known."""
    pts = CIRCUITS.get(race)
    if not pts:
        return False
    # The data lives in a unit square with true proportions — fit a square
    side = min(x2 - x1, y2 - y1)
    ox = x1 + ((x2 - x1) - side) / 2
    oy = y1 + ((y2 - y1) - side) / 2
    screen_pts = [(ox + px * side, oy + py * side) for px, py in pts]
    arcade.draw_line_strip(screen_pts, color or TEXT_FAINT, thickness)
    sx, sy = screen_pts[0]
    arcade.draw_line(sx - 6, sy, sx + 6, sy, AMBER, 3)
    return True
