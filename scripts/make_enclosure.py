"""Build a two-part 3D-printable box around the dongle PCB from hardware/board.json.

The base holds the board on four posts (two with M3 heat-set inserts) and has openings for the keypad
jack on one end, the desk jack on the other and the USB-C power input on the bottom side. The C3's own
USB-C gets no opening: it is only for the first flash, with the board out of the box. The lid screws down
through two bosses that clamp the board and is engraved KEYPAD and DESK at the matching ends, with
chevrons between them. Nothing metal sits near the C3's antenna: the screws are at the far corners.
Models are written in KiCad's 3D frame (origin at the board's top-left, Y up, Z = 0 on the board's
top face) so they drop straight into KiCad renders.

Run with: python scripts/make_enclosure.py hardware
"""

import json
import sys
from pathlib import Path

from build123d import (
    Align,
    Box,
    BuildPart,
    BuildSketch,
    Cylinder,
    FontStyle,
    Location,
    Locations,
    Mode,
    Plane,
    Polygon,
    RectangleRounded,
    Text,
    export_step,
    export_stl,
    extrude,
)

HW = Path(sys.argv[1])
geo = json.loads((HW / "board.json").read_text())
b = geo["board"]
X0, Y0, W, H, R, T = b["x"], b["y"], b["w"], b["h"], b["radius"], b["thickness"]

GAP, WALL, FLOOR, STANDOFF, LID = 0.5, 2.2, 2.0, 4.0, 2.0
INSERT_HOLE, INSERT_LENGTH = 4.0, 5.7
SCREW_CLEARANCE, HEAD_DIAMETER, HEAD_HEIGHT, SCREW_LENGTH = 3.4, 5.5, 3.0, 20.0
BOSS = 3.8
TOP = geo["tallest"] + 1.0
CHEVRONS = (W / 2 - 9.0, W / 2 + 9.0)
LABEL_INSET, LABEL_SIZE = 12.0, 5.5
Z_FLOOR = -(T + STANDOFF + FLOOR)
IW, IH = W + 2 * GAP, H + 2 * GAP
OW, OH = IW + 2 * WALL, IH + 2 * WALL
CX, CY = W / 2, -H / 2


def kx(x):
    return x - X0


def ky(y):
    return -(y - Y0)


with BuildPart() as base:
    with BuildSketch(Plane.XY.offset(Z_FLOOR)), Locations((CX, CY)):
        RectangleRounded(OW, OH, R + GAP + WALL)
    extrude(amount=TOP - Z_FLOOR)
    with BuildSketch(Plane.XY.offset(Z_FLOOR + FLOOR)), Locations((CX, CY)):
        RectangleRounded(IW, IH, R + GAP)
    extrude(amount=TOP - Z_FLOOR, mode=Mode.SUBTRACT)

    posts = [(kx(x), ky(y)) for x, y in geo["mounting_holes"]]
    holes = [(kx(x), ky(y)) for x, y in geo["screw_holes"]]
    for x, y in posts:
        with Locations(Location((x, y, Z_FLOOR + FLOOR))):
            Cylinder(4.0, STANDOFF, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x, y in holes:
        with Locations(Location((x, y, -T))):
            Cylinder(
                INSERT_HOLE / 2, STANDOFF + FLOOR, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT
            )

    for jack in geo["jacks"]:
        wall_x = -(GAP + WALL / 2) if jack["side"] == "left" else W + GAP + WALL / 2
        y_mid = (ky(jack["y1"]) + ky(jack["y2"])) / 2
        with Locations(Location((wall_x, y_mid, (TOP + 0.7) / 2))):
            Box(WALL + 2, abs(jack["y2"] - jack["y1"]) + 0.8, TOP + 1.3, mode=Mode.SUBTRACT)

    usb = geo["usb"]
    start = -(GAP + WALL + 1) if usb["side"] == "top" else H - 0.5
    depth = WALL + 2 if usb["side"] == "top" else GAP + WALL + 1.5
    with BuildSketch(Plane.XZ.offset(start)), Locations((kx(usb["center_x"]), usb["z"])):
        RectangleRounded(13.4, 7.6, 3.2)
    extrude(amount=depth, mode=Mode.SUBTRACT)


with BuildPart() as lid:
    with BuildSketch(Plane.XY.offset(TOP)), Locations((CX, CY)):
        RectangleRounded(OW, OH, R + GAP + WALL)
    extrude(amount=LID)
    for x, y in holes:
        with Locations(Location((x, y, TOP))):
            Cylinder(BOSS, TOP - 0.2, align=(Align.CENTER, Align.CENTER, Align.MAX))
        with Locations(Location((x, y, TOP + LID))):
            Cylinder(SCREW_CLEARANCE / 2, TOP + LID, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
            Cylinder(
                HEAD_DIAMETER / 2 + 0.25,
                HEAD_HEIGHT + 0.05,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            )
    with BuildSketch(Plane.XY.offset(TOP + LID - 1.0)):
        with Locations(*[(x, CY) for x in CHEVRONS]):
            Polygon((-6.0, 8.0), (-1.0, 8.0), (7.0, 0.0), (-1.0, -8.0), (-6.0, -8.0), (2.0, 0.0))
        with Locations((LABEL_INSET, CY)):
            Text("KEYPAD", LABEL_SIZE, font_style=FontStyle.BOLD)
        with Locations((W - LABEL_INSET, CY)):
            Text("DESK", LABEL_SIZE, font_style=FontStyle.BOLD)
    extrude(amount=1.0, mode=Mode.SUBTRACT)

out = HW / "enclosure"
out.mkdir(exist_ok=True)
for name, part in (("base", base.part), ("lid", lid.part)):
    export_step(part, str(out / f"{name}.step"))
    export_stl(part, str(out / f"{name}.stl"))
seat = TOP + LID - HEAD_HEIGHT - 0.05
tip = seat - SCREW_LENGTH
engagement = -T - tip
assert INSERT_LENGTH <= STANDOFF + FLOOR, "the insert must fit inside its post"
assert 3.0 <= engagement <= INSERT_LENGTH, f"an M3 x {SCREW_LENGTH:g} screw engages {engagement:.1f} mm of the insert"
print(f"M3 x {SCREW_LENGTH:g} mm socket-head cap screws engage {engagement:.1f} mm of the {INSERT_LENGTH} mm inserts")
size = base.part.bounding_box().size
print(f"base {size.X:.1f} x {size.Y:.1f} x {size.Z + LID:.1f} mm overall, inner height above the board {TOP:.1f} mm")
