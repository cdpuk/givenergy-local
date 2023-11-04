# GivEnergy Local

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

This custom component provides local access to GivEnergy inverters via Modbus. This provides more frequent and reliable updates compared to using the GivEnergy Cloud API.

While the risk of something going wrong is low, bear in mind the use of this integration is entirely at your own risk.

## Device Support

Modbus support is provided by the [`givenergy-modbus`][givenergy-modbus] library. While this works well for the vast majority of GivEnergy inverters and batteries, inevitably there will be edge cases and new kit that requires updates to either this integration or the underlying library. See the [Limitations](#limitations) section.

## Installation

This integration is delivered as a HACS custom repository.

1. Download and install [HACS][hacs-download].
2. Add a [custom repository][hacs-custom] in HACS. You will need to enter the URL of this repository when prompted: `https://github.com/cdpuk/givenergy-local`.

## Configuration

You need to know the hostname or IP address of your inverter, which you can normally work out by looking at your router status pages. When using an IP address that was issued with DHCP, bear in mind it needs to remain stable; this is normally fine since inverters stay connected 24/7.

* Go to **Configuration** > **Devices & Services** > **Add Integration**, then find **GivEnergy Local** in the list.
* Enter the inverter address when prompted.

If your Home Assistant instance is in a different VLAN or network than inverter, ensure it can reach the inverter via TCP port 8899.

## Documentation

* [Energy dashboard](docs/energy-dashboard.md)
* [Inverter controls](docs/controls.md)
* [Uploading to pvoutput.org](docs/pvoutput.md)

## Limitations

This integration uses the latest public release of the `givenergy_modbus` library. Unfortunately, this hasn't kept pace with GivEnergy product updates, so may be incompatible with communication methods and features found in newer systems.

The current `givenergy_modbus` uses a communication method that is known to be slightly unreliable. Your Home Assistant logs are likely to be filled with a gradual stream of errors from the library. However, due to the fairly high update rate, the odd missed update is rarely an issue.

Other community projects such as GivTCP have chosen to copy & modify the `givenergy_modbus` library to resolve some of these issues, however those modifications have not been released as a standalone project that can easily be reused by this integration.

Don't be offended if you bug report is closed if it relates to the above limitations.

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