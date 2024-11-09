"""Home Assistant sensor descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from typing import Awaitable, Callable

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, Icon
from .coordinator import GivEnergyUpdateCoordinator
from .entity import InverterEntity
from .givenergy_modbus.client.commands import CommandBuilder
from .givenergy_modbus.model import TimeSlot


@dataclass(frozen=True)
class MappedTimeRequiredKeys:
    """Mixin for required keys."""

    ge_modbus_key: str
    get_fn: Callable[[TimeSlot], time]
    set_fn: Callable[[GivEnergyUpdateCoordinator, time], Awaitable[None]]


@dataclass(frozen=True)
class MappedTimeEntityDescription(TimeEntityDescription, MappedTimeRequiredKeys):
    """Sensor description providing a lookup key to obtain the value."""


_GENERIC_ENTITIES: list[MappedTimeEntityDescription] = []

_BATTERY_PAUSE_ENTITIES = [
    MappedTimeEntityDescription(
        key="battery_pause_slot_1_start",
        name="Battery Pause Start",
        icon=Icon.BATTERY_PAUSE,
        ge_modbus_key="battery_pause_slot_1",
        get_fn=lambda t: t.start,
        set_fn=lambda c, t: c.execute(CommandBuilder.set_pause_slot_start(t)),
    ),
    MappedTimeEntityDescription(
        key="battery_pause_slot_1_end",
        name="Battery Pause End",
        icon=Icon.BATTERY_PAUSE,
        ge_modbus_key="battery_pause_slot_1",
        get_fn=lambda t: t.end,
        set_fn=lambda c, t: c.execute(CommandBuilder.set_pause_slot_end(t)),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    entities.extend(
        [
            InverterTimeslotSensor(coordinator, config_entry, entity_description)
            for entity_description in _GENERIC_ENTITIES
        ]
    )

    if coordinator.data.inverter.battery_pause_mode is not None:
        entities.extend(
            [
                InverterTimeslotSensor(coordinator, config_entry, entity_description)
                for entity_description in _BATTERY_PAUSE_ENTITIES
            ]
        )

    async_add_entities(entities)


class InverterTimeslotSensor(InverterEntity, TimeEntity):
    """A sensor that derives its value from the register values fetched from the inverter."""

    entity_description: MappedTimeEntityDescription

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: MappedTimeEntityDescription,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self.data.serial_number}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> time | None:
        """Return the register value as referenced by the 'key' property of the associated entity description."""
        if slot := self.data.dict().get(self.entity_description.ge_modbus_key):
            return self.entity_description.get_fn(slot)
        return None

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""
        self.entity_description.set_fn(self.coordinator, value)
