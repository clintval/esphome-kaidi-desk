"""Draw the README's circuit-board illustration of the dongle as an SVG.

Run with: python3 scripts/draw_board.py docs/board.svg
"""

import sys

W, H = 1200, 860
MASK, EDGE = "#0f5132", "#093621"
TOP, BOTTOM = "#47b077", "#1d6b45"
GOLD, GOLD_EDGE = "#e0ae4c", "#9c7426"
SILK = "#eef5f0"
FONT = "ui-monospace, 'JetBrains Mono', Menlo, Consolas, monospace"

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=13, anchor="middle", fill=SILK, weight="600", opacity=1.0):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    add(
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" fill="{fill}" opacity="{opacity}">{s}</text>'
    )


def trace(points, layer="top", width=7):
    d = "M " + " L ".join(f"{x} {y}" for x, y in points)
    color = TOP if layer == "top" else BOTTOM
    dash = "" if layer == "top" else ' stroke-dasharray="1 0"'
    add(
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-linejoin="round"{dash}/>'
    )


def via(x, y, label=None, dy=-14):
    add(f'<circle cx="{x}" cy="{y}" r="7.5" fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="1.5"/>')
    add(f'<circle cx="{x}" cy="{y}" r="3" fill="#06140d"/>')
    if label:
        text(x, y + dy, label, 10, fill=SILK, weight="700", opacity=0.85)


def pad(x, y, w=14, h=14, r=3):
    add(
        f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" rx="{r}" '
        f'fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="1.2"/>'
    )


def resistor(x, y, code, vertical=False, name="", value=""):
    if vertical:
        pad(x, y - 17, 15, 11, 2)
        pad(x, y + 17, 15, 11, 2)
        add(f'<rect x="{x - 8}" y="{y - 12}" width="16" height="24" rx="2" fill="#1b1b1b"/>')
        add(
            f'<text x="{x}" y="{y + 3}" font-family="{FONT}" font-size="7" font-weight="700" '
            f'text-anchor="middle" fill="#d8d8d8" transform="rotate(-90 {x} {y})">{code}</text>'
        )
        text(x + 16, y - 2, name, 11, "start")
        text(x + 16, y + 11, value, 10, "start", opacity=0.75, weight="500")
    else:
        pad(x - 17, y, 11, 15, 2)
        pad(x + 17, y, 11, 15, 2)
        add(f'<rect x="{x - 12}" y="{y - 8}" width="24" height="16" rx="2" fill="#1b1b1b"/>')
        text(x, y + 3, code, 7, fill="#d8d8d8", weight="700")
        text(x, y - 15, f"{name} {value}".strip(), 11)


def capacitor(x, y, name, value):
    pad(x, y - 15, 15, 10, 2)
    pad(x, y + 15, 15, 10, 2)
    add(f'<rect x="{x - 8}" y="{y - 10}" width="16" height="20" rx="2" fill="#c9a36a" stroke="#8a6a3a"/>')
    text(x - 16, y - 2, name, 11, "end")
    text(x - 16, y + 11, value, 10, "end", opacity=0.75, weight="500")


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add(
    "<defs>"
    '<filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">'
    '<feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.35"/></filter>'
    '<linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#f4f6f8"/><stop offset="0.55" stop-color="#b9c1c9"/>'
    '<stop offset="1" stop-color="#8d97a1"/></linearGradient>'
    '<linearGradient id="chip" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#2b2b2b"/><stop offset="1" stop-color="#111"/></linearGradient>'
    '<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
    '<circle cx="12" cy="12" r="1" fill="#ffffff" opacity="0.05"/></pattern>'
    "</defs>"
)

# board
add(f'<rect x="40" y="50" width="1120" height="760" rx="34" fill="{MASK}" stroke="{EDGE}" stroke-width="4" filter="url(#shadow)"/>')
add('<rect x="40" y="50" width="1120" height="760" rx="34" fill="url(#grid)"/>')
for hx, hy in ((80, 90), (1120, 90), (80, 770), (1120, 770)):
    add(f'<circle cx="{hx}" cy="{hy}" r="15" fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="2"/>')
    add(f'<circle cx="{hx}" cy="{hy}" r="8" fill="#0b0f0d"/>')
text(110, 100, "esphome-kaidi-desk", 22, "start", weight="800")
text(110, 124, "Kaidi KDDY094 dongle  ·  rev 3", 13, "start", opacity=0.8, weight="500")

# bottom-layer traces first, so top copper and parts draw over them
trace([(536, 320), (536, 358), (792, 358), (830, 394)], "bottom")
trace([(845, 432), (800, 456), (800, 690), (480, 690), (480, 650)], "bottom")

# ESP32-C3 SuperMini, component side up, USB-C to the left
mx1, mx2, my1, my2 = 120, 420, 380, 600
add(f'<rect x="{mx1 - 30}" y="450" width="48" height="80" rx="10" fill="url(#metal)" stroke="#6b737b" stroke-width="2"/>')
add(f'<rect x="{mx1 - 22}" y="466" width="20" height="48" rx="6" fill="#30363c"/>')
add(f'<rect x="{mx1}" y="{my1}" width="{mx2 - mx1}" height="{my2 - my1}" rx="10" fill="#1c2633" stroke="#0e141b" stroke-width="2"/>')
add('<rect x="228" y="430" width="128" height="120" rx="6" fill="url(#metal)" stroke="#727b84" stroke-width="1.5"/>')
text(292, 485, "ESP32-C3", 14, fill="#3b434b", weight="800")
text(292, 503, "SuperMini", 11, fill="#4b545d", weight="700")
add('<rect x="372" y="440" width="34" height="100" rx="4" fill="#d9d2c4" stroke="#9e968a" stroke-width="1.5"/>')
text(389, 495, "ANT", 9, fill="#6b6457", weight="800")
top_row = ["5", "6", "7", "8", "9", "10", "20", "21"]
bottom_row = ["5V", "G", "3.3", "4", "3", "2", "1", "0"]
px = {label: 150 + i * 36 for i, label in enumerate(top_row)}
bx = {label: 150 + i * 36 for i, label in enumerate(bottom_row)}
for i in range(8):
    x = 150 + i * 36
    for y in (392, 588):
        add(f'<path d="M {x - 9} {y} a 9 9 0 0 1 18 0 a 9 9 0 0 1 -18 0" fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="1.2"/>')
        add(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#1c2633"/>')
    text(x, 416, top_row[i], 10, fill="#c9d4e0", weight="700")
    text(x, 574, bottom_row[i], 10, fill="#c9d4e0", weight="700")
text(270, 630, "U1", 13, weight="800")

# 74AHCT125, pins 1-7 face the module, pin 1 at the left
cx1, cx2 = 466, 662
add(f'<rect x="{cx1}" y="204" width="{cx2 - cx1}" height="82" rx="6" fill="url(#chip)" stroke="#000" stroke-width="1.5"/>')
add(f'<circle cx="{cx1 + 14}" cy="272" r="4.5" fill="#3a3a3a"/>')
text((cx1 + cx2) / 2, 250, "74AHCT125", 15, fill="#d9d9d9", weight="800")
pin_x = {n: 480 + (n - 1) * 28 for n in range(1, 8)}
pin_x.update({n: 480 + (14 - n) * 28 for n in range(8, 15)})
for n in range(1, 15):
    y = 300 if n <= 7 else 190
    add(f'<rect x="{pin_x[n] - 5}" y="{min(y, 286) if n <= 7 else 190}" width="10" height="{14}" rx="2" fill="#cfd3d6"/>')
    pad(pin_x[n], y, 12, 14, 2)
text(cx2 + 18, 252, "U2", 13, "start", weight="800")

# RJ50 jack on the right edge, pads 1-10 facing the board
add('<rect x="930" y="230" width="190" height="250" rx="10" fill="url(#metal)" stroke="#6b737b" stroke-width="2"/>')
add('<rect x="1040" y="262" width="90" height="186" rx="8" fill="#20262c"/>')
for i in range(10):
    add(f'<rect x="1046" y="{270 + i * 17.5}" width="40" height="6" rx="2" fill="{GOLD}"/>')
text(1025, 505, "J1  TO DESK", 13, weight="800")
text(1025, 523, "RJ50 · 10P10C", 11, opacity=0.75, weight="500")
jy = {i: 262 + (i - 1) * 22 for i in range(1, 11)}
for i in range(1, 11):
    used = i in (3, 7, 8, 10)
    add(
        f'<circle cx="905" cy="{jy[i]}" r="8" fill="{GOLD if used else "#b89a5a"}" '
        f'stroke="{GOLD_EDGE}" stroke-width="1.2" opacity="{1 if used else 0.55}"/>'
    )
    add(f'<circle cx="905" cy="{jy[i]}" r="3" fill="#0b0f0d"/>')
    text(925, jy[i] + 4, str(i), 10, "start", opacity=1 if used else 0.45, weight="700")
text(870, jy[3] + 4, "GND", 10, "end", weight="700", opacity=0.85)

# output enables and command input, module top row to chip pins 1, 2 and 4
trace([(px["6"], 392), (px["6"], 330), (pin_x[1], 330), (pin_x[1], 300)])
trace([(px["7"], 392), (px["7"], 350), (pin_x[2], 350), (pin_x[2], 300)])
trace([(px["10"], 392), (px["10"], 370), (pin_x[4], 370), (pin_x[4], 300)])
trace([(420, 330), (420, 290)])
resistor(420, 272, "104", vertical=True, name="R3", value="100k")
trace([(420, 255), (420, 238)])
via(420, 230, "3V3")
trace([(450, 370), (450, 396)])
resistor(450, 414, "104", vertical=True, name="R4", value="100k")
trace([(450, 431), (450, 448)])
via(450, 456, "3V3", dy=22)
text(300, 324, "OE", 10, weight="700", opacity=0.8)
text(300, 344, "TX", 10, weight="700", opacity=0.8)
text(380, 364, "WAKE OE", 10, weight="700", opacity=0.8)

# chip ties on the top side
trace([(pin_x[14], 190), (pin_x[14], 150)])
via(pin_x[14], 142, "5V")
trace([(pin_x[14], 166), (440, 166), (440, 151)])
capacitor(440, 136, "C1", "100n")
trace([(440, 121), (440, 108)])
via(440, 100)
for n, net in ((13, "3V3"), (12, "GND"), (10, "3V3"), (9, "GND")):
    trace([(pin_x[n], 190), (pin_x[n], 160)])
    via(pin_x[n], 152, net if net == "3V3" else None)

# chip ties and outputs on the module side
trace([(pin_x[5], 300), (pin_x[5], 318)])
via(pin_x[5], 324)
trace([(pin_x[7], 300), (pin_x[7], 318)])
via(pin_x[7], 324)
trace([(pin_x[3], 300), (pin_x[3], 314)])
via(pin_x[3], 320)

# command: chip pin 3, through the bottom layer, R1 1k to J1 pin 7
via(830, 394)
trace([(830, 394), (848, 394)])
resistor(865, 394, "102", name="R1", value="1k")
trace([(882, 394), (905, jy[7])])
text(700, 376, "CMD", 10, weight="700", opacity=0.8)

# wake: chip pin 6, R2 1k under the jack to J1 pin 10
trace([(pin_x[6], 300), (pin_x[6], 345), (760, 345), (760, 480), (820, 480)])
resistor(837, 480, "102", name="R2", value="1k")
trace([(854, 480), (880, 480), (905, jy[10])])
text(700, 337, "WAKE", 10, weight="700", opacity=0.8)

# ground on J1 pin 3
trace([(905, jy[3]), (872, jy[3]), (866, 296)])
via(860, 290)

# height: J1 pin 8 down through the bottom layer to the divider, then to GPIO4
trace([(905, jy[8]), (868, 425), (845, 432)])
via(845, 432)
via(480, 650)
trace([(480, 650), (424, 650)])
resistor(407, 650, "103", name="R5", value="10k")
trace([(390, 650), (330, 650)])
add(f'<circle cx="330" cy="650" r="6" fill="{TOP}"/>')
trace([(330, 650), (bx["4"], 650), (bx["4"], 588)])
trace([(330, 650), (330, 668)])
resistor(330, 686, "103", vertical=True, name="R6", value="10k")
trace([(330, 703), (330, 718)])
resistor(330, 736, "472", vertical=True, name="R7", value="4.7k")
trace([(330, 753), (330, 764)])
via(330, 772)
text(620, 712, "HEIGHT", 10, weight="700", opacity=0.8)

# module power
trace([(bx["5V"], 588), (bx["5V"], 640)])
via(bx["5V"], 648, "5V", dy=24)
trace([(bx["G"], 588), (bx["G"], 680)])
via(bx["G"], 688, "GND", dy=24)
trace([(bx["3.3"], 588), (bx["3.3"], 720)])
via(bx["3.3"], 728, "3V3", dy=24)

# legend
lx, ly = 940, 640
add(f'<rect x="{lx - 20}" y="{ly - 30}" width="210" height="140" rx="12" fill="#0b3f27" opacity="0.6"/>')
for i, (color, label) in enumerate(((TOP, "top copper"), (BOTTOM, "bottom copper"))):
    add(f'<line x1="{lx}" y1="{ly + i * 26}" x2="{lx + 34}" y2="{ly + i * 26}" stroke="{color}" stroke-width="7" stroke-linecap="round"/>')
    text(lx + 48, ly + 4 + i * 26, label, 12, "start", weight="600")
via(lx + 17, ly + 52)
text(lx + 48, ly + 56, "via to the other layer", 12, "start", weight="600")
text(lx, ly + 86, "unlabeled vias: GND plane", 11, "start", opacity=0.75, weight="500")

add("</svg>")
with open(sys.argv[1], "w") as handle:
    handle.write("\n".join(out) + "\n")
