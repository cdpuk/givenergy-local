# type: ignore  # shut up mypy, it seems to struggle with this file
import datetime
import logging
from enum import Enum
from typing import Tuple
import math

from pydantic import root_validator

from givenergy_modbus.model import GivEnergyBaseModel

_logger = logging.getLogger(__package__)


class UnknownModelError(Exception):
    """Raised when encountering an unknown model."""


class Model(str, Enum):
    """Known models of inverters."""

    AC = 'AC'
    Hybrid = 'Hybrid'
    EMS = 'EMS'
    Gateway = 'Gateway'
    AllinOne = "All in One"

    __dtc_to_models_lut__ = {
        2: Hybrid,
        3: AC,
        4: Hybrid,
        5: EMS,
        6: AC,
        7: Gateway,
        8: AllinOne,
    }

    @classmethod
    def from_device_type_code(cls, device_type_code: str):
        """Return the appropriate model from a given serial number."""
        prefix = int(device_type_code[0])
        if prefix in cls.__dtc_to_models_lut__:
            return cls.__dtc_to_models_lut__[prefix]
        else:
            # raise UnknownModelError(f"Cannot determine model number from serial number {serial_number}")
            return 'Unknown'    

class Phase(str, Enum):
    """Determine number of Phases."""

    OnePhase= "Single Phase",
    ThreePhase= "Three Phase",

    __dtc_to_phases_lut__ = {
        2: OnePhase,
        3: OnePhase,
        4: ThreePhase,
        5: OnePhase,
        6: ThreePhase,
        7: OnePhase,
        8: OnePhase,
    }

    @classmethod
    def from_device_type_code(cls, device_type_code: str):
        """Return the appropriate model from a given serial number."""
        prefix = int(device_type_code[0])
        if prefix in cls.__dtc_to_phases_lut__:
            return cls.__dtc_to_phases_lut__[prefix]
        else:
            # raise UnknownModelError(f"Cannot determine model number from serial number {serial_number}")
            return 'Unknown'   

class InvertorPower(str, Enum):
    """Map Invertor max power"""
    __dtc_to_power_lut__ = {
        '2001': 5000,
        '2002': 4600,
        '2003': 3600,
        '3001': 3000,
        '3002': 3600,
        '4001': 6000,
        '4002': 8000,
        '4003': 10000,
        '4004': 11000,
        '8001': 6000
    }
    @classmethod
    def from_dtc_power(cls, dtc: str):
        """Return the appropriate model from a given serial number."""
        if dtc in cls.__dtc_to_power_lut__:
            return cls.__dtc_to_power_lut__[dtc]
        else:
            return 0


class Generation(str, Enum):
    """Known Generations"""
    Gen1 = 'Gen 1'
    Gen2 = 'Gen 2'
    Gen3 = 'Gen 3'

    __dtc_to_models_lut__ = {
        3: Gen3,
        8: Gen2,
        9: Gen2,
    }

    @classmethod
    def from_fw_version(cls, firmware_version: str):
        """Return the appropriate model from a given serial number."""
        genint=math.floor(int(firmware_version)/100) 
        if genint in cls.__dtc_to_models_lut__:
            return cls.__dtc_to_models_lut__[genint]
        else:
            return cls.Gen1


class Inverter(GivEnergyBaseModel):
    """Structured format for all inverter attributes."""

    # Installation details
    inverter_serial_number: str
    device_type_code: str
    inverter_module: int
    dsp_firmware_version: int
    arm_firmware_version: int
    usb_device_inserted: int
    select_arm_chip: bool
    meter_type: int
    reverse_115_meter_direct: bool
    reverse_418_meter_direct: bool
    enable_drm_rj45_port: bool
    ct_adjust: int
    enable_buzzer: bool

    num_mppt: int
    num_phases: int
    enable_ammeter: bool
    p_grid_port_max_output: int
    enable_60hz_freq_mode: bool
    inverter_modbus_address: int
    modbus_version: float

    pv1_voltage_adjust: int
    pv2_voltage_adjust: int
    grid_r_voltage_adjust: int
    grid_s_voltage_adjust: int
    grid_t_voltage_adjust: int
    grid_power_adjust: int
    battery_voltage_adjust: int
    pv1_power_adjust: int
    pv2_power_adjust: int

    system_time: datetime.datetime
    active_power_rate: int
    reactive_power_rate: int
    power_factor: int
    inverter_state: Tuple[int, int]
    inverter_start_time: int
    inverter_restart_delay_time: int

    # Fault conditions
    dci_1_i: float
    dci_1_time: int
    dci_2_i: float
    dci_2_time: int
    f_ac_high_c: float
    f_ac_high_in: float
    f_ac_high_in_time: int
    f_ac_high_out: float
    f_ac_high_out_time: int
    f_ac_low_c: float
    f_ac_low_in: float
    f_ac_low_in_time: int
    f_ac_low_out: float
    f_ac_low_out_time: int
    gfci_1_i: float
    gfci_1_time: int
    gfci_2_i: float
    gfci_2_time: int
    v_ac_high_c: float
    v_ac_high_in: float
    v_ac_high_in_time: int
    v_ac_high_out: float
    v_ac_high_out_time: int
    v_ac_low_c: float
    v_ac_low_in: float
    v_ac_low_in_time: int
    v_ac_low_out: float
    v_ac_low_out_time: int

    # Battery configuration
    first_battery_serial_number: str
    first_battery_bms_firmware_version: int
    enable_bms_read: bool
    battery_type: int
    battery_nominal_capacity: float
    enable_auto_judge_battery_type: bool
    v_pv_input_start: float
    v_battery_under_protection_limit: float
    v_battery_over_protection_limit: float

    enable_discharge: bool
    enable_charge: bool
    enable_charge_target: bool
    battery_power_mode: int
    soc_force_adjust: int

    charge_slot_1: Tuple[datetime.time, datetime.time]
    charge_slot_2: Tuple[datetime.time, datetime.time]
    charge_slot_3: Tuple[datetime.time, datetime.time]
    charge_slot_4: Tuple[datetime.time, datetime.time]
    charge_slot_5: Tuple[datetime.time, datetime.time]
    charge_slot_6: Tuple[datetime.time, datetime.time]
    charge_slot_7: Tuple[datetime.time, datetime.time]
    charge_slot_8: Tuple[datetime.time, datetime.time]
    charge_slot_9: Tuple[datetime.time, datetime.time]
    charge_slot_10: Tuple[datetime.time, datetime.time]
    discharge_slot_1: Tuple[datetime.time, datetime.time]
    discharge_slot_2: Tuple[datetime.time, datetime.time]
    discharge_slot_3: Tuple[datetime.time, datetime.time]
    discharge_slot_4: Tuple[datetime.time, datetime.time]
    discharge_slot_5: Tuple[datetime.time, datetime.time]
    discharge_slot_6: Tuple[datetime.time, datetime.time]
    discharge_slot_7: Tuple[datetime.time, datetime.time]
    discharge_slot_8: Tuple[datetime.time, datetime.time]
    discharge_slot_9: Tuple[datetime.time, datetime.time]
    discharge_slot_10: Tuple[datetime.time, datetime.time]
    charge_and_discharge_soc: Tuple[int, int]

    battery_low_force_charge_time: int
    battery_soc_reserve: int
    battery_charge_limit: int
    battery_discharge_limit: int
    island_check_continue: int
    battery_discharge_min_power_reserve: int
    charge_target_soc: int
    charge_target_soc_1: int
    charge_target_soc_2: int
    charge_target_soc_3: int
    charge_target_soc_4: int
    charge_target_soc_5: int
    charge_target_soc_6: int
    charge_target_soc_7: int
    charge_target_soc_8: int
    charge_target_soc_9: int
    charge_target_soc_10: int
    discharge_target_soc_1: int
    discharge_target_soc_2: int
    discharge_target_soc_3: int
    discharge_target_soc_4: int
    discharge_target_soc_5: int
    discharge_target_soc_6: int
    discharge_target_soc_7: int
    discharge_target_soc_8: int
    discharge_target_soc_9: int
    discharge_target_soc_10: int

#    charge_soc_stop_2: int
#    discharge_soc_stop_2: int
#    charge_soc_stop_1: int
#    discharge_soc_stop_1: int

    local_control_mode: int
    pv_input_mode: int
    battery_pause_mode: int
    battery_pause_slot: Tuple[datetime.time, datetime.time]

    # InputRegisters
    inverter_status: int
    system_mode: int
    inverter_countdown: int
    charge_status: int
    battery_percent: int
    charger_warning_code: int
    work_time_total: int
    fault_code: int

    e_battery_charge_day: float
    e_battery_charge_day_2: float
    e_battery_charge_total: float
    e_battery_discharge_day: float
    e_battery_discharge_day_2: float
    e_battery_discharge_total: float
    e_battery_throughput_total: float
    e_discharge_year: float
    e_inverter_out_day: float
    e_inverter_out_total: float
    e_grid_out_day: float
    e_grid_in_day: float
    e_grid_in_total: float
    e_grid_out_total: float
    e_inverter_in_day: float
    e_inverter_in_total: float
    e_pv1_day: float
    e_pv2_day: float
    e_solar_diverter: float
    f_ac1: float
    f_eps_backup: float
    i_ac1: float
    i_battery: float
    i_grid_port: float
    i_pv1: float
    i_pv2: float
    p_battery: int
    p_eps_backup: int
    p_grid_apparent: int
    p_grid_out: int
    p_inverter_out: int
    p_load_demand: int
    p_pv1: int
    p_pv2: int
    e_pv_total: float
    pf_inverter_out: float
    temp_battery: float
    temp_charger: float
    temp_inverter_heatsink: float
    v_ac1: float
    v_battery: float
    v_eps_backup: float
    v_highbrigh_bus: int
    v_n_bus: float
    v_p_bus: float
    v_pv1: float
    v_pv2: float

    @root_validator
    def compute_model(cls, values) -> dict:
        """Computes the inverter model from the device type code."""
        values['inverter_model'] = Model.from_device_type_code(values['device_type_code'])
        return values

    @root_validator
    def compute_phases(cls, values) -> dict:
        """Computes the number of phases from the device type code."""
        values['inverter_phases'] = Phase.from_device_type_code(values['device_type_code'])
        return values

    @root_validator
    def compute_generation(cls, values) -> dict:
        """Computes the inverter model from the firmware version."""
        values['inverter_generation'] = Generation.from_fw_version(values['arm_firmware_version'])
        return values

    @root_validator
    def compute_maxpower(cls, values) -> dict:
        """Computes the inverter model from the firmware version."""
        values['inverter_maxpower'] = InvertorPower.from_dtc_power(values['device_type_code'])
        return values

    @root_validator
    def compute_firmware_version(cls, values) -> dict:
        """Virtual method to inject a firmware version similar to what the dashboard shows."""
        values['firmware_version'] = f'D0.{values["dsp_firmware_version"]}-A0.{values["arm_firmware_version"]}'
        return values
