'''
import sys
import time
import keyboard

sys.stdout.reconfigure(encoding='utf-8')

def on_e_pressed(e):
    try:
        time.sleep(1)
        # 79 = scan code of Numpad 1 (0x4F)
        keyboard.press_and_release(79)
        print("[E -> 1] Po 1 s issiustas '1'")
    except Exception as err:
        print(f"Klaida mygtuko paspaudime: {err}")

keyboard.on_press_key('e', on_e_pressed)

print("Laukiama E paspaudimo... (paspausk ESC, kad išeitum)")
keyboard.wait('esc')
'''

import time, keyboard
time.sleep(3)
keyboard.press_and_release(79)   # top-row '1'