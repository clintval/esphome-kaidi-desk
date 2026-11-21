"""Model the rev 4 protoboard in KiCad, draw it with PcbDraw and label it.

Run with: python scripts/render_protoboard.py
"""

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KPY = os.environ["KICAD_PYTHON"]
proto = ROOT / "hardware/proto"
values = subprocess.run([KPY, str(ROOT / "scripts/make_protoboard.py"), str(proto)], check=True,
                        capture_output=True, text=True).stdout.strip().splitlines()[-1]
with tempfile.TemporaryDirectory() as tmp:
    drawing = Path(tmp) / "protoboard.svg"
    subprocess.run([KPY, "-m", "pcbdraw.ui", "plot", "--style", str(proto / "eplzon.json"),
                    "--libs", f"{proto / 'art'},KiCAD-base", "--resistor-values", values,
                    str(proto / "protoboard.kicad_pcb"), str(drawing)],
                   check=True, capture_output=True, env=dict(os.environ, PYTHONPATH=os.environ["KICAD_SITE"]))
    subprocess.run(["python", str(ROOT / "scripts/annotate_protoboard.py"), str(drawing), str(ROOT / "docs/protoboard.svg")],
                   check=True)
print("rendered docs/protoboard.svg")
