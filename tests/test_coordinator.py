"""Tests for the GivEnergy update coordinator."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from givenergy_modbus.exceptions import ReadFailure, RefreshPartiallySucceeded
from givenergy_modbus.model.inverter import Model
from givenergy_modbus.model.plant import Plant, PlantCapabilities
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

from custom_components.givenergy_local.const import DOMAIN
from custom_components.givenergy_local.coordinator import GivEnergyUpdateCoordinator
from tests.const import MOCK_CONFIG


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="test",
        version=2,
    )
    entry.add_to_hass(hass)
    return entry


async def test_coordinator_tolerates_hr300_partial_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Gen 1 AC Coupled inverters that time out on HR 300 proceed with partial config."""
    coordinator = GivEnergyUpdateCoordinator(hass, mock_config_entry)

    mock_plant = MagicMock(spec=Plant)
    mock_caps = PlantCapabilities(device_type=Model.AC)
    mock_plant.capabilities = mock_caps
    coordinator.client.plant = mock_plant
    coordinator.client.connected = True

    # Simulate load_config raising RefreshPartiallySucceeded when only HR 300 fails
    failure_hr300 = ReadFailure(
        device_address=0x11,
        request_type="ReadHoldingRegistersRequest",
        base_register=300,
        register_count=60,
    )
    partial_exc = RefreshPartiallySucceeded(
        "1 of 5 register reads failed",
        plant=mock_plant,
        failures=[failure_hr300],
        cause=ExceptionGroup("timeout", [TimeoutError()]),
    )

    with (
        patch.object(
            coordinator.client, "load_config", side_effect=partial_exc
        ) as mock_load,
        patch.object(
            coordinator.client,
            "refresh",
            new_callable=AsyncMock,
            return_value=mock_plant,
        ) as mock_refresh,
    ):
        result = await coordinator._async_update_data()

        assert result == mock_plant
        mock_load.assert_called_once_with(retries=2)
        mock_refresh.assert_called_once_with(retries=2)
        assert 300 in coordinator._unsupported_config_blocks
        assert mock_caps.has_ac_config_block is False


async def test_coordinator_re_raises_critical_partial_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Failures on critical holding registers (e.g. HR 0 or 60) are not ignored."""
    coordinator = GivEnergyUpdateCoordinator(hass, mock_config_entry)

    mock_plant = MagicMock(spec=Plant)
    mock_caps = PlantCapabilities(device_type=Model.AC)
    mock_plant.capabilities = mock_caps
    coordinator.client.plant = mock_plant
    coordinator.client.connected = True

    # Simulate a critical register failure (e.g. HR 60 times out)
    failure_hr60 = ReadFailure(
        device_address=0x11,
        request_type="ReadHoldingRegistersRequest",
        base_register=60,
        register_count=60,
    )
    partial_exc = RefreshPartiallySucceeded(
        "1 of 5 register reads failed",
        plant=mock_plant,
        failures=[failure_hr60],
        cause=ExceptionGroup("timeout", [TimeoutError()]),
    )

    with (
        patch.object(coordinator.client, "load_config", side_effect=partial_exc),
        patch.object(
            coordinator.client, "refresh", new_callable=AsyncMock
        ) as mock_refresh,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        mock_refresh.assert_not_called()
