"""The GivEnergy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_HOST, CONF_NUM_BATTERIES, DOMAIN, LOGGER
from .coordinator import GivEnergyUpdateCoordinator
from .services import async_setup_services, async_unload_services


_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GivEnergy from a config entry."""
    host = entry.data.get(CONF_HOST)
    num_batteries = entry.data.get(CONF_NUM_BATTERIES)

    coordinator = GivEnergyUpdateCoordinator(hass, host, num_batteries)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(
        entry, _PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unload_services(hass)

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
        LOGGER.error("Existing schema version %s is not supported", entry.version)
        return False
