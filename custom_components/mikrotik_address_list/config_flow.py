"""Config flow for MikroTik Address Lists."""
from __future__ import annotations

import logging
from typing import Any
from functools import partial

import voluptuous as vol
from librouteros import connect
from librouteros.exceptions import LibRouterosError

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ADDRESS_LISTS,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)

STEP_FILTER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ADDRESS_LISTS): cv.multi_select,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain = DOMAIN):
    """Handle a config flow for MikroTik Address Lists."""

    VERSION = 1
    _address_lists: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                connect_func = partial(connect,
                    host = user_input[CONF_HOST],
                    username = user_input[CONF_USERNAME],
                    password = user_input[CONF_PASSWORD],
                    port=user_input[CONF_PORT]
                    )
                api = await self.hass.async_add_executor_job(connect_func)

                # Get available address lists
                self._address_lists = {
                    item["list"]: item["list"]
                    for item in await self.hass.async_add_executor_job(
                        api, "/ip/firewall/address-list/print"
                    )
                }

                api.close()

                if not self._address_lists:
                    errors["base"] = "no_address_lists"
                else:
                    return await self.async_step_filter()

            except LibRouterosError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_filter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the filter step."""
        if user_input is None:
            return self.async_show_form(
                step_id="filter",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_ADDRESS_LISTS): cv.multi_select(
                            self._address_lists
                        ),
                    }
                ),
            )

        return self.async_create_entry(
            title=user_input[CONF_HOST],
            data={
                CONF_HOST: user_input[CONF_HOST],
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_PORT: user_input[CONF_PORT],
                CONF_ADDRESS_LISTS: user_input.get(CONF_ADDRESS_LISTS, []),
            },
        )
