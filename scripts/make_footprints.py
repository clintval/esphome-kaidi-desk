"""Write the custom footprints: the RJ50 jack, the C3 SuperMini socket, the USB-C breakout and the B0505S converter.

The jack follows FCI drawing C-BMJ-0101 rev F (10 pol shallow latch, PCB layout view): pin 1 at the
origin in line with one locating peg, odd pins on the row 8.89 mm from the pegs, even pins on the row
6.35 mm from them, ending in line with the other peg. This is KiCad's RJ45_Amphenol_54602-x08 with
one more contact at each end.

Run with: python3 scripts/make_footprints.py hardware/kaidi.pretty
"""

import itertools
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dimensions import (
    B0505S_LENGTH,
    B0505S_PIN1_INSET,
    B0505S_PIN_ROW_INSET,
    B0505S_THICKNESS,
    C3_LENGTH,
    C3_PIN1_INSET,
    C3_USB_OVERHANG,
    C3_WIDTH,
    USBC_BREAKOUT_DEPTH,
    USBC_BREAKOUT_PIN_INSET,
    USBC_BREAKOUT_WIDTH,
    USBC_RECEPTACLE_DEPTH,
    USBC_RECEPTACLE_WIDTH,
)

LIB = sys.argv[1]


IDS = itertools.count()


def u():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kaidi-desk/footprints/{next(IDS)}"))


def line(x1, y1, x2, y2, layer, width):
    return (
        f"(fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width {width}) (type solid)) "
        f'(layer "{layer}") (uuid "{u()}"))'
    )


def rect(x1, y1, x2, y2, layer, width):
    return "".join(
        line(*a, layer, width) for a in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1))
    )


def text(kind, value, x, y, layer, hide=False):
    h = " (hide yes)" if hide else ""
    return (
        f'(property "{kind}" "{value}" (at {x} {y} 0) (layer "{layer}"){h} (uuid "{u()}") '
        "(effects (font (size 1 1) (thickness 0.15))))"
    )


def pad(num, x, y, shape, size, drill):
    kind = "np_thru_hole" if num == "" else "thru_hole"
    layers = '"*.Cu" "*.Mask"'
    return f'(pad "{num}" {kind} {shape} (at {x} {y}) (size {size} {size}) (drill {drill}) (layers {layers}) (uuid "{u()}"))'


def footprint(name, descr, body):
    return (
        f'(footprint "{name}" (version 20240108) (generator "make_footprints") (layer "F.Cu") '
        f'(descr "{descr}") (attr through_hole) {body})\n'
    )


pitch, row = 1.27, 2.54
pins = "".join(
    pad(str(n), round((n - 1) * pitch, 3), -row if n % 2 else 0, "rect" if n == 1 else "circle", 1.5, 0.76)
    for n in range(1, 11)
)
span = 9 * pitch
cx = span / 2
pegs = pad("", 0, 6.35, "circle", 3.2, 3.2) + pad("", round(span, 3), 6.35, "circle", 3.2, 3.2)
x1, x2 = round(cx - 7.65, 3), round(cx + 7.65, 3)
y1, y2 = -3.77, 13.97
body = (
    text("Reference", "J**", cx, -5.2, "F.SilkS")
    + text("Value", "RJ50_54602-910", cx, 15.2, "F.Fab")
    + pins
    + pegs
    + rect(x1, y1, x2, y2, "F.Fab", 0.1)
    + line(x1 - 0.11, y2 - 0.6, x1 - 0.11, y1 - 0.11, "F.SilkS", 0.12)
    + line(x1 - 0.11, y1 - 0.11, x2 + 0.11, y1 - 0.11, "F.SilkS", 0.12)
    + line(x2 + 0.11, y1 - 0.11, x2 + 0.11, y2 - 0.6, "F.SilkS", 0.12)
    + rect(x1 - 0.5, y1 - 0.5, x2 + 0.5, y2 + 0.5, "F.CrtYd", 0.05)
)
Path(f"{LIB}/RJ50_Amphenol_54602-910_Horizontal.kicad_mod").write_text(
    footprint(
        "RJ50_Amphenol_54602-910_Horizontal",
        "10P10C right-angle shallow latch modular jack, Amphenol/FCI 54602-x10LF, drawing C-BMJ-0101 rev F",
        body,
    )
)

pins = ""
for i in range(8):
    pins += pad(str(i + 1), 15.24, round(i * 2.54, 2), "rect" if i == 0 else "circle", 1.7, 1.0)
    pins += pad(str(i + 9), 0, round(i * 2.54, 2), "circle", 1.7, 1.0)
w0, w1 = 7.62 - C3_WIDTH / 2, 7.62 + C3_WIDTH / 2
h0, h1 = -C3_PIN1_INSET, C3_LENGTH - C3_PIN1_INSET
body = (
    text("Reference", "U**", 7.62, h1 + 2, "F.SilkS")
    + text("Value", "ESP32-C3_SuperMini", 7.62, 8.9, "F.Fab")
    + pins
    + line(w0, h0, w1, h0, "F.SilkS", 0.12)
    + line(w0, h0, w0, 12.0, "F.SilkS", 0.12)
    + line(w1, h0, w1, 12.0, "F.SilkS", 0.12)
    + rect(w0, h0, w1, h1, "F.Fab", 0.1)
    + line(3.12, h0, 3.12, h0 - C3_USB_OVERHANG, "F.SilkS", 0.12)
    + line(12.12, h0, 12.12, h0 - C3_USB_OVERHANG, "F.SilkS", 0.12)
    + rect(w0 - 0.5, h0 - C3_USB_OVERHANG, w1 + 0.5, h1 + 0.5, "F.CrtYd", 0.05)
)
Path(f"{LIB}/ESP32-C3_SuperMini.kicad_mod").write_text(
    footprint(
        "ESP32-C3_SuperMini",
        "ESP32-C3 SuperMini plugged into two 1x8 round-pin socket strips, component side up, USB-C toward -Y, antenna toward +Y; pins 1-8 (right) 5V GND 3V3 4 3 2 1 0, pins 9-16 (left) GPIO5 6 7 8 9 10 20 21",
        body,
    )
)

pins = "".join(pad(str(i + 1), round(i * 2.54, 2), 0, "rect" if i == 0 else "circle", 1.7, 1.0) for i in range(6))
cx = 2.5 * 2.54
w0, w1 = round(cx - USBC_BREAKOUT_WIDTH / 2, 3), round(cx + USBC_BREAKOUT_WIDTH / 2, 3)
h0, h1 = -USBC_BREAKOUT_PIN_INSET, round(USBC_BREAKOUT_DEPTH - USBC_BREAKOUT_PIN_INSET, 3)
r0, r1 = round(cx - USBC_RECEPTACLE_WIDTH / 2, 3), round(cx + USBC_RECEPTACLE_WIDTH / 2, 3)
body = (
    text("Reference", "J**", cx, h0 - 1.4, "F.SilkS")
    + text("Value", "USB-C breakout", cx, h1 - 3.0, "F.Fab")
    + pins
    + rect(w0, h0, w1, h1, "F.Fab", 0.1)
    + rect(r0, round(h1 - USBC_RECEPTACLE_DEPTH, 3), r1, h1, "F.Fab", 0.1)
    + rect(w0 - 0.11, h0 - 0.11, w1 + 0.11, h1, "F.SilkS", 0.12)
    + rect(w0 - 0.5, h0 - 0.5, w1 + 0.5, h1 + 0.5, "F.CrtYd", 0.05)
)
Path(f"{LIB}/USB-C_Breakout_Cermant_1x06.kicad_mod").write_text(
    footprint(
        "USB-C_Breakout_Cermant_1x06",
        "Cermant USB-C female breakout (5.1k on CC) on a 1x6 2.54 mm header, receptacle up, mouth toward +Y; pins VBUS GND CC1 D- D+ CC2; outline estimated",
        body,
    )
)

positions = {"1": 0.0, "2": 2.54, "4": 7.62, "6": 12.7}
pins = "".join(pad(n, x, 0, "rect" if n == "1" else "circle", 1.8, 1.0) for n, x in positions.items())
b0, b1 = -B0505S_PIN1_INSET, round(B0505S_LENGTH - B0505S_PIN1_INSET, 3)
t0, t1 = -B0505S_PIN_ROW_INSET, round(B0505S_THICKNESS - B0505S_PIN_ROW_INSET, 3)
body = (
    text("Reference", "U**", 5.08, t1 + 1.4, "F.SilkS")
    + text("Value", "B0505S-2WR3", 5.08, t1 - 2.0, "F.Fab")
    + pins
    + rect(b0, t0, b1, t1, "F.Fab", 0.1)
    + rect(b0 - 0.11, t0 - 0.11, b1 + 0.11, t1 + 0.11, "F.SilkS", 0.12)
    + rect(b0 - 0.25, t0 - 0.25, b1 + 0.25, t1 + 0.25, "F.CrtYd", 0.05)
)
Path(f"{LIB}/Converter_DCDC_Mornsun_B_S-2WR3_SIP.kicad_mod").write_text(
    footprint(
        "Converter_DCDC_Mornsun_B_S-2WR3_SIP",
        "Mornsun B_S-2WR3 isolated DC-DC, SIP on a 2.54 mm grid with pins 1 Vin, 2 GND, 4 0V, 6 +Vo (datasheet layout)",
        body,
    )
)
