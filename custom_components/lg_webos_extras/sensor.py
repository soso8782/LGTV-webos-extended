"""Sensor: when the sleep timer turns the TV off (also restores the timer after restart)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import ExtrasConfigEntry
from .entity import ExtrasEntity
from .sleep_timer import SleepTimer

ATTR_PRESET = "preset"


async def async_setup_entry(
    hass: HomeAssistant, entry: ExtrasConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SleepTimerEndSensor(hass, entry, entry.runtime_data)])


class SleepTimerEndSensor(ExtrasEntity, RestoreEntity, SensorEntity):
    """Timestamp at which the TV will be turned off (empty if no timer)."""

    _attr_translation_key = "sleep_timer_end"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sand"

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry, timer: SleepTimer) -> None:
        super().__init__(hass, entry, "sleep_timer_end")
        self._timer = timer

    @property
    def native_value(self) -> datetime | None:
        return self._timer.end

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return {ATTR_PRESET: self._timer.preset}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._timer.async_add_listener(self.async_write_ha_state))

        if self._timer.active:
            return
        last = await self.async_get_last_state()
        if last is None:
            return
        end = dt_util.parse_datetime(last.state)
        if end is not None:
            self._timer.restore(dt_util.as_utc(end), last.attributes.get(ATTR_PRESET))
