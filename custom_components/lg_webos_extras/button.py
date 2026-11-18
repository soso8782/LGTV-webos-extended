"""Remote control buttons for LG webOS Extras."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ExtrasConfigEntry
from .const import REMOTE_BUTTONS, WEBOSTV_DOMAIN
from .entity import ExtrasEntity

ICONS = {
    "HOME": "mdi:home",
    "BACK": "mdi:arrow-u-left-top",
    "EXIT": "mdi:exit-to-app",
    "MENU": "mdi:cog",
    "QMENU": "mdi:tune-variant",
    "INFO": "mdi:information-outline",
    "UP": "mdi:chevron-up",
    "DOWN": "mdi:chevron-down",
    "LEFT": "mdi:chevron-left",
    "RIGHT": "mdi:chevron-right",
    "ENTER": "mdi:checkbox-blank-circle-outline",
    "VOLUMEUP": "mdi:volume-plus",
    "VOLUMEDOWN": "mdi:volume-minus",
    "MUTE": "mdi:volume-mute",
    "CHANNELUP": "mdi:arrow-up-bold",
    "CHANNELDOWN": "mdi:arrow-down-bold",
    "PLAY": "mdi:play",
    "PAUSE": "mdi:pause",
    "STOP": "mdi:stop",
    "REWIND": "mdi:rewind",
    "FASTFORWARD": "mdi:fast-forward",
    "GUIDE": "mdi:television-guide",
    "LIST": "mdi:format-list-bulleted",
    "NETFLIX": "mdi:netflix",
    "AMAZON": "mdi:alpha-a-box",
    "RED": "mdi:square-rounded",
    "GREEN": "mdi:square-rounded",
    "YELLOW": "mdi:square-rounded",
    "BLUE": "mdi:square-rounded",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ExtrasConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        RemoteButton(hass, entry, key, enabled) for key, enabled in REMOTE_BUTTONS
    )


class RemoteButton(ExtrasEntity, ButtonEntity):
    """One key of the LG remote."""

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry, key: str, enabled: bool) -> None:
        super().__init__(hass, entry, f"button_{key.lower()}")
        self._key = key
        self._attr_translation_key = f"key_{key.lower()}"
        self._attr_entity_registry_enabled_default = enabled
        self._attr_icon = ICONS.get(key, "mdi:numeric" if key.isdigit() else "mdi:remote")

    @property
    def available(self) -> bool:
        return self.tv_on

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            WEBOSTV_DOMAIN,
            "button",
            {ATTR_ENTITY_ID: self._tv, "button": self._key},
            blocking=True,
        )
