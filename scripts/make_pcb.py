"""Place the dongle PCB from the schematic's netlist, using KiCad's own pcbnew API.

Run with KiCad's Python:
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/make_pcb.py hardware/kaidi-desk.kicad_sch hardware/kaidi-desk.kicad_pcb
"""

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew
from dimensions import (
    C3_LENGTH,
    C3_PIN1_INSET,
    C3_USB_OVERHANG,
    USBC_BREAKOUT_DEPTH,
    USBC_BREAKOUT_PIN_INSET,
    USBC_BREAKOUT_STANDOFF,
    USBC_BREAKOUT_THICKNESS,
    USBC_RECEPTACLE_HEIGHT,
)

FP = Path(os.environ.get("KICAD_SHARE", "/Applications/KiCad/KiCad.app/Contents/SharedSupport")) / "footprints"
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ROOT = Path(__file__).resolve().parent.parent
SCH, OUT = Path(sys.argv[1]), Path(sys.argv[2])

X0, Y0, W, H, RADIUS = 100.0, 100.0, 84.0, 50.0, 3.0
YC = Y0 + H / 2

with tempfile.TemporaryDirectory() as tmp:
    xml = Path(tmp) / "net.xml"
    subprocess.run(
        [str(CLI), "sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml), str(SCH)],
        check=True,
        capture_output=True,
    )
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
    if ref.startswith("J") or ref in ("C1", "C2", "C3"):
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
    for (ax, ay), (bx, by) in (
        ((x1 + r, y1), (x2 - r, y1)),
        ((x2, y1 + r), (x2, y2 - r)),
        ((x2 - r, y2), (x1 + r, y2)),
        ((x1, y2 - r), (x1, y1 + r)),
    ):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(mm(ax, ay))
        s.SetEnd(mm(bx, by))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)
    k = r * (1 - 2**-0.5)
    for (sx, sy), (mx, my), (ex, ey) in (
        ((x1, y1 + r), (x1 + k, y1 + k), (x1 + r, y1)),
        ((x2 - r, y1), (x2 - k, y1 + k), (x2, y1 + r)),
        ((x2, y2 - r), (x2 - k, y2 - k), (x2 - r, y2)),
        ((x1 + r, y2), (x1 + k, y2 - k), (x1, y2 - r)),
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
JACKS = (("J1", X0 + 13.97, YC - 5.715, -90, "left"), ("J2", X0 + W - 13.97, YC + 5.715, 90, "right"))
for ref, x, y, angle, _ in JACKS:
    fp = place(jack_lib, "RJ50_Amphenol_54602-910_Horizontal", ref, x, y, angle=angle)
    model(fp, f"{models}/RJ50_Amphenol_54602-910_Horizontal.wrl")
silk("KEYPAD", X0 + 8.9, YC - 9.6, 1.4, bold=True)
silk("DESK", X0 + W - 8.9, YC - 9.6, 1.4, bold=True)

U1_X, U1_Y = X0 + W / 2 - 7.62, Y0 + C3_PIN1_INSET + C3_USB_OVERHANG
fp = place(jack_lib, "ESP32-C3_SuperMini", "U1", U1_X, U1_Y, angle=0)
fp.Reference().SetVisible(False)
model(fp, f"{models}/ESP32-C3_SuperMini.wrl")

dip = FP / "Package_DIP.pretty"
socket = place(dip, "DIP-14_W7.62mm_Socket", "U2", X0 + 21.5, Y0 + 5.5)
# The socket footprint only models the empty socket, so seat the chip in it for the renders.
model(socket, "${KICAD10_3DMODEL_DIR}/Package_DIP.3dshapes/DIP-14_W7.62mm.step", (0, 0, 2.6))
cap = place(FP / "Capacitor_THT.pretty", "C_Disc_D3.0mm_W1.6mm_P2.50mm", "C1", X0 + 24.0, Y0 + 2.2)
dip_ref = next(f for f in board.GetFootprints() if f.GetReference() == "U2").Reference()
dip_ref.SetVisible(False)
for cap_pad in cap.Pads():
    cap_pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

res = FP / "Resistor_THT.pretty"
axial = "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
right = [("R3", 0), ("R4", 1), ("R5", 2), ("R6", 3), ("R7", 4), ("R8", 5), ("R9", 6), ("R10", 7)]
placements = [(ref, X0 + 54.5, Y0 + 3.0 + i * 3.4, 0) for ref, i in right]
placements += [("R1", X0 + 65.5, Y0 + 10.0, 0), ("R2", X0 + 65.5, Y0 + 13.4, 0)]
for ref, x, y, a in placements:
    place(res, axial, ref, x, y, a)

HOLES = [(X0 + 3.6, Y0 + 3.6), (X0 + W - 3.6, Y0 + 3.6), (X0 + 3.6, Y0 + H - 3.6), (X0 + W - 3.6, Y0 + H - 3.6)]
for x, y in HOLES:
    place(FP / "MountingHole.pretty", "MountingHole_3.2mm_M3", "", x, y, value="M3")

USB_X, USB_Y = X0 + W / 2 - 2.5 * 2.54, Y0 + H - USBC_BREAKOUT_DEPTH + USBC_BREAKOUT_PIN_INSET
fp = place(jack_lib, "USB-C_Breakout_Cermant_1x06", "J3", USB_X, USB_Y)
model(fp, f"{models}/USB-C_Breakout_Cermant_1x06.wrl")
U3_X, U3_Y = USB_X - 6.15, Y0 + H - 2.5
fp = place(jack_lib, "Converter_DCDC_Mornsun_B_S-2WR3_SIP", "U3", U3_X, U3_Y, angle=180)
model(fp, f"{models}/Converter_DCDC_Mornsun_B_S-2WR3_SIP.wrl")
caps = FP / "Capacitor_THT.pretty"
C3_X, C3_Y = U3_X - 2.5, USB_Y - 0.5
place(caps, "CP_Radial_D5.0mm_P2.00mm", "C3", C3_X, C3_Y)
place(caps, "CP_Radial_D6.3mm_P2.50mm", "C2", X0 + 5.5, USB_Y - 0.1)
place(FP / "Diode_THT.pretty", "D_DO-41_SOD81_P5.08mm_Vertical_AnodeUp", "D1", X0 + 13.5, USB_Y - 1.6)
silk("USB-C power in", USB_X + 11.85, USB_Y - 3.5, 0.9)
silk("esphome-kaidi-desk", X0 + 56.0, USB_Y + 1.9, 1.6, bold=True, left=True)
silk("Kaidi KDDY094 dongle", X0 + 56.0, USB_Y + 4.3, 1.0, left=True)


def u1_point(lx, ly):
    return U1_X + lx, U1_Y + ly


def polygon(zone, points):
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))


C3_END = C3_LENGTH - C3_PIN1_INSET
ANTENNA = (-3.4, 16.0, 18.64, C3_END + 3.0)
SLOT = (1.9, 15.2, 13.34, C3_END + 0.6)
ax1, ay1, ax2, ay2 = ANTENNA
keepout = pcbnew.ZONE(board)
keepout.SetIsRuleArea(True)
layers = pcbnew.LSET()
layers.AddLayer(pcbnew.F_Cu)
layers.AddLayer(pcbnew.B_Cu)
keepout.SetLayerSet(layers)
keepout.SetDoNotAllowTracks(True)
keepout.SetDoNotAllowVias(True)
keepout.SetDoNotAllowZoneFills(True)
keepout.SetDoNotAllowPads(False)
keepout.SetDoNotAllowFootprints(False)
keepout.SetZoneName("ANTENNA_KEEPOUT")
polygon(keepout, [u1_point(x, y) for x, y in ((ax1, ay1), (ax2, ay1), (ax2, ay2), (ax1, ay2))])
board.Add(keepout)
sx1, sy1, sx2, sy2 = SLOT
corners = [u1_point(x, y) for x, y in ((sx1, sy1), (sx2, sy1), (sx2, sy2), (sx1, sy2))]
for (cx1, cy1), (cx2, cy2) in zip(corners, corners[1:] + corners[:1]):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(mm(cx1, cy1))
    s.SetEnd(mm(cx2, cy2))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    board.Add(s)
silk("antenna keep-out", (corners[0][0] + corners[2][0]) / 2, U1_Y + ANTENNA[3] + 0.9, 0.9)

# The charger side (J3, C3 and U3 pins 1-2) gets no ground pour, a moat no other trace can cross,
# and nothing bridges the converter's barrier.
ISLAND = (U3_X - 5.1, C3_Y - 4.3, USB_X + 17.6, Y0 + H)
BARRIER = (U3_X - 6.6, U3_Y - 6.3, U3_X - 3.6, Y0 + H)


def rule_area(name, rect, tracks):
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetLayerSet(layers)
    zone.SetDoNotAllowTracks(tracks)
    zone.SetDoNotAllowVias(tracks)
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetZoneName(name)
    x1, y1, x2, y2 = rect
    polygon(zone, ((x1, y1), (x2, y1), (x2, y2), (x1, y2)))
    board.Add(zone)


rule_area("ISOLATED_INPUT", ISLAND, tracks=False)
rule_area("ISOLATION_BARRIER", BARRIER, tracks=True)
ix1, iy1, ix2, iy2 = ISLAND
for band in ((ix1, iy1, ix2, iy1 + 1.0), (ix1, iy1, ix1 + 1.0, iy2), (ix2 - 1.0, iy1, ix2, iy2)):
    rule_area("ISOLATION_MOAT", band, tracks=True)

inset = 0.65
for x1, y1, x2, y2 in (
    (X0, Y0, X0 + W, Y0 + inset),
    (X0, Y0 + H - inset, X0 + W, Y0 + H),
    (X0, Y0, X0 + inset, Y0 + H),
    (X0 + W - inset, Y0, X0 + W, Y0 + H),
):
    band = pcbnew.ZONE(board)
    band.SetIsRuleArea(True)
    band.SetLayerSet(layers)
    band.SetDoNotAllowTracks(True)
    band.SetDoNotAllowVias(True)
    band.SetDoNotAllowZoneFills(False)
    band.SetDoNotAllowPads(False)
    band.SetDoNotAllowFootprints(False)
    band.SetZoneName("EDGE_CLEARANCE")
    polygon(band, ((x1, y1), (x2, y1), (x2, y2), (x1, y2)))
    board.Add(band)

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net("GND"))
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetThermalReliefGap(pcbnew.FromMM(0.3))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    outline = z.Outline()
    outline.NewOutline()
    for x, y in ((X0, Y0), (X0 + W, Y0), (X0 + W, Y0 + H), (X0, Y0 + H)):
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)

missing = sorted(
    {f"{r}.{p}" for (r, p) in pad_net}
    - {f"{fp.GetReference()}.{pad.GetNumber()}" for fp in board.GetFootprints() for pad in fp.Pads()}
)
assert not missing, f"netlist pads with no footprint pad: {missing}"
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(str(OUT))

# Ground pads are routed with real traces, so a single thermal spoke into a pour is enough.
project = OUT.with_suffix(".kicad_pro")
config = json.loads(project.read_text()) if project.exists() else {}
rules = config.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
rules["min_resolved_spokes"] = 1
project.write_text(json.dumps(config, indent=2) + "\n")

geometry = {
    "board": {"x": X0, "y": Y0, "w": W, "h": H, "radius": RADIUS, "thickness": 1.6},
    "mounting_holes": [list(h) for h in HOLES],
    "screw_holes": [list(HOLES[0]), list(HOLES[3])],
    "jacks": [
        {"ref": ref, "side": side, "y1": YC - 7.65, "y2": YC + 7.65, "height": 13.0} for ref, _, _, _, side in JACKS
    ],
    "usb": {
        "side": "bottom",
        "center_x": USB_X + 2.5 * 2.54,
        "z": USBC_BREAKOUT_STANDOFF + USBC_BREAKOUT_THICKNESS + USBC_RECEPTACLE_HEIGHT / 2,
    },
    "island": list(ISLAND),
    "antenna": [list(u1_point(x, y)) for x, y in ((ax1, ay1), (ax2, ay2))],
    "tallest": 13.0,
}
(OUT.parent / "board.json").write_text(json.dumps(geometry, indent=2) + "\n")
print("placed", len(board.GetFootprints()), "footprints,", len(nets), "nets")
