import logging
from abc import ABC

from custom_components.givenergy_local.givenergy_modbus.codec import (
    PayloadDecoder,
    PayloadEncoder,
)
from custom_components.givenergy_local.givenergy_modbus.exceptions import (
    InvalidPduState,
)
from custom_components.givenergy_local.givenergy_modbus.pdu.transparent import (
    TransparentMessage,
    TransparentRequest,
    TransparentResponse,
)

_logger = logging.getLogger(__name__)


class ReadRegistersMessage(TransparentMessage, ABC):
    """Mixin for commands that specify base register and register count semantics."""

    base_register: int
    register_count: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_register = kwargs.get("base_register", 0)
        self.register_count = kwargs.get("register_count", 0)

    @classmethod
    def decode_transparent_function(
        cls, decoder: PayloadDecoder, **attrs
    ) -> "ReadRegistersMessage":
        attrs["base_register"] = decoder.decode_16bit_uint()
        attrs["register_count"] = decoder.decode_16bit_uint()
        if issubclass(cls, ReadRegistersResponse) and not attrs.get("error", False):
            attrs["register_values"] = [
                decoder.decode_16bit_uint() for _ in range(attrs["register_count"])
            ]
        attrs["check"] = decoder.decode_16bit_uint()
        return cls(**attrs)

    def _extra_shape_hash_keys(self) -> tuple:
        return super()._extra_shape_hash_keys() + (
            self.base_register,
            self.register_count,
        )

    def _ensure_registers_spec_correct(self):
        if self.base_register is None:
            raise InvalidPduState("Base register must be set", self)
        if self.base_register < 0 or 0xFFFF < self.base_register:
            raise InvalidPduState("Base register must be an unsigned 16-bit int", self)

        if self.register_count is None:
            raise InvalidPduState("Register count must be set", self)
        if self.register_count == 0 and not self.error:
            _logger.warning(f"Register count of 0 does not make sense: {self}")


class ReadRegistersRequest(ReadRegistersMessage, TransparentRequest, ABC):
    """Handles all messages that request a range of registers."""

    def _encode_function_data(self):
        super()._encode_function_data()
        self._builder.add_16bit_uint(self.base_register)
        self._builder.add_16bit_uint(self.register_count)
        self._update_check_code()

    def _update_check_code(self):
        crc_builder = PayloadEncoder()
        crc_builder.add_8bit_uint(self.slave_address)
        crc_builder.add_8bit_uint(self.transparent_function_code)
        crc_builder.add_16bit_uint(self.base_register)
        crc_builder.add_16bit_uint(self.register_count)
        self.check = crc_builder.crc
        self.check = int.from_bytes(self.check.to_bytes(2, "little"), "big")
        self._builder.add_16bit_uint(self.check)

    def ensure_valid_state(self):
        """Sanity check our internal state."""
        self._ensure_registers_spec_correct()

        if self.register_count != 1 and self.base_register % 60 != 0:
            _logger.warning(
                f"Base register {self.base_register} not aligned on 60-byte boundary"
            )
        if self.register_count <= 0 or 60 < self.register_count:
            raise InvalidPduState("Register count must be in (0,60]", self)


class ReadRegistersResponse(ReadRegistersMessage, TransparentResponse, ABC):
    """Handles all messages that respond with a range of registers."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_values: list[int] = kwargs.get("register_values", [])

    def _encode_function_data(self):
        super()._encode_function_data()
        self._builder.add_16bit_uint(self.base_register)
        self._builder.add_16bit_uint(self.register_count)
        [self._builder.add_16bit_uint(v) for v in self.register_values]
        self._update_check_code()

    def ensure_valid_state(self) -> None:
        """Sanity check our internal state."""
        self._ensure_registers_spec_correct()

        if not self.error:
            # if self.register_count != 1 and self.base_register % 60 != 0:
            #     _logger.warning(f'Base register {self.base_register} not aligned on 60-byte boundary')
            if self.register_count != len(self.register_values):
                raise InvalidPduState(
                    f"register_count={self.register_count} but len(register_values)={len(self.register_values)}.",
                    self,
                )

        expected_padding = 0x12 if self.error else 0x8A
        if self.padding != expected_padding:
            _logger.debug(
                f"Expected padding 0x{expected_padding:02x}, found 0x{self.padding:02x} instead: {self}"
            )

        crc_builder = PayloadEncoder()
        crc_builder.add_8bit_uint(self.slave_address)
        crc_builder.add_8bit_uint(self.transparent_function_code)
        crc_builder.add_string(
            self.inverter_serial_number, len(self.inverter_serial_number)
        )
        crc_builder.add_16bit_uint(self.base_register)
        crc_builder.add_16bit_uint(self.register_count)
        [crc_builder.add_16bit_uint(r) for r in self.register_values]
        crc = crc_builder.crc
        crc = int.from_bytes(crc.to_bytes(2, "little"), "big")

        if self.check != crc:
            raise InvalidPduState(
                f"supplied CRC 0x{self.check:04x} does not match calculated CRC 0x{crc:04x}",
                self,
            )

    def to_dict(self) -> dict[int, int]:
        """Return the registers as a dict of register_index:value. Accounts for base_register offsets."""
        return {
            k: v for k, v in enumerate(self.register_values, start=self.base_register)
        }

    def is_suspicious(self) -> bool:
        """Try to identify known-bad data in register lookup calls and prevent them from entering the dispatching."""
        if (
            self.base_register % 60 == 0
            and self.register_count == 60
            and len(self.register_values) == 60
        ):
            count_known_bad_register_values = (
                self.register_values[28] == 0x4C32,
                self.register_values[30] == 0xA119,
                self.register_values[31] == 0x34EA,
                self.register_values[32] == 0xE77F,
                self.register_values[33] == 0xD475,
                self.register_values[35] == 0x4500,
                self.register_values[40] in (0xE4F9, 0xB619),
                self.register_values[41] == 0xC0A8,
                self.register_values[43] == 0xC0A8,
                self.register_values[46] == 0xC5E9,
                self.register_values[50] in (0x60EF, 0x503C),
                self.register_values[51] == 0x8018,
                self.register_values[52] == 0x43E0,
                self.register_values[53] == 0xF6CE,
                self.register_values[56] == 0x080A,
                self.register_values[58] == 0xFCC1,
                self.register_values[59] == 0x661E,
            ).count(True)
            if count_known_bad_register_values > 5:
                _logger.debug(
                    f"Ignoring known suspicious update with {count_known_bad_register_values} known bad "
                    f"register values {self}: {self.to_dict()}"
                )
                return True
        return False


class ReadHoldingRegisters(ReadRegistersMessage, ABC):
    """Request & Response PDUs for function #3/Read Holding Registers."""

    transparent_function_code = 3


class ReadHoldingRegistersRequest(ReadHoldingRegisters, ReadRegistersRequest):
    """Concrete PDU implementation for handling function #3/Read Holding Registers request messages."""

    def expected_response(self):
        return ReadHoldingRegistersResponse(
            base_register=self.base_register,
            register_count=self.register_count,
            slave_address=self.slave_address,
        )


class ReadHoldingRegistersResponse(ReadHoldingRegisters, ReadRegistersResponse):
    """Concrete PDU implementation for handling function #3/Read Holding Registers response messages."""

    def expected_response(self):
        return


class ReadInputRegisters(ReadRegistersMessage, ABC):
    """Request & Response PDUs for function #4/Read Input Registers."""

    transparent_function_code = 4


class ReadInputRegistersRequest(ReadInputRegisters, ReadRegistersRequest):
    """Concrete PDU implementation for handling function #4/Read Input Registers request messages."""

    def expected_response(self):
        return ReadInputRegistersResponse(
            base_register=self.base_register,
            register_count=self.register_count,
            slave_address=self.slave_address,
        )


class ReadInputRegistersResponse(ReadInputRegisters, ReadRegistersResponse):
    """Concrete PDU implementation for handling function #4/Read Input Registers response messages."""

    def expected_response(self):
        return


class ReadBatteryInputRegisters(ReadRegistersMessage, ABC):
    """Request & Response PDUs for function #4/Read Input Registers."""

    transparent_function_code = 0x16


class ReadBatteryInputRegistersRequest(ReadBatteryInputRegisters, ReadRegistersRequest):
    """Concrete PDU implementation for handling function #4/Read Input Registers request messages."""

    def expected_response(self):
        return ReadInputRegistersResponse(
            base_register=self.base_register,
            register_count=self.register_count,
            slave_address=self.slave_address,
        )


class ReadBatteryInputRegistersResponse(
    ReadBatteryInputRegisters, ReadRegistersResponse
):
    """Concrete PDU implementation for handling function #4/Read Input Registers response messages."""

    def expected_response(self):
        return


__all__ = ()
