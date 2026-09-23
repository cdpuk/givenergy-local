"""Tests for the device registry link between battery and inverter devices."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.givenergy_local.const import DOMAIN
from custom_components.givenergy_local.entity import (
    _HA_SUPPORTS_VIA_DEVICE_ID,
    BatteryEntity,
)

from .const import MOCK_CONFIG

_INVERTER_SERIAL = "SD12345678"


def _battery_entity(
    hass: HomeAssistant | None, config_entry: MockConfigEntry
) -> BatteryEntity:
    """Build a BatteryEntity backed by a minimal coordinator."""
    battery = SimpleNamespace(
        serial_number="BAT01", bms_firmware_version=3015, cap_design2=102
    )
    coordinator = SimpleNamespace(
        last_update_success=True,
        data=SimpleNamespace(
            batteries=[battery],
            inverter=SimpleNamespace(serial_number=_INVERTER_SERIAL),
        ),
    )
    entity = BatteryEntity.__new__(BatteryEntity)
    entity.coordinator = coordinator  # type: ignore[assignment]
    entity.config_entry = config_entry
    entity.battery_id = 0
    if hass is not None:
        entity.hass = hass
    return entity


async def test_battery_links_to_registered_inverter(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """The battery device is linked to the inverter, without deprecation warnings."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    inverter = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, _INVERTER_SERIAL)},
    )

    device_info = _battery_entity(hass, config_entry).device_info

    assert device_info["identifiers"] == {(DOMAIN, "BAT01")}
    if _HA_SUPPORTS_VIA_DEVICE_ID:
        assert device_info["via_device_id"] == inverter.id
        assert "via_device" not in device_info
    else:
        # Cores before 2026.8 have no via_device_id keyword; the tuple is kept.
        assert device_info["via_device"] == (DOMAIN, _INVERTER_SERIAL)  # type: ignore[typeddict-item]
        assert "via_device_id" not in device_info

    # Feed it through the registry the way entity_platform does.
    battery = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id, **device_info
    )
    assert battery.via_device_id == inverter.id
    if _HA_SUPPORTS_VIA_DEVICE_ID:
        assert "deprecated" not in caplog.text


async def test_battery_omits_link_when_inverter_unregistered(
    hass: HomeAssistant,
) -> None:
    """An unregistered inverter must not produce an invalid via_device_id."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")
    config_entry.add_to_hass(hass)

    device_info = _battery_entity(hass, config_entry).device_info

    assert "via_device_id" not in device_info
    assert device_info["identifiers"] == {(DOMAIN, "BAT01")}


def test_battery_device_info_before_added_to_hass() -> None:
    """device_info is safe to call before the entity has a hass reference."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test")

    device_info = _battery_entity(None, config_entry).device_info

    assert "via_device_id" not in device_info
    assert device_info["model"] == "Giv-Bat 5.2"
