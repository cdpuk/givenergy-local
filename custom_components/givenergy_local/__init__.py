"""The GivEnergy integration."""
from __future__ import annotations

from datetime import timedelta

import async_timeout
from givenergy_modbus.model.plant import Plant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_HOST, CONF_NUM_BATTERIES, DOMAIN, LOGGER
from .givenergy import GivEnergy

_PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GivEnergy from a config entry."""
    host = entry.data.get(CONF_HOST)
    num_batteries = entry.data.get(CONF_NUM_BATTERIES)

    connection = GivEnergy(host, num_batteries)
    coordinator = GivEnergyUpdateCoordinator(hass, connection)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.config_entries.async_setup_platforms(entry, _PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(
        entry, _PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrates old config versions to the latest."""

    LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        new = {**entry.data}
        new[CONF_NUM_BATTERIES] = 0
        entry.version = 2
        hass.config_entries.async_update_entry(entry, data=new)

        LOGGER.info("Migration to version %s successful", entry.version)
        return True
    else:
        LOGGER.error("Existing schema verson %s is not supported", entry.version)
        return False


class GivEnergyUpdateCoordinator(DataUpdateCoordinator[Plant]):
    """Update coordinator that enables efficient batched updates to all entities associated with an inverter."""

    def __init__(self, hass: HomeAssistant, connection: GivEnergy) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name="Inverter",
            update_interval=timedelta(seconds=60),
        )
        self.connection = connection

    async def _async_update_data(self) -> Plant:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                return await self.hass.async_add_executor_job(
                    self.connection.fetch_data
                )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
