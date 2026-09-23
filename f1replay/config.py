"""Replay settings.

Panel geometry, fonts and colours are NOT here — layout is computed from the
window size in ui/window.py and ui/selection.py, and the visual language lives
in ui/design.py. This file holds only what the data layer and playback need.
"""
import os
import sys
from pathlib import Path


def default_cache_dir() -> Path:
    """Where FastF1 session data is cached.

    A relative "cache" directory only works when the app is run from its own
    source tree; installed as a command it would scatter multi-gigabyte caches
    wherever the shell happened to be. $F1REPLAY_CACHE wins, then the platform's
    user cache location.
    """
    env = os.environ.get("F1REPLAY_CACHE")
    if env:
        return Path(env).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "f1replay"
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "f1replay" / "Cache"
    return Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "f1replay"


# Overridden by `f1replay --cache PATH`.
CACHE_DIR = str(default_cache_dir())

SCREEN_TITLE = "F1 Race Replay"

# Which session to replay; set by the session-select screen (or the CLI)
# before RaceView is built. ROUND is what actually gets loaded — FastF1
# fuzzy-matches event *names*, so loading by round number is the only exact
# way to ask for a race. EVENT_NAME and CIRCUIT_KEY are display/asset lookups.
YEAR = 2025
ROUND = 11
EVENT_NAME = "Austrian Grand Prix"
CIRCUIT_KEY = "Austria"
SESSION = "R"

# Track geometry
DOWNSAMPLE_STEP = 2     # centerline thinning
LINE_OFFSET_PX = 6      # half-width of the drawn asphalt ribbon

# Cars
CAR_RADIUS = 9
HOVER_PICK_RADIUS = 18

# Playback speed: fixed ladder of standard steps (video-player style)
SPEED_STEPS = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
INITIAL_TIME_SPEED = 2.0
SKIP_SECONDS = 10.0
