"""Select entities: sleep timer and sound output."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ExtrasConfigEntry
from .const import CONF_APPS, SLEEP_OFF, SLEEP_OPTIONS, SOUND_OUTPUTS, WEBOSTV_DOMAIN
from .entity import ExtrasEntity, default_apps
from .sleep_timer import SleepTimer


async def async_setup_entry(
    hass: HomeAssistant, entry: ExtrasConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(
        [
            SleepTimerSelect(hass, entry, entry.runtime_data),
            SoundOutputSelect(hass, entry),
            AppSelect(hass, entry),
        ]
    )


class SleepTimerSelect(ExtrasEntity, SelectEntity):
    """Choose sleep timer length: off / 15 / 30 / ... minutes."""

    _attr_translation_key = "sleep_timer"
    _attr_icon = "mdi:timer-outline"
    _attr_options = SLEEP_OPTIONS

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry, timer: SleepTimer) -> None:
        super().__init__(hass, entry, "sleep_timer")
        self._timer = timer

    @property
    def available(self) -> bool:
        return self.tv_reachable

    @property
    def current_option(self) -> str:
        if not self._timer.active:
            return SLEEP_OFF
        return self._timer.preset if self._timer.preset in SLEEP_OPTIONS else SLEEP_OFF

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._timer.async_add_listener(self.async_write_ha_state))

    async def async_select_option(self, option: str) -> None:
        if option == SLEEP_OFF:
            self._timer.cancel()
        else:
            self._timer.start(int(option), preset=option)


class SoundOutputSelect(ExtrasEntity, SelectEntity):
    """Switch between TV speakers, soundbar, headphones..."""

    _attr_translation_key = "sound_output"
    _attr_icon = "mdi:speaker"

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry) -> None:
        super().__init__(hass, entry, "sound_output")

    @property
    def available(self) -> bool:
        return self.tv_on

    @property
    def current_option(self) -> str | None:
        state = self.hass.states.get(self._tv)
        return state.attributes.get("sound_output") if state else None

    @property
    def options(self) -> list[str]:
        current = self.current_option
        if current and current not in SOUND_OUTPUTS:
            return [*SOUND_OUTPUTS, current]
        return list(SOUND_OUTPUTS)

    async def async_select_option(self, option: str) -> None:
        await self.hass.services.async_call(
            WEBOSTV_DOMAIN,
            "select_sound_output",
            {ATTR_ENTITY_ID: self._tv, "sound_output": option},
            blocking=True,
        )


class AppSelect(ExtrasEntity, SelectEntity):
    """Launch one of the favourite apps (Netflix, HBO Max, TiviMate...)."""

    _attr_translation_key = "app"
    _attr_icon = "mdi:apps"

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry) -> None:
        super().__init__(hass, entry, "app")
        self._configured: list[str] = list(entry.options.get(CONF_APPS) or [])

    def _tv_attr(self, name: str):
        state = self.hass.states.get(self._tv)
        return state.attributes.get(name) if state else None

    @property
    def options(self) -> list[str]:
        if self._configured:
            return self._configured
        return default_apps(list(self._tv_attr("source_list") or []))

    @property
    def available(self) -> bool:
        return self.tv_on and bool(self.options)

    @property
    def current_option(self) -> str | None:
        source = self._tv_attr("source")
        return source if source in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.hass.services.async_call(
            "media_player",
            "select_source",
            {ATTR_ENTITY_ID: self._tv, "source": option},
            blocking=True,
        )
