"""Write the two custom footprints: the Amphenol/FCI 54602-x10 right-angle RJ50 jack and the C3 SuperMini socket.

The jack follows FCI drawing C-BMJ-0101 rev F (10 pol shallow latch, PCB layout view) and the same
conventions as KiCad's RJ45_Amphenol_54602-x08_Horizontal: pin 1 at the origin, odd pins on the
front row, even pins 2.54 mm behind, locating pegs 6.35 mm toward the opening.

Run with: python3 scripts/make_footprints.py hardware/kaidi.pretty
"""

import itertools
import sys
import uuid

LIB = sys.argv[1]


IDS = itertools.count()


def u():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kaidi-desk/footprints/{next(IDS)}"))


def line(x1, y1, x2, y2, layer, width):
    return (f'(fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width {width}) (type solid)) '
            f'(layer "{layer}") (uuid "{u()}"))')


def rect(x1, y1, x2, y2, layer, width):
    return "".join(line(*a, layer, width) for a in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)))


def text(kind, value, x, y, layer, hide=False):
    h = " (hide yes)" if hide else ""
    return (f'(property "{kind}" "{value}" (at {x} {y} 0) (layer "{layer}"){h} (uuid "{u()}") '
            '(effects (font (size 1 1) (thickness 0.15))))')


def pad(num, x, y, shape, size, drill):
    kind = "np_thru_hole" if num == "" else "thru_hole"
    layers = '"*.Cu" "*.Mask"' if num else '"*.Cu" "*.Mask"'
    return f'(pad "{num}" {kind} {shape} (at {x} {y}) (size {size} {size}) (drill {drill}) (layers {layers}) (uuid "{u()}"))'


def footprint(name, descr, body):
    return (f'(footprint "{name}" (version 20240108) (generator "make_footprints") (layer "F.Cu") '
            f'(descr "{descr}") (attr through_hole) {body})\n')


pitch, row = 1.27, 2.54
pins = "".join(pad(str(n), round((n - 1) * pitch, 3), 0 if n % 2 else -row, "rect" if n == 1 else "circle", 1.5, 0.76)
               for n in range(1, 11))
span = 9 * pitch
cx = span / 2
pegs = pad("", 0, 6.35, "circle", 3.2, 3.2) + pad("", round(span, 3), 6.35, "circle", 3.2, 3.2)
x1, x2 = round(cx - 7.65, 3), round(cx + 7.65, 3)
y1, y2 = -3.77, 13.97
body = (text("Reference", "J**", cx, -5.2, "F.SilkS") + text("Value", "RJ50_54602-910", cx, 15.2, "F.Fab")
        + pins + pegs + rect(x1, y1, x2, y2, "F.Fab", 0.1)
        + line(x1 - 0.11, y2 - 0.6, x1 - 0.11, y1 - 0.11, "F.SilkS", 0.12) + line(x1 - 0.11, y1 - 0.11, x2 + 0.11, y1 - 0.11, "F.SilkS", 0.12)
        + line(x2 + 0.11, y1 - 0.11, x2 + 0.11, y2 - 0.6, "F.SilkS", 0.12)
        + rect(x1 - 0.5, y1 - 0.5, x2 + 0.5, y2 + 0.5, "F.CrtYd", 0.05))
open(f"{LIB}/RJ50_Amphenol_54602-910_Horizontal.kicad_mod", "w").write(
    footprint("RJ50_Amphenol_54602-910_Horizontal",
              "10P10C right-angle shallow latch modular jack, Amphenol/FCI 54602-x10LF, drawing C-BMJ-0101 rev F", body))

pins = ""
for i in range(8):
    pins += pad(str(i + 1), 0, round(i * 2.54, 2), "rect" if i == 0 else "oval" if False else "circle", 1.7, 1.0)
    pins += pad(str(i + 9), 15.24, round(i * 2.54, 2), "circle", 1.7, 1.0)
w0, w1 = -1.38, 15.24 + 1.38
h0, h1 = -4.3, 7 * 2.54 + 1.4
body = (text("Reference", "U**", 7.62, h1 + 2, "F.SilkS") + text("Value", "ESP32-C3_SuperMini", 7.62, 8.9, "F.Fab")
        + pins + line(w0, h0, w1, h0, "F.SilkS", 0.12) + line(w0, h0, w0, 12.0, "F.SilkS", 0.12)
        + line(w1, h0, w1, 12.0, "F.SilkS", 0.12) + rect(w0, h0, w1, h1, "F.Fab", 0.1)
        + line(4.12, h0, 4.12, h0 - 1.6, "F.SilkS", 0.12) + line(11.12, h0, 11.12, h0 - 1.6, "F.SilkS", 0.12)
        + rect(w0 - 0.5, h0 - 0.5, w1 + 0.5, h1 + 0.5, "F.CrtYd", 0.05))
open(f"{LIB}/ESP32-C3_SuperMini_Flush.kicad_mod", "w").write(
    footprint("ESP32-C3_SuperMini_Flush",
              "ESP32-C3 SuperMini soldered flat to the board on header pins with the plastic spacers removed, component side up, USB-C toward -Y; pins 1-8 5V GND 3V3 4 3 2 1 0, pins 9-16 GPIO5 6 7 8 9 10 20 21",
              body))
