"""Global fixtures for givenergy_local integration."""
from datetime import time
from unittest.mock import MagicMock, patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations."""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


# Prevent any network requests being made.
@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from API."""
    with patch("givenergy_modbus.client.GivEnergyClient.refresh_plant"):
        yield


# Simulate a network request resulting in an Exception.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate error when retrieving data from API."""
    with patch(
        "givenergy_modbus.client.GivEnergyClient.refresh_plant",
        side_effect=Exception,
    ):
        yield


@pytest.fixture(name="mock_plant")
def mock_plant_fixture():
    """Mock enough inverter and battery data to allow platform setup to succeed."""
    with patch("custom_components.givenergy_local.coordinator.Plant") as mock_ge_plant:
        inverter = MagicMock()
        inverter.inverter_serial_number = "SD12345678"
        inverter.inverter_model = "Mock Inverter"
        inverter.firmware_version = "MOCK"
        inverter.temp_inverter_heatsink = 30
        inverter.temp_battery = 20
        inverter.e_inverter_out_total = 1234
        inverter.charge_slot_1 = [time(0), time(1)]
        inverter.charge_slot_2 = [time(2), time(3)]
        inverter.discharge_slot_1 = [time(16), time(17)]
        inverter.discharge_slot_2 = [time(18), time(19)]
        inverter.battery_charge_limit = 50
        inverter.battery_discharge_limit = 50

        inverter.dict = MagicMock()
        inverter.dict.return_value = inverter.__dict__

        battery1 = MagicMock()
        battery1.battery_serial_number = "BAT01"

        battery2 = MagicMock()
        battery2.battery_serial_number = "BAT02"

        plant_instance = mock_ge_plant.return_value
        plant_instance.inverter = inverter
        plant_instance.batteries = [battery1, battery2]

        yield mock_ge_plant
