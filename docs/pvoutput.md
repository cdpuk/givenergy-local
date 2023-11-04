# PVOutput upload

This integration provides data that can be used to upload system stats to [pvoutput.org](pvoutput.org).

Open your Home Assistant `configuration.yaml` file and add the following:

```yaml
shell_command:
  pvoutputcurl: >
    curl -d "d={{now().strftime("%Y%m%d")}}"
         -d "t={{now().strftime("%H:%M")}}"
         -d "v1={{ (states('sensor.pv_energy_today') | float * 1000)  | int }}"
         -d "v2={{ states('sensor.pv_power') }}"
         -d "v6={{ states('sensor.grid_voltage') }}"
         -H "X-Pvoutput-SystemId: <system-id>"
         -H "X-Pvoutput-Apikey: <api-key>"
         https://pvoutput.org/service/r2/addstatus.jsp
```

In the above snippet, you need to replace `<system-id>` and `api-key` with values from your own PVOutput system. These can be string literals or something more clever such as helper values set via the web UI. Once saved, you'll need to restart Home Assistant.

Configure an automation as follows:

* Trigger: Time pattern with minutes set to `/5`, `/10` or `/15` to match your PVOutput expected reporting interval. Note that since the inverter only reports energy with 0.1kWh precision, longer intervals tend to work better, especially in overcast conditions when total energy may not increment over a short period.
* Conditions: Optionally, configure a State condition for the Sun entity with a value `above_horizon`. This trims off uninteresting parts of the day in your PVOutput logs and charts.
* Action: Set this to "Call service" and find "Shell Command: pvoutputcurl".