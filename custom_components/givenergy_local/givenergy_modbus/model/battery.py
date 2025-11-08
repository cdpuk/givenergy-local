from enum import IntEnum

try:
    from pydantic.v1 import BaseConfig, create_model
except ImportError:
    from pydantic import BaseConfig, create_model

from custom_components.givenergy_local.givenergy_modbus.model.register import IR
from custom_components.givenergy_local.givenergy_modbus.model.register import (
    Converter as DT,
)
from custom_components.givenergy_local.givenergy_modbus.model.register import (
    RegisterDefinition as Def,
)
from custom_components.givenergy_local.givenergy_modbus.model.register import (
    RegisterGetter,
)


class UsbDevice(IntEnum):
    """USB devices that can be inserted into batteries."""

    NONE = 0
    DISK = 8


class BatteryRegisterGetter(RegisterGetter):
    """Structured format for all battery attributes."""

    REGISTER_LUT = {
        # Input Registers, block 60-119
        "v_cell_01": Def(DT.milli, None, IR(60)),
        "v_cell_02": Def(DT.milli, None, IR(61)),
        "v_cell_03": Def(DT.milli, None, IR(62)),
        "v_cell_04": Def(DT.milli, None, IR(63)),
        "v_cell_05": Def(DT.milli, None, IR(64)),
        "v_cell_06": Def(DT.milli, None, IR(65)),
        "v_cell_07": Def(DT.milli, None, IR(66)),
        "v_cell_08": Def(DT.milli, None, IR(67)),
        "v_cell_09": Def(DT.milli, None, IR(68)),
        "v_cell_10": Def(DT.milli, None, IR(69)),
        "v_cell_11": Def(DT.milli, None, IR(70)),
        "v_cell_12": Def(DT.milli, None, IR(71)),
        "v_cell_13": Def(DT.milli, None, IR(72)),
        "v_cell_14": Def(DT.milli, None, IR(73)),
        "v_cell_15": Def(DT.milli, None, IR(74)),
        "v_cell_16": Def(DT.milli, None, IR(75)),
        "t_cells_01_04": Def(DT.deci, None, IR(76)),
        "t_cells_05_08": Def(DT.deci, None, IR(77)),
        "t_cells_09_12": Def(DT.deci, None, IR(78)),
        "t_cells_13_16": Def(DT.deci, None, IR(79)),
        "v_cells_sum": Def(DT.milli, None, IR(80)),
        "t_bms_mosfet": Def(DT.deci, None, IR(81)),
        "v_out": Def(DT.uint32, DT.milli, IR(82), IR(83)),
        "cap_calibrated": Def(DT.uint32, DT.centi, IR(84), IR(85)),
        "cap_design": Def(DT.uint32, DT.centi, IR(86), IR(87)),
        "cap_remaining": Def(DT.uint32, DT.centi, IR(88), IR(89)),
        "status_1": Def((DT.duint8, 0), None, IR(90)),
        "status_2": Def((DT.duint8, 1), None, IR(90)),
        "status_3": Def((DT.duint8, 0), None, IR(91)),
        "status_4": Def((DT.duint8, 1), None, IR(91)),
        "status_5": Def((DT.duint8, 0), None, IR(92)),
        "status_6": Def((DT.duint8, 1), None, IR(92)),
        "status_7": Def((DT.duint8, 0), None, IR(93)),
        "warning_1": Def((DT.duint8, 0), None, IR(94)),
        "warning_2": Def((DT.duint8, 1), None, IR(94)),
        # IR(95) unused
        "num_cycles": Def(DT.uint16, None, IR(96)),
        "num_cells": Def(DT.uint16, None, IR(97)),
        "bms_firmware_version": Def(DT.uint16, None, IR(98)),
        # IR(99) unused
        "soc": Def(DT.uint16, None, IR(100)),
        "cap_design2": Def(DT.uint32, DT.centi, IR(101), IR(102)),
        "t_max": Def(DT.deci, None, IR(103)),
        "t_min": Def(DT.deci, None, IR(104)),
        "e_discharge_total": Def(DT.deci, None, IR(105)),
        "e_charge_total": Def(DT.deci, None, IR(106)),
        # IR(107-109) unused
        "serial_number": Def(
            DT.string, None, IR(110), IR(111), IR(112), IR(113), IR(114)
        ),
        "usb_device_inserted": Def(DT.uint16, UsbDevice, IR(115)),
        # IR(116-119) unused
    }


class BatteryConfig(BaseConfig):
    """Pydantic configuration for the Battery class."""

    orm_mode = True
    getter_dict = BatteryRegisterGetter


_Battery = create_model(
    "Battery", __config__=BatteryConfig, **BatteryRegisterGetter.to_fields()
)  # type: ignore[call-overload]


class Battery(_Battery):  # type: ignore[misc,valid-type]
    """Add some utility methods to the base pydantic class."""

    def is_valid(self) -> bool:
        """Try to detect if a battery exists based on its attributes."""
        return self.serial_number not in (
            None,
            "",
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            "          ",
        )
