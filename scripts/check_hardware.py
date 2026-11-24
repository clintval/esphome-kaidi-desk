"""Check the hardware: KiCad ERC and DRC, schematic parity, the netlist, the isolated input, and the protoboard layout.

Run with: python scripts/check_hardware.py
"""

import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = os.environ["KICAD_CLI"]
SCH, PCB = ROOT / "hardware/kaidi-desk.kicad_sch", ROOT / "hardware/kaidi-desk.kicad_pcb"
EXPECTED = {
    "+5V": "C1.1 C13.1 C14.1 J1.2 J2.2 JP1.1 R26.1 TP1.1 U2.12 U2.14 U2.5 U2.9 U5.5 U6.5 U9.5",
    "GND": "C1.2 C11.2 C12.2 C13.2 C14.2 C2.2 C4.2 C5.2 C6.2 C7.2 C8.2 D3.1 J1.3 J1.SH J2.3 J2.SH R10.2 R14.2 R3.2 R4.2 R5.2 R6.2 R8.2 "
    "Q1.2 R27.2 SW1.2 SW2.2 TP2.1 U1.19 U1.9 U2.7 U3.4 U4.2 U5.2 U6.2 U7.15 U7.9 U9.3",
    "/3V3": "C11.1 C12.1 C6.1 C7.1 R21.1 R22.1 R23.1 R24.1 TP4.1 U1.1 U4.5 U7.12 U7.13 U7.14 U7.16",
    "/CC1": "J3.A5 R15.1",
    "/CC2": "J3.B5 R16.1",
    "/CMD_DESK": "J2.7 R1.2 R12.2 U5.1",
    "/CMD_DRV": "R12.1 U2.3",
    "/CMD_KEYPAD": "J1.7 JP2.1 R9.1 U6.1 U9.1",
    "/CMD_SW": "JP2.2 R1.1 U9.2",
    "/DDM": "R19.1 U7.11",
    "/DDP": "R20.1 U7.10",
    "/DESK_FUSED": "F1.2 R11.1",
    "/DESK_LIM": "D2.2 R11.2",
    "/DESK_SW": "F1.1 JP1.2",
    "/EN": "C8.1 R21.2 SW1.1 U1.2",
    "/EN_TX": "R5.1 U1.5 U2.10",
    "/EN_WAKE": "R6.1 U1.10 U2.13",
    "/ESP_5V": "C4.1 C5.1 D1.1 D2.1 TP3.1 U4.1 U4.3",
    "/GND_ISO": "C10.2 C3.2 C9.2 D4.2 J3.A1 J3.A12 J3.B1 J3.B12 J3.SH R15.2 R16.2 TP8.1 U3.2 U7.2 U7.8 U8.2",
    "/HEIGHT": "J1.8 J2.8 R7.1 U5.4 U6.4",
    "/IO2": "R24.2 U1.16",
    "/IO8": "R23.2 U1.7",
    "/IO9": "R22.2 SW2.1 U1.8",
    "/KP_OFF": "Q1.1 R27.1 U1.17",
    "/KP_ON": "Q1.3 R26.2 U9.4",
    "/LED": "R25.1 U1.4",
    "/LED_A": "D3.2 R25.2",
    "/OE_TX": "R3.1 U2.1 U2.8",
    "/OE_WAKE": "R4.1 U2.11 U2.4",
    "/RX": "R7.2 R8.1 TP6.1 U1.3",
    "/SENSE": "R10.1 R9.2 U1.15",
    "/THRU_1": "J1.1 J2.1",
    "/THRU_4": "J1.4 J2.4",
    "/THRU_5": "J1.5 J2.5",
    "/THRU_6": "J1.6 J2.6",
    "/THRU_9": "J1.9 J2.9",
    "/TX": "TP5.1 U1.6 U2.2",
    "/UDM": "R17.2 U7.6",
    "/UDP": "R18.2 U7.7",
    "/USBC_DM": "J3.A7 J3.B7 R17.1 U8.3 U8.4",
    "/USBC_DP": "J3.A6 J3.B6 R18.1 U8.1 U8.6",
    "/USB_DM": "R19.2 U1.13",
    "/USB_DP": "R20.2 U1.14",
    "/VBUS": "F2.1 J3.A4 J3.A9 J3.B4 J3.B9 U8.5",
    "/VDD1": "C10.1 U7.3 U7.4 U7.5",
    "/VIN_ISO": "C3.1 C9.1 D4.1 F2.2 TP7.1 U3.1 U7.1",
    "/VOUT": "C2.1 D1.2 R14.1 U3.6",
    "/WAKE_DESK": "J2.10 R13.2 R2.2 U5.3",
    "/WAKE_DRV": "R13.1 U2.6",
    "/WAKE_KEYPAD": "J1.10 R2.1 U6.3",
}
EXPECTED = {name: set(pads.split()) for name, pads in EXPECTED.items()}
ISOLATED = {"/VIN_ISO", "/GND_ISO", "/VBUS", "/VDD1", "/CC1", "/CC2", "/UDM", "/UDP", "/USBC_DM", "/USBC_DP"}
BARRIER_PARTS = {"U3", "U7"}
MIN_BARRIER = 3.0
failures = []

with tempfile.TemporaryDirectory() as tmp:
    erc = subprocess.run(
        [CLI, "sch", "erc", "--severity-error", "--exit-code-violations", "-o", f"{tmp}/erc.rpt", str(SCH)],
        capture_output=True,
        text=True,
        check=False,
    )
    if erc.returncode:
        failures.append("ERC errors:\n" + Path(f"{tmp}/erc.rpt").read_text())
    drc = subprocess.run(
        [
            CLI,
            "pcb",
            "drc",
            "--severity-error",
            "--schematic-parity",
            "--exit-code-violations",
            "-o",
            f"{tmp}/drc.rpt",
            str(PCB),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if drc.returncode:
        failures.append("DRC errors:\n" + Path(f"{tmp}/drc.rpt").read_text())
    subprocess.run(
        [CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", f"{tmp}/net.xml", str(SCH)],
        check=True,
        capture_output=True,
    )
    nets = {
        n.get("name"): {f"{x.get('ref')}.{x.get('pin')}" for x in n.iter("node")}
        for n in ET.parse(f"{tmp}/net.xml").getroot().iter("net")
    }
nets = {k: v for k, v in nets.items() if len(v) > 1}
for name, want in EXPECTED.items():
    if nets.get(name) != want:
        failures.append(f"net {name}: want {sorted(want)}, got {sorted(nets.get(name, []))}")
for extra in set(nets) - set(EXPECTED):
    failures.append(f"unexpected net {extra}: {sorted(nets[extra])}")

desk_parts = {pad.split(".")[0] for name, pads in nets.items() if name not in ISOLATED for pad in pads}
usb_parts = {pad.split(".")[0] for name in ISOLATED for pad in nets.get(name, set())}
if desk_parts & usb_parts != BARRIER_PARTS:
    failures.append(f"parts joining the USB side to the desk: {sorted(desk_parts & usb_parts)}")

x1, y1, x2, y2 = json.loads((ROOT / "hardware/board.json").read_text())["island"]


def inside(x, y):
    return x1 <= x <= x2 and y1 <= y <= y2


board = PCB.read_text()
for kind, body in re.findall(r"\((segment|via)\b([\s\S]*?)\(uuid", board):
    net = re.search(r'\(net "([^"]*)"\)', body).group(1)
    if kind == "via":
        x, y = map(float, re.search(r"\(at ([-\d.]+) ([-\d.]+)\)", body).groups())
        points = [(x, y)]
    else:
        ax, ay = map(float, re.search(r"\(start ([-\d.]+) ([-\d.]+)\)", body).groups())
        bx, by = map(float, re.search(r"\(end ([-\d.]+) ([-\d.]+)\)", body).groups())
        steps = max(1, math.ceil(math.hypot(bx - ax, by - ay) / 0.5))
        points = [(ax + (bx - ax) * i / steps, ay + (by - ay) * i / steps) for i in range(steps + 1)]
    if net in ISOLATED and not all(inside(x, y) for x, y in points):
        failures.append(f"isolated net {net} leaves the input island near {points[0]}")
    if net not in ISOLATED and any(inside(x, y) for x, y in points):
        failures.append(f"{kind} of {net} crosses the isolated input island near {points[0]}")

moats = re.findall(r'\(name "ISOLATION_MOAT"\)[\s\S]*?\(polygon\s*\(pts([\s\S]*?)\)\s*\)\s*\)', board)
for moat in moats:
    points = [tuple(map(float, xy)) for xy in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", moat)]
    sides = [max(p[i] for p in points) - min(p[i] for p in points) for i in (0, 1)]
    if min(sides) < MIN_BARRIER - 0.01:
        failures.append(f"an isolation moat is only {min(sides):.1f} mm wide")
if len(moats) != 3:
    failures.append(f"want 3 isolation moats, got {len(moats)}")

proto = subprocess.run(["python", str(ROOT / "scripts/protoboard.py")], capture_output=True, text=True, check=False)
if proto.returncode:
    failures.append("protoboard layout:\n" + proto.stderr)

if failures:
    sys.exit("\n\n".join(failures))
print("ERC, DRC, schematic parity, netlist, isolated input and protoboard layout all pass")
