# GivEnergy Local

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

This custom component provides local access to GivEnergy inverters via Modbus. This provides more frequent and reliable updates compared to using the GivEnergy Cloud API.

## Device Support

Model | Status
-- | --
Giv-HY5.0 | Tested by maintainer (battery support pending installation)

Modbus support is provided by the `givenergy-modbus` library. If other devices are found to have issues, it's likely that changes will need to be made to the underlying library.

## Sensors

The integraton provides the following sensors:

* PV Energy Total (kWh)
* PV Energy Today (kWh)
* PV Power (W)
* Grid Import Today (kWh)
* Grid Export Today (kWh)
* Grid Export Power (W, negative values indicating import)
* Inverter Output Today (kWh)
* Inverter Output Total (kWh)
* Consumption Total (kWh)
* Consumption Today (kWh)
* Consumption Power (W)
* AC Voltage (V)
* AC Frequency (Hz)
* Heatsink Temperature (C)
* Charger Temperature (C)

## Installation

You need to know the hostname or IP address of your inverter, which you can normally work out by looking at your router status pages. When using an IP address that was issued with DHCP, bear in mind it needs to remain stable; this is normally fine since inverters stay connected 24/7.

Install this integration via HACS, then enter the inverter address during the setup steps.

## Contributing

If you want to contribute to this please read the [Contribution Guidelines](CONTRIBUTING.md).

[commits-shield]: https://img.shields.io/github/commit-activity/y/cdpuk/givenergy-local.svg?style=for-the-badge
[commits]: https://github.com/cdpuk/givenergy-local/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/cdpuk/givenergy-local.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/cdpuk/givenergy-local.svg?style=for-the-badge
[releases]: https://github.com/cdpuk/givenergy-local/releases
