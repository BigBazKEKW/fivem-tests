"""
FiveM Lockpick Minigame Auto-Solver
====================================
Automatically detects the dark red stick and the orange target zone
inside a fixed screen region, and presses 'E' (via DirectInput) when
the stick is inside the zone.

REQUIREMENTS
------------
    pip install opencv-python pydirectinput mss numpy keyboard

IMPORTANT
---------
* Run this script **as Administrator** on Windows, otherwise
  `pydirectinput` and `keyboard` may not be able to send/receive
  global key events while the game is in the foreground.
* Press **ESC** at any time to stop the script.
"""

import time
import cv2
import numpy as np
import mss
import pydirectinput
import keyboard

# =========================================================
# ============== ADJUSTABLE CONFIGURATION =================
# =========================================================

# Screen capture region — 200x200 box centered on (2468, 703)
MONITOR = {"top": 603, "left": 2368, "width": 200, "height": 200}

# HSV color ranges
# Dark red stick (radar hand)
RED_LOWER = np.array([0, 100, 50])
RED_UPPER = np.array([10, 255, 150])

# Orange target zone
ORANGE_LOWER = np.array([10, 100, 100])
ORANGE_UPPER = np.array([25, 255, 255])

# Debounce — minimum seconds between two 'E' presses
DEBOUNCE_SECONDS = 1.0

# Polling pause (seconds). ~2-5 ms => 200-500 Hz
POLL_INTERVAL = 0.003

# Minimum number of pixels required to consider a detection valid
MIN_RED_PIXELS = 15
MIN_ORANGE_PIXELS = 30

# Angular tolerance (degrees) added on each side of the orange zone
ANGLE_TOLERANCE = 2.0

# Key to press when stick is inside the orange zone
ACTION_KEY = "e"

# Disable pydirectinput safety pause for max speed
pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False

# =========================================================
# ==================== HELPERS ============================
# =========================================================

def pixel_angle(x, y, cx, cy):
    """
    Return angle in degrees of point (x, y) relative to center (cx, cy)
    where 0° = top (12 o'clock) and angles increase clockwise.
    Range: [0, 360).
    """
    dx = x - cx
    dy = y - cy
    # atan2(dx, -dy): rotates so that 0° points up, increases clockwise
    ang = np.degrees(np.arctan2(dx, -dy))
    # Normalize to [0, 360)
    if np.isscalar(ang):
        if ang < 0:
            ang += 360.0
        return ang
    ang = np.where(ang < 0, ang + 360.0, ang)
    return ang


def angle_in_zone(angle, zone_start, zone_end):
    """
    Check if `angle` lies inside the arc from zone_start -> zone_end
    going clockwise (increasing angle), with wrap-around at 360°.
    """
    if zone_start <= zone_end:
        return zone_start <= angle <= zone_end
    # Wrap-around case (e.g. start=350, end=20)
    return angle >= zone_start or angle <= zone_end


def compute_zone_bounds(angles):
    """
    Given an array of angles (0-360) belonging to the orange zone pixels,
    determine the angular start/end of the contiguous arc, correctly
    handling wrap-around through 0°.
    """
    if angles.size == 0:
        return None, None

    sorted_a = np.sort(angles)
    # Largest gap between consecutive angles (treated circularly)
    diffs = np.diff(sorted_a)
    wrap_diff = (sorted_a[0] + 360.0) - sorted_a[-1]
    all_diffs = np.append(diffs, wrap_diff)

    gap_idx = np.argmax(all_diffs)

    if gap_idx == len(sorted_a) - 1:
        # Largest gap is the wrap gap → arc does NOT cross 0°
        return float(sorted_a[0]), float(sorted_a[-1])
    else:
        # Arc crosses 0° → start is angle after the gap, end is angle before it
        start = float(sorted_a[gap_idx + 1])
        end = float(sorted_a[gap_idx])
        return start, end


# =========================================================
# ==================== MAIN LOOP ==========================
# =========================================================

def main():
    print("Lockpick auto-solver running. Press ESC to quit.")
    cx = MONITOR["width"] / 2.0
    cy = MONITOR["height"] / 2.0

    last_press_time = 0.0

    with mss.mss() as sct:
        while True:
            if keyboard.is_pressed("esc"):
                print("ESC pressed — exiting.")
                break

            # Capture region
            frame = np.array(sct.grab(MONITOR))  # BGRA
            bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

            # ---- Detect red stick ----
            red_mask = cv2.inRange(hsv, RED_LOWER, RED_UPPER)
            red_ys, red_xs = np.nonzero(red_mask)

            # ---- Detect orange zone ----
            orange_mask = cv2.inRange(hsv, ORANGE_LOWER, ORANGE_UPPER)
            orange_ys, orange_xs = np.nonzero(orange_mask)

            if (red_xs.size < MIN_RED_PIXELS or
                    orange_xs.size < MIN_ORANGE_PIXELS):
                time.sleep(POLL_INTERVAL)
                continue

            # Stick angle from centroid
            stick_x = red_xs.mean()
            stick_y = red_ys.mean()
            stick_angle = pixel_angle(stick_x, stick_y, cx, cy)

            # Orange zone angular range
            orange_angles = pixel_angle(orange_xs.astype(np.float32),
                                        orange_ys.astype(np.float32),
                                        cx, cy)
            zone_start, zone_end = compute_zone_bounds(orange_angles)
            if zone_start is None:
                time.sleep(POLL_INTERVAL)
                continue

            # Apply tolerance
            z_start = (zone_start - ANGLE_TOLERANCE) % 360.0
            z_end = (zone_end + ANGLE_TOLERANCE) % 360.0

            if angle_in_zone(stick_angle, z_start, z_end):
                now = time.time()
                if now - last_press_time >= DEBOUNCE_SECONDS:
                    pydirectinput.press(ACTION_KEY)
                    last_press_time = now
                    print(f"[HIT] stick={stick_angle:6.2f}°  "
                          f"zone=({zone_start:6.2f}° → {zone_end:6.2f}°) — pressed '{ACTION_KEY.upper()}'")

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()


# =========================================================
# ============== HSV CALIBRATION HELP =====================
# =========================================================
#
# If the script doesn't detect the stick or the orange zone,
# the HSV ranges almost certainly need tuning for your monitor /
# in-game brightness. Use this small calibration snippet:
#
# ---------------------------------------------------------
# import cv2, numpy as np, mss
#
# MONITOR = {"top": 603, "left": 2368, "width": 200, "height": 200}
#
# def nothing(x): pass
# cv2.namedWindow("ctrl")
# for n, v in [("Hl",0),("Sl",100),("Vl",100),("Hu",25),("Su",255),("Vu",255)]:
#     cv2.createTrackbar(n, "ctrl", v, 255, nothing)
#
# with mss.mss() as sct:
#     while True:
#         img = cv2.cvtColor(np.array(sct.grab(MONITOR)), cv2.COLOR_BGRA2BGR)
#         hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
#         lo = np.array([cv2.getTrackbarPos(n,"ctrl") for n in ("Hl","Sl","Vl")])
#         hi = np.array([cv2.getTrackbarPos(n,"ctrl") for n in ("Hu","Su","Vu")])
#         mask = cv2.inRange(hsv, lo, hi)
#         cv2.imshow("frame", img); cv2.imshow("mask", mask)
#         if cv2.waitKey(1) & 0xFF == 27: break
# cv2.destroyAllWindows()
# ---------------------------------------------------------
#
# Move the trackbars until ONLY the stick (or ONLY the orange zone)
# shows up white in the mask, then copy those values into RED_LOWER /
# RED_UPPER or ORANGE_LOWER / ORANGE_UPPER at the top of this script.
#
# Note: pure red wraps around the HSV hue circle. If your stick is
# bright red rather than dark red, you may need TWO ranges combined:
#   mask1 = cv2.inRange(hsv, (0,100,50),  (10,255,255))
#   mask2 = cv2.inRange(hsv, (170,100,50),(180,255,255))
#   red_mask = cv2.bitwise_or(mask1, mask2)
