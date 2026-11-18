"""Switch: turn the TV screen off while the sound keeps playing."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from . import ExtrasConfigEntry
from .const import WEBOSTV_DOMAIN
from .entity import ExtrasEntity

TURN_OFF_SCREEN = "com.webos.service.tvpower/power/turnOffScreen"
TURN_ON_SCREEN = "com.webos.service.tvpower/power/turnOnScreen"


async def async_setup_entry(hass: HomeAssistant, entry: ExtrasConfigEntry, async_add_entities) -> None:
    async_add_entities([ScreenSwitch(hass, entry)])


class ScreenSwitch(ExtrasEntity, SwitchEntity):
    """On = screen on. Off = screen dark, audio keeps playing.

    The TV does not report the screen state to Home Assistant, so the state is
    assumed: it resets to "on" whenever the TV is switched on.
    """

    _attr_translation_key = "screen"
    _attr_assumed_state = True

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry) -> None:
        super().__init__(hass, entry, "screen")
        self._screen_on = True

    @property
    def available(self) -> bool:
        return self.tv_on

    @property
    def is_on(self) -> bool:
        return self._screen_on

    @property
    def icon(self) -> str:
        return "mdi:monitor" if self._screen_on else "mdi:monitor-off"

    @callback
    def _tv_changed(self, event: Event[EventStateChangedData]) -> None:
        old = event.data["old_state"]
        new = event.data["new_state"]
        if new is not None and new.state == STATE_ON and (old is None or old.state != STATE_ON):
            self._screen_on = True
        super()._tv_changed(event)

    async def _send(self, command: str) -> None:
        try:
            await self.hass.services.async_call(
                WEBOSTV_DOMAIN,
                "command",
                {ATTR_ENTITY_ID: self._tv, "command": command},
                blocking=True,
            )
        except HomeAssistantError as err:
            raise HomeAssistantError(
                f"Tento televízor nepodporuje vypnutie obrazovky ({err})"
            ) from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(TURN_OFF_SCREEN)
        self._screen_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(TURN_ON_SCREEN)
        self._screen_on = True
        self.async_write_ha_state()
