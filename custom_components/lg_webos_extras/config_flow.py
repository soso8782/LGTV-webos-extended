"""Config flow for LG webOS Extras."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_APPS, CONF_TV_ENTITY, CONF_WARNING, DOMAIN, WEBOSTV_DOMAIN
from .entity import default_apps


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
    """Options: warning toast and apps shown in the app select."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        entry = self.config_entry
        warning = entry.options.get(CONF_WARNING, entry.data.get(CONF_WARNING, True))

        state = self.hass.states.get(entry.data[CONF_TV_ENTITY])
        sources: list[str] = list(state.attributes.get("source_list") or []) if state else []
        apps = entry.options.get(CONF_APPS) or default_apps(sources)
        choices = sorted(set(sources) | set(apps))

        schema = vol.Schema(
            {
                vol.Optional(CONF_WARNING, default=warning): selector.BooleanSelector(),
                vol.Optional(CONF_APPS, default=apps): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=choices,
                        multiple=True,
                        custom_value=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
