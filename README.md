# esphome-kaidi-desk

[![Build Status](https://github.com/clintval/esphome-kaidi-desk/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/clintval/esphome-kaidi-desk/actions/workflows/ci.yml?query=branch%3Amain)
[![ESPHome](https://img.shields.io/badge/ESPHome-external%20component-000000.svg)](https://esphome.io/components/external_components.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Control a Kaidi standing desk from Home Assistant with an ESP32 and ESPHome.

![Circuit board illustration of the dongle](docs/board.svg)

## Introduction

Many "K Series" and other budget standing desks run on a Kaidi control box, such as the `KDDY094`.
The box talks to its keypad over a 9600 baud serial link on a 10-pin RJ50 cable, and no off-the-shelf smart-desk dongle speaks its protocol.
This component reads the desk's height and drives it the way the keypad does: it raises the keypad's wake line to power the motors, waits for the box to settle, then streams Up, Down and Reset commands.
Earlier Kaidi projects only listened to the box; moving the desk needed the wake line on contact 10, which an 8-pin RJ45 plug cannot reach.

## Quick Start

Add the component to an ESPHome config and wire the dongle as in [Hardware](#hardware):

```yaml
external_components:
  - source: github://clintval/esphome-kaidi-desk@main
    components: [kaidi_desk]

uart:
  rx_pin: GPIO4
  tx_pin: GPIO7
  baud_rate: 9600

kaidi_desk:
  tx_enable_pin:
    number: GPIO6
    inverted: true
  wake_pin:
    number: GPIO10
    inverted: true

sensor:
  - platform: kaidi_desk
    height:
      name: Height

number:
  - platform: kaidi_desk
    target_height:
      name: Target Height
      unit_of_measurement: in
```

A complete config for an ESP32-C3 SuperMini, with every entity, is in [`example/kaidi-desk.yaml`](example/kaidi-desk.yaml).
Once flashed, the board appears in Home Assistant through the ESPHome integration.

## Entities

| Platform | Key | Purpose |
| --- | --- | --- |
| `sensor` | `height` | Height above the desk's lowest point, in cm (Home Assistant converts units) |
| `text_sensor` | `status` | `Ready`, `Reset Needed` (E04), `Resetting`, or `Asleep` |
| `number` | `target_height` | Move to a height; follows the real height while idle, in `cm` or `in` |
| `button` | `nudge_up`, `nudge_down` | Move briefly up or down, about half an inch |
| `button` | `stop` | Stop any move |
| `button` | `reset` | Hold Up and Down until the box re-zeros, which clears E04 |
| `switch` | `keep_awake` | Hold the wake line high so height streams live and moves start at once |

## Hardware

The dongle plugs into the control box's free RJ50 port with a straight-through 10P10C cable and a 10-position breakout.
A 74AHCT125 buffer lifts the ESP's 3.3 V signals to the box's 5 V, and its enable pins release the shared lines whenever the ESP is not sending.
A resistor divider brings the box's 5 V height stream down to about 3.1 V for the ESP.

| RJ50 contact | Signal | Connection |
| --- | --- | --- |
| 2 | +5 V | Unconnected; the ESP runs on USB-C |
| 3 | Ground | Common ground |
| 7 | Command, keypad to box | 74AHCT125 gate 1 through 1 kΩ, input GPIO7, enable GPIO6 |
| 8 | Height, box to keypad | 10 kΩ over 10 kΩ + 4.7 kΩ to GPIO4 |
| 10 | Wake, keypad to box | 74AHCT125 gate 2 through 1 kΩ, input tied high, enable GPIO10 |

The [schematic](docs/wiring.svg) and [breadboard layout](docs/breadboard.svg) list every part and hole.
While the keypad is plugged into the other port, it holds the command and wake lines and the ESP cannot move the desk; an inline revision that merges both senders is in progress.

## Protocol

Each frame is 7 bytes, `0x68 0x01 <mode> <hi> <lo> <checksum> 0x16`, where the checksum is the low byte of `0x01 + mode + hi + lo`.

| Direction | Mode | Meaning |
| --- | --- | --- |
| Keypad to box | `0x01` | Up |
| Keypad to box | `0x02` | Down |
| Keypad to box | `0x03` | Idle |
| Keypad to box | `0x04` | Up and Down held (reset) |
| Box to keypad | `0x00` | Height in 0.1 cm |
| Box to keypad | `0x30` | Reset needed (E04); the value counts down during the reset |
| Box to keypad | `0x04` | Reset rebound in progress |

The keypad sends a frame every 14 ms while awake.
The box answers about 0.6 s after it wakes, ignores moves for about 1 s more, and needs Up held about 0.4 s before the motors start.
It displays E04 when a reset is released before the rebound.

## Development and Testing

See the [contributing guide](./CONTRIBUTING.md) for more information.

## Acknowledgements

The frame format was first decoded in [`xvzf/kaidi-desk-controller-protocol`](https://github.com/xvzf/kaidi-desk-controller-protocol), and [`jcappaert/esphome-kaidi`](https://github.com/jcappaert/esphome-kaidi) read the height on the same `KDDY094` box.

## License

MIT
