"""Export Gerbers and drill files and zip them for a board house.

Run with: python scripts/export_fab.py
"""

import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/kaidi-desk.kicad_pcb"

with tempfile.TemporaryDirectory() as tmp:
    for kind in ("gerbers", "drill"):
        subprocess.run([os.environ["KICAD_CLI"], "pcb", "export", kind, "-o", f"{tmp}/", str(PCB)],
                       check=True, capture_output=True)
    with zipfile.ZipFile(ROOT / "hardware/kaidi-desk-gerbers.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(tmp).iterdir()):
            archive.write(path, path.name)
print("wrote hardware/kaidi-desk-gerbers.zip")
