# Fin-Escape-Velocity

[![CI](https://github.com/simonsteinberg/finev/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/simonsteinberg/finev/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/simonsteinberg/finev/branch/main/graph/badge.svg)](https://codecov.io/gh/simonsteinberg/finev)

Wealth forecasting CLI and NiceGUI app, managed with mise and uv.

## Quickstart

Install tools and dependencies:
```bash
mise install
mise run sync
```

Run a console forecast:
```bash
mise run run
```

Launch the NiceGUI app:
```bash
mise run app
```
Open http://localhost:8081. To override the starting port:
```bash
WEALTH_APP_PORT=8090 mise run app
```

## Defaults

The console forecast and UI start with:
- Current age 40, retirement age 67, end age 100
- ETF MSCI World, bAV, and Daily account assets
- Monthly contributions (500 / 100 / 0)
- Monthly withdrawal after retirement: 3000 EUR

ETF withdrawals apply taxes at 26.25% on 70% of the gains portion. The
console output includes yearly taxes and net cashflow.

To customize the console defaults, edit `src/finev/cli.py`.

## Project Setup and Customization

### Rename the project

Use the `setup-repo` task to rename the entire project from `finev` to your desired project name:

```bash
mise run setup-repo -- myproject
```

This task will:
- Rename the `src/finev/` directory to `src/myproject/`
- Replace all occurrences of `finev` with `myproject` across the repository (in Python files, configuration files, documentation, etc.)
- Exclude git, cache, and build directories from the search

**Example:**
```bash
mise run setup-repo -- workflow_engine
```

**Requirements for the project name:**
- Must start with a letter or underscore
- Can only contain alphanumeric characters and underscores (no hyphens or special characters)

## Mise commands

| Command | Purpose |
| --- | --- |
| `mise install` | Install toolchain versions defined in `mise.toml`. |
| `mise run sync` | Install project dependencies with uv. |
| `mise run run` | Run the console forecast and print yearly totals. |
| `mise run app` | Launch the NiceGUI app on the first available port (default 8081). |
| `mise run format` | Format code with Ruff. |
| `mise run lint` | Run Ruff lint checks. |
| `mise run test` | Run the test suite. |
| `mise run coverage` | Run tests with terminal coverage summary. |
| `mise run coverage-ci` | Run tests and write CI coverage artifacts to `reports/`. |
| `mise run setup-repo -- <name>` | Rename the project to a new module name. |

## Code layout
- `cli.py`: Console entrypoint and default scenario.
- `forecast.py`: Forecast engine and validation logic.
- `models.py`: Domain models and defaults.
- `ui.py`: NiceGUI page composition.
- `app.py`: NiceGUI server entrypoint.

## Quality checks

- Pre-commit runs lint and test before each commit.
- CI runs lint and test on pull requests and on pushes to `main`.
- Coverage percentage badge is published via Codecov (requires repository secret `CODECOV_TOKEN`).
