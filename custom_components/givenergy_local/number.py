"""Home Assistant number entity descriptions."""
from __future__ import annotations

from givenergy_modbus.client.commands import (
    RegisterMap,
    set_battery_charge_limit,
    set_battery_discharge_limit,
    set_battery_power_reserve,
    set_battery_soc_reserve,
)
from givenergy_modbus.pdu.write_registers import WriteHoldingRegisterRequest
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    BATTERY_NOMINAL_VOLTAGE,
    COMMAND_RETRIES,
    COMMAND_TIMEOUT,
    DOMAIN,
    Icon,
)
from .coordinator import GivEnergyUpdateCoordinator
from .entity import InverterEntity


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
            BatterySoCReserveNumber(coordinator, config_entry),
            BatteryMinPowerReserveNumber(coordinator, config_entry),
            InverterBatteryChargeLimitNumber(coordinator, config_entry),
            InverterBatteryDischargeLimitNumber(coordinator, config_entry),
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
        self._attr_unique_id = f"{self.data.serial_number}_{entity_description.key}"
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
        target_soc = int(value)
        if not 4 <= target_soc <= 100:
            raise ValueError(f"Charge Target SOC ({target_soc}) must be in [4-100]%")

        await self.coordinator.client.execute(
            [WriteHoldingRegisterRequest(RegisterMap.CHARGE_TARGET_SOC, target_soc)]
        )
        await self.coordinator.async_request_refresh()


class BatterySoCReserveNumber(InverterBasicNumber):
    """Number to represent and control the Battery SOC Reserve.

    This is believed to only affect systems with EPS enabled.
    """

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Battery SOC Reserve number."""
        super().__init__(
            coordinator,
            config_entry,
            NumberEntityDescription(
                key="battery_soc_reserve",
                name="Battery SOC Reserve",
                icon=Icon.BATTERY_MINUS,
                native_unit_of_measurement=PERCENTAGE,
            ),
        )

        # Values correspond to SOC percentage
        self._attr_native_min_value = 4
        self._attr_native_max_value = 100

        # A 5% step size makes the slider a bit nicer to use
        self._attr_native_step = 5

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.client.execute(
            set_battery_soc_reserve(int(value)), COMMAND_TIMEOUT, COMMAND_RETRIES
        )
        await self.coordinator.async_request_refresh()


class BatteryMinPowerReserveNumber(InverterBasicNumber):
    """Number to represent and control the Battery Minimum Reserve level."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Battery Minimum Reserve number."""
        super().__init__(
            coordinator,
            config_entry,
            NumberEntityDescription(
                key="battery_discharge_min_power_reserve",
                name="Battery Cutoff Limit",
                icon=Icon.BATTERY_MINUS,
                native_unit_of_measurement=PERCENTAGE,
            ),
        )

        # Values correspond to SOC percentage
        self._attr_native_min_value = 4
        self._attr_native_max_value = 100

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.client.execute(
            set_battery_power_reserve(int(value)), COMMAND_TIMEOUT, COMMAND_RETRIES
        )
        await self.coordinator.async_request_refresh()


class InverterBatteryPowerLimitNumber(InverterBasicNumber):
    """Number to represent a battery charge/discharge rate."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the power limit number."""
        super().__init__(coordinator, config_entry, entity_description)

        # We need to calculate the maximum possible value based on inverter and battery
        # capabilities. We know packs are limited to 0.5C charge/discharge, so:
        battery_max_power = int(
            self.data.battery_capacity * BATTERY_NOMINAL_VOLTAGE * 0.5
        )

        # Work out the maximum possible power
        self._attr_native_max_value = min(
            battery_max_power, self.inverter_max_battery_power
        )

        # To add confusion to the matter, the raw values used by the API need to be determined
        # from the battery capacity
        self.battery_power_step = (
            self.data.battery_capacity * BATTERY_NOMINAL_VOLTAGE / 100
        )

    @property
    def native_value(self) -> StateType:
        """Get the current value in Watts."""
        raw_value = self.data.dict().get(self.entity_description.key)
        power_watts = int(raw_value * self.battery_power_step)
        return min(power_watts, self.inverter_max_battery_power)

    def watts_to_api_value(self, watts: int) -> int:
        """
        Convert a battery power limit (in Watts) to a value used by the inverter API.

        There is added complexity here because the API values depend on the battery &
        inverter capabilities.
        """
        target_value = watts / self.battery_power_step
        max_step = int(self.inverter_max_battery_power / self.battery_power_step)

        # The API always jumps to 50 to represent the maximum possible value
        return 50 if target_value > max_step else int(target_value)


class InverterBatteryChargeLimitNumber(InverterBatteryPowerLimitNumber):
    """Number to represent a battery charge power limit in Watts."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise the charge power limit number."""
        super().__init__(
            coordinator,
            config_entry,
            NumberEntityDescription(
                key="battery_charge_limit",
                name="Battery Charge Power Limit",
                icon=Icon.BATTERY_PLUS,
                device_class=NumberDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
            ),
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current charge power limit."""
        raw_value = self.watts_to_api_value(int(value))
        await self.coordinator.client.execute(
            set_battery_charge_limit(raw_value), COMMAND_TIMEOUT, COMMAND_RETRIES
        )
        await self.coordinator.async_request_refresh()


class InverterBatteryDischargeLimitNumber(InverterBatteryPowerLimitNumber):
    """Number to represent a battery discharge power limit in Watts."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialise the discharge power limit number."""
        super().__init__(
            coordinator,
            config_entry,
            NumberEntityDescription(
                key="battery_discharge_limit",
                name="Battery Discharge Power Limit",
                icon=Icon.BATTERY_PLUS,
                device_class=NumberDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
            ),
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current discharge power limit."""
        raw_value = self.watts_to_api_value(int(value))
        await self.coordinator.client.execute(
            set_battery_discharge_limit(raw_value), COMMAND_TIMEOUT, COMMAND_RETRIES
        )
        await self.coordinator.async_request_refresh()
