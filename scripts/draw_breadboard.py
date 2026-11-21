import sys

W, H = 1320, 1060
out = []
TX, OE, RX, P5, P3, GNDC, GRAY = "#1f6fd1", "#8e44ad", "#2e8b57", "#d62728", "#e67e00", "#222", "#9a9a94"

X0, DX = 150, 34
ROWS = {"T+": 160, "T-": 192, "a": 262, "b": 296, "c": 330, "d": 364, "e": 398,
        "f": 466, "g": 500, "h": 534, "i": 568, "j": 602, "B-": 672, "B+": 704}


def x(col):
    return X0 + (col - 1) * DX


def hole(col, row):
    return x(col), ROWS[row]


def t(px, py, s, size=14, anchor="start", weight="normal", fill="#222"):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out.append(f'<text x="{px}" y="{py}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{s}</text>')


def rect(px, py, w, h, fill, stroke="none", rx=6, sw=2, extra=""):
    out.append(f'<rect x="{px}" y="{py}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def wire(a, b, color, bend=0.0, label=None):
    (x1, y1), (x2, y2) = a, b
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    cx, cy = mx - dy * bend, my + dx * bend
    out.append(f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" fill="none" stroke="#00000033" stroke-width="9" stroke-linecap="round"/>')
    out.append(f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>')
    for px, py in (a, b):
        out.append(f'<circle cx="{px}" cy="{py}" r="5" fill="#fff" stroke="{color}" stroke-width="3"/>')


def resistor(a, b, label, bands):
    (x1, y1), (x2, y2) = a, b
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8a8a8a" stroke-width="3"/>')
    for px, py in (a, b):
        out.append(f'<circle cx="{px}" cy="{py}" r="4" fill="#8a8a8a"/>')
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    horiz = abs(x2 - x1) >= abs(y2 - y1)
    L, Wd = 46, 16
    if horiz:
        rect(mx - L / 2, my - Wd / 2, L, Wd, "#e8d3a8", "#8a6d3b", 7, 1.5)
        for i, c in enumerate(bands):
            rect(mx - L / 2 + 8 + i * 8, my - Wd / 2, 4, Wd, c, rx=0)
        t(mx, my - 14, label, 13, "middle", "bold")
    else:
        rect(mx - Wd / 2, my - L / 2, Wd, L, "#e8d3a8", "#8a6d3b", 7, 1.5)
        for i, c in enumerate(bands):
            rect(mx - Wd / 2, my - L / 2 + 8 + i * 8, Wd, 4, c, rx=0)
        t(mx + 14, my + 5, label, 13, "start", "bold")


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
out.append(f'<rect width="{W}" height="{H}" fill="#fbfbf8"/>')
t(30, 42, "Kaidi Desk Dongle: Breadboard Layout", 26, weight="bold")
t(30, 68, "Half-size (30-column) breadboard; fits the same way on a full-size one. Holes are named column + row, e.g. j25.", 15, fill="#555")

# breadboard body
rect(100, 120, 1090, 620, "#f3f1ea", "#c9c5b8", 14)
rect(100, 424, 1090, 18, "#e2ded2", rx=0)
for rail, color in (("T+", P5), ("T-", "#2b5bd7"), ("B-", "#2b5bd7"), ("B+", P5)):
    yy = ROWS[rail]
    off = -17 if rail in ("T+", "B-") else 17
    out.append(f'<line x1="{x(1) - 20}" y1="{yy + off}" x2="{x(30) + 20}" y2="{yy + off}" stroke="{color}" stroke-width="2"/>')
for row, yy in ROWS.items():
    for col in range(1, 31):
        rect(x(col) - 5, yy - 5, 10, 10, "#3a3a3a", rx=2)
    if row in "abcdefghij":
        t(x(1) - 30, yy + 5, row, 14, "middle", "bold", "#777")
        t(x(30) + 30, yy + 5, row, 14, "middle", "bold", "#777")
for col in range(1, 31):
    t(x(col), 236, str(col), 11, "middle", "bold", "#777")
    t(x(col), 632, str(col), 11, "middle", "bold", "#777")
t(x(30) + 34, ROWS["T+"] + 5, "+5V", 14, "start", "bold", P5)
t(x(30) + 34, ROWS["T-"] + 5, "GND", 14, "start", "bold", "#2b5bd7")
t(x(30) + 34, ROWS["B-"] + 5, "GND", 14, "start", "bold", "#2b5bd7")
t(x(30) + 34, ROWS["B+"] + 5, "+3V3", 14, "start", "bold", P3)

# ESP32-C3 SuperMini, upside down, USB-C hanging off the left edge
c3x1, c3x2 = x(1) - 22, x(8) + 22
rect(c3x1 - 38, ROWS["c"] + 48, 44, 76, "#b9bec4", "#555", 5)
rect(c3x1, ROWS["c"] - 22, c3x2 - c3x1, ROWS["g"] - ROWS["c"] + 44, "#1d3557", "#0d1b2a", 8)
t((c3x1 + c3x2) / 2, ROWS["e"] + 2, "ESP32-C3 SuperMini", 13, "middle", "bold", "#fff")
t((c3x1 + c3x2) / 2, ROWS["e"] + 20, "labels facing up", 11, "middle", "normal", "#cfd8e3")
t(c3x1 + 10, ROWS["e"] + 42, "◀ USB-C", 11, "start", "bold", "#cfd8e3")
top = ["5V", "G", "3.3", "4", "3", "2", "1", "0"]
bot = ["5", "6", "7", "8", "9", "10", "20", "21"]
for i, (a, b) in enumerate(zip(top, bot)):
    for row, lab in (("c", a), ("g", b)):
        px, py = hole(i + 1, row)
        out.append(f'<circle cx="{px}" cy="{py}" r="7" fill="#d4af37" stroke="#7a5c00" stroke-width="1.5"/>')
        t(px, py + (24 if row == "c" else -14), lab, 12, "middle", "bold", "#fff")

# SN74AHCT125N: pins 1-7 on row f (cols 16-22), pins 14-8 on row e
ch1, ch2 = x(16) - 18, x(22) + 18
rect(ch1, ROWS["e"] - 16, ch2 - ch1, ROWS["f"] - ROWS["e"] + 32, "#2b2b2b", "#111", 4)
out.append(f'<path d="M {ch1} {(ROWS["e"] + ROWS["f"]) / 2 - 12} A 12 12 0 0 1 {ch1} {(ROWS["e"] + ROWS["f"]) / 2 + 12}" fill="#f3f1ea"/>')
t((ch1 + ch2) / 2 + 8, (ROWS["e"] + ROWS["f"]) / 2 + 5, "74AHCT125", 13, "middle", "bold", "#ddd")
for i in range(7):
    for row, n in (("f", 1 + i), ("e", 14 - i)):
        px, py = hole(16 + i, row)
        rect(px - 6, py - 6, 12, 12, "#c0c0c0", "#666", 1, 1)
        t(px, py + (30 if row == "f" else -20), str(n), 12, "middle", "bold", "#6b5332")

# 0.1 uF across the top rails beside VCC
cx_ = x(15)
out.append(f'<line x1="{cx_}" y1="{ROWS["T+"]}" x2="{cx_}" y2="{ROWS["T-"]}" stroke="#8a8a8a" stroke-width="3"/>')
out.append(f'<ellipse cx="{cx_}" cy="{(ROWS["T+"] + ROWS["T-"]) / 2}" rx="11" ry="8" fill="#e0b84a" stroke="#8a6d3b" stroke-width="1.5"/>')
t(cx_ - 16, (ROWS["T+"] + ROWS["T-"]) / 2 + 5, "0.1 µF", 13, "end", "bold")

# power and ground
wire(hole(1, "a"), hole(1, "T+"), P5, bend=0.15)
wire(hole(2, "a"), hole(2, "T-"), GNDC)
wire(hole(3, "a"), hole(1, "B+"), P3, bend=0.42)
wire(hole(30, "T-"), hole(30, "B-"), GNDC, bend=0.12)
wire(hole(16, "a"), hole(16, "T+"), P5, bend=0.15)
wire(hole(17, "a"), hole(17, "T+"), P5, bend=0.15)
wire(hole(18, "a"), hole(18, "T-"), GNDC)
wire(hole(20, "a"), hole(20, "T+"), P5, bend=0.15)
wire(hole(21, "a"), hole(21, "T-"), GNDC)
wire(hole(20, "j"), hole(20, "B+"), P3)
WK = "#c2185b"
resistor(hole(19, "j"), hole(18, "B+"), "100k", ["#8b4513", "#222", "#ffd700"])
wire(hole(6, "i"), hole(19, "h"), WK, bend=-0.06)
resistor(hole(21, "h"), hole(28, "h"), "1k", ["#8b4513", "#222", "#d62728"])
wire(hole(22, "j"), hole(22, "B-"), GNDC)

# output enable: GPIO6 -> pin 1, 100k pull-up to 3V3
wire(hole(2, "i"), hole(16, "i"), OE, bend=-0.05)
resistor(hole(16, "j"), hole(17, "B+"), "100k", ["#8b4513", "#222", "#ffd700"])

# commands: GPIO7 -> pin 2; pin 3 -> 1k -> j25 (RJ50 7)
wire(hole(3, "h"), hole(17, "h"), TX, bend=-0.02)
resistor(hole(18, "h"), hole(25, "h"), "1k", ["#8b4513", "#222", "#d62728"])

# height: RJ50 8 -> j10; 10k across the channel to node col 10 top; node -> GPIO4; 10k + 4.7k to GND
resistor(hole(10, "e"), hole(10, "f"), "10k", ["#8b4513", "#222", "#ff8c00"])
wire(hole(4, "b"), hole(10, "b"), RX, bend=0.12)
resistor(hole(10, "c"), hole(13, "c"), "10k", ["#8b4513", "#222", "#ff8c00"])
resistor(hole(13, "b"), hole(13, "T-"), "4.7k", ["#ffd700", "#8a2be2", "#d62728"])

# RJ50 breakout below the board
bx, by = 600, 820
rect(bx, by, 560, 150, "#e9e9e4", "#444", 10)
t(bx + 280, by + 140, "RJ50 breakout (plugs into the desk's free port)", 14, "middle", "bold")
pins = {}
for i in range(1, 11):
    px = bx + 40 + (i - 1) * 53
    pins[i] = (px, by + 40)
    out.append(f'<circle cx="{px}" cy="{by + 40}" r="8" fill="#d4af37" stroke="#7a5c00" stroke-width="1.5"/>')
    used = i in (3, 7, 8, 10)
    t(px, by + 72, str(i), 15, "middle", "bold", "#222" if used else GRAY)
    t(px, by + 92, {3: "GND", 7: "cmd", 8: "height", 10: "wake", 2: "5V: no!"}.get(i, "NC"), 12, "middle", "bold" if used else "normal", "#222" if used else GRAY)
wire(pins[8], hole(10, "j"), RX, bend=-0.08)
wire(pins[7], hole(25, "j"), TX, bend=0.05)
wire(pins[3], hole(8, "B-"), GNDC, bend=0.12)
wire(pins[10], hole(28, "j"), WK, bend=-0.05)

# notes
notes = [
    ("Check first", "#222", True),
    ("With USB-C hanging off the left, the top pin row should read", "#333", False),
    ("5V  G  3.3  4  3  2  1  0 (left to right). If your board's", "#333", False),
    ("labels differ, stop and tell me before wiring.", "#333", False),
    ("", "#333", False),
    ("Wire with the RJ50 unplugged, then meter vs GND on USB power:", "#333", False),
    ("chip pin 14 ≈ 5 V, chip pin 1 ≈ 3.3 V, hole b10 (GPIO4) ≈ 0 V.", "#333", False),
]
yy = 800
for s, c, b in notes:
    if s:
        t(40, yy, s, 15 if b else 13, "start", "bold" if b else "normal", c)
    yy += 22

lg = [("command (TX)", TX), ("output enable", OE), ("height (RX)", RX), ("wake", "#c2185b"), ("+5 V", P5), ("+3.3 V", P3), ("ground", GNDC), ("", "#fff")]
for i, (label, color) in enumerate(lg):
    if not label: continue
    lx = 40 + (i % 4) * 130
    ly = 970 + (i // 4) * 26
    out.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 30}" y2="{ly}" stroke="{color}" stroke-width="6" stroke-linecap="round"/>')
    t(lx + 40, ly + 5, label, 13)

out.append("</svg>")
open(sys.argv[1], "w").write("\n".join(out) + "\n")
