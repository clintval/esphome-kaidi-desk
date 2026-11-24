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
CONF_KEYPAD_UART_ID = "keypad_uart_id"
CONF_KEYPAD_CUTOFF_PIN = "keypad_cutoff_pin"
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
            cv.Optional(CONF_KEYPAD_UART_ID): cv.use_id(uart.UARTComponent),
            cv.Optional(CONF_KEYPAD_CUTOFF_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_KEYPAD_SENSE_PIN): cv.invalid(
                "keypad_sense_pin is now the rx_pin of a second 9600 baud uart, given as keypad_uart_id"
            ),
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

FRAME_FORMAT = {"baud_rate": 9600, "require_rx": True, "data_bits": 8, "parity": "NONE", "stop_bits": 1}


def final_validate(config):
    if CONF_KEYPAD_CUTOFF_PIN in config and CONF_KEYPAD_UART_ID not in config:
        raise cv.Invalid(
            "Cutting the keypad off needs keypad_uart_id, so a press can still stop the desk",
            path=[CONF_KEYPAD_CUTOFF_PIN],
        )
    uart.final_validate_device_schema("kaidi_desk", require_tx=True, **FRAME_FORMAT)(config)
    if CONF_KEYPAD_UART_ID in config:
        if config[CONF_KEYPAD_UART_ID] == config[uart.CONF_UART_ID]:
            raise cv.Invalid("The keypad needs a uart of its own", path=[CONF_KEYPAD_UART_ID])
        uart.final_validate_device_schema("kaidi_desk", uart_bus=CONF_KEYPAD_UART_ID, **FRAME_FORMAT)(config)
    return config


FINAL_VALIDATE_SCHEMA = final_validate


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    if CONF_TX_ENABLE_PIN in config:
        cg.add(var.set_tx_enable_pin(await cg.gpio_pin_expression(config[CONF_TX_ENABLE_PIN])))
    if CONF_WAKE_PIN in config:
        cg.add(var.set_wake_pin(await cg.gpio_pin_expression(config[CONF_WAKE_PIN])))
    if CONF_KEYPAD_UART_ID in config:
        cg.add(var.set_keypad_uart(await cg.get_variable(config[CONF_KEYPAD_UART_ID])))
    if CONF_KEYPAD_CUTOFF_PIN in config:
        cg.add(var.set_keypad_cutoff_pin(await cg.gpio_pin_expression(config[CONF_KEYPAD_CUTOFF_PIN])))
    cg.add(var.set_frame_interval(config[CONF_FRAME_INTERVAL]))
    cg.add(var.set_wake_settle(config[CONF_WAKE_SETTLE]))
    cg.add(var.set_wake_timeout(config[CONF_WAKE_TIMEOUT]))
    cg.add(var.set_nudge_duration(config[CONF_NUDGE_DURATION]))
    cg.add(var.set_move_timeout(config[CONF_MOVE_TIMEOUT]))
    cg.add(var.set_reset_timeout(config[CONF_RESET_TIMEOUT]))
    cg.add(var.set_tolerance(config[CONF_TOLERANCE]))
    cg.add(var.set_coast(config[CONF_COAST]))
