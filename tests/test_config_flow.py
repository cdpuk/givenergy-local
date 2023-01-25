"""Test givenergy_local config flow."""
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
import pytest

from custom_components.givenergy_local.const import DOMAIN

from .const import MOCK_CONFIG

_MOCK_SERIAL_NO = "AB123456"


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.givenergy_local.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.fixture(name="bypass_validation")
def skip_validation():
    """Bypasses the validation step that attempts to read the serial number from the inverter."""
    with patch(
        "custom_components.givenergy_local.config_flow.read_inverter_serial",
        return_value=_MOCK_SERIAL_NO,
    ):
        yield


@pytest.fixture(name="error_on_validation")
def error_get_data_fixture():
    """Simulate an error trying to read the serial number."""
    with patch(
        "custom_components.givenergy_local.config_flow.read_inverter_serial",
        side_effect=Exception,
    ):
        yield


async def test_successful_config_flow(hass, bypass_validation):
    """Test a successful config flow."""
    # Initialize a config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Check that the config flow shows the user form as the first step
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # If a user were to enter `test_inverter_host` for host,
    # it would result in this function call
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    # Check that the config flow is complete and a new entry is created with
    # the input data
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == f"Solar Inverter (S/N {_MOCK_SERIAL_NO})"
    assert result["data"] == MOCK_CONFIG
    assert result["result"]


async def test_failed_config_flow(hass, error_on_validation):
    """Test a failed config flow due to credential validation failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {"base": "cannot_connect"}
