from datetime import datetime
from typing import Any

from pydantic.utils import GetterDict


class RegisterGetter(GetterDict):
    """GetterDict implementation to consolidate register data structures."""

    def get(self, key: Any, default: Any = None) -> Any:
        """Getter that computes some virtual attributes."""
        if key == "inverter_serial_number":
            return ''.join(
                [
                    self.get('inverter_serial_number_1_2'),
                    self.get('inverter_serial_number_3_4'),
                    self.get('inverter_serial_number_5_6'),
                    self.get('inverter_serial_number_7_8'),
                    self.get('inverter_serial_number_9_10'),
                ]
            )
        if key in ["num_mppt", 'num_phases']:
            obj = self.get('num_mppt_and_num_phases')
            if obj == default:
                return default
            elif key == "num_mppt":
                return obj[0]
            return obj[1]
        if key == "battery_serial_number":
            return ''.join(
                [
                    self.get('battery_serial_number_1_2'),
                    self.get('battery_serial_number_3_4'),
                    self.get('battery_serial_number_5_6'),
                    self.get('battery_serial_number_7_8'),
                    self.get('battery_serial_number_9_10'),
                ]
            )
        if key == "first_battery_serial_number":
            return ''.join(
                [
                    self.get('first_battery_serial_number_1_2'),
                    self.get('first_battery_serial_number_3_4'),
                    self.get('first_battery_serial_number_5_6'),
                    self.get('first_battery_serial_number_7_8'),
                    self.get('first_battery_serial_number_9_10'),
                ]
            )
        # Some special cases first
        if key == "system_time":
            return datetime(
                self.get('system_time_year') + 2000,
                self.get('system_time_month'),
                self.get('system_time_day'),
                self.get('system_time_hour'),
                self.get('system_time_minute'),
                self.get('system_time_second'),
            )

        if key in ('charge_slot_1', 'charge_slot_2', 'charge_slot_3', 'charge_slot_4', 'charge_slot_5', 'charge_slot_6', 'charge_slot_7', 'charge_slot_8', 'charge_slot_9', 'charge_slot_10', 'discharge_slot_1', 'discharge_slot_2', 'discharge_slot_3', 'discharge_slot_4', 'discharge_slot_5', 'discharge_slot_6', 'discharge_slot_7', 'discharge_slot_8', 'discharge_slot_9', 'discharge_slot_10','battery_pause_slot'):
            return self.get(f'{key}_start'), self.get(f'{key}_end')

        if key == "inverter_firmware_version":
            return f'D0.{self.get("dsp_firmware_version")}-A0.{self.get("arm_firmware_version")}'

        # if key == 'modbus_version':
        #     return f'{self.get("modbus_version"):0.2f}'

        return getattr(self._obj, key, default)
