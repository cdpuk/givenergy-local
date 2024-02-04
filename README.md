# GivEnergy Local

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

This custom component provides local access to GivEnergy inverters via Modbus. This provides more frequent and reliable updates compared to using the GivEnergy Cloud API.

While the risk of something going wrong is low, bear in mind the use of this integration is entirely at your own risk.

## Installation

This integration is delivered as a HACS custom repository.

1. Download and install [HACS][hacs-download].
2. Add a [custom repository][hacs-custom] in HACS. You will need to enter the URL of this repository when prompted: `https://github.com/cdpuk/givenergy-local`.

## Configuration

You need to know the hostname or IP address of your inverter, which you can normally work out by looking at your router status pages. When using an IP address that was issued with DHCP, bear in mind it needs to remain stable; this is normally fine since inverters stay connected 24/7.

* Go to **Configuration** > **Devices & Services** > **Add Integration**, then find **GivEnergy Local** in the list.
* Enter the inverter address when prompted.

Your Home Assistant instance must be able to establish a TCP connection to your inverter on port 8899.

## Documentation

* [Energy dashboard](docs/energy-dashboard.md)
* [Inverter controls](docs/controls.md)
* [Troubleshooting](docs/troubleshooting.md)
* [Uploading to pvoutput.org](docs/pvoutput.md)

## Limitations

GivEnergy are continually releasing new equipment and firmware. There is a risk that new devices won't work, or that firmware updates may suddenly prevent the integration being able to talk to your inverter.

If this happens, bear in mind the maintainers of this integration do not have access to your equipment, so debugging such issues can be challenging. Raise an issue with as much detail as possible to make it easier to help you.

## Acknowledgements

### givenergy_modbus

The Modbus protocol implementation for GivEnergy systems was originally created by the [`givenergy-modbus`][givenergy-modbus] project. Huge thanks goes to the author and contributors for unpicking the non-standard low level technical details of the protocol.

Since the project was paused, the current implementation of this integration uses an embedded forked version of the library so that further bugfixes and updates can be made without an external dependency.

### GivTCP

[GivTCP][givtcp] is an alternative to this integration, which runs as a Home Assistant add-on, and therefore may not be suitable for all installations. However, it sees frequent updates and several compatibility updates made to that project have been reused here.

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
[givtcp]: https://github.com/britkat1980/giv_tcp
[hacs-download]: https://hacs.xyz/docs/setup/download
[hacs-custom]: https://hacs.xyz/docs/faq/custom_repositories