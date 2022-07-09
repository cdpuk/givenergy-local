"""givenergy_modbus library wrappers."""
from __future__ import annotations

from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.plant import Plant

from .const import LOGGER


class GivEnergyException(Exception):
    """An error encountered when fetching data from the inverter."""


class GivEnergy:
    """A lightweight wrapper around the underlying givenergy_modbus library."""

    initial_load_complete = False

    def __init__(self, host: str, num_batteries: int) -> None:
        """Prepare for inverter connections."""
        self.host = host
        self.plant = Plant(number_batteries=num_batteries)

    def fetch_data(self) -> Plant:
        """Fetch data from the inverter via modbus."""
        LOGGER.info("Fetching data from %s", self.host)
        try:
            client = GivEnergyClient(self.host)
            if self.initial_load_complete:
                LOGGER.info("Performing partial refresh")
                client.refresh_plant(self.plant, full_refresh=False)
            else:
                LOGGER.info("Performing full refresh")
                client.refresh_plant(self.plant, full_refresh=True)
                self.initial_load_complete = True
        finally:
            # We seem to have better reliability when we avoid reusing the client object
            # Close the underlying socket to clean up resources
            client.modbus_client.close()

        # The connection sometimes returns what it claims is valid data, but many of the values
        # are zero. This is particularly painful when values are used in the energy dashboard,
        # as the dashboard double counts everything up to the point in the day when the figures
        # go back to normal. Work around this by detecting some extremely unlikely zero values.
        heatsink_temp = self.plant.inverter.temp_inverter_heatsink
        charger_temp = self.plant.inverter.temp_charger
        if heatsink_temp == 0 and charger_temp == 0:
            raise GivEnergyException("Zero values received")

        return self.plant
