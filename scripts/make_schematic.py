"""Write the dongle's KiCad schematic from a plain-Python netlist.

Run with: python3 scripts/make_schematic.py hardware/kaidi-desk.kicad_sch
"""

import itertools
import os
import re
import sys
import uuid
from pathlib import Path

LIBS = os.environ.get("KICAD_SHARE", "/Applications/KiCad/KiCad.app/Contents/SharedSupport") + "/symbols"
GRID = 2.54
STUB = 2 * GRID


IDS = itertools.count()


def uid():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kaidi-desk/schematic/{next(IDS)}"))


def lib_block(lib, name):
    text = Path(f"{LIBS}/{lib}.kicad_sym").read_text()
    start = text.find(f'(symbol "{name}"')
    depth = 0
    for end in range(start, len(text)):
        if text[end] == "(":
            depth += 1
        elif text[end] == ")":
            depth -= 1
            if depth == 0:
                return text[start : end + 1]
    raise KeyError(name)


def embed(lib, name, as_name=None):
    block = lib_block(lib, name)
    block = block.replace(f'(symbol "{name}"', f'(symbol "{lib}:{as_name or name}"', 1)
    if as_name:
        block = block.replace(f'(symbol "{name}_', f'(symbol "{as_name}_')
    return block


def module_symbol():
    left = ["5V", "GND", "3V3", "GPIO4", "GPIO3", "GPIO2", "GPIO1", "GPIO0"]
    right = ["GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO20", "GPIO21"]
    pins = []
    for i, name in enumerate(left):
        kind = {"5V": "power_in", "GND": "power_in", "3V3": "power_out"}.get(name, "bidirectional")
        pins.append((kind, -12.7, 8.89 - i * GRID, 0, name, str(i + 1)))
    for i, name in enumerate(right):
        pins.append(("bidirectional", 12.7, 8.89 - i * GRID, 180, name, str(i + 9)))
    body = "".join(
        f'(pin {k} line (at {x} {y} {a}) (length 3.81) (name "{n}" (effects (font (size 1.27 1.27)))) '
        f'(number "{num}" (effects (font (size 1.27 1.27)))))'
        for k, x, y, a, n, num in pins
    )
    return (
        '(symbol "kaidi:ESP32-C3_SuperMini" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)'
        '(property "Reference" "U" (at 0 13.97 0) (effects (font (size 1.27 1.27))))'
        '(property "Value" "ESP32-C3_SuperMini" (at 0 -13.97 0) (effects (font (size 1.27 1.27))))'
        '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        '(symbol "ESP32-C3_SuperMini_0_1" (rectangle (start -8.89 11.43) (end 8.89 -11.43) '
        "(stroke (width 0.254) (type default)) (fill (type background))))"
        f'(symbol "ESP32-C3_SuperMini_1_1" {body}))'
    )


def converter_symbol():
    pins = [
        ("power_in", -10.16, 2.54, 0, "Vin", "1"),
        ("power_in", -10.16, -2.54, 0, "GND", "2"),
        ("power_out", 10.16, 2.54, 180, "+Vo", "6"),
        ("passive", 10.16, -2.54, 180, "0V", "4"),
    ]
    body = "".join(
        f'(pin {k} line (at {x} {y} {a}) (length 2.54) (name "{n}" (effects (font (size 1.27 1.27)))) '
        f'(number "{num}" (effects (font (size 1.27 1.27)))))'
        for k, x, y, a, n, num in pins
    )
    return (
        '(symbol "kaidi:B0505S-2WR3" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)'
        '(property "Reference" "U" (at 0 7.62 0) (effects (font (size 1.27 1.27))))'
        '(property "Value" "B0505S-2WR3" (at 0 -7.62 0) (effects (font (size 1.27 1.27))))'
        '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        '(symbol "B0505S-2WR3_0_1" (rectangle (start -7.62 5.08) (end 7.62 -5.08) '
        "(stroke (width 0.254) (type default)) (fill (type background)))"
        "(polyline (pts (xy 0 5.08) (xy 0 -5.08)) (stroke (width 0.254) (type dash)) (fill (type none))))"
        f'(symbol "B0505S-2WR3_1_1" {body}))'
    )


def pins_of(block):
    found = {}
    for m in re.finditer(r'\(symbol "[^"]*_(\d+)_\d+"([\s\S]*?)(?=\(symbol "[^"]*_\d+_\d+"|\Z)', block):
        unit = int(m.group(1))
        for p in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)[\s\S]*?\(number "([^"]*)"', m.group(2)):
            found[(unit, p.group(4))] = (float(p.group(1)), float(p.group(2)), int(p.group(3)))
    return found


SYMBOLS = {
    "Device:R": embed("Device", "R"),
    "Device:C": embed("Device", "C"),
    "Device:C_Polarized": embed("Device", "C_Polarized"),
    "Device:D_Schottky": embed("Device", "D_Schottky"),
    "Connector_Generic:Conn_01x06": embed("Connector_Generic", "Conn_01x06"),
    "kaidi:B0505S-2WR3": converter_symbol(),
    "74xx:74AHCT125": embed("74xx", "74LS125", "74AHCT125"),
    "Connector_Generic:Conn_01x10": embed("Connector_Generic", "Conn_01x10"),
    "power:+5V": embed("power", "+5V"),
    "power:GND": embed("power", "GND"),
    "power:PWR_FLAG": embed("power", "PWR_FLAG"),
    "kaidi:ESP32-C3_SuperMini": module_symbol(),
}
PINS = {name: pins_of(block) for name, block in SYMBOLS.items()}

FOOTPRINTS = {
    "R": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
    "C": "Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm",
    "U2": "Package_DIP:DIP-14_W7.62mm_Socket",
    "U1": "kaidi:ESP32-C3_SuperMini",
    "J": "kaidi:RJ50_Amphenol_54602-910_Horizontal",
    "J3": "kaidi:USB-C_Breakout_Cermant_1x06",
    "U3": "kaidi:Converter_DCDC_Mornsun_B_S-2WR3_SIP",
    "C2": "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
    "C3": "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
    "D1": "Diode_THT:D_DO-41_SOD81_P5.08mm_Vertical_AnodeUp",
}

out = []
instances = []
root = uid()


def place(
    lib_id,
    ref,
    value,
    x,
    y,
    unit=1,
    mirror=False,
    footprint="",
    ref_at=(0, -2.54),
    val_at=(0, 2.54),
    hide_ref=False,
    hide_val=False,
    justify="",
):
    u = uid()
    hr = " (hide yes)" if hide_ref or ref.startswith("#") else ""
    hv = " (hide yes)" if hide_val else ""
    j = f" (justify {justify})" if justify else ""
    pins = [num for (un, num) in PINS[lib_id] if un in (unit, 0)]
    mirror_s = "(mirror y)" if mirror else ""
    out.append(
        f'(symbol (lib_id "{lib_id}") (at {x} {y} 0) {mirror_s} (unit {unit}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{u}")'
        f'(property "Reference" "{ref}" (at {x + ref_at[0]} {y + ref_at[1]} 0) (effects (font (size 1.27 1.27)){j}){hr})'
        f'(property "Value" "{value}" (at {x + val_at[0]} {y + val_at[1]} 0) (effects (font (size 1.27 1.27)){j}){hv})'
        f'(property "Footprint" "{footprint}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        f'(property "Datasheet" "" (at {x} {y} 0) (effects (font (size 1.27 1.27)) (hide yes)))'
        + "".join(f'(pin "{p}" (uuid "{uid()}"))' for p in sorted(set(pins)))
        + f'(instances (project "kaidi-desk" (path "/{root}" (reference "{ref}") (unit {unit})))))'
    )
    return lambda num: pin_point(lib_id, unit, num, x, y, mirror)


def pin_point(lib_id, unit, num, x, y, mirror):
    px, py, angle = PINS[lib_id].get((unit, num)) or PINS[lib_id][(0, num)]
    if mirror:
        px, angle = -px, {0: 180, 180: 0}.get(angle, angle)
    outward = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[angle]
    return (round(x + px, 2), round(y - py, 2)), outward


def wire(a, b):
    out.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{uid()}"))')


power_count = [0]


def power(kind, at):
    power_count[0] += 1
    place(f"power:{kind}", f"#PWR0{power_count[0]:02d}", kind, at[0], at[1])


def net(pin, name, stub=STUB):
    (x, y), (dx, dy) = pin
    end = (round(x + dx * stub, 2), round(y + dy * stub, 2))
    wire((x, y), end)
    if name in ("+5V", "GND"):
        drop = (end[0], round(end[1] + (GRID if name == "GND" else -GRID), 2)) if dy == 0 else end
        if drop != end:
            wire(end, drop)
        power(name, drop)
        return
    angle = 180 if dx < 0 else 0 if dx > 0 else (90 if dy < 0 else 270)
    justify = "right" if angle in (180, 270) else "left"
    out.append(
        f'(label "{name}" (at {end[0]} {end[1]} {angle}) (effects (font (size 1.27 1.27)) (justify {justify} bottom)) (uuid "{uid()}"))'
    )


def no_connect(pin):
    (x, y), _ = pin
    out.append(f'(no_connect (at {x} {y}) (uuid "{uid()}"))')


def text(s, x, y, size=1.8):
    out.append(
        f'(text "{s}" (exclude_from_sim no) (at {x} {y} 0) (effects (font (size {size} {size}) (thickness 0.3) bold) (justify left)) (uuid "{uid()}"))'
    )


text("Keypad and desk", 22.86, 27.94)
for ref, label, y in (("J1", "Keypad (RJ50)", 55.88), ("J2", "Desk (RJ50)", 116.84)):
    p = place(
        "Connector_Generic:Conn_01x10",
        ref,
        label,
        38.1,
        y,
        mirror=True,
        footprint=FOOTPRINTS["J"],
        ref_at=(0, -15.24),
        val_at=(0, -12.7),
    )
    side = "KEYPAD" if ref == "J1" else "DESK"
    for num in ("1", "4", "5", "6", "9"):
        no_connect(p(num))
    net(p("2"), "+5V")
    net(p("3"), "GND")
    net(p("7"), f"CMD_{side}")
    net(p("8"), "HEIGHT")
    net(p("10"), f"WAKE_{side}")
flag = place("power:PWR_FLAG", "#FLG01", "PWR_FLAG", 25.4, 160.02)
net(flag("1"), "+5V")
flag = place("power:PWR_FLAG", "#FLG02", "PWR_FLAG", 45.72, 160.02)
net(flag("1"), "GND")

text("Keypad path: 1k in series, so the buffer overrides it only while sending", 76.2, 27.94, 1.5)
for ref, a, b, x in (("R1", "CMD_KEYPAD", "CMD_DESK", 96.52), ("R2", "WAKE_KEYPAD", "WAKE_DESK", 132.08)):
    p = place(
        "Device:R",
        ref,
        "1k",
        x,
        63.5,
        footprint=FOOTPRINTS["R"],
        ref_at=(2.54, -1.27),
        val_at=(2.54, 1.27),
        justify="left",
    )
    net(p("1"), a)
    net(p("2"), b)

text("74AHCT125 on desk 5 V: gates A-B drive the desk; C-D hold them off unless the ESP asks", 76.2, 101.6, 1.5)
gates = [
    (1, 116.84, 124.46, "TX", "OE_TX", "CMD_DESK"),
    (2, 154.94, 124.46, "+5V", "OE_WAKE", "WAKE_DESK"),
    (3, 116.84, 152.4, "+5V", "EN_TX", "OE_TX"),
    (4, 154.94, 152.4, "+5V", "EN_WAKE", "OE_WAKE"),
]
ab = {1: ("2", "1", "3"), 2: ("5", "4", "6"), 3: ("9", "10", "8"), 4: ("12", "13", "11")}
for unit, x, y, a, oe, yy in gates:
    p = place(
        "74xx:74AHCT125",
        "U2",
        "74AHCT125",
        x,
        y,
        unit=unit,
        footprint=FOOTPRINTS["U2"],
        ref_at=(0, -5.08),
        hide_val=True,
    )
    pa, poe, py = ab[unit]
    net(p(pa), a)
    net(p(poe), oe)
    net(p(py), yy)
p = place(
    "74xx:74AHCT125",
    "U2",
    "74AHCT125",
    91.44,
    137.16,
    unit=5,
    footprint=FOOTPRINTS["U2"],
    ref_at=(5.08, -1.27),
    val_at=(5.08, 1.27),
    justify="left",
)
net(p("14"), "+5V")
net(p("7"), "GND")
p = place(
    "Device:C",
    "C1",
    "100n",
    78.74,
    137.16,
    footprint=FOOTPRINTS["C"],
    ref_at=(-2.54, -1.27),
    val_at=(-2.54, 1.27),
    justify="right",
)
net(p("1"), "+5V")
net(p("2"), "GND")

text("Fail-safe defaults", 185.42, 104.14)
for ref, value, a, x, y in (
    ("R3", "10k", "OE_TX", 190.5, 124.46),
    ("R4", "10k", "OE_WAKE", 213.36, 124.46),
    ("R5", "10k", "EN_TX", 190.5, 157.48),
    ("R6", "100k", "EN_WAKE", 213.36, 157.48),
):
    p = place(
        "Device:R",
        ref,
        value,
        x,
        y,
        footprint=FOOTPRINTS["R"],
        ref_at=(2.54, -1.27),
        val_at=(2.54, 1.27),
        justify="left",
    )
    net(p("1"), a)
    net(p("2"), "GND")

text("Dividers (5 V to 3.0 V)", 182.88, 27.94)
for top, bottom, a, mid, x in (("R7", "R8", "HEIGHT", "RX", 190.5), ("R9", "R10", "CMD_KEYPAD", "SENSE", 210.82)):
    pt = place(
        "Device:R",
        top,
        "10k",
        x,
        53.34,
        footprint=FOOTPRINTS["R"],
        ref_at=(2.54, -1.27),
        val_at=(2.54, 1.27),
        justify="left",
    )
    pb = place(
        "Device:R",
        bottom,
        "15k",
        x,
        71.12,
        footprint=FOOTPRINTS["R"],
        ref_at=(2.54, -1.27),
        val_at=(2.54, 1.27),
        justify="left",
    )
    net(pt("1"), a)
    (x1, y1), _ = pt("2")
    (x2, y2), _ = pb("1")
    wire((x1, y1), (x2, y2))
    jy = round((y1 + y2) / 2, 2)
    jy = round(round(jy / 1.27) * 1.27, 2)
    out.append(f'(junction (at {x1} {jy}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')
    net(((x1, jy), (1, 0)), mid)
    net(pb("2"), "GND")

text("ESP32-C3 SuperMini (5V from the isolated input)", 233.68, 27.94)
p = place(
    "kaidi:ESP32-C3_SuperMini",
    "U1",
    "ESP32-C3 SuperMini",
    254.0,
    63.5,
    footprint=FOOTPRINTS["U1"],
    ref_at=(0, -13.97),
    val_at=(0, 13.97),
)
uses = {"1": "ESP_5V", "2": "GND", "4": "RX", "5": "SENSE", "10": "EN_TX", "11": "TX", "14": "EN_WAKE"}
for num in map(str, range(1, 17)):
    if num in uses:
        net(p(num), uses[num], stub=10.16 if num in ("4", "5") else STUB)
    else:
        no_connect(p(num))

text("Isolated USB-C power input: the charger never shares a ground with the desk", 22.86, 170.18, 1.5)
p = place(
    "Connector_Generic:Conn_01x06",
    "J3",
    "USB-C breakout",
    38.1,
    185.42,
    mirror=True,
    footprint=FOOTPRINTS["J3"],
    ref_at=(0, -10.16),
    val_at=(0, -7.62),
)
net(p("1"), "VIN_ISO")
net(p("2"), "GND_ISO")
for num in ("3", "4", "5", "6"):
    no_connect(p(num))
p = place(
    "Device:C_Polarized",
    "C3",
    "10u",
    63.5,
    187.96,
    footprint=FOOTPRINTS["C3"],
    ref_at=(2.54, -1.27),
    val_at=(2.54, 1.27),
    justify="left",
)
net(p("1"), "VIN_ISO")
net(p("2"), "GND_ISO")
p = place(
    "kaidi:B0505S-2WR3",
    "U3",
    "B0505S-2WR3",
    96.52,
    185.42,
    footprint=FOOTPRINTS["U3"],
    ref_at=(0, -7.62),
    val_at=(0, 7.62),
)
net(p("1"), "VIN_ISO")
net(p("2"), "GND_ISO")
net(p("6"), "VOUT")
net(p("4"), "GND")
p = place(
    "Device:C_Polarized",
    "C2",
    "220u",
    127.0,
    187.96,
    footprint=FOOTPRINTS["C2"],
    ref_at=(2.54, -1.27),
    val_at=(2.54, 1.27),
    justify="left",
)
net(p("1"), "VOUT")
net(p("2"), "GND")
p = place(
    "Device:D_Schottky",
    "D1",
    "1N5819",
    157.48,
    182.88,
    footprint=FOOTPRINTS["D1"],
    ref_at=(0, -2.54),
    val_at=(0, 2.54),
)
net(p("2"), "VOUT")
net(p("1"), "ESP_5V")
for ref, name, x in (("#FLG03", "VIN_ISO", 48.26), ("#FLG04", "GND_ISO", 58.42), ("#FLG05", "ESP_5V", 142.24)):
    flag = place("power:PWR_FLAG", ref, "PWR_FLAG", x, 190.5, hide_val=True)
    net(flag("1"), name)

body = "\n".join(out)
lib = "\n".join(SYMBOLS.values())
sch = f"""(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{root}") (paper "A4")
(title_block (title "Kaidi Desk Dongle") (date "2026-11-21") (company "esphome-kaidi-desk")
 (comment 1 "Inline between the keypad and a Kaidi KDDY094 control box") (comment 2 "github.com/clintval/esphome-kaidi-desk"))
(lib_symbols {lib})
{body}
(sheet_instances (path "/" (page "1"))))
"""
Path(sys.argv[1]).write_text(sch)
