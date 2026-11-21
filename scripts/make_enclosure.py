"""Build a two-part 3D-printable box around the dongle PCB from hardware/board.json.

The base holds the board on four posts (two with M3 heat-set inserts) and has openings for the keypad
jack on one end, the desk jack on the other and the USB-C port on the top side. The lid screws down through two bosses that clamp the board. Nothing
metal sits near the C3's antenna: the screws are at the far corners. Models are written in KiCad's
3D frame (origin at the board's top-left, Y up, Z = 0 on the board's top face) so they drop straight
into KiCad renders.

Run with: uv run --no-project --python 3.12 --with build123d python scripts/make_enclosure.py hardware
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
    Location,
    Locations,
    Mode,
    Plane,
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
TOP = geo["tallest"] + 1.0
Z_FLOOR = -(T + STANDOFF + FLOOR)
IW, IH = W + 2 * GAP, H + 2 * GAP
OW, OH = IW + 2 * WALL, IH + 2 * WALL
CX, CY = W / 2, -H / 2


def kx(x):
    return x - X0


def ky(y):
    return -(y - Y0)


with BuildPart() as base:
    with BuildSketch(Plane.XY.offset(Z_FLOOR)):
        with Locations((CX, CY)):
            RectangleRounded(OW, OH, R + GAP + WALL)
    extrude(amount=TOP - Z_FLOOR)
    with BuildSketch(Plane.XY.offset(Z_FLOOR + FLOOR)):
        with Locations((CX, CY)):
            RectangleRounded(IW, IH, R + GAP)
    extrude(amount=TOP - Z_FLOOR, mode=Mode.SUBTRACT)

    posts = [(kx(x), ky(y)) for x, y in geo["mounting_holes"]]
    holes = [(kx(x), ky(y)) for x, y in geo["screw_holes"]]
    for x, y in posts:
        with Locations(Location((x, y, Z_FLOOR + FLOOR))):
            Cylinder(3.25, STANDOFF, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x, y in holes:
        with Locations(Location((x, y, -T))):
            Cylinder(2.1, 5.5, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)

    for jack in geo["jacks"]:
        wall_x = -(GAP + WALL / 2) if jack["side"] == "left" else W + GAP + WALL / 2
        y_mid = (ky(jack["y1"]) + ky(jack["y2"])) / 2
        with Locations(Location((wall_x, y_mid, (TOP - 0.2) / 2 - 0.1))):
            Box(WALL + 2, abs(jack["y2"] - jack["y1"]) + 0.8, TOP + 0.2, mode=Mode.SUBTRACT)

    usb = geo["usb"]
    with BuildSketch(Plane.XZ.offset(-(GAP + WALL + 1))):
        with Locations((kx(usb["center_x"]), usb["z"])):
            RectangleRounded(12.6, 7.0, 3.0)
    extrude(amount=WALL + 2, mode=Mode.SUBTRACT)

    for ex in (14.0, W - 14.0):
        ey = -(H + GAP + WALL + 5.0)
        with Locations(Location((ex, ey, Z_FLOOR))):
            Box(14.0, 12.0, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations(Location((ex, ey - 1.0, Z_FLOOR))):
            Cylinder(2.3, 10, mode=Mode.SUBTRACT)

with BuildPart() as lid:
    with BuildSketch(Plane.XY.offset(TOP)):
        with Locations((CX, CY)):
            RectangleRounded(OW, OH, R + GAP + WALL)
    extrude(amount=LID)
    for x, y in holes:
        with Locations(Location((x, y, TOP))):
            Cylinder(3.25, TOP - 0.2, align=(Align.CENTER, Align.CENTER, Align.MAX))
        with Locations(Location((x, y, TOP + LID))):
            Cylinder(1.7, TOP + LID, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
            Cylinder(3.0, 1.2, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
    with BuildSketch(Plane.XY.offset(TOP + LID - 0.5)):
        with Locations((CX, CY - 2.0)):
            Text("esphome-kaidi-desk", 5.0)
        with Locations((CX, CY - 9.0)):
            Text("Kaidi standing desk", 3.0)
        with Locations((5.5, CY)):
            Text("KEYPAD", 2.8, rotation=90)
        with Locations((W - 5.5, CY)):
            Text("DESK", 2.8, rotation=-90)
        with Locations((kx(usb["center_x"]), -4.0)):
            Text("USB-C", 2.6)
    extrude(amount=0.5, mode=Mode.SUBTRACT)

out = HW / "enclosure"
out.mkdir(exist_ok=True)
for name, part in (("base", base.part), ("lid", lid.part)):
    export_step(part, str(out / f"{name}.step"))
    export_stl(part, str(out / f"{name}.stl"))
size = base.part.bounding_box().size
print(f"base {size.X:.1f} x {size.Y:.1f} x {size.Z + LID:.1f} mm overall, inner height above the board {TOP:.1f} mm")
