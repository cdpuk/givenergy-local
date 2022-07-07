"""Home Assistant sensor descriptions."""
from __future__ import annotations

from enum import Enum

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_FREQUENCY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    ELECTRIC_POTENTIAL_VOLT,
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ,
    PERCENTAGE,
    POWER_WATT,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import GivEnergyUpdateCoordinator
from .const import DOMAIN, LOGGER
from .entity import BatteryEntity, InverterEntity


class Icon(str, Enum):
    """Icon styles."""

    PV = "mdi:solar-power"
    AC = "mdi:power-plug-outline"
    Battery = "mdi:battery-high"
    BatteryMinus = "mdi:battery-minus"
    BatteryPlus = "mdi:battery-plus"
    Inverter = "mdi:flash"
    GridImport = "mdi:transmission-tower-export"
    GridExport = "mdi:transmission-tower-import"
    Temperature = "mdi:thermometer"


_BATTERY_CHARGE_LIMIT_SENSOR = NumberEntityDescription(
    key="battery_charge_limit",
    name="Battery Charge Power Limit",
    icon=Icon.BatteryPlus,
    device_class=DEVICE_CLASS_POWER,
    unit_of_measurement=POWER_WATT,
    min_value=0,
    max_value=2600,
)

_BATTERY_DISCHARGE_LIMIT_SENSOR = NumberEntityDescription(
    key="battery_discharge_limit",
    name="Battery Discharge Power Limit",
    icon=Icon.BatteryMinus,
    device_class=DEVICE_CLASS_POWER,
    unit_of_measurement=POWER_WATT,
    min_value=0,
    max_value=2600,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add entities for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            GivEnergyPowerRateNumber(
                coordinator,
                config_entry,
                entity_description=_BATTERY_CHARGE_LIMIT_SENSOR,
            ),
            GivEnergyPowerRateNumber(
                coordinator,
                config_entry,
                entity_description=_BATTERY_DISCHARGE_LIMIT_SENSOR,
            ),
        ]
    )


class GivEnergyPowerRateNumber(InverterEntity, NumberEntity):
    """Base class for charge & discharge limits."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{self.coordinator.data.inverter.inverter_serial_number}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def value(self) -> StateType:
        """Return the register value as referenced by the 'key' property of the associated entity description."""
        raw_value = self.coordinator.data.inverter.dict().get(
            self.entity_description.key
        )

        # Warning: value for batteries with max charge/discharge rates of 2.6kW
        # Different logic almost certainly required on other units
        # 0 -> 0
        # n -> n * 64
        # 39 -> n * 64 = 2496
        # 40 -> 2600
        # 41-49 never observed
        # 50 -> 2600
        return 2600 if raw_value > 39 else raw_value * 64

    def set_value(self, value: float) -> None:
        """TODO"""
        connection = self.coordinator.connection
        modbus_value = 50 if value >= (40 * 64) else int(value / 64)

        LOGGER.debug("Setting battery charge limit to %d (%dW)", modbus_value, value)
        connection.client.set_battery_charge_limit(modbus_value)
