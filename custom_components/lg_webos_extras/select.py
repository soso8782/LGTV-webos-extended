"""Select entities: sleep timer and sound output."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import ExtrasConfigEntry
from .const import (
    CONF_FIRETV_APPS,
    CONF_FIRETV_ENTITY,
    CONF_FIRETV_INPUT,
    DEFAULT_FIRETV_APPS,
    FIRE2MQTT_DEFAULT_PREFIX,
)
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


def parse_firetv_apps(text: str) -> dict[str, str]:
    """Parse "Netflix=com.netflix.ninja, TiviMate=ar.tvplayer.tv" into {name: package}."""
    apps: dict[str, str] = {}
    for item in text.replace(";", ",").replace("\n", ",").split(","):
        name, sep, package = item.partition("=")
        if sep and name.strip() and package.strip():
            apps[name.strip()] = package.strip()
    return apps


class AppSelect(ExtrasEntity, SelectEntity):
    """Launch a favourite app on the TV itself or on a Fire TV (via Fire2MQTT)."""

    _attr_translation_key = "app"
    _attr_icon = "mdi:apps"

    def __init__(self, hass: HomeAssistant, entry: ExtrasConfigEntry) -> None:
        super().__init__(hass, entry, "app")
        opts = entry.options
        self._configured: list[str] = list(opts.get(CONF_APPS) or [])
        self._firetv: str | None = opts.get(CONF_FIRETV_ENTITY) or None
        self._firetv_input: str | None = opts.get(CONF_FIRETV_INPUT) or None
        self._firetv_apps: dict[str, str] = (
            parse_firetv_apps(opts.get(CONF_FIRETV_APPS, DEFAULT_FIRETV_APPS)) if self._firetv else {}
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._firetv:
            self.async_on_remove(
                async_track_state_change_event(self.hass, [self._firetv], self._tv_changed)
            )

    def _attr(self, entity_id: str | None, name: str):
        state = self.hass.states.get(entity_id) if entity_id else None
        return state.attributes.get(name) if state else None

    @property
    def options(self) -> list[str]:
        tv_apps = self._configured
        if not tv_apps and not self._firetv:
            tv_apps = default_apps(list(self._attr(self._tv, "source_list") or []))
        # Fire TV apps first; TV apps with the same name are skipped.
        return [*self._firetv_apps, *(a for a in tv_apps if a not in self._firetv_apps)]

    @property
    def available(self) -> bool:
        return self.tv_on and bool(self.options)

    @property
    def current_option(self) -> str | None:
        tv_source = self._attr(self._tv, "source")
        if self._firetv and self._firetv_input and tv_source == self._firetv_input:
            ft_source = str(self._attr(self._firetv, "source") or "").lower()
            ft_app = str(self._attr(self._firetv, "app_id") or "").lower()
            for name, package in self._firetv_apps.items():
                if ft_source == name.lower() or ft_app == package.lower():
                    return name
            return None
        return tv_source if tv_source in self.options else None

    def _fire2mqtt_topic(self, command: str) -> str:
        """Build e.g. fire2mqtt/<device_id>/cmd/launch from the Fire2MQTT config entry."""
        ent = er.async_get(self.hass).async_get(self._firetv) if self._firetv else None
        cfg = self.hass.config_entries.async_get_entry(ent.config_entry_id) if ent and ent.config_entry_id else None
        if cfg is None or "device_id" not in cfg.data:
            raise HomeAssistantError("Fire2MQTT zariadenie sa nenašlo – skontroluj Možnosti integrácie")
        prefix = cfg.data.get("topic_prefix", FIRE2MQTT_DEFAULT_PREFIX)
        return f"{prefix}/{cfg.data['device_id']}/cmd/{command}"

    async def _launch_on_firetv(self, package: str) -> None:
        if self._firetv_input and self._attr(self._tv, "source") != self._firetv_input:
            await self.hass.services.async_call(
                "media_player",
                "select_source",
                {ATTR_ENTITY_ID: self._tv, "source": self._firetv_input},
                blocking=True,
            )
        await self.hass.services.async_call(
            "mqtt", "publish", {"topic": self._fire2mqtt_topic("power"), "payload": "wake"}, blocking=True
        )
        await self.hass.services.async_call(
            "mqtt", "publish", {"topic": self._fire2mqtt_topic("launch"), "payload": package}, blocking=True
        )

    async def async_select_option(self, option: str) -> None:
        if option in self._firetv_apps:
            await self._launch_on_firetv(self._firetv_apps[option])
            return
        await self.hass.services.async_call(
            "media_player",
            "select_source",
            {ATTR_ENTITY_ID: self._tv, "source": option},
            blocking=True,
        )
