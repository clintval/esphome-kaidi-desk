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
    "Device:D_TVS": embed("Device", "D_TVS"),
    "Device:LED": embed("Device", "LED"),
    "Device:Polyfuse": embed("Device", "Polyfuse"),
    "Switch:SW_Push": embed("Switch", "SW_Push"),
    "Connector:TestPoint": embed("Connector", "TestPoint"),
    "Connector:USB_C_Receptacle_USB2.0_16P": embed("Connector", "USB_C_Receptacle_USB2.0_16P"),
    "Interface_USB:ADUM3160": embed("Interface_USB", "ADUM4160", "ADUM3160"),
    "Power_Protection:USBLC6-2SC6": embed("Power_Protection", "USBLC6-2P6", "USBLC6-2SC6"),
    "Power_Protection:SRV05-4": embed("Power_Protection", "SRV05-4"),
    "Regulator_Linear:AP2112K-3.3": embed("Regulator_Linear", "AP2204K-1.5", "AP2112K-3.3"),
    "RF_Module:ESP32-C3-WROOM-02": embed("RF_Module", "ESP32-C3-WROOM-02"),
    "kaidi:B0505S-2WR3": converter_symbol(),
    "74xx:74AHCT125": embed("74xx", "74LS125", "74AHCT125"),
    "74xGxx:74LVC1G66": embed("74xGxx", "74LVC1G66"),
    "Transistor_FET:2N7002": embed("Transistor_FET", "Q_NMOS_GSD", "2N7002"),
    "Connector_Generic:Conn_01x02": embed("Connector_Generic", "Conn_01x02"),
    "Connector_Generic_Shielded:Conn_01x10_Shielded": embed("Connector_Generic_Shielded", "Conn_01x10_Shielded"),
    "power:+5V": embed("power", "+5V"),
    "power:GND": embed("power", "GND"),
    "power:PWR_FLAG": embed("power", "PWR_FLAG"),
}
PINS = {name: pins_of(block) for name, block in SYMBOLS.items()}

R0603, R1206 = "Resistor_SMD:R_0603_1608Metric", "Resistor_SMD:R_1206_3216Metric"
C0603, C0805, C1206 = (f"Capacitor_SMD:C_{s}" for s in ("0603_1608Metric", "0805_2012Metric", "1206_3216Metric"))
FUSE, SMA = "Fuse:Fuse_1206_3216Metric", "Diode_SMD:D_SMA"
SOT6 = "Package_TO_SOT_SMD:SOT-23-6"
JACK = "kaidi:RJ50_TE_5558067-1_Horizontal"

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


def part(
    lib_id, ref, value, x, y, footprint, nets, mirror=False, ref_at=(2.54, -1.27), val_at=(2.54, 1.27), stubs=None
):
    side = "left" if ref_at[0] else ""
    p = place(lib_id, ref, value, x, y, mirror=mirror, footprint=footprint, ref_at=ref_at, val_at=val_at, justify=side)
    seen = set()
    for num, name in nets.items():
        at = p(num)
        if at[0] in seen:
            continue
        seen.add(at[0])
        no_connect(at) if name is None else net(at, name, (stubs or {}).get(num, STUB))


def resistor(ref, value, x, y, a, b, footprint=R0603):
    part("Device:R", ref, value, x, y, footprint, {"1": a, "2": b})


def capacitor(ref, value, x, y, a, b="GND", footprint=C0603, symbol="Device:C"):
    part(symbol, ref, value, x, y, footprint, {"1": a, "2": b})


def across(lib_id, ref, value, x, y, footprint, nets, offset=3.81):
    part(lib_id, ref, value, x, y, footprint, nets, ref_at=(0, -offset), val_at=(0, offset))


text("Keypad and desk jacks", 22.86, 27.94)
for ref, label, side, y in (("J1", "Keypad (RJ50)", "KEYPAD", 55.88), ("J2", "Desk (RJ50)", "DESK", 106.68)):
    nets = {num: f"THRU_{num}" for num in ("1", "4", "5", "6", "9")}
    nets |= {"2": "+5V", "3": "GND", "7": f"CMD_{side}", "8": "HEIGHT", "10": f"WAKE_{side}", "SH": "GND"}
    part(
        "Connector_Generic_Shielded:Conn_01x10_Shielded",
        ref,
        label,
        38.1,
        y,
        JACK,
        nets,
        True,
        (0, -15.24),
        (0, -12.7),
        stubs={"2": 17.78, "3": 17.78},
    )
for ref, name, x in (("#FLG01", "+5V", 73.66), ("#FLG02", "GND", 93.98)):
    net(place("power:PWR_FLAG", ref, "PWR_FLAG", x, 139.7, hide_val=True)("1"), name)

text("Surge clamps at both jacks", 73.66, 27.94)
for ref, side, y in (("U6", "KEYPAD", 55.88), ("U5", "DESK", 106.68)):
    part(
        "Power_Protection:SRV05-4",
        ref,
        "SRV05-4",
        96.52,
        y,
        SOT6,
        {"1": f"CMD_{side}", "2": "GND", "3": f"WAKE_{side}", "4": "HEIGHT", "5": "+5V", "6": None},
        ref_at=(5.08, -15.24),
        val_at=(5.08, -12.7),
    )

text("Keypad path: closed unless the ESP opens U9, with 1k in series for the buffer to override", 129.54, 27.94)
resistor("R1", "1k", 139.7, 55.88, "CMD_SW", "CMD_DESK")
resistor("R2", "1k", 167.64, 55.88, "WAKE_KEYPAD", "WAKE_DESK")

text("74AHCT125 on desk 5 V: gates A-B drive the desk; C-D hold them off unless the ESP asks", 129.54, 81.28)
gates = [
    (1, 149.86, 101.6, "TX", "OE_TX", "CMD_DRV"),
    (2, 190.5, 101.6, "+5V", "OE_WAKE", "WAKE_DRV"),
    (3, 149.86, 129.54, "+5V", "EN_TX", "OE_TX"),
    (4, 190.5, 129.54, "+5V", "EN_WAKE", "OE_WAKE"),
]
ab = {1: ("2", "1", "3"), 2: ("5", "4", "6"), 3: ("9", "10", "8"), 4: ("12", "13", "11")}
SOIC14 = "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"
for unit, x, y, a, oe, yy in gates:
    p = place("74xx:74AHCT125", "U2", "74AHCT125", x, y, unit=unit, footprint=SOIC14, ref_at=(0, -5.08), hide_val=True)
    pa, poe, py = ab[unit]
    net(p(pa), a)
    net(p(poe), oe)
    net(p(py), yy)
p = place(
    "74xx:74AHCT125",
    "U2",
    "74AHCT125",
    223.52,
    50.8,
    unit=5,
    footprint=SOIC14,
    ref_at=(7.62, -1.27),
    val_at=(7.62, 1.27),
    justify="left",
)
net(p("14"), "+5V")
net(p("7"), "GND")
capacitor("C1", "100n", 246.38, 50.8, "+5V")
resistor("R12", "47", 218.44, 109.22, "CMD_DRV", "CMD_DESK")
resistor("R13", "47", 246.38, 109.22, "WAKE_DRV", "WAKE_DESK")
text("Everything off by default", 129.54, 147.32)
for ref, value, name, x in (("R3", "10k", "OE_TX", 139.7), ("R4", "10k", "OE_WAKE", 162.56)):
    resistor(ref, value, x, 167.64, name, "GND")
for ref, value, name, x in (("R5", "4.7k", "EN_TX", 185.42), ("R6", "10k", "EN_WAKE", 208.28)):
    resistor(ref, value, x, 167.64, name, "GND")

text("Keypad cutoff: closed by default, and JP2 bypasses it", 182.88, 351.79)
SOT5 = "Package_TO_SOT_SMD:SOT-23-5"
p = place("74xGxx:74LVC1G66", "U9", "74LVC1G66", 309.88, 370.84, footprint=SOT5, ref_at=(0, -7.62), val_at=(0, 12.7))
net(p("1"), "CMD_KEYPAD")
net(p("2"), "CMD_SW")
net(p("4"), "KP_ON")
p = place(
    "74xGxx:74LVC1G66", "U9", "74LVC1G66", 220.98, 370.84, unit=2, footprint=SOT5, ref_at=(10.16, 0), hide_val=True
)
net(p("5"), "+5V")
net(p("3"), "GND")
part(
    "Connector_Generic:Conn_01x02",
    "JP2",
    "Keypad always on",
    190.5,
    370.84,
    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    {"1": "CMD_KEYPAD", "2": "CMD_SW"},
    True,
    (0, -5.08),
    (0, 6.35),
)
resistor("R26", "10k", 347.98, 370.84, "+5V", "KP_ON")
part(
    "Transistor_FET:2N7002",
    "Q1",
    "2N7002",
    378.46,
    370.84,
    "Package_TO_SOT_SMD:SOT-23",
    {"1": "KP_OFF", "2": "GND", "3": "KP_ON"},
    ref_at=(5.08, -1.27),
    val_at=(5.08, 1.27),
)
resistor("R27", "10k", 403.86, 370.84, "KP_OFF", "GND")
capacitor("C14", "100n", 259.08, 370.84, "+5V")
capacitor("C13", "10u", 269.24, 50.8, "+5V", footprint=C0805)

text("Dividers (5 V to 3.0 V), too light to power a dead ESP", 22.86, 149.86)
for top, bottom, a, mid, x in (("R7", "R8", "HEIGHT", "RX", 30.48), ("R9", "R10", "CMD_KEYPAD", "SENSE", 58.42)):
    resistor(top, "100k", x, 172.72, a, mid)
    resistor(bottom, "150k", x, 203.2, mid, "GND")

text("ESP32-C3 module", 287.02, 27.94)
part(
    "RF_Module:ESP32-C3-WROOM-02",
    "U1",
    "ESP32-C3-WROOM-02-N4",
    330.2,
    76.2,
    "RF_Module:ESP32-C3-WROOM-02",
    {
        "1": "3V3",
        "2": "EN",
        "18": None,
        "17": "KP_OFF",
        "16": "IO2",
        "15": "SENSE",
        "3": "RX",
        "4": "LED",
        "5": "EN_TX",
        "6": "TX",
        "7": "IO8",
        "8": "IO9",
        "10": "EN_WAKE",
        "13": "USB_DM",
        "14": "USB_DP",
        "11": None,
        "12": None,
        "9": "GND",
        "19": "GND",
    },
    ref_at=(5.08, -25.4),
    val_at=(5.08, 25.4),
)
for ref, name, x in (("R21", "EN", 287.02), ("R24", "IO2", 309.88), ("R23", "IO8", 332.74), ("R22", "IO9", 355.6)):
    resistor(ref, "10k", x, 132.08, "3V3", name)
capacitor("C8", "1u", 378.46, 132.08, "EN")
capacitor("C7", "100n", 365.76, 76.2, "3V3")
capacitor("C12", "10u", 386.08, 76.2, "3V3", footprint=C0805)
for ref, value, name, x in (("SW1", "RESET", "EN", 297.18), ("SW2", "BOOT", "IO9", 335.28)):
    across(
        "Switch:SW_Push", ref, value, x, 162.56, "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", {"1": name, "2": "GND"}
    )
resistor("R25", "1k", 365.76, 165.1, "LED", "LED_A")
across("Device:LED", "D3", "STATUS", 388.62, 165.1, "LED_SMD:LED_0603_1608Metric", {"2": "LED_A", "1": "GND"})

text("Desk 5 V supply (default): pull JP1 to run from USB-C only", 238.76, 182.88)
part(
    "Connector_Generic:Conn_01x02",
    "JP1",
    "Desk power",
    256.54,
    205.74,
    "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    {"1": "+5V", "2": "DESK_SW"},
    True,
    (0, -5.08),
    (0, 6.35),
)
part("Device:Polyfuse", "F1", "500mA", 279.4, 208.28, FUSE, {"1": "DESK_SW", "2": "DESK_FUSED"})
resistor("R11", "1", 302.26, 208.28, "DESK_FUSED", "DESK_LIM", R1206)
across("Device:D_Schottky", "D2", "SS14", 330.2, 205.74, SMA, {"2": "DESK_LIM", "1": "ESP_5V"})

text("3.3 V for the ESP", 238.76, 231.14)
capacitor(
    "C4", "1000u", 251.46, 254.0, "ESP_5V", footprint="Capacitor_SMD:CP_Elec_10x10.5", symbol="Device:C_Polarized"
)
capacitor("C5", "10u", 276.86, 254.0, "ESP_5V", footprint=C0805)
part(
    "Regulator_Linear:AP2112K-3.3",
    "U4",
    "AP2112K-3.3",
    314.96,
    254.0,
    "Package_TO_SOT_SMD:SOT-23-5",
    {"1": "ESP_5V", "3": "ESP_5V", "2": "GND", "4": None, "5": "3V3"},
    ref_at=(0, -10.16),
    val_at=(0, -7.62),
)
capacitor("C6", "22u", 353.06, 254.0, "3V3", footprint=C0805)

text("USB-C: power and data both isolated from the desk", 22.86, 218.44)
usb = {"A1": "GND_ISO", "B1": "GND_ISO", "A12": "GND_ISO", "B12": "GND_ISO", "SH": "GND_ISO"}
usb |= dict.fromkeys(("A4", "A9", "B4", "B9"), "VBUS") | {"A5": "CC1", "B5": "CC2", "A8": None, "B8": None}
usb |= {"A6": "USBC_DP", "B6": "USBC_DP", "A7": "USBC_DM", "B7": "USBC_DM"}
part(
    "Connector:USB_C_Receptacle_USB2.0_16P",
    "J3",
    "USB-C",
    45.72,
    248.92,
    "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    usb,
    ref_at=(-10.16, -22.86),
    val_at=(-10.16, -20.32),
)
resistor("R15", "5.1k", 81.28, 233.68, "CC1", "GND_ISO")
resistor("R16", "5.1k", 101.6, 233.68, "CC2", "GND_ISO")
part("Device:Polyfuse", "F2", "1A", 124.46, 233.68, FUSE, {"1": "VBUS", "2": "VIN_ISO"})
capacitor("C3", "10u", 144.78, 233.68, "VIN_ISO", "GND_ISO", C0805)
across("Device:D_TVS", "D4", "SMAJ5.0CA", 170.18, 233.68, SMA, {"1": "VIN_ISO", "2": "GND_ISO"})
part(
    "Power_Protection:USBLC6-2SC6",
    "U8",
    "USBLC6-2SC6",
    93.98,
    281.94,
    SOT6,
    {"1": "USBC_DP", "6": "USBC_DP", "3": "USBC_DM", "4": "USBC_DM", "5": "VBUS", "2": "GND_ISO"},
    ref_at=(7.62, -10.16),
    val_at=(7.62, -7.62),
)
resistor("R17", "24", 124.46, 281.94, "USBC_DM", "UDM")
resistor("R18", "24", 144.78, 281.94, "USBC_DP", "UDP")
part(
    "Interface_USB:ADUM3160",
    "U7",
    "ADUM3160",
    185.42,
    281.94,
    "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm",
    {
        "1": "VIN_ISO",
        "2": "GND_ISO",
        "8": "GND_ISO",
        "3": "VDD1",
        "4": "VDD1",
        "5": "VDD1",
        "6": "UDM",
        "7": "UDP",
        "16": "3V3",
        "14": "3V3",
        "12": "3V3",
        "13": "3V3",
        "9": "GND",
        "15": "GND",
        "11": "DDM",
        "10": "DDP",
    },
    ref_at=(10.16, -17.78),
    val_at=(10.16, -15.24),
)
resistor("R19", "24", 218.44, 281.94, "DDM", "USB_DM")
resistor("R20", "24", 243.84, 281.94, "DDP", "USB_DP")
capacitor("C9", "100n", 368.3, 208.28, "VIN_ISO", "GND_ISO")
capacitor("C10", "100n", 393.7, 208.28, "VDD1", "GND_ISO")
capacitor("C11", "100n", 386.08, 254.0, "3V3")

text("Isolated supply, with a preload for the converter's minimum load", 22.86, 314.96)
across(
    "kaidi:B0505S-2WR3",
    "U3",
    "B0505S-2WR3",
    58.42,
    330.2,
    "kaidi:Converter_DCDC_Mornsun_B_S-2WR3_SIP",
    {"1": "VIN_ISO", "2": "GND_ISO", "6": "VOUT", "4": "GND"},
    7.62,
)
capacitor("C2", "22u", 99.06, 332.74, "VOUT", footprint=C1206)
resistor("R14", "220", 119.38, 332.74, "VOUT", "GND", R1206)
across("Device:D_Schottky", "D1", "SS14", 149.86, 330.2, SMA, {"2": "VOUT", "1": "ESP_5V"})
for ref, name, x in (
    ("#FLG03", "VIN_ISO", 182.88),
    ("#FLG04", "GND_ISO", 200.66),
    ("#FLG05", "ESP_5V", 218.44),
    ("#FLG06", "VDD1", 236.22),
):
    net(place("power:PWR_FLAG", ref, "PWR_FLAG", x, 332.74, hide_val=True)("1"), name)

text("Test points", 264.16, 314.96)
for i, name in enumerate(("+5V", "GND", "ESP_5V", "3V3", "TX", "RX", "VIN_ISO", "GND_ISO")):
    part(
        "Connector:TestPoint",
        f"TP{i + 1}",
        name,
        269.24 + i * 17.78,
        330.2,
        "TestPoint:TestPoint_Pad_D1.5mm",
        {"1": name},
        ref_at=(0, -7.62),
        val_at=(0, -5.08),
    )

body = "\n".join(out)
lib = "\n".join(SYMBOLS.values())
sch = f"""(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{root}") (paper "A2")
(title_block (title "Kaidi Desk Dongle") (date "2026-11-24") (company "esphome-kaidi-desk")
 (comment 1 "Inline between the keypad and a Kaidi KDDY094 control box") (comment 2 "github.com/clintval/esphome-kaidi-desk"))
(lib_symbols {lib})
{body}
(sheet_instances (path "/" (page "1"))))
"""
Path(sys.argv[1]).write_text(sch)
