import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button

from . import CONF_KAIDI_DESK_ID, KaidiDesk, kaidi_desk_ns

DEPENDENCIES = ["kaidi_desk"]

KaidiButton = kaidi_desk_ns.class_("KaidiButton", button.Button, cg.Parented.template(KaidiDesk))
ButtonAction = kaidi_desk_ns.enum("ButtonAction", is_class=True)

BUTTONS = {
    "nudge_up": (ButtonAction.NUDGE_UP, "mdi:arrow-up-bold"),
    "nudge_down": (ButtonAction.NUDGE_DOWN, "mdi:arrow-down-bold"),
    "stop": (ButtonAction.STOP, "mdi:stop"),
    "reset": (ButtonAction.RESET, "mdi:restore"),
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        **{cv.Optional(key): button.button_schema(KaidiButton, icon=icon) for key, (_, icon) in BUTTONS.items()},
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    for key, (action, _) in BUTTONS.items():
        if button_config := config.get(key):
            var = await button.new_button(button_config, action)
            cg.add(var.set_parent(desk))
