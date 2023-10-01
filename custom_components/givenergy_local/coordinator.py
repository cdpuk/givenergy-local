"""The GivEnergy update coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Coroutine

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .givenergy_modbus.client.client import Client
from .givenergy_modbus.model.plant import Plant

_LOGGER = getLogger(__name__)
_FULL_REFRESH_INTERVAL = timedelta(minutes=5)


class GivEnergyException(Exception):
    """An error encountered when fetching data from the inverter."""


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that enables efficient batched updates to all entities associated with an inverter."""

    require_full_refresh = True
    last_full_refresh = datetime.min

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
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        if not self.client.connected:
            await self.client.connect()

        if self.last_full_refresh < (datetime.utcnow() - _FULL_REFRESH_INTERVAL):
            self.require_full_refresh = True

        try:
            async with async_timeout.timeout(10):
                await self._fetch_data(self.require_full_refresh)
                return self.client.plant
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_data(self, full_refresh: bool) -> None:
        """Fetch data from the inverter via modbus."""
        _LOGGER.info("Fetching data from %s", self.host)
        await self.client.refresh_plant()

    async def async_request_full_refresh(self) -> None:
        """Force a full update from the inverter."""
        self.require_full_refresh = True
        await self.async_request_refresh()
