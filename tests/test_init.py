"""Test givenergy_local setup process."""
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.givenergy_local import async_migrate_entry, async_setup_entry
from custom_components.givenergy_local.const import (
    CONF_HOST,
    CONF_NUM_BATTERIES,
    DOMAIN,
)

from .const import MOCK_CONFIG


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
