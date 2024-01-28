"""The GivEnergy update coordinator."""

from __future__ import annotations

from dataclasses import dataclass
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
_REFRESH_ATTEMPTS = 3
_COMMAND_TIMEOUT = 3.0
_COMMAND_RETRIES = 3


@dataclass
class QualityCheck:
    """Defines likely values for a given property."""

    attr_name: str
    min: float | None
    max: float | None
    min_inclusive: bool = True
    max_inclusive: bool = True

    @property
    def range_description(self) -> str:
        """Provide a string representation of the accepted range.

        This uses mathematical notation, where square brackets mean inclusive,
        and round brackets mean exclusive.
        """
        return "%s%s, %s%s" % (  # pylint: disable=consider-using-f-string
            "[" if self.min_inclusive else "(",
            self.min,
            self.max,
            "]" if self.max_inclusive else ")",
        )


QC = QualityCheck
_INVERTER_QUALITY_CHECKS = [
    QC("temp_inverter_heatsink", -10, 100),
    QC("temp_charger", -10, 100),
    QC("temp_battery", -10, 100),
    QC("e_inverter_out_total", 0, 1e6, min_inclusive=False),  # 1GWh
    QC("e_grid_in_total", 0, 1e6, min_inclusive=False),  # 1GWh
    QC("e_grid_out_total", 0, 1e6, min_inclusive=False),  # 1GWh
    QC("battery_percent", 0, 100),
    QC("p_eps_backup", -15e3, 15e3),  # +/- 15kW
    QC("p_grid_out", -1e6, 15e3),  # 15kW export, 1MW import
    QC("p_battery", -15e3, 15e3),  # +/- 15kW
]


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that fetches data from a GivEnergy inverter."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Inverter",
            update_interval=timedelta(seconds=10),
        )

        self.host = host
        self.client = Client(host, 8899)
        self.require_full_refresh = True
        self.last_full_refresh = datetime.min

    async def async_shutdown(self) -> None:
        """Terminate the modbus connection and shut down the coordinator."""
        _LOGGER.debug("Shutting down")
        await self.client.close()
        await super().async_shutdown()

    async def _async_update_data(self) -> Plant:
        """Fetch data from the inverter."""
        if not self.client.connected:
            await self.client.connect()
            self.require_full_refresh = True

        if self.last_full_refresh < (datetime.utcnow() - _FULL_REFRESH_INTERVAL):
            self.require_full_refresh = True

        # Allow a few attempts to pull back valid data.
        # Within the inverter comms, there are further retries to ensure >some< data is returned
        # to the coordinator, but sometimes we still get bad values. When that data arrives back
        # here, we perform some quality checks and trigger another attempt if something doesn't
        # look right. If all that fails, then data will show as 'unavailable' in the UI.
        attempt = 1
        while attempt <= _REFRESH_ATTEMPTS:
            try:
                async with async_timeout.timeout(10):
                    _LOGGER.info(
                        "Fetching data from %s (attempt=%d/%d, full_refresh=%s)",
                        self.host,
                        attempt,
                        _REFRESH_ATTEMPTS,
                        self.require_full_refresh,
                    )
                    plant = await self.client.refresh_plant(
                        full_refresh=self.require_full_refresh, retries=2
                    )
            except Exception as err:
                await self.client.close()
                raise UpdateFailed(f"Error communicating with inverter: {err}") from err

            if not self._is_data_valid(plant):
                attempt += 1
                continue

            if self.require_full_refresh:
                self.require_full_refresh = False
                self.last_full_refresh = datetime.utcnow()
            return plant

        raise UpdateFailed(
            f"Failed to obtain valid data after {_REFRESH_ATTEMPTS} attempts"
        )

    @staticmethod
    def _is_data_valid(plant: Plant) -> bool:
        """Perform checks to ensure returned data actually makes sense.

        The connection sometimes returns what it claims is valid data, but many of the values
        are zero (or other highly improbable values). This is particularly painful when values
        are used in the energy dashboard, as the dashboard double counts everything up to the
        point in the day when the figures go back to normal.
        """
        try:
            inverter_data = plant.inverter
            _ = plant.batteries
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Inverter model failed validation: %s", err)
            return False

        for check in _INVERTER_QUALITY_CHECKS:
            value = inverter_data.dict().get(check.attr_name)
            too_low = False
            too_high = False

            if min_val := check.min:
                too_low = not (
                    value > min_val or (check.min_inclusive and value >= min_val)
                )
            if max_val := check.max:
                too_high = not (
                    value < max_val or (check.max_inclusive and value <= max_val)
                )

            if too_low or too_high:
                _LOGGER.warning(
                    "Data discarded: %s value of %s is out of range %s",
                    check.attr_name,
                    value,
                    check.range_description,
                )
                return False

        return True

    async def execute(self, requests: list[TransparentRequest]) -> None:
        """Execute a set of requests and force an update to read any new values."""
        self.client.execute(requests, _COMMAND_TIMEOUT, _COMMAND_RETRIES)
        self.require_full_refresh = True
        await self.async_request_refresh()
