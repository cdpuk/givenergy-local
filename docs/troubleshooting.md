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

## Data issues

Sometimes inverters supply bad data to the integration that can't be understood. This may cause the integration to fail.

### Timeslots with invalid values

If you can't connect at all and your logs mention failure to convert charge/discharge slot values, you may find that these values are not correctly set on the inverter.

To see all available slots, you must log in to the GivEnergy web portal (see above). If any of the start/end times are blank, update these with a value, even if it's just to set the start and end times to the same value.
