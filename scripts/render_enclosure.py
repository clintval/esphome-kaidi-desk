"""Render the dongle PCB inside its box with KiCad's raytracer, plus the bare board from the closed box's camera.

Run with KiCad's Python: $KPY scripts/render_enclosure.py hardware docs
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

HW, DOCS = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
VIEWS = {
    "enclosure-open": {"lid_z": 28.0, "rotate": "-55,0,-20", "zoom": "0.66"},
    "enclosure-closed": {"lid_z": 0.0, "rotate": "-58,0,40", "zoom": "0.82"},
    "enclosure-usb": {"lid_z": 0.0, "rotate": "-60,0,20", "zoom": "0.85"},
    "board-3d": {"lid_z": None, "rotate": "-58,0,40", "zoom": "0.82"},
}

for name, view in VIEWS.items():
    board = pcbnew.LoadBoard(str(HW / "kaidi-desk.kicad_pcb"))
    fp = pcbnew.FOOTPRINT(board)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100), pcbnew.FromMM(100)))
    parts = () if view["lid_z"] is None else (("base", 0.0), ("lid", view["lid_z"]))
    for part, z in parts:
        model = pcbnew.FP_3DMODEL()
        model.m_Filename = str(HW / "enclosure" / f"{part}.step")
        model.m_Offset = pcbnew.VECTOR3D(0, 0, z)
        fp.Models().push_back(model)
    board.Add(fp)
    with tempfile.TemporaryDirectory() as tmp:
        pcb = Path(tmp) / "render.kicad_pcb"
        board.Save(str(pcb))
        for asset in ("kaidi.3dshapes",):
            (Path(tmp) / asset).symlink_to(HW / asset)
        subprocess.run(
            [
                CLI,
                "pcb",
                "render",
                "-w",
                "1800",
                "-h",
                "1150",
                "--quality",
                "high",
                "--perspective",
                "--floor",
                "--background",
                "transparent",
                "--rotate",
                view["rotate"],
                "--zoom",
                view["zoom"],
                "-o",
                str(DOCS / f"{name}.png"),
                str(pcb),
            ],
            check=True,
            capture_output=True,
        )
    print("rendered", name)
