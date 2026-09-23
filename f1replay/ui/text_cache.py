"""
Replaces arcade.draw_text with a cached arcade.Text-based renderer.

arcade.draw_text re-creates an OpenGL texture on every call, which triggers
a PerformanceWarning and is very slow at 60 fps.  arcade.Text pre-compiles
the text into a pyglet Label and just calls .draw() each frame.

We cache Text objects keyed on (content, font_size, color, anchor_x, anchor_y).
Position (x, y) is updated cheaply on the cached object before drawing.

The pool is global and holds GL resources bound to whichever context was
current when each Text was built, so it assumes one window per process --
which is what app.run() creates. Drawing cached text into a second window
raises GLException; clear _pool if multi-window support is ever added.
"""
import arcade

_pool: dict = {}


def _cached_draw_text(
    text,
    x, y,
    color=(255, 255, 255, 255),
    font_size: float = 12,
    width: int = 0,
    align: str = "left",
    font_name=("calibri", "arial"),
    bold: bool = False,
    italic: bool = False,
    anchor_x: str = "left",
    anchor_y: str = "baseline",
    rotation: float = 0,
    **kwargs,
):
    s = str(text)
    c = tuple(color) if not isinstance(color, tuple) else color
    f = tuple(font_name) if isinstance(font_name, (list, tuple)) else (font_name,)

    key = (s, font_size, c, anchor_x, anchor_y, f, bold)
    obj = _pool.get(key)
    if obj is None:
        # Ever-changing strings (clocks, speeds) would grow the pool without
        # bound over a long replay; reset it once it gets large.
        if len(_pool) > 2048:
            _pool.clear()
        obj = arcade.Text(
            s, x, y, color, font_size,
            font_name=f, bold=bold,
            anchor_x=anchor_x, anchor_y=anchor_y,
        )
        _pool[key] = obj
    else:
        obj.x = x
        obj.y = y
    obj.draw()


def install():
    """Call once before arcade.run() to replace arcade.draw_text globally."""
    arcade.draw_text = _cached_draw_text
