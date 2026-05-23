from __future__ import annotations

import tomllib
from pathlib import Path


def get_version() -> str:
    """Read the project version from pyproject.toml."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def main() -> None:
    version = get_version()
    print(f"Hello barista (version {version})")


if __name__ == "__main__":
    main()
