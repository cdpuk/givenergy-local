import logging
from abc import ABC

from custom_components.givenergy_local.givenergy_modbus.codec import PayloadDecoder
from custom_components.givenergy_local.givenergy_modbus.pdu.base import (
    BasePDU,
    ClientIncomingMessage,
    ClientOutgoingMessage,
)

_logger = logging.getLogger(__name__)


class HeartbeatMessage(BasePDU, ABC):
    """Root of the hierarchy for 1/Heartbeat function PDUs."""

    function_code = 1
    data_adapter_type: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_adapter_type: int = kwargs.get("data_adapter_type", 0x00)

    def __str__(self) -> str:
        return (
            f"1/{self.__class__.__name__}("
            f"data_adapter_serial_number={self.data_adapter_serial_number} "
            f"data_adapter_type={self.data_adapter_type})"
        )

    def _encode_function_data(self):
        """Encode request PDU message and populate instance attributes."""
        self._builder.add_8bit_uint(self.data_adapter_type)

    def _decode_function_data(self, decoder):
        """Encode request PDU message and populate instance attributes."""
        self.data_adapter_type = decoder.decode_8bit_uint()

    @classmethod
    def decode_main_function(
        cls, decoder: PayloadDecoder, **attrs
    ) -> "HeartbeatMessage":
        attrs["data_adapter_serial_number"] = decoder.decode_string(10)
        attrs["data_adapter_type"] = decoder.decode_8bit_uint()
        return cls(**attrs)

    def ensure_valid_state(self):
        """Sanity check our internal state."""

    def _update_check_code(self):
        pass

    def _extra_shape_hash_keys(self) -> tuple:
        """Allows extra message-specific keys to be mixed in."""
        return (self.data_adapter_type,)


class HeartbeatRequest(HeartbeatMessage, ClientIncomingMessage, ABC):
    """PDU sent by remote server to check liveness of client."""

    def expected_response(self) -> "HeartbeatResponse":
        """Create an appropriate response for an incoming HeartbeatRequest."""
        return HeartbeatResponse(data_adapter_type=self.data_adapter_type)


class HeartbeatResponse(HeartbeatMessage, ClientOutgoingMessage, ABC):
    """PDU returned by client (within 5s) to confirm liveness."""

    def decode(self, data: bytes):
        """Decode response PDU message and populate instance attributes."""
        decoder = PayloadDecoder(data)
        self.data_adapter_serial_number = decoder.decode_string(10)
        self.data_adapter_type = decoder.decode_8bit_uint()
        _logger.debug(f"Successfully decoded {len(data)} bytes")

    def expected_response(self) -> None:
        """No replies expected for HeartbeatResponse."""


__all__ = ()
