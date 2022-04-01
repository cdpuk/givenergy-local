"""Home Assistant entity descriptions."""
from givenergy_modbus.model.plant import Plant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GivEnergyUpdateCoordinator
from .const import DOMAIN, MANUFACTURER


class GivEnergyEntity(CoordinatorEntity[Plant]):
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

        model_name = self.coordinator.data.inverter.inverter_model
        if model_name is None:
            model_name = "Unknown"

        return DeviceInfo(
            identifiers={
                (DOMAIN, self.coordinator.data.inverter.inverter_serial_number)
            },
            name="Solar Inverter",
            model=model_name,
            manufacturer=MANUFACTURER,
            sw_version=self.coordinator.data.inverter.firmware_version,
            configuration_url="https://www.givenergy.cloud",
        )

    @property
    def available(self) -> bool:
        """Return True if the inverter is online."""
        return self.coordinator.last_update_success  # type: ignore[no-any-return]
