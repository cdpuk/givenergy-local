"""Console script for interacting with GivEnergy inverters."""
import datetime
import logging

import click

from client import GivEnergyClient
from model.battery import Battery
from model.inverter import Inverter  # type: ignore
from model.plant import Plant
from util import InterceptHandler

_logger = logging.getLogger(__package__)


def is_documented_by(original):
    """Copies the docstring from the original source to the decorated target."""

    def wrapper(target):
        target.__doc__ = original.__doc__
        return target

    return wrapper


@click.group()
@click.option('-h', '--host', type=str, required=True, envvar='GIVENERGY_HOST')
@click.option(
    '--log-level',
    default='INFO',
    type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], case_sensitive=False),
)
@click.pass_context
def main(ctx, host, log_level):
    """A python library to access GivEnergy inverters via Modbus TCP, with no dependency on the GivEnergy Cloud."""
    ctx.ensure_object(dict)

    # Install our improved logging handler.
    logging.basicConfig(handlers=[InterceptHandler()], level=getattr(logging, log_level))
    ctx.obj['CLIENT'] = GivEnergyClient(host=host)


@main.command()
@click.pass_context
@click.option('-b', '--batteries', type=int, default=1)
def dump_registers(ctx, batteries):
    """Dump out raw register data for use in debugging."""
    plant = Plant(number_batteries=batteries)
    ctx.obj['CLIENT'].refresh_plant(plant=plant, full_refresh=True)
    inverter_json = plant.inverter_rc.to_json()
    inverter = Inverter.from_orm(plant.inverter_rc)

    batteries_json = {}
    for i in range(batteries):
        batteries_json[i] = plant.batteries_rcs[i].to_json()

    click.echo('Inverter registers:')
    click.echo(inverter_json)
    click.echo('Batteries registers:')
    click.echo(batteries_json)
    click.echo(inverter.json())
    for i in range(batteries):
        click.echo(Battery.from_orm(plant.batteries_rcs[i]).json())


@main.command()
@click.pass_context
@click.argument('target_soc', type=int)
@is_documented_by(GivEnergyClient.enable_charge_target)
def enable_charge_target(ctx, target_soc):  # noqa: D103
    ctx.obj['CLIENT'].enable_charge_target(target_soc)


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.disable_charge_target)
def disable_charge_target(ctx):  # noqa: D103
    ctx.obj['CLIENT'].disable_charge_target()


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.enable_charge)
def enable_charge(ctx):  # noqa: D103
    ctx.obj['CLIENT'].enable_charge()


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.disable_charge)
def disable_charge(ctx):  # noqa: D103
    ctx.obj['CLIENT'].disable_charge()


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.enable_discharge)
def enable_discharge(ctx):  # noqa: D103
    ctx.obj['CLIENT'].enable_discharge()


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.disable_discharge)
def disable_discharge(ctx):  # noqa: D103
    ctx.obj['CLIENT'].disable_discharge()


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.set_battery_discharge_mode_max_power)
def set_battery_discharge_mode_max_power(ctx):  # noqa: D103
    ctx.obj['CLIENT'].set_battery_discharge_mode_max_power()


@main.command()
@click.pass_context
@is_documented_by(GivEnergyClient.set_battery_discharge_mode_demand)
def set_battery_discharge_mode_demand(ctx):  # noqa: D103
    ctx.obj['CLIENT'].set_battery_discharge_mode_demand()


@main.command()
@click.option('-s', '--start', type=click.DateTime(formats=['%H:%m']), required=True)
@click.option('-e', '--end', type=click.DateTime(formats=['%H:%m']), required=True)
@click.pass_context
@is_documented_by(GivEnergyClient.set_charge_slot_1)
def set_charge_slot_1(ctx, start, end):  # noqa: D103
    _logger.info(start)
    _logger.info(end)
    ctx.obj['CLIENT'].set_charge_slot_1((start, end))


@main.command()
@click.option('-s', '--start', type=click.DateTime(formats=['%H:%M', '%H%M']), required=True)
@click.option('-e', '--end', type=click.DateTime(formats=['%H:%M', '%H%M']), required=True)
@click.pass_context
@is_documented_by(GivEnergyClient.set_charge_slot_2)
def set_charge_slot_2(ctx, start: datetime.datetime, end: datetime.datetime):  # noqa: D103
    _logger.info(start.time())
    _logger.info(end.time())
    ctx.obj['CLIENT'].set_charge_slot_2((start, end))


@main.command()
@click.argument('charge_limit', type=int)
@click.pass_context
@is_documented_by(GivEnergyClient.set_battery_charge_limit)
def set_battery_charge_limit(ctx, charge_limit: int):  # noqa: D103
    ctx.obj['CLIENT'].set_battery_charge_limit(charge_limit)


@main.command()
@click.argument('discharge_limit', type=int)
@click.pass_context
@is_documented_by(GivEnergyClient.set_battery_discharge_limit)
def set_battery_discharge_limit(ctx, discharge_limit: int):  # noqa: D103
    ctx.obj['CLIENT'].set_battery_discharge_limit(discharge_limit)


if __name__ == "__main__":
    main(obj={})  # pragma: no cover
