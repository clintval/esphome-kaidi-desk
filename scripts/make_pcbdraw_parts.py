"""Draw shaded PcbDraw component art for the parts its library lacks, in footprint millimetres.

Run with: python3 scripts/make_pcbdraw_parts.py hardware/pcbdraw
"""

import sys
from pathlib import Path

OUT = Path(sys.argv[1])


def svg(path, box, defs, body):
    x, y, w, h = box
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{w}mm" height="{h}mm" viewBox="{x} {y} {w} {h}">'
        f"<defs>{defs}</defs>{body}"
        '<rect id="origin" x="0" y="0" width="1" height="1" fill="#ff0000"/></svg>\n'
    )


def lin(id_, stops, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def rad(id_, stops):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<radialGradient id="{id_}" cx="0.35" cy="0.3" r="0.8">{s}</radialGradient>'


def rect(x, y, w, h, fill, rx=0, stroke="none", sw=0, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def text(x, y, s, size, fill, weight=700, anchor="middle", rotate=None):
    t = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    return (
        f'<text x="{x}" y="{y}" font-family="Helvetica, Arial, sans-serif" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" fill="{fill}"{t}>{s}</text>'
    )


GOLD = lin("gold", [(0, "#ffe7a3"), (0.5, "#d9a441"), (1, "#a0742a")])
SILVER = lin("silver", [(0, "#ffffff"), (0.45, "#c9d0d6"), (1, "#7d868f")])
SHADOW = 'opacity="0.35"'

# Amphenol/FCI 54602-910 right-angle RJ50 jack, opening toward +y (board edge).
cx, x1, x2, y1, y2 = 5.715, -1.935, 13.365, -3.77, 13.97
defs = lin("body", [(0, "#4a4f57"), (0.12, "#2b2f35"), (1, "#15171a")]) + lin("lip", [(0, "#0c0d0f"), (1, "#26292e")])
body = rect(x1 + 0.6, y1 + 0.6, x2 - x1, y2 - y1, "#000", 0.6, extra=SHADOW)
body += rect(x1, y1, x2 - x1, y2 - y1, "url(#body)", 0.6, "#0b0c0e", 0.15)
for i in range(6):
    body += rect(x1 + 1.2, y1 + 1.4 + i * 1.1, x2 - x1 - 2.4, 0.35, "#3d424a", 0.17)
body += rect(x1 + 0.5, y2 - 2.6, x2 - x1 - 1.0, 2.6, "url(#lip)", 0.4)
body += rect(cx - 3.4, y2 - 2.1, 6.8, 1.6, "#050506", 0.3)
body += rect(x1 + 0.25, y1 + 0.25, x2 - x1 - 0.5, 0.5, "#ffffff", 0.25, extra='opacity="0.12"')
body += text(cx, 6.2, "10P10C", 1.5, "#9aa3ad")
svg(
    OUT / "kaidi/RJ50_Amphenol_54602-910_Horizontal.svg",
    (x1 - 0.5, y1 - 0.5, x2 - x1 + 1.6, y2 - y1 + 1.6),
    defs + GOLD,
    body,
)

# ESP32-C3 SuperMini, component side up on two 1x8 sockets, USB-C toward -y.
defs = (
    lin("pcb", [(0, "#2a5bd7"), (0.5, "#1c45b0"), (1, "#122f7a")], 1, 1)
    + GOLD
    + SILVER
    + lin("chip", [(0, "#3a3a3d"), (1, "#111113")], 1, 1)
    + lin("ant", [(0, "#fffaf0"), (1, "#d8cfbd")], 1, 1)
    + lin("socket", [(0, "#2d2f33"), (1, "#0f1012")], 1, 0)
)
mx1, mx2, my1, my2 = -1.4, 16.64, -3.6, 18.9
body = ""
body += rect(mx1 + 0.8, my1 + 0.9, mx2 - mx1, my2 - my1, "#000", 1.0, extra=SHADOW)
body += rect(mx1, my1, mx2 - mx1, my2 - my1, "url(#pcb)", 1.0, "#0b1d4d", 0.15)
for i in range(8):
    for x in (0.0, 15.24):
        body += f'<circle cx="{x}" cy="{i * 2.54}" r="0.85" fill="url(#gold)" stroke="#8a6420" stroke-width="0.08"/>'
        body += f'<circle cx="{x}" cy="{i * 2.54}" r="0.38" fill="#c9b26a"/>'
left = ["5V", "G", "3V3", "4", "3", "2", "1", "0"]
right = ["5", "6", "7", "8", "9", "10", "20", "21"]
for i, (a, b) in enumerate(zip(left, right)):
    body += text(1.45, i * 2.54 + 0.38, a, 0.95, "#e8eef8", anchor="start")
    body += text(13.8, i * 2.54 + 0.38, b, 0.95, "#e8eef8", anchor="end")
body += rect(3.62, -6.4, 8.0, 5.0, "#000", 1.2, extra=SHADOW)
body += rect(3.12, -6.9, 9.0, 4.6, "url(#silver)", 1.4, "#6f7780", 0.12)
body += rect(4.32, -6.4, 6.6, 1.4, "#2b2f34", 0.7)
body += rect(5.12, 5.0, 5.0, 5.0, "url(#chip)", 0.3, "#000", 0.1)
body += '<circle cx="5.7" cy="5.6" r="0.22" fill="#5a5a5e"/>'
body += text(7.62, 7.9, "ESP32", 0.95, "#bfc4ca")
body += text(7.62, 9.0, "C3", 0.95, "#bfc4ca")
body += rect(4.62, 14.2, 6.0, 3.0, "url(#ant)", 0.3, "#a89e8a", 0.1)
for x in (3.6, 9.24):
    body += rect(x, 0.6, 2.4, 2.4, "url(#silver)", 0.3, "#6f7780", 0.1)
    body += f'<circle cx="{x + 1.2}" cy="1.8" r="0.6" fill="#2b2f34"/>'
body += text(4.8, 3.9, "BOOT", 0.7, "#e8eef8")
body += text(10.44, 3.9, "RST", 0.7, "#e8eef8")
for x, y in ((11.2, 6.0), (11.2, 7.4), (3.2, 11.2), (11.6, 11.6)):
    body += rect(x, y, 1.0, 0.55, "#c9a36a", 0.1)
body += rect(3.2, 6.2, 0.9, 0.6, "#ff4d4d", 0.15)
svg(OUT / "kaidi/ESP32-C3_SuperMini_Flush.svg", (mx1 - 0.5, -7.4, mx2 - mx1 + 1.8, my2 + 9.2), defs, body)

# 74AHCT125 in a DIP-14 socket, pin 1 at the origin, pins down the -x side.
defs = (
    lin("sock", [(0, "#2b2d31"), (1, "#121315")], 1, 0)
    + lin("ic", [(0, "#45474c"), (0.15, "#2a2b2f"), (1, "#141517")], 1, 1)
    + SILVER
    + GOLD
)
body = rect(-1.27, -2.54, 10.16, 20.32, "url(#sock)", 0.6, "#000", 0.12)
for i in range(7):
    for x in (0.0, 7.62):
        body += f'<circle cx="{x}" cy="{i * 2.54}" r="0.8" fill="url(#gold)" stroke="#6e521e" stroke-width="0.08"/>'
for i in range(7):
    body += rect(0.75, i * 2.54 - 0.45, 0.9, 0.9, "url(#silver)", 0.1)
    body += rect(5.97, i * 2.54 - 0.45, 0.9, 0.9, "url(#silver)", 0.1)
body += rect(1.9, -1.6, 4.6, 18.44, "#000", 0.4, extra=SHADOW)
body += rect(1.45, -1.9, 4.72, 18.84, "url(#ic)", 0.4, "#000", 0.1)
body += '<path d="M 2.95 -1.9 A 0.86 0.86 0 0 0 4.67 -1.9 Z" fill="#0d0e10"/>'
body += '<circle cx="2.3" cy="-0.6" r="0.35" fill="#1a1b1e" stroke="#3a3b40" stroke-width="0.06"/>'
body += text(3.81, 7.62, "74AHCT125", 1.15, "#c9ccd1", rotate=-90)
svg(OUT / "Package_DIP/DIP-14_W7.62mm_Socket.svg", (-2.0, -3.3, 11.6, 21.8), defs, body)

# 100 nF ceramic disc capacitor, pads at (0, 0) and (2.5, 0).
defs = rad("disc", [(0, "#f2b46b"), (0.6, "#d07a2c"), (1, "#8a4612")])
body = '<ellipse cx="1.55" cy="0.25" rx="1.6" ry="0.9" opacity="0.35" fill="#000"/>'
body += '<ellipse cx="1.25" cy="0" rx="1.55" ry="0.85" fill="url(#disc)" stroke="#6b360f" stroke-width="0.08"/>'
body += text(1.25, 0.3, "104", 0.8, "#4a2208")
svg(OUT / "Capacitor_THT/C_Disc_D3.0mm_W1.6mm_P2.50mm.svg", (-0.6, -1.2, 3.8, 2.6), defs, body)
