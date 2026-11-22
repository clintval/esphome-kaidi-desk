import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import uart
from esphome.const import CONF_ID

CODEOWNERS = ["@clintval"]
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["button", "number", "sensor", "switch", "text_sensor"]
MULTI_CONF = True

CONF_KAIDI_DESK_ID = "kaidi_desk_id"
CONF_TX_ENABLE_PIN = "tx_enable_pin"
CONF_WAKE_PIN = "wake_pin"
CONF_KEYPAD_SENSE_PIN = "keypad_sense_pin"
CONF_FRAME_INTERVAL = "frame_interval"
CONF_WAKE_SETTLE = "wake_settle"
CONF_WAKE_TIMEOUT = "wake_timeout"
CONF_NUDGE_DURATION = "nudge_duration"
CONF_MOVE_TIMEOUT = "move_timeout"
CONF_RESET_TIMEOUT = "reset_timeout"
CONF_TOLERANCE = "tolerance"
CONF_COAST = "coast"

kaidi_desk_ns = cg.esphome_ns.namespace("kaidi_desk")
KaidiDesk = kaidi_desk_ns.class_("KaidiDesk", cg.Component, uart.UARTDevice)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(KaidiDesk),
            cv.Optional(CONF_TX_ENABLE_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_WAKE_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_KEYPAD_SENSE_PIN): pins.internal_gpio_input_pin_schema,
            cv.Optional(CONF_FRAME_INTERVAL, default="14ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_WAKE_SETTLE, default="1200ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_WAKE_TIMEOUT, default="4s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_NUDGE_DURATION, default="900ms"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_MOVE_TIMEOUT, default="45s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_RESET_TIMEOUT, default="90s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_TOLERANCE, default=0.4): cv.positive_float,
            cv.Optional(CONF_COAST, default=1.3): cv.positive_float,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)

FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "kaidi_desk",
    baud_rate=9600,
    require_tx=True,
    require_rx=True,
    data_bits=8,
    parity="NONE",
    stop_bits=1,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    if CONF_TX_ENABLE_PIN in config:
        cg.add(var.set_tx_enable_pin(await cg.gpio_pin_expression(config[CONF_TX_ENABLE_PIN])))
    if CONF_WAKE_PIN in config:
        cg.add(var.set_wake_pin(await cg.gpio_pin_expression(config[CONF_WAKE_PIN])))
    if CONF_KEYPAD_SENSE_PIN in config:
        cg.add(var.set_keypad_sense_pin(await cg.gpio_pin_expression(config[CONF_KEYPAD_SENSE_PIN])))
    cg.add(var.set_frame_interval(config[CONF_FRAME_INTERVAL]))
    cg.add(var.set_wake_settle(config[CONF_WAKE_SETTLE]))
    cg.add(var.set_wake_timeout(config[CONF_WAKE_TIMEOUT]))
    cg.add(var.set_nudge_duration(config[CONF_NUDGE_DURATION]))
    cg.add(var.set_move_timeout(config[CONF_MOVE_TIMEOUT]))
    cg.add(var.set_reset_timeout(config[CONF_RESET_TIMEOUT]))
    cg.add(var.set_tolerance(config[CONF_TOLERANCE]))
    cg.add(var.set_coast(config[CONF_COAST]))
