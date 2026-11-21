"""Check the hardware: KiCad ERC and DRC, schematic parity, the netlist against the design, and the protoboard layout.

Run with: python scripts/check_hardware.py
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = os.environ["KICAD_CLI"]
SCH, PCB = ROOT / "hardware/kaidi-desk.kicad_sch", ROOT / "hardware/kaidi-desk.kicad_pcb"
EXPECTED = {
    "+5V": {"J1.2", "J2.2", "U2.14", "U2.5", "U2.9", "U2.12", "C1.1"},
    "GND": {"J1.3", "J2.3", "U1.2", "U2.7", "C1.2", "R3.2", "R4.2", "R5.2", "R6.2", "R8.2", "R10.2"},
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
}
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

proto = subprocess.run(["python", str(ROOT / "scripts/protoboard.py")], capture_output=True, text=True, check=False)
if proto.returncode:
    failures.append("protoboard layout:\n" + proto.stderr)

if failures:
    sys.exit("\n\n".join(failures))
print("ERC, DRC, schematic parity, netlist and protoboard layout all pass")
