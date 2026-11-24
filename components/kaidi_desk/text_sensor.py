import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor
from esphome.const import CONF_STATUS

from . import CONF_KAIDI_DESK_ID, KaidiDesk

DEPENDENCIES = ["kaidi_desk"]

CONF_KEYPAD = "keypad"
CONF_LAST_STOP = "last_stop"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        cv.Optional(CONF_STATUS): text_sensor.text_sensor_schema(icon="mdi:desk"),
        cv.Optional(CONF_LAST_STOP): text_sensor.text_sensor_schema(icon="mdi:hand-back-left"),
        cv.Optional(CONF_KEYPAD): text_sensor.text_sensor_schema(icon="mdi:gesture-tap-button"),
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    if status_config := config.get(CONF_STATUS):
        cg.add(desk.set_status_sensor(await text_sensor.new_text_sensor(status_config)))
    if last_stop_config := config.get(CONF_LAST_STOP):
        cg.add(desk.set_last_stop_sensor(await text_sensor.new_text_sensor(last_stop_config)))
    if keypad_config := config.get(CONF_KEYPAD):
        cg.add(desk.set_keypad_sensor(await text_sensor.new_text_sensor(keypad_config)))
