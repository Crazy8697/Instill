# main.py — Instill gauge screen with live OBD data

from st7796s import ST7796S, BLACK, YELLOW, GRAY, WHITE, WIDTH, HEIGHT
from obd import OBD
import time

# ------------------------------------------------------------------ layout

GAUGES = [
    ('rpm',      'RPM',      '',      0,   24, 160, 146),
    ('coolant',  'COOLANT',  'C',   161,   24, 159, 146),
    ('battery',  'BATTERY',  'V',   321,   24, 159, 146),
    ('throttle', 'THROTTLE', '%',     0,  171, 240, 149),
    ('maf',      'MAF',    'g/s',   241,  171, 239, 149),
]

PLACEHOLDERS = {
    'rpm':      '----',
    'coolant':  '--',
    'battery':  '--.-',
    'throttle': '--',
    'maf':      '--.-',
}

# ------------------------------------------------------------------ helpers

def text_center(tft, s, cx, y, color, bg, scale):
    x = cx - (len(s) * 8 * scale) // 2
    tft.text(s, x, y, color=color, bg=bg, scale=scale)


def draw_gauge(tft, gauge_id, value_str):
    for gid, label, unit, gx, gy, gw, gh in GAUGES:
        if gid != gauge_id:
            continue
        cx = gx + gw // 2
        tft.fill_rect(gx + 1, gy + 28, gw - 2, 48, BLACK)
        text_center(tft, value_str, cx, gy + 30, YELLOW, BLACK, 3)
        if unit:
            text_center(tft, unit, cx, gy + 58, GRAY, BLACK, 1)
        break


def draw_status(tft, connected):
    label = 'BT' if connected else '--'
    color = YELLOW if connected else GRAY
    tft.fill_rect(WIDTH - 20, 4, 20, 14, BLACK)
    tft.text(label, WIDTH - 18, 4, color=color, bg=BLACK, scale=1)


def draw_layout(tft):
    tft.fill(BLACK)

    text_center(tft, 'INSTILL', WIDTH // 2, 4, YELLOW, BLACK, 2)
    tft.hline(0, 22, WIDTH, YELLOW)
    tft.hline(0, 23, WIDTH, YELLOW)

    tft.hline(0, 169, WIDTH, YELLOW)
    tft.hline(0, 170, WIDTH, YELLOW)

    tft.vline(160, 24, 145, YELLOW)
    tft.vline(320, 24, 145, YELLOW)
    tft.vline(240, 171, 149, YELLOW)

    for gid, label, unit, gx, gy, gw, gh in GAUGES:
        cx = gx + gw // 2
        text_center(tft, label, cx, gy + 8, GRAY, BLACK, 1)
        draw_gauge(tft, gid, PLACEHOLDERS[gid])

    draw_status(tft, False)


# ------------------------------------------------------------------ main

def main():
    tft = ST7796S()
    draw_layout(tft)

    obd = OBD()
    obd.start()

    prev_connected = False

    while True:
        connected = obd.connected

        if connected != prev_connected:
            draw_status(tft, connected)
            if not connected:
                for gid in PLACEHOLDERS:
                    draw_gauge(tft, gid, PLACEHOLDERS[gid])
            prev_connected = connected

        if not connected and obd._state == 'idle':
            time.sleep_ms(3000)
            obd.start()

        for gauge_id, value in obd.get_data().items():
            draw_gauge(tft, gauge_id, value)

        time.sleep_ms(50)


main()
