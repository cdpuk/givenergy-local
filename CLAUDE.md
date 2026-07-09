# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is **GivEnergy Local**, a Home Assistant custom component (HACS custom repository) that talks to GivEnergy solar inverters over the local network via Modbus (TCP port 8899), instead of the GivEnergy Cloud API. The integration domain is `givenergy_local` and all component code lives under `custom_components/givenergy_local/`.

## Commands

Install dependencies:

```
pip install -r requirements.txt -r requirements_dev.txt -r requirements_test.txt
pre-commit install
```

Testing (uses `pytest-homeassistant-custom-component`; `asyncio_mode = auto`):

```
pytest tests/                                              # all tests
pytest tests/test_init.py -k test_setup_unload_and_reload_entry   # single test
pytest --cov=custom_components.givenergy_local --cov-report term-missing tests   # with coverage
```

Lint / type-check (also runs via pre-commit and CI):

```
pre-commit run --all-files    # ruff (check + format), codespell, yamllint, actionlint, mypy
mypy custom_components/        # type-check on its own
```

There is a devcontainer (`.devcontainer.json`) that runs an isolated Home Assistant instance against the `config/` directory for manual testing.

## Architecture

The code is in two layers with a hard boundary between them:

### 1. Modbus protocol library — external `givenergy-modbus` (PyPI)

The non-standard GivEnergy Modbus protocol is handled by the published [`givenergy-modbus`](https://github.com/dewet22/givenergy-modbus) package (pinned in `manifest.json` / `requirements*.txt`). It was previously vendored under `givenergy_modbus/`; that tree has been removed and the integration imports the package as `givenergy_modbus.*`. Key pieces the integration uses:

- `givenergy_modbus.client.client.Client` — async client holding a long-lived TCP connection. `detect()` resolves device type/topology (sets `plant.capabilities`); `load_config()` reads holding-register config blocks; `refresh()` reads input-register measurements; `execute()` sends write commands. (`refresh_plant()` still exists but is deprecated upstream — don't reintroduce it.)
- `givenergy_modbus.client.commands` — **module-level functions** (e.g. `set_mode_dynamic`, `set_charge_slot_1`, `set_inverter_reboot`, `set_charge_target_enabled`) plus `RegisterMap` (holding-register addresses). Not a `CommandBuilder` class.
- `givenergy_modbus.model.plant.Plant` — exposes `.inverter`, `.batteries`, `.number_batteries` (these require `detect()` to have populated `capabilities`).
- Models: `model.inverter` (`SinglePhaseInverter`, `Model`, `Generation`, `BatteryPowerMode`), `model.inverter_threephase.ThreePhaseInverter`, `model.battery` (`Battery`, `BatteryPauseMode`, `ExportPriority`), `model.TimeSlot`. Register values are read via pydantic `model_dump()`.

Upstream field names differ from the old fork; see `entity.py`/`sensor.py` for the current names (e.g. `t_inverter_heatsink`, `battery_soc`, `p_backup`, `e_pv_generation_total`). Sensor entity descriptions keep a stable `key` (used for the entity `unique_id`) and use `ge_modbus_key` for the register lookup where upstream renamed a field — do not change `key` values, as that orphans users' existing entities.

### 2. Home Assistant integration layer

- `__init__.py` — `async_setup_entry` creates the coordinator, forwards setup to platforms, registers services. Platforms enabled: `binary_sensor`, `number`, `sensor`, `select`, `switch`, `time`.
- `coordinator.py` — `GivEnergyUpdateCoordinator` (a `DataUpdateCoordinator[Plant]`) is the heart of the integration. It polls every 10s, forces a full refresh every 5 min, retries on bad data, and reconnects on timeout. `execute()` runs write commands then forces a refresh.
- `entity.py` — base `InverterEntity` and `BatteryEntity` (both `CoordinatorEntity`). They map decoded model data into HA `DeviceInfo`; `_BATTERY_CAPACITY_TO_MODEL` and `_MODEL_DESCRIPTIONS` translate raw values to human-readable model names.
- Platform files (`sensor.py`, `number.py`, `select.py`, `switch.py`, `time.py`, `binary_sensor.py`) — mostly declarative lists of `EntityDescription`s keyed by a model attribute / modbus key. To add a sensor, add an entry to the relevant description list rather than writing a new class.
- `services.py` + `services.yaml` — HA services (e.g. `activate_mode_eco`, `enable_timed_charge`, `reboot_inverter`, `sync_clock`). Each service resolves the target device to its coordinator via the device registry, builds commands with the `givenergy_modbus.client.commands` functions (imported as `ge_commands`), and calls `coordinator.execute()`. `services.yaml` and `translations/en.json`/`strings.json` must stay in sync with the code.

### Data flow

`Client` (TCP) → decodes PDUs into per-address `RegisterCache` inside `Plant` → coordinator validates → `Plant.inverter`/`.batteries` pydantic models → `InverterEntity`/`BatteryEntity` expose values to HA. Writes go the reverse way: service/platform → `ge_commands.set_*()` → `coordinator.execute()` → `Client`.

## Conventions

- Formatting/linting is **ruff** (check + format); line length 88. Do not hand-format — let `ruff-format` do it.
- Type checking is strict via `mypy.ini`; the external `givenergy_modbus.*` package is set to `ignore_missing_imports`.
- CI runs on Python 3.13 and 3.14; target modern syntax (`from __future__ import annotations`, `X | None`, `py312-plus`).
- `manifest.json` `version` is bumped manually per release; keep it updated for HACS. The `givenergy-modbus` dependency is also pinned there (and in `requirements*.txt`).
- When adding an inverter capability, wire it through: the `givenergy_modbus` command function / `RegisterMap` (protocol) → coordinator/service (HA action) → entity description (exposed value) → `services.yaml`/translations (UI), and add tests under `tests/`.
