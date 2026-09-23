import numpy as np

from f1replay.config import LINE_OFFSET_PX


class TrackTransform:
    def __init__(self):
        self._scale = 1.0
        self._off_x = 0.0
        self._off_y = 0.0

    def fit_to_rect(self, x_arr, y_arr, rx1, ry1, rx2, ry2, inner_pad=20):
        """Fit track to an explicit screen rect (px)."""
        if len(x_arr) == 0 or len(y_arr) == 0:
            return                      # keep the identity transform
        pw, ph = rx2 - rx1, ry2 - ry1
        min_x, max_x = float(np.min(x_arr)), float(np.max(x_arr))
        min_y, max_y = float(np.min(y_arr)), float(np.max(y_arr))
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        usable_w = max(1, pw - 2 * inner_pad)
        usable_h = max(1, ph - 2 * inner_pad)
        self._scale = min(usable_w / span_x, usable_h / span_y)
        track_w = span_x * self._scale
        track_h = span_y * self._scale
        cx = rx1 + inner_pad + (usable_w - track_w) / 2
        cy = ry1 + inner_pad + (usable_h - track_h) / 2
        self._off_x = cx - min_x * self._scale
        self._off_y = cy - min_y * self._scale

    def to_screen(self, x, y):
        sx = x * self._scale + self._off_x
        sy = y * self._scale + self._off_y
        return sx, sy

    @staticmethod
    def build_screen_edges(center_pts):
        xs = np.array([p[0] for p in center_pts], dtype=float)
        ys = np.array([p[1] for p in center_pts], dtype=float)

        dx = np.gradient(xs)
        dy = np.gradient(ys)
        length = np.sqrt(dx**2 + dy**2)
        length[length == 0] = 1.0

        nx = -dy / length
        ny = dx / length

        outer_pts = []
        inner_pts = []
        for x, y, nx_i, ny_i in zip(xs, ys, nx, ny):
            outer_pts.append((x + nx_i * LINE_OFFSET_PX, y + ny_i * LINE_OFFSET_PX))
            inner_pts.append((x - nx_i * LINE_OFFSET_PX, y - ny_i * LINE_OFFSET_PX))
        return outer_pts, inner_pts