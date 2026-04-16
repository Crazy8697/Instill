# main.py — Instill gauge screen
# Static layout with OBD placeholder values. Values populated in Phase 1 OBD loop.

from st7796s import ST7796S, BLACK, YELLOW, GRAY, WHITE, WIDTH, HEIGHT
import time

# ------------------------------------------------------------------ layout

# Gauge definitions: (id, label, unit, x, y, w, h)
GAUGES = [
    ('rpm',      'RPM',      '',      0,   24, 160, 146),
    ('coolant',  'COOLANT',  'C',   161,   24, 159, 146),
    ('battery',  'BATTERY',  'V',   321,   24, 159, 146),
    ('throttle', 'THROTTLE', '%',     0,  171, 240, 149),
    ('maf',      'MAF',    'g/s',   241,  171, 239, 149),
]

# Placeholder values shown before OBD connects
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
    """Redraw the value area of a single gauge."""
    for gid, label, unit, gx, gy, gw, gh in GAUGES:
        if gid != gauge_id:
            continue
        cx = gx + gw // 2

        # Clear value + unit area
        tft.fill_rect(gx + 1, gy + 28, gw - 2, 48, BLACK)

        # Value (scale 3 = 24px tall)
        text_center(tft, value_str, cx, gy + 30, YELLOW, BLACK, 3)

        # Unit
        if unit:
            text_center(tft, unit, cx, gy + 58, GRAY, BLACK, 1)
        break


def draw_layout(tft):
    """Draw the full gauge frame. Call once on startup."""
    tft.fill(BLACK)

    # --- header bar ---
    text_center(tft, 'INSTILL', WIDTH // 2, 4, YELLOW, BLACK, 2)
    tft.hline(0, 22, WIDTH, YELLOW)
    tft.hline(0, 23, WIDTH, YELLOW)

    # --- row divider ---
    tft.hline(0, 169, WIDTH, YELLOW)
    tft.hline(0, 170, WIDTH, YELLOW)

    # --- column dividers row 1 ---
    tft.vline(160, 24, 145, YELLOW)
    tft.vline(320, 24, 145, YELLOW)

    # --- column divider row 2 ---
    tft.vline(240, 171, 149, YELLOW)

    # --- gauge labels ---
    for gid, label, unit, gx, gy, gw, gh in GAUGES:
        cx = gx + gw // 2
        text_center(tft, label, cx, gy + 8, GRAY, BLACK, 1)
        draw_gauge(tft, gid, PLACEHOLDERS[gid])


# ------------------------------------------------------------------ main

def main():
    tft = ST7796S()
    draw_layout(tft)
    # OBD loop goes here in Phase 1
    while True:
        time.sleep(1)


main()
