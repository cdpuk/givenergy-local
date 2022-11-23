"""Home Assistant sensor descriptions."""
from __future__ import annotations

from givenergy_modbus.model.inverter import Model
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
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

from .const import DOMAIN, LOGGER, Icon
from .coordinator import GivEnergyUpdateCoordinator
from .entity import BatteryEntity, InverterEntity

_BASIC_INVERTER_SENSORS = [
    SensorEntityDescription(
        key="e_pv_total",
        name="PV Energy Total",
        icon=Icon.PV,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="p_pv1",
        name="PV Power (String 1)",
        icon=Icon.PV,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=POWER_WATT,
    ),
    SensorEntityDescription(
        key="p_pv2",
        name="PV Power (String 2)",
        icon=Icon.PV,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=POWER_WATT,
    ),
    SensorEntityDescription(
        key="e_grid_in_day",
        name="Grid Import Today",
        icon=Icon.GRID_IMPORT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="e_grid_out_day",
        name="Grid Export Today",
        icon=Icon.GRID_EXPORT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="e_inverter_out_day",
        name="Inverter Output Today",
        icon=Icon.INVERTER,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="e_inverter_out_total",
        name="Inverter Output Total",
        icon=Icon.INVERTER,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="e_battery_charge_day",
        name="Battery Charge Today",
        icon=Icon.BATTERY_PLUS,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="e_battery_discharge_day",
        name="Battery Discharge Today",
        icon=Icon.BATTERY_MINUS,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="e_battery_throughput_total",
        name="Battery Throughput Total",
        icon=Icon.BATTERY,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
    ),
    SensorEntityDescription(
        key="p_load_demand",
        name="Consumption Power",
        icon=Icon.AC,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=POWER_WATT,
    ),
    SensorEntityDescription(
        key="p_grid_out",
        name="Grid Export Power",
        icon=Icon.GRID_EXPORT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=POWER_WATT,
    ),
    SensorEntityDescription(
        key="p_battery",
        name="Battery Power",
        icon=Icon.BATTERY,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=POWER_WATT,
    ),
    SensorEntityDescription(
        key="p_eps_backup",
        name="Inverter EPS Backup Power",
        icon=Icon.EPS,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=POWER_WATT,
    ),
    SensorEntityDescription(
        key="battery_percent",
        name="Battery Percent",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="temp_battery",
        name="Battery Temperature",
        icon=Icon.BATTERY_TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    SensorEntityDescription(
        key="v_ac1",
        name="Grid Voltage",
        icon=Icon.AC,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
    ),
    SensorEntityDescription(
        key="f_ac1",
        name="Grid Frequency",
        icon=Icon.AC,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=FREQUENCY_HERTZ,
    ),
    SensorEntityDescription(
        key="temp_inverter_heatsink",
        name="Inverter Heatsink Temperature",
        icon=Icon.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    SensorEntityDescription(
        key="temp_charger",
        name="Inverter Charger Temperature",
        icon=Icon.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
]

_PV_ENERGY_TODAY_SENSOR = SensorEntityDescription(
    key="e_pv_day",
    name="PV Energy Today",
    icon=Icon.PV,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
)

_PV_POWER_SENSOR = SensorEntityDescription(
    key="p_pv",
    name="PV Power",
    icon=Icon.PV,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=POWER_WATT,
)

_CONSUMPTION_TODAY_SENSOR = SensorEntityDescription(
    key="e_consumption_today",
    name="Consumption Today",
    icon=Icon.AC,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
)

_CONSUMPTION_TOTAL_SENSOR = SensorEntityDescription(
    key="e_consumption_consumption",
    name="Consumption Total",
    icon=Icon.AC,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
)

_BATTERY_MODE_SENSOR = SensorEntityDescription(
    key="battery_mode_description",
    name="Battery Mode",
    icon=Icon.BATTERY,
)

_BATTERY_CHARGE_LIMIT_SENSOR = SensorEntityDescription(
    key="battery_charge_limit",
    name="Battery Charge Power Limit",
    icon=Icon.BATTERY_PLUS,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=POWER_WATT,
)

_BATTERY_DISCHARGE_LIMIT_SENSOR = SensorEntityDescription(
    key="battery_discharge_limit",
    name="Battery Discharge Power Limit",
    icon=Icon.BATTERY_MINUS,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=POWER_WATT,
)

_BASIC_BATTERY_SENSORS = [
    SensorEntityDescription(
        key="battery_soc",
        name="Battery Charge",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="battery_num_cycles",
        name="Battery Cycles",
        icon=Icon.BATTERY_CYCLES,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="v_battery_cells_sum",
        name="Battery Voltage",
        icon=Icon.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
    ),
]

_BATTERY_REMAINING_CAPACITY_SENSOR = SensorEntityDescription(
    key="battery_remaining_capacity",
    name="Battery Remaining Capacity",
    icon=Icon.BATTERY,
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: GivEnergyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Add basic inverter sensors that map directly to registers.
    async_add_entities(
        InverterBasicSensor(coordinator, config_entry, entity_description)
        for entity_description in _BASIC_INVERTER_SENSORS
    )

    # Add other inverter sensors that require more customization
    # (e.g. sensors that derive values from several registers).
    async_add_entities(
        [
            PVEnergyTodaySensor(
                coordinator, config_entry, entity_description=_PV_ENERGY_TODAY_SENSOR
            ),
            PVPowerSensor(
                coordinator, config_entry, entity_description=_PV_POWER_SENSOR
            ),
            ConsumptionTodaySensor(
                coordinator, config_entry, entity_description=_CONSUMPTION_TODAY_SENSOR
            ),
            ConsumptionTotalSensor(
                coordinator, config_entry, entity_description=_CONSUMPTION_TOTAL_SENSOR
            ),
            BatteryModeSensor(
                coordinator, config_entry, entity_description=_BATTERY_MODE_SENSOR
            ),
            BatteryChargeLimitSensor(
                coordinator,
                config_entry,
                entity_description=_BATTERY_CHARGE_LIMIT_SENSOR,
            ),
            BatteryDischargeLimitSensor(
                coordinator,
                config_entry,
                entity_description=_BATTERY_DISCHARGE_LIMIT_SENSOR,
            ),
        ]
    )

    # Add battery sensors
    for batt_num, batt in enumerate(coordinator.data.batteries):
        # Only add data for batteries if we can successfully read the serial number
        # Failure to read a S/N can result in null bytes
        if batt.battery_serial_number.replace("\x00", ""):
            async_add_entities(
                BatteryBasicSensor(
                    coordinator, config_entry, entity_description, batt_num
                )
                for entity_description in _BASIC_BATTERY_SENSORS
            )

            async_add_entities(
                [
                    BatteryRemainingCapacitySensor(
                        coordinator,
                        config_entry,
                        entity_description=_BATTERY_REMAINING_CAPACITY_SENSOR,
                        battery_id=batt_num,
                    )
                ]
            )
        else:
            LOGGER.warning("Ignoring battery %d due to missing serial number", batt_num)


class InverterBasicSensor(InverterEntity, SensorEntity):
    """A sensor that derives its value from the register values fetched from the inverter."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = (
            f"{self.data.inverter_serial_number}_{entity_description.key}"
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """Return the register value as referenced by the 'key' property of the associated entity description."""
        return self.data.dict().get(self.entity_description.key)


class PVEnergyTodaySensor(InverterBasicSensor):
    """Total PV Energy sensor."""

    @property
    def native_value(self) -> StateType:
        """Return the sum of energy generated across both PV strings."""
        return self.data.e_pv1_day + self.data.e_pv2_day


class PVPowerSensor(InverterBasicSensor):
    """Total PV Power sensor."""

    @property
    def native_value(self) -> StateType:
        """Return the sum of power generated across both PV strings."""
        return self.data.p_pv1 + self.data.p_pv2


class ConsumptionTodaySensor(InverterBasicSensor):
    """Consumption Today sensor."""

    @property
    def native_value(self) -> StateType:
        """Calculate consumption based on net inverter output plus net grid import."""

        consumption_today = (
            self.data.e_inverter_out_day
            - self.data.e_inverter_in_day
            + self.data.e_grid_in_day
            - self.data.e_grid_out_day
        )

        # For AC inverters, PV output doesn't count as part of the inverter output,
        # so we need to add it on.
        if self.data.inverter_model == Model.AC:
            consumption_today += self.data.e_pv1_day + self.data.e_pv2_day

        return consumption_today


class ConsumptionTotalSensor(InverterBasicSensor):
    """Consumption Total sensor."""

    @property
    def native_value(self) -> StateType:
        """Calculate consumption based on net inverter output plus net grid import."""
        consumption_total = (
            self.data.e_inverter_out_total
            - self.data.e_inverter_in_total
            + self.data.e_grid_in_total
            - self.data.e_grid_out_total
        )

        # For AC inverters, PV output doesn't count as part of the inverter output,
        # so we need to add it on.
        if self.data.inverter_model == Model.AC:
            consumption_total += self.data.e_pv_total

        return consumption_total


class BatteryModeSensor(InverterBasicSensor):
    """Battery mdoe sensor."""

    @property
    def native_value(self) -> StateType:
        """Determine the mode based on various settings."""

        # battery_power_mode:
        # 0: export/max
        # 1: demand/self-consumption
        battery_power_mode = self.data.battery_power_mode
        battery_soc_reserve = self.data.battery_soc_reserve
        enable_discharge = self.data.enable_discharge

        if battery_power_mode == 1 and battery_soc_reserve == 4:
            return "Eco"

        if enable_discharge is True and battery_soc_reserve == 100:
            if battery_power_mode == 1:
                return "Timed Discharge"
            else:
                return "Timed Export"
        return "Unknown"


class BatteryChargeLimitSensor(InverterBasicSensor):
    """Battery charge limit sensor."""

    @property
    def native_value(self) -> StateType:
        """Map the low-level value to power in Watts."""
        raw_value = self.data.battery_charge_limit

        # Warning: value for batteries with max charge/discharge rates of 2.6kW
        # Different logic almost certainly required on other units
        return 2600 if raw_value == 50 else raw_value * 64


class BatteryDischargeLimitSensor(InverterBasicSensor):
    """Battery discharge limit sensor."""

    @property
    def native_value(self) -> StateType:
        """Map the low-level value to power in Watts."""
        raw_value = self.data.battery_discharge_limit

        # Warning: value for batteries with max charge/discharge rates of 2.6kW
        # Different logic almost certainly required on other units
        return 2600 if raw_value == 50 else raw_value * 64


class BatteryBasicSensor(BatteryEntity, SensorEntity):
    """A battery sensor that derives its value from the register values fetched from the inverter."""

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        entity_description: SensorEntityDescription,
        battery_id: int,
    ) -> None:
        """Initialize a sensor based on an entity description."""
        super().__init__(coordinator, config_entry, battery_id)
        self._attr_unique_id = (
            f"{self.data.battery_serial_number}_{entity_description.key}"
        )
        self.entity_description = entity_description

    @property
    def native_value(self) -> StateType:
        """Return the register value as referenced by the 'key' property of the associated entity description."""
        return self.data.dict().get(self.entity_description.key)


class BatteryRemainingCapacitySensor(BatteryBasicSensor):
    """Battery remaining capacity sensor."""

    @property
    def native_value(self) -> StateType:
        """Map the low-level Ah value to energy in kWh."""
        battery_remaining_capacity = (
            self.data.battery_remaining_capacity * self.data.v_battery_cells_sum / 1000
        )
        # Raw value is in Ah (Amp Hour)
        # Convert to KWh using formula Ah * V / 1000
        return round(battery_remaining_capacity, 3)
