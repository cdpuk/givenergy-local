"""givenergy_modbus library wrappers."""
from __future__ import annotations

from givenergy_modbus.client import GivEnergyClient
from givenergy_modbus.model.plant import Plant

from .const import LOGGER


class GivEnergy:
    """A lightweight wrapper around the underlying givenergy_modbus library."""

    initial_load_complete = False

    def __init__(self, host: str, num_batteries: int = 1) -> None:
        """Prepare an inverter connection."""
        LOGGER.info("Connecting to %s", host)
        self.client = GivEnergyClient(host)
        self.plant = Plant(number_batteries=num_batteries)

    def fetch_data(self) -> Plant:
        """Fetch data from the inverter via modbus."""
        if self.initial_load_complete:
            LOGGER.info("Performing partial refresh")
            self.client.refresh_plant(self.plant, full_refresh=False)
        else:
            LOGGER.info("Performing full refresh")
            self.client.refresh_plant(self.plant, full_refresh=True)
            self.initial_load_complete = True

        return self.plant
