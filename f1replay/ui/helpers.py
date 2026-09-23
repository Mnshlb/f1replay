"""Small formatting helpers shared by the views."""
import math


def is_num(v) -> bool:
    """True if v is a real, finite number.

    FastF1 leaves NaN in plenty of per-lap fields (TyreLife is NaN on ~14% of
    laps at Monaco 2022), and `v is not None` happily lets NaN through to
    int(), which raises.
    """
    if v is None:
        return False
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def fmt_laptime(seconds: float) -> str:
    """1:07.924 — timing-screen lap time."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}"


def fmt_hms(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"