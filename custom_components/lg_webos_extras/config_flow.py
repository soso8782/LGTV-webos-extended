"""Config flow for LG webOS Extras."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_TV_ENTITY, CONF_WARNING, DOMAIN, WEBOSTV_DOMAIN


class LgWebosExtrasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            tv = user_input[CONF_TV_ENTITY]
            await self.async_set_unique_id(tv)
            self._abort_if_unique_id_configured()
            state = self.hass.states.get(tv)
            title = state.name if state else tv
            return self.async_create_entry(title=f"{title} Extras", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_TV_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="media_player", integration=WEBOSTV_DOMAIN)
                ),
                vol.Optional(CONF_WARNING, default=True): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LgWebosExtrasOptionsFlow()


class LgWebosExtrasOptionsFlow(OptionsFlow):
    """Options: toggle the warning toast."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_WARNING, self.config_entry.data.get(CONF_WARNING, True)
        )
        schema = vol.Schema(
            {vol.Optional(CONF_WARNING, default=current): selector.BooleanSelector()}
        )
        return self.async_show_form(step_id="init", data_schema=schema)
