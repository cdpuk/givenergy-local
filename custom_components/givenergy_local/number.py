"""Home Assistant number entity descriptions."""
from __future__ import annotations

from givenergy_modbus.client import GivEnergyClient
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, Icon
from .coordinator import GivEnergyUpdateCoordinator
from .entity import InverterEntity
from .givenergy_ext import async_reliable_call


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            ACChargeLimitNumber(coordinator, config_entry),
        ]
    )


class InverterBasicNumber(InverterEntity, NumberEntity):
    """A number that derives its value from the register values fetched from the inverter."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{self.data.inverter_serial_number}_{entity_description.key}"
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """
        Get the current value.

        This returns the register value as referenced by the 'key' property of
        the associated entity description.
        """
        return self.data.dict().get(self.entity_description.key)


class ACChargeLimitNumber(InverterBasicNumber):
    """Number to represent and control the AC Charge SOC Limit."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the AC Charge Limit number."""
        super().__init__(
            coordinator,
            config_entry,
            NumberEntityDescription(
                key="charge_target_soc",
                name="Battery AC Charge Limit",
                icon=Icon.BATTERY_PLUS,
                native_unit_of_measurement=PERCENTAGE,
            ),
        )

        # Values correspond to SOC percentage
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100

        # A 5% step size makes the slider a bit nicer to use
        self._attr_native_step = 5

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""

        def enable_charge_target(client: GivEnergyClient) -> None:
            client.enable_charge_target(int(value))

        await async_reliable_call(
            self.hass,
            self.coordinator,
            enable_charge_target,
        )
