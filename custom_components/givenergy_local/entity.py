"""Home Assistant entity descriptions."""
from givenergy_modbus.model.plant import Battery, Inverter, Plant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import GivEnergyUpdateCoordinator


class InverterEntity(CoordinatorEntity[GivEnergyUpdateCoordinator]):
    """An entity that derives data from a GivEnergy inverter."""

    def __init__(
        self, coordinator: GivEnergyUpdateCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Inverter device information for the entity."""

        model_name = self.data.inverter_model
        if model_name is None:
            model_name = "Unknown"

        return DeviceInfo(
            identifiers={(DOMAIN, self.data.inverter_serial_number)},
            name="Solar Inverter",
            model=model_name,
            manufacturer=MANUFACTURER,
            sw_version=self.data.firmware_version,
            configuration_url="https://givenergy.cloud",
        )

    @property
    def data(self) -> Inverter:
        """Get inverter data for the entity."""
        return self.coordinator.data.inverter

    @property
    def available(self) -> bool:
        """Return True if the inverter is online."""
        return self.coordinator.last_update_success  # type: ignore[no-any-return]


class BatteryEntity(CoordinatorEntity[Plant]):
    """An entity associated with a battery device connected to the inverter."""

    battery_id: int

    def __init__(
        self,
        coordinator: GivEnergyUpdateCoordinator,
        config_entry: ConfigEntry,
        battery_id: int,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.battery_id = battery_id

    @property
    def device_info(self) -> DeviceInfo:
        """Battery device information for the entity."""

        battery_cap = str(self.data.battery_design_capacity)

        return DeviceInfo(
            identifiers={(DOMAIN, self.data.battery_serial_number)},
            name="Battery",
            manufacturer=MANUFACTURER,
            model=self._get_battery_model_from_capacity(battery_cap),
            sw_version=str(self.data.bms_firmware_version),
            configuration_url="https://givenergy.cloud",
            via_device=(DOMAIN, self.coordinator.data.inverter.inverter_serial_number),
        )

    @property
    def data(self) -> Battery:
        """Get battery data for the entity."""
        return self.coordinator.data.batteries[self.battery_id]

    @property
    def available(self) -> bool:
        """Return True if the inverter is online."""
        return self.coordinator.last_update_success  # type: ignore[no-any-return]

    @staticmethod
    def _get_battery_model_from_capacity(capacity):
        base_model_name = "GivBat"
        if capacity is None:
            return base_model_name

        capacity_parts = capacity.split(".", 1)

        if len(capacity_parts) > 0:
            if capacity_parts[0] == "158":
                return f"{base_model_name} 8.2"
            if capacity_parts[0] == "99":
                return f"{base_model_name} 5.2"
        return base_model_name
