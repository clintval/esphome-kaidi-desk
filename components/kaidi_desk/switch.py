import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch

from . import CONF_KAIDI_DESK_ID, KaidiDesk, kaidi_desk_ns

DEPENDENCIES = ["kaidi_desk"]

CONF_KEEP_AWAKE = "keep_awake"

KaidiKeepAwakeSwitch = kaidi_desk_ns.class_("KaidiKeepAwakeSwitch", switch.Switch, cg.Parented.template(KaidiDesk))

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        cv.Optional(CONF_KEEP_AWAKE): switch.switch_schema(
            KaidiKeepAwakeSwitch,
            icon="mdi:power-sleep",
            default_restore_mode="RESTORE_DEFAULT_OFF",
        ),
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    if keep_awake_config := config.get(CONF_KEEP_AWAKE):
        var = await switch.new_switch(keep_awake_config)
        cg.add(var.set_parent(desk))
