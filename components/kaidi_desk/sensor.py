import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import (
    CONF_HEIGHT,
    DEVICE_CLASS_DISTANCE,
    STATE_CLASS_MEASUREMENT,
    UNIT_CENTIMETER,
)

from . import CONF_KAIDI_DESK_ID, KaidiDesk

DEPENDENCIES = ["kaidi_desk"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        cv.Optional(CONF_HEIGHT): sensor.sensor_schema(
            unit_of_measurement=UNIT_CENTIMETER,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_DISTANCE,
            state_class=STATE_CLASS_MEASUREMENT,
            icon="mdi:human-male-height-variant",
        ),
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    if height_config := config.get(CONF_HEIGHT):
        cg.add(desk.set_height_sensor(await sensor.new_sensor(height_config)))
