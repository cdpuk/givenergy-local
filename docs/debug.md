# Inverter debugging

Sometimes the integration isn't able to fetch data because it simply doesn't know how to ask. This is quite common as GivEnergy release new models and firmware updates.

In such situations it can be helpful to use `debug.py` which is included with the integration. This can be run in two ways:

- From a CLI within your Home Assistant installation. The script can be found under `custom_components/givenergy_local`.
- From a standalone development environment (a clone of this repository).

If you're able to successfully fetch some data in this way, please include on your bug report or feature request.

# Reliability

It's possible to run this script while the integration is running within Home Assistant, but for best results it's best to stop the integration (or Home Assistant). When both run in parallel, inverters appear to get requests confused with each other, resulting in corrupt data or timeouts that will disrupt your debugging results.

# A Modbus primer

Here's some brief background information to help understand the data you're asking for.

- Inverter communication happens over an industry standard(ish) protocol called Modbus.
- Inverters store data in 16-bit registers.
- Registers are organised in to categories of "holding registers" (HRs) and "input registers" (IRs).
- You can see existing known register mappings in `inverter.py` and `battery.py` within the `model` directory.
- When asking for register data, we normally ask for 60 at a time, starting from what we call the "base register".
- Each request we make is to a specific "slave address", with each device (e.g. inverters and batteries) having a different slave address.
- Different inverters support different combinations of slave addresses and base registers. Some trial and error is involved.

# Usage

## Simple case

By default, the script will:

- use slave address `0x32`;
- request input registers with base addresses 0, 60 and 120;
- request holding registers with base addresses 0, 60, 120 and 300.

The above settings have been found to work on a broad range of devices. All you have to do is provide your inverter IP address:

```
python debug.py 1.2.3.4
```

In response you'll hopefully get a table of values in hexadecimal format.

## Alternative slave addresses

Some inverters will respond on a different slave address. `0x32` is used by default, but a common alternative to try, particularly for AIO devices, is `0x11`. Some inverters respond on both.

To select an different slave address:

```
python debug.py 1.2.3.4 --slave 0x11
```

## Multiple batteries

The first connected battery has typically been observed to respond on the same slave address as the inverter (`0x32`), with the second on `0x33`, third on `0x34`, etc. This is also likely to vary dependent on model.

Battery data is normally seen in input registers at base address 60.

For example, to see battery data for the second connected battery:

```
python debug.py 1.2.3.4 --slave 0x33 --ir 60 --hr ""
```

Requesting this data for a battery that isn't present generally results in a successful response containing mostly zero values, but again this may vary.

## Other registers

As seen in the battery example, the lists of input registers and holding registers to fetch can be overridden with the `--ir` and `--hr` options respectively. These options accept comma separated lists (no spaces) or an empty string `""` to prevent requests for any registers of that type.
