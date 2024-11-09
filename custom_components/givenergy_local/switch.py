"""Switch sensor platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, Icon
from .coordinator import GivEnergyUpdateCoordinator
from .entity import InverterEntity
from .givenergy_modbus.client.commands import CommandBuilder


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add switches for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            InverterChargeSwitch(coordinator, config_entry),
            InverterDischargeSwitch(coordinator, config_entry),
            InverterEcoModeSwitch(coordinator, config_entry),
        ]
    )


class InverterChargeSwitch(InverterEntity, SwitchEntity):
    """Controls AC charging."""

    entity_description = SwitchEntityDescription(
        key="enable_charge",
        icon=Icon.BATTERY_PLUS,
        name="Battery AC Charging",
    )

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{self.data.serial_number}_{self.entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.data.enable_charge  # type: ignore[no-any-return]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable AC charging, subject to charge slot configuration."""
        await self.coordinator.execute(CommandBuilder.set_enable_charge(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable AC charging, subject to charge slot configuration."""
        await self.coordinator.execute(CommandBuilder.set_enable_charge(False))


class InverterDischargeSwitch(InverterEntity, SwitchEntity):
    """Controls scheduled discharge modes."""

    entity_description = SwitchEntityDescription(
        key="enable_discharge",
        icon=Icon.BATTERY_MINUS,
        name="Battery DC Discharging",
    )

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{self.data.serial_number}_{self.entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.data.enable_discharge  # type: ignore[no-any-return]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable DC charging, subject to mode and discharge slot configuration."""
        await self.coordinator.execute(CommandBuilder.set_enable_discharge(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable DC discharging, subject to mode and discharge slot configuration."""
        await self.coordinator.execute(CommandBuilder.set_enable_discharge(False))


class InverterEcoModeSwitch(InverterEntity, SwitchEntity):
    """Controls Eco/Dynamic mode."""

    entity_description = SwitchEntityDescription(
        key="battery_power_mode",
        icon=Icon.BATTERY,
        name="Battery Eco Mode",
    )

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{self.data.serial_number}_{self.entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.data.battery_power_mode  # type: ignore[no-any-return]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable Eco/Dynamic mode."""
        await self.coordinator.execute(
            CommandBuilder.set_discharge_mode_to_match_demand()
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable Eco/Dynamic mode."""
        await self.coordinator.execute(CommandBuilder.set_discharge_mode_max_power())
