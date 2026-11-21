"""Draw the PCB with PcbDraw (fully assembled and resistors only) and raytrace it with KiCad.

Run with: python scripts/render_art.py
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/kaidi-desk.kicad_pcb"
VALUES = "R1:1k,R2:1k,R3:10k,R4:10k,R5:100k,R6:100k,R7:10k,R8:15k,R9:10k,R10:15k"
RESISTORS = ",".join(f"R{i}" for i in range(1, 11))


def pcbdraw(out, *extra):
    env = dict(os.environ, PYTHONPATH=os.environ["KICAD_SITE"])
    subprocess.run(
        [
            os.environ["KICAD_PYTHON"],
            "-m",
            "pcbdraw.ui",
            "plot",
            "--style",
            "set-blue-enig",
            "--libs",
            f"{ROOT / 'hardware/pcbdraw'},KiCAD-base",
            "--resistor-values",
            VALUES,
            *extra,
            str(PCB),
            str(out),
        ],
        check=True,
        env=env,
        capture_output=True,
    )


pcbdraw(ROOT / "docs/board.svg")
pcbdraw(ROOT / "docs/board-resistors.svg", "--filter", RESISTORS)
subprocess.run(
    [
        os.environ["KICAD_CLI"],
        "pcb",
        "render",
        "-w",
        "1800",
        "-h",
        "1100",
        "--quality",
        "high",
        "--perspective",
        "--floor",
        "--rotate",
        "-40,0,25",
        "--zoom",
        "1.05",
        "--background",
        "transparent",
        "-o",
        str(ROOT / "docs/board-3d.png"),
        str(PCB),
    ],
    check=True,
    capture_output=True,
)
print("rendered docs/board.svg, docs/board-resistors.svg and docs/board-3d.png")
