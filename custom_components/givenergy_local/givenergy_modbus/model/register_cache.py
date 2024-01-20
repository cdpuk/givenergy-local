import datetime
import json
from typing import TYPE_CHECKING, DefaultDict, Optional

from custom_components.givenergy_local.givenergy_modbus.model.register import (
    HR,
    IR,
    Register,
)

if TYPE_CHECKING:
    from custom_components.givenergy_local.givenergy_modbus.model import TimeSlot


class RegisterCache(DefaultDict[Register, int]):
    """Holds a cache of Registers populated after querying a device."""

    def __init__(self, registers: Optional[dict[Register, int]] = None) -> None:
        if registers is None:
            registers = {}
        super().__init__(lambda: 0, registers)

    def json(self) -> str:
        """Return JSON representation of the register cache, to mirror `from_json()`."""  # noqa: D402,D202,E501
        return json.dumps(self)

    @classmethod
    def from_json(cls, data: str) -> "RegisterCache":
        """Instantiate a RegisterCache from its JSON form."""

        def register_object_hook(object_dict: dict[str, int]) -> dict[Register, int]:
            """Rewrite the parsed object to have Register instances as keys instead of their (string) repr."""
            lookup = {"HR": HR, "IR": IR}
            ret = {}
            for k, v in object_dict.items():
                if k.find("(") > 0:
                    reg, idx = k.split("(", maxsplit=1)
                    idx = idx[:-1]
                elif k.find(":") > 0:
                    reg, idx = k.split(":", maxsplit=1)
                else:
                    raise ValueError(f"{k} is not a valid Register type")
                try:
                    ret[lookup[reg](int(idx))] = v
                except ValueError:
                    # unknown register, discard silently
                    continue
            return ret

        return cls(registers=(json.loads(data, object_hook=register_object_hook)))

    # helper methods to convert register data types

    def to_string(self, *registers: Register) -> str:
        """Combine registers into an ASCII string."""
        s = "".join(
            [
                self[r].to_bytes(2, byteorder="big").decode(encoding="latin1")
                for r in registers
            ]
        )
        return "".join(filter(str.isalnum, s)).upper()

    def to_hex_string(self, *registers: Register) -> str:
        """Render a register as a 2-byte hexadecimal value."""
        values = [f"{self[r]:04x}" for r in registers]
        if all(values):
            ret = ""
            for r in registers:
                ret += f"{self[r]:04x}"
            return "".join(filter(str.isalnum, ret)).upper()
        return ""

    def to_duint8(self, *registers: Register) -> tuple[int, ...]:
        """Split registers into two unsigned 8-bit integers each."""
        return sum(((self[r] >> 8, self[r] & 0xFF) for r in registers), ())

    def to_uint32(self, high_register: Register, low_register: Register) -> int:
        """Combine two registers into an unsigned 32-bit integer."""
        return (self[high_register] << 16) + self[low_register]

    def to_datetime(
        self,
        y: Register,
        m: Register,
        d: Register,
        h: Register,
        min: Register,
        s: Register,
    ):
        """Combine 6 registers into a datetime, with safe defaults for zeroes."""
        return datetime.datetime(
            self[y] + 2000, self.get(m, 1), self.get(d, 1), self[h], self[min], self[s]
        )

    def to_timeslot(self, start: Register, end: Register) -> "TimeSlot":
        """Combine two registers into a time slot."""
        from custom_components.givenergy_local.givenergy_modbus.model import TimeSlot

        return TimeSlot.from_repr(self[start], self[end])
