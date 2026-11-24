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
    "+5V": {"J1.2", "J2.2", "U2.14", "U2.5", "U2.9", "U2.12", "C1.1", "JP1.1"},
    "GND": {
        "J1.3",
        "J2.3",
        "U1.2",
        "U2.7",
        "U3.4",
        "C1.2",
        "C2.2",
        "C4.2",
        "R3.2",
        "R4.2",
        "R5.2",
        "R6.2",
        "R8.2",
        "R10.2",
    },
    "/CMD_DESK": {"J2.7", "U2.3", "R1.2"},
    "/CMD_KEYPAD": {"J1.7", "R1.1", "R9.1"},
    "/WAKE_DESK": {"J2.10", "U2.6", "R2.2"},
    "/WAKE_KEYPAD": {"J1.10", "R2.1"},
    "/HEIGHT": {"J1.8", "J2.8", "R7.1"},
    "/RX": {"U1.4", "R7.2", "R8.1"},
    "/SENSE": {"U1.5", "R9.2", "R10.1"},
    "/TX": {"U1.11", "U2.2"},
    "/EN_TX": {"U1.10", "U2.10", "R5.1"},
    "/EN_WAKE": {"U1.14", "U2.13", "R6.1"},
    "/OE_TX": {"U2.1", "U2.8", "R3.1"},
    "/OE_WAKE": {"U2.4", "U2.11", "R4.1"},
    "/VIN_ISO": {"J3.1", "U3.1", "C3.1"},
    "/GND_ISO": {"J3.2", "U3.2", "C3.2"},
    "/VOUT": {"U3.6", "C2.1", "D1.2"},
    "/ESP_5V": {"D1.1", "D2.1", "C4.1", "U1.1"},
    "/DESK_SW": {"JP1.2", "R11.1"},
    "/DESK_LIM": {"R11.2", "D2.2"},
}
ISOLATED = {"/VIN_ISO", "/GND_ISO"}
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

desk = nets.get("GND", set()) | nets.get("+5V", set())
for name in ISOLATED:
    if nets.get(name, set()) & desk:
        failures.append(f"isolated net {name} shares pads with the desk side: {sorted(nets[name] & desk)}")

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

proto = subprocess.run(["python", str(ROOT / "scripts/protoboard.py")], capture_output=True, text=True, check=False)
if proto.returncode:
    failures.append("protoboard layout:\n" + proto.stderr)

if failures:
    sys.exit("\n\n".join(failures))
print("ERC, DRC, schematic parity, netlist, isolated input and protoboard layout all pass")
