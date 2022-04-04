"""Constants for the GivEnergy integration."""

from logging import Logger, getLogger

DOMAIN = "givenergy_local"
LOGGER: Logger = getLogger(__package__)

CONF_HOST = "host"
CONF_NUM_BATTERIES = "num_batteries"

MANUFACTURER = "GivEnergy"
