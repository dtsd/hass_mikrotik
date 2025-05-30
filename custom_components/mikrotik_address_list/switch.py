"""Switch platform for MikroTik Address Lists."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from librouteros.exceptions import LibRouterosError
from librouteros.query import Key

from .const import CONF_ADDRESS_LISTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

def api_select_where(api, id_):
    return api.select(Key('.id'), Key('disabled')).where(Key('.id') == id_)

def api_update(api, id_, disabled):
    return api.update(**{'.id' : id_, 'disabled' : disabled})

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MikroTik Address List switches."""
    api = hass.data[DOMAIN][entry.entry_id]
    address_list_api = api.path("/ip/firewall/address-list")

    address_lists = entry.options.get(CONF_ADDRESS_LISTS, [])

    try:
        address_list_items = await hass.async_add_executor_job(
            address_list_api.select, Key('.id'), Key('list'), Key('address'), Key('comment')
        )

        entities = []
        for item in address_list_items:
            if address_lists and item["list"] not in address_lists:
                continue
            entities.append(MikroTikAddressListSwitch(address_list_api, item))

        async_add_entities(entities, True)
    except LibRouterosError as ex:
        _LOGGER.error("Error fetching address lists: %s", ex)

class MikroTikAddressListSwitch(SwitchEntity):
    """Representation of a MikroTik Address List switch."""

    def __init__(self, address_list_api, address_list_item):
        """Initialize the switch."""
        self._address_list_api = address_list_api
        self._address_list_item = address_list_item
        name = address_list_item['comment'] if 'comment' in address_list_item else address_list_item['address']
        self._attr_name = f"{address_list_item['list']} - {name}"
        self._attr_unique_id = f"{address_list_item['.id']}"
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.hass.async_add_executor_job(
                api_update, self._address_list_api, self._address_list_item[".id"], False
            )
            self._attr_is_on = True
            self.async_write_ha_state()
        except LibRouterosError as ex:
            _LOGGER.error("Error enabling address list item: %s", ex)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.hass.async_add_executor_job(
                api_update, self._address_list_api, self._address_list_item[".id"], True
            )
            self._attr_is_on = False
            self.async_write_ha_state()
        except LibRouterosError as ex:
            _LOGGER.error("Error disabling address list item: %s", ex)

    async def async_update(self) -> None:
        """Update the switch state."""
        try:
            items = await self.hass.async_add_executor_job(
                api_select_where, self._address_list_api, self._address_list_item[".id"]
            )
            for item in items:
                self._attr_is_on = not item['disabled']

        except LibRouterosError as ex:
            _LOGGER.error("Error updating address list item: %s", ex)

