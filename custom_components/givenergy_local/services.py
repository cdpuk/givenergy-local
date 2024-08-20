"""GivEnergy services."""

import datetime

from typing import Any

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from custom_components.givenergy_local.givenergy_modbus.pdu.transparent import (
    TransparentRequest,
)

from .const import DOMAIN, LOGGER
from .coordinator import GivEnergyUpdateCoordinator
from .givenergy_modbus.client.commands import CommandBuilder
from .givenergy_modbus.model import TimeSlot

_ATTR_START_TIME = "start_time"
_ATTR_END_TIME = "end_time"
_ATTR_CHARGE_TARGET = "charge_target"

# Shared schema that typically defines a charging/discharging slot.
_TIME_SPAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(_ATTR_START_TIME): str,
        vol.Required(_ATTR_END_TIME): str,
    }
)

_SERVICE_ACTIVATE_ECO = "activate_mode_eco"
_SERVICE_ACTIVATE_ECO_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): str})

_SERVICE_ACTIVATE_TIMED_DISCHARGE = "activate_mode_timed_discharge"
_SERVICE_ACTIVATE_TIMED_DISCHARGE_SCHEMA = _TIME_SPAN_SCHEMA

_SERVICE_ACTIVATE_TIMED_EXPORT = "activate_mode_timed_export"
_SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA = _TIME_SPAN_SCHEMA

_SERVICE_ENABLE_TIMED_CHARGE = "enable_timed_charge"
_SERVICE_ENABLE_TIMED_CHARGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Optional(_ATTR_START_TIME): str,
        vol.Optional(_ATTR_END_TIME): str,
        vol.Optional(_ATTR_CHARGE_TARGET): vol.All(
            vol.Coerce(int), vol.Range(min=4, max=100)
        ),
    }
)

_SERVICE_DISABLE_TIMED_CHARGE = "disable_timed_charge"
_SERVICE_DISABLE_TIMED_CHARGE_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): str})

_SUPPORTED_SERVICES = [
    _SERVICE_ACTIVATE_ECO,
    _SERVICE_ACTIVATE_TIMED_DISCHARGE,
    _SERVICE_ACTIVATE_TIMED_EXPORT,
    _SERVICE_ENABLE_TIMED_CHARGE,
    _SERVICE_DISABLE_TIMED_CHARGE,
]
_SERVICE_TO_SCHEMA = {
    _SERVICE_ACTIVATE_ECO: _SERVICE_ACTIVATE_ECO_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_DISCHARGE: _SERVICE_ACTIVATE_TIMED_DISCHARGE_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_EXPORT: _SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA,
    _SERVICE_ENABLE_TIMED_CHARGE: _SERVICE_ENABLE_TIMED_CHARGE_SCHEMA,
    _SERVICE_DISABLE_TIMED_CHARGE: _SERVICE_DISABLE_TIMED_CHARGE_SCHEMA,
}


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for GivEnergy integration."""

    services = {
        _SERVICE_ACTIVATE_ECO: _async_activate_mode_eco,
        _SERVICE_ACTIVATE_TIMED_DISCHARGE: _async_activate_mode_timed_discharge,
        _SERVICE_ACTIVATE_TIMED_EXPORT: _async_activate_mode_timed_export,
        _SERVICE_ENABLE_TIMED_CHARGE: _async_enable_timed_charge,
        _SERVICE_DISABLE_TIMED_CHARGE: _async_disable_timed_charge,
    }

    async def async_call_service(service_call: ServiceCall) -> None:
        """Call correct service."""
        await services[service_call.service](hass, service_call.data)

    for service in _SUPPORTED_SERVICES:
        hass.services.async_register(
            DOMAIN,
            service,
            async_call_service,
            schema=_SERVICE_TO_SCHEMA.get(service),
        )


def async_unload_services(hass: HomeAssistant) -> None:
    """Unload GivEnergy services."""
    for service in _SUPPORTED_SERVICES:
        hass.services.async_remove(DOMAIN, service)


async def _async_get_config_entries(hass: HomeAssistant, device_id: str) -> set[str]:
    """Get config entries for a device."""
    device_registry = dr.async_get(hass)
    inverter_device_entry = device_registry.async_get(device_id)

    entries: set[str] = set()
    if inverter_device_entry:
        entries = inverter_device_entry.config_entries.copy()

    return entries


async def _async_service_call(
    hass: HomeAssistant, device_id: str, commands: list[TransparentRequest]
) -> None:
    # Just take the first matching config entry
    # We really shouldn't have multiple entries for the same device ID
    entries = await _async_get_config_entries(hass, device_id)
    if not entries:
        return

    config_entry = entries.pop()
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry]
    await coordinator.execute(commands)


async def _async_activate_mode_eco(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Activate 'Eco' mode, as found in the GivEnergy portal."""
    LOGGER.debug("Activating eco mode")
    commands = CommandBuilder.set_mode_dynamic()
    await _async_service_call(hass, data[ATTR_DEVICE_ID], commands)


async def _async_activate_mode_timed_discharge(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Activate 'Timed Discharge' mode, as found in the GivEnergy portal."""
    start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
    end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])

    commands = CommandBuilder.set_discharge_mode_to_match_demand()
    commands.extend(CommandBuilder.set_enable_discharge(True))
    commands.extend(CommandBuilder.set_discharge_slot_1(TimeSlot(start_time, end_time)))

    LOGGER.debug(
        "Activating timed discharge mode between %s and %s", start_time, end_time
    )
    await _async_service_call(hass, data[ATTR_DEVICE_ID], commands)


async def _async_activate_mode_timed_export(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Activate 'Timed Export' mode, as found in the GivEnergy portal."""
    start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
    end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])

    commands = CommandBuilder.set_discharge_mode_max_power()
    commands.extend(CommandBuilder.set_enable_discharge(True))
    commands.extend(CommandBuilder.set_discharge_slot_1(TimeSlot(start_time, end_time)))

    LOGGER.debug("Activating timed export mode between %s and %s", start_time, end_time)
    await _async_service_call(hass, data[ATTR_DEVICE_ID], commands)


async def _async_enable_timed_charge(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """
    Enable 'Timed Charge', as found in the GivEnergy portal.

    Note that this isn't a battery mode like "Timed Discharge", "Eco", etc. It operates in
    parallel to those modes.
    """
    commands = CommandBuilder.set_enable_charge(True)

    if _ATTR_START_TIME in data and _ATTR_END_TIME in data:
        start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
        end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])
        commands.extend(
            CommandBuilder.set_charge_slot_1(TimeSlot(start_time, end_time))
        )

    if _ATTR_CHARGE_TARGET in data:
        target_soc = int(data[_ATTR_CHARGE_TARGET])
        commands.extend(CommandBuilder.set_charge_target(target_soc))

    LOGGER.debug("Activating timed charge mode")
    await _async_service_call(hass, data[ATTR_DEVICE_ID], commands)


async def _async_disable_timed_charge(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Disable 'Timed Charge', as found in the GivEnergy portal."""
    LOGGER.debug("Deactivating timed charge mode")
    await _async_service_call(
        hass, data[ATTR_DEVICE_ID], CommandBuilder.set_enable_charge(False)
    )
