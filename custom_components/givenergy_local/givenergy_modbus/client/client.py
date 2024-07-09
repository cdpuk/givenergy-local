import asyncio
import logging
import socket
from asyncio import Future, Queue, StreamReader, StreamWriter, Task
from typing import Callable, Dict, List, Optional, Tuple

from custom_components.givenergy_local.givenergy_modbus.client import commands
from custom_components.givenergy_local.givenergy_modbus.exceptions import (
    CommunicationError,
    ExceptionBase,
)
from custom_components.givenergy_local.givenergy_modbus.framer import (
    ClientFramer,
    Framer,
)
from custom_components.givenergy_local.givenergy_modbus.model.plant import Plant
from custom_components.givenergy_local.givenergy_modbus.pdu import (
    HeartbeatRequest,
    TransparentRequest,
    TransparentResponse,
    WriteHoldingRegisterResponse,
)

_logger = logging.getLogger(__name__)


class Client:
    """Asynchronous client utilising long-lived connections to a network device."""

    framer: Framer
    expected_responses: "Dict[int, Future[TransparentResponse]]" = {}
    plant: Plant
    # refresh_count: int = 0
    # debug_frames: Dict[str, Queue]
    connected = False
    reader: StreamReader
    writer: StreamWriter
    network_consumer_task: Task
    network_producer_task: Task

    tx_queue: "Queue[Tuple[bytes, Optional[Future]]]"

    def __init__(self, host: str, port: int, connect_timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.framer = ClientFramer()
        self.plant = Plant()
        self.tx_queue = Queue(maxsize=20)
        # self.debug_frames = {
        #     'all': Queue(maxsize=1000),
        #     'error': Queue(maxsize=1000),
        # }

    async def connect(self) -> None:
        """Connect to the remote host and start background tasks."""
        try:
            connection = asyncio.open_connection(
                host=self.host, port=self.port, flags=socket.TCP_NODELAY
            )
            self.reader, self.writer = await asyncio.wait_for(
                connection, timeout=self.connect_timeout
            )
        except OSError as e:
            raise CommunicationError(
                f"Error connecting to {self.host}:{self.port}"
            ) from e
        self.network_consumer_task = asyncio.create_task(
            self._task_network_consumer(), name="network_consumer"
        )
        self.network_producer_task = asyncio.create_task(
            self._task_network_producer(), name="network_producer"
        )
        # asyncio.create_task(self._task_dump_queues_to_files(), name='dump_queues_to_files'),
        self.connected = True
        _logger.info("Connection established to %s:%d", self.host, self.port)

    async def detect_plant(self, timeout: int = 1, retries: int = 3) -> None:
        """Detect inverter capabilities that influence how subsequent requests are made."""
        _logger.info("Detectig plant")

        # Refresh the core set of registers that work across all inverters
        await self.refresh_plant(True, timeout=timeout, retries=retries)

        # Use that to detect the number of batteries
        self.plant.detect_batteries()
        _logger.info("Batteries detected: %d", self.plant.number_batteries)

        # Some devices support additional registers
        # When unsupported, devices appear to simple ignore requests
        possible_additional_holding_registers = [300]
        for hr in possible_additional_holding_registers:
            try:
                reqs = commands.refresh_additional_holding_registers(hr)
                await self.execute(reqs, timeout=timeout, retries=retries)
                _logger.info(
                    "Detected additional holding register support (base_register=%d)",
                    hr,
                )
                self.plant.additional_holding_registers.append(hr)
            except asyncio.TimeoutError:
                _logger.debug(
                    "Inverter did not respond to holder register query (base_register=%d)",
                    hr,
                )

    async def close(self) -> None:
        """Disconnect from the remote host and clean up tasks and queues."""
        if not self.connected:
            return

        _logger.debug("Disconnecting and cleaning up")

        self.connected = False

        if self.tx_queue:
            while not self.tx_queue.empty():
                _, future = self.tx_queue.get_nowait()
                if future:
                    future.cancel()

        if self.network_producer_task:
            self.network_producer_task.cancel()

        if hasattr(self, "writer") and self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            del self.writer

        if self.network_producer_task:
            self.network_consumer_task.cancel()

        if hasattr(self, "reader") and self.reader:
            self.reader.feed_eof()
            self.reader.set_exception(RuntimeError("cancelling"))
            del self.reader

        self.expected_responses = {}
        # self.debug_frames = {
        #     'all': Queue(maxsize=1000),
        #     'error': Queue(maxsize=1000),
        # }

    async def refresh_plant(
        self,
        full_refresh: bool = True,
        max_batteries: int = 5,
        timeout: float = 1.0,
        retries: int = 0,
    ) -> Plant:
        """Refresh data about the Plant."""
        reqs = commands.refresh_plant_data(
            full_refresh, self.plant.number_batteries, max_batteries
        )
        await self.execute(reqs, timeout=timeout, retries=retries)
        return self.plant

    async def watch_plant(
        self,
        handler: Optional[Callable] = None,
        refresh_period: float = 15.0,
        max_batteries: int = 5,
        timeout: float = 1.0,
        retries: int = 0,
        passive: bool = False,
    ):
        """Refresh data about the Plant."""
        await self.connect()
        await self.refresh_plant(True, max_batteries=max_batteries)
        while True:
            if handler:
                handler()
            await asyncio.sleep(refresh_period)
            if not passive:
                reqs = commands.refresh_plant_data(False, self.plant.number_batteries)
                await self.execute(
                    reqs, timeout=timeout, retries=retries, return_exceptions=True
                )

    async def one_shot_command(
        self, requests: list[TransparentRequest], timeout=1.5, retries=0
    ) -> None:
        """Run a single set of requests and return."""
        await self.connect()
        await self.execute(requests, timeout=timeout, retries=retries)

    async def _task_network_consumer(self):
        """Task for orchestrating incoming data."""
        while hasattr(self, "reader") and self.reader and not self.reader.at_eof():
            frame = await self.reader.read(300)
            # await self.debug_frames['all'].put(frame)
            async for message in self.framer.decode(frame):
                _logger.debug("Processing %s", message)
                if isinstance(message, ExceptionBase):
                    _logger.warning(
                        "Expected response never arrived but resulted in exception: %s",
                        message,
                    )
                    continue
                if isinstance(message, HeartbeatRequest):
                    _logger.debug("Responding to HeartbeatRequest")
                    await self.tx_queue.put(
                        (message.expected_response().encode(), None)
                    )
                    continue
                if not isinstance(message, TransparentResponse):
                    _logger.warning(
                        "Received unexpected message type for a client: %s", message
                    )
                    continue
                if isinstance(message, WriteHoldingRegisterResponse):
                    if message.error:
                        _logger.warning("%s", message)
                    else:
                        _logger.info("%s", message)

                future = self.expected_responses.get(message.shape_hash())

                if future and not future.done():
                    future.set_result(message)
                # try:
                self.plant.update(message)
                # except RegisterCacheUpdateFailed as e:
                #     # await self.debug_frames['error'].put(frame)
                #     _logger.debug(f'Ignoring {message}: {e}')
        _logger.debug(
            "network_consumer reader at EOF, cannot continue, closing connection"
        )
        await self.close()

    async def _task_network_producer(self, tx_message_wait: float = 0.25):
        """Producer loop to transmit queued frames with an appropriate delay."""
        while hasattr(self, "writer") and self.writer and not self.writer.is_closing():
            message, future = await self.tx_queue.get()
            self.writer.write(message)
            await self.writer.drain()
            self.tx_queue.task_done()
            if future:
                future.set_result(True)
            await asyncio.sleep(tx_message_wait)
        _logger.debug(
            "network_producer writer is closing, cannot continue, closing connection"
        )
        await self.close()

    # async def _task_dump_queues_to_files(self):
    #     """Task to periodically dump debug message frames to disk for debugging."""
    #     while True:
    #         await asyncio.sleep(30)
    #         if self.debug_frames:
    #             os.makedirs('debug', exist_ok=True)
    #             for name, queue in self.debug_frames.items():
    #                 if not queue.empty():
    #                     async with aiofiles.open(f'{os.path.join("debug", name)}_frames.txt', mode='a') as str_file:
    #                         await str_file.write(f'# {arrow.utcnow().timestamp()}\n')
    #                         while not queue.empty():
    #                             item = await queue.get()
    #                             await str_file.write(item.hex() + '\n')

    def execute(
        self,
        requests: list[TransparentRequest],
        timeout: float,
        retries: int,
        return_exceptions: bool = False,
    ) -> "Future[List[TransparentResponse]]":
        """Helper to perform multiple requests in bulk."""
        return asyncio.gather(
            *[
                self.send_request_and_await_response(
                    m, timeout=timeout, retries=retries
                )
                for m in requests
            ],
            return_exceptions=return_exceptions,
        )

    async def send_request_and_await_response(
        self, request: TransparentRequest, timeout: float, retries: int
    ) -> TransparentResponse:
        """Send a request to the remote, await and return the response."""
        raw_frame = request.encode()

        # mark the expected response
        expected_response = request.expected_response()
        expected_shape_hash = expected_response.shape_hash()

        tries = 0
        while tries <= retries:
            tries += 1
            existing_response_future = self.expected_responses.get(expected_shape_hash)
            if existing_response_future and not existing_response_future.done():
                _logger.debug(
                    "Cancelling existing in-flight request and replacing: %s", request
                )
                existing_response_future.cancel()
            response_future: Future[
                TransparentResponse
            ] = asyncio.get_event_loop().create_future()
            self.expected_responses[expected_shape_hash] = response_future

            frame_sent = asyncio.get_event_loop().create_future()
            await self.tx_queue.put((raw_frame, frame_sent))
            await asyncio.wait_for(
                frame_sent, timeout=self.tx_queue.qsize() + 1
            )  # this should only happen if the producer task is stuck

            _logger.debug("Request sent (attempt %d): %s", tries, request)

            try:
                await asyncio.wait_for(response_future, timeout=timeout)
                if response_future.done():
                    response = response_future.result()
                    if tries > 1:
                        _logger.debug("Received %s after %d attempts", response, tries)
                    if response.error:
                        _logger.error("Received error response, retrying: %s", response)
                    else:
                        return response
            except asyncio.TimeoutError:
                pass

            if tries <= retries:
                _logger.debug(
                    "Timeout awaiting %s, attempting retry %d of %d",
                    expected_response,
                    tries,
                    retries,
                )

        _logger.warning(
            "Timeout awaiting %s after %d tries at %ds, giving up",
            expected_response,
            tries,
            timeout,
        )
        raise asyncio.TimeoutError()
