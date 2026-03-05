"""Constants for the GivEnergy integration."""

from enum import StrEnum
from logging import Logger, getLogger

DOMAIN = "givenergy_local"
LOGGER: Logger = getLogger(__package__)

CONF_HOST = "host"

MANUFACTURER = "GivEnergy"

# The nominal voltage of all LiFePO4 packs
BATTERY_NOMINAL_VOLTAGE = 51.2


class Icon(StrEnum):
    """Icon styles."""

    PV = "mdi:solar-power"
    AC = "mdi:power-plug-outline"
    DC = "mdi:current-dc"
    BATTERY = "mdi:battery-high"
    BATTERY_CHARGING = "mdi:battery-charging"
    BATTERY_CYCLES = "mdi:battery-sync"
    BATTERY_TEMPERATURE = "mdi:thermometer"
    BATTERY_MINUS = "mdi:battery-minus"
    BATTERY_PLUS = "mdi:battery-plus"
    BATTERY_PAUSE = "mdi:battery-clock"
    INVERTER = "mdi:flash"
    GRID_IMPORT = "mdi:transmission-tower-export"
    GRID_EXPORT = "mdi:transmission-tower-import"
    EPS = "mdi:transmission-tower-off"
    TEMPERATURE = "mdi:thermometer"
