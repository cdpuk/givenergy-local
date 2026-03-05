import builtins
from dataclasses import dataclass
from datetime import datetime as datetime_type
from json import JSONEncoder
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from custom_components.givenergy_local.givenergy_modbus.exceptions import (
    ConversionError,
)

from custom_components.givenergy_local.givenergy_modbus.model import TimeSlot

if TYPE_CHECKING:
    from custom_components.givenergy_local.givenergy_modbus.model.register_cache import (
        RegisterCache,
    )


class Converter:
    """Type of data register represents. Encoding is always big-endian."""

    @staticmethod
    def uint16(val: int) -> int:
        """Simply return the raw unsigned 16-bit integer register value."""
        if val is not None:
            return int(val)

    @staticmethod
    def int16(val: int) -> int:
        """Interpret as a 16-bit integer register value."""
        if val is not None:
            if val & (1 << (16 - 1)):
                val -= 1 << 16
            return val

    @staticmethod
    def duint8(val: int, *idx: int) -> int:
        """Split one register into two unsigned 8-bit ints and return the specified index."""
        if val is not None:
            vals = (val >> 8), (val & 0xFF)
            return vals[idx[0]]

    @staticmethod
    def uint32(high_val: int, low_val: int) -> int:
        """Combine two registers into an unsigned 32-bit int."""
        if high_val is not None and low_val is not None:
            return (high_val << 16) + low_val

    @staticmethod
    def timeslot(start_time: int, end_time: int) -> Optional[TimeSlot]:
        """Interpret register as a time slot."""
        if start_time == 60 or end_time == 60:
            # Probably due to the inverter holding an invalid value in a timeslot.
            # Real life example register values include:
            # - [0, 60]
            # - [60, 2359]
            # Clearly '60' is the problem value in such cases. This seems to correspond to the
            # GivEnergy portal displaying '--:--', which we can only assume means 'undefined'.
            return None

        if start_time is not None and end_time is not None:
            return TimeSlot.from_repr(start_time, end_time)

    @staticmethod
    def bool(val: int | None) -> builtins.bool | None:
        """Interpret register as a bool."""
        if val is not None:
            return bool(val)
        return None

    @staticmethod
    def string(*vals: int) -> Optional[str]:
        """Represent one or more registers as a concatenated string."""
        if vals is not None and None not in vals:
            return (
                b"".join(v.to_bytes(2, byteorder="big") for v in vals)
                .decode(encoding="latin1")
                .replace("\x00", "")
                .upper()
            )
        return None

    @staticmethod
    def fstr(val, fmt) -> Optional[str]:
        """Render a value using a format string."""
        if val is not None:
            return f"{val:{fmt}}"
        return None

    @staticmethod
    def firmware_version(dsp_version: int, arm_version: int) -> Optional[str]:
        """Represent ARM & DSP firmware versions in the same format as the dashboard."""
        if dsp_version is not None and arm_version is not None:
            return f"D0.{dsp_version}-A0.{arm_version}"

    @staticmethod
    def inverter_max_power(device_type_code: str) -> Optional[int]:
        """Determine max inverter power from device_type_code."""
        dtc_to_power = {
            "2001": 5000,
            "2002": 4600,
            "2003": 3600,
            "3001": 3000,
            "3002": 3600,
            "4001": 6000,
            "4002": 8000,
            "4003": 10000,
            "4004": 11000,
            "8001": 6000,
        }
        return dtc_to_power.get(device_type_code)

    @staticmethod
    def hex(val: int, width: int = 4) -> str:
        """Represent a register value as a 4-character hex string."""
        if val is not None:
            return f"{val:0{width}x}"

    @staticmethod
    def milli(val: int) -> float:
        """Represent a register value as a float in 1/1000 units."""
        if val is not None:
            return val / 1000

    @staticmethod
    def centi(val: int) -> float:
        """Represent a register value as a float in 1/100 units."""
        if val is not None:
            return val / 100

    @staticmethod
    def deci(val: int) -> float:
        """Represent a register value as a float in 1/10 units."""
        if val is not None:
            return val / 10

    @staticmethod
    def datetime(year, month, day, hour, min, sec) -> Optional[datetime_type]:
        """Compose a datetime from 6 registers."""
        if None not in [year, month, day, hour, min, sec]:
            return datetime_type(year + 2000, month, day, hour, min, sec)
        return None


@dataclass(init=False)
class RegisterDefinition:
    """Specifies how to convert raw register values into their actual representation."""

    pre_conv: Union[Callable, tuple, None]
    post_conv: Union[Callable, tuple[Callable, Any], None]
    registers: tuple["Register"]

    def __init__(self, *args, **kwargs):
        self.pre_conv = args[0]
        self.post_conv = args[1]
        self.registers = args[2:]

    def __hash__(self):
        return hash(self.registers)


class RegisterGetter:
    """Specifies how device attributes are derived from raw register values."""

    REGISTER_LUT: dict[str, RegisterDefinition]

    def __init__(self, register_cache: "RegisterCache") -> None:
        """Store the register cache for value extraction."""
        self._obj = register_cache

    def get(self, key: str, default: Any = None) -> Any:
        """Return a named register's value, after pre- and post-conversion."""
        try:
            r = self.REGISTER_LUT[key]
        except KeyError:
            return default

        regs = [self._obj.get(r) for r in r.registers]

        if None in regs:
            return None

        try:
            if r.pre_conv:
                if isinstance(r.pre_conv, tuple):
                    args = regs + list(r.pre_conv[1:])
                    val = r.pre_conv[0](*args)
                else:
                    val = r.pre_conv(*regs)
            else:
                val = regs

            if r.post_conv:
                if isinstance(r.post_conv, tuple):
                    return r.post_conv[0](val, *r.post_conv[1:])
                else:
                    if not isinstance(r.post_conv, Callable):  # type: ignore[arg-type]
                        pass
                    return r.post_conv(val)
            return val
        except ValueError as err:
            raise ConversionError(key, regs, str(err)) from err

    def to_dict(self) -> dict[str, Any]:
        """Build dict suitable for model_validate()."""
        return {k: self.get(k) for k in self.REGISTER_LUT}

    @classmethod
    def to_fields(cls) -> dict[str, tuple[Any, None]]:
        """Determine a pydantic fields definition for the class."""

        def infer_return_type(obj: Any):
            # Unwrap staticmethod/classmethod to get underlying function for annotations
            func = getattr(obj, "__func__", obj)
            if hasattr(func, "__annotations__") and (
                ret := func.__annotations__.get("return", None)
            ):
                return ret
            # Only return obj if it's a type (e.g. IntEnum), not a callable
            if isinstance(obj, type):
                return obj
            return Any

        def return_type(v: RegisterDefinition):
            if v.post_conv:
                if isinstance(v.post_conv, tuple):
                    return infer_return_type(v.post_conv[0])
                else:
                    return infer_return_type(v.post_conv)
            elif v.pre_conv:
                if isinstance(v.pre_conv, tuple):
                    return infer_return_type(v.pre_conv[0])
                else:
                    return infer_return_type(v.pre_conv)
            return Any

        register_fields = {
            k: (Optional[return_type(v)], None) for k, v in cls.REGISTER_LUT.items()
        }

        return register_fields


class RegisterEncoder(JSONEncoder):
    """Custom JSONEncoder to work around Register behaviour.

    This is a workaround to force registers to render themselves as strings instead of
    relying on the internal identity by default.
    """

    def default(self, o: Any) -> str:
        """Custom JSON encoder to treat RegisterCaches specially."""
        if isinstance(o, Register):
            return f"{o._type}_{o._idx}"
        else:
            return super().default(o)  # type: ignore[no-any-return]


class Register:
    """Register base class."""

    TYPE_HOLDING = "HR"
    TYPE_INPUT = "IR"

    _type: str
    _idx: int

    def __init__(self, idx):
        self._idx = idx

    def __str__(self):
        return "%s_%d" % (self._type, int(self._idx))

    __repr__ = __str__

    def __eq__(self, other):
        return (
            isinstance(other, Register)
            and self._type == other._type
            and self._idx == other._idx
        )

    def __hash__(self):
        return hash((self._type, self._idx))


class HR(Register):
    """Holding Register."""

    _type = Register.TYPE_HOLDING


class IR(Register):
    """Input Register."""

    _type = Register.TYPE_INPUT
