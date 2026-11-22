"""Protoboard build of the dongle on an EPLZON 1.5 x 2 inch solderable breadboard: the layout and its netlist check.

The board has 17 rows of two 5-hole strips, A-E and F-J, on either side of a center gap.
Holes are named by column and row, such as "G10". Run with:

    python3 scripts/protoboard.py
"""

from collections import defaultdict

COLUMNS = "ABCDEFGHIJ"
ROWS = range(1, 18)

C3_TOP = {"C": ["5", "6", "7", "8", "9", "10", "20", "21"], "G": ["5V", "GND", "3V3", "4", "3", "2", "1", "0"]}
U2_PINS = {n: (f"E{9 + n}" if n <= 7 else f"F{24 - n}") for n in range(1, 15)}

PARTS = [
    ("R2", "10k", "C15", "C16", "pulls the command enable low"),
    ("R3", "10k", "B13", "B16", "holds GPIO6 low while the ESP is off and through its boot pull-up"),
    ("R4", "10k", "H14", "H17", "pulls the wake enable low"),
    ("R5", "100k", "I2", "I8", "holds GPIO0 low while the ESP is off"),
    ("R6", "4.7k", "H5", "H9", "height divider, top"),
    ("R7", "10k", "J2", "J5", "height divider, bottom"),
    ("C1", "100nF", "J15", "J17", "decouples the 74AHCT125"),
]

WIRES = [
    ("A2", "A13", "EN_TX", "GPIO6 to 2OE", "top"),
    ("B3", "B11", "TX", "GPIO7 to 1A", "top"),
    ("D10", "D15", "OE_TX", "1OE to 2Y", "top"),
    ("J8", "J11", "EN_WAKE", "GPIO0 to 4OE", "top"),
    ("G13", "G14", "OE_WAKE", "4Y to 3OE", "top"),
    ("H10", "H12", "+5V", "VCC to 4A", "top"),
    ("I12", "I15", "+5V", "4A to 3A", "top"),
    ("D16", "F17", "GND", "chip GND across the gap", "top"),
    ("C14", "G15", "+5V", "2A to 3A, under the board", "back"),
    ("H2", "G17", "GND", "ESP GND to chip GND, under the board", "back"),
]

EXTERNAL = [
    ("keypad", 2, "A14", "+5V", "Bipom 2, with the desk cable's 2, brown"),
    ("keypad", 3, "I17", "GND", "Bipom 3, with the desk cable's 3, red"),
    ("keypad", 7, "C12", "CMD", "Bipom 7 through a 1k in the terminal"),
    ("keypad", 8, "I9", "HEIGHT", "Bipom 8, with the desk cable's 8, purple"),
    ("keypad", 10, "I16", "WAKE", "Bipom 10 through a 1k in the terminal"),
    ("desk", 7, "B12", "CMD", "desk cable 7, blue"),
    ("desk", 10, "G16", "WAKE", "desk cable 10, white"),
]

EXPECTED = {
    "+5V": {"U2.5", "U2.9", "U2.12", "U2.14", "C1", "keypad.2"},
    "GND": {"U2.7", "U1.GND", "C1", "keypad.3", "R2", "R3", "R4", "R5", "R7"},
    "OE_TX": {"U2.1", "U2.6", "R2"},
    "TX": {"U1.7", "U2.2"},
    "CMD_DESK": {"U2.3", "desk.7", "keypad.7"},
    "EN_TX": {"U1.6", "U2.4", "R3"},
    "OE_WAKE": {"U2.10", "U2.11", "R4"},
    "EN_WAKE": {"U1.0", "U2.13", "R5"},
    "WAKE_DESK": {"U2.8", "desk.10", "keypad.10"},
    "HEIGHT": {"keypad.8", "R6"},
    "RX": {"U1.3", "R6", "R7"},
}


def strip_of(hole: str) -> str:
    column, row = hole[0], int(hole[1:])
    return f"{'L' if column <= 'E' else 'R'}{row}"


def under_c3(hole: str) -> bool:
    column, row = hole[0], int(hole[1:])
    return (row <= 8 and column in "DEF") or (row == 9 and column in "CDEFG")


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
    for a, b, *_ in WIRES:
        place(a, f"wire {a}-{b}")
        place(b, f"wire {a}-{b}")
        union(strip_of(a), strip_of(b))
    for side, contact, hole, *_ in EXTERNAL:
        place(hole, f"{side}.{contact}")

    shared = {h: m for h, m in used.items() if len(m) > 1}
    assert not shared, f"holes used twice: {shared}"
    spans = [(a, b, name) for name, _, a, b, _ in PARTS] + [
        (a, b, f"wire {a}-{b}") for a, b, _, _, layer in WIRES if layer == "top"
    ]
    for a, b, name in spans:
        if a[0] == b[0]:
            lo, hi = sorted((int(a[1:]), int(b[1:])))
            for row in range(lo + 1, hi):
                covered = f"{a[0]}{row}"
                assert covered not in used, f"{name} lies across {covered}, used by {used[covered]}"

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
    unused_c3 = {"U1.5", "U1.8", "U1.9", "U1.10", "U1.20", "U1.21", "U1.5V", "U1.3V3", "U1.4", "U1.2", "U1.1"}
    for found in nets.values():
        if found & unused_c3:
            assert found <= unused_c3 | {p for p, *_ in PARTS} | {f"U1.{x}" for x in ()}, f"unused pin touched: {found}"
    print("layout checks out:", len(PARTS), "parts,", len(WIRES), "wires,", len(EXTERNAL), "external wires")


if __name__ == "__main__":
    check()
