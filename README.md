# Instill

> *"In blackest day, in brightest night,*
> *Beware your fears made into light.*
> *Let those who try to stop what's right*
> *Burn like my power — Sinestro's might!"*

Named after the Sinestro Corps yellow lantern oath. The vehicle is **Malia**, named after a Yellow Lantern character. Instill great fear.

---

## What It Is

A distributed vehicle monitoring and automation system built from scratch for a **2001 Nissan Xterra SE**. No budget. Everything from parts on hand.

Instill runs on a Raspberry Pi Pico 2W and a pair of Arduino Nanos. It reads OBD-II data over Bluetooth LE, drives a 3.5" TFT display with live gauges, automates headlights based on ambient light, and monitors cabin environment — all without cloud dependencies.

---

## Hardware

### Raspberry Pi Pico 2W
**Current test board:** 52Pi Breadboard Kit Plus (EP-0172)

**Responsibilities:**
- **Display** — ST7796S 3.5" TFT, 480×320, SPI
- **OBD comms** — Bluetooth LE (Micro Mechanic 18002, MAC 00:1D:A5:00:F9:57)

| GPIO | Function |
|------|----------|
| 2 | TFT CLK (SPI0) |
| 3 | TFT MOSI (SPI0) |
| 5 | TFT CS |
| 6 | TFT DC |
| 7 | TFT RST |
| 14 | Right button (cycle screens) |
| 15 | Left button (unused) |

### Arduino Nano — Column
**Location:** Steering column

**Responsibilities:**
- Lighting automation
- IR garage door (planned)

### Arduino Nano — Sensor
**Location:** Under dash

**Responsibilities:**
- DHT temp/humidity (planned)

### Nano UART Wiring
- Nano TX (5V) → 15kΩ + 15kΩ voltage divider → Pico RX (3.3V)
- Pico TX (3.3V) → Nano RX directly (5V tolerant)
- Shared GND

---

## Architecture

```
[Micro Mechanic BT] <--BLE--> [Pico2W] <--SPI--> [3.5" TFT]
                                   |
                              [UART out] -----> [Pi 4B / 8.8" display] (Phase 4)
                                   |
                     [I2C or UART] |
                     /             \
          [Column Nano]        [Sensor Nano]
          - IR garage door      - DHT temp/humidity
          - Lighting relay
```

---

## Screens

### Screen 0 — Daily
- **Top 75%:** 2 arc gauges — MPH | RPM
  - 240° sweep, r=88px, animated needle interpolation
  - Gauge centers: x=135, x=345
- **Bottom 25%:** Battery V | Coolant °C | Est. MPG | Engine Load %
- **BT indicator** top-right: yellow=connected, dark=scanning

### Screen 1 — Offroad
3×3 text grid:

|  | Col 0 | Col 1 | Col 2 |
|--|-------|-------|-------|
| Row 0 | Fuel Trim | Timing ° | Runtime min |
| Row 1 | Pitch ° (placeholder) | Roll ° (placeholder) | IAT °C |
| Row 2 | Battery V | O2 V | MAF g/s |

GPIO14 (right button) cycles between screens.

---

## Phases

### Phase 1 — OBD Gauges ✅
- Pico 2W connects to Micro Mechanic over BLE (ELM327 AT commands)
- Polls PIDs: RPM, speed, coolant, battery, MAF, load, timing, fuel trim, IAT, O2, runtime
- Dual-screen gauge display on ST7796S 3.5" TFT
- Tire-corrected MPH (33" on 29.1" stock), instantaneous MPG via MAF

### Phase 2 — Environmental Node
- Sensor Nano reads DHT temp/humidity
- Sends JSON to Pico over UART
- Pico overlays cabin temp on gauge display

### Phase 3 — Auto Headlights
- Column Nano reads photoresistor
- Below threshold → relay closes → triggers headlight circuit
- Nano powered from switched 12V

### Phase 3b — IR Garage Door
- Capture remote IR code with IR receiver
- Replay on button press via IR LED on dash/visor
- Goes in `nano_column/`

### Phase 4 — Pi Integration
- Pico streams OBD + sensor JSON over UART to Pi 4B
- Pi parses stream, displays gauges on HUDIY 8.8" display
- No new hardware required

### Phase 5 — Stretch Goals
- Pitch/roll display (IMU wired to Pico)
- DTC reader/clear via TFT
- Ambient footwell lighting
- G-force / 0–60 display

---

## OBD PIDs Polled

| PID | Data | Formula |
|-----|------|---------|
| 010C | RPM | (A×256+B)/4 |
| 010D | Speed | A × 0.70488 = corrected MPH (33" tires) |
| 0104 | Engine load % | A×100/255 |
| 0105 | Coolant °C | A−40 |
| 010E | Timing advance ° | A/2−64 |
| 0106 | Short term fuel trim % | (A−128)×100/128 |
| 010F | IAT °C | A−40 |
| 0114 | O2 voltage V | A×0.005 |
| 011F | Runtime min | (A×256+B)/60 |
| 0110 | MAF g/s | (A×256+B)/100 |
| ATRV | Battery voltage | ELM327 direct |

### MPG Formula
`MPG = speed_mph × 7.107 / maf_gs` (instantaneous, MAF-based)

---

## Repository Layout

```
/pico           MicroPython — Pico2W firmware (OBD, display)
/nano_column    Arduino C — Column Nano (IR, lighting)
/nano_sensor    Arduino C — Sensor Nano (DHT)
/docs           Wiring diagrams, pinouts, notes
```

---

## Software Stack

| Component | Language | Notes |
|-----------|----------|-------|
| Pico2W | MicroPython v1.28.0 | BLE OBD, ST7796S SPI driver |
| Arduino Nanos | Arduino C | Standard IDE |
| Pi integration (Phase 4) | Python | UART serial stream reader |
