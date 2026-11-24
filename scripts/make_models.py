"""Write STEP models of the parts KiCad's library lacks: the RJ50 jack, the B0505S, the USB-C receptacle and the buttons.

They are in KiCad's 3D frame for each footprint: millimeters, X right, Y up the footprint, Z = 0 on the board.

Run with: python scripts/make_models.py hardware/kaidi.3dshapes
"""

import sys
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Color,
    Compound,
    Cylinder,
    Location,
    Plane,
    Polyline,
    Pos,
    Rot,
    export_step,
    extrude,
    fillet,
    make_face,
)
from dimensions import (
    B0505S_HEIGHT,
    B0505S_LENGTH,
    B0505S_PIN1_INSET,
    B0505S_PIN_ROW_INSET,
    B0505S_STANDOFF,
    B0505S_THICKNESS,
)

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
METAL, GOLD, BLACK = Color(0.80, 0.81, 0.83), Color(0.95, 0.75, 0.30), Color(0.03, 0.03, 0.035)


def block(x1, y1, z1, x2, y2, z2):
    size = (abs(x2 - x1), abs(y2 - y1), abs(z2 - z1))
    return Pos((x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2) * Box(*size)


def prism(points, y, depth):
    """Extrude an outline of (x, z) points from y toward -Y."""
    face = make_face(Plane.XZ.offset(-y) * Polyline(*points, close=True))
    return extrude(face, depth, dir=(0, -1, 0))


def paint(part, color, label):
    part.color, part.label = color, label
    return part


def write(name, parts):
    export_step(Compound(label=name, children=parts), str(OUT / f"{name}.step"))


# TE 5558067-1, drawing C-5558067 rev B1: the opening faces -Y and the latch slot is toward the board.
HALF, BACK, FRONT, TOP, SKIN = 7.935, 4.57, -16.77, 13.64, 0.25
SEAM = BACK - 3.6
OPENING = [(-6.1, 11.0), (6.1, 11.0), (6.1, 3.6), (3.25, 3.6), (3.25, 1.9), (2.1, 1.9), (2.1, 0.8)]
OPENING += [(-x, z) for x, z in reversed(OPENING[4:])] + [(-3.25, 3.6), (-6.1, 3.6)]

shell = block(-HALF, SEAM, 0.0, HALF, FRONT, TOP)
shell = fillet(shell.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 0.6)
shell = fillet(shell.edges().filter_by(Axis.X).group_by(Axis.Z)[-1].group_by(Axis.Y)[:1], 0.4)
shell -= block(-HALF + SKIN, SEAM + 1, -1, HALF - SKIN, FRONT + SKIN, TOP - SKIN)
shell -= prism(OPENING, FRONT + 1, 3)
hood = block(-HALF - 0.05, BACK, 0.7, HALF + 0.05, SEAM + 0.2, TOP + 0.05)
hood = fillet(hood.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 0.6)
hood = fillet(hood.edges().filter_by(Axis.Z).group_by(Axis.Y)[-1], 0.6)
housing = block(-HALF + 0.3, BACK - 0.1, 0.3, HALF - 0.3, FRONT + SKIN + 0.02, TOP - 0.3)
housing -= prism(OPENING, FRONT + 12.0, 13.0)
for s in (-1, 1):
    window = block(s * (HALF + 1), BACK - 1.0, 5.3, s * (HALF - 0.3), BACK - 2.6, 6.9)
    hood -= window
    shell += block(s * HALF, -2.42, -3.4, s * (HALF - SKIN), -3.42, 0.4)
latches = [
    paint(block(s * (HALF - 0.28), BACK - 1.2, 5.5, s * (HALF + 0.02), BACK - 2.4, 6.7), METAL, "latch")
    for s in (-1, 1)
]
contacts = [
    paint(Pos((n - 4.5) * 1.02, FRONT + 6.4, 9.7) * Rot(16, 0, 0) * Box(0.42, 9.6, 0.2), GOLD, "contact")
    for n in range(10)
]
pins = [
    paint(
        block(x - 0.2, y - 0.17, -3.56, x + 0.2, y + 0.17, 0.8),
        METAL,
        "pin",
    )
    for n in range(10)
    for x, y in [((n - 4.5) * 1.27, 0.38 if n % 2 else 2.92)]
]
write(
    "RJ50_TE_5558067-1_Horizontal",
    [
        paint(shell, METAL, "shell"),
        paint(hood, METAL, "hood"),
        paint(housing, BLACK, "housing"),
        *latches,
        *contacts,
        *pins,
    ],
)

left, back = -6.35 - B0505S_PIN1_INSET, B0505S_PIN_ROW_INSET
z0 = B0505S_STANDOFF
body = block(left, back, z0, left + B0505S_LENGTH, back - B0505S_THICKNESS, z0 + B0505S_HEIGHT)
body = fillet(body.edges(), 0.3)
legs = [paint(block(x - 0.25, -0.15, -3.0, x + 0.25, 0.15, 0.8), METAL, "leg") for x in (-6.35, -3.81, 1.27, 6.35)]
write("Converter_DCDC_Mornsun_B_S-2WR3_SIP", [paint(body, BLACK, "body"), *legs])

tube = block(-4.47, 3.65, 0.0, 4.47, -3.65, 3.26)
tube = fillet(tube.edges().filter_by(Axis.Y), 1.55)
bore = block(-4.2, 3.2, 0.27, 4.2, -4.65, 2.99)
tube -= fillet(bore.edges().filter_by(Axis.Y), 1.3)
tongue = block(-3.35, 3.2, 1.28, 3.35, -2.9, 1.98)
fingers = [
    paint(block(x - 0.12, 2.0, z, x + 0.12, -2.6, z + 0.03), GOLD, "finger")
    for x in [(n - 5.5) * 0.5 for n in range(12)]
    for z in (1.25, 1.98)
]
feet = [
    paint(block(s * 4.2, y - 0.5, -1.0, s * 4.47, y + 0.5, 1.8), METAL, "foot") for s in (-1, 1) for y in (3.13, -1.05)
]
write("USB-C_HRO_TYPE-C-31-M-12", [paint(tube, METAL, "shell"), paint(tongue, BLACK, "tongue"), *fingers, *feet])

base = block(-2.55, 2.55, 0.1, 2.55, -2.55, 0.9)
cover = fillet(block(-2.45, 2.45, 0.9, 2.45, -2.45, 1.1).edges().filter_by(Axis.Z), 0.3)
plunger = Location((0, 0, 1.1)) * Cylinder(1.0, 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
tabs = [
    paint(block(s * 2.5, y - 0.35, 0.0, s * 3.3, y + 0.35, 0.15), METAL, "tab") for s in (-1, 1) for y in (1.88, -1.88)
]
write(
    "Button_TS-1187A",
    [paint(base, BLACK, "base"), paint(cover, METAL, "cover"), paint(plunger, BLACK, "plunger"), *tabs],
)
print("wrote the STEP models")
