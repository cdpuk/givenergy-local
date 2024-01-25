"""The GivEnergy update coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .givenergy_modbus.client.client import Client
from .givenergy_modbus.model.plant import Plant
from .givenergy_modbus.pdu.transparent import TransparentRequest

_LOGGER = getLogger(__name__)
_FULL_REFRESH_INTERVAL = timedelta(minutes=5)
_COMMAND_TIMEOUT = 3.0
_COMMAND_RETRIES = 3


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
        self.require_full_refresh = True
        self.last_full_refresh = datetime.min

    async def async_shutdown(self) -> None:
        """Terminate the modbus connection and shut down the coordinator."""
        await self.client.close()
        await super().async_shutdown()

    async def _async_update_data(self) -> Plant:
        """Fetch data from the inverter."""
        if not self.client.connected:
            await self.client.connect()
            self.require_full_refresh = True

        if self.last_full_refresh < (datetime.utcnow() - _FULL_REFRESH_INTERVAL):
            self.require_full_refresh = True

        try:
            async with async_timeout.timeout(10):
                _LOGGER.info(
                    "Fetching data from %s (full refresh=%s)",
                    self.host,
                    self.require_full_refresh,
                )
                plant = await self.client.refresh_plant(
                    full_refresh=self.require_full_refresh
                )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with inverter: {err}") from err

        if self.require_full_refresh:
            self.require_full_refresh = False
            self.last_full_refresh = datetime.utcnow()
        return plant

    async def execute(self, requests: list[TransparentRequest]) -> None:
        """Execute a set of requests and force an update to read any new values."""
        self.client.execute(requests, _COMMAND_TIMEOUT, _COMMAND_RETRIES)
        self.require_full_refresh = True
        await self.async_request_refresh()
