import struct

from crccheck.crc import CrcModbus  # type: ignore[import]


class PayloadDecoder:
    """Decoder to unpack a raw binary payload into sequential typed fields."""

    _byteorder = '>'  # big-endian

    def __init__(self, payload: bytes):
        self._payload = payload
        self._pointer = 0

    # def __str__(self, *args):
    #     return f"?? {args}"
    #
    # @property
    # def string(self):
    #     return self.__str__

    def decode_8bit_uint(self):
        """Decodes an 8-bit unsigned int from the buffer."""
        self._pointer += 1
        handle = self._payload[self._pointer - 1 : self._pointer]
        return struct.unpack(self._byteorder + 'B', handle)[0]

    def decode_16bit_uint(self):
        """Decodes a 16-bit unsigned int from the buffer."""
        self._pointer += 2
        handle = self._payload[self._pointer - 2 : self._pointer]
        return struct.unpack(self._byteorder + 'H', handle)[0]

    def decode_32bit_uint(self):
        """Decodes a 32-bit unsigned int from the buffer."""
        self._pointer += 4
        handle = self._payload[self._pointer - 4 : self._pointer]
        return struct.unpack(self._byteorder + 'I', handle)[0]

    def decode_64bit_uint(self):
        """Decodes a 64-bit unsigned int from the buffer."""
        self._pointer += 8
        handle = self._payload[self._pointer - 8 : self._pointer]
        return struct.unpack(self._byteorder + 'Q', handle)[0]

    def decode_string(self, size=1) -> str:
        """Decodes a string from the buffer."""
        if self.remaining_bytes < size:
            raise struct.error(
                f'unpack requires a buffer of {size-self.remaining_bytes} bytes, {self.remaining_bytes} bytes remain'
            )
        self._pointer += size
        return self._payload[self._pointer - size : self._pointer].decode('latin1')

    @property
    def decoding_complete(self) -> bool:
        """Returns whether the payload has been completely decoded."""
        return self._pointer == len(self._payload)

    @property
    def payload_size(self) -> int:
        """Return the number of bytes the payload consists of."""
        return len(self._payload)

    @property
    def decoded_bytes(self) -> int:
        """Return the number of bytes of the payload that have been decoded."""
        return self._pointer

    @property
    def remaining_bytes(self) -> int:
        """Return the number of bytes of the payload that have been decoded."""
        return self.payload_size - self._pointer

    @property
    def remaining_payload(self) -> bytes:
        """Return the unprocessed / remaining tail of the payload."""
        return self._payload[self._pointer :]


class PayloadEncoder:
    """Encode sequential typed fields into a raw binary payload."""

    _byteorder = '>'  # big-endian
    _payload: bytes

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset the payload buffer."""
        self._payload = b''

    @property
    def payload(self) -> bytes:
        """Return the payload buffer."""
        return self._payload

    @property
    def crc(self) -> int:
        """Calculate a Modbus-compatible CRC based on the buffer contents."""
        return CrcModbus().process(self.payload).final()

    def add_8bit_uint(self, value: int):
        """Adds an 8-bit unsigned int to the buffer."""
        fstring = self._byteorder + 'B'
        self._payload += struct.pack(fstring, value)

    def add_16bit_uint(self, value):
        """Adds a 16-bit unsigned int to the buffer."""
        fstring = self._byteorder + 'H'
        self._payload += struct.pack(fstring, value)

    def add_32bit_uint(self, value):
        """Adds a 32-bit unsigned int to the buffer."""
        fstring = self._byteorder + 'I'
        self._payload += struct.pack(fstring, value)

    def add_64bit_uint(self, value):
        """Adds a 64-bit unsigned int to the buffer."""
        fstring = self._byteorder + 'Q'
        self._payload += struct.pack(fstring, value)

    def add_string(self, value: str, length: int):
        """Adds a string to the buffer."""
        fstring = self._byteorder + str(length) + 's'
        pstring = f'{value[-length:]:*>{length}}'.encode()
        self._payload += struct.pack(fstring, pstring)
