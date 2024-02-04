class ExceptionBase(Exception):
    """Base exception."""

    message: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidPduState(ExceptionBase):
    """Thrown during PDU self-validation."""

    def __init__(self, message: str, pdu) -> None:
        super().__init__(message=message)
        self.pdu = pdu


class InvalidFrame(ExceptionBase):
    """Thrown during framing when a message cannot be extracted from a frame buffer."""

    frame: bytes

    def __init__(self, message: str, frame: bytes) -> None:
        super().__init__(message=message)
        self.frame = frame


class CommunicationError(ExceptionBase):
    """Exception to indicate a communication error."""


class ConversionError(ExceptionBase):
    """Exception to indicate an error converting register values."""

    def __init__(self, key: str, source_registers: list[int], message: str) -> None:
        super().__init__(message)
        self.key = key
        self.source_registers = source_registers
