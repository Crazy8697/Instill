# Instill

> *"In blackest day, in brightest night,*
> *Beware your fears made into light.*
> *Let those who try to stop what's right*
> *Burn like my power — Sinestro's might!"*

Named after the Sinestro Corps yellow lantern oath. The vehicle is **Malia**, named after a Yellow Lantern character. Instill great fear.

---

## What It Is

A distributed vehicle monitoring and automation system built from scratch for a **2001 Nissan Xterra SE**. No budget. Everything from parts on hand.

Instill runs on a Raspberry Pi Pico2W and a pair of Arduino Nanos. It reads OBD-II data over Bluetooth, drives a 3.5" TFT display with live gauges, automates headlights based on ambient light, and monitors cabin environment — all without cloud dependencies.

---

## Hardware

### Brain
| Part | Role |
|------|------|
| Raspberry Pi Pico2W | Main controller — OBD, display, coordination |
| 3.5" TFT display (SPI) | Gauge display, likely ILI9488 controller |
| Micro Mechanic OBD-II adapter | Bluetooth ELM327, plugs into OBD-II port |
| Pico Breadboard Kit breakout | Exposes TFT header, buttons, joystick, RGB LED, buzzer |

### Sensor Nodes
| Part | Location | Role |
|------|----------|------|
| Arduino Nano (Column) | Steering column area | Lighting automation via photoresistor + relay |
| Arduino Nano (Sensor) | Under seat/dash | Cabin temp/humidity (DHT sensor) |

### Sensor Kit (Inland 37-piece)
Joystick, Flame Sensor, RGB LED, Heartbeat Sensor, Light Cup, Hall Magnetic Sensor, Relay, Linear Hall Sensor, SMD RGB, 7-Color Flash, Tilt Switch, Temperature Sensor, Big Sound Sensor, Touch Sensor, Two-Color LED, Laser Emitter, Ball Switch, Analog Temperature Sensor, Small Sound Sensor, Digital Temperature Sensor ×2, Button, Photoresistor, IR Emission, Tracking Sensor, Buzzer, Reed Switch, Shock Sensor, Temperature and Humidity Sensor, IR Receiver, Avoidance Sensor, Passive Buzzer, Mini Reed, Rotary Encoders, Analog Hall Sensor, Tap Module, Light Blocking.

### Additional Parts on Hand
- 1G accelerometer (Radio Shack era)
- MOSFETs, relays, optocouplers, 555 timers, transistors, rectifier diodes
- 15kΩ resistors (~200 in stock)
- Tact buttons and momentary switches
- 24V fans (run at 12V reduced or PWM via MOSFET)
- Stepper motors, adhesive heatsinks
- Harvest boards: TVs, power supplies, HVAC controls, network gear

---

## Architecture

```
[Micro Mechanic BT] <--BT--> [Pico2W] <--SPI--> [3.5" TFT]
                                  |
                             [UART out] -----> [Pi 4B / 8.8" display] (Phase 4)
                                  |
                    [I2C or UART] |
                    /             \
         [Column Nano]        [Sensor Nano]
         - Photoresistor       - DHT temp/humidity
         - Relay               - Rotary encoder input
           → headlight stalk
```

---

## Phases

### Phase 1 — OBD Gauges *(active)*
- Pico2W connects to Micro Mechanic over classic Bluetooth (ELM327 AT commands)
- Polls PIDs: RPM, coolant temp, battery voltage, throttle position, MAF
- Displays gauge layout on 3.5" TFT
- Rotary encoder for page switching

### Phase 2 — Environmental Node
- Sensor Nano reads DHT temp/humidity
- Sends JSON to Pico over UART
- Pico overlays cabin temp on gauge display

### Phase 3 — Auto Headlights
- Column Nano reads photoresistor
- Below threshold → relay closes → triggers headlight circuit (parallel to stalk, full-on)
- Nano powered from switched 12V — relay cannot fire with ignition off
- Mimics stalk full-on position, overrides DRL naturally

### Phase 4 — Pi Integration
- Pico streams OBD + sensor JSON over UART to Pi 4B
- Pi parses stream, displays gauges on HUDIY 8.8" display
- No new hardware required

### Phase 5 — Stretch Goals
- G-force / 0–60 display (1G accelerometer)
- Fuel economy (MPG) from OBD
- DTC reader/clear via TFT
- Pitch/roll for wheeling
- Ambient footwell lighting (MOSFET + LED strip, photoresistor auto-dim)

---

## Repository Layout

```
/pico           MicroPython — Pico2W firmware (OBD, display, coordination)
/nano_column    Arduino C — Column Nano (photoresistor, relay, headlights)
/nano_sensor    Arduino C — Sensor Nano (DHT, rotary encoder)
/docs           Wiring diagrams, pinouts, notes
```

---

## Software Stack

| Component | Language | Notes |
|-----------|----------|-------|
| Pico2W | MicroPython | ELM327 BT, TFT driver, OBD parser |
| Arduino Nanos | Arduino C | Standard IDE |
| Pi integration (Phase 4) | Python | UART serial stream reader |

---

## Wiring Notes

### Pico2W ↔ Arduino Nano UART
- Nano TX (5V) → voltage divider (15kΩ + 15kΩ) → Pico RX (3.3V)
- Pico TX (3.3V) → Nano RX directly (5V tolerant)
- Shared GND

### Power
- Pico2W: 5V from USB or buck converter off switched 12V
- Nanos: 5V from 7805 or buck converter off switched 12V
- MCUs have no filesystem writes — hard power cut is safe

### Isolation
- Optocouplers between vehicle wiring (relay/headlight tap) and Nano GPIO
- Protects against alternator noise and 12V spikes

---

## OBD PID Reference

```
ATZ        reset
ATE0       echo off
ATL0       linefeeds off
ATSP0      auto protocol
0100       supported PIDs
010C       RPM          → raw / 4
010D       vehicle speed
0105       coolant temp → raw − 40 °C
0111       throttle     → raw × 100 / 255 %
0110       MAF air flow rate
```
