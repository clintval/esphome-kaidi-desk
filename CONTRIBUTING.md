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
