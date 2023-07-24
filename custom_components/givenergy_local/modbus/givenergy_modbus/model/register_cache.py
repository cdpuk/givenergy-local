from __future__ import annotations

import json

from givenergy_modbus.model.register import HoldingRegister, InputRegister, Register  # type: ignore  # shut up mypy


class RegisterCache(dict):
    """Holds a cache of Registers populated after querying a device."""

    def __init__(self, registers=None) -> None:
        if registers is None:
            registers = {}
        super().__init__(registers)
        self._register_lookup_table: dict[str, Register] = {}
        for k, v in InputRegister.__members__.items():
            self._register_lookup_table[k] = v
        for k, v in HoldingRegister.__members__.items():
            self._register_lookup_table[k] = v

    def __getattr__(self, item: str):
        """Magic attributes that try to look up and convert register values."""
        item_upper = item.upper()
        if item_upper in self._register_lookup_table:
            register = self._register_lookup_table[item_upper]
            val = self[register]
            return register.convert(val)
        elif item_upper + '_H' in self._register_lookup_table and item_upper + '_L' in self._register_lookup_table:
            register_h = self._register_lookup_table[item_upper + '_H']
            register_l = self._register_lookup_table[item_upper + '_L']
            val_h = self[register_h] << 16
            val_l = self[register_l]
            return register_l.convert(val_h + val_l)
        raise KeyError(item)

    def set_registers(self, type_: type[Register], registers: dict[int, int]):
        """Update internal holding register cache with given values."""
        for k, v in registers.items():
            self[type_(k)] = v

    def to_json(self) -> str:
        """Return JSON representation of the register cache, suitable for using with `from_json()`."""
        return json.dumps(self)

    @classmethod
    def from_json(cls, data: str) -> RegisterCache:
        """Instantiate a RegisterCache from its JSON form."""

        def register_object_hook(object_dict: dict[str, int]) -> dict[Register, int]:
            """Rewrite the parsed object to have Register instances as keys instead of their (string) repr."""
            lookup = {'HR': HoldingRegister, 'IR': InputRegister}
            ret = {}
            for k, v in object_dict.items():
                reg, idx = k.split(':', maxsplit=1)
                ret[lookup[reg](int(idx))] = v
            return ret

        return cls(registers=json.loads(data, object_hook=register_object_hook))

    def debug(self):
        """Dump the internal state of registers and their value representations."""
        class_name = ''

        for r, v in self.items():
            if class_name != r.__class__.__name__:
                class_name = r.__class__.__name__
                print('### ' + class_name + ' ' + '#' * 100)
            print(f'{r} {r.name:>35}: {r.repr(v):20}  |  ' f'{r.type.name:15}  {r.scaling.name:5}  0x{v:04x}  {v:10}')
