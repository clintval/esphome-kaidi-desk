"""Model the rev 4 protoboard build in KiCad, from the layout checked in scripts/protoboard.py.

The EPLZON 1.5 x 2 in board is drawn landscape: rows 1-17 run left to right, columns A-E sit
below the center gap and F-J above it. Run with KiCad's Python:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/make_protoboard.py hardware/proto
"""

import itertools
import os
import sys
import uuid
from pathlib import Path

import pcbnew

sys.path.insert(0, str(Path(__file__).resolve().parent))
from protoboard import C3_TOP, COLUMNS, PARTS, U2_PINS, WIRES  # noqa: E402

OUT = Path(sys.argv[1])
LIB = OUT / "proto.pretty"
ART = OUT / "art/proto"
LIB.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)
KICAD_FP = Path(os.environ.get("KICAD_SHARE", "/Applications/KiCad/KiCad.app/Contents/SharedSupport")) / "footprints"
P = 2.54
BX, BY, BW, BH = 100.0, 100.0, 50.8, 38.1


def hole(name):
    k, row = COLUMNS.index(name[0]), int(name[1:])
    x = BX + 5.08 + (row - 1) * P
    y = BY + 5.08 + (9 - k) * P + (5.08 if k <= 4 else 0.0)
    return round(x, 3), round(y, 3)


IDS = itertools.count()


def u():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kaidi-desk/protoboard/{next(IDS)}"))


def pad(num, x, y, size=1.6, drill=0.9, shape="circle"):
    kind = "np_thru_hole" if num == "" else "thru_hole"
    return f'(pad "{num}" {kind} {shape} (at {x} {y}) (size {size} {size}) (drill {drill}) (layers "*.Cu" "*.Mask") (uuid "{u()}"))'


def write_fp(name, body):
    (LIB / f"{name}.kicad_mod").write_text(
        f'(footprint "{name}" (version 20240108) (generator "make_protoboard") (layer "F.Cu") (attr through_hole) '
        f'(property "Reference" "REF**" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{u()}") (effects (font (size 1 1)))) '
        f'(property "Value" "{name}" (at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{u()}") (effects (font (size 1 1)))) {body})\n')


def write_art(name, box, defs, body):
    x, y, w, h = box
    (ART / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{w}mm" height="{h}mm" viewBox="{x} {y} {w} {h}">'
        f'<defs>{defs}</defs>{body}<rect id="origin" x="0" y="0" width="1" height="1" fill="#ff0000"/></svg>\n')


def lin(id_, stops, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>'


ax, ay = hole("A1")
grid = "".join(pad("", round(hole(f"{c}{r}")[0] - ax, 3), round(hole(f"{c}{r}")[1] - ay, 3)) for c in COLUMNS for r in range(1, 18))
write_fp("EPLZON_Mini_17x10", grid)

C3_LEFT, C3_RIGHT = C3_TOP["C"], C3_TOP["G"]
pins = "".join(pad(str(i + 1), 15.24, i * P, 1.7, 1.0) + pad(str(i + 9), 0, i * P, 1.7, 1.0) for i in range(8))
write_fp("ESP32-C3_SuperMini_LabelsUp", pins)
defs = (lin("pcb", [(0, "#2a5bd7"), (0.5, "#1c45b0"), (1, "#122f7a")], 1, 1)
        + lin("silver", [(0, "#ffffff"), (0.45, "#c9d0d6"), (1, "#7d868f")])
        + lin("gold", [(0, "#ffe7a3"), (0.5, "#d9a441"), (1, "#a0742a")]))
art = '<rect x="-0.6" y="-2.7" width="18.04" height="22.52" rx="1" opacity="0.35" fill="#000"/>'
art += '<rect x="-1.4" y="-3.6" width="18.04" height="22.52" rx="1" fill="url(#pcb)" stroke="#0b1d4d" stroke-width="0.15"/>'
art += '<rect x="3.12" y="-6.9" width="9" height="4.6" rx="1.4" fill="url(#silver)" stroke="#6f7780" stroke-width="0.12"/>'
art += '<rect x="4.32" y="-3.2" width="6.6" height="0.8" rx="0.4" fill="#5c646c"/>'
for i in range(8):
    for x in (0.0, 15.24):
        art += f'<circle cx="{x}" cy="{i * P}" r="0.85" fill="url(#gold)" stroke="#8a6420" stroke-width="0.08"/>'
        art += f'<circle cx="{x}" cy="{i * P}" r="0.36" fill="#c9b26a"/>'
    art += (f'<text x="13.7" y="{i * P + 0.38}" font-family="Helvetica, Arial" font-size="1.0" font-weight="700" '
            f'text-anchor="end" fill="#f4f7fb">{C3_RIGHT[i]}</text>')
    art += (f'<text x="1.55" y="{i * P + 0.38}" font-family="Helvetica, Arial" font-size="1.0" font-weight="700" '
            f'fill="#f4f7fb">{C3_LEFT[i]}</text>')
art += ('<text x="7.62" y="9.6" font-family="Helvetica, Arial" font-size="1.25" font-weight="800" text-anchor="middle" '
        'fill="#f4f7fb" transform="rotate(90 7.62 9.6)">ESP32-C3 SuperMini</text>')
art += '<text x="7.62" y="17.4" font-family="Helvetica, Arial" font-size="0.8" font-weight="600" text-anchor="middle" fill="#c9d6f2">labels up</text>'
write_art("ESP32-C3_SuperMini_LabelsUp", (-2.0, -7.4, 19.4, 27.2), defs, art)

C_ART = (lin("disc", [(0, "#f2b46b"), (0.6, "#d07a2c"), (1, "#8a4612")], 1, 1),
         '<ellipse cx="2.84" cy="0.25" rx="1.7" ry="0.95" opacity="0.35" fill="#000"/>'
         '<path d="M 0 0 L 1.2 0 M 3.88 0 L 5.08 0" stroke="#c9cdd2" stroke-width="0.5" stroke-linecap="round"/>'
         '<ellipse cx="2.54" cy="0" rx="1.65" ry="0.9" fill="url(#disc)" stroke="#6b360f" stroke-width="0.08"/>'
         '<text x="2.54" y="0.3" font-family="Helvetica, Arial" font-size="0.8" font-weight="700" text-anchor="middle" fill="#4a2208">104</text>')
write_fp("C_Disc_P5.08", pad("1", 0, 0) + pad("2", 5.08, 0))
write_art("C_Disc_P5.08", (-0.8, -1.4, 6.7, 2.9), *C_ART)

INSULATION = {"+5V": "#e5484d", "GND": "#2b2b2b", "TX": "#3b82f6", "EN_TX": "#a855f7", "OE_TX": "#ec4899",
              "EN_WAKE": "#a855f7", "OE_WAKE": "#ec4899"}

board = pcbnew.CreateEmptyBoard()


def place(lib, name, ref, at, angle=0, value=""):
    fp = pcbnew.FootprintLoad(str(lib), name)
    fp.SetFPID(pcbnew.LIB_ID(Path(lib).stem, name))
    fp.SetReference(ref)
    fp.SetValue(value or name)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(at[0]), pcbnew.FromMM(at[1])))
    fp.SetOrientationDegrees(angle)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    board.Add(fp)
    return fp


for i, (a, b, net, _, layer) in enumerate(WIRES):
    (x1, y1), (x2, y2) = hole(a), hole(b)
    dx, dy = round(x2 - x1, 3), round(y2 - y1, 3)
    name = f"Wire_{a}_{b}"
    write_fp(name, pad("1", 0, 0) + pad("2", dx, dy))
    path = f"M 0 0 L {dx} 0 L {dx} {dy}" if dx and dy else f"M 0 0 L {dx} {dy}"
    color = INSULATION[net]
    if layer == "back":
        body = "".join(f'<circle cx="{x}" cy="{y}" r="1.05" fill="none" stroke="{color}" stroke-width="0.35" '
                       f'stroke-dasharray="0.5 0.35"/>' for x, y in ((0, 0), (dx, dy)))
    else:
        body = (f'<path d="{path}" fill="none" stroke="#000" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round" '
                f'opacity="0.3" transform="translate(0.25 0.3)"/>'
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.05" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="{path}" fill="none" stroke="#ffffff" stroke-width="0.28" stroke-linecap="round" stroke-linejoin="round" '
                f'opacity="0.35" transform="translate(-0.12 -0.18)"/>')
    body += "".join(f'<circle cx="{x}" cy="{y}" r="0.42" fill="#d6d9dd" stroke="#8b9097" stroke-width="0.08"/>' for x, y in ((0, 0), (dx, dy)))
    lo_x, hi_x = min(0, dx), max(0, dx)
    lo_y, hi_y = min(0, dy), max(0, dy)
    write_art(name, (lo_x - 1.5, lo_y - 1.5, hi_x - lo_x + 3.2, hi_y - lo_y + 3.2), "", body)
    place(LIB, name, f"W{i + 1}", hole(a))

place(LIB, "EPLZON_Mini_17x10", "B1", hole("A1"))
place(LIB, "ESP32-C3_SuperMini_LabelsUp", "U1", hole("C1"), 90)
place(KICAD_FP / "Package_DIP.pretty", "DIP-14_W7.62mm", "U2", hole(U2_PINS[1]), 90, "74AHCT125")

res = KICAD_FP / "Resistor_THT.pretty"
pitch_fp = {7.62: "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
            10.16: "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
            15.24: "R_Axial_DIN0207_L6.3mm_D2.5mm_P15.24mm_Horizontal",
            2.54: "R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"}
values = {}
for ref, value, a, b, _ in PARTS:
    (x1, _), (x2, _) = hole(a), hole(b)
    span = round(abs(x2 - x1), 2)
    if ref.startswith("C"):
        place(LIB, "C_Disc_P5.08", ref, hole(a), 0, value)
        continue
    place(res, pitch_fp[span], ref, hole(a), 0, value)
    values[ref] = value

for x, y in ((BX + 2.2, BY + 2.2), (BX + BW - 2.2, BY + 2.2), (BX + 2.2, BY + BH - 2.2), (BX + BW - 2.2, BY + BH - 2.2)):
    place(KICAD_FP / "MountingHole.pretty", "MountingHole_2.2mm_M2", "", (x, y))
gap_y = (hole("E1")[1] + hole("F1")[1]) / 2
for row in (1, 17):
    place(KICAD_FP / "MountingHole.pretty", "MountingHole_3.2mm_M3", "", (hole(f"A{row}")[0], gap_y))


def silk(text, x, y, size=1.1):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.16))
    board.Add(t)


for c in COLUMNS:
    x0, y0 = hole(f"{c}1")
    silk(c, x0 - 2.6, y0)
    silk(c, hole(f"{c}17")[0] + 2.6, y0)
for r in range(1, 18):
    x0, _ = hole(f"A{r}")
    silk(str(r), x0, hole("J1")[1] - 2.4, 0.9)
    silk(str(r), x0, hole("A1")[1] + 2.4, 0.9)

for (sx, sy), (ex, ey) in (((BX, BY), (BX + BW, BY)), ((BX + BW, BY), (BX + BW, BY + BH)),
                           ((BX + BW, BY + BH), (BX, BY + BH)), ((BX, BY + BH), (BX, BY))):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(sx), pcbnew.FromMM(sy)))
    s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(ex), pcbnew.FromMM(ey)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    board.Add(s)

board.Save(str(OUT / "protoboard.kicad_pcb"))
print(",".join(f"{r}:{v}" for r, v in values.items()))
