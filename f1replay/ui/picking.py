import numpy as np

from f1replay.config import HOVER_PICK_RADIUS, CAR_RADIUS


def pick_driver_on_track(drivers, driver_data, current_time, transform, mx, my):
    best_code = None
    best_d2 = None
    r = max(HOVER_PICK_RADIUS, CAR_RADIUS + 4)
    r2 = r * r

    for code in drivers:
        data = driver_data.get(code)
        if not data:
            continue
        t_arr = data["t"]
        if current_time < t_arr[0] or current_time > t_arr[-1]:
            continue

        wx = float(np.interp(current_time, t_arr, data["x"]))
        wy = float(np.interp(current_time, t_arr, data["y"]))
        sx, sy = transform.to_screen(wx, wy)

        dx = mx - sx
        dy = my - sy
        d2 = dx * dx + dy * dy
        if d2 <= r2 and (best_d2 is None or d2 < best_d2):
            best_d2 = d2
            best_code = code
    return best_code


def pick_driver_on_leaderboard(hitboxes, mx, my):
    for (x1, y1, x2, y2, code) in hitboxes:
        if x1 <= mx <= x2 and y1 <= my <= y2:
            return code
    return None


def pick_driver_anywhere(drivers, driver_data, current_time, transform, hitboxes, mx, my):
    code = pick_driver_on_leaderboard(hitboxes, mx, my)
    if code is not None:
        return code
    return pick_driver_on_track(drivers, driver_data, current_time, transform, mx, my)