"""Base entity for LG webOS Extras."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_TV_ENTITY, DEFAULT_APP_EXACT, DEFAULT_APP_KEYWORDS, DOMAIN


def default_apps(sources: list[str]) -> list[str]:
    """Pick Netflix / HBO Max / TiviMate from the TV source list."""
    picked = []
    for name in sources:
        low = name.lower().strip()
        if low in DEFAULT_APP_EXACT or any(k in low for k in DEFAULT_APP_KEYWORDS):
            picked.append(name)
    return picked


def tv_device_info(hass: HomeAssistant, entry: ConfigEntry) -> DeviceInfo:
    """Attach our entities to the TV's existing device when possible."""
    tv = entry.data[CONF_TV_ENTITY]
    ent = er.async_get(hass).async_get(tv)
    if ent and ent.device_id:
        device = dr.async_get(hass).async_get(ent.device_id)
        if device and device.identifiers:
            return DeviceInfo(identifiers=device.identifiers)
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="LG",
    )


class ExtrasEntity(Entity):
    """Common base: follows the TV entity state."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, key: str) -> None:
        self._tv = entry.data[CONF_TV_ENTITY]
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = tv_device_info(hass, entry)

    @property
    def tv_on(self) -> bool:
        state = self.hass.states.get(self._tv)
        return state is not None and state.state == STATE_ON

    @property
    def tv_reachable(self) -> bool:
        state = self.hass.states.get(self._tv)
        return state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._tv], self._tv_changed)
        )

    @callback
    def _tv_changed(self, event: Event[EventStateChangedData]) -> None:
        self.async_write_ha_state()
