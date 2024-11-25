"""Switch sensor platform."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, Icon
from .coordinator import GivEnergyUpdateCoordinator
from .entity import InverterEntity
from .givenergy_modbus.client.commands import CommandBuilder


@dataclass(frozen=True)
class MappedSwitchRequiredKeys:
    """Mixin for required keys."""

    set_fn: Callable[[GivEnergyUpdateCoordinator, bool], Awaitable[None]]


@dataclass(frozen=True)
class MappedSwitchEntityDescription(SwitchEntityDescription, MappedSwitchRequiredKeys):
    """Sensor description providing a lookup key to obtain the value."""


_GENERIC_ENTITIES = [
    MappedSwitchEntityDescription(
        key="enable_charge",
        name="Battery AC Charging",
        icon=Icon.BATTERY_PLUS,
        set_fn=lambda c, v: c.execute(CommandBuilder.set_enable_charge(v)),
    ),
    MappedSwitchEntityDescription(
        key="enable_charge_target",
        name="Battery AC Charge Limit",
        icon=Icon.BATTERY_PLUS,
        set_fn=lambda c, v: c.execute(CommandBuilder.set_enable_charge_target(v)),
    ),
    MappedSwitchEntityDescription(
        key="enable_discharge",
        name="Battery DC Discharging",
        icon=Icon.BATTERY_MINUS,
        set_fn=lambda c, v: c.execute(CommandBuilder.set_enable_discharge(v)),
    ),
    MappedSwitchEntityDescription(
        key="battery_power_mode",
        name="Battery Eco Mode",
        icon=Icon.BATTERY,
        set_fn=lambda c, v: c.execute(
            CommandBuilder.set_discharge_mode_to_match_demand()
            if v
            else CommandBuilder.set_discharge_mode_max_power()
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add switches for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        InverterSwitch(coordinator, config_entry, entity_description)
        for entity_description in _GENERIC_ENTITIES
    ]
    async_add_entities(entities)


class InverterSwitch(InverterEntity, SwitchEntity):
    """A sensor that derives its value from the register values fetched from the inverter."""

    entity_description: MappedSwitchEntityDescription

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: MappedSwitchEntityDescription,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self.data.serial_number}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool | None:
        """Return the register value as referenced by the 'key' property of the associated entity description."""
        if (val := self.data.dict().get(self.entity_description.key)) is not None:
            return val  # type: ignore[no-any-return]
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.entity_description.set_fn(self.coordinator, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.entity_description.set_fn(self.coordinator, False)
