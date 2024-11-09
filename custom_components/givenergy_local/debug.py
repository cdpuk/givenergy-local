#!/usr/bin/env python3

"""CLI tool for inverter debugging."""

import argparse
import asyncio
import logging
import sys
from types import TracebackType
from typing import Type

from custom_components.givenergy_local.givenergy_modbus.client.client import Client
from custom_components.givenergy_local.givenergy_modbus.pdu.read_registers import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersRequest,
    ReadRegistersResponse,
)


async def main() -> None:
    """Main entry point of the CLI tool."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("inverter_host", help="Hostname or IP address of the inverter")
    parser.add_argument(
        "--slave",
        default="0x32",
        help="Slave address to use (usually 0x32 or 0x11)",
    )
    parser.add_argument(
        "--ir",
        default="0,60,120",
        help="Comma-separated list of input registers to request",
    )
    parser.add_argument(
        "--hr",
        default="0,60,120,300",
        help="List of holding registers to request",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Also log low-level messages"
    )
    args = parser.parse_args()

    try:
        args.slave = int(args.slave, 16)
    except ValueError:
        print(f"Error: Invalid hex value '{args.slave}' for slave address")
        sys.exit(1)

    input_registers = [int(r) for r in args.ir.split(",") if r]
    for register in input_registers:
        if register % 60 != 0:
            print(
                f"Error: requested input register {register} is invalid (must be divisible by 60)"
            )
            sys.exit(1)

    holding_registers = [int(r) for r in args.hr.split(",") if r]
    for register in holding_registers:
        if int(register) % 60 != 0:
            print(
                f"Error: requested holding register {register} is invalid (must be divisible by 60)"
            )
            sys.exit(1)

    if args.verbose:
        logging.basicConfig(
            format="%(name)s %(levelname)s %(message)s", level=logging.DEBUG
        )

    debugger = InverterDebugger(
        args.inverter_host, args.slave, input_registers, holding_registers
    )
    await debugger.run()


class InverterDebugger:
    """Provides debugging tools that read and display inverter data at various levels."""

    def __init__(
        self,
        host: str,
        slave_address: int,
        input_registers: list[int],
        holding_registers: list[int],
    ) -> None:
        """Initialize the inverter client and perform a full refresh"""
        self.host = host
        self.slave_address = slave_address
        self.input_registers = input_registers
        self.holding_registers = holding_registers

    async def run(self) -> None:
        """
        Prints raw register data to stdout.

        This avoids decoding steps that can cause issues on unfamiliar hardware.
        """
        req: ReadRegistersRequest
        for base_register in self.input_registers:
            async with ThrowawayClient(self.host) as client:
                print(
                    f"Read IR slave_address=0x{self.slave_address:02x}, base_register={base_register}"
                )
                req = ReadInputRegistersRequest(  # type: ignore[no-untyped-call]
                    slave_address=self.slave_address,
                    base_register=base_register,
                    register_count=60,
                )
                await self._execute_request(client, req)

        for base_register in self.holding_registers:
            async with ThrowawayClient(self.host) as client:
                print(
                    f"Read HR slave_address=0x{self.slave_address:02x}, base_register={base_register}"
                )
                req = ReadHoldingRegistersRequest(  # type: ignore[no-untyped-call]
                    slave_address=self.slave_address,
                    base_register=base_register,
                    register_count=60,
                )
                await self._execute_request(client, req)

    async def _execute_request(
        self, client: Client, request: ReadRegistersRequest
    ) -> None:
        try:
            response = await client.send_request_and_await_response(
                request, timeout=1, retries=0
            )
        except asyncio.TimeoutError:
            print("Request timed out")
            return

        if isinstance(response, ReadRegistersResponse):
            print("Successfully received response:")
            self._pretty_print_registers(
                response.register_values, request.base_register
            )
        else:
            print(f"Unexpected response: {response}")

    @staticmethod
    def _pretty_print_registers(registers: list[int], base_register: int) -> None:
        registers_per_row = 10

        print(f"    | {" | ".join(f"{i}   " for i in range(10))}")

        for row in range(6):
            first_register = row * registers_per_row
            row_registers = registers[first_register : first_register + 10]
            print(
                f"{row*registers_per_row + base_register:3} | {" | ".join(f"{reg:04x}" for reg in row_registers)}"
            )


class ThrowawayClient:
    def __init__(self, host: str):
        self.client = Client(host, 8899)

    async def __aenter__(self) -> Client:
        await self.client.connect()
        return self.client

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        await self.client.close()


if __name__ == "__main__":
    asyncio.run(main())
