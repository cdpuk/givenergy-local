"""Test givenergy_local setup process."""
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.givenergy_local import (
    async_migrate_entry,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.givenergy_local.const import (
    CONF_HOST,
    CONF_NUM_BATTERIES,
    DOMAIN,
)
from custom_components.givenergy_local.coordinator import GivEnergyUpdateCoordinator

from .const import MOCK_CONFIG


async def test_setup_unload_and_reload_entry(
    hass: HomeAssistant, bypass_get_data, mock_plant
):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # Set up the entry and assert that the values set during setup are where we expect
    # them to be
    assert await async_setup_entry(hass, config_entry)
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], GivEnergyUpdateCoordinator
    )

    # Reload the entry and assert that the data from above is still there
    assert await async_reload_entry(hass, config_entry) is None
    assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][config_entry.entry_id], GivEnergyUpdateCoordinator
    )

    # Unload the entry and verify that the data has been removed
    assert await async_unload_entry(hass, config_entry)
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_setup_entry_exception(hass: HomeAssistant, error_on_get_data):
    """Test ConfigEntryNotReady when API raises an exception during entry setup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    # In this case we are testing the condition where async_setup_entry raises
    # ConfigEntryNotReady using the `error_on_get_data` fixture which simulates
    # an error.
    with pytest.raises(ConfigEntryNotReady):
        assert await async_setup_entry(hass, config_entry)


async def test_migrate_from_v1(hass: HomeAssistant):
    """Test config entry migration from version 1."""
    v1_config = {CONF_HOST: "test_inverter_host"}
    config_entry = MockConfigEntry(domain=DOMAIN, data=v1_config, entry_id="test")
    assert await async_migrate_entry(hass, config_entry)
    assert config_entry.data[CONF_NUM_BATTERIES] == 0
