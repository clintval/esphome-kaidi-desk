"""Autoroute the placed board with Freerouting and pull the result back into KiCad.

The ground pours are lifted off the board while Freerouting runs, so it routes every ground pad with a
real trace instead of trusting a pour that later fills around it, then they go back and are refilled.
Rule areas that only forbid pours are lifted too, since Freerouting would treat them as full keepouts.
Each attempt must pass KiCad's connectivity check and full DRC, otherwise it is routed again with
a different Freerouting strategy.

Run with KiCad's Python:
    $KICAD_PYTHON scripts/route_pcb.py hardware/kaidi-desk.kicad_pcb FREEROUTING_JAR JAVA
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pcbnew

PCB, JAR, JAVA = sys.argv[1], sys.argv[2], sys.argv[3]
ATTEMPTS = 6
STRATEGIES = [
    [],
    ["-us", "global"],
    ["-us", "hybrid"],
    ["-is", "sequential"],
    ["-us", "global", "-is", "sequential"],
    ["-mt", "1"],
]


def route(placed, attempt):
    board = pcbnew.LoadBoard(placed)
    pours = [z for z in board.Zones() if not z.GetIsRuleArea() or not z.GetDoNotAllowTracks()]
    for zone in pours:
        board.Remove(zone)
    netclass = board.GetDesignSettings().m_NetSettings.GetDefaultNetclass()
    netclass.SetTrackWidth(pcbnew.FromMM(0.4))
    netclass.SetClearance(pcbnew.FromMM(0.25))
    netclass.SetViaDiameter(pcbnew.FromMM(0.8))
    netclass.SetViaDrill(pcbnew.FromMM(0.4))
    with tempfile.TemporaryDirectory() as tmp:
        dsn, ses = Path(tmp) / "board.dsn", Path(tmp) / "board.ses"
        assert pcbnew.ExportSpecctraDSN(board, str(dsn)), "DSN export failed"
        subprocess.run(
            [JAVA, "-Djava.awt.headless=true", "-jar", JAR, "--gui.enabled=false", "-de", str(dsn), "-do", str(ses)]
            + ["-mp", "40"]
            + STRATEGIES[(attempt - 1) % len(STRATEGIES)],
            check=True,
            capture_output=True,
        )
        assert pcbnew.ImportSpecctraSES(board, str(ses)), "SES import failed"
    for zone in pours:
        board.Add(zone)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    return board, board.GetConnectivity().GetUnconnectedCount(True)


CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")


def drc_errors(path):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [CLI, "pcb", "drc", "--severity-error", "--exit-code-violations", "-o", f"{tmp}/drc.rpt", path],
            capture_output=True,
            check=False,
        )
        report = Path(f"{tmp}/drc.rpt").read_text()
    return [line for line in report.splitlines() if line.startswith("[")] if result.returncode else []


with tempfile.TemporaryDirectory() as tmp:
    placed = str(Path(tmp) / "placed.kicad_pcb")
    candidate = str(Path(tmp) / Path(PCB).name)
    shutil.copy(PCB, placed)
    for sidecar in (Path(PCB).with_suffix(".kicad_pro"), Path(PCB).parent / "fp-lib-table"):
        if sidecar.exists():
            shutil.copy(sidecar, Path(tmp) / sidecar.name)
    for attempt in range(1, ATTEMPTS + 1):
        board, unconnected = route(placed, attempt)
        board.Save(candidate)
        errors = drc_errors(candidate)
        clean = unconnected == 0 and not errors
        print(f"attempt {attempt}: {unconnected} unconnected, DRC {errors or 'clean'}")
        if clean:
            shutil.copy(candidate, PCB)
            break
    else:
        sys.exit(f"no clean route after {ATTEMPTS} attempts")
