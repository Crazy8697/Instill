# main.py — Instill dual-screen gauge display
# Screen 0 (daily):  3 arc gauges (MPH / RPM / LOAD) + bottom text row (BATT / COOLANT / MPG)
# Screen 1 (offroad): 3x3 text grid
# GPIO14 right button: cycle screens

import math
import time
from machine import Pin
from st7796s import ST7796S, BLACK, YELLOW, GRAY, WHITE, RED, WIDTH, HEIGHT
from obd import OBD

# ------------------------------------------------------------------ colors
DARK  = const(0x2104)   # dark gray arc track
DIM   = const(0x4208)   # slightly lighter gray for offroad labels

# ------------------------------------------------------------------ constants
TIRE_FACTOR  = 0.70488  # km/h → corrected MPH (33" on 29.1" stock)
ARC_START    = 210.0    # degrees (math coords), needle at value=0
ARC_SWEEP    = 240.0    # degrees clockwise to value=max
ARC_R        = 80       # arc radius px
ARC_THICK    = 10       # arc visual thickness (drawn as 3 radii)
ARC_STEP     = 2        # degrees per arc segment

GAUGE_CY     = 112      # arc center y within top 75% (240px)
COL_CX       = [80, 240, 400]  # arc center x per column

# ------------------------------------------------------------------ arc drawing

def _arc_dot(tft, cx, cy, r, angle_deg, color):
    a  = math.radians(angle_deg)
    x  = round(cx + r * math.cos(a))
    y  = round(cy - r * math.sin(a))
    tft.fill_rect(x - 1, y - 1, 3, 3, color)

def draw_arc_range(tft, cx, cy, start_deg, end_deg, color):
    """Draw arc segment clockwise from start_deg down to end_deg."""
    a = start_deg
    while a >= end_deg:
        for dr in (-4, 0, 4):
            _arc_dot(tft, cx, cy, ARC_R + dr, a, color)
        a -= ARC_STEP
    for dr in (-4, 0, 4):
        _arc_dot(tft, cx, cy, ARC_R + dr, end_deg, color)

def val_to_angle(value, max_val):
    ratio = max(0.0, min(1.0, value / max_val))
    return ARC_START - ratio * ARC_SWEEP

# ------------------------------------------------------------------ helpers

def text_center(tft, s, cx, y, color, bg, scale):
    x = cx - (len(s) * 8 * scale) // 2
    if x < 0:
        x = 0
    tft.text(s, x, y, color=color, bg=bg, scale=scale)

def fmt_fuel_trim(val):
    if val is None:
        return '--'
    if abs(val) < 3.0:
        return 'OK'
    elif val > 0:
        return 'LEAN+' + str(round(val))
    else:
        return 'RICH' + str(round(val))

def calc_mpg(speed_raw, maf_str):
    try:
        mph = speed_raw * TIRE_FACTOR
        maf = float(maf_str)
        if maf > 0.5 and mph > 2.0:
            return str(round(mph * 7.107 / maf, 1))
    except:
        pass
    return '--.-'

# ------------------------------------------------------------------ screen 0 layout

_GAUGES = [
    # col, id, label, max_val
    (0, 'speed', 'MPH',  110),
    (1, 'rpm',   'RPM',  8000),
    (2, 'load',  'LOAD', 100),
]

_BOTTOM = [
    # col, id, label, unit
    (0, 'battery', 'BATT', 'V'),
    (1, 'coolant', 'COOL', 'C'),
    (2, 'mpg',     'EST',  'MPG'),
]

def draw_screen0_frame(tft):
    tft.fill(BLACK)
    # Vertical dividers full height
    tft.vline(160, 0, HEIGHT, YELLOW)
    tft.vline(320, 0, HEIGHT, YELLOW)
    # Horizontal divider between gauge area and text row
    tft.hline(0, 240, WIDTH, YELLOW)

    for col, gid, label, max_val in _GAUGES:
        cx = COL_CX[col]
        # Full arc track (dark)
        draw_arc_range(tft, cx, GAUGE_CY, ARC_START, ARC_START - ARC_SWEEP, DARK)
        # Label below arc
        text_center(tft, label, cx, GAUGE_CY + ARC_R + 14, GRAY, BLACK, 1)
        # Placeholder value
        text_center(tft, '--', cx, GAUGE_CY - 12, YELLOW, BLACK, 3)

    for col, bid, label, unit in _BOTTOM:
        cx = COL_CX[col]
        text_center(tft, label, cx, 248, GRAY,   BLACK, 1)
        text_center(tft, '--',  cx, 262, YELLOW, BLACK, 2)
        text_center(tft, unit,  cx, 284, GRAY,   BLACK, 1)

def update_gauge(tft, g_state, new_angle):
    col   = g_state['col']
    cx    = COL_CX[col]
    old_a = g_state['disp_a']

    if abs(new_angle - old_a) < 0.5:
        return

    if new_angle < old_a:
        # Needle moved clockwise — fill new segment in yellow
        draw_arc_range(tft, cx, GAUGE_CY, old_a - ARC_STEP, new_angle, YELLOW)
    else:
        # Needle moved counterclockwise — erase segment in dark
        draw_arc_range(tft, cx, GAUGE_CY, new_angle, old_a - ARC_STEP, DARK)

    g_state['disp_a'] = new_angle

def update_gauge_text(tft, col, val_str, prev_str, y=None, scale=3):
    if val_str == prev_str:
        return
    cy_text = (GAUGE_CY - 12) if y is None else y
    cx = COL_CX[col]
    # Erase old
    tft.fill_rect(cx - len(prev_str) * 8 * scale // 2 - 2, cy_text - 2,
                  len(prev_str) * 8 * scale + 4, 8 * scale + 4, BLACK)
    text_center(tft, val_str, cx, cy_text, YELLOW, BLACK, scale)

def update_bottom(tft, col, val_str, prev_str):
    if val_str == prev_str:
        return
    cx = COL_CX[col]
    tft.fill_rect(col * 160 + 1, 262, 158, 20, BLACK)
    text_center(tft, val_str, cx, 262, YELLOW, BLACK, 2)

# ------------------------------------------------------------------ screen 1 layout (offroad)

_OFFROAD = [
    # row, col, id, label, unit
    (0, 0, 'fuel_trim', 'FUEL TRIM', ''),
    (0, 1, 'timing',    'TIMING',   'DEG'),
    (0, 2, 'runtime',   'RUNTIME',  'MIN'),
    (1, 0, 'pitch',     'PITCH',    'DEG'),
    (1, 1, 'roll',      'ROLL',     'DEG'),
    (1, 2, 'iat',       'IAT',      'C'),
    (2, 0, 'battery',   'BATTERY',  'V'),
    (2, 1, 'o2',        'O2',       'V'),
    (2, 2, 'maf',       'MAF',      'g/s'),
]

ROW_H = 106   # 320 / 3

def draw_screen1_frame(tft):
    tft.fill(BLACK)
    tft.vline(160, 0, HEIGHT, YELLOW)
    tft.vline(320, 0, HEIGHT, YELLOW)
    tft.hline(0, ROW_H,     WIDTH, YELLOW)
    tft.hline(0, ROW_H * 2, WIDTH, YELLOW)

    for row, col, oid, label, unit in _OFFROAD:
        cx = COL_CX[col]
        ty = row * ROW_H
        text_center(tft, label, cx, ty + 10, GRAY,   BLACK, 1)
        val = '--' if oid not in ('pitch', 'roll') else '--'
        text_center(tft, val,   cx, ty + 26, YELLOW, BLACK, 2)
        if unit:
            text_center(tft, unit, cx, ty + 50, GRAY, BLACK, 1)

def update_offroad_cell(tft, row, col, val_str, prev_str):
    if val_str == prev_str:
        return
    cx  = COL_CX[col]
    ty  = row * ROW_H
    tft.fill_rect(col * 160 + 1, ty + 26, 158, 20, BLACK)
    text_center(tft, val_str, cx, ty + 26, YELLOW, BLACK, 2)

# ------------------------------------------------------------------ BT status

def draw_bt_status(tft, connected, screen):
    if screen == 0:
        # Top right of col 2 gauge area
        cx = COL_CX[2]
        label = 'BT' if connected else '--'
        color = YELLOW if connected else DARK
        tft.fill_rect(440, 4, 36, 10, BLACK)
        tft.text(label, 442, 4, color=color, bg=BLACK, scale=1)
    else:
        tft.fill_rect(440, 4, 36, 10, BLACK)
        label = 'BT' if connected else '--'
        color = YELLOW if connected else DARK
        tft.text(label, 442, 4, color=color, bg=BLACK, scale=1)

# ------------------------------------------------------------------ main

def main():
    tft = ST7796S()

    # Button: GPIO14, active low
    btn = Pin(14, Pin.IN, Pin.PULL_UP)

    screen       = 0
    draw_screen0_frame(tft)

    obd = OBD()
    obd.start()

    # Arc gauge state
    g_state = [
        {'col': 0, 'max': 110,  'disp_a': ARC_START, 'tgt_a': ARC_START, 'val_str': '--'},
        {'col': 1, 'max': 8000, 'disp_a': ARC_START, 'tgt_a': ARC_START, 'val_str': '--'},
        {'col': 2, 'max': 100,  'disp_a': ARC_START, 'tgt_a': ARC_START, 'val_str': '--'},
    ]

    # Bottom row state
    b_state = {'battery': '--.-', 'coolant': '--', 'mpg': '--.-'}

    # Offroad cell state
    o_state = {oid: '--' for _, _, oid, _, _ in _OFFROAD}

    prev_connected = False
    prev_btn       = True
    btn_ts         = 0
    speed_raw      = 0
    maf_val        = '--.-'
    fuel_trim_raw  = None

    while True:
        # ---- button debounce ----
        b = btn.value()
        if b == 0 and prev_btn == 1:
            now = time.ticks_ms()
            if time.ticks_diff(now, btn_ts) > 250:
                btn_ts  = now
                screen  = 1 - screen
                if screen == 0:
                    draw_screen0_frame(tft)
                    # Restore arc state to full redraw
                    for g in g_state:
                        draw_arc_range(tft, COL_CX[g['col']], GAUGE_CY,
                                       ARC_START, g['disp_a'], YELLOW)
                else:
                    draw_screen1_frame(tft)
                    for row, col, oid, label, unit in _OFFROAD:
                        update_offroad_cell(tft, row, col, o_state[oid], '')
                draw_bt_status(tft, obd.connected, screen)
        prev_btn = b

        # ---- BT status ----
        connected = obd.connected
        if connected != prev_connected:
            draw_bt_status(tft, connected, screen)
            if not connected:
                # Reset everything
                for g in g_state:
                    cx = COL_CX[g['col']]
                    draw_arc_range(tft, cx, GAUGE_CY, ARC_START, g['disp_a'], DARK)
                    draw_arc_range(tft, cx, GAUGE_CY, ARC_START, ARC_START - ARC_SWEEP, DARK)
                    update_gauge_text(tft, g['col'], '--', g['val_str'])
                    g['disp_a'] = ARC_START
                    g['tgt_a']  = ARC_START
                    g['val_str'] = '--'
                for col, bid, label, unit in _BOTTOM:
                    update_bottom(tft, col, '--', b_state.get(bid, '--'))
                b_state = {'battery': '--.-', 'coolant': '--', 'mpg': '--.-'}
            prev_connected = connected

        if not connected and obd._state == 'idle':
            time.sleep_ms(3000)
            obd.start()
            continue

        # ---- consume OBD data ----
        data = obd.get_data()

        for key, val in data.items():
            if key == 'speed_raw':
                speed_raw = val
                mph = round(val * TIRE_FACTOR)
                new_s = str(mph)
                if screen == 0:
                    tgt = val_to_angle(mph, 110)
                    g_state[0]['tgt_a'] = tgt
                    update_gauge_text(tft, 0, new_s, g_state[0]['val_str'])
                    g_state[0]['val_str'] = new_s
                else:
                    update_offroad_cell(tft, 0, 0, new_s, o_state.get('speed', '--'))
                    o_state['speed'] = new_s
                # Recalc MPG
                new_mpg = calc_mpg(val, maf_val)
                if screen == 0:
                    update_bottom(tft, 2, new_mpg, b_state['mpg'])
                    b_state['mpg'] = new_mpg

            elif key == 'rpm':
                if screen == 0:
                    tgt = val_to_angle(int(val), 8000)
                    g_state[1]['tgt_a'] = tgt
                    update_gauge_text(tft, 1, val, g_state[1]['val_str'])
                    g_state[1]['val_str'] = val

            elif key == 'load':
                if screen == 0:
                    tgt = val_to_angle(int(val), 100)
                    g_state[2]['tgt_a'] = tgt
                    update_gauge_text(tft, 2, val+'%', g_state[2]['val_str'])
                    g_state[2]['val_str'] = val+'%'

            elif key == 'coolant':
                if screen == 0:
                    update_bottom(tft, 1, val, b_state['coolant'])
                    b_state['coolant'] = val
                update_offroad_cell(tft, 1, 2, val, o_state['iat'])  # shares IAT slot? No — just update offroad

            elif key == 'battery':
                if screen == 0:
                    update_bottom(tft, 0, val, b_state['battery'])
                    b_state['battery'] = val
                update_offroad_cell(tft, 2, 0, val, o_state['battery'])
                o_state['battery'] = val

            elif key == 'maf':
                maf_val = val
                new_mpg = calc_mpg(speed_raw, val)
                if screen == 0:
                    update_bottom(tft, 2, new_mpg, b_state['mpg'])
                    b_state['mpg'] = new_mpg
                update_offroad_cell(tft, 2, 2, val, o_state['maf'])
                o_state['maf'] = val

            elif key == 'fuel_trim':
                fuel_trim_raw = val
                fmt = fmt_fuel_trim(val)
                update_offroad_cell(tft, 0, 0, fmt, o_state['fuel_trim'])
                o_state['fuel_trim'] = fmt

            elif key == 'timing':
                update_offroad_cell(tft, 0, 1, val, o_state['timing'])
                o_state['timing'] = val

            elif key == 'runtime':
                update_offroad_cell(tft, 0, 2, val, o_state['runtime'])
                o_state['runtime'] = val

            elif key == 'iat':
                update_offroad_cell(tft, 1, 2, val, o_state['iat'])
                o_state['iat'] = val

            elif key == 'o2':
                update_offroad_cell(tft, 2, 1, val, o_state['o2'])
                o_state['o2'] = val

        # ---- animate arc needles (screen 0 only) ----
        if screen == 0:
            for g in g_state:
                cur = g['disp_a']
                tgt = g['tgt_a']
                if abs(cur - tgt) > 0.5:
                    diff  = cur - tgt
                    step  = max(2.0, abs(diff) * 0.15)
                    new_a = cur - step if diff > 0 else cur + step
                    if abs(new_a - tgt) < step:
                        new_a = tgt
                    update_gauge(tft, g, new_a)


main()
