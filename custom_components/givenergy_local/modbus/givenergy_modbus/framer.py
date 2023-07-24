from __future__ import annotations

import logging
import struct
from typing import Callable

from pymodbus.client.sync import BaseModbusClient
from pymodbus.framer import ModbusFramer
from pymodbus.interfaces import IModbusDecoder
from pymodbus.pdu import ModbusPDU
from pymodbus.utilities import hexlify_packets

from givenergy_modbus.util import hexlify

_logger = logging.getLogger(__package__)


class GivEnergyModbusFramer(ModbusFramer):
    """GivEnergy Modbus Frame controller.

    A framer abstracts away all the detail about how marshall the wire
    protocol, e.g. to detect if a current message frame exists, decoding
    it, sending it, etc.  This implementation understands the
    idiosyncrasies of GivEnergy's implementation of the Modbus spec. **Note that
    the understanding below comes from observing the wire format and analysing the
    data interchanges – no GivEnergy proprietary knowledge was needed or referred to.**

    Packet exchange looks very similar to normal Modbus TCP on the wire, with each
    message still having a regular 7-byte MBAP header consisting of:

      * `tid`, the transaction id
      * `pid`, the protocol id
      * `len`, the byte count / length of the remaining data following the header
      * `uid`, the unit id for addressing devices on the Modbus network

    This is followed by `fid` / a function code to specify how the message should be
    decoded into a PDU:

    ```
    [_________MBAP Header______] [_fid_] [_______________data________________]
    [_tid_][_pid_][_len_][_uid_]
      2b     2b     2b     1b      1b                  (len-1)b
    ```

    GivEnergy's implementation quicks can be summarised as:

      * `tid` is always `0x5959/'YY'`, so the assumption/interpretation is that clients
         have to poll continually instead of maintaining long-lived connections and
         using varying `tid`s to pair requests with responses
      * `pid` is always `0x0001`, whereas normal Modbus uses `0x0000`
      * `len` **adds** 1 extra byte (anecdotally for the unit id?) which normal
         Modbus does not. This leads to continual off-by-one differences appearing
         whenever header/frame length calculations are done. This is probably the
         biggest reason Modbus libraries struggle working out of the box.
      * `unit_id` is always `0x01`
      * `fid` is always `0x02/Read Discrete Inputs` even for requests that modify
         registers. The actual intended function is encoded 19 bytes into the data
         block. You can interpret this as functionally somewhat akin to Modbus
         sub-functions where we always use the `0x02` main function.

    Because these fields are static and we have to reinterpret what `len` means it is
    simpler to just reconsider the entire header:

    ```
    [___"MBAP+" Header____] [_______________GivEnergy Frame_______________]
    [___h1___][_len_][_h2_]
        4b      2b     2b                      (len+2)b
    ```

      * `h1` is always `0x59590001`, so can be used as a sanity check during decoding
      * `len` needs 2 added during calculations because of the previous extra byte
         off-by-one inconsistency, plus expanding the header by including 1-byte `fid`
      * `h2` is always `0x0102`, so can be used as a sanity check during decoding

    TODO These constant headers being present would allow for us to scan through the
    bytestream to try and recover from stream errors and help reset the framing.

    The GivEnergy frame itself has a consistent format:

    ```
    [____serial____] [___pad___] [_addr_] [_func_] [______data______] [_crc_]
          10b            8b         1b       1b            Nb           2b
    ```

     * `serial` of the responding data adapter (wifi/GPRS?/ethernet?) plugged into
        the inverter. For requests this is simply hardcoded as a dummy `AB1234G567`
     * `pad`'s function is unknown - it appears to be a single zero-padded byte that
        varies across responses, so might be some kind of check/crc?
     * `addr` is the "slave" address, conventionally `0x32`
     * `func` is the actual function to be executed:
        * `0x3` - read holding registers
        * `0x4` - read input registers
        * `0x6` - write single register
     * `data` is specific to the invoked function
     * `crc` - for requests it is calculated using the function id, base register and
        step count, but it is not clear how those for responses are calculated (or
        should be checked)

    In short, the message unframing algorithm is simply:

    ```python
    while len(buffer) > 8:
      tid, pid, len, uid, fid = struct.unpack(">HHHBB", buffer)
      data = buffer[8:6+len]
      process_message(tid, pid, len, uid, fid, data)
      buffer = buffer[6+len:]  # skip buffer over frame
    ```

    Raises:
        InvalidMessageReceivedException: When unable to decode an incoming message.
        ModbusIOException: When the identified function decoder fails to decode a message.
    """

    FRAME_HEAD = ">HHHBB"  # tid(w), pid(w), length(w), uid(b), fid(b)

    def __init__(self, decoder: IModbusDecoder, client: BaseModbusClient = None):
        self._buffer = b""
        self._length = 0
        self._hsize = 0x08
        self._check = 0x0
        self._fcode = 0x2
        self.decoder = decoder
        self.client = client

    def decode_data(self, data: bytes = None) -> dict | None:
        """Tries to extract the MBAP frame header and performs a few sanity checks."""
        if not data:
            data = self._buffer[: self._hsize]

        if self.isFrameReady():
            _logger.debug(f"extracting MBAP header from [{hexlify(data)}] as {self.FRAME_HEAD}")
            tid, pid, len_, uid, fid = struct.unpack(self.FRAME_HEAD, data)
            header = dict(transaction=tid, protocol=pid, length=len_, unit=uid, fcode=fid)
            _logger.debug(f"extracted values: { dict((k, f'0x{v:02x}') for k,v in header.items()) }")
            if tid != 0x5959 or pid != 0x1 or uid != 0x1:  # or fid != 0x2:
                _logger.debug(
                    f"Invalid MBAP header; corruption likely so cowardly refusing to proceed with this frame. "
                    f"(0x{tid:04x} 0x{pid:04x} 0x{uid:02x} != 0x5959 0x0001 0x01)"
                )
                return None
            return header
        return None

    def checkFrame(self) -> bool:
        """Check and decode the next frame. Returns operation success."""
        if self.isFrameReady():
            _logger.debug('Frame header should be ready')
            header = self.decode_data()
            if not header:
                _logger.debug('Frame header is corrupt, resetting frame')
                # self.resetFrame()
                return False
            self._fcode = header["fcode"]
            self._length = header["length"]

            # this short a message should not be possible?
            if self._length < 2:
                _logger.warning(f"unexpected short message length {self._length}, advancing frame")
                self.advanceFrame()
                return False
            # we have at least a complete message, continue
            if len(self._buffer) >= self._hsize + self._length - 2:
                return True
            _logger.debug(
                f'Incomplete message: len(buffer)={len(self._buffer)} < hsize={self._hsize} + length={self._length} - 2'
            )
        # we don't have enough of a message yet, try again later
        _logger.debug('Frame is not complete yet, needs more buffer data')
        return False

    def advanceFrame(self):
        """Pop the front-most frame from the buffer."""
        length = self._hsize + self._length - 2
        _logger.debug(f'length {length} = {self._hsize} + {self._length} - 2, len(buffer) = {len(self._buffer)}')
        self._buffer = self._buffer[length:]
        _logger.debug(f"buffer is now {len(self._buffer)} bytes: {self._buffer}")
        self._length = 0

    def addToFrame(self, message: bytes) -> None:
        """Add incoming data to the processing buffer."""
        self._buffer += message

    def isFrameReady(self):
        """Check if we have enough data in the buffer to read at least a frame header."""
        return len(self._buffer) >= self._hsize

    def getFrame(self):
        """Extract the next PDU frame from the buffer, discarding the leading MBAP header."""
        return self._buffer[self._hsize - 1 : self._hsize + self._length]

    def populateResult(self, result: ModbusPDU):
        """Populates the Modbus PDU object's metadata attributes from the decoded MBAP headers."""
        # no-op, there's nothing interesting in there

    def processIncomingPacket(self, data: bytes, callback: Callable, *args, **kwargs) -> None:
        """Process an incoming packet.

        This takes in a bytestream from the underlying transport and adds it to the
        frame buffer. It then repeatedly attempts to perform framing on the buffer
        by checking for a viable message at the head of the buffer, and if found pops
        off the expected length of the raw frame for processing.

        Returns when the buffer is too short to contain any more viable messages. This
        handles cases where multiple and/or partial messages arrive due to fragmentation
        or buffering on the underlying transport - these partial messages will try to
        be completed eventually as more data subsequently arrives and gets handled here.

        If decoding and processing succeeds for a message, the instantiated PDU DTO is
        handed to the supplied callback function for onward processing and dispatching.

        Args:
            data: Data from underlying transport.
            callback: Processor to receive newly-decoded PDUs.
        """
        _logger.debug(f'Incoming {len(data)} bytes: {hexlify_packets(data)}')
        self.addToFrame(data)
        while True:
            if not self.isFrameReady():
                _logger.debug('No more frames waiting, exiting')
                break
            if not self.checkFrame():
                _logger.debug("Frame check failed, dropping and resetting!!")
                self.resetFrame()
            else:
                _logger.debug('Hand off to _process')
                self._process(callback)

    def _process(self, callback, error=False):
        """Process incoming packets irrespective error condition."""
        # if error:
        #     _logger.error('In error _process')
        #     data = self.getRawFrame()
        #     result = self.decoder.decode(data)
        #     if result.function_code < 0x80:
        #         raise InvalidMessageReceivedException(result)
        # else:
        data = self.getFrame()
        _logger.debug(f'getFrame() result: {hexlify(data)}')
        result = self.decoder.decode(data)
        if result is None:
            _logger.warning('Unable to decode request')
            # raise ModbusIOException("Unable to decode request")
        else:
            _logger.info(f'Decoded response {result}')

        self.populateResult(result)
        self.advanceFrame()
        callback(result)  # defer or push to a thread?

    def resetFrame(self):
        """Reset the entire message buffer."""
        # try to mitigate corruption: if we can find the start of another MBAP header truncate the buffer
        # only up to that point
        header_offset = self._buffer.find(b'\x59\x59\x00\x01', 1)
        if header_offset > 0:
            _logger.info(
                f'Found another MBAP header at offset {header_offset} in buffer {hexlify(self._buffer)}, '
                'attempting recovery.'
            )
            self._buffer = self._buffer[header_offset:]
        else:
            self._buffer = b""
        self._length = 0

    def getRawFrame(self):
        """Returns the complete buffer."""
        return self._buffer

    def buildPacket(self, message: ModbusPDU) -> bytes:
        """Creates a finalised GivEnergy Modbus packet from a constant header plus the encoded PDU."""
        return struct.pack(self.FRAME_HEAD, 0x5959, 0x0001, len(message.encode()) + 2, 0x01, 0x02) + message.encode()
