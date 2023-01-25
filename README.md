# GivEnergy Local

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

This custom component provides local access to GivEnergy inverters via Modbus. This provides more frequent and reliable updates compared to using the GivEnergy Cloud API.

## Device Support

Modbus support is provided by the [`givenergy-modbus`][givenergy-modbus] library. While this works well for the vast majority of GivEnergy inverters and batteries, inevitably there will be edge cases and new kit that requires updates to either this integration or the underlying library.

## Services

A number of services are provided to change settings by writing configuration values to your inverter. These operations map on to those provided by GivEnergy, such as turning on Eco mode, or changing charge/discharge rates.

While the risk of something going wrong is low, bear in mind the use of this integration is entirely at your own risk.

## Installation

This integration is delivered as a HACS custom repository.

1. Download and install [HACS][hacs-download].
2. Add a [custom repository][hacs-custom] in HACS. You will need to enter the URL of this repository when prompted: `https://github.com/cdpuk/givenergy-local`.

## Configuration

You need to know the hostname or IP address of your inverter, which you can normally work out by looking at your router status pages. When using an IP address that was issued with DHCP, bear in mind it needs to remain stable; this is normally fine since inverters stay connected 24/7.

* Go to **Configuration** > **Devices & Services** > **Add Integration**, then find **GivEnergy Local** in the list.
* Enter the inverter address when prompted.

If your Home Assistant instance is in a different VLAN or network than inverter, ensure it can reach the inverter via port 8899 (TCP).

## Limitations

The modbus connection used to communiate with GivEnergy inverters can be unreliable at times. This may be due to issues in the `givenergy_modbus` library, or the inverter firmware.

The integration attempts to work around some of these errors, but there's only so much that can be done.

If you see errors coming from the `givenergy_modbus` library, it's unlikely that anything can be done to this integration that will resolve the problem. Don't be offended if you bug report is closed in such cases.

## PVOutput upload

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

## Contributing

If you want to contribute to this please read the [Contribution Guidelines](CONTRIBUTING.md).

[commits-shield]: https://img.shields.io/github/commit-activity/y/cdpuk/givenergy-local.svg?style=for-the-badge
[commits]: https://github.com/cdpuk/givenergy-local/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/cdpuk/givenergy-local.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/cdpuk/givenergy-local.svg?style=for-the-badge
[releases]: https://github.com/cdpuk/givenergy-local/releases
[givenergy-modbus]: https://github.com/dewet22/givenergy-modbus
[hacs-download]: https://hacs.xyz/docs/setup/download
[hacs-custom]: https://hacs.xyz/docs/faq/custom_repositories