"""The GivEnergy update coordinator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from givenergy_modbus.client.client import Client
from givenergy_modbus.exceptions import CommunicationError, RefreshError
from givenergy_modbus.model.plant import Plant
from givenergy_modbus.pdu.transparent import TransparentRequest

from .const import CONF_HOST

_LOGGER = getLogger(__name__)
_FULL_REFRESH_INTERVAL = timedelta(minutes=5)
_REFRESH_ATTEMPTS = 3
_REFRESH_DELAY_BETWEEN_ATTEMPTS = 2.0
_COMMAND_TIMEOUT = 3.0
_COMMAND_RETRIES = 3


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
        # to the coordinator, but decode failures, timeouts and refresh errors can still occur.
        # If all attempts fail, then data will show as 'unavailable' in the UI.
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
            except RefreshError as err:
                # Some or all register reads failed this cycle. Discard any partial
                # data and retry a few times before giving up and marking the data
                # unavailable.
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

    async def execute(self, requests: list[TransparentRequest]) -> None:
        """Execute a set of requests and force an update to read any new values."""
        self.client.execute(requests, _COMMAND_TIMEOUT, _COMMAND_RETRIES)
        self.require_full_refresh = True
        await self.async_request_refresh()
