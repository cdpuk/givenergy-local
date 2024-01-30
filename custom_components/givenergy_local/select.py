"""Select platform."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.givenergy_local.givenergy_modbus.client.commands import (
    set_battery_pause_mode,
)

from . import GivEnergyUpdateCoordinator
from .const import DOMAIN, Icon
from .entity import InverterEntity
from .givenergy_modbus.model.inverter import BatteryPauseMode

_BATTERY_PAUSE_MODE_OPTIONS = {
    BatteryPauseMode.DISABLED: "Not Paused",
    BatteryPauseMode.PAUSE_CHARGE: "Pause Charge",
    BatteryPauseMode.PAUSE_DISCHARGE: "Pause Discharge",
    BatteryPauseMode.PAUSE_BOTH: "Pause Charge & Discharge",
}


_BATTERY_PAUSE_MODE_DESCRIPTION = SelectEntityDescription(
    key="battery_pause_mode",
    options=list(_BATTERY_PAUSE_MODE_OPTIONS.values()),
    icon=Icon.BATTERY_PAUSE,
    name="Battery Pause Mode",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[SelectEntity] = []

    if coordinator.data.inverter.battery_pause_mode is not None:
        entities.append(
            BatteryPauseModeSelect(
                coordinator,
                config_entry,
                _BATTERY_PAUSE_MODE_DESCRIPTION,
            )
        )
    async_add_entities(entities)


class BatteryPauseModeSelect(InverterEntity, SelectEntity):
    """Bubbles selection for spa devices that support 3 levels."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        description: SelectEntityDescription,
    ) -> None:
        """Initialize thermostat."""
        super().__init__(coordinator, config_entry)
        self.entity_description = description
        self._attr_unique_id = f"{self.data.serial_number}_{description.key}"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        return _BATTERY_PAUSE_MODE_OPTIONS.get(self.data.battery_pause_mode)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        for val in BatteryPauseMode:
            if option == _BATTERY_PAUSE_MODE_OPTIONS[val]:
                await self.coordinator.execute(set_battery_pause_mode(val))
