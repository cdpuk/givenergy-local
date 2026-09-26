"""Test givenergy_local config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.givenergy_local.const import CONF_HOST, DOMAIN

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
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # If a user were to enter `test_inverter_host` for host,
    # it would result in this function call
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    # Check that the config flow is complete and a new entry is created with
    # the input data
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Solar Inverter (S/N {_MOCK_SERIAL_NO})"
    assert result["data"] == MOCK_CONFIG
    assert result["result"]


async def test_failed_config_flow(hass, error_on_validation):
    """Test a failed config flow due to credential validation failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_sets_unique_id(hass, bypass_validation):
    """The inverter serial becomes the entry's unique ID."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=MOCK_CONFIG
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == _MOCK_SERIAL_NO


async def test_config_flow_aborts_for_configured_inverter(hass, bypass_validation):
    """The same inverter cannot be added twice, even under a different host."""
    MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, unique_id=_MOCK_SERIAL_NO
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "some_other_host"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_updates_host(hass, bypass_validation):
    """Reconfiguring stores the new host for the same inverter."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id=_MOCK_SERIAL_NO)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "new_inverter_host"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "new_inverter_host"


async def test_reconfigure_rejects_a_different_inverter(hass, bypass_validation):
    """A host belonging to another inverter must not overwrite this entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id="OTHER123")
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "new_inverter_host"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "different_inverter"
    assert entry.data[CONF_HOST] == MOCK_CONFIG[CONF_HOST]


async def test_reconfigure_adopts_missing_unique_id(hass, bypass_validation):
    """An entry created before unique IDs existed gains one on reconfigure."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id=None)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "new_inverter_host"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == _MOCK_SERIAL_NO


async def test_reconfigure_reports_connection_failure(hass, error_on_validation):
    """A host that cannot be reached is reported on the form, not applied."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id=_MOCK_SERIAL_NO)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "unreachable_host"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data[CONF_HOST] == MOCK_CONFIG[CONF_HOST]


async def test_reconfigure_rejects_inverter_owned_by_another_entry(
    hass, bypass_validation
):
    """A legacy entry must not adopt a serial another entry already owns."""
    other = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: "other_host"}, unique_id=_MOCK_SERIAL_NO
    )
    other.add_to_hass(hass)
    legacy = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, unique_id=None)
    legacy.add_to_hass(hass)

    result = await legacy.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "other_host"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert legacy.unique_id is None
    assert legacy.data[CONF_HOST] == MOCK_CONFIG[CONF_HOST]
