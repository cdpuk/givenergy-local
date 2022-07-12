"""Config flow for GivEnergy integration."""
from __future__ import annotations

from typing import Any

import async_timeout
from givenergy_modbus.client import GivEnergyClient, Plant
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol

from .const import CONF_HOST, CONF_NUM_BATTERIES, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Required(CONF_NUM_BATTERIES): int}
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        plant = Plant(number_batteries=data[CONF_NUM_BATTERIES])
        client = GivEnergyClient(data[CONF_HOST])
        async with async_timeout.timeout(10):
            await hass.async_add_executor_job(client.refresh_plant, plant, True)

        serial_no = plant.inverter.inverter_serial_number
        return {"title": f"Solar Inverter (S/N {serial_no})", "host": data[CONF_HOST]}
    except Exception as ex:  # pylint: disable=broad-except
        raise CannotConnect from ex


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for GivEnergy."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
