"""Rev 4 dongle on an EPLZON 1.5 x 2 inch solderable breadboard: layout, netlist check and drawing.

The board has 17 rows of two 5-hole strips, A-E and F-J, on either side of a center gap.
Holes are named by column and row, such as "G10". Run with:

    python3 scripts/protoboard.py docs/protoboard.svg
"""

import sys
from collections import defaultdict

COLUMNS = "ABCDEFGHIJ"
ROWS = range(1, 18)

C3_TOP = {"C": ["5", "6", "7", "8", "9", "10", "20", "21"], "G": ["5V", "GND", "3V3", "4", "3", "2", "1", "0"]}
U2_PINS = {n: (f"E{9 + n}" if n <= 7 else f"F{24 - n}") for n in range(1, 15)}

PARTS = [
    ("R1", "1k", "A9", "A12", "command, keypad to desk"),
    ("R2", "1k", "A15", "A17", "wake, keypad to desk"),
    ("R3", "10k", "I16", "I17", "pulls the command enable low"),
    ("R4", "10k", "A13", "A16", "pulls the wake enable low"),
    ("R5", "100k", "H14", "H17", "holds GPIO6 low while the ESP is off"),
    ("R6", "100k", "G11", "G17", "holds GPIO10 low while the ESP is off"),
    ("R7", "10k", "J9", "J4", "height divider, top"),
    ("R8", "22k", "I4", "I2", "height divider, bottom"),
    ("R9", "47k", "H4", "H2", "height divider, bottom (parallel with R8)"),
    ("C1", "100nF", "J15", "J17", "decouples the 74AHCT125"),
]

WIRES = [
    ("B3", "B11", "TX: GPIO7 to 1A"),
    ("B2", "J14", "GPIO6 to 3OE"),
    ("B6", "J11", "GPIO10 to 4OE"),
    ("B10", "J16", "1OE to 3Y"),
    ("D13", "G13", "2OE to 4Y"),
    ("D14", "G15", "+5V to 2A"),
    ("H10", "H12", "+5V to 4A"),
    ("I12", "I15", "+5V to 3A"),
    ("D16", "F17", "GND across the gap"),
    ("J2", "C16", "ESP GND to chip GND"),
]

EXTERNAL = [
    ("keypad", 2, "I10", "+5V"),
    ("keypad", 3, "B16", "GND"),
    ("keypad", 7, "B9", "CMD"),
    ("keypad", 8, "I9", "HEIGHT"),
    ("keypad", 10, "B17", "WAKE"),
    ("desk", 2, "G10", "+5V"),
    ("desk", 3, "B16", "GND"),
    ("desk", 7, "B12", "CMD"),
    ("desk", 8, "H9", "HEIGHT"),
    ("desk", 10, "B15", "WAKE"),
]

EXPECTED = {
    "+5V": {"U2.5", "U2.9", "U2.12", "U2.14", "C1", "keypad.2", "desk.2"},
    "GND": {"U2.7", "U1.GND", "C1", "keypad.3", "desk.3", "R3", "R4", "R5", "R6", "R8", "R9"},
    "OE1": {"U2.1", "U2.8", "R3"},
    "OE2": {"U2.4", "U2.11", "R4"},
    "TX": {"U1.7", "U2.2"},
    "EN_TX": {"U1.6", "U2.10", "R5"},
    "EN_WAKE": {"U1.10", "U2.13", "R6"},
    "CMD_DESK": {"U2.3", "desk.7", "R1"},
    "CMD_KEYPAD": {"keypad.7", "R1"},
    "WAKE_DESK": {"U2.6", "desk.10", "R2"},
    "WAKE_KEYPAD": {"keypad.10", "R2"},
    "HEIGHT": {"keypad.8", "desk.8", "R7"},
    "GPIO4": {"U1.4", "R7", "R8", "R9"},
}


def strip_of(hole: str) -> str:
    column, row = hole[0], int(hole[1:])
    return f"{'L' if column <= 'E' else 'R'}{row}"


def under_c3(hole: str) -> bool:
    column, row = hole[0], int(hole[1:])
    return row <= 8 and column in "DEF"


def check() -> None:
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    used = defaultdict(list)
    members = defaultdict(set)

    def place(hole, member):
        assert hole[0] in COLUMNS and int(hole[1:]) in ROWS, hole
        assert not under_c3(hole) or member.startswith("U1."), f"{member} at {hole} is under the C3"
        used[hole].append(member)
        members[strip_of(hole)].add(member)

    for column, labels in C3_TOP.items():
        for row, label in enumerate(labels, start=1):
            place(f"{column}{row}", f"U1.{label}")
    for pin, hole in U2_PINS.items():
        place(hole, f"U2.{pin}")
    for name, _, a, b, _ in PARTS:
        place(a, name)
        place(b, name)
    for a, b, _ in WIRES:
        place(a, f"wire {a}-{b}")
        place(b, f"wire {a}-{b}")
        union(strip_of(a), strip_of(b))
    for side, contact, hole, _ in EXTERNAL:
        place(hole, f"{side}.{contact}")

    shared = {h: m for h, m in used.items() if len(m) > 1}
    assert set(shared) == {"B16"}, f"holes used twice: {shared}"

    nets = defaultdict(set)
    for strip, things in members.items():
        nets[find(strip)] |= {t for t in things if not t.startswith("wire")}
    for net, wanted in EXPECTED.items():
        matches = [found for found in nets.values() if wanted <= found]
        assert len(matches) == 1, f"{net}: no strip group holds {sorted(wanted)}"
        two_ended = {p for p, *_ in PARTS}
        extra = {m for m in matches[0] - wanted if m not in two_ended and not m.startswith("U1.")}
        assert not extra, f"{net} also touches {sorted(extra)}"
    for found in nets.values():
        owners = [net for net, wanted in EXPECTED.items() if wanted & found - {p for p, *_ in PARTS}]
        assert len(owners) <= 1, f"strip group shorts {owners}: {sorted(found)}"
    unused_c3 = {"U1.5", "U1.8", "U1.9", "U1.20", "U1.21", "U1.5V", "U1.3V3", "U1.3", "U1.2", "U1.1", "U1.0"}
    for found in nets.values():
        if found & unused_c3:
            assert found <= unused_c3 | {p for p, *_ in PARTS} | {f"U1.{x}" for x in ()}, f"unused pin touched: {found}"
    print("layout checks out:", len(PARTS), "parts,", len(WIRES), "wires,", len(EXTERNAL), "external wires")


PX, X0, Y0 = 40, 360, 210
MASK, MASK_EDGE, STRIP, GOLD, GOLD_EDGE, SILK = "#14855a", "#0d5c3e", "#1f9a6a", "#e5b24f", "#a47a2a", "#f3f7f4"
FONT = "ui-monospace, 'JetBrains Mono', Menlo, Consolas, monospace"
WIRE_COLORS = {"TX": "#2f7de1", "GPIO6": "#9b59b6", "GPIO10": "#c2185b", "1OE": "#9b59b6", "2OE": "#c2185b",
               "+5V": "#e74c3c", "GND": "#2b2b2b", "ESP": "#2b2b2b"}
NET_COLORS = {"+5V": "#e74c3c", "GND": "#2b2b2b", "CMD": "#2f7de1", "HEIGHT": "#27ae60", "WAKE": "#c2185b"}


def xy(hole):
    column, row = hole[0], int(hole[1:])
    i = COLUMNS.index(column)
    return X0 + i * PX + (2 * PX if i >= 5 else 0), Y0 + (row - 1) * PX


def render(path):
    out = []
    add = out.append

    def text(x, y, s, size=13, anchor="middle", fill="#222", weight="600", font=FONT):
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{s}</text>')

    W, H = 1720, 1040
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add('<defs><filter id="sh" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.28"/></filter></defs>')
    add(f'<rect width="{W}" height="{H}" fill="#f6f4ef"/>')
    text(40, 52, "Kaidi desk dongle, rev 4", 26, "start", "#1d1d1d", "800")
    text(40, 80, "EPLZON 1.5 x 2 in solderable breadboard, top view. Each row is two copper strips on the back: A-E and F-J.", 14, "start", "#555", "500")

    bx1, by1 = X0 - 80, Y0 - 80
    bw, bh = 600, 800
    add(f'<rect x="{bx1}" y="{by1}" width="{bw}" height="{bh}" rx="26" fill="{MASK}" stroke="{MASK_EDGE}" stroke-width="3" filter="url(#sh)"/>')
    for hx, hy in ((bx1 + 30, by1 + 30), (bx1 + bw - 30, by1 + 30), (bx1 + 30, by1 + bh - 30), (bx1 + bw - 30, by1 + bh - 30)):
        add(f'<circle cx="{hx}" cy="{hy}" r="13" fill="#bfe6cf" stroke="#9fd2b4" stroke-width="2"/><circle cx="{hx}" cy="{hy}" r="7" fill="#f6f4ef"/>')
    gx = (xy("E1")[0] + xy("F1")[0]) / 2
    for gy in (xy("A1")[1] - 6, xy("A17")[1] + 6):
        add(f'<circle cx="{gx}" cy="{gy}" r="15" fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="2"/><circle cx="{gx}" cy="{gy}" r="9" fill="#2a2a2a"/>')
    for row in ROWS:
        for a, b in (("A", "E"), ("F", "J")):
            x1, y = xy(f"{a}{row}")
            x2, _ = xy(f"{b}{row}")
            add(f'<rect x="{x1 - 11}" y="{y - 11}" width="{x2 - x1 + 22}" height="22" rx="11" fill="{STRIP}"/>')
        text(X0 - 40, xy(f"A{row}")[1] + 5, str(row), 13, fill=SILK, weight="700")
        text(xy("J1")[0] + 40, xy(f"J{row}")[1] + 5, str(row), 13, fill=SILK, weight="700")
    for column in COLUMNS:
        x, _ = xy(f"{column}1")
        text(x, Y0 - 34, column, 14, fill=SILK, weight="700")
        text(x, xy("A17")[1] + 44, column, 14, fill=SILK, weight="700")
    for column in COLUMNS:
        for row in ROWS:
            x, y = xy(f"{column}{row}")
            add(f'<circle cx="{x}" cy="{y}" r="8" fill="{GOLD}" stroke="{GOLD_EDGE}" stroke-width="1.2"/><circle cx="{x}" cy="{y}" r="3.6" fill="#163a2a"/>')

    for a, b, label in WIRES:
        (x1, y1), (x2, y2) = xy(a), xy(b)
        key = label.split(":")[0].split(" ")[0]
        color = WIRE_COLORS.get(key, "#2b2b2b")
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        bend = 0.18 if abs(dx) > 2 * PX and abs(dy) > 2 * PX else 0.0
        cx, cy = mx - dy * bend, my + dx * bend
        add(f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" fill="none" stroke="#00000040" stroke-width="10" stroke-linecap="round"/>')
        add(f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" fill="none" stroke="{color}" stroke-width="7" stroke-linecap="round"/>')
        for x, y in ((x1, y1), (x2, y2)):
            add(f'<circle cx="{x}" cy="{y}" r="5" fill="#fff" stroke="{color}" stroke-width="3"/>')

    c1x, c1y = xy("C1")
    c2x, c2y = xy("G8")
    add(f'<rect x="{c1x - 26}" y="{c1y - 46}" width="{c2x - c1x + 52}" height="{c2y - c1y + 70}" rx="12" fill="#1c2633" opacity="0.93"/>')
    add(f'<rect x="{(c1x + c2x) / 2 - 26}" y="{c1y - 70}" width="52" height="40" rx="9" fill="#b9c1c9" stroke="#6b737b" stroke-width="2"/>')
    text((c1x + c2x) / 2, c1y - 46, "USB-C", 11, fill="#30363c", weight="800")
    text((c1x + c2x) / 2, (c1y + c2y) / 2 - 4, "ESP32-C3", 16, fill="#e8eef5", weight="800")
    text((c1x + c2x) / 2, (c1y + c2y) / 2 + 16, "SuperMini", 12, fill="#c9d4e0", weight="600")
    text((c1x + c2x) / 2, (c1y + c2y) / 2 + 34, "labels up", 11, fill="#9fb0c2", weight="500")
    for column, labels in C3_TOP.items():
        for row, label in enumerate(labels, start=1):
            x, y = xy(f"{column}{row}")
            add(f'<circle cx="{x}" cy="{y}" r="9" fill="{GOLD}" stroke="#fff" stroke-width="2"/>')
            text(x + (16 if column == "C" else -16), y + 4, label, 11, "start" if column == "C" else "end", "#e8eef5", "700")

    (ux1, uy1), (ux2, uy2) = xy("E10"), xy("F16")
    add(f'<rect x="{ux1 + 8}" y="{uy1 - 22}" width="{ux2 - ux1 - 16}" height="{uy2 - uy1 + 44}" rx="6" fill="#1a1a1a"/>')
    add(f'<path d="M {(ux1 + ux2) / 2 - 12} {uy1 - 22} a 12 12 0 0 0 24 0" fill="{MASK}"/>')
    add(f'<text x="{(ux1 + ux2) / 2}" y="{(uy1 + uy2) / 2}" font-family="{FONT}" font-size="13" font-weight="800" text-anchor="middle" fill="#ddd" transform="rotate(90 {(ux1 + ux2) / 2} {(uy1 + uy2) / 2})">74AHCT125</text>')
    for pin, hole in U2_PINS.items():
        x, y = xy(hole)
        add(f'<rect x="{x - 7}" y="{y - 7}" width="14" height="14" rx="2" fill="#cfd3d6" stroke="#fff" stroke-width="1.5"/>')
        text(x + (16 if pin <= 7 else -16), y + 4, str(pin), 10, "start" if pin <= 7 else "end", "#ddd", "700")

    bands = {"1k": ["#7b3f00", "#111", "#d62728"], "10k": ["#7b3f00", "#111", "#ff8c00"], "22k": ["#d62728", "#d62728", "#ff8c00"],
             "47k": ["#f1c40f", "#8e44ad", "#ff8c00"], "100k": ["#7b3f00", "#111", "#f1c40f"]}
    for name, value, a, b, _ in PARTS:
        (x1, y1), (x2, y2) = xy(a), xy(b)
        add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#9a9a9a" stroke-width="3"/>')
        for x, y in ((x1, y1), (x2, y2)):
            add(f'<circle cx="{x}" cy="{y}" r="4.5" fill="#9a9a9a"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if name.startswith("C"):
            add(f'<circle cx="{mx}" cy="{my}" r="11" fill="#e2b85a" stroke="#8a6a3a" stroke-width="1.5"/>')
        else:
            vertical = abs(y2 - y1) >= abs(x2 - x1)
            w, h = (14, 30) if vertical else (30, 14)
            add(f'<rect x="{mx - w / 2}" y="{my - h / 2}" width="{w}" height="{h}" rx="6" fill="#e6d3a8" stroke="#8a6d3b" stroke-width="1.2"/>')
            for i, color in enumerate(bands[value]):
                if vertical:
                    add(f'<rect x="{mx - 7}" y="{my - 10 + i * 6}" width="14" height="3" fill="{color}"/>')
                else:
                    add(f'<rect x="{mx - 10 + i * 6}" y="{my - 7}" width="3" height="14" fill="{color}"/>')
        side = 1 if x1 > gx else -1
        text(mx + side * 20, my + 4, name, 11, "start" if side > 0 else "end", SILK, "800")

    lx = bx1 - 10
    rx = bx1 + bw + 10
    tags = defaultdict(list)
    for side, contact, hole, net in EXTERNAL:
        x, y = xy(hole)
        color = NET_COLORS[net]
        left = hole[0] <= "E"
        ex = lx if left else rx
        add(f'<path d="M {x} {y} L {ex} {y}" fill="none" stroke="{color}" stroke-width="5" stroke-dasharray="2 7" stroke-linecap="round"/>')
        add(f'<circle cx="{x}" cy="{y}" r="6" fill="#fff" stroke="{color}" stroke-width="3"/>')
        tags[(left, y)].append((side, contact, net, color))
    for (left, y), items in tags.items():
        net, color = items[0][2], items[0][3]
        who = " + ".join(f"{'keypad' if side == 'keypad' else 'desk'} {contact}" for side, contact, _, _ in items)
        ex = lx if left else rx
        text(ex + (-8 if left else 8), y + 4, f"{net}  {who}", 12, "end" if left else "start", color, "800")

    tx = 1080
    text(tx, 140, "Parts", 18, "start", "#1d1d1d", "800")
    y = 166
    for name, value, a, b, why in PARTS:
        text(tx, y, f"{name:<3} {value:<5} {a:>3} - {b:<3}", 13, "start", "#222", "700")
        text(tx + 250, y, why, 12, "start", "#666", "500")
        y += 22
    text(tx, y + 6, "U1  ESP32-C3   columns C and G, rows 1-8, USB-C off the top", 13, "start", "#222", "700")
    text(tx, y + 28, "U2  74AHCT125  columns E and F, rows 10-16, notch at row 10", 13, "start", "#222", "700")
    y += 70
    text(tx, y, "Jumper wires", 18, "start", "#1d1d1d", "800")
    y += 26
    for a, b, why in WIRES:
        text(tx, y, f"{a:>3} - {b:<3}", 13, "start", "#222", "700")
        text(tx + 110, y, why, 12, "start", "#666", "500")
        y += 22
    y += 18
    text(tx, y, "Before soldering", 18, "start", "#1d1d1d", "800")
    for i, line in enumerate((
        "Dry-fit the C3 and the chip: both straddle the center gap.",
        "Column G must read 5V, G, 3.3, 4 from the USB-C end.",
        "Long jumpers run on the back, insulated.",
        "Meter before plugging in: no 5V-GND short, chip pin 14 = 5V.",
    )):
        text(tx, y + 26 + i * 22, line, 12.5, "start", "#444", "500")

    add("</svg>")
    with open(path, "w") as handle:
        handle.write("\n".join(out) + "\n")


if __name__ == "__main__":
    check()
    if len(sys.argv) > 1:
        render(sys.argv[1])
