"""Add wire tags and a legend to the PcbDraw drawing of the rev 4 protoboard.

Run with: python3 scripts/annotate_protoboard.py IN.svg docs/protoboard.svg
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from protoboard import COLUMNS, EXTERNAL, WIRES  # noqa: E402

P, BX, BY, BW, BH = 2.54, 100.0, 100.0, 50.8, 38.1
NET = {"+5V": "#e5484d", "GND": "#2b2b2b", "CMD": "#3b82f6", "HEIGHT": "#16a34a", "WAKE": "#d946ef"}
FONT = "Helvetica, Arial, sans-serif"


def hole(name):
    k, row = COLUMNS.index(name[0]), int(name[1:])
    return BX + 5.08 + (row - 1) * P, BY + 5.08 + (9 - k) * P + (5.08 if k <= 4 else 0.0)


svg = Path(sys.argv[1]).read_text()
x0, y0, w, h = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split())
panel = 46.0
OFFSET = {"I17": (1.4, -0.95)}
out = []
out.append(f'<text x="{x0}" y="{y0 - 2.2}" font-family="{FONT}" font-size="2.6" font-weight="800" fill="#1d1d1f">Kaidi desk dongle, rev 4 on an EPLZON 1.5 x 2 in board</text>')
for i, (side, contact, where, net, note) in enumerate(EXTERNAL):
    x, y = hole(where)
    color = NET[net]
    tag = f"{'K' if side == 'keypad' else 'D'}{contact}"
    out.append(f'<circle cx="{x}" cy="{y}" r="1.25" fill="none" stroke="{color}" stroke-width="0.45"/>')
    ox, oy = OFFSET.get(where, (1.1, -2.9))
    out.append(f'<rect x="{x + ox}" y="{y + oy}" width="{1.2 + 0.95 * len(tag)}" height="1.9" rx="0.95" fill="{color}" stroke="#fff" stroke-width="0.15"/>')
    out.append(f'<text x="{x + ox + 0.6}" y="{y + oy + 1.4}" font-family="{FONT}" font-size="1.35" font-weight="800" fill="#fff">{tag}</text>')
lx, ly = x0 + w + 2.5, y0 + 1.5
out.append(f'<text x="{lx}" y="{ly}" font-family="{FONT}" font-size="1.9" font-weight="800" fill="#1d1d1f">Wires to solder</text>')
ly += 3.2
for side, contact, where, net, note in EXTERNAL:
    tag = f"{'K' if side == 'keypad' else 'D'}{contact}"
    out.append(f'<rect x="{lx}" y="{ly - 1.45}" width="{1.2 + 0.95 * len(tag)}" height="1.9" rx="0.95" fill="{NET[net]}"/>')
    out.append(f'<text x="{lx + 0.6}" y="{ly - 0.05}" font-family="{FONT}" font-size="1.35" font-weight="800" fill="#fff">{tag}</text>')
    out.append(f'<text x="{lx + 5.2}" y="{ly}" font-family="{FONT}" font-size="1.35" fill="#333"><tspan font-weight="700">{where}</tspan>  {note}</text>')
    ly += 2.6
ly += 1.6
out.append(f'<text x="{lx}" y="{ly}" font-family="{FONT}" font-size="1.9" font-weight="800" fill="#1d1d1f">Under the board</text>')
ly += 3.0
for a, b, net, note, layer in WIRES:
    if layer != "back":
        continue
    color = NET["+5V" if net == "+5V" else "GND"]
    out.append(f'<circle cx="{lx + 0.9}" cy="{ly - 0.45}" r="0.8" fill="none" stroke="{color}" stroke-width="0.3" stroke-dasharray="0.45 0.3"/>')
    out.append(f'<text x="{lx + 2.4}" y="{ly}" font-family="{FONT}" font-size="1.35" fill="#333"><tspan font-weight="700">{a} to {b}</tspan>  {net}, insulated wire</text>')
    ly += 2.6
ly += 1.6
out.append(f'<text x="{lx}" y="{ly}" font-family="{FONT}" font-size="1.9" font-weight="800" fill="#1d1d1f">Notes</text>')
for line in ("K = keypad side, the Bipom breakout terminals.",
             "D = the cut desk cable. Its 2, 3 and 8 share",
             "Bipom terminals 2, 3 and 8 with the keypad.",
             "Each row is two strips on the back: A-E and F-J.",
             "Firmware: TX GPIO7, enables GPIO6 and GPIO0,",
             "height on GPIO3."):
    ly += 2.3
    out.append(f'<text x="{lx}" y="{ly}" font-family="{FONT}" font-size="1.3" fill="#444">{line}</text>')
height = max(h + 8, ly - (y0 - 6) + 3)
svg = re.sub(r'width="[^"]+" height="[^"]+" viewBox="[^"]+"',
             f'width="{(w + panel) * 12:.0f}" height="{height * 12:.0f}" viewBox="{x0} {y0 - 6} {w + panel} {height}"', svg, count=1)
svg = svg.replace("</svg>", "\n".join(out) + "\n</svg>")
Path(sys.argv[2]).write_text(svg)
