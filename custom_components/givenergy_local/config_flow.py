"""Config flow for GivEnergy integration."""

import asyncio
from typing import Any

import voluptuous as vol
from givenergy_modbus.client.client import Client
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_HOST, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})
STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


async def read_inverter_serial(data: dict[str, Any]) -> str:
    """Validate user input by reading the inverter serial number."""
    client = Client(data[CONF_HOST], 8899)
    async with asyncio.timeout(10):
        await client.connect()
        # detect() resolves the device topology; load_config() then reads the
        # holding-register identity bank that carries the serial number.
        await client.detect()
        await client.load_config()
        await client.close()

    serial_no: str = client.plant.inverter.serial_number
    return serial_no


class GivEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GivEnergy."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            serial_no = await read_inverter_serial(user_input)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed to validate inverter configuration")
            errors["base"] = "cannot_connect"
        else:
            await self.async_set_unique_id(serial_no)
            self._abort_if_unique_id_configured()
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update the host of an existing inverter, e.g. after a DHCP change."""
        entry = self._get_reconfigure_entry()

        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_RECONFIGURE_DATA_SCHEMA,
                    {CONF_HOST: entry.data.get(CONF_HOST, "")},
                ),
            )

        errors = {}

        try:
            serial_no = await read_inverter_serial(user_input)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Failed to validate inverter configuration")
            errors["base"] = "cannot_connect"
        else:
            # Entries created before unique IDs were assigned have none: adopt the
            # serial we just read, unless another entry already owns that inverter.
            # Otherwise refuse a host that is a different inverter.
            existing_entry = await self.async_set_unique_id(
                serial_no, raise_on_progress=False
            )
            if existing_entry is not None and existing_entry.entry_id != entry.entry_id:
                return self.async_abort(reason="already_configured")
            if entry.unique_id is not None:
                self._abort_if_unique_id_mismatch(reason="different_inverter")

            return self.async_update_reload_and_abort(
                entry,
                unique_id=serial_no,
                data={**entry.data, **user_input},
                title=f"Solar Inverter (S/N {serial_no})",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )
