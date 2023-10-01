"""Home Assistant entity descriptions."""
from custom_components.givenergy_local.givenergy_modbus.model.inverter import Model
from custom_components.givenergy_local.givenergy_modbus.model.plant import (
    Battery,
    Inverter,
    Plant,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import GivEnergyUpdateCoordinator

# Maps battery design capacities (as seen under 'battery_design_capacity_2') to model names.
# Keys should match the values seen in the datasheets.
_BATTERY_CAPACITY_TO_MODEL = {
    51: "Giv-Bat-ECO 2.6",
    102: "Giv-Bat 5.2",
    160: "Giv-Bat 8.2",
    186: "Giv-Bat 9.5",
}


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

        model: Model = self.data.model
        model_name = f"TODO_{model}"

        return DeviceInfo(
            identifiers={(DOMAIN, self.data.serial_number)},
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

    @property
    def inverter_model(self) -> Model:
        """Get the inverter model."""
        return self.data.model

    @property
    def inverter_max_battery_power(self) -> int:
        """Get the maximum battery charge/discharge power for this model."""
        if self.inverter_model == Model.EMS:  # TODO: Gen2?
            return 3600
        elif self.inverter_model == Model.AC:
            return 3000
        else:
            return 2600


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

        return DeviceInfo(
            identifiers={(DOMAIN, self.data.serial_number)},
            name="Battery",
            manufacturer=MANUFACTURER,
            model=self.battery_model,
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

    @property
    def battery_model(self) -> str:
        """
        Get a battery model name based on the value from 'battery_design_capacity_2'.

        Unrecognised values are described with a capacity in Ah to allow these to be easily added
        in a future release.
        """
        capacity = int(self.data.battery_design_capacity_2)
        model_name = _BATTERY_CAPACITY_TO_MODEL.get(capacity)

        if model_name is None:
            model_name = f"Unknown ({capacity}Ah)"

        return model_name
