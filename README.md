# barista

[![CI](https://github.com/simonsteinberg/barista/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/simonsteinberg/barista/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/simonsteinberg/barista/branch/main/graph/badge.svg)](https://codecov.io/gh/simonsteinberg/barista)

Minimal Python project managed with mise and uv.

## Quickstart

1. Install tools and project dependencies:
```bash
mise install
mise run sync
```

2. Enable pre-commit hooks:
```bash
uv run pre-commit install
```

3. Run the greeting CLI:
```bash
uv run barista-greet
```

Expected output:

	Hello barista (version <CURRENT_VERSION>)

## Project Setup and Customization

### Rename the project

Use the `setup-repo` task to rename the entire project from `barista` to your desired project name:

```bash
mise run setup-repo -- myproject
```

This task will:
- Rename the `src/barista/` directory to `src/myproject/`
- Replace all occurrences of `barista` with `myproject` across the repository (in Python files, configuration files, documentation, etc.)
- Exclude git, cache, and build directories from the search

**Example:**
```bash
mise run setup-repo -- workflow_engine
```

**Requirements for the project name:**
- Must start with a letter or underscore
- Can only contain alphanumeric characters and underscores (no hyphens or special characters)

## Quality checks

- Pre-commit runs lint and test before each commit.
- CI runs lint and test on pull requests and on pushes to `main`.
- Coverage percentage badge is published via Codecov (requires repository secret `CODECOV_TOKEN`).
