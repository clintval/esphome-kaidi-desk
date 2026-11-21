import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.const import (
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_MODE,
    CONF_STEP,
    CONF_UNIT_OF_MEASUREMENT,
)

from . import CONF_KAIDI_DESK_ID, KaidiDesk, kaidi_desk_ns

DEPENDENCIES = ["kaidi_desk"]

CONF_TARGET_HEIGHT = "target_height"

KaidiTargetNumber = kaidi_desk_ns.class_("KaidiTargetNumber", number.Number, cg.Parented.template(KaidiDesk))

UNITS_PER_CM = {"cm": 1.0, "in": 1 / 2.54}
DEFAULT_MAX = {"cm": 70.0, "in": 27.5}


def _defaults(config):
    unit = config.setdefault(CONF_UNIT_OF_MEASUREMENT, "cm")
    if unit not in UNITS_PER_CM:
        raise cv.Invalid("unit_of_measurement must be 'cm' or 'in'")
    config.setdefault(CONF_MIN_VALUE, 0.0)
    config.setdefault(CONF_MAX_VALUE, DEFAULT_MAX[unit])
    config.setdefault(CONF_STEP, 0.1)
    if str(config.get(CONF_MODE, "AUTO")).upper() == "AUTO":
        config[CONF_MODE] = cv.enum(number.NUMBER_MODES, upper=True)("SLIDER")
    return config


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        cv.Optional(CONF_TARGET_HEIGHT): cv.All(
            number.number_schema(KaidiTargetNumber, icon="mdi:arrow-expand-vertical").extend(
                {
                    cv.Optional(CONF_MIN_VALUE): cv.float_,
                    cv.Optional(CONF_MAX_VALUE): cv.float_,
                    cv.Optional(CONF_STEP): cv.positive_float,
                }
            ),
            _defaults,
        ),
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    if target_config := config.get(CONF_TARGET_HEIGHT):
        var = await number.new_number(
            target_config,
            min_value=target_config[CONF_MIN_VALUE],
            max_value=target_config[CONF_MAX_VALUE],
            step=target_config[CONF_STEP],
        )
        cg.add(var.set_parent(desk))
        cg.add(desk.set_target_number(var, UNITS_PER_CM[target_config[CONF_UNIT_OF_MEASUREMENT]]))
