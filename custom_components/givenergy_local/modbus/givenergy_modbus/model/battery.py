from typing import Tuple

from givenergy_modbus.model import GivEnergyBaseModel


class Battery(GivEnergyBaseModel):
    """Structured format for all inverter attributes."""

    battery_serial_number: str
    v_battery_cell_01: float
    v_battery_cell_02: float
    v_battery_cell_03: float
    v_battery_cell_04: float
    v_battery_cell_05: float
    v_battery_cell_06: float
    v_battery_cell_07: float
    v_battery_cell_08: float
    v_battery_cell_09: float
    v_battery_cell_10: float
    v_battery_cell_11: float
    v_battery_cell_12: float
    v_battery_cell_13: float
    v_battery_cell_14: float
    v_battery_cell_15: float
    v_battery_cell_16: float
    temp_battery_cells_1: float
    temp_battery_cells_2: float
    temp_battery_cells_3: float
    temp_battery_cells_4: float
    v_battery_cells_sum: float
    temp_bms_mos: float
    v_battery_out: float
    battery_full_capacity: float
    battery_design_capacity: float
    battery_remaining_capacity: float
    battery_status_1_2: Tuple[int, int]
    battery_status_3_4: Tuple[int, int]
    battery_status_5_6: Tuple[int, int]
    battery_status_7: Tuple[int, int]
    battery_warning_1_2: Tuple[int, int]
    battery_num_cycles: int
    battery_num_cells: int
    bms_firmware_version: int
    battery_soc: int
    battery_design_capacity_2: float
    temp_battery_max: float
    temp_battery_min: float
    usb_inserted: bool
    e_battery_charge_total_2: float
    e_battery_discharge_total_2: float
