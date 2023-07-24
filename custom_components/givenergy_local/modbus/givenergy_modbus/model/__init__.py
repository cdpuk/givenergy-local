"""Data model."""
from pydantic import BaseModel

from givenergy_modbus.model.register_getter import RegisterGetter


class GivEnergyBaseModel(BaseModel):
    """Structured format for all other attributes."""

    class Config:  # noqa: D106
        orm_mode = True
        getter_dict = RegisterGetter
        allow_mutation = False


# from givenergy_modbus.model import battery, inverter, plant, register_cache
#
# Plant = plant.Plant
# Inverter = inverter.Inverter
# Battery = battery.Battery
# RegisterCache = register_cache.RegisterCache
