"""Write simple VRML 3D models for the RJ50 jack and the ESP32-C3 SuperMini, for KiCad's 3D renders.

Coordinates are in footprint millimetres (x right, y down the footprint, z up) and are converted to
KiCad's VRML units (2.54 mm, y flipped). Run with: python3 scripts/make_models.py hardware/kaidi.3dshapes
"""

import sys
from pathlib import Path

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


BLACK, DARK, GOLD, SILVER = (0.06, 0.06, 0.07), (0.02, 0.02, 0.025), (0.85, 0.65, 0.2), (0.78, 0.8, 0.82)
pitch = 1.27
cx = 9 * pitch / 2
jack = [box(cx - 7.65, -3.77, 0, cx + 7.65, 13.97, 12.7, BLACK, 0.1)]
jack.append(box(cx - 6.03, 12.0, 3.2, cx + 6.03, 14.02, 10.05, DARK, 0.05))
jack.append(box(cx - 1.6, 12.0, 1.5, cx + 1.6, 14.03, 3.2, DARK, 0.05))
for n in range(10):
    x = cx - 6.03 + 0.9 + n * 1.02
    jack.append(box(x - 0.2, 10.5, 8.6, x + 0.2, 13.9, 9.4, GOLD, 0.6))
write("RJ50_Amphenol_54602-910_Horizontal.wrl", jack)

z0 = 0.2
blue = (0.05, 0.12, 0.28)
module = [box(-1.38, -3.6, z0, 16.62, 18.92, z0 + 1.0, blue, 0.3)]
module.append(box(3.12, -6.9, z0 + 1.0, 12.12, 0.4, z0 + 4.2, SILVER, 0.8))
module.append(box(5.12, 6.0, z0 + 1.0, 10.12, 11.0, z0 + 1.9, BLACK, 0.3))
module.append(box(4.62, 14.4, z0 + 1.0, 10.62, 17.4, z0 + 2.2, (0.92, 0.9, 0.86), 0.2))
for x in (1.2, 12.4):
    module.append(box(x, 1.4, z0 + 1.0, x + 2.6, 4.2, z0 + 2.4, (0.7, 0.7, 0.7), 0.4))
    module.append(box(x + 0.6, 2.0, z0 + 2.4, x + 2.0, 3.6, z0 + 2.9, BLACK, 0.2))
for x in (0.0, 15.24):
    for i in range(8):
        module.append(box(x - 0.32, i * 2.54 - 0.32, 0.0, x + 0.32, i * 2.54 + 0.32, z0 + 1.8, GOLD, 0.6))
        module.append(box(x - 0.75, i * 2.54 - 0.75, z0 + 1.0, x + 0.75, i * 2.54 + 0.75, z0 + 1.25, GOLD, 0.7))
write("ESP32-C3_SuperMini.wrl", module)
