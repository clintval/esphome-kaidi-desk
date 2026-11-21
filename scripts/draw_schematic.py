import sys

W, H = 1320, 1060
out = []
TX, OE, RX, P5, P3, GNDC, GRAY = "#1f6fd1", "#8e44ad", "#2e8b57", "#d62728", "#e67e00", "#222", "#9a9a94"


def t(x, y, s, size=14, anchor="start", weight="normal", fill="#222"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{s}</text>')


def line(pts, color, w=3):
    d = " ".join(f"{x},{y}" for x, y in pts)
    out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, color):
    out.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')


def pin(x, y):
    out.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#ffd54a" stroke="#222" stroke-width="1.5"/>')


def box(x, y, w, h, fill, stroke):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')


def gnd(x, y):
    line([(x, y), (x, y + 12)], GNDC)
    for i, half in enumerate((14, 9, 4)):
        yy = y + 12 + i * 6
        line([(x - half, yy), (x + half, yy)], GNDC, 2.5)


def flag(x, y, label, color, up=True):
    y2 = y - 16 if up else y + 16
    line([(x, y), (x, y2)], color)
    line([(x - 12, y2), (x + 12, y2)], color, 3)
    t(x, y2 - 6 if up else y2 + 18, label, 13, "middle", "bold", color)


def res_v(x, y1, y2, label, color):
    out.append(f'<rect x="{x - 9}" y="{y1}" width="18" height="{y2 - y1}" rx="3" fill="#fff" stroke="{color}" stroke-width="2.5"/>')
    t(x + 16, (y1 + y2) / 2 + 5, label, 14, "start", "bold", "#222")


def res_h(x1, x2, y, label, color):
    out.append(f'<rect x="{x1}" y="{y - 9}" width="{x2 - x1}" height="18" rx="3" fill="#fff" stroke="{color}" stroke-width="2.5"/>')
    t((x1 + x2) / 2, y - 16, label, 14, "middle", "bold", "#222")


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
out.append(f'<rect width="{W}" height="{H}" fill="#fbfbf8"/>')
t(30, 42, "Kaidi Desk Dongle: Schematic", 26, weight="bold")
t(30, 68, "Kaidi KDDY094 free RJ50 (10P10C) port → breakout → 74AHCT125 + resistor divider → ESP32-C3 SuperMini (USB-C power only)", 15, fill="#555")

# ESP32-C3 SuperMini
box(60, 140, 160, 300, "#dbe7f5", "#2b4f80")
t(140, 128, "ESP32-C3 SuperMini", 16, "middle", "bold")
t(140, 462, "match pins by printed label", 12, "middle", fill="#555")
t(140, 478, "(board sits upside down)", 12, "middle", fill="#555")
c3 = {"5V": 180, "3V3": 220, "GND": 260, "GPIO6": 310, "GPIO7": 350, "GPIO4": 390, "GPIO10": 425}
for name, y in c3.items():
    pin(220, y)
    t(208, y + 5, name, 15, "end", "bold")
line([(220, 180), (262, 180)], P5)
flag(262, 180, "+5V", P5)
line([(220, 220), (300, 220)], P3)
flag(300, 220, "+3V3", P3)
line([(220, 260), (262, 260)], GNDC)
gnd(262, 260)

# 74AHCT125
cx1, cx2 = 600, 740
box(cx1, 160, cx2 - cx1, 390, "#efe6d6", "#6b5332")
out.append(f'<path d="M {(cx1 + cx2) / 2 - 14} 160 A 14 14 0 0 0 {(cx1 + cx2) / 2 + 14} 160" fill="#fbfbf8" stroke="#6b5332" stroke-width="2"/>')
t((cx1 + cx2) / 2, 148, "SN74AHCT125N (top view)", 16, "middle", "bold")
t((cx1 + cx2) / 2, 575, "notch up, pin 1 top-left", 12, "middle", fill="#555")
left = [(1, "1OE"), (2, "1A"), (3, "1Y"), (4, "2OE"), (5, "2A"), (6, "2Y"), (7, "GND")]
right = [(14, "VCC"), (13, "4OE"), (12, "4A"), (11, "4Y"), (10, "3OE"), (9, "3A"), (8, "3Y")]
py = {}
for i, ((ln, lname), (rn, rname)) in enumerate(zip(left, right)):
    y = 190 + i * 55
    py[ln] = y
    py[rn] = y
    line([(cx1 - 30, y), (cx1, y)], "#6b5332", 2)
    line([(cx2, y), (cx2 + 30, y)], "#6b5332", 2)
    pin(cx1 - 30, y)
    pin(cx2 + 30, y)
    t(cx1 + 8, y + 5, f"{ln} {lname}", 14, "start", "bold")
    t(cx2 - 8, y + 5, f"{rname} {rn}", 14, "end", "bold")

lx, rx = cx1 - 30, cx2 + 30
# unused gates, left side
t(lx - 12, py[5] + 5, "→ +3V3", 13, "end", "bold", P3)
line([(lx, py[7]), (lx - 25, py[7])], GNDC)
gnd(lx - 25, py[7])
# right side
line([(rx, py[14]), (900, py[14])], P5)
flag(830, py[14], "+5V", P5)
dot(830, py[14], P5)
line([(900, py[14]), (900, 218)], P5)
line([(884, 218), (916, 218)], "#222", 3)
line([(884, 228), (916, 228)], "#222", 3)
line([(900, 228), (900, 240)], GNDC)
gnd(900, 240)
t(924, 228, "0.1 µF (104)", 14, "start", "bold")
for n in (13, 10):
    t(rx + 12, py[n] + 5, "→ +3V3", 13, "start", "bold", P3)
for n in (12, 9):
    t(rx + 12, py[n] + 5, "→ GND", 13, "start", "bold", GNDC)
for n in (11, 8):
    t(rx + 12, py[n] + 5, "NC", 13, "start", "bold", GRAY)

# OE: GPIO6 -> pin 1, 100k pull-up to 3V3
line([(220, 310), (420, 310), (420, py[1]), (lx, py[1])], OE)
dot(480, py[1], OE)
line([(480, py[1]), (480, 165)], OE)
res_v(480, 115, 165, "", OE)
t(495, 135, "100k", 14, "start", "bold")
line([(480, 115), (480, 108)], P3)
flag(480, 108, "+3V3", P3)

# TX: GPIO7 -> pin 2
line([(220, 350), (440, 350), (440, py[2]), (lx, py[2])], TX)

# RJ50 breakout, contact 10 at top so the two signal wires never cross
box(60, 610, 160, 340, "#e9e9e4", "#444")
t(140, 598, "RJ50 breakout (free port)", 16, "middle", "bold")
cy = {i: 640 + (10 - i) * 30 for i in range(1, 11)}
for i, y in cy.items():
    pin(220, y)
    t(208, y + 5, str(i), 15, "end", "bold", "#222" if i in (3, 7, 8) else GRAY)
roles = {1: "NC", 2: "+5 V (leave unconnected)", 4: "NC", 5: "NC", 6: "NC", 9: "NC"}
for i, r in roles.items():
    t(232, cy[i] + 5, r, 12, "start", "normal", GRAY)
t(75, cy[3] + 5, "GND", 12, "start", "bold")
t(75, cy[7] + 5, "command", 12, "start", "bold")
t(75, cy[8] + 5, "height", 12, "start", "bold")
t(75, cy[10] + 5, "wake", 12, "start", "bold")
line([(220, cy[3]), (300, cy[3])], GNDC)
gnd(300, cy[3])

# wake: GPIO10 -> pin 4 (2OE, 100k pull-up); pin 6 (2Y) -> 1k -> contact 10
WK = "#c2185b"
line([(220, 425), (505, 425), (505, py[4]), (lx, py[4])], WK)
t(508, py[4] - 8, "100k to +3V3", 11, "start", "bold", P3)
line([(lx, py[6]), (530, py[6]), (530, 560)], WK)
res_v(530, 560, 610, "", WK)
t(538, 600, "1k", 14, "start", "bold")
line([(530, 610), (530, 625), (300, 625), (300, 640), (220, 640)], WK)

# TX: pin 3 (1Y) -> 1k -> contact 7
line([(lx, py[3]), (470, py[3]), (470, 660)], TX)
res_v(470, 660, 705, "1k", TX)
line([(470, 705), (470, cy[7]), (220, cy[7])], TX)

# RX: contact 8 -> 10k -> GPIO4, with 10k + 4.7k to GND
line([(220, cy[8]), (360, cy[8]), (360, 600)], RX)
res_v(360, 540, 600, "", RX)
t(344, 575, "10k", 14, "end", "bold")
line([(360, 540), (360, 390), (220, 390)], RX)
dot(360, 480, RX)
line([(360, 480), (410, 480), (410, 490)], RX)
res_v(410, 490, 530, "10k", RX)
line([(410, 530), (410, 545)], RX)
res_v(410, 545, 585, "4.7k", RX)
line([(410, 585), (410, 600)], GNDC)
gnd(410, 600)
t(350, 470, "≈3.1 V", 13, "end", "bold", RX)

# checklist
box(980, 230, 320, 800, "#ffffff", "#bbb")
t(1000, 260, "Connections", 18, weight="bold")
rows = [
    ("Power", "#222"),
    ("C3 5V → chip 14 (VCC)", P5),
    ("0.1 µF across chip 14 and 7", "#222"),
    ("C3 GND → chip 7 → RJ50 3", GNDC),
    ("C3 3V3 → chip 5, 10, 13", P3),
    ("GND → chip 9, 12", GNDC),
    ("", "#222"),
    ("Commands (TX)", "#222"),
    ("C3 GPIO7 → chip 2 (1A)", TX),
    ("chip 3 (1Y) → 1k → RJ50 7", TX),
    ("C3 GPIO6 → chip 1 (1OE)", OE),
    ("chip 1 → 100k → C3 3V3", OE),
    ("", "#222"),
    ("Wake (motor power)", "#222"),
    ("C3 GPIO10 → chip 4 (2OE)", "#c2185b"),
    ("chip 4 → 100k → C3 3V3", "#c2185b"),
    ("chip 6 (2Y) → 1k → RJ50 10", "#c2185b"),
    ("", "#222"),
    ("Height (RX)", "#222"),
    ("RJ50 8 → 10k → C3 GPIO4", RX),
    ("C3 GPIO4 → 10k → 4.7k → GND", RX),
    ("", "#222"),
    ("Leave unconnected", "#222"),
    ("RJ50 1, 2, 4, 5, 6, 9", GRAY),
    ("chip 8, 11", GRAY),
    ("", "#222"),
    ("Before plugging into the desk", "#222"),
    ("C3 on USB, RJ50 unplugged:", "#555"),
    ("chip 14 ≈ 5 V, chip 1 ≈ 3.3 V,", "#555"),
    ("GPIO4 ≈ 0 V (all vs GND)", "#555"),
]
y = 290
for text, color in rows:
    if text:
        bold = text in ("Power", "Commands (TX)", "Wake (motor power)", "Height (RX)", "Leave unconnected", "Before plugging into the desk")
        t(1000, y, text, 15 if bold else 14, weight="bold" if bold else "normal", fill=color)
    y += 24

# legend
lg = [("command (TX)", TX), ("output enable", OE), ("height (RX)", RX), ("wake", "#c2185b"), ("+5 V", P5), ("+3.3 V", P3), ("ground", GNDC)]
x = 980
for i, (label, color) in enumerate(lg):
    yy = 100 + (i % 4) * 26
    xx = x + (i // 4) * 160
    line([(xx, yy), (xx + 30, yy)], color, 4)
    t(xx + 40, yy + 5, label, 13)

out.append("</svg>")
open(sys.argv[1], "w").write("\n".join(out) + "\n")
