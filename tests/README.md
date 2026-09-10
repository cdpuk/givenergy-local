# Why?

While tests aren't required to publish a custom component for Home Assistant, they will generally make development easier because good tests will expose when changes you want to make to the component logic will break expected functionality. Home Assistant uses [`pytest`](https://docs.pytest.org/en/latest/) for its tests, and the tests that have been included are modeled after tests that are written for core Home Assistant integrations. These tests pass with 100% coverage (unless something has changed ;) ) and have comments to help you understand the purpose of different parts of the test.

# Getting Started

Dependencies are managed with [uv](https://docs.astral.sh/uv/). From the repository root, run:
```bash
uv sync
```

This creates a `.venv` and installs `homeassistant`, `pytest`, and `pytest-homeassistant-custom-component`, a plugin which allows you to leverage helpers that are available in Home Assistant for core integration tests.

# Useful commands

Command | Description
------- | -----------
`uv run pytest tests/` | This will run all tests in `tests/` and tell you how many passed/failed
`uv run pytest --durations=10 --cov-report term-missing --cov=custom_components.givenergy_local tests` | This tells `pytest` that your target module to test is `custom_components.givenergy_local` so that it can give you a [code coverage](https://en.wikipedia.org/wiki/Code_coverage) summary, including % of code that was executed and the line numbers of missed executions.
`uv run pytest tests/test_init.py -k test_setup_unload_and_reload_entry` | Runs the `test_setup_unload_and_reload_entry` test function located in `tests/test_init.py`
