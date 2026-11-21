import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor
from esphome.const import CONF_STATUS

from . import CONF_KAIDI_DESK_ID, KaidiDesk

DEPENDENCIES = ["kaidi_desk"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        cv.Optional(CONF_STATUS): text_sensor.text_sensor_schema(icon="mdi:desk"),
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    if status_config := config.get(CONF_STATUS):
        cg.add(desk.set_status_sensor(await text_sensor.new_text_sensor(status_config)))
