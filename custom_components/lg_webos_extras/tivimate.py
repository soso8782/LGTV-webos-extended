"""Receive the current TiviMate channel/programme from the TiviMate Channel Bridge app."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from aiohttp import web

from homeassistant.components import webhook
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Same id as the upstream bridge default, so the app works with minimal config.
WEBHOOK_ID = "tivimate_channel"
TIVIMATE_PACKAGE = "ar.tvplayer.tv"
FIELDS = ("channel", "number", "program", "program_time", "next_program", "source", "texts")


class TiviMateBridge:
    """Holds the last report from the bridge and notifies sensors."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.data: dict[str, Any] = {}
        self.updated = None
        self.registered = False
        self._listeners: list[Callable[[], None]] = []

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(update)

        @callback
        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    @callback
    def restore(self, data: dict[str, Any]) -> None:
        """Restore last known values after a restart (only if nothing newer arrived)."""
        if not self.data:
            self.data = {k: data.get(k) for k in FIELDS}

    @callback
    def update(self, payload: dict[str, Any]) -> None:
        if not payload.get("channel"):
            return
        new = {k: payload.get(k) for k in FIELDS}
        # A click in the channel list only carries the channel name: keep the programme
        # if it is still the same channel.
        if new.get("source") == "click" and self.data.get("channel") == new["channel"]:
            return
        self.data = new
        self.updated = dt_util.utcnow()
        _LOGGER.debug("TiviMate: %s", new)
        for update in list(self._listeners):
            update()

    @callback
    def async_register(self) -> None:
        try:
            webhook.async_register(
                self.hass,
                DOMAIN,
                "TiviMate Channel Bridge",
                WEBHOOK_ID,
                self._handle,
                local_only=True,
                allowed_methods=["POST"],
            )
            self.registered = True
        except ValueError:
            _LOGGER.warning(
                "Webhook '%s' is already used (another automation or LG webOS Extras entry); "
                "TiviMate sensors of this entry will not receive data",
                WEBHOOK_ID,
            )

    @callback
    def async_unregister(self) -> None:
        if self.registered:
            webhook.async_unregister(self.hass, WEBHOOK_ID)
            self.registered = False
        self._listeners.clear()

    async def _handle(self, hass: HomeAssistant, webhook_id: str, request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except ValueError:
            return web.Response(status=400, text="invalid json")
        if not isinstance(payload, dict):
            return web.Response(status=400, text="expected object")
        self.update(payload)
        return web.Response(status=200, text="ok")
