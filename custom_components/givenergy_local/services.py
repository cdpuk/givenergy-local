"""GivEnergy services."""
import datetime

from typing import Any, Callable

from givenergy_modbus.client import GivEnergyClient
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from .const import DOMAIN, LOGGER
from .coordinator import GivEnergyUpdateCoordinator
from .givenergy_ext import async_reliable_call

# A bit of a workaround for flaky modbus connections.
# We try to call services a few times, and only allow the exception to escape after we've
# made this many attempts.
_MAX_ATTEMPTS = 5
_DELAY_BETWEEN_ATTEMPTS = 2.0

_ATTR_POWER = "power"
_ATTR_START_TIME = "start_time"
_ATTR_END_TIME = "end_time"
_ATTR_CHARGE_TARGET = "charge_target"

# Shared schema used for setting charge/discharge power limits.
_SET_POWER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(_ATTR_POWER): vol.All(vol.Coerce(int), vol.Range(min=0, max=2600)),
    }
)

# Shared shema that typically defines a charging/discharging slot.
_TIME_SPAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(_ATTR_START_TIME): str,
        vol.Required(_ATTR_END_TIME): str,
    }
)

_SERVICE_SET_CHARGE_LIMIT = "set_charge_limit"
_SERVICE_SET_CHARGE_LIMIT_SCHEMA = _SET_POWER_SCHEMA

_SERVICE_SET_DISCHARGE_LIMIT = "set_discharge_limit"
_SERVICE_SET_DISCHARGE_LIMIT_SCHEMA = _SET_POWER_SCHEMA

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
    _SERVICE_SET_CHARGE_LIMIT,
    _SERVICE_SET_DISCHARGE_LIMIT,
    _SERVICE_ACTIVATE_ECO,
    _SERVICE_ACTIVATE_TIMED_DISCHARGE,
    _SERVICE_ACTIVATE_TIMED_EXPORT,
    _SERVICE_ENABLE_TIMED_CHARGE,
    _SERVICE_DISABLE_TIMED_CHARGE,
]
_SERVICE_TO_SCHEMA = {
    _SERVICE_SET_CHARGE_LIMIT: _SERVICE_SET_CHARGE_LIMIT_SCHEMA,
    _SERVICE_SET_DISCHARGE_LIMIT: _SERVICE_SET_DISCHARGE_LIMIT_SCHEMA,
    _SERVICE_ACTIVATE_ECO: _SERVICE_ACTIVATE_ECO_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_DISCHARGE: _SERVICE_ACTIVATE_TIMED_DISCHARGE_SCHEMA,
    _SERVICE_ACTIVATE_TIMED_EXPORT: _SERVICE_ACTIVATE_TIMED_EXPORT_SCHEMA,
    _SERVICE_ENABLE_TIMED_CHARGE: _SERVICE_ENABLE_TIMED_CHARGE_SCHEMA,
    _SERVICE_DISABLE_TIMED_CHARGE: _SERVICE_DISABLE_TIMED_CHARGE_SCHEMA,
}


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for GivEnergy integration."""

    services = {
        _SERVICE_SET_CHARGE_LIMIT: _async_set_charge_power_limit,
        _SERVICE_SET_DISCHARGE_LIMIT: _async_set_discharge_power_limit,
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
    hass: HomeAssistant, device_id: str, func: Callable[[GivEnergyClient], None]
) -> None:
    # Just take the first matching config entry
    # We really shouldn't have multiple entries for the same device ID
    entries = await _async_get_config_entries(hass, device_id)
    if not entries:
        return

    config_entry = entries.pop()
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry]
    await async_reliable_call(hass, coordinator, func)


async def _async_set_charge_power_limit(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Set the maximum battery charge power."""

    def call(client: GivEnergyClient) -> None:
        target_value = int(data[_ATTR_POWER] / 81)

        # Numbering seems to stop at 30, then jump to 50 = 2.6kW
        # See extensive comments in the corresponding sensor
        if target_value > 30:
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
        target_value = int(data[_ATTR_POWER] / 81)

        # Numbering seems to stop at 30, then jump to 50 = 2.6kW
        # See extensive comments in the corresponding sensor
        if target_value > 30:
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
        client.set_battery_discharge_mode_demand()  # battery_power_mode = 1
        client.enable_discharge()
        client.set_discharge_slot_1([start_time, end_time])

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
        client.set_battery_discharge_mode_max_power()  # battery_power_mode = 0
        client.enable_discharge()
        client.set_discharge_slot_1([start_time, end_time])

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)


async def _async_enable_timed_charge(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """
    Enable 'Timed Charge', as found in the GivEnergy portal.

    Note that this isn't a battery mode like "Timed Discharge", "Eco", etc. It operates in
    parallel to those modes.
    """

    def call(client: GivEnergyClient) -> None:
        LOGGER.debug("Activating timed charge mode")

        client.enable_charge()

        if _ATTR_START_TIME in data and _ATTR_END_TIME in data:
            start_time = datetime.time.fromisoformat(data[_ATTR_START_TIME])
            end_time = datetime.time.fromisoformat(data[_ATTR_END_TIME])
            client.set_charge_slot_1((start_time, end_time))

        if _ATTR_CHARGE_TARGET in data:
            client.enable_charge_target(data[_ATTR_CHARGE_TARGET])

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)


async def _async_disable_timed_charge(
    hass: HomeAssistant, data: dict[str, Any]
) -> None:
    """Disable 'Timed Charge', as found in the GivEnergy portal."""

    def call(client: GivEnergyClient) -> None:
        LOGGER.debug("Deactivating timed charge mode")
        client.disable_charge()

    await _async_service_call(hass, data[ATTR_DEVICE_ID], call)
