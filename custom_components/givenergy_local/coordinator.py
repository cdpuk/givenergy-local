"""The GivEnergy update coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger

import async_timeout
from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.plant import Plant
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = getLogger(__name__)
_FULL_REFRESH_INTERVAL = timedelta(minutes=5)


class GivEnergyException(Exception):
    """An error encountered when fetching data from the inverter."""


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that enables efficient batched updates to all entities associated with an inverter."""

    require_full_refresh = True
    last_full_refresh = datetime.min

    def __init__(self, hass: HomeAssistant, host: str, num_batteries: int) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Inverter",
            update_interval=timedelta(seconds=60),
        )

        self.host = host
        self.plant = Plant(number_batteries=num_batteries)

    async def _async_update_data(self) -> Plant:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        if self.last_full_refresh < (datetime.utcnow() - _FULL_REFRESH_INTERVAL):
            self.require_full_refresh = True

        try:
            async with async_timeout.timeout(10):
                await self.hass.async_add_executor_job(
                    self._fetch_data, self.require_full_refresh
                )
                return self.plant
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _fetch_data(self, full_refresh: bool) -> None:
        """Fetch data from the inverter via modbus."""
        _LOGGER.info("Fetching data from %s", self.host)
        try:
            client = GivEnergyClient(self.host)
            if full_refresh:
                _LOGGER.debug("Performing full refresh")
                client.refresh_plant(self.plant, isAIO=False, full_refresh=True)
                self.last_full_refresh = datetime.utcnow()
                self.require_full_refresh = False
            else:
                _LOGGER.debug("Performing partial refresh")
                client.refresh_plant(self.plant, isAIO=False, full_refresh=True)
        finally:
            # We seem to have better reliability when we avoid reusing the client object
            # Close the underlying socket to clean up resources
            client.modbus_client.close()

        # The connection sometimes returns what it claims is valid data, but many of the values
        # are zero. This is particularly painful when values are used in the energy dashboard,
        # as the dashboard double counts everything up to the point in the day when the figures
        # go back to normal. Work around this by detecting some extremely unlikely zero values.
        inverter_data = self.plant.inverter

        # The heatsink and charger temperatures never seem to go below around 10 celsius, even
        # when idle and temperatures well below zero for an outdoor installation.
        heatsink_temp = inverter_data.temp_inverter_heatsink
        charger_temp = inverter_data.temp_charger
        if heatsink_temp == 0 or charger_temp == 0:
            raise GivEnergyException("Data discarded: improbable zero temperature")

        # Total inverter output would only ever be zero prior to commissioning.
        if inverter_data.e_inverter_out_total <= 0:
            raise GivEnergyException("Data discarded: inverter total output <= 0")

    async def async_request_full_refresh(self) -> None:
        """Force a full update from the inverter."""
        self.require_full_refresh = True
        await self.async_request_refresh()
