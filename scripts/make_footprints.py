"""Write the custom footprints: the RJ50 jack and the B0505S converter, both centered on their pads.

The jack follows the board layout on TE drawing C-5558067 rev B1, a component-side view: the odd contacts
are on the row 8.89 mm from the pegs and the even ones 6.35 mm from them, with the latch toward the board
and contact 1 on the left as you look into the opening.

Run with: python3 scripts/make_footprints.py hardware/kaidi.pretty
"""

import itertools
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dimensions import B0505S_LENGTH, B0505S_PIN1_INSET, B0505S_PIN_ROW_INSET, B0505S_THICKNESS, JACK_OVERHANG

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


pitch = 1.27
first = -4.5 * pitch
pins = "".join(
    pad(str(n), round(first + (n - 1) * pitch, 3), -2.92 if n % 2 else -0.38, "rect" if n == 1 else "circle", 1.4, 0.89)
    for n in range(1, 11)
)
shell = "".join(pad("SH", x, 2.92, "circle", 2.2, 1.57) for x in (-7.745, 7.745))
pegs = "".join(pad("", x, 5.97, "circle", 3.25, 3.25) for x in (first, -first))
x1, x2, y1, y2 = -7.935, 7.935, -4.57, 16.77
edge = y2 - JACK_OVERHANG - 0.4
body = (
    text("Reference", "J**", 0, -6.0, "F.SilkS")
    + text("Value", "RJ50_5558067-1", 0, 12.0, "F.Fab")
    + pins
    + shell
    + pegs
    + rect(x1, y1, x2, y2, "F.Fab", 0.1)
    + line(x1 - 0.11, edge, x1 - 0.11, y1 - 0.11, "F.SilkS", 0.12)
    + line(x1 - 0.11, y1 - 0.11, x2 + 0.11, y1 - 0.11, "F.SilkS", 0.12)
    + line(x2 + 0.11, y1 - 0.11, x2 + 0.11, edge, "F.SilkS", 0.12)
    + rect(x1 - 0.5, y1 - 0.5, x2 + 0.5, y2 + 0.5, "F.CrtYd", 0.05)
)
Path(f"{LIB}/RJ50_TE_5558067-1_Horizontal.kicad_mod").write_text(
    footprint(
        "RJ50_TE_5558067-1_Horizontal",
        "10P10C right-angle shielded modular jack, latch down, TE 5558067-1, drawing C-5558067 rev B1",
        body,
    )
)

positions = {"1": -6.35, "2": -3.81, "4": 1.27, "6": 6.35}
pins = "".join(pad(n, x, 0, "rect" if n == "1" else "circle", 1.8, 1.0) for n, x in positions.items())
b0 = -6.35 - B0505S_PIN1_INSET
b1 = round(b0 + B0505S_LENGTH, 3)
t0, t1 = -B0505S_PIN_ROW_INSET, round(B0505S_THICKNESS - B0505S_PIN_ROW_INSET, 3)
body = (
    text("Reference", "U**", 0, t1 + 1.4, "F.SilkS")
    + text("Value", "B0505S-2WR3", 0, t1 - 2.0, "F.Fab")
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
