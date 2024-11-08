import logging

from custom_components.givenergy_local.givenergy_modbus.codec import PayloadDecoder
from custom_components.givenergy_local.givenergy_modbus.pdu.transparent import (
    TransparentResponse,
)

_logger = logging.getLogger(__name__)


class NullResponse(TransparentResponse):
    """Concrete PDU implementation for handling function #0/Null Response messages.

    This seems to be a quirk of the GivEnergy implementation – from time to time these responses will be sent
    unprompted by the remote device and this just handles it gracefully and allows further debugging. The function
    data payload seems to be invariably just a series of nulls.
    """

    transparent_function_code = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nulls = kwargs.get("base_register", [0] * 62)

    def _encode_function_data(self) -> None:
        super()._encode_function_data()
        [self._builder.add_16bit_uint(v) for v in self.nulls]
        self._update_check_code()

    @classmethod
    def decode_transparent_function(
        cls, decoder: PayloadDecoder, **attrs
    ) -> "NullResponse":
        if decoder.remaining_bytes != 126:
            _logger.warning(
                f"remaining bytes: {decoder.remaining_bytes}b 0x{decoder.remaining_payload.hex()} attrs: {attrs}"
            )
        attrs["nulls"] = [decoder.decode_16bit_uint() for _ in range(62)]
        attrs["check"] = decoder.decode_16bit_uint()
        return cls(**attrs)

    def expected_response(self):
        """No response expected."""

    def ensure_valid_state(self) -> None:
        """Sanity check our internal state."""
        if self.inverter_serial_number != "\x00" * 10:
            hex_str = self.inverter_serial_number.encode("latin1").hex()
            _logger.warning(
                f"Unexpected non-null inverter serial number: {self.inverter_serial_number}/0x{hex_str}"
            )
        if any(self.nulls):
            _logger.warning(
                f'Unexpected non-null "register" values: {dict(filter(lambda v: v[1] != 0, enumerate(self.nulls)))}'  # type: ignore[comparison-overlap]
            )

    def _extra_shape_hash_keys(self) -> tuple:
        return ()


__all__ = ()
