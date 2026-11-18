"""Sleep timer logic for LG webOS Extras."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging

from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import WARNING_SECONDS, WEBOSTV_DOMAIN

_LOGGER = logging.getLogger(__name__)


class SleepTimer:
    """Turns the TV off at a given time."""

    def __init__(self, hass: HomeAssistant, tv_entity_id: str, warning: bool) -> None:
        self.hass = hass
        self.tv_entity_id = tv_entity_id
        self.warning = warning
        self.end: datetime | None = None
        self.preset: str | None = None
        self._unsub_fire: CALLBACK_TYPE | None = None
        self._unsub_warn: CALLBACK_TYPE | None = None
        self._unsub_state: CALLBACK_TYPE | None = None
        self._listeners: list[Callable[[], None]] = []

    # ---- listeners -------------------------------------------------------
    @callback
    def async_add_listener(self, update: Callable[[], None]) -> CALLBACK_TYPE:
        """Register a callback called whenever the timer changes."""
        self._listeners.append(update)

        @callback
        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    @callback
    def _notify(self) -> None:
        for update in list(self._listeners):
            update()

    # ---- lifecycle -------------------------------------------------------
    @callback
    def async_setup(self) -> None:
        """Cancel the timer when the TV is turned off some other way."""
        self._unsub_state = async_track_state_change_event(
            self.hass, [self.tv_entity_id], self._tv_changed
        )

    @callback
    def async_shutdown(self) -> None:
        self._cancel_jobs()
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        self._listeners.clear()

    @callback
    def _tv_changed(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if self.end is not None and new_state is not None and new_state.state == STATE_OFF:
            _LOGGER.debug("TV turned off, cancelling sleep timer")
            self.cancel()

    # ---- control ---------------------------------------------------------
    @property
    def active(self) -> bool:
        return self.end is not None

    @callback
    def start(self, minutes: int, preset: str | None = None) -> None:
        """Start (or restart) the timer."""
        self.end = dt_util.utcnow() + timedelta(minutes=minutes)
        self.preset = preset
        self._schedule()
        self._notify()

    @callback
    def restore(self, end: datetime, preset: str | None) -> None:
        """Restore a timer after Home Assistant restart."""
        if end <= dt_util.utcnow():
            return
        self.end = end
        self.preset = preset
        self._schedule()
        self._notify()

    @callback
    def cancel(self) -> None:
        self._cancel_jobs()
        self.end = None
        self.preset = None
        self._notify()

    @callback
    def _cancel_jobs(self) -> None:
        if self._unsub_fire:
            self._unsub_fire()
            self._unsub_fire = None
        if self._unsub_warn:
            self._unsub_warn()
            self._unsub_warn = None

    @callback
    def _schedule(self) -> None:
        self._cancel_jobs()
        assert self.end is not None
        self._unsub_fire = async_track_point_in_utc_time(self.hass, self._fire, self.end)
        warn_at = self.end - timedelta(seconds=WARNING_SECONDS)
        if self.warning and warn_at > dt_util.utcnow():
            self._unsub_warn = async_track_point_in_utc_time(self.hass, self._warn, warn_at)

    async def _warn(self, _now: datetime) -> None:
        self._unsub_warn = None
        try:
            await self.hass.services.async_call(
                WEBOSTV_DOMAIN,
                "command",
                {
                    ATTR_ENTITY_ID: self.tv_entity_id,
                    "command": "system.notifications/createToast",
                    "payload": {"message": "TV sa vypne o 1 minútu (časovač)"},
                },
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001 - a missing toast must not break the timer
            _LOGGER.debug("Could not show warning toast: %s", err)

    async def _fire(self, _now: datetime) -> None:
        self._unsub_fire = None
        self.end = None
        self.preset = None
        self._notify()
        _LOGGER.debug("Sleep timer finished, turning off %s", self.tv_entity_id)
        try:
            await self.hass.services.async_call(
                "media_player",
                "turn_off",
                {ATTR_ENTITY_ID: self.tv_entity_id},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Sleep timer could not turn off %s: %s", self.tv_entity_id, err)
