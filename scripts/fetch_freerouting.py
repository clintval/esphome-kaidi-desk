"""Download the pinned Freerouting release and verify its checksum.

Run with: python scripts/fetch_freerouting.py .pixi/tools/freerouting-2.5.0.jar
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0.jar"
SHA256 = "f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7"

jar = Path(sys.argv[1])
if not jar.exists() or hashlib.sha256(jar.read_bytes()).hexdigest() != SHA256:
    jar.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(URL).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        sys.exit(f"Freerouting checksum mismatch: got {digest}")
    jar.write_bytes(data)
print(jar)
