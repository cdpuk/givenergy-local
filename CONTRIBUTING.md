# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `master`.
2. Ensure your development and test environment is configured correctly (see below).
3. If you've changed something, update the documentation.
4. Test your contribution, and ensure any relevant tests have been updated.
5. Open a pull request.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainer if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose).

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Use a Consistent Coding Style

This project uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting, and [mypy](https://mypy-lang.org/) in strict mode. Both are configured in `pyproject.toml`.

Don't format by hand. The `pre-commit` hooks set up below apply the formatting for you, and CI runs the same checks on every pull request.

## Developing & testing

The integration requires Python 3.14.2 or newer, and supports Home Assistant 2026.3.0 or newer.

This repository is set up with support for Visual Studio Code development containers. After you've forked and opened the repository, VS Code will prompt you to reopen the project inside a container.

This allows you to easily run the integration against an isolated Home Assistant instance.

Dependencies are managed with [uv](https://docs.astral.sh/uv/). Install everything and configure the `pre-commit` checks with:

```
scripts/setup
```

That is equivalent to:

```
uv sync
uv run pre-commit install
```

The devcontainer is optional. `scripts/setup` works anywhere uv is installed, and uv downloads a suitable Python version for you.

Run the tests and checks from the locked environment:

```
uv run pytest tests/
uv run pre-commit run --all-files
```

To try your changes against a real inverter, start Home Assistant with:

```
scripts/develop
```

This creates a `config` directory on first run and serves Home Assistant on port 8123, forwarded to port 9123 on the host when using the devcontainer. VS Code also offers this as the "Run Home Assistant" task.

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`, which is committed. If you change a dependency, run `uv lock` and include the updated lock file in your pull request.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
