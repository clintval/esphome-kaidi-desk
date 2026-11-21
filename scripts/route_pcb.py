"""Autoroute the placed board with Freerouting and pull the result back into KiCad.

Run with KiCad's Python:
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/route_pcb.py hardware/kaidi-desk.kicad_pcb FREEROUTING_JAR JAVA
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

PCB, JAR, JAVA = sys.argv[1], sys.argv[2], sys.argv[3]

board = pcbnew.LoadBoard(PCB)
netclass = board.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
netclass.SetTrackWidth(pcbnew.FromMM(0.4))
netclass.SetClearance(pcbnew.FromMM(0.25))
netclass.SetViaDiameter(pcbnew.FromMM(0.8))
netclass.SetViaDrill(pcbnew.FromMM(0.4))

with tempfile.TemporaryDirectory() as tmp:
    dsn, ses = Path(tmp) / "board.dsn", Path(tmp) / "board.ses"
    assert pcbnew.ExportSpecctraDSN(board, str(dsn)), "DSN export failed"
    subprocess.run([JAVA, "-Djava.awt.headless=true", "-jar", JAR, "--gui.enabled=false",
                    "-de", str(dsn), "-do", str(ses), "-mp", "40"], check=True)
    assert pcbnew.ImportSpecctraSES(board, str(ses)), "SES import failed"

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("routed:", len(board.GetTracks()), "tracks and vias")
