from __future__ import annotations

import abc
import logging
from typing import Mapping, Sequence

from pymodbus.interfaces import IModbusDecoder

from givenergy_modbus.pdu import REQUEST_PDUS, RESPONSE_PDUS, ErrorResponse, ModbusPDU
from givenergy_modbus.util import friendly_class_name, hexlify

_logger = logging.getLogger(__package__)


class GivEnergyDecoder(IModbusDecoder, metaclass=abc.ABCMeta):
    """GivEnergy Modbus Decoder factory base class.

    This is to enable efficient decoding of unencapsulated messages (i.e. having the Modbus-specific framing
    stripped) and creating populated matching PDU DTO instances. Two factories are created, dealing with messages
    traveling in a particular direction (Request/Client vs. Response/Server) since implementations generally know
    what side of the conversation they'll be on. It does allow for more general ideas like being able to decode
    arbitrary streams of messages (i.e. captured from a network interface) where these classes may be intermixed.

    The Decoder's job is to do the bare minimum inspecting of the raw message to determine its type,
    instantiate a concrete PDU handler to decode it, and pass it on.
    """

    _function_table: Sequence[type[ModbusPDU]]  # contains all the decoder functions this factory will consider
    _lookup: Mapping[int, type[ModbusPDU]]  # lookup table mapping function code to decoder type

    def __init__(self):
        # build the lookup table at instantiation time
        self._lookup = {f.function_code: f for f in self._function_table}

    def lookupPduClass(self, fn_code: int) -> type[ModbusPDU] | None:
        """Attempts to find the ModbusPDU handler class that can handle a given function code."""
        if fn_code >= 0x80:
            fn_code &= 0x7F
        if fn_code in self._lookup:
            fn = self._lookup[fn_code]
            _logger.debug(f"Identified incoming PDU as {fn_code}/{friendly_class_name(fn)}")
            return fn
        return None

    def decode(self, data: bytes) -> ModbusPDU | ErrorResponse | None:
        """Create an appropriately populated PDU message object from a valid Modbus message.

        Extracts the `function code` from the raw message and looks up the matching ModbusPDU handler class
        that claims that function. This handler is instantiated and passed the raw message, which then proceeds
        to decode its attributes from the bytestream.
        """
        main_fn = data[0]
        data = data[1:]
        if main_fn == 0x1:
            # heartbeat / error?
            err_response = ErrorResponse()
            _logger.debug(f"About to decode data [{hexlify(data)}]")
            err_response.decode(data)
            return err_response
        elif main_fn == 0x2:
            # most functions
            if len(data) <= 19:
                _logger.error(f"PDU data is too short to find a valid function id: len={len(data)} [{hexlify(data)}]")
                return None
            fn_code = data[19]
            response = self.lookupPduClass(fn_code)
            if response:
##### changed logging here debug->info
                _logger.info(f"About to decode data [{hexlify(data[18:])}]")
                r = response(function_code=fn_code)
                r.decode(data)
                return r
            _logger.error(f"No decoder for function code {fn_code}")
            return None
        _logger.error(f"Unknown main function code {hex(main_fn)}")
        # return ExceptionResponse(main_fn, ModbusExceptions.IllegalFunction)
        return None


class GivEnergyRequestDecoder(GivEnergyDecoder):
    """Factory class to decode GivEnergy Request PDU messages. Typically used by servers processing inbound requests."""

    _function_table = REQUEST_PDUS


class GivEnergyResponseDecoder(GivEnergyDecoder):
    """Factory class to decode GivEnergy Response PDU messages. Typically used by clients to process responses."""

    _function_table = RESPONSE_PDUS
