from enum import IntEnum, StrEnum
import math

from pydantic.v1 import BaseConfig, create_model

from custom_components.givenergy_local.givenergy_modbus.model.register import HR, IR
from custom_components.givenergy_local.givenergy_modbus.model.register import (
    Converter as C,
)
from custom_components.givenergy_local.givenergy_modbus.model.register import (
    RegisterDefinition as Def,
)
from custom_components.givenergy_local.givenergy_modbus.model.register import (
    RegisterGetter,
)


class Model(StrEnum):
    """Known models of inverters."""

    HYBRID = "2"
    AC = "3"
    HYBRID_3PH = "4"
    AC_3PH = "6"
    EMS = "5"
    GATEWAY = "7"
    ALL_IN_ONE = "8"

    @classmethod
    def _missing_(cls, value):
        """Pick model from the first digit of the device type code."""
        return cls(value[0])


class Generation(StrEnum):
    """Known Generations"""

    GEN1 = "Gen 1"
    GEN2 = "Gen 2"
    GEN3 = "Gen 3"

    @classmethod
    def _missing_(cls, value: int) -> "Generation":  # type: ignore[override]
        """Pick generation from the arm_firmware_version."""
        arm_firmware_version_to_gen = {
            3: cls.GEN3,
            8: cls.GEN2,
            9: cls.GEN2,
        }
        key = math.floor(int(value) / 100)
        if gen := arm_firmware_version_to_gen.get(key):
            return gen
        else:
            return cls.GEN1


class UsbDevice(IntEnum):
    """USB devices that can be inserted into inverters."""

    NONE = 0
    WIFI = 1
    DISK = 2


class BatteryPowerMode(IntEnum):
    """Battery discharge strategy."""

    EXPORT = 0
    SELF_CONSUMPTION = 1


class BatteryCalibrationStage(IntEnum):
    """Battery calibration stages."""

    OFF = 0
    DISCHARGE = 1
    SET_LOWER_LIMIT = 2
    CHARGE = 3
    SET_UPPER_LIMIT = 4
    BALANCE = 5
    SET_FULL_CAPACITY = 6
    FINISH = 7


class MeterType(IntEnum):
    """Installed meter type."""

    CT_OR_EM418 = 0
    EM115 = 1


class BatteryType(IntEnum):
    """Installed battery type."""

    LEAD_ACID = 0
    LITHIUM = 1


class BatteryPauseMode(IntEnum):
    """Battery pause mode."""

    DISABLED = 0
    PAUSE_CHARGE = 1
    PAUSE_DISCHARGE = 2
    PAUSE_BOTH = 3


class PowerFactorFunctionModel(IntEnum):
    """Power Factor function model."""

    PF_1 = 0
    PF_BY_SET = 1
    DEFAULT_PF_LINE = 2
    USER_PF_LINE = 3
    UNDER_EXCITED_INDUCTIVE_REACTIVE_POWER = 4
    OVER_EXCITED_CAPACITIVE_REACTIVE_POWER = 5
    QV_MODEL = 6


class Status(IntEnum):
    """Inverter status."""

    WAITING = 0
    NORMAL = 1
    WARNING = 2
    FAULT = 3
    FLASHING_FIRMWARE_UPDATE = 4


class InverterRegisterGetter(RegisterGetter):
    """Structured format for all inverter attributes."""

    REGISTER_LUT = {
        #
        # Holding Registers, block 0-59
        #
        "device_type_code": Def(C.hex, None, HR(0)),
        "inverter_max_power": Def(C.hex, C.inverter_max_power, HR(0)),
        "model": Def(C.hex, Model, HR(0)),
        "module": Def(C.uint32, (C.hex, 8), HR(1), HR(2)),
        "num_mppt": Def((C.duint8, 0), None, HR(3)),
        "num_phases": Def((C.duint8, 1), None, HR(3)),
        # HR(4-6) unused
        "enable_ammeter": Def(C.bool, None, HR(7)),
        "first_battery_serial_number": Def(
            C.string, None, HR(8), HR(9), HR(10), HR(11), HR(12)
        ),
        "serial_number": Def(C.string, None, HR(13), HR(14), HR(15), HR(16), HR(17)),
        "first_battery_bms_firmware_version": Def(C.uint16, None, HR(18)),
        "dsp_firmware_version": Def(C.uint16, None, HR(19)),
        "enable_charge_target": Def(C.bool, None, HR(20)),
        "arm_firmware_version": Def(C.uint16, None, HR(21)),
        "generation": Def(C.uint16, Generation, HR(21)),
        "firmware_version": Def(C.firmware_version, None, HR(19), HR(21)),
        "usb_device_inserted": Def(C.uint16, UsbDevice, HR(22)),
        "select_arm_chip": Def(C.bool, None, HR(23)),
        "variable_address": Def(C.uint16, None, HR(24)),
        "variable_value": Def(C.uint16, None, HR(25)),
        "grid_port_max_power_output": Def(C.uint16, None, HR(26)),
        "battery_power_mode": Def(C.uint16, BatteryPowerMode, HR(27)),
        "enable_60hz_freq_mode": Def(C.bool, None, HR(28)),
        "battery_calibration_stage": Def(C.uint16, BatteryCalibrationStage, HR(29)),
        "modbus_address": Def(C.uint16, None, HR(30)),
        "charge_slot_2": Def(C.timeslot, None, HR(31), HR(32)),
        "user_code": Def(C.uint16, None, HR(33)),
        "modbus_version": Def(C.centi, (C.fstr, "0.2f"), HR(34)),
        "system_time": Def(
            C.datetime, None, HR(35), HR(36), HR(37), HR(38), HR(39), HR(40)
        ),
        "enable_drm_rj45_port": Def(C.bool, None, HR(41)),
        "enable_reversed_ct_clamp": Def(C.bool, None, HR(42)),
        "charge_soc": Def((C.duint8, 0), None, HR(43)),
        "discharge_soc": Def((C.duint8, 1), None, HR(43)),
        "discharge_slot_2": Def(C.timeslot, None, HR(44), HR(45)),
        "bms_firmware_version": Def(C.uint16, None, HR(46)),
        "meter_type": Def(C.uint16, MeterType, HR(47)),
        "enable_reversed_115_meter": Def(C.bool, None, HR(48)),
        "enable_reversed_418_meter": Def(C.bool, None, HR(49)),
        "active_power_rate": Def(C.uint16, None, HR(50)),
        "reactive_power_rate": Def(C.uint16, None, HR(51)),
        "power_factor": Def(C.uint16, None, HR(52)),  # /10_000 - 1
        "enable_inverter_auto_restart": Def((C.duint8, 0), C.bool, HR(53)),
        "enable_inverter": Def((C.duint8, 1), C.bool, HR(53)),
        "battery_type": Def(C.uint16, BatteryType, HR(54)),
        "battery_capacity": Def(C.uint16, None, HR(55)),
        "discharge_slot_1": Def(C.timeslot, None, HR(56), HR(57)),
        "enable_auto_judge_battery_type": Def(C.bool, None, HR(58)),
        "enable_discharge": Def(C.bool, None, HR(59)),
        #
        # Holding Registers, block 60-119
        #
        "v_pv_start": Def(C.uint16, C.deci, HR(60)),
        "start_countdown_timer": Def(C.uint16, None, HR(61)),
        "restart_delay_time": Def(C.uint16, None, HR(62)),
        # skip protection settings HR(63-93)
        "charge_slot_1": Def(C.timeslot, None, HR(94), HR(95)),
        "enable_charge": Def(C.bool, None, HR(96)),
        "battery_low_voltage_protection_limit": Def(C.uint16, C.centi, HR(97)),
        "battery_high_voltage_protection_limit": Def(C.uint16, C.centi, HR(98)),
        # skip voltage adjustment settings 99-107
        "battery_low_force_charge_time": Def(C.uint16, None, HR(108)),
        "enable_bms_read": Def(C.bool, None, HR(109)),
        "battery_soc_reserve": Def(C.uint16, None, HR(110)),
        "battery_charge_limit": Def(C.uint16, None, HR(111)),
        "battery_discharge_limit": Def(C.uint16, None, HR(112)),
        "enable_buzzer": Def(C.bool, None, HR(113)),
        "battery_discharge_min_power_reserve": Def(C.uint16, None, HR(114)),
        # 'island_check_continue': Def(C.uint16, None, HR(115)),
        "charge_target_soc": Def(
            C.uint16, None, HR(116)
        ),  # requires enable_charge_target
        "charge_soc_stop_2": Def(C.uint16, None, HR(117)),
        "discharge_soc_stop_2": Def(C.uint16, None, HR(118)),
        "charge_soc_stop_1": Def(C.uint16, None, HR(119)),
        #
        # Holding Registers, block 120-179
        #
        "discharge_soc_stop_1": Def(C.uint16, None, HR(120)),
        "enable_local_command_test": Def(C.bool, None, HR(121)),
        "power_factor_function_model": Def(C.uint16, PowerFactorFunctionModel, HR(122)),
        "frequency_load_limit_rate": Def(C.uint16, None, HR(123)),
        "enable_low_voltage_fault_ride_through": Def(C.bool, None, HR(124)),
        "enable_frequency_derating": Def(C.bool, None, HR(125)),
        "enable_above_6kw_system": Def(C.bool, None, HR(126)),
        "start_system_auto_test": Def(C.bool, None, HR(127)),
        "enable_spi": Def(C.bool, None, HR(128)),
        # skip PF configuration and protection settings 129-166
        "threephase_balance_mode": Def(C.uint16, None, HR(167)),
        "threephase_abc": Def(C.uint16, None, HR(168)),
        "threephase_balance_1": Def(C.uint16, None, HR(169)),
        "threephase_balance_2": Def(C.uint16, None, HR(170)),
        "threephase_balance_3": Def(C.uint16, None, HR(171)),
        # HR(172-174) unused
        "enable_battery_on_pv_or_grid": Def(C.bool, None, HR(175)),
        "debug_inverter": Def(C.uint16, None, HR(176)),
        "enable_ups_mode": Def(C.bool, None, HR(177)),
        "enable_g100_limit_switch": Def(C.bool, None, HR(178)),
        "enable_battery_cable_impedance_alarm": Def(C.bool, None, HR(179)),
        #
        # Holding Registers, block 180-239
        #
        "enable_standard_self_consumption_logic": Def(C.bool, None, HR(199)),
        "cmd_bms_flash_update": Def(C.bool, None, HR(200)),
        #
        # Holding Registers, block 300-359
        #
        "battery_pause_mode": Def(C.uint16, BatteryPauseMode, HR(318)),
        "battery_pause_slot_1": Def(C.timeslot, None, HR(319), HR(320)),
        #
        # Holding Registers, block 4080-4139
        #
        "pv_power_setting": Def(C.uint32, None, HR(4107), HR(4108)),
        "e_battery_discharge_total2": Def(C.uint32, None, HR(4109), HR(4110)),
        "e_battery_charge_total2": Def(C.uint32, None, HR(4111), HR(4112)),
        "e_battery_discharge_today": Def(C.uint16, None, HR(4113)),
        "e_battery_charge_today": Def(C.uint16, None, HR(4114)),
        #
        # Holding Registers, block 4140-4199
        #
        "e_inverter_export_total": Def(C.uint32, None, HR(4141), HR(4142)),
        #
        # Input Registers, block 0-59
        #
        "status": Def(C.uint16, Status, IR(0)),
        "v_pv1": Def(C.deci, None, IR(1)),
        "v_pv2": Def(C.deci, None, IR(2)),
        "v_p_bus": Def(C.deci, None, IR(3)),
        "v_n_bus": Def(C.deci, None, IR(4)),
        "v_ac1": Def(C.deci, None, IR(5)),
        "e_battery_throughput_total": Def(C.uint32, C.deci, IR(6), IR(7)),
        "i_pv1": Def(C.centi, None, IR(8)),
        "i_pv2": Def(C.centi, None, IR(9)),
        "i_ac1": Def(C.centi, None, IR(10)),
        "e_pv_total": Def(C.uint32, C.deci, IR(11), IR(12)),
        "f_ac1": Def(C.centi, None, IR(13)),
        "e_pv1_day": Def(C.deci, None, IR(17)),
        "p_pv1": Def(C.uint16, None, IR(18)),
        "e_pv2_day": Def(C.deci, None, IR(19)),
        "p_pv2": Def(C.uint16, None, IR(20)),
        "e_grid_out_total": Def(C.uint32, C.deci, IR(21), IR(22)),
        "e_solar_diverter": Def(C.deci, None, IR(23)),
        "p_inverter_out": Def(C.int16, None, IR(24)),
        "e_grid_out_day": Def(C.deci, None, IR(25)),
        "e_grid_in_day": Def(C.deci, None, IR(26)),
        "e_inverter_in_total": Def(C.uint32, C.deci, IR(27), IR(28)),
        "e_discharge_year": Def(C.deci, None, IR(29)),
        "p_grid_out": Def(C.int16, None, IR(30)),
        "p_eps_backup": Def(C.uint16, None, IR(31)),
        "e_grid_in_total": Def(C.uint32, C.deci, IR(32), IR(33)),
        "e_inverter_in_day": Def(C.deci, None, IR(35)),
        "e_battery_charge_day": Def(C.deci, None, IR(36)),
        "e_battery_discharge_day": Def(C.deci, None, IR(37)),
        "inverter_countdown": Def(C.uint16, None, IR(38)),
        # FAULT_CODE_H = (39, {'type': T_BITFIELD})
        # FAULT_CODE_L = (40, {'type': T_BITFIELD})
        "temp_inverter_heatsink": Def(C.deci, None, IR(41)),
        "p_load_demand": Def(C.uint16, None, IR(42)),
        "p_grid_apparent": Def(C.uint16, None, IR(43)),
        "e_inverter_out_day": Def(C.deci, None, IR(44)),
        "e_inverter_out_total": Def(C.uint32, C.deci, IR(45), IR(46)),
        "work_time_total": Def(C.uint32, None, IR(47), IR(48)),
        "system_mode": Def(C.uint16, None, IR(49)),
        "v_battery": Def(C.centi, None, IR(50)),
        "i_battery": Def(C.int16, C.centi, None, IR(51)),
        "p_battery": Def(C.int16, None, IR(52)),
        "v_eps_backup": Def(C.deci, None, IR(53)),
        "f_eps_backup": Def(C.centi, None, IR(54)),
        "temp_charger": Def(C.deci, None, IR(55)),
        "temp_battery": Def(C.deci, None, IR(56)),
        "i_grid_port": Def(C.centi, None, IR(58)),
        "battery_percent": Def(C.uint16, None, IR(59)),
    }

    # @computed('p_pv')
    # def compute_p_pv(p_pv1: int, p_pv2: int, **kwargs) -> int:
    #     """Computes the discharge slot 2."""
    #     return p_pv1 + p_pv2

    # @computed('e_pv_day')
    # def compute_e_pv_day(e_pv1_day: float, e_pv2_day: float, **kwargs) -> float:
    #     """Computes the discharge slot 2."""
    #     return e_pv1_day + e_pv2_day


class InverterConfig(BaseConfig):
    """Pydantic configuration for the Inverter class."""

    orm_mode = True
    getter_dict = InverterRegisterGetter


Inverter = create_model(
    "Inverter", __config__=InverterConfig, **InverterRegisterGetter.to_fields()
)  # type: ignore[call-overload]
