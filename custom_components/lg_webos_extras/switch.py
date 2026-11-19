"""Switch: turn the TV screen off while the sound keeps playing.

Newer webOS TVs (3.0+) have a direct command for this. Older TVs (webOS 1/2,
2014-2015 models) only have it in the menu (Picture > Energy Saving > Screen
Off), so a configurable key sequence ("macro") can be used instead.
"""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from . import ExtrasConfigEntry
from .const import CONF_SCREEN_OFF_SEQ, MACRO_KEY_DELAY, WEBOSTV_DOMAIN
from .entity import ExtrasEntity

TURN_OFF_SCREEN = "com.webos.service.tvpower/power/turnOffScreen"
TURN_ON_SCREEN = "com.webos.service.tvpower/power/turnOnScreen"

# Any key except power/volume wakes the screen on old models; EXIT has no side effects.
WAKE_KEY = "EXIT"


def parse_sequence(text: str) -> list[tuple[str, float]]:
    """Parse e.g. "MENU, wait 2, DOWN*3, ENTER" into [(key, delay_after), ...].

    - KEY        press a remote key (HOME, MENU, QMENU, UP, DOWN, LEFT, RIGHT, ENTER, BACK, EXIT...)
    - KEY*N      press it N times
    - wait X     pause X seconds (decimals allowed)
    """
    steps: list[tuple[str, float]] = []
    for raw in text.replace(";", ",").replace("\n", ",").split(","):
        token = raw.strip()
        if not token:
            continue
        low = token.lower()
        if low.startswith("wait"):
            value = low[4:].strip(" =:") or "1"
            try:
                seconds = float(value)
            except ValueError as err:
                raise ValueError(f"Neplatná pauza: {token}") from err
            if steps:
                key, delay = steps[-1]
                steps[-1] = (key, delay + seconds)
            else:
                steps.append(("", seconds))
            continue
        key, _, count = token.partition("*")
        key = key.strip().upper()
        try:
            times = int(count) if count else 1
        except ValueError as err:
            raise ValueError(f"Neplatný počet opakovaní: {token}") from err
        steps.extend((key, MACRO_KEY_DELAY) for _ in range(times))
    return steps


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
        self._unsupported = False
        self._sequence: str = (entry.options.get(CONF_SCREEN_OFF_SEQ) or "").strip()
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        return self.tv_on and (bool(self._sequence) or not self._unsupported)

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

    async def _press(self, key: str) -> None:
        await self.hass.services.async_call(
            WEBOSTV_DOMAIN, "button", {ATTR_ENTITY_ID: self._tv, "button": key}, blocking=True
        )

    async def _command(self, command: str) -> None:
        try:
            await self.hass.services.async_call(
                WEBOSTV_DOMAIN,
                "command",
                {ATTR_ENTITY_ID: self._tv, "command": command},
                blocking=True,
            )
        except HomeAssistantError as err:
            if "404" in str(err):
                # Older webOS has no screen-off service: hide the switch
                # unless a menu key sequence is configured.
                self._unsupported = True
                self.async_write_ha_state()
                raise HomeAssistantError(
                    "Tento televízor nepodporuje priame vypnutie obrazovky. "
                    "Nastav postupnosť tlačidiel v Možnostiach integrácie."
                ) from err
            raise

    async def _run_macro(self) -> None:
        try:
            steps = parse_sequence(self._sequence)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        async with self._lock:
            for key, delay in steps:
                if key:
                    await self._press(key)
                await asyncio.sleep(delay)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._sequence:
            await self._run_macro()
        else:
            await self._command(TURN_OFF_SCREEN)
        self._screen_on = False
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self._sequence:
            await self._press(WAKE_KEY)
        else:
            await self._command(TURN_ON_SCREEN)
        self._screen_on = True
        self.async_write_ha_state()
