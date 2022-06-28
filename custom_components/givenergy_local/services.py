"""GivEnergy services."""
import datetime
from typing import Any

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from custom_components.givenergy_local.givenergy import GivEnergy

from .const import DOMAIN, LOGGER

_ATTR_POWER = "power"
_ATTR_START_TIME = "start_time"
_ATTR_END_TIME = "end_time"

_SERVICE_SET_CHARGE_LIMIT = "set_charge_limit"
_SERVICE_SET_CHARGE_LIMIT_SCHEMA = vol.All(
    vol.Schema({vol.Required(ATTR_DEVICE_ID): str, vol.Required(_ATTR_POWER): int})
)

_SERVICE_ACTIVATE_ECO = "activate_mode_eco"
_SERVICE_ACTIVATE_ECO_SCHEMA = vol.All(vol.Schema({vol.Required(ATTR_DEVICE_ID): str}))

_SERVICE_ACTIVATE_TIMED_EXPORT = "activate_mode_timed_export"
_SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_DEVICE_ID): str,
            vol.Required(_ATTR_START_TIME): str,
            vol.Required(_ATTR_END_TIME): str,
        }
    )
)

_SUPPORTED_SERVICES = [
    _SERVICE_SET_CHARGE_LIMIT,
    _SERVICE_ACTIVATE_ECO,
    _SERVICE_ACTIVATE_TIMED_EXPORT,
]
_SERVICE_TO_SCHEMA = {
    _SERVICE_SET_CHARGE_LIMIT: _SERVICE_SET_CHARGE_LIMIT_SCHEMA,
    _SERVICE_ACTIVATE_ECO: _SERVICE_ACTIVATE_ECO_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_EXPORT: _SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA,
}


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for GivEnergy integration."""

    services = {
        _SERVICE_SET_CHARGE_LIMIT: _async_set_charge_power_limit,
        _SERVICE_ACTIVATE_ECO: _async_activate_mode_eco,
        _SERVICE_ACTIVATE_TIMED_EXPORT: _async_activate_mode_timed_export,
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
        entries = inverter_device_entry.config_entries

    return entries


async def _async_set_charge_power_limit(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Set the maximum battery charge power."""
    for config_entry in await _async_get_config_entries(hass, data[ATTR_DEVICE_ID]):
        connection: GivEnergy = hass.data[DOMAIN][config_entry].connection
        target_value = int(data[_ATTR_POWER] / 64)

        LOGGER.debug(
            "Setting battery charge limit to %d (%dW)", target_value, data[_ATTR_POWER]
        )
        connection.client.set_battery_charge_limit(target_value)


async def _async_activate_mode_eco(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Activate 'Eco' mode, as found in the GivEnergy portal."""
    for config_entry in await _async_get_config_entries(hass, data[ATTR_DEVICE_ID]):
        connection: GivEnergy = hass.data[DOMAIN][config_entry].connection
        LOGGER.debug("Activating eco mode")
        connection.client.set_mode_dynamic()


async def _async_activate_mode_timed_export(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Activate 'Timed Export' mode, as found in the GivEnergy portal."""
    for config_entry in await _async_get_config_entries(hass, data[ATTR_DEVICE_ID]):
        connection: GivEnergy = hass.data[DOMAIN][config_entry].connection
        start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
        end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])

        LOGGER.debug(
            "Activating timed export mode between %s and %s", start_time, end_time
        )
        connection.client.set_mode_storage((start_time, end_time), export=True)
