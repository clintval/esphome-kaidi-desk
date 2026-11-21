# Contributing

## Toolchain

Install [ESPHome](https://esphome.io/guides/installing_esphome.html), for example with `pip install esphome` or `brew install esphome`.

## Building

Compile the example against the component in this checkout:

```bash
mkdir -p .build
printf 'wifi_ssid: "ssid"\nwifi_password: "password1"\n' > .build/secrets.yaml
sed 's#source: github://clintval/esphome-kaidi-desk@main#source: {type: local, path: ../components}#' \
    example/kaidi-desk.yaml > .build/kaidi-desk.yaml
esphome compile .build/kaidi-desk.yaml
```

## Diagrams

The SVGs in `docs/` are drawn by the scripts in `scripts/`:

```bash
python3 scripts/draw_board.py docs/board.svg
python3 scripts/draw_schematic.py docs/wiring.svg
python3 scripts/draw_breadboard.py docs/breadboard.svg
```

## Mandatory Pre-submission Checks

The example must compile, as in CI:

```bash
esphome compile .build/kaidi-desk.yaml
```

## Board Illustration

The README's board drawing comes from [PcbDraw](https://github.com/yaqwsx/PcbDraw), installed into KiCad's Python, with part drawings from `scripts/make_pcbdraw_parts.py`:

```bash
python3 scripts/make_pcbdraw_parts.py hardware/pcbdraw
PYTHONPATH=~/Library/Python/3.9/lib/python/site-packages \
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
    -m pcbdraw.ui plot --style set-blue-enig --libs "$PWD/hardware/pcbdraw,KiCAD-base" \
    --resistor-values R1:1k,R2:1k,R3:10k,R4:10k,R5:100k,R6:100k,R7:10k,R8:15k,R9:10k,R10:15k \
    hardware/kaidi-desk.kicad_pcb docs/board.svg
```
