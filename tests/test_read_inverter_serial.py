"""The config flow's validation must always close its connection to the inverter."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.givenergy_local.config_flow import read_inverter_serial
from custom_components.givenergy_local.const import CONF_HOST

_SERIAL = "AB123456"


def _client(**overrides) -> SimpleNamespace:
    values = {
        "connect": AsyncMock(),
        "detect": AsyncMock(),
        "load_config": AsyncMock(),
        "close": AsyncMock(),
        "plant": SimpleNamespace(inverter=SimpleNamespace(serial_number=_SERIAL)),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _patched(client):
    return patch(
        "custom_components.givenergy_local.config_flow.Client", return_value=client
    )


async def test_returns_serial_and_closes():
    client = _client()
    with _patched(client):
        assert await read_inverter_serial({CONF_HOST: "inverter"}) == _SERIAL
    client.close.assert_awaited_once()


@pytest.mark.parametrize("failing_step", ["connect", "detect", "load_config"])
async def test_closes_when_a_step_fails(failing_step):
    client = _client(**{failing_step: AsyncMock(side_effect=OSError("boom"))})
    with _patched(client), pytest.raises(OSError, match="boom"):
        await read_inverter_serial({CONF_HOST: "inverter"})
    client.close.assert_awaited_once()


async def test_closes_when_validation_times_out():
    async def never_finishes():
        await asyncio.sleep(3600)

    client = _client(detect=never_finishes)
    with (
        _patched(client),
        patch(
            "custom_components.givenergy_local.config_flow._VALIDATION_TIMEOUT", 0.01
        ),
        pytest.raises(TimeoutError),
    ):
        await read_inverter_serial({CONF_HOST: "inverter"})
    client.close.assert_awaited_once()


async def test_close_failure_does_not_mask_the_original_error():
    client = _client(
        detect=AsyncMock(side_effect=OSError("detect failed")),
        close=AsyncMock(side_effect=OSError("close failed")),
    )
    with _patched(client), pytest.raises(OSError, match="detect failed"):
        await read_inverter_serial({CONF_HOST: "inverter"})
