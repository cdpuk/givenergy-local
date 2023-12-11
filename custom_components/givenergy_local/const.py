"""Constants for the GivEnergy integration."""

from enum import Enum
from logging import Logger, getLogger

DOMAIN = "givenergy_local"
LOGGER: Logger = getLogger(__package__)

CONF_HOST = "host"
CONF_NUM_BATTERIES = "num_batteries"

MANUFACTURER = "GivEnergy"

# The nominal voltage of all LiFePO4 packs
BATTERY_NOMINAL_VOLTAGE = 51.2

COMMAND_TIMEOUT = 3.0
COMMAND_RETRIES = 3


class Icon(str, Enum):
    """Icon styles."""

    PV = "mdi:solar-power"
    AC = "mdi:power-plug-outline"
    BATTERY = "mdi:battery-high"
    BATTERY_CYCLES = "mdi:battery-sync"
    BATTERY_TEMPERATURE = "mdi:thermometer"
    BATTERY_MINUS = "mdi:battery-minus"
    BATTERY_PLUS = "mdi:battery-plus"
    INVERTER = "mdi:flash"
    GRID_IMPORT = "mdi:transmission-tower-export"
    GRID_EXPORT = "mdi:transmission-tower-import"
    EPS = "mdi:transmission-tower-off"
    TEMPERATURE = "mdi:thermometer"
