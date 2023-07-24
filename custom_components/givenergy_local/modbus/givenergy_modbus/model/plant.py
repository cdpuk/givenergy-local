from typing import List

from pydantic import BaseModel

from givenergy_modbus.model.battery import Battery
from givenergy_modbus.model.inverter import Inverter  # type: ignore  # shut up mypy
from givenergy_modbus.model.register_cache import RegisterCache


class Plant(BaseModel):
    """Representation of a complete GivEnergy plant."""

    inverter_rc: RegisterCache
    batteries_rcs: List[RegisterCache]

    class Config:  # noqa: D106
        arbitrary_types_allowed = True
        orm_mode = True
        # allow_mutation = False

    def __init__(self, **data):
        """Constructor. Use `number_batteries` to specify the total number of batteries installed."""
        data['inverter_rc'] = data.get('inverter_rc', RegisterCache())
        data['batteries_rcs'] = data.get(
            'batteries_rcs', [RegisterCache() for _ in range(data.get('number_batteries', 0))]
        )
        super().__init__(**data)

    @property
    def inverter(self) -> Inverter:
        """Return Inverter model for the Plant."""
        return Inverter.from_orm(self.inverter_rc)

    @property
    def batteries(self) -> List[Battery]:
        """Return Battery models for the Plant."""
        return [Battery.from_orm(rc) for rc in self.batteries_rcs]
