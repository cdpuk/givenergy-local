"""Config flow for GivEnergy integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from enum import StrEnum
import socket

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
import voluptuous as vol

from .const import CONF_HOST, DOMAIN, LOGGER
from .givenergy_modbus.client.client import Client
from .givenergy_modbus.exceptions import CommunicationError

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})
STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class ConfigFlowError(StrEnum):
    """User-visible config flow error keys."""

    CANNOT_CONNECT = "cannot_connect"
    INVALID_HOST = "invalid_host"
    INVALID_INVERTER = "invalid_inverter"
    ALREADY_CONFIGURED = "already_configured"
    DIFFERENT_INVERTER = "different_inverter"


class InvalidInverterError(Exception):
    """Raised when a host responds, but not like a usable inverter."""


def _normalise_host(host: str) -> str:
    """Normalise and sanity-check host input before connecting."""
    normalised_host = host.strip()

    if not normalised_host:
        raise ValueError("Host cannot be blank")

    if "://" in normalised_host or "/" in normalised_host:
        raise ValueError("Host must be a hostname or IP address")

    return normalised_host


def _map_validation_error(err: Exception) -> ConfigFlowError:
    """Map internal validation failures to translated config-flow errors."""
    if isinstance(err, (ValueError, socket.gaierror)):
        return ConfigFlowError.INVALID_HOST

    if isinstance(
        err, (CommunicationError, TimeoutError, OSError, asyncio.TimeoutError)
    ):
        return ConfigFlowError.CANNOT_CONNECT

    if isinstance(err, (AttributeError, InvalidInverterError)):
        return ConfigFlowError.INVALID_INVERTER

    return ConfigFlowError.CANNOT_CONNECT


async def _validate_input(data: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Validate and normalise user input, returning clean data and inverter serial."""
    validated_data = dict(data)
    validated_data[CONF_HOST] = _normalise_host(str(data[CONF_HOST]))

    serial_no = (await read_inverter_serial(validated_data)).strip()
    if not serial_no:
        raise InvalidInverterError("Inverter serial number was blank")

    return validated_data, serial_no


async def read_inverter_serial(data: dict[str, Any]) -> str:
    """Validate user input by reading the inverter serial number."""
    client = Client(data[CONF_HOST], 8899)
    try:
        async with asyncio.timeout(10):
            await client.connect()
            await client.detect_plant()
        serial_no: str = client.plant.inverter.serial_number
    finally:
        await client.close()

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

        errors: dict[str, str] = {}

        try:
            validated_input, serial_no = await _validate_input(user_input)
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception("Failed to validate inverter configuration")
            errors["base"] = _map_validation_error(err)
        else:
            await self.async_set_unique_id(serial_no)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Solar Inverter (S/N {serial_no})", data=validated_input
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
        """Allow users to update the configured inverter host in place."""
        entry = self._get_reconfigure_entry()

        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_RECONFIGURE_DATA_SCHEMA,
                    {CONF_HOST: entry.data.get(CONF_HOST, "")},
                ),
            )

        errors: dict[str, str] = {}

        try:
            validated_input, serial_no = await _validate_input(user_input)
        except Exception as err:  # pylint: disable=broad-except
            LOGGER.exception("Failed to validate inverter reconfiguration")
            errors["base"] = _map_validation_error(err)
        else:
            existing_entry = await self.async_set_unique_id(
                serial_no, raise_on_progress=False
            )
            if existing_entry is not None and existing_entry.entry_id != entry.entry_id:
                return self.async_abort(reason=ConfigFlowError.ALREADY_CONFIGURED)
            if entry.unique_id is not None:
                self._abort_if_unique_id_mismatch(
                    reason=ConfigFlowError.DIFFERENT_INVERTER
                )

            return self.async_update_reload_and_abort(
                entry,
                unique_id=serial_no,
                data={**entry.data, **validated_input},
                title=f"Solar Inverter (S/N {serial_no})",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )
