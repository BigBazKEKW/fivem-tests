import sys
import time
import cv2
import numpy as np
import mss
import pydirectinput
import keyboard

# Fix Unicode crash on Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

# =========================================================
# ============== ADJUSTABLE CONFIGURATION =================
# =========================================================

#MONITOR = {"top": 603, "left": 2368, "width": 200, "height": 200}
MONITOR = {"top": 390, "left": 810, "width": 300, "height": 300}

RED_LOWER  = np.array([0,  120,  80])
RED_UPPER  = np.array([8,  255, 255])

# Used to exclude red pixels from the orange mask
RED_EXCLUDE_LOWER = np.array([0,  100, 100])
RED_EXCLUDE_UPPER = np.array([8,  255, 255])

ORANGE_LOWER = np.array([10, 120, 120])
ORANGE_UPPER = np.array([28, 255, 255])

DEBOUNCE_SECONDS  = 1.0
POLL_INTERVAL     = 0.003
MIN_RED_PIXELS    = 20
MIN_ORANGE_PIXELS = 80
MIN_ORANGE_SPREAD = 10.0   # zone must span at least this many degrees
MAX_ORANGE_SPREAD = 90.0   # zone must not span more than this (filters false positives)
ANGLE_TOLERANCE   = 0.0
ACTION_KEY        = "e"

pydirectinput.PAUSE    = 0
pydirectinput.FAILSAFE = False

# =========================================================
# ==================== HELPERS ============================
# =========================================================

def pixel_angle(x, y, cx, cy):
    """0 deg = top, increasing clockwise, range [0, 360)."""
    dx = x - cx
    dy = y - cy
    ang = np.degrees(np.arctan2(dx, -dy))
    if np.isscalar(ang):
        return ang + 360.0 if ang < 0 else ang
    return np.where(ang < 0, ang + 360.0, ang)


def angle_in_zone(angle, zone_start, zone_end):
    if zone_start <= zone_end:
        return zone_start <= angle <= zone_end
    return angle >= zone_start or angle <= zone_end


def compute_zone_bounds(angles):
    if angles.size == 0:
        return None, None
    sorted_a = np.sort(angles)
    diffs     = np.diff(sorted_a)
    wrap_diff = (sorted_a[0] + 360.0) - sorted_a[-1]
    all_diffs = np.append(diffs, wrap_diff)
    gap_idx   = np.argmax(all_diffs)
    if gap_idx == len(sorted_a) - 1:
        return float(sorted_a[0]), float(sorted_a[-1])
    return float(sorted_a[gap_idx + 1]), float(sorted_a[gap_idx])

# =========================================================
# ==================== MAIN LOOP ==========================
# =========================================================

def main():
    print("Lockpick auto-solver running. Press ESC to quit.")
    cx = MONITOR["width"]  / 2.0
    cy = MONITOR["height"] / 2.0
    last_press_time = 0.0

    with mss.MSS() as sct:
        while True:
            if keyboard.is_pressed("esc"):
                print("ESC pressed - exiting.")
                break

            frame = np.array(sct.grab(MONITOR))
            bgr   = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            hsv   = cv2.cvtColor(bgr,   cv2.COLOR_BGR2HSV)

            # --- Red stick ---
            red_mask       = cv2.inRange(hsv, RED_LOWER, RED_UPPER)
            red_ys, red_xs = np.nonzero(red_mask)

            # --- Orange zone (exclude red pixels so needle doesn't bleed in) ---
            orange_mask  = cv2.inRange(hsv, ORANGE_LOWER, ORANGE_UPPER)
            red_exclude  = cv2.inRange(hsv, RED_EXCLUDE_LOWER, RED_EXCLUDE_UPPER)
            orange_mask  = cv2.bitwise_and(orange_mask, cv2.bitwise_not(red_exclude))
            orange_ys, orange_xs = np.nonzero(orange_mask)

            # Skip frame if not enough pixels detected
            if red_xs.size < MIN_RED_PIXELS or orange_xs.size < MIN_ORANGE_PIXELS:
                time.sleep(POLL_INTERVAL)
                continue

            stick_angle   = pixel_angle(red_xs.mean(), red_ys.mean(), cx, cy)
            orange_angles = pixel_angle(
                orange_xs.astype(np.float32),
                orange_ys.astype(np.float32),
                cx, cy
            )

            zone_start, zone_end = compute_zone_bounds(orange_angles)
            if zone_start is None:
                time.sleep(POLL_INTERVAL)
                continue

            # --- False-positive guard: reject implausible arc sizes ---
            arc_span = (zone_end - zone_start) % 360.0
            if arc_span < MIN_ORANGE_SPREAD or arc_span > MAX_ORANGE_SPREAD:
                time.sleep(POLL_INTERVAL)
                continue

            # --- Check if stick is inside the zone ---
            z_start = (zone_start - ANGLE_TOLERANCE) % 360.0
            z_end   = (zone_end   + ANGLE_TOLERANCE) % 360.0

            if angle_in_zone(stick_angle, z_start, z_end):
                now = time.time()
                if now - last_press_time >= DEBOUNCE_SECONDS:
                    pydirectinput.press(ACTION_KEY)
                    last_press_time = now
                    print("[HIT] stick={:6.2f} deg  zone=({:6.2f} -> {:6.2f}) - pressed '{}'".format(
                        stick_angle, zone_start, zone_end, ACTION_KEY.upper()
                    ))

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()