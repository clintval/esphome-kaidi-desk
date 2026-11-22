"""Draw the PCB with PcbDraw (resistors only, assembled and underside) and raytrace both sides with KiCad.

Run with: python scripts/render_art.py
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/kaidi-desk.kicad_pcb"
VALUES = "R1:1k,R2:1k,R3:10k,R4:10k,R5:10k,R6:100k,R7:10k,R8:15k,R9:10k,R10:15k"
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


pcbdraw(ROOT / "docs/board-resistors.svg", "--filter", RESISTORS)
pcbdraw(ROOT / "docs/board-back.svg", "--side", "back")


def render(out, side, rotate, zoom, *lights):
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
            "--side",
            side,
            "--rotate",
            rotate,
            "--zoom",
            zoom,
            "--background",
            "transparent",
            *lights,
            "-o",
            str(out),
            str(PCB),
        ],
        check=True,
        capture_output=True,
    )


FLAT_LIGHTS = ("--light-camera", "0.9", "--light-bottom", "0.6", "--light-side", "0.5")
render(ROOT / "docs/board-3d-top.png", "top", "-12,0,-6", "1.3", *FLAT_LIGHTS)
render(ROOT / "docs/board-3d-bottom.png", "bottom", "-12,0,-6", "1.3", *FLAT_LIGHTS)
print("rendered the board art and its 3D renders into docs/")
