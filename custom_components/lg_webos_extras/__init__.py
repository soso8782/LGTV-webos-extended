"""LG webOS Extras: sleep timer, remote buttons, apps, screen and TiviMate info for LG webOS TVs."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_TV_ENTITY, CONF_WARNING
from .sleep_timer import SleepTimer
from .tivimate import TiviMateBridge

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]


@dataclass
class ExtrasData:
    timer: SleepTimer
    tivimate: TiviMateBridge


type ExtrasConfigEntry = ConfigEntry[ExtrasData]


async def async_setup_entry(hass: HomeAssistant, entry: ExtrasConfigEntry) -> bool:
    """Set up LG webOS Extras from a config entry."""
    warning = entry.options.get(CONF_WARNING, entry.data.get(CONF_WARNING, True))
    timer = SleepTimer(hass, entry.data[CONF_TV_ENTITY], warning)
    timer.async_setup()
    tivimate = TiviMateBridge(hass)
    tivimate.async_register()
    entry.runtime_data = ExtrasData(timer=timer, tivimate=tivimate)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ExtrasConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.timer.async_shutdown()
        entry.runtime_data.tivimate.async_unregister()
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: ExtrasConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
