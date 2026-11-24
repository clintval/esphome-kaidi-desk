import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button
from esphome.const import ENTITY_CATEGORY_CONFIG

from . import CONF_KAIDI_DESK_ID, KaidiDesk, kaidi_desk_ns

DEPENDENCIES = ["kaidi_desk"]

KaidiButton = kaidi_desk_ns.class_("KaidiButton", button.Button, cg.Parented.template(KaidiDesk))
ButtonAction = kaidi_desk_ns.enum("ButtonAction", is_class=True)

BUTTONS = {
    "nudge_up": (ButtonAction.NUDGE_UP, "mdi:arrow-up-bold"),
    "nudge_down": (ButtonAction.NUDGE_DOWN, "mdi:arrow-down-bold"),
    "stop": (ButtonAction.STOP, "mdi:stop"),
    "reset": (ButtonAction.RESET, "mdi:restore"),
    **{f"preset_{n}": (getattr(ButtonAction, f"PRESET_{n}"), f"mdi:numeric-{n}-box-outline") for n in range(1, 5)},
}
SAVE_BUTTONS = {
    f"save_preset_{n}": (getattr(ButtonAction, f"SAVE_PRESET_{n}"), "mdi:content-save") for n in range(1, 5)
}

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_KAIDI_DESK_ID): cv.use_id(KaidiDesk),
        **{cv.Optional(key): button.button_schema(KaidiButton, icon=icon) for key, (_, icon) in BUTTONS.items()},
        **{
            cv.Optional(key): button.button_schema(KaidiButton, icon=icon, entity_category=ENTITY_CATEGORY_CONFIG)
            for key, (_, icon) in SAVE_BUTTONS.items()
        },
    }
)


async def to_code(config):
    desk = await cg.get_variable(config[CONF_KAIDI_DESK_ID])
    for key, (action, _) in (BUTTONS | SAVE_BUTTONS).items():
        if button_config := config.get(key):
            var = await button.new_button(button_config, action)
            cg.add(var.set_parent(desk))
