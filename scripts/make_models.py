"""Write simple VRML 3D models for the RJ50 jack, the B0505S, the USB-C receptacle and the buttons, for KiCad's 3D renders.

Coordinates are in footprint millimetres (x right, y down the footprint, z up) and are converted to
KiCad's VRML units (2.54 mm, y flipped). Run with: python3 scripts/make_models.py hardware/kaidi.3dshapes
"""

import sys
from pathlib import Path

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
U = 2.54


def box(x1, y1, z1, x2, y2, z2, color, shine=0.2, transparency=0.0):
    cx, cy, cz = (x1 + x2) / 2 / U, -(y1 + y2) / 2 / U, (z1 + z2) / 2 / U
    sx, sy, sz = abs(x2 - x1) / U, abs(y2 - y1) / U, abs(z2 - z1) / U
    r, g, b = color
    return (
        f"Transform {{ translation {cx:.4f} {cy:.4f} {cz:.4f} children [ Shape {{ appearance Appearance {{ material "
        f"Material {{ diffuseColor {r} {g} {b} specularColor {shine} {shine} {shine} shininess {shine} "
        f"transparency {transparency} }} }} geometry Box {{ size {sx:.4f} {sy:.4f} {sz:.4f} }} }} ] }}\n"
    )


def write(name, parts):
    (OUT / name).write_text("#VRML V2.0 utf8\n" + "".join(parts))


BLACK, GOLD, SILVER = (0.06, 0.06, 0.07), (0.85, 0.65, 0.2), (0.78, 0.8, 0.82)
JACK, OPENING = (0.42, 0.44, 0.47), (0.12, 0.13, 0.14)
pitch = 1.27
cx = 9 * pitch / 2
jack = [box(cx - 7.65, -3.77, 0, cx + 7.65, 13.97, 12.7, JACK, 0.15)]
jack.append(box(cx - 6.03, 12.0, 3.2, cx + 6.03, 14.02, 10.05, OPENING, 0.05))
jack.append(box(cx - 1.6, 12.0, 1.5, cx + 1.6, 14.03, 3.2, OPENING, 0.05))
for n in range(10):
    x = cx - 6.03 + 0.9 + n * 1.02
    jack.append(box(x - 0.2, 10.5, 8.6, x + 0.2, 13.9, 9.4, GOLD, 0.6))
write("RJ50_Amphenol_54602-910_Horizontal.wrl", jack)

z0 = B0505S_STANDOFF
converter = [
    box(
        -B0505S_PIN1_INSET,
        -B0505S_PIN_ROW_INSET,
        z0,
        B0505S_LENGTH - B0505S_PIN1_INSET,
        B0505S_THICKNESS - B0505S_PIN_ROW_INSET,
        z0 + B0505S_HEIGHT,
        BLACK,
        0.2,
    )
]
for x in (0.0, 2.54, 7.62, 12.7):
    converter.append(box(x - 0.25, -0.25, -1.5, x + 0.25, 0.25, z0 + 0.5, SILVER, 0.6))
write("Converter_DCDC_Mornsun_B_S-2WR3_SIP.wrl", converter)

usb = [box(-4.47, -3.65, 0, 4.47, 3.65, 3.26, SILVER, 0.8), box(-3.6, 3.5, 0.9, 3.6, 3.67, 2.3, BLACK, 0.1)]
write("USB-C_HRO_TYPE-C-31-M-12.wrl", usb)
button = [box(-2.55, -2.55, 0, 2.55, 2.55, 1.0, SILVER, 0.6), box(-1.2, -1.2, 1.0, 1.2, 1.2, 1.5, BLACK, 0.2)]
write("Button_TS-1187A.wrl", button)
