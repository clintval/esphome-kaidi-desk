"""Compile the prebuilt firmware and assemble the browser installer's website.

Run with: python scripts/make_site.py VERSION .build/site
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION, SITE = sys.argv[1], Path(sys.argv[2])
WORK = ROOT / ".build"
REPOSITORY = "https://github.com/clintval/esphome-kaidi-desk"

assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION), f"not a version: {VERSION}"
WORK.mkdir(exist_ok=True)
for name in ("desk", "factory"):
    config = (ROOT / f"example/{name}.yaml").read_text()
    local = config.replace(
        "source: github://clintval/esphome-kaidi-desk@main", "source: {type: local, path: ../components}"
    )
    (WORK / f"{name}.yaml").write_text(local)
assert "type: local" in (WORK / "desk.yaml").read_text(), "the firmware must be built from this checkout"
subprocess.run(["esphome", "-s", "version", VERSION, "compile", str(WORK / "factory.yaml")], check=True)

build = next((WORK / ".esphome/build/kaidi-desk-factory").rglob("firmware.factory.bin")).parent
shutil.rmtree(SITE, ignore_errors=True)
firmware = SITE / "firmware"
firmware.mkdir(parents=True)
for kind in ("factory", "ota"):
    shutil.copy(build / f"firmware.{kind}.bin", firmware / f"kaidi-desk-{VERSION}.{kind}.bin")
update = firmware / f"kaidi-desk-{VERSION}.ota.bin"
manifest = {
    "name": "Kaidi Desk",
    "version": VERSION,
    "home_assistant_domain": "esphome",
    "new_install_prompt_erase": True,
    "builds": [
        {
            "chipFamily": "ESP32-C3",
            "parts": [{"path": f"kaidi-desk-{VERSION}.factory.bin", "offset": 0}],
            "ota": {
                "path": update.name,
                "md5": hashlib.md5(update.read_bytes()).hexdigest(),
                "summary": f"esphome-kaidi-desk {VERSION}",
                "release_url": f"{REPOSITORY}/releases/tag/{VERSION}",
            },
        }
    ],
}
(firmware / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
shutil.copy(ROOT / "web/index.html", SITE / "index.html")
shutil.copy(ROOT / "docs/board-3d.png", SITE / "board.png")
print(f"wrote the installer for {VERSION} to {SITE}")
