"""Unit tests for entity value mapping onto the givenergy-modbus library.

These focus on the parts of the integration most exposed to upstream field renames:
the sensor register lookup and the battery model lookup. They construct entities
against a mocked coordinator, so no inverter (real or simulated) is contacted.
"""

from unittest.mock import MagicMock

from givenergy_modbus.model.inverter import Model

from custom_components.givenergy_local.entity import BatteryEntity
from custom_components.givenergy_local.sensor import (
    InverterBasicSensor,
    MappedSensorEntityDescription,
)


def _coordinator_with_inverter(**model_dump: object) -> MagicMock:
    """Build a mock coordinator whose inverter exposes the given register values."""
    coordinator = MagicMock()
    coordinator.data.inverter.serial_number = "SD12345678"
    coordinator.data.inverter.model_dump.return_value = dict(model_dump)
    return coordinator


def test_inverter_sensor_prefers_ge_modbus_key() -> None:
    """A renamed register is read via ge_modbus_key, not the stable entity key."""
    coordinator = _coordinator_with_inverter(t_battery=21, temp_battery=999)
    description = MappedSensorEntityDescription(
        key="temp_battery",
        name="Battery Temperature",
        ge_modbus_key="t_battery",
    )

    sensor = InverterBasicSensor(coordinator, MagicMock(), description)

    # Value comes from the upstream field name, and the unique_id keeps the old key
    # so existing installations don't lose entity history.
    assert sensor.native_value == 21
    assert sensor.unique_id == "SD12345678_temp_battery"


def test_inverter_sensor_falls_back_to_key() -> None:
    """A plain description without ge_modbus_key still looks up by its key."""
    coordinator = _coordinator_with_inverter(e_pv_total=1234)
    description = MappedSensorEntityDescription(
        key="e_pv_total", name="PV Energy Total"
    )

    sensor = InverterBasicSensor(coordinator, MagicMock(), description)

    assert sensor.native_value == 1234


def test_battery_model_lookup() -> None:
    """The battery model name is resolved from the design capacity register."""
    coordinator = MagicMock()
    battery = coordinator.data.batteries.__getitem__.return_value
    battery.serial_number = "BAT01"
    battery.cap_design2 = 102

    entity = BatteryEntity(coordinator, MagicMock(), battery_id=0)

    assert entity.battery_model == "Giv-Bat 5.2"


def test_battery_model_lookup_unknown_capacity() -> None:
    """An unrecognised design capacity is reported with its raw Ah value."""
    coordinator = MagicMock()
    battery = coordinator.data.batteries.__getitem__.return_value
    battery.serial_number = "BAT01"
    battery.cap_design2 = 999

    entity = BatteryEntity(coordinator, MagicMock(), battery_id=0)

    assert entity.battery_model == "Unknown (999Ah)"


def test_model_descriptions_cover_known_models() -> None:
    """Every model the entity layer describes maps to a real upstream enum member."""
    from custom_components.givenergy_local.entity import _MODEL_DESCRIPTIONS

    for model in _MODEL_DESCRIPTIONS:
        assert isinstance(model, Model)
