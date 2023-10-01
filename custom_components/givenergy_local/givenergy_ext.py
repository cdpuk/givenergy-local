"""GivEnergy client wrapper functions."""
import asyncio

from typing import Callable

from custom_components.givenergy_local.givenergy_modbus.client.client import Client
from homeassistant.core import HomeAssistant

from .const import LOGGER
from .coordinator import GivEnergyUpdateCoordinator

# A bit of a workaround for flaky modbus connections.
# We try to call services a few times, and only allow the exception to escape after we've
# made this many attempts.
_MAX_ATTEMPTS = 5
_DELAY_BETWEEN_ATTEMPTS = 2.0


async def async_reliable_call(
    hass: HomeAssistant,
    coordinator: GivEnergyUpdateCoordinator,
    func: Callable[[Client], None],
) -> None:
    """
    Attempt to reliably call a function on a GivEnergy client.

    When setting values on the inverter, failures are frustratingly common.
    Using this method will make a number of retries before eventually giving up.
    """
    attempts = _MAX_ATTEMPTS

    while attempts > 0:
        LOGGER.debug("Attempting function call (%d attempts left)", attempts)
        client = Client(coordinator.host, 1883)

        try:
            await hass.async_add_executor_job(func, client)
            await coordinator.async_request_full_refresh()
            break
        except AssertionError as err:
            LOGGER.error("Function failed %s", err)
            attempts = attempts - 1
            await asyncio.sleep(_DELAY_BETWEEN_ATTEMPTS)
        finally:
            client.modbus_client.close()
