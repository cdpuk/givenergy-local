"""Binary sensor platform."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from typing import Any, Mapping

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt

from .const import DOMAIN, LOGGER, Icon
from .coordinator import GivEnergyUpdateCoordinator
from .entity import InverterEntity
from .givenergy_modbus.model import TimeSlot

_CHARGE_SLOT_BINARY_SENSORS = [
    BinarySensorEntityDescription(
        key="charge_slot_1",
        icon=Icon.BATTERY_PLUS,
        name="Battery Charge Slot 1",
    ),
    BinarySensorEntityDescription(
        key="charge_slot_2",
        icon=Icon.BATTERY_PLUS,
        name="Battery Charge Slot 2",
    ),
    BinarySensorEntityDescription(
        key="discharge_slot_1",
        icon=Icon.BATTERY_MINUS,
        name="Battery Discharge Slot 1",
    ),
    BinarySensorEntityDescription(
        key="discharge_slot_2",
        icon=Icon.BATTERY_MINUS,
        name="Battery Discharge Slot 2",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Add inverter sensors for charge/discharge slots.
    async_add_entities(
        InverterChargeSlotBinarySensor(coordinator, config_entry, entity_description)
        for entity_description in _CHARGE_SLOT_BINARY_SENSORS
    )


class InverterChargeSlotBinarySensor(InverterEntity, BinarySensorEntity):
    """A binary sensor that reports whether a charge/discharge slot is currently active."""

    entity_description: BinarySensorEntityDescription
    _cancel_scheduled_update: CALLBACK_TYPE | None = None

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self.data.serial_number}_{entity_description.key}"
        self.entity_description = entity_description

    async def async_added_to_hass(self) -> None:
        """Entity has been added to HA."""
        await super().async_added_to_hass()
        self._schedule_next_update()

    async def async_will_remove_from_hass(self) -> None:
        """Entity has been removed from HA."""
        await super().async_will_remove_from_hass()
        if self._cancel_scheduled_update is not None:
            self._cancel_scheduled_update()

    async def _async_scheduled_update(self, now: datetime) -> None:
        """
        Respond to a scheduled update.

        We've been woken up by a timer because we've just passed over the start
        or end time for the slot. Ask HA to reassess the entity state and schedule
        another update.
        """
        self.async_schedule_update_ha_state()
        self._schedule_next_update()

    def _schedule_next_update(self) -> None:
        """
        Schedule a future update to the entity state, if required.

        Work out when we next need to update the state due to the current time
        passing over the start of end time of the slot.
        """
        if (slot := self.slot) is None:
            return

        now = dt.now()

        # Get slot details
        current_time = now.time()
        start = slot.start
        end = slot.end

        # We don't need to be notified about entering/leaving an undefined slot
        if start == end:
            return

        # Work out the next time at which we need to check again
        if current_time < start:
            next_change = datetime.combine(now.date(), start)
        elif current_time < end:
            next_change = datetime.combine(now.date(), end)
        else:
            next_change = datetime.combine(now.date() + timedelta(days=1), start)

        # Schedule the next update
        self._cancel_scheduled_update = async_track_point_in_time(
            self.hass,
            self._async_scheduled_update,
            next_change,
        )
        LOGGER.debug(
            "Scheduled next update for %s at %s",
            self.entity_description.key,
            next_change,
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._cancel_scheduled_update is not None:
            self._cancel_scheduled_update()

        self._schedule_next_update()
        self.async_write_ha_state()

    @property
    def slot(self) -> TimeSlot | None:
        """Get the slot definition."""
        slot: TimeSlot = self.data.dict().get(self.entity_description.key)
        return slot

    @property
    def is_on(self) -> bool | None:
        """Determine whether we're currently within the slot."""
        if slot := self.slot:
            now: time = dt.now().time()
            is_on: bool = slot.start <= now < self.slot.end
            return is_on
        return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Attach charge slot configuration."""
        if slot := self.slot:
            return {
                "start": slot.start.strftime("%H:%M"),
                "end": slot.end.strftime("%H:%M"),
            }
        return None
