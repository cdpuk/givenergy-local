"""The GivEnergy update coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from givenergy_modbus.client.client import Client
from givenergy_modbus.exceptions import (
    CommunicationError,
    RefreshFailed,
    RefreshPartiallySucceeded,
)
from givenergy_modbus.model.plant import Plant
from givenergy_modbus.pdu.transparent import TransparentRequest

from .const import CONF_HOST

_LOGGER = getLogger(__name__)
_FULL_REFRESH_INTERVAL = timedelta(minutes=5)
_REFRESH_ATTEMPTS = 3
_REFRESH_DELAY_BETWEEN_ATTEMPTS = 2.0
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
    QC("t_inverter_heatsink", -10, 100),
    QC("t_charger", -10, 100),
    QC("t_battery", -10, 100),
    QC("e_pv_generation_total", 0, 1e6, min_inclusive=False),  # 1GWh
    QC("e_grid_in_total", 0, 1e6, min_inclusive=False),  # 1GWh
    QC("e_grid_out_total", 0, 1e6, min_inclusive=False),  # 1GWh
    QC("battery_soc", 0, 100),
    QC("p_backup", -15e3, 15e3),  # +/- 15kW
    QC("p_grid_out", -1e6, 15e3),  # 15kW export, 1MW import
    QC("p_battery", -15e3, 15e3),  # +/- 15kW
]


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that fetches data from a GivEnergy inverter."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Inverter",
            update_interval=timedelta(seconds=10),
        )

        self.host = str(config_entry.data.get(CONF_HOST))
        self.client = Client(self.host, 8899)
        self.require_full_refresh = True
        self.last_full_refresh = datetime.min.replace(tzinfo=UTC)

    async def async_shutdown(self) -> None:
        """Terminate the modbus connection and shut down the coordinator."""
        _LOGGER.debug("Shutting down")
        await self.client.close()
        await super().async_shutdown()

    async def _async_update_data(self) -> Plant:
        """Fetch data from the inverter."""
        if not self.client.connected:
            await self.client.connect()
            # Discover device type and topology. This populates plant.capabilities,
            # which the config/measurement reads below rely on. A freshly detected
            # plant has no register data yet, so force a full refresh this cycle.
            await self.client.detect()
            self.require_full_refresh = True

        if self.last_full_refresh < (datetime.now(UTC) - _FULL_REFRESH_INTERVAL):
            self.require_full_refresh = True

        # Allow a few attempts to pull back valid data.
        # Within the inverter comms, there are further retries to ensure >some< data is returned
        # to the coordinator, but sometimes we still get bad values. When that data arrives back
        # here, we perform some quality checks and trigger another attempt if something doesn't
        # look right. If all that fails, then data will show as 'unavailable' in the UI.
        attempt = 0
        while attempt < _REFRESH_ATTEMPTS:
            attempt += 1
            try:
                async with asyncio.timeout(10):
                    _LOGGER.info(
                        "Fetching data from %s (attempt=%d/%d, full_refresh=%s)",
                        self.host,
                        attempt,
                        _REFRESH_ATTEMPTS,
                        self.require_full_refresh,
                    )
                    # A full refresh re-reads the holding-register config blocks
                    # (settings, slots, etc.); every poll re-reads the input-register
                    # measurement blocks.
                    if self.require_full_refresh:
                        await self.client.load_config(retries=2)
                    plant = await self.client.refresh(retries=2)
            except RefreshPartiallySucceeded as err:
                # Some device blocks couldn't be read, but the library still
                # returns a plant with whatever data did arrive. Keep it and let the
                # quality checks below decide whether it's good enough to publish.
                _LOGGER.warning("Plant refresh partially succeeded: %s", err)
                plant = err.plant
            except ValueError as err:
                # We expect to hit this path when corrupt data is received and so fails decoding.
                # Since CRC checking was added, hitting this is far less likely.
                _LOGGER.warning("Plant refresh failed due to bad data: %s", err)
                await asyncio.sleep(_REFRESH_DELAY_BETWEEN_ATTEMPTS)
                continue
            except TimeoutError:
                # For some inverters/environments, frequent timeout errors occur.
                # In such cases, a retry using the same connection is often unsuccessful.
                # To prevent 'unavailable' data in HA, we attempt a full reconnect here.
                _LOGGER.warning("Plant refresh timed out")
                await self.client.close()
                await asyncio.sleep(_REFRESH_DELAY_BETWEEN_ATTEMPTS)
                await self.client.connect()
                await self.client.detect()
                self.require_full_refresh = True
                continue
            except RefreshFailed as err:
                # The library couldn't read any usable data this cycle. Retry a few
                # times before giving up and marking the data unavailable.
                _LOGGER.warning("Plant refresh failed: %s", err)
                await asyncio.sleep(_REFRESH_DELAY_BETWEEN_ATTEMPTS)
                continue
            except CommunicationError as err:
                _LOGGER.debug("Closing connection due to communication error: %s", err)
                await self.client.close()
                raise UpdateFailed() from err
            except Exception as err:
                _LOGGER.error("Closing connection due to expected error: %s", err)
                await self.client.close()
                raise UpdateFailed("Connection closed due to expected error") from err

            if not self._is_data_valid(plant):
                await asyncio.sleep(_REFRESH_DELAY_BETWEEN_ATTEMPTS)
                continue

            if self.require_full_refresh:
                self.require_full_refresh = False
                self.last_full_refresh = datetime.now(UTC)
            _LOGGER.info(
                f"Current time: {plant.inverter.model_dump().get('system_time')}"
            )
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

        except (ValueError, KeyError) as err:
            # A register held a value outside the expected range (e.g. an unknown
            # enum value), or an expected register block hasn't been read yet.
            _LOGGER.warning("Failed to decode register data: %s", err)
            return False
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Unexpected register validation error: %s", err)
            return False

        for check in _INVERTER_QUALITY_CHECKS:
            value = inverter_data.model_dump().get(check.attr_name)
            too_low = False
            too_high = False

            if (min_val := check.min) is not None:
                too_low = not (
                    value > min_val or (check.min_inclusive and value >= min_val)
                )
            if (max_val := check.max) is not None:
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
