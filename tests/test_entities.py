from unittest.mock import MagicMock

from givenergy_modbus.model.inverter import Model

from custom_components.givenergy_local.entity import BatteryEntity


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
