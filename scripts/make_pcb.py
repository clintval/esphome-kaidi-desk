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
from dimensions import JACK_OVERHANG

FP = Path(os.environ.get("KICAD_SHARE", "/Applications/KiCad/KiCad.app/Contents/SharedSupport")) / "footprints"
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
ROOT = Path(__file__).resolve().parent.parent
SCH, OUT = Path(sys.argv[1]), Path(sys.argv[2])

X0, Y0, W, H, RADIUS = 100.0, 100.0, 84.0, 50.0, 3.0
YC = Y0 + H / 2
ESP_X, ESP_Y = X0 + 42.0, Y0 + 13.1
POWER = ("+5V", "/ESP_5V", "/3V3", "/VOUT", "/VBUS", "/VIN_ISO", "/DESK_SW", "/DESK_FUSED", "/DESK_LIM")
NOTCH = (ESP_X - 14.2, ESP_X + 14.2, Y0 + 5.6)

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
board.SetCopperLayerCount(4)
COPPER = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
settings = board.GetDesignSettings()
settings.m_TrackMinWidth = pcbnew.FromMM(0.15)
settings.m_MinClearance = pcbnew.FromMM(0.15)
settings.m_ViasMinSize = pcbnew.FromMM(0.5)
settings.m_MinThroughDrill = pcbnew.FromMM(0.3)
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
    fp.Reference().SetVisible(False)
    if not ref:
        fp.SetBoardOnly(True)
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
    nx1, nx2, ny = NOTCH[0], NOTCH[1], NOTCH[2]
    for (ax, ay), (bx, by) in (
        ((x1 + r, y1), (nx1, y1)),
        ((nx1, y1), (nx1, ny)),
        ((nx1, ny), (nx2, ny)),
        ((nx2, ny), (nx2, y1)),
        ((nx2, y1), (x2 - r, y1)),
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
JACK_INSET = 16.77 - JACK_OVERHANG
JACKS = (("J1", X0 + JACK_INSET, YC, -90, "left"), ("J2", X0 + W - JACK_INSET, YC, 90, "right"))
for ref, x, y, angle, _ in JACKS:
    fp = place(jack_lib, "RJ50_TE_5558067-1_Horizontal", ref, x, y, angle=angle)
    model(fp, f"{models}/RJ50_TE_5558067-1_Horizontal.step")
silk("KEYPAD", X0 + 8.9, YC - 9.6, 1.4, bold=True)
silk("DESK", X0 + W - 8.9, YC - 9.6, 1.4, bold=True)


R0603, R1206 = ("Resistor_SMD", "R_0603_1608Metric"), ("Resistor_SMD", "R_1206_3216Metric")
C0603, C0805 = ("Capacitor_SMD", "C_0603_1608Metric"), ("Capacitor_SMD", "C_0805_2012Metric")
C1206, FUSE = ("Capacitor_SMD", "C_1206_3216Metric"), ("Fuse", "Fuse_1206_3216Metric")
SMA, SOT6 = ("Diode_SMD", "D_SMA"), ("Package_TO_SOT_SMD", "SOT-23-6")
BUTTON = ("Button_Switch_SMD", "SW_Push_1P1T_XKB_TS-1187A")
MODELS = {
    "U3": "Converter_DCDC_Mornsun_B_S-2WR3_SIP",
    "J3": "USB-C_HRO_TYPE-C-31-M-12",
    "SW1": "Button_TS-1187A",
    "SW2": "Button_TS-1187A",
}
PLACEMENTS = {
    "U1": (("RF_Module", "ESP32-C3-WROOM-02"), 42.0, 13.1, 0),
    "R21": (R0603, 30.3, 8.2, 90),
    "C8": (C0603, 28.0, 8.2, 90),
    "C7": (C0603, 30.3, 12.0, 90),
    "C12": (C0805, 27.6, 12.2, 90),
    "SW1": (BUTTON, 20.5, 7.8, 0),
    "R24": (R0603, 53.7, 10.6, 0),
    "R23": (R0603, 30.3, 18.4, 90),
    "R22": (R0603, 28.0, 18.4, 90),
    "SW2": (BUTTON, 20.5, 13.6, 0),
    "R25": (R0603, 12.6, 4.0, 0),
    "D3": (("LED_SMD", "LED_0603_1608Metric"), 9.2, 4.0, 0),
    "U4": (("Package_TO_SOT_SMD", "SOT-23-5"), 25.4, 26.8, 0),
    "C5": (C0805, 21.2, 27.4, 90),
    "C6": (C0805, 29.4, 27.4, 90),
    "U6": (SOT6, 21.7, 20.6, 0),
    "R1": (R0603, 25.6, 19.4, 90),
    "R2": (R0603, 25.6, 23.0, 90),
    "R9": (R0603, 22.5, 17.5, 0),
    "R10": (R0603, 28.0, 23.0, 90),
    "U2": (("Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm"), 58.2, 24.6, 0),
    "C1": (C0603, 60.6, 18.0, 0),
    "R12": (R0603, 63.6, 22.4, 90),
    "R13": (R0603, 63.6, 26.0, 90),
    "U5": (SOT6, 62.9, 31.6, 90),
    "R3": (R0603, 53.0, 23.4, 90),
    "R4": (R0603, 53.0, 27.0, 90),
    "R5": (R0603, 50.8, 23.4, 90),
    "R6": (R0603, 50.8, 27.0, 90),
    "R7": (R0603, 60.6, 15.6, 0),
    "R8": (R0603, 60.6, 13.4, 0),
    "JP1": (("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical"), 62.4, 36.6, 0),
    "F1": (FUSE, 63.0, 43.2, 90),
    "R11": (R1206, 63.0, 47.8, 0),
    "D2": (SMA, 70.5, 47.4, 0),
    "C4": (("Capacitor_SMD", "CP_Elec_10x10.5"), 71.2, 39.2, 0),
    "U7": (("Package_SO", "SOIC-16W_7.5x10.3mm_P1.27mm"), 39.5, 33.0, 90),
    "C11": (C0603, 32.2, 28.0, 90),
    "R19": (R0603, 46.6, 24.8, 90),
    "R20": (R0603, 44.4, 24.8, 90),
    "J3": (("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12"), 51.2, 46.35, 0),
    "R15": (R0603, 50.4, 38.0, 90),
    "R16": (R0603, 53.4, 38.0, 90),
    "F2": (FUSE, 36.0, 47.6, 0),
    "C3": (C0805, 30.0, 39.6, 90),
    "D4": (SMA, 37.1, 44.0, 180),
    "U8": (SOT6, 42.6, 45.6, 90),
    "R17": (R0603, 41.6, 41.4, 90),
    "R18": (R0603, 43.8, 41.4, 90),
    "C9": (C0603, 33.2, 38.2, 90),
    "C10": (C0603, 37.6, 41.0, 0),
    "U3": (("kaidi", "Converter_DCDC_Mornsun_B_S-2WR3_SIP"), 24.65, 47.5, 180),
    "C2": (C1206, 18.6, 38.0, 90),
    "R14": (R1206, 14.6, 38.0, 90),
    "D1": (SMA, 9.0, 38.4, 90),
    "TP1": (None, 72.0, 9.8, 0),
    "TP2": (None, 75.2, 9.8, 0),
    "TP3": (None, 68.8, 9.8, 0),
    "TP4": (None, 13.4, 9.6, 0),
    "TP5": (None, 62.4, 9.8, 0),
    "TP6": (None, 65.6, 9.8, 0),
    "TP7": (None, 47.4, 38.2, 0),
    "TP8": (None, 56.0, 39.0, 0),
}
for ref, (footprint, x, y, angle) in PLACEMENTS.items():
    lib, name = footprint or ("TestPoint", "TestPoint_Pad_D1.5mm")
    fp = place(jack_lib if lib == "kaidi" else FP / f"{lib}.pretty", name, ref, X0 + x, Y0 + y, angle)
    if ref == "U1":
        for pad in fp.Pads():
            if 0 < pad.GetDrillSize().x < pcbnew.FromMM(0.3):
                pad.SetDrillSize(mm(0.3, 0.3))
                pad.SetSize(mm(0.6, 0.6))
    if ref in MODELS:
        fp.Models().clear()
        model(fp, f"{models}/{MODELS[ref]}.step")

HOLES = [(X0 + 3.6, Y0 + 3.6), (X0 + W - 3.6, Y0 + 3.6), (X0 + 3.6, Y0 + H - 3.6), (X0 + W - 3.6, Y0 + H - 3.6)]
for x, y in HOLES:
    place(FP / "MountingHole.pretty", "MountingHole_3.2mm_M3", "", x, y, value="M3")

silk("DESK PWR", X0 + 62.6, Y0 + 34.4, 0.7)
silk("RESET", X0 + 20.5, Y0 + 4.2, 0.9)
silk("BOOT", X0 + 14.6, Y0 + 13.6, 0.8)
silk("STATUS", X0 + 9.2, Y0 + 5.8, 0.9)
silk("USB-C, isolated", X0 + 51.0, Y0 + 40.4, 0.7)
silk("esphome-kaidi-desk", X0 + 57.6, Y0 + 3.4, 1.2, bold=True, left=True)
silk("Kaidi KDDY094 dongle", X0 + 57.6, Y0 + 5.4, 0.9, left=True)
for ref, label in zip(("TP1", "TP2", "TP3", "TP5", "TP6"), ("5V", "GND", "ESP5V", "TX", "RX")):
    at = PLACEMENTS[ref]
    silk(label, X0 + at[1], Y0 + at[2] - 1.5, 0.7)
silk("3V3", X0 + 13.4, Y0 + 11.1, 0.7)


def polygon(zone, points):
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))


def rect_points(rect):
    x1, y1, x2, y2 = rect
    return ((x1, y1), (x2, y1), (x2, y2), (x1, y2))


layers = pcbnew.LSET()
for layer in COPPER:
    layers.AddLayer(layer)


def rule_area(name, rect, tracks=True, fills=True, on=layers):
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetLayerSet(on)
    zone.SetDoNotAllowTracks(tracks)
    zone.SetDoNotAllowVias(tracks)
    zone.SetDoNotAllowZoneFills(fills)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetZoneName(name)
    polygon(zone, rect_points(rect))
    board.Add(zone)


# The USB side is walled in by the board edge and these moats, which no copper crosses on any layer.
bottom = Y0 + H
ISLAND = (X0 + 27.4, Y0 + 35.4, X0 + 57.2, bottom)
ix1, iy1, ix2, iy2 = ISLAND
for moat in (
    (X0 + 24.4, Y0 + 30.6, ix2 + 3.0, iy1),
    (X0 + 24.4, iy1, ix1, bottom),
    (ix2, iy1, ix2 + 3.0, bottom),
):
    rule_area("ISOLATION_MOAT", moat)

# The jacks' grounded shells rest on the board, so no signal runs under them on the top layer.
top = pcbnew.LSET()
top.AddLayer(pcbnew.F_Cu)
for x1, x2 in ((X0, X0 + 18.4), (X0 + W - 18.4, X0 + W)):
    rule_area("JACK_SHELL", (x1, YC - 8.0, x2, YC + 8.0), fills=False, on=top)

inset = 0.65
for band in (
    (X0, Y0, X0 + W, Y0 + inset),
    (X0, bottom - inset, X0 + W, bottom),
    (X0, Y0, X0 + inset, bottom),
    (X0 + W - inset, Y0, X0 + W, bottom),
    (NOTCH[0] - inset, Y0, NOTCH[1] + inset, NOTCH[2] + inset),
):
    rule_area("EDGE_CLEARANCE", band, fills=False)

for name, rect, priority in (("GND", (X0, Y0, X0 + W, bottom), 0), ("/GND_ISO", ISLAND, 1)):
    for layer in COPPER:
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net(name))
        z.SetAssignedPriority(priority)
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetThermalReliefGap(pcbnew.FromMM(0.3))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        polygon(z, rect_points(rect))
        board.Add(z)

missing = sorted(
    {f"{r}.{p}" for (r, p) in pad_net}
    - {f"{fp.GetReference()}.{pad.GetNumber()}" for fp in board.GetFootprints() for pad in fp.Pads()}
)
assert not missing, f"netlist pads with no footprint pad: {missing}"
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(str(OUT))

project = OUT.with_suffix(".kicad_pro")
config = json.loads(project.read_text()) if project.exists() else {}
rules = config.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
rules |= {
    "min_resolved_spokes": 1,
    "min_clearance": 0.15,
    "min_copper_edge_clearance": 0.4,
    "min_track_width": 0.15,
    "min_via_diameter": 0.5,
    "min_through_hole_diameter": 0.3,
}
classes = config.setdefault("net_settings", {})
signal = dict(classes["classes"][0], name="Default", track_width=0.2, clearance=0.15, via_diameter=0.55, via_drill=0.3)
power = dict(signal, name="Power", track_width=0.4, priority=0)
classes["classes"] = [signal, power]
classes["netclass_patterns"] = [{"netclass": "Power", "pattern": name} for name in POWER]
project.write_text(json.dumps(config, indent=2) + "\n")

centers = {}
for fp in board.GetFootprints():
    pads = [pad.GetPosition() for pad in fp.Pads() if pad.GetNumber()]
    if pads:
        centers[fp.GetReference()] = [
            round(pcbnew.ToMM(min(axis) + max(axis)) / 2, 3) for axis in ([p.x for p in pads], [p.y for p in pads])
        ]

geometry = {
    "centers": centers,
    "board": {"x": X0, "y": Y0, "w": W, "h": H, "radius": RADIUS, "thickness": 1.6},
    "mounting_holes": [list(h) for h in HOLES],
    "screw_holes": [list(HOLES[0]), list(HOLES[3])],
    "jacks": [
        {"ref": ref, "side": side, "y1": YC - 7.935, "y2": YC + 7.935, "height": 13.7} for ref, _, _, _, side in JACKS
    ],
    "usb": {"side": "bottom", "center_x": X0 + PLACEMENTS["J3"][1], "z": 1.63},
    "island": list(ISLAND),
    "tallest": 13.7,
}
(OUT.parent / "board.json").write_text(json.dumps(geometry, indent=2) + "\n")
print("placed", len(board.GetFootprints()), "footprints,", len(nets), "nets")
