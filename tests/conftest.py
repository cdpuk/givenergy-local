"""Global fixtures for givenergy_local integration."""

from unittest.mock import patch

from homeassistant.helpers.update_coordinator import UpdateFailed
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
    with (
        patch("homeassistant.components.persistent_notification.async_create"),
        patch("homeassistant.components.persistent_notification.async_dismiss"),
    ):
        yield


# Simulate the coordinator failing to obtain data from the inverter.
@pytest.fixture(name="error_on_get_data")
def error_get_data_fixture():
    """Simulate an error when the coordinator refreshes data from the inverter."""
    with patch(
        "custom_components.givenergy_local.coordinator."
        "GivEnergyUpdateCoordinator._async_update_data",
        side_effect=UpdateFailed,
    ):
        yield
