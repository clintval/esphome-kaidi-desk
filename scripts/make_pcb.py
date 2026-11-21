"""Place the rev 5 dongle PCB from the schematic's netlist, using KiCad's own pcbnew API.

Run with KiCad's Python:
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/make_pcb.py hardware/kaidi-desk.kicad_sch hardware/kaidi-desk.kicad_pcb
"""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

KICAD = Path("/Applications/KiCad/KiCad.app/Contents")
FP = KICAD / "SharedSupport/footprints"
CLI = KICAD / "MacOS/kicad-cli"
ROOT = Path(__file__).resolve().parent.parent
SCH, OUT = Path(sys.argv[1]), Path(sys.argv[2])

X0, Y0, W, H, RADIUS = 100.0, 100.0, 72.0, 46.0, 3.0

with tempfile.TemporaryDirectory() as tmp:
    xml = Path(tmp) / "net.xml"
    subprocess.run([str(CLI), "sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml), str(SCH)],
                   check=True, capture_output=True)
    root = ET.parse(xml).getroot()
pad_net = {}
for net in root.iter("net"):
    name = net.get("name")
    for node in net.iter("node"):
        pad_net[(node.get("ref"), node.get("pin"))] = name
values = {c.get("ref"): c.findtext("value") for c in root.iter("comp")}

board = pcbnew.CreateEmptyBoard()
board.SetCopperLayerCount(2)
settings = board.GetDesignSettings()
settings.m_TrackMinWidth = pcbnew.FromMM(0.25)
settings.m_CopperEdgeClearance = pcbnew.FromMM(0.4)
nets = {}


def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def net(name):
    if name not in nets:
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    return nets[name]


def place(lib, name, ref, x, y, angle=0, value=None):
    fp = pcbnew.FootprintLoad(str(lib), name)
    fp.SetFPID(pcbnew.LIB_ID("kaidi" if "kaidi" in str(lib) else Path(lib).stem, name))
    fp.SetReference(ref)
    fp.SetValue(value or values.get(ref, name))
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(angle)
    board.Add(fp)
    if ref.startswith("R"):
        pads = list(fp.Pads())
        mid = (pads[0].GetPosition() + pads[1].GetPosition()) / 2
        fp.Reference().SetPosition(pcbnew.VECTOR2I(int(mid.x), int(mid.y)))
        fp.Reference().SetTextSize(mm(0.8, 0.8))
        fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))
    if ref.startswith("J"):
        fp.Reference().SetVisible(False)
    if not ref:
        fp.SetBoardOnly(True)
        fp.Reference().SetVisible(False)
    for pad in fp.Pads():
        number = pad.GetNumber()
        if (ref, number) in pad_net:
            pad.SetNet(net(pad_net[(ref, number)]))
    return fp


def model(fp, path, offset=(0, 0, 0)):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(*offset)
    fp.Models().push_back(m)


def edge_outline():
    x1, y1, x2, y2, r = X0, Y0, X0 + W, Y0 + H, RADIUS
    for (ax, ay), (bx, by) in (((x1 + r, y1), (x2 - r, y1)), ((x2, y1 + r), (x2, y2 - r)),
                               ((x2 - r, y2), (x1 + r, y2)), ((x1, y2 - r), (x1, y1 + r))):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(mm(ax, ay))
        s.SetEnd(mm(bx, by))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)
    k = r * (1 - 2 ** -0.5)
    for (sx, sy), (mx, my), (ex, ey) in (
        ((x1, y1 + r), (x1 + k, y1 + k), (x1 + r, y1)), ((x2 - r, y1), (x2 - k, y1 + k), (x2, y1 + r)),
        ((x2, y2 - r), (x2 - k, y2 - k), (x2 - r, y2)), ((x1 + r, y2), (x1 + k, y2 - k), (x1, y2 - r)),
    ):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(mm(sx, sy), mm(mx, my), mm(ex, ey))
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(pcbnew.FromMM(0.1))
        board.Add(a)


def silk(text, x, y, size=1.2, layer=pcbnew.F_SilkS, bold=False, left=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    if left:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    t.SetPosition(mm(x, y))
    t.SetLayer(layer)
    t.SetTextSize(mm(size, size))
    t.SetTextThickness(pcbnew.FromMM(size * (0.2 if bold else 0.15)))
    board.Add(t)


edge_outline()
bottom = Y0 + H

jack_lib = ROOT / "hardware/kaidi.pretty"
models = "${KIPRJMOD}/kaidi.3dshapes"
for ref, x in (("J1", 103.5), ("J2", 120.0)):
    fp = place(jack_lib, "RJ50_Amphenol_54602-910_Horizontal", ref, x, bottom - 13.97)
    model(fp, f"{models}/RJ50_Amphenol_54602-910_Horizontal.wrl")
silk("KEYPAD", 109.2, bottom - 19.2, 1.4, bold=True)
silk("DESK", 125.7, bottom - 19.2, 1.4, bold=True)

fp = place(jack_lib, "ESP32-C3_SuperMini_Socket", "U1", X0 + W - 6.9, 104.0, angle=-90)
fp.Reference().SetVisible(False)
model(fp, f"{models}/ESP32-C3_SuperMini.wrl")
silk("USB-C", X0 + W - 4.0, 123.4, 1.0)

dip = FP / "Package_DIP.pretty"
place(dip, "DIP-14_W7.62mm_Socket", "U2", 139.0, 105.5, angle=-90)
place(FP / "Capacitor_THT.pretty", "C_Disc_D3.0mm_W1.6mm_P2.50mm", "C1", 143.0, 109.5, angle=-90)

res = FP / "Resistor_THT.pretty"
axial = "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
for ref, x, y, a in (("R1", 103.5, 121.0, 0), ("R2", 120.0, 121.0, 0),
                     ("R3", 110.0, 103.5, 0), ("R4", 110.0, 107.0, 0), ("R5", 110.0, 110.5, 0), ("R6", 110.0, 114.0, 0),
                     ("R7", 140.0, 123.5, -90), ("R8", 144.0, 123.5, -90), ("R9", 148.0, 123.5, -90), ("R10", 152.0, 123.5, -90)):
    place(res, axial, ref, x, y, a)

for x, y in ((X0 + 3.6, Y0 + 3.6), (X0 + W - 3.6, Y0 + H - 3.6)):
    place(FP / "MountingHole.pretty", "MountingHole_3.2mm_M3", "", x, y, value="M3")

silk("esphome-kaidi-desk", 140.0, 136.0, 1.6, bold=True, left=True)
silk("Kaidi KDDY094 dongle  rev 5", 140.0, 138.5, 1.0, left=True)

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net("GND"))
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetThermalReliefGap(pcbnew.FromMM(0.3))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    outline = z.Outline()
    outline.NewOutline()
    for x, y in ((X0, Y0), (X0 + W, Y0), (X0 + W, Y0 + H), (X0, Y0 + H)):
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)

missing = sorted({f"{r}.{p}" for (r, p) in pad_net} - {f"{fp.GetReference()}.{pad.GetNumber()}" for fp in board.GetFootprints() for pad in fp.Pads()})
assert not missing, f"netlist pads with no footprint pad: {missing}"
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(str(OUT))
print("placed", len(board.GetFootprints()), "footprints,", len(nets), "nets")
