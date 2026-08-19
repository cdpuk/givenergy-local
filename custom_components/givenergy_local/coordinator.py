"""The GivEnergy update coordinator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
_EXECUTE_TIMEOUT = 15.0

# Bound on how long we will wait for the underlying socket to close. A half-dead
# dongle can leave writer.wait_closed() hanging (or raising TimeoutError)
# indefinitely; without a bound, tearing down a wedged connection can itself
# wedge the coordinator (see issue #147).
_CLOSE_TIMEOUT = 5.0

# Bound on connect()+detect() at the top of each poll.
_CONNECT_TIMEOUT = 15.0

# Backoff applied between reconnect attempts while the inverter is unreachable,
# so a sick dongle is not handed a fresh socket every 10s poll while its limited
# connection slots are still draining (see issue #147 - stale sockets on the
# WiFi bridge).
_RECONNECT_BACKOFF_INITIAL = 10.0
_RECONNECT_BACKOFF_MAX = 60.0


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
        self._reconnect_backoff = _RECONNECT_BACKOFF_INITIAL
        self._next_reconnect_attempt = datetime.min.replace(tzinfo=UTC)

    async def async_shutdown(self) -> None:
        """Terminate the modbus connection and shut down the coordinator.

        Unschedules the refresh first, unconditionally: stopping the
        coordinator must never be contingent on the socket closing cleanly.
        This method must never raise - HA runs it as a detached task from the
        config entry's on-unload processing, so an exception here would only
        ever be logged, never surfaced or retried (see issue #147).
        """
        _LOGGER.debug("Shutting down")
        await super().async_shutdown()
        await self._close_client()

    async def _close_client(self) -> bool:
        """Close the current client, bounded and never raising.

        Returns True on a clean close. On timeout or any other failure, the
        client is discarded and replaced with a fresh, disconnected one: a
        Client whose close() has failed can never be revived, because
        writer.wait_closed() keeps re-raising off the same already-failed
        close-waiter future on every subsequent attempt (issue #147).
        Rebuilding is the only way out available from here, short of an
        upstream fix.
        """
        client = self.client
        try:
            async with asyncio.timeout(_CLOSE_TIMEOUT):
                await client.close()
        except Exception as err:  # noqa: BLE001 - deliberately broad, see docstring
            _LOGGER.warning(
                "Failed to close inverter connection cleanly, abandoning it: %s", err
            )
            for task in (
                getattr(client, "network_consumer_task", None),
                getattr(client, "network_producer_task", None),
            ):
                if task is not None and not task.done():
                    task.cancel()
            self.client = Client(self.host, 8899)
            return False
        return True

    async def _reconnect(self) -> None:
        """Establish (or re-establish) the connection and device topology.

        Bounded, and converts connection failures into UpdateFailed rather
        than letting them escape raw. Backs off between attempts so a sick
        dongle is not handed a fresh socket every 10s poll while its
        connection slots are still draining.
        """
        if datetime.now(UTC) < self._next_reconnect_attempt:
            raise UpdateFailed("Waiting before next reconnect attempt")

        try:
            async with asyncio.timeout(_CONNECT_TIMEOUT):
                await self.client.connect()
                # Discover device type and topology. This populates
                # plant.capabilities, which the config/measurement reads
                # below rely on. A freshly detected plant has no register
                # data yet, so force a full refresh this cycle.
                await self.client.detect()
        except (CommunicationError, TimeoutError) as err:
            await self._close_client()
            self._next_reconnect_attempt = datetime.now(UTC) + timedelta(
                seconds=self._reconnect_backoff
            )
            _LOGGER.warning(
                "Failed to connect to inverter at %s, retrying in %.0fs: %s",
                self.host,
                self._reconnect_backoff,
                err,
            )
            self._reconnect_backoff = min(
                self._reconnect_backoff * 2, _RECONNECT_BACKOFF_MAX
            )
            raise UpdateFailed(f"Failed to connect to inverter: {err}") from err

        self._reconnect_backoff = _RECONNECT_BACKOFF_INITIAL
        self._next_reconnect_attempt = datetime.min.replace(tzinfo=UTC)
        self.require_full_refresh = True

    async def _async_update_data(self) -> Plant:
        """Fetch data from the inverter."""
        if not self.client.connected:
            await self._reconnect()

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
                    _LOGGER.debug(
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
            except TimeoutError as err:
                # For some inverters/environments, frequent timeout errors occur.
                # In such cases, a retry using the same connection is often unsuccessful.
                # To prevent 'unavailable' data in HA, we close the connection here so the
                # next poll's top-of-loop check reconnects (bounded, with backoff).
                _LOGGER.warning("Plant refresh timed out: %s", err)
                await self._close_client()
                await asyncio.sleep(_REFRESH_DELAY_BETWEEN_ATTEMPTS)
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
                await self._close_client()
                raise UpdateFailed() from err
            except Exception as err:
                _LOGGER.error("Closing connection due to unexpected error: %s", err)
                await self._close_client()
                raise UpdateFailed("Connection closed due to unexpected error") from err

            if self.require_full_refresh:
                self.require_full_refresh = False
                self.last_full_refresh = datetime.now(UTC)
            return plant

        raise UpdateFailed(
            f"Failed to obtain valid data after {_REFRESH_ATTEMPTS} attempts"
        )

    async def execute(self, requests: list[TransparentRequest]) -> None:
        """Execute a set of requests and force an update to read any new values."""
        try:
            async with asyncio.timeout(_EXECUTE_TIMEOUT):
                await self.client.execute(requests, _COMMAND_TIMEOUT, _COMMAND_RETRIES)
        except (TimeoutError, CommunicationError) as err:
            raise HomeAssistantError(
                f"Failed to send command to inverter: {err}"
            ) from err
        self.require_full_refresh = True
        await self.async_request_refresh()
