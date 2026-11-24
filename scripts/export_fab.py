"""Export Gerbers, drill files, and the assembly parts list and positions for a board house.

Run with: python scripts/export_fab.py
"""

import csv
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from parts import PARTS

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/kaidi-desk.kicad_pcb"
CLI = os.environ["KICAD_CLI"]
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

with tempfile.TemporaryDirectory() as tmp:
    for kind in (("gerbers", "--layers", LAYERS), ("drill",)):
        subprocess.run([CLI, "pcb", "export", *kind, "-o", f"{tmp}/", str(PCB)], check=True, capture_output=True)
    with zipfile.ZipFile(ROOT / "hardware/kaidi-desk-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(tmp).iterdir()):
            archive.write(path, path.name)
    positions = Path(tmp) / "positions.csv"
    subprocess.run(
        [CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "-o", str(positions), str(PCB)],
        check=True,
        capture_output=True,
    )
    rows = {row["Ref"]: row for row in csv.DictReader(positions.open())}

centers = json.loads((ROOT / "hardware/board.json").read_text())["centers"]
fitted = {ref: lcsc for refs, (_, lcsc) in PARTS.items() for ref in refs.split()}
missing = {ref for ref in rows if ref not in fitted and not ref.startswith(("TP", "REF"))}
assert not missing, f"parts with no LCSC number: {sorted(missing)}"
assert not set(fitted) - set(rows), f"parts not on the board: {sorted(set(fitted) - set(rows))}"

with (ROOT / "hardware/kaidi-desk-bom.csv").open("w", newline="") as out:
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for refs, (comment, lcsc) in PARTS.items():
        names = refs.split()
        writer.writerow([comment, ",".join(names), rows[names[0]]["Package"], lcsc])
with (ROOT / "hardware/kaidi-desk-positions.csv").open("w", newline="") as out:
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for ref in sorted(fitted):
        x, y = centers[ref]
        writer.writerow([ref, f"{x:.3f}mm", f"{-y:.3f}mm", "Top", rows[ref]["Rot"]])
print("wrote the Gerber zip, the parts list and the positions into hardware/")
