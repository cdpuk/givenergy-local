from unittest.mock import MagicMock

from givenergy_modbus.model.inverter import Model

from custom_components.givenergy_local.sensor import (
    ConsumptionTodaySensor,
    ConsumptionTotalSensor,
    InverterBasicSensor,
    MappedSensorEntityDescription,
    PVEnergyTodaySensor,
    PVPowerSensor,
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


def test_inverter_sensor_falls_back_to_ge_modbus_fallback_key() -> None:
    """When the primary key is None, the fallback key is used instead."""
    coordinator = _coordinator_with_inverter(
        e_battery_charge_today=None, e_battery_charge_today_alt1=1.23
    )
    description = MappedSensorEntityDescription(
        key="e_battery_charge_day",
        name="Battery Charge Today",
        ge_modbus_key="e_battery_charge_today",
        ge_modbus_fallback_key="e_battery_charge_today_alt1",
    )

    sensor = InverterBasicSensor(coordinator, MagicMock(), description)

    assert sensor.native_value == 1.23


def test_inverter_sensor_prefers_ge_modbus_key_over_fallback() -> None:
    """The primary key wins when both it and the fallback have values."""
    coordinator = _coordinator_with_inverter(
        e_battery_charge_today=4.56, e_battery_charge_today_alt1=1.23
    )
    description = MappedSensorEntityDescription(
        key="e_battery_charge_day",
        name="Battery Charge Today",
        ge_modbus_key="e_battery_charge_today",
        ge_modbus_fallback_key="e_battery_charge_today_alt1",
    )

    sensor = InverterBasicSensor(coordinator, MagicMock(), description)

    assert sensor.native_value == 4.56


def _coordinator_with_inverter_attrs(**attrs: object) -> MagicMock:
    """Build a mock coordinator whose inverter exposes the given attributes."""
    coordinator = MagicMock()
    coordinator.data.inverter.serial_number = "SD12345678"
    coordinator.data.inverter.configure_mock(**attrs)
    return coordinator


_CONSUMPTION_TODAY_ATTRS = {
    "model": Model.HYBRID,
    "e_pv_generation_today": 10.0,
    "e_ac_charge_today": 1.0,
    "e_grid_in_day": 3.0,
    "e_grid_out_day": 2.0,
}


def test_consumption_today_computes_net_consumption() -> None:
    """Consumption Today sums net inverter output and net grid import."""
    coordinator = _coordinator_with_inverter_attrs(**_CONSUMPTION_TODAY_ATTRS)

    sensor = ConsumptionTodaySensor(coordinator, MagicMock(), MagicMock())

    # 10 - 1 + 3 - 2
    assert sensor.native_value == 10.0


def test_consumption_today_skips_update_when_value_missing() -> None:
    """A temporarily missing register makes the sensor skip the update, not crash."""
    attrs = {**_CONSUMPTION_TODAY_ATTRS, "e_pv_generation_today": None}
    coordinator = _coordinator_with_inverter_attrs(**attrs)

    sensor = ConsumptionTodaySensor(coordinator, MagicMock(), MagicMock())

    assert sensor.native_value is None


def test_consumption_total_skips_update_when_value_missing() -> None:
    """A temporarily missing register makes the sensor skip the update, not crash."""
    coordinator = _coordinator_with_inverter_attrs(
        model=Model.HYBRID,
        e_pv_generation_total=None,
        e_inverter_in_total=1.0,
        e_grid_in_total=3.0,
        e_grid_out_total=2.0,
    )

    sensor = ConsumptionTotalSensor(coordinator, MagicMock(), MagicMock())

    assert sensor.native_value is None


def test_pv_energy_today_sums_both_strings() -> None:
    """PV Energy Today is the sum of both PV string readings."""
    coordinator = _coordinator_with_inverter_attrs(e_pv1_day=1.5, e_pv2_day=2.5)

    sensor = PVEnergyTodaySensor(coordinator, MagicMock(), MagicMock())

    assert sensor.native_value == 4.0


def test_pv_energy_today_skips_update_when_value_missing() -> None:
    """A temporarily missing register makes the sensor skip the update, not crash."""
    coordinator = _coordinator_with_inverter_attrs(e_pv1_day=1.5, e_pv2_day=None)

    sensor = PVEnergyTodaySensor(coordinator, MagicMock(), MagicMock())

    assert sensor.native_value is None


def test_pv_power_sums_both_strings() -> None:
    """PV Power is the sum of both PV string readings."""
    coordinator = _coordinator_with_inverter_attrs(p_pv1=100, p_pv2=200)

    sensor = PVPowerSensor(coordinator, MagicMock(), MagicMock())

    assert sensor.native_value == 300


def test_pv_power_skips_update_when_value_missing() -> None:
    """A temporarily missing register makes the sensor skip the update, not crash."""
    coordinator = _coordinator_with_inverter_attrs(p_pv1=None, p_pv2=200)

    sensor = PVPowerSensor(coordinator, MagicMock(), MagicMock())

    assert sensor.native_value is None
