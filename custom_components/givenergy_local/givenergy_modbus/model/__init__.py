"""Data model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import IntEnum
from typing import TYPE_CHECKING

try:
    from pydantic.v1 import BaseModel
except ImportError:
    from pydantic import BaseModel

if TYPE_CHECKING:
    from custom_components.givenergy_local.givenergy_modbus.model.register_cache import (
        RegisterCache,
    )


class GivEnergyBaseModel(BaseModel):
    """Structured format for all other attributes."""

    class Config:  # noqa: D106
        allow_mutation = False
        frozen = True
        use_enum_values = True
        orm_mode = True

    @classmethod
    def from_registers(cls, register_cache: RegisterCache):
        """Constructor parsing registers directly."""
        raise NotImplementedError()


class DefaultUnknownIntEnum(IntEnum):
    """Enum that returns unknown instead of blowing up."""

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


@dataclass
class TimeSlot:
    """Dataclass to represent a time slot, with a start and end time."""

    start: time
    end: time

    @classmethod
    def from_components(
        cls, start_hour: int, start_minute: int, end_hour: int, end_minute: int
    ):
        """Shorthand for the individual datetime.time constructors."""
        return cls(time(start_hour, start_minute), time(end_hour, end_minute))

    @classmethod
    def from_repr(cls, start: int | str, end: int | str) -> TimeSlot:
        """Converts from human-readable/ASCII representation: '0034' -> 00:34."""
        if isinstance(start, int):
            start = f"{start:04d}"
        start_hour = int(start[:-2])
        start_minute = int(start[-2:])
        if isinstance(end, int):
            end = f"{end:04d}"
        end_hour = int(end[:-2])
        end_minute = int(end[-2:])
        return cls(time(start_hour, start_minute), time(end_hour, end_minute))


# from custom_components.givenergy_local.givenergy_modbus.model import battery, inverter, plant, register_cache
#
# Plant = plant.Plant
# Inverter = inverter.Inverter
# Battery = battery.Battery
# RegisterCache = register_cache.RegisterCache
