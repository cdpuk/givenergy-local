"""Config flow for GivEnergy integration."""
from __future__ import annotations

from typing import Any

import async_timeout
from custom_components.givenergy_local.givenergy_modbus.client.client import Client
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import CONF_HOST, CONF_NUM_BATTERIES, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Required(CONF_NUM_BATTERIES): int}
)


async def read_inverter_serial(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """Validate user input by reading the inverter serial number."""
    client = Client(data[CONF_HOST], 8899)
    async with async_timeout.timeout(10):
        await client.connect()
        await client.refresh_plant(timeout=5.0)
        await client.close()

    serial_no: str = client.plant.inverter.serial_number
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
            serial_no = await read_inverter_serial(self.hass, user_input)
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
