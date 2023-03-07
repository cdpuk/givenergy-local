"""Global fixtures for givenergy_local integration."""
# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)
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


# This fixture, when used, will result in calls to fetch_data to return None. To have the call
# return a value, we would add the `return_value=<VALUE_TO_RETURN>` parameter to the patch call.
@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture():
    """Skip calls to get data from API."""
    with patch(
        "custom_components.givenergy_local.coordinator.GivEnergyUpdateCoordinator._fetch_data"
    ):
        yield


# In this fixture, we are forcing calls to async_get_data to raise an Exception. This is useful
# for exception handling.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate error when retrieving data from API."""
    with patch(
        "custom_components.givenergy_local.coordinator.GivEnergyUpdateCoordinator._fetch_data",
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
