"""GivEnergy services."""
import asyncio
import datetime

from typing import Any, Callable

from givenergy_modbus.client import GivEnergyClient
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from .const import DOMAIN, LOGGER
from .coordinator import GivEnergyUpdateCoordinator

# A bit of a workaround for flaky modbus connections.
# We try to call services a few times, and only allow the exception to escape after we've
# made this many attempts.
_MAX_ATTEMPTS = 5
_DELAY_BETWEEN_ATTEMPTS = 2.0

_ATTR_POWER = "power"
_ATTR_START_TIME = "start_time"
_ATTR_END_TIME = "end_time"

_SERVICE_SET_CHARGE_LIMIT = "set_charge_limit"
_SERVICE_SET_CHARGE_LIMIT_SCHEMA = vol.All(
    vol.Schema({vol.Required(ATTR_DEVICE_ID): str, vol.Required(_ATTR_POWER): int})
)

_SERVICE_SET_DISCHARGE_LIMIT = "set_discharge_limit"
_SERVICE_SET_DISCHARGE_LIMIT_SCHEMA = _SERVICE_SET_CHARGE_LIMIT_SCHEMA

_SERVICE_ACTIVATE_ECO = "activate_mode_eco"
_SERVICE_ACTIVATE_ECO_SCHEMA = vol.All(vol.Schema({vol.Required(ATTR_DEVICE_ID): str}))

_SERVICE_ACTIVATE_TIMED_DISCHARGE = "activate_mode_timed_discharge"
_SERVICE_ACTIVATE_TIMED_DISCHARGE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_DEVICE_ID): str,
            vol.Required(_ATTR_START_TIME): str,
            vol.Required(_ATTR_END_TIME): str,
        }
    )
)


_SERVICE_ACTIVATE_TIMED_EXPORT = "activate_mode_timed_export"
_SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA = _SERVICE_ACTIVATE_TIMED_DISCHARGE_SCHEMA

_SUPPORTED_SERVICES = [
    _SERVICE_SET_CHARGE_LIMIT,
    _SERVICE_SET_DISCHARGE_LIMIT,
    _SERVICE_ACTIVATE_ECO,
    _SERVICE_ACTIVATE_TIMED_DISCHARGE,
    _SERVICE_ACTIVATE_TIMED_EXPORT,
]
_SERVICE_TO_SCHEMA = {
    _SERVICE_SET_CHARGE_LIMIT: _SERVICE_SET_CHARGE_LIMIT_SCHEMA,
    _SERVICE_SET_DISCHARGE_LIMIT: _SERVICE_SET_DISCHARGE_LIMIT_SCHEMA,
    _SERVICE_ACTIVATE_ECO: _SERVICE_ACTIVATE_ECO_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_DISCHARGE: _SERVICE_ACTIVATE_TIMED_DISCHARGE_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_EXPORT: _SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA,
}


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for GivEnergy integration."""

    services = {
        _SERVICE_SET_CHARGE_LIMIT: _async_set_charge_power_limit,
        _SERVICE_SET_DISCHARGE_LIMIT: _async_set_discharge_power_limit,
        _SERVICE_ACTIVATE_ECO: _async_activate_mode_eco,
        _SERVICE_ACTIVATE_TIMED_DISCHARGE: _async_activate_mode_timed_discharge,
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
        entries = inverter_device_entry.config_entries.copy()

    return entries


async def _async_service_call(
    hass: HomeAssistant, device_id: str, func: Callable[[GivEnergyClient], None]
) -> None:
    # Just take the first matching config entry
    # We really shouldn't have multiple entries for the same device ID
    entries = await _async_get_config_entries(hass, device_id)
    if not entries:
        return

    config_entry = entries.pop()
    attempts = _MAX_ATTEMPTS

    while attempts > 0:
        LOGGER.debug("Attempting service call (%d attempts left)", attempts)
        coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry]
        client = GivEnergyClient(coordinator.host)

        try:
            await hass.async_add_executor_job(func, client)
            await coordinator.async_request_full_refresh()
            break
        except AssertionError as err:
            LOGGER.error("Service call failed %s", err)
            attempts = attempts - 1
            await asyncio.sleep(_DELAY_BETWEEN_ATTEMPTS)
        finally:
            client.modbus_client.close()


async def _async_set_charge_power_limit(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Set the maximum battery charge power."""

    def call(client: GivEnergyClient) -> None:
        target_value = int(data[_ATTR_POWER] / 64)

        # Numbering seems to stop at 39, then jump to 50 = 2.6kW
        if target_value > 39:
            target_value = 50

        LOGGER.debug(
            "Setting battery charge limit to %d (%dW)", target_value, data[_ATTR_POWER]
        )

        client.set_battery_charge_limit(target_value)

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)


async def _async_set_discharge_power_limit(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Set the maximum battery discharge power."""

    def call(client: GivEnergyClient) -> None:
        target_value = int(data[_ATTR_POWER] / 64)

        # Numbering seems to stop at 39, then jump to 50 = 2.6kW
        if target_value > 39:
            target_value = 50

        LOGGER.debug(
            "Setting battery discharge limit to %d (%dW)",
            target_value,
            data[_ATTR_POWER],
        )

        client.set_battery_discharge_limit(target_value)

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)


async def _async_activate_mode_eco(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Activate 'Eco' mode, as found in the GivEnergy portal."""

    def call(client: GivEnergyClient) -> None:
        LOGGER.debug("Activating eco mode")
        client.set_mode_dynamic()

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)


async def _async_activate_mode_timed_discharge(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Activate 'Timed Discharge' mode, as found in the GivEnergy portal."""

    def call(client: GivEnergyClient) -> None:
        start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
        end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])

        LOGGER.debug(
            "Activating timed discharge mode between %s and %s", start_time, end_time
        )
        client.set_mode_storage((start_time, end_time), export=False)

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)


async def _async_activate_mode_timed_export(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Activate 'Timed Export' mode, as found in the GivEnergy portal."""

    def call(client: GivEnergyClient) -> None:
        start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
        end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])

        LOGGER.debug(
            "Activating timed export mode between %s and %s", start_time, end_time
        )
        client.set_mode_storage((start_time, end_time), export=True)

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)
