"""Home Assistant entity descriptions."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from givenergy_modbus.model.battery import Battery
from givenergy_modbus.model.inverter import Model, SinglePhaseInverter, resolve_model
from givenergy_modbus.model.inverter_threephase import ThreePhaseInverter

from .const import DOMAIN, MANUFACTURER
from .coordinator import GivEnergyUpdateCoordinator

# Maps battery design capacities (as seen under 'cap_design2') to model names.
# Keys should match the values seen in the datasheets.
_BATTERY_CAPACITY_TO_MODEL = {
    51: "Giv-Bat-ECO 2.6",
    102: "Giv-Bat 5.2",
    106: "Giv-Bat 5.12",
    160: "Giv-Bat 8.2",
    186: "Giv-Bat 9.5",
}

# Maps models to human readable descriptions
_MODEL_DESCRIPTIONS = {
    Model.HYBRID: "Hybrid",
    Model.AC: "AC",
    Model.HYBRID_3PH: "Hybrid (3-phase)",
    Model.AC_3PH: "AC (3-phase)",
    Model.EMS: "EMS",
    Model.GATEWAY: "Gateway",
    Model.ALL_IN_ONE: "All In One",
    Model.HYBRID_GEN1: "Hybrid Gen1",
    Model.HYBRID_GEN2: "Hybrid Gen2",
    Model.HYBRID_GEN3: "Hybrid Gen3",
    Model.POLAR: "Polar",
    Model.AIO_COMMERCIAL: "All In One Commercial",
    Model.EMS_COMMERCIAL: "EMS Commercial",
    Model.HYBRID_HV_GEN3: "Hybrid HV Gen3",
    Model.ALL_IN_ONE_HYBRID: "All In One Hybrid",
    Model.HYBRID_GEN4: "Hybrid Gen4",
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

        dtc = self.data.device_type_code
        arm_fw = self.data.arm_firmware_version
        # Resolve the specific model variant (e.g. HYBRID_GEN2) when possible;
        # fall back to the coarse model if detection hasn't completed yet.
        model = (
            resolve_model(int(dtc, 16), int(arm_fw))
            if dtc is not None and arm_fw is not None
            else self.data.model
        )
        model_name = _MODEL_DESCRIPTIONS.get(
            model, model.name.replace("_", " ").title()
        )
        power_description = ""
        if max_power := self.data.inverter_max_power:
            power_description = f"{max_power / 1000}kW"
        model_description = f"{model_name} {power_description}".rstrip()

        return DeviceInfo(
            identifiers={(DOMAIN, self.data.serial_number)},
            name="Solar Inverter",
            model=model_description,
            manufacturer=MANUFACTURER,
            serial_number=self.data.serial_number,
            sw_version=self.data.firmware_version,
            configuration_url="https://givenergy.cloud",
        )

    @property
    def data(self) -> SinglePhaseInverter | ThreePhaseInverter:
        """Get inverter data for the entity."""
        return self.coordinator.data.inverter

    @property
    def available(self) -> bool:
        """Return True if the inverter is online."""
        return self.coordinator.last_update_success

    @property
    def inverter_max_battery_power(self) -> int:
        """Get the maximum battery charge/discharge power for this model."""
        battery_max_power: int | None = self.data.battery_max_power
        if battery_max_power is not None:
            return battery_max_power

        # Fallback to a safe value (lowest possible rating of all models)
        return 2600


class BatteryEntity(CoordinatorEntity[GivEnergyUpdateCoordinator]):
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
            serial_number=self.data.serial_number,
            sw_version=str(self.data.bms_firmware_version),
            configuration_url="https://givenergy.cloud",
            via_device=(DOMAIN, self.coordinator.data.inverter.serial_number),
        )

    @property
    def data(self) -> Battery:
        """Get battery data for the entity."""
        # TODO watch for disappearing batteries
        return self.coordinator.data.batteries[self.battery_id]

    @property
    def available(self) -> bool:
        """Return True if the inverter is online."""
        return self.coordinator.last_update_success

    @property
    def battery_model(self) -> str:
        """
        Get a battery model name based on the value from 'cap_design2'.

        Unrecognised values are described with a capacity in Ah to allow these to be easily added
        in a future release.
        """
        capacity = int(self.data.cap_design2)
        model_name = _BATTERY_CAPACITY_TO_MODEL.get(capacity)

        if model_name is None:
            model_name = f"Unknown ({capacity}Ah)"

        return model_name
