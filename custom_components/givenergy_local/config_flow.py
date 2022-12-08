"""Config flow for GivEnergy integration."""
from __future__ import annotations

from typing import Any

import async_timeout
from givenergy_modbus.client import GivEnergyClient, Plant
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import CONF_HOST, CONF_NUM_BATTERIES, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Required(CONF_NUM_BATTERIES): int}
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    plant = Plant(number_batteries=data[CONF_NUM_BATTERIES])
    client = GivEnergyClient(data[CONF_HOST])
    async with async_timeout.timeout(10):
        await hass.async_add_executor_job(client.refresh_plant, plant, True)

    serial_no: str = plant.inverter.inverter_serial_number
    return serial_no


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
            serial_no = await validate_input(self.hass, user_input)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed to validate inverter configuration")
            errors["base"] = "cannot_connect"
        else:
            return self.async_create_entry(
                title=f"Solar Inverter (S/N {serial_no})", data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )
