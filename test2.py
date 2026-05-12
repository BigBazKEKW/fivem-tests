"""
Paprastas įrankis:
Kai nuspaudžiamas E (fiziškai ar iš kito skripto),
po 1 sekundės automatiškai paspaudžiamas 1 (virš Q, ą).
Veikia visada, kol paspausite ESC.
"""

import sys
import time
import keyboard

# Kad lietuviškos raidės nekeltų klaidos – ASCII tik jei reikia, arba pakeisti koduotę
sys.stdout.reconfigure(encoding='utf-8')

def on_e_pressed(e):
    try:
        time.sleep(1)
        keyboard.press_and_release('1')   # galima keisti į pydirectinput.press('1')
        print("[E -> 1] Po 1 s issiustas '1'")
    except Exception as err:
        print(f"Klaida mygtuko paspaudime: {err}")

keyboard.on_press_key('e', on_e_pressed)

print("Laukiama E paspaudimo... (paspausk ESC, kad išeitum)")
keyboard.wait('esc')