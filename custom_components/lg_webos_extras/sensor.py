"""Sensors: sleep timer end time and TiviMate channel / programme."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import ExtrasConfigEntry
from .const import CONF_FIRETV_ENTITY
from .entity import ExtrasEntity
from .sleep_timer import SleepTimer
from .tivimate import FIELDS, TIVIMATE_PACKAGE, TiviMateBridge

ATTR_PRESET = "preset"


async def async_setup_entry(
    hass: HomeAssistant, entry: ExtrasConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data
    firetv = entry.options.get(CONF_FIRETV_ENTITY) or None
    async_add_entities(
        [
            SleepTimerEndSensor(hass, entry, data.timer),
            TiviMateChannelSensor(hass, entry, data.tivimate, firetv),
            TiviMateProgramSensor(hass, entry, data.tivimate, firetv),
        ]
    )


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


class _TiviMateSensor(ExtrasEntity, RestoreEntity, SensorEntity):
    """Base for values reported by the TiviMate Channel Bridge app on the Fire TV."""

    _field = "channel"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ExtrasConfigEntry,
        bridge: TiviMateBridge,
        firetv: str | None,
        key: str,
    ) -> None:
        super().__init__(hass, entry, key)
        self._bridge = bridge
        self._firetv = firetv
        # Only useful for people with TiviMate: enabled by default once a Fire TV is set.
        self._attr_entity_registry_enabled_default = firetv is not None

    @property
    def available(self) -> bool:
        return True

    @property
    def tivimate_active(self) -> bool:
        """True if the Fire TV currently runs TiviMate (or we cannot tell)."""
        if not self._firetv:
            return True
        state = self.hass.states.get(self._firetv)
        if state is None:
            return True
        app = state.attributes.get("app_id") or state.attributes.get("source")
        return app in (TIVIMATE_PACKAGE, "TiviMate") and state.state not in ("off", "standby")

    @property
    def native_value(self) -> str | None:
        if not self.tivimate_active:
            return None
        value = self._bridge.data.get(self._field)
        return str(value)[:255] if value else None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._bridge.async_add_listener(self.async_write_ha_state))
        if self._firetv:
            self.async_on_remove(
                async_track_state_change_event(self.hass, [self._firetv], self._tv_changed)
            )
        last = await self.async_get_last_state()
        if last is not None and last.state not in ("unknown", "unavailable"):
            restored = {k: last.attributes.get(k) for k in FIELDS}
            restored[self._field] = last.state
            self._bridge.restore(restored)


class TiviMateChannelSensor(_TiviMateSensor):
    _attr_translation_key = "tivimate_channel"
    _attr_icon = "mdi:television-classic"
    _field = "channel"

    def __init__(self, hass, entry, bridge, firetv) -> None:
        super().__init__(hass, entry, bridge, firetv, "tivimate_channel")

    @property
    def extra_state_attributes(self) -> dict:
        d = self._bridge.data
        return {"number": d.get("number"), "program": d.get("program"), "source": d.get("source")}


class TiviMateProgramSensor(_TiviMateSensor):
    _attr_translation_key = "tivimate_program"
    _attr_icon = "mdi:television-guide"
    _field = "program"

    def __init__(self, hass, entry, bridge, firetv) -> None:
        super().__init__(hass, entry, bridge, firetv, "tivimate_program")

    @property
    def extra_state_attributes(self) -> dict:
        d = self._bridge.data
        return {
            "channel": d.get("channel"),
            "program_time": d.get("program_time"),
            "next_program": d.get("next_program"),
            "texts": d.get("texts"),
        }
