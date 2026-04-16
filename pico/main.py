# main.py — Instill boot screen
# Runs on power-up. Displays boot screen then hands off to app.

from st7796s import ST7796S, BLACK, YELLOW, GRAY, WIDTH, HEIGHT
import time

def boot_screen(tft):
    tft.fill(BLACK)

    # "INSTILL" — 7 chars * 8px * 5 scale = 280px wide, 40px tall
    label     = "INSTILL"
    scale_big = 5
    cw        = 8 * scale_big
    ch        = 8 * scale_big
    lw        = len(label) * cw
    lx        = (WIDTH - lw) // 2      # 20
    ly        = (HEIGHT // 2) - ch     # 200

    tft.text(label, lx, ly, color=YELLOW, bg=BLACK, scale=scale_big)

    # Separator lines
    sep_y = ly + ch + 10
    tft.hline(20,         sep_y,     WIDTH - 40, YELLOW)
    tft.hline(20,         sep_y + 2, WIDTH - 40, YELLOW)

    # "GREAT FEAR" — 10 chars * 8px * 2 scale = 160px wide
    sub       = "GREAT FEAR"
    scale_sm  = 2
    sw        = len(sub) * 8 * scale_sm
    sx        = (WIDTH - sw) // 2      # 80
    sy        = sep_y + 16
    tft.text(sub, sx, sy, color=YELLOW, bg=BLACK, scale=scale_sm)

    # Version tag bottom-right
    tft.text("v0.1", WIDTH - 4 * 8 - 8, HEIGHT - 16, color=GRAY, bg=BLACK, scale=1)


def main():
    tft = ST7796S()
    boot_screen(tft)
    # Future: launch OBD app here
    while True:
        time.sleep(1)


main()
