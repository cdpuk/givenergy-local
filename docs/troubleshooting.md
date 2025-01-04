# Troubleshooting

## Debugging techniques

### Debug logs

If something isn't right, the first place to start (before raising an issue) is the debug logs.

There are two ways to capture debug logs:

1. Via the UI, see https://www.home-assistant.io/docs/configuration/troubleshooting/#enabling-debug-logging
2. Via the configuration file, see https://www.home-assistant.io/components/logger/

There will often be clues as to what's going wrong, and these logs are essential to include when raising an issue.

When capturing logs, it's important to include the moment the integration loads, as certain log entries may only be produced once at this point. You can achieve this by reloading the integration via the Home Assistant UI.

### GivEnergy portal

The GivEnergy web portal provides a more detailed view on to inverter configuration, compare to the app which is a fairly simplified view.

To access this:

- Go to https://www.givenergy.cloud/ and log in.
- Select "My Inverter" from the menu.
- Find the icon for "Remote Control" in the top-right of the page.

The "Remote Control History" panel is particularly useful, as the "Show Raw Values" checkbox exposes the values get sent to/from the inverter.

## CRC errors

Logs may sometimes indicate CRC errors in data received from the inverter. This happens when corrupt/invalid data is received. The integration will automatically retry up to a limit of 3 total attempts for each request. After that point it will give up and entities in the UI will be `unavailable` until data can be fetched successfully again.

The volume of these errors typically increases when the inverter is being queried from multiple locations at the same time, e.g. by running both this integration and GivTCP.

## Warning about values not strictly increasing

You may see warnings in your Home Assistant logs such as:

```log
Entity sensor.consumption_today from integration givenergy_local has state class total_increasing, but its state is not strictly increasing.
```

This is a known issue and is caused by the GivEnergy firmware decrementing a value in a way that shouldn't be possible. For example, you would expect your consumption figure in kWh to increase over the course of a day, however it's relatively common to this this drop by 0.1 at a random point during the day.

This is considered a bug in the GivEnergy firmware and won't be fixed in the integration.

## Timeslots with invalid values

If you can't connect at all and your logs mention failure to convert charge/discharge slot values, you may find that these values are not correctly set on the inverter.

To see all available slots, you must log in to the GivEnergy web portal (see above). If any of the start/end times are blank, update these with a value, even if it's just to set the start and end times to the same value.

## Errors after a new year

GivEnergy firmware has been observed to poorly handle the new year transition, which may result in an error message such as:

```log
Failed to convert system_time from [25, 13, 1, 6, 45, 40]: month must be in 1..12
```

The inverter firmware appears to incorrectly increment the month from 12 to 13, which results in an invalid date. To fix this, visit the GivEnergy Portal and manually correct the date.

## Low level debug

If you're struggling to get data out of your inverter, you may need to resort to [low-level debugging](debug.md) to understand how the data is structured.
