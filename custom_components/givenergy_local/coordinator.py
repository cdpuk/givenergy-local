"""The GivEnergy update coordinator."""
from __future__ import annotations

from datetime import timedelta
from logging import getLogger
from typing import Any, Coroutine

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from givenergy_modbus.client.client import Client
from givenergy_modbus.model.plant import Plant

_LOGGER = getLogger(__name__)


class GivEnergyException(Exception):
    """An error encountered when fetching data from the inverter."""


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that fetches data from a GivEnergy inverter."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Inverter",
            update_interval=timedelta(seconds=30),
        )

        self.host = host
        self.client = Client(host, 8899)

    async def async_shutdown(self) -> Coroutine[Any, Any, None]:
        await self.client.close()
        return await super().async_shutdown()

    async def _async_update_data(self) -> Plant:
        """Fetch data from the inverter."""
        if not self.client.connected:
            await self.client.connect()

        try:
            async with async_timeout.timeout(10):
                _LOGGER.info("Fetching data from %s", self.host)
                return await self.client.refresh_plant()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with inverter: {err}") from err
