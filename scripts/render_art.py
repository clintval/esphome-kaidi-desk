"""Raytrace both sides of the PCB with KiCad.

Run with: python scripts/render_art.py
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/kaidi-desk.kicad_pcb"


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
render(ROOT / "docs/board-3d-top.png", "top", "-12,0,-6", "1.0", *FLAT_LIGHTS)
render(ROOT / "docs/board-3d-bottom.png", "bottom", "-12,0,-6", "1.0", *FLAT_LIGHTS)
print("rendered the board art and its 3D renders into docs/")
