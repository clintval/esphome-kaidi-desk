"""Render the KiCad schematic in the repo's dark theme, cropped to its content.

Run with: python3 scripts/render_schematic.py
"""

import os
import pathlib
import re
import shutil
import subprocess
import tempfile

KICAD_CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
THEMES = pathlib.Path(os.environ.get("KICAD_CONFIG", pathlib.Path.home() / "Library/Preferences/kicad/10.0")) / "colors"
ROOT = pathlib.Path(__file__).resolve().parent.parent
X, Y, W, H = 12.0, 18.0, 284.0, 190.0

THEMES.mkdir(parents=True, exist_ok=True)
shutil.copy(ROOT / "hardware/themes/kaidi-dark.json", THEMES / "kaidi-dark.json")
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(
        [
            KICAD_CLI,
            "sch",
            "export",
            "svg",
            "--theme",
            "kaidi-dark",
            "--exclude-drawing-sheet",
            "-o",
            tmp,
            str(ROOT / "hardware/kaidi-desk.kicad_sch"),
        ],
        check=True,
        capture_output=True,
    )
    svg = (pathlib.Path(tmp) / "kaidi-desk.svg").read_text()
svg = re.sub(
    r'width="[\d.]+mm" height="[\d.]+mm" viewBox="[^"]+"',
    f'width="{W * 4:.0f}" height="{H * 4:.0f}" viewBox="{X} {Y} {W} {H}"',
    svg,
    count=1,
)
svg = re.sub(
    r'<rect x="0\.000000" y="0\.000000" width="[\d.]+" height="[\d.]+" rx="0\.000000" />',
    f'<rect x="{X}" y="{Y}" width="{W}" height="{H}" rx="4" />',
    svg,
    count=1,
)
svg = re.sub(r"<title>.*?</title>", "<title>Kaidi desk dongle schematic</title>", svg, count=1)
(ROOT / "docs/schematic.svg").write_text(svg)
