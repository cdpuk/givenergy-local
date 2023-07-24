from __future__ import annotations

import logging

from pymodbus.exceptions import InvalidMessageReceivedException, ModbusIOException
from pymodbus.transaction import FifoTransactionManager
from pymodbus.utilities import ModbusTransactionState

from givenergy_modbus.pdu import ModbusPDU
from givenergy_modbus.util import hexlify

_logger = logging.getLogger(__package__)


class GivEnergyTransactionManager(FifoTransactionManager):
    """Implements a ModbusTransactionManager.

    The only reason this exists is to be able to specify the ADU size for automated response frame processing
    since the socket needs to know how many bytes to expect in response to a given Request. See
    `ModbusTransactionManager::execute` where it checks whether the framer is an instance of
    `ModbusSocketFramer` to inform the expected response length, and even lower down the call chain
    in `ModbusTransactionManager::_recv` where there's more byte calculations based on the TransactionManager's
    provenance.

    We could've extended `GivEnergyModbusFramer` from `ModbusSocketFramer` instead, but that brings a different set
    of problems around implementation divergence in the GivEnergy implementation that would probably have been
    more work instead. Full novel in the `GivEnergyModbusFramer` class description.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._set_adu_size()  # = 8  # frame length calculation shenanigans, see `GivEnergyModbusFramer`
        # self.retry_on_empty = True
        # self.retry_on_invalid = True
        # self.retries = 1
        # self.backoff = 0.8

    def _set_adu_size(self):
        """Essentially the MBAP header size."""
        self.base_adu_size = 8

    def _calculate_response_length(self, expected_pdu_size: int) -> int:
        """Expected size of the response frame, if nothing goes wrong."""
        return self.base_adu_size + expected_pdu_size

    def _calculate_exception_length(self) -> int:
        """Index in the raw message where we can determine whether / what exception we're dealing with."""
        return 8  # was 28

    def _validate_response(self, pdu: ModbusPDU, data: bytes, expected_response_length: int) -> bool:
        """Try to validate the incoming message using the responsible PDU."""
        if not data:
            _logger.info('No response provided, cannot validate request')
            return False

        header = self.client.framer.decode_data(data)
        if not header:
            return False
        if header['len_'] != expected_response_length:
            _logger.warning(
                f'Expected ({expected_response_length}) response length differs from '
                f'actual ({header["len_"]}) - potential bug?'
            )
            return False
        return True

    def execute(self, request: ModbusPDU) -> ModbusPDU:
        """Main processing loop."""
        res = super().execute(request)
        _logger.debug(f'Old implementation returned: execute(request)={res}')
        return res

    def _transact(
        self, request: ModbusPDU, expected_response_length: int, full=False, broadcast=False
    ) -> tuple[bytes, None | Exception]:
        """Connects and sends the request, and reads back the response."""
        # if full:
        #     raise NotImplementedError('This implementation does not support full messages')
        if broadcast:
            raise NotImplementedError('This implementation does not support broadcast messages')

        try:
            self.client.connect()
            tx_data = self.client.framer.buildPacket(request)
            _logger.debug(f"SEND raw frame: {hexlify(tx_data)}")
            #print(f"SEND raw frame: {hexlify(tx_data)}")
            _logger.info(f'Sending request {request}')
            tx_size = self._send(tx_data)

            # need to handle retry logic?

            if tx_size:
                _logger.debug("Transition from SENDING to WAITING_FOR_REPLY")
                self.client.state = ModbusTransactionState.WAITING_FOR_REPLY

            rx_data = self._recv(expected_response_length, full)
            _logger.debug(f"RECV raw frame: {hexlify(rx_data)}")
            return rx_data, None

        except (OSError, ModbusIOException, InvalidMessageReceivedException) as msg:
            _logger.error("Transaction failed")
            # if self.reset_socket:
            self.client.close()
            return b'', msg

    def _send(self, data: bytes, retrying=False) -> int:
        return self.client.framer.sendPacket(data)

    # def _recv(self, expected_response_length: int, _) -> bytes:
    #     exception_length = self._calculate_exception_length()
    #     min_size = 28  # 8 (hdr) + 20 (fn offset)
